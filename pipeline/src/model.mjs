import timers from 'node:timers/promises';
import {readFileSync} from 'node:fs';
import {randomUUID, createHash} from 'node:crypto';
import {tokenUsage, tokenSummary} from '../../harness/src/metrics.mjs';

const CONFIG = JSON.parse(readFileSync(process.env.TRINITY_PROVIDERS_FILE || new URL('../../config/providers.json', import.meta.url), 'utf8'));
export const PROVIDER_IDS = Object.freeze(Object.keys(CONFIG.providers));
export const SEARCH_MODES = Object.freeze(['dynamic', 'direct', 'basic', 'openrouter', 'off']);
const AUTH_MODES = new Set(['x-api-key', 'bearer']);

export class ProviderConfigError extends Error {}
const setting = (env, ...names) => names.filter(Boolean).map(name => env[name]).find(value => typeof value === 'string' && value.trim() !== '')?.trim();
const flag = (value, name) => {
  if (value === undefined) return undefined;
  if (/^(on|true|1)$/i.test(value)) return true;
  if (/^(off|false|0)$/i.test(value)) return false;
  throw new ProviderConfigError(`${name} must be on or off`);
};
export const canonicalModel = model => String(model ?? '').split('/').pop().replace(/^~/, '').replace(/\./g, '-');
export const activeProviderId = (env = process.env) => setting(env, 'TRINITY_PROVIDER') ?? CONFIG.default;

function baseUrlOf(value, id) {
  if (!value) throw new ProviderConfigError(`Set TRINITY_BASE_URL for the ${id} provider`);
  const url = String(value).trim().replace(/\/+$/, '').replace(/\/v1$/, '');
  if (!/^https:\/\/[^/\s]+/i.test(url) && !/^http:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(\/|$)/i.test(url)) throw new ProviderConfigError('The provider base URL must use https');
  return url;
}

export function resolveProfile(id = activeProviderId(), env = process.env) {
  const preset = CONFIG.providers[id];
  if (!preset) throw new ProviderConfigError(`Unknown provider ${id}; choose one of ${PROVIDER_IDS.join(', ')}`);
  const active = id === activeProviderId(env);
  const override = (...names) => active ? setting(env, ...names) : undefined;
  const legacySearch = override('PIPELINE_WEB_SEARCH') === 'off' ? 'off' : undefined;
  const profile = {
    id, label: preset.label,
    baseUrl: baseUrlOf(override('TRINITY_BASE_URL') ?? preset.baseUrl, id),
    auth: (override('TRINITY_AUTH') ?? preset.auth).toLowerCase(),
    keyEnv: preset.keyEnv,
    model: override('TRINITY_MODEL', 'PIPELINE_MODEL') ?? preset.model,
    effort: override('TRINITY_EFFORT', 'PIPELINE_EFFORT') ?? CONFIG.effort,
    apiVersion: override('TRINITY_API_VERSION') ?? preset.apiVersion,
    webSearch: (override('TRINITY_WEB_SEARCH') ?? legacySearch ?? preset.webSearch).toLowerCase(),
    sessionAffinity: flag(override('TRINITY_SESSION_AFFINITY'), 'TRINITY_SESSION_AFFINITY') ?? preset.sessionAffinity,
  };
  if (!AUTH_MODES.has(profile.auth)) throw new ProviderConfigError('TRINITY_AUTH must be x-api-key or bearer');
  if (!SEARCH_MODES.includes(profile.webSearch)) throw new ProviderConfigError(`TRINITY_WEB_SEARCH must be one of ${SEARCH_MODES.join(', ')}`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(profile.apiVersion)) throw new ProviderConfigError('TRINITY_API_VERSION must be a date such as 2023-06-01');
  profile.forcedToolChoice = flag(override('TRINITY_FORCED_TOOL_CHOICE', 'PIPELINE_FORCED_TOOL_CHOICE'), 'TRINITY_FORCED_TOOL_CHOICE') ?? canonicalModel(profile.model) === 'claude-opus-5';
  profile.name = `${profile.label}: ${profile.model}, adaptive thinking, ${profile.effort} effort`;
  return profile;
}

