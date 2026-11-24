                                                                                                                                    
                                                                                                                                      
                                                                                                                                         
                                                                                                                                    
                                                     
                                                                                                                                         
                                                                            
import fs from 'node:fs';
import path from 'node:path';
import {openFifoProcess} from '../../lib/fifo-process.mjs';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { contentHash, sha256 } from '../../lib/hash.mjs';
import { textFrame } from '../../lib/text-frame.mjs';
import { pythonFor } from '../../lib/python-env.mjs';
import { claudeCliJudgeCall } from './judge-cli.mjs';

const ID = 'discoverphysics';
const JUDGE_ROUTE = Object.freeze({ taskId: 'discoverphysics', role: 'judge', model: 'claude-opus-4-6', temperature: 1, maxTokens: 1024, responseProjection: 'plain' });
                                                                                                                                
                                                                                                             
const JUDGE_SOURCE = 'h0_environment_model_bridge';
const SOURCE_URLS = ['https://github.com/SampsonML/DiscoverPhysics', 'https://arxiv.org/abs/2605.26087'];
const ENGINE = 'SampsonML/DiscoverPhysics @ 33b7fa9df96de9c35744efd181ca7e5a8dd60ad5 (ScienceAgent DiscoveryAgent/Evaluator/TrajectoryLogger, PhysicsSchool NBodySampler), jax 0.10.2, scipy 1.17.1';
const LIMITATIONS = [
  'Verdict = official pass rule (paper and spec): normalized MSE < 0.1 AND official ExplanationJudge score >= 0.9 (the repository run_benchmark uses 0.75; the raw score is kept so either threshold can be applied). Both components are in terminal.components.',
  'Judge: the official ExplanationJudge prompt is unchanged (claude-opus-4-6, max_tokens 1024, official score parser). The request is answered through environmentModelCall: by default the local Claude Code CLI (judge-cli.mjs; temperature 1 is requested but not enforced by the CLI), in replay by the recorded replies. Judge replies are used verbatim.',
  'Fail closed: a final law the evaluator can evaluate is always judged; if the judge reply is missing, incomplete, or from another model the episode raises an error and no outcome is inferred from the MSE component alone. A law error ends as failure without a judge call, as upstream run_discovery.py does not judge it either.',
  'Execution-protocol correction to the upstream harness: upstream evaluator._compile_law and _compile_fit_parameters exec the agent Python inside the evaluator process. Here every Player source (<run_mse_fit> and <final_law>, including fit_parameters) runs in a separate process under /usr/bin/sandbox-exec (deny-by-default profile, numpy/scipy/math only, 12 s per call, 2 GiB cap). Results return as JSON; the official fit and evaluator code otherwise run unchanged.',
  'Action wrapper: the one action carries the official XML-tag protocol of DiscoveryAgent.run (<run_experiment>, <run_mse_fit>, <final_law> with <explanation>), so one round may combine an experiment and a fit as the official agent may.',
  'Noise follows configs/bench.yml (noise_frac 0.05, sigma = 0.05 * sqrt(Var(GT_world))), not an absolute sigma of 0.05 as the spec text states.',
  'Six other official worlds at native noise seed 0: yukawa, fractional, hubble, circle, oscillator and extra_dimensions. These replace gravity/0 and ether/1; all episodes are planned, with no H0 runs.',
  'terminal.score is the official normalized MSE (lower is better), null when the law errors. The judge rationale stays private (state.evaluation.explanation_judge).',
];
const RECORDING = 'Per episode: one persistent official worker (discoverphysics-worker.py over named pipes; the instance is its first line). After every complete response (step 0 = reset, then each action) the driver writes episodes/<id>/dd-log/step-N.json (request, official response, judge record) and step-N.trajectory.csv (the real trajectory CSV bytes). Frames: episodes/<id>/frames/step-N.png.';
const ACTION_CONTRACT = "Call submit_action with exactly {\"reply\": \"<your full reply for this round>\"}. Each call is one round reply of the science agent in the official DiscoverPhysics protocol: include <run_experiment>[...JSON experiments...]</run_experiment> and/or <run_mse_fit>...python...</run_mse_fit>, or, from round 2 on, <final_law>...python discovered_law (+ optional fit_parameters)...</final_law> together with <explanation>...</explanation>. At most 16 rounds; round 16 forces the final law. Your Python runs in an OS sandbox for numeric code (numpy, scipy, math; no files outside a private scratch directory, no network, no processes; 60 s to load a source, 12 s per call, 2 GiB memory). The final law is scored on held-out noise-free test particles (normalized MSE must be below 0.1) and the explanation is graded against the world's rubric.";
const PARAMETERS = { type: 'object', additionalProperties: false, required: ['reply'], properties: { reply: { type: 'string', minLength: 1, maxLength: 60000 } } };
const environmentError = (message, code = 'environment_error') => Object.assign(new Error(message), { code });

                                                                         
function normalizeDiscoverphysicsAction(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
  const keys = Object.keys(input);
  if (keys.length !== 1 || keys[0] !== 'reply' || typeof input.reply !== 'string') return null;
  if (!input.reply.trim() || input.reply.length > 60000) return null;
  return { reply: input.reply };
}

                                                                                                                              
                                                
