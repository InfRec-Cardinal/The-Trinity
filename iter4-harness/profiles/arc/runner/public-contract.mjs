import assert from 'node:assert/strict';
import {repairRequestContract} from './request-contract.mjs';
import {NativeDecisionConversation} from './native-decision-protocol.mjs';
import {PublicExecutionReceipts} from './public-execution-receipts.mjs';

export const PUBLIC_CONTRACT='Public output contract: submit_action accepts the native game action only. Auxiliary tools accept the public task evidence needed by their documented computation. Do not place a continuing work journal, self-analysis, action justification or reasoning transcript into tool arguments. Execution counts and observed feedback are supplied by the host. Skill references to recording or writing are handled by the public host receipts and do not require extra output. Module advice may be acted on or rejected; no written acknowledgment is required. Predictions and interpretations are not observations or proof of success.';

export function preparePublicTemplate(source,branch) {
  const {branchTool,branchNotice}=branch;
  assert.equal(source.messages.length,0,'Only a new unsigned template can be changed');
  const template=structuredClone(source);
  const native=template.tools.find(t=>t.name==='submit_action');assert(native);
  assert.deepEqual(Object.keys(native.input_schema.properties).sort(),['action','x','y']);
  assert.deepEqual(native.input_schema.required,['action']);
  template.tools=[native,structuredClone(branchTool)];
  assert(template.system.some(b=>b.text?.includes(branchNotice)),'Frozen v7 module notice required');
  const repaired=repairRequestContract(template).request;
  repaired.system.at(-1).text+='\n'+PUBLIC_CONTRACT;
  return repaired;
}

export function publicBlocks(observation,preview,receipts) {
  if(preview)assert(preview.ok,preview.error);
  return [{type:'text',text:observation.publicText},
    {type:'text',text:'PUBLIC_EXECUTION_RECEIPTS: '+JSON.stringify(receipts.snapshot())},
    ...(preview?[{type:'text',text:'PUBLIC CONTROL MODULE: '+JSON.stringify({...preview.output,moduleAdvice:true,noWorldActionExecuted:true})}]:[])];
}

export function prepareFromRecords(template,records,session,branch) {
  assert(records.length&&records[0].action==null);
  const receipts=new PublicExecutionReceipts(records[0].observation);
  session?.observeInitial(records[0].observation);
  for(const row of records.slice(1)) {
    receipts.record(row.action,row.observation);
    session?.record(row.action,row.observation);
  }
  const preview=session?.preview();if(preview)assert(preview.ok,preview.error);
  const current=records.at(-1).observation;
  const body=preparePublicTemplate(template,branch);
  body.messages=[{role:'user',content:[
    {type:'text',text:JSON.stringify({kind:'public_environment_checkpoint',
      nativeActions:records.length-1,remainingNativeActions:Number(process.env.ARC_NATIVE_ACTION_LIMIT??240)-(records.length-1),
      actionReceipts:receipts.all(),recentPublicObservations:records.slice(-5).map((r,i)=>({
        id:`obs-${Math.max(0,records.length-5)+i}`,publicText:r.observation.publicText})),
      source:'Host-owned public game observations and actual actions. No previous Player plan or private reasoning is imported.'})},
    ...publicBlocks(current,preview,receipts)]}];
  return {conversation:new NativeDecisionConversation(body),receipts,preview};
}

export function parseNativeAction(input) {
  assert(input&&typeof input==='object'&&!Array.isArray(input),'Native action object required');
  assert(Object.keys(input).every(k=>['action','x','y'].includes(k)),'Only native action fields are accepted');
  assert(['RESET','ACTION1','ACTION2','ACTION3','ACTION4','ACTION5','ACTION6','ACTION7'].includes(input.action));
  if(input.action==='ACTION6')for(const k of ['x','y'])assert(Number.isInteger(input[k])&&input[k]>=0&&input[k]<=63,'Invalid coordinate');
  else assert(input.x===undefined&&input.y===undefined,'Coordinates only apply to ACTION6');
  return structuredClone(input);
}
