import { fn, runAgent, checkArgs } from '../agent.mjs';
import { prompt } from '../prompts.mjs';
import { contentHash, now, readJson, writeJsonAtomic, redact } from '../core.mjs';
import { join } from 'node:path';
import { verifyQuotes } from '../capture.mjs';
import { supportsSearch } from '../model.mjs';
import { PAGE_TOOLS, pageHandlers } from './discover.mjs';
import { quoteList } from './schema.mjs';

export const LINEAGE_POLICY = 'library-wide-evidenced-lineage-v1';
const strings = { type: 'array', items: { type: 'string', minLength: 1 } };
const resourceSchema = { type: 'object', properties: { id: { type: 'string' }, name: { type: 'string', minLength: 3 }, kind: { type: 'string', minLength: 3 },
  aliases: strings, urls: strings, evidence: quoteList(1) }, required: ['id', 'name', 'kind', 'aliases', 'urls', 'evidence'], additionalProperties: false };
const taskSchema = { type: 'object', properties: { taskId: { type: 'string' }, resourceIds: strings,
  status: { type: 'string', enum: ['independent', 'shared', 'unknown'] }, consideredTaskIds: strings, evidence: quoteList(), reason: { type: 'string', minLength: 20 } },
  required: ['taskId', 'resourceIds', 'status', 'evidence', 'reason'], additionalProperties: false };
export const LINEAGE_TOOL = fn('submit_lineage_audit', 'Finalize previously staged resources and task verdicts with finalize=true and the exact library fingerprint. For a small registry, resources and tasks may be submitted together.', {
  comparedLibraryFingerprint: { type: 'string' },
  finalize: { type: 'boolean' },
  resources: { type: 'array', items: resourceSchema },
  tasks: { type: 'array', minItems: 1, items: taskSchema } }, []);
export const LINEAGE_BATCH_ROWS = 12;
export const LINEAGE_BATCH_BYTES = 24000;
export const LINEAGE_DRAFT_VERSION = 'evidenced-lineage-batches-v1';
export const STAGE_LINEAGE_RESOURCES_TOOL = fn('stage_lineage_resources', 'Durably stage or replace 1 to 12 canonical resources. Quotes are verified now. Use removeResourceIds when merging obsolete canonical ids. Send only one staging call per reply, below 24000 UTF-8 bytes.', {
  comparedLibraryFingerprint: { type: 'string' }, resources: { type: 'array', maxItems: LINEAGE_BATCH_ROWS, items: resourceSchema },
  removeResourceIds: { ...strings, maxItems: LINEAGE_BATCH_ROWS },
}, ['comparedLibraryFingerprint', 'resources']);
export const STAGE_LINEAGE_TASKS_TOOL = fn('stage_lineage_tasks', 'Durably stage or replace 1 to 12 task verdicts using registered canonical resource ids. This saves partial work, not approval of independence. Send only one staging call per reply, below 24000 UTF-8 bytes.', {
  comparedLibraryFingerprint: { type: 'string' }, tasks: { type: 'array', minItems: 1, maxItems: LINEAGE_BATCH_ROWS, items: taskSchema },
});
export const READ_LINEAGE_DRAFT_TOOL = fn('read_lineage_draft', 'Inspect durable staging progress or a page of saved resources/task verdicts. Use this after resuming and before finalization. Nothing is approved until the entire library passes final checks.', {
  section: { type: 'string', enum: ['status', 'resources', 'tasks'] }, offset: { type: 'integer' }, limit: { type: 'integer' },
}, ['section']);

const admitted = state => Object.values(state.search.candidates).filter(c => c.status === 'admitted').sort((a, b) => a.taskId.localeCompare(b.taskId)).map(c => ({
  taskId: c.taskId, name: c.name, kind: c.kind, sourceUrl: c.sourceUrl, origin: c.origin ?? 'search', specification: state.search.specs[c.taskId], review: state.search.reviews[c.taskId] }));
export const lineageFingerprint = state => contentHash(admitted(state));
export const isCurrentLineageAudit = state => Boolean(state.search?.lineageAudit?.policy === LINEAGE_POLICY && state.search.lineageAudit.fingerprint === lineageFingerprint(state));
export const declaredResources = spec => [...(spec?.lineage?.resources ?? []), ...(spec?.lineage?.sharedResources ?? [])];

