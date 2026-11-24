import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {layeredPlan} from './plan.mjs';
import {solidPng} from './png.mjs';
import {applyRelay, parseJsonReply, PRICES} from './model-io.mjs';
import {SpendingBudget, DEFAULT_BUDGET_PROFILE} from '../../pipeline/src/spending.mjs';
export {SpendCap} from '../../pipeline/src/spending.mjs';
import {materializeProject} from './project-environment.mjs';
import {closeLevelEngine} from './level-engine.mjs';

const {analyzeTree} = globalThis.TrinityTree;

const emit = (type, payload = {}) => process.stdout.write(JSON.stringify({type, ...payload}) + '\n');
const load = (root, file) => import(pathToFileURL(path.join(root, file)).href);

export function publishNodeModules(tree, registries, paths, publish = emit) {
  const info = analyzeTree(tree);
  for (const nodePath of paths) {
    const nodes = tree.nodes.filter(node => node.kind === 'capability' && info.path(node.id) === nodePath);
    const modules = JSON.parse(JSON.stringify(registries[nodePath] ?? []));
    for (const node of nodes) node.modules = JSON.parse(JSON.stringify(modules));
    publish('node_modules', {treeNodes: nodes.map(node => node.id), modules});
  }
}

async function readJob() {
  let text = '';
  for await (const chunk of process.stdin) text += chunk;
  return JSON.parse(text);
}

export function normalizeDecision(operation, response) {
  if (operation !== 'explorer_act' || !response || typeof response !== 'object' || Array.isArray(response) || response.kind) return response;
  if (typeof response.moduleId === 'string') return {kind: 'module', ...response};
  let action = response;
  while (action && typeof action.action === 'object' && action.action !== null && !Array.isArray(action.action)) action = action.action;
  if (action && typeof action.action === 'string') return {kind: 'action', action: {action: action.action, args: action.args ?? {}}};
  return response;
}

const spend = {usd: 0, calls: 0, limit: null, stopped: false, budget: null};
function writeSpend() {spend.budget?.save();}

export function modelBackend(code, apiKey, providerId = 'anthropic') {
  return Promise.all([load(code, 'pipeline/src/model.mjs'), load(code, 'harness/src/media.mjs')]).then(([model, media]) => {
    const profile = model.resolveProfile(providerId);
    return {
    executionProfile: {kind: 'model', profile, maxTokens: 16000, searchEnabled: false},
    async respond(request) {
      if (JSON.stringify(model.resolveProfile(providerId)) !== JSON.stringify(profile)) throw Error('Model execution profile changed during learning');
      let result;
      try {
        result = await model.callModel({profile: profile.id, apiKey, system: request.system,
          turns: [{role: 'user', text: media.modelContent({operation: request.operation, context: request.context, outputContract: request.outputContract})}],
          maxTokens: 16000, searchEnabled: false, budget: spend.budget});
      } catch (error) {throw error;}
      try {
        if (result.stopReason !== 'done') throw Error('Incomplete model response');
        const response = normalizeDecision(request.operation, parseJsonReply(result.text));
        return {transport: 'trinity-agent-result-v1', response, usage: result.usage, attempts: result.attempts,
          attemptRecords: result.attemptRecords, callId: result.callId, provider: profile.id, model: result.model};
      } catch (error) {
        Object.assign(error, {usage: result.usage, attempts: result.attempts, attemptRecords: result.attemptRecords,
          callId: result.callId, provider: profile.id, model: result.model});
        throw error;
      }
    }
  };});
}

export function initSpend(job) {
  if (!Number.isFinite(job.spendLimitUsd) || job.spendLimitUsd <= 0) throw Error('Model runs require a finite positive spending limit');
  if (spend.budget) return;
  const model = job.relay?.model ?? DEFAULT_BUDGET_PROFILE.model;
  const prices = PRICES[model];
  if (!prices) throw Error('No price table for model ' + model + '; cannot enforce the spending cap');
  spend.budget = new SpendingBudget({limitUsd: job.spendLimitUsd,
    profile: {model, inputTokenLimit: DEFAULT_BUDGET_PROFILE.inputTokenLimit, prices},
    file: path.join(job.out, 'spend.json'), onChange(state) {
      const newlyStopped = state.stopped && !spend.stopped;
      Object.assign(spend, {usd: state.usd, calls: state.calls, limit: state.limitUsd, stopped: state.stopped});
      emit(newlyStopped ? 'spend_cap' : 'spend', {usd: state.usd, reservedUsd: state.reservedUsd,
        calls: state.calls, limit: state.limitUsd, uncertainAttempts: state.uncertainAttempts});
    }});
}

