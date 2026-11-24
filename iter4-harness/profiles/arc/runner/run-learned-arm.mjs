import {pathToFileURL} from 'node:url';
import {AppendOnlyDecision} from './append-only-decision.mjs';
import {parseMessage} from './native-decision-protocol.mjs';
const nativeConversations=new Map();
import {verifyModuleBuild} from '../verify-module-build.mjs';
verifyModuleBuild();
import {auditRequest} from './request-audit.mjs';
import {repairRequestContract} from './request-contract.mjs';
if(process.env.ARC_RESUME_EPISODE_DIR)throw Error('This runner starts a fresh episode; use the dedicated resume runner to continue a saved episode');
import {createArcBranch} from './branch-modules.mjs';
const branch=createArcBranch(process.env.H0_CAPABILITY_NODE),{activeBranch,branchTool,branchNotice,consultBranch}=branch;

import { mkdirSync, writeFileSync, readFileSync, existsSync, appendFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import {requestPolicy, requestAction, retainedProviderOutcome, consultationMessages, sanitizeToolCallHistory} from './player-protocol.mjs';
import {resolveStepBudget, finishWithStepBudget, stepBudgetPolicySha256, stepBudgetImplementationSha256} from './step-budgets.mjs';
import {autoResetArc} from './arc-auto-reset.mjs';

const unseenMode = process.argv.includes('--unseen') || process.env.H0_UNSEEN === '1';
const UNSEEN_ROOT = process.env.H0_UNSEEN_ENV_ROOT ?? process.env.H0_ENV_ROOT;
const ENV_ROOT = unseenMode
  ? UNSEEN_ROOT
  : (process.env.H0_ENV_ROOT ?? process.env.H0_ENV_ROOT);
const PIPELINE = process.env.H0_PIPELINE_ROOT ?? process.env.H0_PIPELINE_ROOT;

const BASE_URL = (process.env.RELAY_BASE_URL ?? 'https://api.anthropic.com').replace(/\/$/, '');
const MODEL = process.env.RELAY_MODEL ?? 'claude-opus-5';

const thinkingEffort = process.env.H0_THINKING_EFFORT ?? 'low';
const thinkingOn = !['low','off'].includes(thinkingEffort);

const argv = process.argv.slice(2);
const taskId = argv[0];
if (!taskId || taskId.startsWith('--')) { console.error('usage: run-learned-arm.mjs <taskId> [--unseen] [--max-episodes N] [--out DIR]'); process.exit(2); }
const flag = (name, fallback) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : fallback; };
const maxEpisodes = Number(flag('--max-episodes', '0')) || Infinity;
const outRoot = resolve(flag('--out', `./runs/${taskId}`));

const { installAnthropicAtomicRetry } = await import('../../../vendor/anthropic-atomic-retry.mjs');

const registryModule = await import(pathToFileURL(join(ENV_ROOT, 'interface/registry.mjs')).href);
const createRegistry = unseenMode
  ? registryModule.createUnseenDriverRegistry
  : (registryModule.createTrainDriverRegistry ?? registryModule.createTrain28DriverRegistry);

const prompt = await import(pathToFileURL(join(ENV_ROOT, 'interface/prompt.mjs')).href);
const legacyModules = await import('./capability-module-bridge.mjs');
const {isExecutableRegistry,createVerifiedSession,programTool,programPatches}=await import('./executable-module-bridge.mjs');
const {isPolicyRegistry,policyTool,policyPatches}=await import('./policy-module-bridge.mjs');
const {PolicySession,AdviceBudget,hash:policyHash}=await import('../policy-runtime/program.mjs');
const capabilityModulePromptPatches=r=>isPolicyRegistry(r)?policyPatches(r):isExecutableRegistry(r)?programPatches(r):legacyModules.capabilityModulePromptPatches(r);
const capabilityModuleTool=r=>isPolicyRegistry(r)?policyTool(r):isExecutableRegistry(r)?programTool(r):legacyModules.capabilityModuleTool(r);
const runCapabilityModule=legacyModules.runCapabilityModule;

const apiKey = (process.env.UPSTREAM_API_KEY ?? '').trim();
if (!apiKey) { console.error('UPSTREAM_API_KEY is required'); process.exit(2); }

installAnthropicAtomicRetry(BASE_URL, {
  maxRetries: Number(process.env.RELAY_PROVIDER_MAX_RETRIES ?? 2),
  retryBaseDelayMs: Number(process.env.RELAY_RETRY_BASE_DELAY_MS ?? 2000),
  maxRetryDelayMs: Number(process.env.RELAY_PROVIDER_MAX_RETRY_DELAY_MS ?? 60000),
  firstResponseTimeoutMs: Number(process.env.RELAY_FIRST_RESPONSE_TIMEOUT_MS ?? 120000),
  idleTimeoutMs: Number(process.env.RELAY_IDLE_TIMEOUT_MS ?? 90000),
  onProgress: event => log(`  [retry] ${JSON.stringify(event).slice(0, 200)}`),
});

mkdirSync(outRoot, { recursive: true });
const logPath = join(outRoot, 'runner.log');
function log(line) {
  const stamped = `${new Date().toISOString()} ${line}`;
  console.log(stamped);
  appendFileSync(logPath, stamped + '\n');
}

const frozen = prompt.loadFrozenHarness();
const skillsPath = process.env.H0_AUTHORED_SKILLS ?? join(PIPELINE, 'artifacts/bench-skills', `${taskId}.json`);
if (!existsSync(skillsPath)) { log(`FATAL no authored skills at ${skillsPath}`); process.exit(3); }
const authored = JSON.parse(readFileSync(skillsPath, 'utf8'));
const extensionPath=process.env.H0_EVOLVED_SKILLS;
let extension=extensionPath?JSON.parse(readFileSync(extensionPath,'utf8')):null;
if(extension){
 const {skillProposalSchema}=await import('../../../vendor/skill-schema.mjs');
 if(!Array.isArray(extension.replaces)||!extension.replaces.every(x=>typeof x==='string')||!Array.isArray(extension.proposals))throw Error('Invalid skill extension');
 extension.proposals=extension.proposals.map(p=>{const s=skillProposalSchema.parse(p);if(s.audience.length!==1||s.audience[0]!=='playing')throw Error('Playing skills only');return s;});
}
const initial=Array.isArray(authored.proposals)?authored.proposals:[];
if(extension){for(const id of extension.replaces)if(!initial.some(p=>p.id===id))throw Error('Unknown skill replacement: '+id);}
const proposals=extension?[...initial.filter(p=>!extension.replaces.includes(p.id)),...extension.proposals]:initial;
if(new Set(proposals.map(p=>p.id)).size!==proposals.length)throw Error('Duplicate effective skill IDs');
if (!proposals.length) { log(`FATAL ${taskId} has no proposals`); process.exit(3); }

