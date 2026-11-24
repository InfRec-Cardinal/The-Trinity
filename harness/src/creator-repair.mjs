import {clone, digest, ensure, exact, identifier} from './core.mjs';
import {assertConsistentRules, ruleKey} from './creator-logic.mjs';
import {consolidateCreator, evaluateRuleModule, validateArtifact} from './creator.mjs';

const fields = rule => [rule.left, ...(Object.hasOwn(rule.right, 'field') ? [rule.right.field] : [])];
const inconsistent = rules => {
  try {assertConsistentRules(rules); return null;}
  catch (error) {return error.message;}
};

export function creatorConflicts(state) {
  return [...new Set(state.modules.map(m => m.measurementKind))].flatMap(kind => {
    const modules = state.modules.filter(m => m.measurementKind === kind);
    const reason = inconsistent(modules.flatMap(m => m.rules));
    return reason ? [{measurementKind: kind, ids: modules.map(m => m.id), reason}] : [];
  });
}

function protectedRules(rules) {
  const remaining = [...rules], result = [];
  while (remaining.length) {
    const component = [remaining.shift()], names = new Set(fields(component[0]));
    let changed = true;
    while (changed) {
      changed = false;
      for (let i = remaining.length - 1; i >= 0; i--) {
        if (!fields(remaining[i]).some(name => names.has(name))) continue;
        const [rule] = remaining.splice(i, 1);
        component.push(rule); fields(rule).forEach(name => names.add(name)); changed = true;
      }
    }
    if (!inconsistent(component)) result.push(...component);
  }
  return result;
}

export function applyCreatorRepairs(registry, repairs, measurements) {
  ensure(Array.isArray(repairs) && repairs.length > 0 && repairs.length <= registry.modules.length, 'Conflict repair groups required');
  const state = clone(registry), provenance = [];
  for (const repair of repairs) {
    exact(repair, ['ids', 'newId', 'rules', 'reason', 'evidenceRefs'], 'Creator conflict repair');
    ensure(Array.isArray(repair.ids) && repair.ids.length >= 2 && new Set(repair.ids).size === repair.ids.length, 'Repair requires distinct source modules');
    ensure(identifier(repair.newId) && ![...state.modules, ...state.skills].some(m => m.id === repair.newId), 'Repair ID must be new');
    ensure(typeof repair.reason === 'string' && repair.reason.trim().length > 0 && repair.reason.length <= 12000, 'Repair rationale required');
    const selected = repair.ids.map(id => state.modules.find(m => m.id === id));
    ensure(selected.every(Boolean) && selected.every(m => m.measurementKind === selected[0].measurementKind), 'Repair requires existing modules of one measurement kind');
    const originalRules = selected.flatMap(m => m.rules);
    ensure(inconsistent(originalRules), 'Use ordinary lossless consolidation for compatible modules');
    const artifact = validateArtifact('module', {id: repair.newId, version: 1, node: 'shared', measurementKind: selected[0].measurementKind, rules: clone(repair.rules)});
    assertConsistentRules(artifact.rules);
    const originalFields = new Set(originalRules.flatMap(fields)), replacementFields = new Set(artifact.rules.flatMap(fields));
    ensure(originalFields.size === replacementFields.size && [...originalFields].every(f => replacementFields.has(f)), 'Repair cannot drop measured fields or invent new fields');
    const keys = new Set(artifact.rules.map(ruleKey));
    ensure(protectedRules(originalRules).every(rule => keys.has(ruleKey(rule))), 'Repair dropped an unrelated constraint');
    const corpus = measurements.filter(m => m.kind === artifact.measurementKind && m.current === true);
    const byDigest = new Map(corpus.map(m => [digest(m), m]));
    ensure(Array.isArray(repair.evidenceRefs) && repair.evidenceRefs.length > 0 && new Set(repair.evidenceRefs).size === repair.evidenceRefs.length && repair.evidenceRefs.every(ref => byDigest.has(ref)), 'Repair requires recorded host measurement references');
    ensure(repair.evidenceRefs.every(ref => evaluateRuleModule(artifact, byDigest.get(ref)).verdict === 'pass'), 'Repaired module must pass its cited host measurements');
    const checks = corpus.map(measurement => {
      const before = selected.map(m => evaluateRuleModule(m, measurement).verdict);
      const actual = evaluateRuleModule(artifact, measurement).verdict;
      if (before.every(v => v === 'pass') || before.every(v => v === 'conflict')) {
        ensure(actual === before[0], 'Repair changed an agreed host regression verdict');
      }
      return {measurementDigest: digest(measurement), before, actual};
    });
    const position = state.modules.findIndex(m => repair.ids.includes(m.id));
    state.modules = state.modules.filter(m => !repair.ids.includes(m.id));
    state.modules.splice(position, 0, artifact);
    provenance.push({action: 'model_reconciled_conflict', sources: selected.map(m => ({id: m.id, digest: digest(m)})),
      id: artifact.id, digest: digest(artifact), reason: repair.reason, evidenceRefs: clone(repair.evidenceRefs),
      validation: {method: 'consistent_rewrite_with_host_regression', checks}});
  }
  const final = consolidateCreator(state, [], [], {autoMerge: false, measurements});
  return {state: final.state, provenance: [...provenance, ...final.provenance]};
}

