import {hostVerificationCall} from './host-verification.mjs';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import path from 'node:path';
import {clone, digest, ensure, snapshot} from './core.mjs';
import {freezeEvaluationInstance} from './evaluation-plan.mjs';
import {runBatch} from './explorer.mjs';
import {tokenSummary} from './metrics.mjs';

const pending = new Map();
const protocol = 'benchmark-harness-skills-v2';
const text = value => typeof value === 'string' && value.trim().length > 0;
export function skillIdentity({benchmarkId, protocolId, modules, budget}) {
  ensure(text(benchmarkId) && text(protocolId), 'Explicit benchmarkId and protocolId are required for evaluation skills');
  ensure(Number.isInteger(budget) && budget > 0, 'Positive evaluation action budget required');
  const prompts = ['explorer', 'skills'].map(role => fs.readFileSync(new URL('../prompts/' + role + '.txt', import.meta.url), 'utf8'));
  return {protocol, benchmarkId, protocolId, harnessId: snapshot(modules).id, budget, promptDigest: digest(prompts)};
}

export async function prepareEvaluationSkills(options) {
  const preparationId = randomUUID();
  const task = () => prepareSkills({...options, preparationId});
  return options.agent.withScope ? options.agent.withScope({preparationId, benchmarkId: options.benchmarkId, protocolId: options.protocolId, split: 'preparation'}, task) : task();
}
async function prepareSkills(options) {
  const {agent, driver, store, node, modules, budget, preparationTrials = 5} = options;
  ensure(preparationTrials === 5, 'Exactly five preparation trials required');
  ensure(options.previousSkills === undefined && options.validationTrials === undefined, 'Evaluation skills use frozen preparation, not previousSkills or validationTrials');
  const identity = skillIdentity(options), key = digest(identity);
  const directory = path.resolve(options.skillDirectory ?? path.join(store.directory, 'evaluation-skills'));
  fs.mkdirSync(directory, {recursive: true});
  const file = path.join(directory, key + '.json');
  const load = async () => {
    const {artifact, artifactDigest} = JSON.parse(fs.readFileSync(file, 'utf8'));
    ensure(artifactDigest === digest(artifact) && digest(artifact.identity) === key, 'Frozen skill artifact integrity mismatch');
    ensure(artifact.status === 'frozen' && artifact.episodes?.length === 5 && artifact.skills?.length === 1 && text(artifact.skills[0]), 'Incomplete frozen skill artifact');
    if (options.preparationWorlds !== undefined) {
      ensure(digest(options.preparationWorlds) === artifact.preparationPlanDigest, 'Preparation plan changed; use a new protocolId');
      const current = [];
      for (const world of options.preparationWorlds) current.push(digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))));
      ensure(digest(current) === digest(artifact.buildDigests), 'Preparation environment changed; use a new protocolId');
    }
    store.record('evaluation_skills_reused', {key, benchmarkId: identity.benchmarkId, harnessId: identity.harnessId, artifactDigest});
    return {...clone(artifact), reused: true, adaptationCost: 0, usage: tokenSummary([])};
  };
  if (fs.existsSync(file)) return load();
  if (pending.has(file)) {await pending.get(file); return load();}
  const task = async () => {
    const worlds = clone(options.preparationWorlds);
    ensure(Array.isArray(worlds) && worlds.length === 5 && worlds.every(world => world && typeof world === 'object'), 'Provide five explicit preparationWorlds before the first evaluation of a pair');
    const lock = file + '.lock';
    let handle;
    try {handle = fs.openSync(lock, 'wx');}
    catch (error) {if (error.code === 'EEXIST') throw Error('Skill preparation is already locked; reuse the completed artifact when available'); throw error;}
    const usageStart = agent.calls?.length ?? 0;
    const episodes = [], buildDigests = [];
    const frozen = snapshot(modules);
    try {
      const instances = [];
      for (let index = 0; index < worlds.length; index++) instances.push(await freezeEvaluationInstance(
        {...options, world: worlds[index], instance: undefined, expectedInitialStateHash: undefined},
        {phase: 'preparation', index, trials: worlds.length}));
      for (const [index, world] of worlds.entries()) {
        const buildDigest = digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world))));
        episodes.push(...await runBatch({instances: [instances[index].instance], initialStateHashes: [instances[index].expectedInitialStateHash], instancePlan: instances[index].instancePlan, agent, driver, store, world, modules: frozen.modules, node, budget, benchmarkId: identity.benchmarkId, protocolId: identity.protocolId, split: 'preparation', scoreNormalization: options.scoreNormalization, phase: 'evaluation_skill_preparation', skills: []}, 1));
        ensure(digest(await hostVerificationCall('world_fingerprint', () => driver.fingerprint(clone(world)))) === buildDigest, 'Preparation world changed during execution');
        buildDigests.push(buildDigest);
      }
      ensure(!episodes.some(row => row.technicalFailure), 'Preparation contains technical failures; no frozen skill artifact was created');
      const result = await agent.ask('skills_prepare', {benchmarkId: identity.benchmarkId, protocolId: identity.protocolId, episodes, harnessId: frozen.id}, {guidance: 'Frozen benchmark guidance', evidenceIds: ['Preparation episode ID']}, {node, phase: 'evaluation_skill_summary'});
      store.record('evaluation_skill_proposal_saved', {proposalDigest: store.put(result), harnessId: frozen.id, key});
      ensure(text(result.guidance), 'Loadable skill guidance required');
      const evidenceIds = Array.isArray(result.evidenceIds) ? clone(result.evidenceIds) : [];
      if (!evidenceIds.length || !evidenceIds.every(id => episodes.some(row => row.episodeId === id))) store.record('evaluation_skill_diagnostic', {key, message: 'Invalid skill evidence references', retained: true});
      ensure(snapshot(modules).id === frozen.id, 'Harness changed during preparation');
      const preparationUsage = agent.usageSince?.(usageStart, {preparationId: options.preparationId}) ?? null;
      const preparationCost = episodes.reduce((sum, row) => sum + row.cost, 0);
      const artifact = {namespace: 'evaluation_skills', key, identity, status: 'frozen', harnessId: frozen.id,
        preparationPlanDigest: digest(worlds), buildDigests, episodes, preparationEpisodeIds: episodes.map(row => row.episodeId),
        evidenceIds, skills: [result.guidance], guidance: result.guidance, preparationCost, preparationUsage};
      const envelope = {artifact, artifactDigest: digest(artifact)}, temporary = file + '.pending';
      fs.writeFileSync(temporary, JSON.stringify(envelope) + '\n');
      fs.renameSync(temporary, file);
      store.record('evaluation_skills_frozen', {key, benchmarkId: identity.benchmarkId, harnessId: frozen.id, artifactDigest: envelope.artifactDigest, preparationEpisodeIds: artifact.preparationEpisodeIds});
      return {...clone(artifact), reused: false, adaptationCost: preparationCost, usage: preparationUsage};
    } finally {fs.closeSync(handle); fs.unlinkSync(lock);}
  };
  const promise = task();
  pending.set(file, promise);
  try {return await promise;} finally {pending.delete(file);}
}
