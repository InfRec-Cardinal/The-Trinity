                                                                                                                          
                                                                                                                          
                                                                                                                     
                                                                                                                     
                                                                                                       
                                                                                                                     
                                                                                                 
                                                                                                                    
                                                         
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { createHash } from 'node:crypto';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const MAX_ACTIONS = 30, MAX_MOVES = 5, STEP_MAX_CM = 10, TURN_MAX_DEG = 90;
const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;
const PHYSICS = fileURLToPath(new URL('../../capxi/physics.py', import.meta.url));
const PYTHON = process.env.CAPXO_PYTHON || process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');                                
const sha256 = b => createHash('sha256').update(b).digest('hex');
const OPS = ['move', 'turn', 'open', 'close', 'home'];

const PREAMBLE = `You are controlling a bimanual AlohaMini2 robot: a mobile robot with a lift and two 6-DoF arms, each ending in a gripper. The robot stands at the near edge of a table and faces it; its base and lift stay still. Arm 0 is the robot's left arm, arm 1 its right arm.
What you get: only the robot's own camera images and this text. Each image shows three views side by side: the head camera (on top of the robot's mast, looking forward and down at the table), the left wrist camera (on arm 0's gripper) and the right wrist camera (on arm 1's gripper). A wrist camera sits on its gripper above the fingers and looks along them: the gripper's two fingers come into its image from the bottom, with the table and the objects ahead of and between the fingertips beyond them; the view moves and turns with the gripper. At turn 0 the right side of every view is the robot's right and the top of the view is away from the robot. There is no depth, no coordinates and no object detection; judge positions and heights from the images.
How you act: with small gripper moves. A move shifts the gripper of one arm in a straight line; the arm's joints follow automatically.
- "move": right_cm / forward_cm / up_cm, each between -${STEP_MAX_CM} and ${STEP_MAX_CM}. right = towards the robot's right = towards the right side of the image; forward = away from the robot = towards the top of the image; up = vertically up (negative = down).
- "turn": turn_deg between -${TURN_MAX_DEG} and ${TURN_MAX_DEG}; turns the gripper about the vertical axis, positive = clockwise as seen in the image.
- "open" / "close": open or close the gripper.
- "home": raise the gripper and move it back to its start pose (its arm's start pose; the turn goes back to 0).
Grippers always point forward and down, tilted about 35 degrees from vertical towards their turn direction (at turn 0: away from the robot); moves keep this tilt. Each gripper has one fixed finger and one moving finger: closing swings the moving finger towards the fixed one, so a grasped object ends up pressed against the fixed finger. At turn 0 the fingers are side by side along the robot's left-right direction, the fixed finger on the left and the moving finger on the right; the fingers close along that line. The open fingers are about 6 cm apart at the tips; the fingertips reach about 2 cm beyond the middle of the gripper along the fingers. A safety limit keeps the fingertips just above the table top; moves that hit it, an object, or the arm's reach stop early, and the result says so.
Start: both grippers are open, turned 0, in their start pose above the left and right parts of the work area with the fingertips about 16 cm above the table.
Each response submits one action: a list of 1 to ${MAX_MOVES} moves, executed in order; then you get the result of every move and a new image of the three camera views. At most ${MAX_ACTIONS} actions per trial. Finish the trial with the finish action (with the answer, if the task asks for one).`;

