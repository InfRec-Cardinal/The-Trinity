import assert from 'node:assert/strict';
import {canonicalizeReplayRequest} from './checkpoint-transport.mjs';
import {prepareNativeDecision,inspectDecisionOutput,parseMessage} from './native-decision-protocol.mjs';
import {sanitizeToolCallHistory,selectAction} from './player-protocol.mjs';
import {auditRequest} from './request-audit.mjs';

export class NativeEpisodeTransport {
  previous = null;
  response = null;
  requests = 0;
  async call({body,post,forceEnvironment=false}) {
    let request = prepareNativeDecision(sanitizeToolCallHistory(body).body);

    request.messages=request.messages.map(m=>({...m,content:m.content.map(b=>{
      const {cache_control,...block}=b;return block;
    })}));
    if (this.previous) {
      assert.deepEqual(request.system,this.previous.system,'System changed inside native tool turn');
      assert.deepEqual(request.tools,this.previous.tools,'Tool schema changed inside native tool turn');
      const selected=selectAction(this.response,request.tools);
      assert(selected.toolId,'Previous native response has no complete tool call');
      const index=request.messages.findLastIndex(m=>m.role==='assistant' && m.content.some(b=>b.type==='tool_use'&&b.id===selected.toolId));
      assert(index>=0,'The previous response must receive its real tool result');
      const suffix=request.messages.slice(index+1);
      assert(suffix.length && suffix[0].role==='user','Missing immediate tool result');
      assert(suffix[0].content.some(b=>b.type==='tool_result'&&b.tool_use_id===selected.toolId),'Mismatched tool result');
      const assistant=sanitizeToolCallHistory({messages:[{role:'assistant',content:this.response.content}]}).body.messages[0];

      request.messages=[...structuredClone(this.previous.messages),structuredClone(assistant),...suffix];
    }
    assert(auditRequest(request).valid,'Native request has an invalid tool/result pairing');
    request=canonicalizeReplayRequest(request);
    this.requests++;
    const message=parseMessage(await post(request));
    const inspected=inspectDecisionOutput(message,request.tools);
    if (!inspected.ok && !['refusal','output_cap'].includes(inspected.outcome)) {
      const error=new Error('Native output contract violation: '+inspected.errors.join(','));
      error.responseUsage=inspected.selected.usage;error.responseStopReason=message.stop_reason;
      throw error;
    }

    if (forceEnvironment && inspected.selected.action && inspected.selected.toolName!=='submit_action') {
      const error=new Error('Auxiliary module budget exhausted; no extra helper call executed');
      error.responseUsage=inspected.selected.usage;throw error;
    }
    this.previous=structuredClone(request);this.response=structuredClone(message);
    return inspected.selected;
  }
}
