import {key, shortest} from './common.mjs';

export function step(config, state, action) {
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
export function successors(config, state) {
  const result = [];
  for (let da = -1; da <= 1; da++) for (let db = -1; db <= 1; db++) {
    if (!da && !db) continue;
    const action = {da, db}, r = step(config, state, action);
    if (r.status === 'legal') result.push({state: r.state, action});
  }
  return result;
}
export const done = (c, s) => s.a === 0 && s.b === 0 && s.pa === (1 << c.aCargo.length) - 1 && s.pb === (1 << c.bCargo.length) - 1;

