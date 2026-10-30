import { fn, runAgent, checkArgs } from '../agent.mjs';
import { patchSubmissionTool, patchedSubmission, rememberSubmission } from '../submission.mjs';
import { prompt } from '../prompts.mjs';
import { now } from '../core.mjs';
import { supportsSearch } from '../model.mjs';
import { verifyQuotes, captureMeta } from '../capture.mjs';
import { PAGE_TOOLS, pageHandlers } from './discover.mjs';
import { ASSIGNMENT_KEYS, REQUIRED_FIELDS, assignmentSchema, inputScopeSchema, checkAssignment, checkInterfaceAnswers, checkInputScope, routeOf, quoteList } from './schema.mjs';

export const SPECIFICATION_VERSION = 5;
const designFields = [...ASSIGNMENT_KEYS, 'success'];
const interfaceSchema = { type: 'object', properties: {
  officialInterface: { type: 'object', properties: { exists: { type: 'boolean' }, kind: { type: ['string', 'null'] }, url: { type: ['string', 'null'] }, evidence: quoteList() }, required: ['exists', 'kind', 'url', 'evidence'], additionalProperties: false },
  recording: { type: 'object', properties: { runHistory: { type: 'boolean' }, trajectories: { type: 'boolean' }, evidence: quoteList() }, required: ['runHistory', 'trajectories', 'evidence'], additionalProperties: false },
  missing: { type: ['string', 'null'] } }, required: ['officialInterface', 'recording', 'missing'], additionalProperties: false };
const scorerSchema = { type: 'object', properties: { official: { type: 'boolean' }, url: { type: ['string', 'null'] }, evidence: quoteList() }, required: ['official', 'url', 'evidence'], additionalProperties: false };
const resourceSchema = { type: 'object', properties: { id: { type: 'string' }, kind: { type: 'string' }, name: { type: 'string' },
  aliases: { type: 'array', items: { type: 'string' } }, urls: { type: 'array', items: { type: 'string' } }, evidence: quoteList(1) }, required: ['id', 'kind', 'evidence'], additionalProperties: false };
const lineageSchema = { type: 'object', properties: { status: { type: 'string', enum: ['independent', 'shared', 'unknown'] }, resources: { type: 'array', items: resourceSchema },
  sharedResources: { type: 'array', items: resourceSchema }, note: { type: 'string', minLength: 10 } }, required: ['status', 'resources', 'sharedResources', 'note'], additionalProperties: false };
const authoritySchema = { type: 'object', properties: { stars: { type: ['integer', 'null'] }, citations: { type: ['integer', 'null'] },
  evidence: { type: 'object', properties: { stars: quoteList(), citations: quoteList() }, required: ['stars', 'citations'], additionalProperties: false } },
  required: ['stars', 'citations', 'evidence'], additionalProperties: false };
const sourceFactSchema = { type: 'array', minItems: 1, maxItems: 2, items: { type: 'object', properties: { claim: { type: 'string', minLength: 10 }, evidence: quoteList(1) },
  required: ['claim', 'evidence'], additionalProperties: false } };
const designDecisionSchema = { type: 'array', items: { type: 'object', properties: { id: { type: 'string', minLength: 2 }, field: { type: 'string', enum: designFields },
  basis: { type: 'string', enum: ['reconstruction_design'] }, decision: { type: 'string', minLength: 10 }, preserves: { type: 'string', minLength: 10 },
  sourceFactFields: { type: 'array', minItems: 1, items: { type: 'string' } } }, required: ['id', 'field', 'basis', 'decision', 'preserves', 'sourceFactFields'], additionalProperties: false } };

