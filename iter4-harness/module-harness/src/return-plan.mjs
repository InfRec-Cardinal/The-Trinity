import {key, shortest} from './common.mjs';

function step(config, state, action) {
  const {da, db} = action, a = state.a + da, b = state.b + db;
  if (![da, db].every(x => [-1, 0, 1].includes(x))) return {status: 'invalid_delta'};
  if (a < 0 || b < 0 || a >= config.length || b >= config.length) return {status: 'out_of_bounds'};
  const cross = (x, y, edge) => x !== y && Math.min(x, y) === edge;
  const unsatisfied = [
    ...config.aGates.filter(g => cross(state.a, a, g.edge) && b !== (da > 0 ? g.out : g.back))
      .map(g => ({robot: 'A', edge: g.edge, requiredPartnerPosition: da > 0 ? g.out : g.back, proposedPartnerPosition: b})),
    ...config.bGates.filter(g => cross(state.b, b, g.edge) && a !== g.plate)
      .map(g => ({robot: 'B', edge: g.edge, requiredPartnerPosition: g.plate, proposedPartnerPosition: a}))
  ];
  if (unsatisfied.length) return {status: 'blocked_both', unsatisfied};
  let pa = state.pa, pb = state.pb;
  config.aCargo.forEach((p, i) => { if (a === p) pa |= 1 << i; });
  config.bCargo.forEach((p, i) => { if (b === p) pb |= 1 << i; });
  return {status: 'legal', state: {a, b, pa, pb}};
}
function successors(config, state) {
  const result = [];
  for (let da = -1; da <= 1; da++) for (let db = -1; db <= 1; db++) {
    if (!da && !db) continue;
    const action = {da, db}, r = step(config, state, action);
    if (r.status === 'legal') result.push({state: r.state, action});
  }
  return result;
}
const done = (c, s) => s.a === 0 && s.b === 0 && s.pa === (1 << c.aCargo.length) - 1 && s.pb === (1 << c.bCargo.length) - 1;

export function returnViability({config, state, proposed, budget, maxStates = 50000}) {
  const masksA = 1 << config.aCargo.length, masksB = 1 << config.bCargo.length;
  const count = config.length ** 2 * masksA * masksB;
  if (count > maxStates) return {status: 'search_limit', stateCount: count};
  const reverse = new Map();
  for (let a = 0; a < config.length; a++) for (let b = 0; b < config.length; b++)
    for (let pa = 0; pa < masksA; pa++) for (let pb = 0; pb < masksB; pb++) {
      const from = {a, b, pa, pb};
      for (const edge of successors(config, from)) {
        const k = key(edge.state), xs = reverse.get(k) || []; xs.push(from); reverse.set(k, xs);
      }
    }
  const goal = {a: 0, b: 0, pa: masksA - 1, pb: masksB - 1}, queue = [goal], distance = new Map([[key(goal), 0]]);
  for (let i = 0; i < queue.length; i++) for (const previous of reverse.get(key(queue[i])) || []) {
    const k = key(previous); if (distance.has(k)) continue;
    distance.set(k, distance.get(key(queue[i])) + 1); queue.push(previous);
  }
  const actions = successors(config, state).map(e => ({action: e.action, next: e.state,
    remainingDistance: distance.get(key(e.state)) ?? null,
    withinBudget: distance.has(key(e.state)) && distance.get(key(e.state)) + 1 <= budget}))
    .sort((a, b) => (a.remainingDistance ?? Infinity) - (b.remainingDistance ?? Infinity));
  return {status: 'viability_computed', distanceToComplete: distance.get(key(state)) ?? null,
    recommendation: actions.find(a => a.withinBudget)?.action ?? null, actions,
    proposed: proposed ? actions.find(a => key(a.action) === key(proposed)) ?? {status: step(config, state, proposed).status} : null,
    note: 'Return direction uses back plates independently of cargo; this is exact only for the supplied joint-track model.'};
}