export const providerKey = (profile = resolveProfile(), env = process.env) => setting(env, profile.keyEnv, 'TRINITY_API_KEY') ?? null;
export function requireProviderKey(profile = resolveProfile(), env = process.env) {
  const key = providerKey(profile, env);
  if (!key) throw new ProviderConfigError(`Set ${profile.keyEnv}${profile.keyEnv === 'TRINITY_API_KEY' ? '' : ' or TRINITY_API_KEY'} for the ${profile.id} provider`);
  return key;
}
export const supportsSearch = (profile = activeProviderId()) => resolveProfile(profile).webSearch !== 'off';

export const STOP = Object.freeze({ done: 'done', paused: 'paused', truncated: 'truncated', refused: 'refused' });

const QUIET_MS = 180_000, TOTAL_MS = 900_000, ATTEMPTS = 4;
const RETRY_STATUS = new Set([408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, 529]);
const NON_RETRYABLE_CODES = new Set(['provider_quota', 'provider_auth', 'tool_unavailable']);

export class ProviderError extends Error {
  constructor(message, status = null, retryable = false, code = 'provider_error') {
    super(message); this.name = 'ProviderError'; this.status = status; this.retryable = retryable && !NON_RETRYABLE_CODES.has(code); this.code = code;
  }
}
const redact = (text, key) => (key && String(key).length >= 8 ? String(text ?? '').split(key).join('[redacted]') : String(text ?? ''))
  .replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi, 'Bearer [redacted]').replace(/\b(?:sk|ak|key)-[A-Za-z0-9_-]{12,}\b/g, '[redacted]').slice(0, 400);
const stopped = () => new ProviderError('stopped by user', null, false, 'stopped');
const STREAM_CONNECTION_CODES = new Set(['UND_ERR_SOCKET', 'UND_ERR_BODY_TIMEOUT', 'UND_ERR_CONNECT_TIMEOUT', 'ECONNRESET', 'ECONNABORTED', 'ETIMEDOUT', 'EPIPE', 'ENETRESET']);
const transientStreamDisconnect = error => !(error instanceof ProviderError) && error?.retryable !== false && error?.code !== 'provider_quota'
  && ((error?.name === 'TypeError' && error.message === 'terminated') || [error?.code, error?.cause?.code].some(code => STREAM_CONNECTION_CODES.has(code)));
const safeStreamError = (error, apiKey) => new ProviderError(redact(error?.message ?? error, apiKey),
  Number.isInteger(error?.status) && error.status >= 100 && error.status <= 599 ? error.status : null,
  error?.retryable === true || transientStreamDisconnect(error),
  typeof error?.code === 'string' && /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(error.code) && !(apiKey && error.code.includes(apiKey)) ? error.code : 'provider_error');
const LOCALIZED_CREDIT_EXHAUSTION = /(?:\u4f59\u989d|\u9918\u984d)\s*(?:\u4e0d\u8db3|(?:\u5df2)?(?:\u7528\u5b8c|\u7528\u5c3d|\u8017\u5c3d))|(?:api\s*key|\u4ee4\u724c|\u8d26\u6237|\u5e33\u6236)\s*(?:\u989d\u5ea6|\u984d\u5ea6)\s*(?:\u4e0d\u8db3|(?:\u5df2)?(?:\u7528\u5b8c|\u7528\u5c3d|\u8017\u5c3d))/i;
const providerCode = (status, detail) => status === 402 || LOCALIZED_CREDIT_EXHAUSTION.test(detail)
  || /insufficient.*(?:balance|credit|quota)|(?:balance|credit|quota).*(?:exhaust|deplet|empty)|billing|payment required/i.test(detail) ? 'provider_quota'
  : status === 401 || status === 403 || /authentication_error|permission_error|invalid.{0,12}(?:api.?key|token)/i.test(detail) ? 'provider_auth'
  : status === 429 || /rate_limit_error/i.test(detail) ? 'provider_rate_limit'
  : status === 400 && /organization has been disabled/i.test(detail) ? 'provider_upstream'
  : /web.?search|server.?tool|allowed_callers|code.?execution/i.test(detail) && /unavailable|unsupported|not supported|not enabled|unknown|invalid.*tool|allowed_callers/i.test(detail) ? 'tool_unavailable' : 'provider_error';

