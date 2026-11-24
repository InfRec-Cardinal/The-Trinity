import {redact} from './security.mjs';


const TERMINAL_EVENT = 'message_stop';
const RETRYABLE_STATUS = new Set([408, 409, 429]);

const TRANSIENT_TRANSPORT_CODES = new Set([
  'UND_ERR_SOCKET', 'UND_ERR_CONNECT_TIMEOUT', 'UND_ERR_HEADERS_TIMEOUT', 'UND_ERR_BODY_TIMEOUT',
  'ECONNRESET', 'ETIMEDOUT', 'ECONNREFUSED', 'EPIPE', 'ENETRESET', 'ENETUNREACH', 'EHOSTUNREACH',
]);

const RETRYABLE_ERROR = /(?:fetch failed|terminated|timed?\s*out|timeout|socket|connection error|connection reset|econnreset|etimedout|epipe|und_err_|before message_stop|incomplete stream|server_error|internal_server_error|upstream_error|upstream_timeout|overloaded|service_unavailable|rate_limit)/i;

const FATAL_ERROR = /(?:invalid_api_key|authentication|permission|invalid_request|context_length|content_policy|policy_violation|unsupported|not_found)/i;

function boundedDelay(attempt, baseDelayMs, maxRetryDelayMs, headers) {
  const retryAfterMs = headers?.get?.('retry-after-ms');
  const retryAfter = headers?.get?.('retry-after');
  let requested;
  if (retryAfterMs && Number.isFinite(Number(retryAfterMs))) requested = Number(retryAfterMs);
  else if (retryAfter) {
    const seconds = Number(retryAfter);
    requested = Number.isFinite(seconds) ? seconds * 1_000 : Date.parse(retryAfter) - Date.now();
  }
  const exponential = baseDelayMs * (2 ** Math.max(0, attempt - 1));
  const jittered = exponential * (0.75 + Math.random() * 0.25);
  const delay = Number.isFinite(requested) && requested >= 0 ? requested : jittered;
  return maxRetryDelayMs > 0 ? Math.min(delay, maxRetryDelayMs) : delay;
}

async function abortableSleep(ms, signal) {
  if (ms <= 0) return;
  await new Promise((resolve, reject) => {
    const stop = () => { clearTimeout(timer); reject(signal.reason ?? new Error('Request aborted')); };
    const timer = setTimeout(() => { signal.removeEventListener('abort', stop); resolve(); }, ms);
    signal.addEventListener('abort', stop, { once: true });
    if (signal.aborted) stop();
  });
}

async function readBodyUnderWatchdog(response, { firstResponseTimeoutMs, idleTimeoutMs, controller }) {
  const reader = response.body?.getReader?.();
  if (!reader) return await response.text();
  const decoder = new TextDecoder();
  let text = '';
  let sawByte = false;
  try {
    for (;;) {
      const window = sawByte ? idleTimeoutMs : firstResponseTimeoutMs;
      let timer;
      const stalled = new Promise((_, reject) => {
        timer = setTimeout(() => {
          const error = new Error(`Anthropic stream stalled ${window}ms before ${
            sawByte ? 'its next chunk' : 'its first byte'}`);
          error.stalled = true;
          controller.abort(error);
          reject(error);
        }, window);
      });
      let step;
      try {
        step = await Promise.race([reader.read(), stalled]);
      } finally { clearTimeout(timer); }
      if (step.done) break;
      sawByte = true;
      text += decoder.decode(step.value, { stream: true });
    }
    text += decoder.decode();
    return text;
  } finally {
    reader.cancel().catch(() => {});
  }
}

function retryable(status, error, bodyText) {
  const evidence = `${error?.message ?? error ?? ''}\n${bodyText ?? ''}`;
  if (FATAL_ERROR.test(evidence)) return false;

  if (error?.stalled) return true;
  if (status !== null && (RETRYABLE_STATUS.has(status) || status >= 500)) return true;
  if ((status === null || status < 400)
      && [error?.code, error?.cause?.code].some(code => TRANSIENT_TRANSPORT_CODES.has(code))) return true;
  return RETRYABLE_ERROR.test(evidence);
}

