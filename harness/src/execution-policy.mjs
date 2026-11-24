import {randomUUID} from 'node:crypto';

const unknownProfiles = new WeakMap();
export function executionIdentity(agent) {
  const declared = agent?.executionProfile ?? agent?.backend?.executionProfile;
  if (declared) return structuredClone(declared);
  if (!agent || typeof agent !== 'object') return null;
  if (!unknownProfiles.has(agent)) unknownProfiles.set(agent, {kind: 'unreported', agentScope: randomUUID()});
  return structuredClone(unknownProfiles.get(agent));
}

export function validateFreeActionAllowance(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Explicit nonnegative maxFreeActions required for environment-cost execution');
  return value;
}

export function executionLimits({budget, driver, maxFreeActions}) {
  if (!Number.isSafeInteger(budget) || budget <= 0) throw Error('Positive integer action budget required');
  const budgetUnit = driver?.budgetUnit ?? 'action';
  if (!['action', 'environment_cost'].includes(budgetUnit)) throw Error('Unsupported driver budget unit');
  if (maxFreeActions !== undefined) validateFreeActionAllowance(maxFreeActions);
  const interactionLimit = budgetUnit === 'environment_cost' ? budget + validateFreeActionAllowance(maxFreeActions) : budget;
  if (!Number.isSafeInteger(interactionLimit)) throw Error('Interaction limit is too large');
  return {budgetUnit, interactionLimit};
}

export function benchmarkBudget(task, defaults) {
  return {budget: task.actionBudget ?? defaults.actionBudget,
    maxFreeActions: task.maxFreeActions ?? defaults.maxFreeActions};
}

export function bindTaskBudgets(tasks, budgets = {}) {
  if (!budgets || typeof budgets !== 'object' || Array.isArray(budgets)) throw Error('taskBudgets must be an object');
  const ids = new Set(tasks.map(task => task.id));
  for (const [id, policy] of Object.entries(budgets)) {
    if (!ids.has(id)) throw Error('Unknown task budget: ' + id);
    if (!policy || typeof policy !== 'object' || Array.isArray(policy) ||
      Object.keys(policy).some(key => !['actionBudget', 'maxFreeActions'].includes(key))) throw Error('Invalid task budget policy');
    if (!Number.isSafeInteger(policy.actionBudget) || policy.actionBudget <= 0) throw Error('Positive per-task actionBudget required');
    if (policy.maxFreeActions !== undefined) validateFreeActionAllowance(policy.maxFreeActions);
  }
  return tasks.map(task => ({...task, ...budgets[task.id]}));
}
