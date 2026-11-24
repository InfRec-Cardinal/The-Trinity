import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {randomUUID, randomBytes, createHash} from 'node:crypto';
import {fileURLToPath, pathToFileURL} from 'node:url';
import './public/tree.js';
import {EnvironmentManager} from './lib/environments.mjs';
import {modelErrorPayload, connectionRelay} from './lib/model-io.mjs';
import {closeLevelEngine, configureLevelEngine} from './lib/level-engine.mjs';

                                                                              
configureLevelEngine({handleSignals: false});

const {validateTree} = globalThis.TrinityTree;

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const option = (name, fallback) => {const i = args.indexOf('--' + name); return i >= 0 && args[i + 1] ? args[i + 1] : fallback;};
const CODE = path.resolve(option('code', path.join(ROOT, '..')));
const ENV = path.resolve(option('env-package', path.join(ROOT, '..', 'level-api-44')));
const RUNS = path.resolve(option('runs', path.join(ROOT, 'runs')));
const VENDOR = path.join(ENV, 'vendor');
const RELAY = {baseUrl: option('base-url', 'https://api.anthropic.com'), model: option('model', 'claude-opus-5'), auth: option('auth', 'bearer'), webSearch: option('web-search', 'basic')};
const spendOption = args.indexOf('--max-usd');
const SCRATCH_MAX_USD = Number(spendOption < 0 ? '30' : args[spendOption + 1]);
if (!Number.isFinite(SCRATCH_MAX_USD) || SCRATCH_MAX_USD <= 0) throw Error('--max-usd requires a finite positive number');
const TREES = path.resolve(option('trees', path.join(ROOT, 'trees')));
const HOST = '127.0.0.1', PORT = Number(option('port', '8188'));
const ALLOW_LOCAL = args.includes('--allow-local-env');
const environments = new EnvironmentManager({root: option('environment-root', path.join(ROOT, '..', 'environments')), python: option('environment-python', process.env.TRINITY_ENV_PYTHON || (process.platform === 'win32' ? 'python' : 'python3'))});
const IMAGE_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg'};
const renderCache = new Map(), RENDER_CACHE_BYTES = 256 * 1024 * 1024, RENDER_SLOTS = 2;
let renderEngine = null, rendersRunning = 0, renderCacheBytes = 0;
const renderWaiters = [];
async function withRenderSlot(fn) {
  if (rendersRunning >= RENDER_SLOTS) await new Promise(resolve => renderWaiters.push(resolve));
  rendersRunning++;
  try {return await fn();} finally {rendersRunning--; renderWaiters.shift()?.();}
}
function renderLevelCached({source, node, variant, actions}) {
  const key = createHash('sha256').update(JSON.stringify([source, node, variant, actions])).digest('hex');
  const hit = renderCache.get(key);
  if (hit) {renderCache.delete(key); renderCache.set(key, hit); return hit.job;}
  const entry = {bytes: 0, job: null};
  entry.job = withRenderSlot(async () => {
    renderEngine ??= await import(pathToFileURL(path.join(ROOT, 'lib', 'level-engine.mjs')).href);
    return renderEngine.renderLevel({source, node, variant, actions, vendorDir: VENDOR});
  }).then(out => {
    entry.bytes = out.frames.reduce((sum, frame) => sum + frame.length, 0);
    renderCacheBytes += entry.bytes;
    for (const [k, e] of renderCache) {
      if (renderCacheBytes <= RENDER_CACHE_BYTES) break;
      if (e !== entry && e.bytes) {renderCache.delete(k); renderCacheBytes -= e.bytes;}
    }
    return out;
  });
  entry.job.catch(() => {if (renderCache.get(key) === entry) renderCache.delete(key);});
  renderCache.set(key, entry);
  return entry.job;
}

const TOKEN = randomBytes(18).toString('hex');
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json'};
const jobs = new Map();
let pkg = null;

async function loadPackage() {
  const {readEnvironmentPackage} = await import(pathToFileURL(path.join(CODE, 'src/environment-package.mjs')).href);
  const p = readEnvironmentPackage(ENV);
  return {descriptor: p.descriptor, curriculum: p.curriculum, revision: p.revision};
}

