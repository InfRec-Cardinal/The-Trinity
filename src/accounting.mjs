import fs from 'node:fs';
import path from 'node:path';
import {digest, verifyLedger} from '../harness/src/core.mjs';
import {tokenUsage, usageReport, scoreReport, benchmarkScoreReport, routingBenchmarkScoreReport} from '../harness/src/metrics.mjs';

export function collectAccounting(directories) {
  const seen = new Set(), calls = new Map(), episodes = new Map(), sources = [], warnings = [], frozenSkills = new Map(), oracleSelections = new Map(), legacyAggregates = new Map();
  let duplicateCalls = 0, duplicateEpisodes = 0;
  const insert = (map, id, row, kind) => {
    if (map.has(id)) {
      if (digest(map.get(id)) !== digest(row)) throw Error('Conflicting accounting records for ' + kind + ' ' + id);
      if (kind === 'call') duplicateCalls++;
      if (kind === 'episode') duplicateEpisodes++;
      return;
    }
    map.set(id, row);
  };
  const visit = file => {
    const real = fs.realpathSync(file);
    if (seen.has(real)) return;
    seen.add(real);
    const stat = fs.statSync(real);
    if (stat.isDirectory()) {
      for (const entry of fs.readdirSync(real).sort()) if (!['node_modules', '.git', '__pycache__', 'objects'].includes(entry)) visit(path.join(real, entry));
      return;
    }
    if (path.basename(real) === 'events.jsonl') {
      const lines = fs.readFileSync(real, 'utf8').split('\n');
      if (lines.at(-1) !== '') warnings.push({kind: 'truncated_log', file: path.basename(path.dirname(real)) + '/events.jsonl'});
      const events = lines.slice(0, -1).filter(Boolean).map(line => JSON.parse(line));
      const chained = events.some(event => Object.hasOwn(event, 'hash') || Object.hasOwn(event, 'previous') || Object.hasOwn(event, 'sequence'));
      if (chained) verifyLedger(real);
      const routedResults = new Set(events.filter(event => event.type === 'routing_finished').map(event => event.payload.episodeId));
      let count = 0;
      for (const event of events) {
        if (!chained) {
          if (event.type === 'connection_usage') for (const call of event.calls) {insert(calls, call.callId, call, 'call'); count++;}
          continue;
        }
        if (event.type === 'model_usage') {insert(calls, event.payload.callId ?? event.hash, event.payload, 'call'); count++;}
        if (['episode_finished', 'routing_invalid', 'routing_finished'].includes(event.type)) {
          const {events, ...row} = event.payload;
          if (event.type === 'routing_finished' || !routedResults.has(row.episodeId)) insert(episodes, row.episodeId ?? event.hash, row, 'episode');
        }
        if (event.type === 'oracle_evaluated') {
          const row = event.payload;
          insert(oracleSelections, row.oracleId ?? event.hash, {selectionMetric: row.selectionMetric ?? 'success', selected: row.selected, totalCandidateExecutionCost: row.totalCandidateExecutionCost, totalCandidateAdaptationCost: row.totalCandidateAdaptationCost ?? null, totalCost: row.totalCost ?? null}, 'oracle');
        }
      }
      sources.push({kind: chained ? 'harness' : 'stage1_events', calls: count});
      return;
    }
    if (!real.endsWith('.json')) return;
    let state;
    try {state = JSON.parse(fs.readFileSync(real, 'utf8'));}
    catch {warnings.push({kind: 'unreadable_json', file: path.basename(real)}); return;}
    if (state?.artifact?.namespace === 'evaluation_skills') {
      if (digest(state.artifact) !== state.artifactDigest) throw Error('Frozen skill accounting integrity mismatch');
      const artifact = state.artifact;
      insert(frozenSkills, state.artifactDigest, {key: artifact.key, identity: artifact.identity, preparationEpisodeIds: artifact.preparationEpisodeIds,
        historicalPreparationCost: artifact.preparationCost, historicalPreparationUsage: artifact.preparationUsage}, 'frozen_skill');
      return;
    }
    if (!state?.key || !(Array.isArray(state.turns) || Array.isArray(state.messages))) return;
    const kind = Array.isArray(state.messages) ? 'stage2' : 'stage1';
    const legacyUsage = state.legacyUsage ?? (!Array.isArray(state.modelCalls) ? state.usage : null);
    if (legacyUsage && Object.values(legacyUsage).some(value => value > 0)) {
      const id = 'legacy-' + digest({kind, key: state.originalKey ?? state.key, sessionId: state.sessionId ?? null, startedAt: state.startedAt ?? null});
      const previous = legacyAggregates.get(id);
      const usage = tokenUsage({...legacyUsage, partial: true});
      if (previous) for (const key of ['input', 'output', 'cachedInput', 'cacheCreationInput']) {
        if (previous.usage[key] !== null) usage[key] = Math.max(previous.usage[key], usage[key] ?? 0);
      }
      legacyAggregates.set(id, {callId: id, legacyAggregate: true, usage: tokenUsage(usage), role: kind, phase: kind, operation: state.originalKey ?? state.key});
    }
    if (!Array.isArray(state.modelCalls)) warnings.push({kind, key: state.key, reason: 'Legacy checkpoint has no per-call accounting'});
    for (const [index, call] of (state.modelCalls ?? []).entries()) {
      const operation = state.originalKey ?? state.key;
      const id = call.callId ?? digest({kind, sessionId: state.sessionId ?? null, operation, index, call});
      if (!call.callId) warnings.push({kind, key: operation, index, reason: 'Legacy call identity is inferred; identical independent runs cannot be distinguished'});
      insert(calls, id, {...call, usage: tokenUsage(call.usage), role: kind, operation, phase: kind}, 'call');
    }
    sources.push({kind, key: state.key, calls: state.modelCalls?.length ?? 0});
  };
  for (const directory of directories) visit(directory);
  for (const row of legacyAggregates.values()) warnings.push({kind: row.role, key: row.operation, reason: 'Historical aggregate usage is included as an unattributed lower bound; request count is unknown'});
  const tokens = usageReport([...calls.values(), ...legacyAggregates.values()]);
  return {schema: 'trinity-accounting-v2', ...tokens, sources, warnings, duplicateCalls, duplicateEpisodes,
    accountingComplete: tokens.tokens.complete && warnings.length === 0,
    scores: scoreReport([...episodes.values()]), benchmarkScores: benchmarkScoreReport([...episodes.values()]), routingScores: routingBenchmarkScoreReport([...episodes.values()]), oracleSelections: [...oracleSelections.values()],
    legacyUsage: [...legacyAggregates.values()], frozenSkillProvenance: [...frozenSkills.values()], monetaryCost: null};
}
