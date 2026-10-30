import {clone, digest, ensure, identifier, exact} from './core.mjs';
import {assertConsistentRules, moduleSignature, mergeRuleModules, similarPair} from './creator-logic.mjs';

const operators = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte'];
export const creatorEvolutionChoices = ['create_module', 'create_skill', 'revise_module', 'revise_skill'];
export const emptyCreator = () => ({modules: [], skills: []});

export function composeCreator(base, updates) {
  const result = emptyCreator();
  for (const key of ['modules', 'skills']) {
    const map = new Map(base[key].map(value => [value.id, clone(value)]));
    for (const value of updates[key]) map.set(value.id, clone(value));
    result[key] = [...map.values()];
  }
  return result;
}
export function validateArtifact(kind, artifact) {
  const keys = kind === 'module' ? ['id', 'version', 'node', 'measurementKind', 'rules'] : ['id', 'version', 'node', 'trigger', 'procedure', 'checks'];
  exact(artifact, keys, 'Creator artifact');
  ensure(identifier(artifact.id) && identifier(artifact.node) && Number.isInteger(artifact.version) && artifact.version > 0, 'Invalid Creator identity');
  if (kind === 'module') {
    ensure(identifier(artifact.measurementKind) && Array.isArray(artifact.rules) && artifact.rules.length > 0 && artifact.rules.length <= 64, 'Invalid rule program');
    const ids = new Set();
    for (const rule of artifact.rules) {
      exact(rule, ['id', 'left', 'operator', 'right', 'message'], 'rule');
      ensure(identifier(rule.id) && !ids.has(rule.id) && identifier(rule.left) && operators.includes(rule.operator), 'Invalid predicate');
      ids.add(rule.id);
      ensure(rule.right && Object.keys(rule.right).length === 1, 'Invalid right operand');
      if (Object.hasOwn(rule.right, 'field')) ensure(identifier(rule.right.field), 'Invalid operand field');
      else ensure(Object.hasOwn(rule.right, 'value') && (rule.right.value === null || ['string', 'boolean', 'number'].includes(typeof rule.right.value)) && !(typeof rule.right.value === 'number' && !Number.isFinite(rule.right.value)), 'Invalid scalar operand');
      ensure(typeof rule.message === 'string' && rule.message.trim().length > 0 && rule.message.length <= 2000, 'Rule explanation required');
    }
  } else {
    ensure(typeof artifact.trigger === 'string' && artifact.trigger.trim().length > 0 && artifact.trigger.length <= 2000, 'Skill trigger required');
    for (const key of ['procedure', 'checks']) ensure(Array.isArray(artifact[key]) && artifact[key].length > 0 && artifact[key].length <= 32 && artifact[key].every(line => typeof line === 'string' && line.trim().length > 0 && line.length <= 2000), 'Invalid skill guidance');
  }
  return artifact;
}
export function evaluateRuleModule(module, measurement) {
  validateArtifact('module', module);
  if (!measurement || measurement.kind !== module.measurementKind || !measurement.current) return {verdict: 'unknown', findings: ['Missing current host measurement']};
  const findings = [];
  let unknown = false;
  for (const rule of module.rules) {
    const left = measurement.values[rule.left], right = Object.hasOwn(rule.right, 'field') ? measurement.values[rule.right.field] : rule.right.value;
    if (left === undefined || right === undefined || typeof left !== typeof right || (['gt', 'gte', 'lt', 'lte'].includes(rule.operator) && (typeof left !== 'number' || !Number.isFinite(left) || !Number.isFinite(right)))) {
      unknown = true;
      findings.push('Unknown: ' + rule.message);
      continue;
    }
    const pass = rule.operator === 'eq' ? left === right : rule.operator === 'ne' ? left !== right : rule.operator === 'gt' ? left > right : rule.operator === 'gte' ? left >= right : rule.operator === 'lt' ? left < right : left <= right;
    if (!pass) findings.push('Conflict: ' + rule.message);
  }
  return {verdict: findings.some(value => value.startsWith('Conflict:')) ? 'conflict' : unknown ? 'unknown' : 'pass', findings};
}
export function auditCreator(state, inspection, buildDigest) {
  ensure(inspection.buildDigest === buildDigest, 'Stale host inspection');
  return state.modules.map(module => ({id: module.id, ...evaluateRuleModule(module, {
    kind: module.measurementKind,
    current: inspection.buildDigest === buildDigest && Object.hasOwn(inspection.measurements, module.measurementKind) &&
      (module.measurementKind !== 'core' || inspection.hostEvidence?.buildDigest === buildDigest &&
        digest(inspection.hostEvidence.measurements) === digest(inspection.measurements.core)),
    values: inspection.measurements[module.measurementKind] ?? {}
  })}));
}
export function applyCreatorChoice(state, choice, node, failureIds) {
  exact(choice, ['choice', 'reason', 'evidenceRefs', 'baseVersion', 'artifact'], 'Creator choice');
  ensure(creatorEvolutionChoices.includes(choice.choice) && typeof choice.reason === 'string' && choice.reason.trim(), 'Creator must choose one of four required evolution actions');
  ensure(failureIds.length > 0 && Array.isArray(choice.evidenceRefs) && choice.evidenceRefs.length > 0 && choice.evidenceRefs.every(id => failureIds.includes(id)), 'Verified failure evidence required');
  const kind = choice.choice.endsWith('_module') ? 'module' : 'skill', revise = choice.choice.startsWith('revise_');
  const artifact = validateArtifact(kind, choice.artifact), key = kind === 'module' ? 'modules' : 'skills';
  if (kind === 'module') assertConsistentRules([
    ...state.modules.filter(m => m.id !== artifact.id && m.measurementKind === artifact.measurementKind).flatMap(m => m.rules),
    ...artifact.rules]);
  ensure(artifact.node === node, 'Wrong Creator node');
  const old = state[key].find(value => value.id === artifact.id);
  ensure(!state[key === 'modules' ? 'skills' : 'modules'].some(value => value.id === artifact.id), 'Artifact ID already has another kind');
  if (revise) {
    ensure(old, 'Creator revision requires an existing artifact of the same kind');
    ensure(choice.baseVersion === old.version && artifact.version === old.version + 1, 'Stale Creator revision');
    const omit = value => Object.fromEntries(Object.entries(value).filter(([name]) => !['version', 'node'].includes(name)));
    ensure(digest(omit(old)) !== digest(omit(artifact)), 'No-op Creator revision');
  } else ensure(!old && choice.baseVersion === null && artifact.version === 1, 'Creator creation requires a new ID and version one');
  const result = clone(state);
  result[key] = [...result[key].filter(value => value.id !== artifact.id), clone(artifact)];
  return {state: result, update: {kind, action: choice.choice, artifact: clone(artifact), predecessor: old ? digest(old) : null, evidenceRefs: clone(choice.evidenceRefs)}};
}
function identity(kind, artifact) {
  if (kind === 'skills') return digest({trigger: artifact.trigger, procedure: artifact.procedure, checks: artifact.checks});
  return moduleSignature(artifact);
}
export function consolidateCreator(base, updates, groups = [], {measurements = [], autoMerge = true} = {}) {
  const result = clone(base), provenance = [];
  for (const module of result.modules) validateArtifact('module', module);
  for (const update of updates) {
    const key = update.kind === 'module' ? 'modules' : 'skills', artifact = clone(update.artifact), old = result[key].find(value => value.id === artifact.id);
    validateArtifact(update.kind, artifact);
    if (old) {
      if (digest(old) === digest(artifact)) continue;
      if (update.predecessor !== digest(old)) {
        provenance.push({action: 'reject_stale_revision', id: artifact.id, retained: digest(old), candidate: digest(artifact), predecessor: update.predecessor});
        continue;
      }
      result[key][result[key].findIndex(value => value.id === artifact.id)] = artifact;
      provenance.push({action: 'accept', id: artifact.id, digest: digest(artifact), evidenceRefs: update.evidenceRefs});
      continue;
    }
    result[key].push(artifact);
    provenance.push({action: 'accept', id: artifact.id, digest: digest(artifact), evidenceRefs: update.evidenceRefs});
  }
  for (const key of ['modules', 'skills']) {
    const signatures = new Set();
    result[key] = result[key].filter(artifact => {
      const signature = identity(key, artifact);
      if (signatures.has(signature)) {provenance.push({action: 'drop_semantic_duplicate', id: artifact.id, signature}); return false;}
      signatures.add(signature);
      return true;
    });
  }
  for (const group of groups) {
    exact(group, ['kind', 'ids', 'newId'], 'consolidation group');
    ensure(['module', 'skill'].includes(group.kind) && identifier(group.newId) && Array.isArray(group.ids) && group.ids.length >= 2 && new Set(group.ids).size === group.ids.length, 'Invalid consolidation group');
    ensure(![...result.modules, ...result.skills].some(value => value.id === group.newId), 'Merged artifact ID collision');
    const key = group.kind === 'module' ? 'modules' : 'skills', selected = group.ids.map(id => result[key].find(value => value.id === id));
    ensure(selected.every(Boolean), 'Unknown consolidation member');
    let artifact, validation;
    if (key === 'modules') {
      ({artifact, validation} = mergeRuleModules(selected, group.newId, evaluateRuleModule, measurements));
    } else artifact = {id: group.newId, version: 1, node: 'shared', trigger: selected.map(value => value.trigger).join(' OR '), procedure: [...new Set(selected.flatMap(value => value.procedure))], checks: [...new Set(selected.flatMap(value => value.checks))]};
    validateArtifact(group.kind, artifact);
    result[key] = [...result[key].filter(value => !group.ids.includes(value.id)), artifact];
    provenance.push({action: 'merge_without_dropping_conditions', sources: selected.map(value => ({id: value.id, digest: digest(value)})), id: artifact.id, validation: validation ?? null});
  }
  if (autoMerge) {
    let ids;
    const blocked = new Set();
    while ((ids = similarPair(result.modules.filter(module => !blocked.has(module.id))))) {
      const selected = ids.map(id => result.modules.find(m => m.id === id));
      const newId = 'merged_' + digest(selected).slice(0, 24);
      try {
        const {artifact, validation} = mergeRuleModules(selected, newId, evaluateRuleModule, measurements);
        validateArtifact('module', artifact);
        const position = result.modules.findIndex(m => m.id === ids[0]);
        result.modules = result.modules.filter(m => !ids.includes(m.id));
        result.modules.splice(position, 0, artifact);
        provenance.push({action: 'auto_merge_complementary', sources: selected.map(m => ({id: m.id, digest: digest(m)})), id: newId, validation});
      } catch (error) {
        ids.forEach(id => blocked.add(id));
        provenance.push({action: 'reject_conflicting_merge', ids, message: String(error.message)});
      }
    }
  }
  return {state: result, provenance};
}

export function retainCreatorChoice(state, choice, node, failureIds) {
  ensure(creatorEvolutionChoices.includes(choice?.choice), 'Creator must choose one of four required evolution actions');
  const kind = choice.choice.endsWith('_module') ? 'module' : 'skill';
  const artifact = validateArtifact(kind, choice.artifact), key = kind === 'module' ? 'modules' : 'skills';
  ensure(artifact.node === node, 'Creator artifact must belong to the current node');
  ensure(!state[key === 'modules' ? 'skills' : 'modules'].some(value => value.id === artifact.id), 'Artifact ID already has another kind');
  try {return {...applyCreatorChoice(state, choice, node, failureIds), accepted: true, diagnostics: []};}
  catch (error) {
    return {state: clone(state), accepted: false, diagnostics: [String(error.message)], update: null};
  }
}
