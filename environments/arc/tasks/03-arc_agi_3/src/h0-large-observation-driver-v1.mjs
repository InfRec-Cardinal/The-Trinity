                                                                                                                            
                                                                                                                                
import { encodeArcObservation } from './h0-large-observation-codec-v1.mjs';

export const LARGE_OBSERVATION_TASKS = Object.freeze(['arc_agi_3']);

export function withCompactLargeObservation(taskId, driver) {
  if (!LARGE_OBSERVATION_TASKS.includes(taskId) || !driver) return driver;
  const present = value => encodeArcObservation(value);
  const wrapped = { ...driver, source: { ...driver.source, publicObservationEncoding: { version: 1, lossless: true, scope: 'all_public_grid_layers_fixed_width_hex_rows' } } };
  wrapped.prepare = async context => {
    const prepared = await driver.prepare(context);
    return { ...prepared, initialScenes: (prepared.initialScenes ?? []).map(present) };
  };
  wrapped.open = async context => {
    const opened = await driver.open(context);
    return { ...opened, observation: present(opened.observation), async step(...args) { return present(await opened.step(...args)); } };
  };
  return wrapped;
}
