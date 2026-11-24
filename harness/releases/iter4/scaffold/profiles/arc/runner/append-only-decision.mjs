import assert from 'node:assert/strict';
import {prepareNativeDecision,inspectDecisionOutput} from './native-decision-protocol.mjs';
import {sanitizeToolCallHistory} from './player-protocol.mjs';
import {auditRequest} from './request-audit.mjs';

export class AppendOnlyDecision {
  #body=null;
  #pending=null;
  prepare(candidate) {
    if (!this.#body) {
      this.#body=prepareNativeDecision(candidate);
    } else {
      assert(this.#pending,'No accepted response awaiting a public result');
      assert.deepEqual(candidate.tools,this.#body.tools,'Tools changed within signed conversation');
      const expected=prepareNativeDecision(candidate);
      assert.deepEqual(expected.system,this.#body.system,'System changed within signed conversation');
      const id=this.#pending.content.find(b=>b.type==='tool_use').id;
      const index=candidate.messages.findIndex(m=>m.role==='user'&&Array.isArray(m.content)&&
        m.content.some(b=>b.type==='tool_result'&&b.tool_use_id===id));
      assert(index>=0,'Missing public result for pending action; refusing to drop signed history');
      const assistant=sanitizeToolCallHistory({messages:[{role:'assistant',content:this.#pending.content}]}).body.messages[0];
      this.#body.messages.push(structuredClone(assistant),...structuredClone(candidate.messages.slice(index)));
      this.#pending=null;
    }
    assert(auditRequest(this.#body).valid,'Unpaired tool history');
    return structuredClone(this.#body);
  }
  accept(message) {
    const inspected=inspectDecisionOutput(message,this.#body.tools);
    if (!inspected.ok) {
      if (['refusal','output_cap'].includes(inspected.outcome)) return inspected;
      const error=new Error(inspected.outcome+': '+inspected.errors.join(', '));
      error.responseUsage=inspected.selected.usage;
      error.responseStopReason=inspected.selected.stopReason;
      throw error;
    }
    assert(!this.#pending,'Response already pending');
    this.#pending=structuredClone(message);
    return inspected;
  }
}
