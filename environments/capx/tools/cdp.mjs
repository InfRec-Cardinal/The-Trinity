                                                                                                           
                                                                   
                                                                                                                                           
import { spawn, execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const CHROME = process.env.CHROME_BIN || (process.platform === 'darwin' ? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' : process.platform === 'win32' ? 'chrome' : ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome'].find(file => fs.existsSync(file)) || 'chromium');
const sleep = ms => new Promise(r => setTimeout(r, ms));

class Page {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map(); this.events = []; this.failure = null;
    ws.addEventListener('message', ev => {
      if (this.failure) return;
      let message;
      try { message = JSON.parse(ev.data); if (!message || typeof message !== 'object') throw Error('Invalid CDP message'); }
      catch (error) { this.fail(error); return; }
      const pending = this.pending.get(message.id);
      if (pending) {
        this.pending.delete(message.id); clearTimeout(pending.timer);
        message.error ? pending.reject(new Error(message.error.message)) : pending.resolve(message.result);
      } else this.events.push(message);
    });
    ws.addEventListener('close', () => this.fail(new Error('CDP connection closed')));
    ws.addEventListener('error', () => this.fail(new Error('CDP connection failed')));
  }
  fail(error) {
    if (this.failure) return;
    this.failure = error;
    for (const pending of this.pending.values()) { clearTimeout(pending.timer); pending.reject(error); }
    this.pending.clear(); try { this.ws.close(); } catch {}
  }
  send(method, params = {}, timeoutMs = 600000) {
    if (this.failure) return Promise.reject(this.failure);
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.fail(new Error('CDP request timed out: ' + method)), timeoutMs);
      this.pending.set(id, {resolve, reject, timer});
      try { this.ws.send(JSON.stringify({id, method, params})); } catch (error) { this.fail(error); }
    });
  }
  async eval(expression, { awaitPromise = true, timeoutMs = 600000 } = {}) {
    const r = await this.send('Runtime.evaluate', {expression, awaitPromise, returnByValue: true}, timeoutMs);
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result.value;
  }
  async waitFor(expression, timeoutMs = 30000) { const t = Date.now(); while (Date.now() - t < timeoutMs) { try { if (await this.eval(expression)) return true; } catch {} await sleep(150); } throw new Error('waitFor timeout: ' + expression); }
  async close() {                                                                                              
    try { await fetch(`http://127.0.0.1:${this.port}/json/close/${this.targetId}`, { headers: { Connection: 'close' }, signal: AbortSignal.timeout(1000) }); } catch {}
    try { this.ws.close(); } catch {}
  }
  async screenshot() { const r = await this.send('Page.captureScreenshot', { format: 'png' }); return Buffer.from(r.data, 'base64'); }
  consoleErrors() { return this.events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error')).map(e => JSON.stringify(e.params).slice(0, 300)); }
}

export class Browser {
  static async launch({ port = 9300 + Math.floor(Math.random() * 500), width = 1280, height = 900 } = {}) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cdp-'));
    const proc = spawn(CHROME, ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage', `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`, '--no-first-run', '--no-default-browser-check',
      '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', `--window-size=${width},${height}`, 'about:blank'], { stdio: 'ignore' });
    let launchError = null; proc.on('error', error => { launchError = error; });
    const b = new Browser(); b.proc = proc; b.port = port; b.dir = dir;
    proc.unref();
                                                                                                                         
    process.on('exit', () => { try { execFileSync('pkill', ['-9', '-f', `user-data-dir=${dir}`]); } catch {} try { fs.rmSync(dir, { recursive: true, force: true }); } catch {} });
    try {
      const deadline = Date.now() + 10000;
      while (Date.now() < deadline) {
        if (launchError) throw launchError;
        if (proc.exitCode !== null || proc.signalCode !== null) throw new Error('Chrome exited during startup');
        try {
          const v = await (await fetch(`http://127.0.0.1:${port}/json/version`, {headers: {Connection: 'close'}, signal: AbortSignal.timeout(1000)})).json();
          if (v.webSocketDebuggerUrl) {
    spawn('/bin/sh', ['-c', `while kill -0 ${process.pid} 2>/dev/null; do sleep 1; done; pkill -9 -f "user-data-dir=${dir}"; rm -rf "${dir}"`], { detached: true, stdio: 'ignore' }).on('error', () => {}).unref();
            return b;
          }
        } catch {}
        await sleep(100);
      }
      throw new Error('Chrome did not start');
    } catch (error) { await b.close(); throw error; }
  }
  async open(url) {
    const t = await (await fetch(`http://127.0.0.1:${this.port}/json/new?${encodeURIComponent(url)}`, { method: 'PUT', headers: { Connection: 'close' } })).json();
    const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise((res, rej) => { const timer = setTimeout(() => { ws.close(); rej(new Error('CDP connection timed out')); }, 10000); ws.onopen = () => { clearTimeout(timer); res(); }; ws.onerror = error => { clearTimeout(timer); ws.close(); rej(error); }; });
    const p = new Page(ws); p.targetId = t.id; p.port = this.port; (this.pages ??= []).push(p); await p.send('Runtime.enable'); await p.send('Page.enable'); return p;
  }
  async close() { for (const p of this.pages ?? []) try { p.ws.close(); } catch {} try { execFileSync('pkill', ['-9', '-f', `user-data-dir=${this.dir}`]); } catch {} await sleep(300); try { fs.rmSync(this.dir, { recursive: true, force: true }); } catch {} }
}
