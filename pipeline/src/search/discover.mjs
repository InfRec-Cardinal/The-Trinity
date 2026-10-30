import { fn, runAgent, askOnce, AgentError } from '../agent.mjs';
import { prompt } from '../prompts.mjs';
import { now } from '../core.mjs';
import { supportsSearch } from '../model.mjs';
import { capturePage, readCapture } from '../capture.mjs';
import { KINDS } from './schema.mjs';

export const AREA_ID_MIN_LENGTH = 2, AREA_ID_MAX_LENGTH = 41;
export const SUPPORT_CANDIDATE_LIMIT = 3;
export const PLAN_TOOL = fn('plan_search_areas', 'Submit the areas to sweep.', { areas: { type: 'array', minItems: 6, items: { type: 'object',
  properties: { id: { type: 'string', minLength: AREA_ID_MIN_LENGTH, maxLength: AREA_ID_MAX_LENGTH, pattern: '^[a-z][a-z0-9-]*$',
    description: 'A unique, stable ASCII id, 2-41 characters. Start with a lowercase letter; use lowercase letters, digits and hyphens. Keep full detail in title, why and queries. If rejected, shorten only the id and resubmit all areas without dropping coverage.' },
    title: { type: 'string', minLength: 4 }, why: { type: 'string', minLength: 20 }, queries: { type: 'array', minItems: 1, items: { type: 'string' } },
    researchRole: { type: 'string', enum: ['game_world', 'support'], description: 'Research allocation only, never a taxonomy direction. game_world requires actual interactive games, puzzles or simulated worlds.' },
    supportDomain: { type: ['string', 'null'], enum: ['digital_interaction', 'other', null], description: 'Use null for game_world, digital_interaction for all web/desktop/document interaction in one combined area, and other for remaining support.' } },
  required: ['id', 'title', 'why', 'queries'], additionalProperties: false } } });

export function normalizeAreaFocus(area) {
  const researchRole = area.researchRole === 'game_world' ? 'game_world' : 'support';
  return { ...area, researchRole, supportDomain: researchRole === 'game_world' ? null
    : area.supportDomain === 'digital_interaction' ? 'digital_interaction' : 'other' };
}

export function validateFocusedAreas(areas, { maxAreas = Infinity, requireMetadata = true } = {}) {
  const problems = [], ids = new Set();
  if (areas.length > maxAreas) problems.push(`at most ${maxAreas} areas`);
  for (const area of areas) {
    if (area.id.length < AREA_ID_MIN_LENGTH || area.id.length > AREA_ID_MAX_LENGTH) problems.push(`area id ${area.id} has ${area.id.length} characters; allowed length is ${AREA_ID_MIN_LENGTH}-${AREA_ID_MAX_LENGTH}. Shorten only the id, preserve this area's title and queries, and resubmit all areas`);
    if (!/^[a-z][a-z0-9-]*$/.test(area.id)) problems.push(`area id ${area.id} must start with a lowercase ASCII letter and contain only lowercase letters, digits and hyphens`);
    if (ids.has(area.id)) problems.push(`duplicate area ${area.id}; choose a distinct id without dropping the area`); ids.add(area.id);
    if (requireMetadata && !['game_world', 'support'].includes(area.researchRole)) problems.push(`area ${area.id} must declare researchRole as game_world or support`);
    if (requireMetadata && area.researchRole === 'game_world' && area.supportDomain !== null) problems.push(`game_world area ${area.id} must set supportDomain to null`);
    if (requireMetadata && area.researchRole === 'support' && !['digital_interaction', 'other'].includes(area.supportDomain)) problems.push(`support area ${area.id} must declare supportDomain as digital_interaction or other`);
  }
  const focused = areas.map(normalizeAreaFocus), games = focused.filter(area => area.researchRole === 'game_world').length;
  if (games < Math.ceil(areas.length * 2 / 3)) problems.push(`at least two thirds of research areas must be actual game_world areas; ${games} of ${areas.length} were declared. Explore distinct game/world mechanisms rather than relabeling fixed questions or ordinary office tasks`);
  const digital = focused.filter(area => area.supportDomain === 'digital_interaction').length;
  if (digital > 1) problems.push(`web, operating-system and document interaction must share at most one combined digital_interaction area; found ${digital}`);
  if (requireMetadata && !focused.some(area => area.supportDomain === 'digital_interaction')) problems.push('include one compact combined digital_interaction support area for web, operating-system and document interaction');
  return problems;
}