const ERROR_BODY_BYTES = 65_536;

async function providerDiagnostic(res, apiKey) {
  let text = '', parsed;
  try { text = typeof res.text === 'function' ? (await res.text()).slice(0, ERROR_BODY_BYTES) : ''; } catch {}
  try { parsed = text ? JSON.parse(text) : typeof res.json === 'function' ? await res.json() : undefined; } catch {}
  const message = parsed?.error?.message ?? parsed?.message ?? parsed?.error?.type ?? (typeof parsed?.error === 'string' ? parsed.error : text);
  const plain = String(message).replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, ' ').replace(/<[^>]+>/g, ' ').replace(/[\u0000-\u001f\u007f]/g, ' ').replace(/\s+/g, ' ').trim();
  return { raw: plain, detail: redact(plain, apiKey) };
}

const SEARCH_TOOL_NAMES = new Set(['web_search', 'openrouter:web_search']);
const CODE_EXECUTION_TOOL = /^(?:code_execution|bash_code_execution|text_editor_code_execution)$/;
const serverResult = block => typeof block?.type === 'string' && block.type !== 'tool_result' && block.type.endsWith('_tool_result');
const resultError = block => {
  const content = Array.isArray(block.content) ? block.content : [block.content];
  const error = content.find(item => typeof item?.type === 'string' && item.type.endsWith('_tool_result_error'));
  return error ? (typeof error.error_code === 'string' && /^[A-Za-z0-9_]{1,80}$/.test(error.error_code) ? error.error_code : 'unknown_error') : null;
};

export function searchDiagnostics(blocks, usage = {}) {
  const calls = new Map(blocks.filter(b => b.type === 'server_tool_use').map(b => [b.id, b]));
  const results = blocks.filter(serverResult);
  const toolOf = block => calls.get(block.tool_use_id)?.name ?? block.type.replace(/_tool_result$/, '');
  const errors = results.map(block => ({ block, code: resultError(block) })).filter(row => row.code)
    .map(({ block, code }) => ({ toolUseId: block.tool_use_id ?? null, tool: toolOf(block), code }));
  const isSearch = block => block.type === 'web_search_tool_result' || SEARCH_TOOL_NAMES.has(calls.get(block.tool_use_id)?.name);
  const searchResults = results.filter(block => isSearch(block) && !resultError(block));
  const queries = [...calls.values()].filter(block => SEARCH_TOOL_NAMES.has(block.name)).map(block => {
    const codes = errors.filter(error => error.toolUseId === block.id).map(error => error.code);
    const resultCount = searchResults.filter(result => result.tool_use_id === block.id).flatMap(result => Array.isArray(result.content) ? result.content : []).length;
    return { id: block.id ?? null, query: typeof block.input?.query === 'string' ? block.input.query : null, executed: !codes.includes('max_uses_exceeded'),
      resultCount, errorCodes: codes, ...(block.caller ? { caller: block.caller.type ?? null } : {}) };
  });
  const reported = Number.isInteger(usage?.server_tool_use?.web_search_requests) ? usage.server_tool_use.web_search_requests : 0;
  const unblocked = !queries.length && !results.some(isSearch) && reported > 0;
  const details = errors.map(error => ({ ...error, code: CODE_EXECUTION_TOOL.test(error.tool) ? `${error.tool}:${error.code}` : error.code }));
  return { searchCalls: unblocked ? reported : queries.filter(q => q.executed).length, searchAttempts: unblocked ? reported : queries.length,
    searchResults: unblocked ? reported : searchResults.length, searchErrors: details.map(error => error.code), searchErrorDetails: details,
    searchQueries: queries, refusedSearches: queries.filter(q => !q.executed).length };
}