const baselineArm = argv.includes('--baseline');
let learnedHarness = baselineArm ? frozen : {
  ...frozen,
  skills: [...frozen.skills, ...proposals.map(p => ({
    id: p.id, title: p.title, audience: p.audience ?? ['playing'], capability: p.capability,
    trigger: p.trigger, procedure: p.procedure,
    successSignals: p.successSignals, failureSignals: p.failureSignals,
    recovery: p.recovery, invariants: p.invariants,
    sourceGapIds: p.sourceGapIds ?? [], version: 1, status: 'frozen',
  }))],
};

const modulesPath = flag('--modules', '');
const moduleRegistry = modulesPath ? branch.scope.bindPolicy(JSON.parse(readFileSync(modulesPath, 'utf8')),{ownerId:branch.automaticId}) : null;
if(moduleRegistry && taskId==='arc_agi_3'){
  if(!branch.automaticId)throw Error('The ARC policy registry requires node d-a');
  const expected=JSON.parse(readFileSync(new URL('../../../module-harness/registries/arc_agi_3.json',import.meta.url),'utf8'));
  if(JSON.stringify(moduleRegistry)!==JSON.stringify(expected))throw Error('This integrated runner requires its matching generated registry; refusing stale module input');
}
const freeTools = Boolean(moduleRegistry) || argv.includes('--free-tools');
const moduleTool = moduleRegistry ? capabilityModuleTool(moduleRegistry) : null;

const TOS_SAFE = process.env.H0_MODULE_TOS_SAFE === '1';
if (moduleRegistry) {
  const components = learnedHarness.components ?? {};
  const patches = capabilityModulePromptPatches(moduleRegistry)
    .map(p => TOS_SAFE ? p.replace(/^Target capability node: .*\n?/gm, '') : p);
  learnedHarness = {
    ...learnedHarness,
    promptPatches: [...(learnedHarness.promptPatches ?? []), ...patches],
    components: {
      ...components,
      tools: { ...(components.tools ?? {}), ...(moduleTool ? { [moduleTool.name]: true } : {}) },
      mcp: { ...(components.mcp ?? {}), capability_modules: true },
      ...((TOS_SAFE||isExecutableRegistry(moduleRegistry)||isPolicyRegistry(moduleRegistry)) ? {} : { modules: moduleRegistry }),
    },
  };
}
learnedHarness={...learnedHarness,promptPatches:[...(learnedHarness.promptPatches??[]),branchNotice]};
writeFileSync(join(outRoot,'branch-provenance.json'),JSON.stringify({path:branch.path,globalModuleCount:29,active:activeBranch},null,2));
const harnessDigest = createHash('sha256').update(JSON.stringify(learnedHarness)).digest('hex');
if(isExecutableRegistry(moduleRegistry))writeFileSync(join(outRoot,'executable-runtime-provenance.json'),JSON.stringify({registryHash:createHash('sha256').update(JSON.stringify(moduleRegistry)).digest('hex'),files:Object.fromEntries(['program.mjs','registry.mjs','session.mjs','public-adapters.mjs','../../../shared/public-model-adapters.mjs'].map(f=>[f,createHash('sha256').update(readFileSync(new URL('../runtime/'+f,import.meta.url))).digest('hex')]))},null,2));
if(isPolicyRegistry(moduleRegistry))writeFileSync(join(outRoot,'policy-runtime-provenance.json'),JSON.stringify({registryHash:policyHash(moduleRegistry),files:Object.fromEntries(['../policy-runtime/program.mjs','../policy-runtime/worker.mjs','policy-module-bridge.mjs','player-protocol.mjs','run-learned-arm.mjs'].map(f=>[f,createHash('sha256').update(readFileSync(new URL(f,import.meta.url))).digest('hex')]))},null,2));
writeFileSync(join(outRoot, 'learned-harness.json'), JSON.stringify(learnedHarness, null, 2));

const registry = createRegistry({ root: ENV_ROOT });
const driver = await registry.getDriver(taskId);
if (!driver) {
  console.error(`${taskId}: no driver in ${ENV_ROOT}`
    + (unseenMode ? ' (buildarena_1_0 runs its own AutoGen workflow and is not served as a driver)' : ''));
  process.exit(2);
}

const configurationBudgets = driver.configurations.map(configuration => resolveStepBudget({
  taskId, driver, configuration, unseen: unseenMode, env: process.env,
}));

const presentation = taskId === 'eleusis'
  ? await import(pathToFileURL(join(registry.tasks.get('eleusis').folder, 'player-presentation.mjs')).href)
  : null;

function eleusisToolSchema() {
  const { oneOf, ...root } = presentation.eleusisActionParameters();
  const branchProps = Object.assign({}, ...oneOf.map(b => b.properties));
  return { ...root, properties: { ...root.properties, card: branchProps.card, statement: branchProps.statement } };
}
const taskSpec = registry.taskSpec(taskId);
const assignment = taskSpec?.spec?.assignment ?? taskSpec?.assignment;

const playerSettings = taskSpec?.player ?? {};
const contextPolicy = playerSettings.contextPolicy ?? null;
const imageOrder = playerSettings.imageOrder ?? 'after';
if (unseenMode && !contextPolicy) {
  console.error(`${taskId}: task.json has no player.contextPolicy; refusing to guess the context window`);
  process.exit(2);
}

const dropOrphanToolResults = turns => {
  const kept = [];
  for (const turn of turns) {
    if (turn.role === 'tool') {
      const prev = kept.at(-1);
      const ids = prev?.role === 'assistant'
        ? new Set(prev.content.filter(b => b.type === 'tool_use').map(b => b.id)) : new Set();
      if (!turn.results.every(r => ids.has(r.id))) continue;
    }
    kept.push(turn);
  }
  return kept.length === turns.length ? turns : kept;
};
const buildRequestTurns = unseenMode
  ? (stored, observation) => dropOrphanToolResults(prompt.unseenRequestTurns(contextPolicy, stored, observation, imageOrder))
  : (stored, observation) => dropOrphanToolResults(prompt.requestTurns(stored, observation));
