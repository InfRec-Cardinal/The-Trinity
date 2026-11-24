import {facts, cover, equal} from './common.mjs';

export function pairedDiagnosis({entities, observations, rules, epoch}) {
  const rows = entities.map(entity => {
    const f = facts(observations, entity, epoch);
    const required = [...new Set(['front', 'back', ...rules.flatMap(r => Object.keys(r.when))])];
    const missing = required.filter(k => !Object.hasOwn(f.values, k));
    const hits = rules.filter(r => Object.entries(r.when).every(([k, v]) => equal(f.values[k], v)));
    return {entity, ...f, missing, diagnosis: f.conflicts.length || missing.length ? null :
      hits.length === 0 ? 'none' : hits.length === 1 ? hits[0].label : null,
      matchedRuleCount: hits.length, ambiguousRule: hits.length > 1};
  });
  return {status: rows.every(r => r.diagnosis !== null) ? 'classified' : 'needs_evidence', rows,
    reports: rows.filter(r => r.diagnosis !== null && r.matchedRuleCount === 1).map(r => ({entity: r.entity, label: r.diagnosis}))};
}

export function inspectionTransaction(input) {
  const {entities, stations, reports = {}, budget, submitCost = 1} = input;
  const result = pairedDiagnosis(input), edits = [];
  for (const r of result.rows) if (r.diagnosis !== null) {
    const old = Object.hasOwn(reports, r.entity) ? reports[r.entity] : undefined;
    if (r.matchedRuleCount === 0 && old !== undefined) edits.push({kind: 'retract', entity: r.entity});
    if (r.matchedRuleCount === 1 && old !== r.diagnosis) edits.push({kind: 'report', entity: r.entity, label: r.diagnosis});
  }
  for (const entity of Object.keys(reports)) if (!entities.includes(entity)) edits.push({kind: 'retract', entity});
  const missingEvidence = result.rows.flatMap(r => [...new Set([...r.missing, ...r.conflicts])].map(attribute => ({entity:r.entity,attribute,key:r.entity+':'+attribute})));
  const missing = missingEvidence.map(r => r.key);
  const ambiguousCoverageKeys = [...new Set(missing.filter((key,i) => missing.indexOf(key)!==i))];
  const ambiguousEntities = result.rows.filter(r => r.ambiguousRule).map(r => r.entity);
  const classificationComplete = result.status === 'classified';
  const plan = ambiguousCoverageKeys.length ? {status:'ambiguous_coverage_keys',complete:false,keys:ambiguousCoverageKeys} : cover(missing, stations, Math.max(0, budget - edits.length - submitCost));
  return {status: missing.length ? 'acquire_then_recompute' : !classificationComplete ? 'resolve_rule_ambiguity' : budget >= edits.length + submitCost ? 'ready_to_reconcile' : 'budget_shortfall',
    edits, missingEvidence, acquisition: plan, knownMinimumCost: edits.length + submitCost + (plan.cost || 0),
    completeCoverage: !missing.length, classificationComplete, ambiguousEntities, canSubmitNow: classificationComplete && !missing.length && !edits.length && budget >= submitCost,
    caveat: 'New evidence can reveal further report edits; acquisition estimate is not a full budget guarantee.'};
}

export function crossViewBinding({entities, frames, rules, epoch}) {
  const observations = [], unresolved = [];
  for (const frame of frames) for (const row of frame.rows) {
    const mapped = frame.publicSlotToEntity && Object.hasOwn(frame.publicSlotToEntity, row.slot) ? frame.publicSlotToEntity[row.slot] : undefined;
    const entity = row.entity ?? mapped;
    if (!entities.includes(entity) || row.entity !== undefined && mapped !== undefined && mapped !== row.entity) {
      unresolved.push({source: frame.source, slot: row.slot, reason: 'missing_or_conflicting_identity'}); continue;
    }
    observations.push({entity, attribute: frame.face, value: row.value,
      visible: row.visible === true, source: frame.source, epoch: frame.epoch});
  }
  const classification = pairedDiagnosis({entities, observations, rules, epoch});
  return {status: unresolved.length ? 'identity_unresolved' : classification.status,
    unresolved, normalizedObservations: observations, classification,
    rule: 'Explicit ID or public slot mapping only; reversed visual order does not reverse identity.'};
}
