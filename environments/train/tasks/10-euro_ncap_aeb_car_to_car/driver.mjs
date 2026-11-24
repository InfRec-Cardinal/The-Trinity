                                                                               
                                                                                                                   
                                                                                                                 
import { readFileSync } from 'node:fs';
import { makeWorldDriver } from '../../lib/world-driver.mjs';
import { euroNCAPDefinition } from './world.mjs';

const read = name => JSON.parse(readFileSync(new URL(`./${name}`, import.meta.url), 'utf8'));
const instances = read('instances.json');
const configurations = read('configurations.json').configurations;

export async function createDriver({ root } = {}) {
  const driver = makeWorldDriver(euroNCAPDefinition, {
    configurations,
                                                                                                    
    resolveWorld: configuration => structuredClone(selectedInstance(configuration, instances, configurations)),
  });
  return { ...driver, configurationSelection: { mode: 'adaptive', availableCount: configurations.length, providerId: "euro_ncap_aeb_car_to_car-train-refresh-20261016-v1", providerVersion: 1, mechanismReview: 'reviewed', sourceScope: 'Nine replacement simulated CCRs/CCRm/CCRb rows pinned in instances.json.' } };
}

function selectedInstance(configuration, instances, configurations) {
  const ordinal = configuration?.selector?.ordinal;
  const expected = configurations[ordinal];
  if (!Number.isInteger(ordinal) || !expected || configuration.selector.providerId !== expected.selector.providerId || configuration.id !== expected.id || configuration.configurationHash !== expected.configurationHash || (configuration.ordinal !== undefined && configuration.ordinal !== ordinal)) throw new Error('Unknown replacement configuration identity');
  return instances[ordinal];
}
