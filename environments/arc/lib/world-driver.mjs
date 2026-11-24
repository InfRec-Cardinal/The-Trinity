                                                                                   
                                                                                                                       
                                                                                             
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, sep } from 'node:path';

export const hash = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
const clone = value => JSON.parse(JSON.stringify(value));

export function makeWorldDriver(definition, { configurations, resolveWorld = () => null }) {
  const describe = {
    id: `real2sim-${definition.taskId}`, version: definition.version ?? 1, kind: 'interactive', maxSteps: definition.maxSteps,
    tool: { name: 'submit_action', description: definition.actionContract, parameters: definition.parameters },
    actionContract: definition.actionContract, normalizeAction: definition.normalizeAction,
    source: { kind: 'real2sim', family: definition.family, urls: definition.sources, fidelityNotes: definition.fidelityNotes, limitations: definition.limitations ?? [] },
    configurations: clone(configurations),
  };
  async function observe(engine, runDir, dir) {
    const publicView = engine.publicView(); const pixels = engine.render().png();
    const path = `${dir}/frame-${String(engine.state.step ?? 0).padStart(4, '0')}.png`;
    const absolute = resolve(runDir, path); if (!absolute.startsWith(resolve(runDir) + sep)) throw new Error('Frame path escapes run');
    mkdirSync(resolve(absolute, '..'), { recursive: true }); writeFileSync(absolute, pixels);
    const image = { path, sha256: hash(pixels), mimeType: 'image/png' };
    return { publicText: publicView.text, ...(definition.playerRGB ? { frame: image } : { previewFrame: image }),
      stateHash: hash(engine.state), configurationHash: engine.configuration.configurationHash, step: engine.state.step ?? 0,
      reward: publicView.reward ?? 0, info: publicView.info ?? {}, instance: { caseId: engine.configuration.id, origin: engine.configuration.origin, reconstruction: true },
      terminal: publicView.terminal ?? { ended: false, outcome: null, reason: null } };
  }
  function engineFor(configuration, index) {
    const world = resolveWorld(configuration);
    const engine = definition.create(world ? 0 : (configuration.selector?.scenario ?? index), world ?? undefined);
    engine.configuration = clone(configuration); return engine;
  }
  return { ...describe,
    async prepare({ runDir }) { const initialScenes = []; for (const [i, c] of describe.configurations.entries()) initialScenes.push(await observe(engineFor(c, i), runDir, `initial/${c.id}`)); return { initialScenes, configurations: clone(describe.configurations) }; },
    async open({ runDir, run, episode }) {
      const list = run?.configurations?.length ? run.configurations : describe.configurations;
      const index = episode.configurationIndex ?? 0, configuration = list[index];
      if (!configuration) throw new Error('Unknown configuration index');
      const engine = engineFor(configuration, index), dir = `episodes/${episode.id}/frames`;
      let observation = await observe(engine, runDir, dir), closed = false;
      return { observation,
        async step(action) {
          if (closed) throw new Error('Episode is closed');
          if (observation.terminal.ended) throw new Error('Episode already ended');
          const normalized = definition.normalizeAction(action); if (!normalized) throw new Error('Malformed action');
          engine.step(normalized); observation = await observe(engine, runDir, dir); return clone(observation);
        },
        async close() { closed = true; } };
    } };
}