export function resourceTokens(resource) {
  const names = [resource.id, resource.name, ...(resource.aliases ?? [])].filter(Boolean).map(x => `name:${String(x).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}`);
  const urls = (resource.urls ?? []).map(value => {
    try {
      const u = new URL(value); u.hash = ''; u.hostname = u.hostname.replace(/^www\./, '').toLowerCase();
      for (const k of [...u.searchParams.keys()]) if (/^utm_|^(ref|fbclid|gclid)$/i.test(k)) u.searchParams.delete(k);
      u.searchParams.sort();
      return `url:${u.hostname}${u.pathname.toLowerCase().replace(/\.git\/?$/, '').replace(/\/+$/, '')}${u.search}`;
    } catch { return null; }
  }).filter(Boolean);
  return [...new Set([...names.filter(n => n !== 'name:'), ...urls])];
}

export function resourcesOverlap(a, b) {
  const right = new Set(resourceTokens(b));
  return resourceTokens(a).some(token => right.has(token));
}

export function checkLineageAudit(args, tasks, dataDir, fingerprint = contentHash(tasks)) {
  const problems = [], ids = new Set(tasks.map(t => t.taskId)), registry = new Map(), rows = new Map();
  const entireLibraryCompared = args.comparedLibraryFingerprint === fingerprint;
  if (args.comparedLibraryFingerprint !== undefined && !entireLibraryCompared) problems.push('comparedLibraryFingerprint must match the current admitted library fingerprint');
  for (const r of args.resources) {
    if (!/^[a-z][a-z0-9-]{1,100}$/.test(r.id)) problems.push(`resource ${r.id} must have a stable kebab-case id`);
    if (registry.has(r.id)) problems.push(`duplicate canonical resource ${r.id}`);
    registry.set(r.id, r);
    if (!r.evidence.length) problems.push(`resource ${r.id} requires captured evidence`);
    problems.push(...verifyQuotes(dataDir, r.evidence, `resources.${r.id}.evidence`));
    for (const url of r.urls) if (!/^https?:\/\/\S+$/.test(url)) problems.push(`resource ${r.id} has an invalid URL`);
  }
  const resources = [...registry.values()];
  for (let i = 0; i < resources.length; i++) for (let j = i + 1; j < resources.length; j++) if (resourcesOverlap(resources[i], resources[j]))
    problems.push(`resources ${resources[i].id} and ${resources[j].id} share an alias or URL; merge them into one canonical resource`);
  for (const row of args.tasks) {
    if (!ids.has(row.taskId)) problems.push(`unknown task ${row.taskId}`);
    if (rows.has(row.taskId)) problems.push(`task ${row.taskId} must be audited exactly once`);
    rows.set(row.taskId, row);
    if (new Set(row.resourceIds).size !== row.resourceIds.length) problems.push(`task ${row.taskId} has duplicate resource ids`);
    for (const id of row.resourceIds) if (!registry.has(id)) problems.push(`task ${row.taskId} uses unknown canonical resource ${id}`);
    const considered = row.consideredTaskIds ?? (entireLibraryCompared ? [...ids].filter(id => id !== row.taskId) : []);
    if (considered.some(id => !ids.has(id) || id === row.taskId) || new Set(considered).size !== considered.length) problems.push(`task ${row.taskId} has invalid or duplicate comparison ids`);
    if (tasks.some(t => t.taskId !== row.taskId && !considered.includes(t.taskId))) problems.push(`task ${row.taskId} must consider every other admitted task in the library`);
    problems.push(...verifyQuotes(dataDir, row.evidence, `tasks.${row.taskId}.evidence`));
    if (row.status !== 'unknown' && (!row.resourceIds.length || !row.evidence.length)) problems.push(`task ${row.taskId}: ${row.status} requires a nonempty resource inventory and captured evidence`);
  }
  for (const task of tasks) {
    const row = rows.get(task.taskId);
    if (!row) { problems.push(`task ${task.taskId} must be audited exactly once`); continue; }
    const resources = row.resourceIds.map(id => registry.get(id)).filter(Boolean);
    for (const raw of declaredResources(task.specification)) if (!resources.some(r => resourcesOverlap(raw, r))) problems.push(`task ${task.taskId} omits declared resource ${raw.id} or its aliases from the canonical inventory`);
    if (row.status === 'independent') {
      for (const other of tasks) {
        if (other.taskId === task.taskId) continue;
        const otherRow = rows.get(other.taskId);
        const otherResources = [...declaredResources(other.specification), ...(otherRow?.resourceIds ?? []).map(id => registry.get(id)).filter(Boolean)];
        if (resources.some(r => otherResources.some(otherResource => resourcesOverlap(r, otherResource)))) problems.push(`task ${task.taskId} cannot be independent: a resource or alias overlaps ${other.taskId}`);
        if (!otherRow || otherRow.status === 'unknown' || !otherRow.resourceIds.length) problems.push(`task ${task.taskId} cannot be independent while ${other.taskId}'s inventory remains unknown`);
      }
    }
  }
  for (const r of registry.values()) if (!args.tasks.some(t => t.resourceIds.includes(r.id))) problems.push(`canonical resource ${r.id} is not assigned to any task`);
  return [...new Set(problems)];
}