export const publicAssistantContent = blocks => blocks.filter(b => !['thinking', 'redacted_thinking'].includes(b.type))
  .map(b => Object.fromEntries(Object.entries(b).filter(([key]) => !key.startsWith('_'))));

export function toMessages(turns) {
  return turns.map(t => {
    if (t.role === 'user') return { role: 'user', content: t.text };
    if (t.role === 'assistant') {
      const content = publicAssistantContent(t.content ?? []).filter(b => !(b.type === 'text' && !String(b.text ?? '').trim()));
      return { role: 'assistant', content: content.length ? content : [{ type: 'text', text: '(no content)' }] };
    }
    return { role: 'user', content: t.results.map(r => ({ type: 'tool_result', tool_use_id: r.id, content: r.output })) };
  });
}

const clip = (value, size) => typeof value === 'string' ? value.slice(0, size) : null;
function publicResult(block, query) {
  const error = resultError(block);
  if (error) return `Historical ${block.type.replace(/_tool_result$/, '').replace(/_/g, ' ')} result: ${JSON.stringify({ query, error_code: error })}`;
  if (block.type === 'web_search_tool_result') return `Historical web search results (public metadata only): ${JSON.stringify({ query,
    results: (Array.isArray(block.content) ? block.content : []).map(r => ({ title: clip(r?.title, 300), url: clip(r?.url, 2000), page_age: clip(r?.page_age, 80) })) })}`;
  const content = block.content && !Array.isArray(block.content) ? block.content : {};
  if (CODE_EXECUTION_TOOL.test(block.type.replace(/_tool_result$/, ''))) return `Historical code execution output: ${JSON.stringify({ stdout: clip(content.stdout, 6000), stderr: clip(content.stderr, 1000), return_code: content.return_code ?? null })}`;
  return `Historical ${block.type.replace(/_/g, ' ')} (details omitted)`;
}

export function publicServerToolMessages(messages, { reissuePending = false } = {}) {
  const assistantBlocks = messages.filter(m => m.role === 'assistant' && Array.isArray(m.content)).flatMap(m => m.content);
  const completed = new Set(assistantBlocks.filter(serverResult).map(b => b.tool_use_id));
  const queries = new Map(assistantBlocks.filter(b => b.type === 'server_tool_use').map(b => [b.id, typeof b.input?.query === 'string' ? b.input.query : null]));
  return messages.map(message => {
    if (message.role !== 'assistant' || !Array.isArray(message.content)) return message;
    const content = message.content.map(block => {
      if (block.type === 'server_tool_use' && completed.has(block.id)) return { type: 'text', text: `Historical ${block.name ?? 'server tool'} request (completed): ${JSON.stringify({ query: queries.get(block.id) ?? null })}` };
      if (block.type === 'server_tool_use' && reissuePending) return { type: 'text', text: `Unfulfilled ${block.name ?? 'server tool'} request: ${JSON.stringify({ query: queries.get(block.id) ?? null })}. No result was returned; reissue it with the current tools if it is still needed and do not infer its result.` };
      if (serverResult(block)) return { type: 'text', text: publicResult(block, queries.get(block.tool_use_id) ?? null) };
      if (block.type === 'text' && Array.isArray(block.citations)) {
        const { citations, ...rest } = block, sources = citations.filter(c => c?.type === 'web_search_result_location').map(c => JSON.stringify({ url: clip(c.url, 2000), title: clip(c.title, 300), cited_text: clip(c.cited_text, 300) }));
        const kept = citations.filter(c => c?.type !== 'web_search_result_location');
        return sources.length ? { ...rest, text: `${block.text ?? ''}\nPublic web citations: ${sources.join('\n')}`, ...(kept.length ? { citations: kept } : {}) } : block;
      }
      return block;
    });
    return { ...message, content };
  });
}

export function markCache(messages, count = 3) {
  const marks = messages.map((m, i) => m.role === 'user' ? i : -1).filter(i => i >= 0).slice(-count);
  return messages.map((m, i) => {
    if (!marks.includes(i)) return m;
    const content = typeof m.content === 'string' ? [{ type: 'text', text: m.content }] : m.content.map(b => ({ ...b }));
    content[content.length - 1] = { ...content[content.length - 1], cache_control: { type: 'ephemeral' } };
    return { ...m, content };
  });
}

