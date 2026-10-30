import {modelCall, tokenSummary} from '../../harness/src/metrics.mjs';
import { assert, now, uid } from './core.mjs';
import { createHash } from 'node:crypto';
import { STOP, resolveProfile, canonicalModel, publicAssistantContent } from './model.mjs';

export class AgentError extends Error {
  constructor(message, code, details = {}) {
    super(message); this.name = 'AgentError'; this.code = code; Object.assign(this, details);
    if (details.key) this.agentKey = details.key;
  }
}

const stable = value => Array.isArray(value) ? value.map(stable) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(k => [k, stable(value[k])])) : value;
const fingerprint = value => createHash('sha256').update(JSON.stringify(stable(value))).digest('hex');
const cleanMessage = (message, apiKey) => String(message ?? '').split(apiKey).join('[redacted]')
  .replace(/\b(?:sk|ak|key)-[A-Za-z0-9_-]{12,}\b/g, '[redacted]').slice(0, 1500);
const truncationFeedback = maxTokens => `The response reached its ${maxTokens}-token output ceiling and was truncated. `
  + 'Its local tool calls cannot be executed or accepted, even when partial arguments look valid. '
  + 'Retry with a shorter, complete JSON tool submission, not an empty object or a continuation fragment. '
  + 'Keep all required fields and necessary evidence; use concise statements, quote each source claim once, '
  + 'and reference those claims elsewhere when the schema supports references. Remove repeated quotations and explanations.';
const NO_PROGRESS_LIMIT = 3;
const nativeSearchProgress = blocks => (blocks ?? []).some(block => block?.type === 'server_tool_use' && ['web_search', 'openrouter:web_search'].includes(block.name)
  || block?.type === 'web_search_tool_result');
const captureIdFromOutput = output => {
  try {
    const value = typeof output === 'string' ? JSON.parse(output) : Array.isArray(output)
      ? JSON.parse(output.find(block => block?.type === 'text')?.text ?? 'null') : output;
    return value?.ok !== false && typeof value?.captureId === 'string' && value.captureId.trim() ? value.captureId : null;
  } catch { return null; }
};
const repeatedCaptureFeedback = captureId => `This capture ${captureId} was already fetched successfully in this session. `
  + 'fetch_page returns capture metadata, not the source text. Repeating the same capture does not add research evidence. '
  + `Use read_page with captureId ${captureId} and offset 0 to inspect its text, then read later offsets only if needed. `
  + 'If it is not extractable, try a different source. Otherwise use the saved evidence and submit when adequately supported.';

function historicalCaptureProgress(turns, schemas) {
  const outputs = new Map();
  for (const turn of turns ?? []) if (turn.role === 'tool') for (const result of turn.results ?? []) outputs.set(result.id, result.output);
  const ids = new Set();
  let consecutive = 0, duplicateInSuffix = false;
  for (const turn of turns ?? []) {
    if (turn.role !== 'assistant') continue;
    const blocks = turn.content ?? [], calls = blocks.filter(block => block?.type === 'tool_use' && Object.hasOwn(schemas, block.name));
    let progress = nativeSearchProgress(blocks) || calls.some(call => call.name !== 'fetch_page');
    let repeated = false, unfinished = false;
    for (const call of calls.filter(call => call.name === 'fetch_page')) {
      if (!outputs.has(call.id)) { unfinished = true; continue; }
      const id = captureIdFromOutput(outputs.get(call.id));
      if (!id) progress = true;
      else if (ids.has(id)) repeated = true;
      else { ids.add(id); progress = true; }
    }
    if (unfinished && !progress) continue;
    if (progress) { consecutive = 0; duplicateInSuffix = false; }
    else { consecutive++; duplicateInSuffix ||= repeated; }
  }
  return { ids: [...ids], consecutive, duplicateInSuffix };
}

function checkpointSafe(value, apiKey) {
  if (typeof value === 'string') return value.split(apiKey).join('[redacted]');
  if (Array.isArray(value)) return value.filter(v => !['thinking', 'redacted_thinking'].includes(v?.type)).map(v => checkpointSafe(v, apiKey));
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).filter(([k]) => !/^(api_?key|authorization|access_?token|thinking|reasoning)$/i.test(k))
    .map(([k, v]) => [k, checkpointSafe(v, apiKey)]));
}

