import assert from 'node:assert/strict';
import {sanitizeToolCallHistory} from './player-protocol.mjs';

export const OUTPUT_CONTRACT='Application output contract: this game executor consumes tool calls. Return exactly one call to an offered tool, with only the fields in its input schema. Do not add narrative text before or after the call. Auxiliary module inputs contain public observations and task evidence only. The environment determines whether the task has finished.';
const cleanBlocks=xs=>xs.map(b=>{const {cache_control,...rest}=structuredClone(b);return rest;});
const cleanMessages=ms=>sanitizeToolCallHistory({messages:ms.map(m=>({...m,content:cleanBlocks(m.content)}))}).body.messages;

export class NativeWire {
  base=null;messages=[];pending=null;receipt=null;requests=0;
  nativeResult(toolId,result){
    assert.equal(toolId,this.pending,'Native receipt must match the pending tool call');
    this.receipt=structuredClone(result);
  }
  prepare(body,{nativeOnly=false}={}){
    assert.equal(body.model,'claude-opus-5','Native repair qualified for claude-opus-5');
    if(!this.base){
      const {messages,...base}=structuredClone(body);
      base.system=cleanBlocks(base.system);base.system.at(-1).text+='\n'+OUTPUT_CONTRACT;
      base.thinking={type:'adaptive',display:'omitted'};
      base.output_config={...base.output_config,effort:'low'};
      base.tool_choice={type:'auto',disable_parallel_tool_use:true};
      this.base=base;this.messages=cleanMessages(messages);
    }else{
      assert(this.pending,'Prior tool call needs a result before another request');
      const incoming=cleanMessages(body.messages);
      const receipt=incoming.flatMap(m=>m.content).findLast(b=>b.type==='tool_result'&&b.tool_use_id===this.pending)??this.receipt;
      assert(receipt&&receipt.type==='tool_result'&&receipt.tool_use_id===this.pending,'Missing exact native/module result');
      const lastAssistant=incoming.findLastIndex(m=>m.role==='assistant');
      const publicBlocks=incoming.slice(lastAssistant+1).filter(m=>m.role==='user').flatMap(m=>m.content).filter(b=>b.type!=='tool_result');
      this.messages.push({role:'user',content:[structuredClone(receipt),...publicBlocks]});
      this.pending=null;this.receipt=null;
    }
    if(nativeOnly)this.messages.at(-1).content.push({type:'text',text:'The auxiliary consultation budget for this environment step is exhausted. Submit one native environment action now. Further auxiliary calls will end this attempt without executing a world action.'});
    const request={...structuredClone(this.base),messages:structuredClone(this.messages)};

    const cache={type:'ephemeral',ttl:process.env.RELAY_CACHE_TTL??'5m'};
    request.system.at(-1).cache_control=cache;
    request.messages.at(-1).content.at(-1).cache_control=cache;
    this.requests++;return request;
  }
  accept(result){
    if(!result.action||['refusal','max_tokens'].includes(result.stopReason))return;
    const blocks=result.assistantContent;
    for(const b of blocks){

      if(b.type==='thinking')assert(typeof b.thinking==='string'&&typeof b.signature==='string'&&b.signature.length,'Invalid signed thinking block');
      if(b.type==='redacted_thinking')assert(typeof b.data==='string'&&b.data.length,'Invalid redacted thinking block');

    }
    const prefix=cleanMessages(result.requestMessages);
    assert.deepEqual(prefix.slice(0,this.messages.length),this.messages,'Signed wire prefix changed');
    this.messages=[...prefix,...cleanMessages([{role:'assistant',content:blocks}])];
    this.pending=result.toolId;
  }
}