function instruction(c) {
  if (c.task === 'C') return `Goal (cup search): there are 3 identical opaque paper cups standing upside down on the table (9 cm tall, 7 cm across the mouth on the table, 5 cm across the closed bottom on top), numbered 1 to 3 on their tops. There may be one small wooden cube (2 cm; red, green or blue) under one of them, or there may be none. Lift one cup at a time to look under it and put it back down where it was after looking. Finish with the answer: the cube's colour and the number of the cup it is under, for example "red, cup 2", or "none" if there is no cube under any cup.\nSuccess: with a cube, the answer names its colour and its cup, and that cup was lifted; without a cube, the answer is "none" and all 3 cups were lifted.`;
  if (c.task === 'H1') return `Goal (Cube Restack): there are a red, a green and a blue wooden cube (4 cm) on the table; the green cube is stacked on top of the red cube. Rebuild the stack the other way round: put the red cube on top of the green cube (two layers, the green cube on the table), release it, then finish. The blue cube is not part of the task.\nSuccess: at the end the red cube rests on the green cube, the green cube stands on the table, nothing is held, and the stack has stayed up for 3 seconds after release.`;
  if (c.task === 'H2') return `Goal (three-layer tower): there are a red, a green and a blue wooden cube (4 cm) on the table. Build a tower of all three cubes: the ${c.bottom} cube at the bottom (on the table), the ${c.middle} cube in the middle and the ${c.top} cube on top. Release the cubes, then finish.\nSuccess: at the end the ${c.middle} cube rests on the ${c.bottom} cube, the ${c.top} cube rests on the ${c.middle} cube, the ${c.bottom} cube stands on the table, nothing is held, and the tower has stayed up for 3 seconds after release.`;
  const cups = 'There are 5 identical opaque cups (about 7.5 cm tall) standing upside down on the table, numbered 1 to 5 on their tops.';
  return `Goal (presence search): ${cups} There may be a small lime under one of them, or there may be none. Lift one cup at a time to look and put it back down where it was after looking. If you find the lime, put that cup down on a free part of the table away from the lime so the lime is uncovered, and finish with the answer "yes, cup N". If you are sure there is no lime, finish with the answer "none".\nSuccess: with a lime, the lime is uncovered and visible at the end and the answer names the right cup; without a lime, the answer is "none" and all 5 cups were lifted to look under them. Answering "none" without lifting every cup is a failure.`;
}

function physicsProcess() {
  const proc = spawn(PYTHON, ['-I', PHYSICS], { stdio: ['pipe', 'pipe', 'pipe'], env: { ...process.env, MUJOCO_GL: process.env.MUJOCO_GL || (process.platform === 'darwin' ? 'cgl' : process.platform === 'linux' ? 'egl' : 'glfw'), CAPXI_VIEW: 'robot', CAPXI_SOLID_CUPS: '1', CAPXI_WOBBLE: '1' } });                                                      
  let buf = '', err = '', failure = null;
  const waiting = [];
  const configuredTimeout = Number(process.env.CAPXO_PHYSICS_TIMEOUT_MS ?? 180000);
  const timeoutMs = Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 180000;
  const fail = error => {
    if (failure) return;
    failure = error;
    for (const pending of waiting.splice(0)) { clearTimeout(pending.timer); pending.reject(error); }
    proc.stdin.destroy();
    if (proc.pid && proc.exitCode === null && proc.signalCode === null) proc.kill('SIGKILL');
  };
  proc.stdout.setEncoding('utf8');
  proc.stdout.on('data', d => {
    if (failure) return;
    buf += d;
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i); buf = buf.slice(i + 1);
      let value;
      try { value = JSON.parse(line); if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Expected an object'); }
      catch { fail(new Error('Invalid JSON response from physics process')); return; }
      const pending = waiting.shift();
      if (!pending) { fail(new Error('Unexpected response from physics process')); return; }
      clearTimeout(pending.timer); pending.resolve(value);
    }
  });
  proc.stderr.on('data', d => { err += d; if (err.length > 20000) err = err.slice(-10000); });
  proc.on('error', error => fail(new Error('Could not start physics process: ' + error.message)));
  proc.on('exit', (code, signal) => fail(new Error('Physics process ended (' + (signal || code) + '): ' + err.slice(-500))));
  proc.stdin.on('error', error => fail(new Error('Physics input failed: ' + error.message)));
  proc.stdout.on('error', error => fail(new Error('Physics output failed: ' + error.message)));
  proc.stdout.on('end', () => fail(new Error('Physics output closed: ' + err.slice(-500))));
  let chain = Promise.resolve();
  const request = req => (chain = chain.then(() => new Promise((resolve, reject) => {
    if (failure) return reject(failure);
    if (proc.exitCode !== null || proc.signalCode !== null) return reject(new Error('Physics process has ended'));
    let data;
    try { data = JSON.stringify(req) + '\n'; } catch (error) { reject(error); return; }
    const pending = {resolve, reject, timer: setTimeout(() => fail(new Error('Physics request timed out after ' + timeoutMs + ' ms')), timeoutMs)};
    waiting.push(pending);
    try { proc.stdin.write(data, error => { if (error) fail(new Error('Physics input failed: ' + error.message)); }); }
    catch (error) { fail(error); }
  })));
  return { request, close() { fail(new Error('Physics process closed')); } };
}

