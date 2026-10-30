import {freezeExplorationInstances} from '../harness/src/exploration-plan.mjs';
import {stage2Binding, verifyTrainingCompletion} from '../harness/src/protocol-state.mjs';
import fs from 'node:fs';
import {modelContent, normalizeMedia} from '../harness/src/media.mjs';
import {resolveProfile, requireProviderKey, callModel} from '../pipeline/src/model.mjs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {Agent, CommandAgent} from '../harness/src/agent.mjs';
import {Store, clone, ensure, digest, buildTree, validateConfig, writeAtomic} from '../harness/src/core.mjs';
import {runBatch} from '../harness/src/explorer.mjs';
import {Trinity} from '../harness/src/engine.mjs';
import {capabilityDefinitions} from '../harness/src/capabilities.mjs';

export const ROOT = fileURLToPath(new URL('../', import.meta.url));
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const write = (file, value) => writeAtomic(file, JSON.stringify(value, null, 2) + '\n');

export function runCommand(command, args, {cwd = ROOT, env = process.env, capture = false} = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {cwd, env, shell: false, stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit'});
    let stdout = '', stderr = '', settled = false;
    const finish = (error, value) => {
      if (settled) return;
      settled = true;
      error ? reject(error) : resolve(value);
    };
    if (capture) {
      child.stdout.on('data', chunk => {
        stdout += chunk;
        if (Buffer.byteLength(stdout) > 33554432) {child.kill(); finish(Error('Command output limit exceeded'));}
      });
      child.stderr.on('data', chunk => {stderr = (stderr + chunk).slice(-4000);});
    }
    child.on('error', error => finish(error));
    child.on('close', code => finish(code === 0 ? null : Error('Command failed: ' + (stderr || String(code))), stdout));
  });
}

export function runStage2(args, {capture = false} = {}) {
  const stage = path.join(ROOT, 'stage2');
  const env = {...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: [stage, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)};
  return runCommand(process.env.TRINITY_PYTHON || 'python3', ['-B', '-m', 'trinity_stage2.cli', ...args], {cwd: process.cwd(), env, capture});
}

