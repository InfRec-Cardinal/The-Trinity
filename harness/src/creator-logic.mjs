import {clone, digest, ensure, stable} from './core.mjs';

const reverse = {gt: 'lt', gte: 'lte', lt: 'gt', lte: 'gte', eq: 'eq', ne: 'ne'};
const relation = {lt: [-1], lte: [-1, 0], gt: [1], gte: [0, 1], eq: [0], ne: [-1, 1]};
export function canonicalRule(rule) {
  const result = clone(rule);
  if (Object.hasOwn(rule.right, 'field') && rule.right.field < rule.left) {
    result.left = rule.right.field;
    result.right = {field: rule.left};
    result.operator = reverse[rule.operator];
  }
  return result;
}
export const ruleKey = rule => {
  const {left, operator, right} = canonicalRule(rule);
  return stable({left, operator, right});
};

export function assertConsistentRules(rules) {
  const fields = new Map(), pairs = new Map();
  for (const original of rules) {
    const r = canonicalRule(original);
    if (Object.hasOwn(r.right, 'field')) {
      const key = stable([r.left, r.right.field]);
      const allowed = (pairs.get(key) ?? (r.left === r.right.field ? [0] : [-1, 0, 1])).filter(x => relation[r.operator].includes(x));
      ensure(allowed.length, 'Contradictory field comparisons: ' + key);
      pairs.set(key, allowed);
    } else {
      const list = fields.get(r.left) ?? [];
      list.push(r); fields.set(r.left, list);
    }
  }
  for (const [field, rs] of fields) {
    const equals = rs.filter(r => r.operator === 'eq').map(r => r.right.value);
    ensure(!equals.length || equals.every(x => x === equals[0]), 'Conflicting equalities: ' + field);
    const matches = (x, r) => {
      const y = r.right.value;
      if (typeof x !== typeof y) return false;
      return r.operator === 'eq' ? x === y : r.operator === 'ne' ? x !== y :
        r.operator === 'gt' ? x > y : r.operator === 'gte' ? x >= y : r.operator === 'lt' ? x < y : x <= y;
    };
    if (equals.length) ensure(rs.every(r => matches(equals[0], r)), 'Unsatisfiable equality constraints: ' + field);
    const numeric = rs.filter(r => typeof r.right.value === 'number');
    if (numeric.length) {
      ensure(numeric.length === rs.length && numeric.every(r => Number.isFinite(r.right.value)), 'Incompatible scalar types: ' + field);
      let low = -Infinity, high = Infinity, lowOpen = false, highOpen = false;
      for (const r of numeric) {
        const v = r.right.value;
        if (['gt', 'gte', 'eq'].includes(r.operator) && v >= low) {
          lowOpen = v === low ? lowOpen || r.operator === 'gt' : r.operator === 'gt'; low = v;
        }
        if (['lt', 'lte', 'eq'].includes(r.operator) && v <= high) {
          highOpen = v === high ? highOpen || r.operator === 'lt' : r.operator === 'lt'; high = v;
        }
      }
      ensure(low < high || low === high && !lowOpen && !highOpen && numeric.every(r => matches(low, r)), 'Empty numeric interval: ' + field);
    }
    if (rs.every(r => typeof r.right.value === 'boolean')) ensure([true, false].some(x => rs.every(r => matches(x, r))), 'Empty boolean domain: ' + field);
  }
}


export function canonicalRules(rules) {
  assertConsistentRules(rules);
  const unique = [...new Map(rules.map(r => [ruleKey(r), canonicalRule(r)])).values()];
  return unique.filter((r, index) => {
    if (!['gt', 'gte', 'lt', 'lte'].includes(r.operator) || typeof r.right.value !== 'number') return true;
    return !unique.some((s, other) => {
      if (other === index || s.left !== r.left || typeof s.right.value !== 'number') return false;
      if (s.operator === 'eq') return r.operator === 'gt' ? s.right.value > r.right.value : r.operator === 'gte' ? s.right.value >= r.right.value : r.operator === 'lt' ? s.right.value < r.right.value : s.right.value <= r.right.value;
      if (['gt', 'gte'].includes(r.operator) && ['gt', 'gte'].includes(s.operator)) return s.right.value > r.right.value || s.right.value === r.right.value && s.operator === 'gt' && r.operator === 'gte';
      if (['lt', 'lte'].includes(r.operator) && ['lt', 'lte'].includes(s.operator)) return s.right.value < r.right.value || s.right.value === r.right.value && s.operator === 'lt' && r.operator === 'lte';
      return false;
    });
  }).sort((a, b) => ruleKey(a).localeCompare(ruleKey(b)));
}

export function moduleSignature(module) {
  return digest({kind: module.measurementKind, rules: canonicalRules(module.rules).map(ruleKey)});
}

export function similarPair(modules) {
  for (let a = 0; a < modules.length; a++) for (let b = a + 1; b < modules.length; b++) {
    if (modules[a].measurementKind !== modules[b].measurementKind) continue;
    const left = new Set(canonicalRules(modules[a].rules).map(ruleKey));
    const right = new Set(canonicalRules(modules[b].rules).map(ruleKey));
    const shared = [...left].filter(key => right.has(key)).length;
    if (shared > 0 && shared / Math.min(left.size, right.size) >= 0.5) return [modules[a].id, modules[b].id];
  }
  return null;
}

export function mergeRuleModules(selected, newId, evaluate, measurements = []) {
  ensure(selected.length >= 2 && selected.every(m => m.measurementKind === selected[0].measurementKind), 'Merge requires matching measurement kinds');
  const rules = canonicalRules(selected.flatMap(m => m.rules)).map(r => ({...r, id: 'rule_' + digest(ruleKey(r)).slice(0, 16)}));
  const artifact = {id: newId, version: 1, node: 'shared', measurementKind: selected[0].measurementKind, rules};
  const corpus = measurements.filter(m => m.kind === artifact.measurementKind).map(clone);

  corpus.push({kind: artifact.measurementKind, current: true, values: {}});
  for (const r of selected.flatMap(m => m.rules)) {
    const v = r.right.value;
    if (Number.isFinite(v)) for (const x of [v - 1, v, v + 1]) corpus.push({kind: artifact.measurementKind, current: true, values: {[r.left]: x}});
  }
  const checks = corpus.map(measurement => {
    const before = selected.map(m => evaluate(m, measurement).verdict);
    const expected = before.includes('conflict') ? 'conflict' : before.includes('unknown') ? 'unknown' : 'pass';
    const actual = evaluate(artifact, measurement).verdict;
    ensure(actual === expected, 'Merged audit changed behavior on an executable regression case');
    return {measurementDigest: digest(measurement), before, expected, actual};
  });
  return {artifact, validation: {method: 'canonical_predicate_union_and_execution', inputRules: selected.reduce((n, m) => n + m.rules.length, 0),
    outputRules: rules.length, cases: checks.length, checks}};
}