export function createLineageDraft({ dataDir, runId, fingerprint, tasks, secrets = [], currentFingerprint = () => fingerprint }) {
  const path = join(dataDir, 'lineage-drafts', `${contentHash({ runId, fingerprint, version: LINEAGE_DRAFT_VERSION })}.json`);
  const taskIds = tasks.map(task => task.taskId).sort(), admittedIds = new Set(taskIds);
  const empty = { version: LINEAGE_DRAFT_VERSION, policy: LINEAGE_POLICY, runId, fingerprint, taskIds,
    resources: [], tasks: [], createdAt: now(), updatedAt: now() };
  let draft = readJson(path, empty);
  if (draft.version !== LINEAGE_DRAFT_VERSION || draft.policy !== LINEAGE_POLICY || draft.runId !== runId
    || draft.fingerprint !== fingerprint || contentHash(draft.taskIds) !== contentHash(taskIds)
    || !Array.isArray(draft.resources) || !Array.isArray(draft.tasks)) throw new Error('lineage staging checkpoint does not match the current contract and library');
  const fail = problems => { if (problems.length) throw new Error(problems.slice(0, 30).join('; ')); };
  const current = () => { if (currentFingerprint() !== fingerprint) throw new Error('the admitted library changed; resume lineage with its new fingerprint before staging or finalizing'); };
  const batch = (tool, args) => {
    current(); fail(checkArgs(tool.parameters, args));
    if (args.comparedLibraryFingerprint !== fingerprint) throw new Error('comparedLibraryFingerprint must match the current admitted library fingerprint');
    const encoded = JSON.stringify(args);
    if (Buffer.byteLength(encoded, 'utf8') > LINEAGE_BATCH_BYTES) throw new Error(`lineage batch exceeds ${LINEAGE_BATCH_BYTES} UTF-8 bytes; use fewer rows and concise evidence`);
    if (redact(encoded, secrets) !== encoded) throw new Error('lineage staging cannot persist credentials');
  };
  const save = candidate => {
    if (contentHash({ resources: candidate.resources, tasks: candidate.tasks }) === contentHash({ resources: draft.resources, tasks: draft.tasks })) return;
    const next = { ...candidate, updatedAt: now() };
    writeJsonAtomic(path, next); draft = next;
  };
  const status = () => {
    current(); const stagedIds = new Set(draft.tasks.map(row => row.taskId)), registered = new Set(draft.resources.map(resource => resource.id));
    return { version: LINEAGE_DRAFT_VERSION, fingerprint, resourcesStaged: draft.resources.length, tasksStaged: draft.tasks.length,
      tasksRequired: taskIds.length, missingTaskIds: taskIds.filter(id => !stagedIds.has(id)),
      canonicalResourceIds: draft.resources.map(resource => resource.id),
      tasksWithUnregisteredResources: draft.tasks.filter(row => row.resourceIds.some(id => !registered.has(id))).map(row => row.taskId),
      approved: false, guidance: 'Saved batches are drafts. Compare the complete library and run submit_lineage_audit with finalize=true; do not resubmit already saved rows unless correcting them.' };
  };
  const stageResources = args => {
    batch(STAGE_LINEAGE_RESOURCES_TOOL, args);
    const removals = args.removeResourceIds ?? [], incoming = args.resources;
    if (!incoming.length && !removals.length || incoming.length + removals.length > LINEAGE_BATCH_ROWS) throw new Error(`a resource batch must contain 1 to ${LINEAGE_BATCH_ROWS} total staged rows and removals`);
    const problems = [], registry = new Map(draft.resources.map(resource => [resource.id, resource]));
    if (new Set(removals).size !== removals.length) problems.push('resource removals must be unique');
    if (new Set(incoming.map(resource => resource.id)).size !== incoming.length) problems.push('a resource batch cannot stage the same canonical id twice');
    for (const id of removals) {
      if (incoming.some(resource => resource.id === id)) problems.push(`resource ${id} cannot be removed and staged in the same batch`);

      registry.delete(id);
    }
    for (const resource of incoming) {
      if (!/^[a-z][a-z0-9-]{1,100}$/.test(resource.id)) problems.push(`resource ${resource.id} must have a stable kebab-case id`);
      problems.push(...verifyQuotes(dataDir, resource.evidence, `resources.${resource.id}.evidence`));
      for (const url of resource.urls) if (!/^https?:\/\/\S+$/.test(url)) problems.push(`resource ${resource.id} has an invalid URL`);
      registry.set(resource.id, structuredClone(resource));
    }
    const resources = [...registry.values()].sort((a, b) => a.id.localeCompare(b.id));
    const tokenOwners = new Map(), collisions = new Set();
    for (const resource of resources) for (const token of resourceTokens(resource)) {
      for (const other of tokenOwners.get(token) ?? []) collisions.add(`resources ${other} and ${resource.id} share an alias or URL; merge them into one canonical resource and remove the obsolete id`);
      tokenOwners.set(token, [...(tokenOwners.get(token) ?? []), resource.id]);
    }
    problems.push(...collisions);
    fail(problems); save({ ...draft, resources }); return status();
  };
  const stageTasks = args => {
    batch(STAGE_LINEAGE_TASKS_TOOL, args);
    const problems = [], registry = new Map(draft.resources.map(resource => [resource.id, resource])), rows = new Map(draft.tasks.map(row => [row.taskId, row]));
    if (new Set(args.tasks.map(row => row.taskId)).size !== args.tasks.length) problems.push('a task batch cannot stage the same task twice');
    for (const row of args.tasks) {
      if (!admittedIds.has(row.taskId)) problems.push(`unknown task ${row.taskId}`);
      if (new Set(row.resourceIds).size !== row.resourceIds.length) problems.push(`task ${row.taskId} has duplicate resource ids`);
      for (const id of row.resourceIds) if (!registry.has(id)) problems.push(`task ${row.taskId} uses unknown canonical resource ${id}; stage that resource first`);
      const considered = row.consideredTaskIds ?? taskIds.filter(id => id !== row.taskId);
      if (considered.some(id => !admittedIds.has(id) || id === row.taskId) || new Set(considered).size !== considered.length)
        problems.push(`task ${row.taskId} has invalid or duplicate comparison ids`);
      if (taskIds.some(id => id !== row.taskId && !considered.includes(id))) problems.push(`task ${row.taskId} must consider every other admitted task in the library`);
      problems.push(...verifyQuotes(dataDir, row.evidence, `tasks.${row.taskId}.evidence`));
      if (row.status !== 'unknown' && (!row.resourceIds.length || !row.evidence.length)) problems.push(`task ${row.taskId}: ${row.status} requires a nonempty resource inventory and captured evidence`);
      const resources = row.resourceIds.map(id => registry.get(id)).filter(Boolean), task = tasks.find(task => task.taskId === row.taskId);
      for (const raw of declaredResources(task?.specification)) if (!resources.some(resource => resourcesOverlap(raw, resource)))
        problems.push(`task ${row.taskId} omits declared resource ${raw.id} or its aliases from the canonical inventory`);
      rows.set(row.taskId, structuredClone(row));
    }
    fail(problems); save({ ...draft, tasks: [...rows.values()].sort((a, b) => a.taskId.localeCompare(b.taskId)) }); return status();
  };
  const read = args => {
    current(); fail(checkArgs(READ_LINEAGE_DRAFT_TOOL.parameters, args));
    if (args.section === 'status') return status();
    const offset = args.offset ?? 0, limit = args.limit ?? LINEAGE_BATCH_ROWS;
    if (!Number.isSafeInteger(offset) || offset < 0 || !Number.isSafeInteger(limit) || limit < 1 || limit > LINEAGE_BATCH_ROWS)
      throw new Error(`offset must be nonnegative and limit must be 1 to ${LINEAGE_BATCH_ROWS}`);
    const rows = draft[args.section];
    return { section: args.section, fingerprint, total: rows.length, offset, rows: structuredClone(rows.slice(offset, offset + limit)),
      nextOffset: offset + limit < rows.length ? offset + limit : null, approved: false };
  };
  const finalize = args => {
    current(); fail(checkArgs(LINEAGE_TOOL.parameters, args));
    let result;
    if (args.finalize === true) {
      if (Object.hasOwn(args, 'resources') || Object.hasOwn(args, 'tasks')) throw new Error('finalize=true uses saved batches; omit resources and tasks');
      if (args.comparedLibraryFingerprint !== fingerprint) throw new Error('comparedLibraryFingerprint must match the current admitted library fingerprint');
      result = { comparedLibraryFingerprint: fingerprint, resources: structuredClone(draft.resources), tasks: structuredClone(draft.tasks) };
    } else {
      if (!Array.isArray(args.resources) || !Array.isArray(args.tasks)) throw new Error('stage resource/task batches, then submit { comparedLibraryFingerprint, finalize: true }; the legacy form requires complete resources and tasks');
      const { finalize: ignored, ...legacy } = args; result = structuredClone(legacy);
    }
    fail(checkLineageAudit(result, tasks, dataDir, fingerprint)); return result;
  };
  return { path, status, stageResources, stageTasks, read, finalize };
}