export function specificationTool(kind) {
  const fields = REQUIRED_FIELDS[kind];
  return fn('submit_specification', 'Submit a concise task specification. Quote source facts once in sourceFacts; the host derives the evidence index. Stop when the required mechanisms and gates are established.', {
    assignment: assignmentSchema(),
    summary: { type: 'string', minLength: 20, maxLength: 600 },
    sourceFacts: { type: 'object', properties: Object.fromEntries(fields.map(f => [f, sourceFactSchema])), required: [...fields], additionalProperties: false },
    inputScope: inputScopeSchema(), designDecisions: designDecisionSchema, ...(kind === 'interactive' ? { interface: interfaceSchema } : { scorer: scorerSchema }), lineage: lineageSchema, authority: authoritySchema });
}
export const SCOPE_EXCLUSION_TOOL = fn('submit_scope_exclusion', 'Submit source evidence that this candidate requires audio task input; a fresh reviewer must support exclusion before the task is rejected.', {
  inputScope: inputScopeSchema(), reason: { type: 'string', minLength: 20 } });
export function checkScopeExclusion(args, dataDir) {
  const problems = checkInputScope(args.inputScope, { allowExcludedChannels: true });
  if (!args.inputScope?.channels?.includes?.('audio')) problems.push('scope exclusion must identify required audio task input');
  if (typeof args.reason !== 'string' || args.reason.trim().length < 20) problems.push('scope exclusion requires an explanation of the evidenced required task inputs');
  problems.push(...verifyQuotes(dataDir, args.inputScope?.evidence, 'inputScope.evidence'));
  return problems;
}
const quoteKey = q => `${q.captureId}\n${q.quote}`;
const quoteSet = list => new Set((list ?? []).map(quoteKey));
const sameQuotes = (a, b) => { const x = quoteSet(a), y = quoteSet(b); return x.size === y.size && [...x].every(q => y.has(q)); };

export function normalizeSpecification(args, kind) {
  if (!args || typeof args !== 'object' || Array.isArray(args) || args.evidence !== undefined) return args;
  const evidence = Object.fromEntries(REQUIRED_FIELDS[kind].map(field => {
    const seen = new Set(), quotes = [];
    for (const fact of Array.isArray(args.sourceFacts?.[field]) ? args.sourceFacts[field] : []) {
      for (const quote of Array.isArray(fact?.evidence) ? fact.evidence : []) {
        const key = quoteKey(quote);
        if (!seen.has(key)) { seen.add(key); quotes.push({ ...quote }); }
      }
    }
    return [field, quotes];
  }));
  return { ...args, evidence };
}

export function specificationArgumentProblems(args, kind, dataDir, { reuseDenseEvidence = false } = {}) {
  const schema = structuredClone(specificationTool(kind).parameters);
  if (reuseDenseEvidence) {
    for (const field of REQUIRED_FIELDS[kind]) delete schema.properties.sourceFacts.properties[field].maxItems;
    delete schema.properties.summary.maxLength;
  }
  const problems = checkArgs(schema, args);
  if (!problems.length) problems.push(...checkSpecification(args, kind, dataDir));
  return problems;
}