export function pipelineCallModel(code, apiKey) {
  return load(code, 'pipeline/src/model.mjs').then(model => request => model.callModel({...request, apiKey, budget: spend.budget}));
}

function followLedger(file, onEvent) {
  let offset = 0, rest = '';
  const read = () => {
    if (!fs.existsSync(file)) return;
    const size = fs.statSync(file).size;
    if (size <= offset) return;
    const fd = fs.openSync(file, 'r'), buffer = Buffer.alloc(size - offset);
    fs.readSync(fd, buffer, 0, buffer.length, offset);
    fs.closeSync(fd);
    offset = size;
    const lines = (rest + buffer.toString('utf8')).split('\n');
    rest = lines.pop();
    for (const line of lines) if (line.trim()) try {onEvent(JSON.parse(line));} catch {}
  };
  const timer = setInterval(read, 300);
  return () => {clearInterval(timer); read();};
}

const relay = layer => event => {
  const p = event.payload ?? {};
  if (event.type === 'environment_learning_started') emit('task_started', {layer, taskId: p.taskId, capability: p.node, cursor: p.cursor});
  else if (event.type === 'environment_learned') emit('task_finished', {layer, taskId: p.taskId, capability: p.node,
    accepted: p.moduleUpdateAccepted, comparison: p.measurement?.comparison, baseline: p.measurement?.baselineCompletions,
    candidate: p.measurement?.candidateCompletions, usage: p.usage});
  else if (event.type === 'episode_finished') emit('episode', {layer, episodeId: p.episodeId, node: p.node, phase: p.phase, success: p.success, technicalFailure: p.technicalFailure});
};

const placeholder = frame => solidPng(64, [42, 58, 82], frame);

function imageOf(observation) {
  const frame = observation && (observation.frame || (Array.isArray(observation.images) && observation.images[0]));
  if (frame && typeof frame.data === 'string' && /^image\/(png|jpeg)$/.test(frame.mimeType || '')) return {bytes: Buffer.from(frame.data, 'base64'), ext: frame.mimeType === 'image/png' ? 'png' : 'jpg'};
  return null;
}

const previews = {};
const previewPhases = {
  environment_learning: {offset: 0, label: 'learn'},
  environment_training_side_evaluation: {offset: 5, label: 'validate'},
  inheritance_previous: {offset: 10, label: 'inheritance_previous'},
  inheritance_candidate: {offset: 15, label: 'inheritance_candidate'},
};
let previewFile = null;
function flushPreviews() {
  if (!previewFile) return;
  const tmp = previewFile + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify({schema: 'trinity-studio-run-previews-v1', paths: previews}) + '\n');
  fs.renameSync(tmp, previewFile);
}
function remember(run, state, name, receipt) {
  if (!run.path || !run.taskId) return;
  const tasks = previews[run.path] ??= {};
  const rounds = tasks[run.taskId] ??= [];
  let round = rounds.find(r => r.round === state.round);
  if (!round) {
    round = {round: state.round, phase: state.phase, success: null, frames: []};
    rounds.push(round);
    rounds.sort((a, b) => a.round - b.round);
  }
  round.frames[state.frame - 1] = name;
  if (receipt && receipt.done) round.success = receipt.success === true;
  flushPreviews();
}

