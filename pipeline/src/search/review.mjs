import { fn, runAgent, checkArgs } from '../agent.mjs';
import { patchSubmissionTool, patchedSubmission, rememberSubmission } from '../submission.mjs';
import { prompt } from '../prompts.mjs';
import { now, contentHash } from '../core.mjs';
import { readCapture, quoteContext } from '../capture.mjs';
import { REQUIRED_FIELDS, checkInputScope } from './schema.mjs';
import { citedEvidence, exactCountInQuotes, checkScopeExclusion, SPECIFICATION_VERSION } from './specify.mjs';

const READ_TOOL = fn('read_page', 'Read more captured source context by captureId, 6000 characters from offset.', { captureId: { type: 'string' }, offset: { type: 'integer' } }, ['captureId']);
const idsSchema = { type: 'array', items: { type: 'string' } }, reasonSchema = { type: 'string', minLength: 10 };
const countVerdictSchema = { type: 'object', properties: { verdict: { type: 'string', enum: ['supported', 'unknown', 'unsupported'] }, value: { type: ['integer', 'null'] },
  reason: reasonSchema, evidenceIds: idsSchema }, required: ['verdict', 'value', 'reason', 'evidenceIds'], additionalProperties: false };
export const SCOPE_EXCLUSION_REVIEW_TOOL = fn('submit_scope_exclusion_review', 'Independently judge whether the captured protocol proves required audio task input.', {
  verdict: { type: 'string', enum: ['supported', 'unsupported', 'insufficient'] }, reason: reasonSchema, evidenceIds: idsSchema, contextEvidenceIds: idsSchema });
export function reviewTool(kind) {
  return fn('submit_review', 'Review source support and design consistency separately, referencing supplied context evidence IDs.', {
    fields: { type: 'array', items: { type: 'object', properties: { field: { type: 'string', enum: [...REQUIRED_FIELDS[kind]] }, verdict: { type: 'string', enum: ['supported', 'unsupported', 'insufficient'] },
      reason: reasonSchema, evidenceIds: idsSchema }, required: ['field', 'verdict', 'reason', 'evidenceIds'], additionalProperties: false } },
    gate: { type: 'object', properties: { agree: { type: 'boolean' }, reason: reasonSchema, evidenceIds: idsSchema }, required: ['agree', 'reason', 'evidenceIds'], additionalProperties: false },
    scope: { type: 'object', properties: { verdict: { type: 'string', enum: ['in_scope', 'out_of_scope', 'insufficient'] }, reason: reasonSchema, evidenceIds: idsSchema },
      required: ['verdict', 'reason', 'evidenceIds'], additionalProperties: false },
    design: { type: 'object', properties: { assignmentVerdict: { type: 'string', enum: ['consistent', 'conflicting', 'insufficient'] }, reason: reasonSchema,
      decisions: { type: 'array', items: { type: 'object', properties: { id: { type: 'string' }, verdict: { type: 'string', enum: ['consistent', 'conflicting', 'insufficient'] }, reason: reasonSchema, evidenceIds: idsSchema },
        required: ['id', 'verdict', 'reason', 'evidenceIds'], additionalProperties: false } } }, required: ['assignmentVerdict', 'reason', 'decisions'], additionalProperties: false },
    lineage: { type: 'object', properties: { verdict: { type: 'string', enum: ['independent', 'shared', 'unknown'] }, agree: { type: 'boolean' }, reason: reasonSchema, evidenceIds: idsSchema },
      required: ['verdict', 'agree', 'reason', 'evidenceIds'], additionalProperties: false },
    authority: { type: 'object', properties: { stars: countVerdictSchema, citations: countVerdictSchema }, required: ['stars', 'citations'], additionalProperties: false },
    contextEvidenceIds: idsSchema, decision: { type: 'string', enum: ['admit', 'reject'] }, reason: reasonSchema });
}

