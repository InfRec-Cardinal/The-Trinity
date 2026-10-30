import {clone, ensure, snapshot} from './core.mjs';

export function mergeRoutingCandidates(candidates) {
  const bySnapshot = new Map();
  for (const candidate of candidates) {
    ensure(candidate.snapshotId === snapshot(candidate.modules).id, 'Candidate snapshot mismatch');
    const source = {node: candidate.node, endpointTaskIds: clone(candidate.endpointTaskIds), description: candidate.description};
    const existing = bySnapshot.get(candidate.snapshotId);
    if (!existing) {
      bySnapshot.set(candidate.snapshotId, {candidate: clone(candidate), sources: [source]});
      continue;
    }
    ensure(!existing.sources.some(row => row.node === source.node), 'Duplicate routing source node');
    existing.sources.push(source);
  }
  return [...bySnapshot.values()].map(({candidate, sources}) => {
    if (sources.length === 1) return candidate;
    return {...candidate, sourceNodes: sources,
      endpointTaskIds: [...new Set(sources.flatMap(source => source.endpointTaskIds))],
      description: 'One unchanged Harness configuration is shared by these training endpoints. The path definitions below record provenance, not evidence that rejected updates added capabilities.\n' +
        JSON.stringify(sources.map(({node, description}) => ({node, description})), null, 2)};
  });
}
