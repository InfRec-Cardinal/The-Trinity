import { readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = join(dirname(dirname(fileURLToPath(import.meta.url))), 'prompts');
const TASK_SCOPE_FILE = 'task-input-scope.txt';
export const PROMPT_FILES = Object.freeze({
  plan: 's1-plan.txt', discover: 's1-discover.txt', coverage: 's1-coverage.txt', specify: 's1-specify.txt', review: 's1-review.txt', scopeExclusionReview: 's1-scope-exclusion-review.txt', taxonomy: 's1-taxonomy.txt', lineage: 's1-lineage.txt', supplement: 's1-supplement.txt',
});

export function prompt(name) {
  const file = PROMPT_FILES[name];
  if (!file) throw new Error(`unknown prompt ${name}`);
  return effectivePrompt(file);
}

const effectivePrompt = file => [readFileSync(join(DIR, TASK_SCOPE_FILE), 'utf8').trim(),
  readFileSync(join(DIR, file), 'utf8').trim()].join('\n\n');


