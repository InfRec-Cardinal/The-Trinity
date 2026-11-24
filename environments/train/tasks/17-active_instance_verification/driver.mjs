                                                                 
                                                                                                         
                                                                                                   
                                                                                                  
                                                                                                                           
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { createInterface } from 'node:readline';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pythonFor } from '../../lib/python-env.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ACTIONS = [
  "nav_front",
  "nav_front_left",
  "nav_back_left",
  "nav_back",
  "nav_back_right",
  "nav_front_right",
  "decide_yes",
  "decide_no"
];
const TOOL = {
  "name": "submit_action",
  "description": "Submit one official PInVerify relative navigation or terminal binary commitment. Navigation and commitment each consume one of six steps.",
  "parameters": {
    "type": "object",
    "additionalProperties": false,
    "properties": {
      "action": {
        "type": "string",
        "enum": [
          "nav_front",
          "nav_front_left",
          "nav_back_left",
          "nav_back",
          "nav_back_right",
          "nav_front_right",
          "decide_yes",
          "decide_no"
        ]
      }
    },
    "required": [
      "action"
    ]
  }
};
const ACTION_CONTRACT = "Observe the unchanged full RGB capture and the three original query descriptions. Decide whether the visible candidate is the described instance. Submit {action: \"nav_front\"|\"nav_front_left\"|\"nav_back_left\"|\"nav_back\"|\"nav_back_right\"|\"nav_front_right\"|\"decide_yes\"|\"decide_no\"}. The native angular resolver chooses available unvisited sectors; nav_front stays in the current sector. Unreachable or already-visited directions consume a step and retain the current frame with feedback. Trap visibility is reported after navigation. There are six total actions including the terminal decision. On action six, a NAV forces Unsure and fails (official unsure_as_negative=false). A YES/NO decision on action six is valid. No target boxes, masks, identity, pair type or gold label are Player input. Detection and verification remain the fixed Player responsibility; Grounding DINO belongs to the published reference policy, not the environment interface.";
const SOURCE = {
  "kind": "official",
  "engine": "PInVerifyEnv",
  "commit": "3e4b011d7bc1f3b0824ecfa08fa4f3160790fa51",
  "datasetRevision": "076d076d8855c36ee7d925175e00bb89e7ac8466",
  "urls": [
    "https://github.com/Avalon-S/PInVerify",
    "https://huggingface.co/datasets/Avalon-S/PInVerify"
  ],
  "fidelityNotes": "The original Python environment executes unchanged with max_steps=6, sectors=6, far-first view priority, seed=42 and each original full-index row number. Full original RGB captures, original three query descriptions and the reference query-category cache are public input. The official evaluator flag unsure_as_negative=false implements the admitted no-commitment failure. The wrapper filters private metadata and records all outcomes; it does not execute the paper reference MLLMPolicy or its Grounding DINO crop.",
  "limitations": [
    "Nine-row train subset with five planned trials per row is an integration evaluation, not all3,000 unique paper rows. Official source metrics report coverage and full-paper-equivalence only when all3,000 distinct rows are present.",
    "The original assignment summarizes sector visits as once each; native nav_front intentionally stays, consumes one step and may be repeated.",
    "Unreachable NAV is a nonterminal native transition; a subsequent correct commitment remains correct. Navigation failures are recorded separately.",
    "The original assignment names Grounding DINO in the reference agent; the environment exposes raw RGB, and this binding preserves fixed H0 without adding that reference policy."
  ]
};
const fail = message => { throw new Error(message); };

                                                                                                      
class PythonWorker {
  constructor(root, timeoutMs = 60_000) {
    this.process = spawn(pythonFor(root, 'piv3-runtime'), ['-B', '-u', path.join(HERE, 'worker.py')], { cwd: root, stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PINVERIFY_SOURCE: path.join(root, 'vendor/pinverify'), PINVERIFY_DATA: path.join(root, 'data/pinverify/pinverify-data-076d076d') } });
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

export async function createDriver({ root }) {
  const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
  return {
    id: 'official-pinverify-offline-relocated-full3000-driver-v3', version: 3, kind: 'interactive', maxSteps: 6,
    tool: TOOL, actionContract: ACTION_CONTRACT, source: SOURCE, configurations,
    normalizeAction(input) {
      return input && !Array.isArray(input) && Object.keys(input).length === 1 && ACTIONS.includes(input.action) ? { action: input.action } : null;
    },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex ?? 0] ?? fail('Unknown configuration index');
      const worker = new PythonWorker(root);
      try {
        const observation = await worker.request({ command: 'init', runDir: path.resolve(runDir), episodePath: `episodes/${episode.id}`, configuration });
        return { observation, step: action => worker.request({ command: 'step', action }), close: () => worker.close() };
      } catch (error) { await worker.close(); throw error; }
    },
                                                                                                                          
    async aggregateRun(run) {
      const episodes = (run.episodes ?? []).filter(e => e.status === 'completed')
        .map(e => ({ id: e.id, configuration: run.configurations[e.configurationIndex], steps: e.steps }));
      const worker = new PythonWorker(root);
      try { return await worker.request({ command: 'aggregate_official', episodes }); } finally { await worker.close(); }
    },
  };
}