function withQuiet(promise, ms) {
  let timer;
  const quiet = new Promise((_, reject) => { timer = setTimeout(() => reject(new ProviderError('the stream went quiet', 524, true)), ms); });
  return Promise.race([promise, quiet]).finally(() => clearTimeout(timer));
}

const plainObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const malformed = reason => new ProviderError(`malformed stream: ${reason}`, null, true, 'malformed_stream');

export async function assembleStream(body) {
  const reader = body.getReader(), decoder = new TextDecoder();
  const blocks = [], partial = new Map();
  let buffer = '', stop = null, usage = {}, event = null, data = [];
  const block = index => { if (!Number.isInteger(index) || !blocks[index]) throw malformed(`event for unknown content block ${index}`); return blocks[index]; };
  const finishInput = (b, json) => {
    const text = json.trim();
    if (!text) { if (!plainObject(b.input)) { b.input = {}; b._input_parse_error = 'the tool arguments were missing'; } return; }
    try { const value = JSON.parse(text); if (!plainObject(value)) throw new Error('not an object'); b.input = value; }
    catch { b.input = {}; b._input_parse_error = 'the tool arguments were not a valid JSON object'; }
  };
  const handle = (name, payload) => {
    switch (name) {
      case 'message_start': usage = { ...usage, ...(payload.message?.usage ?? {}) }; break;
      case 'content_block_start': {
        if (!Number.isInteger(payload.index) || !plainObject(payload.content_block)) throw malformed('content block without an index');
        blocks[payload.index] = { ...payload.content_block };
        if (['tool_use', 'server_tool_use'].includes(payload.content_block.type)) partial.set(payload.index, '');
        break;
      }
      case 'content_block_delta': {
        const b = block(payload.index), d = payload.delta ?? {};
        if (d.type === 'text_delta') b.text = (b.text ?? '') + d.text;
        else if (d.type === 'thinking_delta') b.thinking = (b.thinking ?? '') + d.thinking;
        else if (d.type === 'signature_delta') b.signature = (b.signature ?? '') + d.signature;
        else if (d.type === 'input_json_delta') {
          if (!partial.has(payload.index)) throw malformed('tool arguments for a block that is not a tool call');
          partial.set(payload.index, partial.get(payload.index) + (d.partial_json ?? ''));
        }
        break;
      }
      case 'content_block_stop': {
        const b = block(payload.index);
        if (partial.has(payload.index)) { finishInput(b, partial.get(payload.index)); partial.delete(payload.index); }
        break;
      }
      case 'message_delta': stop = payload.delta?.stop_reason ?? stop; usage = { ...usage, ...(payload.usage ?? {}) }; break;
      case 'error': {
        const message = payload.error?.message ?? 'stream error', code = providerCode(null, `${payload.error?.type ?? ''} ${message}`);
        throw new ProviderError(message, null, !NON_RETRYABLE_CODES.has(code), code);
      }
      default: break;
    }
  };
  const flush = () => {
    const raw = data.join('\n'), name = event;
    event = null; data = [];
    if (!raw || raw === '[DONE]') return;
    let payload;
    try { payload = JSON.parse(raw); } catch { throw malformed(`invalid JSON in a ${name ?? 'data'} event`); }
    handle(name ?? payload?.type, payload);
  };
  const line = text => {
    if (!text) return flush();
    if (text.startsWith(':')) return;
    const colon = text.indexOf(':'), field = colon < 0 ? text : text.slice(0, colon);
    let value = colon < 0 ? '' : text.slice(colon + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    if (field === 'event') event = value;
    else if (field === 'data') data.push(value);
  };
  try {
    while (true) {
      const { value, done } = await withQuiet(reader.read(), QUIET_MS);
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf('\n')) >= 0) { line(buffer.slice(0, nl).replace(/\r$/, '')); buffer = buffer.slice(nl + 1); }
    }
    buffer += decoder.decode();
    if (buffer) line(buffer.replace(/\r$/, ''));
    flush();
    for (const index of partial.keys()) { blocks[index].input = plainObject(blocks[index].input) ? blocks[index].input : {}; blocks[index]._input_parse_error = 'the tool arguments were incomplete'; }
    if (!stop) throw malformed('the stream ended without a stop reason');
    return { blocks: blocks.filter(Boolean), stop, usage };
  } catch (error) { error.usage = { ...usage, partial: true }; throw error; }
  finally { try { await reader.cancel(); } catch {} reader.releaseLock(); }
}