export function collectContextualEvidence(spec, dataDir) {
  const contexts = [], dedupe = new Map();
  for (const row of citedEvidence(spec)) {
    const key = `${row.captureId}\n${row.quote}`;
    if (dedupe.has(key)) { dedupe.get(key).paths.push(row.path); continue; }
    const context = quoteContext(dataDir, row.captureId, row.quote, { before: 1000, after: 1000 });
    if (!context.ok) throw new Error(`cannot review ${row.path} without source context: ${context.reason}`);
    const entry = { evidenceId: `evidence-${contexts.length + 1}`, ...context, paths: [row.path] };
    contexts.push(entry); dedupe.set(key, entry);
  }
  return contexts;
}
const contextIdsFor = (contexts, predicate) => contexts.filter(context => context.paths.some(predicate)).map(context => context.evidenceId);
const prefixIds = (contexts, prefix) => contextIdsFor(contexts, path => path.startsWith(prefix));
const includesAll = (provided, required) => Array.isArray(provided) && required.every(id => provided.includes(id));
export function checkReview(args, kind, spec = null, contexts = null) {
  const problems = [], fields = args.fields ?? [];
  for (const f of REQUIRED_FIELDS[kind]) if (fields.filter(x => x.field === f).length !== 1) problems.push(`field ${f} must be reviewed exactly once`);
  for (const f of fields) if (!REQUIRED_FIELDS[kind].includes(f.field)) problems.push(`unexpected review field ${f.field}`);
  if (!args.design) problems.push('design must be reviewed separately from source facts');
  if (!args.scope || !['in_scope', 'out_of_scope', 'insufficient'].includes(args.scope.verdict)) problems.push('non-audio input scope must be reviewed explicitly');
  if (!args.lineage) problems.push('lineage must be reviewed explicitly');
  if (!args.authority) problems.push('authority counts must be reviewed explicitly');
  if (!spec || !Array.isArray(contexts) || !contexts.length) problems.push('review needs the specification and host-provided contextual evidence');
  if (spec && Array.isArray(contexts)) {
    const available = new Set(contexts.map(c => c.evidenceId));
    const requireContext = (ids, required, label) => {
      if (!Array.isArray(ids) || ids.some(id => !available.has(id))) problems.push(`${label} references unknown or missing contextual evidence IDs${Array.isArray(ids) ? `: ${ids.filter(id => !available.has(id)).join(', ')}` : ''}`);
      if (!includesAll(ids, required)) problems.push(`${label} must account for all relevant contextual evidence; missing IDs: ${required.filter(id => !ids?.includes?.(id)).join(', ')}`);
    };
    requireContext(args.contextEvidenceIds, [...available], 'contextEvidenceIds');
    for (const field of fields) {
      requireContext(field.evidenceIds, contextIdsFor(contexts, p => p.startsWith(`evidence.${field.field}[`) || p.startsWith(`sourceFacts.${field.field}[`)), `fields.${field.field}.evidenceIds`);
      if (field.verdict === 'supported' && !spec.sourceFacts?.[field.field]?.length) problems.push(`field ${field.field} cannot be supported until legacy source facts are explicitly separated from design`);
    }
    requireContext(args.gate?.evidenceIds, prefixIds(contexts, kind === 'interactive' ? 'interface.' : 'scorer.'), 'gate.evidenceIds');
    const scopeIds = prefixIds(contexts, 'inputScope.evidence[');
    requireContext(args.scope?.evidenceIds, [...new Set([...scopeIds, ...contextIdsFor(contexts, p => p.startsWith('evidence.observation[') || p.startsWith('sourceFacts.observation['))])], 'scope.evidenceIds');
    if (args.scope?.verdict === 'in_scope' && (!scopeIds.length || checkInputScope(spec.inputScope).length)) problems.push('in_scope requires evidenced task inputs excluding audio');
    const decisions = args.design?.decisions ?? [], expected = spec.designDecisions ?? [];
    for (const d of expected) {
      const matches = decisions.filter(x => x.id === d.id);
      if (matches.length !== 1) { problems.push(`design decision ${d.id} must be reviewed exactly once`); continue; }
      const linkedIds = contextIdsFor(contexts, p => (d.sourceFactFields ?? []).some(f => p.startsWith(`sourceFacts.${f}[`) || p.startsWith(`evidence.${f}[`)));
      requireContext(matches[0].evidenceIds, linkedIds, `design.decisions.${d.id}.evidenceIds`);
    }
    for (const d of decisions) if (!expected.some(x => x.id === d.id)) problems.push(`review names unknown design decision ${d.id}`);
    if (args.design?.assignmentVerdict === 'consistent' && decisions.some(d => d.verdict !== 'consistent')) problems.push('a consistent assignment cannot contain a conflicting or insufficient design decision');
    if (args.lineage) {
      requireContext(args.lineage.evidenceIds, prefixIds(contexts, 'lineage.'), 'lineage.evidenceIds');
      if (args.lineage.agree && args.lineage.verdict !== (spec.lineage?.status ?? 'unknown')) problems.push('lineage agreement must match the declared lineage status');
      if (args.lineage.verdict !== 'unknown' && !spec.lineage?.resources?.length) problems.push('a known lineage verdict needs the complete source resource inventory');
    }
    for (const metric of ['stars', 'citations']) {
      const review = args.authority?.[metric], count = spec.authority?.[metric] ?? null, evidence = spec.authority?.evidence?.[metric] ?? [];
      if (!review) { problems.push(`authority.${metric} must be reviewed`); continue; }
      requireContext(review.evidenceIds, prefixIds(contexts, `authority.evidence.${metric}[`), `authority.${metric}.evidenceIds`);
      if (review.value !== count) problems.push(`authority.${metric}.value must equal the submitted count, including null for unknown`);
      if (count === null && review.verdict !== 'unknown') problems.push(`authority.${metric} must remain unknown when no exact count was submitted`);
      if (count !== null && review.verdict === 'unknown') problems.push(`authority.${metric} must support or reject the submitted exact count`);
      if (review.verdict === 'supported' && !exactCountInQuotes(count, evidence)) problems.push(`authority.${metric} cannot be supported without captured exact-count evidence`);
    }
  }
  const holds = fields.length === REQUIRED_FIELDS[kind].length && fields.every(x => x.verdict === 'supported') && args.gate?.agree
    && args.scope?.verdict === 'in_scope' && spec && !checkInputScope(spec.inputScope).length
    && args.design?.assignmentVerdict === 'consistent' && (args.design?.decisions ?? []).every(d => d.verdict === 'consistent')
    && args.lineage?.agree && ['stars', 'citations'].every(metric => ['supported', 'unknown'].includes(args.authority?.[metric]?.verdict));
  if (args.decision === 'admit' && !holds) problems.push('admit requires source support, in_scope non-audio inputs, consistent design, gate and lineage agreement, and supported or unknown authority counts');
  if (args.decision === 'reject' && holds) problems.push('all review dimensions hold, so the decision must be admit');
  return problems;
}
export async function reviewSpec(ctx, candidate, spec, attempt) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search, kind = spec.kind;
  candidate.reviewInputs ??= {};
  const fingerprint = contentHash(spec), stamp = `${attempt}:${spec.at}:${fingerprint}`;

  const verifiedContexts = collectContextualEvidence(spec, store.dataDir);

  candidate.reviewInputs[stamp] ??= structuredClone({ task: { taskId: candidate.taskId, name: candidate.name, kind, sourceUrl: candidate.sourceUrl, origin: candidate.origin, attempt: spec.attempt },
      gate: kind === 'interactive' ? 'interface decision (official vs real2sim)' : 'official scorer', specification: { assignment: spec.assignment, summary: spec.summary,
        sourceFacts: spec.sourceFacts ?? null, inputScope: spec.inputScope ?? null, designDecisions: spec.designDecisions ?? [], interface: spec.interface, scorer: spec.scorer, lineage: spec.lineage, authority: spec.authority },
      specificationStamp: { at: spec.at, fingerprint }, requiredFields: REQUIRED_FIELDS[kind], pages: spec.sources, contextualEvidence: verifiedContexts,
      ...(candidate.reusableReviewDraft ? { reusableDraft: candidate.reusableReviewDraft } : {}),
      resourceRegistry: s.lineageAudit?.resources ?? [], legacySpecification: spec.schemaVersion !== SPECIFICATION_VERSION });
  store.save();
  const input = candidate.reviewInputs[stamp], contextualEvidence = input.contextualEvidence;
  const agentKey = `${s.runId}/review-${candidate.taskId}-${attempt}-v${SPECIFICATION_VERSION}`;
  const result = await runAgent(ctx, { key: agentKey, purpose: 'independent review', system: prompt('review'),
    kickoff: JSON.stringify(input),
    tools: [reviewTool(kind), patchSubmissionTool('patch_review'), READ_TOOL], maxTurns: cfg.reviewTurns, maxTokens: cfg.reviewTokens ?? 16000,
    handlers: { read_page: ({ captureId, offset = 0 }) => readCapture(store.dataDir, captureId, offset), submit_review: (args, run) => {
      rememberSubmission(run, 'submit_review', args);
      const problems = checkReview(args, kind, spec, contextualEvidence); if (problems.length) throw new Error(problems.join('; ')); return { finish: args }; },
      patch_review: ({ operations }, run) => {
        const args = patchedSubmission(run, 'submit_review', operations, input.reusableDraft);
        const problems = checkArgs(reviewTool(kind).parameters, args);
        if (!problems.length) problems.push(...checkReview(args, kind, spec, contextualEvidence));
        if (problems.length) throw new Error(problems.join('; ')); return { finish: args };
      } } });
  const problems = checkReview(result, kind, spec, contextualEvidence);
  if (problems.length) throw new Error(`cached review failed current checks: ${problems.join('; ')}`);
  const review = { schemaVersion: SPECIFICATION_VERSION, taskId: candidate.taskId, attempt, specAt: spec.at, ...result,
    contextCoverage: { provided: contextualEvidence.map(c => c.evidenceId), acknowledged: result.contextEvidenceIds, citations: contextualEvidence.length }, at: store.loadAgent(agentKey)?.finishedAt ?? now() };
  s.reviews[candidate.taskId] = review; store.save(); return review;
}

