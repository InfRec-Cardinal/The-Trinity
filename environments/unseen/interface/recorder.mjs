                                                                                                     
                                                                                                
                                                                                                                        
                               
import { appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
const slim = o => o && { publicText: o.publicText, terminal: o.terminal, reward: o.reward, info: o.info, stateHash: o.stateHash,
  frame: o.frame ?? o.previewFrame ?? null, ...(o.frames ? { frames: o.frames } : {}), step: o.step };
export function withRecorder(driver) {
  return { ...driver, async open(context) {
    const opened = await driver.open(context);
    const dir = join(context.runDir, 'episodes', context.episode.id); mkdirSync(dir, { recursive: true });
    const file = join(dir, 'record.jsonl'); let index = 0;
    const write = row => appendFileSync(file, JSON.stringify({ ...row, at: new Date().toISOString() }) + '\n');
    write({ kind: 'initial', taskId: driver.taskId, configuration: (context.run?.configurations ?? driver.configurations)?.[context.episode.configurationIndex ?? 0]?.id ?? null, observation: slim(opened.observation) });
    const wrapped = { ...opened, async step(action, options) {
      const observation = await opened.step(action, options);
      write({ kind: 'step', index: ++index, action, observation: slim(observation) });
      return observation;
    } };
                                                                                                                  
    for (const name of ['stop', 'hostEnd']) if (opened[name]) wrapped[name] = async (...args) => {
      const observation = await opened[name](...args);
      write({ kind: 'host_end', index: ++index, via: name, reason: args[0] ?? null, observation: slim(observation) });
      return observation;
    };
    return wrapped;
  } };
}