const normaliseStop = raw => raw === 'pause_turn' ? STOP.paused : raw === 'max_tokens' ? STOP.truncated : raw === 'refusal' ? STOP.refused : STOP.done;

export function searchTool(mode, remaining) {
  const max_uses = Math.max(1, Math.min(remaining, 10));
  if (mode === 'dynamic') return { type: 'web_search_20260209', name: 'web_search', max_uses };
  if (mode === 'direct') return { type: 'web_search_20260209', name: 'web_search', max_uses, allowed_callers: ['direct'] };
  if (mode === 'basic') return { type: 'web_search_20250305', name: 'web_search', max_uses };
  if (mode === 'openrouter') return { type: 'openrouter:web_search', parameters: { max_uses } };
  return null;
}

export function sessionMetadata(sessionId) {
  const hex = createHash('sha256').update(String(sessionId)).digest('hex').slice(0, 32).split('');
  hex[12] = '4'; hex[16] = ((parseInt(hex[16], 16) & 3) | 8).toString(16);
  const id = hex.join('');
  return { user_id: JSON.stringify({ device_id: createHash('sha256').update('trinity').digest('hex'), account_uuid: '',
    session_id: `${id.slice(0, 8)}-${id.slice(8, 12)}-${id.slice(12, 16)}-${id.slice(16, 20)}-${id.slice(20)}` }) };
}

export function requestBody(p, { system, turns, tools = [], searchMode = 'off', searchesRemaining = 0, maxTokens = 12000, toolChoice = null, sessionId = null, recovery = null }) {
  const search = searchMode === 'off' ? null : searchTool(searchMode, searchesRemaining);
  const toolList = [...(search ? [search] : []), ...tools.map(t => ({ name: t.name, description: t.description, input_schema: t.parameters }))];
  const messages = recovery ? publicServerToolMessages(toMessages(turns), { reissuePending: recovery.mode === 'reissue' }) : toMessages(turns);
  return { model: p.model, max_tokens: maxTokens, stream: true, thinking: { type: 'adaptive' }, output_config: { effort: p.effort },
    messages: markCache(messages),
    ...(system ? { system: [{ type: 'text', text: system, cache_control: { type: 'ephemeral' } }] } : {}),
    ...(toolList.length ? { tools: toolList } : {}),
    ...(toolList.length && toolChoice === 'required' && p.forcedToolChoice ? { tool_choice: { type: 'any' } } : {}),
    ...(p.sessionAffinity && sessionId ? { metadata: sessionMetadata(sessionId) } : {}) };
}

export const requestHeaders = (p, apiKey) => ({ 'content-type': 'application/json', accept: 'text/event-stream', 'anthropic-version': p.apiVersion,
  ...(p.auth === 'bearer' ? { authorization: `Bearer ${apiKey}` } : { 'x-api-key': apiKey }) });

