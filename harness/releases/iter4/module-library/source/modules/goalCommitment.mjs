

import {rankValue} from '../src/value-decision.mjs';
export default function goalCommitment(input){
  const result=rankValue(input),best=result.ranked.find(r=>r.id===result.recommendation);
  const terminal=result.ranked.filter(r=>['stop','commit'].includes(r.kind));
  const continuing=result.ranked.filter(r=>!['stop','commit'].includes(r.kind));
  return {...result,decision:best?(terminal.includes(best)?'commit_goal':'continue_with_value'):'acquire_missing_evidence',
    canCommit:!!best&&terminal.includes(best),terminalOptions:terminal.map(r=>r.id),continuationOptions:continuing.map(r=>r.id),
    intent:'Commit only with observed goal evidence; compare stopping against continuing under the public score and remaining action budget.'};
}