const num = v => (typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : 0);
function normalizeMove(m) {
  if (!m || typeof m !== 'object') return null;
  const arm = m.arm === 'left' ? 0 : m.arm === 'right' ? 1 : Number(m.arm);
  if (arm !== 0 && arm !== 1) return null;
  if (!OPS.includes(m.op)) return null;
  const out = { arm, op: m.op };
  if (m.op === 'move') {
    for (const k of ['right_cm', 'forward_cm', 'up_cm']) { const v = num(m[k] ?? 0); if (!Number.isFinite(v) || Math.abs(v) > STEP_MAX_CM) return null; out[k] = v; }
    if (!out.right_cm && !out.forward_cm && !out.up_cm) return null;
  }
  if (m.op === 'turn') { const v = num(m.turn_deg ?? 0); if (!Number.isFinite(v) || Math.abs(v) > TURN_MAX_DEG || v === 0) return null; out.turn_deg = v; }
  return out;
}
function normalizeAction(input) {
  if (!input || typeof input !== 'object') return null;
  if (input.kind === 'finish') return { kind: 'finish', moves: [], answer: typeof input.answer === 'string' ? input.answer.trim() : '' };
  if (input.kind !== 'act' || !Array.isArray(input.moves) || input.moves.length < 1 || input.moves.length > MAX_MOVES) return null;
  const moves = input.moves.map(normalizeMove);
  if (moves.some(m => !m)) return null;
  return { kind: 'act', moves, answer: '' };
}

