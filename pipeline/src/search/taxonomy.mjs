import { fn, runAgent } from '../agent.mjs';
import { prompt } from '../prompts.mjs';
import { now, contentHash } from '../core.mjs';
import { ROOTS } from './schema.mjs';
import { isCurrentAdmission } from './specify.mjs';

export const TAXONOMY_TOOL = fn('submit_taxonomy', 'Submit the tree and the assignment of every task to one leaf.', {
  nodes: { type: 'array', minItems: 1, items: { type: 'object', properties: { id: { type: 'string' }, parentId: { type: 'string' }, label: { type: 'string', minLength: 3 }, definition: { type: 'string', minLength: 20 }, boundary: { type: 'string', minLength: 20 } },
    required: ['id', 'parentId', 'label', 'definition'], additionalProperties: false } },
  assignments: { type: 'array', items: { type: 'object', properties: { taskId: { type: 'string' }, nodeId: { type: 'string' }, reason: { type: 'string', minLength: 20 } }, required: ['taskId', 'nodeId'], additionalProperties: false } } });

export function rootOf(nodes, id) {
  const seen = new Set();
  let cur = id;
  while (!(cur in ROOTS)) { if (seen.has(cur) || !nodes.has(cur)) return null; seen.add(cur); cur = nodes.get(cur).parentId; }
  return cur;
}

export function checkTaxonomy(args, tasks) {
  const problems = [], ids = new Set(Object.keys(ROOTS)), nodes = new Map();
  for (const n of args.nodes) {
    if (!/^[a-z][a-z0-9-]{1,60}$/.test(n.id)) problems.push(`node id ${n.id} must be kebab-case`);
    if (ids.has(n.id)) problems.push(`node id ${n.id} is a duplicate or a reserved root id`);
    ids.add(n.id); nodes.set(n.id, n);
  }
  for (const n of args.nodes) if (!rootOf(nodes, n.id)) problems.push(`node ${n.id} does not descend from benchmarks (unknown parent or cycle)`);
  const children = new Map();
  for (const n of args.nodes) children.set(n.parentId, (children.get(n.parentId) ?? 0) + 1);
  const count = new Map(), held = new Map();
  for (const a of args.assignments) { count.set(a.taskId, (count.get(a.taskId) ?? 0) + 1); held.set(a.nodeId, [...(held.get(a.nodeId) ?? []), a.taskId]); }
  for (const t of tasks) if (count.get(t.taskId) !== 1) problems.push(`task ${t.taskId} must be assigned exactly once`);
  for (const a of args.assignments) {
    const t = tasks.find(x => x.taskId === a.taskId);
    if (!t) { problems.push(`unknown task ${a.taskId}`); continue; }
    if (!nodes.has(a.nodeId)) { problems.push(`task ${a.taskId} is assigned to unknown node ${a.nodeId}`); continue; }
    if (children.get(a.nodeId)) problems.push(`node ${a.nodeId} has children, so it cannot hold tasks`);
  }
  for (const n of args.nodes) if (!children.get(n.id) && !held.get(n.id)) problems.push(`node ${n.id} is empty`);

  const depth = id => { let d = 0; for (let cur = id; cur && !(cur in ROOTS); cur = nodes.get(cur)?.parentId) d++; return d; };
  for (const n of args.nodes) if (!children.get(n.id) && rootOf(nodes, n.id) === 'benchmarks' && depth(n.id) !== 2)
    problems.push(`leaf ${n.id} sits ${depth(n.id)} level(s) below benchmarks; a sub-class must have a domain as its parent (root -> domain -> sub-class)`);
  return [...new Set(problems)];
}

export const admittedTasks = state => Object.values(state.search.candidates).filter(c => c.status === 'admitted'
  && isCurrentAdmission(state.search.specs[c.taskId], state.search.reviews[c.taskId]))
  .sort((a, b) => a.taskId.localeCompare(b.taskId)).map(c => {
    const spec = state.search.specs[c.taskId];
    return { taskId: c.taskId, kind: c.kind, name: c.name, summary: spec?.summary ?? c.summary,
      assignment: spec?.assignment ?? null, goal: spec?.assignment?.task ?? null, observations: spec?.assignment?.observation ?? null,
      actions: spec?.assignment?.actions ?? null, successCriteria: spec?.assignment?.evaluation?.success ?? null, evaluation: spec?.assignment?.evaluation ?? null,
      route: c.kind === 'static' ? 'official_dataset' : spec?.interface?.route ?? null, interface: spec?.interface ?? null, scorer: spec?.scorer ?? null,
      inputScope: spec.inputScope, scopeReview: state.search.reviews[c.taskId].scope, sourceFacts: spec?.sourceFacts ?? null, designDecisions: spec?.designDecisions ?? [] };
  });

export const taxonomyFingerprint = state => contentHash({roots: ROOTS, tasks: admittedTasks(state)});

export const TAXONOMY_CONTEXT_BYTES = 850000;
export const TAXONOMY_DETAIL_BYTES = 8000;
const DETAIL_SECTIONS = Object.freeze(['name', 'summary', 'goal', 'observations', 'actions', 'successCriteria', 'evaluation',
  'inputScope', 'interface', 'scorer', 'sourceFacts', 'designDecisions']);
export const TAXONOMY_DETAILS_TOOL = fn('read_task_details', 'Read one section of an admitted reviewed task when its mechanics need clarification. Results are byte-bounded and paginated; this does not browse or change the task.', {
  taskId: { type: 'string' }, section: { type: 'string', enum: [...DETAIL_SECTIONS] }, offset: { type: 'integer' },
}, ['taskId', 'section']);