export const orderedResearchAreas = areas => [...areas.filter(area => area.researchRole === 'game_world'),
  ...areas.filter(area => area.researchRole !== 'game_world')];

export function searchFocusSummary(search) {
  const areas = (search.areas ?? []).map(normalizeAreaFocus), candidates = Object.values(search.candidates ?? {});
  const gameAreas = areas.filter(area => area.researchRole === 'game_world').length;
  const focusOf = candidate => candidate.researchRole ?? areas.find(area => area.id === candidate.foundIn)?.researchRole ?? 'support';
  const gameCandidates = candidates.filter(candidate => focusOf(candidate) === 'game_world' && candidate.kind === 'interactive').length;
  const admitted = candidates.filter(candidate => candidate.status === 'admitted');
  const admittedGames = admitted.filter(candidate => focusOf(candidate) === 'game_world' && candidate.kind === 'interactive').length;
  return { areaCount: areas.length, gameAreas, supportAreas: areas.length - gameAreas,
    digitalInteractionAreas: areas.filter(area => area.supportDomain === 'digital_interaction').length,
    gameAreaShare: areas.length ? gameAreas / areas.length : 0, candidateCount: candidates.length,
    gameCandidates, supportCandidates: candidates.length - gameCandidates,
    gameCandidateShare: candidates.length ? gameCandidates / candidates.length : 0,
    admittedCount: admitted.length, admittedGames, admittedSupport: admitted.length - admittedGames,
    admittedGameShare: admitted.length ? admittedGames / admitted.length : 0,
    minimumGameWorldAreaShare: 2 / 3, supportCandidateLimitPerArea: SUPPORT_CANDIDATE_LIMIT,
    allocationIsAdmissionGuarantee: false };
}

export const PAGE_TOOLS = [
  fn('fetch_page', 'Capture a public web page so it can be read now and quoted later.', { url: { type: 'string' } }),
  fn('read_page', 'Read a captured page by captureId, 6000 characters from offset.', { captureId: { type: 'string' }, offset: { type: 'integer' } }, ['captureId']),
];
export const pageHandlers = ctx => ({
  fetch_page: async ({ url }) => {
    const captured = await capturePage(url, ctx.store.dataDir, { signal: ctx.signal, transport: ctx.transport });
    return { ...captured, instruction: captured.extractable
      ? 'This response contains capture metadata, not page text. Read the captured text with read_page; fetching the same URL again does not read it. Follow nextOffset when more text is needed.'
      : 'This capture has no readable text. Use its note to choose another text source; repeating this fetch does not read the document.',
    ...(captured.extractable ? { nextAction: { tool: 'read_page', arguments: { captureId: captured.captureId, offset: 0 } } } : {}) };
  },
  read_page: ({ captureId, offset = 0 }) => readCapture(ctx.store.dataDir, captureId, offset),
});

export const TASK_FIELDS = { taskId: { type: 'string' }, protocolId: { type: 'string', minLength: 3 }, name: { type: 'string', minLength: 4 }, kind: { type: 'string', enum: [...KINDS] }, sourceUrl: { type: 'string' },
  summary: { type: 'string', minLength: 20 }, whyAgentTask: { type: 'string', minLength: 20 }, interfaceNote: { type: ['string', 'null'] } };
export const SWEEP_TOOLS = [
  fn('save_task', 'Record one protocol found in this area, or update it under the same taskId.', TASK_FIELDS),
  ...PAGE_TOOLS,
  fn('finish_area', 'Finish this area when further search is no longer useful. There is no minimum search count or required successful result; report actual coverage and limitations.', { summary: { type: 'string', minLength: 20 }, notReached: { type: 'array', items: { type: 'string' } },
    stopReason: { type: 'string', enum: ['saturated', 'budget_exhausted'] } }),
];