export function discoverphysicsJudgeRequest(raw) {
  const message = raw?.messages?.[0];
  if (!raw || raw.model !== JUDGE_ROUTE.model || raw.max_tokens !== JUDGE_ROUTE.maxTokens || typeof raw.system !== 'string' || !raw.system
    || raw.messages.length !== 1 || message?.role !== 'user' || typeof message.content !== 'string' || !message.content) {
    throw environmentError('The official ExplanationJudge request differs from the pinned judge route');
  }
  const request = { model: raw.model, system: raw.system, turns: [{ role: 'user', text: message.content }], maxTokens: raw.max_tokens };
  return { requestId: `dpjudge_${contentHash(request)}`, ...request };
}


                                                                                                         
function startWorker({ python, script, episodeDir, instance }) {
  const fifoDir = mkdtempSync(path.join(tmpdir(), 'train-dp-fifo-'));
  const req = path.join(fifoDir, 'requests.fifo'), resp = path.join(fifoDir, 'responses.fifo');
  let proc;
  const close = () => { proc?.close(); fs.rmSync(fifoDir, {recursive: true, force: true}); };
  const parse = line => {
    try {
      if (line == null) throw environmentError('Official engine session ended unexpectedly');
      const out = JSON.parse(line); if (!out.ok) throw environmentError(out.message ?? 'Official engine rejected the operation'); return out;
    } catch (error) { close(); throw error; }
  };
  try {
    const env = {PATH: '/usr/bin:/bin', TMPDIR: path.join(episodeDir, 'tmp'), PYTHONHASHSEED: '0', PYTHONDONTWRITEBYTECODE: '1'};
    proc = openFifoProcess({python, args: [script, req, resp, '600'], cwd: episodeDir, env, req, resp, timeoutMs: 600000});
    let initial = proc.send({instance});
    return {
      read() { const line = initial; initial = null; return parse(line ?? proc.readLine()); },
      send: value => parse(proc.send(value)), close
    };
  } catch (error) { close(); throw error; }

}

