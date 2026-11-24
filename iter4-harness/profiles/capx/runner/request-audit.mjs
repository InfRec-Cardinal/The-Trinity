import {createHash} from 'node:crypto';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
export function auditRequest(body){
 const errors=[];const ids=new Set();let pending=new Set();
 for(const [i,m] of body.messages.entries()){
  const content=m.content;
  if(!Array.isArray(content)){errors.push({message:i,reason:'content_not_array'});continue;}
  const calls=content.filter(b=>b.type==='tool_use'),results=content.filter(b=>b.type==='tool_result');
  if(results.length&&m.role!=='user')errors.push({message:i,reason:'result_wrong_role'});
  const returned=new Set(results.map(b=>b.tool_use_id));
  if(returned.size!==results.length)errors.push({message:i,reason:'duplicate_result'});
  if(pending.size){
   if(returned.size!==pending.size||[...returned].some(id=>!pending.has(id)))errors.push({message:i,reason:'missing_or_mismatched_result'});
   pending=new Set();
  }else if(returned.size)errors.push({message:i,reason:'orphan_result'});
  if(calls.length&&m.role!=='assistant')errors.push({message:i,reason:'call_wrong_role'});
  for(const c of calls){
   if(!c.id||ids.has(c.id))errors.push({message:i,reason:'invalid_or_duplicate_call_id'});
   ids.add(c.id);pending.add(c.id);
  }
 }
 if(pending.size)errors.push({reason:'unanswered_tool_call'});
 return {valid:errors.length===0,errors,systemSha256:hash(body.system),toolsSha256:hash(body.tools),
  messagesSha256:hash(body.messages),requestSha256:hash(body),offeredTools:body.tools.map(t=>t.name),
  messageCount:body.messages.length,thinking:body.thinking??null};
}