const send = (res, status, body, type = 'application/json') => {
  if (res.destroyed || res.writableEnded) return;
  res.writeHead(status, {'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'});
  res.end(type === 'application/json' ? JSON.stringify(body) : body);
};
function streamFile(res, file, headers) {
  const stream = fs.createReadStream(file);
  for (const [name, value] of Object.entries(headers)) res.setHeader(name, value);
  stream.on('error', error => {
    if (res.destroyed || res.writableEnded) return;
    if (!res.headersSent) send(res, error.code === 'ENOENT' ? 404 : 500, {error: 'File could not be read'});
    else res.destroy();
  });
  res.once('close', () => stream.destroy());
  stream.pipe(res);
}
const body = req => new Promise((resolve, reject) => {
  let text = '', settled = false;
  const finish = (error, value) => {
    if (settled) return;
    settled = true;
    req.off('data', data); req.off('end', end); req.off('aborted', aborted);
    if (error) reject(error); else resolve(value);
  };
  const data = chunk => {text += chunk; if (text.length > 4_000_000) {finish(Error('Request too large')); req.destroy();}};
  const end = () => {try {finish(null, text ? JSON.parse(text) : {});} catch {finish(Error('Invalid JSON'));}};
  const aborted = () => finish(Error('Request aborted'));
  const failed = error => finish(error);
                                                                                
  req.setEncoding('utf8');
  req.on('data', data); req.on('end', end); req.on('aborted', aborted); req.once('error', failed);
});
const safeName = name => typeof name === 'string' && name.length > 0 && Buffer.byteLength(name, 'utf8') <= 240 &&
  !/[\u0000-\u001f\u007f-\u009f<>:"/\\|?*]/u.test(name) && !/^[. ]|[. ]$/u.test(name) && !name.includes('..') &&
  !/^(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\.|$)/iu.test(name);

function treeDirectory() {
  fs.mkdirSync(TREES, {recursive: true});
  const canonical = fs.realpathSync(TREES);
  const fd = fs.openSync(canonical, fs.constants.O_RDONLY | (fs.constants.O_DIRECTORY || 0) | (fs.constants.O_NOFOLLOW || 0));
  const directory = process.platform === 'linux' ? '/proc/self/fd/' + fd : canonical;
  return {directory, close: () => fs.closeSync(fd)};
}
function treeEntry(file) {
  try {
    const value = fs.lstatSync(file);
    if (!value.isFile() || value.isSymbolicLink()) throw Error('Tree entry must be a regular file, not a link');
    return value;
  } catch (error) {if (error.code === 'ENOENT') return null; throw error;}
}
function readTreeFile(file) {
  if (!treeEntry(file)) return null;
  const fd = fs.openSync(file, fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0) | (fs.constants.O_NONBLOCK || 0));
  try {
    if (!fs.fstatSync(fd).isFile()) throw Error('Tree entry must be a regular file');
    return {value: JSON.parse(fs.readFileSync(fd, 'utf8'))};
  } finally {fs.closeSync(fd);}
}
function writeTreeFile(file, tree) {
  treeEntry(file);
  const temp = path.join(path.dirname(file), '.' + randomUUID() + '.tmp');
  let fd;
  try {
    fd = fs.openSync(temp, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0), 0o600);
    fs.writeFileSync(fd, JSON.stringify(tree, null, 2) + '\n'); fs.fsyncSync(fd); fs.closeSync(fd); fd = undefined;
    treeEntry(file);
    fs.renameSync(temp, file);
  } finally {if (fd !== undefined) fs.closeSync(fd); fs.rmSync(temp, {force: true});}
}