const buildObservationTurn = unseenMode
  ? observation => prompt.unseenObservationTurn(observation, imageOrder)
  : observation => prompt.observationTurn(observation);
const buildToolResultTurn = unseenMode
  ? (toolId, observation) => prompt.unseenToolResultTurn(toolId, observation)
  : (toolId, observation) => prompt.toolResultTurn(toolId, observation);

const { moduleAwareSystem } = await import('./module-tool-instruction.mjs');
const system = moduleAwareSystem(prompt.renderFrozenH0(learnedHarness, assignment, driver.kind ?? 'interactive', driver.actionContract), moduleTool?.name).replace('The executor supplies the current observation and up to the last 12 public action/tool turns within a 180000-character context budget. Old complete exchanges are dropped together. Full trajectories are retained outside the Player context.','The executor supplies public observations and computed module feedback. After native thinking is enabled, complete tool exchanges and signatures are preserved in append-only wire history. Full trajectories remain archived.');

log(`task=${taskId} kind=${driver.kind} configurations=${driver.configurations.length}`);
log(`package=${unseenMode ? 'UNSEEN-17' : 'TRAIN-28'} root=${ENV_ROOT}`);
log(`conversation=${unseenMode ? `contextPolicy=${contextPolicy} imageOrder=${imageOrder} toolResultTerminal=null-until-end`
  : 'append-only signed wire history, public observation and module feedback'}`);
log(`arm=${baselineArm ? 'BASELINE (frozen harness only)'
  : moduleRegistry ? `MODULE+SKILLS (frozen + authored skills + ${Object.keys(moduleRegistry.active).join(',')})`
  : freeTools ? 'LEARNED/free-tools (frozen + authored skills, tool_choice=any)'
  : 'LEARNED (frozen + authored skills)'}`);
log(`frozen skills=${frozen.skills.length} + authored=${baselineArm ? 0 : proposals.length} -> arm skills=${learnedHarness.skills.length}`);
log('tool_choice=auto, disable_parallel_tool_use=true, thinking=adaptive/omitted, effort=low');
log(`learned harness sha256=${harnessDigest.slice(0, 16)}  system prompt=${system.length} chars`);

