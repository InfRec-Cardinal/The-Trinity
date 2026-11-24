                                                                                                                        
                                                                                                                        
                                                                                                                        
                        
                                                                                                                        
                                             
import fs from 'node:fs';
import {openFifoProcess} from '../../../lib/fifo-process.mjs';
import { join } from 'node:path';
import { textFrame } from '../../../lib/text-frame.mjs';



                                                                                                      
export function createPythonSessionEngine({ cwd, python, script, instance, env = {}, fifoDir, idleSeconds = 90, fallbackRender }) {
  const actions = []; let proc = null, last = null, counter = 0;
  const dispose = () => { proc?.close(); proc = null; };
  const start = () => {
    dispose(); fs.mkdirSync(fifoDir, {recursive: true});
    const tag = `${process.pid}-${Date.now()}-${counter++}`, req = join(fifoDir, `${tag}.req`), resp = join(fifoDir, `${tag}.resp`);
    proc = openFifoProcess({python, args: [script, req, resp, String(idleSeconds)], cwd,
      env: {...process.env, PYTHONHASHSEED: '0', SDL_VIDEODRIVER: 'dummy', SDL_AUDIODRIVER: 'dummy', ...env, AGENTB_INSTANCE: JSON.stringify(instance)},
      req, resp, timeoutMs: idleSeconds * 1000});
    return proc.readLine();
  };
  const exchange = action => proc.send(action);
  const parse = line => { const out = JSON.parse(line); if (!out.ok) throw Object.assign(new Error(out.message ?? 'Official engine rejected the operation'), { code: 'environment_error' }); return out; };
  const resync = () => { dispose(); let line = start(); for (const a of actions) line = exchange(a); return line; };
  try { last = parse(start()); } catch (error) { dispose(); throw error; }
  const engine = {
    dispose,
    state: { step: 0, actions: [], engine: last.state },
    step(action) {
      if (last?.terminal?.ended) throw new Error('Official engine episode already ended');
      actions.push(action);
      let line = null; try { line = proc ? exchange(action) : null; } catch { line = null; }
      try { last = parse(line ?? resync()); } catch (error) { actions.pop(); dispose(); throw error; }
      engine.state = { step: actions.length, actions: structuredClone(actions), engine: last.state };
    },
    publicView() { return { text: last.text, reward: last.reward ?? 0, info: last.info ?? {}, terminal: last.terminal }; },
    render() { if (last.pngBase64) { const b = Buffer.from(last.pngBase64, 'base64'); return { png: () => b }; } return fallbackRender ? fallbackRender(last) : textFrame(last.text); },
  };
  return engine;
}
