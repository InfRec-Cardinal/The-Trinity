import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {arcPublicMeta} from './arc-auto-reset.mjs';

const hash=text=>createHash('sha256').update(text).digest('hex');
function publicState(observation) {
  const data=arcPublicMeta(observation);
  return {state:data.state??null,levelsCompleted:data.levels_completed??null,
    fullReset:data.full_reset??null,publicTextSha256:hash(observation.publicText)};
}

export class PublicExecutionReceipts {
  #rows=[];
  #last;
  constructor(initial) { this.#last=publicState(initial); }
  record(action,observation) {
    assert(action&&typeof action.action==='string');
    assert(Object.keys(action).every(k=>['action','x','y'].includes(k)));
    const after=publicState(observation),index=this.#rows.length;
    this.#rows.push({from:`obs-${index}`,to:`obs-${index+1}`,
      action:structuredClone(action),before:this.#last,after});
    this.#last=after;
  }
  snapshot(limit=Number(process.env.ARC_NATIVE_ACTION_LIMIT??240)) {
    const counts={};
    for(const row of this.#rows)counts[row.action.action]=(counts[row.action.action]??0)+1;
    return {nativeActions:this.#rows.length,remainingNativeActions:Math.max(0,limit-this.#rows.length),
      actionCounts:counts,resetCommands:counts.RESET??0,
      gameOverResponses:this.#rows.filter(r=>r.after.state==='GAME_OVER').length,
      current:structuredClone(this.#last),recent:structuredClone(this.#rows.slice(-3)),
      semantics:'Actual executed commands and public environment metadata only. Counts do not prove displacement, object identity, causal effect, a safe route or success. Native terminal status determines completion.'};
  }
  all() { return structuredClone(this.#rows); }
}
