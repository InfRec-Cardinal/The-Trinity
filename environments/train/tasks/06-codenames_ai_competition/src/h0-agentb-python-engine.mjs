                                                                                                                                   
                                                                                                                     
                                                                                                                  
                                                 
                                                                   
                                      
                                                                                                                                         
import { spawnSync } from 'node:child_process';
import { textFrame } from '../../../lib/text-frame.mjs';

                                                                                                      
export function createPythonReplayEngine({ cwd, python, script, instance, timeoutMs = 120000, env = {}, fallbackRender }) {
  const actions = [];
  let last = null;
  const run = () => {
    const result = spawnSync(python, [script], { cwd, input: JSON.stringify({ instance, actions }), encoding: 'utf8',
      timeout: timeoutMs, maxBuffer: 256 * 1024 * 1024,
      env: { ...process.env, PYTHONHASHSEED: '0', PYTHONDONTWRITEBYTECODE: '1', SDL_VIDEODRIVER: 'dummy', SDL_AUDIODRIVER: 'dummy', PYGAME_HIDE_SUPPORT_PROMPT: '1', ...env } });
    if (result.error) throw Object.assign(new Error(`Official engine process failed: ${result.error.message}`), { code: 'environment_error' });
    const line = result.stdout.trim().split('\n').at(-1);
    let parsed; try { parsed = JSON.parse(line); } catch { throw Object.assign(new Error(`Official engine returned no result (exit ${result.status}): ${result.stderr.slice(-400)}`), { code: 'environment_error' }); }
    if (!parsed.ok) throw Object.assign(new Error(parsed.message ?? 'Official engine rejected the operation'), { code: 'environment_error' });
    return parsed;
  };
  const engine = {
    state: null,
    step(action) {
      if (last?.terminal?.ended) throw new Error('Official engine episode already ended');
      actions.push(action);
      try { last = run(); } catch (error) { actions.pop(); throw error; }
      engine.state = { step: actions.length, actions: structuredClone(actions), engine: last.state };
    },
    publicView() { return { text: last.text, reward: last.reward ?? 0, info: last.info ?? {}, terminal: last.terminal }; },
    render() {
      if (last.pngBase64) { const bytes = Buffer.from(last.pngBase64, 'base64'); return { png: () => bytes }; }
      return fallbackRender ? fallbackRender(last) : textFrame(last.text);
    },
  };
  last = run();
  engine.state = { step: 0, actions: [], engine: last.state };
  return engine;
}
