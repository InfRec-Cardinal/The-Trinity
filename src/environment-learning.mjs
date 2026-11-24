import {learningContract, reusableContract, verifyReusableEpisode} from './environment-learning-reuse.mjs';
import {executionLimits} from '../harness/src/execution-policy.mjs';
import {validateFreeActionAllowance} from '../harness/src/execution-policy.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {Store,clone,compose,digest,ensure,snapshot,verifyLedger} from '../harness/src/core.mjs';
import {Agent} from '../harness/src/agent.mjs';
import {validateRegistry,installModules,registry} from '../harness/src/runtime.mjs';
import {loadModuleRelease} from './module-release.mjs';
import {fileURLToPath} from 'node:url';
import {freezeExplorationInstances} from '../harness/src/exploration-plan.mjs';
import {runBatch,performanceDecision,chooseInheritance} from '../harness/src/explorer.mjs';
import {buildNodeModuleGenerationRequest,retainNodeModuleGeneration} from '../harness/src/generation.mjs';
import {scoreSummary,usageReport} from '../harness/src/metrics.mjs';
import {readEnvironmentPackage,assertEnvironmentReuse} from './environment-package.mjs';
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const positive=(value,name)=>ensure(Number.isSafeInteger(value)&&value>0,'Positive integer required: '+name);
const learnerRevision=()=>{
 const root=fileURLToPath(new URL('../',import.meta.url)),files=[];
 const walk=relative=>{for(const entry of fs.readdirSync(path.join(root,relative),{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
  const name=relative+'/'+entry.name;
  if(entry.isDirectory())walk(name);else if(entry.isFile())files.push([name,fs.readFileSync(path.join(root,name),'utf8')]);
 }};
 for(const dir of ['src','harness/src','harness/config','harness/prompts','pipeline/src'])walk(dir);
 for(const name of ['cli.mjs','package.json'])files.push([name,fs.readFileSync(path.join(root,name),'utf8')]);
 return digest(files);
};
export function readLearningCheckpoint(directory){
 directory=path.resolve(directory);const envelope=read(path.join(directory,'checkpoint.json'));
 const {artifact,hash,event}=envelope;
 ensure(artifact?.schema==='trinity-environment-learning-checkpoint-v1'&&digest(artifact)===hash,'Invalid learning checkpoint');
 const ledger=verifyLedger(path.join(directory,'events.jsonl'));ensure(!ledger.truncatedTail,'Truncated learning ledger');
 const events=fs.readFileSync(path.join(directory,'events.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
 ensure(events.some(e=>e.hash===event&&e.type==='environment_learning_checkpoint'&&e.payload.artifactDigest===hash),'Checkpoint event missing');
 ensure(Number.isInteger(artifact.cursor)&&artifact.cursor>=0&&artifact.summary.length===artifact.cursor,'Invalid checkpoint progress');
 for(const [node,modules] of Object.entries(artifact.registries)){validateRegistry(modules);ensure(modules.every(m=>m.targetCapabilityNodeId===node),'Checkpoint module owner mismatch');}
 for(const modules of Object.values(artifact.inheritedRegistries??{}))validateRegistry(modules);
 return {directory,...clone(envelope)};
}
export function prepareEnvironmentLearning({environmentPackage,epochs,tasks,nodes,resumeFrom=null,validationPolicies,moduleRelease,maxFreeActions,selectiveInheritance}={}){
 const pkg=readEnvironmentPackage(environmentPackage),previous=resumeFrom?readLearningCheckpoint(resumeFrom):null;
 moduleRelease??=previous?.artifact.plan.moduleRelease?.name;
 const release=moduleRelease?loadModuleRelease(moduleRelease):null;
 if(previous)installModules(Object.values(previous.artifact.registries).flat(),{nativeHost:release?.nativeHost});
 ensure(!(tasks?.length&&nodes?.length),'Choose tasks or nodes');
 let selected=pkg.curriculum;
 if(tasks!==undefined){ensure(Array.isArray(tasks)&&tasks.length&&new Set(tasks).size===tasks.length&&tasks.every(id=>selected.some(t=>t.id===id)),'Unknown or duplicate task selection');selected=selected.filter(t=>tasks.includes(t.id));}
 if(nodes!==undefined){ensure(Array.isArray(nodes)&&nodes.length&&new Set(nodes).size===nodes.length&&nodes.every(id=>selected.some(t=>t.node===id)),'Unknown or duplicate node selection');selected=selected.filter(t=>nodes.includes(t.node));}
 if(previous&&tasks===undefined&&nodes===undefined)selected=selected.filter(t=>previous.artifact.plan.taskIds.includes(t.id));
 epochs??=previous?.artifact.epochs??1;positive(epochs,'epochs');
 maxFreeActions??=previous?.artifact.plan.maxFreeActions??8;validateFreeActionAllowance(maxFreeActions);
 selectiveInheritance??=previous?.artifact.plan.selectiveInheritance??false;
 ensure(typeof selectiveInheritance==='boolean','Invalid selective inheritance policy');
 const plan={schema:'trinity-environment-learning-plan-v1',packageId:pkg.descriptor.id,packageRevision:pkg.revision,learnerRevision:learnerRevision(),
  purpose:'fixed_environment_learning',paperProtocol:false,selectiveInheritance,maxFreeActions,moduleRelease:release?.identity??null,taskIds:selected.map(t=>t.id),trainingTrials:5,validationTrials:5,instanceSemantics:pkg.descriptor.instanceSemantics,
  validationPolicies:clone(validationPolicies??previous?.artifact.plan.validationPolicies??{})};
 if(previous){ensure(digest(plan)===digest(previous.artifact.plan),'Resume requires the same environment package, curriculum and policies');ensure(epochs>=previous.artifact.epochs,'Resume cannot reduce epochs');ensure(previous.artifact.cursor<=selected.length*epochs,'Invalid resume cursor');}
 const initialRegistries={};
 for(const m of release?.modules??[]){ensure(Object.hasOwn(pkg.descriptor.capabilities,m.targetCapabilityNodeId),'Release module owner absent from curriculum');(initialRegistries[m.targetCapabilityNodeId]??=[]).push(m);}
 return {pkg,plan,selected,epochs,previous,initialRegistries,nativeHost:release?.nativeHost};
}
export function verifyLearningCompletion(directory){
 const checkpoint=readLearningCheckpoint(directory),{artifact,hash,event}=read(path.join(directory,'learning-complete.json'));
 ensure(artifact?.schema==='trinity-environment-learning-complete-v1'&&digest(artifact)===hash,'Invalid learning completion');
 const names=['learning-plan.json','checkpoint.json','learned-harness.json','summary.json'];
 ensure(digest(Object.keys(artifact.files).sort())===digest(names.sort()),'Incomplete learning artifact pins');
 for(const name of names)ensure(digest(read(path.join(directory,name)))===artifact.files[name],'Completed learning artifact changed: '+name);
 const ledger=fs.readFileSync(path.join(directory,'events.jsonl'),'utf8').trim().split('\n').map(JSON.parse),last=ledger.at(-1);
 ensure(last.hash===event&&last.type==='environment_learning_completed'&&last.payload.artifactDigest===hash,'Learning completion must be the final event');
 ensure(artifact.completed===checkpoint.artifact.cursor&&artifact.completed===checkpoint.artifact.plan.taskIds.length*checkpoint.artifact.epochs,'Learning curriculum is incomplete');
 return {artifact,hash,event};
}
function activeModules(registries,scope){return scope.reduce((modules,node)=>compose(modules,registries[node]??[]),[]);}
export function retainedNodeModules(registries,inheritedRegistries,node){return compose(inheritedRegistries[node]??[],registries[node]??[]);}
export async function validateEnvironmentLearning(prepared,driverOptions={}, {allowLocalEnvironment=false}={}){
 const driver=await prepared.pkg.createDriver(driverOptions,{allowLocalEnvironment});const checked=[];
 try{
  for(const task of prepared.selected){
   const world=await driver.loadBenchmark(clone(task));ensure((await driver.fingerprint(clone(world))).revision===prepared.pkg.revision,'Driver package revision mismatch');
   let session;
   try{
    const instances=await driver.instanceManifest(clone(world),1);ensure(instances.length===1,'Invalid instance manifest');
    session=await driver.reset(clone(world),instances[0]);
    ensure(session?.observation&&session.actionSchema?.type==='object','Invalid environment reset');
    ensure(session.observation.feedback?.budget===task.budget,'Curriculum budget mismatch');
    ensure(await driver.initialState(session),'Missing initial state');checked.push(task.id);
   }finally{if(session)await driver.close(session);}
  }
  prepared.pkg.verify();return {passed:true,packageId:prepared.plan.packageId,packageRevision:prepared.pkg.revision,tasks:checked,modelCalls:0,instanceSemantics:prepared.plan.instanceSemantics};
 }finally{await driver.shutdown();}
}
function exportedHarness(prepared,registries,inheritedRegistries){
 const scopes=new Map(prepared.pkg.curriculum.map(t=>[t.node,t.moduleScope]));
 return {schema:'trinity-learned-environment-harness-v1',packageId:prepared.plan.packageId,packageRevision:prepared.plan.packageRevision,
  moduleRelease:prepared.plan.moduleRelease,learnerRevision:prepared.plan.learnerRevision,registries:clone(registries),inheritedRegistries:clone(inheritedRegistries),harnesses:[...scopes].filter(([node])=>registries[node]).map(([node,scope])=>({node,moduleScope:scope,...snapshot(prepared.plan.selectiveInheritance?retainedNodeModules(registries,inheritedRegistries,node):activeModules(registries,scope))}))};
}
export async function learnEnvironments({prepared,backend,directory,driver=null,driverOptions={},allowLocalEnvironment=false,executionIdentity=backend?.executionProfile??null}){
 ensure(prepared?.pkg&&backend&&typeof backend.respond==='function','Prepared package and agent backend required');
 if(!driver)assertEnvironmentReuse(driverOptions,allowLocalEnvironment);
 installModules(Object.values(prepared.previous?.artifact.registries??prepared.initialRegistries??{}).flat(),{nativeHost:prepared.nativeHost});
 directory=path.resolve(directory);ensure(!fs.existsSync(directory),'Choose a new output directory');prepared.pkg.verify();
 const contract=learningContract(prepared.plan,executionIdentity,driverOptions);
 const config={learningContract:contract,mode:'environment_package_learning',allowLocalEnvironment,plan:prepared.plan,epochs:prepared.epochs,
  resume:prepared.previous?{checkpointHash:prepared.previous.hash,cursor:prepared.previous.artifact.cursor}:null};
 const store=new Store(directory,config),agent=new Agent(backend,store);
 let registries=clone(prepared.previous?.artifact.registries??prepared.initialRegistries??{}),summary=clone(prepared.previous?.artifact.summary??[]);
 let inheritedRegistries=clone(prepared.previous?.artifact.inheritedRegistries??{});
 for(const [node,modules] of Object.entries(inheritedRegistries)){
  const scope=prepared.pkg.curriculum.find(t=>t.node===node)?.moduleScope;
  ensure(scope&&modules.every(m=>scope.includes(m.targetCapabilityNodeId)&&m.targetCapabilityNodeId!==node),'Inherited module owner outside node scope');
  installModules(modules,{nativeHost:prepared.nativeHost});
 }
 let validationFeedback=clone(prepared.previous?.artifact.validationFeedback??{}),learningFeedback=clone(prepared.previous?.artifact.learningFeedback??{}),cursor=prepared.previous?.artifact.cursor??0;
 let ownedDriver=false,closed=false,failure=null;
 const checkpoint=()=>{
  const artifact={schema:'trinity-environment-learning-checkpoint-v1',plan:prepared.plan,epochs:prepared.epochs,cursor,registries,inheritedRegistries,validationFeedback,learningFeedback,summary};
  const hash=digest(artifact),event=store.record('environment_learning_checkpoint',{artifactDigest:hash,cursor});
  store.write('checkpoint.json',{artifact,hash,event});
  store.write('learned-harness.json',exportedHarness(prepared,registries,inheritedRegistries));
 };
 try{
  store.write('learning-plan.json',{...prepared.plan,epochs:prepared.epochs,curriculum:prepared.selected});
  checkpoint();
  if(!driver){driver=await prepared.pkg.createDriver(driverOptions,{allowLocalEnvironment});ownedDriver=true;}
  for(;cursor<prepared.selected.length*prepared.epochs;){
   prepared.pkg.verify();
   const task=prepared.selected[cursor%prepared.selected.length],epoch=Math.floor(cursor/prepared.selected.length)+1;
   agent.scope={node:task.node,iteration:epoch};
   const world=await driver.loadBenchmark(clone(task)),fingerprint=await driver.fingerprint(clone(world));
   ensure(fingerprint.revision===prepared.pkg.revision,'Driver package revision mismatch');
   const plan=await freezeExplorationInstances({driver,world,trials:5,store,taskId:task.id});
   let selectedInheritance=clone(inheritedRegistries[task.node]??[]),inheritance=null;
   const usageStart=agent.calls.length;
   const options={learningContract:contract,nativeHost:prepared.nativeHost,agent,driver,store,world,budget:task.budget,maxFreeActions:prepared.plan.maxFreeActions,taskId:task.id,benchmarkId:prepared.plan.packageId,split:'train',
    node:task.node,iteration:epoch,instances:plan.instances,initialStateHashes:plan.initialStateHashes,instancePlan:plan.event};
   const reuse=prepared.reuse?.[task.id]??null;
   const limits=executionLimits({budget:task.budget,driver,maxFreeActions:prepared.plan.maxFreeActions});
   const reused=(phase,harnessId)=>(reuse?.[phase]??[]).filter(({report:row})=>reusableContract(contract)&&row&&!row.technicalFailure&&row.iteration===epoch&&row.taskId===task.id&&row.node===task.node&&row.phase===phase&&digest(row.learningContract)===digest(contract)&&row.worldDigest===plan.worldDigest&&row.harnessId===harnessId&&row.budget===task.budget&&(row.budgetUnit??'action')===limits.budgetUnit&&(row.interactionLimit??row.budget)===limits.interactionLimit);
   const fill=async(phase,batchModules,keep)=>{
    const harnessId=snapshot(batchModules).id,rows=new Array(5).fill(null),imports=[];
    if(keep)for(const entry of reused(phase,harnessId)){
     const row=entry.report,i=plan.instances.findIndex(x=>digest(x)===digest(row.instance));
     if(i>=0&&!rows[i]&&row.initialStateHash===plan.initialStateHashes[i]){
      verifyReusableEpisode(row,entry.proof,contract);rows[i]=clone(row);imports.push(entry);
     }
    }
    const missing=rows.map((row,i)=>row?null:i).filter(i=>i!==null);
    for(const entry of imports)store.record('episode_reused',{...entry.report,reuseProofDigest:store.put(entry.proof),reusedFrom:entry.source});
    store.record('environment_episodes_reused',{taskId:task.id,phase,reused:rows.map((row,i)=>row?{trial:i,episodeId:row.episodeId}:null).filter(Boolean),played:missing});
    driver.setPhase?.(phase);
    if(missing.length){
     const played=await runBatch({...options,modules:batchModules,phase,instances:missing.map(i=>plan.instances[i]),initialStateHashes:missing.map(i=>plan.initialStateHashes[i])},missing.length);
     missing.forEach((i,k)=>{rows[i]=played[k];});
    }
    return rows;
   };
   if(prepared.plan.selectiveInheritance&&task.moduleScope.length>1){
    const parent=task.moduleScope.at(-2),candidateInheritance=retainedNodeModules(registries,inheritedRegistries,parent);
    const oldModules=compose(selectedInheritance,registries[task.node]??[]),newModules=compose(candidateInheritance,registries[task.node]??[]);
    const oldSnapshot=snapshot(oldModules),newSnapshot=snapshot(newModules);
    if(oldSnapshot.id!==newSnapshot.id){
     const previousRows=await fill('inheritance_previous',oldModules,false),candidateRows=await fill('inheritance_candidate',newModules,false);
     const decision=chooseInheritance(previousRows,candidateRows);
     inheritance={...decision,parent,previousHarnessId:oldSnapshot.id,candidateHarnessId:newSnapshot.id,
      previousEpisodes:previousRows.map(r=>r.episodeId),candidateEpisodes:candidateRows.map(r=>r.episodeId)};
     store.record('environment_inheritance_decision',{node:task.node,taskId:task.id,epoch,...inheritance});
     ensure(![...previousRows,...candidateRows].some(r=>r.technicalFailure),'Technical inheritance failure; checkpoint was not advanced');
     if(decision.accepted)selectedInheritance=clone(candidateInheritance);
    }else inheritance={accepted:false,reason:'unchanged',parent,previousHarnessId:oldSnapshot.id,candidateHarnessId:newSnapshot.id};
   }
   const modules=prepared.plan.selectiveInheritance?compose(selectedInheritance,registries[task.node]??[]):activeModules(registries,task.moduleScope),start=snapshot(modules);
   store.record('environment_learning_started',{cursor,epoch,taskId:task.id,node:task.node,harnessId:start.id,worldDigest:plan.worldDigest});
   const trajectories=await fill('environment_learning',modules,true);
   ensure(!trajectories.some(row=>row.technicalFailure),'Technical learning failure; checkpoint was not advanced');
   const context={mode:'training',node:task.node,boundary:5,inheritedRegistry:modules,validationPolicies:prepared.plan.validationPolicies,
    capabilityDefinitions:task.moduleScope.map(node=>clone(prepared.pkg.descriptor.capabilities[node])),
    feedback:clone(learningFeedback[task.node]??[]),...(validationFeedback[task.node]?{hostValidationFeedback:validationFeedback[task.node]}:{}),
    trajectories:trajectories.map((row,index)=>({round:index+1,events:row.events}))};
   const request=buildNodeModuleGenerationRequest(context,{nativeHost:prepared.nativeHost});
   const packet={...request.packet,iteration:epoch,environment:{taskId:task.id,instanceSemantics:prepared.plan.instanceSemantics}};
   const requestDigest=store.put({...request,packet}),trainingEpisodes=trajectories.map(t=>t.episodeId),feedbackDigest=digest(context.feedback);
   const priorProposal=reusableContract(contract)?reuse?.proposals?.find(p=>p.epoch===epoch&&p.node===task.node&&digest(p.learningContract)===digest(contract)&&p.requestDigest===requestDigest&&p.feedbackDigest===feedbackDigest&&digest(p.trainingEpisodes)===digest(trainingEpisodes)):null;
   const proposal=priorProposal?clone(priorProposal.value):await agent.ask('evolver_modules',packet,request.schema);
   store.record('explorer_proposal_saved',{node:task.node,epoch,taskId:task.id,learningContract:contract,requestDigest,trainingEpisodes,feedbackDigest,proposalDigest:store.put(proposal),...(priorProposal?{reusedFrom:priorProposal.source}:{})});
   const result=await retainNodeModuleGeneration(context,proposal,{nativeHost:prepared.nativeHost});
   const candidateRegistries=clone(registries);
   if(result.accepted)candidateRegistries[task.node]=result.registry.filter(m=>m.targetCapabilityNodeId===task.node);
   const candidate=prepared.plan.selectiveInheritance?compose(selectedInheritance,candidateRegistries[task.node]??[]):activeModules(candidateRegistries,task.moduleScope);
   const evaluation=await fill('environment_training_side_evaluation',candidate,Boolean(priorProposal));
   ensure(!evaluation.some(row=>row.technicalFailure),'Technical evaluation failure; checkpoint was not advanced');
   prepared.pkg.verify();ensure(digest(await driver.fingerprint(clone(world)))===plan.worldDigest,'Environment changed during learning');
   const measurement=performanceDecision(trajectories,evaluation);
   registries=candidateRegistries;
   if(prepared.plan.selectiveInheritance)inheritedRegistries[task.node]=selectedInheritance;
   validationFeedback[task.node]=result.accepted?null:clone(result.audit);
   learningFeedback[task.node]=clone([...trajectories,...evaluation].map(({learningContract,reusedFrom,...row})=>row));
   const row={cursor,epoch,taskId:task.id,node:task.node,previousHarnessId:start.id,harnessId:snapshot(candidate).id,
    moduleUpdateAccepted:result.accepted,moduleAudit:result.audit,measurement,inheritance,
    trainingScores:scoreSummary(trajectories),evaluationScores:scoreSummary(evaluation),usage:agent.usageSince(usageStart),
    trainingEpisodes:trajectories.map(t=>t.episodeId),evaluationEpisodes:evaluation.map(t=>t.episodeId)};
   summary.push(row);cursor++;store.record('environment_learned',row);checkpoint();
  }
  prepared.pkg.verify();
  if(ownedDriver){closed=true;await driver.shutdown();}
  const result={schema:'trinity-environment-learning-summary-v1',mode:config.mode,packageId:prepared.plan.packageId,
   packageRevision:prepared.plan.packageRevision,epochs:prepared.epochs,curriculumTasks:prepared.selected.length,completed:cursor,
   skippedPriorSteps:prepared.previous?.artifact.cursor??0,summary,accounting:usageReport(agent.calls),
   treeConstruction:false,creatorCalls:0,instanceSemantics:prepared.plan.instanceSemantics,generalizationClaim:false};
  store.write('summary.json',result);
  const names=['learning-plan.json','checkpoint.json','learned-harness.json','summary.json'];
  const artifact={schema:'trinity-environment-learning-complete-v1',files:Object.fromEntries(names.map(n=>[n,digest(read(path.join(directory,n)))])),packageRevision:prepared.plan.packageRevision,completed:cursor};
  const hash=digest(artifact),event=store.record('environment_learning_completed',{artifactDigest:hash});store.write('learning-complete.json',{artifact,hash,event});
  return result;
 }catch(error){failure=error;store.record('run_failed',{message:String(error.message),completed:cursor});throw error;}
 finally{if(ownedDriver&&!closed)try{await driver.shutdown();}catch(error){store.record('driver_cleanup_failed',{message:String(error.message)});if(!failure)throw error;}}
}

export function loadLearnedHarness(directory){
 verifyLearningCompletion(directory);
 const checkpoint=readLearningCheckpoint(directory),artifact=read(path.join(directory,'learned-harness.json'));
 ensure(digest(artifact.registries)===digest(checkpoint.artifact.registries),'Export differs from checkpoint');
 ensure(digest(artifact.inheritedRegistries??{})===digest(checkpoint.artifact.inheritedRegistries??{}),'Export inheritance differs from checkpoint');
 ensure(artifact.learnerRevision===learnerRevision(),'Learned harness requires the same code package');
 const release=artifact.moduleRelease?loadModuleRelease(artifact.moduleRelease.name):null;
 ensure(digest(release?.identity??null)===digest(artifact.moduleRelease),'Learned harness source release changed');
 const modules=Object.values(artifact.registries).flat(),options={nativeHost:release?.nativeHost};
 installModules(modules,options);
 for(const inherited of Object.values(artifact.inheritedRegistries??{}))installModules(inherited,options);
 return {...artifact,modules,nativeHost:release?.nativeHost,registry:registry(modules,options)};
}