const MEDIA_TYPES = { png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', gif: 'image/gif', webp: 'image/webp' };
const mediaTypeFor = path => MEDIA_TYPES[String(path).split('.').pop().toLowerCase()] ?? 'image/png';
function toAnthropicContent(turn, runDir) {
  if (turn.role === 'user' && Array.isArray(turn.text)) {
    return turn.text.map(block => {
      if (block.type === 'text') return { type: 'text', text: block.text };

      if (block.type === 'image' && block.source) return block;

      const data = readFileSync(join(runDir, block.path)).toString('base64');
      return { type: 'image', source: { type: 'base64', media_type: mediaTypeFor(block.path), data } };
    });
  }
  if (turn.role === 'assistant') return turn.content;
  if (turn.role === 'tool') return turn.results.map(r => ({ type: 'tool_result', tool_use_id: r.id, content: r.output }));
  throw new Error(`unknown turn role ${turn.role}`);
}

async function callPlayer(turns, runDir, tool, forceEnvTool = false, forceModuleTool = false) {

  let messages = turns.map(t => ({
    role: t.role === 'tool' ? 'user' : t.role,
    content: toAnthropicContent(t, runDir),
  }));
  if(forceModuleTool&&!forceEnvTool&&moduleTool)messages=consultationMessages(messages,moduleTool.name);

  const CACHE = { type: 'ephemeral', ttl: process.env.RELAY_CACHE_TTL ?? '1h' };
  const cachedSystem = [{ type: 'text', text: system, cache_control: CACHE }];
  const last = messages.at(-1);
  if (last && Array.isArray(last.content) && last.content.length) {
    last.content = last.content.map((b, i) =>
      i === last.content.length - 1 ? { ...b, cache_control: CACHE } : b);
  }

  const asTool=t=>({name:t.name,description:t.description,input_schema:t.parameters});
  const policy=requestPolicy({effort:thinkingEffort,environmentTool:asTool(tool),
    moduleTool:moduleTool?asTool(moduleTool):null,forceEnvironment:forceEnvTool,forceModule:forceModuleTool});
  policy.tools.push(branchTool);
  const body={model:MODEL,max_tokens:thinkingOn?Number(process.env.H0_MAX_TOKENS??24000):16384,
    system:cachedSystem,...policy,messages,stream:true};
  let result;
  try { result=await requestAction({body,allowTextAction:process.env.H0_TEXT_ACTION_ADAPTER==='1',post:async request=>{
    const captureId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const sanitized = sanitizeToolCallHistory(request);
    request = sanitized.body;
    if (sanitized.removed) appendFileSync(join(runDir,'transport-sanitizations.jsonl'),JSON.stringify({captureId,adapter:'strip_response_tool_caller_v1',removed:sanitized.removed})+'\n');
    const repaired=repairRequestContract(request);
    request=repaired.request;
    appendFileSync(join(runDir,'request-contract-repairs.jsonl'),JSON.stringify({captureId,...repaired.audit})+'\n');
    if(!nativeConversations.has(runDir))nativeConversations.set(runDir,new AppendOnlyDecision());
    request=nativeConversations.get(runDir).prepare(request);
    const wireAudit=auditRequest(request);
    appendFileSync(join(runDir,'wire-request-provenance.jsonl'),JSON.stringify({captureId,...wireAudit})+'\n');
    if(!wireAudit.valid)throw Error('Invalid tool history: '+JSON.stringify(wireAudit.errors));
    writeFileSync(join(runDir,'effective-request-config.json'),JSON.stringify({captureId,systemSha256:wireAudit.systemSha256,toolsSha256:wireAudit.toolsSha256,requestSha256:wireAudit.requestSha256,model:request.model,thinking:request.thinking},null,2));
    appendFileSync(join(runDir,'api-requests.jsonl'),JSON.stringify({captureId,request})+'\n');
    if(process.env.ARC_FIX_VERIFY_ONLY==='1'){
      writeFileSync(join(runDir,'fixed-request-ready.json'),JSON.stringify({captureId,...repaired.audit,newPaidCalls:0},null,2));
      process.exit(0);
    }
    const response=await fetch(`${BASE_URL}/v1/messages`,{method:'POST',
      headers:{'content-type':'application/json','x-api-key':apiKey,'anthropic-version':'2023-06-01'},body:JSON.stringify(request)});
    const raw = (await response.text()).replaceAll(apiKey, '[redacted]');
    appendFileSync(join(runDir,'api-responses.jsonl'),JSON.stringify({captureId,status:response.status,raw})+'\n');
    if(!response.ok)throw new Error(`HTTP ${response.status}: ${raw.slice(0,400)}`);
    nativeConversations.get(runDir).accept(parseMessage(raw));
    return raw;
  }}); } catch(error) {
    appendFileSync(join(runDir,'protocol-errors.jsonl'),JSON.stringify({error:error.message,
      effort:thinkingEffort,offered:policy.tools.map(t=>t.name),toolChoice:policy.tool_choice,
      stopReason:error.responseStopReason??null,stopDetails:error.responseStopDetails??null,usage:error.responseUsage??null,
      returnedToolCalls:error.responseToolCalls??null,usageKnown:Boolean(error.responseUsage)})+'\n');
    throw error;
  }
  appendFileSync(join(runDir,'protocol-calls.jsonl'),JSON.stringify({effort:thinkingEffort,
    offered:policy.tools.map(t=>t.name),toolChoice:policy.tool_choice,toolName:result.toolName,
    transportAdapter:result.transportAdapter??null,stopReason:result.stopReason,stopDetails:result.stopDetails??null,usage:result.usage,thinkingBlocks:result.assistantContent.filter(b=>b.type==='thinking').length})+'\n');
  return result;
}

const plan = [];
driver.configurations.forEach((cfg, index) => {
  const n = cfg.episodes ?? 1;
  for (let k = 1; k <= n; k++) plan.push({ id: `case-${index}-repeat-${k}`, configurationIndex: index, caseId: cfg.id });
});

const casesArg = flag('--cases', '');
if (casesArg) {
  const wanted = casesArg.split(',').map(s => s.trim()).filter(Boolean);
  const known = new Set(driver.configurations.map(cfg => cfg.id));
  const unknown = wanted.filter(id => !known.has(id));
  if (unknown.length) {
    console.error(`--cases: ${taskId} has no configuration ${unknown.join(', ')}`);
    process.exit(2);
  }
  const keep = new Set(wanted);
  const selected = plan.filter(episode => keep.has(episode.caseId));
  plan.length = 0; plan.push(...selected);
  log(`cases: ${plan.length} episodes pinned by configuration id (${wanted.join(', ')})`);
}

const shardArg = flag('--shard', '');
const serialRequested = argv.includes('--serial');
let shardIndex = 1, shardTotal = 1;
if (shardArg) {
  const match = /^(\d+)\/(\d+)$/.exec(shardArg);
  if (!match) { console.error(`--shard must look like i/n, got ${shardArg}`); process.exit(2); }
  shardIndex = Number(match[1]); shardTotal = Number(match[2]);
  if (shardIndex < 1 || shardIndex > shardTotal) { console.error(`--shard ${shardArg} is out of range`); process.exit(2); }
}
const wholePlan = plan.length;
const planned = maxEpisodes === Infinity ? wholePlan : Math.min(maxEpisodes, wholePlan);

if (argv.includes('--validate-only')) {
  writeFileSync(join(outRoot, 'validation.json'), JSON.stringify({taskId, model: MODEL,
    evolvedSkills:extensionPath??null, effectiveSkillIds:learnedHarness.skills.map(s=>s.id), systemSha256:createHash('sha256').update(system).digest('hex'),
    configurations: driver.configurations.map((c, index) => ({id:c.id, index,stepBudget:configurationBudgets[index],configSha256:createHash('sha256').update(JSON.stringify(c)).digest('hex')})),
    selected:plan.slice(0, planned), learnedHarnessSha256:harnessDigest,
    branchModuleIds:activeBranch.map(r=>r.moduleId), globalModules:28, authoredSkills:proposals.length, modules:Object.keys(moduleRegistry?.active ?? {})}, null, 2));
  process.exit(0);
}

if (!shardArg && !serialRequested && planned > 1) {
  const requestedFanout = Number(flag('--fanout', '8'));
  if (!Number.isSafeInteger(requestedFanout) || requestedFanout < 1) throw Error('--fanout must be a positive integer');
  const fanout = Math.min(planned, requestedFanout);

  const passthrough = [];
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--out' || argv[i] === '--fanout') { i += 1; continue; }
    if (argv[i] === '--serial') continue;
    passthrough.push(argv[i]);
  }
  log(`fanout: ${planned} episodes over ${fanout} child processes (use --serial to play them in order)`);
  const { spawn } = await import('node:child_process');
  const codes = await Promise.all(Array.from({ length: fanout }, (_, k) => new Promise(resolve => {
    const child = spawn(process.execPath, [process.argv[1], ...passthrough,
      '--shard', `${k + 1}/${fanout}`, '--out', join(outRoot, `shard${k + 1}`)],
      { stdio: 'inherit' });
    child.once('error', () => resolve(1));
    child.once('close', code => resolve(code ?? 1));
  })));

  const merged = []; const shards = [];
  for (let k = 1; k <= fanout; k += 1) {
    const file = join(outRoot, `shard${k}`, 'results.json');
    let rows = [], planCount = null;
    if (existsSync(file)) {
      const part = JSON.parse(readFileSync(file, 'utf8'));
      rows = part.results ?? []; planCount = part.plannedEpisodes ?? null;
    }
    merged.push(...rows);
    shards.push({ shard: `${k}/${fanout}`, exit: codes[k - 1], planned: planCount, recorded: rows.length });
  }
  const shardPlanTotal = shards.reduce((sum, s) => sum + (s.planned ?? 0), 0);
  writeFileSync(join(outRoot, 'results.json'), JSON.stringify({ taskId, model: MODEL,
    stepBudgetPolicySha256, stepBudgetImplementationSha256,
    learnedHarnessSha256: harnessDigest, frozenSkills: frozen.skills.length, authoredSkills: proposals.length,
    arm: moduleRegistry ? 'module+skills' : freeTools ? 'skills/free-tools' : baselineArm ? 'baseline' : 'skills',
    modules: moduleRegistry ? Object.keys(moduleRegistry.active) : [],
    plannedEpisodes: planned, wholePlanEpisodes: wholePlan, shards,

    coverageComplete: shardPlanTotal === planned && shards.every(s => s.exit === 0),
    results: merged }, null, 2) + '\n');
  const won = merged.filter(r => r.outcome === 'success').length;
  log(`FINISHED ${taskId}: ${won}/${merged.length} success across ${fanout} shards`
    + (shardPlanTotal === planned ? '' : ` -- COVERAGE INCOMPLETE: shards planned ${shardPlanTotal} of ${planned}`));
  process.exit(shards.every(s => s.exit === 0) ? 0 : 1);
}

