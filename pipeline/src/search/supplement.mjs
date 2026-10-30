import { fn, runAgent } from '../agent.mjs';
import { prompt } from '../prompts.mjs';
import { now } from '../core.mjs';
import { supportsSearch } from '../model.mjs';
import { PAGE_TOOLS, pageHandlers, TASK_FIELDS, saveCandidate, requireSearchProgress } from './discover.mjs';

export const SUPPLEMENT_TOOLS = [
  fn('save_task', 'Record one published task for the gap direction.', { ...TASK_FIELDS, origin: { type: 'string', enum: ['search'] }, mechanismSourceUrl: { type: ['string', 'null'] } }),
  ...PAGE_TOOLS,
  fn('finish_supplement', 'Finish this search round after real searches.', { summary: { type: 'string', minLength: 20 }, outcome: { type: 'string', enum: ['recorded_candidates', 'nothing_found'] }, stopReason: { type: 'string', enum: ['saturated', 'budget_exhausted'] } }),
];

export async function supplementGap(ctx, gap, round, mode) {
  const { store } = ctx, state = store.state, s = state.search, cfg = state.config.search;
  if (mode !== 'search') throw new Error('Supplemental rounds search for published tasks; self-proposed library tasks are recorded through library curation and are train-only');
  if (!supportsSearch(ctx.profile)) throw new Error('Web search is unavailable for the connected provider');
  const direction = state.library.directions.find(d => d.id === gap.direction);
  const focusedTask = Object.values(s.candidates).find(c => s.taxonomy?.assignments[c.taskId] === gap.direction && c.researchRole === 'game_world')
    ?? Object.values(s.candidates).find(c => s.taxonomy?.assignments[c.taskId] === gap.direction && c.researchRole);
  const inheritedFocus = { researchRole: focusedTask?.researchRole ?? 'support',
    supportDomain: focusedTask?.researchRole === 'game_world' ? null : focusedTask?.supportDomain ?? 'other' };
  const current = state.library.tasks.filter(t => t.direction === gap.direction).map(t => ({ taskId: t.taskId, name: t.name, set: state.split.sets[t.taskId] ?? null, sourceGroup: t.sourceGroup, sourceUrl: t.sourceUrl }));
  let record = s.supplements.find(x => x.round === round && x.mode === mode && x.direction === gap.direction);
  if (!record) { record = { round, mode, direction: gap.direction, need: gap.need, candidates: [], status: 'searching', at: now(),
    checkpointInput: { mode, round, gap, direction, currentTasks: current, minimumSearches: cfg.minSupplementSearches, searchBudget: cfg.supplementSearches } }; s.supplements.push(record); store.save(); }
  if (record.status === 'discovered' || record.status === 'done') return record.candidates;
  const result = await runAgent(ctx, { key: `${s.runId}/supplement-${round}-${mode}-${gap.direction}`, purpose: `supplement (${mode})`, system: prompt('supplement'),
    kickoff: JSON.stringify(record.checkpointInput),
    tools: SUPPLEMENT_TOOLS, maxTurns: cfg.supplementTurns, maxTokens: cfg.supplementTokens, searchBudget: cfg.supplementSearches,
    handlers: { ...pageHandlers(ctx),
      save_task: ({ origin, mechanismSourceUrl, ...args }) => {
        if (origin !== 'search') throw new Error('Supplement this library with published tasks only');
        const prior = s.candidates[args.taskId];
        const candidateFocus = args.kind === 'static' ? {researchRole: 'support', supportDomain: inheritedFocus.supportDomain ?? 'other'} : inheritedFocus;
        const r = saveCandidate(state, args, { ...candidateFocus,
          ...(prior?.researchRole ? { researchRole: prior.researchRole, supportDomain: prior.supportDomain } : {}),
          origin, mechanismSourceUrl: mechanismSourceUrl ?? null, targetDirection: gap.direction, foundIn: `supplement:${gap.direction}` });
        if (!record.candidates.includes(args.taskId)) record.candidates.push(args.taskId); store.save(); return r;
      },
      finish_supplement: (args, run) => {
        requireSearchProgress(run, Math.min(cfg.minSupplementSearches, cfg.supplementSearches));
        if (args.stopReason === 'budget_exhausted' && run.searches < run.budget.searchLimit) throw new Error('the granted search budget is not exhausted');
        if (args.outcome === 'recorded_candidates' && !record.candidates.length) throw new Error('no candidates were recorded');
        if (args.outcome === 'nothing_found' && record.candidates.length) throw new Error('candidates were recorded; use recorded_candidates');
        return { finish: { ...args, searches: run.searches, results: run.searchResults, turns: run.turn } };
      } } });
  Object.assign(record, result, { status: 'discovered', discoveredAt: now() });
  store.save();
  return record.candidates;
}
