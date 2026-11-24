(function (root) {
  'use strict';
  root.TrinityExplorer = {create({getPage, getLabel, fit, transform, t, getLang, onFocus = () => {}}) {
    const $ = selector => document.querySelector(selector);
    const make = (tag, cls, text) => {const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n;};
    const svgNode = (tag, attrs) => {const n = document.createElementNS('http://www.w3.org/2000/svg', tag); for (const [k,v] of Object.entries(attrs)) n.setAttribute(k, v); return n;};
    const data = p => p && (p.explorer ||= {focusId: null, detailId: null, tab: 'inputs', events: Object.create(null), runError: ''});
    let related = null, mapFrame = 0, mapping = null, detailSignature = '', detailIdentity = '';
    const area = () => {const r = $('#canvas').getBoundingClientRect(), log = $('#log').getBoundingClientRect(); return {width: r.width, height: Math.max(1, Math.min(r.bottom, log.top) - r.top)};};
    function focus(id) {const p = getPage(); if (!p) return; data(p).focusId = p.tree.nodes.some(n => n.id === id) ? id : null; refreshFocus(); onFocus(data(p).focusId);}
    function refreshFocus() {
      const p = getPage(); if (!p) return;
      const ui = data(p), nodes = p.tree.nodes, links = p.tree.links;
      if (!nodes.some(n => n.id === ui.focusId)) ui.focusId = null;
      related = ui.focusId ? new Set([ui.focusId]) : null;
      if (related) {
        const walk = reverse => {const seen = new Set(), pending = [ui.focusId]; while (pending.length) {const id = pending.pop(); if (seen.has(id)) continue; seen.add(id); related.add(id); for (const l of links) if ((reverse ? l.to : l.from) === id) pending.push(reverse ? l.from : l.to);}};
        walk(true); walk(false);
        const benches = new Set(nodes.filter(n => n.kind === 'bench').map(n => n.id));
        for (const l of links) if (related.has(l.from) && benches.has(l.to)) related.add(l.to);
      }
      document.querySelectorAll('.node').forEach(n => {n.classList.toggle('focus-muted', !!related && !related.has(n.dataset.id)); n.classList.toggle('focus-anchor', n.dataset.id === ui.focusId);});
      document.querySelectorAll('#links path').forEach(n => n.classList.toggle('focus-muted', !!related && (!related.has(n.dataset.to) || (n.dataset.from && !related.has(n.dataset.from)))));
      $('#branch-focus').hidden = !related;
      $('#branch-focus-label').textContent = related ? getLabel(nodes.find(n => n.id === ui.focusId)) : '';
      queueMap();
    }
    function open(id) {
      const p = getPage(); if (!p || !p.tree.nodes.some(n => n.id === id)) return;
      onFocus(id); data(p).detailId = id; $('#sidebar').classList.remove('hidden'); $('#log').classList.remove('wide');
      renderDetails(); $('#close-inspector').focus({preventScroll: true}); queueMap();
    }
    function close() {const p = getPage(); if (p) data(p).detailId = null; renderDetails();}
    function locate(id) {
      const p = getPage(), n = p?.tree.nodes.find(n => n.id === id); if (!n) return;
      const card = [...document.querySelectorAll('.node')].find(e => e.dataset.id === id), a = area();
      p.view.x = a.width / 2 - (n.pos[0] + (card?.offsetWidth || 420) / 2) * p.view.k;
      p.view.y = a.height / 2 - (n.pos[1] + (card?.offsetHeight || 300) / 2) * p.view.k;
      transform();
    }
    function renderDetails() {
      const p = getPage(), ui = data(p), node = p?.tree.nodes.find(n => n.id === ui.detailId);
      $('#library-panel').hidden = !!node; $('#node-inspector').hidden = !node;
      if (!node) {if (ui) ui.detailId = null; detailSignature = ''; return;}
      const status = p.status?.[node.id], entries = ui.events[node.id] || [], rounds = node.preview?.rounds || [];
      const upstream = p.tree.links.filter(l => l.to === node.id).map(l => p.tree.nodes.find(n => n.id === l.from)).filter(Boolean);
      const signature = JSON.stringify([getLang(), node.id, getLabel(node), node.level, node.modules, rounds.map(r => [r.round,r.phase,r.success,r.tape?.actions?.length]), status, entries, ui.runError, ui.tab, upstream.map(getLabel)]);
      if (signature === detailSignature) return; detailSignature = signature;
      $('#inspector-name').textContent = getLabel(node);
      const states = {queued:'detailQueued',running:'detailRunning',done:'detailDone',failed:'detailFailed',partial:'detailPartial',skipped:'detailSkipped'};
      $('#inspector-meta').textContent = node.id + ' · ' + t('detailStatus') + ': ' + (status ? t(states[status.state] || 'detailUnknown') : t('detailIdle'));
      for (const tab of document.querySelectorAll('[data-detail-tab]')) {const active = tab.dataset.detailTab === ui.tab; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;}
      const content = $('#inspector-content'), identity = node.id + ':' + ui.tab;
      const scroll = identity === detailIdentity ? content.scrollTop : 0; detailIdentity = identity;
      content.setAttribute('aria-labelledby', 'inspector-tab-' + ui.tab); content.replaceChildren();
      const heading = key => content.append(make('h3', '', t(key)));
      const empty = key => content.append(make('p', 'muted', t(key)));
      const field = (key, value) => {const r = make('div','detail-field');r.append(make('span','muted',t(key)),make('span','',String(value)));content.append(r);};
      const outcome = success => t(success === true ? 'detailPassed' : success === false ? 'detailFailed' : 'detailUnknown');
      if (ui.tab === 'inputs') {
        heading('detailConfig');
        if (node.level) {field('level', node.level.node);field('detailVariant', node.level.variant ?? 0);if (node.level.budget !== undefined) field('detailBudget', node.level.budget);} else empty('detailNoInputs');
        if (upstream.length) {heading('detailUpstream');for (const n of upstream) {const button = make('button','detail-related',getLabel(n));button.onclick = () => {focus(n.id);open(n.id);locate(n.id);};content.append(button);}}
        const modules = (node.modules || []).filter(m => m.interface);
        if (modules.length) heading('detailRequirements');
        for (const m of modules) {
          const section = make('details','detail-interface'), title = make('summary','',m.name || m.moduleId || t('moduleTitle'));
          section.append(title,make('pre','',JSON.stringify(m.interface,null,2)));content.append(section);
        }
      } else if (ui.tab === 'outputs') {
        heading('evolvedModules');
        if (!node.modules?.length) empty('detailNoModules');
        for (const m of node.modules || []) {
          const article = make('article','detail-module'); article.append(make('h4','',m.name || m.moduleId || t('moduleTitle')));
          if (m.version !== undefined) article.append(make('small','muted',t('detailModuleVersion') + ' ' + m.version));
          const description = [m.description,m.purpose,m.summary,m.prompt].find(v => typeof v === 'string' && v.trim());
          if (description) article.append(make('p','',description));content.append(article);
        }
        if (rounds.length) {heading('detailPreviewHistory');field('detailRounds',rounds.length);}
      } else if (ui.tab === 'history') {
        heading('detailRuntimeHistory');
        if (!entries.length) empty('detailNoHistory');
        for (const entry of [...entries].reverse()) {
          const item = make('article','detail-event');item.append(make('strong','',t(entry.label)),make('time','muted',new Date(entry.time).toLocaleTimeString(getLang()==='zh'?'zh-CN':'en-US')));
          if (entry.taskId) item.append(make('p','',entry.taskId));
          if (entry.baseline !== undefined || entry.candidate !== undefined) item.append(make('p','',String(entry.baseline ?? '—') + ' → ' + String(entry.candidate ?? '—')));
          if (entry.success !== undefined) item.append(make('p','',outcome(entry.success)));
          content.append(item);
        }
        if (rounds.length) heading('detailPreviewHistory');
        for (const r of rounds) {const item = make('article','detail-event');item.append(make('strong','',t('detailRound')+' '+r.round),make('p','',(r.phase ? t(r.phase)+' · ' : '')+outcome(r.success)));if (r.tape?.actions) item.append(make('small','muted',t('detailActions')+': '+r.tape.actions.length));content.append(item);}
      } else {
        if (status?.error) content.append(make('p','detail-error',String(status.error)));
        else empty('detailNoErrors');
        if (ui.runError) {heading('detailRunError');content.append(make('p','detail-error',ui.runError));}
      }
      content.scrollTop = scroll;
    }
    function record(event, run) {
      const p = run.page, ui = data(p);
      if (ui.runId !== run.id) {ui.events = Object.create(null);ui.runError = '';ui.runId = run.id;}
      const labels = {task_started:'detailTaskStarted',task_finished:'detailTaskFinished',layer_finished:'detailLayerFinished',node_modules:'detailModulesUpdated',frame:'detailRoundFinished'};
      if (event.type === 'failed') ui.runError = String(event.message || '');
      if (!labels[event.type] || (event.type === 'frame' && !event.done)) return;
      const layer = run.layers?.get(event.layer), task = layer?.tasks?.find(task => task.id === event.taskId) || [...(run.layers?.values() || [])].flatMap(layer => layer.tasks || []).find(task => task.id === event.taskId);
      const ids = new Set((event.treeNodes?.length ? event.treeNodes : task?.treeNodes) || (event.type === 'layer_finished' ? layer?.nodes : []) || []);
      for (const l of p.tree.links) if (ids.has(l.from) && p.tree.nodes.some(n => n.id === l.to && n.kind === 'bench')) ids.add(l.to);
      for (const id of ids) {
        if (!p.tree.nodes.some(n => n.id === id)) continue;
        const rows = ui.events[id] ||= [];
        rows.push({label:labels[event.type],time:Date.now(),taskId:event.taskId,baseline:event.baseline,candidate:event.candidate,success:event.success});
        if (rows.length > 40) rows.shift();
      }
    }
    function drawMap() {
      mapFrame = 0; const p = getPage(); if (!p) return;
      const canvas = $('#canvas').getBoundingClientRect(), log = $('#log').getBoundingClientRect();
      $('#minimap-shell').style.bottom = Math.max(12,canvas.bottom-log.top+12)+'px';
      $('#map-zoom').textContent = Math.round(p.view.k*100)+'%';
      const svg = $('#minimap'); if ($('#minimap-shell').classList.contains('collapsed')) return;
      svg.replaceChildren();
      const boxes = [...document.querySelectorAll('.node,.origin-node')].map(n => ({id:n.dataset.id||null,x:n.offsetLeft,y:n.offsetTop,w:n.offsetWidth,h:n.offsetHeight,bench:n.classList.contains('bench-node')}));
      if (!boxes.length) {mapping = null;return;}
      const minX=Math.min(...boxes.map(n=>n.x))-40,minY=Math.min(...boxes.map(n=>n.y))-40,maxX=Math.max(...boxes.map(n=>n.x+n.w))+40,maxY=Math.max(...boxes.map(n=>n.y+n.h))+40;
      const scale=Math.min(192/(maxX-minX),116/(maxY-minY)),ox=(200-(maxX-minX)*scale)/2-minX*scale,oy=(124-(maxY-minY)*scale)/2-minY*scale;
      mapping={scale,ox,oy};const byId=new Map(boxes.map(n=>[n.id,n]));
      for (const link of p.tree.links) {const a=byId.get(link.from),b=byId.get(link.to);if(a&&b)svg.append(svgNode('line',{x1:ox+(a.x+a.w)*scale,y1:oy+(a.y+38)*scale,x2:ox+b.x*scale,y2:oy+(b.y+8)*scale,class:'map-link'+(related&&(!related.has(a.id)||!related.has(b.id))?' focus-muted':'')}));}
      for (const n of boxes) svg.append(svgNode('rect',{x:ox+n.x*scale,y:oy+n.y*scale,width:Math.max(2,n.w*scale),height:Math.max(2,n.h*scale),rx:1,class:'map-node'+(n.bench?' map-bench':'')+(related&&n.id!==null&&!related.has(n.id)?' focus-muted':'')+(n.id===data(p).focusId?' map-selected':'')}));
      const a=area();svg.append(svgNode('rect',{x:ox-p.view.x/p.view.k*scale,y:oy-p.view.y/p.view.k*scale,width:a.width/p.view.k*scale,height:a.height/p.view.k*scale,class:'map-viewport'}));
    }
    function queueMap() {if (!mapFrame) mapFrame=requestAnimationFrame(drawMap);}
    function zoom(factor) {const p=getPage();if(!p)return;const a=area(),v=p.view,k=Math.max(.05,Math.min(2.5,v.k*factor));v.x=a.width/2-(a.width/2-v.x)*k/v.k;v.y=a.height/2-(a.height/2-v.y)*k/v.k;v.k=k;transform();}
    function localize() {
      $('#minimap').setAttribute('aria-label',t('mapHint'));$('#minimap-shell').setAttribute('aria-label',t('overviewMap'));$('#minimap').setAttribute('title',t('mapHint'));
      $('#toggle-minimap').setAttribute('aria-label',t('mapToggle'));$('#toggle-minimap').title=t('mapToggle');
      $('#map-zoom-in').setAttribute('aria-label',t('zoomIn'));$('#map-zoom-out').setAttribute('aria-label',t('zoomOut'));
      $('#inspector-tabs').setAttribute('aria-label',t('nodeDetails'));renderDetails();refreshFocus();
    }
    $('#clear-focus').onclick=()=>focus(null);
    $('#close-inspector').onclick=()=>{close();$('#part-search').focus({preventScroll:true});};
    $('#inspector-locate').onclick=()=>locate(data(getPage())?.detailId);
    $('#inspector-focus').onclick=()=>focus(data(getPage())?.detailId);
    for(const tab of document.querySelectorAll('[data-detail-tab]')) {
      tab.onclick=()=>{const ui=data(getPage());if(ui){ui.tab=tab.dataset.detailTab;renderDetails();}};
      tab.onkeydown=e=>{const tabs=[...document.querySelectorAll('[data-detail-tab]')],i=tabs.indexOf(tab);let next;if(e.key==='ArrowRight')next=(i+1)%tabs.length;if(e.key==='ArrowLeft')next=(i+tabs.length-1)%tabs.length;if(e.key==='Home')next=0;if(e.key==='End')next=tabs.length-1;if(next!==undefined){e.preventDefault();tabs[next].click();tabs[next].focus();}};
    }
    const shell=$('#minimap-shell');shell.onmousedown=e=>e.stopPropagation();shell.onwheel=e=>e.stopPropagation();shell.oncontextmenu=e=>{e.preventDefault();e.stopPropagation();};
    $('#toggle-minimap').onclick=()=>{const collapsed=shell.classList.toggle('collapsed');$('#toggle-minimap').setAttribute('aria-expanded',String(!collapsed));$('#toggle-minimap').textContent=collapsed?'▸':'▾';queueMap();};
    $('#branch-focus').onmousedown=e=>e.stopPropagation();
    $('#map-fit').onclick=()=>fit();$('#map-zoom-in').onclick=()=>zoom(1.25);$('#map-zoom-out').onclick=()=>zoom(.8);
    $('#minimap').onclick=e=>{const p=getPage();if(!p||!mapping)return;const matrix=$('#minimap').getScreenCTM();if(!matrix)return;const point=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse()),a=area();p.view.x=a.width/2-(point.x-mapping.ox)/mapping.scale*p.view.k;p.view.y=a.height/2-(point.y-mapping.oy)/mapping.scale*p.view.k;transform();};
    $('#minimap').onkeydown=e=>{const p=getPage();if(!p)return;const d={ArrowLeft:[80,0],ArrowRight:[-80,0],ArrowUp:[0,80],ArrowDown:[0,-80]}[e.key];if(d){e.preventDefault();p.view.x+=d[0];p.view.y+=d[1];transform();}if(e.key==='Home'){e.preventDefault();fit();}if(e.key==='+'||e.key==='='){e.preventDefault();zoom(1.25);}if(e.key==='-'){e.preventDefault();zoom(.8);}};
    const resize=new ResizeObserver(queueMap);resize.observe($('#canvas'));resize.observe($('#log'));
    return {focus,open,close,record,localize,queueMap,refreshFocus,renderDetails,render:()=>{refreshFocus();renderDetails();}};
  }};
})(globalThis);
