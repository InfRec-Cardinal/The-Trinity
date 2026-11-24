import fs from 'node:fs';
import path from 'node:path';
import {applyRelay,askModelJson} from './model-io.mjs';
import {judgeDesign} from './design.mjs';
import {createLevel} from './create-level.mjs';
import {renderLevel} from './level-engine.mjs';

export async function buildVerifiedLevel({code,apiKey,relay,callModel,vendorDir,capability,brief,directory,feedback=null,contract=null}) {
  fs.mkdirSync(directory,{recursive:true});
  const save = (name,value)=>fs.writeFileSync(path.join(directory,name),JSON.stringify(value,null,2)+'\n');
  const common = {code,apiKey,relay,callModel,vendorDir};
  const {design} = contract?.value??await judgeDesign({...common,existingCapabilities:[capability],capabilityText:JSON.stringify({
    instruction:'Use exactly the supplied capabilityId. Preserve the full mechanism, observations, actions, budget and scoring in the brief. Do not invent external data or simplify a benchmark into a different toy task. If faithful execution is impossible with the UI contract, return an invalid design and explain the missing dependency.',
    ...(contract?{screeningConstraint:'Declare a positive integer actionBudget in the design before construction. The full design, actions, scoring, difficulty dimension names and ranges, and actionBudget will be frozen for all screening retries in this iteration. Only tune difficulty within those ranges; no replacement mechanics or dimensions.'}:{}),
    capabilityId:capability.id,brief,feedback})});
  if (design.capabilityId !== capability.id) throw Error('Design changed the assigned capability ID');
  contract?.pin(design);
  save('design.json',design);
  if(contract)save('screening-contract.json',contract.value);
  const built = await createLevel({...common,design,feedback,screeningContract:contract?.value??null});
  contract?.check(built);
  save('level.json',built);
  const ask = (operation,system,context)=>askModelJson({code,apiKey,providerId:applyRelay(relay),callModel,system,userText:JSON.stringify({operation,...context})});
  const {response:tests} = await ask('creator_verification',
    'Return JSON {successTape:[{action,args}],failureTape:[{action,args}]}. Read the supplied level source. Provide one legal action sequence reaching success and one legal sequence reaching terminal failure, both on variant 0. Do not change the code, fabricate outcomes, use nonexistent actions, or rely on hidden state access. This is host verification, not Explorer training.',
    {design,source:built.source,node:built.node});
  const checks=[];
  for(const [name,expected] of [['successTape',true],['failureTape',false]]) {
    const actions=tests[name];
    if(!Array.isArray(actions)||!actions.length||actions.length>300) throw Error('Missing bounded verification tape: '+name);
    const out=await renderLevel({source:built.source,node:built.node,variant:0,actions,vendorDir});
    const check={name,actions,ended:out.inspect.ended,success:out.inspect.success,rejected:out.receipts.filter(r=>r.accepted===false).length,
      steps:out.inspect.steps,budget:out.inspect.budget,consumed:out.receipts.length};
    checks.push(check);
    save('host-checks.json',checks);
    if(contract&&check.budget!==contract.value.actionBudget)throw Error('Screening action budget changed during host verification');
    if(!check.ended || check.success!==expected || check.rejected || check.consumed!==actions.length) throw Error('Host verification failed: '+name);
  }
  const {response:review}=await ask('judge_level',
    'Independently review the source against the full brief and design. Return JSON {accepted:boolean,reason:string}. Reject missing mechanics, invented dataset items, lost modalities, answer leaks, hard-coded success, scoring changes, or pretending a local reconstruction calls an official service. The host checks are real but do not prove semantic fidelity. Require the exact task rules and all stated constraints. For a practice environment, require the requested capability conjunction and descendant-task mechanisms.',
    {brief,design,source:built.source,hostChecks:checks,...(contract?{screeningContract:contract.value,
      constraint:'Reject any change to the frozen design, action budget, action semantics, scoring or difficulty axes/ranges. Difficulty tuning must stay within the declared ranges.'}:{})});
  save('review.json',review);
  if(review.accepted!==true || typeof review.reason!=='string' || !review.reason.trim()) throw Error('Independent level review rejected: '+String(review.reason));
  return {...built,verification:{checks,review}};
}
