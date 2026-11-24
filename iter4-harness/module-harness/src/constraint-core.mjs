import {equal} from './common.mjs';

export function holds(c, a) {
  const vs = c.vars.map(k => Object.hasOwn(a, k) ? a[k] : undefined);
  if (['sameParity', 'oddCount'].includes(c.op) && vs.some(v => v !== undefined && !Number.isSafeInteger(v))) throw Error('Parity constraints require safe integer values');
  if (c.op === 'allDifferent') { const known = vs.filter(x => x !== undefined); return new Set(known).size === known.length; }
  if (vs.some(x => x === undefined)) return true;
  if (c.op === 'sum') return vs.reduce((n, x) => n + x, 0) === c.value;
  if (c.op === 'less') return vs[0] < vs[1];
  if (c.op === 'absDiff') return Math.abs(vs[0] - vs[1]) === c.value;
  if (c.op === 'sameParity') return Math.abs(vs[0] % 2) === Math.abs(vs[1] % 2);
  if (c.op === 'oddCount') return vs.filter(x => x % 2 !== 0).length === c.value;
  throw Error('Unsupported public constraint: ' + c.op);
}
export function initialized(domains, fixed) {
  const d = structuredClone(domains);
  for (const [k, value] of Object.entries(fixed)) {
    if (!Object.hasOwn(d, k) || !d[k]?.includes(value)) return null; d[k] = [value];
  }
  return d;
}
export function enumerate(domains, constraints, current, maxVisits) {
  const solutions = []; let visits = 0, cut = false;
  const vars = Object.keys(domains).sort((a, b) => domains[a].length - domains[b].length);
  function dfs(i, a) {
    if (++visits > maxVisits) { cut = true; return; }
    if (!constraints.every(c => holds(c, a))) return;
    if (i === vars.length) { solutions.push({...a}); return; }
    const k = vars[i]; for (const v of domains[k]) { dfs(i + 1, {...a, [k]: v}); if (cut) return; }
  }
  dfs(0, {});
  const ranked = solutions.map(values => ({values, edits: Object.entries(values).filter(([k, v]) => current[k] !== v)
    .map(([cell, value]) => ({cell, value}))})).sort((a, b) => a.edits.length - b.edits.length);
  return {status: cut ? 'search_limit' : !solutions.length ? 'inconsistent' : solutions.length === 1 ? 'unique' : 'multiple_solutions',
    visits, complete: !cut, solutionsFound: solutions.length, best: ranked[0] ?? null};
}

