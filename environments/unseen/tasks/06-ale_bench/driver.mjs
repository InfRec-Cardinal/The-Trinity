                                                                                  
                                                                                                                 
                                                                                                                  
                                                                                                                       
                                                                                                                    
                                                                                                     
import { spawn } from 'node:child_process';
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { createInterface } from 'node:readline';
import { join } from 'node:path';
import {fileURLToPath} from 'node:url';

const TASK_ID = 'ale_bench';
const ROUNDS = 16;
const CHECKPOINTS = [1, 2, 4, 8, 16];
const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
const BRIDGE = fileURLToPath(new URL('./bridge.py', import.meta.url));
const ALE_ROOT = process.env.ALE_BENCH_ROOT || fileURLToPath(new URL('../../../ale-bench/',import.meta.url));
const NUM_WORKERS = Number(process.env.ALE_NUM_WORKERS || 6);
                                                                                                           
                                                                                                               
const deferPrivate = () => process.env.ALE_DEFER_PRIVATE === '1' || existsSync('/tmp/ale-defer-private');
const sha256 = value => createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');

function startBridge(logFile) {
  const child = spawn(process.env.ALE_PYTHON || (existsSync(join(ALE_ROOT,'.venv/bin/python'))?join(ALE_ROOT,'.venv/bin/python'):process.env.PYTHON || (process.platform==='win32'?'python':'python3')), [BRIDGE], { cwd: ALE_ROOT, env:{...process.env,ALE_BENCH_DATA:process.env.ALE_BENCH_DATA??join(ALE_ROOT,'data'),PYTHONPATH:[join(ALE_ROOT,'src'),process.env.PYTHONPATH].filter(Boolean).join(process.platform==='win32'?';':':')}, stdio: ['pipe', 'pipe', 'pipe'] });
  const lines = createInterface({ input: child.stdout });
  const waiting = [];
  let failure = null;
  const configuredTimeout = Number(process.env.ALE_BRIDGE_TIMEOUT_MS ?? 1800000);
  const timeout = Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 1800000;
  const fail = error => {
    if (failure) return;
    failure = error;
    for (const pending of waiting.splice(0)) { clearTimeout(pending.timer); pending.reject(error); }
    child.stdin.destroy();
    if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
  };
  lines.on('line', line => {
    if (failure) return;
    let reply;
    try { reply = JSON.parse(line); if (!reply || typeof reply !== 'object' || Array.isArray(reply)) throw Error('Expected an object'); }
    catch { fail(new Error('Invalid JSON response from ALE-Bench bridge')); return; }
    const pending = waiting.shift();
    if (!pending) { fail(new Error('Unexpected response from ALE-Bench bridge')); return; }
    clearTimeout(pending.timer);
    if (!reply.ok) pending.reject(Object.assign(new Error(`ALE-Bench bridge: ${reply.error}`), {trace: reply.trace}));
    else pending.resolve(reply);
  });
  child.stderr.on('data', chunk => { try { writeFileSync(logFile, chunk, { flag: 'a' }); } catch {} });
  child.once('error', fail);
  child.once('exit', (code, signal) => fail(new Error(`ALE-Bench bridge exited (${signal || code})`)));
  child.stdin.on('error', fail);
  child.stdout.on('error', fail);
  lines.once('close', () => fail(new Error('ALE-Bench bridge output closed')));
  const call = (msg, timeoutMs = timeout) => new Promise((resolve, reject) => {
    if (failure) return reject(failure);
    if (child.exitCode !== null || child.signalCode !== null) return reject(new Error('ALE-Bench bridge has ended'));
    let data;
    try { data = JSON.stringify(msg) + '\n'; } catch (error) { reject(error); return; }
    const timer = setTimeout(() => fail(new Error('ALE-Bench bridge request timed out')), timeoutMs);
    waiting.push({resolve, reject, timer});
    try { child.stdin.write(data, error => { if (error) fail(error); }); } catch (error) { fail(error); }
  });
  return {call, kill: () => fail(new Error('ALE-Bench bridge closed'))};
}

function normalizeAction(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
  if (typeof input.code !== 'string') return null;
  return { code: input.code };
}

