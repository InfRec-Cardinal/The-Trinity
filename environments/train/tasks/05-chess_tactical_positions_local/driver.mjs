                                                                                                            
                                                                                                              
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import { Raster } from '../../lib/raster.mjs';

const TASK_ID = 'chess_tactical_positions_local';
const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
                                                                      
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(v => canonical(v) ?? 'null').join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
const contentHash = value => sha256(canonical(value));

                                                         
const RAW = JSON.parse(readFileSync(new URL('./instances.json', import.meta.url), 'utf8'));

                                                                   
const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;

const boardText = rows => rows.map((row, index) => `${8 - index} ${[...row].join(' ')}`).join('\n') + '\n  a b c d e f g h';

function render(instance, result = null) {
  const raster = new Raster(520, 600, [243, 246, 248]), tile = 56, ox = 34, oy = 60;
  raster.text(`CHESS TACTIC MATE IN ${instance.horizon}`, 24, 16, [35, 49, 65], 2);
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) {
    raster.rect(ox + x * tile, oy + y * tile, tile, tile, (x + y) % 2 ? [121, 151, 112] : [225, 229, 201]);
    const piece = instance.rows[y][x];
    if (piece !== '.') {
      const white = piece === piece.toUpperCase();
      raster.circle(ox + x * tile + 28, oy + y * tile + 28, 20, white ? [248, 248, 244] : [43, 51, 61]);
      raster.text(piece.toUpperCase(), ox + x * tile + 21, oy + y * tile + 18, white ? [35, 45, 58] : [250, 250, 247], 3);
    }
  }
  for (let x = 0; x < 8; x++) raster.text('ABCDEFGH'[x], ox + x * tile + 23, oy + 460, [45, 58, 72], 2);
  raster.text(`${instance.turn} TO MOVE`, 24, 545, [35, 49, 65], 2);
  if (result) raster.text(result === 'success' ? 'CORRECT FORCED MATE' : 'MOVE DOES NOT FORCE MATE', 230, 545, result === 'success' ? [42, 145, 100] : [191, 65, 78], 2);
  return raster;
}

function normalizeAction(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input) || Object.keys(input).length !== 1) return null;
  if (typeof input.move !== 'string' || !/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(input.move.trim().toLowerCase())) return null;
  return { move: input.move.trim().toLowerCase() };
}

function instanceFor(configuration) {
  const instance = selectedInstance(configuration, RAW, configurations);
  if (!instance) throw new Error('Unknown chess tactical configuration');
  return instance;
}

function writeFrame(runDir, relativePath, bytes) {
  const path = join(runDir, relativePath);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, bytes);
  return { path: relativePath, mimeType: 'image/png', sha256: sha256(bytes) };
}

function observation(runDir, relativeRoot, configuration, state) {
  const instance = instanceFor(configuration);
  const terminal = state.ended
    ? { ended: true, outcome: state.outcome, reason: state.outcome === 'success' ? 'unique_forced_mate_move' : 'move_does_not_force_mate', score: state.outcome === 'success' ? 1 : 0 }
    : { ended: false, outcome: null, reason: null, score: null };
  const publicText = `Perfect-information chess tactic. ${instance.turn} to move. Find the unique first move that forces checkmate within ${instance.horizon} move${instance.horizon === 1 ? '' : 's'}. Submit one UCI move.\nFEN: ${instance.fen}\n${boardText(instance.rows)}`
    + (state.ended ? `\nSubmitted: ${state.move}. Native verdict: ${state.outcome}.` : '');
  const bytes = render(instance, state.ended ? state.outcome : null).png();
  const frame = writeFrame(runDir, `${relativeRoot}/frames/step-${state.step}.png`, bytes);
  return {
    publicText, previewFrame: frame, step: state.step,
    stateHash: contentHash({ taskId: TASK_ID, configurationHash: configuration.configurationHash, state }),
    configurationHash: configuration.configurationHash,
    reward: state.outcome === 'success' ? 1 : 0,
    info: { turn: instance.turn, mateHorizon: instance.horizon, difficulty: instance.difficulty },
    terminal,
    instance: { taskId: TASK_ID, caseId: configuration.id, reconstruction: true }
  };
}

export async function createDriver({ root } = {}) {
  return {
    id: 'real2sim-chess-tactical-positions-local', version: 1, kind: 'interactive', maxSteps: 1,
    tool: {
      name: 'submit_action', description: 'Submit exactly one UCI move.',
      parameters: { type: 'object', additionalProperties: false, required: ['move'], properties: { move: { type: 'string', pattern: '^[a-h][1-8][a-h][1-8][qrbn]?$' } } }
    },
    actionContract: 'The complete board is public. Submit exactly one UCI move as {"move":"e2e4"}. The episode ends immediately; success requires the unique move that forces mate within the stated horizon.',
    normalizeAction,
    invalidActionPolicy: { reprompts: 1, exhaustedAction: { move: 'a1a1' }, exhaustedOutcome: 'malformed_uci_move', scoreDefined: true },
    source: {
      kind: 'real2sim', reconstructed: true, mechanismReviewed: true, protocolCompatible: true,
      urls: ['https://www.chessprogramming.org/Forsyth-Edwards_Notation', 'https://python-chess.readthedocs.io/'],
      recording: 'H0 records the complete public FEN/board, submitted UCI move, exact verdict and rendered frame for every episode.',
      limitations: ['Self-proposed local tactical subset, not an official chess benchmark or leaderboard.', 'Fixed mate positions test local tactical calculation rather than full-game strategy.']
    },
    configurations,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      const relativeRoot = `episodes/${episode.id}`;
      const state = { step: 0, ended: false, outcome: null, move: null };
      let current = observation(runDir, relativeRoot, configuration, state);
      const instance = instanceFor(configuration);
      return {
        observation: current,
        async step(action) {
          const normalized = normalizeAction(action);
          if (!normalized) throw new Error('Malformed UCI move');
          if (state.ended) throw new Error('Chess tactical episode already ended');
          state.step = 1; state.move = normalized.move; state.ended = true;
          state.outcome = normalized.move === instance.answer ? 'success' : 'failure';
          current = observation(runDir, relativeRoot, configuration, state);
          return current;
        },
        async close() {}
      };
    }
  };
}

function selectedInstance(configuration, instances, configurations) {
  const ordinal = configuration?.selector?.ordinal;
  const expected = configurations[ordinal];
  if (!Number.isInteger(ordinal) || !expected || configuration.selector.providerId !== expected.selector.providerId || configuration.id !== expected.id || configuration.configurationHash !== expected.configurationHash || (configuration.ordinal !== undefined && configuration.ordinal !== ordinal)) throw new Error('Unknown replacement configuration identity');
  return instances[ordinal];
}
