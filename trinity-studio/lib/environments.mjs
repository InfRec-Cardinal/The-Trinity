import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';

// The packaged manifests are the only source for the Studio catalog.
function readCatalog(root) {
  const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
  const manifest = read('manifest.json'), catalog = read('downloads.json');
  const record = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const text = v => typeof v === 'string' && Boolean(v.trim());
  const ensure = (ok, field) => {if (!ok) throw Error('Invalid environment catalog: ' + field);};
  const refs = (list, table) => Array.isArray(list) && new Set(list).size === list.length && list.every(k => text(k) && Object.hasOwn(table, k));
  ensure(manifest?.schema === 'trinity-task-environments-v1' && catalog?.schema === 'trinity-environment-downloads-v1', 'schema');
  ensure(record(manifest.tasks) && record(catalog.tasks) && record(catalog.assets), 'tasks/assets');
  const entries = Object.entries(manifest.tasks);
  ensure(entries.length > 0 && entries.length === manifest.taskCount && entries.length === Object.keys(catalog.tasks).length, 'taskCount');
  const excludedTasks = manifest.excludedFromRuntimeValidation ?? [], excludedAssets = catalog.excludedByDefault ?? [];
  ensure(refs(excludedTasks, manifest.tasks) && refs(excludedAssets, catalog.assets) && refs(catalog.optionalAssets ?? [], catalog.assets), 'exclusions/optionalAssets');
  ensure(Object.entries(catalog.assets).every(([id, a]) => text(id) && record(a) && text(a.kind)), 'assets');
  const tasks = entries.map(([id, task]) => {
    ensure(text(id) && record(task) && text(task.profile) && text(task.root), 'task ' + id);
    const segments = task.root.split('/');
    ensure(segments.every(s => /^[a-zA-Z0-9_-]+$/.test(s)) && fs.statSync(path.join(root, ...segments)).isDirectory(), 'root for ' + id);
    ensure(Object.hasOwn(catalog.tasks, id) && refs(catalog.tasks[id], catalog.assets), 'resources for ' + id);
    return {id, root: task.root, profile: task.profile, resources: catalog.tasks[id], excludedFromRuntimeValidation: excludedTasks.includes(id)};
  });
  const keys = Object.keys(catalog.assets).filter(k => !excludedAssets.includes(k));
  ensure(keys.length > 0, 'empty default downloads');
  const kinds = keys.map(k => catalog.assets[k].kind);
  const imports = [...(kinds.includes('glove') ? ['import numpy'] : []), ...(kinds.includes('frames') ? ['from PIL import Image', 'import decord'] : [])];
  return {tasks, keys, imports};
}

export class EnvironmentManager {
  constructor({root, python = process.env.TRINITY_ENV_PYTHON || (process.platform === 'win32' ? 'python' : 'python3')}) {
    this.root = path.resolve(root);
    this.python = python;
    this.children = new Set();
    this.pending = null;
    this.closed = false;
    this.state = {phase: 'idle', ready: false, assets: [], progress: null, error: null, checkedAt: null, directory: this.root};
    try {
      const {tasks, keys, imports} = readCatalog(this.root);
      this.keys = keys; this.imports = imports;
      this.state.tasks = tasks; this.state.assets = keys.map(id => ({id, status: 'unchecked'}));
    } catch (error) {this.keys = []; this.state.phase = 'error'; this.state.error = error.message;}
  }

  snapshot() {return structuredClone(this.state);}
  get busy() {return Boolean(this.pending);}
  emit(event) {
    if (event.asset && !Object.hasOwn(event, 'video') && ['ready', 'missing-or-invalid', 'error'].includes(event.status)) {
      const asset = this.state.assets.find(a => a.id === event.asset);
      if (asset) asset.status = event.status === 'missing-or-invalid' ? 'missing' : event.status;
    }
    if (event.type === 'progress' || event.type === 'asset-start') this.state.progress = event;
    if (event.status === 'error') this.state.error = event.error || 'Environment operation failed';
  }

