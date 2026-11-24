import {equal, shortest} from './common.mjs';

function archive(rows, attributes) {
  const entries = new Map(), conflicts = [];
  for (const row of rows) {
    if (!row.source || row.visible !== true) continue;
    const old = entries.get(row.id);
    if (old && !equal(old.attributes, row.attributes)) { conflicts.push(row.id); continue; }
    entries.set(row.id, row);
  }
  return {entries, conflicts, incomplete: [...entries.values()].filter(r => attributes.some(k => !Object.hasOwn(r.attributes, k))).map(r => r.id)};
}
function route(targets, startRoom, depot, capacity, ordered, maxDepth, bag = [], delivered = []) {
  const byId = new Map(targets.map(t => [t.id, t])), ids = targets.map(t => t.id);
  const rooms = [...new Set([depot, ...targets.map(t => t.room)])];
  return shortest({room: startRoom, bag, delivered}, s => {
    const out = rooms.filter(r => r !== s.room).map(room => ({state: {...s, room}, action: {kind: 'move', room}}));
    if (s.bag.length < capacity) for (const id of ids) {
      const t = byId.get(id);
      if (t.room !== s.room || s.bag.includes(id) || s.delivered.includes(id)) continue;
      if (ordered && id !== ids[s.delivered.length + s.bag.length]) continue;
      out.push({state: {...s, bag: [...s.bag, id]}, action: {kind: 'take', room: t.room, slot: t.slot, id}});
    }
    if (s.room === depot && s.bag.length === capacity) out.push({state: {...s, bag: [],
      delivered: ordered ? [...s.delivered, ...s.bag] : [...s.delivered, ...s.bag].sort()}, action: {kind: 'deliver'}});
    return out;
  }, s => s.delivered.length === ids.length, maxDepth);
}

export function archiveAndUnorderedTour({observations, expectedIds, attributes, orders = null, startRoom, depot,
  capacity = 2, budget, sealed = false}) {
  const a = archive(observations, attributes), missing = expectedIds.filter(id => !a.entries.has(id));
  if (missing.length || a.conflicts.length || a.incomplete.length) return {status: 'scan_before_seal', missing,
    conflicts: a.conflicts, incomplete: a.incomplete, safeToSeal: false};
  if (!orders) return {status: sealed ? 'await_public_orders' : 'ready_to_seal', safeToSeal: true};
  const matches = orders.map(o => [...a.entries.values()].filter(r => Object.entries(o).every(([k, v]) => equal(r.attributes[k], v))));
  if (matches.some(m => m.length !== 1)) return {status: 'ambiguous_order', matches: matches.map(m => m.map(r => r.id))};
  const targets = matches.flat();
  if (new Set(targets.map(t => t.id)).size !== targets.length) return {status: 'conflicting_orders'};
  return {status: 'resolved', targets: targets.map(t => t.id), plan: route(targets, startRoom, depot, capacity, false, budget)};
}

export function orderedBatchPlanner({targets, startRoom, depot, bag = [], delivered = [], capacity = 2, budget}) {
  const ids = targets.map(t => t.id), prefix = [...delivered, ...bag];
  if (new Set(ids).size !== ids.length) return {status: 'unsupported_repeated_physical_item'};
  const mismatch = prefix.findIndex((id, i) => id !== ids[i]);
  if (mismatch >= 0 || bag.length > capacity || delivered.length % capacity !== 0)
    return {status: 'prefix_violation', mismatch, recovery: 'Inspect actual bag; only native LIFO return in original room is supported.'};
  const plan = route(targets, startRoom, depot, capacity, true, budget, bag, delivered);
  return {...plan, nextRequired: ids[prefix.length] ?? null,
    batches: Array.from({length: Math.ceil(ids.length / capacity)}, (_, i) => ids.slice(i * capacity, (i + 1) * capacity)),
    note: 'Targets must first be resolved from observed attributes; room transitions here cost one native move.'};
}
