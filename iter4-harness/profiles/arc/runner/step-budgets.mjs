import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';

const policyBytes = readFileSync(new URL('./step-budget-policy.json', import.meta.url));
export const stepBudgetPolicy = JSON.parse(policyBytes);
export const stepBudgetPolicySha256 = createHash('sha256').update(policyBytes).digest('hex');
export const stepBudgetImplementationSha256 = createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex');

function positiveInteger(value, label) {
  const n = typeof value === 'number' || typeof value === 'string' && value.trim() ? Number(value) : NaN;
  if (!Number.isSafeInteger(n) || n <= 0) throw new Error(`${label} must be a positive safe integer`);
  return n;
}

export function resolveStepBudget({taskId, driver = {}, configuration = {}, unseen = false, env = {}}) {
  const limits = [];
  const add = (source, value) => limits.push({source, steps: positiveInteger(value, source)});
  const rule = stepBudgetPolicy.tasks[taskId];

  if (driver.maxSteps != null) add('driver.maxSteps', driver.maxSteps);
  if (configuration.maxSteps != null) add('configuration.maxSteps', configuration.maxSteps);
  if (rule) add('task_policy', rule.maxSteps);
  if (!limits.length) add('legacy_fallback', unseen ? 4000 : 200);
  if (env.H0_STEP_CEILING !== undefined) add('H0_STEP_CEILING', env.H0_STEP_CEILING);
  if (unseen && env.H0_UNSEEN_STEP_CEILING !== undefined) add('H0_UNSEEN_STEP_CEILING', env.H0_UNSEEN_STEP_CEILING);

  if (taskId === 'arc_agi_3') {
    const independent = configuration.protocol === 'independent-native-level-v1'
      || configuration.selector?.scope === 'independent_native_level';
    const level = configuration.levelIndex ?? configuration.selector?.levelIndex;
    if (independent && (!Number.isSafeInteger(level) || level < 0)) throw new Error('Independent ARC level needs a nonnegative integer levelIndex');
    const baselines = configuration.baselineActions;
    if (Array.isArray(baselines) && baselines.length && baselines.every(n => Number.isSafeInteger(n) && n > 0)) {
      if (independent && level >= baselines.length) throw new Error('ARC levelIndex exceeds baseline metadata');
      const baseline = independent ? baselines[level] : baselines.reduce((a,b) => a+b, 0);
      add(independent ? 'arc_level_baseline' : 'arc_game_baselines',
        Math.max(independent ? rule.independentMin : 200, rule.baselineMultiplier * baseline + rule.baselineSlack));
    }
  }
  return {
    version: stepBudgetPolicy.version, policySha256: stepBudgetPolicySha256,
    implementationSha256: stepBudgetImplementationSha256,
    maxSteps: Math.min(...limits.map(x => x.steps)), limits,
    comparisonScope: ['balrog_nethack', 'balrog_crafter'].includes(taskId) ? 'cost_limited_progression' : 'task_budgeted',
  };
}

export function finishWithStepBudget({terminal, observation, steps, budget}) {

  if (terminal?.ended) return terminal;
  if (observation?.terminal?.ended) return observation.terminal;

  if (terminal?.outcome) return terminal;
  if (steps < budget.maxSteps) return terminal ?? observation?.terminal ?? null;
  return {
    ended: false, outcome: 'budget_exhausted', reason: 'host_step_limit', score: null,
    budgetTruncated: true, retryable: false, steps, maxSteps: budget.maxSteps,
    nativeTerminal: observation?.terminal ?? null,
    lastPublicEvidence: {
      publicText: observation?.publicText ?? null,
      info: observation?.info ?? null, reward: observation?.reward ?? null,
      stateHash: observation?.stateHash ?? null, step: observation?.step ?? null,
    },
  };
}
