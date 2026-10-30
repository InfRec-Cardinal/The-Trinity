import { fn, runAgent } from '../agent.mjs';
import { assert, contentHash, now } from '../core.mjs';
import { prompt } from '../prompts.mjs';

const areaProperties = {
  id: { type: 'string', minLength: 2, maxLength: 41, pattern: '^[a-z][a-z0-9-]*$' },
  title: { type: 'string', minLength: 4 },
  why: { type: 'string', minLength: 20, description: 'The distinct game-world mechanism that the recorded pool has not adequately explored.' },
  queries: { type: 'array', minItems: 1, maxItems: 6, items: { type: 'string', minLength: 3 } },
  researchRole: { type: 'string', enum: ['game_world'] },
  supportDomain: { type: 'null' },
};

export const COVERAGE_TOOL = fn('submit_discovery_coverage', 'Report actual discovery coverage and at most three new game-world repair areas for missing mechanisms.', {
  verdict: { type: 'string', enum: ['covered', 'gaps'] },
  summary: { type: 'string', minLength: 30 },
  coveredMechanisms: { type: 'array', items: { type: 'object', properties: {
    mechanism: { type: 'string', minLength: 20 },
    candidateTaskIds: { type: 'array', minItems: 1, items: { type: 'string' } },
  }, required: ['mechanism', 'candidateTaskIds'], additionalProperties: false } },
  uncoveredMechanisms: { type: 'array', items: { type: 'string', minLength: 10 } },
  limitations: { type: 'array', minItems: 1, items: { type: 'string', minLength: 10 } },
  additionalAreas: { type: 'array', maxItems: 3, items: { type: 'object', properties: areaProperties,
    required: Object.keys(areaProperties), additionalProperties: false } },
});

export function discoveryCoverageInput(search, maxRepairAreas = 3) {
  const initialAreas = search.areas.filter(area => !area.coverageRepair);
  const roles = new Map(initialAreas.map(area => [area.id, area.researchRole ?? 'support']));
  const candidates = Object.values(search.candidates ?? {}).sort((a, b) => a.taskId.localeCompare(b.taskId)).map(candidate => {
    const foundInAreas = [...new Set([candidate.foundIn, ...(candidate.foundInAreas ?? [])].filter(Boolean))].sort();
    const researchRole = candidate.researchRole ?? (foundInAreas.some(id => roles.get(id) === 'game_world') ? 'game_world' : 'support');
    return { taskId: candidate.taskId, protocolId: candidate.protocolId, kind: candidate.kind,
      name: candidate.name, summary: candidate.summary, whyAgentTask: candidate.whyAgentTask,
      sourceUrl: candidate.sourceUrl, status: candidate.status, researchRole, foundInAreas };
  });
  return { maxRepairAreas, policy: { emphasis: 'distinct game-world interaction mechanisms',
    digitalInteraction: 'already represented as a small supporting sample; do not expand its catalogue',
    passes: 1, evidenceStatus: 'discovery records, not independently admitted source facts' },
  areas: initialAreas.map(area => ({ id: area.id, title: area.title, why: area.why, researchRole: area.researchRole ?? 'support',
    supportDomain: area.supportDomain ?? null, summary: area.summary ?? null, notReached: area.notReached ?? [],
    searches: area.searches ?? 0, searchResults: area.searchResults ?? 0, coverage: area.coverage ?? null })), candidates };
}