const sampled = plan.slice(0, planned);
const shardPlan = sampled.filter((_, index) => index % shardTotal === shardIndex - 1);
plan.length = 0; plan.push(...shardPlan);
log(`plan: ${plan.length} episodes across ${driver.configurations.length} configurations`
  + (shardTotal > 1 ? ` (shard ${shardIndex}/${shardTotal} of ${planned} sampled from ${wholePlan})`
     : serialRequested ? ' (serial, requested)' : ''));

const TRANSIENT_HTTP = /^HTTP 5\d\d|^HTTP 429|billing_service_error|overloaded/i;

const REFUSAL_RETRIES = Number(process.env.RELAY_REFUSAL_RETRIES ?? 16);

const MODULE_CALLS_PER_STEP = Number(process.env.H0_MODULE_CALLS_PER_STEP ?? 3);

const MODULE_FORCE_STEPS = Number(process.env.H0_MODULE_FORCE_STEPS ?? 6);

const PROBE_ACTION_LIMIT=Number(process.env.H0_PROBE_ACTION_LIMIT??0);
const PROBE_WALL_MS=Number(process.env.H0_PROBE_WALL_MS??0);
const PROBE_STARTED=Date.now();
class ProbeStop extends Error {}
const EPISODE_STALL_MS = Number(process.env.H0_EPISODE_STALL_MS ?? 3_906_000);
const EPISODE_WALL_CLOCK_MS = Number(process.env.H0_EPISODE_WALL_CLOCK_MS ?? 30_705_000);
class EpisodeTimeout extends Error {}

const withDeadline = async (promise, ms, label) => {
  const remaining=PROBE_WALL_MS?Math.max(1,PROBE_WALL_MS-(Date.now()-PROBE_STARTED)):Infinity;
  const probeBound=remaining<ms;ms=Math.min(ms,remaining);
  if (!(ms > 0)) return promise;
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new EpisodeTimeout(
        `no progress for ${(ms / 60000).toFixed(0)} min while awaiting ${label}`)), ms);
    })]);
  } finally { clearTimeout(timer); }
};

const RELEASE_ON_ECHO = process.env.H0_MODULE_RELEASE_ON_ECHO === '1';

function moduleOutputIsEcho(input, output) {
  if (!output || typeof output !== 'object') return false;
  const supplied = new Set();
  const add = value => { if (value !== null && value !== undefined) supplied.add(String(value).trim()); };
  if (input && typeof input === 'object') {
    for (const fact of input.facts ?? []) {
      if (fact && typeof fact === 'object') { add(fact.key); add(fact.value); }
    }
    for (const item of input.history ?? []) {
      if (item && typeof item === 'object') for (const value of Object.values(item)) add(value);
    }
  }
  if (!supplied.size) return false;
  const asserted = [];
  for (const attribute of output.attributes ?? []) {
    if (attribute && typeof attribute === 'object') {
      for (const key of ['attribute', 'shows', 'target']) {
        const value = attribute[key];
        if (value !== null && value !== undefined) asserted.push(String(value).trim());
      }
    }
  }
  if (!asserted.length) return false;
  return asserted.every(value => supplied.has(value));
}
const MODULE_FORCE_FROM_STEP = Number(process.env.H0_MODULE_FORCE_FROM_STEP ?? 0);

const QUOTA_EXHAUSTED = /API_KEY_QUOTA_EXHAUSTED|quota exhausted/;
const TRANSIENT_ATTEMPTS = Number(process.env.H0_TRANSIENT_ATTEMPTS ?? 6);
const QUOTA_ATTEMPTS = Number(process.env.H0_QUOTA_ATTEMPTS ?? 8);
const QUOTA_BACKOFF_CAP_MS = Number(process.env.H0_QUOTA_BACKOFF_CAP_MS ?? 600_000);
async function callPlayerRetrying(turns,runDir,tool,label,forceEnvTool=false,forceModuleTool=false) {

  return callPlayer(turns,runDir,tool,forceEnvTool,forceModuleTool);
}

const isAnchor = (driver.kind ?? 'interactive') === 'anchor';

let results = [];
const resultsPath = join(outRoot, 'results.json');
if(existsSync(resultsPath))throw Error('Immutable attempt already has results; reserve a new budgeted output directory to rerun.');
const alreadyDone = new Set(results.map(r => r.episode));

