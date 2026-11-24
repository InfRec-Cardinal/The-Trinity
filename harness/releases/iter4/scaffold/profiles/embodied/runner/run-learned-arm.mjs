import {reviewPublicPlan} from './adaplan-public-constraints.mjs';
import {enableEventLedger,auditPublicSequence,reviewPublicSequence,pendingSequenceCorrection} from './public-event-ledger.mjs';
import {enableSourceAcquisition,sourceAcquisitionNotice,acquirePublicSource,sourceScopeEvidence} from './public-source-acquisition.mjs';
import {visualCommitReview} from '../../../module-harness/src/visual-commit-review.mjs';
import {automaticVisualEvidence} from './automatic-visual-evidence.mjs';
import {publicDecisionAdvice,actionOnlyPresentation} from './public-decision-adapters.mjs';
import {NativeWire} from './native-wire.mjs';
import {PublicExecutionReceipts} from './public-execution-receipts.mjs';
const nativeThinking=process.env.H0_NATIVE_THINKING==='1';
const nativeWires=new Map();
import {fileURLToPath, pathToFileURL} from 'node:url';
import {replayResponse,resumeElapsedMs,finishReplay} from './resume-replay.mjs';
import {resolvePolicy,capabilityNotice} from '../../../shared/capability-scope.mjs';
const branchNode=process.env.H0_CAPABILITY_NODE??'d';
const {scope,activeBranch,branchTool:baseBranchTool,consultBranch}=await import('./branch-path-modules.mjs');
import {enableFrameInspection,inspectPublicFrame} from './public-frame-inspection.mjs';
const branchTool=enableEventLedger(enableSourceAcquisition(enableFrameInspection(baseBranchTool,activeBranch)),activeBranch);
import {evidenceTool,splitAction} from './evidence-bridge.mjs';

