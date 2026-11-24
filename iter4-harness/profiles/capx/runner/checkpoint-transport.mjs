import {fileURLToPath} from 'node:url';
import {readResponseLog,recordReplayFailure,verifyReplayObservations} from '../../../vendor/resume-response-log.mjs';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {execFileSync} from 'node:child_process';

const source=process.env.SOON_RESUME_SOURCE;
const lines=p=>fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const requests=source?lines(path.join(source,'api-requests.jsonl')):[];
const responses=new Map(readResponseLog(source,requests).map(r=>[r.captureId,r]));
const digest=x=>crypto.createHash('sha256').update(JSON.stringify(x)).digest('hex');

const canonical=b=>({...b,
  system:b.system.map(({cache_control,...block})=>block),
  tools:b.tools.map(({cache_control,...tool})=>tool),
  messages:b.messages.map(m=>({...m,content:m.content.map(({cache_control,...block})=>block)}))});
const imageProofs=new Map();let cursor=0,latestProofs=[],boundaryVerified=false;
const sourceResult=source?JSON.parse(fs.readFileSync(path.join(source,'..','results.json'))).results.find(r=>r.episode===path.basename(source)):null;
const pendingAtTimeout=sourceResult?.outcome==='timeout' && /awaiting the Player request/.test(sourceResult.reason??'');

export function resumeElapsedMs(){
  if(!source)return 0;
  const rows=JSON.parse(fs.readFileSync(path.join(source,'..','results.json'))).results;
  const row=rows.find(r=>r.episode===path.basename(source));
  assert(row,'Resume source has no result row');
  return (row.seconds??0)*1000;
}

export function canonicalizeReplayRequest(request){
  if(!source||cursor>=requests.length)return request;
  const result=structuredClone(request), expected=requests[cursor].request;
  latestProofs=[];const imageGroups=new Map();
  function walk(x,y,p=''){
    if(!x||!y||typeof x!=='object'||typeof y!=='object')return;
    if(x.type==='image'&&y.type==='image'&&x.source?.media_type==='image/png'&&y.source?.media_type==='image/png'){
      const groupKey=p.split('/content/')[0];
      if(!imageGroups.has(groupKey))imageGroups.set(groupKey,{changed:0,total:0,max:0});
      const group=imageGroups.get(groupKey);
      if(x.source.data!==y.source.data){
        const key=digest(x.source.data)+'|'+digest(y.source.data);let proof=imageProofs.get(key);
        if(!proof){
          proof=JSON.parse(execFileSync(process.env.CAPXO_PYTHON,
            [fileURLToPath(new URL('./verify-replay-png.py',import.meta.url))],
            {input:JSON.stringify({a:x.source.data,b:y.source.data}),encoding:'utf8',timeout:10000}));
          imageProofs.set(key,proof);
        }
        group.changed+=proof.changedPixels;group.total+=proof.totalPixels;group.max=Math.max(group.max,proof.maxChannelDifference);
        latestProofs.push({path:p,...proof});x.source.data=y.source.data;
      }else{
        const key='dimensions:'+digest(x.source.data);let proof=imageProofs.get(key);
        if(!proof){proof=JSON.parse(execFileSync(process.env.CAPXO_PYTHON,[fileURLToPath(new URL('./verify-replay-png.py',import.meta.url))],{input:JSON.stringify({a:x.source.data,b:x.source.data}),encoding:'utf8',timeout:10000}));imageProofs.set(key,proof);}
        group.total+=proof.totalPixels;
      }
      return;
    }
    for(const k of Object.keys(x))if(k in y)walk(x[k],y[k],p+'/'+k);
  }
  walk(result,expected);

  for(const [key,g] of imageGroups){
    const passed=g.max<=1 && g.changed<=Math.max(1,Math.floor(g.total*0.0001));
    assert(passed,'Public RGB observation replay mismatch: '+key+' '+JSON.stringify(g));
    if(g.changed)latestProofs.push({group:key,passed,changedPixels:g.changed,totalPixels:g.total,maxChannelDifference:g.max,scope:'complete observation camera views'});
  }
  assert.equal(digest(canonical(result)),digest(canonical(expected)),
    'Request content changed during replay at index '+cursor);
  return result;
}

function verifyState(runDir,complete=false){
  const name=path.basename(source);
  const record=lines(path.join(runDir,'episodes',name,'record.jsonl'));
  const original=lines(path.join(source,'episodes',name,'record.jsonl'));
  assert(record.length<=original.length,'Replay passed original environment boundary');
  if(complete)assert.equal(record.length,original.length,'Incomplete native replay');
  verifyReplayObservations(original.slice(0,record.length),record,{compareFrames:false});
  const dir=path.join(runDir,'episodes',name,'actions'),old=path.join(source,'episodes',name,'actions');
  for(const f of fs.existsSync(dir)?fs.readdirSync(dir).filter(f=>f.endsWith('.json')):[]){
    assert.equal(digest(JSON.parse(fs.readFileSync(path.join(dir,f)))),
      digest(JSON.parse(fs.readFileSync(path.join(old,f)))),'Native state replay mismatch: '+f);
  }
  return record.length-1;
}

function boundary(runDir){
  if(!boundaryVerified){
    const nativeActions=verifyState(runDir,true);
    fs.writeFileSync(path.join(runDir,'resume-verified.json'),JSON.stringify({
      passed:true,source,nativeActions,replayedResponses:cursor,
      networkCallsBeforeBoundary:0,originalSignedPrefixPreserved:true,
      cacheMetadataMayDiffer:true,pngJitterProofs:imageProofs.size
    },null,2));
    boundaryVerified=true;
  }
  if(process.env.SOON_RESUME_VERIFY_ONLY==='1')throw Error('OFFLINE_RESUME_VERIFIED_NO_NETWORK');
}

export function finishReplay(runDir){
  if(!source||boundaryVerified)return;
  try{
    assert.equal(cursor,requests.length,'Unconsumed archived request history');
    boundary(runDir);
  }catch(error){recordReplayFailure(runDir,error);throw error;}
}

export function replayResponse(request,runDir){
  if(!source)return null;
  if(cursor>=requests.length){boundary(runDir);return null;}
  const previous=requests[cursor];
  assert.equal(digest(canonical(request)),digest(canonical(previous.request)),'Archived request content not exact');
  const nativeActions=verifyState(runDir);
  const response=responses.get(previous.captureId);
  const cached=Boolean(response && response.status>=200 && response.status<300);
  fs.appendFileSync(path.join(runDir,'resume-checks.jsonl'),JSON.stringify({
    index:cursor,requestContentExact:true,nativeActions,cachedResponse:cached,pngJitter:latestProofs
  })+'\n');

  if(pendingAtTimeout && cursor===requests.length-1){
    boundary(runDir);cursor++;return cached?response:null;
  }
  if(!cached){
    assert.equal(cursor,requests.length-1,'Missing response inside replay prefix');
    boundary(runDir);cursor++;return null;
  }
  cursor++;return response;
}
