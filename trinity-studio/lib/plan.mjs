import '../public/tree.js';

const {assertTree, analyzeTree} = globalThis.TrinityTree;

export function layeredPlan(tree, curriculum) {
  assertTree(tree);
  const info = analyzeTree(tree);
  const layers = new Map(), skipped = [];
  for (const node of tree.nodes) {
    if (node.kind !== 'capability') continue;
    const path = info.path(node.id), depth = info.depth(node.id), benches = info.benches(node.id);
    const levels = curriculum.filter(task => task.node === path && (!Array.isArray(node.variants) || node.variants.includes(task.variant)));
    if (!levels.length) {skipped.push({treeNode: node.id, path, benches}); continue;}
    const entry = layers.get(depth) ?? {layer: depth, nodes: [], benches: [], tasks: []};
    layers.set(depth, entry);
    entry.nodes.push(node.id);
    entry.benches.push(...benches);
    for (const level of levels) {
      const existing = entry.tasks.find(task => task.id === level.id);
      if (existing) {existing.treeNodes.push(node.id); continue;}
      entry.tasks.push({...level, moduleScope: info.scope(node.id), treeNodes: [node.id], path});
    }
  }
  const plan = [...layers.keys()].sort((a, b) => a - b).map(key => layers.get(key));
  if (!plan.length) throw Error('No capability path in this tree has practice levels in the environment package');
  return {layers: plan, skipped};
}
