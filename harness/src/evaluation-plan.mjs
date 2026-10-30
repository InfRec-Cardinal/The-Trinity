import {hostVerificationCall} from './host-verification.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {clone, digest, ensure} from './core.mjs';

const pending = new Map();

export async function freezeEvaluationInstance(options, {phase = 'formal', index = 0, trials = 1} = {}) {
  const {driver, store, world, benchmarkId, protocolId} = options;
  ensure(typeof driver.initialState === 'function', 'Evaluation requires initialState');
  if (options.expectedInitialStateHash != null) {
    ensure(options.instance && typeof options.expectedInitialStateHash === 'string', 'A frozen initial state requires an explicit instance');
    return {instance: clone(options.instance), expectedInitialStateHash: options.expectedInitialStateHash, instancePlan: options.instancePlan ?? null};
  }
  const identity = {schema: 'trinity-evaluation-instance-v1', benchmarkId, protocolId, phase, index,
    worldDigest: digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))), instance: options.instance ?? null};
  const directory = path.resolve(options.skillDirectory ?? path.join(store.directory, 'evaluation-skills'), 'instance-plans');
  fs.mkdirSync(directory, {recursive: true});
  const file = path.join(directory, digest(identity) + '.json');
  const load = () => {
    const {plan, hash} = JSON.parse(fs.readFileSync(file, 'utf8'));
    ensure(hash === digest(plan) && digest(plan.identity) === digest(identity) && plan.instance &&
      typeof plan.initialStateHash === 'string', 'Frozen evaluation instance integrity mismatch');
    const event = store.record('evaluation_instance_frozen', {planDigest: hash, artifact: store.put(plan)});
    return {instance: clone(plan.instance), expectedInitialStateHash: plan.initialStateHash, instancePlan: event};
  };
  if (fs.existsSync(file)) return load();
  if (pending.has(file)) {await pending.get(file); return load();}
  const create = async () => {
    const lock = file + '.lock';
    const handle = fs.openSync(lock, 'wx');
    try {
      let instance = clone(options.instance ?? null);
      if (instance === null) {
        ensure(typeof driver.instanceManifest === 'function', 'Evaluation requires instanceManifest or an explicit instance');
        const manifest = await hostVerificationCall('instance_manifest', () => driver.instanceManifest(clone(world), trials));
        ensure(Array.isArray(manifest) && manifest.length === trials, 'Invalid evaluation instance manifest');
        instance = clone(manifest[index]);
      }
      ensure(instance && typeof instance === 'object' && !Array.isArray(instance), 'Invalid evaluation instance');
      let session, initialStateHash;
      try {
        session = await hostVerificationCall('evaluation_state_probe', () => driver.reset(clone(world), clone(instance)));
        initialStateHash = digest(await hostVerificationCall('evaluation_state_probe', () => driver.initialState(session)));
      } finally {if (session && driver.close) await hostVerificationCall('probe_cleanup', () => driver.close(session));}
      ensure(digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))) === identity.worldDigest, 'World changed while freezing evaluation state');
      const plan = {identity, instance, initialStateHash};
      fs.writeFileSync(file, JSON.stringify({plan, hash: digest(plan)}) + '\n', {flag: 'wx'});
    } finally {fs.closeSync(handle); fs.unlinkSync(lock);}
  };
  const promise = create();
  pending.set(file, promise);
  try {await promise; return load();} finally {pending.delete(file);}
}
