import {createHash} from 'node:crypto';
import {manifest as integratedManifest} from '../../../module-harness/harness.mjs';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {PolicySession,AdviceBudget} from '../policy-runtime/program.mjs';
import {verifyModuleBuild} from '../verify-module-build.mjs';
import {prepareFromRecords,publicBlocks,parseNativeAction} from './public-contract.mjs';
import {NativeDecisionConversation,inspectDecisionOutput} from './native-decision-protocol.mjs';
import {autoResetArc,arcPublicMeta} from './arc-auto-reset.mjs';
import {createArcBranch} from './branch-modules.mjs';
const branch=createArcBranch(process.env.H0_CAPABILITY_NODE),{consultBranch}=branch;

const harnessRoot=path.resolve(fileURLToPath(new URL('../',import.meta.url)));
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const paused=()=>assert(!fs.existsSync(path.join(harnessRoot,'PAUSED.json')),'Experiments paused by user');
assert(process.argv.includes('--execute'),'No dispatch by default; use checks/public-contract-regression.mjs for offline validation');
paused();
const round=Number(process.env.ARC_PUBLIC_ROUND);assert(Number.isSafeInteger(round)&&round>0);
const {root,callOnce,withPromptCache,hash}=await import('./public-transport.mjs');
assert(!fs.existsSync(root),'Do not overwrite a previous experiment');
fs.mkdirSync(root,{recursive:true});fs.mkdirSync(path.join(root,'attempts'));
const write=(name,x)=>fs.writeFileSync(path.join(root,name),JSON.stringify(x,null,2)+'\n');
const append=(name,x)=>fs.appendFileSync(path.join(root,name),JSON.stringify(x)+'\n');
const publicTemplateSha256=createHash('sha256').update(fs.readFileSync(process.env.ARC_REQUEST_TEMPLATE)).digest('hex');
const source=process.env.ARC_PUBLIC_SOURCE?path.resolve(process.env.ARC_PUBLIC_SOURCE):null;
const sample=JSON.parse(process.env.ARC_PUBLIC_SAMPLE_JSON);assert(sample?.caseId,'Explicit sample required');
assert.equal(round,sample.round);
const episode={id:`case-${sample.configurationIndex}-repeat-${round}`,configurationIndex:sample.configurationIndex,caseId:sample.caseId};
const actionLimit=sample.actionLimit,requestLimit=sample.requestLimit;
assert.equal(Number(process.env.ARC_NATIVE_ACTION_LIMIT),actionLimit);
let opened,observation,conversation,receipts,session,steps=0,calls=0,resets=0,helperCalls=0,invalids=0;
let outcome='initializing',lastInputTokens=0;
let sourceResult=null,sourceManifest=null,inheritedCalls=0,startActions=0;
const records=[],advice=new AdviceBudget(),started=Date.now();
write('budget.json',{limit:requestLimit,attemptsStarted:0,attemptsCompleted:0,automaticRetries:0,
  provider:process.env.RELAY_BASE_URL??'https://api.anthropic.com',model:'claude-opus-5',nativeActionLimit:actionLimit,
  scope:'Only an explicitly resumed/started sample. No refusal retries. Source replay uses zero API calls.'});
