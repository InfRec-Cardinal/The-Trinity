import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { now, writeJsonAtomic, writeFileAtomic } from './core.mjs';
import { setOf } from './split.mjs';

const ROOT_LABELS = { benchmarks: 'Benchmarks' };

export function buildTaskTree(state) {
  const { search: s, library, split } = state;
  if (!library || !split) throw new Error('the library and split must exist before the task tree can be exported');
  const nodes = library.tree, byParent = new Map();
  for (const node of nodes) byParent.set(node.parentId ?? null, [...(byParent.get(node.parentId ?? null) ?? []), node]);
  const tasksOf = id => library.tasks.filter(t => t.direction === id)
    .map(t => ({ taskId: t.taskId, name: t.name, set: split.sets[t.taskId] ?? null, route: t.route, sourceGroup: t.sourceGroup,
      lineage: t.lineageAudit?.status ?? null, unseenEligible: t.unseenEligible === true, sourceUrl: t.sourceUrl, origin: t.origin }))
    .sort((a, b) => (a.set === 'unseen' ? -1 : b.set === 'unseen' ? 1 : 0) || a.taskId.localeCompare(b.taskId));
  const walk = node => ({ id: node.id, label: node.label, definition: node.definition, boundary: node.boundary ?? null,
    children: (byParent.get(node.id) ?? []).map(walk), tasks: byParent.get(node.id)?.length ? [] : tasksOf(node.id) });
  const roots = Object.keys(ROOT_LABELS).map(id => ({ id, label: ROOT_LABELS[id], children: (byParent.get(id) ?? []).map(walk) }));
  return {
    schema: 'trinity-task-tree-v1', publishedAt: now(),
    run: { runId: s.runId, status: s.status, phase: s.phase, policyVersion: s.policyVersion, specificationVersion: s.specificationVersion },
    taxonomy: { fingerprint: s.taxonomy?.fingerprint ?? null, grownAt: s.taxonomy?.grownAt ?? null, nodes: nodes.length, directions: library.directions.length },
    lineage: { policy: s.lineageAudit?.policy ?? null, fingerprint: s.lineageAudit?.fingerprint ?? null, resources: s.lineageAudit?.resources.length ?? 0, auditedTasks: s.lineageAudit?.tasks.length ?? 0, at: s.lineageAudit?.at ?? null },
    split: { policy: split.policy, rule: split.rule, config: split.config, counts: split.counts, gaps: split.gaps, errors: split.errors, derivedAt: split.derivedAt },
    supplements: (s.supplements ?? []).map(r => ({ round: r.round, direction: r.direction, need: r.need, status: r.status, candidates: r.candidates.length })),
    roots,
  };
}

const bullet = (depth, text) => `${'  '.repeat(depth)}- ${text}`;
export function renderTaskTreeMarkdown(data) {
  const lines = ['# Task tree', '', `Run \`${data.run.runId}\` · status **${data.run.status}** · published ${data.publishedAt}.`, '',
    `Tree: ${data.taxonomy.nodes} nodes, ${data.taxonomy.directions} leaf directions (fingerprint \`${data.taxonomy.fingerprint}\`).`,
    `Provenance audit: ${data.lineage.auditedTasks} tasks over ${data.lineage.resources} canonical resources (fingerprint \`${data.lineage.fingerprint}\`).`,
    `Split (${data.split.policy}): train ${data.split.counts.train}, unseen ${data.split.counts.unseen}.`, ''];
  lines.push(data.split.gaps.length || data.split.errors.length
    ? `**Incomplete:** ${data.split.gaps.length} split gap(s), ${data.split.errors.length} error(s).`
    : '**Complete:** every direction has training tasks and independently audited unseen tasks; multiple unseen tasks per direction are allowed for interactive and static tasks alike.', '');
  const mark = task => task.set === 'unseen' ? '**unseen**' : 'train';
  const walk = (node, depth) => {
    lines.push(bullet(depth, `**${node.label}** - ${node.definition ?? ''}`.trim()));
    for (const child of node.children) walk(child, depth + 1);
    for (const task of node.tasks) lines.push(bullet(depth + 1, `${mark(task)} · \`${task.taskId}\` - ${task.name} (${task.route}, lineage ${task.lineage})`));
  };
  for (const root of data.roots) { lines.push('', `## ${root.label}`, ''); for (const child of root.children) walk(child, 0); }
  return lines.join('\n') + '\n';
}