export class ProviderBackend {
  async respond(request) {
    const profile = resolveProfile(), apiKey = requireProviderKey(profile);
    const result = await callModel({profile: profile.id, apiKey, system: request.system,
      turns: [{role: 'user', text: modelContent({operation: request.operation, context: request.context, outputContract: request.outputContract})}],
      maxTokens: 16000, searchEnabled: false});
    try {
      ensure(result.stopReason === 'done', 'Incomplete model response');
      const text = result.text.trim();
      return {transport: 'trinity-agent-result-v1', response: JSON.parse(text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')), usage: result.usage, attempts: result.attempts, attemptRecords: result.attemptRecords, callId: result.callId, provider: profile.id, model: result.model};
    } catch (error) {error.usage = result.usage; error.attempts = result.attempts; error.attemptRecords = result.attemptRecords; error.callId = result.callId; error.model = result.model; throw error;}
  }
}

export async function loadAdapter(file) {
  const resolved = path.resolve(file), settings = read(resolved);
  ensure(typeof settings.driverModule === 'string', 'adapter.driverModule is required');
  const driverPath = path.resolve(path.dirname(resolved), settings.driverModule);
  const imported = await import(pathToFileURL(driverPath).href);
  ensure(typeof imported.createDriver === 'function', 'Driver module must export createDriver');
  const driver = await imported.createDriver(clone(settings.driverOptions ?? {}));
  const backend = settings.agentCommand ? new CommandAgent(settings.agentCommand, settings.agentOptions) : new ProviderBackend();
  return {settings, backend, driver};
}

export function publicTask(task) {
  ensure(typeof task.taskId === 'string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,159}$/.test(task.taskId), 'Invalid task identifier');
  const result = {id: task.taskId, taskId: task.taskId, name: task.name ?? task.taskId,
    goal: task.assignment?.task ?? task.summary ?? task.name ?? task.taskId};
  for (const key of ['kind', 'track', 'route', 'sourceUrl', 'taskTreeOrigin', 'summary', 'assignment', 'inputScope', 'scorer', 'interface', 'failureRule']) {
    if (Object.hasOwn(task, key)) result[key] = clone(task[key]);
  }
  return result;
}

export function trainingConfig(input, settings = {}) {
  ensure(input.schema === 'trinity-training-input-v1', 'Unsupported training handoff');
  const defaults = read(path.join(ROOT, 'harness/config/defaults.json'));
  const ids = input.trainingTasks.map(task => task.taskId);
  const tasks = new Map(input.trainingTasks.map(task => [task.taskId, publicTask(task)]));
  ensure(new Set(ids).size === ids.length && input.assignments.length === ids.length, 'Training task coverage mismatch');
  const seen = new Set(), assignments = [], baselineTasks = [];
  for (const row of input.assignments) {
    ensure(tasks.has(row.taskId) && !seen.has(row.taskId), 'Unknown or duplicate training assignment');
    seen.add(row.taskId);
    ensure(Array.isArray(row.requirements), 'Invalid capability requirements');
    if (row.requirements.length) assignments.push(clone(row));
    else baselineTasks.push(tasks.get(row.taskId));
  }
  const trainingTasks = assignments.map(row => tasks.get(row.taskId));
  ensure(trainingTasks.length > 0, 'No nonempty capability routes to evolve');
  for (const key of ['trainingTrials', 'validationTrials']) {
    ensure(settings[key] === undefined || settings[key] === 5, 'Five episodes are required');
  }
  const config = {mode: 'integrated_pipeline', capabilityMode: 'fixed_tree',
    iterations: settings.iterations ?? defaults.iterations, actionBudget: settings.actionBudget ?? defaults.actionBudget,
    maxBuildAttempts: settings.maxBuildAttempts ?? defaults.maxBuildAttempts,
    screening: clone(settings.screening ?? defaults.screening), trainingTrials: 5, validationTrials: 5,
    taxonomy: clone(input.taxonomy), capabilityDefinitions: capabilityDefinitions(input.taxonomy, input.capabilityDefinitions), assignments, trainingTasks, baselineTasks,
    initialFeedback: clone(input.initialFeedback ?? {}), routingExcludedNodes: clone(settings.routingExcludedNodes ?? []),
    unseenTasks: input.unseenTasks.map(publicTask),
    creatorBase: clone(settings.creatorBase ?? defaults.creatorBase), creatorNodeSkills: clone(settings.creatorNodeSkills ?? {}), validationPolicies: clone(settings.validationPolicies ?? {}),
    trainingMemoryDirectory: input.trainingMemoryDirectory ?? null, stage2Binding: input.stage2Binding ?? null,
    creatorCoding: clone(settings.creatorCoding ?? {}), upstreamDigest: digest(input)};
  const allIds = [...config.trainingTasks, ...config.baselineTasks, ...config.unseenTasks].map(task => task.id);
  ensure(new Set(allIds).size === allIds.length, 'Task cohorts must be disjoint');
  buildTree(config.taxonomy, assignments, trainingTasks.map(task => task.id));
  return validateConfig(config);
}

export function canonicalEpisode(task, report) {
  ensure(!report.technicalFailure, 'Technical failures cannot be imported as task failures');
  const events = report.events.map(event => event.publicData ?? JSON.parse(event.publicText)).filter(event => event.action && event.receipt);
  ensure(events.length === report.actions && events.length > 0, 'Incomplete native action trajectory');
  const observation = normalizeMedia;
  const last = events.at(-1).receipt;
  const outcome = report.success ? 'success' : 'failure';
  const score = Number.isFinite(last.score) ? last.score : null;
  const reason = report.reason ?? last.reason ?? 'Terminal receipt';
  return {taskId: task.id, episodeId: report.episodeId, configuration: report.harnessId, outcome, score, reason,
    initialObservation: observation(events[0].observation),
    steps: events.map((event, index) => ({index: index + 1, action: event.action, observation: observation(event.receipt.observation),
      terminal: index === events.length - 1 ? {outcome, score, reason} : null, reward: event.receipt.reward ?? null})),
    source: {format: 'trinity-exploration', harnessId: report.harnessId, worldDigest: report.worldDigest, usage: report.usage, actionCost: report.cost, reward: report.reward, reportedRewardSum: report.reportedRewardSum, missingRewards: report.missingRewards, scoreSource: report.scoreSource, normalizedScore: report.normalizedScore, scoreNormalization: report.scoreNormalization, benchmarkId: report.benchmarkId, split: report.split, protocolId: report.protocolId, success: report.success}};
}

export async function explore({handoff, backend, driver, directory, budget, cohort = 'train', trainingRun = null}) {
  ensure(handoff.schema === 'trinity-stage2-handoff-v1', 'Unsupported task handoff');
  ensure(['train', 'unseen'].includes(cohort), 'Exploration cohort must be train or unseen');
  ensure(Number.isInteger(budget) && budget > 0, 'Positive action budget required');
  const split = handoff.taskTree?.split;
  ensure(!split?.gaps?.length && !split?.errors?.length, 'Incomplete task split');
  const selected = handoff.tasks.filter(task => task.set === cohort).map(publicTask);
  ensure(selected.length && new Set(selected.map(task => task.id)).size === selected.length, 'Empty or duplicate exploration task list');
  const completed = cohort === 'unseen' ? verifyTrainingCompletion(trainingRun) : null;
  if (completed) {
    ensure(completed.artifact.stage2?.handoffDigest === digest(JSON.parse(JSON.stringify(handoff))), 'Unseen handoff differs from the completed training split');
    ensure(digest(selected.map(task => task.id).sort()) === digest([...completed.artifact.unseenTaskIds].sort()), 'Unseen cohort differs from completed training');
  }
  const store = new Store(directory, {mode: 'initial_exploration', cohort, budget, tasks: selected});
  if (completed) store.record('unseen_exploration_authorized', {completionHash: completed.hash, completionEvent: completed.event});
  const agent = new Agent(backend, store), runs = {}, plans = [];
  for (const task of selected) {
    const world = await driver.loadBenchmark(clone(task));
    const plan = await freezeExplorationInstances({driver, world, trials: 5, store, taskId: task.id});
    plans.push({task, world, plan});
  }
  store.write('initial-instances.json', {schema: 'trinity-exploration-plan-v1', plans: plans.map(({task, plan}) => ({taskId: task.id, ...plan}))});
  for (const {task, world, plan} of plans) {
    const fingerprint = plan.worldDigest;
    const rows = await runBatch({agent, driver, store, world, modules: [], budget, taskId: task.id, benchmarkId: task.benchmarkId ?? task.id, split: cohort, instances: plan.instances, initialStateHashes: plan.initialStateHashes, instancePlan: plan.event, phase: 'initial_training_exploration', node: 'root'}, 5);
    ensure(digest(await driver.fingerprint(clone(world))) === fingerprint, 'World changed during initial exploration');
    const episodes = rows.map(row => canonicalEpisode(task, row));
    const relative = 'records/' + task.id + '.json';
    write(path.join(directory, relative), episodes);
    runs[task.id] = {format: 'canonical', path: relative};
    store.record('exploration_task_exported', {taskId: task.id, cohort, episodeIds: rows.map(row => row.episodeId), recordsDigest: digest(episodes)});
  }
  for (const source of Object.values(runs)) Object.assign(source, {ledgerPath: 'events.jsonl', ledgerHead: store.previous});
  write(path.join(directory, 'handoff.json'), handoff);
  write(path.join(directory, 'runs.json'), runs);
  return {tasks: selected.length, episodes: selected.length * 5, cohort};
}

export async function prepareTraining(stage2, settings = {}) {
  const input = JSON.parse(await runStage2(['export-training', '--out', path.resolve(stage2)], {capture: true}));
  input.stage2Binding = stage2Binding(stage2);
  return trainingConfig(input, settings);
}

export async function train({config, backend, driver, directory}) {
  const store = new Store(directory, config), agent = new Agent(backend, store);
  try {return await new Trinity({config, backend, agent, driver, store}).run();}
  catch (error) {store.record('run_failed', {message: String(error.message)}); throw error;}
}
