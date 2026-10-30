import fs from 'node:fs';
import {normalizeMedia} from './media.mjs';
import {modelCall, tokenSummary} from './metrics.mjs';
import {AsyncLocalStorage} from 'node:async_hooks';
import {spawn} from 'node:child_process';
import {clone, ensure, digest} from './core.mjs';

export class CommandAgent {
  constructor(command, {timeoutMs = 180000, maxBytes = 2097152} = {}) {
    ensure(Array.isArray(command) && command.length > 0 && command.every(value => typeof value === 'string'), 'Agent command must be an argument array');
    this.command = command;
    this.timeoutMs = timeoutMs;
    this.maxBytes = maxBytes;
  }
  async respond(request) {
    return new Promise((resolve, reject) => {
      const child = spawn(this.command[0], this.command.slice(1), {stdio: ['pipe', 'pipe', 'pipe'], shell: false});
      let output = '', error = '', settled = false;
      const finish = (failure, value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        failure ? reject(failure) : resolve(value);
      };
      const timer = setTimeout(() => {child.kill('SIGKILL'); finish(Error('Agent response timeout'));}, this.timeoutMs);
      child.stdout.on('data', chunk => {
        output += chunk;
        if (Buffer.byteLength(output) > this.maxBytes) {child.kill('SIGKILL'); finish(Error('Agent response limit exceeded'));}
      });
      child.stderr.on('data', chunk => {error = (error + chunk).slice(-2000);});
      child.on('error', failure => finish(failure));
      child.stdin.on('error', failure => finish(failure));
      child.on('close', code => {
        try {
          ensure(code === 0, 'Agent command failed: ' + error);
          const response = JSON.parse(output);
          finish(null, response);
        } catch (failure) {finish(failure);}
      });
      child.stdin.end(JSON.stringify(request));
    });
  }
}
export class Agent {
  constructor(backend, store) {
    this.backend = backend;
    this.store = store;
    this.calls = [];
    this.scope = {};
    this.context = new AsyncLocalStorage();
  }
  withScope(scope, task) {return this.context.run({...this.context.getStore(), ...scope}, task);}
  usageSince(index = 0, scope = {}) {return tokenSummary(this.calls.slice(index).filter(call => Object.entries(scope).every(([key, value]) => call[key] === value)));}
  async ask(operation, context, outputContract, scope = {}) {
    const inherited = {...this.scope, ...this.context.getStore(), ...scope};
    const startedAt = new Date().toISOString();
    const role = operation.split('_')[0];
    const system = fs.readFileSync(new URL('../prompts/' + role + '.txt', import.meta.url), 'utf8');
    const request = {operation, system, context: normalizeMedia(clone(context)), outputContract: clone(outputContract)};
    const requestId = this.store.put(request);
    let transport, failure;
    try {
      transport = await this.backend.respond(request);
      const response = transport?.transport === 'trinity-agent-result-v1' ? transport.response : transport;
      ensure(response && typeof response === 'object' && !Array.isArray(response), 'Agent must return a JSON object');
      const responseId = this.store.put(response);
      this.store.record('agent_exchange', {operation, requestId, responseId, contextDigest: digest(context)});
      return clone(response);
    } catch (error) {failure = error; throw error;}
    finally {
      const source = transport?.transport === 'trinity-agent-result-v1' ? transport : failure;
      const call = modelCall(source, {...inherited, operation, role, requestId, startedAt, finishedAt: new Date().toISOString(),
        node: scope.node ?? context.node?.id ?? context.node ?? inherited.node ?? null,
        phase: scope.phase ?? operation, iteration: context.iteration ?? inherited.iteration ?? null,
        failed: Boolean(failure)});
      this.calls.push(call);
      this.store.record('model_usage', call);
    }
  }
}
