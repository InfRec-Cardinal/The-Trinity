

import {holds,initialized,enumerate} from './constraint-core.mjs';
import {equal} from './common.mjs';
export default function constraintSolve({domains,fixed={},constraints,current={},maxVisits=100000}) {
  if (!Number.isInteger(maxVisits)||maxVisits<1) throw Error('Positive search limit required');
  const d=initialized(domains,fixed);if(!d)return {status:'invalid_fixed_clue',edits:[]};
  for(const [k,vs] of Object.entries(d)) if(!Array.isArray(vs)||!vs.length) return {status:'inconsistent',cell:k,edits:[]};
  for(const c of constraints) if(c.vars.some(k=>!Object.hasOwn(d, k))) throw Error('Constraint references unknown variable');
  let visits=0,cut=false,changed=true;const removals=[];
  function supported(c,cell,value){
    const vars=[...new Set(c.vars.filter(k=>k!==cell))];
    function visit(i,a){
      if(visits>=maxVisits){cut=true;return true;}visits++;
      if(!holds(c,a))return false;
      if(c.op==='sum'){
        const lower=c.vars.reduce((s,k)=>s+(Object.hasOwn(a,k)?a[k]:Math.min(...d[k])),0);
        const upper=c.vars.reduce((s,k)=>s+(Object.hasOwn(a,k)?a[k]:Math.max(...d[k])),0);
        if(lower>c.value||upper<c.value)return false;
      }
      if(i===vars.length)return true;
      return d[vars[i]].some(v=>visit(i+1,{...a,[vars[i]]:v}));
    }
    return visit(0,{[cell]:value});
  }
  while(changed&&!cut){changed=false;
    for(const c of constraints){
      for(const cell of new Set(c.vars)){
        const before=d[cell],after=before.filter(value=>supported(c,cell,value));
        if(!after.length)return {status:'inconsistent',cell,constraint:c.id,removals,visits,edits:[]};
        if(!equal(before,after)){removals.push({constraint:c.id,cell,before,after});d[cell]=after;changed=true;}
        if(cut)break;
      }if(cut)break;
    }
  }
  if(cut||visits>=maxVisits)return {status:'search_limit',domains:d,removals,visits,complete:false,edits:[]};
  const completion=enumerate(d,constraints,current,maxVisits-visits);
  const unique=completion.complete&&completion.status==='unique';
  return {status:completion.status,domains:d,removals,changes:removals,completion,
    complete:completion.complete,visits:visits+completion.visits,solutionsFound:completion.solutionsFound,
    best:completion.best,edits:unique?completion.best.edits:[],
    note:'Arithmetic bounds and relation supports share domains and one total visit budget. Editable current values are preferences, not clues; ambiguous or cutoff results do not authorize writes.'};
}