function withoutStreaming(requestBody) {
  if (!requestBody?.byteLength) return undefined;
  let payload;
  try { payload = JSON.parse(new TextDecoder().decode(requestBody)); } catch { return undefined; }
  if (payload?.stream !== true) return undefined;
  payload.stream = false;
  return new TextEncoder().encode(JSON.stringify(payload));
}

function streamFromMessage(bodyText) {
  const message = JSON.parse(bodyText);
  if (message?.type !== 'message') throw new Error(`Non-streaming reply was not a message: ${String(message?.type)}`);
  const frames = [];
  const push = (event, data) => frames.push(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  push('message_start', { type: 'message_start', message: { ...message, content: [], stop_reason: null, stop_sequence: null } });
  for (const [index, block] of (Array.isArray(message.content) ? message.content : []).entries()) {
    const delta = (value) => push('content_block_delta', { type: 'content_block_delta', index, delta: value });
    if (block?.type === 'text') {
      push('content_block_start', { type: 'content_block_start', index, content_block: { type: 'text', text: '' } });
      if (block.text) delta({ type: 'text_delta', text: block.text });
    } else if (block?.type === 'thinking') {
      push('content_block_start', { type: 'content_block_start', index, content_block: { type: 'thinking', thinking: '' } });
      if (block.thinking) delta({ type: 'thinking_delta', thinking: block.thinking });

      if (block.signature) delta({ type: 'signature_delta', signature: block.signature });
    } else if (block?.type === 'tool_use') {
      push('content_block_start', { type: 'content_block_start', index, content_block: { type: 'tool_use', id: block.id, name: block.name, input: {} } });
      delta({ type: 'input_json_delta', partial_json: JSON.stringify(block.input ?? {}) });
    } else {

      push('content_block_start', { type: 'content_block_start', index, content_block: block });
    }
    push('content_block_stop', { type: 'content_block_stop', index });
  }
  push('message_delta', {
    type: 'message_delta',
    delta: { stop_reason: message.stop_reason ?? 'end_turn', stop_sequence: message.stop_sequence ?? null },
    usage: { output_tokens: Number(message.usage?.output_tokens ?? 0) },
  });
  push(TERMINAL_EVENT, { type: TERMINAL_EVENT });
  return frames.join('');
}

export function installAnthropicAtomicRetry(baseUrl, {
  maxRetries = 0,
  retryBaseDelayMs = 2_000,
  maxRetryDelayMs = 60_000,
  firstResponseTimeoutMs = 600_000,
  idleTimeoutMs = 300_000,
  onProgress = () => {},
} = {}) {
  if (!Number.isInteger(maxRetries) || maxRetries < 0 || maxRetries > 32) throw new Error('maxRetries must be 0..32');
  if (!Number.isFinite(retryBaseDelayMs) || retryBaseDelayMs < 0) throw new Error('retryBaseDelayMs must be non-negative');
  if (!Number.isFinite(maxRetryDelayMs) || maxRetryDelayMs < 0) throw new Error('maxRetryDelayMs must be non-negative');
  if (!Number.isFinite(firstResponseTimeoutMs) || firstResponseTimeoutMs <= 0) throw new Error('firstResponseTimeoutMs must be positive');
  if (!Number.isFinite(idleTimeoutMs) || idleTimeoutMs <= 0) throw new Error('idleTimeoutMs must be positive');

  const originalFetch = globalThis.fetch;
  const endpoint = new URL(`${String(baseUrl).replace(/\/$/, '')}/v1/messages`);
  const records = [];
  let requestNumber = 0;
  let restored = false;

  globalThis.fetch = async (input, init) => {
    let url;
    try {
      url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url);
    } catch {
      return originalFetch(input, init);
    }
    if (url.origin !== endpoint.origin || url.pathname.replace(/\/$/, '') !== endpoint.pathname) {
      return originalFetch(input, init);
    }

    const template = new Request(input, init);

    const requestBody = template.method === 'GET' || template.method === 'HEAD'
      ? undefined : new Uint8Array(await template.clone().arrayBuffer());
    const requestId = ++requestNumber;

    const nonStreamingBody = withoutStreaming(requestBody);
    let nonStreaming = false;
    let justFlipped = false;
    let lastError;

    for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
      if (restored || template.signal.aborted) throw template.signal.reason ?? new Error('Anthropic retry adapter restored');

      justFlipped = false;
      const started = Date.now();
      let status = null;
      let headers;
      let bodyText = '';

      const attemptController = new AbortController();
      const onOuterAbort = () => attemptController.abort(template.signal.reason ?? new Error('Request aborted'));
      if (template.signal.aborted) onOuterAbort();
      else template.signal.addEventListener('abort', onOuterAbort, { once: true });

      let headersTimer;
      const headersStalled = new Promise((_, reject) => {
        headersTimer = setTimeout(() => {
          const error = new Error(`Anthropic request received no response headers within ${firstResponseTimeoutMs}ms`);
          error.stalled = true;
          attemptController.abort(error);
          reject(error);
        }, firstResponseTimeoutMs);
      });
      try {
        const response = await Promise.race([
          originalFetch(new Request(template, { signal: attemptController.signal, redirect: 'error', body: (nonStreaming ? nonStreamingBody : requestBody)?.slice() })),
          headersStalled,
        ]).finally(() => clearTimeout(headersTimer));
        status = response.status;
        headers = response.headers;
        bodyText = await readBodyUnderWatchdog(response, { firstResponseTimeoutMs, idleTimeoutMs, controller: attemptController });
        if (!response.ok) {
          const error = new Error(`Provider HTTP ${status}: ${bodyText.slice(0, 2_000)}`);
          error.status = status;
          throw error;
        }

        const streamed = /^data:|^event:/m.test(bodyText);
        if (streamed && !bodyText.includes(TERMINAL_EVENT)) {
          const error = new Error(`Anthropic stream ended before ${TERMINAL_EVENT} after ${bodyText.length} bytes`);
          error.truncated = true;
          throw error;
        }

        let responseHeaders = response.headers;
        if (nonStreaming && !streamed) {
          bodyText = streamFromMessage(bodyText);
          responseHeaders = new Headers(response.headers);
          responseHeaders.set('content-type', 'text/event-stream');
          responseHeaders.delete('content-length');
        }
        records.push({ requestId, attempt, status, bytes: bodyText.length, committed: true,
                       ...(nonStreaming ? { nonStreaming: true } : {}),
                       ms: Date.now() - started });
        return new Response(bodyText, { status, statusText: response.statusText, headers: responseHeaders });
      } catch (error) {
        error.message = redact(error.message, [template.headers.get('x-api-key'), template.headers.get('authorization')?.replace(/^Bearer /i,'')]);
        lastError = error;
        const willRetry = attempt <= maxRetries && retryable(status, error, bodyText);
        records.push({ requestId, attempt, status, bytes: bodyText.length, committed: false,
                       ms: Date.now() - started, truncated: Boolean(error?.truncated),
                       stalled: Boolean(error?.stalled),
                       ...(nonStreaming ? { nonStreaming: true } : {}),
                       error: String(error?.message ?? error).slice(0, 500), willRetry });
        if (!willRetry) throw error;

        if ((error?.truncated || error?.stalled) && nonStreamingBody && !nonStreaming) {
          nonStreaming = true;
          justFlipped = true;
          onProgress({ phase: 'non_streaming_fallback', requestId, attempt,
                       reason: String(error?.message ?? error).slice(0, 300) });
        }

        const delay = justFlipped ? 0 : boundedDelay(attempt, retryBaseDelayMs, maxRetryDelayMs, headers);
        onProgress({ phase: 'request_retry', requestId, attempt, delayMs: Math.round(delay),
                     status, truncated: Boolean(error?.truncated), stalled: Boolean(error?.stalled),
                     reason: String(error?.message ?? error).slice(0, 300) });
        await abortableSleep(delay, template.signal);
      } finally {
        template.signal.removeEventListener('abort', onOuterAbort);
      }
    }
    throw lastError ?? new Error('Anthropic atomic retry exhausted without an error');
  };

  return {
    records,
    uninstall() { restored = true; globalThis.fetch = originalFetch; },
  };
}