import { mkdirSync, writeFileSync, readFileSync, existsSync, appendFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import {requestPolicy, requestAction, retainedProviderOutcome, consultationMessages, sanitizeToolCallHistory} from './player-protocol.mjs';
import {resolveStepBudget, finishWithStepBudget, stepBudgetPolicySha256, stepBudgetImplementationSha256} from './step-budgets.mjs';

const unseenMode = process.argv.includes('--unseen') || process.env.H0_UNSEEN === '1';
const UNSEEN_ROOT = process.env.H0_UNSEEN_ENV_ROOT;
if(unseenMode&&!UNSEEN_ROOT)throw Error('Set H0_UNSEEN_ENV_ROOT for an external unseen environment');
const ENV_ROOT = unseenMode
  ? UNSEEN_ROOT
  : (process.env.H0_ENV_ROOT ?? fileURLToPath(new URL('../package/code',import.meta.url)));
const PIPELINE = process.env.H0_PIPELINE_ROOT ?? fileURLToPath(new URL('..',import.meta.url));

const BASE_URL = (process.env.RELAY_BASE_URL ?? 'https://api.anthropic.com').replace(/\/$/, '');
const MODEL = process.env.RELAY_MODEL ?? 'claude-opus-5';

const thinkingEffort = process.env.H0_THINKING_EFFORT ?? 'low';
const thinkingOn = nativeThinking||!['low','off'].includes(thinkingEffort);

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
const {PolicySession,AdviceBudget,hash:policyHash}=await import('../../../module-harness/policy-runtime/program.mjs');
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
const skillsPath = process.env.H0_AUTHORED_SKILLS ?? fileURLToPath(new URL('../skills/frozen-empty.json',import.meta.url));
if (!existsSync(skillsPath)) { log(`FATAL no authored skills at ${skillsPath}`); process.exit(3); }
const authored = JSON.parse(readFileSync(skillsPath, 'utf8'));
const extensionPath=process.env.H0_EVOLVED_SKILLS;
let extension=extensionPath?JSON.parse(readFileSync(extensionPath,'utf8')):null;
if(extension){
 const {skillProposalSchema}=await import('../../../vendor/skill-schema.mjs');
 if(!Array.isArray(extension.replaces)||!extension.replaces.every(s=>typeof s==='string')||!Array.isArray(extension.proposals))throw Error('Invalid skill extension');
 extension.proposals=extension.proposals.map(p=>{const s=skillProposalSchema.parse(p);if(s.audience.length!==1||s.audience[0]!=='playing')throw Error('Playing skills only');return s});
}
const initial=Array.isArray(authored.proposals)?authored.proposals:[];
if(extension){for(const id of extension.replaces)if(!initial.some(p=>p.id===id))throw Error('Unknown skill replacement: '+id);}
const proposals=extension?[...initial.filter(p=>!extension.replaces.includes(p.id)),...extension.proposals]:initial;
if(new Set(proposals.map(p=>p.id)).size!==proposals.length)throw Error('Duplicate effective skill IDs');
if (!proposals.length && !argv.includes('--baseline')) { log(`FATAL ${taskId} has no proposals`); process.exit(3); }

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

const registry = createRegistry({ root: ENV_ROOT });
const driver = await registry.getDriver(taskId);
if(!driver)throw Error('Task driver not available');
const modulesPath = flag('--modules', '');
const requestedModuleRegistry = modulesPath ? JSON.parse(readFileSync(modulesPath, 'utf8')) : null;
const {registry:moduleRegistry,automaticPolicyNote}=resolvePolicy(scope,requestedModuleRegistry,{nativeSchema:driver.tool?.parameters});
if(automaticPolicyNote)log(automaticPolicyNote);
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
learnedHarness={...learnedHarness,promptPatches:[...(learnedHarness.promptPatches??[]),capabilityNotice(scope,baseBranchTool.input_schema.properties.moduleId.enum,Object.keys(moduleRegistry?.active??{}))+(automaticPolicyNote?'\n'+automaticPolicyNote:'')]};
const harnessDigest = createHash('sha256').update(JSON.stringify(learnedHarness)).digest('hex');
if(isExecutableRegistry(moduleRegistry))writeFileSync(join(outRoot,'executable-runtime-provenance.json'),JSON.stringify({registryHash:createHash('sha256').update(JSON.stringify(moduleRegistry)).digest('hex'),files:Object.fromEntries(['program.mjs','registry.mjs','session.mjs','public-adapters.mjs','../../../shared/public-model-adapters.mjs'].map(f=>[f,createHash('sha256').update(readFileSync(new URL('../runtime/'+f,import.meta.url))).digest('hex')]))},null,2));
if(isPolicyRegistry(moduleRegistry))writeFileSync(join(outRoot,'policy-runtime-provenance.json'),JSON.stringify({registryHash:policyHash(moduleRegistry),files:Object.fromEntries(['../../../module-harness/policy-runtime/program.mjs','../../../module-harness/policy-runtime/worker.mjs','policy-module-bridge.mjs','player-protocol.mjs','run-learned-arm.mjs'].map(f=>[f,createHash('sha256').update(readFileSync(new URL(f,import.meta.url))).digest('hex')]))},null,2));
writeFileSync(join(outRoot, 'learned-harness.json'), JSON.stringify(learnedHarness, null, 2));

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
const playerAssignment=taskId==='among_us_deception_sandbox'?{task:assignment.task,observation:assignment.observation,actions:assignment.actions,evaluation:{budget:assignment.evaluation.budget,success:assignment.evaluation.success,failure:assignment.evaluation.failure}}:assignment;
const playerActionContract=taskId==='among_us_deception_sandbox'?'Submit one listed game action using submit_action with action and optional room. The action text is passed unchanged to the original native parser; all legal moves and scoring remain native.':driver.actionContract;
const system = moduleAwareSystem(prompt.renderFrozenH0(learnedHarness, playerAssignment, driver.kind ?? 'interactive', playerActionContract), [moduleTool?.name,branchTool.name].filter(Boolean));

log(`task=${taskId} kind=${driver.kind} configurations=${driver.configurations.length}`);
log(`package=${unseenMode ? 'UNSEEN-17' : 'TRAIN-28'} root=${ENV_ROOT}`);
log(`wire_history=${nativeThinking?'append-only signed history (overrides environment request window)':'environment window'}; public receipts enabled`);
log(`conversation=${unseenMode ? `contextPolicy=${contextPolicy} imageOrder=${imageOrder} toolResultTerminal=null-until-end`
  : 'train last64 (trimmed to a user turn), single frame after text, terminal object in every tool result'}`);
log(`arm=${baselineArm ? 'BASELINE (frozen harness only)'
  : moduleRegistry ? `MODULE+SKILLS (frozen + authored skills + ${Object.keys(moduleRegistry.active).join(',')})`
  : freeTools ? 'LEARNED/free-tools (frozen + authored skills, tool_choice=any)'
  : 'LEARNED (frozen + authored skills)'}`);
log(`frozen skills=${frozen.skills.length} + authored=${baselineArm ? 0 : proposals.length} -> arm skills=${learnedHarness.skills.length}`);
log(`tool_choice=${thinkingOn ? 'auto (a forced choice suppresses thinking)' : freeTools ? 'any' : 'forced'}`
  + `${moduleTool ? ` + ${moduleTool.name}` : ''} thinking_effort=${thinkingEffort}`);
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

  const CACHE = { type: 'ephemeral', ttl: process.env.RELAY_CACHE_TTL ?? '5m' };
  const cachedSystem = [{ type: 'text', text: system, cache_control: CACHE }];
  const last = messages.at(-1);
  if (last && Array.isArray(last.content) && last.content.length) {
    last.content = last.content.map((b, i) =>
      i === last.content.length - 1 ? { ...b, cache_control: CACHE } : b);
  }

  const asTool=t=>({name:t.name,description:t.description,input_schema:t.parameters});
  const policy=requestPolicy({effort:thinkingEffort,environmentTool:asTool(tool),
    moduleTool:moduleTool?asTool(moduleTool):null,forceEnvironment:nativeThinking?false:forceEnvTool,forceModule:nativeThinking?false:forceModuleTool});
  if(nativeThinking||!forceEnvTool)policy.tools.push(branchTool);
  let body={model:MODEL,max_tokens:Number(process.env.H0_MAX_TOKENS??(['low','off'].includes(thinkingEffort)?16384:24000)),
    system:cachedSystem,...policy,messages,stream:true};
  let wire=null;
  if(nativeThinking){
    wire=nativeWires.get(runDir);if(!wire){wire=new NativeWire();nativeWires.set(runDir,wire);}
    body=wire.prepare(body,{nativeOnly:forceEnvTool});
    appendFileSync(join(runDir,'native-wire.jsonl'),JSON.stringify({request:wire.requests,thinking:body.thinking,effort:body.output_config.effort,messages:body.messages.length,prefixMode:'append-only',nativeOnly:forceEnvTool})+'\n');
  }
  let result;
  try { result=await requestAction({body,allowTextAction:process.env.H0_TEXT_ACTION_ADAPTER==='1',post:async request=>{
    request=sanitizeToolCallHistory(request).body;
    let lastTransportError;
    const originalRequestHash=createHash('sha256').update(JSON.stringify(request)).digest('hex');
    for(let transportAttempt=1;transportAttempt<=2;transportAttempt++){
     if(createHash('sha256').update(JSON.stringify(request)).digest('hex')!==originalRequestHash)throw Error('Retry input changed');
     let captureId,transportStarted=false;
     try{
    captureId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const sanitized = sanitizeToolCallHistory(request);
    request = sanitized.body;
    if (sanitized.removed) appendFileSync(join(runDir,'transport-sanitizations.jsonl'),JSON.stringify({captureId,adapter:'strip_response_tool_caller_v1',removed:sanitized.removed})+'\n');
    const requestBytes=Buffer.byteLength(JSON.stringify(request));
    appendFileSync(join(runDir,'request-sizes.jsonl'),JSON.stringify({captureId,requestBytes})+'\n');
    if(requestBytes>32000000)throw Error('Local request-size guard: request exceeds 32 MB; do not send oversized imagery');
                                                                                
    appendFileSync(join(runDir,'api-responses.jsonl'),'');
    appendFileSync(join(runDir,'api-requests.jsonl'),JSON.stringify({captureId,request})+'\n');
    const cached=replayResponse(request,runDir);
    if(cached){appendFileSync(join(runDir,'api-responses.jsonl'),JSON.stringify({...cached,captureId,replayedFrom:cached.captureId})+'\n');return cached.raw;}
    transportStarted=true;
    const response=await fetch(`${BASE_URL}/v1/messages`,{method:'POST',signal:AbortSignal.timeout(180000),
      headers:{'content-type':'application/json','x-api-key':apiKey,'anthropic-version':'2023-06-01'},body:JSON.stringify(request),redirect:'error'});
    const raw = (await response.text()).replaceAll(apiKey, '[redacted]');
    const headers=Object.fromEntries(['request-id','x-request-id','anthropic-request-id','content-type'].map(k=>[k,response.headers.get(k)]).filter(([,v])=>v));
    appendFileSync(join(runDir,'api-responses.jsonl'),JSON.stringify({captureId,status:response.status,headers,raw})+'\n');
    if(!response.ok)throw new Error(`HTTP ${response.status}: ${raw.slice(0,400)}`);
    return raw;
     }catch(error){
      lastTransportError=error;
      const retryable=error instanceof TypeError||error.name==='TimeoutError'||/HTTP 400:.*ValidationException: request failed/.test(error.message);
      if(transportStarted)appendFileSync(join(runDir,'exact-transport-retries.jsonl'),JSON.stringify({phase:'transport',captureId,transportAttempt,requestHash:originalRequestHash,retryable,error:error.message,unchangedInput:true})+'\n');
      if(!transportStarted||!retryable||transportAttempt===2)throw error;
      await new Promise(resolve=>setTimeout(resolve,10000));
     }
    }
    throw lastTransportError;

  }}); } catch(error) {
    appendFileSync(join(runDir,'protocol-errors.jsonl'),JSON.stringify({error:error.message,
      effort:thinkingEffort,offered:policy.tools.map(t=>t.name),toolChoice:policy.tool_choice,
      stopReason:error.responseStopReason??null,usage:error.responseUsage??null,
      returnedToolCalls:error.responseToolCalls??null,usageKnown:Boolean(error.responseUsage)})+'\n');
    throw error;
  }
  if(wire){try{wire.accept(result);if(forceEnvTool&&result.action&&result.toolName!==tool.name)throw Error('Auxiliary consultation budget exhausted');}catch(error){error.responseUsage=result.usage;throw error;}}
  appendFileSync(join(runDir,'protocol-calls.jsonl'),JSON.stringify({effort:thinkingEffort,
    offered:policy.tools.map(t=>t.name),toolChoice:policy.tool_choice,toolName:result.toolName,
    transportAdapter:result.transportAdapter??null,stopReason:result.stopReason,usage:result.usage,thinkingBlocks:result.assistantContent.filter(b=>b.type==='thinking').length})+'\n');
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
if(argv.includes('--one-per-case')){
  const seen=new Set();const unique=plan.filter(e=>{if(seen.has(e.caseId))return false;seen.add(e.caseId);return true;});
  plan.length=0;plan.push(...unique);log(`one-per-case: ${plan.length} distinct configurations`);
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
    authoredSkills:proposals.length, modules:activeBranch.map(e=>e.moduleId), automaticPolicyModules:Object.keys(moduleRegistry?.active ?? {}),automaticPolicyNote}, null, 2));
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
    arm: moduleRegistry||activeBranch.length ? 'module+skills' : freeTools ? 'skills/free-tools' : baselineArm ? 'baseline' : 'skills',
    modules:activeBranch.map(e=>e.moduleId), automaticPolicyModules:moduleRegistry ? Object.keys(moduleRegistry.active) : [],
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