export async function consolidateCreatorWithRepair({base, updates, measurements, agent, store, iteration}) {
  const preliminary = consolidateCreator(base, updates, [], {autoMerge: false, checkConsistency: false, measurements});
  const proposal = await agent.ask('creator_consolidate', {iteration, registry: preliminary.state, provenance: preliminary.provenance},
    {groups: [{kind: 'module', ids: ['Artifact ID'], newId: 'New ID'}]});
  let failure;
  try {
    ensure(Array.isArray(proposal.groups) && proposal.groups.every(g => g.kind === 'module'), 'Shared consolidation requires module groups');
    const result = consolidateCreator(preliminary.state, [], updates.length ? proposal.groups : [], {autoMerge: Boolean(updates.length), measurements});
    return {state: result.state, provenance: [...preliminary.provenance, ...result.provenance]};
  } catch (error) {
    failure = error.message;
    store.record('creator_merge_rejected', {iteration, reason: failure});
  }
  const conflicts = creatorConflicts(preliminary.state);
  if (!conflicts.length) {
    const result = consolidateCreator(preliminary.state, [], [], {measurements});
    return {state: result.state, provenance: [...preliminary.provenance, ...result.provenance]};
  }
  let previousProposal = null;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const response = await agent.ask('creator_reconcile', {iteration, attempt, maxAttempts: 3,
        registry: preliminary.state, provenance: preliminary.provenance, conflicts,
        measurements: measurements.filter(m => m.current === true && conflicts.some(c => c.measurementKind === m.kind)).map(m => ({id: digest(m), measurement: clone(m)})),
        validationFailure: failure, previousProposal},
      {repairs: [{ids: ['Conflicting source module IDs'], newId: 'New merged module ID', rules: [{id: 'rule', left: 'Host field', operator: 'gte', right: {value: 0}, message: 'Requirement'}], reason: 'Explain evidence-backed corrections', evidenceRefs: ['Host measurement ID']}]});
      previousProposal = response;
      exact(response, ['repairs'], 'Creator reconciliation response');
      const result = applyCreatorRepairs(preliminary.state, response.repairs, measurements);
      store.record('creator_conflict_repaired', {iteration, attempt, provenance: result.provenance});
      return {state: result.state, provenance: [...preliminary.provenance, ...result.provenance]};
    } catch (error) {
      failure = error.message;
      store.record('creator_repair_rejected', {iteration, attempt, reason: failure});
    }
  }
  let state = clone(base);
  const provenance = [];
  for (const update of updates) {
    try {
      const result = consolidateCreator(state, [update], [], {measurements});
      state = result.state; provenance.push(...result.provenance);
    } catch (error) {
      const rejection = {action: 'quarantine_conflicting_update', id: update.artifact.id, digest: digest(update.artifact), reason: error.message};
      provenance.push(rejection); store.record('creator_update_quarantined', {iteration, ...rejection});
    }
  }
  store.record('creator_repair_exhausted', {iteration, attempts: 3, reason: failure});
  return {state, provenance};
}
