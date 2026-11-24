(function (root) {
  'use strict';
  const TREE_SCHEMA = 'trinity-studio-tree-v3';
  const SEARCH_SCHEMA = 'trinity-provisional-domain-capability-tree-v1';
  const ID = /^[A-Za-z][A-Za-z0-9_-]{0,79}$/;
  const CAP = /^[a-z][a-z0-9_]{0,15}$/;
  const LIMITS = {nodes: 2000, links: 4000, name: 120, bench: 120};
  const KINDS = ['capability', 'bench'];

  function emptyTree(name) {
    return {schema: TREE_SCHEMA, name: name || 'Untitled', capabilities: {}, levels: {}, nodes: [], links: []};
  }

  function validBenchName(value) {
    return typeof value === 'string' && value.trim().length > 0 && value.length <= LIMITS.bench && !/[\u0000-\u001f]/.test(value);
  }

  const LEVEL_REF = /^[a-f0-9]{64}$/;
  const LEVEL_NODE = /^[a-z][a-z0-9_-]{0,159}$/;
  const MAX_LEVEL_SOURCE = 400000, MAX_TAPE = 300;
  const plainObject = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const matches = (pattern, value) => typeof value === 'string' && pattern.test(value);
  function validTape(tape) {
    return plainObject(tape) && Number.isInteger(tape.variant) && tape.variant >= 0 && tape.variant < 64 &&
      Array.isArray(tape.actions) && tape.actions.length <= MAX_TAPE &&
      tape.actions.every(a => plainObject(a) && typeof a.action === 'string' && a.action.length > 0 && a.action.length <= 200 &&
        (a.args === undefined || plainObject(a.args)));
  }
  function validLevelRef(level) {
    return plainObject(level) && matches(LEVEL_REF, level.ref) && matches(LEVEL_NODE, level.node) &&
      Number.isInteger(level.variant) && level.variant >= 0 && level.variant < 64 &&
      (level.budget === undefined || (Number.isInteger(level.budget) && level.budget > 0));
  }

  const FRAME_FILE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,220}$/;
  function validPreview(p) {
    if (!plainObject(p) || !['run', 'level'].includes(p.source) || !Array.isArray(p.rounds) || p.rounds.length > 20) return false;
    if (p.source === 'level') return p.rounds.every(r => plainObject(r) && Number.isInteger(r.round) && validTape(r.tape) &&
      (r.success === null || r.success === undefined || typeof r.success === 'boolean'));
    return p.rounds.every(r => r && Number.isInteger(r.round) && Array.isArray(r.frames) && r.frames.length <= 5000 &&
      r.frames.every(f => f === null || (typeof f === 'string' && FRAME_FILE.test(f))));
  }

  function validateTree(tree) {
    const errors = [], fail = message => errors.push(message);
    if (!plainObject(tree)) return ['Tree must be a JSON object'];
    const known = plainObject(tree.capabilities) ? tree.capabilities : {};
    if (tree.schema !== TREE_SCHEMA) fail('Unsupported tree schema (expected ' + TREE_SCHEMA + ')');
    if (typeof tree.name !== 'string' || !tree.name.trim() || tree.name.length > LIMITS.name) fail('Invalid tree name');
    if (tree.capabilities !== undefined && !plainObject(tree.capabilities)) fail('Invalid capability definitions');
    for (const [id, cap] of Object.entries(known)) {
      if (!matches(CAP, id) || !plainObject(cap) || typeof cap.name !== 'string' || !cap.name.trim()) fail('Invalid capability definition ' + id);
    }
    if (tree.benchLabels !== undefined && (!plainObject(tree.benchLabels) || Object.entries(tree.benchLabels).some(([id, label]) => !validBenchName(id) || !validBenchName(label)))) fail('Invalid bench display names');
    const levels = tree.levels === undefined ? {} : tree.levels;
    if (!plainObject(levels)) fail('Invalid level library');
    else for (const [ref, level] of Object.entries(levels)) {
      if (!matches(LEVEL_REF, ref) || !plainObject(level) || typeof level.source !== 'string' || !level.source.trim() || level.source.length > MAX_LEVEL_SOURCE) {fail('Invalid level ' + ref.slice(0, 12)); continue;}
      if (level.meta !== undefined && !plainObject(level.meta)) {fail('Invalid meta on level ' + ref.slice(0, 12)); continue;}
      const provides = level.meta ? level.meta.provides : undefined;
      if (provides === undefined) continue;
      if (!Array.isArray(provides) || provides.length > 200 || !provides.every(o => plainObject(o) && (o.name === undefined || validBenchName(o.name)) && matches(CAP, o.capability) && validLevelRef({ref, node: o.node, variant: o.variant, budget: o.budget})))
        fail('Invalid provides list on level ' + ref.slice(0, 12));
      else for (const o of provides) if (!Object.prototype.hasOwnProperty.call(known, o.capability)) fail('Level ' + ref.slice(0, 12) + ' provides undefined capability ' + o.capability);
    }
    if (!Array.isArray(tree.nodes) || tree.nodes.length > LIMITS.nodes) return errors.concat('Invalid node list');
    if (!Array.isArray(tree.links) || tree.links.length > LIMITS.links) return errors.concat('Invalid link list');
    const byId = new Map();
    for (const node of tree.nodes) {
      if (!node || typeof node !== 'object') {fail('Invalid node'); continue;}
      if (!matches(ID, node.id) || byId.has(node.id)) {fail('Invalid or duplicate node id' + (typeof node.id === 'string' ? ': ' + node.id : '')); continue;}
      byId.set(node.id, node);
      if (!KINDS.includes(node.kind)) fail('Node ' + node.id + ' must be a capability or a bench');
      if (!Array.isArray(node.pos) || node.pos.length !== 2 || !node.pos.every(Number.isFinite)) fail('Invalid position on node ' + node.id);
      if (node.kind === 'capability') {
        if (!matches(CAP, node.capability)) fail('Invalid capability on node ' + node.id);
        else if (!Object.prototype.hasOwnProperty.call(known, node.capability)) fail('Unknown capability ' + node.capability + ' (define it in tree.capabilities)');
        if (node.variants !== undefined && (!Array.isArray(node.variants) || !node.variants.every(v => Number.isInteger(v) && v >= 0 && v < 64))) fail('Invalid variants on node ' + node.id);
        if (node.level !== undefined) {
          if (!validLevelRef(node.level)) fail('Invalid level reference on node ' + node.id);
          else if (!plainObject(levels) || !Object.prototype.hasOwnProperty.call(levels, node.level.ref)) fail('Node ' + node.id + ' references a level missing from tree.levels');
        }
      }
      if (node.kind === 'bench' && !validBenchName(node.bench)) fail('Invalid bench name on node ' + node.id);
      if (node.modules !== undefined && (!Array.isArray(node.modules) || !node.modules.every(plainObject))) fail('Invalid modules on node ' + node.id);
      if (node.preview !== undefined) {
        if (!validPreview(node.preview)) fail('Invalid preview on node ' + node.id);
        else if (node.preview.source === 'level' && node.level === undefined) fail('Node ' + node.id + ' has a level preview but no level');
      }
    }
    const benchLabel = node => typeof node.bench === 'string' ? node.bench : node.id;
    const linkIds = new Set(), parent = new Map(), attached = new Set();
    for (const link of tree.links) {
      if (!link || typeof link !== 'object' || !matches(ID, link.id) || linkIds.has(link.id)) {fail('Invalid or duplicate link id'); continue;}
      linkIds.add(link.id);
      const from = byId.get(link.from), to = byId.get(link.to);
      if (!from || !to) {fail('Link ' + link.id + ' references a missing node'); continue;}
      if (from === to) {fail('Link ' + link.id + ' connects a node to itself'); continue;}
      if (from.kind !== 'capability') {fail('Bench "' + benchLabel(from) + '" is a leaf and cannot have children'); continue;}
      if (parent.has(to.id)) fail('Node ' + to.id + ' has more than one parent');
      parent.set(to.id, from.id);
      if (to.kind === 'bench' && validBenchName(to.bench)) {
        const key = from.id + '|' + to.bench;
        if (attached.has(key)) fail('Bench "' + benchLabel(to) + '" is attached twice under the same node');
        attached.add(key);
      }
    }
    for (const node of byId.values()) if (node.kind === 'bench' && !parent.has(node.id)) fail('Bench "' + benchLabel(node) + '" is not attached to a capability');
    if (!errors.length) {
      for (const id of byId.keys()) {
        const seen = new Set();
        for (let at = id; parent.has(at);) {
          at = parent.get(at);
          if (at === id || seen.has(at)) {fail('Cycle through node ' + id); break;}
          seen.add(at);
        }
      }
    }
    return errors;
  }

  function assertTree(tree) {
    const errors = validateTree(tree);
    if (errors.length) throw Error(errors.join('; '));
    return tree;
  }

  function analyzeTree(tree) {
    const parent = new Map(tree.links.map(link => [link.to, link.from]));
    const byId = new Map(tree.nodes.map(node => [node.id, node]));
    const owner = id => (byId.get(id) && byId.get(id).kind === 'bench' ? parent.get(id) : id);
    const chain = id => {
      const out = [], seen = new Set();
      for (let at = owner(id); at && !seen.has(at); at = parent.get(at)) {
        seen.add(at);
        if (byId.get(at) && byId.get(at).kind === 'capability') out.unshift(byId.get(at).capability);
      }
      return out;
    };
    const path = id => chain(id).join('-');
    const scope = id => chain(id).map((_, index, all) => all.slice(0, index + 1).join('-'));
    const depth = id => chain(id).length;
    const children = id => tree.links.filter(link => link.from === id).map(link => byId.get(link.to)).filter(Boolean);
    const benches = id => children(id).filter(node => node.kind === 'bench').map(node => node.bench);
    return {parent, owner, chain, path, scope, depth, children, benches};
  }

  const slug = value => String(value).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40) || 'x';

  function layout(name, rows, capabilities) {
    const COLUMN = 320, ROW = 40, GAP = 34, CARD = 170;
    const used = new Set(), nodeIds = new Map();
    const unique = base => {
      let id = base.slice(0, 72), n = 1;
      while (used.has(id)) id = base.slice(0, 72) + '_' + (++n);
      used.add(id);
      return id;
    };
    const nid = key => {if (!nodeIds.has(key)) nodeIds.set(key, unique('n_' + slug(key))); return nodeIds.get(key);};
    const maxDepth = Math.max(1, ...rows.map(row => row.depth));
    const benchX = 60 + maxDepth * COLUMN + 40;
    const kids = new Map();
    for (const row of rows) {const p = row.parentKey || ''; if (!kids.has(p)) kids.set(p, []); kids.get(p).push(row);}
    const nodes = [], links = [];
    let y = 40;
    const place = row => {
      const top = y, id = nid(row.key);
      const node = {id, kind: 'capability', capability: row.capability, pos: [60 + (row.depth - 1) * COLUMN, top]};
      nodes.push(node);
      if (row.parentKey) links.push({id: unique('l_' + id.slice(2)), from: nid(row.parentKey), to: id});
      row.benches.forEach(bench => {
        const bid = unique('b_' + slug(row.key) + '_' + slug(bench));
        nodes.push({id: bid, kind: 'bench', bench, pos: [benchX, y]});
        links.push({id: unique('l_' + bid.slice(2)), from: id, to: bid});
        y += ROW;
      });
      if (row.benches.length) node.pos[1] = Math.max(top, Math.round((top + y - ROW) / 2 - 50));
      y = Math.max(y, top + CARD) + GAP;
      for (const child of kids.get(row.key) || []) place(child);
    };
    for (const row of kids.get('') || []) place(row);
    return {schema: TREE_SCHEMA, name, capabilities: capabilities || {}, levels: {}, nodes, links};
  }

  function importSearchTree(doc, name) {
    if (!doc || doc.schema !== SEARCH_SCHEMA || !doc.tree || !Array.isArray(doc.tree.nodes)) throw Error('Not a searched capability tree');
    const capabilities = {};
    for (const cap of doc.capabilities || []) {
      if (cap && matches(CAP, cap.id)) {
        if (Object.prototype.hasOwnProperty.call(capabilities, cap.id)) throw Error('Duplicate capability ' + cap.id);
        capabilities[cap.id] = {id: cap.id, name: String(cap.name || cap.id).slice(0, 120), definition: String(cap.definition || '').slice(0, 2000)};
      }
    }
    const byId = new Map(), parents = new Map();
    for (const node of doc.tree.nodes) {
      if (!plainObject(node) || typeof node.id !== 'string' || !node.id || byId.has(node.id)) throw Error('Invalid or duplicate searched node ID');
      if (node.children !== undefined && !Array.isArray(node.children)) throw Error('Invalid searched children on ' + node.id);
      if (node.parent !== undefined && node.parent !== null && (typeof node.parent !== 'string' || !node.parent)) throw Error('Invalid searched parent on ' + node.id);
      byId.set(node.id, node);
    }
    for (const node of byId.values()) for (const child of node.children || []) {
      if (typeof child !== 'string' || !byId.has(child)) throw Error('Missing or invalid searched child on ' + node.id);
      if (parents.has(child)) throw Error('Duplicate child or multiple parents on ' + child);
      parents.set(child, node.id);
    }
    for (const node of byId.values()) {
      if (node.parent !== undefined && node.parent !== (parents.get(node.id) ?? null)) throw Error('Conflicting searched parent on ' + node.id);
    }
    const rows = [], seen = new Set();
    const roots = doc.tree.nodes.filter(node => !parents.has(node.id));
    const pending = roots.map(node => ({id: node.id, parentKey: null, depth: 0})).reverse();
    let outputNodes = 0;
    while (pending.length) {
      const {id, parentKey, depth} = pending.pop(), node = byId.get(id);
      if (seen.has(id)) throw Error('Cycle through searched node ' + id);
      seen.add(id);
      const hasCapability = node.capability !== undefined && node.capability !== null;
      const here = hasCapability ? depth + 1 : depth;
      if (hasCapability) {
        if (!matches(CAP, node.capability)) throw Error('Invalid capability on searched node ' + id);
        const benches = (Array.isArray(node.tasks) ? node.tasks : []).filter(validBenchName);
        outputNodes += 1 + benches.length;
        if (outputNodes > LIMITS.nodes) throw Error('Imported tree exceeds node limit');
        rows.push({key: id, capability: node.capability, parentKey, depth: here, benches});
      }
      const children = node.children || [];
      for (let i = children.length - 1; i >= 0; i--) pending.push({id: children[i], parentKey: hasCapability ? id : parentKey, depth: here});
    }
    if (seen.size !== byId.size) throw Error('Search tree contains a cycle');
    return assertTree(layout(name || doc.domain || 'imported', rows, capabilities));
  }

  function arrangeTree(tree, size, viewport) {
    const GAP_Y = 16, BENCH_GAP = 5, BENCH_TOP = 64;
    let column = 704;
    const height = node => (size && size(node)) || (node.kind === 'bench' ? 32 : 320);
    const byId = new Map(tree.nodes.map(node => [node.id, node])), kids = new Map(), parent = new Map();
    for (const link of tree.links) if (byId.has(link.from) && byId.has(link.to)) {
      if (!kids.has(link.from)) kids.set(link.from, []);
      kids.get(link.from).push(byId.get(link.to)); parent.set(link.to, link.from);
    }
    // Move each branch as a unit. Match its occupied columns against the
    // preceding branches, allowing only their empty margins to interleave.
    // Parent/first-child alignment and the original sibling order stay intact.
    const placed = new Set();
    const merge = (target, branch, depthOffset, yOffset) => {
      for (const item of branch.items) target.items.push({...item, depth: item.depth + depthOffset, y: item.y + yOffset});
      for (const [depth, bounds] of branch.contour) {
        const at = depth + depthOffset, top = bounds[0] + yOffset, bottom = bounds[1] + yOffset, old = target.contour.get(at);
        target.contour.set(at, old ? [Math.min(old[0], top), Math.max(old[1], bottom)] : [top, bottom]);
      }
    };
    const append = (target, branch) => {
      let shift = 0;
      for (const [depth, bounds] of branch.contour) {
        const previous = target.contour.get(depth);
        if (previous) shift = Math.max(shift, previous[1] + GAP_Y - bounds[0]);
      }
      merge(target, branch, 0, shift);
    };
    const build = node => {
      const branch = {items: [], contour: new Map()};
      if (placed.has(node.id)) return branch;
      placed.add(node.id);
      branch.items.push({node, depth: 0, y: 0, dx: 0});
      const children = kids.get(node.id) || [], benches = children.filter(n => n.kind === 'bench'), caps = children.filter(n => n.kind === 'capability');
      let y = BENCH_TOP;
      for (const bench of benches) {
        if (placed.has(bench.id)) continue;
        placed.add(bench.id); branch.items.push({node: bench, depth: 0, y, dx: 452}); y += height(bench) + BENCH_GAP;
      }
      branch.contour.set(0, [0, Math.max(height(node), benches.length ? y - BENCH_GAP : 0)]);
      const descendants = {items: [], contour: new Map()};
      for (const child of caps) append(descendants, build(child));
      merge(branch, descendants, 1, 0);
      return branch;
    };
    const layout = {items: [], contour: new Map()};
    for (const root of tree.nodes.filter(n => n.kind === 'capability' && !parent.has(n.id))) append(layout, build(root));
    const maxDepth = Math.max(0, ...layout.contour.keys());
    const totalHeight = Math.max(0, ...[...layout.contour.values()].map(bounds => bounds[1]));
    if (maxDepth && viewport?.width > 0 && viewport?.height > 0) {
      column = Math.max(704, Math.min(960, Math.round((totalHeight * viewport.width / viewport.height - 892) / maxDepth)));
    }
    for (const {node, depth, y, dx} of layout.items) node.pos = [60 + depth * column + dx, 40 + Math.round(y)];
    let x = 60, y = 40 + totalHeight + GAP_Y;
    for (const node of tree.nodes.filter(n => !placed.has(n.id))) {node.pos = [x, y]; x += (node.kind === 'bench' ? 220 : 420) + 30;}
    // Keep branch regions compact while siblings share one horizontal position.
    const caps = layout.items.filter(item => item.node.kind === 'capability').map(item => item.node);
    if (viewport?.width > 0 && viewport?.height > 0 && caps.length >= 4 && caps.length <= 24) {
      const proposed = new Map();
      for (const node of caps) {
        proposed.set(node.id, [60 + (node.pos[0] - 60) * .92, 40 + (node.pos[1] - 40) * .68]);
      }
      const occupied = [], intersects = (x, y, w, h) => occupied.some(r => x < r.x + r.w + 12 && x + w + 12 > r.x && y < r.y + r.h + 12 && y + h + 12 > r.y);
      for (const node of [...caps].sort((a, b) => proposed.get(a.id)[1] - proposed.get(b.id)[1])) {
        const [x, targetY] = proposed.get(node.id); let y = targetY;
        while (intersects(x, y, 420, height(node))) y += 12;
        node.pos = [Math.round(x), Math.round(y)]; occupied.push({x: node.pos[0], y: node.pos[1], w: 420, h: height(node)});
      }
      // Keep the owner's bench siblings in a single nearby column as well.
      for (const node of caps) {
        const benches = (kids.get(node.id) || []).filter(n => n.kind === 'bench');
        if (!benches.length) continue;
        const groupHeight = benches.reduce((sum, bench) => sum + height(bench) + BENCH_GAP, -BENCH_GAP);
        const desired = [node.pos[0] + 452, node.pos[1] + BENCH_TOP];
        let best = null;
        for (const x of [desired[0], desired[0] + 232, node.pos[0] + 232, node.pos[0]]) for (let offset = -64; offset <= 800; offset += 8) {
          const y = desired[1] + offset;
          if (y < 40 || intersects(x, y, 220, groupHeight)) continue;
          const score = (x - desired[0]) ** 2 + (y - desired[1]) ** 2;
          if (!best || score < best.score) best = {x, y, score};
        }
        if (!best) {
          let y = node.pos[1] + height(node) + 16;
          while (intersects(desired[0], y, 220, groupHeight)) y += 16;
          best = {x: desired[0], y};
        }
        let y = Math.round(best.y);
        for (const bench of benches) {
          bench.pos = [Math.round(best.x), y]; occupied.push({x: bench.pos[0], y, w: 220, h: height(bench)});
          y += height(bench) + BENCH_GAP;
        }
      }
    }
    return tree;
  }

  root.TrinityTree = {TREE_SCHEMA, SEARCH_SCHEMA, emptyTree, validateTree, assertTree, analyzeTree, importSearchTree, validBenchName, arrangeTree};
})(globalThis);
