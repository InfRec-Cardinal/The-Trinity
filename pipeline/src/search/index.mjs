import { uid, now } from '../core.mjs';
import { DEFAULT_SEARCH_CONFIG, prepareSearchScheduling } from '../store.mjs';
import { AgentError } from '../agent.mjs';
import { deriveSplit } from '../split.mjs';
import { resetFrom } from '../pipeline.mjs';
import { captureMeta } from '../capture.mjs';
import { planAreas, sweepArea, orderedResearchAreas, searchFocusSummary } from './discover.mjs';
import { auditDiscoveryCoverage } from './coverage.mjs';
import { specifyTask, SPECIFICATION_VERSION, isCurrentAdmission, checkSpecification, specificationArgumentProblems } from './specify.mjs';
import { SEARCH_POLICY_VERSION, policyWidensFrom, checkInputScope } from './schema.mjs';
import { reviewSpec, reviewScopeExclusion, checkReview, collectContextualEvidence } from './review.mjs';
import { growTaxonomy } from './taxonomy.mjs';
import { deriveGroups, assembleLibrary } from './library.mjs';
import { auditLineage } from './lineage.mjs';
import { supplementGap } from './supplement.mjs';
import { callModel as defaultTransport } from '../model.mjs';

export { SEARCH_POLICY_VERSION } from './schema.mjs';
export const newSearchState = () => ({ policyVersion: SEARCH_POLICY_VERSION, specificationVersion: SPECIFICATION_VERSION, runId: uid('search'), status: 'idle', phase: null,
  startedAt: null, finishedAt: null, error: null, areas: [], candidates: {}, specs: {}, reviews: {}, taxonomy: null,
  lineageAudit: null, coverageAudit: null, focus: null, groups: null, supplements: [], supplementBatch: null, agentUsage: {}, budgetGrants: {}, budgets: [] });
export const admittedSpecs = state => Object.values(state.search.candidates).filter(c => c.status === 'admitted'
  && isCurrentAdmission(state.search.specs[c.taskId], state.search.reviews[c.taskId])).map(c => state.search.specs[c.taskId]);
const feedbackOf = review => review && ({ reason: review.reason, fields: (review.fields ?? []).filter(f => f.verdict !== 'supported'),
  scope: review.scope, gate: review.gate, design: review.design, lineage: review.lineage, authority: review.authority });

function reusableSources(store, search, candidate, specification) {
  const sources = new Map();
  const add = row => {
    const meta = captureMeta(store.dataDir, row?.captureId);
    if (meta?.extractable) sources.set(meta.captureId, { captureId: meta.captureId, url: meta.url });
  };
  for (const source of [...(specification?.sources ?? []), ...(candidate.reusableSources ?? [])]) add(source);
  const attempts = Math.max(candidate.activeAttempt ?? 0, candidate.attempts ?? 0, specification?.attempt ?? 0, 1);
  for (const version of [3, 4]) for (let attempt = 1; attempt <= attempts; attempt++) {
    const checkpoint = store.loadAgent(`${search.runId}/spec-${candidate.taskId}-${attempt}-v${version}`);
    const results = [...(checkpoint?.turns ?? []).filter(turn => turn.role === 'tool').flatMap(turn => turn.results ?? []),
      ...(checkpoint?.pending?.results ?? [])];
    for (const result of results) {
      try { add(typeof result.output === 'string' ? JSON.parse(result.output) : result.output); } catch {}
    }
  }
  return [...sources.values()];
}

function reusableSubmission(store, search, candidate, submitName, purpose) {
  const attempts = Math.max(candidate.activeAttempt ?? 0, candidate.attempts ?? 0, 1);
  for (const version of [4, 3]) for (let attempt = attempts; attempt >= 1; attempt--) {
    const checkpoint = store.loadAgent(`${search.runId}/${purpose}-${candidate.taskId}-${attempt}-v${version}`);
    for (const turn of [...(checkpoint?.turns ?? [])].reverse()) {
      if (turn.role !== 'assistant') continue;
      for (const block of [...(turn.content ?? [])].reverse()) {
        if (block.type !== 'tool_use' || block.name !== submitName || !block.input || typeof block.input !== 'object' || Array.isArray(block.input) || !Object.keys(block.input).length) continue;
        const submission = structuredClone(block.input), sourceCallId = `${checkpoint.key}:${block.id}`;
        return { sourceCallId, submission, validationErrors: [] };
      }
    }
  }
  return null;
}

