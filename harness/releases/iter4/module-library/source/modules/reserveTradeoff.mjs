

import {rankValue} from '../src/value-decision.mjs';
export default function reserveTradeoff(input){
  if(!input.reserveSource) return {status:'needs_public_reserve_contract',recommendation:null};
  const result=rankValue(input);
  return {...result,requiredReserves:input.resourceReserve,reserveSource:input.reserveSource,
    resourceSlack:result.ranked.map(r=>{const c=input.candidates.find(c=>c.id===r.id);return {id:r.id,
      slack:Object.fromEntries(Object.entries(input.resourceReserve).map(([k,v])=>[k,c.remainingResources[k].lower-v]))};}),
    intent:'Preserve required future resources, then compare actual scored delivery opportunities; do not maximize unused stock as a proxy goal.'};
}
