export const KINDS = Object.freeze(['interactive', 'static']);
export const SEARCH_POLICY_VERSION = 'non-audio-evidence-first-v5';

export const WIDENED_FROM = Object.freeze({ 'non-audio-evidence-first-v5': ['non-audio-video-evidence-first-v4'] });
export const policyWidensFrom = previous => (WIDENED_FROM[SEARCH_POLICY_VERSION] ?? []).includes(previous);

export const ROOTS = Object.freeze({
  benchmarks: { label: 'Benchmarks', definition: 'Published tasks with evidenced goals, permitted inputs, decisions and externally verifiable outcomes. Interactive protocols and fixed question or artifact evaluations share the same capability-based taxonomy and train/unseen split rules. Only audio task inputs are excluded. No task family or direction is prescribed.' },
});
export const REQUIRED_FIELDS = Object.freeze({ interactive: ['task', 'observation', 'actions', 'success', 'evaluation'], static: ['task', 'observation', 'success', 'evaluation'] });
export const ASSIGNMENT_KEYS = Object.freeze(['id', 'reference', 'task', 'observation', 'actions', 'evaluation', 'generation', 'verification']);


export const TEXT_ROLES = Object.freeze(['instructions_and_action_feedback', 'task_input_or_observation', 'none']);

export const quoteList = (min = 0) => ({ type: 'array', minItems: min, items: { type: 'object',
  properties: { captureId: { type: 'string' }, quote: { type: 'string', minLength: 8, maxLength: 600 } }, required: ['captureId', 'quote'], additionalProperties: false } });
export const inputScopeSchema = (minimumEvidence = 1) => ({ type: 'object', properties: {
  channels: { type: 'array', minItems: 1, items: { type: 'string', minLength: 1 } },
  textRole: { type: 'string', enum: [...TEXT_ROLES] }, evidence: quoteList(minimumEvidence) }, required: ['channels', 'textRole', 'evidence'], additionalProperties: false });

export function checkInputScope(scope, { requireEvidence = true, allowExcludedChannels = false } = {}) {
  if (!scope || typeof scope !== 'object' || Array.isArray(scope)) return ['inputScope is required to establish the actual non-audio task inputs'];
  const problems = [];
  if (!Array.isArray(scope.channels) || !scope.channels.length || scope.channels.some(channel => typeof channel !== 'string' || !/^[a-z][a-z0-9_-]{0,63}$/.test(channel))
    || new Set(scope.channels).size !== scope.channels.length) problems.push('inputScope.channels must be a nonempty unique list of stable lowercase input channel IDs');
  if (!allowExcludedChannels && scope.channels?.includes?.('audio')) problems.push('inputScope.channels cannot include audio task inputs');
  if (!TEXT_ROLES.includes(scope.textRole)) problems.push('inputScope.textRole must describe instruction text, task-input text or no text');
  if (!Array.isArray(scope.evidence) || (requireEvidence && !scope.evidence.length)) problems.push('inputScope.evidence needs captured evidence of the actual non-audio input protocol');
  return problems;
}

export const assignmentSchema = () => ({ type: 'object', properties: {
  ...Object.fromEntries(['id', 'reference', 'task', 'observation', 'generation', 'verification'].map(key => [key, { type: 'string', minLength: 1,
    description: 'A concise task-level description; implementation code and exhaustive details belong to environment integration.' }])),
  actions: { type: 'object', minProperties: 1, additionalProperties: { type: 'string', minLength: 1 },
    description: 'Map each permitted action ID to its concise description. Do not submit an array or a prose string.' },
  evaluation: { type: 'object', properties: { budget: { type: 'integer', minimum: 1 },
    ...Object.fromEntries(['success', 'failure', 'efficiency'].map(key => [key, { type: 'string', minLength: 1 }])) },
    required: ['budget', 'success', 'failure', 'efficiency'], additionalProperties: false },
}, required: [...ASSIGNMENT_KEYS], additionalProperties: false });

export function checkAssignment(a) {
  if (!a || typeof a !== 'object' || Array.isArray(a)) return ['assignment must be an object'];
  const problems = [];
  for (const k of ASSIGNMENT_KEYS) if (a[k] === undefined || a[k] === null || a[k] === '') problems.push(`assignment.${k} is required`);
  for (const k of Object.keys(a)) if (!ASSIGNMENT_KEYS.includes(k)) problems.push(`assignment.${k} is not one of the eight keys`);
  for (const k of ['id', 'reference', 'task', 'observation', 'generation', 'verification']) if (typeof a[k] !== 'string' || !a[k].trim()) problems.push(`assignment.${k} must be a non-empty string`);
  if (typeof a.id === 'string') {
    if (!/^[a-z][a-z0-9-]*$/.test(a.id)) problems.push('assignment.id must be kebab-case');
  }
  const acts = a.actions;
  if (!acts || typeof acts !== 'object' || Array.isArray(acts) || !Object.keys(acts).length
    || Object.entries(acts).some(([id, d]) => !id.trim() || typeof d !== 'string' || !d.trim())) problems.push('assignment.actions must map each action id to a description');
  const e = a.evaluation && typeof a.evaluation === 'object' ? a.evaluation : {};
  if (!Number.isInteger(e.budget) || e.budget < 1) problems.push('assignment.evaluation.budget must be a positive integer');
  for (const k of ['success', 'failure', 'efficiency']) if (typeof e[k] !== 'string' || !e[k].trim()) problems.push(`assignment.evaluation.${k} is required`);
  return problems;
}

export const routeOf = i => i.officialInterface.exists && i.recording.runHistory && i.recording.trajectories ? 'official' : 'real2sim';

export function checkInterfaceAnswers(i) {
  if (!i) return ['the interface answers are required for an interactive task'];
  const problems = [];
  if (i.officialInterface.exists && !i.officialInterface.evidence.length) problems.push('officialInterface.exists=true needs evidence');
  if (!i.officialInterface.exists && (i.recording.runHistory || i.recording.trajectories)) problems.push('recording cannot be true without an official interface');
  if ((i.recording.runHistory || i.recording.trajectories) && !i.recording.evidence.length) problems.push('a recording claim needs evidence');
  if (routeOf(i) === 'real2sim' && !String(i.missing ?? '').trim()) problems.push('say what is missing when the route is real2sim');
  return problems;
}


export const rank = (x, y) => (y.authority?.citations ?? -1) - (x.authority?.citations ?? -1) || (y.authority?.stars ?? -1) - (x.authority?.stars ?? -1) || x.taskId.localeCompare(y.taskId);