export function prepareSpecificationRevision(store) {
  const s = store.state.search;
  if (s.specificationVersion === SPECIFICATION_VERSION) return null;
  const report = { from: s.specificationVersion ?? 3, to: SPECIFICATION_VERSION, retainedAdmissions: 0, reusedSpecifications: 0, restartedTasks: 0, reusedDrafts: 0 };
  s.specificationHistory ??= [];
  for (const c of Object.values(s.candidates)) {
    const spec = s.specs[c.taskId], review = s.reviews[c.taskId];
    if (spec?.schemaVersion === SPECIFICATION_VERSION || c.specificationInputs?.[`${SPECIFICATION_VERSION}:${c.activeAttempt ?? 1}`]) continue;
    if (!spec && !['specifying', 'admitted', 'rejected'].includes(c.status)) continue;
    s.specificationHistory.push({ schemaVersion: spec?.schemaVersion ?? s.specificationVersion ?? 3, migratedTo: SPECIFICATION_VERSION, taskId: c.taskId, migratedAt: now(),
      status: c.status, attempts: c.attempts ?? 0, activeAttempt: c.activeAttempt ?? null,
      specification: structuredClone(spec ?? null), review: structuredClone(review ?? null) });
    c.reusableSources = reusableSources(store, s, c, spec);
    let reusable = false;
    if ([3, 4].includes(spec?.schemaVersion) && !spec.outcome) {
      try { reusable = !checkSpecification(spec, c.kind, store.dataDir).length; }
      catch {}
    }
    if (reusable) {
      const promoted = { ...spec, schemaVersion: SPECIFICATION_VERSION, migratedFromVersion: spec.schemaVersion };
      s.specs[c.taskId] = promoted; report.reusedSpecifications++;
      let compatibleAdmission = false;
      if (c.status === 'admitted' && review?.schemaVersion === spec.schemaVersion && review.specAt === spec.at && review.decision === 'admit') {
        try { compatibleAdmission = !checkReview(review, c.kind, promoted, collectContextualEvidence(promoted, store.dataDir)).length; }
        catch {}
      }
      if (compatibleAdmission) {
        s.reviews[c.taskId] = { ...review, schemaVersion: SPECIFICATION_VERSION, migratedFromVersion: review.schemaVersion };
        report.retainedAdmissions++; continue;
      }
      delete s.reviews[c.taskId]; c.status = 'specifying'; c.activeAttempt = spec.attempt; c.attempts = Math.max(0, spec.attempt - 1);
      c.reusableReviewDraft = reusableSubmission(store, s, c, 'submit_review', 'review');
    } else {
      delete s.specs[c.taskId]; delete s.reviews[c.taskId];
      const draft = reusableSubmission(store, s, c, 'submit_specification', 'spec');
      if (draft) {
        try { draft.validationErrors = specificationArgumentProblems(draft.submission, c.kind, store.dataDir, { reuseDenseEvidence: true }); }
        catch { draft.validationErrors = ['The draft needs valid required fields and captured source facts before admission.']; }
        c.reusableDraft = draft; report.reusedDrafts++;
      }
      c.status = 'recorded'; c.attempts = 0; c.activeAttempt = null; report.restartedTasks++;
    }
    delete c.admittedAt; delete c.rejectedReason;
  }
  s.specificationVersion = SPECIFICATION_VERSION; store.save();
  return report;
}

