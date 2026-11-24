                                                                             
                                                                                                            
                                                                                                                       
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { resolve, sep } from 'node:path';
import { palletRackDefinition as definition, createPalletRack, contentHash, sha256 } from './world.mjs';

const read = name => JSON.parse(readFileSync(new URL(`./${name}`, import.meta.url), 'utf8'));
const clone = value => JSON.parse(JSON.stringify(value));

export async function createDriver({ root } = {}) {
  const configurations = read('configurations.json').configurations;
  const instances = read('instances.json');
  const imageField = definition.playerRGB ? 'frame' : 'previewFrame';
  const describe = {
    id: `real2sim-${definition.taskId}`, version: 1, kind: 'interactive', maxSteps: definition.maxSteps,
    ready: true, preparationOnly: false, formalExecutionBlockers: [],
    tool: { name: 'submit_action', description: definition.actionContract, parameters: definition.parameters },
    actionContract: definition.actionContract, normalizeAction: definition.normalizeAction,
    source: { kind: 'real2sim', reconstructed: true, mechanismReviewed: true, protocolCompatible: true,
      urls: ['https://en.wikipedia.org/wiki/Pallet_racking'],
      recording: 'Exact deterministic state/action replay, public observation frames and terminal scoring.',
      limitations: ['Self-proposed simulation with explicitly declared reconstruction designs; not the physical contest or commercial game.'] },
    configurations: clone(configurations),
    configurationSelection: { mode: 'adaptive', availableCount: configurations.length, providerId: "pallet_rack_inspection-train-refresh-20261016-v1", providerVersion: 1 },
  };

                                                                                                                                                         
  function observe(engine, configuration, runDir, base) {
    const instance = engine.instance, view = engine.publicView(), step = engine.state.step;
    const stateHash = contentHash({ instance, state: engine.state });
    const framePath = `${base}/frames/step-${step}.png`, bytes = engine.render().png();
    const imagePath = resolve(runDir, framePath);
    if (!imagePath.startsWith(resolve(runDir) + sep)) throw new Error('Frame path escapes run');
    mkdirSync(resolve(imagePath, '..'), { recursive: true });
    if (!existsSync(imagePath)) writeFileSync(imagePath, bytes);
    return { publicText: view.text, [imageField]: { path: framePath, mimeType: 'image/png', sha256: sha256(bytes) },
      step, stateHash, configurationHash: configuration.configurationHash, reward: view.reward ?? 0, info: view.info ?? {},
      terminal: view.terminal, instance: { taskId: definition.taskId, caseId: configuration.id, reconstruction: true } };
  }

  function engineFor(configuration) {
    const instance = selectedInstance(configuration, instances, configurations);
    if (!instance) throw new Error('Unknown pallet-rack configuration');
    const engine = createPalletRack(clone(instance));
    engine.instance = clone(instance);
    return engine;
  }

  return {
    ...describe,
    async prepareConfiguration({ runDir, configuration, index }) {
      return observe(engineFor(configuration), configuration, runDir, `scenes/case-${index}`);
    },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : configurations;
      const configuration = list[episode.configurationIndex ?? 0];
      if (!configuration) throw new Error('Unknown configuration index');
      if (!/^[A-Za-z0-9_-]{1,120}$/.test(episode.id)) throw new Error('Invalid episode identity');
      const engine = engineFor(configuration), base = `episodes/${episode.id}`;
      let observation = observe(engine, configuration, runDir, base), closed = false;
      return {
        observation,
        async step(input) {
          if (closed) throw new Error('Episode is closed');
          if (observation.terminal.ended) throw new Error('Episode already ended');
          const action = definition.normalizeAction(input);
          if (!action) throw new Error('Malformed pallet-rack action');
          engine.step(action);
          observation = observe(engine, configuration, runDir, base);
          return clone(observation);
        },
        async close() { closed = true; },
      };
    },
  };
}

function selectedInstance(configuration, instances, configurations) {
  const ordinal = configuration?.selector?.ordinal;
  const expected = configurations[ordinal];
  if (!Number.isInteger(ordinal) || !expected || configuration.selector.providerId !== expected.selector.providerId || configuration.id !== expected.id || configuration.configurationHash !== expected.configurationHash || (configuration.ordinal !== undefined && configuration.ordinal !== ordinal)) throw new Error('Unknown replacement configuration identity');
  return instances[ordinal];
}
