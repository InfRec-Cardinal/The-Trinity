

import executionState from './executionState.mjs';
import {equal} from '../src/common.mjs';
export default function revisionMemory(input){
  const {activeConstraints,previousConstraints,previousDeductions=[],snapshot}=input;
  const byId=new Map(activeConstraints.map(c=>[c.id,c]));
  if(byId.size!==activeConstraints.length||activeConstraints.some(c=>!c.id||!c.source))
    return {status:'needs_identified_sourced_constraints',safeToWrite:false,edits:[]};
  const changed=previousConstraints.filter(c=>!equal(c,byId.get(c.id))).map(c=>c.id);
  const stageChanged=input.previousSnapshot?.stage!==undefined && input.previousSnapshot.stage!==snapshot?.stage;
  const invalidated=previousDeductions.filter(d=>!d.source||!Array.isArray(d.dependencies)||
    d.dependencies.some(id=>!byId.has(id)||changed.includes(id))||d.stageScoped===true&&d.stage!==snapshot?.stage);

  const invalidIds=new Set(invalidated.map(d=>d.id));
  let changedClosure=true;
  while(changedClosure){changedClosure=false;for(const d of previousDeductions){
    if(!invalidIds.has(d.id)&&(d.deductionDependencies??[]).some(id=>invalidIds.has(id))){invalidIds.add(d.id);invalidated.push(d);changedClosure=true;}
  }}
  const retained=previousDeductions.filter(d=>!invalidIds.has(d.id));
  const result=executionState(input);
  const staleTarget=Object.keys(input.desired??{}).length &&
    (!Array.isArray(input.desiredConstraintSnapshot)||!input.desiredConstraintSnapshot.length||
      input.desiredConstraintSnapshot.some(c=>!equal(c,byId.get(c.id))));
  return {...result,...(staleTarget?{status:'rederive_target_after_revision',safeToWrite:false,edits:[]}:{}),changedConstraintIds:changed,invalidated,retainedDeductions:retained,stageChanged,
    invalidatedValueFields:[...new Set(invalidated.flatMap(d=>d.fields??[]))],
    note:'Stage changes retract unsupported beliefs, not physical cell values. Re-read current state; old derived values never become immutable clues.'};
}