export function saveCandidate(state, args, extra = {}) {
  const s = state.search, problems = [];
  const prior = s.candidates[args.taskId];
  if (!/^[a-z][a-z0-9_]{2,60}$/.test(args.taskId)) problems.push('taskId must be snake_case ASCII, 3-61 characters');
  if (!/^https?:\/\/\S+$/.test(args.sourceUrl)) problems.push('sourceUrl must be an http(s) URL');
  if (!/^[a-z][a-z0-9_-]{2,100}$/.test(args.protocolId ?? '')) problems.push('protocolId must be a stable ASCII protocol identity, 3-101 characters');
  const dup = Object.values(s.candidates).find(c => c.taskId !== args.taskId && (c.protocolId ?? c.taskId) === args.protocolId);
  if (dup) problems.push(`that protocol is already recorded as ${dup.taskId}; update it under that taskId`);
  if (prior && (prior.protocolId ?? prior.taskId) !== args.protocolId) problems.push(`taskId ${args.taskId} already identifies protocol ${prior.protocolId ?? prior.taskId}; use a distinct taskId for a different protocol`);
  if (problems.length) throw new Error(problems.join('; '));
  if (prior && ['admitted', 'rejected'].includes(prior.status)) throw new Error(`${args.taskId} is already ${prior.status}; record a different protocol`);
  const foundInAreas = [...new Set([...(prior?.foundInAreas ?? []), prior?.foundIn, ...(extra.foundInAreas ?? []), extra.foundIn].filter(Boolean))];
  s.candidates[args.taskId] = { ...(prior ?? { foundAt: now(), origin: 'search' }), ...args, ...extra,
    ...(foundInAreas.length ? { foundIn: prior?.foundIn ?? extra.foundIn ?? foundInAreas[0], foundInAreas } : {}), status: 'recorded', updatedAt: now() };
  return { ok: true, taskId: args.taskId, updated: Boolean(prior), recorded: Object.keys(s.candidates).length };
}

export function saveAreaCandidate(state, area, args) {
  const focus = normalizeAreaFocus(area), prior = state.search.candidates[args.taskId];
  if (prior && prior.kind !== args.kind) throw new Error('a canonical protocol cannot change between interactive and static during a cross-area update; verify the original protocol or record a genuinely different protocol');
  if (focus.researchRole === 'game_world' && args.kind !== 'interactive') throw new Error('game_world discovery records actual interactive games, puzzles and simulated worlds; fixed questions and artifacts belong to support, not a relabeled game');
  const owned = Object.values(state.search.candidates).filter(candidate => candidate.foundIn === area.id).length;
  const limit = area.supportCandidateLimit ?? (area.researchRole === 'support' ? SUPPORT_CANDIDATE_LIMIT : Infinity);
  if (!prior && focus.researchRole === 'support' && owned >= limit) throw new Error(`this support area has recorded its maximum ${limit} distinct protocols; update an existing canonical protocol if needed, then finish_area. Do not create aliases or move office protocols into game_world areas`);
  const researchRole = prior?.researchRole ?? focus.researchRole;
  return saveCandidate(state, args, { foundIn: area.id,
    researchRole, supportDomain: researchRole === 'game_world' ? null : prior?.supportDomain ?? focus.supportDomain });
}

export async function planAreas(ctx) {
  const { store } = ctx, s = store.state.search, max = store.state.config.search.maxAreas;
  const result = await askOnce(ctx, { key: `${s.runId}/plan`, system: prompt('plan'), text: JSON.stringify({ maximumAreas: max,
    researchFocus: { minimumGameWorldAreaShare: 2 / 3, combinedDigitalInteractionAreas: 1, maximumSupportCandidatesPerArea: SUPPORT_CANDIDATE_LIMIT } }), tool: PLAN_TOOL,
    attempts: store.state.config.search.planTurns, maxTokens: store.state.config.search.planTokens, check: a => {
    return validateFocusedAreas(a.areas, { maxAreas: max }); } });
  s.areas = result.areas.map(a => ({ ...normalizeAreaFocus(a), status: 'pending' }));
  store.save();
  return s.areas;
}