export async function createDriver() {
  return {
    id: 'capx-cupsearch-v2-simulation', version: 2, kind: 'interactive', maxSteps: MAX_ACTIONS + 1,
    tool: { name: 'submit_action', description: 'Submit one action (1 to 5 gripper moves, executed in order), or finish the trial.',
      parameters: { type: 'object', additionalProperties: false, required: ['kind', 'moves', 'answer'],
        properties: {
          kind: { type: 'string', enum: ['act', 'finish'] },
          moves: { type: 'array', description: `1 to ${MAX_MOVES} moves, executed in order`, items: { type: 'object', additionalProperties: false, required: ['arm', 'op'],
            properties: { arm: { type: 'integer', enum: [0, 1] }, op: { type: 'string', enum: OPS },
              right_cm: { type: 'number' }, forward_cm: { type: 'number' }, up_cm: { type: 'number' }, turn_deg: { type: 'number' } } } },
          answer: { type: 'string' } } } },
    actionContract: `Each response submits exactly one action: {"kind":"act","moves":[{"arm":0|1,"op":"move","right_cm":x,"forward_cm":y,"up_cm":z} | {"arm":0|1,"op":"turn","turn_deg":d} | {"arm":0|1,"op":"open"|"close"|"home"}, ... (1 to ${MAX_MOVES})],"answer":""} or {"kind":"finish","moves":[],"answer":"<final answer or empty>"}. Distances in cm (each at most ${STEP_MAX_CM}), turns in degrees (at most ${TURN_MAX_DEG}). At most ${MAX_ACTIONS} actions per trial. Only the judgement of the final state decides success.`,
    normalizeAction,
    invalidActionPolicy: { reprompts: 2, exhaustedAction: { kind: 'finish', moves: [], answer: '' }, exhaustedOutcome: 'finish_without_answer', scoreDefined: true },
    source: { kind: 'cup_search_v2_robot_cameras_simulated_alohamini2', urls: ['https://arxiv.org/abs/2603.22435', 'https://github.com/capgym/cap-x', 'https://github.com/liyiteng/AlohaMini'],
      recording: 'Player side: record.jsonl with every action, result and image; actions/NN.json (moves, results, replay frame range); replay/ third-person frames; simulator judgement in the terminal evaluation.' },
    configurations,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const conf = list[episode.configurationIndex];
      const rel = `episodes/${episode.id}`, trialId = `sim-${conf.id}`, epDir = join(runDir, rel);
      mkdirSync(join(epDir, 'frames'), { recursive: true }); mkdirSync(join(epDir, 'actions'), { recursive: true });
      const phys = physicsProcess();
      try {
      const p0 = await phys.request({ cmd: 'reset', conf, replay_dir: join(epDir, 'replay') }); if (!p0.ok) throw new Error(p0.error);
      let actions = 0;
      const head = `${PREAMBLE}\n\n${instruction(conf)}`;
      const frame = async step => {
        const relPath = `${rel}/frames/step-${step}.png`, r = await phys.request({ cmd: 'image', path: join(runDir, relPath) }); if (!r.ok) throw new Error(r.error);
        const bytes = readFileSync(join(runDir, relPath)); return { path: relPath, mimeType: 'image/png', sha256: sha256(bytes) };
      };
      const obs = async (text, step, terminal = { ended: false, outcome: null, reason: null, score: null }) => ({
        publicText: text, frame: await frame(step), step, terminal, reward: terminal.outcome === 'success' ? 1 : 0,
        stateHash: sha256(`${trialId}:${step}:${text}`), info: { trialId, actionsUsed: actions } });
      const finish = async (answer, reason, step, before = '') => {
        const r = await phys.request({ cmd: 'judge', answer }); if (!r.ok) throw new Error(r.error);
        writeFileSync(join(epDir, 'judge.json'), JSON.stringify({ frames: r.frames, checks: r.checks, detail: r.detail, counts: r.counts, state: r.state }));
        const outcome = reason === 'agent_finished' && r.success ? 'success' : 'failure';
        return obs(`${before}Trial ended (${reason}). Judgement: ${outcome}.`, step,
          { ended: true, outcome, reason, score: outcome === 'success' ? 1 : 0,
            evaluation: { official: { judgement: outcome, checks: r.checks, detail: r.detail, counts: r.counts, answer, actions, takeover: false } } });
      };
      return {
        observation: await obs(`${head}\n\nThe trial has started. Actions used: 0 of ${MAX_ACTIONS}. The image shows the current camera views (head, left wrist, right wrist).`, 0),
        async step(action) {
          const a = normalizeAction(action); const step = actions + 1;
          if (!a) throw new Error('illegal action');
          if (a.kind === 'finish') return finish(a.answer, 'agent_finished', step);
          actions++;
          const r = await phys.request({ cmd: 'act', moves: a.moves }); if (!r.ok) throw new Error(r.error);
          writeFileSync(join(epDir, 'actions', `${String(actions).padStart(2, '0')}.json`), JSON.stringify({ moves: a.moves, results: r.result, frames: r.frames, state: r.state }));
          const text = `Action ${actions} of ${MAX_ACTIONS}:\n${r.result.map((x, i) => `${i + 1}. ${x}`).join('\n')}\nThe image shows the camera views (head, left wrist, right wrist) after the action.`;
          if (actions >= MAX_ACTIONS) return finish('', 'action_budget_used', step, text + '\n\n');
          return obs(text, step);
        },
        async close() { phys.close(); }
      };
      } catch (error) { phys.close(); throw error; }
    }
  };
}
