import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
import {auditRequest} from './request-audit.mjs';

export function publicCheckpointRequest(original,stored,observation,preview,steps,actionLimit,interruption=null){
  assert(Number.isSafeInteger(steps)&&steps>=0);
  assert(Number.isSafeInteger(actionLimit)&&actionLimit>=steps);
  assert.equal(stored.length,steps*3);
  assert(auditRequest(original).valid);
  const parse=o=>JSON.parse(o.slice(o.indexOf('{')));
  const actions=[];
  for(let i=0;i<steps;i++){
    const [before,assistant,result]=stored.slice(i*3,i*3+3);
    const call=assistant.content.filter(b=>b.type==='tool_use');assert.equal(call.length,1);
    const results=result.content.filter(b=>b.type==='tool_result');assert.equal(results.length,1);
    assert.equal(results[0].tool_use_id,call[0].id);
    actions.push({fromObservation:`obs-${i}`,toObservation:`obs-${i+1}`,action:structuredClone(call[0].input)});
    assert(before.content.every(b=>b.type==='text'));
  }
  const recent=[];
  for(let i=Math.max(0,steps-4);i<steps;i++)recent.push({id:`obs-${i}`,observationText:stored[i*3].content[0].text});
  recent.push({id:`obs-${steps}`,observationText:observation.publicText});
  const state=parse(observation.publicText);assert(state);
  const body=structuredClone(original);
  const oldContext='The executor supplies the current observation and up to the last 12 public action/tool turns within a 180000-character context budget. Old complete exchanges are dropped together. Full trajectories are retained outside the Player context.';
  const currentContext='The executor supplies public observations and computed module feedback. After native thinking is enabled, complete tool exchanges and signatures are preserved in append-only wire history. Full trajectories remain archived.';
  const priorContext=body.system.at(-1).text.includes(oldContext)?oldContext:currentContext;
  assert(body.system.at(-1).text.includes(priorContext),'Unrecognized context contract; do not silently rewrite system');
  body.system.at(-1).text=body.system.at(-1).text.replace(priorContext,
    'The executor supplies an environment checkpoint with executed action receipts, recent public observations and locally computed module memory. This starts a new API turn at the saved game state. Subsequent assistant content and tool results are preserved unchanged in append-only history. Full original trajectories remain archived.');
  const summary={kind:'public_environment_checkpoint',nativeActions:steps,remainingNativeActions:actionLimit-steps,
    previousInterruption:interruption,
    continuation:'Same environment episode and cumulative action budget; fresh model context from recorded public facts. No prior assistant prose or private reasoning is reproduced.',
    actionReceipts:actions,recentPublicObservations:recent,
    currentObservationId:`obs-${steps}`,
    moduleMemory:{...preview.output,moduleAdvice:true,noWorldActionExecuted:true,
      hostPolicyContract:'Computed from public observations and executed actions. Advice is optional. No known solution is supplied. Select one legal game action.'}};
  body.messages=[{role:'user',content:[{type:'text',text:JSON.stringify(summary)},
    {type:'text',text:'Continue this public interactive puzzle from the current observation using an offered tool. All earlier action costs remain counted; the game has not restarted.'}]}];
  assert.deepEqual(body.tools,original.tools);
  assert(auditRequest(body).valid);
  return {body,manifest:{scheme:'public-environment-checkpoint-v1',sourceRequestHash:hash(original),
    actionReceipts:actions.length,recentObservations:recent.length,originalSkillsAndModulesUnchanged:true,
    originalAssistantMessagesArchived:true,newContextContainsOldAssistantContent:false,
    priorInterruptionDisclosed:Boolean(interruption),source:'https://platform.claude.com/docs/en/build-with-claude/preserved-thinking#simple-compaction-recommended'}};
}
