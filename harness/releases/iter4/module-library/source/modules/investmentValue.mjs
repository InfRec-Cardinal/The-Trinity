

import {rankValue} from '../src/value-decision.mjs';
export default function investmentValue(input){
  const result=rankValue(input),base=result.ranked.find(r=>r.id===input.baselineId);
  return {...result,baselineId:input.baselineId??null,
    comparisons:result.ranked.map(r=>({id:r.id,conservativeValueGain:base?r.utilityLower-base.utilityUpper:null,
      costDifference:base?r.cost-base.cost:null})),
    intent:'Compare investment timing against its public scored benefit and action cost; a feasible expansion is not automatically valuable.'};
}