async function once(p, apiKey, body, signal) {
  const total = AbortSignal.timeout(TOTAL_MS);
  let res;
  try {
    res = await fetch(`${p.baseUrl}/v1/messages`, { method: 'POST', signal: signal ? AbortSignal.any([signal, total]) : total, headers: requestHeaders(p, apiKey), body: JSON.stringify(body) });
  } catch (error) {
    if (signal?.aborted) throw stopped();
    throw new ProviderError(`transport: ${redact(error.message, apiKey)}`, null, true);
  }
  const requestId = res.headers?.get?.('request-id') ?? res.headers?.get?.('x-request-id') ?? null;
  if (res.status !== 200) {
    const { raw, detail } = await providerDiagnostic(res, apiKey);
    const code = providerCode(res.status, raw);
    const error = new ProviderError(`Provider ${res.status}${detail ? ': ' + detail : ''}${requestId ? ` (request ${requestId})` : ''}`,
      res.status, !NON_RETRYABLE_CODES.has(code) && (RETRY_STATUS.has(res.status) || code === 'provider_upstream'), code);
    error.requestId = requestId;
    throw error;
  }
  let assembled;
  try { assembled = await assembleStream(res.body); }
  catch (error) { const failure = signal?.aborted ? stopped() : safeStreamError(error, apiKey); failure.usage = error.usage; failure.requestId = requestId; throw failure; }
  const { blocks, stop, usage } = assembled;
  const toolCalls = blocks.filter(b => b.type === 'tool_use' && !b._input_parse_error).map(b => ({ id: b.id, name: b.name, args: b.input }));
  const badCalls = blocks.filter(b => b.type === 'tool_use' && b._input_parse_error).map(b => ({ id: b.id, name: b.name, reason: b._input_parse_error }));
  return { requestId, assistantContent: publicAssistantContent(blocks), text: blocks.filter(b => b.type === 'text').map(b => b.text).join('\n'), toolCalls, badCalls,
    ...searchDiagnostics(blocks, usage),
    usage: { input: usage.input_tokens ?? null, output: usage.output_tokens ?? null, cachedInput: usage.cache_read_input_tokens ?? null, cacheCreationInput: usage.cache_creation_input_tokens ?? null },
    stopReason: normaliseStop(stop), rawStopReason: stop };
}

const RECOVERABLE = /encrypted_content|encrypted_index|srvtoolu_|server_tool_use|tool_result|container|code_execution|caller/i;
const sessionRecovery = new Map();
const serverHistory = body => body.messages.some(m => m.role === 'assistant' && Array.isArray(m.content)
  && m.content.some(b => b.type === 'server_tool_use' || serverResult(b) || (Array.isArray(b.citations) && b.citations.length)));
function nextRecovery(error, body, current) {
  if (error?.status !== 400 || error.code === 'provider_quota' || !RECOVERABLE.test(error.message ?? '') || !serverHistory(body)) return null;
  if (!current) return { mode: 'replay', reason: redact(error.message, null).slice(0, 200) };
  return current.mode === 'replay' ? { mode: 'reissue', reason: current.reason } : null;
}

export async function callModel({ profile = activeProviderId(), apiKey, system, turns, tools = [], searchEnabled = false, searchesRemaining = 0, maxTokens = 12000, signal, sessionId = null, toolChoice = null }) {
  const p = resolveProfile(profile);
  if (!apiKey) throw new ProviderConfigError(`missing API key for the ${p.id} provider`);
  if (toolChoice != null && toolChoice !== 'required') throw new Error('unsupported tool choice');
  let searchMode = searchEnabled && searchesRemaining > 0 ? p.webSearch : 'off';
  let recovery = sessionId ? sessionRecovery.get(sessionId) ?? null : null, searchFallback = null;
  const build = () => requestBody(p, { system, turns, tools, searchMode, searchesRemaining, maxTokens, toolChoice, sessionId, recovery });
  let body = build();
  const callId = randomUUID(), attemptRecords = [];
  const attach = value => Object.assign(value, { callId, provider: p.id, model: p.model, attempts: attemptRecords.length, attemptRecords: structuredClone(attemptRecords),
    ...(searchFallback ? { searchFallback } : {}), ...(recovery ? { transportRecovery: recovery } : {}) });
  for (let failures = 0; ;) {
    if (signal?.aborted) throw attach(stopped());
    const startedAt = new Date().toISOString(), attemptId = randomUUID();
    try {
      const result = await once(p, apiKey, body, signal);
      const record = { attemptId, startedAt, finishedAt: new Date().toISOString(), failed: false, requestId: result.requestId, usage: tokenUsage(result.usage) };
      const executionFailure = result.searchErrorDetails.find(error => CODE_EXECUTION_TOOL.test(error.tool));
      if (searchMode === 'dynamic' && !result.searchResults && executionFailure) {
        attemptRecords.push({ ...record, failed: true, discarded: 'dynamic_filtering_failed' });
        searchFallback = { from: 'dynamic', to: 'direct', reason: executionFailure.code, requestId: result.requestId };
        searchMode = 'direct'; body = build();
        continue;
      }
      attemptRecords.push(record);
      if (recovery && sessionId) sessionRecovery.set(sessionId, recovery);
      return attach(result);
    } catch (error) {
      attemptRecords.push({ attemptId, startedAt, finishedAt: new Date().toISOString(), failed: true, requestId: error.requestId ?? null, usage: tokenUsage(error.usage) });
      if (signal?.aborted) throw attach(stopped());
      const next = nextRecovery(error, body, recovery);
      if (next) { recovery = next; body = build(); continue; }
      if (!error.retryable || ++failures >= ATTEMPTS) throw attach(error);
      try { await timers.setTimeout(Math.min(60_000, 2_000 * 2 ** (failures - 1)), undefined, signal ? { signal } : undefined); }
      catch (waitError) { throw attach(signal?.aborted ? stopped() : safeStreamError(waitError, apiKey)); }
    }
  }
}