function recordingDriver(driver, framesDir, current) {
  fs.mkdirSync(framesDir, {recursive: true});
  const pending = new WeakMap();
  const write = (run, state, observation, receipt = null) => {
    state.frame++;
    const image = imageOf(observation) ?? {bytes: placeholder(state.frame), ext: 'png'};
    const name = run.key + '-r' + state.round + '-f' + state.frame + '.' + image.ext;
    fs.writeFileSync(path.join(framesDir, name), image.bytes);
    remember(run, state, name, receipt);
    emit('frame', {treeNodes: run.treeNodes, taskId: run.taskId, round: state.round, frame: state.frame,
      phase: state.phase, file: name,
      ...(receipt && receipt.done ? {done: true, success: receipt.success === true} : {})});
  };
  return Object.assign(Object.create(driver), {
    async reset(world, instance, ...rest) {
      const session = await driver.reset(world, instance, ...rest);
      if (session) pending.set(session, {observation: session.observation, trial: Number.isInteger(instance?.trial) ? instance.trial : null});
      return session;
    },
    async step(session, action) {
      const receipt = await driver.step(session, action);
      const run = current();
      if (run && session) {
        let state = run.sessions.get(session);
        if (!state) {
          const start = pending.get(session) ?? {observation: null, trial: null};
          let round;
          if (start.trial === null) round = ++run.round;
          else if (run.phase) round = start.trial + 1 + (previewPhases[run.phase]?.offset ?? 0);
          else {
            const seen = run.trials.get(start.trial) ?? 0;
            run.trials.set(start.trial, seen + 1);
            round = start.trial + 1 + seen * 5;
          }
          state = {round, frame: 0, phase: previewPhases[run.phase]?.label ?? (round <= 5 ? 'learn' : 'validate')};
          run.sessions.set(session, state);
          write(run, state, start.observation);
        }
        write(run, state, receipt.observation, receipt);
      }
      return receipt;
    },
  });
}

function copyReusedFrames(row, sourceRun, framesDir, slug) {
  const round = row.instance.trial + 1 + (row.phase === 'environment_learning' ? 0 : 5);
  const key = slug(row.taskId), frames = [];
  for (let f = 1; f <= row.actions + 1; f++) {
    const name = key + '-r' + round + '-f' + f + '.png', from = path.join(sourceRun, 'frames', name);
    if (!fs.existsSync(from)) {frames.push(null); continue;}
    fs.copyFileSync(from, path.join(framesDir, name));
    frames.push(name);
  }
  const node = row.node, tasks = previews[node] ??= {}, rounds = tasks[row.taskId] ??= [];
  const entry = {round, phase: round <= 5 ? 'learn' : 'validate', success: row.success === true, frames, reused: true};
  const i = rounds.findIndex(r => r.round === round);
  if (i >= 0) rounds[i] = entry; else rounds.push(entry);
  rounds.sort((a, b) => a.round - b.round);
  flushPreviews();
  emit('frame', {treeNodes: [], taskId: row.taskId, round, frame: frames.length, phase: entry.phase, file: frames.at(-1), done: true, success: entry.success, reused: true});
}

export async function loadReuse(dirs, code, onDiagnostic = () => {}) {
  const {loadLearningReuse} = await load(code, 'src/environment-learning-reuse.mjs');
  const sources = [];
  for (const dir of dirs) {
    if (!dir || !fs.existsSync(dir)) {onDiagnostic({source: dir, reason: 'missing_source'}); continue;}
    for (const layer of fs.readdirSync(dir, {withFileTypes: true}).filter(e => e.isDirectory() && /^layer-\d+$/.test(e.name)).sort((a,b) => a.name.localeCompare(b.name)))
      for (const group of fs.readdirSync(path.join(dir, layer.name), {withFileTypes: true}).filter(e => e.isDirectory()).sort((a,b) => a.name.localeCompare(b.name))) {
        const directory = path.join(dir, layer.name, group.name);
        if (fs.existsSync(path.join(directory, 'events.jsonl'))) sources.push({directory, source: path.resolve(dir)});
      }
  }
  return loadLearningReuse(sources, {onDiagnostic});
}

function studioRevision() {
  const root = new URL('./', import.meta.url);
  const files = fs.readdirSync(root).filter(name => name.endsWith('.mjs')).sort().map(name => [name, fs.readFileSync(new URL(name, root), 'utf8')]);
  return createHash('sha256').update(JSON.stringify(files)).digest('hex');
}

