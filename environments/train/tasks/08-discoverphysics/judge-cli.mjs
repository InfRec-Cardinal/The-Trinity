                                                                                      
                                                                                  
                                                                               
import { appendFileSync } from 'node:fs';
import { join } from 'node:path';
import { contentHash } from '../../lib/hash.mjs';

export const JUDGE_MODEL = 'claude-opus-4-6';
export async function claudeCliJudgeCall({ requestId, model, system, turns, maxTokens, temperature, signal, runDir }) {
  if (model !== JUDGE_MODEL || maxTokens !== 1024 || typeof system !== 'string'
      || turns?.length !== 1 || turns[0].role !== 'user' || typeof turns[0].text !== 'string')
    throw Object.assign(new Error('Official ExplanationJudge request differs from the pinned route'), { code: 'source_model_response_invalid' });
  const key = process.env.UPSTREAM_API_KEY;
  const base = process.env.RELAY_BASE_URL;
  if (!key || !base) throw new Error('Judge provider credentials are not configured');
  const body = { model, system, max_tokens: maxTokens, temperature: temperature ?? 1,
    messages: [{ role: 'user', content: turns[0].text }] };
  const response = await fetch(`${base.replace(/\/$/, '')}/v1/messages`, {
    method: 'POST', redirect: 'error',
    signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(180000)]) : AbortSignal.timeout(180000),
    headers: { 'content-type': 'application/json', 'anthropic-version': '2023-06-01', 'x-api-key': key },
    body: JSON.stringify(body),
  });
  const raw = (await response.text()).replaceAll(key, '[redacted]');
  if (runDir) appendFileSync(join(runDir, 'native-judge-transport.jsonl'), JSON.stringify({
    requestId, transport: 'authorized-provider-messages-v1', requestHash: contentHash(body),
    model, maxTokens, temperature: body.temperature, status: response.status, raw,
  }) + '\n');
  if (!response.ok) throw new Error(`Judge HTTP ${response.status}: ${raw.slice(0, 400)}`);
  let result;
  try { result = JSON.parse(raw); } catch { throw new Error('Judge provider returned incomplete JSON'); }
  if (result.model !== model || result.stop_reason !== 'end_turn' || !Array.isArray(result.content)
      || result.content.some(b => b.type !== 'text'))
    throw new Error('Judge did not complete the pinned model text turn');
  const text = result.content.map(b => b.text).join('');
  if (!text.trim()) throw new Error('Judge returned empty text');
  const u = result.usage ?? {};
  const usage = { prompt_tokens: u.input_tokens ?? null, completion_tokens: u.output_tokens ?? null,
    total_tokens: Number.isFinite(u.input_tokens) && Number.isFinite(u.output_tokens) ? u.input_tokens + u.output_tokens : null };
  return { requestId, model, text, usage, finishReason: 'stop',
    responseFingerprint: contentHash({ requestId, model, text, usage, finishReason: 'stop' }) };
}
