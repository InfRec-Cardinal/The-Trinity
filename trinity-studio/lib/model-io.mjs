import path from 'node:path';
import {pathToFileURL} from 'node:url';

const load = (code, file) => import(pathToFileURL(path.join(code, file)).href);

export function applyRelay(relay, env = process.env) {
  if (!relay) return 'anthropic';
  const url = new URL(relay.baseUrl);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash) throw Error('Relay base URL must be a plain https URL');
  if (typeof relay.model !== 'string' || !/^[A-Za-z0-9._:-]{1,80}$/.test(relay.model)) throw Error('Invalid relay model name');
  const webSearch = relay.webSearch ?? 'basic';
  if (!['dynamic', 'direct', 'basic', 'off'].includes(webSearch)) throw Error('Invalid web search mode');
  Object.assign(env, {TRINITY_PROVIDER: 'custom', TRINITY_BASE_URL: url.origin + url.pathname.replace(/\/+$/, ''),
    TRINITY_MODEL: relay.model, TRINITY_AUTH: relay.auth === 'x-api-key' ? 'x-api-key' : 'bearer', TRINITY_WEB_SEARCH: webSearch});
  return 'custom';
}

export function connectionRelay(connection, defaults) {
  if (connection === undefined) return {...defaults};
  if (!connection || typeof connection !== 'object' || Array.isArray(connection)) throw Error('Invalid API connection');
  if (connection.type === 'official') return {...defaults, baseUrl: 'https://api.anthropic.com', auth: 'x-api-key'};
  if (connection.type !== 'relay' || typeof connection.url !== 'string' || connection.url.length > 2048 || /[\s\\]/.test(connection.url.trim())) throw Error('Enter a valid HTTPS relay URL');
  const relay = {...defaults, baseUrl: connection.url.trim(), auth: 'bearer'};
  try {applyRelay(relay, {});} catch {throw Error('Enter a valid HTTPS relay URL without credentials, query or fragment');}
  return relay;
}

export function parseJsonReply(text) {
  const trimmed = String(text ?? '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  try {return JSON.parse(trimmed);}
  catch {}
  const candidates = [], stack = [];
  let start = -1, quoted = false, escaped = false, malformed = false;
  for (let i = 0; i < trimmed.length; i++) {
    const char = trimmed[i];
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') quoted = false;
      continue;
    }
    if (stack.length && char === '"') {quoted = true; continue;}
    if (char === '{' || char === '[') {
      if (!stack.length) {start = i; malformed = false;}
      stack.push(char === '{' ? '}' : ']');
    } else if (stack.length && (char === '}' || char === ']')) {
      if (stack.pop() !== char) malformed = true;
      if (!stack.length && !malformed) {
        try {candidates.push(JSON.parse(trimmed.slice(start, i + 1)));} catch {}
      }
    }
  }
  if (candidates.length === 1 && !stack.length) return candidates[0];
  const reason = !trimmed ? 'empty' : candidates.length > 1 ? 'ambiguous' : 'invalid_json';
  const message = reason === 'empty' ? 'Model returned no text' : reason === 'ambiguous' ? 'Model returned multiple JSON values' : 'Model response is not valid JSON';
  throw Object.assign(Error(message), {code: 'model_response_' + reason});
}

export function modelMetadata(result) {
  return Object.fromEntries(['usage', 'attemptRecords', 'attempts', 'callId', 'callIds', 'formatRetries', 'model', 'provider'].filter(key => result?.[key] !== undefined).map(key => [key, structuredClone(result[key])]));
}

export function withModelMetadata(error, result) {
  return Object.assign(error, modelMetadata(result));
}

export function unwrapJsonResponse(value, validate, fields, wrappers) {
  const original = value;
  for (let depth = 0; depth < 4; depth++) {
    if (!validate(value).length) return value;
    if (typeof value === 'string') {
      try {value = parseJsonReply(value);} catch {break;}
      continue;
    }
    if (!value || typeof value !== 'object' || Array.isArray(value) || fields.some(key => Object.hasOwn(value, key)) || Object.hasOwn(value, 'error') || value.success === false || value.is_error === true || value.status === 'error') break;
    const keys = wrappers.filter(key => Object.hasOwn(value, key));
    if (keys.length !== 1) break;
    value = value[keys[0]];
  }
  return original;
}

export function modelErrorPayload(error, apiKey) {
  const payload = {error: String(error.message), ...(error.code ? {code: error.code} : {}),
    ...(error.validationErrors ? {validationErrors: error.validationErrors, responseFields: error.responseFields} : {}), ...modelMetadata(error)};
  const redacted = apiKey ? JSON.parse(JSON.stringify(payload).replaceAll(JSON.stringify(apiKey).slice(1, -1), '[redacted]')) : payload;
  redacted.error = redacted.error.slice(0, 400);
  return redacted;
}

