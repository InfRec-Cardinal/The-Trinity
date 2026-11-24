
export const key = x => JSON.stringify(x);
export function equal(a, b) {
  if (a === b) return true;
  if (a === null || b === null || typeof a !== 'object' || typeof b !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a)) return a.length === b.length && a.every((value, i) => equal(value, b[i]));
  const keys = Object.keys(a);
  return keys.length === Object.keys(b).length && keys.every(k => Object.hasOwn(b, k) && equal(a[k], b[k]));
}
export const sum = xs => xs.reduce((a, b) => a + b, 0);
export const unique = xs => [...new Set(xs)];
export const unknown = reason => ({status: 'unknown', reason});
export function requireFields(input, names) {
  for (const name of names) if (!Object.hasOwn(input, name)) throw Error('Missing public input: ' + name);
}

export function facts(observations, entity, epoch) {
  const groups = new Map();
  for (const o of observations) {
    if (o.entity !== entity || o.visible !== true || !o.source || o.value == null ||
        (epoch !== undefined && o.epoch !== epoch)) continue;
    const rows = groups.get(o.attribute) || [];
    rows.push(o); groups.set(o.attribute, rows);
  }
  const values = Object.create(null), conflicts = [], sources = Object.create(null);
  for (const [attribute, rows] of groups) {
    sources[attribute] = rows.map(o => o.source);
    if (rows.some(o => !equal(o.value, rows[0].value))) conflicts.push(attribute);
    else values[attribute] = rows[0].value;
  }
  return {values, conflicts, sources};
}

export function cover(required, options, budget, limit = 100000) {
  const targets = new Set(required); let visits = 0, cut = false, best = null;
  function visit(i, found, chosen, cost) {
    if (++visits > limit) { cut = true; return; }
    if (cost > budget || best && cost >= best.cost) return;
    if ([...targets].every(x => found.has(x))) { best = {chosen, cost}; return; }
    if (i === options.length) return;
    const o = options[i];
    visit(i + 1, new Set([...found, ...o.covers]), [...chosen, o.id], cost + o.cost);
    visit(i + 1, found, chosen, cost);
  }
  visit(0, new Set(), [], 0);
  return {status: cut ? 'search_limit' : best ? 'covered' : 'not_coverable',
    ...best, complete: !cut, visits};
}

export function shortest(start, successors, goal, maxDepth = 100, maxStates = 50000) {
  const q = [{state: start, path: []}], seen = new Set([key(start)]);
  let depthCut = false;
  for (let i = 0; i < q.length; i++) {
    if (i >= maxStates) return {status: 'search_limit', expanded: i};
    const r = q[i];
    if (goal(r.state)) return {status: 'planned', ...r, expanded: i + 1};
    if (r.path.length >= maxDepth) { depthCut = true; continue; }
    for (const {state, action} of successors(r.state)) {
      const k = key(state); if (seen.has(k)) continue;
      seen.add(k); q.push({state, path: [...r.path, action]});
    }
  }
  return {status: depthCut ? 'no_plan_within_depth' : 'unreachable_in_model', expanded: q.length};
}

export function observedGraph(observations, phase) {
  const latest = new Map();
  for (const o of observations) if (o.phase === phase && o.source && o.complete === true)
    latest.set(o.room, o.exits.slice());
  return latest;
}
export const graphRoute = (graph, start, goal, maxDepth = 100) => shortest(start,
  u => (graph.get(u) || []).map(v => ({state: v, action: {from: u, to: v}})),
  u => u === goal, maxDepth);

export function feedback(secret, guess) {
  let exact = 0; const left = new Map(), right = new Map();
  secret.forEach((v, i) => {
    if (v === guess[i]) exact++;
    else { left.set(v, (left.get(v) || 0) + 1); right.set(guess[i], (right.get(guess[i]) || 0) + 1); }
  });
  return [exact, sum([...left].map(([v, n]) => Math.min(n, right.get(v) || 0)))];
}
export function codes(alphabet, length, maxCandidates = 20000) {
  if (!Number.isInteger(length) || length < 1 || !alphabet.length ||
      new Set(alphabet).size !== alphabet.length) throw Error('Invalid public domain');
  if (alphabet.length ** length > maxCandidates) return null;
  let rows = [[]];
  for (let i = 0; i < length; i++) rows = rows.flatMap(r => alphabet.map(x => [...r, x]));
  return rows;
}
export function partition(candidates, probe, predict = feedback) {
  const counts = new Map();
  for (const c of candidates) { const k = key(predict(c, probe)); counts.set(k, (counts.get(k) || 0) + 1); }
  const n = candidates.length;
  return {worst: n ? Math.max(...counts.values()) : 0,
    expected: n ? sum([...counts.values()].map(v => v * v)) / n : 0,
    entropy: n ? -sum([...counts.values()].map(v => v / n * Math.log2(v / n))) : 0};
}
