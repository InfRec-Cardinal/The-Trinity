import {cooperativeForecast} from '../src/cooperative-forecast.mjs';
import {semanticSignal} from '../src/semantic-signals.mjs';
import {resourceContest,consequenceMatrix} from '../src/public-decision-models.mjs';

import {infer,predict,allocations} from '../src/opponent-core.mjs';
import {partition} from '../src/common.mjs';
function nodeModelDecision({base,t,signal,archives=[],history=[],total=14,reverseOdd=false,
  availableArchives=[],budget=0,roundsRemaining=0,objective='guaranteed_win'}) {
  if (!['guaranteed_win','mean_outcome'].includes(objective)) throw Error('Unknown objective');
  const survivors=infer({base,archives,history},reverseOdd);
  if (!survivors.length) return {status:'inconsistent_evidence',survivors};
  const predictions=survivors.map(h=>predict(base,h,t,signal,reverseOdd));
  const ranking=allocations(total).map(action=>{
    const wins=predictions.map(p=>Number(action.filter((v,i)=>v>p[i]).length>=2));
    const scores=predictions.map(p=>Math.sign(action.reduce((n,v,i)=>n+Math.sign(v-p[i]),0)));
    return {action,guaranteedWin:Math.min(...wins),modelWinFraction:wins.reduce((a,b)=>a+b,0)/wins.length,
      mean:scores.reduce((a,b)=>a+b,0)/scores.length,worst:Math.min(...scores)};
  }).sort((a,b)=>objective==='guaranteed_win'?b.guaranteedWin-a.guaranteedWin||b.modelWinFraction-a.modelWinFraction:
    b.mean-a.mean||b.worst-a.worst||Math.max(...a.action)-Math.max(...b.action));
  const archiveRanking=availableArchives.map(q=>({...q,...partition(survivors,q,(h,q)=>predict(base,h,q.t,q.signal,reverseOdd))}))
    .sort((a,b)=>a.worst-b.worst||b.entropy-a.entropy);
  const next=ranking[0].guaranteedWin?null:archiveRanking.find(q=>q.worst<survivors.length && q.cost<=budget-roundsRemaining);
  return {status:next?'inspect_archive':'allocation_ready',survivors,predictions,objective,
    recommendation:ranking[0],ranking:ranking.slice(0,8),archive:next?.id??null,archiveRanking,
    reservedBattleActions:roundsRemaining,guaranteedAcrossSurvivors:Boolean(ranking[0].guaranteedWin),
    note:'Guarantees are conditional on the supplied public 24-hypothesis family. Ranking objective is explicit, not inferred from iteration.'};
}

export default function opponentDecision(input){
 if(input.mode==='cooperative_forecast')return cooperativeForecast(input);
 if(input.mode==='semantic_signal')return semanticSignal(input);
 if(input.mode==='resource_contest')return resourceContest(input);
 if(input.mode==='consequence_matrix')return consequenceMatrix(input);
 return nodeModelDecision(input);
}
