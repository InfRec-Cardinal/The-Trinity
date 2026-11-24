import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';

export class GLEENativeClient {
  constructor(home, {python, worker, source, timeoutMs = 240000}) {
    fs.mkdirSync(home + '/tmp', {recursive: true});
    this.id = 0; this.pending = new Map(); this.home = home; this.failure = null;
    this.timeoutMs = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 240000;
    const fd = fs.openSync(home + '/native-stderr.log', 'a');
    try {
      this.child = spawn(python, ['-I', '-B', worker], {cwd: home, env: {...process.env, GLEE_SOURCE: source, HOME: home, TMPDIR: home + '/tmp', TMP: home + '/tmp', TEMP: home + '/tmp', PYTHONDONTWRITEBYTECODE: '1', PYTHONUNBUFFERED: '1'}, stdio: ['pipe', 'pipe', fd]});
    } finally { fs.closeSync(fd); }
    this.exited = new Promise(resolve => this.child.once('close', resolve));
    const lines = createInterface({input: this.child.stdout});
    lines.on('line', line => {
      if (this.failure) return;
      let reply;
      try { reply = JSON.parse(line); if (!reply || typeof reply !== 'object' || Array.isArray(reply)) throw Error('Expected an object'); }
      catch { this.fail(new Error('Native stdout must contain complete RPC JSON only')); return; }
      const pending = this.pending.get(reply.id);
      if (!pending) { this.fail(new Error('Foreign native RPC identity')); return; }
      this.pending.delete(reply.id); clearTimeout(pending.timer);
      if (reply.error) pending.reject(Object.assign(new Error(reply.error.message), {nativeError: reply.error}));
      else pending.resolve(reply.result);
    });
    this.child.on('error', error => this.fail(error));
    this.child.on('exit', (code, signal) => this.fail(new Error('Native process exited ' + (signal || code))));
    this.child.stdin.on('error', error => this.fail(error));
    this.child.stdout.on('error', error => this.fail(error));
    lines.once('close', () => this.fail(new Error('Native output closed')));
  }
  fail(error) {
    if (this.failure) return;
    this.failure = error;
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error); }
    this.pending.clear(); this.child.stdin.destroy();
    if (this.child.pid && this.child.exitCode === null && this.child.signalCode === null) this.child.kill('SIGKILL');
  }
  call(method, params = {}, timeoutMs = this.timeoutMs) {
    if (this.failure) return Promise.reject(this.failure);
    if (this.child.exitCode !== null || this.child.signalCode !== null) return Promise.reject(new Error('Native process has ended'));
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      let data;
      try { data = JSON.stringify({id, method, params}) + '\n'; } catch (error) { reject(error); return; }
      const timer = setTimeout(() => this.fail(new Error('Native RPC request timed out')), timeoutMs);
      this.pending.set(id, {resolve, reject, timer});
      try { this.child.stdin.write(data, error => { if (error) this.fail(error); }); } catch (error) { this.fail(error); }
    });
  }
  async open(seed) { return this.call('open', {home: this.home, seed}); }
  async answer(snapshot, text) { return this.call('answer', {role: snapshot.pendingRole, ordinal: snapshot.ordinal, text}); }
  async close() {
    if (!this.failure) { try { await this.call('close', {}, 3000); } catch {} }
    this.fail(new Error('Native client closed'));
    await this.exited;
  }
}
