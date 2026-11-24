                                                                                                                
                                                                                                                          
                                                                                                                        
  
                                                                                                                       
                                                           
                                                                                                              
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { openSession, validateArgs } from './env-sessions.mjs';
import { sha256 } from './hash.mjs';

export function makeSessionDriver({ root, task, configurations }) {
  const env = task.environment;
  const envDir = resolve(root, env.envDir);
  const sessionTask = { id: task.taskId, adapter: env.adapter, env: env.name, python: env.python, bridge: env.bridge,
    terminal: env.terminal, limits: env.limits, tool: task.tool };
  return {
    id: task.driverId, version: 1, kind: 'interactive', taskId: task.taskId,
    maxSteps: task.evaluation?.maxSteps ?? null,
    tool: task.tool, actionContract: task.contract, configurations,
    contextPolicy: task.player.contextPolicy, imageOrder: task.player.imageOrder ?? null,
                                                                                                                   
    normalizeAction: input => (validateArgs(task.tool.parameters, input) ? null : input),
    source: task.source,
    async open({ runDir, run, episode }) {
      const configuration = (run?.configurations ?? configurations)[episode.configurationIndex];
      if (!configuration) throw new Error(`unknown configuration index ${episode.configurationIndex}`);
      const epRel = join('episodes', episode.id), envOut = join(runDir, epRel, 'env');
      mkdirSync(envOut, { recursive: true });
      const session = openSession(sessionTask, configuration, envOut, { root, envDir, harness: run?.harness ?? 'h0', runId: run?.id ?? null });
      let step = 0;
      const observation = o => {
        const frames = (o.images ?? []).map((b64, k) => {
          const rel = join(epRel, 'frames', `step-${step}-${k}.png`), bytes = Buffer.from(b64, 'base64');
          mkdirSync(join(runDir, epRel, 'frames'), { recursive: true }); writeFileSync(join(runDir, rel), bytes);
          return { path: rel, sha256: sha256(bytes), mimeType: 'image/png' };
        });
        const terminal = o.terminal ?? { ended: false, outcome: null, reason: null, score: null };
        return { publicText: o.text, frames, ...(frames.length === 1 ? { frame: frames[0] } : {}), step, terminal,
          reward: o.terminal?.score ?? 0, info: { taskId: task.taskId, configuration: configuration.id },
          stateHash: sha256(JSON.stringify({ text: o.text, frames: frames.map(f => f.sha256), terminal: o.terminal ?? null })) };
      };
      const first = observation(await session.open());
      return {
        observation: first,
        async step(action) { step++; return observation(await session.step(action)); },
                                                                                                             
        stop(reason, label = reason) { step++; return observation(session.stop(reason, label)); },
                                                                                                                          
                                                                                                    
        ...(env.terminal === 'pencil' ? { async hostEnd(reason) { step++; return observation(await session.hostEnd(reason)); } } : {}),
        async close() { session.close(); },
      };
    },
  };
}
