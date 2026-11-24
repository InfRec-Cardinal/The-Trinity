                                                                                                                      
                                                                                                                     
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Browser } from './tools/cdp.mjs';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.png': 'image/png' };
let shared = null;

async function serve() {
  const server = http.createServer((req, res) => {
    const p = path.normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^\/+/, '');
    const file = path.join(ROOT, p);
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] ?? 'application/octet-stream' }); fs.createReadStream(file).pipe(res);
  });
  server.on('connection', sock => sock.unref());                                                                       
  await new Promise(r => server.listen(0, '127.0.0.1', r)); server.unref();
  return server;
}

export async function openSim(kind) {                           
  shared ??= (async () => { const server = await serve(); const browser = await Browser.launch(); return { server, browser, base: `http://127.0.0.1:${server.address().port}` }; })();
  const { browser, base } = await shared;
  const page = await browser.open(`${base}/${kind}/sim.html`);
  await page.waitFor('window.__ready === true', 60000);
  return {
    eval: expr => page.eval(expr),
    call: (method, ...args) => page.eval(`(() => { try { return { ok: true, value: window.__sim.${method}(...${JSON.stringify(args)}) }; } catch (e) { return { ok: false, error: e.message, skill: e.constructor?.name === 'SkillError' }; } })()`),
    async close() { await page.close(); },
  };
}
export async function shutdown() { if (!shared) return; const { server, browser } = await shared; server.close(); await browser.close(); shared = null; }
