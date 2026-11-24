import fs from 'node:fs';
import fsp from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {askModelJson, costOf, PRICES, modelMetadata, withModelMetadata, unwrapJsonResponse} from './model-io.mjs';
import {validateDesign} from './design.mjs';
import {renderLevel} from './level-engine.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SYSTEM = fs.readFileSync(path.join(HERE, 'prompts', 'creator-level.txt'), 'utf8');
const NODE_ID = /^[a-z][a-z0-9_]{0,15}$/;
const nodeCheck = file => new Promise((resolve, reject) =>
  execFile(process.execPath, ['--check', file], err => err ? reject(Error('Generated module failed node --check: ' + String(err.message).slice(0, 300))) : resolve()));

const FORBIDDEN = [/^\s*import\s/m, /\brequire\s*\(/, /\bfetch\s*\(/, /\bprocess\b/, /\beval\s*\(/, /\bFunction\s*\(/, /\bXMLHttpRequest\b/, /\bWebSocket\b/, /\bimport\s*\(/];

export async function createLevel({code, apiKey, relay, design, vendorDir, callModel, feedback=null, screeningContract=null}) {
  const errors = validateDesign(design);
  if (errors.length) throw Error('Design is invalid: ' + errors.join('; '));
  if (!NODE_ID.test(design.capabilityId)) throw Error('Invalid capability ID');
  const node = design.capabilityId;

  const userText = JSON.stringify({operation: 'creator_build_level', design, feedback,
    ...(screeningContract?{screeningContract,instruction:'Preserve the frozen design and numeric actionBudget exactly. Respond to screening feedback only by tuning declared difficulty dimensions within their fixed ranges. Do not change objectives, observations, actions, scoring or add dimensions.'}:{})});
  const validateModule = value => value && typeof value === 'object' && !Array.isArray(value) && typeof value.module === 'string' && value.module.trim() ? [] : ['module must be a nonempty string containing the complete JavaScript source'];
  const validateResponse = async value => {
    const issues = validateModule(value);
    if (issues.length) return issues;
    const source = value.module;
    for (const re of FORBIDDEN) if (re.test(source)) throw Error('Module contains a forbidden construct: ' + re);
    if (!/export\s+function\s+createLevel\s*\(/.test(source)) return ['Module must export function createLevel'];
    const tmp = await fsp.mkdtemp(path.join(os.tmpdir(), 'trinity-level-'));
    try {
      const file = path.join(tmp, 'level.mjs');
      await fsp.writeFile(file, source);
      try {await nodeCheck(file);} catch (error) {return [error.message.replaceAll(tmp, '<generated>')];}
      return [];
    } finally {await fsp.rm(tmp, {recursive: true, force: true});}
  };
  const result = await askModelJson({code, apiKey, relay, system: SYSTEM, userText, maxTokens: 16000, callModel, validateResponse,
    normalizeResponse: value => unwrapJsonResponse(value, validateModule, ['module'], ['data', 'result', 'response'])});
  const {response, usage} = result;
  try {
  const source = typeof response?.module === 'string' ? response.module : null;
  if (!source) throw Error('Creator did not return a module string');
  const rendered = await renderLevel({source, node, variant: 0, actions: [], ...(vendorDir ? {vendorDir} : null)});
  if (!rendered.frames[0] || rendered.frames[0].length < 500) throw Error('Rendered frame is empty');
  return {
    ref: crypto.createHash('sha256').update(source).digest('hex'),
    source, node, variant: 0, budget: rendered.inspect.budget, rules: rendered.inspect.rules,
    capability: {id: design.capabilityId, name: design.capabilityName, definition: design.definition},
    design, ...modelMetadata(result), cost: Number(costOf(usage, PRICES[relay?.model] ?? PRICES['claude-opus-5']).toFixed(4)),
  };
  } catch (error) {throw withModelMetadata(error, result);}
}
