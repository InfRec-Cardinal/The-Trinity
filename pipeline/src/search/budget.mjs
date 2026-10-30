import { assert, now } from '../core.mjs';

const positive = (value, label, max) => {
  assert(Number.isInteger(value) && value >= 0 && value <= max, `${label} must be an integer from 0 to ${max}`); return value;
};
export function searchCheckpoint(store) {
  const s = store.state.search;
  if (!s) return { runId: null, status: 'not started', agents: [], totals: { turns: 0, searches: 0, input: 0, output: 0 } };
  const agents = Object.values(s.agentUsage ?? {}).map(summary => {
    const run = store.loadAgent(summary.key);
    return { ...summary, status: run?.status ?? summary.status, turns: run?.turn ?? summary.turns,
      searches: run?.searches ?? summary.searches, searchResults: run?.searchResults ?? summary.searchResults,
      usage: run?.usage ?? summary.usage, previousUsage: run?.invalidated?.previousUsage ?? null,
      previousTurns: run?.invalidated?.previousTurns ?? 0, previousSearches: run?.invalidated?.previousSearches ?? 0,
      budget: run?.budget ?? summary.budget, lastError: run?.lastError ?? null,
      turnsRemaining: Math.max(0, (run?.budget?.turnLimit ?? 0) - (run?.turn ?? 0)),
      searchesRemaining: Math.max(0, (run?.budget?.searchLimit ?? 0) - (run?.searches ?? 0)) };
  });
  const totals = agents.reduce((total, a) => ({ turns: total.turns + a.turns + a.previousTurns, searches: total.searches + a.searches + a.previousSearches,
    input: total.input + (a.usage?.input ?? 0) + (a.previousUsage?.input ?? 0), output: total.output + (a.usage?.output ?? 0) + (a.previousUsage?.output ?? 0) }), { turns: 0, searches: 0, input: 0, output: 0 });
  return { runId: s.runId, status: s.status, phase: s.phase, activeAgentKey: s.activeAgentKey, agents, totals,
    grants: s.budgetGrants ?? {}, history: s.budgets ?? [], errorCode: s.errorCode, savedAt: store.state.updatedAt,
    checkpointDirectory: 'data/agents/', config: store.state.config.search };
}

export function grantSearchBudget(store, { agentKey, turns = 80, searches = 32, supplementRounds = 3 } = {}) {
  const s = store.state.search; assert(s && s.status !== 'done', 'an unfinished search is required to add a budget');
  positive(turns, 'additional turns', 10000); positive(searches, 'additional searches', 10000);
  positive(supplementRounds, 'additional supplement rounds', 100);
  const key = agentKey ?? s.activeAgentKey;
  let grant = null, addedSearches = 0;
  if (key) {
    assert(key.startsWith(`${s.runId}/`), 'the agent must belong to the current search');
    const run = store.loadAgent(key); assert(run?.budget, 'the selected agent has no saved budget checkpoint');
    const previous = s.budgetGrants?.[key] ?? run.budget;

    addedSearches = run.budget.searchLimit > 0 ? searches : 0;
    grant = { turnLimit: Math.max(previous.turnLimit, run.budget.turnLimit) + turns,
      searchLimit: run.budget.searchLimit > 0 ? Math.max(previous.searchLimit, run.budget.searchLimit) + addedSearches : 0,
      maxTokens: run.budget.maxTokens };
    assert(grant.turnLimit <= 10000 && grant.searchLimit <= 10000, 'per-agent ceilings cannot exceed 10000');
    (s.budgetGrants ??= {})[key] = grant;
  } else assert(s.status === 'incomplete', 'no active agent checkpoint is available; resume the saved search first');
  if (s.status === 'incomplete') {
    assert(supplementRounds > 0, 'an incomplete split needs additional supplement rounds');

    s.nextSupplementRounds = supplementRounds;
  }
  const entry = { at: now(), agentKey: key ?? null, added: { turns: key ? turns : 0, searches: addedSearches,
    supplementRounds: s.status === 'incomplete' ? supplementRounds : 0 }, effective: grant };
  (s.budgets ??= []).push(entry); store.event('search_budget_added', entry); store.save();
  return { ...entry, checkpoint: searchCheckpoint(store) };
}



