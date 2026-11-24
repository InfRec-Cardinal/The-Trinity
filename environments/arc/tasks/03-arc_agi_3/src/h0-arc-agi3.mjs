                                                                                                                      
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createInterface } from 'node:readline';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pythonFor } from '../../../lib/python-env.mjs';

export const PYTHON_ENV = 'arc-agi3-venv';
const WORKER = join(dirname(fileURLToPath(import.meta.url)), '../adapters/h0-arc-agi3-worker.py');
export const ACTIONS = ['RESET', 'ACTION1', 'ACTION2', 'ACTION3', 'ACTION4', 'ACTION5', 'ACTION6', 'ACTION7'];
export const TOOL = { name: 'submit_action', description: 'Submit one official ARC-AGI-3 action from the observed available_actions. ACTION6 requires integer x,y in 0..63. No rules, goals or source baselines are supplied.',
  parameters: { type: 'object', additionalProperties: false, properties: { action: { type: 'string', enum: ACTIONS },
    x: { type: 'integer', minimum: 0, maximum: 63 }, y: { type: 'integer', minimum: 0, maximum: 63 } }, required: ['action'] } };

class ArcAgi3Worker {
  constructor(root, { timeoutMs = 90_000 } = {}) {
    this.process = spawn(pythonFor(root, PYTHON_ENV), [WORKER], { cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
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

export function normalizeArcAction(input) {
  if (!input || Array.isArray(input) || !ACTIONS.includes(input.action)) return null;
  const expected = input.action === 'ACTION6' ? ['action', 'x', 'y'] : ['action'];
  if (Object.keys(input).length !== expected.length || !expected.every(key => Object.hasOwn(input, key))) return null;
  if (input.action === 'ACTION6' && !['x', 'y'].every(key => Number.isInteger(input[key]) && input[key] >= 0 && input[key] <= 63)) return null;
  return Object.fromEntries(expected.map(key => [key, input[key]]));
}

                                                                                                          
export function makeArcAgi3Driver({ root, spec }) {
  const { configurations, ...fixed } = spec;
  return {
    ...fixed,
    kind: 'interactive',
    tool: TOOL,
    configurations,
    normalizeAction: normalizeArcAction,
    async prepare({ runDir }) {
      const initialScenes = [];
      for (const [index, configuration] of configurations.entries()) {
        const worker = new ArcAgi3Worker(root);
        try { initialScenes.push(await worker.request({ command: 'init', runDir, episodePath: `scenes/case-${index}`, configuration })); }
        finally { await worker.close(); }
      }
      return { initialScenes, configurations };
    },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      const worker = new ArcAgi3Worker(root);
      try {
        const observation = await worker.request({ command: 'init', runDir, episodePath: `episodes/${episode.id}`, configuration });
        let closed = false;
        return {
          observation,
          async step(action, { index } = {}) {
            if (closed) throw new Error('Episode is closed');
            const normalized = normalizeArcAction(action); if (!normalized) throw new Error('Malformed action');
            return worker.request({ command: 'step', action: normalized, expectedStep: index ?? null });
          },
          async close() { if (!closed) { closed = true; await worker.close(); } },
        };
      } catch (error) { await worker.close(); throw error; }
    },
  };
}
