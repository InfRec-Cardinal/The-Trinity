import {observedGraph, graphRoute, shortest} from './common.mjs';

export function orderedStampRoute({observations, phase, start, stampOrder, stampLocations, collectedCount, goal, budget}) {
  const graph = observedGraph(observations, phase), missing = stampOrder.slice(collectedCount).filter(id => !Object.hasOwn(stampLocations, id));
  const nextId = stampOrder[collectedCount];
  if (missing.length) {
    const route = Object.hasOwn(stampLocations, nextId) ? graphRoute(graph, start, stampLocations[nextId], budget) : null;
    return {status: 'incomplete_target_map', missing, nextRequired: nextId, route,
      note: 'Remember out-of-order stamp locations without marking them collected.'};
  }
  const plan = shortest({room: start, next: collectedCount}, s => (graph.get(s.room) || []).map(room => {
    const next = s.next < stampOrder.length && stampLocations[stampOrder[s.next]] === room ? s.next + 1 : s.next;
    return {state: {room, next}, action: {to: room, expectedCollection: next > s.next ? stampOrder[s.next] : null}};
  }), s => s.next === stampOrder.length && s.room === goal, budget);
  return {...plan, nextRequired: nextId ?? null, note: 'Input progress comes from native receipts; current-room presence alone does not collect a previously skipped stamp.'};
}

export function phaseEdgeRepair({observations, oldPhase, phase, gates, current, home, budget, staticUnmarkedGuaranteed}) {
  if (!staticUnmarkedGuaranteed) return {status: 'unknown', reason: 'No public guarantee that unmarked corridors persist'};
  const graph = observedGraph(observations, oldPhase), changes = [];
  for (const g of gates) {
    if (!g.source || typeof g.openByPhase?.[phase] !== 'boolean') continue;
    for (const [from, to] of [[g.from, g.to], [g.to, g.from]]) {
      if (!graph.has(from)) continue;
      const before = graph.get(from), open = g.openByPhase[phase];
      graph.set(from, open ? [...new Set([...before, to])] : before.filter(x => x !== to));
    }
    changes.push({from: g.from, to: g.to, open: g.openByPhase[phase], source: g.source});
  }
  for (const [room, exits] of observedGraph(observations, phase)) graph.set(room, exits);
  const route = graphRoute(graph, current, home, budget);
  const staleRisk = gates.filter(g => !g.source || typeof g.openByPhase?.[phase] !== 'boolean');
  const uncertainEdges = new Set(staleRisk.flatMap(g => [JSON.stringify([g.from, g.to]), JSON.stringify([g.to, g.from])]));
  if (route.path?.some(a => uncertainEdges.has(JSON.stringify([a.from, a.to]))))
    return {status: 'reobserve_gate', changes, staleRisk, tentativeRoute: route};
  return {...route, changes, staleRisk, note: 'Unseen doors remain unknown; this graph is not the environment map oracle.'};
}