try {
  const build=verifyModuleBuild();
  if(source)assert.equal(read(path.join(source,'run-manifest.json')).node??'d-a',branch.node,'Resume node mismatch');
  const envRoot=path.resolve(process.env.H0_ENV_ROOT);
  const {createTrainDriverRegistry}=await import((await import('node:url')).pathToFileURL(path.join(envRoot,'interface/registry.mjs')));
  const driver=await createTrainDriverRegistry({root:envRoot,record:true}).getDriver('arc_agi_3');
  const configurations=structuredClone(driver.configurations);
  const selectedConfiguration=configurations[episode.configurationIndex];assert.equal(selectedConfiguration.id,episode.caseId);
  selectedConfiguration.parentBudgetConfigurationHash=selectedConfiguration.configurationHash;
  selectedConfiguration.maxSteps=actionLimit;
  selectedConfiguration.evaluationBudgetPolicy='Explicit per-level action budget; RESET included';
  delete selectedConfiguration.configurationHash;
  selectedConfiguration.configurationHash=(await import('node:crypto')).createHash('sha256').update(JSON.stringify(selectedConfiguration)).digest('hex');
  write('selected-configuration.json',selectedConfiguration);
  paused();opened=await driver.open({runDir:root,run:{configurations},episode});
  observation=opened.observation;
  if(source) {
    sourceResult=read(path.join(source,'result.json'));sourceManifest=read(path.join(source,'run-manifest.json'));
    assert.equal(sourceManifest.integratedHarnessId,integratedManifest.harnessId,'Resume requires the same integrated harness');
    assert.equal(sourceManifest.publicTemplateSha256,publicTemplateSha256,'Resume template changed');
    assert.equal(sourceManifest.actionLimit,actionLimit,'Resume action budget changed');
    assert.equal(sourceManifest.requestLimit,requestLimit,'Resume request budget changed');
    assert.equal(sourceResult.outcome,'transport_error','Only a saved network interruption can use this one-shot entry');
    const latest=fs.readdirSync(path.join(source,'attempts')).filter(n=>fs.existsSync(path.join(source,'attempts',n,'metadata.json'))).sort((a,b)=>Number(a.split('-')[0])-Number(b.split('-')[0])).at(-1);
    const meta=read(path.join(source,'attempts',latest,'metadata.json'));
    assert(['TypeError','TimeoutError'].includes(meta.errorClass),'Only a network failure or deadline without a response can be resumed');assert.equal(meta.httpStatus,undefined);
    assert(!fs.existsSync(path.join(source,'attempts',latest,'response.private.raw')),'A received response requires separate diagnosis; never retry a refusal here');
    assert.equal(sourceManifest.build.policySourceSha256,build.policySourceSha256,'Do not change module during a logical retest');
    inheritedCalls=sourceResult.totalLogicalCalls??sourceResult.calls;
    assert(inheritedCalls<requestLimit,'Logical request budget exhausted');
    const budget=read(path.join(root,'budget.json'));budget.limit=requestLimit-inheritedCalls;budget.inheritedCalls=inheritedCalls;write('budget.json',budget);
    const progress=read(path.join(source,'progress.json'));
    const cp=read(path.join(source,'checkpoint.json'));assert.equal(cp.caseId,episode.caseId);
    const saved=fs.readFileSync(path.join(source,cp.record),'utf8').trim().split('\n').map(JSON.parse);
    assert.equal(saved.length,progress.steps+1,'Replay must use a complete saved checkpoint');
    const comparable=o=>{const d=structuredClone(arcPublicMeta(o));delete d.guid;return d;};
    const oldGuid=arcPublicMeta(saved[0].observation).guid,newGuid=arcPublicMeta(observation).guid;
    const normalize=o=>({...o,publicText:o.publicText.replaceAll(newGuid,oldGuid)});
    const verify=(got,want)=>{
      assert.deepEqual(comparable(got),comparable(want),'Public replay differs');
      assert.deepEqual(got.terminal,want.terminal,'Terminal replay differs');
      assert.equal(got.info.nativeActions,want.info.nativeActions);
      assert.equal((got.frame??got.previewFrame).sha256,(want.frame??want.previewFrame).sha256,'RGB replay differs');
    };
    verify(observation,saved[0].observation);observation=normalize(observation);records.push({action:null,observation});
    for(const row of saved.slice(1)) {
      paused();const result=await opened.step(parseNativeAction(row.action),{index:steps});
      const actual=result.observation??result;verify(actual,row.observation);observation=normalize(actual);steps++;
      records.push({action:row.action,observation});
    }
    const nativeStep=opened.step.bind(opened);
    opened.step=async(...args)=>{const result=await nativeStep(...args);return normalize(result.observation??result);};
    write('replay-proof.json',{source,restoredActions:steps,observationsMatched:records.length,apiCalls:0,
      policyChanged:false,freshEvaluation:false,oldSignedHistoryEdited:false,oldPlayerPlansImported:false});
  } else records.push({action:null,observation});
  session=branch.automaticId?new PolicySession(branch.scope.bindPolicy(read(path.join(harnessRoot,'../../module-harness/registries/arc_agi_3.json')),{ownerId:branch.automaticId})):null;
  ({conversation,receipts}=prepareFromRecords(read(process.env.ARC_REQUEST_TEMPLATE),records,session,branch));
  startActions=steps;

  if(source) {
    const rows=name=>fs.existsSync(path.join(source,name))?fs.readFileSync(path.join(source,name),'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
    const policyRows=rows('policy-checks.jsonl').filter(r=>r.step===steps);
    const helpers=rows('module-consultations.jsonl').filter(r=>r.step===steps);
    helperCalls=helpers.length;assert(helperCalls<=2);
    if(policyRows.some(r=>r.output?.status==='advice'))advice.shouldReview('advice');
    invalids=policyRows.filter(r=>r.output?.status==='block').length;
    const last=policyRows.at(-1);
    if(last||helpers.length) {
      const initial=conversation.request();
      initial.messages[0].content.push({type:'text',text:'PENDING_PUBLIC_MODULE_FEEDBACK: '+JSON.stringify({
        observationId:`obs-${steps}`,proposal:last?.action??null,output:last?.output??null,
        helpers:helpers.map(r=>({input:r.input,result:r.result})),remainingHelperCalls:2-helperCalls,
        noWorldActionExecuted:true,scope:'Actual prior local-module computation at this same state. No written acknowledgment is required; submit a native action.'})});
      conversation=new NativeDecisionConversation(initial);
    }
  }
  assert(source,'Network recovery requires an existing interrupted logical sample');
  const original=read(path.join(source,'conversation.json'));
  const lastAttempt=fs.readdirSync(path.join(source,'attempts')).filter(n=>fs.existsSync(path.join(source,'attempts',n,'request.json'))).sort((a,b)=>Number(a.split('-')[0])-Number(b.split('-')[0])).at(-1);
  const originalWire=read(path.join(source,'attempts',lastAttempt,'request.json'));
  conversation=new NativeDecisionConversation(original);
  assert.deepEqual(withPromptCache(conversation.request()),originalWire,'Network recovery must preserve the full original request');
  write('network-recovery-proof.json',{source,requestHash:hash(originalWire),exactRequestPreserved:true,signedHistoryPreserved:true,apiCallsForReplay:0,reason:'Network failure or deadline without a complete HTTP response; identical signed request, bounded recovery only'});
  resets=receipts.snapshot().resetCommands;
  write('run-manifest.json',{integratedHarnessId:integratedManifest.harnessId,publicTemplateSha256,sample:sample.sample,actionLimit,requestLimit,round,caseId:episode.caseId,build,source,freshFullEpisode:!source,
    logicalFreshFullEpisode:source?(sourceManifest.logicalFreshFullEpisode??sourceManifest.freshFullEpisode):true,
    totalModules:29,...branch.selection,registeredBranchModules:branch.selection.registeredModules,selectedBranchModules:branch.selection.selectedModules,thinking:{type:'adaptive',display:'omitted'},effort:'low',
    moduleAlgorithms:'v7 unchanged',skillChanges:'Output-contract wording only',
    nativeSchemaUnchanged:true,contextPolicy:'Signed history append-only; save and stop at context threshold; no automatic conversation reset'});
  const save=()=>{
    write('conversation.json',conversation.request());
    write('checkpoint.json',{round,caseId:episode.caseId,nativeActions:steps,remainingNativeActions:actionLimit-steps,
      record:`episodes/${episode.id}/record.jsonl`,publicReceipts:receipts.snapshot(),source});
    write('progress.json',{round,steps,calls,resets,outcome,terminal:observation.terminal,updatedAt:new Date().toISOString()});
  };
  const blocks=()=>{const preview=session?.preview();if(preview)assert(preview.ok,preview.error);
    if(preview)append('module-predecision.jsonl',{step:steps,...preview});
    append('public-execution-receipts.jsonl',{step:steps,...receipts.snapshot()});
    return publicBlocks(observation,preview,receipts);};
  save();
  while(steps<actionLimit&&!observation.terminal?.ended) {
    paused();
    const reset=await autoResetArc({observation,opened,steps,limit:actionLimit});
    if(reset) {
      observation=reset.observation;session?.record(reset.action,observation);receipts.record(reset.action,observation);
      steps++;resets++;helperCalls=0;invalids=0;advice.nativeStepCompleted();
      conversation.appendHostReset(reset.toolId,{publicText:observation.publicText,terminal:observation.terminal},blocks());save();continue;
    }
    const body=conversation.request();
    if(lastInputTokens>100000||JSON.stringify(body.messages).length>700000) {
      outcome='context_budget_checkpoint';save();break;
    }
    const response=await callOnce(`public-round-${round}-step-${steps}-call-${calls+1}`,body);calls++;
    if(!response.message){outcome='transport_error';save();break;}
    const checked=inspectDecisionOutput(response.message,body.tools),selected=checked.selected;
    const usage=response.message.usage??{};
    lastInputTokens=(usage.input_tokens??0)+(usage.cache_creation_input_tokens??0)+(usage.cache_read_input_tokens??0);
    append('responses.jsonl',{step:steps,attempt:response.attempt,outcome:checked.outcome,stats:checked.stats,
      errors:checked.errors??[],category:selected.stopDetails?.category??null});
    if(!checked.ok){outcome=checked.outcome;save();break;}
    if(selected.toolName==='consult_branch_module') {
      if(helperCalls>=2){outcome='helper_budget_exhausted';save();break;}
      helperCalls++;const result=await consultBranch(selected.action,steps,actionLimit-steps);
      append('module-consultations.jsonl',{step:steps,input:selected.action,result});
      conversation.appendToolResult(response.message,selected.toolId,result);save();continue;
    }
    let action;
    try {action=parseNativeAction(selected.action);assert.deepEqual(driver.normalizeAction(action),action);}
    catch(e) {
      invalids++;conversation.appendToolResult(response.message,selected.toolId,{error:e.message,noWorldActionExecuted:true});
      save();if(invalids>=3){outcome='invalid_native_action';break;}continue;
    }
    if(session){
    const policy=session.check(action);assert(policy.ok,policy.error);append('policy-checks.jsonl',{step:steps,action,...policy});
    if(policy.output.status==='block'||advice.shouldReview(policy.output.status)) {
      if(policy.output.status==='block')invalids++;
      conversation.appendToolResult(response.message,selected.toolId,{...policy.output,noWorldActionExecuted:true,
        publicContract:'Submit the next native action directly. No plan, written acknowledgment or action justification is required.'});
      save();if(invalids>=3){outcome='invalid_native_action';break;}continue;
    }
    }
    paused();const result=await opened.step(action,{index:steps});observation=result.observation??result;
    session?.record(action,observation);receipts.record(action,observation);steps++;
    assert.equal(observation.info.nativeActions,steps);helperCalls=0;invalids=0;advice.nativeStepCompleted();
    conversation.appendToolResult(response.message,selected.toolId,{publicText:observation.publicText,terminal:observation.terminal},blocks());
    outcome='running';save();
  }
  if(observation.terminal?.ended)outcome=observation.terminal.outcome;
  else if(steps>=actionLimit)outcome='action_budget_exhausted';
  save();
} catch(e) {
  outcome=fs.existsSync(path.join(harnessRoot,'PAUSED.json'))?'user_paused':'diagnostic_error';
  fs.writeFileSync(path.join(root,'error.private.txt'),String(e.stack??e));process.exitCode=1;
} finally {
  if(opened)await opened.close();
  write('result.json',{node:branch.node,path:branch.path,sample:sample.sample,actionLimit,requestLimit,round,caseId:episode.caseId,outcome,steps,calls,resets,source,freshFullEpisode:!source,
    startActions,newNativeActions:steps-startActions,inheritedCalls,totalLogicalCalls:inheritedCalls+calls,
    completed:!!observation?.terminal?.ended,score:observation?.terminal?.ended?observation.terminal.score:null,
    terminal:observation?.terminal??null,elapsedSeconds:(Date.now()-started)/1000});
}