function signalJob(job, signal) {
  if (process.platform !== 'win32' && job.child.pid) {
    try {process.kill(-job.child.pid, signal); return;}
    catch (error) {if (error.code !== 'ESRCH') throw error;}
  }
  job.child.kill(signal);
}
function stopJob(job) {
  if (job.child.exitCode !== null || job.child.signalCode !== null) return;
  job.status = 'stopping';
  signalJob(job, 'SIGTERM');
  if (!job.stopTimer) {
    job.stopTimer = setTimeout(() => signalJob(job, 'SIGKILL'), 5000);
    job.stopTimer.unref();
  }
}
function runSnapshot(job) {
  return {id: job.id, requestId: job.requestId, mode: job.mode, status: job.status, out: job.out, tree: job.initialTree};
}
function startJob({mode, tree, apiKey, agent, requestId, relay}) {
  const id = randomUUID(), out = path.join(RUNS, new Date().toISOString().replace(/[:.]/g, '-') + '-' + id.slice(0, 8));
  fs.mkdirSync(out, {recursive: true});
  const eventLog = path.join(out, '.studio-events.jsonl');
  fs.writeFileSync(eventLog, '', {flag: 'wx', mode: 0o600});
  const job = {id, mode, out, eventLog, requestId, initialTree: mode === 'evolve' ? structuredClone(tree) : globalThis.TrinityTree.emptyTree('scratch'),
    status: 'running', sequence: 0, persistedSequence: 0, clients: new Set(), child: null, fallback: [], logError: false, failure: null, stopTimer: null};
  const deliver = record => {
    for (const client of job.clients) {
      try {client.write('id: ' + record.id + '\ndata: ' + JSON.stringify(record.event) + '\n\n');}
      catch {job.clients.delete(client); client.destroy();}
    }
  };
  const fail = message => {
    if (job.failure && (!job.logError || job.fallback.some(record => record.event.type === 'failed'))) return;
    job.failure ||= String(message).replaceAll(apiKey || '\u0000', '[redacted]').slice(0, 1000);
    const ended = job.child.exitCode !== null || job.child.signalCode !== null;
    if (ended) job.status = 'failed'; else stopJob(job);
    push({type: 'failed', message: job.failure});
    if (ended && !job.fallback.some(record => record.event.type === 'status' && record.event.status === 'failed')) push({type: 'status', status: 'failed'});
  };
  const redact = value => value.replaceAll(apiKey || '\u0000', '[redacted]');
  const push = event => {
    if (typeof event.message === 'string') event = {...event, message: redact(event.message)};
    if (job.logError) {
      if (!['failed', 'status'].includes(event.type)) return;
      const record = {id: ++job.sequence, event}; job.fallback.push(record); deliver(record); return;
    }
    const record = {id: job.sequence + 1, event};
    try {fs.appendFileSync(job.eventLog, JSON.stringify(record) + '\n');}
    catch (error) {job.logError = true; fail('Run event log could not be saved: ' + error.message); return;}
    job.sequence = record.id; job.persistedSequence = record.id; deliver(record);
  };
  job.events = () => {
    const records = [];
    try {
      for (const line of fs.readFileSync(job.eventLog, 'utf8').split('\n')) {
        if (job.logError && records.length === job.persistedSequence) break;
        if (!line) continue;
        const record = JSON.parse(line);
        if (record?.id !== records.length + 1 || record.id > job.persistedSequence || !record.event || typeof record.event.type !== 'string') throw new Error('Invalid event sequence or event payload');
        records.push(record);
      }
      if (records.length !== job.persistedSequence) throw new Error('Incomplete event log');
    } catch (error) {records.length = 0; job.logError = true; fail('Run event log could not be read: ' + error.message);}
    return (job.logError ? records.filter(record => record.event.type !== 'status') : records).concat(job.fallback);
  };
  const child = spawn(process.execPath, [path.join(ROOT, 'lib/worker.mjs')], {stdio: ['pipe', 'pipe', 'pipe'], detached: process.platform !== 'win32',
    env: {PATH: process.env.PATH ?? '', HOME: process.env.HOME ?? '', NODE_ENV: 'production',
      ...(process.env.PLAYWRIGHT_MODULE ? {PLAYWRIGHT_MODULE: process.env.PLAYWRIGHT_MODULE} : {}),
      ...(process.env.TRINITY_PYTHON ? {TRINITY_PYTHON: process.env.TRINITY_PYTHON} : {})}});
  job.child = child;
  child.on('error', error => fail('Worker could not be started: ' + error.message));
  child.stdin.on('error', error => fail('Worker input could not be delivered: ' + error.message));
  let rest = '', stderrRest = '';
  const outputLine = line => {
    if (!line.trim()) return;
    let event;
    try {event = JSON.parse(line);} catch {}
    if (!event || typeof event !== 'object' || Array.isArray(event) || typeof event.type !== 'string' || event.type === 'status') event = {type: 'log', message: Array.from(redact(line)).slice(0, 500).join('')};
    push(event);
  };
  const flushStderr = final => {
    let boundary = final ? stderrRest.length : Math.max(0, stderrRest.length - (apiKey ? apiKey.length - 1 : 0));
    const left = stderrRest.charCodeAt(boundary - 1), right = stderrRest.charCodeAt(boundary);
    if (left >= 0xd800 && left <= 0xdbff && right >= 0xdc00 && right <= 0xdfff) boundary--;
    let offset = 0, message = '';
    while (offset < boundary) {
      const next = apiKey ? stderrRest.indexOf(apiKey, offset) : -1;
      if (next >= 0 && next < boundary) {message += stderrRest.slice(offset, next) + '[redacted]'; offset = next + apiKey.length;}
      else {message += stderrRest.slice(offset, boundary); offset = boundary;}
    }
    stderrRest = stderrRest.slice(offset);
    if (message) push({type: 'log', message: Array.from(message).slice(-1000).join('')});
  };
  child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
  child.stdout.on('data', chunk => {
    const lines = (rest + chunk).split('\n'); rest = lines.pop();
    for (const line of lines) outputLine(line);
  });
  child.stdout.on('end', () => {outputLine(rest); rest = '';});
  child.stderr.on('data', chunk => {stderrRest += chunk; flushStderr(false);});
  child.stderr.on('end', () => flushStderr(true));
  child.on('exit', () => {if (process.platform !== 'win32') signalJob(job, 'SIGKILL');});
  child.on('close', code => {
    job.closed = true;
    clearTimeout(job.stopTimer); job.stopTimer = null;
    job.status = job.failure ? 'failed' : job.status === 'stopping' ? 'stopped' : code === 0 ? 'done' : 'failed';
    push({type: 'status', status: job.status});
    for (const client of job.clients) client.end();
    job.clients.clear();
  });
  child.stdin.end(JSON.stringify({mode, tree, apiKey: apiKey ?? null, agent, code: CODE, env: ENV, out, allowLocalEnvironment: ALLOW_LOCAL,
    relay: agent === 'model' ? relay : null, spendLimitUsd: agent === 'model' ? SCRATCH_MAX_USD : null}));
  jobs.set(id, job);
  return job;
}

