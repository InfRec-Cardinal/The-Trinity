import { now } from '../core.mjs';
import { ROOTS } from './schema.mjs';
import { rootOf } from './taxonomy.mjs';
import { declaredResources, resourceTokens, isCurrentLineageAudit } from './lineage.mjs';
import { isCurrentAdmission } from './specify.mjs';

export function deriveGroups(specs, audit = null) {
  const parent = new Map();
  const find = x => { while (parent.get(x) !== x) { parent.set(x, parent.get(parent.get(x))); x = parent.get(x); } return x; };
  const add = x => { if (!parent.has(x)) parent.set(x, x); };
  const registry = new Map((audit?.resources ?? []).map(r => [r.id, r]));
  const audited = new Map((audit?.tasks ?? []).map(t => [t.taskId, t]));
  for (const spec of specs) {
    add(`t:${spec.taskId}`);
    const resources = [...declaredResources(spec), ...(audited.get(spec.taskId)?.resourceIds ?? []).map(id => registry.get(id)).filter(Boolean)];
    for (const r of resources) for (const token of resourceTokens(r)) { add(`r:${token}`); parent.set(find(`t:${spec.taskId}`), find(`r:${token}`)); }
  }
  const members = new Map();
  for (const key of parent.keys()) members.set(find(key), [...(members.get(find(key)) ?? []), key]);
  const groups = {};
  for (const spec of specs) {
    const component = members.get(find(`t:${spec.taskId}`));
    const tasks = component.filter(k => k.startsWith('t:'));
    groups[spec.taskId] = tasks.length === 1 ? `solo:${spec.taskId}` : `shared:${tasks.map(k => k.slice(2)).sort().join('+')}`;
  }
  return groups;
}

export const leavesOf = taxonomy => taxonomy.nodes.filter(n => !(n.id in ROOTS) && !taxonomy.nodes.some(m => m.parentId === n.id));
export function pathOf(taxonomy, id) {
  const nodes = new Map(taxonomy.nodes.map(n => [n.id, n])), path = [];
  for (let cur = id; cur && !(cur in ROOTS); cur = nodes.get(cur)?.parentId) path.unshift(nodes.get(cur)?.label ?? cur);
  return path;
}

export function assembleLibrary(state) {
  const s = state.search, nodes = new Map(s.taxonomy.nodes.map(n => [n.id, n]));
  const currentAudit = isCurrentLineageAudit(state), audit = currentAudit ? s.lineageAudit : null;
  const admitted = Object.values(s.candidates).filter(c => c.status === 'admitted' && isCurrentAdmission(s.specs[c.taskId], s.reviews[c.taskId]));
  const specs = admitted.map(c => s.specs[c.taskId]);
  const groups = deriveGroups(specs, audit), groupSize = new Map();
  for (const group of Object.values(groups)) groupSize.set(group, (groupSize.get(group) ?? 0) + 1);
  const directions = leavesOf(s.taxonomy).map(n => ({ id: n.id, label: n.label, definition: n.definition, parentId: n.parentId, track: rootOf(nodes, n.id), path: pathOf(s.taxonomy, n.id) }));
  const tasks = admitted.filter(c => s.taxonomy.assignments[c.taskId]).map(c => {
    const spec = s.specs[c.taskId], review = s.reviews[c.taskId];
    const lineageAudit = audit?.tasks.find(t => t.taskId === c.taskId) ?? null;
    const freshReview = isCurrentAdmission(spec, review);
    const authority = { ...spec.authority };
    for (const metric of ['stars', 'citations']) {
      const verdict = Array.isArray(review?.authority) ? review.authority.find(row => row.metric === metric)?.verdict : review?.authority?.[metric]?.verdict;
      if (!freshReview || !spec.authority?.evidence?.[metric]?.length || verdict !== 'supported') authority[metric] = null;
    }
    return { taskId: c.taskId, name: c.name, kind: c.kind, track: rootOf(nodes, s.taxonomy.assignments[c.taskId]), direction: s.taxonomy.assignments[c.taskId], path: pathOf(s.taxonomy, s.taxonomy.assignments[c.taskId]),
      origin: c.origin ?? 'search', selfProposed: c.origin === 'self_proposed', sourceUrl: c.sourceUrl, summary: spec.summary, assignment: spec.assignment,
      inputScope: spec.inputScope, scopeReview: review.scope, interface: spec.interface, scorer: spec.scorer, route: c.kind === 'static' ? 'official_dataset' : spec.interface.route,
      lineage: spec.lineage, lineageAudit, sourceGroup: groups[c.taskId] ?? `solo:${c.taskId}`,
      unseenEligible: c.origin !== 'self_proposed' && freshReview && lineageAudit?.status === 'independent' && lineageAudit.resourceIds.length > 0
        && groupSize.get(groups[c.taskId]) === 1,
      authority, sources: spec.sources, deliverable: true, admittedAt: review?.at ?? null };
  });
  return { source: { kind: 'search', runId: s.runId, assembledAt: now(), lineageFingerprint: audit?.fingerprint ?? null, lineageCurrent: currentAudit }, tree: s.taxonomy.nodes, directions, tasks };
}