export function exactCountInQuotes(value, quotes) {
  if (!Number.isSafeInteger(value) || value < 0) return false;
  return (quotes ?? []).some(({ quote }) => [...String(quote).matchAll(/\d[\d,]*/g)].some(match => {
    const before = String(quote)[match.index - 1] ?? '', after = String(quote)[match.index + match[0].length] ?? '';
    if (/[\w.+-]/.test(before) || /[\w.%]/.test(after)) return false;
    const token = match[0];
    if (token.includes(',') && !/^\d{1,3}(,\d{3})+$/.test(token)) return false;
    return Number(token.replaceAll(',', '')) === value;
  }));
}
export function checkAuthority(authority, dataDir) {
  const problems = [];
  for (const metric of ['stars', 'citations']) {
    const value = authority?.[metric], evidence = authority?.evidence?.[metric];
    if (value !== null && (!Number.isSafeInteger(value) || value < 0)) problems.push(`authority.${metric} must be a non-negative exact integer or null`);
    if (!Array.isArray(evidence)) { problems.push(`authority.evidence.${metric} is required`); continue; }
    problems.push(...verifyQuotes(dataDir, evidence, `authority.evidence.${metric}`));
    if (value !== null && !exactCountInQuotes(value, evidence)) problems.push(`authority.${metric} needs captured evidence containing its exact count; unavailable or rounded counts must be null`);
    if (value === null && evidence.length) problems.push(`authority.evidence.${metric} must be empty when the count is unknown`);
  }
  return problems;
}
export function checkSpecification(args, kind, dataDir) {
  const providedEvidence = args?.evidence !== undefined;
  args = normalizeSpecification(args, kind);
  const problems = checkAssignment(args.assignment), fields = REQUIRED_FIELDS[kind];
  problems.push(...checkInputScope(args.inputScope));
  problems.push(...verifyQuotes(dataDir, args.inputScope?.evidence, 'inputScope.evidence'));
  for (const f of fields) {
    if (providedEvidence) problems.push(...verifyQuotes(dataDir, args.evidence?.[f], `evidence.${f}`));
    if (!args.evidence?.[f]?.length) problems.push(`evidence.${f} needs at least one quote`);
    const facts = args.sourceFacts?.[f];
    if (!Array.isArray(facts) || !facts.length) { problems.push(`sourceFacts.${f} is required; source claims and design decisions must be separate`); continue; }
    for (const [i, fact] of facts.entries()) {
      if (typeof fact.claim !== 'string' || fact.claim.trim().length < 10) problems.push(`sourceFacts.${f}[${i}].claim is required`);
      if (!fact.evidence?.length) problems.push(`sourceFacts.${f}[${i}] needs captured evidence`);
      problems.push(...verifyQuotes(dataDir, fact.evidence, `sourceFacts.${f}[${i}].evidence`));
    }
    if (!sameQuotes(args.evidence?.[f], facts.flatMap(fact => fact.evidence ?? []))) problems.push(`evidence.${f} must contain exactly the quotes used by sourceFacts.${f}`);
  }
  const decisions = args.designDecisions;
  if (!Array.isArray(decisions)) problems.push('designDecisions is required, including an empty array when no new design is needed');
  const ids = new Set();
  for (const [i, d] of (decisions ?? []).entries()) {
    if (!d.id || ids.has(d.id)) problems.push(`designDecisions[${i}].id must be unique`); ids.add(d.id);
    if (d.basis !== 'reconstruction_design') problems.push(`designDecisions[${i}] must be explicitly labeled reconstruction_design`);
    if (!designFields.includes(d.field)) problems.push(`designDecisions[${i}].field is not an assignment field`);
    if (!d.sourceFactFields?.length || d.sourceFactFields.some(f => !fields.includes(f))) problems.push(`designDecisions[${i}] must identify its existing sourceFactFields`);
    for (const key of ['decision', 'preserves']) if (typeof d[key] !== 'string' || d[key].trim().length < 10) problems.push(`designDecisions[${i}].${key} is required`);
  }
  if (kind === 'interactive') {
    problems.push(...checkInterfaceAnswers(args.interface));
    problems.push(...verifyQuotes(dataDir, args.interface?.officialInterface?.evidence, 'interface.officialInterface.evidence'));
    problems.push(...verifyQuotes(dataDir, args.interface?.recording?.evidence, 'interface.recording.evidence'));
    if (args.interface && routeOf(args.interface) === 'real2sim') for (const field of ['observation', 'actions', 'evaluation', 'generation', 'verification']) {
      if (!(decisions ?? []).some(d => d.field === field)) problems.push(`Real2Sim requires an explicit reconstruction design decision for ${field}`);
    }
  } else {
    if (!args.scorer?.official) problems.push('a static benchmark is admitted only with an official scoring procedure');
    if (!args.scorer?.evidence?.length) problems.push('scorer.evidence is required');
    problems.push(...verifyQuotes(dataDir, args.scorer?.evidence, 'scorer.evidence'));
  }
  const lineage = args.lineage ?? {}, resources = lineage.resources ?? [], shared = lineage.sharedResources ?? [];
  if (!['independent', 'shared', 'unknown'].includes(lineage.status)) problems.push('lineage.status must distinguish independent, shared and unknown');
  if (lineage.status !== 'unknown' && !resources.length) problems.push('a known lineage status requires an evidenced resource inventory');
  if (lineage.status === 'independent' && shared.length) problems.push('independent lineage cannot declare shared resources');
  if (lineage.status === 'shared' && !shared.length) problems.push('shared lineage must identify its shared resources');
  for (const [list, label] of [[resources, 'resources'], [shared, 'sharedResources']]) list.forEach((r, i) => {
    if (!/^[a-z][a-z0-9_-]{1,60}$/.test(r.id)) problems.push(`lineage.${label}[${i}].id must be a stable kebab or snake id`);
    if (!r.evidence?.length) problems.push(`lineage.${label}[${i}].evidence is required`);
    problems.push(...verifyQuotes(dataDir, r.evidence, `lineage.${label}[${i}].evidence`));
    if (label === 'sharedResources' && !resources.some(resource => resource.id === r.id)) problems.push(`lineage.sharedResources[${i}] must also appear in the complete resource inventory`);
    for (const url of r.urls ?? []) { try { if (!['http:', 'https:'].includes(new URL(url).protocol)) throw new Error(); } catch { problems.push(`lineage.${label}[${i}].urls must be web URLs`); } }
  });
  problems.push(...checkAuthority(args.authority, dataDir));
  return problems;
}

