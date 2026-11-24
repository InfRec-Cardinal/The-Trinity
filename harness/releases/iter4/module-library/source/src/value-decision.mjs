
const finite=x=>typeof x==='number' && Number.isFinite(x);
export function rankValue({candidates,objective,budget,terminalReserve=1,resourceReserve={}}) {
  if(!finite(budget)||budget<0||!finite(terminalReserve)||terminalReserve<0) throw Error('Nonnegative budget/reserve required');
  if(Object.values(resourceReserve).some(v=>!finite(v)||v<0)) throw Error('Invalid resource reserve');
  if(!objective?.source) return {status:'needs_public_scoring_contract',recommendation:null,ranked:[],excluded:[],
    note:'No proxy score is substituted for the environment objective.'};
  if(!['maximize','minimize'].includes(objective.direction)||!Array.isArray(objective.terms)||!objective.terms.length||
    objective.terms.some(t=>typeof t.metric!=='string'||!finite(t.weight))) throw Error('Explicit affine scoring terms and direction required');
  const ids=new Set(),ranked=[],excluded=[];
  for(const c of candidates){
    if(!c.id||ids.has(c.id))throw Error('Unique candidate IDs required');ids.add(c.id);
    const reasons=[];
    if(!c.feasibility?.source||c.feasibility.established!==true) reasons.push('no_feasibility_witness');
    if(!finite(c.cost)||c.cost<0)reasons.push('unknown_cost');
    const terminal=['commit','stop'].includes(c.kind);
    if(terminal && !(c.goalEvidence?.source && c.goalEvidence.confirmed===true))reasons.push('goal_not_observed');
    const reserve=terminal?0:terminalReserve;
    if(c.cost+reserve>budget)reasons.push('terminal_budget_shortfall');
    for(const [key,min] of Object.entries(resourceReserve)){
      const v=c.remainingResources?.[key];
      if(!v?.source||!finite(v.lower))reasons.push('unknown_resource:'+key);
      else if(v.lower<min)reasons.push('resource_reserve_shortfall:'+key);
    }
    let lower=objective.offset??0,upper=lower;
    if(!finite(lower))throw Error('Invalid score offset');
    for(const term of objective.terms){
      const m=c.metrics?.[term.metric];
      if(!m?.source || !['observed','public_model'].includes(m.basis)) {reasons.push('unsupported_metric:'+term.metric);continue;}
      const lo=m.value??m.lower,hi=m.value??m.upper;
      if(!finite(lo)||!finite(hi)||lo>hi){reasons.push('invalid_metric_bounds:'+term.metric);continue;}
      lower+=term.weight>=0?term.weight*lo:term.weight*hi;
      upper+=term.weight>=0?term.weight*hi:term.weight*lo;
    }
    if(reasons.length){excluded.push({id:c.id,reasons});continue;}
    const utilityLower=objective.direction==='maximize'?lower:-upper;
    const utilityUpper=objective.direction==='maximize'?upper:-lower;
    ranked.push({id:c.id,kind:c.kind,cost:c.cost,scoreLower:lower,scoreUpper:upper,utilityLower,utilityUpper,
      reserveAfterAction:budget-c.cost,metricBasis:Object.fromEntries(Object.entries(c.metrics).map(([k,m])=>[k,m.basis]))});
  }
  ranked.sort((a,b)=>b.utilityLower-a.utilityLower||a.cost-b.cost||String(a.id).localeCompare(String(b.id)));
  const best=ranked[0];
  return {status:best?'ranked_supplied_candidates':'no_supported_affordable_candidate',recommendation:best?.id??null,
    ranked,excluded,objectiveSource:objective.source,selectionRule:'maximize conservative score bound, then minimize action cost',
    dominanceAmongEvaluated:!!best && ranked.slice(1).every(r=>best.utilityLower>=r.utilityUpper),
    globallyOptimal:false,note:'Scores follow supplied public affine scoring rules; predictions remain model-dependent. Only supplied witnessed candidates are compared.'};
}