export async function evolveTree(job, {backendOverride} = {}) {
  if (job.agent !== 'model') throw Error('Unknown agent');
  const {prepareEnvironmentLearning, learnEnvironments, validateEnvironmentLearning, retainedNodeModules} = await load(job.code, 'src/environment-learning.mjs');
  const {snapshot, clone} = await load(job.code, 'harness/src/core.mjs');
  const project = await materializeProject({tree:job.tree,directory:path.join(job.out,'project-environment'),vendorDir:path.join(job.env,'vendor')});
  const prepared = prepareEnvironmentLearning({environmentPackage: project.directory, selectiveInheritance: true});
  await validateEnvironmentLearning(prepared,{}, {allowLocalEnvironment:job.allowLocalEnvironment});
  const reuse = Array.isArray(job.reuseFrom) && job.reuseFrom.length ? await loadReuse(job.reuseFrom, job.code, diagnostic => emit('reuse_diagnostic', diagnostic)) : null;
  if (reuse) emit('reuse', {sources: job.reuseFrom.map(d => path.basename(d)), tasks: Object.fromEntries(Object.entries(reuse).map(([id, t]) =>
    [id, {learn: t.environment_learning.length, validate: t.environment_training_side_evaluation.length, proposal: t.proposals.length > 0}]))});
  const {layers, skipped} = layeredPlan(job.tree, prepared.pkg.curriculum);
  emit('plan', {layers: layers.map(l => ({layer: l.layer, nodes: l.nodes, benches: l.benches,
    tasks: l.tasks.map(t => ({id: t.id, treeNodes: t.treeNodes, moduleScope: t.moduleScope}))})), skipped});
  const backend = backendOverride ?? await modelBackend(job.code, job.apiKey, applyRelay(job.relay));
  const profile = backend.executionProfile ?? null;
  const executionIdentity = profile ? {studioRevision: studioRevision(), profile} : null;
  let registries = {}, inheritedRegistries = {}, validationFeedback = {};
  const framesDir = path.join(job.out, 'frames');
  const slug = value => String(value).replace(/[^A-Za-z0-9]+/g, '_').slice(0, 60);
  const record = driver => {
    let current = null;
    const inner = recordingDriver(driver, framesDir, () => current);
    return Object.assign(inner, {
      setPhase(phase) {if (current) current.phase = phase;},
      async loadBenchmark(task) {
        current = {key: slug(task.id ?? task), taskId: task.id ?? null, path: task.path ?? null, treeNodes: task.treeNodes ?? [], round: 0, trials: new Map(), sessions: new WeakMap()};
        return driver.loadBenchmark(task);
      },
    });
  };
  const attempts = Number.isInteger(job.groupAttempts) && job.groupAttempts > 0 ? job.groupAttempts : 2;
  const failedNodes = [];
  fs.mkdirSync(job.out, {recursive: true});
  previewFile = path.join(job.out, 'previews.json');
  initSpend(job);
  fs.writeFileSync(path.join(job.out, 'tree.json'), JSON.stringify(job.tree, null, 2) + '\n');
  for (const layer of layers) {
    if (spend.stopped) {
      for (const node of layer.nodes) failedNodes.push({layer: layer.layer, node, message: 'Not started: spending cap reached'});
      emit('layer_skipped', {layer: layer.layer, nodes: layer.nodes, reason: 'spending cap reached'});
      continue;
    }
    emit('layer_started', {layer: layer.layer, nodes: layer.nodes});
    const groups = new Map();
    for (const task of layer.tasks) (groups.get(task.node) ?? groups.set(task.node, []).get(task.node)).push(task);
    const inherited = layer.layer > 1 ? {hash: 'layer-' + (layer.layer - 1), artifact: {registries, inheritedRegistries, validationFeedback, summary: [], cursor: 0, epochs: 1}} : null;
    const learnGroup = async (node, tasks) => {
      for (let attempt = 1; ; attempt++) {
        const directory = path.join(job.out, 'layer-' + layer.layer, node + (attempt > 1 ? '-retry' + (attempt - 1) : ''));
        const plan = {...prepared.plan, taskIds: tasks.map(t => t.id), treeLayer: layer.layer};
        const pkg = Object.assign(Object.create(prepared.pkg), {
          createDriver: async (...args) => record(await prepared.pkg.createDriver(...args)),
        });
        const run = {...prepared, pkg, plan, selected: tasks, epochs: 1, previous: inherited, reuse};
        const forward = relay(layer.layer);
        const stop = followLedger(path.join(directory, 'events.jsonl'), event => {
          forward(event);
          if (event.type === 'episode_reused') {
            const source = (job.reuseFrom ?? []).find(d => path.resolve(d) === event.payload.reusedFrom);
            if (source) copyReusedFrames(event.payload, source, framesDir, slug);
          }
        });
        try {
          await learnEnvironments({prepared: run, backend, executionIdentity, directory, driverOptions: {}, allowLocalEnvironment: job.allowLocalEnvironment});
          return JSON.parse(fs.readFileSync(path.join(directory, 'checkpoint.json'), 'utf8')).artifact;
        } catch (error) {
          emit('group_failed', {layer: layer.layer, node, attempt, retrying: attempt < attempts, message: String(error.message).slice(0, 500)});
          if (attempt >= attempts || spend.stopped) throw error;
        } finally {stop(); flushPreviews();}
      }
    };
    const results = await Promise.allSettled([...groups].map(([node, tasks]) => learnGroup(node, tasks)));
    [...groups.keys()].forEach((node, index) => {
      const result = results[index];
      if (result.status === 'fulfilled') {
        registries[node] = result.value.registries[node] ?? [];
        inheritedRegistries[node] = result.value.inheritedRegistries[node] ?? [];
        validationFeedback[node] = result.value.validationFeedback[node] ?? null;
      } else failedNodes.push({layer: layer.layer, node, message: String(result.reason?.message).slice(0, 500)});
    });
    publishNodeModules(job.tree, registries, [...groups.keys()].filter((node, index) => results[index].status === 'fulfilled'));
    fs.writeFileSync(path.join(job.out, 'tree.json'), JSON.stringify(job.tree, null, 2) + '\n');
    emit('layer_finished', {layer: layer.layer, modules: Object.fromEntries(Object.entries(registries).map(([k, v]) => [k, v.length])),
      failed: failedNodes.filter(f => f.layer === layer.layer).map(f => f.node)});
  }
  const info = analyzeTree(job.tree);
  const harnesses = job.tree.nodes.filter(node => node.kind === 'capability').map(node => {
    const scope = info.scope(node.id);
    const modules = retainedNodeModules(registries, inheritedRegistries, info.path(node.id));
    return {treeNode: node.id, path: info.path(node.id), moduleScope: scope, benches: info.benches(node.id), ...snapshot(modules)};
  });
  fs.writeFileSync(path.join(job.out, 'tree-harness.json'), JSON.stringify({schema: 'trinity-studio-tree-harness-v1', tree: job.tree.name,
    packageRevision: prepared.pkg.revision, registries: clone(registries), inheritedRegistries: clone(inheritedRegistries), harnesses, failedNodes}, null, 2) + '\n');
  writeSpend();
  emit('finished', {out: job.out, layers: layers.length, skipped: skipped.length, failed: failedNodes,
    ...(spend.limit !== null ? {spendUsd: Number(spend.usd.toFixed(2)), spendLimit: spend.limit, capReached: spend.stopped} : {})});
  if (failedNodes.length) process.exitCode = 1;
}