export async function auditLineage(ctx) {
  const { store } = ctx, state = store.state, s = state.search, cfg = state.config.search;
  if (isCurrentLineageAudit(state)) return s.lineageAudit;
  const tasks = admitted(state), fingerprint = lineageFingerprint(state);
  if (!tasks.length) throw new Error('no admitted tasks to audit');
  const staging = createLineageDraft({ dataDir: store.dataDir, runId: s.runId, fingerprint, tasks, secrets: [ctx.apiKey],
    currentFingerprint: () => lineageFingerprint(state) });
  const stageOnce = handler => (args, run) => {
    const previous = run.lineageStagingCall, id = run.activeToolCall?.id;
    if (previous?.turn === run.turn && previous.id !== id) throw new Error('only one lineage staging call is allowed per model reply; saved rows remain intact, stage the next batch in the next reply');
    const output = handler(args); run.lineageStagingCall = { turn: run.turn, id }; return output;
  };

  const auditTasks = tasks.map(({ specification, review, ...task }) => ({ ...task,
    specification: { summary: specification.summary, lineage: specification.lineage, sources: specification.sources,
      sourceFacts: { task: specification.sourceFacts?.task ?? [] } },
    review: { decision: review?.decision ?? null, specAt: review?.specAt ?? null, lineage: review?.lineage ?? null } }));
  const result = await runAgent(ctx, { key: `${s.runId}/lineage-${fingerprint}`, purpose: 'library-wide lineage audit', system: prompt('lineage'),
    kickoff: JSON.stringify({ policy: LINEAGE_POLICY, stagingVersion: LINEAGE_DRAFT_VERSION, fingerprint, tasks: auditTasks,
      rule: 'Compare every task against every other admitted task, across all directions and both protocol kinds. No missing information counts as independence. Inspect read_lineage_draft status first; stage at most 12 resource or task rows per reply and finalize the saved whole-library audit.' }),
    tools: [STAGE_LINEAGE_RESOURCES_TOOL, STAGE_LINEAGE_TASKS_TOOL, READ_LINEAGE_DRAFT_TOOL, LINEAGE_TOOL, ...PAGE_TOOLS], maxTurns: cfg.lineageTurns ?? cfg.reviewTurns, maxTokens: cfg.lineageTokens ?? 24000,
    searchBudget: supportsSearch(ctx.profile) ? (cfg.lineageSearches ?? 32) : 0,
    handlers: { ...pageHandlers(ctx), stage_lineage_resources: stageOnce(staging.stageResources), stage_lineage_tasks: stageOnce(staging.stageTasks),
      read_lineage_draft: staging.read, submit_lineage_audit: args => ({ finish: staging.finalize(args) }) } });
  s.lineageAudit = { policy: LINEAGE_POLICY, fingerprint, ...result,
    tasks: result.tasks.map(t => ({ ...t, consideredTaskIds: t.consideredTaskIds ?? tasks.filter(other => other.taskId !== t.taskId).map(other => other.taskId) })), at: now() };
  store.save();
  return s.lineageAudit;
}
