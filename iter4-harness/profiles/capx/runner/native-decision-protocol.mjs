import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {auditRequest} from './request-audit.mjs';
import {parseMessage,selectAction,sanitizeToolCallHistory} from './player-protocol.mjs';

export const OUTPUT_CONTRACT='Application output contract: this game executor consumes tool calls. Return exactly one call to an offered tool, with only the fields in its input schema. Do not add narrative text before or after the call. Auxiliary module inputs contain public observations and task evidence only. The environment determines whether the task has finished.';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');

export function prepareNativeDecision(body){
  assert.equal(body.model,'claude-opus-5','This adapter is qualified only for the selected model');
  assert(Array.isArray(body.system));
  assert.deepEqual(body.tool_choice,{type:'auto',disable_parallel_tool_use:true});
  const request=structuredClone(body);
  const last=request.system.findLast(b=>b.type==='text');assert(last);
  if(!last.text.endsWith(OUTPUT_CONTRACT))last.text+='\n'+OUTPUT_CONTRACT;
  request.thinking={type:'adaptive',display:'omitted'};
  request.output_config={...request.output_config,effort:'low'};
  assert.equal(hash(request.messages),hash(body.messages));
  assert.deepEqual(request.tools,body.tools);
  assert(auditRequest(request).valid);
  return request;
}

export function inspectDecisionOutput(message,tools){
  const selected=selectAction(message,tools);
  const stats={textCharacters:message.content.filter(b=>b.type==='text').reduce((n,b)=>n+(b.text??'').length,0),
    thinkingBlocks:message.content.filter(b=>b.type==='thinking').length,
    redactedThinkingBlocks:message.content.filter(b=>b.type==='redacted_thinking').length,
    nonemptyThinkingBlocks:message.content.filter(b=>b.type==='thinking'&&(b.thinking??'').trim()).length,
    toolCalls:message.content.filter(b=>b.type==='tool_use').length};

  if(selected.stopReason==='refusal')return {ok:false,outcome:'refusal',selected,stats};
  if(selected.stopReason==='max_tokens')return {ok:false,outcome:'output_cap',selected,stats};
  const errors=[];
  if(selected.stopReason!=='tool_use'||!selected.action)errors.push('one_complete_tool_call_required');

  if(message.content.some(b=>!['text','tool_use','thinking','redacted_thinking'].includes(b.type)))errors.push('unexpected_content_block');
  if(message.content.some(b=>b.type==='thinking'&&(!(typeof b.signature==='string'&&b.signature.length)||typeof b.thinking!=='string')))errors.push('invalid_signed_thinking_block');
  if(message.content.some(b=>b.type==='redacted_thinking'&&!(typeof b.data==='string'&&b.data.length)))errors.push('invalid_redacted_thinking_block');
  return {ok:errors.length===0,outcome:errors.length?'output_contract_violation':'valid_tool_call',errors,selected,stats};
}

export class NativeDecisionConversation{
  #body;
  #sealedPrefix;
  constructor(source){this.#body=prepareNativeDecision(source);this.#sealedPrefix=hash(this.#body);}
  request(){assert.equal(hash(this.#body),this.#sealedPrefix);return structuredClone(this.#body);}
  appendToolResult(message,toolId,result,publicBlocks=[]){
    const inspected=inspectDecisionOutput(message,this.#body.tools);
    assert(inspected.ok,'Only a complete, contract-valid response can be continued');
    assert.equal(inspected.selected.toolId,toolId);
    assert(publicBlocks.every(b=>b.type==='text'),'Only authored public observation text is accepted here');
    const previous=this.request();
    const assistant={role:'assistant',content:structuredClone(message.content)};

    const clean=sanitizeToolCallHistory({messages:[assistant]}).body.messages[0];
    this.#body.messages.push(clean,{role:'user',content:[
      {type:'tool_result',tool_use_id:toolId,content:JSON.stringify(result)},...structuredClone(publicBlocks)]});
    assert.deepEqual(this.#body.messages.slice(0,previous.messages.length),previous.messages);
    assert(auditRequest(this.#body).valid);
    this.#sealedPrefix=hash(this.#body);
  }
  appendHostReset(toolId,result,publicBlocks=[]){
    assert(toolId.startsWith('host_reset_'));assert(publicBlocks.every(b=>b.type==='text'));
    const previous=this.request();
    this.#body.messages.push({role:'assistant',content:[
      {type:'text',text:'[Harness automatic action: GAME_OVER/NOT_PLAYED recovery; no model call.]'},
      {type:'tool_use',id:toolId,name:'submit_action',input:{action:'RESET'}}]},
      {role:'user',content:[{type:'tool_result',tool_use_id:toolId,content:JSON.stringify(result)},...structuredClone(publicBlocks)]});
    assert.deepEqual(this.#body.messages.slice(0,previous.messages.length),previous.messages);
    assert(auditRequest(this.#body).valid);this.#sealedPrefix=hash(this.#body);
  }
}

export function responseTransportMetadata(response,message=null){
  const headers={};
  for(const name of ['request-id','x-request-id','anthropic-request-id','content-type']){
    const value=response.headers.get(name);if(value)headers[name]=value;
  }
  return {httpStatus:response.status,headers,messageId:message?.id??null,model:message?.model??null,
    stopReason:message?.stop_reason??null,category:message?.stop_details?.category??null,
    usage:message?.usage??null};
}

export {parseMessage};