export function renderTaskTreeSvg(data) {
  const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const ROW = 22, COL = [20, 240, 520, 860], W = 1500;
  let y = 30; const items = [], edges = [];
  const place = (node, depth, parentY) => {
    const top = y;
    const leafTasks = node.tasks ?? [];
    if (node.children?.length) { for (const child of node.children) place(child, depth + 1, null); }
    for (const task of leafTasks) { items.push({ x: COL[Math.min(depth + 1, 3)], y, text: `${task.set === 'unseen' ? '[unseen] ' : ''}${task.name}`, cls: task.set }); y += ROW; }
    const mid = leafTasks.length || node.children?.length ? (top + y - ROW) / 2 : y;
    if (!leafTasks.length && !node.children?.length) y += ROW;
    items.push({ x: COL[Math.min(depth, 3)], y: mid, text: node.label, cls: 'node', bold: depth <= 1 });
    if (parentY != null) edges.push([COL[Math.min(depth - 1, 3)] + 150, parentY, COL[Math.min(depth, 3)] - 6, mid]);
    for (const child of node.children ?? []) child._mid !== undefined && edges.push([COL[Math.min(depth, 3)] + 150, mid, COL[Math.min(depth + 1, 3)] - 6, child._mid]);
    node._mid = mid; y += 6;
    return mid;
  };
  for (const root of data.roots) place(root, 0, null);
  const colour = { train: '#1f2a37', unseen: '#8a5a00', node: '#243246' };
  const body = [...edges.map(([x1, y1, x2, y2]) => `<path d="M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}" fill="none" stroke="#97a3b3" stroke-width="1.2"/>`),
    ...items.map(i => `<text x="${i.x}" y="${i.y + 5}" font-family="Helvetica, Arial, sans-serif" font-size="13" ${i.bold ? 'font-weight="bold"' : ''} ${i.cls === 'unseen' ? 'font-style="italic"' : ''} fill="${colour[i.cls] ?? '#1f2a37'}">${esc(i.text)}</text>`)];
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${y + 20}" viewBox="0 0 ${W} ${y + 20}"><rect width="100%" height="100%" fill="#ffffff"/>${body.join('')}</svg>`;
}

export function buildHandoff(state) {
  const tree = buildTaskTree(state), nodes = new Map(state.library.tree.map(n => [n.id, n]));
  const pathOf = id => { const path = []; for (let cur = id; cur && nodes.get(cur)?.parentId; cur = nodes.get(cur).parentId) path.unshift(nodes.get(cur)); return path; };
  const tasks = state.library.tasks.map(t => {
    const path = pathOf(t.direction);
    const domain = path[0] ?? null, subClass = path[path.length - 1] ?? null;
    return { taskId: t.taskId, name: t.name, kind: t.kind, track: t.track, set: setOf(state, t.taskId), origin: t.origin, route: t.route, sourceUrl: t.sourceUrl,
      taskTreeOrigin: { domainId: domain?.id ?? null, domainName: domain?.label ?? null, subCategoryId: subClass?.id ?? null, subCategoryName: subClass?.label ?? null, path: path.map(n => n.id) },
      summary: t.summary, assignment: t.assignment, inputScope: t.inputScope, scorer: t.scorer, interface: t.interface };
  }).sort((a, b) => a.taskId.localeCompare(b.taskId));
  return { schema: 'trinity-stage2-handoff-v1', createdAt: now(), taskTree: tree, tasks };
}

export function exportLibrary(store, exportDir) {
  mkdirSync(exportDir, { recursive: true });
  const tree = buildTaskTree(store.state), stamp = tree.publishedAt.slice(0, 10).replace(/-/g, '');
  const files = { json: join(exportDir, `task-tree-${stamp}.json`), txt: join(exportDir, `task-tree-${stamp}.txt`), svg: join(exportDir, `task-tree-${stamp}.svg`), handoff: join(exportDir, `stage2-handoff-${stamp}.json`) };
  writeJsonAtomic(files.json, tree);
  writeFileAtomic(files.txt, renderTaskTreeMarkdown(tree));
  writeFileAtomic(files.svg, renderTaskTreeSvg(tree));
  writeJsonAtomic(files.handoff, buildHandoff(store.state));
  store.event('library_exported', { files: Object.values(files) });
  return files;
}