export function checkScopeExclusionReview(args, spec, contexts) {
  const problems = [], available = new Set((contexts ?? []).map(row => row.evidenceId));
  if (spec?.outcome !== 'scope_exclusion') problems.push('scope-only review cannot review a normal specification');
  if (!['supported', 'unsupported', 'insufficient'].includes(args.verdict)) problems.push('scope exclusion needs a supported, unsupported or insufficient verdict');
  if (!available.size) problems.push('scope exclusion requires host-provided source contexts');
  for (const name of ['evidenceIds', 'contextEvidenceIds']) {
    if (!Array.isArray(args[name]) || args[name].some(id => !available.has(id))) problems.push(`${name} references unknown or missing contextual evidence IDs`);
    if (!includesAll(args[name], [...available])) problems.push(`${name} must account for all scope exclusion evidence`);
  }
  return problems;
}

export async function reviewScopeExclusion(ctx, candidate, spec, attempt) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search;
  const problems = checkScopeExclusion(spec, store.dataDir);
  if (problems.length) throw new Error(`cannot review invalid scope exclusion: ${problems.join('; ')}`);
  const fingerprint = contentHash(spec), contexts = collectContextualEvidence(spec, store.dataDir);
  const agentKey = `${s.runId}/review-scope-exclusion-${candidate.taskId}-${attempt}-v${SPECIFICATION_VERSION}-${fingerprint}`;
  const result = await runAgent(ctx, { key: agentKey, purpose: 'independent scope exclusion review', system: prompt('scopeExclusionReview'),
    kickoff: JSON.stringify({ task: { taskId: candidate.taskId, name: candidate.name, kind: candidate.kind, sourceUrl: candidate.sourceUrl },
      exclusion: spec, contextualEvidence: contexts }), tools: [SCOPE_EXCLUSION_REVIEW_TOOL, READ_TOOL], maxTurns: cfg.reviewTurns, maxTokens: cfg.reviewTokens ?? 16000,
    handlers: { read_page: ({ captureId, offset = 0 }) => readCapture(store.dataDir, captureId, offset), submit_scope_exclusion_review: args => {
      const reviewProblems = checkScopeExclusionReview(args, spec, contexts); if (reviewProblems.length) throw new Error(reviewProblems.join('; ')); return { finish: args }; } } });
  const reviewProblems = checkScopeExclusionReview(result, spec, contexts);
  if (reviewProblems.length) throw new Error(`cached scope exclusion review failed current checks: ${reviewProblems.join('; ')}`);
  const review = { schemaVersion: SPECIFICATION_VERSION, taskId: candidate.taskId, attempt, specAt: spec.at, outcome: 'scope_exclusion_review', ...result,
    decision: result.verdict === 'supported' ? 'reject' : 'revise', fields: [],
    scope: { verdict: result.verdict === 'supported' ? 'out_of_scope' : 'insufficient', reason: result.reason, evidenceIds: result.evidenceIds },
    contextCoverage: { provided: contexts.map(c => c.evidenceId), acknowledged: result.contextEvidenceIds, citations: contexts.length },
    at: store.loadAgent(agentKey)?.finishedAt ?? now() };
  s.reviews[candidate.taskId] = review; store.save(); return review;
}
