import { join } from 'node:path';
import { existsSync } from 'node:fs';
import { readJson, writeJsonAtomic, appendJsonLine, now } from './core.mjs';
import { DEFAULT_SPLIT_CONFIG } from './split.mjs';
import { SEARCH_POLICY_VERSION, policyWidensFrom } from './search/schema.mjs';

export const STATE_VERSION = 'trinity-pipeline-v2';
export const SEARCH_BUDGET_PRESET = 'research-v2';
export const SEARCH_SCHEDULING_VERSION = 'specification-ten-v1';
export const DEFAULT_SEARCH_CONFIG = Object.freeze({
  maxAreas: 15, areaConcurrency: 3, minSearchesPerArea: 0, searchesPerArea: 48, sweepTurns: 120, sweepTokens: 12000,
  planTurns: 5, planTokens: 12000,
  coverageTurns: 12, coverageTokens: 8000, maxRepairAreas: 3,
  specifyConcurrency: 10, specifySearches: 24, specifyTurns: 80, specifyTokens: 20000, specifyAttempts: 4,
  reviewTurns: 24, reviewTokens: 16000, taxonomyTurns: 24, taxonomyTokens: 24000,
  lineageTurns: 80, lineageSearches: 32, lineageTokens: 24000,
  supplementRounds: 6, minSupplementSearches: 4, supplementSearches: 40,
  supplementTurns: 100, supplementTokens: 12000, selfProposedRounds: 0,
});
const PREVIOUS_SEARCH_DEFAULTS = { maxAreas: 20, searchesPerArea: 12, sweepTurns: 40,
  specifySearches: 4, specifyTurns: 24, specifyAttempts: 2, reviewTurns: 6, taxonomyTurns: 8,
  supplementRounds: 2, supplementSearches: 10, supplementTurns: 30, selfProposedRounds: 1 };
export const DEFAULT_CONFIG = Object.freeze({
  searchBudgetPreset: SEARCH_BUDGET_PRESET,
  search: DEFAULT_SEARCH_CONFIG,
  split: DEFAULT_SPLIT_CONFIG,
});

export function blankState() {
  return { version: STATE_VERSION, createdAt: now(), updatedAt: now(), config: structuredClone(DEFAULT_CONFIG),
    search: null, library: null, split: null, analysis: null, jobs: [] };
}

export function prepareSearchScheduling(store) {
  const config = store.state.config;
  if (config.searchSchedulingVersion === SEARCH_SCHEDULING_VERSION) return null;
  const from = config.search.specifyConcurrency ?? null;
  if (from == null || from === 5 || from === 20) config.search.specifyConcurrency = DEFAULT_SEARCH_CONFIG.specifyConcurrency;
  config.searchSchedulingVersion = SEARCH_SCHEDULING_VERSION;
  store.save();
  return { from, to: config.search.specifyConcurrency, version: SEARCH_SCHEDULING_VERSION };
}

export function openStore(dataDir) {
  const stateFile = join(dataDir, 'state.json'), eventsFile = join(dataDir, 'events.jsonl'), agentDir = join(dataDir, 'agents');
  const state = existsSync(stateFile) ? readJson(stateFile) : blankState();
  if (state.version !== STATE_VERSION) throw new Error(`unsupported state version ${state.version}`);
  const configured = { ...(state.config?.search ?? {}) };
  if (state.config?.searchBudgetPreset !== SEARCH_BUDGET_PRESET) {
    for (const [key, old] of Object.entries(PREVIOUS_SEARCH_DEFAULTS)) {
      if (configured[key] === old) configured[key] = DEFAULT_SEARCH_CONFIG[key];
    }
  }
  state.config = { ...DEFAULT_CONFIG, ...state.config, searchBudgetPreset: SEARCH_BUDGET_PRESET,
    search: { ...DEFAULT_SEARCH_CONFIG, ...configured, minSearchesPerArea: 0, selfProposedRounds: 0 },
    split: { ...DEFAULT_SPLIT_CONFIG, ...state.config?.split } };

  if (state.search && state.search.policyVersion !== SEARCH_POLICY_VERSION && !policyWidensFrom(state.search.policyVersion)) {
    state.search.status = 'policy_update_required'; state.search.phase = 'scope_review';
    state.search.errorCode = 'search_policy_changed'; state.search.error = 'A narrowed task-input scope requires renewed specification and admission review; saved search evidence and checkpoints are retained.';
    state.library = null; state.split = null; state.analysis = null;
    state.updatedAt = now(); writeJsonAtomic(stateFile, state);
  }
  return {
    dataDir, state,
    save() { state.updatedAt = now(); writeJsonAtomic(stateFile, state); },
    event(type, data = {}) { const e = { at: now(), type, ...data }; appendJsonLine(eventsFile, e); return e; },
    loadAgent(key) { const f = join(agentDir, safeName(key) + '.json'); return existsSync(f) ? readJson(f) : null; },
    saveAgent(run) { writeJsonAtomic(join(agentDir, safeName(run.key) + '.json'), run); },
  };
}

export const safeName = key => String(key).replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 180);