async function api(req, res, url) {
  if (req.method !== 'GET' && req.headers['x-studio-token'] !== TOKEN) return send(res, 403, {error: 'Invalid session token'});
  if (req.method === 'GET' && url.pathname === '/api/info') {
    return send(res, 200, {token: TOKEN, allowLocalEnvironment: ALLOW_LOCAL, package: pkg ? {id: pkg.descriptor.id, version: pkg.descriptor.version, revision: pkg.revision} : null});
  }
  if (req.method === 'GET' && url.pathname === '/api/environments') {
    if (environments.state.phase === 'idle') void environments.check();
    return send(res, 200, environments.snapshot());
  }
  if (req.method === 'POST' && url.pathname === '/api/environments/check') {
    void environments.check();
    return send(res, 202, environments.snapshot());
  }
  if (req.method === 'POST' && url.pathname === '/api/environments/download') {
    if ([...jobs.values()].some(j => ['running', 'stopping'].includes(j.status))) return send(res, 409, {error: 'A run is already in progress'});
    if (!environments.keys.length) return send(res, 503, {error: environments.state.error || 'No downloadable assets configured'});
    if (environments.busy) return send(res, 202, environments.snapshot());
    void environments.download();
    return send(res, 202, environments.snapshot());
  }
  if (req.method === 'GET' && url.pathname.startsWith('/api/frames/')) {
    const parts = url.pathname.slice('/api/frames/'.length).split('/').map(decodeURIComponent);
    let file = null;
    if (parts[0] === 'run' && parts.length === 3 && /^[A-Za-z0-9_-]+-r\d+-f\d+\.(png|jpg)$/.test(parts[2])) {
      const job = jobs.get(parts[1]);
      const dir = job ? job.out : (/^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$/.test(parts[1]) && parts[1] !== '..' ? path.join(RUNS, parts[1]) : null);
      const full = dir && path.join(dir, 'frames', parts[2]);
      if (full && fs.existsSync(full)) file = full;
    }
    if (!file) return send(res, 404, {error: 'Frame not found'});
    return streamFile(res, file, {'Content-Type': IMAGE_TYPES[path.extname(file)] ?? 'image/png', 'Cache-Control': 'max-age=3600', 'X-Content-Type-Options': 'nosniff'});
  }
  if (req.method === 'POST' && url.pathname === '/api/render') {
    const input = await body(req);
    if (!ALLOW_LOCAL) return send(res, 400, {error: 'Start the studio with --allow-local-env to render levels'});
    if (typeof input.source !== 'string' || !input.source.trim()) return send(res, 400, {error: 'Level source is required'});
    if (typeof input.node !== 'string' || !/^[a-z][a-z0-9_-]{0,159}$/.test(input.node)) return send(res, 400, {error: 'Invalid level node'});
    if (!Number.isInteger(input.variant) || input.variant < 0 || input.variant > 63) return send(res, 400, {error: 'Invalid variant'});
    if (!Array.isArray(input.actions) || input.actions.length > 300) return send(res, 400, {error: 'Invalid action tape'});
    try {
      const out = await renderLevelCached({source: input.source, node: input.node, variant: input.variant, actions: input.actions});
      return send(res, 200, {frames: out.frames, receipts: out.receipts, ended: out.inspect.ended, success: out.inspect.success, budget: out.inspect.budget, rules: out.inspect.rules});
    } catch (error) {return send(res, 422, {error: 'Level could not be rendered: ' + String(error.message).slice(0, 300)});}
  }
  if (req.method === 'GET' && url.pathname === '/api/trees') {
    const root = treeDirectory();
    try {return send(res, 200, fs.readdirSync(root.directory, {withFileTypes: true}).filter(e => e.isFile() && safeName(e.name) && e.name.endsWith('.json')).map(e => e.name).sort());}
    finally {root.close();}
  }
  const treeMatch = /^\/api\/trees\/([^/]+)$/.exec(url.pathname);
  if (treeMatch) {
    let name;
    try {name = decodeURIComponent(treeMatch[1]);} catch {return send(res, 400, {error: 'Invalid tree file name'});}
    if (!safeName(name) || !name.endsWith('.json')) return send(res, 400, {error: 'Invalid tree file name'});
    if (!['GET', 'PUT'].includes(req.method)) return send(res, 405, {error: 'Method not allowed'});
    const tree = req.method === 'PUT' ? await body(req) : null;
    if (req.method === 'PUT') {const errors = validateTree(tree); if (errors.length) return send(res, 400, {error: errors.join('; ')});}
    const root = treeDirectory();
    try {
      const file = path.join(root.directory, name);
      if (req.method === 'GET') {const result = readTreeFile(file); return result ? send(res, 200, result.value) : send(res, 404, {error: 'Not found'});}
      writeTreeFile(file, tree);
      return send(res, 200, {saved: name});
    } catch (error) {return send(res, 400, {error: error.message});}
    finally {root.close();}
  }
  if (req.method === 'POST' && url.pathname === '/api/design') {
    const input = await body(req);
    let relay;
    try {relay = connectionRelay(input.connection, RELAY);} catch (error) {return send(res, 400, {error: error.message});}
    if (typeof input.apiKey !== 'string' || input.apiKey.trim().length < 8) return send(res, 400, {error: 'Enter a model API key in Settings'});
    if (typeof input.capabilityText !== 'string' || input.capabilityText.trim().length < 4) return send(res, 400, {error: 'Describe the capability first'});
    try {
      const {judgeDesign} = await import(pathToFileURL(path.join(ROOT, 'lib', 'design.mjs')).href);
      const result = await judgeDesign({code: CODE, apiKey: input.apiKey.trim(), relay, capabilityText: input.capabilityText, existingCapabilities: input.existingCapabilities});
      return send(res, 200, result);
    } catch (error) {return send(res, 502, modelErrorPayload(error, input.apiKey.trim()));}
  }
  if (req.method === 'POST' && url.pathname === '/api/create-level') {
    const input = await body(req);
    let relay;
    try {relay = connectionRelay(input.connection, RELAY);} catch (error) {return send(res, 400, {error: error.message});}
    if (!ALLOW_LOCAL) return send(res, 400, {error: 'Start the studio with --allow-local-env to render levels'});
    if (typeof input.apiKey !== 'string' || input.apiKey.trim().length < 8) return send(res, 400, {error: 'Enter a model API key in Settings'});
    if (!input.design || typeof input.design !== 'object') return send(res, 400, {error: 'A design object is required'});
    try {
      const {createLevel} = await import(pathToFileURL(path.join(ROOT, 'lib', 'create-level.mjs')).href);
      const result = await createLevel({code: CODE, apiKey: input.apiKey.trim(), relay, design: input.design, vendorDir: VENDOR});
      return send(res, 200, result);
    } catch (error) {return send(res, 502, modelErrorPayload(error, input.apiKey.trim()));}
  }
  if (req.method === 'POST' && url.pathname === '/api/runs') {
    const input = await body(req);
    let relay;
    try {relay = connectionRelay(input.connection, RELAY);} catch (error) {return send(res, 400, {error: error.message});}
                                                                               
    if (stopping) return send(res, 503, {error: 'Studio is shutting down'});
    if (input.requestId !== undefined && (typeof input.requestId !== 'string' || !/^[0-9a-f-]{36}$/.test(input.requestId))) return send(res, 400, {error: 'Invalid run request ID'});
    if (!['evolve', 'scratch'].includes(input.mode)) return send(res, 400, {error: 'Unknown run mode'});
    if (input.agent !== 'model') return send(res, 400, {error: 'Unknown agent'});
    if (input.mode === 'scratch' && input.agent === 'model' && relay.webSearch === 'off') return send(res, 400, {error: 'Run from scratch requires web search; start with --web-search basic, direct or dynamic'});
    if (!ALLOW_LOCAL) return send(res, 400, {error: 'Start the studio with --allow-local-env to reuse the local environment package'});
    if (input.agent === 'model' && (typeof input.apiKey !== 'string' || input.apiKey.trim().length < 8)) return send(res, 400, {error: 'Enter a model API key in Settings'});
    if (input.mode === 'evolve') {
      const errors = validateTree(input.tree);
      if (errors.length) return send(res, 400, {error: errors.join('; ')});
    }
    if (input.requestId && [...jobs.values()].some(j => j.requestId === input.requestId)) return send(res, 409, {code: 'REQUEST_ID_REUSED', error: 'Run request ID was already used; create a new request ID'});
    if ([...jobs.values()].some(j => ['running', 'stopping'].includes(j.status))) return send(res, 409, {error: 'A run is already in progress'});
    const job = startJob({mode: input.mode, tree: input.tree ?? null, apiKey: input.agent === 'model' ? input.apiKey.trim() : null, agent: input.agent, requestId: input.requestId, relay});
    return send(res, 200, {id: job.id, out: job.out});
  }
  const requestMatch = /^\/api\/runs\/request\/([0-9a-f-]{36})$/.exec(url.pathname);
  if (requestMatch && req.method === 'GET') {
    const job = [...jobs.values()].find(job => job.requestId === requestMatch[1]);
    return job ? send(res, 200, runSnapshot(job)) : send(res, 404, {error: 'Unknown run request'});
  }
  if (url.pathname === '/api/runs/active' && req.method === 'GET') {
    const active = [...jobs.values()].find(job => ['running', 'stopping'].includes(job.status));
    return send(res, 200, active ? runSnapshot(active) : null);
  }
  const runMatch = /^\/api\/runs\/([0-9a-f-]{36})(\/events|\/stop|\/snapshot)?$/.exec(url.pathname);
  if (runMatch) {
    const job = jobs.get(runMatch[1]);
    if (!job) return send(res, 404, {error: 'Unknown run'});
    if (runMatch[2] === '/snapshot' && req.method === 'GET') return send(res, 200, runSnapshot(job));
    if (runMatch[2] === '/stop' && req.method === 'POST') {
      if (['running', 'stopping'].includes(job.status)) stopJob(job);
      return send(res, 200, {status: job.status});
    }
    if (runMatch[2] === '/events' && req.method === 'GET') {
      const records = job.events();
      res.writeHead(200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-store', Connection: 'keep-alive'});
      const requested = Number(req.headers['last-event-id'] ?? 0);
      const cursor = Number.isSafeInteger(requested) && requested >= 0 && requested <= job.sequence ? requested : 0;
      res.write('retry: 500\n\n');
      for (const {id, event} of records) {
        if (id > cursor) res.write('id: ' + id + '\ndata: ' + JSON.stringify(event) + '\n\n');
      }
      if (job.status === 'running' || job.status === 'stopping') {job.clients.add(res); req.on('close', () => job.clients.delete(res)); res.on('error', () => job.clients.delete(res));}
      else res.end();
      return;
    }
    return send(res, 200, {id: job.id, status: job.status, out: job.out});
  }
  send(res, 404, {error: 'Unknown endpoint'});
}

let stopping = false;
const pendingRequests = new Set();
const server = http.createServer((req, res) => {
  const pending = handleRequest(req, res);
  pendingRequests.add(pending);
  pending.then(() => pendingRequests.delete(pending), () => pendingRequests.delete(pending));
});
async function handleRequest(req, res) {
  try {
    if (stopping) return send(res, 503, {error: 'Studio is shutting down'});
    const host = (req.headers.host ?? '').split(':')[0];
    if (!['127.0.0.1', 'localhost'].includes(host)) return send(res, 403, {error: 'Forbidden host'});
    const url = new URL(req.url, 'http://' + HOST);
    if (url.pathname.startsWith('/api/')) return await api(req, res, url);
    const name = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
    if (!/^[A-Za-z0-9_-]+\.(html|js|css)$/.test(name)) return send(res, 404, 'Not found', 'text/plain');
    const file = path.join(ROOT, 'public', name);
    if (!fs.existsSync(file)) return send(res, 404, 'Not found', 'text/plain');
    streamFile(res, file, {'Content-Type': TYPES[path.extname(name)], 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'"});

  } catch (error) {
    if (!res.headersSent) send(res, 500, {error: String(error.message).slice(0, 500)});
  }
}

try {pkg = await loadPackage();} catch (error) {
  if (ALLOW_LOCAL) throw new Error('Local environment package validation failed: ' + error.message);
  console.error('Environment package not loaded: ' + error.message);
}
server.listen(PORT, HOST, () => console.log('Trinity Studio: http://' + HOST + ':' + PORT + (ALLOW_LOCAL ? '' : '  (read-only: add --allow-local-env to run learning)')));

async function shutdown() {
  if (stopping) return;
  stopping = true;
  const closed = new Promise(resolve => server.close(resolve));
  const workers = [];
  for (const job of jobs.values()) {
    for (const client of job.clients) client.end();
    job.clients.clear();
    if (!job.closed) {
      workers.push(new Promise(resolve => job.child.once('close', resolve)));
      stopJob(job);
    }
  }
  try {
                                                                            
                                                                           
    await Promise.all([closed, environments.close(), ...workers, ...pendingRequests]);
    await closeLevelEngine();
  } catch (error) {
    console.error('Studio shutdown failed: ' + error.message);
    process.exitCode = 1;
  }
}
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
