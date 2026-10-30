import {randomUUID} from 'node:crypto';

const fields = ['input', 'output', 'cachedInput', 'cacheCreationInput'];
const number = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
export function tokenUsage(raw) {
  const usage = {
    input: number(raw?.input ?? raw?.input_tokens), output: number(raw?.output ?? raw?.output_tokens),
    cachedInput: number(raw?.cachedInput ?? raw?.cache_read_input_tokens),
    cacheCreationInput: number(raw?.cacheCreationInput ?? raw?.cache_creation_input_tokens)
  };
  if (raw?.partial) usage.partial = true;
  usage.totalInput = [usage.input, usage.cachedInput, usage.cacheCreationInput].every(v => v !== null) ? usage.input + usage.cachedInput + usage.cacheCreationInput : null;
  usage.total = !usage.partial && usage.totalInput !== null && usage.output !== null ? usage.totalInput + usage.output : null;
  usage.knownTotalInput = (usage.input ?? 0) + (usage.cachedInput ?? 0) + (usage.cacheCreationInput ?? 0);
  usage.knownTotal = usage.knownTotalInput + (usage.output ?? 0);
  return usage;
}
export function modelCall(source, metadata = {}) {
  const records = source?.attemptRecords?.map(row => ({...row, usage: tokenUsage(row.usage)}));
  const usage = tokenUsage(source?.usage);
  if (records?.length) {
    for (const field of fields) usage[field] = records.every(row => row.usage[field] !== null) ? records.reduce((sum, row) => sum + row.usage[field], 0) : null;
    if (records.some(row => row.usage.partial)) usage.partial = true;
  }
  return {...metadata, callId: source?.callId ?? randomUUID(), model: source?.model ?? metadata.model ?? null,
    usage: tokenUsage(usage), ...(records ? {attemptRecords: records} : {}),
    unknownAttempts: records ? 0 : Math.max(0, (source?.attempts ?? 1) - 1)};
}
export function tokenSummary(calls) {
  const logicalCalls = calls.filter(call => !call.legacyAggregate);
  const legacyAggregates = calls.length - logicalCalls.length;
  const attempts = calls.flatMap(call => call.attemptRecords?.length ? call.attemptRecords : [call]);
  const usages = attempts.map(call => tokenUsage(call.usage));
  const unknownAttempts = calls.reduce((sum, call) => sum + (call.unknownAttempts ?? 0), 0);
  const result = {calls: logicalCalls.length, legacyAggregates, attemptCountComplete: legacyAggregates === 0, attempts: attempts.length + unknownAttempts,
    reportedCalls: logicalCalls.filter(c => c.usage?.input != null && c.usage?.output != null).length,
    failedCalls: logicalCalls.filter(c => c.failed).length, failedAttempts: attempts.filter(c => c.failed).length,
    partialAttempts: usages.filter(usage => usage.partial).length, unknownAttempts};
  for (const key of [...fields, 'totalInput', 'total']) {
    const values = usages.map(usage => usage[key]).filter(v => v !== null);
    const callValues = logicalCalls.map(call => tokenUsage(call.usage)[key]);
    result[key] = {known: values.reduce((a, b) => a + b, 0), missingCalls: callValues.filter(v => v === null).length,
      missingAttempts: usages.length - values.length + unknownAttempts};
  }
  result.totalInput.lowerBound = usages.reduce((sum, usage) => sum + usage.knownTotalInput, 0);
  result.total.lowerBound = usages.reduce((sum, usage) => sum + usage.knownTotal, 0);
  result.complete = result.total.missingAttempts === 0 && result.partialAttempts === 0;
  result.exactTotal = result.complete ? result.total.known : null;
  return result;
}
export function routingScore(row) {
  const policy = {scoringPolicy: 'routing-zero-failure-v1'};
  if (row.technicalFailure || row.invalidSelection) return {...row, ...policy, success: false,
    rawScore: row.rawScore ?? row.score ?? null, rawNormalizedScore: row.rawNormalizedScore ?? row.normalizedScore ?? null,
    score: 0, normalizedScore: 0, scoreSource: 'protocol_zero'};
  if (!Number.isFinite(row.score) && typeof row.success === 'boolean') return {...row, ...policy,
    rawScore: null, score: Number(row.success), normalizedScore: 100 * Number(row.success), scoreSource: 'terminal_outcome'};
  return {...row, ...policy};
}
export function scoreSummary(rows) {
  const valid = rows.filter(row => !row.technicalFailure && !row.invalidSelection);
  const routed = row => ['routed_evaluation', 'oracle_candidate'].includes(row.phase) || row.scoringPolicy === 'routing-zero-failure-v1';
  const protocolFailures = rows.filter(row => routed(row) && (row.technicalFailure || row.invalidSelection));
  const scored = [...valid, ...protocolFailures].map(row => routed(row) ? routingScore(row) : row);
  const outcomes = scored.filter(row => typeof row.success === 'boolean');
  const mixedScoreScales = new Set(scored.filter(row => Number.isFinite(row.score)).map(row => row.benchmarkId ?? row.taskId ?? row.worldDigest ?? 'unspecified')).size > 1;
  const scores = scored.map(row => row.score).filter(Number.isFinite);
  const successes = outcomes.filter(row => row.success).length;
  const costs = rows.map(row => row.executionCost ?? row.cost).filter(v => number(v) !== null);
  const rewards = rows.map(row => row.reward).filter(Number.isFinite);
  const normalized = scored.map(row => row.normalizedScore).filter(Number.isFinite);
  return {attempts: rows.length, validEpisodes: valid.length, technicalFailures: rows.filter(row => row.technicalFailure).length,
    protocolZeroEpisodes: protocolFailures.length,
    validEpisodeWinRate: valid.filter(row => typeof row.success === 'boolean').length ? valid.filter(row => row.success).length / valid.filter(row => typeof row.success === 'boolean').length : null,
    invalidSelections: rows.filter(row => row.invalidSelection).length, successes, failures: outcomes.length - successes,
    missingOutcomes: scored.length - outcomes.length, winRate: outcomes.length ? successes / outcomes.length : null,
    attemptWinRate: rows.length ? successes / rows.length : null, scoredEpisodes: scores.length, missingScores: scored.length - scores.length,
    scoreCoverage: scored.length ? scores.length / scored.length : null,
    mixedScoreScales, scoreSum: scores.length && !mixedScoreScales ? scores.reduce((a, b) => a + b, 0) : null,
    scoreMean: scores.length && !mixedScoreScales ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
    normalizationErrors: rows.filter(row => row.normalizationError).length, normalizedEpisodes: normalized.length,
    normalizedScoreMean: normalized.length && (!rows.some(routed) || normalized.length === scored.length) ? normalized.reduce((a, b) => a + b, 0) / normalized.length : null,
    availableNormalizedScoreMean: normalized.length ? normalized.reduce((a, b) => a + b, 0) / normalized.length : null,
    actionCost: costs.reduce((a, b) => a + b, 0), missingActionCosts: rows.length - costs.length,
    actionCostComplete: costs.length === rows.length && rows.every(row => (row.missingCosts ?? 0) === 0),
    actionAttempts: rows.reduce((sum, row) => sum + (row.actionAttempts ?? row.actions ?? 0), 0),
    actions: rows.reduce((sum, row) => sum + (row.actions ?? 0), 0),
    moduleCalls: rows.reduce((sum, row) => sum + (row.moduleCalls ?? 0), 0),
    moduleAttempts: rows.reduce((sum, row) => sum + (row.moduleAttempts ?? row.moduleCalls ?? 0), 0),
    rewardSum: rewards.length ? rewards.reduce((a, b) => a + b, 0) : null,
    reportedRewardSum: rows.reduce((sum, row) => sum + (row.reportedRewardSum ?? row.reward ?? 0), 0),
    missingRewardEpisodes: rows.length - rewards.length,
    terminalScores: valid.filter(row => row.scoreSource === 'terminal_receipt' && Number.isFinite(row.score)).length};
}
export function normalizeScore(score, specification) {
  if (!Number.isFinite(score) || !specification) return null;
  const {min, max, higherIsBetter = true} = specification;
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min || typeof higherIsBetter !== 'boolean') throw Error('Invalid score normalization range');
  if (score < min || score > max) throw Error('Host score is outside the declared normalization range');
  const fraction = (score - min) / (max - min);
  return 100 * (higherIsBetter ? fraction : 1 - fraction);
}
export function scoreReport(rows) {
  const buckets = new Map();
  for (const row of rows) {
    const dimensions = Object.fromEntries(['phase', 'benchmarkId', 'taskId', 'split', 'protocolId', 'iteration', 'node', 'worldDigest', 'harnessId', 'scoreNormalization'].map(key => [key, row[key] ?? null]));
    const key = JSON.stringify(dimensions);
    if (!buckets.has(key)) buckets.set(key, {dimensions, rows: []});
    buckets.get(key).rows.push(row);
  }
  return [...buckets.values()].map(bucket => ({...bucket.dimensions, ...scoreSummary(bucket.rows)}));
}
export function benchmarkScoreReport(rows) {
  const buckets = new Map();
  for (const row of rows) {
    const dimensions = Object.fromEntries(['phase', 'benchmarkId', 'split', 'protocolId', 'iteration', 'harnessId', 'scoreNormalization'].map(key => [key, row[key] ?? null]));
    if (!dimensions.benchmarkId) dimensions.benchmarkId = row.taskId ?? row.worldDigest ?? 'unassigned';
    const key = JSON.stringify(dimensions);
    if (!buckets.has(key)) buckets.set(key, {dimensions, rows: []});
    buckets.get(key).rows.push(row);
  }
  return [...buckets.values()].map(bucket => {
    const tasks = new Map();
    for (const row of bucket.rows) {
      const key = row.taskId ?? row.worldDigest ?? 'unassigned';
      if (!tasks.has(key)) tasks.set(key, []);
      tasks.get(key).push(row);
    }
    const summaries = [...tasks.values()].map(scoreSummary);
    const means = summaries.map(row => row.normalizedScoreMean).filter(Number.isFinite);
    return {...bucket.dimensions, ...scoreSummary(bucket.rows), tasks: tasks.size,
      normalizedTaskCoverage: tasks.size ? means.length / tasks.size : null,
      macroNormalizedScore: means.length === tasks.size && means.length ? means.reduce((a, b) => a + b, 0) / means.length : null};
  });
}
export function routingBenchmarkScoreReport(rows) {
  const groups = new Map();
  for (const row of rows.filter(row => row.phase === 'routed_evaluation')) {
    const identity = {benchmarkId: row.benchmarkId ?? 'unassigned', split: row.split ?? 'unassigned', protocolId: row.protocolId ?? null};
    const key = JSON.stringify(identity);
    if (!groups.has(key)) groups.set(key, {identity, rows: []});
    groups.get(key).rows.push(row);
  }
  const benchmarks = [...groups.values()].map(group => ({...group.identity, ...scoreSummary(group.rows)}));
  const splits = new Map();
  for (const benchmark of benchmarks) {
    const key = JSON.stringify([benchmark.split, benchmark.protocolId]);
    if (!splits.has(key)) splits.set(key, []);
    splits.get(key).push(benchmark);
  }
  return {benchmarks, splits: [...splits.values()].map(group => ({split: group[0].split, protocolId: group[0].protocolId,
    benchmarks: group.length, complete: group.every(row => Number.isFinite(row.normalizedScoreMean)),
    benchmarkEqualScore: group.every(row => Number.isFinite(row.normalizedScoreMean)) ? group.reduce((sum, row) => sum + row.normalizedScoreMean, 0) / group.length : null}))};
}
export function usageReport(calls) {
  const groups = {};
  for (const key of ['operation', 'role', 'node', 'phase', 'iteration', 'model', 'benchmarkId', 'taskId', 'split', 'protocolId']) {
    const buckets = new Map();
    for (const call of calls) {const value = String(call[key] ?? 'unassigned'); if (!buckets.has(value)) buckets.set(value, []); buckets.get(value).push(call);}
    groups[key] = Object.fromEntries([...buckets].map(([key, rows]) => [key, tokenSummary(rows)]));
  }
  return {tokens: tokenSummary(calls), groups};
}