export async function specifyAndReview(ctx, taskId) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search, c = s.candidates[taskId];
  if (c.status === 'admitted' && isCurrentAdmission(s.specs[taskId], s.reviews[taskId])) return c.status;
  if (c.status === 'rejected' && s.specs[taskId]?.schemaVersion === SPECIFICATION_VERSION && s.reviews[taskId]?.schemaVersion === SPECIFICATION_VERSION) return c.status;
  if (['admitted', 'rejected'].includes(c.status)) { c.status = 'recorded'; c.attempts = 0; c.activeAttempt = null; }
  let attempt = c.activeAttempt ?? (c.attempts ?? 0) + 1;
  let feedback = feedbackOf(s.reviews[taskId]);
  for (; attempt <= cfg.specifyAttempts; attempt++) {
    c.activeAttempt = attempt; c.status = 'specifying'; store.save();
    let spec = s.specs[taskId];
    if (!spec || spec.attempt !== attempt || spec.schemaVersion !== SPECIFICATION_VERSION) spec = await specifyTask(ctx, c, attempt, feedback);
    let review = s.reviews[taskId];
    const wrongReviewMode = spec.outcome === 'scope_exclusion' ? review?.outcome !== 'scope_exclusion_review' : review?.outcome === 'scope_exclusion_review';
    if (!review || review.attempt !== attempt || review.specAt !== spec.at || review.schemaVersion !== SPECIFICATION_VERSION || wrongReviewMode) review = spec.outcome === 'scope_exclusion'
      ? await reviewScopeExclusion(ctx, c, spec, attempt) : await reviewSpec(ctx, c, spec, attempt);
    c.attempts = attempt; c.activeAttempt = null;
    if (spec.outcome === 'scope_exclusion' && review.verdict === 'supported') {
      c.status = 'rejected'; c.rejectedReason = review.reason; store.save(); return 'rejected';
    }
    if (spec.outcome !== 'scope_exclusion' && isCurrentAdmission(spec, review)) { c.status = 'admitted'; c.admittedAt = now(); store.save(); return 'admitted'; }
    feedback = feedbackOf(review); store.save();
  }
  c.status = 'rejected'; c.rejectedReason = feedback?.reason ?? 'not admitted'; store.save();
  return 'rejected';
}

export async function runSpecificationTasks(ctx, { processTask = specifyAndReview, candidateIds = null, targetDirection = null } = {}) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search;
  if (cfg.specifyConcurrency == null) { cfg.specifyConcurrency = DEFAULT_SEARCH_CONFIG.specifyConcurrency; store.save(); }
  const concurrency = cfg.specifyConcurrency;
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 10) throw new Error('specifyConcurrency must be an integer from 1 to 10');
  const selected = candidateIds == null ? Object.values(s.candidates)
    : [...new Set(candidateIds)].map(id => s.candidates[id]).filter(Boolean);
  const pending = selected.filter(c => ['recorded', 'specifying'].includes(c.status)
    && !s.supplements.some(record => record.status === 'searching' && record.candidates.includes(c.taskId)));
  const controller = new AbortController();
  const signal = ctx.signal ? AbortSignal.any([ctx.signal, controller.signal]) : controller.signal;
  const workerCtx = { ...ctx, signal };
  let next = 0, failure = null;
  const assign = c => {
    const direction = targetDirection ?? c.targetDirection;
    if (c.status === 'admitted' && direction && s.taxonomy?.nodes.some(n => n.id === direction)) {
      s.taxonomy.assignments[c.taskId] = direction; store.save();
    }
  };
  const worker = async () => {
    while (!signal.aborted && next < pending.length) {
      const c = pending[next++];
      try {
        ctx.emit?.('search_specification_start', { runId: s.runId, taskId: c.taskId, concurrency });
        const outcome = await processTask(workerCtx, c.taskId);
        assign(c);
        ctx.emit?.('search_specification_end', { runId: s.runId, taskId: c.taskId, status: outcome });
      } catch (error) {
        const interrupted = signal.aborted;
        if (!failure) { failure = error; controller.abort(error); }

        try {
          store.save(); ctx.emit?.('search_specification_end', { runId: s.runId, taskId: c.taskId,
            status: interrupted ? 'stopped' : 'error', errorCode: interrupted ? 'stopped' : error.code ?? 'search_error' });
        } catch {}
        return;
      }
    }
  };
  await Promise.allSettled(Array.from({ length: Math.min(concurrency, pending.length) }, () => worker()));
  if (failure) throw failure;
  if (signal.aborted) throw new AgentError('stopped by user', 'stopped');

  if (targetDirection) for (const c of selected) assign(c);
  return selected;
}

export function rebuildLibrary(store) {
  const { state } = store;
  state.search.groups = deriveGroups(admittedSpecs(state), state.search.lineageAudit);
  state.library = assembleLibrary(state);
  state.split = deriveSplit(state.library, state.config?.split);
  store.save();
  return state.split;
}

