import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {clone, digest, ensure, verifyLedger} from './core.mjs';
import {loadTrainingMemory} from './receipts.mjs';

const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const events = directory => fs.readFileSync(path.join(directory, 'events.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const pinnedFiles = ['handoff.json', 'capabilities/capabilities.json', 'train/task-capability-gaps.json'];

export function stage2Binding(directory) {
  directory = path.resolve(directory);
  return {directory, files: Object.fromEntries(pinnedFiles.map(name => [name, digest(read(path.join(directory, name)))])),
    handoffDigest: digest(read(path.join(directory, 'handoff.json')))};
}

export function completeTraining({store, config, baseline}) {
  const memoryDirectory = config.trainingMemoryDirectory ?? store.directory;
  const memory = loadTrainingMemory(memoryDirectory);
  ensure(memory.length > 0, 'Completed training requires verified initial training memory');
  const expected = baseline.flatMap(entry => entry.rows.map(row => row.episodeId)).sort();
  ensure(digest(memory.map(row => row.episodeId).sort()) === digest(expected), 'Training memory does not cover the initial training records');
  const memorySource = {schema: 'trinity-training-memory-source-v1', directory: path.resolve(memoryDirectory),
    digest: digest(memory), count: memory.length};
  store.write('training-memory-source.json', memorySource);
  const names = ['tree.json', 'routing-candidates.json', 'summary.json', 'checkpoint-' + config.iterations + '.json', 'training-memory-source.json'];
  const artifact = {schema: 'trinity-training-complete-v1', iterations: config.iterations,
    files: Object.fromEntries(names.map(name => [name, digest(read(path.join(store.directory, name)))])),
    stage2: config.stage2Binding ?? null,
    trainTaskIds: [...config.trainingTasks, ...(config.baselineTasks ?? [])].map(task => task.id),
    unseenTaskIds: config.unseenTasks.map(task => task.id)};
  const event = store.record('training_completed', {artifactDigest: digest(artifact)});
  store.write('training-complete.json', {artifact, hash: digest(artifact), event});
  return artifact;
}

export function verifyTrainingCompletion(directory, stage2 = null) {
  ensure(typeof directory === 'string' && directory.length > 0, 'Completed training run is required');
  directory = path.resolve(directory);
  const envelope = read(path.join(directory, 'training-complete.json'));
  const {artifact, hash, event} = envelope;
  ensure(artifact?.schema === 'trinity-training-complete-v1' && digest(artifact) === hash, 'Invalid training completion record');
  const ledger = verifyLedger(path.join(directory, 'events.jsonl'));
  const last = events(directory).at(-1);
  ensure(last.hash === event && ledger.head === event && last.type === 'training_completed' && last.payload.artifactDigest === hash, 'Training completion is not the final verified event');
  const names = ['tree.json', 'routing-candidates.json', 'summary.json', 'checkpoint-' + artifact.iterations + '.json', 'training-memory-source.json'];
  ensure(digest(Object.keys(artifact.files).sort()) === digest(names.sort()), 'Incomplete training artifact pins');
  for (const name of names) ensure(digest(read(path.join(directory, name))) === artifact.files[name], 'Completed training artifact changed: ' + name);
  const summary = read(path.join(directory, 'summary.json'));
  ensure(summary.iterations === artifact.iterations && summary.summary.length === summary.nodes * summary.iterations, 'Training is incomplete');
  const tree = read(path.join(directory, 'tree.json'));
  const completed = new Set(summary.summary.map(row => row.node + ':' + row.iteration));
  ensure(completed.size === summary.summary.length && tree.nodes.every(node => Array.from({length: artifact.iterations}, (_, i) => completed.has(node.id + ':' + (i + 1))).every(Boolean)), 'Missing completed node iterations');
  if (artifact.stage2) {
    const current = stage2Binding(stage2 ?? artifact.stage2.directory);
    ensure(digest(current.files) === digest(artifact.stage2.files), 'Training taxonomy, assignments or split changed');
  } else ensure(stage2 === null, 'This training run has no Stage 2 binding');
  return {directory, ...clone(envelope)};
}

export function defaultTrainingMemory(directory) {
  const complete = verifyTrainingCompletion(directory);
  const source = read(path.join(complete.directory, 'training-memory-source.json'));
  const memory = loadTrainingMemory(source.directory);
  ensure(memory.length > 0 && memory.length === source.count && digest(memory) === source.digest, 'Training memory source changed or is empty');
  return memory;
}

export function verifyUnseenLedger(trainingDirectory, ledgerFile, stage2 = null) {
  const complete = verifyTrainingCompletion(trainingDirectory, stage2);
  verifyLedger(ledgerFile);
  const rows = fs.readFileSync(ledgerFile, 'utf8').trim().split('\n').map(JSON.parse);
  const authorizations = rows.filter(row => row.type === 'unseen_exploration_authorized');
  ensure(authorizations.length === 1 && authorizations[0].payload.completionHash === complete.hash &&
    authorizations[0].payload.completionEvent === complete.event, 'Unseen records were not collected after this completed training run');
  const authorization = authorizations[0];
  const episodes = rows.filter(row => row.type === 'episode_started');
  ensure(episodes.length > 0 && episodes.every(row => row.sequence > authorization.sequence && row.payload.split === 'unseen' && complete.artifact.unseenTaskIds.includes(row.payload.taskId)), 'Invalid Unseen execution order or task cohort');
  return complete;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try {
    const [operation, directory, stage2, ledger] = process.argv.slice(2);
    ensure(['verify', 'verify-unseen'].includes(operation), 'Unknown protocol check');
    const result = operation === 'verify-unseen' ? verifyUnseenLedger(directory, ledger, stage2) : verifyTrainingCompletion(directory, stage2);
    console.log(JSON.stringify(result));
  } catch (error) {console.error(error.message); process.exitCode = 1;}
}
