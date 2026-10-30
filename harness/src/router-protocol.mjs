import fs from 'node:fs';
import {clone, digest, ensure, snapshot} from './core.mjs';
import {validate} from './runtime.mjs';
import {normalizeMedia} from './media.mjs';

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const forbidden = new Set(['evaluationcapabilitylabels', 'requiredcapabilities', 'capabilitylabels', 'capabilitypath',
  'missingcapabilities', 'satisfiedcapabilities', 'defecttypesobserved', 'evaluationlabels', 'groundtruth',
  'privatelabels', 'preparationtrajectories', 'evaluationskills', 'futureoutcomes']);
function publicOnly(value) {
  if (!value || typeof value !== 'object') return;
  for (const [key, child] of Object.entries(value)) {
    ensure(!forbidden.has(key.replace(/[^a-z]/gi, '').toLowerCase()), 'Private evaluation field in public routing context: ' + key);
    publicOnly(child);
  }
}
function keys(value, allowed, name) {
  ensure(object(value) && Object.keys(value).every(key => allowed.includes(key)), 'Unsupported ' + name + ' field');
}
export function publicRoutingTask(task, metadataKeys = []) {
  keys(task, ['id', 'goal', 'initialObservation', 'metadata', 'images'], 'public task');
  publicOnly(task);
  const metadata = task.metadata ?? {};
  ensure(object(metadata), 'Public metadata must be an object');
  for (const [key, value] of Object.entries(metadata)) {
    ensure(metadataKeys.includes(key), 'Undeclared public metadata field: ' + key);
    ensure(value === null || ['string', 'boolean'].includes(typeof value) || typeof value === 'number' && Number.isFinite(value), 'Public metadata values must be finite scalars');
  }

  return normalizeMedia(clone({goal: task.goal ?? null, initialObservation: task.initialObservation ?? null,
    metadata, ...(task.images === undefined ? {} : {images: task.images})}));
}
export function freezeRoutingPlan(input) {
  keys(input, ['schema', 'protocolId', 'split', 'publicMetadataKeys', 'candidates', 'tasks', 'excludedNodes'], 'routing plan');
  ensure(input.schema === 'trinity-routing-plan-v1' && text(input.protocolId), 'Versioned routing plan and protocolId required');
  ensure(['train', 'unseen'].includes(input.split), 'Routing plan split must be train or unseen');
  const metadataKeys = input.publicMetadataKeys ?? [];
  ensure(Array.isArray(metadataKeys) && metadataKeys.every(text) && new Set(metadataKeys).size === metadataKeys.length, 'Invalid public metadata allowlist');
  publicOnly(Object.fromEntries(metadataKeys.map(key => [key, null])));
  ensure(Array.isArray(input.candidates) && input.candidates.length > 0, 'Frozen Harness pool required');
  const excludedNodes = input.excludedNodes ?? [];
  ensure(Array.isArray(excludedNodes) && excludedNodes.every(text), 'Invalid excluded nodes');
  const candidates = input.candidates.map(candidate => {
    ensure(!excludedNodes.includes(candidate.node), 'Node excluded from standalone Harness routing: ' + candidate.node);
    keys(candidate, ['snapshotId', 'modules', 'node', 'description', 'endpointTaskIds', 'sourceNodes'], 'Harness candidate');
    if (candidate.endpointTaskIds !== undefined) ensure(Array.isArray(candidate.endpointTaskIds) &&
      candidate.endpointTaskIds.length > 0 && candidate.endpointTaskIds.every(text) &&
      new Set(candidate.endpointTaskIds).size === candidate.endpointTaskIds.length,
      'Independent Harness requires direct training endpoint tasks');
    ensure(Array.isArray(candidate.modules) && text(candidate.description) && text(candidate.node), 'Candidate modules, node and public description required');
    if (candidate.sourceNodes !== undefined) {
      ensure(Array.isArray(candidate.sourceNodes) && candidate.sourceNodes.length > 1, 'Merged candidate requires multiple source nodes');
      for (const source of candidate.sourceNodes) {
        keys(source, ['node', 'endpointTaskIds', 'description'], 'candidate source node');
        ensure(text(source.node) && text(source.description), 'Source node and description required');
        ensure(!excludedNodes.includes(source.node), 'Node excluded from standalone Harness routing: ' + source.node);
        ensure(Array.isArray(source.endpointTaskIds) && source.endpointTaskIds.length > 0 && source.endpointTaskIds.every(text) &&
          new Set(source.endpointTaskIds).size === source.endpointTaskIds.length, 'Source node requires direct training endpoint tasks');
      }
      const nodes = candidate.sourceNodes.map(source => source.node);
      ensure(new Set(nodes).size === nodes.length && candidate.node === nodes[0], 'Invalid merged candidate node provenance');
      const endpoints = [...new Set(candidate.sourceNodes.flatMap(source => source.endpointTaskIds))].sort();
      ensure(Array.isArray(candidate.endpointTaskIds) && digest([...candidate.endpointTaskIds].sort()) === digest(endpoints), 'Merged candidate endpoint provenance mismatch');
    }
    candidate.modules.forEach(validate);
    ensure(candidate.snapshotId === snapshot(candidate.modules).id, 'Candidate snapshot mismatch');
    return clone(candidate);
  });
  const poolIds = candidates.map(candidate => candidate.snapshotId);
  ensure(new Set(poolIds).size === poolIds.length, 'Duplicate Harness snapshot in frozen pool');
  ensure(Array.isArray(input.tasks) && input.tasks.length > 0, 'Ordered routing task manifest required');
  const tasks = input.tasks.map(task => {
    keys(task, ['taskId', 'publicTask', 'world', 'candidateIds', 'budget', 'modelCallBudget', 'benchmarkId',
      'preparationWorlds', 'skillDirectory', 'scoreNormalization', 'instance', 'expectedInitialStateHash'], 'routing task');
    ensure(text(task.taskId) && text(task.benchmarkId) && object(task.world), 'Task ID, benchmark ID and world required');
    if (task.instance !== undefined) ensure(object(task.instance), 'Invalid routing instance');
    if (task.expectedInitialStateHash !== undefined) ensure(object(task.instance) && text(task.expectedInitialStateHash), 'Frozen routing state requires an instance and hash');
    for (const key of ['budget', 'modelCallBudget']) ensure(Number.isInteger(task[key]) && task[key] > 0, 'Positive ' + key + ' required');
    const candidateIds = task.candidateIds ?? poolIds;
    ensure(Array.isArray(candidateIds) && candidateIds.length > 0 && new Set(candidateIds).size === candidateIds.length && candidateIds.every(id => poolIds.includes(id)), 'Compatible candidates must be a subset of the frozen pool');
    if (task.publicTask?.id !== undefined) ensure(task.publicTask.id === task.taskId, 'Public task ID differs from manifest ID');
    return {...clone(task), publicTask: publicRoutingTask(task.publicTask, metadataKeys), candidateIds: [...candidateIds]};
  });
  ensure(new Set(tasks.map(task => task.taskId)).size === tasks.length, 'Duplicate task instance in manifest');
  return JSON.parse(JSON.stringify({schema: input.schema, protocolId: input.protocolId, split: input.split,
    publicMetadataKeys: [...metadataKeys], excludedNodes: [...excludedNodes], candidates, tasks}));
}
export function orderedTrainingMemory(memory, metadataKeys) {
  if (!memory.length) return [];
  const files = new Set(memory.map(row => row.provenance.ledgerFile));
  ensure(files.size === 1, 'Import training memory from one ordered source ledger');
  const file = [...files][0];
  const sourceIds = fs.readFileSync(file, 'utf8').trim().split('\n').map(JSON.parse)
    .filter(event => event.type === 'episode_finished' && event.payload.phase === 'initial_training_exploration' && event.payload.split === 'train' && !event.payload.technicalFailure)
    .map(event => event.hash);
  ensure(digest(memory.map(row => row.provenance.episodeEventHash)) === digest(sourceIds), 'Import the complete training memory once in source file order');
  return memory.map(row => ({...clone(row), publicTask: publicRoutingTask(row.publicTask, metadataKeys)})).slice(-20000);
}
export function memoryForModel(row) {
  return clone({publicTask: row.publicTask, snapshotId: row.snapshotId, success: row.success, score: row.score, cost: row.cost});
}
export function boundedRoutingAgent(agent, budget) {
  const proxy = {
    get calls() {return agent.calls;},
    get scope() {return agent.scope;},
    async ask(operation, context, contract, scope) {
      const prompt = fs.readFileSync(new URL('../prompts/router.txt', import.meta.url), 'utf8');
      ensure(digest(prompt) === budget.promptDigest, 'Router prompt changed after registration');
      const preparation = operation === 'skills_prepare' || scope?.phase === 'evaluation_skill_preparation';
      const key = preparation ? 'preparationCalls' : 'modelCalls';
      const ceiling = preparation ? budget.preparationLimit : budget.limit;
      ensure(budget[key] < ceiling, preparation ? 'Skill preparation model-call budget exhausted' : 'Routing model-call budget exhausted');
      budget[key]++;
      return agent.ask(operation, clone(context), clone(contract), clone(scope));
    }
  };
  if (agent.withScope) proxy.withScope = agent.withScope.bind(agent);
  if (agent.usageSince) proxy.usageSince = agent.usageSince.bind(agent);
  return proxy;
}
