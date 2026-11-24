

export function resourceContest({total,fields,observations,priorWeight=2,symmetryWeight=0.75,maxActions=5000}){
 if(!Number.isSafeInteger(total)||total<1||total>100||!Number.isSafeInteger(fields)||fields<2||fields>5)throw Error('Unsupported public finite allocation domain');
 if(!Array.isArray(observations)||!Number.isFinite(priorWeight)||priorWeight<0)throw Error('Observed moves and nonnegative prior required');
 const actions=[];const walk=(prefix,left)=>{if(actions.length>maxActions)return;if(prefix.length===fields-1){actions.push([...prefix,left]);return;}for(let v=0;v<=left;v++)walk([...prefix,v],left-v);};walk([],total);
 if(actions.length>maxActions||actions.length**2>1000000)return {status:'domain_limit',recommendation:null};
 for(const r of observations)if(!r.source||!Array.isArray(r.allocation)||r.allocation.length!==fields||r.allocation.some(v=>!Number.isSafeInteger(v)||v<0)||r.allocation.reduce((a,b)=>a+b,0)!==total)throw Error('Invalid sourced public allocation');
 const permute=a=>a.length===1?[a]:a.flatMap((v,i)=>permute(a.filter((_,j)=>i!==j)).map(p=>[v,...p]));
 const orbits=observations.map(r=>[...new Map(permute(r.allocation).map(a=>[a.join(','),a])).values()]);
 if(!Number.isFinite(symmetryWeight)||symmetryWeight<0||symmetryWeight>1)throw Error('Invalid symmetry weight');
 const reward=(a,b)=>Math.sign(a.reduce((n,v,i)=>n+Math.sign(v-b[i]),0));
 const ranked=actions.map(action=>{
  const obs=observations.map(r=>reward(action,r.allocation));
  const prior=actions.reduce((sum,b)=>sum+reward(action,b),0)/actions.length;
  const orbitUtility=orbits.reduce((sum,orbit)=>sum+orbit.reduce((x,b)=>x+reward(action,b),0)/orbit.length,0);
  const expected=((1-symmetryWeight)*obs.reduce((a,b)=>a+b,0)+symmetryWeight*orbitUtility+priorWeight*prior)/Math.max(1,observations.length+priorWeight);
  return {action,expected,observedWins:obs.filter(v=>v>0).length,observedTies:obs.filter(v=>v===0).length,observedLosses:obs.filter(v=>v<0).length,worstObserved:obs.length?Math.min(...obs):null,uniformPriorUtility:prior};
 }).sort((a,b)=>b.expected-a.expected||(b.worstObserved??0)-(a.worstObserved??0)||b.observedWins-a.observedWins||Math.max(...a.action)-Math.max(...b.action));
 const best=ranked[0];const tied=ranked.filter(r=>Math.abs(r.expected-best.expected)<1e-10&&r.worstObserved===best.worstObserved);
 return {status:'public_empirical_ranking',recommendation:best,top:ranked.slice(0,12),equivalentBest:tied.slice(0,12),actionsEvaluated:actions.length,observations:observations.length,priorWeight,symmetryWeight,utility:'sign(number of strictly won fields minus number of strictly lost fields)',scope:'Expected utility under a mixture of observed moves, their exchangeable field permutations, and a uniform legal-allocation prior. Permutation symmetry is an uncertainty model, not an observed fact. This is not a next-move prediction or a guaranteed win. Repeat observations retain their empirical frequency.'};
}
export function consequenceMatrix({models,candidates}){
 if(!Array.isArray(models)||!models.length||!Array.isArray(candidates))throw Error('Public models and candidates required');
 const ids=new Set();for(const m of models){if(!m.id||ids.has(m.id)||!m.source||!Number.isFinite(m.weight)||m.weight<0)throw Error('Invalid sourced model');ids.add(m.id);}
 const weight=models.reduce((n,m)=>n+m.weight,0);if(!weight)throw Error('Positive total model weight required');
 const ranked=[],excluded=[];
 for(const c of candidates){
  const outcomes=c.outcomes??[];
  if(outcomes.length!==models.length||new Set(outcomes.map(r=>r.modelId)).size!==models.length||outcomes.some(r=>!ids.has(r.modelId)||!r.source||!Number.isFinite(r.utility)||typeof r.unsafe!=='boolean')){excluded.push({id:c.id,reason:'incomplete_or_unsourced_consequences'});continue;}
  if(outcomes.some(r=>r.unsafe)){excluded.push({id:c.id,reason:'known_unsafe_consequence',models:outcomes.filter(r=>r.unsafe).map(r=>r.modelId)});continue;}
  ranked.push({id:c.id,action:c.action,expected:outcomes.reduce((n,r)=>n+r.utility*models.find(m=>m.id===r.modelId).weight,0)/weight,worst:Math.min(...outcomes.map(r=>r.utility))});
 }
 ranked.sort((a,b)=>b.expected-a.expected||b.worst-a.worst);
 return {status:ranked.length?'ranked':'no_verified_safe_candidate',recommendation:ranked[0]??null,ranked,excluded,scope:'Conditional on supplied public consequences; unverified semantics and images remain unverified. This module does not act.'};
}
