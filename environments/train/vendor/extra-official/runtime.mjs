                                                                             
                                                                                                              
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createInterface } from 'node:readline';
import { join } from 'node:path';
import { pythonFor } from '../../lib/python-env.mjs';

export const PYTHON_ENV = 'extra-official-venv';
export const TOOL = { name: 'submit_action', description: 'Submit one public directive in the official task response format.',
  parameters: { type: 'object', additionalProperties: false, properties: { action: { type: 'string', maxLength: 8192 } }, required: ['action'] } };

class ExtraOfficialWorker {
  constructor(root, { timeoutMs = 60_000 } = {}) {
    this.process = spawn(pythonFor(root, PYTHON_ENV), [join(root, 'vendor/extra-official/worker.py')], { cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', SDL_VIDEODRIVER: 'dummy', SDL_AUDIODRIVER: 'dummy', PYGAME_HIDE_SUPPORT_PROMPT: '1' } });
    this.timeoutMs = timeoutMs;
    this.pending = new Map(); this.closed = false; this.stderrTail = '';
    this.exited = new Promise(resolveExit => this.process.once('close', resolveExit));
    this.process.stderr.on('data', chunk => { this.stderrTail = (this.stderrTail + chunk.toString('utf8')).slice(-2000); });
    createInterface({ input: this.process.stdout }).on('line', line => {
      if (this.closed) return;
      let message; try { message = JSON.parse(line); if (!message || typeof message !== 'object' || Array.isArray(message)) throw Error('Expected an object'); } catch { ended(new Error('Invalid JSON response from environment worker')); return; }
      const pending = this.pending.get(message.id); if (!pending) { ended(new Error('Unknown environment response identity')); return; }
      this.pending.delete(message.id); clearTimeout(pending.timer);
      if (message.ok) pending.resolve(message.result);
      else pending.reject(Object.assign(new Error(message.message ?? 'Environment worker rejected the operation'), { code: 'environment_error' }));
    });
    const ended = error => {
      if (this.closed) return;
      this.closed = true;
      for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error instanceof Error ? error : Object.assign(new Error(`Environment worker exited: ${this.stderrTail.slice(-400)}`), { code: 'environment_error' })); }
      this.pending.clear(); this.process.stdin.destroy();
      if (this.process.pid && this.process.exitCode === null && this.process.signalCode === null) this.process.kill('SIGKILL');
    };
    this.fail = ended;
    this.process.on('error', ended); this.process.on('exit', () => ended());
    this.process.stdin.on('error', ended); this.process.stdout.on('error', ended);
    this.process.stdout.on('end', () => ended());
  }
  request(command, timeoutMs = this.timeoutMs) {
    if (this.closed || this.process.exitCode !== null || this.process.signalCode !== null) return Promise.reject(new Error('Environment worker is closed'));
    const id = randomUUID();
    return new Promise((resolvePromise, reject) => {
      const data = JSON.stringify({ ...command, id }) + '\n';
      const timer = setTimeout(() => this.fail(Object.assign(new Error('Environment worker timed out'), { code: 'environment_timeout' })), timeoutMs);
      this.pending.set(id, { resolve: resolvePromise, reject, timer });
      try { this.process.stdin.write(data, error => { if (error) this.fail(error); }); } catch (error) { this.fail(error); }
    });
  }
  async close() {
    let closeError;
    if (!this.closed) {
      try { await this.request({ command: 'close' }, 3000); }
      catch (error) { closeError = error; }
      finally { this.process.stdin.end(); }
    }
                                                                                        
                                                                          
    const timer = setTimeout(() => this.process.kill('SIGKILL'), 5000);
    try { await this.exited; } finally { clearTimeout(timer); }
    if (closeError) throw closeError;
  }
}

                                                                                                         
                                                                                      
export function makeExtraOfficialDriver({ root, spec }) {
  const { taskId, configurations, ...fixed } = spec;
  const normalizeAction = input => input && !Array.isArray(input) && Object.keys(input).length === 1 && typeof input.action === 'string'
    && input.action.length <= 8192 ? { action: input.action } : null;
  const driver = {
    ...fixed,
    kind: 'interactive',
    tool: TOOL,
    configurations,
    normalizeAction,
    async prepare({ runDir }) {
      const initialScenes = [];
      for (const [index, configuration] of configurations.entries()) {
        const worker = new ExtraOfficialWorker(root);
        try { initialScenes.push(await worker.request({ command: 'init', taskId, runDir, episodePath: `scenes/case-${index}`, configuration })); }
        finally { await worker.close(); }
      }
      return { initialScenes, configurations };
    },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      const worker = new ExtraOfficialWorker(root);
      try {
        const observation = await worker.request({ command: 'init', taskId, runDir, episodePath: `episodes/${episode.id}`, configuration });
        let closed = false;
        return {
          observation,
          async step(action, { index } = {}) {
            if (closed) throw new Error('Episode is closed');
            const normalized = normalizeAction(action); if (!normalized) throw new Error('Malformed action');
            return worker.request({ command: 'step', action: normalized, expectedStep: index ?? null });
          },
          async close() { if (!closed) { closed = true; await worker.close(); } },
        };
      } catch (error) { await worker.close(); throw error; }
    },
  };
  return driver;
}
