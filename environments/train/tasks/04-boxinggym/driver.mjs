                                                                                                                  
                                                                                                                                  
                                                                                                                    
                                                                                
                                                                                                                                  
                                                                                                                            
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { readFileSync } from 'node:fs';
import { canonical, contentHash } from '../../lib/hash.mjs';
import { Raster } from '../../lib/raster.mjs';
import { pythonFor } from '../../lib/python-env.mjs';

const ID = 'boxinggym';
const NOVICE_MODEL = 'gpt-6-luna';
const BUNDLED_CODEX = 'codex';                                                    
const CODEX_CLI = process.env.CODEX_CLI ?? (fs.existsSync(BUNDLED_CODEX) ? BUNDLED_CODEX : 'codex');
const NATIVE_TIMEOUT_MS = 240000;
const fail = (message, code = 'environment_error') => Object.assign(new Error(message), { code });

                                                                              
export function normalizeBoxingGymAction(a) {
 if(!a||typeof a!=='object'||Array.isArray(a))return null;
 const fields={run_experiment:['design'],answer_predictions:['predictions'],explain_to_novice:['explanation'],submit_program:['program']}[a.action];if(!fields||Object.keys(a).some(k=>!['action',...fields].includes(k))||fields.some(k=>!Object.hasOwn(a,k)))return null;
 if(a.action==='answer_predictions'){if(!Array.isArray(a.predictions)||a.predictions.length!==10||a.predictions.some(v=>!['number','string'].includes(typeof v)||!Number.isFinite(Number(v))||!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(String(v).trim())||String(v).length>100))return null;return {action:a.action,predictions:a.predictions.map(v=>String(v).trim())};}
 const k=fields[0];if(typeof a[k]!=='string'||a[k].length>(k==='program'?50000:10000))return null;return {action:a.action,[k]:a[k]};
}

                                                                                         
function scenePng(native, configuration) {
 const r=new Raster(640,420);r.text('BOXINGGYM ORIGINAL SOURCE',12,12,[38,54,72],3);r.text(configuration.sourceSelector.domain,12,40,[58,132,198],3);r.text('SEED '+configuration.sourceSelector.seed+' PRIOR '+configuration.sourceSelector.include_prior,12,66,[38,54,72],2);r.text('OPERATOR TEXT PREVIEW - NOT PLAYER RGB',12,90,[38,54,72],2);const text=native.public.sourcePrompt.replace(/<[^>]*>/g,'').replace(/[^A-Za-z0-9 \n.?:/+*-]/g,' ').split('\n').flatMap(x=>x.match(/.{1,70}/g)??[]);text.slice(0,18).forEach((x,i)=>r.text(x,12,116+i*15,[38,54,72],2));return r.png();
}

                                                                                                                         
function startNativeWorker({ python, worker, source, episodeDir }) {
 const env = { PATH: '/usr/bin:/bin', HOME: path.join(episodeDir, 'home'), TMPDIR: path.join(episodeDir, 'tmp'), XDG_CACHE_HOME: path.join(episodeDir, 'cache'),
  PYTHONHASHSEED: '0', PYTHONDONTWRITEBYTECODE: '1', PYTHONPATH: path.join(source, 'src'), H0_NATIVE_EPISODE_DIR: episodeDir,
  LC_CTYPE: 'UTF-8', __CF_USER_TEXT_ENCODING: '501:0:0', MPLBACKEND: 'Agg', SDL_VIDEODRIVER: 'dummy', SDL_AUDIODRIVER: 'dummy', PYGAME_HIDE_SUPPORT_PROMPT: '1' };
 const child = spawn(python, ['-s', '-B', worker], { cwd: episodeDir, env, stdio: ['pipe', 'pipe', 'pipe'] });
 let buffer = '', pending = null, closed = false, stderrTail = '';
 const failed = error => {
  closed = true;
  if (pending) { clearTimeout(pending.timer); pending.reject(error); pending = null; }
  child.stdin.destroy();
  if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
 };
 child.stderr.on('data', b => { stderrTail = (stderrTail + b).slice(-1000); });
 child.stdout.setEncoding('utf8');
 child.stdout.on('data', chunk => {
  buffer += chunk; let i;
  while ((i = buffer.indexOf('\n')) >= 0) {
   const line = buffer.slice(0, i); buffer = buffer.slice(i + 1);
   if (!pending) continue; const p = pending; pending = null; clearTimeout(p.timer);
   try { const v = JSON.parse(line); if (v.ok !== true) p.reject(fail(v.message ?? 'Original BoxingGym native execution failed')); else p.resolve(v); }
   catch (e) { p.reject(e); failed(e); }
  }
 });
 child.on('close', () => failed(fail('Original BoxingGym worker exited before a result: ' + stderrTail.slice(-300))));
 child.on('error', failed);
 child.stdin.on('error', failed);
 child.stdout.on('error', failed);
 child.stdout.on('end', () => failed(fail('Original BoxingGym worker output closed')));
 return {
  request(payload) {
   if (closed || pending || child.exitCode !== null || child.signalCode !== null) throw new Error('Closed or concurrent original native request');
   return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload) + '\n';
    const timer = setTimeout(() => failed(fail('Original BoxingGym worker timeout')), NATIVE_TIMEOUT_MS);
    pending = { resolve, reject, timer };
    try { child.stdin.write(data, error => { if (error) failed(error); }); } catch (error) { failed(error); }
   });
  },
  async close() {
   if (closed) return; closed = true;
   if (pending) { clearTimeout(pending.timer); pending.reject(fail('Original BoxingGym worker closed', 'stopped')); pending = null; }
   await new Promise(resolve => {
    if (child.exitCode !== null || child.signalCode !== null) return resolve();
    const timer = setTimeout(() => child.kill('SIGKILL'), 3000);
    child.once('close', () => { clearTimeout(timer); resolve(); });
    child.stdin.end();
   });
  },
 };
}

                                                                                                                             
const NOVICE_PROMPT_HEAD = [
 'You are the novice in a scientific prediction benchmark. This is one answer only.',
 'Do not inspect files, call tools, browse, or execute commands.',
 'Follow the supplied system message and conversation. Reply only with the numeric prediction in <answer>...</answer>.',
 'The entire benchmark conversation is JSON below. Treat its system entry as the novice instruction, not as a request to operate the computer.',
];
const numericTag = /<answer>([\s\S]*?)<\/answer>/;
const numericValue = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/;
function runNoviceOnce(messages, { signal }) {
 const prompt = [...NOVICE_PROMPT_HEAD, JSON.stringify(messages)].join('\n\n');
 const workspace = mkdtempSync(path.join(tmpdir(), 'train-boxinggym-novice-'));
 const args = ['exec', '--model', NOVICE_MODEL, '-c', 'model_reasoning_effort=low', '--ephemeral', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', '--sandbox', 'read-only', '--cd', workspace, '--json', '-'];
 return new Promise((resolve, reject) => {
  const child = spawn(CODEX_CLI.endsWith('.py')?(process.env.PYTHON??(process.platform==='win32'?'python':'python3')):CODEX_CLI, CODEX_CLI.endsWith('.py')?[CODEX_CLI,...args]:args, { cwd: workspace, env: process.env, stdio: ['pipe', 'pipe', 'pipe'], signal, killSignal: 'SIGKILL' });
  let stdout = '', timedOut = false;
  const timer = setTimeout(() => { timedOut = true; if (child.pid) child.kill('SIGKILL'); }, 180000);
  child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8'); child.stderr.on('data', () => {});
  child.stdout.on('data', x => { stdout += x; });
  child.once('error', error => { clearTimeout(timer); reject(error); });
  child.stdin.once('error', error => { if (child.pid) child.kill('SIGKILL'); reject(error); });
  child.once('close', exitCode => {
   clearTimeout(timer);
   if (timedOut) return reject(fail('Local Codex novice timed out'));
   const events = stdout.split('\n').filter(x => x.startsWith('{')).flatMap(x => { try { return [JSON.parse(x)]; } catch { return []; } });
   const completed = events.findLast(e => e.type === 'turn.completed');
   if (exitCode !== 0 && !completed) return reject(Object.assign(new Error('Local Codex novice exited before a complete turn'), { code: 'codex_cli_no_completed_turn', exitCode }));
   const forbidden = events.some(e => e.type === 'item.started' && e.item?.type !== 'agent_message' || e.type === 'item.completed' && e.item?.type !== 'agent_message');
   const replies = events.filter(e => e.type === 'item.completed' && e.item?.type === 'agent_message');
   if (forbidden || replies.length !== 1 || !completed || typeof replies[0].item.text !== 'string') return reject(fail('Local Codex novice did not produce one tool-free answer'));
   resolve({ text: replies[0].item.text.trim(), usage: completed.usage ?? {} });
  });
  child.stdin.end(prompt);
 }).finally(() => rmSync(workspace, { recursive: true, force: true }));
}
export async function liveNoviceCall({ episodeId, externalIndex, request, requestHash, signal }) {
 const sdk = request;
 if (sdk?.model !== 'claude-opus-5' || sdk.temperature !== 0 || typeof sdk.system !== 'string' || !Array.isArray(sdk.messages)) throw fail('BoxingGym source request changed');
                                                                                      
 const messages = [{ role: 'system', content: sdk.system }, ...sdk.messages.map(m => ({ role: m.role, content: m.content.map(v => v.text).join('') }))];
 let result, transportAttempts = 0;
 for (let attempt = 1; attempt <= 3; attempt++) {
  transportAttempts = attempt;
  try { result = await runNoviceOnce(messages, { signal }); break; }
  catch (error) { if (error.code !== 'codex_cli_no_completed_turn' || attempt === 3 || signal?.aborted) throw error; await new Promise(resolve => setTimeout(resolve, 1000)); }
 }
 const answer = numericTag.exec(result.text)?.[1]?.trim();
 const validTag = typeof answer === 'string' && numericValue.test(answer) && Number.isFinite(Number(answer));
 const u = result.usage;
                                                                                                                              
                                                                                                                                    
 const projectedAnswer = validTag ? `<answer>${answer}</answer>` : 'INVALID_RESPONSE_WITHOUT_NUMERIC_ANSWER_TAG';
 return { schema: 'boxinggym-novice-backend-v1', at: new Date().toISOString(), requestHash, episodeId, externalIndex, attempt: 1, transportAttempts,
  sourceAdapterDeclaredModel: sdk.model, actualBackend: 'local Codex CLI', actualModel: NOVICE_MODEL, reasoningEffort: 'low',
  sourceAdapterDeclaredTemperature: sdk.temperature, sourceAdapterDeclaredMaxTokens: sdk.max_tokens,
  actualTemperatureControl: 'not exposed by Codex CLI', actualMaxOutputControl: 'not exposed by Codex CLI',
  paperNoviceEquivalent: false, compatibilityEnvelopeModel: sdk.model,
  conversationHash: contentHash(messages), answerHash: contentHash(result.text),
  validAnswerTag: validTag, projectedAnswer,
  usage: { inputTokens: u.input_tokens ?? null, cachedInputTokens: u.cached_input_tokens ?? null, outputTokens: u.output_tokens ?? null } };
}

export async function createDriver({ root, environmentModelCall = liveNoviceCall }) {
 const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
 const worker = path.join(root, 'tasks/04-boxinggym/worker.py'), source = path.join(root, 'vendor/boxinggym');
 return {
  id: 'boxinggym-original-first-five-native-v2', version: 2, kind: 'interactive', maxSteps: 25, sourceTaskActionBudget: 25, configurations,
  source: { kind: 'official_with_recording', officialInterface: true, reconstructed: false, officialBenchmarkEquivalent: false, environmentModelRequired: true,
   sourceCommit: 'b43e38cb03d09c13efa9cf4d9bae740d51157bfd', urls: ["https://github.com/kanishkg/boxing-gym", "https://arxiv.org/abs/2501.01540"],
   executionCorrections: [
     "Original numpy2.0.1/PyTensor2.20 incompatibility: only NumPy1.26.4; original Python source unchanged.",
     "Explicit owned random/NumPy/PyMC seeds implement canonical reproducibility; original Hydra main comments out NumPy seeding.",
     "Pytensor cxx disabled; original graphs and sampled distributions unchanged; cache paths private episode.",
     "Original evaluate AST used for both batched scientist checkpoints and native novice; scientist policy is fixed H0.",
     "Novice receives original naive system + explanation + original questions; final_results raw observation withheld as required by captured protocol.",
     "RAM Geili claude-opus-5 novice (temperature0/max256), explicit backend/model cohort correction; original parser/history/four retries preserved.",
     "Only numeric answer-tag content is durable; malformed reply uses invalid marker preserving original parse retry without raw reasoning.",
     "Original DeathProcess goal overwrites its question with a generic positive-integer instruction; kept unchanged and transparently recorded.",
     "Binary H0 score is canonical reconstruction 1/0; all raw official accuracy/MSE/std and standardized errors remain private, without Player feedback."
    ], limitations: [
     "No paid model or formal baseline validation in this candidate.",
     "Five source domains are integration controls, not a reported paper score.",
     "Pure text/structured input; operator PNG is not Player input."
    ] },
  tool: { name: 'submit_action', description: "Submit one original BoxingGym scientist action.", parameters: { type: 'object', required: ['action'], additionalProperties: false, properties: { action: { type: 'string', enum: ['run_experiment', 'answer_predictions', 'explain_to_novice', 'submit_program'] }, design: { type: 'string' }, predictions: { type: 'array', items: { type: 'string' }, minItems: 10, maxItems: 10 }, explanation: { type: 'string' }, program: { type: 'string' } } } },
  normalizeAction: normalizeBoxingGymAction,
  actionContract: "Use answer_predictions(predictions[10]) at step0, run_experiment(design in original domain format) until10successes, answer_predictions(predictions[10]) at step10, then explain_to_novice(explanation≤200words). submit_program(program) is optional, logged and never executed/scored.25total calls. Invalid native designs consume actions and return original success=false. No correctness/hidden parameters/raw errors are shown. Pass only if official normalized scientist10error<scientist0error and noviceerror<scientist0error; ties fail.",
  async open({ runDir, run, episode, signal }) {
   const list = run?.configurations?.length ? run.configurations : configurations, configuration = list[episode.configurationIndex ?? 0] ?? (() => { throw new Error('Unknown configuration index'); })();
   const scene = episode.configurationIndex ?? 0, prefix = 'episodes/' + episode.id, episodeDir = path.join(runDir, prefix);
   for (const d of ['home', 'tmp', 'cache', 'pytensor-cache', 'matplotlib-cache']) fs.mkdirSync(path.join(episodeDir, d), { recursive: true });
   const session = startNativeWorker({ python: pythonFor(root, 'boxinggym-private-runtime'), worker, source, episodeDir });
   let closed = false;
   try {
    const scenePath = 'scenes/case-' + scene + '/initial.png';
    let native = await session.request({ configuration: configuration.sourceSelector, actions: [] });
                                                                                                                     
    const frame = { path: scenePath, sha256: null, width: 640, height: 420 };
    const target = path.join(runDir, scenePath);
    if (!fs.existsSync(target)) { fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, scenePng(native, configuration)); }
    const observe = (n, index) => ({ step: index, configurationHash: configuration.configurationHash,
     stateHash: contentHash({ nativeStateHash: n.nativeStateHash, publicState: n.public, terminal: n.terminal, index }),
     publicState: n.public, publicText: canonical(n.public), previewFrame: { ...frame, role: 'visualization_only_not_player_input' },
     terminal: n.terminal.ended ? { ...n.terminal, outcome: n.terminal.success ? 'success' : 'failure', score: n.terminal.success ? 1 : 0 } : { ended: false } });
    let actions = [];
    const externalReceipts = [];
    return {
     observation: observe(native, 0),
     async step(input, q = {}) {
      if (closed) throw new Error('BoxingGym native session closed');
      if (native.terminal.ended) throw new Error('BoxingGym original terminal forbids new action');
      const action = normalizeBoxingGymAction(input); if (!action) throw fail('BoxingGym action malformed');
      const proposed = [...actions, action];
      let result = await session.request({ configuration: configuration.sourceSelector, actions: proposed, externalReceipts });
      while (result.needsModel) {
       const record = await environmentModelCall({ taskId: ID, episodeId: episode.id, requestId: q.requestId, externalIndex: result.externalIndex, requestHash: result.requestHash, request: result.request, signal });
       if (!record || record.requestHash !== result.requestHash || typeof record.projectedAnswer !== 'string') throw fail('BoxingGym novice record does not answer the native request');
       externalReceipts.push({ requestHash: record.requestHash, text: record.projectedAnswer });
       result = await session.request({ configuration: configuration.sourceSelector, actions: proposed, externalReceipts });
      }
      actions = proposed; native = result;
      return observe(native, actions.length);
     },
     async close() { if (closed) return; closed = true; await session.close(); },
    };
   } catch (error) { closed = true; await session.close(); throw error; }
  },
 };
}