async function finishSupplementCandidates(ctx, record) {
  const { store } = ctx;
  await runSpecificationTasks(ctx, { candidateIds: record.candidates, targetDirection: record.direction });
  await auditLineage(ctx); rebuildLibrary(store);
  record.status = 'done'; record.finishedAt = now(); store.save();
}

async function supplementRounds(ctx) {
  const { store } = ctx, state = store.state, s = state.search, cfg = state.config.search;

  for (const record of s.supplements) if (record.status === 'searching') {
    const direction = state.library.directions.find(d => d.id === record.direction);
    await supplementGap(ctx, { direction: record.direction, label: direction?.label ?? record.direction,
      track: direction?.track ?? 'benchmarks', need: record.need }, record.round, 'search');
    await finishSupplementCandidates(ctx, record);
  }
  for (const record of s.supplements) if (record.status === 'discovered') await finishSupplementCandidates(ctx, record);
  if (!s.supplementBatch) {
    const start = Math.max(0, ...s.supplements.map(x => x.round)) + 1;
    const rounds = s.nextSupplementRounds ?? cfg.supplementRounds;
    delete s.nextSupplementRounds;
    s.supplementBatch = { start, end: start + rounds - 1 }; store.save();
  }
  for (let round = s.supplementBatch.start; round <= s.supplementBatch.end; round++) {
    const gaps = [...new Map(state.split.gaps.map(g => [g.direction, g])).values()]; if (!gaps.length) break;
    for (const gap of gaps) {
      if (s.supplements.some(x => x.round === round && x.direction === gap.direction && x.status === 'done')) continue;
      await supplementGap(ctx, gap, round, 'search');
      const record = s.supplements.find(x => x.round === round && x.direction === gap.direction);
      await finishSupplementCandidates(ctx, record);
    }
  }
  s.supplementBatch = null; store.save();
}

function migrateSearch(s) {
  if (s.policyVersion === SEARCH_POLICY_VERSION) return;
  s.specs ??= {}; s.reviews ??= {};
  s.policyHistory ??= [];

  if (policyWidensFrom(s.policyVersion)) {
    const narrowed = Object.values(s.candidates).filter(c => c.status === 'admitted'
      && checkInputScope(s.specs[c.taskId]?.inputScope).length);
    if (!narrowed.length) {
      s.policyHistory.push({ policyVersion: s.policyVersion ?? null, migratedAt: now(), widenedTo: SEARCH_POLICY_VERSION,
        retainedAdmissions: Object.values(s.candidates).filter(c => c.status === 'admitted').length });
      s.policyVersion = SEARCH_POLICY_VERSION;
      return;
    }
  }
  s.policyHistory.push({ policyVersion: s.policyVersion ?? null, migratedAt: now(), taxonomy: s.taxonomy, lineageAudit: s.lineageAudit,
    groups: s.groups, supplements: s.supplements, supplementBatch: s.supplementBatch });
  for (const c of Object.values(s.candidates)) {
    if (isCurrentAdmission(s.specs[c.taskId], s.reviews[c.taskId])) continue;
    c.admissionHistory ??= [];
    c.admissionHistory.push({ policyVersion: s.policyVersion ?? null, status: c.status, attempts: c.attempts, activeAttempt: c.activeAttempt,
      admittedAt: c.admittedAt, rejectedReason: c.rejectedReason, targetDirection: c.targetDirection });
    c.protocolId ??= c.taskId; c.attempts = 0; c.activeAttempt = null; c.status = 'recorded';
    delete c.admittedAt; delete c.rejectedReason; delete c.targetDirection;
  }

  s.specs ??= {}; s.reviews ??= {}; s.taxonomy = null; s.lineageAudit = null; s.groups = null;
  s.supplements = []; s.supplementBatch = null;
  for (const area of s.areas) if (area.status !== 'done') delete area.checkpointInput;
  s.policyVersion = SEARCH_POLICY_VERSION;
}

