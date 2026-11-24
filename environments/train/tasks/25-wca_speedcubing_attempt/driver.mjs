                                                                                             
                                                                                                                                                                           
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import { createWCACube, normalize } from './world.mjs';

const TASK_ID = 'wca_speedcubing_attempt';
const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
                                                                      
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(v => canonical(v) ?? 'null').join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
const contentHash = value => sha256(canonical(value));
const clone = value => JSON.parse(JSON.stringify(value));

                                                                         
const INSTANCES = JSON.parse(readFileSync(new URL('./instances.json', import.meta.url), 'utf8'));

const configurations = JSON.parse(readFileSync(new URL('./configurations.json', import.meta.url), 'utf8')).configurations;

const actionContract = "Restore all54 facelets to six uniform faces in any orientation. turn takes a string of1–20 moves F/B/R/L/U/D with ' or2, or free x/y/z rotations. finish ends. Face moves each count1OBTM; rotations0. At60actions or300moves the attempt ends and is judged on its actual cube state. A batch reaching300 is truncated at that move.";
const parameters = {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "turn",
        "finish"
      ]
    },
    "moves": {
      "type": "string"
    }
  },
  "required": [
    "action"
  ]
};
const invalidActionPolicy = {"reprompts": 1, "exhaustedAction": {"action": "finish"}, "exhaustedOutcome": "invalid_response_finish", "scoreDefined": true};
const invalidResponseRecoveryDesign = "Host submits the declared finish action after one invalid reprompt; the original cube state and score determine the outcome.";

export async function createDriver({ root } = {}) {
  return {
    id: 'real2sim-wca_speedcubing_attempt', version: 2, kind: 'interactive', maxSteps: 60,
    tool: { name: 'submit_action', description: actionContract, parameters },
    actionContract,
    normalizeAction: normalize,
    invalidActionPolicy,
    invalidResponseRecoveryDesign,
    source: { kind: 'real2sim', reconstructed: true, mechanismReviewed: true, protocolCompatible: true, officialBenchmarkEquivalent: false, engine: 'Original 54-sticker integer 3D geometric cube permutation engine', urls: ['https://www.worldcubeassociation.org/regulations/'] },
    configurations,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!Number.isInteger(configuration.ordinal) || configuration.selector?.ordinal !== configuration.ordinal || configuration.id !== configurations[configuration.ordinal]?.id) throw new Error('Unknown WCA selector');
      const instance = INSTANCES[configuration.ordinal] && clone(INSTANCES[configuration.ordinal]);
      if (!instance) throw new Error('Unknown WCA configuration');
      const engine = createWCACube(instance);
      const relativeRoot = `episodes/${episode.id}`;
      const observe = () => {
        const view = engine.publicView(), step = engine.state.step;
        const stateHash = contentHash({ instance, state: engine.state });
        const framePath = `${relativeRoot}/frames/step-${step}.png`;
        const bytes = engine.render().png();
        const full = join(runDir, framePath);
        mkdirSync(dirname(full), { recursive: true });
        writeFileSync(full, bytes);
        return {
          publicText: view.text, previewFrame: { path: framePath, mimeType: 'image/png', sha256: sha256(bytes) },
          step, stateHash, configurationHash: configuration.configurationHash, reward: view.reward ?? 0, info: view.info ?? {},
          terminal: view.terminal, instance: { taskId: TASK_ID, caseId: configuration.id, reconstruction: true }
        };
      };
      let observation = observe();
      return {
        observation,
        async step(input) {
          const action = normalize(input);
          if (!action) throw new Error('Malformed WCA action');
          if (observation.terminal.ended) throw new Error('WCA episode already ended');
          engine.step(action);
          observation = observe();
          return clone(observation);
        },
        async close() {}
      };
    }
  };
}
