import {screeningPolicy} from './screening-policy.mjs';
import fs from 'node:fs';
import {usageReport, scoreSummary, scoreReport, benchmarkScoreReport, routingBenchmarkScoreReport} from './metrics.mjs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';

export const clone = value => structuredClone(value);
export function ensure(condition, message) {
  if (!condition) throw new Error(message);
}
export function stable(value) {
  if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + stable(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
export const digest = value => createHash('sha256').update(stable(value)).digest('hex');
export function writeAtomic(file, text) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  const temporary = file + '.' + randomUUID() + '.tmp';
  const descriptor = fs.openSync(temporary, 'wx', 0o644);
  try {fs.writeFileSync(descriptor, text); fs.fsyncSync(descriptor);}
  finally {fs.closeSync(descriptor);}
  try {fs.renameSync(temporary, file);}
  finally {if (fs.existsSync(temporary)) fs.unlinkSync(temporary);}
}
export function appendLine(file, line) {
  const bytes = Buffer.from(line), descriptor = fs.openSync(file, 'a');
  let size = null;
  try {
    size = fs.fstatSync(descriptor).size;
    for (let written = 0; written < bytes.length;) written += fs.writeSync(descriptor, bytes, written, bytes.length - written);
    fs.fsyncSync(descriptor);
  } catch (error) {
    try {if (size !== null) fs.ftruncateSync(descriptor, size);} catch {error.partialWrite = true;}
    throw error;
  } finally {fs.closeSync(descriptor);}
}
export function identifier(value) {
  return typeof value === 'string' && /^[a-zA-Z][a-zA-Z0-9_-]{0,159}$/.test(value) && !['constructor', 'prototype', '__proto__'].includes(value);
}
export function exact(value, keys, label) {
  ensure(value && typeof value === 'object' && !Array.isArray(value), 'Invalid ' + label);
  ensure(Object.keys(value).every(key => keys.includes(key)) && keys.every(key => Object.hasOwn(value, key)), 'Invalid ' + label + ' fields');
}
export function compose(parent, local) {
  const values = new Map(parent.map(module => [module.moduleId, clone(module)]));
  for (const module of local) values.set(module.moduleId, clone(module));
  return [...values.values()];
}
export function snapshot(modules) {
  const ordered = clone(modules).sort((a, b) => a.moduleId.localeCompare(b.moduleId));
  return {id: digest(ordered), modules: ordered};
}
export function buildTree(taxonomy, assignments, taskIds) {
  ensure(Array.isArray(taxonomy) && taxonomy.length > 0 && new Set(taxonomy).size === taxonomy.length && taxonomy.every(identifier), 'Invalid capability order');
  ensure(new Set(taskIds).size === taskIds.length && assignments.length === taskIds.length, 'Task assignment coverage mismatch');
  const nodes = new Map(), seen = new Set();
  for (const row of assignments) {
    ensure(taskIds.includes(row.taskId) && !seen.has(row.taskId), 'Unknown or duplicate training assignment');
    seen.add(row.taskId);
    ensure(row.requirements.length > 0 && new Set(row.requirements).size === row.requirements.length && row.requirements.every(value => taxonomy.includes(value)), 'Invalid requirements');
    const ordered = taxonomy.filter(value => row.requirements.includes(value));
    let parent = null;
    for (let length = 1; length <= ordered.length; length++) {
      const requirements = ordered.slice(0, length), id = requirements.join('-');
      if (!nodes.has(id)) nodes.set(id, {id, parent, requirements, tasks: [], endpointTasks: []});
      nodes.get(id).tasks.push(row.taskId);
      if (length === ordered.length) nodes.get(id).endpointTasks.push(row.taskId);
      parent = id;
    }
  }
  return [...nodes.values()].sort((a, b) => a.requirements.length - b.requirements.length || a.id.localeCompare(b.id));
}
export function validateConfig(config) {
  ensure(Number.isInteger(config.iterations) && config.iterations > 0, 'Positive iteration count required');
  screeningPolicy(config.screening);
  for (const name of ['trainingTrials', 'validationTrials']) ensure(config[name] === 5, 'Five episodes required for ' + name);
  ensure(Number.isInteger(config.maxBuildAttempts) && config.maxBuildAttempts > 0 && Number.isInteger(config.actionBudget) && config.actionBudget > 0, 'Invalid budget');
  const train = config.trainingTasks.map(task => task.id), unseen = config.unseenTasks.map(task => task.id);
  ensure(new Set(train).size === train.length && new Set(unseen).size === unseen.length && !train.some(id => unseen.includes(id)), 'Training and unseen task IDs must be disjoint');
  return config;
}
export class Store {
  constructor(directory, config) {
    this.directory = path.resolve(directory);
    ensure(!fs.existsSync(path.join(this.directory, 'events.jsonl')), 'Run directory already contains an event ledger');
    fs.mkdirSync(path.join(this.directory, 'objects'), {recursive: true});
    this.modelCalls = [];
    this.episodes = [];
    this.eventOffsets = new Map();
    this.ledgerBytes = 0;
    this.lastEpisodeReport = null;
    this.previous = null;
    this.sequence = 0;
    this.ledgerDamaged = false;
    const configDigest = this.put(config);
    this.record('run_started', {runId: randomUUID(), configDigest});
  }
  put(value) {
    value = JSON.parse(JSON.stringify(value));
    const id = digest(value), file = path.join(this.directory, 'objects', id + '.json');
    if (!fs.existsSync(file)) writeAtomic(file, JSON.stringify(value, null, 2) + '\n');
    return id;
  }
  record(type, payload) {
    ensure(!this.ledgerDamaged, 'The event ledger holds a partial write and cannot be extended');
    const event = {sequence: this.sequence + 1, previous: this.previous, type, payload: JSON.parse(JSON.stringify(payload))};
    event.hash = digest(event);
    const line = JSON.stringify(event) + '\n', length = Buffer.byteLength(line);
    try {appendLine(path.join(this.directory, 'events.jsonl'), line);}
    catch (error) {if (error.partialWrite) this.ledgerDamaged = true; throw error;}
    this.sequence = event.sequence;
    this.previous = event.hash;
    this.eventOffsets.set(event.hash, {offset: this.ledgerBytes, length});
    this.ledgerBytes += length;
    if (type === 'episode_finished') this.lastEpisodeReport = clone(payload);
    if (type === 'routing_finished') this.lastEpisodeReport = null;
    if (type === 'model_usage') this.modelCalls.push(clone(payload));
    const scored = type === 'routing_finished' || (type === 'episode_finished' && payload.phase !== 'routed_evaluation');
    if (scored) {const {events, ...row} = payload; this.episodes.push(clone(row));}
    if (type === 'model_usage' || scored) {
      const phases = [...new Set(this.episodes.map(row => row.phase))];
      this.write('metrics.json', {...usageReport(this.modelCalls), scores: scoreReport(this.episodes), benchmarkScores: benchmarkScoreReport(this.episodes), routingScores: routingBenchmarkScoreReport(this.episodes), scoresByPhase: Object.fromEntries(phases.map(phase => [phase, scoreSummary(this.episodes.filter(row => row.phase === phase))]))});
    }
    return event.hash;
  }
  readEvent(hash) {
    const location = this.eventOffsets.get(hash);
    ensure(location, 'Unknown host event');
    const descriptor = fs.openSync(path.join(this.directory, 'events.jsonl'), 'r');
    const bytes = Buffer.alloc(location.length);
    try {ensure(fs.readSync(descriptor, bytes, 0, bytes.length, location.offset) === bytes.length, 'Truncated host event');}
    finally {fs.closeSync(descriptor);}
    const event = JSON.parse(bytes.toString('utf8'));
    ensure(event.hash === hash && digest(Object.fromEntries(Object.entries(event).filter(([key]) => key !== 'hash'))) === hash, 'Damaged host event');
    return event;
  }
  write(name, value) {
    ensure(/^[a-zA-Z0-9_-]+\.json$/.test(name), 'Invalid output filename');
    writeAtomic(path.join(this.directory, name), JSON.stringify(value, null, 2) + '\n');
  }
}
export function verifyLedger(file) {
  let previous = null, sequence = 0;
  const lines = fs.readFileSync(file, 'utf8').split('\n'), truncatedTail = lines.at(-1) !== '';
  for (const line of lines.slice(0, -1)) {
    let parsed;
    try {parsed = JSON.parse(line);} catch {throw new Error('Ledger integrity failure');}
    const {hash, ...event} = parsed;
    ensure(event.sequence === ++sequence && event.previous === previous && digest(event) === hash, 'Ledger integrity failure');
    previous = hash;
  }
  return {events: sequence, head: previous, truncatedTail};
}
