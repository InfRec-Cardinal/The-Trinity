                                                                                     
                                                                                                                                                 
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createHash } from 'node:crypto';
import { createSaboteur, normalizeSaboteurAction } from './world.mjs';

const TASK_ID = 'saboteur_card_game';
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

const actionContract = "One card per turn. place_path {card, x, y, rotated?} (rotated=true turns the card 180 degrees: N<->S, E<->W); play_broken_tool {card, target seat 0-4}; play_repair {card, target, tool? (pick|lantern|cart, required for two-tool repair cards)}; play_rockfall {card, x, y} (removes the path card at x,y); play_map {card, goal 0|1|2}; pass_discard {card} (card:null only with an empty hand). Card ids come from you.hand. Illegal actions are rejected without using your turn; the third rejection loses.";
const parameters = {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "action": {
      "type": "string",
      "enum": [
        "place_path",
        "play_broken_tool",
        "play_repair",
        "play_rockfall",
        "play_map",
        "pass_discard"
      ]
    },
    "card": {
      "type": [
        "string",
        "null"
      ]
    },
    "x": {
      "type": "integer"
    },
    "y": {
      "type": "integer"
    },
    "rotated": {
      "type": "boolean"
    },
    "target": {
      "type": "integer",
      "minimum": 0,
      "maximum": 4
    },
    "tool": {
      "type": "string",
      "enum": [
        "pick",
        "lantern",
        "cart"
      ]
    },
    "goal": {
      "type": "integer",
      "minimum": 0,
      "maximum": 2
    }
  },
  "required": [
    "action"
  ]
};

export async function createDriver({ root } = {}) {
  return {
    id: 'real2sim-saboteur_card_game', version: 2, kind: 'interactive', maxSteps: 60,
    tool: { name: 'submit_action', description: actionContract, parameters },
    actionContract,
    normalizeAction: normalizeSaboteurAction,
    invalidActionPolicy: {"reprompts": 1, "scoreDefined": true, "exhaustedOutcome": "rejected_action", "exhaustedAction": {"action": "pass_discard", "card": null}},
    source: { kind: 'real2sim', reconstructed: true, mechanismReviewed: true, protocolCompatible: true, officialBenchmarkEquivalent: false, engine: 'original JS reconstruction of the AMIGO Saboteur rulebook (v2.0)', urls: ['https://www.rulespal.com/saboteur/rulebook', 'https://cdn.1j1ju.com/medias/83/8a/e7-saboteur-rulebook.pdf'] },
    configurations,
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!Number.isInteger(configuration.ordinal) || configuration.selector?.ordinal !== configuration.ordinal || configuration.id !== configurations[configuration.ordinal]?.id) throw new Error('Unknown Saboteur selector');
      const instance = INSTANCES[configuration.ordinal] && clone(INSTANCES[configuration.ordinal]);
      if (!instance) throw new Error('Unknown saboteur configuration');
      const engine = createSaboteur(instance);
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
          const action = normalizeSaboteurAction(input);
          if (!action) throw new Error('Malformed Saboteur action');
          if (observation.terminal.ended) throw new Error('Saboteur episode already ended');
          engine.step(action);
          observation = observe();
          return clone(observation);
        },
        async close() {}
      };
    }
  };
}
