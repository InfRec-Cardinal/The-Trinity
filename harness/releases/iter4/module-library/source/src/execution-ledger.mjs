import {equal} from './common.mjs';

export function auditExecution({snapshot,previousSnapshot,receipts=[],memory={entries:[]},desired={},fixed={}}){
  if(!snapshot?.source||!Number.isInteger(snapshot.revision)||!snapshot.values||snapshot.stage===undefined)
    return {status:'needs_sourced_current_snapshot',safeToWrite:false,edits:[]};
  if(previousSnapshot && (!previousSnapshot.source||snapshot.revision<previousSnapshot.revision))
    return {status:'stale_or_unsourced_snapshot',safeToWrite:false,edits:[]};
  if(previousSnapshot && snapshot.revision===previousSnapshot.revision && !equal(snapshot.values,previousSnapshot.values))
    return {status:'conflicting_snapshot_revision',safeToWrite:false,edits:[]};
  const entries=[...(memory.entries??[])],byId=new Map(entries.map(e=>[e.id,e])),issues=[];
  const observedChanges=previousSnapshot?Object.entries(snapshot.values).filter(([k,v])=>!equal(previousSnapshot.values[k],v))
    .map(([field,after])=>({field,before:previousSnapshot.values[field],after,source:snapshot.source})):[];
  const pending=[],failed=[],successful=[];
  for(const r of receipts){
    if(!r.id||!r.source||r.stage===undefined||!Number.isInteger(r.afterRevision)||
      !r.intended||typeof r.intended.field!=='string'||!r.beforeSource||!r.afterSource||
      !Object.hasOwn(r,'before')||!Object.hasOwn(r,'after')||typeof r.accepted!=='boolean'){
      issues.push({id:r.id??null,reason:'incomplete_execution_receipt'});continue;
    }
    const signature=JSON.stringify(r),old=byId.get(r.id);
    if(old){
      let duplicate=false;try{duplicate=equal(JSON.parse(old.signature),r);}catch{}
      if(!duplicate)issues.push({id:r.id,reason:'conflicting_receipt_id'});continue;
    }
    if(r.afterRevision>snapshot.revision){pending.push(r.id);continue;}
    const changed=!equal(r.before,r.after),effectMatches=equal(r.after,r.intended.value);
    const status=!r.accepted?'rejected':effectMatches?(changed?'applied':'already_satisfied'):changed?'unexpected_effect':'inert';
    const entry={id:r.id,signature,stage:r.stage,afterRevision:r.afterRevision,intended:r.intended,
      observedBefore:r.before,observedAfter:r.after,status,source:r.source,afterSource:r.afterSource};
    entries.push(entry);byId.set(r.id,entry);
  }
  for(const r of entries){
    if(r.afterRevision>snapshot.revision && !pending.includes(r.id))pending.push(r.id);
    if(r.stage===snapshot.stage && r.afterRevision===snapshot.revision &&
      (!Object.hasOwn(snapshot.values,r.intended.field)||!equal(snapshot.values[r.intended.field],r.observedAfter)))
      issues.push({id:r.id,reason:'receipt_current_snapshot_disagree'});
  }
  const lastByField=new Map();
  for(const r of entries.filter(e=>e.stage===snapshot.stage).sort((a,b)=>a.afterRevision-b.afterRevision))lastByField.set(r.intended.field,r);
  const suppressed=[],edits=[],alreadySatisfied=[];
  for(const r of entries){if(r.status==='applied')successful.push(r.id);else if(['rejected','unexpected_effect','inert'].includes(r.status))failed.push(r.id);}
  for(const [field,value] of Object.entries(desired)){
    if(!Object.hasOwn(snapshot.values,field)){issues.push({field,reason:'field_not_observed'});continue;}
    if(Object.hasOwn(fixed,field)&&!equal(fixed[field],value)){issues.push({field,reason:'immutable_value_conflict'});continue;}
    if(equal(snapshot.values[field],value)){alreadySatisfied.push(field);continue;}
    const last=lastByField.get(field);
    if(last && ['inert','rejected','unexpected_effect'].includes(last.status) && equal(last.intended.value,value) &&
      last.afterRevision===snapshot.revision){suppressed.push({field,value,receipt:last.id,reason:'same_failed_action_same_revision'});continue;}
    edits.push({field,value,observed:snapshot.values[field],basedOnRevision:snapshot.revision,stage:snapshot.stage});
  }
  const safeToWrite=!issues.length&&!pending.length;
  return {status:!safeToWrite?'reobserve_before_write':suppressed.length?'review_failed_action':edits.length?'observed_changes_pending':'state_reconciled',
    safeToWrite,edits:safeToWrite?edits:[],suppressed,alreadySatisfied,observedChanges,issues,pending,
    appliedReceiptIds:successful,failedReceiptIds:failed,memory:{entries},current:snapshot.values,
    note:'Accepted is not the same as effective. Only actual after-observations update memory; old-stage receipts never certify a new-stage write.'};
}
