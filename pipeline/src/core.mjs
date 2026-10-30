import { createHash, randomUUID } from 'node:crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync, renameSync, openSync, fsyncSync, closeSync, unlinkSync } from 'node:fs';
import { dirname } from 'node:path';
import { appendLine } from '../../harness/src/core.mjs';

export class PipelineError extends Error {}
export function assert(condition, message) { if (!condition) throw new PipelineError(message); }
export const now = () => new Date().toISOString();
export const uid = prefix => `${prefix}-${randomUUID()}`;
export const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(v => canonical(v) ?? 'null').join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort().filter(k => value[k] !== undefined)
    .map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
  return JSON.stringify(value);
}
export const contentHash = value => sha256(canonical(value));

export function readJson(path, fallback = undefined) {
  if (!existsSync(path)) { if (fallback !== undefined) return fallback; throw new PipelineError(`missing file ${path}`); }
  return JSON.parse(readFileSync(path, 'utf8'));
}

export function writeFileAtomic(path, data) {
  mkdirSync(dirname(path), { recursive: true });
  const temporary = `${path}.${randomUUID()}.tmp`;
  const fd = openSync(temporary, 'wx', 0o600);
  try { writeFileSync(fd, data); fsyncSync(fd); } finally { closeSync(fd); }
  try { renameSync(temporary, path); } finally { if (existsSync(temporary)) unlinkSync(temporary); }
}

export const writeJsonAtomic = (path, value) => writeFileAtomic(path, JSON.stringify(value, null, 2) + '\n');

export function appendJsonLine(path, value) {
  mkdirSync(dirname(path), { recursive: true });
  appendLine(path, JSON.stringify(value) + '\n');
}

export function redact(text, secrets) {
  let out = String(text ?? '');
  for (const secret of secrets) if (secret && secret.length >= 8) out = out.split(secret).join('[redacted]');
  return out.replace(/\b(sk|ak|key)-[A-Za-z0-9_-]{12,}\b/g, '[redacted]');
}


