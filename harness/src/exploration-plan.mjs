import {hostVerificationCall} from './host-verification.mjs';
import {clone, digest, ensure} from './core.mjs';

export async function freezeExplorationInstances({driver, world, trials, store, taskId, retries = 2}) {
  ensure(typeof driver.instanceManifest === 'function' && typeof driver.initialState === 'function', 'Initial exploration requires instanceManifest and initialState');
  const instances = clone(await hostVerificationCall('instance_manifest', () => driver.instanceManifest(clone(world), trials)));
  ensure(Array.isArray(instances) && instances.length === trials && instances.every(row => row && typeof row === 'object' && !Array.isArray(row)), 'Invalid initial instance manifest');
  const worldDigest = digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))), initialStateHashes = [];
  for (let index = 0; index < instances.length; index++) {
    for (let attempt = 0; ; attempt++) {
      let session, hash, failure;
      try {
        session = await hostVerificationCall('initial_state_probe', () => driver.reset(clone(world), clone(instances[index])));
        hash = digest(await hostVerificationCall('initial_state_probe', () => driver.initialState(session)));
      } catch (error) {failure = error;}
      finally {
        if (session && driver.close) try {await hostVerificationCall('probe_cleanup', () => driver.close(session));} catch (error) {failure = error;}
      }
      if (!failure) {initialStateHashes.push(hash); break;}
      store.record('initial_state_probe_invalid', {taskId, index, attempt, reason: String(failure.message)});
      ensure(attempt < retries, 'Technical failures exhausted the initial state probe retry budget');
    }
  }
  ensure(digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))) === worldDigest, 'World changed while fixing initial states');
  const plan = {schema: 'trinity-exploration-instances-v1', taskId: taskId ?? null, worldDigest, instances, initialStateHashes};
  const artifact = store.put(plan);
  const event = store.record('initial_instances_frozen', {taskId, artifact, planDigest: digest(plan)});
  return {...plan, event};
}
