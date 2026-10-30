import { now } from './core.mjs';
import { rank } from './search/schema.mjs';

export const SPLIT_POLICY = 'train-unseen-per-direction-v6';
export const SPLIT_RULE = 'a configurable fraction of each direction is unseen, selected by authority from independently audited published tasks of solo source groups; reserve at least one training task per nonempty direction; every other task train; the same rules apply to interactive and static tasks';
export const DEFAULT_SPLIT_CONFIG = Object.freeze({ unseenFraction: 18 / 46 });
export const SETS = Object.freeze(['train', 'unseen']);

export function normalizeSplitConfig(config = {}) {
  const { unseenFraction } = { ...DEFAULT_SPLIT_CONFIG, ...config };
  if (typeof unseenFraction !== 'number' || !Number.isFinite(unseenFraction) || unseenFraction <= 0 || unseenFraction >= 1) {
    throw new Error('unseenFraction must be a finite number greater than 0 and less than 1');
  }
  return { unseenFraction };
}

export function deriveSplit(library, options = {}) {
  const config = normalizeSplitConfig(options);
  const sets = {}, gaps = [], errors = [], directions = [];
  const groupSize = new Map();
  for (const t of library.tasks) groupSize.set(t.sourceGroup, (groupSize.get(t.sourceGroup) ?? 0) + 1);
  for (const d of library.directions) {
    const tasks = library.tasks.filter(t => t.direction === d.id).sort(rank);
    const unseenTarget = Math.min(Math.max(0, tasks.length - 1), Math.max(1, Math.round(tasks.length * config.unseenFraction)));
    const eligible = tasks.filter(t => t.unseenEligible === true && !t.selfProposed && t.origin !== 'self_proposed' && groupSize.get(t.sourceGroup) === 1);
    const unseen = new Set(eligible.slice(0, unseenTarget).map(t => t.taskId));
    for (const t of tasks) sets[t.taskId] = unseen.has(t.taskId) ? 'unseen' : 'train';
    const trainCount = tasks.length - unseen.size;
    if (!unseen.size) gaps.push({ direction: d.id, label: d.label, track: d.track, need: 'independent_unseen', have: 0, want: 1 });
    if (!trainCount) gaps.push({ direction: d.id, label: d.label, track: d.track, need: 'train_task', have: 0, want: 1 });
    directions.push({ id: d.id, label: d.label, track: d.track, train: trainCount, unseen: unseen.size, unseenTarget });
  }
  for (const t of library.tasks) if (!(t.taskId in sets)) errors.push(`${t.taskId} sits in no direction of the tree`);
  const counts = Object.fromEntries(SETS.map(s => [s, Object.values(sets).filter(v => v === s).length]));
  return { policy: SPLIT_POLICY, rule: SPLIT_RULE, config, sets, directions, gaps, errors, counts, derivedAt: now() };
}

export const setOf = (state, taskId) => state.split?.sets?.[taskId] ?? null;
export const tasksIn = (state, set) => (state.library?.tasks ?? []).filter(t => setOf(state, t.taskId) === set);