export function citedEvidence(args) {
  const rows = [], collect = (list, path) => (list ?? []).forEach((quote, i) => rows.push({ ...quote, path: `${path}[${i}]` }));
  for (const [field, quotes] of Object.entries(args.evidence ?? {})) collect(quotes, `evidence.${field}`);
  for (const [field, facts] of Object.entries(args.sourceFacts ?? {})) facts.forEach((fact, i) => collect(fact.evidence, `sourceFacts.${field}[${i}].evidence`));
  collect(args.inputScope?.evidence, 'inputScope.evidence');
  if (args.interface) { collect(args.interface.officialInterface.evidence, 'interface.officialInterface.evidence'); collect(args.interface.recording.evidence, 'interface.recording.evidence'); }
  if (args.scorer) collect(args.scorer.evidence, 'scorer.evidence');
  for (const key of ['resources', 'sharedResources']) (args.lineage?.[key] ?? []).forEach((r, i) => collect(r.evidence, `lineage.${key}[${i}].evidence`));
  for (const metric of ['stars', 'citations']) collect(args.authority?.evidence?.[metric], `authority.evidence.${metric}`);
  return rows;
}
export function sourcesOf(args, dataDir) {
  return [...new Set(citedEvidence(args).map(q => q.captureId))].map(captureId => ({ captureId, url: captureMeta(dataDir, captureId)?.url ?? null }));
}

export const isCurrentAdmission = (spec, review) => Boolean(spec?.schemaVersion === SPECIFICATION_VERSION && review?.schemaVersion === SPECIFICATION_VERSION
  && spec.outcome !== 'scope_exclusion' && spec.at && review.specAt === spec.at && review.decision === 'admit'
  && review.scope?.verdict === 'in_scope' && !checkInputScope(spec.inputScope).length);
