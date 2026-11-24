import {equal} from '../src/common.mjs';


import {auditExecution} from '../src/execution-ledger.mjs';
import solve from '../src/constraint-solver-diagnostic.mjs';
export default function executionState(input){
  const initial=auditExecution(input);
  if(!initial.safeToWrite)return initial;
  let desired=input.desired??{},diagnostic=null;
  if(input.constraintDiagnostic){
    const q=input.constraintDiagnostic;
    if(q.stage!==input.snapshot.stage||!q.source)return {...initial,status:'needs_current_stage_constraint_source',safeToWrite:false,edits:[]};
    diagnostic=solve({...q,current:input.snapshot.values,fixed:input.fixed??{}});
    if(diagnostic.status!=='unique')return {...initial,status:'no_unique_diagnostic_target',safeToWrite:false,edits:[],diagnostic};
    const conflicts=Object.keys(desired).filter(k=>Object.hasOwn(diagnostic.best.values,k)&&!equal(desired[k],diagnostic.best.values[k]));
    if(conflicts.length)return {...initial,status:'conflicting_desired_state',safeToWrite:false,edits:[],conflicts,diagnostic};
    desired={...diagnostic.best.values,...desired};
  }
  if(Object.keys(desired).length && (!input.desiredSource||input.desiredStage!==input.snapshot.stage) && !diagnostic)
    return {...initial,status:'needs_current_stage_desired_state_source',safeToWrite:false,edits:[]};
  return {...auditExecution({...input,desired}),diagnostic,
    intent:'Track observed effects, confirmed edits and failed actions. Constraint solving may propose a target, but never substitutes for execution evidence.'};
}