const searchHint = (state, errors, fallback) => fallback ? 'Dynamic filtering failed inside code execution and the request fell back to direct search; set TRINITY_WEB_SEARCH=direct to skip the failing step.'
  : state === 'answered' ? null
  : errors.some(code => code.includes(':')) ? 'Dynamic filtering failed inside code execution; set TRINITY_WEB_SEARCH=direct for this provider.'
  : state === 'unavailable' ? 'The provider rejected the web search tool; try TRINITY_WEB_SEARCH=direct, basic or openrouter.'
  : 'No usable search result came back; try another TRINITY_WEB_SEARCH mode for this provider.';

export async function verifyProfile({ profile = activeProviderId(), apiKey, signal }) {
  const p = resolveProfile(profile), sessionId = randomUUID();
  const base = await callModel({ profile, apiKey, system: 'Answer in one word.', turns: [{ role: 'user', text: 'Say ok.' }], maxTokens: 64, signal, sessionId });
  let search;
  const modelCalls = [base];
  if (p.webSearch === 'off') search = { ok: false, state: 'disabled', mode: 'off', note: 'web search is switched off for this provider' };
  else try {
    const r = await callModel({ profile, apiKey, system: 'Use web search to answer in one sentence.', turns: [{ role: 'user', text: 'Search the web: what is the latest stable Node.js major version?' }],
      searchEnabled: true, searchesRemaining: 2, maxTokens: 1200, signal, sessionId });
    modelCalls.push(r);
    const state = r.searchErrors.length && !r.searchResults ? 'server_tool_error' : !r.searchCalls ? 'never_invoked' : !r.searchResults ? 'no_result' : 'answered';
    const hint = searchHint(state, r.searchErrors, r.searchFallback);
    search = { ok: state === 'answered', state, mode: r.searchFallback ? r.searchFallback.to : p.webSearch,
      note: state === 'answered' ? `${r.searchCalls} search call(s), ${r.searchResults} result block(s)` : r.searchErrors.join(', ') || 'no search result',
      ...(r.searchFallback ? { fallback: r.searchFallback } : {}), ...(hint ? { hint } : {}) };
  } catch (error) {
    modelCalls.push({ ...error, failed: true });
    search = { ok: false, state: 'unavailable', mode: p.webSearch, note: redact(error.message, apiKey), hint: searchHint('unavailable', [], null) };
  }
  return { provider: p.id, label: p.label, model: p.model, effort: p.effort, baseUrl: p.baseUrl, auth: p.auth, apiVersion: p.apiVersion, webSearch: p.webSearch,
    sessionAffinity: p.sessionAffinity, reply: base.text.slice(0, 80), usage: base.usage, modelCalls, tokenAccounting: tokenSummary(modelCalls), search };
}
