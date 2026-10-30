import {hostVerificationCall} from './host-verification.mjs';
import {screeningPolicy} from './screening-policy.mjs';
import {freezeExplorationInstances} from './exploration-plan.mjs';
import {normalizeScore} from './metrics.mjs';
import {normalizeMedia, publicText} from './media.mjs';
import {execute, validate} from './runtime.mjs';
import {clone, ensure, digest, snapshot} from './core.mjs';
import {sealTerminalReceipt} from './receipts.mjs';

export async function runEpisode({agent, driver, store, world, modules, budget, phase, node, skills = [], benchmarkId = null, taskId = null, split = null, protocolId = null, iteration = agent.scope?.iteration ?? null, scoreNormalization = null, decisionId = null, publicTask = null, instance = null, expectedInitialStateHash = null, instancePlan = null}) {
  if (phase === 'initial_training_exploration' && instancePlan === null) {
    const plan = await freezeExplorationInstances({driver, world, trials: 1, store, taskId});
    instance = plan.instances[0];
    expectedInitialStateHash = plan.initialStateHashes[0];
    instancePlan = plan.event;
  }
  const frozen = snapshot(modules);
  const identity = {benchmarkId, taskId, split, protocolId, iteration, scoreNormalization, budget, instance: clone(instance), expectedInitialStateHash, instancePlan};
  let initialStateHash = null;
  const evidence = [], history = [], carry = {}, receipts = [];
  const episodeKey = store.record('episode_started', {...identity, phase, node, budget, decisionId, worldDigest: digest(world), harnessId: frozen.id});
  let failureStage = 'reset';
  let session, calls = 0, moduleAttempts = 0, actionAttempts = 0;
  const usageStart = agent.calls?.length ?? 0;
  const metrics = () => ({...identity, initialStateHash, actionAttempts, moduleAttempts, missingCosts: actionAttempts - receipts.filter(row => Number.isFinite(row.cost) && row.cost >= 0).length, moduleCalls: calls, scoreSource: receipts.at(-1)?.done ? 'terminal_receipt' : receipts.length ? 'last_receipt' : null, score: Number.isFinite(receipts.at(-1)?.score) ? receipts.at(-1).score : null,
    reward: receipts.length && receipts.length === actionAttempts && receipts.every(row => Number.isFinite(row.reward)) ? receipts.reduce((n, row) => n + row.reward, 0) : null,
    reportedRewardSum: receipts.reduce((n, row) => n + (Number.isFinite(row.reward) ? row.reward : 0), 0),
    missingRewards: actionAttempts - receipts.filter(row => Number.isFinite(row.reward)).length, usage: agent.usageSince?.(usageStart, {episodeId: episodeKey}) ?? null});
  const finish = async report => {
    report.publicTask = clone(publicTask ?? {goal: null, initialObservation: null, metadata: {}});
    report.decisionId = decisionId;
    try {report.normalizedScore = normalizeScore(report.score, scoreNormalization);}
    catch (error) {report.normalizedScore = null; report.normalizationError = String(error.message);}
    report.costComplete = report.missingCosts === 0;
    if (session && driver.close) {
      try {await hostVerificationCall('episode_cleanup', () => driver.close(session));}
      catch (error) {report.success = false; report.technicalFailure = true; report.failureStage = 'cleanup'; report.reason = 'Environment cleanup failed: ' + String(error.message);}
      session = null;
    }
    if (!report.technicalFailure) report.terminalReceipt = sealTerminalReceipt(report, {decisionId, budget,
      termination: receipts.at(-1)?.done ? 'environment' : 'host_budget_exhausted'});
    store.record('episode_finished', report);
    return report;
  };
  try {
    session = instance === null ? await hostVerificationCall('episode_reset', () => driver.reset(clone(world))) : await hostVerificationCall('episode_reset', () => driver.reset(clone(world), clone(instance)));
    if (instance !== null) {
      failureStage = 'initial_state';
      ensure(typeof driver.initialState === 'function', 'Matched execution requires driver.initialState');
      initialStateHash = digest(await hostVerificationCall('episode_initial_state', () => driver.initialState(session)));
      ensure(expectedInitialStateHash === null || initialStateHash === expectedInitialStateHash, 'Initial state differs from the frozen exploration plan');
    }
    ensure(session && session.observation && typeof session.actionSchema === 'object', 'Invalid environment reset');
    let observation = normalizeMedia(session.observation);
    publicTask ??= {goal: observation.goal ?? null, initialObservation: clone(observation), metadata: {}};
    for (let step = 1; step <= budget; step++) {
      let moduleResults = [], action;
      for (let call = 0; call <= 2; call++) {
        failureStage = 'model_transport';
        const response = await agent.ask('explorer_act', {
          observation, history: clone(history), remaining: budget - step + 1,
          modules: frozen.modules.map(module => ({moduleId: module.moduleId, protocolClass: module.protocolClass, prompt: module.prompt, required: module.interface.required})),
          moduleResults, carry: clone(carry), callsRemaining: 2 - call, actionSchema: session.actionSchema, skills: clone(skills)
        }, {kind: 'module or action', module: ['moduleId', 'publicInput'], action: ['action']}, {...identity, episodeId: episodeKey, harnessId: frozen.id, phase, node});
        failureStage = 'agent_protocol';
        if (response.kind === 'action') {action = response.action; break;}
        ensure(response.kind === 'module' && call < 2, 'Module allowance exceeded or invalid decision');
        const module = frozen.modules.find(value => value.moduleId === response.moduleId);
        ensure(module, 'Unknown module selection');
        validate(module);
        const input = clone(response.publicInput);
        if (module.protocolClass === 'memory') input.carry = clone(carry[module.moduleId] ?? null);
        else ensure(!Object.hasOwn(input, 'carry'), 'Only Memory may receive retained carry');
        moduleAttempts++;
        const output = await execute(module, input);
        if (module.protocolClass === 'memory' && output && Object.hasOwn(output, 'carry')) carry[module.moduleId] = clone(output.carry);
        const result = {moduleId: module.moduleId, version: module.version, output};
        moduleResults.push(result);
        evidence.push({step: evidence.length + 1, publicText: publicText({observation, ...result}), publicData: {observation, ...result}, moduleInput: input});
        calls++;
      }
      ensure(action && typeof action === 'object', 'Native action required');
      actionAttempts++;
      failureStage = 'step';
      const receipt = await hostVerificationCall('episode_step', () => driver.step(session, clone(action)));
      receipts.push({done: receipt?.done === true, cost: Number.isFinite(receipt?.cost) && receipt.cost >= 0 ? receipt.cost : null,
        score: Number.isFinite(receipt?.score) ? receipt.score : null, reward: Number.isFinite(receipt?.reward) ? receipt.reward : null});
      ensure(receipt && typeof receipt.done === 'boolean' && typeof receipt.success === 'boolean' && receipt.observation && typeof receipt.cost === 'number' && receipt.cost >= 0 && Number.isFinite(receipt.cost), 'Invalid host receipt');
      ensure(!receipt.success || receipt.done, 'Success requires a terminal receipt');
      receipt.observation = normalizeMedia(receipt.observation);
      for (const key of ['score', 'reward']) ensure(receipt[key] == null || Number.isFinite(receipt[key]), 'Invalid host ' + key);
      const item = {step, observation: clone(observation), action: clone(action), receipt: clone(receipt)};
      history.push(item);
      evidence.push({step: evidence.length + 1, publicText: publicText(item), publicData: item});
      observation = clone(receipt.observation);
      if (receipt.done) {
        const report = {...metrics(), episodeId: episodeKey, phase, node, harnessId: frozen.id, worldDigest: digest(world), success: receipt.success, technicalFailure: false, actions: step, moduleCalls: calls, cost: receipts.reduce((sum, value) => sum + value.cost, 0), events: evidence};
        return await finish(report);
      }
    }
    const report = {...metrics(), episodeId: episodeKey, phase, node, harnessId: frozen.id, worldDigest: digest(world), success: false, technicalFailure: false, actions: budget, cost: receipts.reduce((sum, value) => sum + value.cost, 0), events: evidence, reason: 'Action budget exhausted'};
    return await finish(report);
  } catch (error) {
    const report = {...metrics(), episodeId: episodeKey, phase, node, harnessId: frozen.id, worldDigest: digest(world), success: false, technicalFailure: true, actions: receipts.length, cost: receipts.reduce((sum, value) => sum + value.cost, 0), events: evidence, failureStage, reason: String(error.message)};
    return await finish(report);
  }
}
export async function runBatch(options, trials) {
  if (options.phase === 'initial_training_exploration' && !options.initialStateHashes) {
    const plan = await freezeExplorationInstances({...options, trials});
    options = {...options, instances: plan.instances, initialStateHashes: plan.initialStateHashes, instancePlan: plan.event};
  }
  const rows = [];
  ensure(Number.isInteger(trials) && trials > 0, 'Positive episode count required');
  const retries = options.phase === 'initial_training_exploration' ? (options.infrastructureRetries ?? 2) : 0;
  ensure(Number.isInteger(retries) && retries >= 0, 'Invalid infrastructure retry budget');
  if (options.instances) ensure(options.instances.length === trials, 'Instance manifest length mismatch');
  for (let trial = 0; trial < trials; trial++) {
    for (let attempt = 0; ; attempt++) {
      const row = await runEpisode({...options, instance: options.instances?.[trial] ?? null, expectedInitialStateHash: options.initialStateHashes?.[trial] ?? null});
      if (!row.technicalFailure || options.phase !== 'initial_training_exploration') {rows.push(row); break;}
      ensure(['reset', 'step', 'cleanup', 'model_transport'].includes(row.failureStage), 'Technical failures in agent protocol are not retryable infrastructure errors');
      options.store.record('initial_exploration_retry', {trial, attempt, episodeId: row.episodeId, exhausted: attempt >= retries});
      ensure(attempt < retries, 'Technical failures exhausted the initial exploration retry budget');
    }
  }
  return rows;
}
export async function matchedInstances(driver, world, trials) {
  ensure(typeof driver.instanceManifest === 'function' && typeof driver.initialState === 'function', 'Matched comparisons require instanceManifest and initialState adapter methods');
  const instances = await hostVerificationCall('instance_manifest', () => driver.instanceManifest(clone(world), trials));
  ensure(Array.isArray(instances) && instances.length === trials && instances.every(row => row && typeof row === 'object'), 'Invalid matched instance manifest');
  return clone(instances);
}
function matched(left, right) {
  return left.worldDigest === right.worldDigest && left.taskId === right.taskId && Number.isInteger(left.budget) && left.budget === right.budget &&
    left.instance !== null && left.instance !== undefined && digest(left.instance) === digest(right.instance) &&
    (left.technicalFailure || right.technicalFailure || typeof left.initialStateHash === 'string' && left.initialStateHash === right.initialStateHash);
}
export const completions = rows => rows.filter(row => row.success && !row.technicalFailure).length;
export function performanceDecision(baseline, validation) {
  ensure(baseline.length === 5 && validation.length === 5, 'Performance measurement requires five learning and five validation episodes');
  ensure(baseline.every((row, index) => matched(row, validation[index])), 'Performance comparison worlds differ');
  const baselineCompletions = completions(baseline), candidateCompletions = completions(validation);
  const technicalFailure = [...baseline, ...validation].some(row => row.technicalFailure);
  const nonDecreasing = !technicalFailure && candidateCompletions >= baselineCompletions;
  return {accepted: true, reason: 'retained_without_performance_gate', technicalFailure, nonDecreasing, comparison: technicalFailure ? 'unavailable' : candidateCompletions > baselineCompletions ? 'improved' : candidateCompletions === baselineCompletions ? 'tied' : 'regressed', baselineCompletions, candidateCompletions, baselineTrials: 5, validationTrials: 5, baselineWinRate: baselineCompletions / 5, candidateWinRate: candidateCompletions / 5};
}
export function screeningDecision(rows, configuredPolicy) {
  const policy = screeningPolicy(configuredPolicy);
  ensure(Array.isArray(rows) && rows.length === policy.trials, 'Screening episode count differs from the frozen policy');
  if (rows.some(row => row.technicalFailure)) return {accepted: false, reason: 'technical_failure', successes: completions(rows), trials: policy.trials, policy};
  const successes = completions(rows), accepted = successes >= policy.minSuccesses && successes <= policy.maxSuccesses;
  return {accepted, reason: accepted ? 'admitted' : successes < policy.minSuccesses ? 'too_hard' : 'too_easy', successes, trials: policy.trials, policy};
}
export function chooseInheritance(oldRows, newRows) {
  ensure(oldRows.length === newRows.length && oldRows.length > 0 && oldRows.every((row, index) => matched(row, newRows[index])), 'Inheritance comparison is not matched');
  return {accepted: !oldRows.some(row => row.technicalFailure) && !newRows.some(row => row.technicalFailure) && completions(newRows) > completions(oldRows), previousCompletions: completions(oldRows), candidateCompletions: completions(newRows)};
}
