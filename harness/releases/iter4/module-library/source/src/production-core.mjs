import {key, sum} from './common.mjs';

export function transition(c, s, a) {
  const day = s.day;
  if (day >= c.days || [a.w, a.o, a.e, a.x, a.y].some(n => !Number.isInteger(n) || n < 0) ||
      typeof a.build !== 'boolean' || sum([a.w, a.o, a.e, a.x, a.y, Number(a.build)]) > c.workers[day]) return null;
  const n = {...s, day: day + 1};
  if (a.build) { if (s.cap !== 1 || s.wood < 3 || s.ore < 2) return null; n.wood -= 3; n.ore -= 2; n.cap = 2; }
  if (a.x + a.y > (c.maintenance.includes(day + 1) ? 1 : n.cap)) return null;
  n.wood += a.w * c.woodYield[day] - 2 * a.x - a.y;
  n.ore += a.o * c.oreYield[day] - a.x - 2 * a.y;
  n.energy += 2 * a.e - a.x - 2 * a.y;
  if (Math.min(n.wood, n.ore, n.energy) < 0) return null;
  n.lost = [Math.max(0, n.wood - c.storage[0]), Math.max(0, n.ore - c.storage[1]), Math.max(0, n.energy - c.storage[2])];
  [n.wood, n.ore, n.energy] = [n.wood, n.ore, n.energy].map((v, i) => Math.min(v, c.storage[i]));
  n.x += a.x; n.y += a.y;
  for (const q of c.due.filter(q => q.day === n.day)) { n.x -= q.x; n.y -= q.y; }
  if (n.x < 0 || n.y < 0) return null;
  return n;
}
function actions(c, s) {
  const result = [], n = c.workers[s.day];
  for (const build of [false, true]) for (let x = 0; x <= 2; x++) for (let y = 0; y <= 2 - x; y++)
    for (let w = 0; w <= n; w++) for (let o = 0; o <= n - w; o++) for (let e = 0; e <= n - w - o; e++) {
      const action = {w, o, e, x, y, build}, next = transition(c, s, action);
      if (next) result.push({action, next});
    }
  return result;
}
const goal = (c, s) => s.day === c.days && [s.wood, s.ore, s.energy].every((n, i) => n >= c.reserve[i]);
const canonical = s => key([s.day, s.wood, s.ore, s.energy, s.x, s.y, s.cap]);
export function search(c, initial, limit, ordering = () => 0, accept = () => true) {
  let visits = 0, cut = false; const dead = new Set();
  function visit(s) {
    if (++visits > limit) { cut = true; return null; }
    if (s.day === c.days) return goal(c, s) ? [] : null;
    const k = canonical(s); if (dead.has(k)) return null;
    for (const r of actions(c, s).filter(r => accept(s, r)).sort((a, b) => ordering(b) - ordering(a))) {
      const tail = visit(r.next); if (tail) return [r, ...tail]; if (cut) return null;
    }
    dead.add(k); return null;
  }
  const path = visit(initial);
  return {status: path ? 'feasible_plan' : cut ? 'search_limit' : 'infeasible_in_public_model', path, visits};
}
export function deadlines(c, s) {
  let needX = 0, needY = 0;
  return c.due.filter(q => q.day > s.day).map(q => {
    needX += q.x; needY += q.y;
    const products = Math.max(0, needX - s.x) + Math.max(0, needY - s.y);
    const slots = c.workers.slice(s.day, q.day).reduce((n, w, i) => n + Math.min(w,
      c.maintenance.includes(s.day + i + 1) ? 1 : 2), 0);
    return {deadline: q.day, unmetProducts: products, optimisticProductionSlots: slots, impossible: products > slots};
  });
}