export function taxonomyContext(tasks, { maxBytes = TAXONOMY_CONTEXT_BYTES } = {}) {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error('The taxonomy context ceiling must be a positive integer byte count');
  const cards = tasks.map(t => ({ taskId: t.taskId, kind: t.kind, name: t.name, goal: t.goal,
    observations: t.observations, actions: t.actions, successCriteria: t.successCriteria, evaluation: t.evaluation,
    route: t.route, inputScope: { channels: t.inputScope?.channels ?? [], textRole: t.inputScope?.textRole ?? null },
    interface: t.interface ? { exists: t.interface.officialInterface?.exists ?? null, runHistory: t.interface.recording?.runHistory ?? null,
      trajectories: t.interface.recording?.trajectories ?? null } : null,
    scorer: t.scorer ? { official: t.scorer.official ?? null } : null,
    sourceFacts: t.sourceFacts ? Object.fromEntries(Object.entries(t.sourceFacts).map(([section, rows]) => [section,
      rows.map(row => ({ claim: row.claim }))])) : null }));
  const context = { version: 'reviewed-mechanism-cards-v1', taskCount: cards.length, maxBytes,
    detailTool: 'read_task_details', note: 'All admitted task IDs are present. sourceFacts contains reviewed published claims without repeated evidence; goal, observations, actions and evaluation describe the reviewed selected protocol. Full evidence and reconstruction decisions remain saved. Read details for ambiguous mechanics or explicit detailAvailable references.' };
  const payload = { roots: ROOTS, context, tasks: cards };
  const bytes = () => Buffer.byteLength(JSON.stringify(payload));
  if (bytes() > maxBytes) {
    const fields = cards.flatMap(card => ['name', 'goal', 'observations', 'actions', 'successCriteria', 'evaluation', 'sourceFacts'].map(section => ({ card, section,
      size: Buffer.byteLength(JSON.stringify(card[section] ?? null)) }))).sort((a, b) => b.size - a.size);
    for (const { card, section, size } of fields) {
      if (bytes() <= maxBytes) break;
      const reference = { detailAvailable: true, taskId: card.taskId, section, bytes: size };
      if (Buffer.byteLength(JSON.stringify(reference)) < size) card[section] = reference;
    }
    if (bytes() > maxBytes) throw new Error(`The complete taxonomy identity inventory exceeds its ${maxBytes}-byte context ceiling; tasks cannot be silently omitted.`);
  }
  return payload;
}

export function readTaxonomyTaskDetails(tasks, { taskId, section, offset = 0 }) {
  const task = tasks.find(t => t.taskId === taskId);
  if (!task) throw new Error(`Unknown admitted task ${taskId}`);
  if (!DETAIL_SECTIONS.includes(section)) throw new Error(`Unknown reviewed task section ${section}`);
  if (!Number.isSafeInteger(offset) || offset < 0) throw new Error('offset must be a nonnegative integer');
  const value = task[section] ?? null, text = typeof value === 'string' ? value : JSON.stringify(value);
  if (offset > text.length || (offset > 0 && /[\uDC00-\uDFFF]/.test(text[offset]) && /[\uD800-\uDBFF]/.test(text[offset - 1])))
    throw new Error('offset must be a valid returned character offset within this section');
  let end = offset, used = 0;
  for (const char of text.slice(offset)) {
    const size = Buffer.byteLength(char);
    if (used + size > TAXONOMY_DETAIL_BYTES) break;
    used += size; end += char.length;
  }
  return { taskId, section, format: typeof value === 'string' ? 'text' : 'json', offset, text: text.slice(offset, end),
    totalChars: text.length, totalBytes: Buffer.byteLength(text), nextOffset: end < text.length ? end : null };
}

export async function growTaxonomy(ctx) {
  const { store } = ctx, s = store.state.search, tasks = admittedTasks(store.state), fingerprint = taxonomyFingerprint(store.state);
  if (!tasks.length) throw new Error('no admitted task to organise');
  const result = await runAgent(ctx, { key: `${s.runId}/taxonomy-${fingerprint}`, purpose: 'task tree', system: prompt('taxonomy'),
    kickoff: JSON.stringify(taxonomyContext(tasks)), tools: [TAXONOMY_DETAILS_TOOL, TAXONOMY_TOOL], maxTurns: store.state.config.search.taxonomyTurns, maxTokens: store.state.config.search.taxonomyTokens ?? 24000,
    handlers: { read_task_details: (args, run) => {
      const result = readTaxonomyTaskDetails(tasks, args), bytes = Buffer.byteLength(JSON.stringify(result));
      if ((run.taxonomyDetailBytes ?? 0) + bytes > 150000) throw new Error('The supplemental reviewed-detail context ceiling is reached. Classify from the supplied mechanism cards and details already read; do not repeat detail requests.');
      run.taxonomyDetailBytes = (run.taxonomyDetailBytes ?? 0) + bytes;
      return result;
    }, submit_taxonomy: args => { const problems = checkTaxonomy(args, tasks); if (problems.length) throw new Error(problems.slice(0, 20).join('; ')); return { finish: args }; } } });
  s.taxonomy = { nodes: [...Object.entries(ROOTS).map(([id, r]) => ({ id, parentId: null, ...r })), ...result.nodes],
    assignments: Object.fromEntries(result.assignments.map(a => [a.taskId, a.nodeId])), assignmentReasons: Object.fromEntries(result.assignments.map(a => [a.taskId, a.reason ?? null])), fingerprint, grownAt: now() };
  store.save();
  return s.taxonomy;
}