export async function runDiscoveryAreas(ctx, { sweep = sweepArea, retryAreaId = null } = {}) {
  const { store } = ctx, s = store.state.search;
  const cfg = store.state.config.search;
  if (cfg.areaConcurrency == null) { cfg.areaConcurrency = 3; store.save(); }
  const concurrency = cfg.areaConcurrency;
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 8) throw new Error('areaConcurrency must be an integer from 1 to 8');
  const pending = orderedResearchAreas(s.areas.filter(area => area.status !== 'done'));
  const retryIndex = pending.findIndex(area => area.id === retryAreaId);
  const retryArea = retryIndex >= 0 ? pending.splice(retryIndex, 1)[0] : null;
  if (retryArea) pending.unshift(retryArea);
  const retryCheckpoint = retryArea ? store.loadAgent(`${s.runId}/sweep-${retryArea.id}`) : null;
  const retryTurn = retryCheckpoint?.turn ?? 0;
  const controller = new AbortController();
  const signal = ctx.signal ? AbortSignal.any([ctx.signal, controller.signal]) : controller.signal;
  const workerCtx = { ...ctx, signal };
  let releaseGate, recoveryConfirmed = !retryArea;
  const recoveryGate = new Promise(resolve => { releaseGate = resolve; });
  if (recoveryConfirmed) releaseGate(true);
  const confirmRecovery = () => {
    if (recoveryConfirmed || signal.aborted) return;
    recoveryConfirmed = true; releaseGate(true);
    ctx.emit?.('search_parallel_resume', { runId: s.runId, areaId: retryArea.id, concurrency });
  };
  const interruptRecovery = () => releaseGate(false);
  signal.addEventListener('abort', interruptRecovery, { once: true });
  if (signal.aborted) interruptRecovery();
  let next = 0, failure = null;
  const worker = async index => {
    if (index > 0 && !recoveryConfirmed) await recoveryGate;
    while (!signal.aborted && next < pending.length) {

      const area = pending[next++];
      try {
        area.status = 'running'; area.startedAt ??= now(); delete area.errorCode; delete area.error;
        store.save(); ctx.emit?.('search_area_start', { runId: s.runId, areaId: area.id, concurrency });
        const areaCtx = area === retryArea ? { ...workerCtx, onTurn: async (event, run) => {
          await workerCtx.onTurn?.(event, run);
          const newSession = retryCheckpoint?.sessionId && run.sessionId && run.sessionId !== retryCheckpoint.sessionId;
          if (event.phase === 'turn' && run.key === `${s.runId}/sweep-${area.id}`
            && (run.turn > retryTurn || (newSession && run.turn > 0))) confirmRecovery();
        } } : workerCtx;
        await sweep(areaCtx, area);
        area.status = 'done'; area.finishedAt ??= now(); store.save();
        ctx.emit?.('search_area_end', { runId: s.runId, areaId: area.id, status: area.status });
        if (area === retryArea) confirmRecovery();
      } catch (error) {
        const interrupted = signal.aborted;
        if (!failure) { failure = error; controller.abort(error); }
        area.status = interrupted ? 'stopped' : 'error';
        area.errorCode = interrupted ? 'stopped' : error.code ?? 'search_error';
        area.error = `Discovery interrupted (${area.errorCode}); resume this area's saved agent.`;
        try {
          store.save(); ctx.emit?.('search_area_end', { runId: s.runId, areaId: area.id, status: area.status, errorCode: area.errorCode });
        } catch {}
        return;
      }
    }
  };
  try { await Promise.allSettled(Array.from({ length: Math.min(concurrency, pending.length) }, (_, index) => worker(index))); }
  finally { signal.removeEventListener('abort', interruptRecovery); }
  if (failure) throw failure;
  if (signal.aborted) throw new AgentError('stopped by user', 'stopped');
  return s.areas;
}

