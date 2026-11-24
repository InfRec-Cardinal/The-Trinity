import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const load = (code, file) => import(pathToFileURL(path.join(code, file)).href);
const CAP = /^[a-z][a-z0-9_]{0,15}$/;
function slug(label, id, used) {
  let base = String(label || id).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 16);
  if (!CAP.test(base)) base = String(id).toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 16);
  if (!CAP.test(base) || !base) base = 'cap';
  let s = base, n = 1;
  while (used.has(s)) s = (base.slice(0, 14) + '_' + (++n)).slice(0, 16);
  used.add(s);
  return s;
}

export function taxonomyToSearchDoc(taxonomy, admitted) {
  const nodes = taxonomy.nodes.filter(n => n.parentId !== null);
  const used = new Set();
  const capOf = new Map();
  const capabilities = [];
  for (const node of nodes) {
    const cap = slug(node.label, node.id, used);
    capOf.set(node.id, cap);
    capabilities.push({id: cap, name: node.label || node.id, definition: node.definition || node.label || node.id});
  }
  const benchesByNode = new Map();
  for (const task of admitted) {
    const list = benchesByNode.get(task.nodeId) ?? [];
    list.push(task.name);
    benchesByNode.set(task.nodeId, list);
  }
  const childrenByParent = new Map();
  for (const node of nodes) {
    const parent = node.parentId && capOf.has(node.parentId) ? node.parentId : null;
    const list = childrenByParent.get(parent) ?? [];
    list.push(node.id);
    childrenByParent.set(parent, list);
  }
  const treeNodes = nodes.map(node => ({
    id: node.id,
    parent: node.parentId && capOf.has(node.parentId) ? node.parentId : null,
    capability: capOf.get(node.id),
    children: childrenByParent.get(node.id) ?? [],
    tasks: benchesByNode.get(node.id) ?? [],
  }));
  return {schema: 'trinity-provisional-domain-capability-tree-v1', capabilities, tree: {nodes: treeNodes}};
}

export async function runScratchSearch({code, callModel, profile, apiKey, emit, directory, signal}) {
  const {openStore} = await load(code, 'pipeline/src/store.mjs');
  const {runSearch} = await load(code, 'pipeline/src/search/index.mjs');
  const {buildHandoff} = await load(code, 'pipeline/src/library.mjs');
  const {supportsSearch} = await load(code, 'pipeline/src/model.mjs');
  if (!supportsSearch(profile)) throw Error('Run from scratch requires a search-enabled provider');
  const store = openStore(directory);
  const ctx = {store, profile, apiKey, callModel, signal, emit: (type, data) => emit('search_event', {type, ...data})};
  emit('phase', {phase: 'search'});
  await runSearch(ctx);
  const s = store.state.search;
  if (s.status !== 'done') throw Error('Search is incomplete; see the saved search checkpoint');
  const handoff = buildHandoff(store.state);
  if (handoff.taskTree.split.gaps.length || handoff.taskTree.split.errors.length) throw Error('Search split is incomplete');
  fs.writeFileSync(path.join(directory,'handoff.json'),JSON.stringify(handoff,null,2)+'\n');
  for (const task of handoff.tasks) emit('bench_found',{bench:task.name,taskId:task.taskId,cohort:task.set});
  return handoff;
}