export async function sweepArea(ctx, area) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search;
  if (!supportsSearch(ctx.profile)) throw new Error('Web search is unavailable for the connected provider');
  const focus = normalizeAreaFocus(area);
  area.checkpointInput ??= { area: { id: area.id, title: area.title, why: area.why, queries: area.queries,
    researchRole: focus.researchRole, supportDomain: focus.supportDomain },
    maximumNewCandidates: area.researchRole === 'support' ? area.supportCandidateLimit ?? SUPPORT_CANDIDATE_LIMIT : null,
    minimumSearches: 0, searchBudget: cfg.searchesPerArea,
    alreadyRecorded: Object.values(s.candidates).map(c => ({ taskId: c.taskId, protocolId: c.protocolId ?? c.taskId, name: c.name, kind: c.kind, sourceUrl: c.sourceUrl })) };
  const key = `${s.runId}/sweep-${area.id}`, kickoff = JSON.stringify(area.checkpointInput), currentSystem = prompt('discover');
  area.checkpointSystem = currentSystem;
  store.save();
  const result = await runAgent(ctx, { key, purpose: 'discovery sweep', system: currentSystem, kickoff,
    tools: SWEEP_TOOLS, maxTurns: cfg.sweepTurns, maxTokens: cfg.sweepTokens, searchBudget: cfg.searchesPerArea,
    handlers: { save_task: args => { const r = saveAreaCandidate(store.state, area, args); store.save(); return r; },
      ...pageHandlers(ctx), finish_area: (args, run) => {
        return { finish: finishArea(args, run) };
      } } });
  Object.assign(area, { status: 'done', summary: result.summary, notReached: result.notReached, stopReason: result.stopReason,
    reportedStopReason: result.reportedStopReason, budgetExhausted: result.budgetExhausted,
    searches: result.searches, searchResults: result.results, searchPerformed: result.searchPerformed,
    successfulSearchPerformed: result.successfulSearchPerformed, coverage: result.coverage, turns: result.turns,
    searchesRemaining: result.searchesRemaining, turnsRemaining: result.turnsRemaining,
    finishedAt: now() });
  store.save();
  return area;
}

export function finishArea(args, run) {
  const searchesRemaining = Math.max(0, run.budget.searchLimit - run.searches);
  const turnsRemaining = Math.max(0, run.budget.turnLimit - run.turn);
  const budgetExhausted = searchesRemaining === 0 || turnsRemaining === 0;
  const searchPerformed = run.searches > 0, successfulSearchPerformed = searchPerformed && run.searchResults > 0;
  const coverage = !searchPerformed ? 'not_searched' : successfulSearchPerformed ? 'search_results_recorded' : 'no_successful_results';
  return { ...args, reportedStopReason: args.stopReason,
    stopReason: ((args.stopReason === 'budget_exhausted' && !budgetExhausted) || (args.stopReason === 'saturated' && !successfulSearchPerformed)) ? 'model_finished' : args.stopReason,
    budgetExhausted, searches: run.searches, results: run.searchResults, turns: run.turn,
    searchPerformed, successfulSearchPerformed, coverage, searchesRemaining, turnsRemaining, queries: run.searchQueries ?? [] };
}

export function requireSearchProgress(run, minimum) {
  if (!run.searchResults) {
    const errors = (run.searchErrors ?? []).map(e => e.code ?? e);
    const message = `no successful web search results; inspect tool errors and retry: ${errors.join(', ')}`;
    if (run.searches >= run.budget.searchLimit || errors.some(code => /unavailable|unsupported|invalid_tool|not_enabled/i.test(code))) {
      throw new AgentError(message, errors.length ? 'tool_unavailable' : 'budget_exhausted', { key: run.key, resource: 'searches' });
    }
    throw new Error(message);
  }
  if (run.searches < minimum) throw new Error(`at least ${minimum} actual web searches are required before finishing; performed ${run.searches}`);
}
