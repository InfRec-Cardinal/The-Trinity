

export function outcomeMemory({current, transitions = [], memory = null, proposedAction = null}) {
  const canonical = x => {
    if (x === null || typeof x !== 'object') return JSON.stringify(x);
    if (Array.isArray(x)) return '[' + x.map(canonical).join(',') + ']';
    return '{' + Object.keys(x).sort().map(k => JSON.stringify(k) + ':' + canonical(x[k])).join(',') + '}';
  };
  const clone = x => JSON.parse(JSON.stringify(x));
  const present = x => typeof x === 'string' && x.length > 0;
  const snapshot = s => s && present(s.source) && Number.isSafeInteger(s.revision) && s.revision >= 0 &&
    present(s.stateKey) && present(s.phase) && present(s.epoch);
  if (!snapshot(current)) throw Error('Sourced current snapshot, monotonic revision, phase, epoch and stateKey required');
  if (!Array.isArray(transitions) || transitions.length > 2000 || (memory && !Array.isArray(memory.entries)))
    throw Error('Bounded transition array and memory entries required');
  const errors = [], pending = [], entries = [], ids = new Map();
  const prior = memory?.lastCurrent;
  if (prior && (!snapshot(prior) || prior.revision > current.revision ||
    (prior.revision === current.revision && canonical(prior) !== canonical(current))))
    errors.push({reason:'stale_or_conflicting_current'});
  for (const t of [...(memory?.entries ?? []), ...transitions]) {
    if (!t || !present(t.id) || !present(t.source) || !snapshot(t.before) || !snapshot(t.after) ||
      !t.action || typeof t.action !== 'object' || Array.isArray(t.action) || !Object.keys(t.action).length ||
      t.after.revision <= t.before.revision || ![true,false,null,undefined].includes(t.accepted) ||
      ![true,false,null,undefined].includes(t.changed) ||
      ![undefined,null,'failure','completion','reset'].includes(t.event) ||
      (t.event && (!present(t.eventSource) || t.accepted === false))) {
      errors.push({id:t?.id ?? null,reason:'invalid_or_unsourced_transition'}); continue;
    }
    const clean = clone(t), value = canonical(clean);
    if (ids.has(t.id)) {
      if (ids.get(t.id) !== value) errors.push({id:t.id,reason:'conflicting_receipt_id'});
      continue;
    }
    ids.set(t.id,value);
    if (t.after.revision > current.revision) {pending.push({id:t.id,reason:'future_receipt'});continue;}
    entries.push(clean);
  }
  if (entries.length > 2000) throw Error('Memory capacity reached; explicit archival required');
  entries.sort((a,b) => a.after.revision-b.after.revision);
  const byRevision = new Map();
  const snapshots = new Map([[current.revision,canonical(current)]]);
  for (const t of entries) {
    const previous=byRevision.get(t.after.revision);
    if (previous && canonical(previous)!==canonical(t)) errors.push({id:t.id,reason:'ambiguous_transition_revision'});
    byRevision.set(t.after.revision,t);
    for (const s of [t.before,t.after]) {
      if(snapshots.has(s.revision) && snapshots.get(s.revision)!==canonical(s))
        errors.push({id:t.id,reason:'conflicting_public_snapshot'});
      else snapshots.set(s.revision,canonical(s));
    }
  }
  const outcome = t => t.accepted === false ? 'rejected' : t.event === 'failure' ? 'failure' :
    t.event === 'completion' ? 'completion' : t.event === 'reset' ? 'reset' :
    t.accepted !== true ? 'unknown' : t.changed === true ? 'observed_change' :
    t.changed === false ? 'no_visible_change' : 'unknown';
  const brief = t => ({id:t.id,source:t.source,beforeSource:t.before.source,afterSource:t.after.source,
    revision:t.after.revision,phase:t.before.phase,epoch:t.before.epoch,action:t.action,outcome:outcome(t),
    eventSource:t.eventSource ?? null});
  const sameScope = t => t.before.epoch === current.epoch && t.before.phase === current.phase &&
    t.before.stateKey === current.stateKey;
  const relevant = entries.filter(sameScope);
  const proposedKey = proposedAction ? canonical(proposedAction) : null;
  const matches = proposedKey ? relevant.filter(t => canonical(t.action) === proposedKey) : relevant;
  let exactActionRun=0, inertRun=0;
  const last=entries.at(-1), lastKey=last ? canonical(last.action) : null;
  let cursor=current.revision;
  for(let i=entries.length-1;i>=0;i--){
    const t=entries[i];
    if(t.after.revision!==cursor || t.before.epoch!==current.epoch || t.after.epoch!==current.epoch ||
      t.before.phase!==current.phase || t.after.phase!==current.phase || t.event==='reset' || canonical(t.action)!==lastKey)break;
    exactActionRun++;cursor=t.before.revision;
  }
  cursor=current.revision;
  for(let i=entries.length-1;i>=0;i--){
    const t=entries[i];
    if(t.after.revision!==cursor || !sameScope(t) || t.after.stateKey!==current.stateKey ||
      t.after.epoch!==current.epoch || t.after.phase!==current.phase || canonical(t.action)!==lastKey || outcome(t)!=='no_visible_change')break;
    inertRun++;cursor=t.before.revision;
  }
  const counts={};for(const t of entries){const key=outcome(t);counts[key]=(counts[key]??0)+1;}
  const failures=entries.filter(t=>outcome(t)==='failure');
  const resetSincePrior=Boolean(prior && (prior.epoch!==current.epoch || prior.phase!==current.phase));
  const uncertain=entries.filter(t=>outcome(t)==='unknown').length;
  const ready=!errors.length&&!pending.length;
  return {
    status:ready?'memory_ready':'needs_reobservation',safeToUse:ready,errors,pending,
    memory:ready?{lastCurrent:clone(current),entries}:memory?clone(memory):{lastCurrent:clone(current),entries:[]},
    summary:{counts,lastOutcome:last?brief(last):null,recentOutcomes:entries.slice(-3).map(brief),
      failureEvidence:failures.slice(-3).map(brief),matchingPublicContext:ready?matches.slice(-4).map(brief):[],
      exactActionRun,inertRun,uncertainResults:uncertain,resetSincePrior,
      historicalFailureCount:failures.length,
      interpretation:'An observed failure stays a failure even if pixels change. Matching public context is conditional evidence, not proof of identical hidden state. No remembered action is made globally illegal. Changes alone do not prove goal progress.',
      reuse:'Retain sourced experiences; current facts require current observations. Different epochs or phases are not pooled. No cross-epoch invariant is assumed.'}
  };
}
