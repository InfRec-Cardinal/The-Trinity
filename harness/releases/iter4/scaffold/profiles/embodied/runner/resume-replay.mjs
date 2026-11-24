import {readResponseLog,verifyReplayState,recordReplayFailure} from '../../../vendor/resume-response-log.mjs';
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';
const source=process.env.SOON_RESUME_SOURCE;
const lines=p=>fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const requests=source?lines(path.join(source,'api-requests.jsonl')):[];
const responses=new Map(readResponseLog(source,requests).map(r=>[r.captureId,r]));
let cursor=0,replayedResponses=0,boundaryVerified=false;
export function resumeElapsedMs(){
 if(!source)return 0;
 const file=fs.readdirSync(path.join(source,'episodes'))[0];const rows=lines(path.join(source,'episodes',file,'record.jsonl'));
 const resultFile=path.join(source,'..','results.json');
 const result=fs.existsSync(resultFile)?JSON.parse(fs.readFileSync(resultFile,'utf8')).results?.find(r=>r.episode===path.basename(source)):null;
 return Math.max(Number(rows.at(-1).observation.publicText.match(/Time used: (\d+) s/)?.[1]??0),result?.seconds??0)*1000;
}
function boundary(runDir){
 if(!boundaryVerified){
  const nativeActions=verifyReplayState(source,runDir);
  fs.writeFileSync(path.join(runDir,'resume-verified.json'),JSON.stringify({passed:true,source,requests:cursor,replayedResponses,nativeActions,networkCallsBeforeBoundary:0},null,2));
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
 while(cursor<requests.length){
  const previous=requests[cursor];
  assert.deepEqual(request,previous.request,'Restored API request differs at index '+cursor);
  const response=responses.get(previous.captureId);
  const cached=Boolean(response&&response.status>=200&&response.status<300);
  fs.appendFileSync(path.join(runDir,'resume-checks.jsonl'),JSON.stringify({index:cursor,captureId:previous.captureId,exactRequestMatch:true,cachedResponse:cached,requestSha256:crypto.createHash('sha256').update(JSON.stringify(request)).digest('hex')})+'\n');cursor++;
  if(cached){replayedResponses++;return response;}
                                                                         
                                                                           
 }
 boundary(runDir);return null;
}
