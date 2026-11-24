                                                                                                                 
                                                                                                       
                                                                                                                   
                                                                    
                                                                                                     
                                                                                          
            
                                                                                              
                                                                                                             
import fs from 'node:fs';
import {createInterface} from 'node:readline';
import { spawn } from 'node:child_process';
import { join } from 'node:path';
import { pythonFor as packagePython } from './python-env.mjs';

export class EnvError extends Error { constructor(msg) { super(msg); this.code = 'env_error'; } }

                                                                                         
                                                                                                         
export function pythonFor(name, ctx) {
  if (name === 'system') return process.env.UNSEEN17_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
  try { return packagePython(ctx.root, name); } catch (e) { throw new EnvError(e.message); }
}

const fill = (s, vars) => String(s).replace(/\{([A-Za-z_]+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`));

function opponentEnv() {
  const e = {};
  if (process.env.H0_OPPONENT_CODEX_HOME) e.CODEX_HOME = process.env.H0_OPPONENT_CODEX_HOME;
  return e;
}

                                                                                                                  
const TERMINALS = {
  actiview: ev => { const ok = !!ev.correct; return [{ ended: true, outcome: ok ? 'success' : 'failure', reason: 'official_answer', score: ok ? 1 : 0, evaluation: { official: { correct: ok, prediction: ev.prediction, gold: ev.gold, setting: ev.setting, viewsUsed: ev.viewsUsed, steps: ev.steps, droppedTokens: ev.droppedTokens ?? null } } },
    `[ActiView instance ended] ${ok ? 'correct' : 'incorrect'}; prediction ${JSON.stringify(ev.prediction)}; gold ${JSON.stringify(ev.gold)}`]; },
  hanabi: ev => [{ ended: true, outcome: ev.score === 25 ? 'success' : 'failure', reason: ev.lifeTokens === 0 ? 'official_all_lives_lost' : 'official_game_end', score: ev.score, evaluation: { official: { score: ev.score, fireworks: ev.fireworks, lifeTokens: ev.lifeTokens, informationTokens: ev.informationTokens, turns: ev.turns } } },
    `[Hanabi game ended] Official score ${ev.score}/25. Fireworks ${JSON.stringify(ev.fireworks)}; life tokens ${ev.lifeTokens}; turns ${ev.turns}.`],
  pencil: ev => [{ ended: true, outcome: ev.success ? 'success' : 'failure', reason: ev.reason, score: ev.success ? 1 : 0, evaluation: { official: { solved: ev.success, moves: ev.moves, turns: ev.turns, gaveUp: ev.gaveUp, pid: ev.pid } } },
    `[Pencil Puzzle episode ended] ${ev.success ? 'Solved' : 'Not solved'} (${ev.reason}); moves ${ev.moves}; tool calls ${ev.turns}. Last tool result: ${ev.lastMessage}`],
  phyre: ev => [{ ended: true, outcome: ev.solved ? 'success' : 'failure', reason: ev.reason, score: ev.solved ? 1 : 0, evaluation: { official: { solved: ev.solved, firstSuccessAttempt: ev.firstSuccessAttempt, attempts: ev.attempts, actions: ev.actions } } },
    `[PHYRE task ended] ${ev.solved ? 'SOLVED at attempt ' + ev.firstSuccessAttempt : 'Not solved'} (${ev.reason}); valid attempts ${ev.attempts}. ${ev.lastMessage}`],
  balrog: ev => { const st = ev.stats ?? {}; const prog = typeof st.progression === 'number' ? st.progression : 0;
    return [{ ended: true, outcome: prog >= 1 ? 'success' : 'failure', reason: ev.truncated || ev.steps >= ev.maxSteps ? 'official_step_limit' : 'official_episode_end', score: prog, evaluation: { official: { ...st, episodeReturn: ev.episodeReturn, steps: ev.steps, maxSteps: ev.maxSteps } } },
      `[BALROG episode ended] progression ${prog}; steps ${ev.steps}/${ev.maxSteps}; stats ${JSON.stringify(st)}`]; },
  coup: ev => [{ ended: true, outcome: ev.playerWon ? 'success' : 'failure', reason: 'official_game_end', score: ev.playerWon ? 1 : 0, evaluation: { official: { playerWon: ev.playerWon, winner: ev.winner, playerSeat: ev.playerSeat, rewards: ev.rewards, turns: ev.turns, playerDecisions: ev.playerDecisions, invalidMoves: ev.invalidMoves, forfeitedByInvalid: ev.forfeitedByInvalid, eliminationOrder: ev.eliminationOrder, stats: ev.stats, opponentCalls: ev.opponentCalls } } },
    `[Coup game ended] winner seat ${ev.winner}; your seat ${ev.playerSeat}; ${ev.playerWon ? 'you won' : 'you lost'}`],
  poker: ev => [{ ended: true, outcome: ev.playerChipDelta > 0 ? 'success' : 'failure', reason: 'official_episode_end', score: ev.bbPer100, evaluation: { official: { bbPer100: ev.bbPer100, playerChipDelta: ev.playerChipDelta, hands: ev.hands, illegal: ev.illegal, decisions: ev.decisions, pair: ev.pair, seat: ev.seat, presetLine: ev.presetLine, perHand: ev.perHand } } },
    `[Poker episode ended] ${ev.hands} hands; your chips ${ev.playerChipDelta}; BB/100 ${ev.bbPer100}`],
  videomme: ev => { const ok = !!ev.correct; return [{ ended: true, outcome: ok ? 'success' : 'failure', reason: 'official_answer', score: ok ? 1 : 0, evaluation: { official: { correct: ok, rawResponse: ev.rawResponse, prediction: ev.prediction, answer: ev.answer, groupId: ev.groupId, groupType: ev.groupType, groupStructure: ev.groupStructure, level: ev.level, frameSide: ev.frameSide } } },
    `[Video-MME-v2 question ended] ${ok ? 'correct' : 'incorrect'}; prediction ${JSON.stringify(ev.prediction)}; answer ${JSON.stringify(ev.answer)}`]; },
  scigym: ev => { const e = ev.evaluation ?? {};
    return [{ ended: true, outcome: ev.submitted ? 'success' : 'failure', reason: ev.submitted ? 'official_model_submitted' : 'no_valid_submission', score: typeof e.rp_f1 === 'number' ? e.rp_f1 : 0, evaluation: { official: e, iterations: ev.iterations, calls: ev.calls } },
      `[SciGym episode ended] Submitted: ${ev.submitted}. Official evaluation: ${JSON.stringify(e)}`]; },
};

const REPLY = {
  args: a => a,                                                                                                                            
  'move-int': a => ({ move: Number.isInteger(a?.move) ? a.move : 0 }),
  'scigym-text': a => ({ text: typeof a?.response === 'string' ? a.response : '' }),
};

                                                                                                                             
class JsonlBridgeSession {
  constructor(task, config, episodeDir, ctx) { this.task = task; this.config = config; this.dir = episodeDir; this.ctx = ctx; }
  async open() {
    const b = this.task.bridge, envDir = this.ctx.envDir;
    const vars = { ...this.config, ENV_DIR: envDir, EPISODE_DIR: this.dir };
    const extra = Object.fromEntries(Object.entries(b.env ?? {}).map(([k, v]) => [k, fill(v, vars)]));
    fs.mkdirSync(join(this.dir, 'scratch'), { recursive: true });
    for (const v of b.args) if (String(v).includes('{EPISODE_DIR}')) fs.mkdirSync(fill(v, vars), { recursive: true });
    const env = { ...process.env, ...opponentEnv(), H0_BRIDGE_SCRATCH: join(this.dir, 'scratch'), PYTHONDONTWRITEBYTECODE: '1', ...extra };
    if (this.task.env === 'phyre' && process.platform === 'darwin' && !env.PHYRE_PKG_DIR) env.PHYRE_PKG_DIR = join(envDir, 'phyre-macos-arm64-py39');
    this.p = spawn(pythonFor(this.task.python, this.ctx), ['-B', join(envDir, b.script), ...b.args.map(a => fill(a, vars))], { cwd: envDir, stdio: ['pipe', 'pipe', 'pipe'], env });
    const log = fs.createWriteStream(join(this.dir, 'bridge-stderr.log'), {flags: 'a'});
    log.on('error', () => this.close()); this.p.stderr.pipe(log);
    this.queue = []; this.waiter = null; this.closed = false; let buf = '';
    this.p.stdin.on('error', () => this.close()); this.p.stdout.on('error', () => this.close());
    this.p.stdout.on('end', () => this.close());
    this.p.stdout.setEncoding('utf8');
    this.p.stdout.on('data', d => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); if (!line.trim()) continue;
      let m; try { m = JSON.parse(line); if (!m || typeof m !== 'object' || Array.isArray(m)) throw Error('Expected an object'); } catch { m = { kind: 'error', message: 'bridge wrote a non-JSON line: ' + line.slice(0, 200) }; }
      if (this.waiter) { const w = this.waiter; this.waiter = null; w(m); } else this.queue.push(m); } });
    this.p.on('close', code => { this.closed = true; if (this.waiter) { const w = this.waiter; this.waiter = null; w({ kind: 'exit', code }); } });
    this.p.on('error', err => { this.closed = true; if (this.waiter) { const w = this.waiter; this.waiter = null; w({ kind: 'exit', code: -1, message: String(err) }); } });
    try { return this.#observe(await this.#next()); } catch (error) { this.close(); throw error; }
  }
  #raw() { return new Promise(res => { if (this.queue.length) res(this.queue.shift()); else if (this.closed) res({ kind: 'exit' }); else if (this.waiter) res({kind: 'error', message: 'Concurrent environment read'}); else this.waiter = res; }); }
  async #next() {
    const skip = new Set(this.task.bridge.skipKinds ?? []), configured = this.task.bridge.stepTimeoutMs;
    const deadline = Date.now() + (Number.isFinite(configured) && configured > 0 ? configured : 180000);
    for (;;) {
      let timer,m; const ms = Math.max(1, deadline - Date.now());
      try{m = ms ? await Promise.race([this.#raw(), new Promise(res => {timer=setTimeout(() => res({ kind: 'timeout' }), ms);})]) : await this.#raw();}
      finally{clearTimeout(timer);}
      if (m.kind === 'timeout') { this.close(); return m; }
      if (!skip.has(m.kind)) return m;
    }
  }
  #observe(ev) {
    if (ev.kind === 'player_request') return { text: String(ev.message ?? ''), images: ev.images ?? [], terminal: null };
    if (ev.kind === 'terminal') { const [terminal, text] = TERMINALS[this.task.terminal](ev); return { text, images: [], terminal }; }
    if (ev.kind === 'timeout') throw new EnvError(`environment step exceeded ${Math.round(this.task.bridge.stepTimeoutMs / 60000)} min`);
    throw new EnvError(`environment bridge ${ev.kind === 'exit' ? 'exited (code ' + ev.code + ')' : 'error'}: ${String(ev.message ?? '').slice(0, 300)}`);
  }
  async step(args) {
    if (this.closed) throw new EnvError('environment bridge is closed');
    this.p.stdin.write(JSON.stringify(REPLY[this.task.bridge.reply](args)) + '\n');
    return this.#observe(await this.#next());
  }
  stop(reason) { return { text: `[Episode stopped] ${reason}`, images: [], terminal: { ended: true, outcome: 'failure', reason, score: 0, evaluation: { stoppedBy: reason } } }; }
                                                                                                                       
                                                                                                                          
  async hostEnd(reason = 'h0_output_cap_exhausted') {
    if (this.task.terminal !== 'pencil') throw new EnvError('hostEnd is defined for pencil only');
    this.p.stdin.write(JSON.stringify({ tool: '__host_end__', reason }) + '\n');
    const ev = await this.#next();
    if (ev.kind !== 'terminal') throw new EnvError('pencil bridge did not end the episode on __host_end__');
    return { text: `[Pencil Puzzle episode ended] Not solved (H0 reached the 16384-token response cap 3 times in a row without an action); moves ${ev.moves}.`, images: [],
      terminal: { ended: true, outcome: 'failure', reason, score: 0, evaluation: { official: { solved: ev.success, moves: ev.moves, turns: ev.turns, gaveUp: false, pid: ev.pid } } } };
  }
  close() {
    this.closed = true;
    if (this.waiter) { const waiter = this.waiter; this.waiter = null; waiter({kind: 'exit', message: 'Bridge closed'}); }
    this.p?.stdin.destroy();
    if (this.p?.pid && this.p.exitCode === null && this.p.signalCode === null) this.p.kill('SIGKILL');
  }
}

                                                                                                                                     

function workerRpc(child, timeoutMs = 180000) {
  let id = 0, failure = null;
  const pending = new Map(), lines = createInterface({input: child.stdout});
  const fail = error => {
    if (failure) return;
    failure = error;
    for (const p of pending.values()) { clearTimeout(p.timer); p.reject(error); }
    pending.clear(); child.stdin.destroy();
    if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
  };
  lines.on('line', line => {
    if (failure || !line.trim()) return;
    let reply;
    try { reply = JSON.parse(line); if (!reply || typeof reply !== 'object' || Array.isArray(reply)) throw Error('Expected an object'); }
    catch { fail(new EnvError('Invalid worker JSON')); return; }
    const p = pending.get(reply.id);
    if (!p) { fail(new EnvError('Unknown worker response identity')); return; }
    pending.delete(reply.id); clearTimeout(p.timer);
    if (reply.ok) p.resolve(reply.result);
    else p.reject(new EnvError('EDA worker: ' + String(JSON.stringify(reply.error) ?? 'Unknown worker error').slice(0, 300)));
  });
  child.on('error', fail); child.stdin.on('error', fail); child.stdout.on('error', fail);
  child.on('exit', (code, signal) => fail(new EnvError('Worker exited: ' + (signal || code))));
  lines.on('close', () => fail(new EnvError('Worker output closed')));
  return {
    fail,
    call(command, extra = {}) {
      if (failure) return Promise.reject(failure);
      if (child.exitCode !== null || child.signalCode !== null) return Promise.reject(new EnvError('Worker has ended'));
      const rid = ++id;
      return new Promise((resolve, reject) => {
        const data = JSON.stringify({...extra, id: rid, command}) + '\n';
        const timer = setTimeout(() => fail(new EnvError('Worker request timed out')), timeoutMs);
        pending.set(rid, {resolve, reject, timer});
        try { child.stdin.write(data, error => { if (error) fail(error); }); } catch (error) { fail(error); }
      });
    },
    close() { fail(new EnvError('Worker closed')); }
  };
}

class EdaSession {
  constructor(task, config, episodeDir, ctx) { this.task = task; this.config = config; this.dir = episodeDir; this.ctx = ctx; this.judgeCalls = 0; }
  async open() {
    const envDir = this.ctx.envDir;
    this.p = spawn(pythonFor('eda', this.ctx), ['-I', '-B', join(envDir, 'eda-source-class-worker.py')], { stdio: ['pipe', 'pipe', 'pipe'] });
    this.rpc = workerRpc(this.p);
    const log = fs.createWriteStream(join(this.dir, 'bridge-stderr.log'), {flags: 'a'});
    log.on('error', error => this.rpc.fail(error)); this.p.stderr.pipe(log);
    this.cmd = (command, extra) => this.rpc.call(command, extra);
    const sess = join(this.dir, 'eda-session'); fs.mkdirSync(sess, { recursive: true });
    const { id: _id, ordinal, ...entity } = this.config;
    try { return this.#observe(await this.#settle(await this.cmd('init', { configuration: { ...entity, sessionIndex: 0 }, sessionDir: sess }))); }
    catch (error) { this.close(); throw error; }
  }
  async #settle(ev) { while (ev.kind === 'judge_request') ev = await this.cmd('judge_response', { text: await this.#judge(ev.judgeRequest) }); return ev; }
  #codex(prompt, outFile) {
    const bin = process.env.H0_OPPONENT_CODEX_BIN || 'codex', cwd = join(this.dir, 'judge'); fs.mkdirSync(cwd, { recursive: true });
    return new Promise((res, rej) => {
      const p = spawn(bin.endsWith('.py')?(process.env.PYTHON??(process.platform==='win32'?'python':'python3')):bin, [...(bin.endsWith('.py')?[bin]:[]),'exec', '--skip-git-repo-check', '-s', 'read-only', '-m', 'gpt-5.6-luna', '-c', 'model_reasoning_effort=low', '-o', outFile, prompt],
        { cwd, stdio: ['ignore', 'ignore', 'pipe'], env: { ...process.env, ...opponentEnv() } });
      let err = ''; p.stderr.on('data', d => { err += d; }); p.on('error', e => rej(new EnvError('judge codex failed to start: ' + e.message)));
      const t = setTimeout(() => p.kill('SIGKILL'), 180000);
      p.on('close', code => { clearTimeout(t); if (code !== 0) return rej(new EnvError('judge codex exit ' + code + ': ' + err.slice(-300))); try { res(fs.readFileSync(outFile, 'utf8').trim()); } catch (error) { rej(new EnvError('Judge output unavailable: ' + error.message)); } });
    });
  }
  async #judge(request) {
    const allowed = this.config.category === 'things' ? ['Yes.', 'No.', 'Maybe.'] : ['Yes.', 'No.', 'Dunno.'];
    const prompt = 'You are the answerer (judge) in a 20-questions game. Below are the exact chat messages of the original judge prompt as JSON. '
      + 'Reply as the assistant to the last message, following its instructions. Output only your reply, which must be exactly one of: ' + allowed.join(' ') + '\n\n' + JSON.stringify(request.messages);
    for (let attempt = 0; attempt < 4; attempt++) {
      try { const raw = await this.#codex(prompt, join(this.dir, 'judge', `judge-${++this.judgeCalls}.txt`)); const m = raw.match(/\b(yes|no|maybe|dunno)\b/i);
        if (m) { const v = allowed.find(a => a.toLowerCase().startsWith(m[1].toLowerCase())); if (v) return v; } } catch (e) { if (attempt === 3) throw e; }
    }
    throw new EnvError('judge out-of-vocabulary');
  }
  #observe(ev) {
    const pub = ev.publicObservation, text = JSON.stringify(pub);
    if (ev.kind === 'terminal' || pub?.ended) {
      const t = pub.terminal ?? {};
      return { text, images: [], terminal: { ended: true, outcome: t.outcome, reason: t.outcome === 'success' ? 'original_answerer_bingo' : 'original_20_turn_cap', score: t.officialMetrics?.score ?? 0, evaluation: { officialSerializedMetrics: t.officialMetrics } } };
    }
    return { text, images: [], terminal: null };
  }
  async step(args) { return this.#observe(await this.#settle(await this.cmd('act', { text: typeof args?.text === 'string' ? args.text : '' }))); }
  stop(reason) { return { text: `[Episode stopped] ${reason}`, images: [], terminal: { ended: true, outcome: 'failure', reason, score: 0, evaluation: { stoppedBy: reason } } }; }
  close() { this.rpc?.close(); }
}

                                                                                                                               
                                                                                                                              
                                                                                                                      
const DIG_API = process.env.DIGBENCH_API_URL || 'https://api.digbench.ai/api/agent';
function digToken() {
  const t = process.env.DIGBENCH_TOKEN || (process.env.DIGBENCH_TOKEN_FILE && fs.existsSync(process.env.DIGBENCH_TOKEN_FILE) ? fs.readFileSync(process.env.DIGBENCH_TOKEN_FILE, 'utf8') : '');
  if (!t.trim()) throw new EnvError('DiG-bench token missing: set DIGBENCH_TOKEN or DIGBENCH_TOKEN_FILE');
  return t.trim();
}
const stateForModel = s => { const out = { observation: s?.observation ?? '', level: s?.level ?? null, max_level: s?.max_level ?? null, lives_left: s?.lives_left ?? null,
  steps_remaining: s?.steps_remaining ?? null, status: s?.status ?? null, done: s?.done ?? null, legal_actions: s?.actions ?? [] };
  if (s?.mode != null) { out.mode = s.mode; out.creative_toggle = s.creative_toggle ?? null; } if (s?.transition != null) out.transition = s.transition; return out; };
const pyRepr = v => `'${String(v).replaceAll('\\', '\\\\').replaceAll("'", "\\'")}'`;
function pyJson(v, indent = null) {                                
  const esc = str => JSON.stringify(str).replace(/[\u007f-￿]/g, c => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));
  const go = (x, lvl) => { if (x === null || typeof x !== 'object') return typeof x === 'string' ? esc(x) : JSON.stringify(x);
    const pad = indent == null ? '' : '\n' + ' '.repeat(indent * (lvl + 1)), end = indent == null ? '' : '\n' + ' '.repeat(indent * lvl), sep = indent == null ? ', ' : ',';
    if (Array.isArray(x)) return x.length ? '[' + x.map(y => pad + go(y, lvl + 1)).join(sep) + end + ']' : '[]';
    const ks = Object.keys(x); return ks.length ? '{' + ks.map(k => pad + esc(k) + ': ' + go(x[k], lvl + 1)).join(sep) + end + '}' : '{}'; };
  return go(v, 0);
}
function creativeModeInstruction(toggle) {
  if (!toggle) return ''; const action = JSON.stringify(toggle);
  return 'Important: creative mode\n'
    + 'At nearly any time, you can use a button to switch into "creative mode", where you can experiment safely without losing steps or lives.\n'
    + 'It may be necessary to use creative mode in order to discover the rules of the game without running out of steps.\n\n'
    + `Call \`submit_action\` with action ${action} to enter creative mode.\n`
    + `Call \`submit_action\` with action ${action} again to return to survival mode.\n`
    + `Only submit ${action} when it appears in \`legal_actions\`.`;
}
const okState = s => s && typeof s.observation === 'string' && Array.isArray(s.actions) && typeof s.done === 'boolean' && Number.isInteger(s.level);
const levelsBeaten = b => Number.isInteger(b?.levels_beaten) ? b.levels_beaten
  : !Number.isInteger(b?.state?.level) ? 0 : b.state.status === 'completed' && Number.isInteger(b.state.max_level) ? b.state.max_level : Math.max(0, b.state.level - 1);

class DigSession {
  constructor(task, config, episodeDir, ctx) { this.task = task; this.config = config; this.dir = episodeDir; this.ctx = ctx; this.turns = 0; this.consecutiveInvalid = 0; }
  async #call(method, path, body) {
    const token = digToken();
    for (let attempt = 1; ; attempt++) {
      let status = 0, json = null;
      try {
        const ctl = new AbortController(), timer = setTimeout(() => ctl.abort(), 60000);
        const res = await fetch(DIG_API + path, { method, redirect: 'error', signal: ctl.signal,
          headers: { Authorization: `Bearer ${token}`, Accept: 'application/json', 'User-Agent': 'h0-unseen17-env/1', ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined });
        clearTimeout(timer); status = res.status; json = await res.json().catch(() => null);
      } catch { status = 0; }
      fs.appendFileSync(join(this.dir, 'server-recording.jsonl'), JSON.stringify({ at: new Date().toISOString(), method, path: path.replace(/\/sessions\/[^/?]+/, '/sessions/{id}'), request: body ?? null, status, body: json }) + '\n');
      if (status === 401 || status === 403) throw new EnvError(`DiG-bench token rejected (HTTP ${status})`);
      if ((status === 0 || status === 429 || status >= 500) && attempt < 8) { await new Promise(r => setTimeout(r, Math.min(120000, 5000 * 2 ** attempt))); continue; }
      return { status, body: json };
    }
  }
  #terminal(extra = null) {
    if (extra) return extra; const s = this.body?.state; if (!s?.done) return null; const lb = levelsBeaten(this.body);
    return { ended: true, outcome: s.status === 'completed' ? 'success' : 'failure', reason: `server_status_${s.status}`, score: lb,
      evaluation: { official: { status: s.status, levels_beaten: lb, level: s.level, max_level: s.max_level ?? null, step_index: this.body.step_index } } };
  }
  async open() {
    const r = await this.#call('POST', '/sessions', { game: this.config.game, model_name: `h0-unseen17-${this.ctx.harness}`, model_version: 'unseen-dig_bench', notes: JSON.stringify({ client: 'h0-unseen17-env', harness: this.ctx.harness, run: this.ctx.runId }) });
    if (r.status !== 200 || !okState(r.body?.state) || typeof r.body?.session_id !== 'string') throw new EnvError(`DiG-bench start failed HTTP ${r.status}`);
    this.body = r.body; this.state = r.body.state; this.session = r.body.session_id; this.stepIndex = r.body.step_index;
    fs.writeFileSync(join(this.dir, 'server-session.json'), JSON.stringify({ sessionId: this.session, seed: r.body.seed ?? null, frameworkVersion: r.body.framework_version ?? null }, null, 1));
    const slice = stateForModel(this.state), creative = creativeModeInstruction(slice.creative_toggle);
    const text = 'You are now playing this game.\n\n' + (creative ? creative + '\n\n' : '') + 'TASK DESCRIPTION (objective + any special actions, NOT the rules):\n'
      + (r.body.description || '(none provided)') + '\n\nINITIAL STATE:\n' + pyJson(slice, 2) + '\n\nReason about it, then call submit_action.';
    return { text, images: [], terminal: this.#terminal() };
  }
  #result(action, kind) {
    const result = stateForModel(this.state); if (kind === 'local_illegal') delete result.transition;
    result.invalid_action = kind !== 'ok'; if (kind !== 'ok') result.note = `${pyRepr(action)} is not legal — pick one of legal_actions.`;
    return pyJson({ result });
  }
  stop(reason, label = reason) {
    const lb = levelsBeaten(this.body);
    return { text: `[DiG-bench run stopped] ${label}; levels_beaten ${lb}`, images: [], terminal: { ended: true, outcome: 'failure', reason, score: lb,
      evaluation: { official: { status: reason, levels_beaten: lb, level: this.state?.level ?? null, max_level: this.state?.max_level ?? null, turns: this.turns } } } };
  }
  async step(args) {
    const action = typeof args?.action === 'string' ? args.action : '';
    let text, terminal = null, invalid;
    this.turns++;
    if (!this.state.actions.includes(action)) { invalid = true; text = this.#result(action, 'local_illegal'); }
    else {
      const s = await this.#call('POST', `/sessions/${encodeURIComponent(this.session)}/step`, { step_index: this.stepIndex + 1, action });
      if (s.status !== 200 || !okState(s.body?.state)) throw new EnvError(`DiG-bench step failed HTTP ${s.status}`);
      this.body = s.body; this.state = s.body.state; this.stepIndex = s.body.step_index; invalid = s.body.invalid_action === true;
      terminal = this.#terminal(); text = this.#result(action, invalid ? 'server_invalid' : 'ok');
    }
    this.consecutiveInvalid = invalid ? this.consecutiveInvalid + 1 : 0;
    const L = this.task.limits ?? {};
    if (!terminal && this.consecutiveInvalid > (L.maxConsecutiveInvalid ?? 5)) return this.stop('blocked', `more than ${L.maxConsecutiveInvalid ?? 5} consecutive invalid moves`);
    if (!terminal && this.turns >= (L.maxTurns ?? 3000)) return this.stop('max_steps', `turn cap ${L.maxTurns ?? 3000} reached`);
    return { text, images: [], terminal };
  }
  close() {}
}

export function openSession(task, config, episodeDir, ctx) {
  const S = task.adapter === 'eda' ? EdaSession : task.adapter === 'dig' ? DigSession : JsonlBridgeSession;
  return new S(task, config, episodeDir, ctx);
}

                                                                                                                           
export function validateArgs(schema, args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return 'arguments must be a JSON object';
  for (const k of schema.required ?? []) if (!(k in args)) return `missing required field "${k}"`;
  for (const [k, v] of Object.entries(args)) {
    const p = schema.properties?.[k];
    if (!p) { if (schema.additionalProperties === false) return `unexpected field "${k}"`; continue; }
    const ok = p.type === 'integer' ? Number.isInteger(v) : p.type === 'number' ? typeof v === 'number' && Number.isFinite(v)
      : p.type === 'array' ? Array.isArray(v) && (!p.items?.type || v.every(x => typeof x === p.items.type)) : p.type ? typeof v === p.type : true;
    if (!ok) return `field "${k}" must be of type ${p.type}${p.items?.type ? ' of ' + p.items.type : ''}`;
    if (p.enum && !p.enum.includes(v)) return `field "${k}" must be one of ${p.enum.join(', ')}`;
  }
  return null;
}