export const fn = (name, description, properties, required = Object.keys(properties)) =>
  ({ name, description, parameters: { type: 'object', properties, required, additionalProperties: false } });

export function checkArgs(schema, value, path = 'arguments') {
  const problems = [];
  const visit = (s, v, p) => {
    if (!s) return;
    const types = [].concat(s.type ?? []);
    const typeOf = v === null ? 'null' : Array.isArray(v) ? 'array' : Number.isInteger(v) ? 'integer' : typeof v;
    if (types.length && !types.some(t => t === typeOf || (t === 'number' && typeOf === 'integer'))) { problems.push(`${p} must be ${types.join(' or ')}`); return; }
    if (s.enum && !s.enum.includes(v)) problems.push(`${p} must be one of ${s.enum.join(', ')}`);
    if (typeOf === 'string' && s.minLength && v.trim().length < s.minLength) problems.push(`${p} is too short`);
    if (typeOf === 'string' && s.maxLength !== undefined && [...v].length > s.maxLength) problems.push(`${p} has ${[...v].length} characters; maximum is ${s.maxLength}. Shorten this field and resubmit`);
    if (typeOf === 'string' && s.pattern && !new RegExp(s.pattern).test(v)) problems.push(`${p} must match the case-sensitive pattern ${s.pattern}`);
    if (typeOf === 'array') {
      if (s.minItems && v.length < s.minItems) problems.push(`${p} needs at least ${s.minItems} item(s)`);
      if (s.maxItems && v.length > s.maxItems) problems.push(`${p} allows at most ${s.maxItems} item(s)`);
      v.forEach((item, i) => visit(s.items, item, `${p}[${i}]`));
    }
    if (typeOf === 'object') {
      for (const key of s.required ?? []) if (!(key in v)) problems.push(`${p}.${key} is required`);
      for (const [key, item] of Object.entries(v)) {
        if (s.properties?.[key]) visit(s.properties[key], item, `${p}.${key}`);
        else if (s.additionalProperties === false) problems.push(`${p}.${key} is not allowed`);
      }
    }
  };
  visit(schema, value, path);
  return problems;
}