export async function createDriver({ root } = {}) {
  return {
    id: 'ale-bench-self-refine-x16', version: 1, kind: 'interactive', maxSteps: ROUNDS,
    tool: {
      name: 'submit_action',
      description: 'Submit one complete C++20 (gcc 12.2.0) source file for official public evaluation.',
      parameters: { type: 'object', additionalProperties: false, required: ['code'],
        properties: { code: { type: 'string', description: 'The complete C++20 program (reads stdin, writes stdout).' } } },
    },
    actionContract: `Submit {"code": "<complete C++20 source>"}. The code field is the solution code block the official prompt asks for: put the whole program there, without Markdown fences. `
      + `Each submission is compiled with C++20 (gcc 12.2.0) and judged on the official public test cases; the next observation is the official feedback. `
      + `There are exactly ${ROUNDS} submissions. After the last one, the official private evaluation scores the submission with the best public score.`,
    normalizeAction,
    configurations,
    source: { repository: 'https://github.com/SakanaAI/ALE-Bench', protocol: 'ale_bench_eval Self-Refine (n_repeated_sampling=1, n_self_refine=16), cpp20 / judge 202301, prompts en, no statement images' },
    async open({ runDir, run, episode }) {
      const configuration = (run?.configurations ?? configurations)[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown ALE-Bench configuration index');
      const episodeDir = join(runDir, 'episodes', episode.id);
      mkdirSync(join(episodeDir, 'submissions'), { recursive: true });
      const bridge = startBridge(join(episodeDir, 'bridge.log'));
      let opened;
      try { opened = await bridge.call({ cmd: 'open', problem_id: configuration.id, num_workers: NUM_WORKERS }); }
      catch (error) { bridge.kill(); throw error; }
      const state = { round: 0, publicScores: [], ended: false };
      const status = () => `\n\n[Submissions used: ${state.round}/${ROUNDS}]`;
      const observation = (publicText, terminal, info = {}) => ({
        publicText, step: state.round, reward: 0,
        stateHash: sha256({ taskId: TASK_ID, problem: configuration.id, round: state.round, publicScores: state.publicScores }),
        info: { problem: opened.problem, round: state.round, ...info },
        terminal: terminal ?? { ended: false, outcome: null, reason: null, score: null },
      });
      return {
        observation: observation(opened.text + status()),
        async step(action) {
          if (state.ended) throw new Error('ALE-Bench episode already ended');
          const { code } = normalizeAction(action) ?? (() => { throw new Error('Malformed ALE-Bench action'); })();
          const judged = await bridge.call({ cmd: 'public', code });
          state.round = judged.round;
          state.publicScores.push(judged.score);
          writeFileSync(join(episodeDir, 'submissions', `round-${String(state.round).padStart(2, '0')}.cpp`), code);
          const info = { judgeResult: judged.judge_result, publicScore: judged.score, judgeRetries: judged.judge_retries };
          if (state.round < ROUNDS) return observation(judged.text + status(), null, info);
          if (deferPrivate()) {
                                                                                                                           
            const { selections } = await bridge.call({ cmd: 'select', checkpoints: CHECKPOINTS });
            state.ended = true;
            const terminal = { ended: true, outcome: 'pending_private_evaluation', reason: 'self_refine_budget_exhausted', score: null,
              evaluation: { official: { problemId: configuration.id, pending: true, selections, publicScores: state.publicScores } } };
            return observation(judged.text + status() + `\n\nAll ${ROUNDS} submissions are used. The episode has ended.`, terminal, info);
          }
          const privateEval = await bridge.call({ cmd: 'private', checkpoints: CHECKPOINTS });
          const final = privateEval.results[`self_refine_${ROUNDS}`];
          state.ended = true;
          const terminal = {
            ended: true,
            outcome: final.overall_judge_result === 'ACCEPTED' ? 'success' : 'failure',
            reason: 'self_refine_budget_exhausted',
            score: final.performance,
            evaluation: { official: { problemId: configuration.id, metric: 'performance (rank-based)', final,
              x1: privateEval.results.x1_first_submission, checkpoints: privateEval.results, publicScores: state.publicScores } },
          };
          return observation(judged.text + status() + `\n\nAll ${ROUNDS} submissions are used. The episode has ended.`, terminal, info);
        },
        async close() {
          try { await bridge.call({ cmd: 'close' }, 3000); } catch {}
          bridge.kill();
        },
      };
    },
  };
}
