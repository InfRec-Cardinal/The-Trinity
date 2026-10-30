import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
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
  for (const [taskId, codes] of Object.entries(withdraw)) {
    const c = s.candidates[taskId];
    if (!c) throw new Error(`unknown task ${taskId}`);
    if (c.status !== 'admitted') throw new Error(`${taskId} is ${c.status}, not admitted`);
    const texts = codes.map(code => WITHDRAW_REASONS[code] ?? (() => { throw new Error(`unknown reason ${code}`); })());
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
  store.save();
  store.event('search_library_curated', { runId: s.runId, reason, withdrawn, recorded });
  return { withdrawn, recorded };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { CURATION } = await import(join(ROOT, '.work', 'curation-plan.mjs'));
  const store = openStore(join(ROOT, 'data'));
  console.log(JSON.stringify(curate(store, CURATION), null, 1));
}