function combinedMetadata(results, provider) {
  const last = results.at(-1), metadata = {...modelMetadata(last), attemptRecords: last.attemptRecords ?? [], provider: last.provider ?? provider};
  if (results.length === 1) return metadata;
  const usages = results.flatMap(result => result.attemptRecords?.length ? result.attemptRecords.map(record => record.usage) : [result.usage]);
  metadata.usage = Object.fromEntries(['input', 'output', 'cachedInput', 'cacheCreationInput'].map(key => [key,
    usages.every(usage => Number.isFinite(usage?.[key])) ? usages.reduce((sum, usage) => sum + usage[key], 0) : null]));
  if (usages.some(usage => usage?.partial)) metadata.usage.partial = true;
  metadata.attemptRecords = results.flatMap(result => result.attemptRecords ?? []);
  metadata.attempts = results.reduce((sum, result) => sum + (result.attempts ?? result.attemptRecords?.length ?? 1), 0);
  metadata.callIds = results.map(result => result.callId).filter(Boolean);
  metadata.callId = results[0].callId ?? last.callId;
  metadata.formatRetries = results.length - 1;
  return metadata;
}

export async function askModelJson({code, apiKey, providerId = 'anthropic', relay, system, userText, maxTokens = 16000, callModel, normalizeResponse, validateResponse}) {
  const env = relay || providerId === 'anthropic' ? {} : {...process.env};
  if (relay) providerId = applyRelay(relay, env);
  const model = await load(code, 'pipeline/src/model.mjs');
  const profile = model.resolveProfile(providerId, env);
  let taskText = userText;
  if (profile.id !== 'anthropic' && typeof system === 'string' && system.trim()) {
    let task;
    try {task = JSON.parse(userText);} catch {}
    taskText = JSON.stringify(task && typeof task === 'object' && !Array.isArray(task)
      ? {...task, responseContract: system}
      : {task: userText, responseContract: system});
  }
  const results = [], turns = [{role: 'user', text: taskText}];
  for (let attempt = 0; attempt < 2; attempt++) {
    let result;
    try {result = await (callModel ?? model.callModel)({profile: profile.id, apiKey, system, turns: structuredClone(turns), maxTokens, searchEnabled: false, env});}
    catch (error) {throw withModelMetadata(error, combinedMetadata([...results, error], profile.id));}
    results.push(result);
    const metadata = combinedMetadata(results, profile.id);
    if (result.stopReason !== 'done') {
      const message = result.stopReason === 'truncated' ? 'Model response was truncated at the output limit' : result.stopReason === 'refused' ? 'Model declined the request' : 'Incomplete model response';
      throw withModelMetadata(Object.assign(Error(message), {code: 'model_response_incomplete'}), metadata);
    }
    try {
      let response = parseJsonReply(result.text);
      if (normalizeResponse) response = normalizeResponse(response);
      const issues = await validateResponse?.(response) ?? [];
      if (issues.length) {
        const fields = response && typeof response === 'object' && !Array.isArray(response) ? Object.keys(response).slice(0, 12) : [];
        const shape = fields.length ? fields.join(', ').slice(0, 100) : response && typeof response === 'object' && !Array.isArray(response) ? 'empty object' : Array.isArray(response) ? 'array' : response === null ? 'null' : typeof response;
        throw Object.assign(Error('Model JSON does not match the required schema (received: ' + shape + ')'), {code: 'model_response_invalid_schema', validationErrors: issues, responseFields: fields});
      }
      return {response, ...metadata};
    }
    catch (error) {
      if (!String(error.code ?? '').startsWith('model_response_')) throw withModelMetadata(error, metadata);
      if (attempt === 1) {
        const raw = String(result.text ?? '').trim(), preview = (apiKey ? raw.replaceAll(apiKey, '[redacted]') : raw).slice(0, 180);
        error.message += '; one format retry also failed' + (preview ? '. Reply excerpt: ' + JSON.stringify(preview) : '. Check that the API returns text content');
        throw withModelMetadata(error, metadata);
      }
      if (String(result.text ?? '').trim()) turns.push({role: 'assistant', content: [{type: 'text', text: result.text}]});
      const correction = (error.validationErrors ? 'The previous reply is JSON but fails the required schema. Validation errors: ' + JSON.stringify(error.validationErrors) + '. Return all required fields directly at the top level, without a design/data/result/response wrapper. ' : 'The previous reply could not be parsed as a single JSON value. ') + 'Return the complete JSON object requested by the original instructions, using the original schema. Preserve the original task, constraints and assigned identifiers. Do not invent a different task to pass validation. Do not include explanations, Markdown fences, or multiple alternatives. Escape newlines and quotes inside JSON strings correctly.';
      if (turns.length > 1) turns.push({role: 'user', text: correction});
      else turns[0].text += '\n\n' + correction;
    }
  }
}

export const PRICES = {'claude-opus-5': {input: 5, output: 25, cacheCreationInput: 6.25, cachedInput: 0.5}};
export function costOf(usage, price) {
  if (!usage || !price) return 0;
  return Object.entries(price).reduce((sum, [key, rate]) => sum + (Number(usage[key]) || 0) * rate, 0) / 1e6;
}
