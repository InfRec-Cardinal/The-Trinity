                                                                                                                           
                                                                                                               
                                                                                 
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pythonFor } from '../../lib/python-env.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const configurations = JSON.parse(readFileSync(join(here, 'configurations.json'), 'utf8')).configurations;
const PYTHON_ENV = 'textarena-geoffrey-venv-v2';
const TIMEOUT_MS = 60_000;
const TOOL = { name: 'submit_action', description: 'Submit one action string under the current public game rules.',
  parameters: { type: 'object', additionalProperties: false, properties: { action: { type: 'string', maxLength: 1000 } }, required: ['action'] } };

const normalizeAction = input => input && !Array.isArray(input) && Object.keys(input).length === 1
  && typeof input.action === 'string' && input.action.length <= 1000 ? { action: input.action } : null;

class EnvironmentWorker {
  constructor(root) {
    this.process = spawn(pythonFor(root, PYTHON_ENV), ['-I', '-B', join(here, 'worker.py'), resolve(root, '../vendor/TextArena/textarena')], {
      cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', SDL_VIDEODRIVER: 'dummy', SDL_AUDIODRIVER: 'dummy', PYGAME_HIDE_SUPPORT_PROMPT: '1' } });
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
  request(command, timeoutMs = TIMEOUT_MS) {
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

export async function createDriver({ root }) {
  return {
    id: 'textarena-colonel_blotto-public-driver',
    version: 3,
    kind: 'interactive',
    maxSteps: 18,
    tool: TOOL,
    configurations,
    actionContract: 'One allocation string such as [A7 B7 C6], non-negative integers over A/B/C summing exactly to 20. Native official simultaneous allocation, 9-round match and terminal rewards apply.',
    source: {
      mechanismReviewed: true, kind: 'official', engine: 'TextArena', commit: '6dfb577c01d0337fe03b05adce84c5ae1878eca1',
      urls: ['https://github.com/TextArena/TextArena'], recording: 'unchanged native public observations and actions',
      reconstructed: false, protocolCompatible: true,
      fidelityNotes: 'Official ColonelBlotto-v0: 3 fields, 20 units, 9 rounds, native win/draw/forfeit scoring. Fixed scripted opponent and paired seats are declared evaluation designs. Distinct configurations bind different complete nine-round opponent allocation schedules and evaluated seats; their hidden parameters can leave the public initial screen identical.',
      limitations: [],
    },
    normalizeAction,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      const worker = new EnvironmentWorker(root);
      try {
        const observation = await worker.request({ command: 'init', taskId: 'colonel_blotto', runDir,
          episodePath: `episodes/${episode.id}`, configuration });
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
}