export async function createDriver({ root, environmentModelCall = claudeCliJudgeCall } = {}) {
  if (!root) throw new Error('createDriver requires root (the package root)');
  const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
  const script = fileURLToPath(new URL('./discoverphysics-worker.py', import.meta.url));
  return {
    id: 'official-discoverphysics', version: 2, kind: 'interactive', maxSteps: 17, configurations,
    source: { kind: 'official', officialBenchmarkEquivalent: false, sourceUrls: SOURCE_URLS, engine: ENGINE, limitations: LIMITATIONS, recording: RECORDING,
      judgeRoute: { ...JUDGE_ROUTE, calls: 'one official ExplanationJudge call per evaluated final law' } },
    tool: { name: 'submit_action', description: ACTION_CONTRACT, parameters: PARAMETERS },
    actionContract: ACTION_CONTRACT,
    normalizeAction: normalizeDiscoverphysicsAction,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex ?? 0];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!/^[A-Za-z0-9_-]{1,120}$/.test(episode.id)) throw new Error('Invalid episode identity');
      const prefix = `episodes/${episode.id}`, episodeDir = path.join(runDir, prefix);
      for (const d of ['tmp', 'frames', 'dd-log']) fs.mkdirSync(path.join(episodeDir, d), { recursive: true });
      const worker = startWorker({ python: pythonFor(root, 'discoverphysics-runtime'), script, episodeDir, instance: configuration.instance });
                                                                                                                                    
      const judge = async raw => {
        const request = discoverphysicsJudgeRequest(raw);
        const response = await environmentModelCall({ taskId: ID, runDir, episodeId: episode.id, requestId: request.requestId, role: 'judge',
          model: request.model, temperature: JUDGE_ROUTE.temperature, system: request.system, turns: request.turns, maxTokens: request.maxTokens,
          responseProjection: JUDGE_ROUTE.responseProjection });
        if (!response || response.requestId !== request.requestId || typeof response.text !== 'string' || response.model !== request.model)
          throw environmentError('The environment judge returned an incomplete answer or a different model', 'source_model_response_invalid');
        return { source: JUDGE_SOURCE, requestId: request.requestId, model: response.model, text: response.text,
          usage: response.usage ?? null, finishReason: response.finishReason ?? null, responseFingerprint: response.responseFingerprint ?? null };
      };
      const settle = async out => { while (out.judgeRequest) out = worker.send({ judgeReply: await judge(out.judgeRequest) }); return out; };
      let closed = false, actions = [], last, state, observation;
                                                                                                                         
      const recordStep = (step, request, out) => {
        const csv = out.ddlog?.csv ?? null, dir = path.join(episodeDir, 'dd-log');
        const record = { schema: 'discoverphysics-ddlog-step-v1', taskId: ID, step, request: request ?? null,
          response: { state: out.state, text: out.text, reward: out.reward ?? 0, info: out.info ?? {}, terminal: out.terminal },
          judge: out.state?.evaluation?.explanation_judge?.record ?? null, csvFile: csv == null ? null : `step-${step}.trajectory.csv` };
        if (csv != null) fs.writeFileSync(path.join(dir, record.csvFile), csv);
        fs.writeFileSync(path.join(dir, `step-${step}.json`), JSON.stringify(record) + '\n');
      };
      const observe = () => {
        const step = state.step, stateHash = contentHash({ instance: configuration.instance, state });
        const framePath = `${prefix}/frames/step-${step}.png`, bytes = textFrame(last.text).png();
        const target = path.join(runDir, framePath);
        if (!fs.existsSync(target)) fs.writeFileSync(target, bytes);
        return { publicText: last.text, previewFrame: { path: framePath, mimeType: 'image/png', sha256: sha256(bytes) }, step, stateHash,
          configurationHash: configuration.configurationHash, reward: last.reward ?? 0, info: last.info ?? {}, terminal: last.terminal,
          instance: { taskId: ID, caseId: configuration.id, reconstruction: false } };
      };
      try {
        last = await settle(worker.read());
      } catch (error) { worker.close(); throw error; }
      state = { step: 0, actions: [], engine: last.state };
      recordStep(0, null, last);
      observation = observe();
      return {
        observation,
        async step(input) {
          if (closed) throw new Error('Official engine session closed');
          if (observation.terminal.ended) throw new Error('Official engine episode already ended');
          const action = normalizeDiscoverphysicsAction(input);
          if (!action) throw new Error('Malformed action');
          let out;
          try { out = await settle(worker.send(action)); }
          catch (error) { closed = true; worker.close(); throw error; }
          actions.push(action);
          last = out;
          state = { step: actions.length, actions: structuredClone(actions), engine: last.state };
          recordStep(state.step, action, out);
          observation = observe();
          return structuredClone(observation);
        },
        async close() { if (closed) return; closed = true; worker.close(); },
      };
    },
  };
}