  command(command, args, {events = false, timeout = 0} = {}) {
    if (this.closed) return Promise.reject(Error('Environment manager is closed'));
    return new Promise((resolve, reject) => {
      const child = spawn(command, args, {cwd: this.root, env: {...process.env, PYTHONUNBUFFERED: '1', PYTHONDONTWRITEBYTECODE: '1'},
        detached: process.platform !== 'win32', stdio: ['ignore', 'pipe', 'pipe']});
      this.children.add(child);
      let rest = '', stderr = '', spawnError;
      const timer = timeout ? setTimeout(() => this.kill(child, 'SIGKILL'), timeout) : null;
      const line = value => {if (events && value.trim()) try {this.emit(JSON.parse(value));} catch {}};
      child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
      child.stdout.on('data', chunk => {
        const lines = (rest + chunk).split('\n'); rest = lines.pop().slice(-20000);
        for (const value of lines) line(value);
      });
      child.stderr.on('data', chunk => {stderr = Array.from(stderr + chunk).slice(-2000).join('');});
      child.on('error', error => {spawnError = error;});
      child.on('close', (code, signal) => {
        clearTimeout(timer); this.children.delete(child); line(rest);
        if (spawnError) reject(Error('Python could not be started: ' + spawnError.message));
        else resolve({code, signal, stderr});
      });
    });
  }

  kill(child, signal) {
    try {if (process.platform === 'win32') child.kill(signal); else process.kill(-child.pid, signal);} catch {}
  }

  async inspect(python = this.python) {
    this.state.ready = false;
    this.state.assets.forEach(a => {a.status = 'unchecked';});
    const result = await this.command(python, [path.join(this.root, 'download.py'), '--all', '--check'], {events: true, timeout: 600000});
    if (this.closed) return;
    this.state.checkedAt = new Date().toISOString();
    this.state.ready = result.code === 0 && this.state.assets.every(a => a.status === 'ready');
    if (this.state.assets.some(a => a.status === 'error')) throw Error(this.state.error || 'Environment check failed');
    if (result.code !== 0 && result.code !== 1) throw Error(result.stderr || 'Environment check failed');
    if (!this.state.ready && this.state.assets.some(a => a.status === 'unchecked')) throw Error(result.stderr || 'Environment check did not complete');
    this.state.phase = this.state.ready ? 'ready' : 'missing';
  }

  launch(operation) {
    if (this.closed) throw Error('Environment manager is closed');
    if (this.pending) return this.pending;
    if (!this.keys.length) return Promise.resolve(this.snapshot());
    this.state.ready = false; this.state.error = null; this.state.progress = null;
    this.pending = (async () => {
      try {await operation();}
      catch (error) {if (!this.closed) {this.state.phase = 'error'; this.state.ready = false; this.state.error = Array.from(String(error.message)).slice(-2000).join('');}}
      finally {this.pending = null;}
      return this.snapshot();
    })();
    return this.pending;
  }

  check() {
    if (this.pending) return this.pending;
    return this.launch(async () => {this.state.phase = 'checking'; await this.inspect();});
  }

  download() {
    return this.launch(async () => {
      this.state.phase = 'preparing';
      let python = this.python;
      const imports = ['-c', this.imports.join('; ') || 'pass'];
      const available = await this.command(python, imports, {timeout: 60000});
      if (available.code !== 0) {
        const runtime = path.join(this.root, '.download-runtime');
        python = path.join(runtime, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
        if (!fs.existsSync(python)) {
          const result = await this.command(this.python, ['-m', 'venv', runtime], {timeout: 180000});
          if (result.code !== 0) throw Error(result.stderr || 'Could not create the download Python environment');
        }
        let result = await this.command(python, imports, {timeout: 60000});
        if (result.code !== 0) {
          result = await this.command(python, ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', path.join(this.root, 'requirements-download.txt')], {timeout: 1800000});
          if (result.code !== 0) throw Error(result.stderr || 'Could not install download dependencies');
          result = await this.command(python, imports, {timeout: 60000});
          if (result.code !== 0) throw Error(result.stderr || 'Download dependencies are unavailable');
        }
      }
      if (this.closed) return;
      this.state.phase = 'downloading';
      const result = await this.command(python, [path.join(this.root, 'download.py'), '--all', '--progress'], {events: true});
      if (this.closed) return;
      if (result.code !== 0) throw Error(this.state.error || result.stderr || 'Environment download failed; retry to continue');
      this.state.phase = 'checking';
      await this.inspect(python);
    });
  }

  async close() {
    this.closed = true;
    const children = [...this.children];
    for (const child of children) this.kill(child, 'SIGTERM');
    const timer = setTimeout(() => {for (const child of children) this.kill(child, 'SIGKILL');}, 3000);
    try {await this.pending;} finally {clearTimeout(timer);}
  }
}