const EPISODE_STALL_MS = Number(process.env.H0_EPISODE_STALL_MS ?? 3_906_000);
const EPISODE_WALL_CLOCK_MS = Number(process.env.H0_EPISODE_WALL_CLOCK_MS ?? 30_705_000);
class EpisodeTimeout extends Error {}

const withDeadline = async (promise, ms, label) => {
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
  const started = Date.now()-resumeElapsedMs();
  let opened, stored = [], steps = 0, invalid = 0, refusals = 0, terminal = null;
  const publicReceipts=new PublicExecutionReceipts();

  let outputCapHits = 0;

  const verifiedSession=isExecutableRegistry(moduleRegistry)?createVerifiedSession(moduleRegistry,scope):null;
  const policySession=isPolicyRegistry(moduleRegistry)?new PolicySession(moduleRegistry):null;
  let policyRejectedAtStep=0,policyRejectedTotal=0;const adviceBudget=new AdviceBudget();
  let visualInspectedAt=-1,visualReviewedAt=-1,eventReviewedAt=-1,eventCorrectionReviewedAt=-1;
  let auxiliaryAtStep=0;let publicAdviceStep=-1,publicAdvice=null,consequenceReviewAt=-1,automaticVisualStep=-1,visualEvidence=[],scopeEvidence=null;
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
    policySession?.observeInitial({publicText:(observation.publicText??'')+'\nPUBLIC_FRAME_SHA256: '+(observation.frame?.sha256??'unavailable')});
    while (!observation?.terminal?.ended && steps < stepCeiling) {
      if (Date.now() - started >= EPISODE_WALL_CLOCK_MS) {
        throw new EpisodeTimeout(`episode exceeded the ${(EPISODE_WALL_CLOCK_MS / 3600000).toFixed(1)}h wall clock at step ${steps}`);
      }

      let turns = isAnchor ? [observation.playerTurn, ...moduleExtra]
        : [...buildRequestTurns(stored, observation), ...moduleExtra];
      const sourceNotice=sourceAcquisitionNotice(observation,steps,scope,runDir);
      if(sourceNotice&&!(nativeThinking&&moduleExtra.length))turns.push({role:'user',text:[{type:'text',text:'PUBLIC_SOURCE_ACQUISITION: '+JSON.stringify(sourceNotice)}]});
      if(automaticVisualStep!==steps){
        automaticVisualStep=steps;
        scopeEvidence=sourceScopeEvidence({observation,step:steps,runDir,activeBranch,scope});
        if(scopeEvidence)appendFileSync(join(runDir,'scope-evidence.jsonl'),JSON.stringify({step:steps,...scopeEvidence})+'\n');
        visualEvidence=automaticVisualEvidence({observation,step:steps,runDir,activeBranch,scope});
        if(visualEvidence.length)appendFileSync(join(runDir,'automatic-visual-evidence.jsonl'),JSON.stringify({step:steps,results:visualEvidence})+'\n');
      }
      if(visualEvidence.length&&!(sourceNotice&&nativeThinking&&moduleExtra.length))turns.push({role:'user',text:visualEvidence.flatMap(v=>[{type:'text',text:'Prerequisite module read-only visual preprocessing: '+JSON.stringify({moduleId:v.moduleId,output:v.output,error:v.error})+' Interpret this together with the original full frame. No new observation was acquired.'},...(v.imagePath?[{type:'frame_reference',path:v.imagePath}]:[])])});
      if(scopeEvidence&&!(nativeThinking&&moduleExtra.length))turns.push({role:'user',text:[{type:'text',text:'SOURCE_BOUNDARY_WITNESSES: '+JSON.stringify(scopeEvidence)+' These are additional original-video frames, selected from public OCR evidence by the acquisition module. Confirm the headings and scope before counting.'},...scopeEvidence.imagePaths.map(path=>({type:'frame_reference',path}))]});
      if(publicAdviceStep!==steps){
        publicAdviceStep=steps;
        try{publicAdvice=await publicDecisionAdvice({text:observation.publicText??'',step:steps,history:[{source:'obs-0',action:null,publicFeedback:opened.observation.publicText??''},...publicReceipts.evidenceHistory()],remaining:stepCeiling-steps,scope});}
        catch(error){publicAdvice={error:String(error),noWorldActionExecuted:true};}
        if(publicAdvice)appendFileSync(join(runDir,'automatic-branch-advice.jsonl'),JSON.stringify({step:steps,...publicAdvice})+'\n');
      }
      if(publicAdvice)turns.push({role:'user',text:[{type:'text',text:'PREREQUISITE_MODULE_ADVICE: '+JSON.stringify({moduleId:publicAdvice.moduleId,output:publicAdvice.output,details:publicAdvice.details,scope:publicAdvice.scope,error:publicAdvice.error})+' This computes from current public evidence only. Check its assumptions; execute your selected native action yourself. Known unsafe candidates are not safe merely because another action is uncertain.'}]});
      const receipts=publicReceipts.snapshot();
      turns.push({role:'user',text:[{type:'text',text:'PUBLIC_EXECUTION_RECEIPTS: '+JSON.stringify(receipts)}]});
      appendFileSync(join(runDir,'public-execution-receipts.jsonl'),JSON.stringify({step:steps,receipts})+'\n');
      turns=actionOnlyPresentation(turns);
      const nativeTool = isAnchor ? observation.tool
        : presentation ? { ...driver.tool, parameters: eleusisToolSchema() }
        : taskId==='among_us_deception_sandbox'?{...driver.tool,description:playerActionContract}:driver.tool;
      const evidenceEnabled=Boolean(moduleRegistry?.evidenceProtocol);
      if(evidenceEnabled)policySession?.configure(nativeTool.parameters);
      const tool=evidenceEnabled?evidenceTool(nativeTool):nativeTool;
      if(!evidenceEnabled)turns=[...turns,{role:'user',text:[{type:'text',text:`Public observation ID: obs-${steps}. Earlier obs-N refers to the observation after N native actions. Native actions remaining: ${stepCeiling-steps}. Optional module consultations use only these public observations; do not invent facts or public rules.`}]}];
      if(evidenceEnabled)turns=[...turns,{role:'user',text:[{type:'text',text:`Current public observation ID: obs-${steps}. Past obs-N references refer to observations after N native actions. Budget ledger: ${JSON.stringify(policySession?.getBudgetStatus(stepCeiling-steps))}. Frozen goal contract: ${JSON.stringify(policySession?.getContract()??null)}. Prior evidence coverage: ${JSON.stringify(policySession?.getEvidenceStatus()??null)}. If null, declare setup on this action using exact quotes from the initial public observation. Later use setup:null and these fixed requirement IDs/types. Evidence is metadata; all native actions and scoring remain unchanged.`}]}];
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
      const eventCorrection=auxiliaryAtStep===2?pendingSequenceCorrection({step:steps,runDir,activeBranch,scope}):null;
      if(eventCorrection)turns.push({role:'user',text:[{type:'text',text:'ONE_EVENT_PARTITION_CORRECTION: '+JSON.stringify(eventCorrection)}]});
      let { toolId, toolName, action, stopReason, stopDetails, usage, assistantContent } = await withDeadline(callPlayerRetrying(
        turns, runDir, tool, episode.id, moduleCalls >= MODULE_CALLS_PER_STEP || (auxiliaryAtStep >= 2&&!eventCorrection), forceModule),
        EPISODE_STALL_MS, `the Player request at step ${steps}`);
      if (usage) for (const k of Object.keys(tok)) tok[k] += usage[k] ?? 0;
      if(toolName===branchTool.name&&action){
        auxiliaryAtStep++;
        const forbiddenExtra=auxiliaryAtStep>2&&(!eventCorrection||action.moduleId!=='eventLedger'||action.input?.mode!=='audit_public_sequence');
        const response=forbiddenExtra?{ok:false,noWorldActionExecuted:true,error:'Only the single pending event-partition correction is available; no extra acquisition is authorized.'}:action.input?.mode==='audit_public_sequence'?auditPublicSequence(action,{step:steps,runDir,activeBranch,scope}):action.input?.mode==='acquire_public_video'?acquirePublicSource(action,{observation,step:steps,runDir,activeBranch,scope,index:auxiliaryAtStep}):['inspect_public_frame','inspect_public_sequence'].includes(action.input?.mode)?inspectPublicFrame(action,{observation,step:steps,runDir,activeBranch,scope,index:auxiliaryAtStep}):await consultBranch(action,steps,stepCeiling-steps);
        if(response.ok&&['inspect_public_frame','inspect_public_sequence','acquire_public_video'].includes(action.input?.mode))visualInspectedAt=steps;
        appendFileSync(join(runDir,'branch-module-calls.jsonl'),JSON.stringify({step:steps,toolId,input:action,...response})+'\n');
        moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(response)}]});
        if(response.imagePaths?.length)moduleExtra.push({role:'user',text:[{type:'text',text:response.evidenceCaption??'Additional original-video evidence decoded by the acquisition module. Read in chronological order; timestamps are seconds in the source. Interpret event identity and complete cycles yourself.'},...response.imagePaths.map(path=>({type:'frame_reference',path}))]});
        if(response.imagePath)moduleExtra.push({role:'user',text:[{type:'text',text:'Read-only enlargement of already delivered pixels. Preserve source identity and interpret the image yourself.'},{type:'frame_reference',path:response.imagePath}]});
        continue;
      }
      const retained=retainedProviderOutcome({stopReason,action},{nativeOutputCapPolicy:Boolean(unseenMode&&opened.hostEnd)});
      if(retained) {
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
      if(toolName===tool.name){
        if(eventCorrection&&eventCorrectionReviewedAt!==steps){
          eventCorrectionReviewedAt=steps;
          appendFileSync(join(runDir,'event-correction-reviews.jsonl'),JSON.stringify({step:steps,proposed:action,...eventCorrection})+'\n');
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(eventCorrection)}]});continue;
        }
        const eventReview=reviewPublicSequence({observation,step:steps,runDir,activeBranch,scope,alreadyReviewed:eventReviewedAt===steps,auxiliaryCalls:auxiliaryAtStep});
        if(eventReview){
          eventReviewedAt=steps;
          appendFileSync(join(runDir,'event-ledger-reviews.jsonl'),JSON.stringify({step:steps,proposed:action,moduleId:'eventLedger',...eventReview})+'\n');
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(eventReview)}]});continue;
        }
        const visualReview=visualCommitReview({sourceAvailable:!!sourceNotice,frameCount:observation.frames?.length??0,inspected:visualInspectedAt===steps,alreadyReviewed:visualReviewedAt===steps,moduleId:activeBranch.find(m=>m.moduleId==='adaptiveAcquisition')?.moduleId,source:`obs-${steps}`});
        if(visualReview.status==='review_once'){
          visualReviewedAt=steps;moduleCallsTotal++;
          appendFileSync(join(runDir,'visual-commit-reviews.jsonl'),JSON.stringify({step:steps,proposed:action,...visualReview})+'\n');
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(visualReview)}]});continue;
        }
      }
      if(toolName===tool.name&&publicAdvice?.input?.mode==='cooperative_forecast'&&publicAdvice.output?.ranked){
        const chosen=publicAdvice.output.ranked.find(c=>JSON.stringify(c.action)===JSON.stringify(action)),best=publicAdvice.output.recommendation;
        const reconsider=Boolean(chosen&&best&&consequenceReviewAt!==steps&&(chosen.deathProbability>best.deathProbability+.15||best.expected-chosen.expected>4));
        appendFileSync(join(runDir,'cooperative-action-reviews.jsonl'),JSON.stringify({step:steps,proposed:action,chosen,best,reconsideration:reconsider})+'\n');
        if(reconsider){consequenceReviewAt=steps;moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify({noWorldActionExecuted:true,oneTimeReconsideration:true,proposedForecast:chosen,alternative:best,note:'Compare the modeled partner responses and survival risk. If no public evidence contradicts this partner model, prefer the better forecast. No action is substituted; select one native move.'})}]});continue;}
      }
      if(toolName===tool.name&&publicAdvice?.input?.mode==='consequence_matrix'){
        const chosen=publicAdvice.input.candidates.find(c=>JSON.stringify(c.action)===JSON.stringify(action));
        const excluded=chosen&&publicAdvice.output.excluded.find(c=>c.id===chosen.id&&c.reason==='known_unsafe_consequence');
        const reconsider=Boolean(excluded&&publicAdvice.output.recommendation&&publicAdvice.output.recommendation.expected>0&&consequenceReviewAt!==steps);
        appendFileSync(join(runDir,'consequence-action-reviews.jsonl'),JSON.stringify({step:steps,proposed:action,excluded:excluded??null,reconsideration:reconsider})+'\n');
        if(reconsider){
          consequenceReviewAt=steps;
          const review={noWorldActionExecuted:true,oneTimeReconsideration:true,modelExclusion:excluded,alternative:publicAdvice.output.recommendation,note:'The prerequisite public consequence model predicts an avoidable bad outcome. Reconsider once using actual public evidence. No action is substituted. If the model assumptions are inapplicable, select the legal action you judge appropriate.'};
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify(review)}]});continue;
        }
      }
      const evidenceSplit=evidenceEnabled?splitAction(action,nativeTool.parameters):{native:action,evidence:null};
      if(evidenceSplit.transportRepair)appendFileSync(join(runDir,'evidence-transport-repairs.jsonl'),JSON.stringify({step:steps,repair:evidenceSplit.transportRepair,original:action,native:evidenceSplit.native})+'\n');
      const legal = action && toolName===tool.name ? driver.normalizeAction(evidenceSplit.native) : null;
      if (!legal) appendFileSync(join(runDir, 'invalid-actions.jsonl'), JSON.stringify({step:steps,toolName,action,stopReason})+'\n');
      if (!legal) {
        if(nativeThinking&&toolId)nativeWires.get(runDir)?.nativeResult(toolId,{type:'tool_result',tool_use_id:toolId,content:JSON.stringify({invalidNativeAction:true,noWorldActionExecuted:true})});
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
      const planReview=await reviewPublicPlan({action:legal,publicText:observation.publicText??'',step:steps,history:[{source:'obs-0',publicFeedback:opened.observation.publicText??''},...publicReceipts.evidenceHistory()],scope});
      if(planReview){
        moduleCallsTotal++;appendFileSync(join(runDir,'plan-constraint-reviews.jsonl'),JSON.stringify({step:steps,action:legal,...planReview})+'\n');
        if(planReview.output.status==='revise'){
          auxiliaryAtStep++;
          if(auxiliaryAtStep>4){terminal={ended:false,outcome:'module_guard_exhausted',reason:'Repeated public constraint violations before native submission',score:null};break;}
          moduleExtra.push({role:'assistant',content:assistantContent},{role:'tool',results:[{id:toolId,output:JSON.stringify({noWorldActionExecuted:true,moduleAdvice:planReview.output,instruction:'Revise the proposal to satisfy the already disclosed public constraints. Changing a forbidden resource to a functional synonym does not repair it. Submit the complete corrected native plan.'})}]});
          continue;
        }
      }
      let checkedPolicy=null;
      if(policySession){
        checkedPolicy=policySession.check(legal,evidenceSplit.evidence,{remaining:stepCeiling-steps,commitReserve:1});moduleCallsTotal++;
        appendFileSync(join(runDir,'module-calls.jsonl'),JSON.stringify({step:steps,automatic:true,input:{proposedAction:legal,evidencePacket:evidenceSplit.evidence},...checkedPolicy})+'\n');
        if(!checkedPolicy.ok){terminal={ended:false,outcome:'module_error',reason:checkedPolicy.error,score:null};break;}
        if(adviceBudget.shouldReview(checkedPolicy.output.status,checkedPolicy.output.analysis)){
          const feedback={moduleAdvice:true,noWorldActionExecuted:true,...checkedPolicy.output,hostPolicyContract:'Review this gap once; unchanged gaps do not require repeated reviews. It is strategic guidance, not a claim of native illegality. You may keep your proposal or revise it, then submit the action. There is no separate consultation tool.'};
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
      publicReceipts.record(legal,observation.publicText);
      if(verifiedSession)verifiedSession.record(legal,{publicText:observation.publicText??''});
      if(policySession){appendFileSync(join(runDir,'policy-executions.jsonl'),JSON.stringify({step:steps,action:legal,...checkedPolicy,publicFeedback:observation.publicText})+'\n');policySession.record(legal,{publicText:(observation.publicText??'')+'\nPUBLIC_FRAME_SHA256: '+(observation.frame?.sha256??'unavailable')});policyRejectedAtStep=0;adviceBudget.nativeStepCompleted();}
      if(nativeThinking)nativeWires.get(runDir)?.nativeResult(toolId,toAnthropicContent(actionOnlyPresentation([buildToolResultTurn(toolId,observation)])[0],runDir)[0]);
      stored.push(buildToolResultTurn(toolId, observation));
      steps += 1;

      moduleCalls = 0; moduleExtra = []; auxiliaryAtStep=0;
    }

    finishReplay(runDir);
    terminal = finishWithStepBudget({terminal, observation, steps, budget: stepBudget});
  } catch (error) {
    if(error.responseUsage)for(const k of Object.keys(tok))tok[k]+=error.responseUsage[k]??0;

    if (error instanceof EpisodeTimeout) {
      log(`  ${episode.id} TIMEOUT ${error.message} -- ending episode as 'timeout'`);
      terminal = { ended: false, outcome: 'timeout', reason: error.message };
    } else {
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
    arm: moduleRegistry||activeBranch.length ? 'module+skills' : freeTools ? 'skills/free-tools' : baselineArm ? 'baseline' : 'skills',
    modules:activeBranch.map(e=>e.moduleId), automaticPolicyModules:moduleRegistry ? Object.keys(moduleRegistry.active) : [],

    plannedEpisodes: plan.length, wholePlanEpisodes: wholePlan,
    ...(shardTotal > 1 ? { shard: `${shardIndex}/${shardTotal}` } : {}),
    results }, null, 2) + '\n');
}
const won = results.filter(r => r.outcome === 'success').length;
log(`FINISHED ${taskId}: ${won}/${results.length} success`);