export async function specifyTask(ctx, candidate, attempt, feedback = null) {
  const { store } = ctx, s = store.state.search, cfg = store.state.config.search;
  candidate.specificationInputs ??= {};

  const inputKey = `${SPECIFICATION_VERSION}:${attempt}`;
  candidate.specificationInputs[inputKey] ??= structuredClone({
    task: Object.fromEntries(['taskId', 'protocolId', 'name', 'kind', 'sourceUrl', 'summary', 'whyAgentTask', 'interfaceNote', 'origin', 'targetDirection', 'mechanismSourceUrl']
      .filter(key => candidate[key] !== undefined).map(key => [key, candidate[key]])),
    schemaVersion: SPECIFICATION_VERSION, attempt, reviewerFeedback: feedback, requiredFields: REQUIRED_FIELDS[candidate.kind],
    ...(candidate.reusableDraft ? { reusableDraft: candidate.reusableDraft } : {}),
    priorSources: [...new Map([...(s.specs[candidate.taskId]?.sources ?? []), ...(candidate.reusableSources ?? [])]
      .map(source => [source.captureId, source])).values()], resourceRegistry: s.lineageAudit?.resources ?? [],
  });
  store.save();
  const input = candidate.specificationInputs[inputKey], kind = input.task.kind;
  const agentKey = `${s.runId}/spec-${candidate.taskId}-${attempt}-v${SPECIFICATION_VERSION}`;

  const submitted = await runAgent(ctx, { key: agentKey, purpose: 'specification', system: prompt('specify'),
    kickoff: JSON.stringify(input),
    tools: [specificationTool(kind), patchSubmissionTool('patch_specification'), SCOPE_EXCLUSION_TOOL, ...PAGE_TOOLS], maxTurns: cfg.specifyTurns, maxTokens: cfg.specifyTokens ?? 20000, searchBudget: supportsSearch(ctx.profile) ? cfg.specifySearches : 0,
    handlers: { ...pageHandlers(ctx), submit_specification: (args, run) => {
      rememberSubmission(run, 'submit_specification', args);
      const problems = checkSpecification(args, kind, store.dataDir); if (problems.length) throw new Error(problems.join('; '));
      return { finish: normalizeSpecification(args, kind) }; },
      patch_specification: ({ operations }, run) => {
        const args = patchedSubmission(run, 'submit_specification', operations, input.reusableDraft);
        const reuseDenseEvidence = Boolean(input.reusableDraft)
          && run.submissionDrafts?.submit_specification?.sourceCallId === (input.reusableDraft.sourceCallId ?? null);
        const problems = specificationArgumentProblems(args, kind, store.dataDir, { reuseDenseEvidence });
        if (problems.length) throw new Error(problems.join('; ')); return { finish: normalizeSpecification(args, kind) };
      },
      submit_scope_exclusion: args => { const problems = checkScopeExclusion(args, store.dataDir); if (problems.length) throw new Error(problems.join('; ')); return { finish: { ...args, outcome: 'scope_exclusion' } }; } } });
  const result = submitted.outcome === 'scope_exclusion' ? submitted : normalizeSpecification(submitted, kind);
  if (result.outcome === 'scope_exclusion') {
    const problems = checkScopeExclusion(result, store.dataDir);
    if (problems.length) throw new Error(`cached scope exclusion failed current checks: ${problems.join('; ')}`);
    const exclusion = { schemaVersion: SPECIFICATION_VERSION, taskId: candidate.taskId, kind, attempt, outcome: 'scope_exclusion',
      inputScope: result.inputScope, reason: result.reason, sources: sourcesOf(result, store.dataDir), at: store.loadAgent(agentKey)?.finishedAt ?? now() };
    s.specs[candidate.taskId] = exclusion; store.save(); return exclusion;
  }
  const problems = checkSpecification(result, kind, store.dataDir);
  if (problems.length) throw new Error(`cached specification failed current checks: ${problems.join('; ')}`);
  const spec = { schemaVersion: SPECIFICATION_VERSION, taskId: candidate.taskId, kind, attempt, assignment: result.assignment, summary: result.summary,
    evidence: result.evidence, sourceFacts: result.sourceFacts, inputScope: result.inputScope, designDecisions: result.designDecisions,
    interface: result.interface ? { ...result.interface, route: routeOf(result.interface) } : null, scorer: result.scorer ?? null,
    lineage: result.lineage, authority: result.authority, sources: sourcesOf(result, store.dataDir), at: store.loadAgent(agentKey)?.finishedAt ?? now() };
  s.specs[candidate.taskId] = spec; store.save(); return spec;
}
