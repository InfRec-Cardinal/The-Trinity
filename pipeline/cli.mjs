import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';
import { openStore } from './src/store.mjs';
import {modelCall} from '../harness/src/metrics.mjs';
import { now, uid } from './src/core.mjs';
import { activeProviderId, resolveProfile, requireProviderKey, callModel, verifyProfile } from './src/model.mjs';
import { runSearch } from './src/search/index.mjs';
import { grantSearchBudget, searchCheckpoint } from './src/search/budget.mjs';
import { splitLibrary, overview } from './src/pipeline.mjs';
import { normalizeSplitConfig } from './src/split.mjs';
import { exportLibrary } from './src/library.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const DATA = process.env.PIPELINE_DATA_DIR ?? join(ROOT, 'data'), EXPORTS = process.env.PIPELINE_EXPORT_DIR ?? join(ROOT, 'exports');
const args = process.argv.slice(2), command = args[0];
const flag = name => { const i = args.indexOf(`--${name}`); return i >= 0 ? args[i + 1] : undefined; };
const has = name => args.includes(`--${name}`);
const requireKey = profile => requireProviderKey(resolveProfile(profile));

async function main() {
  mkdirSync(DATA, { recursive: true }); mkdirSync(EXPORTS, { recursive: true });
  const store = openStore(DATA), profile = activeProviderId();
  if (['search', 'split'].includes(command) && has('unseen-fraction')) {
    store.state.config.split = normalizeSplitConfig({ unseenFraction: Number(flag('unseen-fraction')) });
    store.save();
  }
  switch (command) {
    case 'connect-test': {
      let result;
      try {result = await verifyProfile({ profile, apiKey: requireKey(profile) });}
      catch (error) {store.event('connection_usage', {calls: [modelCall(error, {failed: true, role: 'stage1', phase: 'connection_test', operation: 'connection_test'})]}); throw error;}
      store.event('connection_usage', {calls: result.modelCalls.map(call => modelCall(call, {failed: Boolean(call.failed), role: 'stage1', phase: 'connection_test', operation: 'connection_test'}))});
      console.log(JSON.stringify(result, null, 2));
      if (!result.search.ok) process.exitCode = 1;
      return;
    }
    case 'search': {
      const key = requireKey(profile);
      if (has('new')) { store.state.search = null; store.state.library = null; store.state.split = null; store.save(); }
      const controller = new AbortController();
      process.on('SIGINT', () => { console.error('\npausing: the current turn is checkpointed'); controller.abort(); });
      const job = { id: uid('job'), stage: 'search', status: 'running', startedAt: now(), provider: profile, model: resolveProfile(profile).model };
      store.state.jobs.push(job); store.save();
      const ctx = { store, profile, apiKey: key, applicationRoot: ROOT, signal: controller.signal, callModel,
        emit: (type, data) => { store.event(type, data); if (['agent_start', 'agent_done', 'search_start', 'search_done', 'search_phase'].includes(type)) console.error(`${type} ${JSON.stringify(data).slice(0, 200)}`); } };
      try { const result = await runSearch(ctx); job.status = result?.status ?? 'done'; job.result = result; console.log(JSON.stringify(result, null, 2)); }
      catch (error) { job.status = controller.signal.aborted ? 'stopped' : error.code ?? 'error'; job.error = String(error.message).slice(0, 800); console.error(`search ${job.status}: ${job.error}`); process.exitCode = 1; }
      finally { job.finishedAt = now(); store.save(); }
      if (store.state.library && store.state.search?.status === 'done') { splitLibrary(store); console.log(JSON.stringify(exportLibrary(store, EXPORTS), null, 2)); }
      return;
    }
    case 'budget': {
      const grant = grantSearchBudget(store, { agentKey: flag('agent'), turns: Number(flag('turns') ?? 80), searches: Number(flag('searches') ?? 32) });
      console.log(JSON.stringify(grant, null, 2)); return;
    }
    case 'split': console.log(JSON.stringify(splitLibrary(store), null, 2)); return;
    case 'export': console.log(JSON.stringify(exportLibrary(store, EXPORTS), null, 2)); return;
    case 'status': console.log(JSON.stringify({ overview: overview(store.state), checkpoint: searchCheckpoint(store) }, null, 2)); return;
    case 'curate': {
      const { curate } = await import('./scripts/curate-library.mjs');
      const withdraw = Object.fromEntries((flag('withdraw') ?? '').split(',').filter(Boolean).map(pair => pair.split(':')));
      console.log(JSON.stringify(curate(store, { withdraw, candidates: [], reason: flag('reason') ?? 'curation' }), null, 2)); return;
    }
    default:
      console.error('Unknown command: ' + (command ?? ''));
      process.exitCode = 2;
  }
}
main().catch(error => { console.error(error.message ?? error); process.exitCode = 1; });
