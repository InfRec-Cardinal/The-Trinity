import { createHash } from 'node:crypto';
import { lookup } from 'node:dns/promises';
import { isIP } from 'node:net';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { writeJsonAtomic, writeFileAtomic, readJson, now } from './core.mjs';

export const MAX_BYTES = 8 * 1024 * 1024, FETCH_TIMEOUT_MS = 30_000, MAX_QUOTE = 600;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const captureDir = dataDir => join(dataDir, 'capture');

export function isPrivateAddress(ip) {
  if (ip.startsWith('::ffff:')) ip = ip.slice(7);
  if (isIP(ip) === 4) {
    const [a, b] = ip.split('.').map(Number);
    return a === 10 || a === 127 || a === 0 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 100 && b >= 64 && b <= 127);
  }
  const low = ip.toLowerCase();
  return low === '::1' || low === '::' || /^f[cd]/.test(low) || /^fe[89ab]/.test(low);
}

async function assertPublic(url) {
  const u = new URL(url);
  if (!['http:', 'https:'].includes(u.protocol)) throw new Error('only http(s) pages can be captured');
  if (isIP(u.hostname)) { if (isPrivateAddress(u.hostname)) throw new Error('private addresses cannot be captured'); return; }
  const addresses = await lookup(u.hostname, { all: true });
  if (!addresses.length || addresses.some(a => isPrivateAddress(a.address))) throw new Error(`${u.hostname} does not resolve to a public address`);
}

async function readBounded(res) {
  const reader = res.body.getReader(), chunks = [];
  let total = 0, truncated = false;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    total += value.length;
    if (total > MAX_BYTES) { chunks.push(value.subarray(0, value.length - (total - MAX_BYTES))); truncated = true; await reader.cancel(); break; }
    chunks.push(value);
  }
  return { bytes: Buffer.concat(chunks), truncated };
}

export async function defaultTransport(url, { signal } = {}) {
  let current = url;
  for (let hop = 0; hop < 5; hop++) {
    await assertPublic(current);
    const timeout = AbortSignal.timeout(FETCH_TIMEOUT_MS);
    const res = await fetch(current, { signal: signal ? AbortSignal.any([signal, timeout]) : timeout, redirect: 'manual',
      headers: { 'user-agent': 'trinity-pipeline/0.1 (research capture)', accept: 'text/html,application/xhtml+xml,application/pdf,text/plain,application/json;q=0.9,*/*;q=0.5' } });
    if ([301, 302, 303, 307, 308].includes(res.status) && res.headers.get('location')) { current = new URL(res.headers.get('location'), current).href; continue; }
    const { bytes, truncated } = await readBounded(res);
    return { status: res.status, contentType: res.headers.get('content-type') ?? '', bytes, truncated, finalUrl: current };
  }
  throw new Error('too many redirects');
}