for (const episode of plan) {
  if (alreadyDone.has(episode.id)) continue;
  const runDir = join(outRoot, episode.id);
  mkdirSync(runDir, { recursive: true });
  const stepBudget = configurationBudgets[episode.configurationIndex];
  const stepCeiling = stepBudget.maxSteps;
  writeFileSync(join(runDir, 'step-budget.json'), JSON.stringify(stepBudget, null, 2) + '\n');
  log(`  ${episode.id} host action limit=${stepCeiling} policy=${stepBudget.policySha256.slice(0,12)}`);
  const started = Date.now();
  let opened, stored = [], steps = 0, invalid = 0, refusals = 0, terminal = null;

  let outputCapHits = 0;

  const verifiedSession=isExecutableRegistry(moduleRegistry)?createVerifiedSession(moduleRegistry,branch.scope,{ownerId:branch.automaticId}):null;
  const policySession=isPolicyRegistry(moduleRegistry)?new PolicySession(moduleRegistry):null;
  let previewedStep=-1;let policyRejectedAtStep=0,policyRejectedTotal=0;const adviceBudget=new AdviceBudget();
  let auxiliaryAtStep=0;
  let moduleCalls = 0, moduleCallsTotal = 0, moduleErrors = 0, moduleExtra = [];

  let moduleForceReleased = false, moduleForceRefusals = 0;

  let moduleEchoCalls = 0, moduleEchoReleases = 0;

  const tok = { input: 0, cacheCreate: 0, cacheRead: 0, output: 0 };
  try {

    opened = await withDeadline(
      driver.open({ runDir, run: { evolvedSkills:extensionPath??null, effectiveSkillIds:learnedHarness.skills.map(s=>s.id), systemSha256:createHash('sha256').update(system).digest('hex'),
    configurations: driver.configurations }, episode }),
      EPISODE_STALL_MS, `${taskId} driver.open()`);
    let observation = opened.observation;
    if(verifiedSession)verifiedSession.observeInitial({publicText:observation.publicText??''});
    policySession?.observeInitial({publicText:observation.publicText??''});
    while (!observation?.terminal?.ended && (taskId === 'arc_agi_3' ? observation.info.nativeActions : steps) < stepCeiling) {
      if (PROBE_ACTION_LIMIT && steps>=PROBE_ACTION_LIMIT || PROBE_WALL_MS && Date.now()-PROBE_STARTED>=PROBE_WALL_MS) {terminal={ended:false,outcome:'probe_truncated',reason:'planned_short_probe_limit',score:null};break;}
      if (Date.now() - started >= EPISODE_WALL_CLOCK_MS) {
        throw new EpisodeTimeout(`episode exceeded the ${(EPISODE_WALL_CLOCK_MS / 3600000).toFixed(1)}h wall clock at step ${steps}`);
      }
      if (taskId === 'arc_agi_3') {
        const reset = await withDeadline(autoResetArc({observation, opened, steps, limit:stepCeiling}),
          EPISODE_STALL_MS, 'official automatic RESET');
        if (reset) {

          stored.push(buildObservationTurn(observation));
          stored.push({role:'assistant',content:[
            {type:'text',text:'[Harness automatic action: GAME_OVER/NOT_PLAYED recovery; no model call.]'},
            {type:'tool_use',id:reset.toolId,name:driver.tool.name,input:reset.action}]});
          observation=reset.observation;
          stored.push(buildToolResultTurn(reset.toolId,observation));
          policySession?.record(reset.action,{publicText:observation.publicText??''});
          verifiedSession?.record(reset.action,{publicText:observation.publicText??''});
          appendFileSync(join(runDir,'host-resets.jsonl'),JSON.stringify({step:steps,...reset})+'\n');
          steps++;invalid=0;outputCapHits=0;moduleCalls=0;moduleExtra=[];auxiliaryAtStep=0;policyRejectedAtStep=0;
          adviceBudget.nativeStepCompleted();
          continue;
        }
      }
      if(policySession && taskId==='arc_agi_3' && previewedStep!==steps){
        moduleExtra.push({role:'user',text:[{type:'text',text:`Current public observation obs-${steps}; remaining native actions ${stepCeiling-steps}. Consult a branch helper only if public evidence fits its contract.`}]});
        const preview=policySession.preview();moduleCallsTotal++;
        appendFileSync(join(runDir,'module-predecision.jsonl'),JSON.stringify({step:steps,...preview})+'\n');
        if(!preview.ok){terminal={ended:false,outcome:'module_error',reason:preview.error,score:null};break;}
        const feedback={...preview.output,moduleAdvice:true,noWorldActionExecuted:true,hostPolicyContract:'Computed public-evidence module, before your decision. Use or reject its measured hypothesis. This is not an environment command or a known solution. Select one legal game action.'};
        moduleExtra.push({role:'user',text:[{type:'text',text:'PUBLIC CONTROL MODULE: '+JSON.stringify(feedback)}]});
        appendFileSync(join(runDir,'module-feedback.jsonl'),JSON.stringify({step:steps,phase:'before_proposal',feedback})+'\n');
        adviceBudget.shouldReview('advice');previewedStep=steps;
      }

      let turns = isAnchor ? [observation.playerTurn, ...moduleExtra]
        : [...buildRequestTurns(stored, observation), ...moduleExtra];
      const tool = isAnchor ? observation.tool
        : presentation ? { ...driver.tool, parameters: eleusisToolSchema() }
        : driver.tool;
      if (!isAnchor && invalid > 0 && driver.invalidActionPolicy) {
        const note = prompt.invalidResponseReprompt(driver.invalidActionPolicy);
        const last = turns.at(-1);
        turns = [...turns, { role: 'user', text: [{ type: 'text', text: note }] }];
      }

      if (!isAnchor && taskId === 'among_us_deception_sandbox' && invalid > 0) {
        turns = [...turns, {role:'user',text:[{type:'text',text:'The previous response did not satisfy the public action schema; no environment action executed. Submit exactly one complete tool call. '+driver.actionContract}]}];
      }
      if (!isAnchor && presentation) {

        if (invalid > 0 && moduleExtra.length) {
          const context = turns.slice(0, -moduleExtra.length);
          turns = [...presentation.appendEleusisFormatCorrection({ taskId, turns: context, invalidResponses: invalid }), ...moduleExtra];
        } else {
          turns = presentation.appendEleusisFormatCorrection({ taskId, turns, invalidResponses: invalid });
        }
      }

      const forceModule = Boolean(moduleTool) && moduleCalls === 0
        && steps >= MODULE_FORCE_FROM_STEP && steps < MODULE_FORCE_STEPS && !moduleForceReleased;
      let { toolId, toolName, action, stopReason, stopDetails, usage, assistantContent } = await withDeadline(callPlayerRetrying(
        turns, runDir, tool, episode.id, moduleCalls >= MODULE_CALLS_PER_STEP || auxiliaryAtStep>=2, forceModule),
        EPISODE_STALL_MS, `the Player request at step ${steps}`);
      if (usage) for (const k of Object.keys(tok)) tok[k] += usage[k] ?? 0;
      if(toolName===branchTool.name&&action){
        if(auxiliaryAtStep>=2){terminal={ended:false,outcome:'helper_budget_exhausted',reason:'Two helper calls already consumed before this action',score:null};break;}
        auxiliaryAtStep++;
        const response=await consultBranch(action,steps,stepCeiling-steps);
        appendFileSync(join(runDir,'branch-module-calls.jsonl'),JSON.stringify({step:steps,toolId,input:action,...response})+'\n');
        moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(response)}]});
        continue;
      }
      const retained=retainedProviderOutcome({stopReason,stopDetails,action},{nativeOutputCapPolicy:Boolean(unseenMode&&opened.hostEnd)});
      if(retained) {
        appendFileSync(join(runDir,'provider-stop-events.jsonl'),JSON.stringify({step:steps,stopReason,stopDetails,usage,outcome:retained.outcome})+'\n');
        if(stopReason==='refusal')writeFileSync(join(runDir,'interruption-checkpoint.json'),JSON.stringify({caseId:episode.caseId,nativeActions:observation.info.nativeActions,actionBudget:stepCeiling,remainingNativeActions:stepCeiling-observation.info.nativeActions,resets:observation.info.resets,gameOvers:observation.info.gameOvers,configSha256:createHash('sha256').update(JSON.stringify(driver.configurations[episode.configurationIndex])).digest('hex'),registrySha256:policyHash(moduleRegistry),effectiveRequestConfig:existsSync(join(runDir,'effective-request-config.json'))?JSON.parse(readFileSync(join(runDir,'effective-request-config.json'),'utf8')):null,providerStopDetails:stopDetails,score:null,recoveryRequires:'Provider refusal investigation; preserve this sample and do not automatically retry refusal.'},null,2));
        if(forceModule&&stopReason==='refusal')moduleForceRefusals+=1;
        terminal=retained;
        break;
      }
      refusals = 0;
      let verifiedError=null;
      if(verifiedSession && toolName===moduleTool.name && action?.mode==='commit'){
        try{
          const receipt=verifiedSession.consumeReceipt(action);
          appendFileSync(join(runDir,'verified-commits.jsonl'),JSON.stringify({step:steps,...receipt})+'\n');
          action=receipt.action;toolName=tool.name;
        }catch(e){verifiedError={ok:false,error:e.message};}
      }

      if (moduleTool && toolName === moduleTool.name) {
        moduleCalls += 1; moduleCallsTotal += 1;
        const verdict = verifiedError ?? (policySession ? policySession.run(action) : verifiedSession ? verifiedSession.run(action) : runCapabilityModule(moduleRegistry, { moduleId: Object.keys(moduleRegistry.active)[0], ...action }));
        if (!verdict.ok) moduleErrors += 1;

        const output = verdict.ok ? JSON.stringify(verdict.output)
          : JSON.stringify({ error: verdict.error, hint: 'Fix the named field and call again; no environment action has executed.' });

        const callTurn = { role: 'assistant', content: assistantContent };
        const resultTurn = { role: 'tool', results: [{ id: toolId, output }] };

        const echo = moduleOutputIsEcho(action, verdict.ok ? verdict.output : null);
        if (echo) moduleEchoCalls += 1;
        try {
          appendFileSync(join(runDir, 'module-calls.jsonl'), JSON.stringify({
            step: steps, callIndexThisStep: moduleCalls, compelled: forceModule, echo,
            moduleId: action.moduleId ?? Object.keys(moduleRegistry.active)[0], input: action,
            ok: Boolean(verdict.ok), output: verdict.ok ? verdict.output : verdict.error,
          }) + '\n');
        } catch {}

        if (echo && RELEASE_ON_ECHO && forceModule && !moduleForceReleased) {
          moduleForceReleased = true; moduleEchoReleases += 1;
          log(`  ${episode.id} step${steps} compelled module call added nothing the Player had not supplied -- releasing the compulsion`);
        }

        moduleExtra.push(callTurn, resultTurn);
        if (moduleCalls >= MODULE_CALLS_PER_STEP) {
          log(`  ${episode.id} step${steps} module called ${moduleCalls}x -- taking the choice back to the environment tool`);
        }
        continue;
      }
      const legal = action && toolName===tool.name ? driver.normalizeAction(action) : null;
      if (!legal) appendFileSync(join(runDir, 'invalid-actions.jsonl'), JSON.stringify({step:steps,toolName,action,stopReason})+'\n');
      if (!legal) {
        invalid += 1;
        log(`  ${episode.id} step${steps} no legal action (invalid #${invalid})`);

        if (unseenMode && opened.hostEnd && stopReason === 'max_tokens') {
          outputCapHits += 1;
          if (outputCapHits >= 3) {
            log(`  ${episode.id} step${steps} 3 consecutive responses hit the output cap without an action -- hostEnd()`);
            const ended = await opened.hostEnd('h0_output_cap_exhausted');
            observation = ended?.observation ?? ended;
            terminal = observation?.terminal ?? null;
            break;
          }
        }
        if (driver.invalidActionPolicy && invalid > driver.invalidActionPolicy.reprompts) {

          const forced = driver.normalizeAction(driver.invalidActionPolicy.exhaustedAction);
          const forcedResult = await withDeadline(opened.step(forced, { index: steps }),
            EPISODE_STALL_MS, `the environment's exhausted action at step ${steps}`);
          observation = forcedResult?.observation ?? forcedResult;
          if(verifiedSession)verifiedSession.record(forced,{publicText:observation.publicText??''});
          stored.push(buildObservationTurn(observation));
          steps += 1; invalid = 0;
          moduleCalls = 0; moduleExtra = []; auxiliaryAtStep=0;
          continue;
        }

        if (!driver.invalidActionPolicy && invalid >= 20) { log(`  ${episode.id} aborting after 20 consecutive invalid responses`); break; }
        continue;
      }
      let checkedPolicy=null;
      if(policySession){
        checkedPolicy=policySession.check(legal);moduleCallsTotal++;
        appendFileSync(join(runDir,'module-calls.jsonl'),JSON.stringify({step:steps,automatic:true,input:{proposedAction:legal},...checkedPolicy})+'\n');
        if(!checkedPolicy.ok){terminal={ended:false,outcome:'module_error',reason:checkedPolicy.error,score:null};break;}
        if(adviceBudget.shouldReview(checkedPolicy.output.status)){
          const feedback={moduleAdvice:true,noWorldActionExecuted:true,...checkedPolicy.output,hostPolicyContract:'Review this computed advice once. It is strategic guidance, not a claim of native illegality. You may keep your proposal or revise it, then submit the action. There is no separate consultation tool.'};
          appendFileSync(join(runDir,'module-feedback.jsonl'),JSON.stringify({step:steps,actionHash:checkedPolicy.actionHash,feedback})+'\n');
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(feedback)}]});
          continue;
        }
        if(checkedPolicy.output.status==='block'){
          policyRejectedAtStep++;policyRejectedTotal++;
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify({blockedByModule:true,noWorldActionExecuted:true,...checkedPolicy.output,hostPolicyContract:'No override endpoint exists. Submit a proposal satisfying the returned policy; this blocked proposal has not executed.'})}]});
          if(policyRejectedAtStep>=4||policyRejectedTotal>=16){terminal={ended:false,outcome:'module_guard_exhausted',reason:'Repeated rejected proposals; no fabricated native terminal',score:null};break;}
          continue;
        }
        if(checkedPolicy.actionHash!==policyHash(legal))throw Error('Policy/action binding changed');
      }
      invalid = 0;

      outputCapHits = 0;

      stored.push(buildObservationTurn(observation));
      stored.push({role:'assistant',content:assistantContent});

      const stepped = await withDeadline(opened.step(legal, { index: steps }),
        EPISODE_STALL_MS, `the environment step ${steps}`);
      observation = stepped.observation ?? stepped;
      if(verifiedSession)verifiedSession.record(legal,{publicText:observation.publicText??''});
      if(policySession){appendFileSync(join(runDir,'policy-executions.jsonl'),JSON.stringify({step:steps,action:legal,...checkedPolicy,publicFeedback:observation.publicText})+'\n');policySession.record(legal,{publicText:observation.publicText??''});policyRejectedAtStep=0;adviceBudget.nativeStepCompleted();}
      stored.push(buildToolResultTurn(toolId, observation));
      steps += 1;

      moduleCalls = 0; moduleExtra = []; auxiliaryAtStep=0;
    }

    terminal = finishWithStepBudget({terminal, observation, steps:taskId === 'arc_agi_3' ? observation.info.nativeActions : steps, budget: stepBudget});
  } catch (error) {
    if(error.responseUsage)for(const k of Object.keys(tok))tok[k]+=error.responseUsage[k]??0;

    if(PROBE_WALL_MS && Date.now()-PROBE_STARTED>=PROBE_WALL_MS){terminal={ended:false,outcome:'probe_truncated',reason:'planned_probe_wall_limit',score:null};}
    else if (error instanceof EpisodeTimeout) {
      log(`  ${episode.id} TIMEOUT ${error.message} -- ending episode as 'timeout'`);
      terminal = { ended: false, outcome: 'timeout', reason: error.message };
    } else {
    appendFileSync(join(runDir,'error-diagnostics.jsonl'),JSON.stringify({name:error.name,message:error.message,code:error.code,cause:{name:error.cause?.name,message:error.cause?.message,code:error.cause?.code}})+'\n');
    log(`  ${episode.id} ERROR ${error.message}`);
    terminal = { ended: false, outcome: 'error', reason: error.message };
    }

    if (/INSUFFICIENT_BALANCE|Insufficient account balance/i.test(error.message)) {
      results.push(row0(episode, steps, terminal, started, tok, moduleCallsTotal, moduleErrors, moduleForceRefusals, moduleEchoCalls, moduleEchoReleases));
      writeResults();
      log(`FATAL relay account balance exhausted -- stopping ${taskId} with ${results.length} rows; rerun to resume`);
      process.exit(4);
    }
  } finally { try { await opened?.close?.(); } catch {} }
  const row = row0(episode, steps, terminal, started, tok, moduleCallsTotal, moduleErrors, moduleForceRefusals, moduleEchoCalls, moduleEchoReleases);
  results.push(row);
  const billed = tok.input + tok.cacheCreate + tok.cacheRead;
  log(`  DONE ${episode.id} outcome=${row.outcome} score=${row.score} steps=${steps} ${row.seconds}s `
    + `tok in=${tok.input} cc=${tok.cacheCreate} cr=${tok.cacheRead} out=${tok.output}`
    + (billed ? ` cacheHit=${(100 * tok.cacheRead / billed).toFixed(0)}%` : '')
    + (moduleTool ? ` moduleCalls=${moduleCallsTotal} errors=${moduleErrors}` : ''));
  writeResults();
}
function row0(episode, steps, terminal, started, tok = { input: 0, cacheCreate: 0, cacheRead: 0, output: 0 }, moduleCallsTotal = 0, moduleErrors = 0, moduleForceRefusals = 0, moduleEchoCalls = 0, moduleEchoReleases = 0) {
  return { taskId, episode: episode.id, configurationIndex: episode.configurationIndex,

    caseId: episode.caseId ?? null,
    configSha256:createHash('sha256').update(JSON.stringify(driver.configurations[episode.configurationIndex])).digest('hex'),
    registrySha256:modulesPath?createHash('sha256').update(readFileSync(modulesPath)).digest('hex'):null,
    evolvedSkillsSha256:extensionPath?createHash('sha256').update(readFileSync(extensionPath)).digest('hex'):null,
    runtimeSha256:createHash('sha256').update(readFileSync(new URL(import.meta.url))).digest('hex'),
    stepBudget: configurationBudgets[episode.configurationIndex],
    budgetTruncated: terminal?.budgetTruncated === true,
    ...(terminal?.budgetTruncated ? {attemptCompleted:true,retryable:false} : {}),
    steps, outcome: terminal?.outcome ?? null, reason: terminal?.reason ?? null, tokens: { ...tok },
    score: terminal?.score ?? null, terminalEvidence: terminal ?? null, ended: Boolean(terminal?.ended), seconds: Math.round((Date.now() - started) / 1000),
    ...(moduleTool ? { moduleCalls: moduleCallsTotal, moduleErrors, moduleForceRefusals,
      moduleEchoCalls, moduleEchoReleases, releaseOnEcho: RELEASE_ON_ECHO } : {}) };
}
function writeResults() {
  writeFileSync(join(outRoot, 'results.json'), JSON.stringify({ taskId, model: MODEL,
    stepBudgetPolicySha256, stepBudgetImplementationSha256,
    learnedHarnessSha256: harnessDigest, frozenSkills: frozen.skills.length, authoredSkills: proposals.length,
    arm: moduleRegistry ? 'module+skills' : freeTools ? 'skills/free-tools' : baselineArm ? 'baseline' : 'skills',
    modules: moduleRegistry ? Object.keys(moduleRegistry.active) : [],

    plannedEpisodes: plan.length, wholePlanEpisodes: wholePlan,
    ...(shardTotal > 1 ? { shard: `${shardIndex}/${shardTotal}` } : {}),
    results }, null, 2) + '\n');
}
const won = results.filter(r => r.outcome === 'success').length;
log(`FINISHED ${taskId}: ${won}/${results.length} success`);
