import {hostVerificationCall} from './host-verification.mjs';
import {defaultTrainingMemory} from './protocol-state.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {clone, digest, ensure, snapshot, verifyLedger} from './core.mjs';
import {runEpisode} from './explorer.mjs';
import {freezeEvaluationInstance} from './evaluation-plan.mjs';
import {prepareEvaluationSkills} from './evaluation-skills.mjs';
import {validateTrainingMemory, verifyRoutedReceipt} from './receipts.mjs';
import {freezeRoutingPlan, orderedTrainingMemory, memoryForModel, boundedRoutingAgent} from './router-protocol.mjs';
import {routingScore} from './metrics.mjs';
export {loadTrainingMemory} from './receipts.mjs';
export {prepareEvaluationSkills} from './evaluation-skills.mjs';

function vector(value) {
  const words = JSON.stringify(value).toLowerCase().match(/[a-z0-9]+/g) ?? [], result = new Map();
  for (const word of words) result.set(word, (result.get(word) ?? 0) + 1);
  return result;
}
export function cosine(left, right) {
  const a = vector(left), b = vector(right);
  let dot = 0, aa = 0, bb = 0;
  for (const [key, value] of a) {dot += value * (b.get(key) ?? 0); aa += value * value;}
  for (const value of b.values()) bb += value * value;
  return aa && bb ? dot / Math.sqrt(aa * bb) : 0;
}
export class Router {
  #plan; #memory; #results = []; #cursor = 0; #running = false; #sealed = null;
  #agent; #driver; #store; #similarity; #planDigest; #poolDigest; #promptDigest;
  constructor({agent, driver, store, plan, memory, trainingRun = null, allowColdStart = false, similarity = cosine}) {
    this.#plan = freezeRoutingPlan(plan);
    memory ??= trainingRun ? defaultTrainingMemory(trainingRun) : allowColdStart ? [] : defaultTrainingMemory(path.dirname(store.directory));
    ensure(memory.length > 0 || allowColdStart, 'Verified training memory is required; cold start must be explicit');
    this.#agent = agent; this.#driver = driver; this.#store = store; this.#similarity = similarity;
    this.#memory = orderedTrainingMemory(validateTrainingMemory(memory), this.#plan.publicMetadataKeys);
    this.#planDigest = digest(this.#plan);
    this.#poolDigest = digest(this.#plan.candidates);
    this.#promptDigest = digest(fs.readFileSync(new URL('../prompts/router.txt', import.meta.url), 'utf8'));
    const existing = fs.readFileSync(path.join(store.directory, 'events.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
    ensure(!existing.some(event => event.type === 'routing_session_registered'), 'This run directory already has a routing session');
    const planArtifact = store.put(this.#plan);
    store.record('routing_session_registered', {planDigest: this.#planDigest, planArtifact, poolDigest: this.#poolDigest,
      promptDigest: this.#promptDigest, protocolId: plan.protocolId, split: plan.split,
      taskIds: this.#plan.tasks.map(task => task.taskId), initialMemoryDigest: digest(this.#memory),
      sourceMemoryDigest: digest(memory), sourceMemoryCount: memory.length,
      retrieval: {threshold: 0.5, limit: 10, capacity: 20000}});
  }
  get memory() {return clone(this.#memory);}
  get results() {return clone(this.#results);}
  get nextTaskId() {return this.#plan.tasks[this.#cursor]?.taskId ?? null;}
  async run(taskId) {
    ensure(!this.#sealed && !this.#running, 'Routing session is sealed or already running');
    ensure(typeof taskId === 'string' && taskId === this.nextTaskId, 'Task must be the next unprocessed manifest instance');
    this.#running = true;
    try {
      const item = clone(this.#plan.tasks[this.#cursor]);
      const callBudget = {limit: item.modelCallBudget, modelCalls: 0, preparationCalls: 0,
        preparationLimit: 5 * 3 * item.budget + 1, promptDigest: this.#promptDigest};
      const agent = boundedRoutingAgent(this.#agent, callBudget);
      const options = {...item, publicTask: {...item.publicTask, id: item.taskId},
        candidates: this.#plan.candidates.filter(candidate => item.candidateIds.includes(candidate.snapshotId)).map(clone),
        protocolId: this.#plan.protocolId, split: this.#plan.split};
      const result = await this.#runTask(options, agent, callBudget);
      this.#results.push(clone(result));
      this.#cursor++;
      if (this.#cursor === this.#plan.tasks.length) this.#seal();
      return clone(result);
    } finally {this.#running = false;}
  }
  async runAll() {
    while (this.nextTaskId !== null) await this.run(this.nextTaskId);
    return this.results;
  }
  #seal() {
    const ledger = verifyLedger(path.join(this.#store.directory, 'events.jsonl'));
    const predictions = this.#results.map((row, index) => ({taskId: this.#plan.tasks[index].taskId,
      routingId: row.routingId, decisionId: row.decisionId, snapshotId: row.selectedSnapshotId ?? row.harnessId ?? null,
      success: row.success, normalizedScore: row.normalizedScore, technicalFailure: row.technicalFailure === true,
      invalidSelection: row.invalidSelection === true}));
    const artifact = {schema: 'trinity-routing-predictions-v1', protocolId: this.#plan.protocolId,
      planDigest: this.#planDigest, poolDigest: this.#poolDigest, ledgerHead: ledger.head,
      ledgerEvents: ledger.events, predictions};
    const hash = digest(artifact);
    const sealEvent = this.#store.record('routing_predictions_sealed', {hash, count: predictions.length, ledgerHead: ledger.head});
    const file = path.join(this.#store.directory, 'routing-predictions-' + hash + '.json');
    fs.writeFileSync(file, JSON.stringify({artifact, hash, sealEvent}, null, 2) + '\n', {flag: 'wx'});
    this.#sealed = {file, hash, sealEvent};
  }
  get predictionFile() {return this.#sealed?.file ?? null;}
  readEvaluationLabels(file) {
    ensure(this.#sealed && this.#cursor === this.#plan.tasks.length && !this.#running, 'Complete and seal all predictions before reading evaluation labels');
    const envelope = JSON.parse(fs.readFileSync(this.#sealed.file, 'utf8'));
    ensure(envelope.hash === this.#sealed.hash && digest(envelope.artifact) === envelope.hash && envelope.sealEvent === this.#sealed.sealEvent, 'Sealed prediction artifact changed');
    const ledgerFile = path.join(this.#store.directory, 'events.jsonl');
    verifyLedger(ledgerFile);
    const events = fs.readFileSync(ledgerFile, 'utf8').trim().split('\n').map(JSON.parse);
    const end = events.findIndex(event => event.hash === this.#sealed.sealEvent);
    ensure(end === envelope.artifact.ledgerEvents && events[end - 1]?.hash === envelope.artifact.ledgerHead &&
      events[end].type === 'routing_predictions_sealed' && events[end].payload.hash === envelope.hash, 'Prediction ledger seal mismatch');

    const labels = JSON.parse(fs.readFileSync(file, 'utf8'));
    ensure(Array.isArray(labels) && labels.length === this.#results.length && new Set(labels.map(row => row.taskId)).size === labels.length,
      'Evaluation labels must cover every manifest task exactly once');
    const byId = new Map(labels.map(row => [row.taskId, row]));
    return envelope.artifact.predictions.map(prediction => {
      const row = byId.get(prediction.taskId);
      ensure(row && Array.isArray(row.capabilities) && row.capabilities.every(value => typeof value === 'string'), 'Missing task capability labels');
      return {...clone(prediction), evaluationCapabilities: clone(row.capabilities)};
    });
  }
  async #runTask(options, agent, callBudget) {
    const routingId = randomUUID();
    const task = async () => {
      const usageStart = agent.calls?.length ?? 0;
      try {return await this.#execute({...options, routingId}, agent, callBudget);}
      catch (error) {
        const report = {routingId, episodeId: routingId, decisionId: null, benchmarkId: options.benchmarkId ?? null,
          taskId: options.publicTask?.id ?? null, split: options.split ?? 'unseen', protocolId: options.protocolId ?? null,
          phase: 'routed_evaluation', modelCallBudget: callBudget.limit, modelCalls: callBudget.modelCalls, preparationModelCalls: callBudget.preparationCalls, scoringPolicy: 'routing-zero-failure-v1', technicalFailure: true, success: false,
          score: 0, normalizedScore: 0, scoreSource: 'protocol_zero', reason: String(error.message), cost: 0, costComplete: false,
          usage: agent.usageSince?.(usageStart, {routingId}) ?? null};
        this.#store.record('routing_finished', report);
        return report;
      }
    };
    return agent.withScope ? agent.withScope({routingId, benchmarkId: options.benchmarkId, taskId: options.publicTask.id ?? null, protocolId: options.protocolId, split: options.split ?? 'unseen'}, task) : task();
  }
  async #execute({publicTask, world, candidates, budget, split = 'unseen', benchmarkId, protocolId, preparationWorlds, skillDirectory, scoreNormalization, instance, expectedInitialStateHash, routingId}, agent, callBudget) {
    const usageStart = agent.calls?.length ?? 0;
    const episodeStart = this.#store.episodes.length;
    ensure(candidates.length > 0, 'No compatible Harness candidates');
    const {id: _taskId, ...safeTask} = clone(publicTask);
    ensure(!Object.hasOwn(safeTask.metadata, 'evaluationCapabilityLabels'), 'Held-out labels are not routing input');
    for (const candidate of candidates) ensure(candidate.snapshotId === snapshot(candidate.modules).id, 'Candidate snapshot mismatch');
    const retrieved = this.#memory.map(row => ({row, similarity: this.#similarity(clone(safeTask), clone(row.publicTask))})).filter(item => item.similarity >= 0.5).sort((a, b) => b.similarity - a.similarity).slice(0, 10).map(item => memoryForModel(item.row));
    const summaries = candidates.map(candidate => {
      const rows = this.#memory.filter(row => row.snapshotId === candidate.snapshotId);
      return {snapshotId: candidate.snapshotId, observations: rows.length, successRate: rows.length ? rows.filter(row => row.success).length / rows.length : null, meanCost: rows.length ? rows.reduce((sum, row) => sum + row.cost, 0) / rows.length : null};
    });
    const frozenInstance = await freezeEvaluationInstance({driver: this.#driver, store: this.#store, world, benchmarkId, protocolId, skillDirectory, instance, expectedInitialStateHash});
    const selection = await agent.ask('router_select', {publicTask: safeTask, candidates: candidates.map(candidate => ({snapshotId: candidate.snapshotId, description: candidate.description})), retrieved, summaries}, {snapshotId: 'Candidate ID', rationale: 'Evidence-based reason'});
    ensure(typeof selection?.rationale === 'string' && selection.rationale.trim().length > 0, 'Routing selection requires a rationale before execution');
    const candidate = candidates.find(value => value.snapshotId === selection.snapshotId);
    const decisionId = this.#store.record('routing_committed', {publicTask: safeTask, selection, budget, modelCallBudget: callBudget.limit, planDigest: this.#planDigest, poolDigest: this.#poolDigest, worldDigest: digest(world)});
    const finish = report => {
      const final = {...routingScore(report), routingId, decisionId, selectedSnapshotId: selection.snapshotId ?? null, phase: 'routed_evaluation',
        modelCallBudget: callBudget.limit, modelCalls: callBudget.modelCalls, preparationModelCalls: callBudget.preparationCalls,
        benchmarkId: benchmarkId ?? null, taskId: publicTask.id ?? null, split, protocolId: protocolId ?? null,
        usage: agent.usageSince?.(usageStart, {routingId}) ?? null};
      this.#store.record('routing_finished', final);
      return final;
    };
    if (!candidate) {
      const report = {episodeId: decisionId, decisionId, benchmarkId: benchmarkId ?? null, protocolId: protocolId ?? null, taskId: publicTask.id ?? null, split, phase: 'routed_evaluation', worldDigest: digest(world), success: false, invalidSelection: true, fallback: false, cost: 0, score: null, usage: agent.usageSince?.(usageStart, {routingId}) ?? null};
      this.#store.record('routing_invalid', report);
      return finish(report);
    }
    let report;
    try {
      report = await evaluateWithSkills({...frozenInstance, agent, driver: this.#driver, store: this.#store, world, modules: candidate.modules, budget, decisionId, publicTask: safeTask, phase: 'routed_evaluation', node: candidate.node, benchmarkId, taskId: publicTask.id ?? null, split, protocolId, preparationWorlds, skillDirectory, scoreNormalization});
      if (report.technicalFailure) return finish(report);

      const receipt = verifyRoutedReceipt({...report, cost: report.executionCost}, {store: this.#store, decisionId,
        harnessId: candidate.snapshotId, worldDigest: digest(world), budget});
      this.#store.record('routing_receipt_verified', {decisionId, episodeId: report.episodeId, receiptHash: report.terminalReceipt.hash});
      const entry = {publicTask: safeTask, snapshotId: candidate.snapshotId, success: receipt.success, score: receipt.score,
        usage: report.executionUsage, cost: receipt.cost, split, verified: true, decisionId, episodeId: receipt.episodeId, terminalReceiptHash: report.terminalReceipt.hash};
      this.#memory.push(entry);
      this.#memory = this.#memory.slice(-20000);
      this.#store.record('routing_memory_appended', entry);
      return finish(report);
    } catch (error) {
      const preparation = this.#store.episodes.slice(episodeStart).filter(row => row.phase === 'evaluation_skill_preparation');
      const executed = this.#store.lastEpisodeReport?.decisionId === decisionId ? this.#store.lastEpisodeReport : null;
      const executionCost = report?.executionCost ?? executed?.cost ?? 0;
      const adaptationCost = report?.adaptationCost ?? preparation.reduce((sum, row) => sum + (row.cost ?? 0), 0);
      return finish({...executed, ...report, episodeId: report?.episodeId ?? executed?.episodeId ?? decisionId, harnessId: candidate.snapshotId, worldDigest: digest(world),
        technicalFailure: true, success: false, reason: String(error.message),
        executionCost, adaptationCost, cost: executionCost + adaptationCost,
        costComplete: report?.costComplete ?? false});
    }
  }
}
export async function evaluateWithSkills(options) {
  const evaluationId = randomUUID();
  const task = () => evaluate({...options, evaluationId});
  return options.agent.withScope ? options.agent.withScope({evaluationId, benchmarkId: options.benchmarkId, protocolId: options.protocolId, taskId: options.taskId ?? null, split: options.split ?? null}, task) : task();
}
async function evaluate(options) {
  const usageStart = options.agent.calls?.length ?? 0;
  const frozen = snapshot(options.modules), world = clone(options.world);
  const buildDigest = digest(await hostVerificationCall('world_fingerprint', () => options.driver.fingerprint(clone(world))));
  const instance = await freezeEvaluationInstance({...options, world});
  const prepared = await prepareEvaluationSkills({...options, modules: frozen.modules});
  const episode = await runEpisode({...options, ...instance, world, modules: frozen.modules, skills: prepared.skills, phase: options.phase ?? 'formal_evaluation'});
  ensure(digest(await hostVerificationCall('world_fingerprint', () => options.driver.fingerprint(clone(world)))) === buildDigest, 'World changed during formal evaluation');
  return {...episode, executionUsage: episode.usage, adaptationUsage: prepared.usage, usage: options.agent.usageSince?.(usageStart, {evaluationId: options.evaluationId}) ?? null, executionCost: episode.cost, adaptationCost: prepared.adaptationCost, cost: episode.cost + prepared.adaptationCost, skillKey: prepared.key, skillsReused: prepared.reused, appliedSkills: prepared.skills};
}
export async function oracleEvaluate(options, candidates) {
  const oracleId = randomUUID();
  const task = () => evaluateOracle({...options, oracleId}, candidates);
  return options.agent.withScope ? options.agent.withScope({oracleId}, task) : task();
}
async function evaluateOracle(options, candidates) {
  ensure(candidates.length > 0, 'No Oracle candidates');
  const usageStart = options.agent.calls?.length ?? 0;
  options = {...options, ...await freezeEvaluationInstance(options)};
  const results = [];
  for (const candidate of candidates) {
    ensure(candidate.snapshotId === snapshot(candidate.modules).id, 'Oracle candidate snapshot mismatch');
    results.push({snapshotId: candidate.snapshotId, episode: routingScore(await evaluateWithSkills({...options, modules: candidate.modules, node: candidate.node, phase: 'oracle_candidate'}))});
  }
  const available = results.filter(row => !row.episode.technicalFailure);
  const ranked = available.length ? available : results;
  const normalized = ranked.every(row => Number.isFinite(row.episode.normalizedScore));
  const scored = ranked.every(row => Number.isFinite(row.episode.score));
  const selectionMetric = normalized ? 'normalizedScore' : scored ? 'score' : 'success';
  const direction = selectionMetric === 'score' && options.scoreNormalization?.higherIsBetter === false ? -1 : 1;
  const selected = [...ranked].sort((a, b) => direction * (Number(b.episode[selectionMetric]) - Number(a.episode[selectionMetric])) || a.episode.executionCost - b.episode.executionCost)[0];
  const result = {mode: 'retrospective_oracle', oracleId: options.oracleId, selectionMetric, usage: options.agent.usageSince?.(usageStart, {oracleId: options.oracleId}) ?? null, selected, candidates: results, totalCandidateExecutionCost: results.reduce((sum, row) => sum + row.episode.executionCost, 0), totalCandidateAdaptationCost: results.reduce((sum, row) => sum + row.episode.adaptationCost, 0), totalCost: results.reduce((sum, row) => sum + row.episode.cost, 0)};
  options.store.record('oracle_evaluated', result);
  return result;
}