async function executeAgent(ctx, spec) {
  const { key, system, kickoff, tools, handlers, maxTurns = 120, searchBudget = 0, maxTokens = 12000 } = spec;
  assert(ctx.apiKey, 'Set the provider API key before running a model stage');
  assert(Number.isInteger(maxTurns) && maxTurns > 0 && maxTurns <= 10000, 'maxTurns must be an integer from 1 to 10000');
  assert(Number.isInteger(searchBudget) && searchBudget >= 0 && searchBudget <= 10000, 'searchBudget must be an integer from 0 to 10000');
  assert(Number.isInteger(maxTokens) && maxTokens > 0 && maxTokens <= 128000, 'maxTokens must be an integer from 1 to 128000');
  const grant = ctx.agentBudgetOverrides?.get?.(key) ?? ctx.agentBudgetOverrides?.[key] ?? {};
  const allowed = { turnLimit: Math.max(maxTurns, grant.turnLimit ?? 0), searchLimit: Math.max(searchBudget, grant.searchLimit ?? 0),
    maxTokens: Math.max(maxTokens, grant.maxTokens ?? 0) };
  assert(Number.isInteger(allowed.turnLimit) && allowed.turnLimit <= 10000, 'granted turnLimit must be an integer at most 10000');
  assert(Number.isInteger(allowed.searchLimit) && allowed.searchLimit <= 10000, 'granted searchLimit must be an integer at most 10000');
  assert(Number.isInteger(allowed.maxTokens) && allowed.maxTokens <= 128000, 'granted maxTokens must be an integer at most 128000');
  const schemas = Object.fromEntries(tools.map(t => [t.name, t.parameters]));
  const registeredNames = Object.keys(schemas);
  const registeredCall = calls => (calls ?? []).some(call => Object.hasOwn(schemas, call.name));
  const fetchOnlyCalls = (calls, badCalls, nativeProgress = false) => !nativeProgress && !registeredCall(badCalls)
    && (calls ?? []).some(call => call.name === 'fetch_page' && Object.hasOwn(schemas, call.name))
    && !(calls ?? []).some(call => Object.hasOwn(schemas, call.name) && call.name !== 'fetch_page');
  const registryFeedback = () => `Only these registered tools are available in this task: ${registeredNames.join(', ') || '(none)'}. `
    + 'Call them directly with complete arguments. Use the provided research and repair tools to resolve outstanding work. '
    + 'Complete the task with an accepted final submission; a text response alone does not submit a result.';
  const provider = resolveProfile(ctx.profile);
  const contractHash = fingerprint({ system, kickoff, tools, model: canonicalModel(provider.model), effort: provider.effort, version: spec.checkpointVersion ?? 1 });
  let run = ctx.store.loadAgent(key);
  let invalidated = null;
  if (run && run.contractHash !== contractHash) {
    const archiveKey = `${key.slice(0, 100)}/archive-${uid('contract')}`, previousUsage = {};
    for (const field of ['input', 'output', 'cachedInput', 'cacheCreationInput']) previousUsage[field] = (run.usage?.[field] ?? 0) + (run.invalidated?.previousUsage?.[field] ?? 0);
    invalidated = { previousStatus: run.status, previousTurns: (run.turn ?? 0) + (run.invalidated?.previousTurns ?? 0),
      previousSearches: (run.searches ?? 0) + (run.invalidated?.previousSearches ?? 0),
      previousSearchResults: (run.searchResults ?? 0) + (run.invalidated?.previousSearchResults ?? 0), previousUsage,
      archiveKey, at: now() };
    ctx.store.saveAgent(checkpointSafe({ ...run, key: archiveKey, originalKey: key, archivedAt: now(), replacedBy: key }, ctx.apiKey));
    run = null;
  }
  const persist = () => ctx.store.saveAgent(checkpointSafe(run, ctx.apiKey));
  const cachedDone = run?.status === 'done';
  if (!run) run = { key, checkpointVersion: 2, contractHash, purpose: spec.purpose ?? null, status: 'running', profile: ctx.profile, sessionId: uid('session'),
    turns: [{ role: 'user', text: kickoff }], turn: 0, searches: 0, searchAttempts: 0, searchResults: 0, searchErrors: [], searchQueries: [],
    usage: { input: 0, output: 0, cachedInput: 0, cacheCreationInput: 0 }, startedAt: now(), log: [], ...(invalidated ? { invalidated } : {}),
    budget: { ...allowed, extensions: 0 }, noProgressConsecutive: 0, noProgressTotal: 0, requireToolChoice: false,
    captureProgressVersion: 1, fetchedCaptureIds: [] };
  else {
    run.searchResults ??= 0; run.searchErrors ??= []; run.searchQueries ??= []; run.searchAttempts ??= run.searches;
    run.budget ??= { ...allowed, extensions: 0 };
    const increased = allowed.turnLimit > run.budget.turnLimit || allowed.searchLimit > run.budget.searchLimit || allowed.maxTokens > run.budget.maxTokens;
    if (increased) run.budget.extensions++;
    run.budget.turnLimit = Math.max(run.budget.turnLimit, allowed.turnLimit);
    run.budget.searchLimit = Math.max(run.budget.searchLimit, allowed.searchLimit); run.budget.maxTokens = Math.max(run.budget.maxTokens, allowed.maxTokens);
    if (increased && !cachedDone) run.pendingBudgetNotice = { ...run.budget, grantedAt: now() };
  }

  if (!cachedDone && !Number.isSafeInteger(run.noProgressConsecutive)) {
    let consecutive = 0;
    for (const turn of [...run.turns].reverse()) {
      if (turn.role !== 'assistant') continue;
      const blocks = turn.content ?? [];
      if (registeredCall(blocks.filter(block => block.type === 'tool_use')) || nativeSearchProgress(blocks)) break;
      consecutive++;
    }
    run.noProgressConsecutive = consecutive;
    run.noProgressTotal = consecutive;
    if (consecutive && run.lastStopReason === STOP.done) {
      run.requireToolChoice = Boolean(tools.length);
      run.pendingToolRecovery = { source: 'legacy_resume', afterTurn: run.turn };
      run.legacyRecoveryRequestPending = true;
    }
  }
  run.noProgressTotal ??= 0;
  if (!cachedDone && run.captureProgressVersion !== 1) {
    const historical = historicalCaptureProgress(run.turns, schemas), ids = new Set(historical.ids);
    run.captureProgressVersion = 1;
    if (historical.duplicateInSuffix) {
      run.noProgressConsecutive = Math.max(run.noProgressConsecutive, historical.consecutive);
      run.noProgressTotal = Math.max(run.noProgressTotal, historical.consecutive);
    }
    if (run.pending) {
      const pending = run.pending, blocks = [...run.turns].reverse().find(turn => turn.role === 'assistant')?.content ?? [];
      pending.fetchProgressOnly = fetchOnlyCalls(pending.calls, pending.badCalls, nativeSearchProgress(blocks));
      pending.progressBefore = run.noProgressConsecutive;
      pending.fetchProgress = false;
      pending.repeatedCaptures = [];
      for (const result of pending.results ?? []) {
        if (pending.calls.find(call => call.id === result.id)?.name !== 'fetch_page') continue;
        const id = captureIdFromOutput(result.output);
        if (!id) pending.fetchProgress = true;
        else if (ids.has(id)) pending.repeatedCaptures.push(id);
        else { ids.add(id); pending.fetchProgress = true; }
      }
    }
    run.fetchedCaptureIds = [...ids];
    if (historical.duplicateInSuffix || (run.pending?.fetchProgressOnly && !run.pending.fetchProgress && run.pending.repeatedCaptures.length)) {
      run.requireToolChoice = Boolean(tools.length);
      run.pendingCaptureRecovery = { source: 'capture_progress_migration', afterTurn: run.turn };
      run.legacyRecoveryRequestPending = true;
    }
  }
  run.fetchedCaptureIds ??= [];
  const fetchedCaptureIds = new Set(run.fetchedCaptureIds);
  const flushToolRecovery = () => {
    if ((!run.pendingToolRecovery && !run.pendingCaptureRecovery) || run.pending || run.lastStopReason === STOP.paused) return;
    const guidance = run.pendingCaptureRecovery
      ? 'The saved transcript repeatedly fetched captures that were already available. fetch_page returns metadata only; read the saved captures with read_page instead of fetching them again. '
      : 'The host detected responses without a registered tool or native web-search progress. ';
    run.turns.push({ role: 'user', text: `Resume this same task from its saved work. ${guidance}${registryFeedback()}` });
    if (run.pendingToolRecovery) run.lastToolRecovery = { ...run.pendingToolRecovery, at: now() };
    if (run.pendingCaptureRecovery) run.lastCaptureRecovery = { ...run.pendingCaptureRecovery, at: now() };
    delete run.pendingToolRecovery;
    delete run.pendingCaptureRecovery;
    persist();
  };
  const flushBudgetNotice = () => {
    if (!run.pendingBudgetNotice || run.pending || run.lastStopReason === STOP.paused) return;
    run.turns.push({ role: 'user', text: `The host explicitly increased this existing run's budget. Continue this same task and session from the saved work. `
      + `The current total model-turn ceiling is ${run.budget.turnLimit}; ${Math.max(0, run.budget.turnLimit - run.turn)} turns remain. `
      + `The current total actual-web-search ceiling is ${run.budget.searchLimit}; ${Math.max(0, run.budget.searchLimit - run.searches)} searches remain. `
      + `The output-token ceiling per response is ${run.budget.maxTokens}. These current ceilings replace the earlier budget numbers in the kickoff. `
      + `Finish when the task is adequately supported and coverage is saturated; claim budget_exhausted only when the relevant current allowance is exhausted.` });
    delete run.pendingBudgetNotice; persist();
  };
  const report = async (phase = 'turn') => {
    const event = { key, phase, status: run.status, turn: run.turn, turnLimit: run.budget.turnLimit, turnsRemaining: Math.max(0, run.budget.turnLimit - run.turn),
      searches: run.searches, searchResults: run.searchResults, searchLimit: run.budget.searchLimit,
      searchesRemaining: Math.max(0, run.budget.searchLimit - run.searches), usage: { ...run.usage }, tokenAccounting: run.tokenAccounting ?? null,
      searchErrors: run.searchErrors.filter(e => e.turn === run.turn), invalidated: run.invalidated ?? null, at: now() };
    event.noProgressConsecutive = run.noProgressConsecutive ?? 0;
    event.noProgressTotal = run.noProgressTotal ?? 0;
    ctx.emit?.('agent_turn', event);
    try { for (const callback of [ctx.onTurn, spec.onTurn].filter(Boolean)) await callback(event, run); }
    catch (error) { error.key = key; error.agentKey = key; throw error; }
  };
  const stop = async () => { run.status = 'stopped'; persist(); await report('stopped'); throw new AgentError('stopped by user', 'stopped', { key }); };
  if (cachedDone) { persist(); await report('cached_done'); return run.result; }
  {
    const recorded = tokenSummary(run.modelCalls ?? []);
    run.legacyUsage = Object.fromEntries(['input', 'output', 'cachedInput', 'cacheCreationInput'].map(field => [field, Math.max(0, (run.usage?.[field] ?? 0) - recorded[field].known)]));
  }
  run.status = 'running';
  ctx.emit?.('agent_start', { key, resumedAt: run.turn, budget: run.budget, invalidated });
  persist();
  await report('start');
  flushBudgetNotice();
  flushToolRecovery();
  while (run.pending || run.turn < run.budget.turnLimit) {
    if (ctx.signal?.aborted) await stop();
    if (!run.pending) {
      let response;
      try {
        response = await ctx.callModel({ profile: ctx.profile, apiKey: ctx.apiKey, system, turns: run.turns, tools,
          searchEnabled: run.budget.searchLimit > run.searches, searchesRemaining: Math.max(0, run.budget.searchLimit - run.searches),
          maxTokens: run.budget.maxTokens, signal: ctx.signal, sessionId: run.sessionId,
          ...(run.requireToolChoice && tools.length ? { toolChoice: 'required' } : {}) });
      } catch (error) {
        (run.modelCalls ??= []).push(modelCall(error, {failed: true, provider: ctx.profile, operation: key}));
        run.tokenAccounting = tokenSummary(run.modelCalls);
        if (Object.values(run.legacyUsage).some(value => value > 0)) {
          run.tokenAccounting.legacyUsage = run.legacyUsage;
          run.tokenAccounting.complete = false;
          run.tokenAccounting.exactTotal = null;
        }
        run.usage = Object.fromEntries(['input', 'output', 'cachedInput', 'cacheCreationInput'].map(field => [field, (run.legacyUsage[field] ?? 0) + run.tokenAccounting[field].known]));
        const code = ctx.signal?.aborted ? 'stopped' : error.code ?? 'provider_error';
        run.status = code === 'stopped' ? 'stopped' : 'error';
        run.lastError = { code, message: code === 'stopped' ? 'stopped by user' : cleanMessage(error.message ?? error, ctx.apiKey), at: now() }; persist(); await report('error');
        throw new AgentError(run.lastError.message, code, { key, turn: run.turn });
      }

      delete run.legacyRecoveryRequestPending;
      (run.modelCalls ??= []).push(modelCall(response, {failed: false, provider: ctx.profile, operation: key}));
      run.tokenAccounting = tokenSummary(run.modelCalls);
        if (Object.values(run.legacyUsage).some(value => value > 0)) {
          run.tokenAccounting.legacyUsage = run.legacyUsage;
          run.tokenAccounting.complete = false;
          run.tokenAccounting.exactTotal = null;
        }
        run.usage = Object.fromEntries(['input', 'output', 'cachedInput', 'cacheCreationInput'].map(field => [field, (run.legacyUsage[field] ?? 0) + run.tokenAccounting[field].known]));
      run.turn++;

      run.searches += response.searchCalls ?? 0; run.searchResults += response.searchResults ?? 0;
      run.searchAttempts += response.searchAttempts ?? response.searchCalls ?? 0;
      const diagnostics = response.searchErrorDetails ?? (response.searchErrors ?? []).map(code => ({ code, toolUseId: null }));
      run.searchErrors.push(...diagnostics.map(e => ({ ...e, turn: run.turn, at: now() })));
      run.searchQueries.push(...(response.searchQueries ?? []).map(q => ({ ...q, turn: run.turn })));
      if (response.searchFallback) (run.searchFallbacks ??= []).push({ ...response.searchFallback, turn: run.turn, at: now() });
      run.turns.push({ role: 'assistant', content: publicAssistantContent(response.assistantContent ?? []) });
      run.lastStopReason = response.stopReason;
      const progressBefore = run.noProgressConsecutive;
      const nativeProgress = response.searchCalls > 0 || response.searchResults > 0 || nativeSearchProgress(response.assistantContent);
      const progress = registeredCall(response.toolCalls) || registeredCall(response.badCalls)
        || nativeProgress;
      if (progress) {
        run.noProgressConsecutive = 0;
        run.requireToolChoice = false;
      } else {
        run.noProgressConsecutive++;
        run.noProgressTotal++;
        run.requireToolChoice = Boolean(tools.length);
        run.lastNoProgress = { turn: run.turn, at: now(), stopReason: response.stopReason ?? null,
          unknownToolNames: [...new Set([...(response.toolCalls ?? []), ...(response.badCalls ?? [])]
            .map(call => cleanMessage(call.name ?? '(unnamed)', ctx.apiKey)))],
          publicTextPresent: (response.assistantContent ?? []).some(block => block.type === 'text' && Boolean(block.text?.trim())) };
      }

      if (response.stopReason !== STOP.paused || response.toolCalls?.length || response.badCalls?.length || !progress) run.pending = { calls: response.toolCalls ?? [], badCalls: response.badCalls ?? [], results: [], nextCall: 0,
        noProgress: !progress,
        fetchProgressOnly: fetchOnlyCalls(response.toolCalls, response.badCalls, nativeProgress),
        progressBefore, fetchProgress: false, repeatedCaptures: [],
        ...(response.stopReason === STOP.truncated ? { truncated: true } : {}) };
      persist();
      await report();
      if (ctx.signal?.aborted) await stop();
      if (!run.pending) continue;
    }
    const pending = run.pending;

    const truncated = pending.truncated ?? run.lastStopReason === STOP.truncated;
    if (truncated) { delete pending.finished; delete pending.result; }
    while (pending.nextCall < pending.calls.length && !pending.finished) {
      if (ctx.signal?.aborted) await stop();
      const call = pending.calls[pending.nextCall];
      let output, fatal;
      run.activeToolCall = { id: call.id, name: call.name, turn: run.turn }; pending.inFlight = call.id; persist();
      try {
        if (truncated) throw new AgentError(truncationFeedback(run.budget.maxTokens), 'response_truncated');
        const handler = Object.hasOwn(handlers, call.name) ? handlers[call.name] : null;
        if (!Object.hasOwn(schemas, call.name) || typeof handler !== 'function') throw new Error(`unknown tool ${call.name}. ${registryFeedback()}`);
        const problems = checkArgs(schemas[call.name], call.args);
        if (problems.length) throw new Error(problems.slice(0, 8).join('; '));
        let value = await handler(call.args, run);
        if (call.name === 'fetch_page') {
          const id = captureIdFromOutput(value);
          if (!id) pending.fetchProgress = true;
          else if (fetchedCaptureIds.has(id)) {
            (pending.repeatedCaptures ??= []).push(id);
            value = { ...value, code: 'repeated_capture', progress: 'unchanged', guidance: repeatedCaptureFeedback(id) };
          } else {
            fetchedCaptureIds.add(id); run.fetchedCaptureIds = [...fetchedCaptureIds]; pending.fetchProgress = true;
          }
        }
        if (value && Object.hasOwn(value, 'finish')) { pending.finished = true; pending.result = value.finish; output = JSON.stringify({ ok: true, accepted: true }); }
        else if (value && Object.hasOwn(value, 'attach')) output = [{ type: 'text', text: JSON.stringify(value.output ?? { ok: true }) }, ...value.attach];
        else output = JSON.stringify(value ?? { ok: true });
        run.log.push({ turn: run.turn, tool: call.name, id: call.id, ok: true });
      } catch (error) {
        if (call.name === 'fetch_page') pending.fetchProgress = true;
        const message = cleanMessage(error.message ?? error, ctx.apiKey);
        output = JSON.stringify({ ok: false, error: message, ...(error.code ? { code: error.code } : {}) });
        run.log.push({ turn: run.turn, tool: call.name, id: call.id, ok: false, error: message.slice(0, 300), ...(error.code ? { code: error.code } : {}) });
        if (['budget_exhausted', 'tool_unavailable', 'provider_quota'].includes(error.code)) fatal = error;
      }
      pending.results.push({ id: call.id, output }); pending.nextCall++; pending.inFlight = null;
      delete run.activeToolCall; persist();
      if (ctx.signal?.aborted) await stop();
      if (fatal) {
        run.status = fatal.code === 'budget_exhausted' ? 'budget_exhausted' : 'error';
        run.lastError = { code: fatal.code, resource: fatal.resource ?? null, message: cleanMessage(fatal.message, ctx.apiKey), at: now() };
        persist(); await report(fatal.code);
        throw new AgentError(run.lastError.message, fatal.code, { key, resource: fatal.resource ?? null, budget: run.budget });
      }
    }
    if (pending.fetchProgressOnly && !pending.finished) {
      pending.noProgress = !pending.fetchProgress;
      if (pending.noProgress) {
        run.noProgressConsecutive = (pending.progressBefore ?? 0) + 1;
        run.noProgressTotal++;
        run.requireToolChoice = Boolean(tools.length);
        run.lastNoProgress = { turn: run.turn, at: now(), stopReason: run.lastStopReason ?? null,
          reason: 'repeated_capture', captureIds: [...new Set(pending.repeatedCaptures ?? [])] };
      } else { run.noProgressConsecutive = 0; run.requireToolChoice = false; }
    }
    const results = [...pending.results, ...pending.badCalls.map(bad => ({ id: bad.id, output: JSON.stringify({ ok: false,
      error: truncated ? truncationFeedback(run.budget.maxTokens) : 'the tool arguments were not valid JSON',
      ...(truncated ? { code: 'response_truncated' } : {}) }) }))];
    if (pending.finished) {
      for (const call of pending.calls.slice(pending.nextCall)) results.push({ id: call.id, output: JSON.stringify({ ok: false, error: 'the run already accepted its final submission' }) });
      run.status = 'done'; run.result = pending.result; run.finishedAt = now();
      if (results.length) run.turns.push({ role: 'tool', results });
      delete run.pending; persist(); await report('done'); ctx.emit?.('agent_done', { key, turns: run.turn, searches: run.searches, searchResults: run.searchResults, usage: run.usage });
      return run.result;
    }
    if (results.length) run.turns.push({ role: 'tool', results });
    const noProgress = pending.noProgress ?? (run.noProgressConsecutive > 0
      && !registeredCall(pending.calls) && !registeredCall(pending.badCalls));
    if (noProgress) run.requireToolChoice = Boolean(tools.length);
    if (!results.length || noProgress) run.turns.push({ role: 'user', text: [
      ...(truncated ? [truncationFeedback(run.budget.maxTokens)] : []),
      ...(noProgress && pending.repeatedCaptures?.length ? [repeatedCaptureFeedback(pending.repeatedCaptures.at(-1))] : []),
      noProgress ? registryFeedback() : 'Continue with the tools. The run ends only when a submit tool accepts your result.',
    ].join(' ') });
    delete run.pending; persist(); flushBudgetNotice(); flushToolRecovery();
    if (noProgress && run.noProgressConsecutive >= NO_PROGRESS_LIMIT && !run.legacyRecoveryRequestPending) {
      const message = `The agent produced ${run.noProgressConsecutive} consecutive responses without new research or registered-tool progress. Resume with the saved work and required registered-tool recovery.`;
      run.status = 'agent_stalled'; run.lastError = { code: 'agent_stalled', message, consecutive: run.noProgressConsecutive, at: now() };
      persist(); await report('agent_stalled');
      throw new AgentError(message, 'agent_stalled', { key, turn: run.turn, consecutive: run.noProgressConsecutive });
    }
  }
  run.status = 'turn_limit'; run.lastError = { code: 'budget_exhausted', resource: 'turns', at: now() }; persist(); await report('budget_exhausted');
  throw new AgentError(`${key} reached its ${run.budget.turnLimit}-turn limit without an accepted submission`, 'budget_exhausted', { key, resource: 'turns', budget: run.budget });
}

export async function runAgent(ctx, spec) {
  try { return await executeAgent(ctx, spec); }
  catch (error) {
    error.key ??= spec.key; error.agentKey ??= spec.key;

    try {
      const run = ctx.store.loadAgent(spec.key);
      if (run?.status === 'running') {
        run.status = 'error'; run.lastError = { code: error.code ?? 'agent_error', message: cleanMessage(error.message ?? error, ctx.apiKey), at: now() };
        ctx.store.saveAgent(checkpointSafe(run, ctx.apiKey));
      }
    } catch {}
    throw error;
  }
}

export async function askOnce(ctx, { key, system, text, tool, check, maxTokens = 12000, attempts = 12 }) {
  return runAgent(ctx, { key, system, kickoff: text, tools: [tool], maxTurns: attempts, maxTokens,
    handlers: { [tool.name]: async args => { const problems = check ? check(args) : []; if (problems.length) throw new Error(problems.join('; ')); return { finish: args }; } } });
}
