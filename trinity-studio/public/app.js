(function () {
  'use strict';
  const {t, setLang, getLang} = globalThis.TrinityI18n;
  const {emptyTree, validateTree, analyzeTree, importSearchTree, validBenchName, arrangeTree, SEARCH_SCHEMA} = globalThis.TrinityTree;
  const $ = sel => document.querySelector(sel);
  const el = (tag, cls, text) => {const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e;};
  const WIDTH = {capability: 420, bench: 220};
  const SLOT_Y = {capability: 45, bench: 15};
  const BENCH_GAP = 12;
  const state = {info: null, offline: false, pages: [], active: 0, apiKey: '', connection: 'official', relayUrl: '', keys: {official: '', relay: ''}, run: null,
    selected: new Set(), status: {}, environments: null};
  let environmentTimer = null, environmentPromptPending = false, environmentRequestId = 0;
  const page = () => state.pages[state.active];
  Object.defineProperty(state, 'status', {get: () => page()?.status || {}, set: value => {if (page()) page().status = value;}});
  const explorer = globalThis.TrinityExplorer.create({getPage: page, t, getLang, onFocus: id => {if (id && page()?.detailView) showStage(id);}, fit: () => fitView(), transform: () => renderTransform(),
    getLabel: node => node.kind === 'bench' ? benchLabel(node.bench) : node.level ? levelTitle(page().tree, node.level.ref) + ' · ' + node.level.node : capabilityInfo(node.capability)?.name || node.capability || node.id});
  let editDepth = 0, editGesture = false;
  let viewGesture = null;
  const editingLocked = p => state.run?.page === p && ['starting', 'running', 'stopping'].includes(state.run.status);
  const snapshot = p => JSON.stringify({tree: p.tree, draftBenches: p.draftBenches || []});
  function renderHistory() {
    const p = page(), locked = !p || editingLocked(p) || editGesture;
    for (const action of ['undo', 'redo']) document.querySelectorAll('[data-act="' + action + '"]').forEach(b => {b.disabled = locked || !p[action]?.length;});
  }
  function commitEdit(p, before) {
    if (before !== snapshot(p)) {
      (p.undo ||= []).push(before);
      while (p.undo.length > 50 || (p.undo.length > 1 && p.undo.reduce((size, value) => size + value.length, 0) > 8000000)) p.undo.shift();
      p.redo = [];
    }
    renderHistory();
  }
  function edit(fn) {
    const p = page();
    if (editingLocked(p) || editGesture) return;
    if (editDepth) return fn();
    const before = snapshot(p);
    editDepth++;
    try {return fn();} finally {editDepth--; commitEdit(p, before);}
  }
  function restoreEdit(action) {
    const p = page();
    if (editingLocked(p) || editGesture || !p[action]?.length) return;
    (p[action === 'undo' ? 'redo' : 'undo'] ||= []).push(snapshot(p));
    Object.assign(p, JSON.parse(p[action].pop()));
    state.selected.clear(); state.status = {};
    renderAll();
  }
  const uid = prefix => prefix + '_' + Math.random().toString(36).slice(2, 9);

  async function request(method, url, body) {
    if (state.offline) throw Error(t('noServer'));
    const headers = {};
    if (method !== 'GET') headers['X-Studio-Token'] = state.info ? state.info.token : '';
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const res = await fetch(url, {method, headers, body: body === undefined ? undefined : JSON.stringify(body)});
    let data;
    try {data = await res.json();} catch (error) {if (res.ok) throw error;}
    if (!res.ok) {const error = Error(data?.error || res.statusText); error.status = res.status; error.code = data?.code; error.environments = data?.environments; throw error;}
    return data;
  }
  function toast(message, error) {
    const box = $('#toast'); box.textContent = message; box.className = 'show' + (error ? ' err' : '');
    clearTimeout(toast.timer); toast.timer = setTimeout(() => {box.className = '';}, 3600);
  }
  function log(line) {const body = $('#log-body'); body.textContent += line + '\n'; body.scrollTop = body.scrollHeight;}

  const NONE = Object.freeze(Object.create(null));
  const capabilityInfo = id => (page().tree.capabilities || NONE)[id];
  const levelKey = (capability, level) => [capability, level.ref, level.node, level.variant || 0].join('|');
  const levelEntry = (tree, ref) => (tree.levels || NONE)[ref];
  const levelTitle = (tree, ref) => {const entry = levelEntry(tree, ref); return (entry && entry.meta && entry.meta.title) || ref.slice(0, 8);};
  function levelOffers(tree) {
    const offers = new Map(), caps = tree.capabilities || NONE;
    const add = (capability, ref, level) => {
      const variant = level.variant || 0, key = levelKey(capability, {ref, node: level.node, variant});
      if (caps[capability] && levelEntry(tree, ref) && !offers.has(key)) offers.set(key, {key, capability, ref, node: level.node, variant, budget: level.budget, name: level.name});
    };
    for (const [ref, entry] of Object.entries(tree.levels || NONE)) for (const offer of (entry.meta && entry.meta.provides) || []) add(offer.capability, ref, offer);
    for (const node of tree.nodes) if (node.kind === 'capability' && node.level) add(node.capability, node.level.ref, node.level);
    return [...offers.values()];
  }
  const offerName = (tree, offer) => offer.name || levelTitle(tree, offer.ref) + ' · ' + offer.node + (offer.variant ? ' · v' + offer.variant : '');
  const benchLabel = id => Object.hasOwn(page().tree.benchLabels || NONE, id) ? page().tree.benchLabels[id] : id;
  const benchNames = () => {
    const names = new Set([...(page().draftBenches || []), ...Object.keys(page().tree.benchLabels || {})]);
    for (const node of page().tree.nodes) if (node.kind === 'bench') names.add(node.bench);
    return [...names];
  };

  function addPage(tree, view, arrange) {
    if (!tree.capabilities) tree.capabilities = {};
    if (!tree.levels) tree.levels = {};
    state.pages.push({tree, view: view || {x: 40, y: 30, k: 0.8}, draftBenches: []});
    state.active = state.pages.length - 1;
    state.selected.clear(); state.status = {};
    renderAll();
    if (arrange) requestAnimationFrame(() => {
      if (page().tree !== tree) return;
      arrangeTree(tree, n => {const c = document.querySelector('.node[data-id="' + n.id + '"]'); return c ? c.offsetHeight : 0;}, layoutViewport());
      renderGraph(); fitView();
    });
    else if (!view) setTimeout(() => {if (page().tree === tree) fitView();}, 0);
  }
  function closePage(index) {
    if (editingLocked(state.pages[index]) || editGesture) {toast(t('editLocked'), true); return;}
    if (state.run?.page === state.pages[index]) forgetRun(state.run.id);
    state.pages.splice(index, 1);
    if (index < state.active) state.active--;
    if (!state.pages.length) state.pages.push({tree: emptyTree(t('untitled')), view: {x: 40, y: 30, k: 0.8}});
    state.active = Math.max(0, Math.min(state.active, state.pages.length - 1));
    state.selected.clear();
    renderAll();
  }

  function renderThemeButton() {
    const label = t(globalThis.TrinityTheme.get() === 'dark' ? 'switchToLight' : 'switchToDark');
    $('#toggle-theme').title = label;
    $('#toggle-theme').setAttribute('aria-label', label);
  }
  function renderI18n() {
    document.documentElement.lang = getLang() === 'zh' ? 'zh' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(node => {node.textContent = t(node.dataset.i18n);});
    $('#lang').textContent = t('language');
    renderThemeButton();
    $('#part-search').placeholder = t('search');
    $('#describe-text').placeholder = t('describePlaceholder');
    $('#hint').textContent = t('deleteHint');
    explorer.localize();
  }
  function renderTabs() {
    const box = $('#tabs'); box.replaceChildren();
    state.pages.forEach((p, index) => {
      const tab = el('div', 'tab' + (index === state.active ? ' active' : ''));
      tab.append(el('span', '', p.tree.name));
      const close = el('span', 'x', '×');
      close.onclick = event => {event.stopPropagation(); if (editingLocked(p) || editGesture) {toast(t('editLocked'), true); return;} if (confirm(t('confirmClose'))) closePage(index);};
      tab.append(close);
      tab.onclick = () => {state.active = index; state.selected.clear(); renderAll();};
      box.append(tab);
    });
    const add = el('div', 'tab add', '+'); add.title = t('newPage'); add.onclick = () => addPage(emptyTree(t('untitled')));
    box.append(add);
  }

  function renderParts() {
    const tree = page().tree, caps = tree.capabilities || NONE, box = $('#parts'), query = $('#part-search').value.trim().toLowerCase();
    box.replaceChildren();
    const locked = editingLocked(page()) || editGesture;
    const matches = text => !query || text.toLowerCase().includes(query);
    const part = (kind, id, label, chip, title, count) => {
      const item = el('div', 'part ' + (kind === 'bench' ? 'bench' : kind === 'capability' ? 'category' : 'capability'));
      item.draggable = kind !== 'capability'; item.dataset.kind = kind; item.dataset.partId = id; item.title = title;
      item.append(el('span', 'uses', '×' + count));
      if (chip) item.append(el('span', 'id', chip));
      item.append(el('span', 'name', label));
      item.oncontextmenu = event => {event.preventDefault(); event.stopPropagation(); partMenu(event, kind, id);};
      if (kind !== 'capability') {
        item.ondragstart = event => {if (locked) {event.preventDefault(); return;} event.dataTransfer.setData('text/plain', kind + '\u0001' + id); event.dataTransfer.effectAllowed = 'copy';};
        item.ondblclick = () => {const v = page().view; placePart(kind, id, [(220 - v.x) / v.k, (140 - v.y) / v.k], null);};
      }
      box.append(item);
    };
    const section = (label, button, onclick) => {
      const head = el('div', 'group-label row-label'), add = el('button', 'mini', button); add.disabled = Boolean(locked); add.onclick = onclick;
      head.append(el('span', '', label), add); box.append(head);
    };
    const nothing = text => box.append(el('p', 'muted none', query ? t('noMatch') : text));
    section(t('capabilities'), t('addCapability'), () => openPartEditor('new-capability'));
    const categories = Object.entries(caps).filter(([id, cap]) => matches(id + ' ' + cap.name));
    for (const [id, cap] of categories) part('capability', id, cap.name, id, cap.definition || cap.name, tree.nodes.filter(n => n.kind === 'capability' && n.capability === id).length);
    if (!categories.length) nothing(t('noCapabilities'));
    section(t('levelLibrary'), t('describeNode'), openDescribe);
    const offers = levelOffers(tree).filter(o => matches(o.capability + ' ' + caps[o.capability].name + ' ' + offerName(tree, o) + ' ' + o.node));
    for (const o of offers) part('level', o.key, offerName(tree, o), caps[o.capability].name, offerName(tree, o) + '\n' + caps[o.capability].name,
      tree.nodes.filter(n => n.kind === 'capability' && n.level && levelKey(n.capability, n.level) === o.key).length);
    if (!offers.length) nothing(t('noLibraryLevels'));
    section(t('benches'), t('addBench'), () => {
      if (editingLocked(page()) || editGesture) return;
      const name = (prompt(t('benchName')) || '').trim();
      if (!name) return;
      if (!validBenchName(name)) {toast(t('invalidPartName'), true); return;}
      if (benchNames().some(id => id === name || benchLabel(id) === name)) {toast(t('duplicatePartName'), true); return;}
      edit(() => Object.defineProperty(tree.benchLabels ||= {}, name, {value: name, writable: true, enumerable: true, configurable: true})); renderParts();
    });
    const names = benchNames().filter(id => matches(id + ' ' + benchLabel(id))).sort((a, b) => benchLabel(a).localeCompare(benchLabel(b)));
    for (const id of names) part('bench', id, benchLabel(id), null, benchLabel(id), tree.nodes.filter(n => n.kind === 'bench' && n.bench === id).length);
    if (!names.length) nothing(t('noBenches'));
  }
  function partMenu(event, kind, id) {
    const owner = page(), tree = owner.tree, menu = $('#ctx'); menu.replaceChildren();
    const offer = kind === 'level' ? levelOffers(tree).find(o => o.key === id) : null;
    const item = (label, mode) => {
      const button = el('button', '', t(label)); button.disabled = editingLocked(owner) || Boolean(editGesture);
      button.onclick = () => {menu.classList.remove('open'); if (page() === owner && owner.tree === tree) openPartEditor(mode, offer?.capability || id, offer);};
      menu.append(button);
    };
    item(kind === 'level' ? 'renameLevel' : kind === 'bench' ? 'renameBench' : 'renameCapability', kind);
    if (offer) item('reassignLevel', 'category');
    item(kind === 'level' ? 'deleteLevel' : kind === 'bench' ? 'deleteBench' : 'deleteCapability', 'remove-' + kind);
    menu.classList.add('open');
    menu.style.left = Math.max(0, Math.min(event.clientX, innerWidth - menu.offsetWidth - 8)) + 'px';
    menu.style.top = Math.max(0, Math.min(event.clientY, innerHeight - menu.offsetHeight - 8)) + 'px';
  }
  function ensureOffer(tree, offer) {
    const entry = tree.levels[offer.ref]; entry.meta ||= {}; entry.meta.provides ||= [];
    let found = entry.meta.provides.find(o => o.capability === offer.capability && o.node === offer.node && (o.variant || 0) === offer.variant);
    if (!found) {found = {capability: offer.capability, node: offer.node, variant: offer.variant, ...(offer.budget ? {budget: offer.budget} : {})}; entry.meta.provides.push(found);}
    return found;
  }
  function moveOffer(tree, offer, target) {
    const moved = ensureOffer(tree, offer), entry = tree.levels[offer.ref];
    entry.meta.provides = entry.meta.provides.filter(o => o !== moved);
    if (!entry.meta.provides.some(o => o.capability === target && o.node === offer.node && (o.variant || 0) === offer.variant)) entry.meta.provides.push({...moved, capability: target});
    for (const node of tree.nodes) if (node.kind === 'capability' && node.level && levelKey(node.capability, node.level) === offer.key) node.capability = target;
  }
  function removeInstances(tree, ids) {
    for (const link of tree.links) if (ids.has(link.from)) {
      const bench = tree.nodes.find(n => n.id === link.to && n.kind === 'bench');
      if (bench) {Object.defineProperty(tree.benchLabels ||= {}, bench.bench, {value: benchLabel(bench.bench), writable: true, enumerable: true, configurable: true}); ids.add(bench.id);}
    }
    tree.nodes = tree.nodes.filter(n => !ids.has(n.id)); tree.links = tree.links.filter(l => !ids.has(l.from) && !ids.has(l.to));
    state.selected.clear(); state.status = {};
  }
  function openPartEditor(mode, id, offer) {
    const owner = page(), tree = owner.tree, dialog = $('#part-editor');
    if (editingLocked(owner) || editGesture) return;
    const adding = mode === 'new-capability', removing = mode.startsWith('remove-');
    const usedCategory = mode === 'remove-capability' && (tree.nodes.some(n => n.kind === 'capability' && n.capability === id) || levelOffers(tree).some(o => o.capability === id));
    const category = mode === 'category' || usedCategory, naming = !removing && !category;
    const name = $('#part-name'), select = $('#part-category'), error = $('#part-edit-error');
    const title = adding ? 'addCapability' : mode === 'category' ? 'reassignLevel' : mode === 'level' ? 'renameLevel' : mode === 'bench' ? 'renameBench' : mode === 'capability' ? 'renameCapability' : mode === 'remove-level' ? 'deleteLevel' : mode === 'remove-bench' ? 'deleteBench' : 'deleteCapability';
    $('#part-editor-title').textContent = t(title);
    $('#part-editor-hint').textContent = t(usedCategory ? 'deleteCategoryMoveHint' : removing ? (mode === 'remove-level' ? 'deleteLevelHint' : mode === 'remove-bench' ? 'deleteBenchHint' : 'deleteCategoryHint') : adding ? 'addCategoryHint' : category ? 'reassignLevelHint' : 'renamePartHint');
    $('#part-name-wrap').hidden = !naming; name.required = naming; name.disabled = !naming;
    $('#part-category-wrap').hidden = !category; select.required = category; select.disabled = !category;
    $('#part-edit-form button[type="submit"]').textContent = t(removing ? 'remove' : 'applyPartEdit');
    name.value = adding ? '' : mode === 'bench' ? benchLabel(id) : mode === 'level' ? offerName(tree, offer) : tree.capabilities[id]?.name || '';
    select.replaceChildren();
    for (const [key, cap] of Object.entries(tree.capabilities)) {
      if (usedCategory && key === id) continue;
      const option = el('option', '', cap.name + ' (' + key + ')'); option.value = key; select.append(option);
    }
    if (!usedCategory) select.value = id;
    error.textContent = usedCategory && !select.options.length ? t('needCategoryBeforeDelete') : '';
    $('#part-edit-cancel').onclick = () => dialog.close();
    $('#part-edit-form').onsubmit = event => {
      event.preventDefault();
      if (page() !== owner || owner.tree !== tree || editingLocked(owner) || editGesture) {error.textContent = t('editLocked'); return;}
      const value = category ? select.value : name.value.trim();
      if (naming && !validBenchName(value)) {error.textContent = t('invalidPartName'); return;}
      if (category && (!Object.hasOwn(tree.capabilities, value) || (usedCategory && value === id))) {error.textContent = t('needCategoryBeforeDelete'); return;}
      if (offer && !levelOffers(tree).some(o => o.key === offer.key)) {error.textContent = t('invalid'); return;}
      const duplicate = mode === 'bench' ? benchNames().some(key => key !== id && benchLabel(key) === value)
        : (mode === 'capability' || adding) && Object.entries(tree.capabilities).some(([key, cap]) => key !== id && cap.name === value);
      if (duplicate) {error.textContent = t('duplicatePartName'); return;}
      edit(() => {
        if (adding) {
          let key = 'cap_' + value.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 12);
          if (key === 'cap_' || Object.hasOwn(tree.capabilities, key)) do {key = uid('cap');} while (Object.hasOwn(tree.capabilities, key));
          tree.capabilities[key] = {id: key, name: value, definition: value};
        } else if (mode === 'bench') Object.defineProperty(tree.benchLabels ||= {}, id, {value, writable: true, enumerable: true, configurable: true});
        else if (mode === 'capability') tree.capabilities[id].name = value;
        else if (mode === 'level') ensureOffer(tree, offer).name = value;
        else if (mode === 'category' && value !== id) moveOffer(tree, offer, value);
        else if (mode === 'remove-capability') {
          if (usedCategory) {
            for (const o of levelOffers(tree).filter(o => o.capability === id)) moveOffer(tree, o, value);
            for (const node of tree.nodes) if (node.kind === 'capability' && node.capability === id) node.capability = value;
          }
          delete tree.capabilities[id];
        } else if (mode === 'remove-bench') {
          removeInstances(tree, new Set(tree.nodes.filter(n => n.kind === 'bench' && n.bench === id).map(n => n.id)));
          owner.draftBenches = (owner.draftBenches || []).filter(n => n !== id); if (tree.benchLabels) delete tree.benchLabels[id];
        } else if (mode === 'remove-level') {
          const entry = tree.levels[offer.ref];
          if (entry.meta?.provides) entry.meta.provides = entry.meta.provides.filter(o => !(o.capability === id && o.node === offer.node && (o.variant || 0) === offer.variant));
          removeInstances(tree, new Set(tree.nodes.filter(n => n.kind === 'capability' && n.level && levelKey(n.capability, n.level) === offer.key).map(n => n.id)));
          if (!entry.meta?.provides?.length && !tree.nodes.some(n => n.level?.ref === offer.ref)) delete tree.levels[offer.ref];
        }
      });
      dialog.close(); renderAll();
    };
    dialog.showModal();
    if (category) select.focus(); else if (naming) {name.focus(); name.select();} else $('#part-edit-cancel').focus();
  }
  const freshPreview = level => ({source: 'level', collapsed: false, round: 1, frame: 1,
    rounds: [{round: 1, phase: null, success: null, tape: {variant: level.variant || 0, actions: []}}]});
  function placePart(kind, id, pos, target) {
    const tree = page().tree;
    let node = null;
    if (kind === 'level') {
      const offer = levelOffers(tree).find(o => o.key === id);
      if (!offer) return;
      const level = {ref: offer.ref, node: offer.node, variant: offer.variant};
      if (Number.isInteger(offer.budget) && offer.budget > 0) level.budget = offer.budget;
      node = {id: uid('n'), kind: 'capability', capability: offer.capability, pos: pos.map(Math.round), level, preview: freshPreview(level)};
    }
    if (node) {
      tree.nodes.push(node); state.selected = new Set([node.id]);
      if (target && target.kind === 'capability') tree.links.push({id: uid('l'), from: target.id, to: node.id});
    } else {
      if (kind !== 'bench' || !validBenchName(id)) return;
      const owner = target && target.kind === 'capability' ? target : null;
      if (owner && tree.links.some(l => l.from === owner.id && tree.nodes.some(n => n.id === l.to && n.bench === id))) {toast('"' + id + '" is already attached here', true); return;}
      let at = pos;
      if (owner) {
        const siblings = tree.links.filter(l => l.from === owner.id).map(l => tree.nodes.find(n => n.id === l.to)).filter(n => n && n.kind === 'bench');
        at = siblings.length ? [siblings[0].pos[0], Math.max(...siblings.map(n => n.pos[1] + (document.querySelector('.node[data-id="' + n.id + '"]')?.offsetHeight || 32))) + BENCH_GAP] : [owner.pos[0] + WIDTH.capability + 60, owner.pos[1]];
      }
      const bench = {id: uid('b'), kind: 'bench', bench: id, pos: at.map(Math.round)};
      tree.nodes.push(bench);
      if (owner) tree.links.push({id: uid('l'), from: owner.id, to: bench.id});
      state.selected = new Set([bench.id]);
    }
    renderGraph(); renderParts();
  }

  function renderGraph() {
    $('#ctx').classList.remove('open');
    const {tree} = page();
    document.body.classList.toggle('node-detail-view', !!page().detailView);
    renderTransform();
    const errors = validateTree(tree);
    const info = analyzeTree(tree);
    const box = $('#nodes'); box.replaceChildren();
    for (const node of tree.nodes) box.append(node.kind === 'bench' ? renderBench(node) : renderCapability(node, info));
    box.append(renderOrigin());
    renderLinks();
    explorer.render();
    renderStage();
    $('#stats').textContent = tree.nodes.length + ' ' + t('nodes') + ' · ' + tree.links.length + ' ' + t('links') + (errors.length ? ' · ⚠ ' + errors[0] : '');
  }
  function showStage(id) {
    const p = page(); if (!p || !p.tree.nodes.some(n => n.id === id)) return;
    if (!p.detailView) {
      p.treeView = {...p.view};
      p.treeFocusId = p.explorer?.focusId || null;
      p.detailView = true;
      p.stageId = id;
      renderGraph(); fitView();
      $('#stage-back').focus({preventScroll: true});
    } else {p.stageId = id; renderStage();}
  }
  function closeStage() {
    const p = page(); if (!p?.detailView) return;
    const id = p.stageId;
    p.detailView = false;
    if (p.treeView) Object.assign(p.view, p.treeView);
    explorer.close();
    explorer.focus(p.treeFocusId);
    renderGraph();
    [...document.querySelectorAll('#nodes .node')].find(card => card.dataset.id === id)?.focus({preventScroll: true});
  }
  function renderStage() {
    const p = page(), body = $('#stage-body'), picker = $('#stage-select');
    $('#node-stage').hidden = !p.detailView;
    $('#stage-back').onclick = closeStage;
    if (!p.detailView) {body.replaceChildren(); return;}
    const node = p.tree.nodes.find(n => n.id === p.stageId) || p.tree.nodes.find(n => n.kind === 'capability' && n.preview) || p.tree.nodes[0];
    p.stageId = node?.id || null;
    const info = analyzeTree(p.tree), label = n => n.kind === 'bench' ? benchLabel(n.bench) : (n.level ? levelTitle(p.tree, n.level.ref) : capabilityInfo(n.capability)?.name || n.capability) + ' · ' + info.path(n.id);
    picker.replaceChildren();
    for (const n of p.tree.nodes) {const option = el('option', '', label(n)); option.value = n.id; option.selected = n === node; picker.append(option);}
    picker.disabled = !node; picker.onchange = () => explorer.focus(picker.value);
    $('#stage-details').disabled = !node; $('#stage-details').onclick = () => {if (node) explorer.open(node.id);};
    document.querySelectorAll('#nodes .node').forEach(card => card.classList.toggle('stage-selected', card.dataset.id === node?.id));
    body.replaceChildren(); $('#node-stage').dataset.nodeId = node?.id || '';
    $('#stage-title').textContent = node ? label(node) : t('stageHeading');
    $('#stage-meta').textContent = node ? node.id + ' · ' + t('layer') + ' ' + info.depth(node.id) + (node.kind === 'capability' ? ' · ' + info.benches(node.id).length + ' ' + t('benchCount') : '') : '';
    if (!node) {body.append(el('p', 'stage-empty muted', t('stageEmpty'))); return;}
    if (node.kind === 'bench') {
      body.append(el('p', 'stage-empty muted', t('stageBenchHint')));
      const owner = info.parent.get(node.id);
      if (owner) {const button = el('button', '', t('stageOwner')); button.onclick = () => explorer.focus(owner); body.append(button);}
      return;
    }
    const preview = renderPreview(node, true);
    body.append(preview || el('p', 'stage-empty muted', t('stageNoPreview')), renderModules(node));
  }
  function baseCard(node, cls) {
    const status = state.status[node.id];
    const card = el('div', 'node ' + cls + (state.selected.has(node.id) ? ' selected' : '') + (status ? ' ' + status.state : ''));
    card.dataset.id = node.id; card.style.left = node.pos[0] + 'px'; card.style.top = node.pos[1] + 'px';
    card.onmousedown = event => {if (event.button === 0 && !event.target.closest('.slot,.title,input,select,button,textarea,a,.module-content')) select(node.id, event.shiftKey);};
    card.oncontextmenu = event => {event.preventDefault(); nodeMenu(event, node);};
    card.onclick = event => {if (event.target.closest('.title') && !event.shiftKey && !event.ctrlKey && !event.metaKey) explorer.focus(node.id);};
    card.tabIndex = 0;
    card.setAttribute('aria-label', (node.kind === 'bench' ? benchLabel(node.bench) : node.capability) + ' · ' + t('nodeDetails'));
    card.ondblclick = event => {if (event.target.closest('input,select,button,textarea,a,.module-content')) return; event.stopPropagation(); showStage(node.id);};
    card.onkeydown = event => {if (event.target !== card) return; if (event.key === 'Enter') {event.preventDefault();showStage(node.id);} if (event.key === ' ') {event.preventDefault();select(node.id,false);}};
    return card;
  }
  function renderCapability(node, info) {
    const cap = capabilityInfo(node.capability), status = state.status[node.id], card = baseCard(node, 'cap-node');
    const title = el('div', 'title');
    title.append(el('span', 'cap', node.capability), el('span', 'label', node.level ? offerName(page().tree, levelOffers(page().tree).find(o => o.key === levelKey(node.capability, node.level))) : cap ? cap.name : '?'));
    if (status && status.label) title.append(el('span', 'state', status.label));
    const body = el('div', 'body');
    const row = (label, value, cls) => {const r = el('div', 'row'); r.append(el('span', '', label), el('b', cls || '', value)); body.append(r);};
    row(t('path'), info.path(node.id) || node.capability);
    row(t('layer'), String(info.depth(node.id)));
    row(t('benchCount'), String(info.benches(node.id).length));
    const inSlot = el('div', 'slot in'), outSlot = el('div', 'slot out');
    inSlot.onmousedown = event => startLink(event, node.id, 'in');
    outSlot.onmousedown = event => startLink(event, node.id, 'out');
    card.append(title, body, inSlot, outSlot);
    const preview = renderPreview(node);
    const previews = el('div', 'node-previews');
    if (preview) previews.append(preview);
    previews.append(renderModules(node));
    card.append(previews);
    if (status && status.layer) card.append(el('div', 'layer-tag', t('layer') + ' ' + status.layer));
    title.onmousedown = event => {if (event.button === 0) card.focus({preventScroll: true}); startDrag(event, node);};
    card.addEventListener('dragover', event => {event.preventDefault(); card.classList.add('drop');});
    card.addEventListener('dragleave', () => card.classList.remove('drop'));
    card.addEventListener('drop', event => {
      event.preventDefault(); event.stopPropagation(); card.classList.remove('drop');
      const [kind, id] = (event.dataTransfer.getData('text/plain') || '').split('\u0001');
      if (['bench', 'level'].includes(kind)) {const p = toWorld(event); placePart(kind, id, [p[0] + 40, p[1] + 60], node);}
    });
    return card;
  }
  function renderBench(node) {
    const status = state.status[node.id], card = baseCard(node, 'bench-node');
    const title = el('div', 'title');
    title.append(el('span', 'leaf', '◆'), el('span', 'label', benchLabel(node.bench)));
    if (status && status.label) title.append(el('span', 'state', status.label));
    const inSlot = el('div', 'slot in');
    inSlot.onmousedown = event => startLink(event, node.id, 'in');
    title.onmousedown = event => {if (event.button === 0) card.focus({preventScroll: true}); startDrag(event, node);};
    card.title = benchLabel(node.bench);
    card.append(title, inSlot);
    return card;
  }
  const readableName = value => String(value || '').replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[_-]+/g, ' ').replace(/^./, c => c.toUpperCase());
  function renderModules(node) {
    const box = el('section', 'module-preview');
    box.setAttribute('aria-label', t('evolvedModules'));
    box.onmousedown = event => event.stopPropagation();
    box.addEventListener('wheel', event => event.stopPropagation(), {passive: true});
    const modules = node.modules || [], head = el('div', 'module-head');
    head.append(el('span', '', t('evolvedModules')), el('span', 'module-count', String(modules.length)));
    const content = el('div', 'module-content');
    content.tabIndex = 0;
    content.setAttribute('aria-label', modules.length ? t('evolvedModules') : t('emptyModules'));
    for (const module of modules) {
      const item = el('article', 'module-summary');
      item.append(el('h4', '', readableName(module.name || module.moduleId) || t('moduleTitle')));
      const description = [module.description, module.purpose, module.summary, module.prompt].find(v => typeof v === 'string' && v.trim());
      item.append(el('p', '', description || t('moduleNoDescription')));
      const required = module.interface?.required;
      if (Array.isArray(required) && required.some(v => typeof v === 'string')) item.append(el('p', 'module-inputs', t('moduleInputs') + required.filter(v => typeof v === 'string').map(readableName).join(', ') + '.'));
      content.append(item);
    }
    box.append(head, content);
    return box;
  }
  function originInfo(tree) {
    const attached = new Set(tree.links.map(link => link.to));
    const roots = tree.nodes.filter(node => node.kind === 'capability' && !attached.has(node.id));
    const centers = roots.map(node => node.pos[1] + SLOT_Y.capability);
    return {roots, pos: roots.length ? [Math.min(...roots.map(node => node.pos[0])) - 168, (Math.min(...centers) + Math.max(...centers)) / 2 - 32] : [60, 40]};
  }
  function renderOrigin() {
    const {pos} = originInfo(page().tree), card = el('div', 'origin-node');
    card.append(el('strong', '', 'H0'), el('span', '', t('sharedStart')));
    card.style.left = pos[0] + 'px'; card.style.top = pos[1] + 'px';
    card.onmousedown = event => event.stopPropagation();
    card.oncontextmenu = event => event.preventDefault();
    return card;
  }
  const runFrameUrl = (p, file) => '/api/frames/run/' + encodeURIComponent(p.runId) + '/' + encodeURIComponent(file);
  const renders = new Map(), wholeWanted = new WeakSet(), WHOLE_ROUNDS_KEPT = 24;
  function levelRender(tree, level, variant, actions) {
    const entry = levelEntry(tree, level.ref);
    if (!entry) return {status: 'error', error: t('noLevel'), frames: []};
    const key = level.ref + '|' + level.node + '|' + variant + '|' + JSON.stringify(actions);
    let job = renders.get(key);
    if (job && job.source === entry.source) {renders.delete(key); renders.set(key, job); return job;}
    job = {source: entry.source, status: 'loading', frames: [], whole: actions.length > 0};
    renders.set(key, job);
    const kept = [...renders].filter(([, j]) => j.whole && j.status !== 'loading');
    while (kept.length > WHOLE_ROUNDS_KEPT) renders.delete(kept.shift()[0]);
    request('POST', '/api/render', {source: entry.source, node: level.node, variant, actions})
      .then(out => {job.frames = out.frames.map(b => 'data:image/png;base64,' + b); job.status = 'ready';})
      .catch(error => {job.status = 'error'; job.error = error.message;})
      .finally(scheduleRender);
    return job;
  }
  function renderPreview(node, expanded = false) {
    const p = node.preview;
    if (!p || !Array.isArray(p.rounds) || !p.rounds.length) return null;
    const tree = page().tree, isLevel = p.source === 'level' && Boolean(node.level);
    const box = el('div', 'preview'); box.dataset.previewNode = node.id;
    box.onmousedown = event => event.stopPropagation();
    const head = el('div', 'ph');
    const label = p.label || (isLevel ? levelTitle(tree, node.level.ref) + ' · ' + node.level.node : p.source === 'run' ? t('live') : '');
    head.append(el('span', 'tw', p.collapsed && !expanded ? '▸' : '▾'), el('span', '', t('preview')), el('span', 'src', label));
    if (!expanded) head.onclick = () => {p.collapsed = !p.collapsed; renderGraph();};
    box.append(head);
    if (p.collapsed && !expanded) return box;
    const rounds = p.rounds, round = rounds.find(r => r.round === p.round) || rounds[0];
    p.round = round.round;
    let count, frameAt, waiting, wantWhole = () => false;
    if (isLevel) {
      const actions = round.tape.actions, variant = round.tape.variant;
      const opening = levelRender(tree, node.level, variant, []);
      const whole = () => (actions.length && (p.frame > 1 || wholeWanted.has(round)) ? levelRender(tree, node.level, variant, actions) : null);
      wantWhole = () => {if (!actions.length || wholeWanted.has(round)) return false; wholeWanted.add(round); whole(); return true;};
      const ready = whole();
      count = ready && ready.status === 'ready' ? ready.frames.length : actions.length + 1;
      frameAt = k => {
        const w = whole();
        if (w && w.status === 'ready') return w.frames[Math.min(k, w.frames.length) - 1];
        return k === 1 && opening.status === 'ready' ? opening.frames[0] : null;
      };
      const failed = [ready, opening].find(j => j && j.status === 'error');
      waiting = failed ? failed.error : state.offline ? t('noServer') : t('rendering');
      box.addEventListener('mouseenter', () => {if (wantWhole()) scheduleRender();});
    } else {
      count = round.frames.length;
      frameAt = k => (round.frames[k - 1] && !state.offline ? runFrameUrl(p, round.frames[k - 1]) : null);
      waiting = state.offline ? t('noServer') : t('noFrame');
    }
    p.frame = Math.max(1, Math.min(p.frame || 1, count || 1));
    const img = el('div', 'pimg');
    const image = el('img'); image.draggable = false;
    const empty = el('div', 'empty');
    image.onerror = () => {image.style.display = 'none'; empty.style.display = ''; empty.textContent = t('noFrame');};
    const show = () => {
      const src = frameAt(p.frame);
      if (src) {image.style.display = ''; empty.style.display = 'none'; if (image.getAttribute('src') !== src) image.src = src; image.alt = node.id + ' r' + p.round + ' f' + p.frame;}
      else {image.style.display = 'none'; empty.style.display = ''; empty.textContent = waiting;}
    };
    img.append(image, empty);
    show();
    const phase = (round.phase ? t(round.phase) : '') + (round.screening ? ' · ' + t('screening') : '');
    const badge = (phase + (round.success === true ? ' ✓' : round.success === false ? ' ✗' : '')).trim();
    if (badge) img.append(el('span', 'badge' + (round.success === true ? ' ok' : round.success === false ? ' no' : ''), badge));
    box.append(img);
    const controls = el('div', 'pc');
    const sel = el('select');
    for (const r of rounds) {
      const o = el('option', '', t('round').replace('{n}', r.round) + (r.phase ? ' · ' + t(r.phase) : ''));
      o.value = String(r.round); if (r.round === p.round) o.selected = true; sel.append(o);
    }
    sel.onchange = () => {p.round = Number(sel.value); p.frame = 1; p.follow = false; renderGraph();};
    const range = el('input'); range.type = 'range'; range.min = '1'; range.max = String(Math.max(1, count)); range.value = String(p.frame);
    const num = el('input'); num.type = 'number'; num.min = '1'; num.max = String(Math.max(1, count)); num.value = String(p.frame);
    const setFrame = v => {
      p.frame = Math.max(1, Math.min(count || 1, Number(v) || 1)); p.follow = false;
      range.value = String(p.frame); num.value = String(p.frame);
      if (wantWhole()) scheduleRender();
      for (const peer of document.querySelectorAll('.preview')) if (peer.dataset.previewNode === node.id) peer.refreshFrame?.();
    };
    box.refreshFrame = () => {range.value = String(p.frame); num.value = String(p.frame); show(); const dot = controls.querySelector('.live'); if (dot) dot.remove();};
    range.oninput = () => setFrame(range.value); num.onchange = () => setFrame(num.value);
    for (const input of [range, num, sel]) {
      input.onfocus = () => {editingPreview = true;};
      input.onblur = () => {editingPreview = false;};
    }
    controls.append(sel, range, num, el('span', '', '/' + count));
    if (p.source === 'run' && p.follow) controls.append(el('span', 'live', '●'));
    box.append(controls);
    box.addEventListener('wheel', event => event.stopPropagation(), {passive: true});
    return box;
  }
  function onFrame(event) {
    const p = state.run.page;
    for (const id of event.treeNodes || []) {
      const node = p.tree.nodes.find(n => n.id === id);
      if (!node) continue;
      if (!node.preview || node.preview.source !== 'run' || node.preview.runId !== state.run.id || node.preview.taskId !== event.taskId) {
        node.preview = {source: 'run', runId: state.run.id, taskId: event.taskId, label: t('live') + ' · ' + event.taskId,
          rounds: [], round: event.round, frame: 1, follow: true, collapsed: node.preview ? node.preview.collapsed : false};
      }
      const pv = node.preview;
      let round = pv.rounds.find(r => r.round === event.round);
      if (!round) {round = {round: event.round, phase: event.phase, frames: [], success: null}; pv.rounds.push(round); pv.rounds.sort((a, b) => a.round - b.round);}
      round.frames[event.frame - 1] = event.file;
      if (event.done) round.success = event.success === true;
      if (pv.follow !== false) {pv.round = event.round; pv.frame = event.frame; pv.follow = true;}
    }
  }

  const slotPos = (node, side) => [node.pos[0] + (side === 'out' ? WIDTH[node.kind] : 0), node.pos[1] + SLOT_Y[node.kind]];
  const curve = (a, b) => {const dx = Math.max(12, Math.abs(b[0] - a[0]) / 2); return 'M' + a[0] + ',' + a[1] + ' C' + (a[0] + dx) + ',' + a[1] + ' ' + (b[0] - dx) + ',' + b[1] + ' ' + b[0] + ',' + b[1];};
  function renderLinks(draft) {
    const {tree} = page(), svg = $('#links'), byId = new Map(tree.nodes.map(n => [n.id, n]));
    svg.replaceChildren();
    for (const link of tree.links) {
      const from = byId.get(link.from), to = byId.get(link.to);
      if (!from || !to) continue;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.dataset.from = from.id; path.dataset.to = to.id;
      path.setAttribute('d', curve(slotPos(from, 'out'), slotPos(to, 'in')));
      if (to.kind === 'bench') path.classList.add('bench-link');
      if (state.status[to.id] && state.status[to.id].state === 'running') path.classList.add('active');
      const remove = event => {event.preventDefault(); edit(() => {tree.links = tree.links.filter(l => l !== link); renderGraph();});};
      path.addEventListener('contextmenu', remove); path.addEventListener('dblclick', remove);
      svg.append(path);
    }
    const origin = originInfo(tree), card = $('#nodes .origin-node');
    if (card) {card.style.left = origin.pos[0] + 'px'; card.style.top = origin.pos[1] + 'px';}
    for (const node of origin.roots) {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', curve([origin.pos[0] + 140, origin.pos[1] + 32], slotPos(node, 'in')));
      path.dataset.to = node.id; path.classList.add('origin-link'); svg.append(path);
    }
    if (draft) {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', curve(draft[0], draft[1])); path.classList.add('draft'); svg.append(path);
    }
    explorer.refreshFocus();
  }
  function select(id, add) {
    if (!add) state.selected.clear();
    if (state.selected.has(id) && add) state.selected.delete(id); else state.selected.add(id);
    document.querySelectorAll('.node').forEach(card => card.classList.toggle('selected', state.selected.has(card.dataset.id)));
    explorer.focus(!add && state.selected.size === 1 ? id : null);
  }
  const toWorld = event => {const rect = $('#canvas').getBoundingClientRect(), v = page().view; return [(event.clientX - rect.left - v.x) / v.k, (event.clientY - rect.top - v.y) / v.k];};

  function startDrag(event, node) {
    if (event.button !== 0 || editingLocked(page()) || editGesture) return;
    event.stopPropagation(); event.preventDefault();
    if (event.shiftKey && state.selected.has(node.id)) {select(node.id, true); return;}
    if (!state.selected.has(node.id)) select(node.id, event.shiftKey);
    else if (!event.shiftKey && state.selected.size === 1) explorer.focus(node.id);
    const p = page(), before = snapshot(p), tree = p.tree, moving = new Set(state.selected);
    editGesture = {page: p}; renderHistory();
    if (node.kind === 'capability' && !event.altKey) for (const link of tree.links) if (moving.has(link.from) && tree.nodes.some(n => n.id === link.to && n.kind === 'bench')) moving.add(link.to);
    const start = toWorld(event), origins = tree.nodes.filter(n => moving.has(n.id)).map(n => [n, n.pos.slice()]);
    const move = e => {
      if (page() !== p || !(e.buttons & 1)) {cancel(); return;}
      const now = toWorld(e), dx = now[0] - start[0], dy = now[1] - start[1];
      for (const [n, origin] of origins) {
        n.pos = [Math.round(origin[0] + dx), Math.round(origin[1] + dy)];
        const card = document.querySelector('.node[data-id="' + n.id + '"]');
        if (card) {card.style.left = n.pos[0] + 'px'; card.style.top = n.pos[1] + 'px';}
      }
      renderLinks();
    };
    const cancel = () => {removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', cancel); editGesture = false; Object.assign(p, JSON.parse(before)); if (page() === p) state.selected.clear(); renderAll();};
    const up = () => {if (page() !== p) {cancel(); return;} removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', cancel); editGesture = false; commitEdit(p, before);};
    editGesture.cancel = cancel;
    addEventListener('mousemove', move); addEventListener('mouseup', up); addEventListener('blur', cancel);
  }
  function startLink(event, nodeId, side) {
    if (event.button !== 0 || editingLocked(page()) || editGesture) return;
    event.stopPropagation(); event.preventDefault();
    const p = page(), before = snapshot(p), tree = p.tree;
    editGesture = {page: p}; renderHistory();
    let anchorId = nodeId, anchorSide = side;
    if (side === 'in') {
      const existing = tree.links.find(l => l.to === nodeId);
      if (existing) {tree.links = tree.links.filter(l => l !== existing); anchorId = existing.from; anchorSide = 'out'; renderGraph();}
    }
    const anchor = tree.nodes.find(n => n.id === anchorId);
    const move = e => {if (page() !== p || !(e.buttons & 1)) {cancel(); return;} const point = toWorld(e), a = slotPos(anchor, anchorSide); renderLinks(anchorSide === 'out' ? [a, point] : [point, a]);};
    const cancel = () => {removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', cancel); editGesture = false; Object.assign(p, JSON.parse(before)); if (page() === p) state.selected.clear(); renderAll();};
    const up = e => {
      if (page() !== p) {cancel(); return;}
      removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', cancel);
      const target = document.elementFromPoint(e.clientX, e.clientY);
      const card = target && target.closest('.node'), targetId = card && card.dataset.id;
      if (targetId && targetId !== anchorId) {
        const pair = anchorSide === 'out' ? [anchorId, targetId] : [targetId, anchorId];
        const next = Object.assign({}, tree, {links: tree.links.filter(l => l.to !== pair[1]).concat({id: uid('l'), from: pair[0], to: pair[1]})});
        const errors = validateTree(next).filter(m => !/is not attached to a capability/.test(m));
        if (errors.length) toast(errors[0], true); else tree.links = next.links;
      }
      editGesture = false; commitEdit(p, before); renderGraph();
    };
    editGesture.cancel = cancel;
    addEventListener('mousemove', move); addEventListener('mouseup', up); addEventListener('blur', cancel);
  }
  function nodeMenu(event, node) {
    const owner = page(), tree = owner.tree;
    const menu = $('#ctx'); menu.replaceChildren();
    const item = (label, fn) => {const b = el('button', '', label); b.onclick = () => {menu.classList.remove('open'); if (page() === owner && owner.tree === tree && tree.nodes.includes(node)) fn();}; menu.append(b);};
    const many = state.selected.has(node.id) && state.selected.size > 1;
    const kind = node.kind === 'bench' ? 'bench' : node.level ? 'level' : 'capability';
    const id = kind === 'bench' ? node.bench : kind === 'level' ? levelKey(node.capability, node.level) : node.capability;
    item(t('viewNodeDetails'), () => showStage(node.id));
    item(t('focusBranch'), () => explorer.focus(node.id));
    item(t('duplicate'), () => placePart(kind, id, [node.pos[0] + 30, node.pos[1] + 30], null));
    if (node.preview) item(node.preview.collapsed ? t('expandPreview') : t('collapsePreview'), () => {
      const targets = many ? page().tree.nodes.filter(n => state.selected.has(n.id) && n.preview) : [node];
      const to = !node.preview.collapsed;
      for (const n of targets) n.preview.collapsed = to;
      renderGraph();
    });
    if (many) item(t('arrange') + ' (' + state.selected.size + ')', arrangeNodes);
    item(many ? t('remove') + ' (' + state.selected.size + ')' : t('remove'), () => {if (!many) state.selected = new Set([node.id]); deleteSelection();});
    menu.style.left = event.clientX + 'px'; menu.style.top = event.clientY + 'px'; menu.classList.add('open');
  }
  function deleteSelection() {
    const tree = page().tree;
    tree.nodes = tree.nodes.filter(n => !state.selected.has(n.id));
    tree.links = tree.links.filter(l => !state.selected.has(l.from) && !state.selected.has(l.to));
    state.selected.clear(); renderGraph(); renderParts();
  }
  function layoutViewport() {
    const rect = $('#canvas').getBoundingClientRect(), log = $('#log').getBoundingClientRect();
    const bottom = log.width && log.top < rect.bottom ? Math.max(rect.top, log.top) : rect.bottom;
    return {width: Math.max(1, rect.width - 32), height: Math.max(1, bottom - rect.top - 64)};
  }
  function fitView() {
    const {tree, view} = page(), area = layoutViewport();
    if (!tree.nodes.length) {Object.assign(view, {x: 40, y: 30, k: 0.8}); renderGraph(); return;}
    const origin = originInfo(tree);
    const heights = new Map([...document.querySelectorAll('.node')].map(card => [card.dataset.id, card.offsetHeight]));
    const minX = Math.min(origin.pos[0], ...tree.nodes.map(n => n.pos[0]));
    const minY = Math.min(origin.pos[1], ...tree.nodes.map(n => n.pos[1]));
    const maxX = Math.max(origin.pos[0] + 140, ...tree.nodes.map(n => n.pos[0] + WIDTH[n.kind]));
    const maxY = Math.max(origin.pos[1] + 64, ...tree.nodes.map(n => n.pos[1] + (heights.get(n.id) || 170)));
    const k = Math.max(0.05, Math.min(1.2, area.width / (maxX - minX), area.height / (maxY - minY)));
    Object.assign(view, {k, x: 16 - minX * k + (area.width - (maxX - minX) * k) / 2, y: 16 - minY * k + (area.height - (maxY - minY) * k) / 2});
    renderGraph();
  }
  function renderTransform() {
    const v = page().view;
    $('#world').style.transform = 'translate(' + v.x + 'px,' + v.y + 'px) scale(' + v.k + ')';
    $('#canvas').style.backgroundSize = 24 * v.k + 'px ' + 24 * v.k + 'px';
    $('#canvas').style.backgroundPosition = v.x + 'px ' + v.y + 'px';
    explorer.queueMap();
  }
  let renderQueued = false, editingPreview = false;
  function scheduleRender() {
    if (renderQueued) return;
    renderQueued = true;
    const go = () => {
      if (editingPreview || $('#ctx').classList.contains('open')) {setTimeout(go, 400); return;}
      renderQueued = false; renderGraph();
    };
    requestAnimationFrame(go);
  }
  function renderAll() {if (editGesture && editGesture.page !== page()) {editGesture.cancel(); return;} if (viewGesture && viewGesture.page !== page()) viewGesture.cancel(); renderI18n(); renderEnvironments(); renderTabs(); renderParts(); renderGraph(); renderRunControls(); renderHistory();}

  function startMarquee(event) {
    event.preventDefault();
    const canvas = $('#canvas'), rect = canvas.getBoundingClientRect(), box = $('#marquee');
    const owner = page(), additive = event.shiftKey, before = new Set(state.selected);
    const x0 = event.clientX - rect.left, y0 = event.clientY - rect.top;
    const move = e => {
      if (page() !== owner || !(e.buttons & 1)) {cancel(); return;}
      const x1 = e.clientX - rect.left, y1 = e.clientY - rect.top;
      const l = Math.min(x0, x1), tp = Math.min(y0, y1), w = Math.abs(x1 - x0), h = Math.abs(y1 - y0);
      Object.assign(box.style, {display: 'block', left: l + 'px', top: tp + 'px', width: w + 'px', height: h + 'px'});
      state.selected = additive ? new Set(before) : new Set();
      for (const card of document.querySelectorAll('.node')) {
        const r = card.getBoundingClientRect();
        const cl = r.left - rect.left, ct = r.top - rect.top;
        if (cl < l + w && cl + r.width > l && ct < tp + h && ct + r.height > tp) state.selected.add(card.dataset.id);
      }
      document.querySelectorAll('.node').forEach(card => card.classList.toggle('selected', state.selected.has(card.dataset.id)));
    };
    const up = () => {box.style.display = 'none'; removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', cancel); viewGesture = null;};
    const cancel = () => {
      up();
      if (page() !== owner) return;
      state.selected = before;
      document.querySelectorAll('.node').forEach(card => card.classList.toggle('selected', state.selected.has(card.dataset.id)));
    };
    viewGesture = {page: owner, cancel};
    addEventListener('mousemove', move); addEventListener('mouseup', up); addEventListener('blur', cancel);
  }
  function arrangeNodes() {
    const tree = page().tree, k = page().view.k;
    const heights = new Map([...document.querySelectorAll('.node')].map(card => [card.dataset.id, card.getBoundingClientRect().height / k]));
    const scope = state.selected.size > 1 ? state.selected : null;
    if (scope) {
      const sub = {nodes: tree.nodes.filter(n => scope.has(n.id)), links: tree.links.filter(l => scope.has(l.from) && scope.has(l.to))};
      const minX = Math.min(...sub.nodes.map(n => n.pos[0])), minY = Math.min(...sub.nodes.map(n => n.pos[1]));
      arrangeTree(sub, n => heights.get(n.id));
      const ax = Math.min(...sub.nodes.map(n => n.pos[0])), ay = Math.min(...sub.nodes.map(n => n.pos[1]));
      for (const n of sub.nodes) n.pos = [n.pos[0] - ax + minX, n.pos[1] - ay + minY];
    } else arrangeTree(tree, n => heights.get(n.id), layoutViewport());
    renderGraph();
    if (!scope) fitView();
  }

  function setupCanvas() {
    const canvas = $('#canvas');
    document.addEventListener('mousedown', () => {if (editGesture) editGesture.cancel(); if (viewGesture) viewGesture.cancel();}, true);
    canvas.addEventListener('mousedown', event => {
      if (event.target.closest('.node,#minimap-shell,#branch-focus') || event.button !== 0) return;
      $('#ctx').classList.remove('open');
      if (event.ctrlKey || event.metaKey || event.shiftKey) {explorer.focus(null); startMarquee(event); return;}
      state.selected.clear(); document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
      const owner = page(), v = owner.view, start = [event.clientX - v.x, event.clientY - v.y];
      canvas.classList.add('panning');
      let moved = false; const down = [event.clientX, event.clientY];
      const move = e => {if (page() !== owner || !(e.buttons & 1)) {up(); return;} moved ||= Math.hypot(e.clientX-down[0],e.clientY-down[1]) > 4; v.x = e.clientX - start[0]; v.y = e.clientY - start[1]; renderTransform();};
      const up = () => {if (!moved && page() === owner) explorer.focus(null); canvas.classList.remove('panning'); removeEventListener('mousemove', move); removeEventListener('mouseup', up); removeEventListener('blur', up); viewGesture = null;};
      viewGesture = {page: owner, cancel: up};
      addEventListener('mousemove', move); addEventListener('mouseup', up); addEventListener('blur', up);
    });
    canvas.addEventListener('wheel', event => {
      if (event.target.closest('#minimap-shell,#branch-focus')) return;
      event.preventDefault();
      const v = page().view, rect = canvas.getBoundingClientRect(), mx = event.clientX - rect.left, my = event.clientY - rect.top;
      const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
      const k = Math.max(0.05, Math.min(2.5, v.k * Math.exp(-delta * 0.0015)));
      v.x = mx - (mx - v.x) * k / v.k; v.y = my - (my - v.y) * k / v.k; v.k = k; renderTransform();
    }, {passive: false});
    canvas.addEventListener('contextmenu', event => {
      if (event.target.closest('.node,#minimap-shell,#branch-focus') || event.target.closest('path')) return;
      event.preventDefault();
      const menu = $('#ctx'); menu.replaceChildren();
      const item = (label, fn) => {const b = el('button', '', label); b.onclick = () => {menu.classList.remove('open'); fn();}; menu.append(b);};
      item(t('arrange') + (state.selected.size > 1 ? ' (' + state.selected.size + ')' : ''), arrangeNodes);
      item(t('selectAll'), () => {state.selected = new Set(page().tree.nodes.map(n => n.id)); explorer.focus(null); renderGraph();});
      item(t('fit'), fitView);
      menu.style.left = event.clientX + 'px'; menu.style.top = event.clientY + 'px'; menu.classList.add('open');
    });
    canvas.addEventListener('dragover', event => {event.preventDefault(); event.dataTransfer.dropEffect = 'copy';});
    canvas.addEventListener('drop', event => {
      event.preventDefault();
      const [kind, id] = (event.dataTransfer.getData('text/plain') || '').split('\u0001');
      if (!['capability', 'bench', 'level'].includes(kind) || !id) return;
      const p = toWorld(event);
      placePart(kind, id, [p[0] - WIDTH[kind === 'bench' ? 'bench' : 'capability'] / 2, p[1] - 15], null);
    });
    document.addEventListener('dragover', event => event.preventDefault());
    document.addEventListener('drop', event => event.preventDefault());
    addEventListener('keydown', event => {
      if (event.target.closest('#node-inspector,#minimap-shell,#branch-focus') && event.key !== 'Escape') return;
      if (document.querySelector('dialog[open]') || event.target.closest('input,textarea,select,[contenteditable=true],.module-content')) return;
      if ((event.ctrlKey || event.metaKey) && ['z', 'y'].includes(event.key.toLowerCase())) {event.preventDefault(); restoreEdit(event.key.toLowerCase() === 'y' || event.shiftKey ? 'redo' : 'undo'); return;}
      if ((event.key === 'Delete' || event.key === 'Backspace') && state.selected.size) deleteSelection();
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
        event.preventDefault(); $('#ctx').classList.remove('open'); state.selected = new Set(page().tree.nodes.map(n => n.id)); explorer.focus(null);
        document.querySelectorAll('.node').forEach(card => card.classList.add('selected'));
      }
      if (event.key === 'Escape') {explorer.focus(null); explorer.close(); $('#ctx').classList.remove('open'); state.selected.clear(); document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));}
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {event.preventDefault(); downloadTree();}
    });
  }

  function projectFileName(name) {
    const clean = (name || 'tree').replace(/[\u0000-\u001f\u007f-\u009f<>:"/\\|?*]/gu, '_').replace(/\.{2,}/g, '_').replace(/^[. ]+|[. ]+$/g, '').slice(0, 60) || 'tree';
    return (/^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)/iu.test(clean) ? '_' : '') + clean + '.json';
  }
  function downloadTree() {
    const tree = page().tree, blob = new Blob([JSON.stringify(tree, null, 2) + '\n'], {type: 'application/json'});
    const a = el('a'); a.href = URL.createObjectURL(blob); a.download = projectFileName(tree.name);
    document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  function openTree(doc, label, arrange) {
    let tree = doc;
    if (doc && doc.schema === SEARCH_SCHEMA) {
      try {tree = importSearchTree(doc, label.replace(/\.json$/, ''));} catch (error) {toast(t('invalid') + ': ' + error.message, true); return false;}
    }
    const errors = validateTree(tree);
    if (errors.length) {toast(t('invalid') + ': ' + errors[0], true); return false;}
    addPage(JSON.parse(JSON.stringify(tree)), null, Boolean(arrange) || tree !== doc); toast(t('loaded') + ': ' + label);
    return true;
  }
  async function saveToServer() {
    const name = prompt(t('fileName'), projectFileName(page().tree.name));
    if (!name) return;
    try {await request('PUT', '/api/trees/' + encodeURIComponent(name.endsWith('.json') ? name : name + '.json'), page().tree); toast(t('saved') + ': ' + name);}
    catch (error) {toast(error.message, true);}
  }
  async function openFromServer() {
    let names = [];
    try {names = await request('GET', '/api/trees');} catch (error) {toast(error.message, true); return;}
    const list = $('#library-list'); list.replaceChildren();
    if (!names.length) list.append(el('p', 'muted', t('none')));
    for (const name of names) {
      const b = el('button', '', name);
      b.onclick = async event => {event.preventDefault(); $('#library').close(); try {openTree(await request('GET', '/api/trees/' + encodeURIComponent(name)), name);} catch (error) {toast(error.message, true);}};
      list.append(b);
    }
    $('#library').showModal();
  }

  function renderRunControls() {
    renderHistory();
    const running = state.recovering || (state.run && ['starting', 'running', 'stopping'].includes(state.run.status));
    const allowed = state.info && state.info.allowLocalEnvironment && !state.offline;
    $('#run').disabled = Boolean(running || !allowed);
    $('#run').title = allowed ? t('runHint') : t('readOnly');
    $('#run-more').disabled = Boolean(running || !allowed);
    document.querySelectorAll('[data-act="run"],[data-act="scratch"]').forEach(b => {b.disabled = Boolean(running || !allowed);});
    $('#run').classList.toggle('busy', Boolean(running));
    $('#stop').disabled = !state.run || !running || Boolean(state.run?.stopRequested);
    $('#stop').title = running ? t('stop') : t('stopIdle');
    $('#readonly-note').hidden = Boolean(allowed);
    $('#readonly-note').textContent = state.offline ? t('noServer') : t('readOnly');
    $('#run-state').textContent = state.run ? state.run.status + (state.run.connection === 'reconnecting' ? ' · ' + t('reconnecting') : '') + (state.run.layer ? ' · ' + t('layer') + ' ' + state.run.layer : '') : (state.offline ? t('noServer') : '');
  }
  async function startRun(mode) {
    if (editGesture || state.recovering) return;
    if (state.run && ['starting', 'running', 'stopping'].includes(state.run.status)) return;
    if (!modelSettingsReady()) return;
    if (mode === 'evolve') {
      const errors = validateTree(page().tree);
      if (errors.length || !page().tree.nodes.length) {toast(t('invalid') + ': ' + (errors[0] || 'empty'), true); return;}
    }
    if (mode === 'scratch') addPage(emptyTree('scratch-' + new Date().toISOString().slice(11, 19).replace(/:/g, '')));
    const runPage = page(), previousRun = state.run, requestId = crypto.randomUUID();
    state.run = {status: 'starting', page: runPage, requestId, stopRequested: false}; renderRunControls();
    state.status = {};
    for (const node of runPage.tree.nodes) state.status[node.id] = {state: 'queued', label: ''};
    renderGraph();
    rememberRun(null, requestId);
    try {
      const result = await request('POST', '/api/runs', {requestId, mode, tree: mode === 'evolve' ? runPage.tree : null, agent: 'model', apiKey: state.apiKey, connection: connectionPayload()});
      if (typeof result?.id !== 'string' || !/^[0-9a-f-]{36}$/.test(result.id)) throw Error('Invalid run start response');
      runPage.undo = []; runPage.redo = [];
      Object.assign(state.run, {id: result.id, status: state.run.stopRequested ? 'stopping' : 'running', layers: new Map(), lastEventId: 0, connection: 'connecting'});
      log('▶ ' + mode + ' · ' + result.out);
      renderRunControls();
      rememberRun(state.run.id); connectRun(state.run);
    } catch (error) {
      if (!error.status) {
        state.run.connection = 'reconnecting';
        if (await recoverRun(requestId, state.run.stopRequested)) return;
      }
      state.run = previousRun; runPage.status = {}; renderRunControls(); renderGraph();
      if (error.code === 'ENVIRONMENTS_NOT_READY') {state.environments = error.environments; renderEnvironments(); renderRunControls(); showEnvironments(); toast(t('envRunBlocked'), true);}
      else toast(error.message, true);
      if (previousRun?.id) rememberRun(previousRun.id); else forgetRun();
    }
  }
  function rememberRun(id, requestId) {
    try {sessionStorage.setItem('trinity-studio-run', JSON.stringify({id, requestId, stopRequested: Boolean(state.run?.stopRequested), server: state.info.token}));} catch {}
  }
  function forgetRun(id) {
    try {const saved = JSON.parse(sessionStorage.getItem('trinity-studio-run') || 'null'); if (!id || saved?.id === id) sessionStorage.removeItem('trinity-studio-run');} catch {}
  }
  function connectRun(run) {
    const source = new EventSource('/api/runs/' + run.id + '/events');
    source.onopen = () => {if (state.run === run) {run.connection = 'connected'; renderRunControls();} else source.close();};
    source.onmessage = message => {
      if (state.run !== run) {source.close(); return;}
      const id = Number(message.lastEventId);
      if (id && id <= run.lastEventId) return;
      onRunEvent(JSON.parse(message.data), source);
      if (id) run.lastEventId = id;
    };
    source.onerror = () => {
      if (state.run !== run || !['running', 'stopping'].includes(run.status)) {source.close(); return;}
      run.connection = 'reconnecting'; renderRunControls();
    };
    if (run.stopRequested) void requestRunStop(run);
  }
  async function recoverRun(requestId, stopRequested = false) {
    state.recovering = true; renderRunControls();
    let warned = false;
    try {
      for (;;) {
        try {
          let saved;
          try {saved = JSON.parse(sessionStorage.getItem('trinity-studio-run') || 'null');} catch {}
          let snapshot;
          if (requestId) {
            try {snapshot = await request('GET', '/api/runs/request/' + requestId);}
            catch (error) {if (error.status !== 404) throw error;}
          }
          if (!snapshot) snapshot = await request('GET', '/api/runs/active');
          if (!snapshot && !requestId) {
            if (saved?.server === state.info.token && /^[0-9a-f-]{36}$/.test(saved.id || saved.requestId)) {
              try {snapshot = await request('GET', saved.id ? '/api/runs/' + saved.id + '/snapshot' : '/api/runs/request/' + saved.requestId);}
              catch (error) {if (error.status === 404) forgetRun(saved.id); else throw error;}
            } else forgetRun();
          }
          if (!snapshot) return false;
          addPage(snapshot.tree);
          const p = page(); p.status = {};
          for (const node of p.tree.nodes) p.status[node.id] = {state: 'queued', label: ''};
          const savedStop = saved?.server === state.info.token && (saved.id === snapshot.id || (saved.requestId && saved.requestId === snapshot.requestId)) && saved.stopRequested;
          const pendingStop = requestId && requestId === snapshot.requestId && (stopRequested || (state.run?.requestId === requestId && state.run.stopRequested));
          const stopping = ['running', 'stopping'].includes(snapshot.status) && Boolean(pendingStop || savedStop);
          state.run = {id: snapshot.id, requestId: snapshot.requestId, status: stopping || snapshot.status === 'stopping' ? 'stopping' : 'running', page: p,
            layers: new Map(), lastEventId: 0, connection: 'connecting', stopRequested: stopping};
          rememberRun(snapshot.id); connectRun(state.run); renderAll(); return true;
        } catch (error) {
          if (!warned) {toast(error.message, true); warned = true;}
          if (error.status && error.status < 500) return false;
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
    } finally {state.recovering = false; renderRunControls();}
  }
  async function requestRunStop(run) {
    if (!run.id || run.stopInFlight) return;
    run.stopInFlight = true;
    try {
      await request('POST', '/api/runs/' + run.id + '/stop', {});
    } catch (error) {
      if (state.run === run && ['running', 'stopping'].includes(run.status)) {
        run.stopRequested = false; run.status = 'running'; rememberRun(run.id); toast(error.message, true);
      }
    } finally {run.stopInFlight = false; if (state.run === run) renderRunControls();}
  }
  function stopRun() {
    const run = state.run;
    if (!run || !['starting', 'running', 'stopping'].includes(run.status) || run.stopRequested) return;
    run.stopRequested = true; run.status = 'stopping'; rememberRun(run.id, run.requestId); renderRunControls();
    if (run.id) void requestRunStop(run);
  }
  const mark = (ids, value) => {const status = state.run.page.status ||= {}; for (const id of ids) status[id] = Object.assign({}, status[id], value);};
  function onRunEvent(event, source) {
    const run = state.run, p = run.page, onPage = page() === p;
    const status = p.status ||= {};
    const info = () => analyzeTree(p.tree);
    const benchLeaves = ids => {const a = info(); return ids.flatMap(id => a.children(id).filter(n => n.kind === 'bench').map(n => n.id));};
    switch (event.type) {
      case 'plan':
        for (const layer of event.layers) {
          run.layers.set(layer.layer, layer);
          for (const id of layer.nodes) {
            const total = layer.tasks.filter(x => x.treeNodes.includes(id)).length;
            mark([id], {state: 'queued', layer: layer.layer, done: 0, total, label: '0/' + total});
          }
          mark(benchLeaves(layer.nodes), {state: 'queued'});
        }
        for (const skip of event.skipped || []) {mark([skip.treeNode], {state: 'skipped', label: t('skipped')}); mark(benchLeaves([skip.treeNode]), {state: 'skipped'});}
        log('plan: ' + event.layers.map(l => t('layer') + ' ' + l.layer + ' [' + l.benches.length + ' bench, ' + l.tasks.length + ' ' + t('levels') + ']').join(' · '));
        if ((event.skipped || []).length) log('  ' + t('skipped') + ': ' + event.skipped.map(s => s.path).join(', '));
        break;
      case 'layer_started': {
        run.layer = event.layer;
        log('— ' + t('layer') + ' ' + event.layer); break;
      }
      case 'task_started': {
        const layer = run.layers.get(event.layer), task = layer && layer.tasks.find(x => x.id === event.taskId);
        for (const id of Object.keys(status)) if (status[id].state === 'running') status[id].state = status[id].done ? 'partial' : 'queued';
        const ids = task ? task.treeNodes : [];
        mark(ids, {state: 'running'}); mark(benchLeaves(ids), {state: 'running'});
        log('  ' + t('task') + ' ' + event.taskId); break;
      }
      case 'task_finished': {
        const layer = run.layers.get(event.layer), task = layer && layer.tasks.find(x => x.id === event.taskId);
        for (const id of task ? task.treeNodes : []) {
          const s = status[id] || (status[id] = {state: 'running'});
          s.done = (s.done || 0) + 1; s.label = s.done + '/' + (s.total || '?');
          if (s.total && s.done >= s.total) {s.state = 'done'; mark(benchLeaves([id]), {state: 'done'});}
        }
        log('  ✓ ' + event.taskId + ': ' + event.baseline + '/5 → ' + event.candidate + '/5 ' + t(event.comparison || 'unavailable') + ', ' + t(event.accepted ? 'accepted' : 'rejected'));
        break;
      }
      case 'node_modules':
        if (Array.isArray(event.modules) && event.modules.every(m => m && typeof m === 'object' && !Array.isArray(m))) {
          for (const id of event.treeNodes || []) {
            const node = p.tree.nodes.find(n => n.id === id);
            if (node) node.modules = JSON.parse(JSON.stringify(event.modules));
          }
        }
        break;
      case 'layer_finished': {
        const nodes = (run.layers.get(event.layer) || {nodes: []}).nodes;
        mark(nodes, {state: 'done'}); mark(benchLeaves(nodes), {state: 'done'});
        log('  ' + t('layerDone') + ' · modules ' + JSON.stringify(event.modules)); break;
      }
      case 'phase': log('phase: ' + event.phase); break;
      case 'bench_found': log('  ' + t('found') + ': ' + event.bench); break;
      case 'frame': onFrame(event); break;
      case 'tree_patch':
        if (event.op === 'replace_tree' && event.tree) {p.tree = event.tree; if(onPage)fitView();}
        if (event.op === 'add_capability' && event.capability) p.tree.capabilities[event.capability.id] = event.capability;
        if (event.op === 'add_level' && event.ref && event.level) p.tree.levels[event.ref] = event.level;
        if (event.op === 'add_node') {p.tree.nodes.push(event.node); status[event.node.id] = {state: 'queued', label: ''};}
        if (event.op === 'add_link') p.tree.links.push(event.link);
        if (onPage) {renderParts(); if (p.tree.nodes.length % 8 === 0) fitView();}
        break;
      case 'reserved': log('ⓘ ' + t('reserved') + ': ' + event.message); toast(t('reserved') + ': ' + event.message); break;
      case 'finished': log('■ ' + t('runDone') + ' · ' + event.out); toast(t('runDone')); if (onPage) fitView(); break;
      case 'failed':
        log('✗ ' + t('runFailed') + ': ' + event.message); toast(t('runFailed') + ': ' + event.message, true);
        for (const id of Object.keys(status)) if (status[id].state === 'running') status[id].state = 'failed';
        run.error = event.message;
        break;
      case 'log': log('  ' + String(event.message).trim()); break;
      case 'status':
        run.status = event.status; run.connection = 'closed'; source.close();
        if (event.status !== 'done') for (const id of Object.keys(status)) if (['running', 'queued'].includes(status[id].state)) status[id].state = event.status === 'failed' ? 'failed' : 'skipped';
        break;
    }
    explorer.record(event, run);
    if (onPage && event.type !== 'episode') scheduleRender();
    renderRunControls();
  }

  const connectionPayload = () => state.connection === 'relay' ? {type: 'relay', url: state.relayUrl} : {type: 'official'};
  function modelSettingsReady() {
    if (state.apiKey.length < 8) {toast(t('needKey'), true); $('#settings').showModal(); $('#api-key').focus(); return false;}
    if (state.connection === 'relay') {
      try {
        const url = new URL(state.relayUrl);
        if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || /[\s\\]/.test(state.relayUrl)) throw Error();
      } catch {toast(t('relayUrlInvalid'), true); $('#settings').showModal(); $('#relay-url').focus(); return false;}
    }
    return true;
  }

  function setupMenus() {
    const closeMenus = () => document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    const toggle = id => event => {event.stopPropagation(); const m = $(id), open = m.classList.contains('open'); closeMenus(); if (!open) m.classList.add('open');};
    document.querySelector('[data-menu="workflow"]').onclick = toggle('#menu-workflow');
    $('#run-more').onclick = toggle('#menu-run');
    addEventListener('click', closeMenus);
    const actions = {
      new: () => addPage(emptyTree(t('untitled'))),
      'open-file': () => $('#file-input').click(),
      'import-search': () => $('#file-input').click(),
      'save-file': downloadTree,
      'open-server': openFromServer,
      'save-server': saveToServer,
      rename: () => edit(() => {const name = prompt(t('rename'), page().tree.name); if (name && name.trim()) {page().tree.name = name.trim().slice(0, 120); renderTabs();}}),
      undo: () => restoreEdit('undo'),
      redo: () => restoreEdit('redo'),
      fit: fitView,
      arrange: arrangeNodes,
      run: () => startRun('evolve'),
      scratch: () => startRun('scratch'),
    };
    document.querySelectorAll('[data-act]').forEach(b => {b.onclick = () => {closeMenus(); actions[b.dataset.act]();};});
    $('#run').onclick = () => startRun(page().tree.nodes.length ? 'evolve' : 'scratch');
    $('#stop').onclick = stopRun;
    $('#file-input').onchange = async event => {
      const file = event.target.files[0]; event.target.value = '';
      if (!file) return;
      try {openTree(JSON.parse(await file.text()), file.name);} catch (error) {toast(t('invalid') + ': ' + error.message, true);}
    };
    $('#lang').onclick = () => {setLang(getLang() === 'en' ? 'zh' : 'en'); renderAll();};
    $('#toggle-theme').onclick = () => {
      globalThis.TrinityTheme.set(globalThis.TrinityTheme.get() === 'dark' ? 'light' : 'dark');
      renderThemeButton();
    };
    $('#open-environments').onclick = () => {showEnvironments(); if (!environmentBusy()) refreshEnvironments(true);};
    $('#environment-close').onclick = () => $('#environments-dialog').close();
    $('#environments-dialog').onclose = () => {environmentPromptPending = false;};
    $('#environment-check').onclick = () => refreshEnvironments(true);
    $('#environment-download').onclick = downloadEnvironments;
    $('#open-settings').onclick = () => $('#settings').showModal();
    $('#api-key').oninput = event => {state.apiKey = event.target.value.trim(); state.keys[state.connection] = state.apiKey;};
    $('#relay-url').oninput = event => {state.relayUrl = event.target.value.trim();};
    $('#connection').onchange = event => {
      state.connection = event.target.value;
      state.apiKey = state.keys[state.connection]; $('#api-key').value = state.apiKey;
      $('#api-key').placeholder = state.connection === 'relay' ? 'sk-…' : 'sk-ant-…';
      $('#relay-url-wrap').hidden = state.connection !== 'relay';
    };
    $('#toggle-sidebar').onclick = () => {$('#sidebar').classList.toggle('hidden'); $('#log').classList.toggle('wide');};
    $('#toggle-log').onclick = () => $('#log').classList.toggle('collapsed');
    $('#clear-log').onclick = () => {$('#log-body').textContent = '';};
    $('#part-search').oninput = renderParts;
    $('#describe-ask').onclick = askJudge;
    $('#describe-text').oninput = resetDesign;
    $('#design-json').oninput = () => {designRequestId++; $('#describe-status').textContent = '';};
    $('#create-node').onclick = createNodeFromDesign;
  }

  let designRequestId = 0;
  function resetDesign() {
    designRequestId++;
    $('#describe-status').textContent = '';
    $('#design-wrap').hidden = true; $('#create-node').hidden = true;
    $('#describe-ask').disabled = false;
  }
  function openDescribe() {
    resetDesign();
    $('#describe').showModal();
  }
  async function askJudge() {
    if (!modelSettingsReady()) return;
    const text = $('#describe-text').value.trim();
    if (text.length < 4) {toast(t('describeLabel'), true); return;}
    resetDesign();
    const requestId = designRequestId;
    $('#describe-status').textContent = t('judgeThinking'); $('#describe-ask').disabled = true;
    try {
      const existingCapabilities = Object.values(page().tree.capabilities || NONE).map(c => ({id: c.id, name: c.name, definition: c.definition || ''}));
      const r = await request('POST', '/api/design', {capabilityText: text, apiKey: state.apiKey, connection: connectionPayload(), existingCapabilities});
      if (requestId !== designRequestId || !$('#describe').open) return;
      $('#design-json').value = JSON.stringify(r.design, null, 2);
      $('#design-wrap').hidden = false; $('#create-node').hidden = false;
      $('#describe-status').textContent = '$' + r.cost + ' · ' + r.model;
    } catch (error) {if (requestId === designRequestId && $('#describe').open) $('#describe-status').textContent = t('designError') + ': ' + error.message;}
    finally {if (requestId === designRequestId) $('#describe-ask').disabled = false;}
  }
  async function createNodeFromDesign() {
    if (!modelSettingsReady()) return;
    let design;
    try {design = JSON.parse($('#design-json').value);} catch (error) {toast(t('invalid') + ': ' + error.message, true); return;}
    const target = page(), requestId = designRequestId;
    $('#describe-status').textContent = t('creatorThinking'); $('#create-node').disabled = true;
    try {
      const r = await request('POST', '/api/create-level', {design, apiKey: state.apiKey, connection: connectionPayload()});
      while (editGesture) await new Promise(resolve => setTimeout(resolve, 30));
      if (editingLocked(target)) throw Error(t('editLocked'));
      const keepPage = $('#describe').open && requestId !== designRequestId ? page() : null;
      const selection = keepPage && new Set(state.selected);
      try {
        if (state.pages.includes(target)) state.active = state.pages.indexOf(target); else addPage(emptyTree(t('untitled')));
        edit(() => {
          const tree = page().tree, provides = {capability: r.capability.id, node: r.node, variant: r.variant};
          if (Number.isInteger(r.budget) && r.budget > 0) provides.budget = r.budget;
          const previous = tree.levels[r.ref], offers = [...(previous?.meta?.provides || [])];
          if (!offers.some(o => o.capability === provides.capability && o.node === provides.node && (o.variant || 0) === provides.variant)) offers.push(provides);
          tree.levels[r.ref] = {...previous, source: r.source, meta: {...(previous?.meta || {title: r.capability.name, design: r.design}), provides: offers}};
          if (!tree.capabilities[r.capability.id]) tree.capabilities[r.capability.id] = r.capability;
          const v = page().view;
          placePart('level', levelKey(r.capability.id, {...provides, ref: r.ref}), [(260 - v.x) / v.k, (160 - v.y) / v.k], null);
        });
      } finally {
        if (keepPage && state.pages.includes(keepPage)) {state.active = state.pages.indexOf(keepPage); state.selected = selection;}
        renderAll();
      }
      if (requestId === designRequestId) $('#describe').close();
      toast(t('createNode') + ': ' + r.capability.name + ' ($' + r.cost + ')');
    } catch (error) {
      const message = t('designError') + ': ' + error.message;
      if (requestId === designRequestId && $('#describe').open) $('#describe-status').textContent = message;
      else toast(message, true);
    }
    finally {$('#create-node').disabled = false;}
  }


  const assetNames = {'video-index': 'Video-Index', ale: 'ALE-Bench', siglip: 'SigLIP', actiview: 'ActiView', videomme: 'Video-MME', glove: 'GloVe', yolo: 'YOLO', 'public-media': 'Public media'};
  function environmentBusy() {return ['checking', 'preparing', 'downloading', 'idle'].includes(state.environments?.phase);}
  function showEnvironments() {
    renderEnvironments();
    if (!$('#environments-dialog').open) $('#environments-dialog').showModal();
  }
  function renderEnvironments() {
    const value = state.environments, busy = environmentBusy();
    $('#open-environments').classList.toggle('needs-attention', Boolean(value && !value.ready));
    $('#environment-status').textContent = t('envPhase_' + (value?.phase || 'checking'));
    $('#environment-count').textContent = value?.tasks ? String(value.tasks.length) : '—';
    const tasks = $('#environment-tasks'); tasks.replaceChildren();
    for (const task of value?.tasks || []) {
      const info = [task.root, ...task.resources.map(id => assetNames[id] || id)];
      if (task.excludedFromRuntimeValidation) info.push(t('envExcludedValidation'));
      const row = el('li'); row.append(el('code', '', task.id), el('small', 'muted', info.join(' · '))); tasks.append(row);
    }
    const list = $('#environment-assets'); list.replaceChildren();
    for (const asset of value?.assets || []) {
      const row = el('li'); row.append(el('span', '', assetNames[asset.id] || asset.id), el('span', 'asset-' + asset.status, t('envAsset_' + asset.status))); list.append(row);
    }
    const assets = value?.assets || [], completed = assets.filter(a => a.status === 'ready').length;
    const bar = $('#environment-progress');
    bar.max = assets.length || 1;
    if (!value || ['idle', 'checking', 'preparing'].includes(value.phase)) bar.removeAttribute('value');
    else bar.value = completed;
    const progress = value?.progress;
    let detail = completed + '/' + assets.length + ' ' + t('envCompleted');
    if (progress?.file) {
      detail += ' · ' + progress.file;
      if (Number.isFinite(progress.bytes)) detail += ' · ' + (progress.bytes / 1048576).toFixed(1) + (progress.total ? '/' + (progress.total / 1048576).toFixed(1) : '') + ' MB';
      if (progress.frames) detail += ' · ' + progress.frames + '/' + progress.totalFrames + ' ' + t('envFrames');
    } else if (progress?.asset) detail += ' · ' + (assetNames[progress.asset] || progress.asset);
    $('#environment-detail').textContent = detail;
    $('#environment-error').hidden = !value?.error;
    $('#environment-error').textContent = value?.error || '';
    $('#environment-download').hidden = Boolean(value?.ready);
    $('#environment-download').disabled = busy || !assets.length || state.offline || Boolean(state.run && ['starting', 'running', 'stopping'].includes(state.run.status));
    $('#environment-check').disabled = busy || state.offline;
  }
  function scheduleEnvironmentPoll() {
    clearTimeout(environmentTimer);
    if (environmentBusy()) environmentTimer = setTimeout(() => refreshEnvironments(), 1500);
  }
  async function refreshEnvironments(force = false, initial = false) {
    clearTimeout(environmentTimer);
    if (initial) environmentPromptPending = true;
    const requestId = ++environmentRequestId;
    if (force) {state.environments = {...state.environments, phase: 'checking', ready: false}; renderEnvironments(); renderRunControls();}
    let result;
    try {
      result = await request(force ? 'POST' : 'GET', '/api/environments' + (force ? '/check' : ''), force ? {} : undefined);
    } catch (error) {result = {phase: 'error', ready: false, assets: [], error: t('envConnection') + ' ' + error.message};}
    if (requestId !== environmentRequestId) return;
    state.environments = result;
    renderEnvironments(); renderRunControls();
    if (environmentPromptPending && !['idle', 'checking'].includes(state.environments.phase)) {
      environmentPromptPending = false;
      if (!state.environments.ready) showEnvironments();
    }
    scheduleEnvironmentPoll();
  }
  async function downloadEnvironments() {
    clearTimeout(environmentTimer);
    const requestId = ++environmentRequestId;
    $('#environment-download').disabled = true;
    let result;
    try {result = await request('POST', '/api/environments/download', {});}
    catch (error) {result = {...state.environments, phase: 'error', ready: false, error: error.message};}
    if (requestId !== environmentRequestId) return;
    state.environments = result;
    renderEnvironments(); renderRunControls(); scheduleEnvironmentPoll();
  }

  async function boot() {
    setLang('en');
    setupMenus(); setupCanvas(); renderI18n();
    state.offline = location.protocol === 'file:' || globalThis.TRINITY_STUDIO_OFFLINE === true;
    state.recovering = !state.offline;
    if (!state.offline) try {state.info = await request('GET', '/api/info');} catch (error) {toast(error.message, true);}
    if (!state.info) state.info = {allowLocalEnvironment: false};
    addPage(emptyTree(t('untitled')));
    if (!state.offline) {await recoverRun(); await refreshEnvironments(true, false);}
    else $('#open-environments').disabled = true;
  }
  for (const [name, fn] of [['placePart', placePart], ['deleteSelection', deleteSelection], ['arrangeNodes', arrangeNodes]]) {
    const wrapped = (...args) => edit(() => fn(...args));
    if (name === 'placePart') placePart = wrapped;
    if (name === 'deleteSelection') deleteSelection = wrapped;
    if (name === 'arrangeNodes') arrangeNodes = wrapped;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
