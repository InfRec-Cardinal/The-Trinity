import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { openStore } from '../src/store.mjs';
import { SEARCH_POLICY_VERSION } from '../src/search/schema.mjs';
import { now } from '../src/core.mjs';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

export function expandSearchAreas(store, areas, { policyVersion = SEARCH_POLICY_VERSION, reason } = {}) {
  const s = store.state.search;
  if (!s?.areas) throw new Error('an existing search run with planned areas is required');
  if (!reason?.trim()) throw new Error('say why the newly appended areas are needed');
  const added = [];
  for (const area of areas) {
    if (!/^[\x20-\x7e]{2,41}$/.test(area.id)) throw new Error(`area id ${area.id} must be 2-41 ASCII characters`);
    if (s.areas.some(existing => existing.id === area.id)) continue;
    if (!area.title?.trim() || !area.why?.trim() || !Array.isArray(area.queries) || !area.queries.length) throw new Error(`area ${area.id} needs a title, a rationale and query routes`);
    if (!['game_world', 'support'].includes(area.researchRole)) throw new Error(`area ${area.id} needs researchRole game_world or support`);
    s.areas.push({ ...area, supportDomain: area.researchRole === 'support' ? area.supportDomain ?? 'other' : null,
      status: 'pending', policyExpansion: policyVersion, policyExpansionReason: reason, addedAt: now() });
    added.push(area.id);
  }
  if (added.length) { store.save(); store.event('search_areas_expanded', { runId: s.runId, policyVersion, reason, addedAreaIds: added }); }
  return added;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const store = openStore(join(ROOT, 'data'));
  const reason = 'The task-input policy widened from excluding audio and video to excluding audio alone. Every existing area was swept while video protocols were out of scope, so the newly admissible scope has never been searched.';
  const added = expandSearchAreas(store, [
    { id: 'video-observation-game-worlds', researchRole: 'game_world',
      title: 'Interactive worlds whose per-step Player observation is video rather than a single frame',
      why: 'Every admitted playable task observes single frames, text or structured state, because video was excluded when these areas were swept. The distinct mechanism now admissible is an environment that returns a clip or a continuous stream after each action, so the agent must read motion, timing and events across frames to choose the next action. Streaming game environments, embodied simulators that hand back short clips, and interactive video protocols where the agent controls what is played next all belong here.',
      queries: [
        'interactive benchmark agent receives video clip observation after each action environment step streaming',
        'embodied agent benchmark continuous video stream observation action loop evaluation protocol',
        'interactive video game environment LLM agent video input per step official API trajectory logging',
        'agent controls playback chooses next segment video environment benchmark terminal outcome scored',
        'video streaming simulator benchmark temporal observation action budget success criterion 2026',
      ] },
    { id: 'video-understanding-benchmarks', researchRole: 'support', supportDomain: 'other',
      title: 'Fixed video evaluations with one scored answer or artifact per item and an official scorer',
      why: 'Video question answering, temporal grounding and long-video reasoning need discovery coverage. These fixed published evaluations provide one deliverable per item and an official scoring procedure. Classify their evidenced requirements alongside interactive tasks and apply the same train/unseen split rules.',
      queries: [
        'video question answering benchmark official evaluation script accuracy test split held out',
        'long video understanding benchmark official scorer multiple choice evaluation protocol 2025 2026',
        'temporal grounding benchmark video official metric IoU evaluation code released',
        'video reasoning benchmark official leaderboard evaluation server answer per item',
        'egocentric video benchmark question answering official evaluation protocol released annotations',
      ] },
  ], { reason });
  console.log(JSON.stringify({ added, areas: store.state.search.areas.length, searchStatus: store.state.search.status }));
}