const NAMED = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', mdash: '—', ndash: '–', hellip: '…', rsquo: '’', lsquo: '‘', rdquo: '”', ldquo: '“', copy: '©', middot: '·' };
export function decodeEntities(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === '#') { const code = /^#x/i.test(e) ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return Number.isFinite(code) && code > 0 && code < 0x110000 ? String.fromCodePoint(code) : m; }
    return NAMED[e.toLowerCase()] ?? m;
  });
}
export function htmlToText(html) {
  let s = html.replace(/<!--[\s\S]*?-->/g, ' ').replace(/<(script|style|noscript|svg|template)\b[\s\S]*?<\/\1\s*>/gi, ' ');
  s = s.replace(/<\s*(br|\/p|\/div|\/li|\/h[1-6]|\/tr|\/section|\/article|\/table|\/blockquote|\/pre|\/dd|\/dt)\b[^>]*>/gi, '\n').replace(/<\s*\/?(td|th)\b[^>]*>/gi, ' ');
  s = decodeEntities(s.replace(/<[^>]+>/g, ' '));
  return s.replace(/[ \t\r\f\v ]+/g, ' ').replace(/ ?\n ?/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
}

function extractWith(command, args, bytes) {
  return new Promise((resolve, reject) => {
    const child = execFile(command, args, { timeout: FETCH_TIMEOUT_MS, maxBuffer: MAX_BYTES * 2, encoding: 'utf8' }, (error, stdout) => {
      if (error) reject(error); else resolve(stdout.trim());
    });
    child.stdin.on('error', () => {});
    child.stdin.end(bytes);
  });
}

export async function pdfToText(bytes, { env = process.env } = {}) {
  const python = [...new Set([env.PIPELINE_PDF_PYTHON, 'python3'].filter(Boolean))];
  const attempts = [
    { command: env.PIPELINE_PDFTOTEXT || 'pdftotext', args: ['-layout', '-enc', 'UTF-8', '-', '-'], extractor: 'pdftotext' },
    ...python.map(command => ({ command, args: ['-c', 'import io, sys\nfrom pypdf import PdfReader\nreader = PdfReader(io.BytesIO(sys.stdin.buffer.read()))\nprint("\\n\\n".join(page.extract_text() or "" for page in reader.pages))'], extractor: 'pypdf' })),
  ];
  let installed = false;
  for (const attempt of attempts) {
    try {
      const text = await extractWith(attempt.command, attempt.args, bytes);
      installed = true;
      if (text) return { text, extractor: attempt.extractor, reason: null };
    } catch (error) {
      if (error.code !== 'ENOENT' && !/No module named ['"]pypdf/.test(error.stderr ?? '')) installed = true;
    }
  }
  return { text: null, extractor: null, reason: installed
    ? 'PDF text extraction failed or returned no text; capture the publisher HTML version or another text source (scanned PDFs need OCR)'
    : 'PDF text extraction is unavailable: neither local pdftotext nor Python pypdf is installed; capture a publisher HTML or text version' };
}

export async function capturePage(url, dataDir, { signal, transport = defaultTransport } = {}) {
  if (typeof url !== 'string' || !/^https?:\/\/\S+$/.test(url)) throw new Error('url must be an http(s) URL');
  const dir = captureDir(dataDir); mkdirSync(dir, { recursive: true });
  const r = await transport(url, { signal });
  if (r.status >= 400) throw new Error(`HTTP ${r.status} for ${url}`);
  const captureId = sha(r.bytes), type = r.contentType.split(';')[0].trim().toLowerCase();
  const file = join(dir, captureId), previous = existsSync(file + '.json') ? readJson(file + '.json') : null;
  const head = r.bytes.subarray(0, 512).toString('utf8');
  const isPdf = type === 'application/pdf' || head.startsWith('%PDF-');
  const pdf = isPdf && !r.truncated && !previous?.extractable ? await pdfToText(r.bytes) : null;
  const textual = type === '' || /^text\/|json|xml/.test(type);
  const text = isPdf ? pdf?.text ?? null : !textual ? null : /html|xml/.test(type) || /^\s*<(!doctype|html|\?xml)/i.test(head) ? htmlToText(r.bytes.toString('utf8')) : r.bytes.toString('utf8');
  const extractable = Boolean(text && text.trim());
  if (!existsSync(file + '.json')) {
    const meta = { captureId, url, urls: [url], finalUrl: r.finalUrl, contentType: r.contentType, bytes: r.bytes.length, truncated: r.truncated, extractable,
      chars: extractable ? text.length : 0, textSha256: extractable ? sha(text) : null,
      extractor: isPdf ? pdf?.extractor ?? null : textual ? 'text' : null,
      reason: extractable ? null : isPdf ? r.truncated ? 'PDF capture exceeded the size limit; capture an HTML or text version' : pdf?.reason : `no text is extracted from ${type || 'an untyped response'}`, capturedAt: now() };
    writeFileAtomic(file + '.raw', r.bytes);
    if (extractable) writeFileAtomic(file + '.txt', text);
    writeJsonAtomic(file + '.json', meta);
  } else {
    const meta = readJson(file + '.json');
    meta.urls ??= [meta.url];
    if (!meta.urls.includes(url)) meta.urls.push(url);
    if (!meta.extractable && extractable) {
      if (sha(readFileSync(file + '.raw')) !== captureId) throw new Error('the stored page no longer matches its hash');
      writeFileAtomic(file + '.txt', text);
      Object.assign(meta, { extractable: true, chars: text.length, textSha256: sha(text), extractor: pdf?.extractor ?? 'text', reason: null, extractedAt: now() });
    }
    writeJsonAtomic(file + '.json', meta);
  }
  const meta = readJson(file + '.json');
  return { captureId, url, finalUrl: r.finalUrl, contentType: r.contentType, chars: meta.chars, extractable: meta.extractable, truncated: meta.truncated, note: meta.reason };
}

export function captureMeta(dataDir, id) {
  if (!/^[a-f0-9]{64}$/.test(String(id))) return null;
  const file = join(captureDir(dataDir), id + '.json');
  return existsSync(file) ? readJson(file) : null;
}

export function readCapture(dataDir, id, offset = 0, maxChars = 6000) {
  const meta = captureMeta(dataDir, id);
  if (!meta) throw new Error(`no capture ${id}`);
  if (!meta.extractable) throw new Error(meta.reason);
  if (!Number.isInteger(offset) || offset < 0 || !Number.isInteger(maxChars) || maxChars < 1 || maxChars > 20000) throw new Error('invalid read window');
  const text = readFileSync(join(captureDir(dataDir), id + '.txt'), 'utf8');
  const slice = text.slice(offset, offset + maxChars);
  return { captureId: id, url: meta.url, offset, text: slice, totalChars: text.length, nextOffset: offset + slice.length < text.length ? offset + slice.length : null };
}

export const normalizeText = s => String(s).toLowerCase().replace(/[‘’‚‛]/g, "'").replace(/[“”„‟]/g, '"')
  .replace(/[‐-―−]/g, '-').replace(/\s+/g, ' ').trim();

export function quoteInCapture(dataDir, id, quote) {
  const meta = captureMeta(dataDir, id);
  if (!meta) return { ok: false, reason: `no capture ${id}` };
  if (!meta.extractable) return { ok: false, reason: meta.reason };
  if (typeof quote !== 'string' || normalizeText(quote).length < 8) return { ok: false, reason: 'a quote needs at least eight characters' };
  if (quote.length > MAX_QUOTE) return { ok: false, reason: `a quote is at most ${MAX_QUOTE} characters` };
  const raw = readFileSync(join(captureDir(dataDir), id + '.raw'));
  if (sha(raw) !== id) return { ok: false, reason: 'the stored page no longer matches its hash' };
  const text = readFileSync(join(captureDir(dataDir), id + '.txt'), 'utf8');
  if (sha(text) !== meta.textSha256) return { ok: false, reason: 'the stored text no longer matches its hash' };
  return normalizeText(text).includes(normalizeText(quote)) ? { ok: true, url: meta.url } : { ok: false, reason: `the quote is not verbatim on the captured page ${meta.url}` };
}

export function quoteContext(dataDir, id, quote, { before = 1200, after = 1200 } = {}) {
  const checked = quoteInCapture(dataDir, id, quote);
  if (!checked.ok) return { ...checked, captureId: id, quote };
  if (!Number.isInteger(before) || before < 0 || before > 10000 || !Number.isInteger(after) || after < 0 || after > 10000) throw new Error('invalid quote context window');
  const text = readFileSync(join(captureDir(dataDir), id + '.txt'), 'utf8'), lowered = text.toLowerCase(), chars = [], starts = [], ends = [];

  let inWhitespace = false, lowerOffset = 0;
  for (let offset = 0; offset < text.length;) {
    const raw = String.fromCodePoint(text.codePointAt(offset)), end = offset + raw.length;

    const lowerLength = raw.toLowerCase().length;
    const normal = lowered.slice(lowerOffset, lowerOffset + lowerLength).replace(/[‘’‚‛]/g, "'").replace(/[“”„‟]/g, '"').replace(/[‐-―−]/g, '-');
    lowerOffset += lowerLength;
    if (/\s/.test(normal)) {
      if (!inWhitespace && chars.length) { chars.push(' '); starts.push(offset); ends.push(end); }
      else if (inWhitespace && chars.at(-1) === ' ') ends[ends.length - 1] = end;
      inWhitespace = true;
    } else {
      for (let i = 0; i < normal.length; i++) { chars.push(normal[i]); starts.push(offset); ends.push(end); }
      inWhitespace = false;
    }
    offset = end;
  }
  const needle = normalizeText(quote), found = chars.join('').indexOf(needle);
  if (found < 0) return { ok: false, captureId: id, quote, reason: 'verified quote could not be mapped to its original context' };
  const start = starts[found], end = ends[found + needle.length - 1], contextStart = Math.max(0, start - before), contextEnd = Math.min(text.length, end + after);
  return { ok: true, captureId: id, url: checked.url, quote, matchedText: text.slice(start, end), start, end,
    contextStart, contextEnd, context: text.slice(contextStart, contextEnd), totalChars: text.length,
    truncated: contextStart > 0 || contextEnd < text.length };
}

export function verifyQuotes(dataDir, items, label) {
  const problems = [];
  (items ?? []).forEach((item, i) => { const r = quoteInCapture(dataDir, item.captureId, item.quote); if (!r.ok) problems.push(`${label}[${i}]: ${r.reason}`); });
  return problems;
}
