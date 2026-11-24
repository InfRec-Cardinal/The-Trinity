import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {askModelJson, costOf, PRICES, modelMetadata, unwrapJsonResponse} from './model-io.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SYSTEM = fs.readFileSync(path.join(HERE, 'prompts', 'judge-design.txt'), 'utf8');

const ID = /^[a-z][a-z0-9_]{0,15}$/;
const str = v => typeof v === 'string' && v.trim().length > 0;

export function validateDesign(d) {
  const errors = [];
  if (!d || typeof d !== 'object' || Array.isArray(d)) return ['Design must be a JSON object'];
  if (typeof d.capabilityId !== 'string' || !ID.test(d.capabilityId)) errors.push('capabilityId must start with a lowercase letter and contain at most 16 lowercase letters, digits or underscores');
  for (const k of ['capabilityName', 'definition', 'objective', 'observationStyle', 'scoring', 'creatorPrompt'])
    if (!str(d[k])) errors.push(k + ' is required');
  if (!Array.isArray(d.actions) || !d.actions.length || !d.actions.every(a => a && str(a.name) && str(a.effect)))
    errors.push('actions must be a non-empty list of {name, args, cost, effect}');
  if (!Array.isArray(d.difficultyDimensions) || !d.difficultyDimensions.every(x => x && str(x.name) && Array.isArray(x.range) && x.range.length === 2 && x.range.every(Number.isInteger)))
    errors.push('difficultyDimensions must each have {name, controls, range:[min,max]}');
  if (str(d.creatorPrompt) && d.creatorPrompt.length < 80) errors.push('creatorPrompt is too short to brief the Creator');
  return errors;
}

export async function judgeDesign({code, apiKey, relay, capabilityText, existingCapabilities = [], callModel}) {
  if (!str(capabilityText)) throw Error('Describe the capability to design a node for');
  const existing = (Array.isArray(existingCapabilities) ? existingCapabilities : []).slice(0, 200)
    .filter(c => c && typeof c.id === 'string').map(c => ({id: c.id, name: String(c.name ?? ''), definition: String(c.definition ?? '').slice(0, 600)}));
  const userText = JSON.stringify({operation: 'judge_design', capabilityDescription: capabilityText.trim(), existingCapabilities: existing});
  const fields = ['capabilityId', 'capabilityName', 'definition', 'objective', 'observationStyle', 'scoring', 'creatorPrompt', 'actions', 'difficultyDimensions', 'actionBudget'];
  const result = await askModelJson({code, apiKey, relay, system: SYSTEM, userText, callModel,
    normalizeResponse: value => unwrapJsonResponse(value, validateDesign, fields, ['design', 'data', 'result', 'response']), validateResponse: validateDesign});
  const {response, usage} = result;
  return {design: response, ...modelMetadata(result), cost: Number(costOf(usage, PRICES[relay?.model] ?? PRICES['claude-opus-5']).toFixed(4))};
}
