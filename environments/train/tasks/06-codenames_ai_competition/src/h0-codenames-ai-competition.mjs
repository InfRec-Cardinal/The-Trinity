                                                                                              
                                                                                                                           
                                                                                                                       
                                                                                                                          
                                                                                                       
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pythonFor } from '../../../lib/python-env.mjs';
import { createPythonReplayEngine } from './h0-agentb-python-engine.mjs';

const TASK_ID = 'codenames_ai_competition';
const ENV_NAME = 'agentb-codenames-ai-competition-venv';
const CLUE_BUDGET = 25;
const TASK_DIR = fileURLToPath(new URL('../', import.meta.url));
const FRAMEWORK_COMMIT = 'f13d9fcbc6264124f24dc0c41b20255526c9fce4';
const PREDECESSOR_COMMIT = '1116940767d8e82c339067ef8f522e43e81fdcef';

                                                              
                                                                                   

const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
                                                                                                         
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(v => canonical(v) ?? 'null').join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().filter(k => value[k] !== undefined)
    .map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
const contentHash = value => sha256(canonical(value));
const clone = value => structuredClone(value);

export function normalizeCodenamesAction(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) return null;
  const keys = Object.keys(input).sort().join(',');
  return keys === 'clue,number' && typeof input.clue === 'string' && input.clue.trim() && input.clue.length <= 40 && Number.isSafeInteger(input.number) && input.number >= 0 && input.number <= 25
    ? { clue: input.clue.trim(), number: input.number } : null;
}

const ACTION_CONTRACT = 'You are the red Codemaster. Submit {"clue":"<one English word>","number":<words it covers, >= 1>}. The partner guesser sees only the board and your clue, guesses the nearest unrevealed words up to the number, and stops at the first non-red word. The clue must be letters only and must not contain or be contained in any unrevealed board word; an invalid clue, the assassin or all eight blue words ends the game with the worst score 25. Reveal all nine red words in as few clues as possible; at most 25 clues.';
const PARAMETERS = { type: 'object', additionalProperties: false, properties: { clue: { type: 'string', maxLength: 40 }, number: { type: 'integer', minimum: 0, maximum: 25 } }, required: ['clue', 'number'] };
const SOURCE = {
  kind: 'official', reconstructed: false, mechanismReviewed: true, protocolCompatible: true, officialBenchmarkEquivalent: false,
  engine: `stepmat/Codenames_GPT @ ${FRAMEWORK_COMMIT} codenames/game.py (single_team=True); partner guesser_glove.py from CodenamesAICompetition/Game @ ${PREDECESSOR_COMMIT}; Stanford GloVe 6B 100d/50d`,
  urls: ['https://github.com/stepmat/Codenames_GPT', 'https://github.com/CodenamesAICompetition/Game', 'https://nlp.stanford.edu/projects/glove/'],
  recording: 'Every observation is recomputed by the official Game from the seed and the full public clue history; the private state carries the board, key grid and the framework move history.',
  limitations: [
    'The framework\'s only shipped guesser is the paid GPT agent and competition partners are other entrants\' submissions; no paid model may run, so the held-out partner is the predecessor framework\'s unchanged non-LLM guesser_glove (cosine nearest board word, guessing exactly the clue number of times) over Stanford GloVe 6B 100d or 50d vectors. The predecessor\'s WordNet guessers were not used because their per-guess similarity search is too slow for exact full-history replay; the word2vec guesser needs the 1.6 GB GoogleNews vectors and gensim.',
    'The Player\'s clue is validated with the framework codemaster\'s own rules (codemaster_GPT.get_clue: one word of letters, number >= 1, not contained in or containing an unrevealed board word); unlike that agent, which re-prompts up to 10 times, an invalid clue ends the episode as a failure, as the spec requires. The clue is passed to the partner in lower case because the GloVe vocabulary is lower case; a clue outside the 400k-word vocabulary makes the official guesser raise, which is scored as a failed (invalid) clue.',
    'GloVe vectors are parsed exactly as the predecessor Game.load_glove_vecs does (Python float to float64) and stored as an exact float64 matrix and vocabulary; the tie-breaking order of the partner\'s sort is unchanged.',
    'Score is the framework single-team score: turns taken on a red win, 25 for assassin, all-blue, invalid clue or exhausting the 25-clue budget. Boards come from the framework word list and key-grid shuffle under the recorded seed.',
  ],
};

export async function createDriver({ root }) {
  const configurations = JSON.parse(readFileSync(new URL('../configurations.json', import.meta.url), 'utf8')).configurations;
  const script = join(TASK_DIR, 'adapters/agentb-codenames-ai-competition-worker.py');
  const cwd = root;
  const python = pythonFor(root, ENV_NAME);
  const source = join(root, 'vendor/codenames');
  const glove = join(root, 'data/glove');

  const describe = {
    id: `official-${TASK_ID}`, version: 1, kind: 'interactive', maxSteps: CLUE_BUDGET,
    tool: { name: 'submit_action', description: ACTION_CONTRACT, parameters: PARAMETERS },
    actionContract: ACTION_CONTRACT, normalizeAction: normalizeCodenamesAction,
    source: SOURCE, configurationSelection: { mode: 'adaptive', availableCount: configurations.length, providerId: 'codenames_ai_competition-refresh-20261016', providerVersion: 1 },
    configurations: clone(configurations),
  };

  return { ...describe,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : describe.configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!/^[A-Za-z0-9_-]{1,120}$/.test(episode.id ?? '')) throw new Error('Invalid episode identity');
      const instance = clone(configuration.instance);
      if (!instance) throw new Error('Missing configuration instance');
      const engine = createPythonReplayEngine({ cwd, python, script, instance, timeoutMs: 120000,
        env: { AGENTB_CODENAMES_SRC: source, AGENTB_CODENAMES_GLOVE: glove, PYTHONDONTWRITEBYTECODE: '1' } });
      const path = `episodes/${episode.id}`, absoluteRun = resolve(runDir), dir = resolve(runDir, path);
      if (!dir.startsWith(absoluteRun + sep)) throw new Error('Episode path escapes run');
      const observe = () => {
        const view = engine.publicView(), step = engine.state.step;
        const stateHash = contentHash({ instance, state: engine.state });
        const framePath = `${path}/frames/step-${step}.png`, imagePath = join(runDir, framePath), bytes = engine.render().png();
        mkdirSync(dirname(imagePath), { recursive: true }); writeFileSync(imagePath, bytes);
        return { publicText: view.text, previewFrame: { path: framePath, mimeType: 'image/png', sha256: sha256(bytes) },
          step, stateHash, configurationHash: configuration.configurationHash, reward: view.reward ?? 0, info: view.info ?? {},
          terminal: view.terminal, instance: { taskId: TASK_ID, caseId: configuration.id, reconstruction: false } };
      };
      let observation = observe(), closed = false;
      return { observation,
        async step(input) {
          if (closed) throw new Error('Episode is closed');
          if (observation.terminal.ended) throw new Error('Episode already ended');
          const action = normalizeCodenamesAction(input); if (!action) throw new Error('Malformed action');
          engine.step(action); observation = observe();
          return clone(observation);
        },
        async close() { closed = true; } };
    } };
}
