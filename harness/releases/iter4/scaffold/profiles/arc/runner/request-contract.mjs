import {createHash} from 'node:crypto';
import {moduleAwareSystem,validToolName,toolInstructionCandidates} from '../../../shared/module-tool-instruction.mjs';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const legacy='Call submit_action exactly once per response.';
const expected=names=>moduleAwareSystem(legacy,names);

export function repairRequestContract(body){
 if(!Array.isArray(body.tools)||!Array.isArray(body.system))throw Error('Tool and system arrays required');
 const offered=body.tools.map(t=>t.name);
 if(new Set(offered).size!==offered.length)throw Error('Duplicate offered tools');
 if(!offered.includes('submit_action'))throw Error('Native submit_action tool required');
 const names=offered.filter(n=>n!=='submit_action');
 if(names.some(n=>!validToolName(n)))throw Error('Unsupported auxiliary tool contract');
 const replacement=names.length?expected(names):legacy;
 let changed=0,matched=0;
 const system=body.system.map(block=>{
  if(block.type!=='text')return block;
  let text=block.text;
  const candidates=toolInstructionCandidates(text);
  const matches=[];
  for(const candidate of candidates){
   let start=0;
   while((start=text.indexOf(candidate,start))!==-1){
    const end=start+candidate.length;
    if(!matches.some(m=>start<m.end&&end>m.start))matches.push({start,end,candidate});
    start=end;
   }
  }
  matched+=matches.length;
  if(matches.length===1&&matches[0].candidate!==replacement){
   const match=matches[0];text=text.slice(0,match.start)+replacement+text.slice(match.end);changed++;
  }
  return text===block.text?block:{...block,text};
 });
 if(matched!==1)throw Error('Expected exactly one recognized tool-selection instruction');
 const request=changed?{...body,system}:body;
 return {request,audit:{repair:'offered_tool_instruction_consistency_v2',changedSystemBlocks:changed,
  offeredTools:offered,beforeSystemSha256:hash(body.system),afterSystemSha256:hash(request.system),
  messagesUnchanged:request.messages===body.messages,toolsUnchanged:request.tools===body.tools,
  scope:'Tool contract only; preserves observations, prior assistant messages, modules, skills, and refusal policy.'}};
}
