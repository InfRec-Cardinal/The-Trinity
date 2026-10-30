import { fn } from './agent.mjs';

const forbidden = new Set(['__proto__', 'prototype', 'constructor']);
const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const clone = value => structuredClone(value);

export function patchSubmissionTool(name) {
  return fn(name, 'Correct only fields identified in validation feedback using JSON Pointer paths. '
    + 'Do not rewrite the entire submission or replace the root. Preserve its other fields and source quotations.', {
    operations: { type: 'array', minItems: 1, maxItems: 16, items: { type: 'object', properties: {
      op: { type: 'string', enum: ['set', 'remove'] },
      path: { type: 'string', minLength: 2, pattern: '^/.+', description: 'A field path such as /assignment/id or /fields/0/verdict. Escape ~ as ~0 and / as ~1.' },
      value: {},
    }, required: ['op', 'path'], additionalProperties: false } },
  });
}

const validateName = name => {
  if (typeof name !== 'string' || !name || forbidden.has(name)) throw new Error('a valid submission tool name is required');
};
const validateSubmission = value => {
  if (!isObject(value)) throw new Error('the submission to correct must be an object');
};
function storeDraft(run, submitName, submission, sourceCallId) {
  run.submissionDrafts ??= {};
  run.submissionDrafts[submitName] = { sourceCallId: sourceCallId ?? null, submission: clone(submission) };
  return clone(submission);
}

export function rememberSubmission(run, submitName, args) {
  validateName(submitName); validateSubmission(args);
  return storeDraft(run, submitName, args, run.activeToolCall?.id);
}

function latestSubmission(run, submitName) {
  for (let i = (run.turns?.length ?? 0) - 1; i >= 0; i--) {
    const turn = run.turns[i];
    if (turn.role !== 'assistant') continue;
    for (let j = (turn.content?.length ?? 0) - 1; j >= 0; j--) {
      const block = turn.content[j];
      if (block.type === 'tool_use' && block.name === submitName && isObject(block.input) && Object.keys(block.input).length) {
        return { sourceCallId: block.id ?? null, submission: block.input };
      }
    }
  }
  return null;
}

function pointer(path) {
  if (typeof path !== 'string' || !path.startsWith('/') || path.length < 2) throw new Error('a correction path must name a field with a leading /; root replacement is forbidden');
  return path.slice(1).split('/').map(part => {
    if (/~(?![01])/.test(part)) throw new Error('a JSON Pointer escape must be ~0 or ~1');
    const decoded = part.replace(/~1/g, '/').replace(/~0/g, '~');
    if (forbidden.has(decoded)) throw new Error('a correction path cannot name prototype properties');
    return decoded;
  });
}

function arrayIndex(segment, length, allowAppend) {
  if (!/^(0|[1-9][0-9]*)$/.test(segment)) throw new Error('an array correction path requires a canonical non-negative integer index');
  const index = Number(segment);
  if (!Number.isSafeInteger(index) || index > length || (!allowAppend && index === length)) throw new Error('an array correction index is out of range');
  return index;
}

function applyOperation(submission, operation) {
  if (!isObject(operation) || !['set', 'remove'].includes(operation.op)) throw new Error('a correction operation must be set or remove');
  const parts = pointer(operation.path);
  if (operation.op === 'set' && !Object.hasOwn(operation, 'value')) throw new Error('a set correction requires value');
  let parent = submission;
  for (const part of parts.slice(0, -1)) {
    if (!parent || typeof parent !== 'object') throw new Error('the correction parent must already exist');
    const key = Array.isArray(parent) ? arrayIndex(part, parent.length, false) : part;
    if (!Object.hasOwn(parent, key)) throw new Error('the correction parent must already exist');
    parent = parent[key];
  }
  if (!parent || typeof parent !== 'object') throw new Error('the correction parent must already exist');
  const last = parts.at(-1), key = Array.isArray(parent) ? arrayIndex(last, parent.length, operation.op === 'set') : last;
  if (operation.op === 'set') parent[key] = clone(operation.value);
  else {
    if (!Object.hasOwn(parent, key)) throw new Error('a remove correction must name an existing field');
    if (Array.isArray(parent)) parent.splice(key, 1);
    else delete parent[key];
  }
}

export function patchedSubmission(run, submitName, operations, seed = null) {
  validateName(submitName);
  if (!Array.isArray(operations) || !operations.length || operations.length > 16) throw new Error('a correction batch requires 1 to 16 operations');
  const latest = latestSubmission(run, submitName), draft = run.submissionDrafts?.[submitName];
  let source;
  if (latest) source = draft?.sourceCallId === latest.sourceCallId ? draft : latest;
  else if (seed) {
    validateSubmission(seed.submission);
    source = draft?.sourceCallId === (seed.sourceCallId ?? null) ? draft : seed;
  } else source = draft;
  if (!source) throw new Error('submit a nonempty full result before correcting its fields');
  validateSubmission(source.submission);
  const submission = clone(source.submission);
  for (const operation of operations) applyOperation(submission, operation);
  return storeDraft(run, submitName, submission, source.sourceCallId);
}