export async function runSearch(ctx) {
  ctx = { ...ctx, callModel: ctx.callModel ?? defaultTransport };
  const { store } = ctx, state = store.state;
  const schedulingRevision = prepareSearchScheduling(store);
  if (schedulingRevision) ctx.emit?.('search_scheduling_revision', schedulingRevision);
  state.config.search.minSearchesPerArea = 0;
  state.config.search.maxAreas = Math.min(state.config.search.maxAreas ?? 15, 15);
  state.config.search.coverageTurns ??= 12;
  state.config.search.coverageTokens ??= 8000;
  state.config.search.maxRepairAreas ??= 3;
  if (!state.search || (state.search.status === 'done' && state.search.policyVersion === SEARCH_POLICY_VERSION)) {
    state.search = newSearchState(); state.library = null; resetFrom(state, 'split');
  }
  const s = state.search;
  if (s.policyVersion !== SEARCH_POLICY_VERSION && !policyWidensFrom(s.policyVersion)) { state.library = null; resetFrom(state, 'split'); }
  migrateSearch(s); s.agentUsage ??= {}; s.budgetGrants ??= {};
  const specificationRevision = prepareSpecificationRevision(store);
  if (specificationRevision) ctx.emit?.('search_specification_revision', { runId: s.runId, ...specificationRevision });
  const retryAreaId = s.status === 'error' && s.phase === 'discover'
    ? s.areas.find(area => area.status === 'error' && s.activeAgentKey === `${s.runId}/sweep-${area.id}`)?.id : null;
  const outerOnTurn = ctx.onTurn;
  ctx = { ...ctx, agentBudgetOverrides: s.budgetGrants, onTurn: async (event, run) => {
    s.agentUsage[run.key] = { key: run.key, purpose: run.purpose, turns: run.turn,
      searches: run.searches, searchResults: run.searchResults ?? 0, usage: run.usage, budget: run.budget,
      searchErrors: run.searchErrors ?? [], status: run.status };
    s.focus = searchFocusSummary(s);
    store.save(); await outerOnTurn?.(event, run);
  } };
  resetFrom(state, 'analysis');
  s.status = 'running'; s.startedAt ??= now(); s.error = null; s.errorCode = null; s.activeAgentKey = null; store.save();
  ctx.emit?.('search_start', { runId: s.runId, resumed: Boolean(s.areas.length) });
  try {
    if (!s.areas.length) { s.phase = 'plan'; store.save(); await planAreas(ctx); }
    s.phase = 'discover'; store.save();

    await runDiscoveryAreas(ctx, { retryAreaId });
    s.phase = 'coverage'; store.save();
    await auditDiscoveryCoverage(ctx);
    s.phase = 'discover'; store.save();
    await runDiscoveryAreas(ctx);
    s.focus = searchFocusSummary(s); store.save();
    s.phase = 'specify'; store.save();
    await runSpecificationTasks(ctx);
    s.focus = searchFocusSummary(s); store.save();
    if (!admittedSpecs(state).length) throw new Error('no candidate was admitted; nothing to organise');
    s.phase = 'taxonomy'; store.save();
    if (!s.taxonomy || Object.values(s.candidates).some(c => c.status === 'admitted' && !s.taxonomy.assignments[c.taskId])) await growTaxonomy(ctx);
    s.phase = 'lineage'; store.save(); await auditLineage(ctx);
    s.phase = 'split'; store.save(); rebuildLibrary(store);
    s.phase = 'supplement'; store.save(); await supplementRounds(ctx);
    const gaps = state.split.gaps, errors = state.split.errors;
    s.status = gaps.length || errors.length ? 'incomplete' : 'done'; s.phase = s.status;
    if (s.status === 'incomplete') { s.errorCode = 'library_incomplete'; s.error = `${gaps.length} split gap(s), ${errors.length} error(s) remain after the supplemental search budget; progress is saved`; }
  } catch (error) {
    const failure = ctx.signal?.aborted ? new AgentError('stopped by user', 'stopped', { key: error.agentKey ?? error.key }) : error;
    s.status = failure.code === 'stopped' ? 'stopped' : ['budget_exhausted', 'provider_quota'].includes(failure.code) ? failure.code : 'error';
    s.errorCode = failure.code ?? 'search_error'; s.activeAgentKey = failure.agentKey ?? null;
    s.error = String(failure.message ?? failure).slice(0, 500); throw failure;
  } finally { s.focus = searchFocusSummary(s); s.finishedAt = now(); store.save(); ctx.emit?.('search_end', { runId: s.runId, status: s.status }); }
  return { status: s.status, runId: s.runId, tasks: state.library.tasks.length, directions: state.library.directions.length,
    split: state.split.counts, gaps: state.split.gaps.length };
}
