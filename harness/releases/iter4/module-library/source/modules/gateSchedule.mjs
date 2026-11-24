import constraintAudit from '../src/constraint-audit.mjs';

import {step,successors,done} from '../src/gate-core.mjs';
import {shortest} from '../src/common.mjs';
import gridPush from '../src/grid-push-plan.mjs';
import permutationPlan from '../src/permutation-plan.mjs';
export default function gateSchedule(input){if(input.mode==='constraint_audit')return constraintAudit(input);if(input.mode==='reversible_permutation')return permutationPlan(input);if(input.mode==='grid_push')return gridPush(input);return gateModel(input);}
function gateModel({config,state={a:0,b:0,pa:0,pb:0},proposed,budget,maxStates=50000}) {
  if (!Number.isInteger(budget)||budget<0) throw Error('Nonnegative integer budget required');
  const plan=shortest(state,s=>successors(config,s),s=>done(config,s),budget,maxStates);
  const validation=proposed?step(config,state,proposed):null;
  const proposedContinuation=validation?.status==='legal' && budget>0?
    shortest(validation.state,s=>successors(config,s),s=>done(config,s),budget-1,maxStates):null;
  let cursor=state;const timeline=[],milestones=[],waits={a:0,b:0};
  for (const [i,action] of (plan.path??[]).entries()) {
    const next=step(config,cursor,action).state;
    if (!action.da) waits.a++;if (!action.db) waits.b++;
    for (const robot of ['a','b']) {
      const field=robot==='a'?'pa':'pb',cargo=robot==='a'?config.aCargo:config.bCargo;
      cargo.forEach((position,bit)=>{if (!(cursor[field]&(1<<bit)) && (next[field]&(1<<bit))) milestones.push({step:i+1,robot,position,cargoIndex:bit});});
    }
    timeline.push({step:i+1,action,before:cursor,after:next});cursor=next;
  }
  const freeMotionLowerBound=Math.max(...['a','b'].map(robot=>{
    const cargo=robot==='a'?config.aCargo:config.bCargo,mask=robot==='a'?state.pa:state.pb;
    const far=Math.max(state[robot],...cargo.filter((_,i)=>!(mask&(1<<i))));return 2*far-state[robot];
  }));
  return {status:plan.status,plan,path:plan.path??null,recommendation:plan.path?.[0]??null,validation,
    proposedContinuation,proposedFitsBudget:proposedContinuation?.status==='planned',timeline,milestones,waits,
    freeMotionLowerBound,synchronizationOverhead:plan.path?plan.path.length-freeMotionLowerBound:null,
    spareActions:plan.path?budget-plan.path.length:null,
    note:'One joint search supplies both the executable route and collection schedule. The free-motion lower bound is not a gate-feasibility proof.'};
}