async function fromScratch(job) {
  initSpend(job);
  const providerId = applyRelay(job.relay);
  const model = await load(job.code, 'pipeline/src/model.mjs');
  const profile = model.resolveProfile(providerId, providerId === 'anthropic' ? {} : process.env);
  const callModel = await pipelineCallModel(job.code, job.apiKey);
  const {runScratchWorkflow} = await import('./scratch-workflow.mjs');
  const backend = await modelBackend(job.code,job.apiKey,providerId);
  const target = await runScratchWorkflow({job,callModel,backend,profile:profile.id,emit});
  emit('phase', {phase: 'evolve'});
  await evolveTree({...job, tree: {...target, name: job.tree?.name || 'scratch'}});
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url) {
  const job = await readJob();
  const playwright = path.join(job.env,'node_modules','playwright','index.js');
  if(!process.env.PLAYWRIGHT_MODULE && fs.existsSync(playwright)) process.env.PLAYWRIGHT_MODULE=playwright;
  try {
    if (job.mode === 'scratch') await fromScratch(job);
    else await evolveTree(job);
  } catch (error) {
    emit('failed', {message: String(error.message).replaceAll(job.apiKey || '\u0000', '[redacted]').slice(0, 2000)});
    process.exitCode = 1;
  } finally {await closeLevelEngine();}
}
