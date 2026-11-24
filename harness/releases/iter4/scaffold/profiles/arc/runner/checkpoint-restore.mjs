import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {parseMessage,selectAction} from './player-protocol.mjs';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const rows=p=>fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const publicData=o=>JSON.parse(o.publicText.slice(o.publicText.indexOf('{')));
const comparable=o=>{const d=publicData(o);delete (d.data??d).guid;return d;};

export async function restoreCheckpoint({checkpointDir,opened,driver,episode,runDir,policySession,
  buildObservationTurn,buildToolResultTurn,stopAt=101}){
  assert([100,101].includes(stopAt));
  const checkpoint=read(path.join(checkpointDir,'checkpoint.json'));
  const source=checkpoint.originalEpisode;
  const original=rows(path.join(source,'episodes/case-6-repeat-1/record.jsonl'));
  const diagnostic=rows(path.join(checkpointDir,'episodes/case-6-repeat-1/record.jsonl'));
  const records=[...original,diagnostic.at(-1)];
  assert.equal(records.length,102);assert.equal(original.length,101);
  assert.equal(checkpoint.nativeActions,101);assert.equal(checkpoint.caseId,episode.caseId);
  assert.equal(driver.configurations[episode.configurationIndex].id,checkpoint.caseId);
  const calls=new Map();
  const responses=new Map(rows(path.join(source,'api-responses.jsonl')).map(r=>[r.captureId,r]));
  for(const req of rows(path.join(source,'api-requests.jsonl'))){
    const response=responses.get(req.captureId);assert(response);
    const selected=selectAction(parseMessage(response.raw),req.request.tools);
    if(selected.toolName!=='submit_action'||!selected.action)continue;
    const matches=req.request.messages.flatMap(m=>m.content??[]).filter(b=>b.type==='text')
      .flatMap(b=>[...b.text.matchAll(/Current public observation obs-(\d+); remaining native actions/g)]);
    assert.equal(matches.length,1);
    const step=Number(matches[0][1]);assert(!calls.has(step));
    calls.set(step,{toolId:selected.toolId,action:selected.action,content:selected.assistantContent,actor:'archived_player'});
  }
  for(const reset of rows(path.join(source,'host-resets.jsonl'))){
    assert(!calls.has(reset.step));
    calls.set(reset.step,{toolId:reset.toolId,action:reset.action,actor:'official_protocol_host',content:[
      {type:'text',text:'[Harness automatic action: GAME_OVER/NOT_PLAYED recovery; no model call.]'},
      {type:'tool_use',id:reset.toolId,name:driver.tool.name,input:reset.action}]});
  }
  const latestRequest=read(path.join(checkpointDir,'api-request.json'));
  const latest=selectAction(parseMessage(fs.readFileSync(path.join(checkpointDir,'api-response.raw'),'utf8')),latestRequest.tools);
  assert.equal(latest.stopReason,'tool_use');assert.equal(latest.toolName,'submit_action');
  calls.set(100,{toolId:latest.toolId,action:latest.action,content:latest.assistantContent,actor:'checkpoint_player'});
  const originalGuid=publicData(original[0].observation).data.guid;
  const replayGuid=publicData(opened.observation).data.guid;

  const normalize=o=>({...o,publicText:o.publicText.replaceAll(replayGuid,originalGuid)});
  const nativeStep=opened.step.bind(opened);
  opened.step=async(...args)=>normalize(await nativeStep(...args));
  let observation=normalize(opened.observation);
  const evidence=[];
  const verify=(got,want,step)=>{
    assert.deepEqual(comparable(got),comparable(want),'public observation '+step);
    assert.deepEqual(got.terminal,want.terminal,'terminal '+step);
    const {nativeStateHash:a,...ai}=got.info,{nativeStateHash:b,...bi}=want.info;
    assert.deepEqual(ai,bi,'counters '+step);
    const frame=got.frame??got.previewFrame;
    assert.equal(frame.sha256,want.frame.sha256,'RGB '+step);
    evidence.push({step,publicMatched:true,countersMatched:true,rgbMatched:true,
      nativeStateHash:a,archivedNativeStateHash:b,rawNativeHashComparable:false});
  };
  verify(observation,records[0].observation,0);
  policySession.observeInitial(observation);
  const stored=[];
  for(let step=0;step<stopAt;step++){
    const call=calls.get(step);assert(call,'missing paid receipt '+step);
    assert.deepEqual(driver.normalizeAction(call.action),records[step+1].action,'action '+step);
    stored.push(buildObservationTurn(observation));
    stored.push({role:'assistant',content:call.content});
    observation=await opened.step(call.action,{index:step});
    verify(observation,records[step+1].observation,step+1);
    stored.push(buildToolResultTurn(call.toolId,observation));
    policySession.record(call.action,observation);
  }
  const preview=policySession.preview();assert(preview.ok);
  const expected=stopAt===101?read(path.join(checkpointDir,'continued-policy-preview.json')):
    read(path.join(checkpointDir,'module-predecision.json'));
  assert.equal(preview.moduleHash,expected.moduleHash);assert.equal(preview.snapshotHash,expected.snapshotHash);
  assert.deepEqual(preview.output,expected.output);
  const proof={source,checkpointDir,restoredNativeActions:stopAt,observationsMatched:evidence.length,
    playerRequestsForRestoration:0,sourceRecordsHash:hash(records.slice(0,stopAt+1)),
    originalGuid,replayGuid,policySnapshotHash:preview.snapshotHash,evidence,
    caveat:'Private hashes include process-dependent keys; public observations, RGB, counters and policy ledger were verified.'};
  fs.writeFileSync(path.join(runDir,'checkpoint-restoration.json'),JSON.stringify(proof,null,2)+'\n');
  return {opened,observation,stored,steps:stopAt};
}
