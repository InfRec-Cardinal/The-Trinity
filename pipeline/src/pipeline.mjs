import { now, assert } from './core.mjs';
import { tasksIn, SPLIT_RULE, deriveSplit } from './split.mjs';

export function resetFrom(state, stage) {
  const order = ['split', 'analysis'];
  for (const s of order.slice(Math.max(0, order.indexOf(stage)))) {
    if (s === 'split') state.split = null;
    if (s === 'analysis') state.analysis = null;
  }
}

export function splitLibrary(store) {
  const { state } = store;
  assert(state.library, 'assemble the task library first (the search stage does this when it completes)');
  state.split = deriveSplit(state.library, state.config?.split);
  resetFrom(state, 'analysis');
  store.event('split_derived', state.split.counts);
  store.save();
  return state.split;
}

export function overview(state) {
  const s = state.search, tasks = state.library?.tasks ?? [];
  const candidates = Object.values(s?.candidates ?? {});
  return {
    search: { status: s?.status ?? 'not started', phase: s?.phase ?? null, areas: s?.areas.length ?? 0, areasDone: s?.areas.filter(a => a.status === 'done').length ?? 0,
      candidates: candidates.length, admitted: candidates.filter(c => c.status === 'admitted').length, rejected: candidates.filter(c => c.status === 'rejected').length,
      selfProposed: candidates.filter(c => c.status === 'admitted' && c.origin === 'self_proposed').length,
      directions: state.library?.directions.length ?? 0, tasks: tasks.length, train: tasksIn(state, 'train').length, unseen: tasksIn(state, 'unseen').length,
      gaps: state.split?.gaps ?? [], splitErrors: state.split?.errors ?? [], rule: state.split?.rule ?? SPLIT_RULE, error: s?.error ?? null },
    split: state.split ? { policy: state.split.policy, counts: state.split.counts, gaps: state.split.gaps.length, errors: state.split.errors.length } : null,
    at: now(),
  };
}


