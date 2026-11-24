                                                                                                                                 
                                                                                                                    
                                                                                                               
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createInterface } from 'node:readline';
import { mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pythonFor } from '../../lib/python-env.mjs';

const TASK_ID = 'pooltool_billiards_shots';
const ENV_NAME = 'pooltool-venv';
const MAX_STEPS = 15;
const REQUEST_TIMEOUT_MS = 240_000;
const TASK_DIR = fileURLToPath(new URL('./', import.meta.url));
const ACTION_CONTRACT = 'Pot ball9 within15 attempts. Submit exactly one speed Low/Medium/High and one named strikespot. The original runner auto-aims at the lowest-numbered remaining ball, applies V0=2/5/8m/s and the source cue offsets, then runs unchanged Pooltool physics. Cue scratches are repositioned at the original head-string point. Only the original top-down RGB rendering and stated task/action rules are input; raw coordinates, private simulator events and native physics histories stay outside Player observations. Invalid responses consume a source attempt without simulation; genuine engine exceptions are invalid environment trials rather than fabricated model failures. No source prediction policy, solution witness or privileged state is added.';

                                                                                             
class PoolWorker {
  constructor(python, script, env) {
    this.child = spawn(python, ['-B', '-u', script], { cwd: TASK_DIR, stdio: ['pipe', 'pipe', 'pipe'], env });
    this.pending = new Map(); this.closed = false; this.stderrTail = '';
    this.exited = new Promise(resolveExit => this.child.once('close', resolveExit));
    this.child.stderr.on('data', chunk => { this.stderrTail = (this.stderrTail + chunk.toString('utf8')).slice(-2000); });
    createInterface({ input: this.child.stdout }).on('line', line => {
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
      this.pending.clear(); this.child.stdin.destroy();
      if (this.child.pid && this.child.exitCode === null && this.child.signalCode === null) this.child.kill('SIGKILL');
    };
    this.fail = ended;
    this.child.on('error', ended); this.child.on('exit', () => ended());
    this.child.stdin.on('error', ended); this.child.stdout.on('error', ended);
    this.child.stdout.on('end', () => ended());
  }
  request(command, timeoutMs = REQUEST_TIMEOUT_MS) {
    if (this.closed || this.child.exitCode !== null || this.child.signalCode !== null) return Promise.reject(new Error('Environment worker is closed'));
    const id = randomUUID();
    return new Promise((resolvePromise, reject) => {
      const data = JSON.stringify({ ...command, id }) + '\n';
      const timer = setTimeout(() => this.fail(Object.assign(new Error('Environment worker timed out'), { code: 'environment_timeout' })), timeoutMs);
      this.pending.set(id, { resolve: resolvePromise, reject, timer });
      try { this.child.stdin.write(data, error => { if (error) this.fail(error); }); } catch (error) { this.fail(error); }
    });
  }
  async close() {
    let closeError;
    if (!this.closed) {
      try { await this.request({ command: 'close' }, 3000); }
      catch (error) { closeError = error; }
      finally { this.child.stdin.end(); }
    }
                                                                                        
                                                                          
    const timer = setTimeout(() => this.child.kill('SIGKILL'), 5000);
    try { await this.exited; } finally { clearTimeout(timer); }
    if (closeError) throw closeError;
  }
}

export async function createDriver({ root }) {
  const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
  const vendor = join(root, 'vendor/pooltool');
  const conf = JSON.parse(readFileSync(join(vendor, 'conf/env_config_04_pooltool.json'), 'utf8'));
  const fields = Object.keys(conf.speed_mapping);
  const spots = Object.keys(conf.strikespot_mapping);
  const python = pythonFor(root, ENV_NAME);
  const script = join(TASK_DIR, 'adapters/pooltool-billiards-worker.py');
  const parameters = { type: 'object', additionalProperties: false, properties: {
    speed: { type: 'string', enum: fields }, strikespot: { type: 'string', enum: spots } }, required: ['speed', 'strikespot'] };

  const normalizeAction = input => {
    if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
    if (Object.keys(input).length === 2 && fields.includes(input.speed) && spots.includes(input.strikespot))
      return { speed: input.speed, strikespot: input.strikespot };
    return null;
  };

  const workerEnvironment = home => ({ PATH: '/usr/bin:/bin:/usr/sbin:/sbin', HOME: home, TMPDIR: join(home, 'tmp'),
    LC_ALL: 'en_US.UTF-8', PYTHONHASHSEED: '0', MPLCONFIGDIR: join(home, 'matplotlib'), NUMBA_CACHE_DIR: join(home, 'numba'),
    POOLTOOL_VENDOR_DIR: vendor });
  const startWorker = () => {
    const home = mkdtempSync(join(tmpdir(), 'train-pooltool-'));
    for (const n of ['tmp', 'matplotlib', 'numba']) mkdirSync(join(home, n), { recursive: true });
    return { home, worker: new PoolWorker(python, script, workerEnvironment(home)) };
  };
  const endWorker = async ({ home, worker }) => {
    let closeError;
    try { await worker.close(); } catch (error) { closeError = error; }
    try { rmSync(home, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); }
    catch (error) { if (!closeError) throw error; }
    if (closeError) throw closeError;
  };

  const describe = {
    id: 'original-deepphy-pooltool-isolated-nineball', version: 4, kind: 'interactive', maxSteps: MAX_STEPS,
    tool: { name: 'submit_action', description: 'Choose one power and one cue strikespot. Target/aim are set by the original runner.', parameters },
    actionContract: ACTION_CONTRACT, normalizeAction,
    invalidOutcomePolicy: 'repeat_same_configuration', maxInvalidAttempts: 3,
                                                                                                                       
    invalidActionPolicy: { reprompts: 0, exhaustedOutcome: 'invalid_vlm_action', scoreDefined: true, exhaustedAction: { invalid: true } },
    configurations,
    configurationSelection: { mode: 'adaptive', availableCount: configurations.length, providerId: 'original-nineball-racks-seeds0through99', providerVersion: 1,
      sourceActionBudget: MAX_STEPS, sourceScope: 'Complete original nine-ball racks (seeds 0..99 in the source); this package ships nine other native racks, seeds 10..18.' },
    source: { kind: 'official', reconstructed: false, engine: 'Unchanged DeepPHY helper ASTs and Pooltool0.4.4 event physics',
      urls: ['https://github.com/XinrunXu/DeepPHY', 'https://github.com/ekiefl/pooltool'],
      recording: 'Original top-down RGB frames per state (media/<stateHash>.png); typed power/offsets in each action; native pocket/collision results in the private state.',
      limitations: ['Seeds 0..99 and durable image retention implement the admitted reproducibility designs.',
        'Native default configuration paths are relocated into the package (vendor/pooltool/configuration); native physics and default values are unchanged.',
        'Any native simulation exception remains an invalid environment trial, never a claimed model failure.'] },
  };

  return { ...describe,
    async prepareConfiguration({ runDir, configuration, index }) {
      const started = startWorker();
      try { return await started.worker.request({ command: 'init', configuration: { seed: configuration.seed, configurationHash: configuration.configurationHash },
        runDir: resolve(runDir), episodePath: `scenes/case-${index}` }); }
      finally { await endWorker(started); }
    },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : describe.configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!/^[A-Za-z0-9_-]{1,120}$/.test(episode.id ?? '')) throw new Error('Invalid episode identity');
      const absoluteRun = resolve(runDir), episodePath = `episodes/${episode.id}`, episodeDirectory = resolve(absoluteRun, episodePath);
      if (!episodeDirectory.startsWith(absoluteRun + sep)) throw new Error('Episode path escapes run');
      const started = startWorker();
      try {
        const observation = await started.worker.request({ command: 'init', configuration: { seed: configuration.seed, configurationHash: configuration.configurationHash },
          runDir: absoluteRun, episodePath });
        let closed = false, current = observation, count = 0;
        return { observation,
          async step(action, { index } = {}) {
            if (closed) throw new Error('Episode is closed');
            if (current.terminal?.ended) throw new Error('Pooltool episode already ended');
            current = await started.worker.request({ command: 'step', action, expectedStep: index ?? count });
            count += 1;
            return current;
          },
          async close() { if (!closed) { closed = true; await endWorker(started); } } };
      } catch (error) { await endWorker(started); throw error; }
    } };
}