export function checkDiscoveryCoverage(args, input) {
  const problems = [], candidateIds = new Set(input.candidates.map(candidate => candidate.taskId));
  const gameCandidates = input.candidates.filter(candidate => candidate.researchRole === 'game_world' && candidate.kind === 'interactive');
  const supportCandidates = input.candidates.filter(candidate => candidate.researchRole === 'support');
  const referencedIds = new Set(args.coveredMechanisms.flatMap(finding => finding.candidateTaskIds));
  for (const finding of args.coveredMechanisms) for (const taskId of finding.candidateTaskIds)
    if (!candidateIds.has(taskId)) problems.push(`coverage finding references unknown candidate ${taskId}`);
  if (args.verdict === 'covered') {
    if (gameCandidates.length < 2) problems.push('no or very few interactive game-world candidates were recorded; report gaps and the actual limitation instead of covered');
    if (gameCandidates.length <= supportCandidates.length) problems.push('recorded game-world candidates do not outnumber supporting candidates; report the actual balance as a gap instead of claiming game-focused coverage is adequate');
    if (!args.coveredMechanisms.length) problems.push('a covered verdict must identify recorded mechanisms and their candidate ids');
    if (gameCandidates.filter(candidate => referencedIds.has(candidate.taskId)).length < 2) problems.push('a covered verdict must ground its game-world findings in at least two recorded interactive game candidates');
    if (args.uncoveredMechanisms.length || args.additionalAreas.length) problems.push('a covered verdict cannot simultaneously request coverage repairs');
  } else if (!args.uncoveredMechanisms.length) problems.push('a gaps verdict must state at least one actual missing or insufficiently explored mechanism');
  if (args.additionalAreas.length > input.maxRepairAreas) problems.push(`only ${input.maxRepairAreas} game-world repair areas are allowed in this one pass`);
  const ids = new Set(input.areas.map(area => area.id));
  for (const area of args.additionalAreas) {
    if (ids.has(area.id)) problems.push(`repair area id ${area.id} duplicates an existing area or another repair`);
    ids.add(area.id);
    if (area.researchRole !== 'game_world' || area.supportDomain !== null) problems.push('repair areas must explore game worlds, with researchRole game_world and supportDomain null');
  }
  return [...new Set(problems)];
}

export async function auditDiscoveryCoverage(ctx) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search;
  assert(s?.runId && Array.isArray(s.areas), 'discovery coverage requires an existing search run and planned areas');
  if (s.coverageAudit?.status === 'done') return s.coverageAudit;
  if (!s.coverageAudit) {
    assert(s.areas.filter(area => !area.coverageRepair).every(area => area.status === 'done'), 'complete the initial discovery areas before auditing their coverage');
    const maxRepairAreas = cfg.maxRepairAreas ?? 3;
    assert(Number.isInteger(maxRepairAreas) && maxRepairAreas >= 0 && maxRepairAreas <= 3, 'maxRepairAreas must be an integer from zero to three');
    const input = discoveryCoverageInput(s, maxRepairAreas), fingerprint = contentHash(input);
    s.coverageAudit = { status: 'pending', fingerprint, input, agentKey: `${s.runId}/coverage-${fingerprint}`,
      pass: 1, addedAreaIds: [], createdAt: now() };
    store.save();
  }
  const audit = s.coverageAudit;
  audit.status = 'running'; delete audit.error; delete audit.errorCode; store.save();
  ctx.emit?.('coverage_audit_start', { key: audit.agentKey, fingerprint: audit.fingerprint, pass: 1 });
  let result;
  try {
    result = await runAgent(ctx, { key: audit.agentKey, purpose: 'discovery coverage audit', system: prompt('coverage'),
      kickoff: JSON.stringify(audit.input), tools: [COVERAGE_TOOL], maxTurns: cfg.coverageTurns ?? 12,
      maxTokens: cfg.coverageTokens ?? 8000, searchBudget: 0,
      handlers: { submit_discovery_coverage: args => {
        const problems = checkDiscoveryCoverage(args, audit.input);
        if (problems.length) throw new Error(problems.slice(0, 12).join('; '));
        return { finish: args };
      } } });
  } catch (error) {
    audit.status = ctx.signal?.aborted || error.code === 'stopped' ? 'stopped' : 'error';
    audit.errorCode = error.code ?? 'agent_error';

    audit.error = store.loadAgent(audit.agentKey)?.lastError?.message ?? 'The coverage audit stopped before an accepted result.';
    store.save(); throw error;
  }
  for (const area of result.additionalAreas) {
    if (s.areas.some(existing => existing.id === area.id)) continue;
    s.areas.push({ ...area, status: 'pending', coverageRepair: true, coverageAuditFingerprint: audit.fingerprint });
  }
  Object.assign(audit, { status: 'done', result, addedAreaIds: result.additionalAreas.map(area => area.id), finishedAt: now() });
  store.save();
  ctx.emit?.('coverage_audit_end', { key: audit.agentKey, verdict: result.verdict, addedAreaIds: audit.addedAreaIds,
    summary: result.summary, limitations: result.limitations });
  return audit;
}
