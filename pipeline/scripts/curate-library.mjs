import {readFileSync} from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { openStore } from '../src/store.mjs';
import { saveCandidate } from '../src/search/discover.mjs';
import { now } from '../src/core.mjs';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
export const WITHDRAW_REASONS = {
  too_hard: 'Too hard for a model-driven agent to yield both successes and failures: the published protocol is a very long single run or needs tens of thousands of real-time control steps, so every episode would fail.',
  too_dated: 'Too dated: the protocol was designed for sample-heavy reinforcement learning from pixels and is superseded for agent evaluation by newer tasks already in the library.',
  too_easy: 'Too easy: a capable agent solves essentially every instance, so the task yields no failure trajectories to learn from.',
  superseded: 'Superseded: the published protocol is retired or dated, and the same mechanism is covered by newer or more widely used tasks already in the library.',
  irreproducible: 'Irreproducible: the published setup depends on a proprietary platform or an unreleased system, so the task cannot be rebuilt faithfully.',
};

export function curate(store, { withdraw = {}, candidates = [], reason }) {
  const s = store.state.search, at = now(), withdrawn = [], recorded = [];
  if (!reason?.trim()) throw new Error('say why the library is being curated');
  if (!s?.candidates) throw new Error('No task library to curate');
  const removals = Object.entries(withdraw).map(([taskId, value]) => {
    const codes = typeof value === 'string' ? [value] : value;
    if (!Array.isArray(codes) || !codes.length || codes.some(code => typeof code !== 'string' || !Object.hasOwn(WITHDRAW_REASONS, code))) throw new Error(`invalid withdrawal reasons for ${taskId}`);
    const c = s.candidates[taskId];
    if (!c) throw new Error(`unknown task ${taskId}`);
    if (c.status !== 'admitted') throw new Error(`${taskId} is ${c.status}, not admitted`);
    const texts = codes.map(code => WITHDRAW_REASONS[code] ?? (() => { throw new Error(`unknown reason ${code}`); })());
    return {taskId, c, codes, texts};
  });
  for (const {taskId, c, codes, texts} of removals) {
    c.status = 'withdrawn'; c.withdrawnAt = at; c.withdrawnReasons = codes; c.withdrawnReason = texts.join(' ');
    withdrawn.push(taskId);
  }
  for (const candidate of candidates) {
    const { origin, targetDirection, mechanismSourceUrl, foundIn, ...fields } = candidate;
    if (!['search', 'self_proposed'].includes(origin)) throw new Error(`${fields.taskId}: origin must be search or self_proposed`);
    saveCandidate(store.state, fields, { origin, targetDirection, mechanismSourceUrl: mechanismSourceUrl ?? null, foundIn,
      researchRole: 'game_world', supportDomain: null });
    recorded.push(fields.taskId);
  }
  s.curation ??= [];
  s.curation.push({ at, reason, withdrawn, recorded });
  s.status = 'stopped'; s.phase = 'specify'; s.errorCode = 'library_curation';
  s.error = `Curated: ${withdrawn.length} withdrawn, ${recorded.length} recorded. Resume to specify, review, classify and audit.`;

  s.taxonomyHistory ??= [];
  if (s.taxonomy) s.taxonomyHistory.push({ at, reason: 'library curation', fingerprint: s.taxonomy.fingerprint, nodes: s.taxonomy.nodes.length });
  s.taxonomy = null;
  store.state.library = null;
  store.state.split = null;
  store.state.analysis = null;
  store.save();
  store.event('search_library_curated', { runId: s.runId, reason, withdrawn, recorded });
  return { withdrawn, recorded };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const args = process.argv.slice(2);
  const option = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
  const plan = option('--plan');
  if (!plan || plan.startsWith('--')) throw new Error('Usage: node curate-library.mjs --plan PLAN.json [--data DIRECTORY]');
  const curation = JSON.parse(readFileSync(resolve(plan), 'utf8'));
  if (!curation || typeof curation !== 'object' || Array.isArray(curation)) throw new Error('Curation plan must be an object');
  const store = openStore(resolve(option('--data') ?? join(ROOT, 'data')));
  console.log(JSON.stringify(curate(store, curation), null, 1));
}
