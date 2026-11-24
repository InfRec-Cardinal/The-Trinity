import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import '../public/tree.js';
import {runScratchSearch} from './scratch.mjs';
import {runStage2} from './stage2.mjs';
import {buildVerifiedLevel} from './build-level.mjs';
import {screeningContract} from './screening-contract.mjs';
import {materializeProject} from './project-environment.mjs';

const load=(code,file)=>import(pathToFileURL(path.join(code,file)).href);
const sha=text=>createHash('sha256').update(text).digest('hex');
const routeNode=id=>'n_'+sha(id).slice(0,20);
const save=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n');};
const levelNode=(id,capability,built)=>({id,kind:'capability',capability,pos:[0,0],
  level:{ref:built.ref,node:built.node,variant:0,budget:built.budget},
  preview:{source:'level',collapsed:false,round:1,frame:1,rounds:[{round:1,phase:null,success:null,tape:{variant:0,actions:[]}}]}});
const addLevel=(tree,built)=>{
  const entry=tree.levels[built.ref]??={source:built.source,meta:{title:built.capability.name,provides:[]}};
  if(!entry.meta.provides.some(p=>p.capability===built.capability.id&&p.node===built.node&&p.variant===0))
    entry.meta.provides.push({capability:built.capability.id,node:built.node,variant:0,budget:built.budget});
};

export function treeFromTraining(input,name='scratch') {
  if(input.schema!=='trinity-training-input-v1')throw Error('Invalid Stage 2 training handoff');
  const tree=globalThis.TrinityTree.emptyTree(name);
  tree.capabilities=structuredClone(input.capabilityDefinitions);
  tree.benchmarks=Object.fromEntries(input.trainingTasks.map(t=>[t.taskId,structuredClone(t)]));
  tree.deferredBenchmarks=structuredClone(input.unseenTasks);
  tree.baselineTasks=input.assignments.filter(a=>!a.requirements.length).map(a=>a.taskId);
  return tree;
}

export async function runScratchWorkflow({job,callModel,backend,profile,emit,signal,
  search=runScratchSearch,induce=runStage2,build=buildVerifiedLevel}) {
  const {code,apiKey,relay}=job;
  const vendorDir=path.join(job.env,'vendor');
  fs.mkdirSync(job.out,{recursive:true});
  const checkpoint=(phase,data={})=>{save(path.join(job.out,'scratch-state.json'),{schema:'trinity-studio-scratch-state-v1',phase,...data});emit('phase',{phase});};
  const {readEnvironmentPackage}=await load(code,'src/environment-package.mjs');
  const {explore}=await load(code,'src/integration.mjs');
  const {Store,buildTree}=await load(code,'harness/src/core.mjs');
  const {Agent}=await load(code,'harness/src/agent.mjs');
  const {runBatch,screeningDecision}=await load(code,'harness/src/explorer.mjs');
  const {freezeExplorationInstances}=await load(code,'harness/src/exploration-plan.mjs');
  const common={code,apiKey,relay,callModel,vendorDir};
  try {
    checkpoint('search');
    const handoff=await search({code,apiKey,callModel,profile,emit,signal,directory:path.join(job.out,'search')});
    if(handoff.schema!=='trinity-stage2-handoff-v1'||handoff.taskTree?.split?.gaps?.length||handoff.taskTree?.split?.errors?.length)throw Error('Incomplete searched task handoff');
    const tasks=handoff.tasks.filter(t=>t.set==='train');
    if(!tasks.length)throw Error('No training benchmarks found');
    save(path.join(job.out,'handoff.json'),handoff);
    checkpoint('benchmark_build');
    const benchmarkTree=globalThis.TrinityTree.emptyTree('searched-benchmarks'), taskNodes=new Map(),provenance={};
    for(const task of tasks) {
      const id='b_'+sha(task.taskId).slice(0,12),capability={id,name:task.name,definition:task.summary||task.name};
      let built,lastError;
      for(let attempt=1;attempt<=3;attempt++) {
        try {
          built=await build({...common,capability,directory:path.join(job.out,'benchmark-builds',id,'attempt-'+attempt),
            brief:{purpose:'faithful executable reconstruction of the reviewed benchmark protocol',task,
              executionMode:'local_reconstruction',constraint:'Keep the benchmark rules and scorer, including all public observations and legal actions. This is a local reconstruction, not a claim of executing an official external service. If official datasets, inaccessible assets or external services are essential, reject instead of inventing substitutes.'},
            feedback:lastError?{error:lastError}:null});
          break;
        } catch(error) {lastError=String(error.message);emit('build_retry',{taskId:task.taskId,attempt,message:lastError});if(attempt===3)throw error;}
      }
      benchmarkTree.capabilities[id]=capability;addLevel(benchmarkTree,built);
      benchmarkTree.nodes.push(levelNode('n_'+id,id,built));taskNodes.set(task.taskId,id);
      provenance[task.taskId]={executionMode:'local_reconstruction',sourceUrl:task.sourceUrl??null,sourceTask:task.taskId,levelRef:built.ref,review:built.verification.review};
    }
    const benchPackage=await materializeProject({tree:benchmarkTree,directory:path.join(job.out,'benchmark-environment'),vendorDir});
    const pkg=readEnvironmentPackage(benchPackage.directory), driver=await pkg.createDriver({}, {allowLocalEnvironment:job.allowLocalEnvironment});
    const nativeLoad=driver.loadBenchmark.bind(driver);
    const taskByOriginal=new Map(tasks.map(t=>[t.taskId,pkg.curriculum.find(c=>c.node===taskNodes.get(t.taskId))]));
    driver.loadBenchmark=task=>nativeLoad(taskByOriginal.get(task.taskId??task.id)??task);
    const exploration=path.join(job.out,'h0');
    checkpoint('h0');save(path.join(job.out,'benchmark-provenance.json'),provenance);
    try {
      await explore({handoff,backend,driver,directory:exploration,budget:1,maxFreeActions:8,
        taskBudgets:Object.fromEntries([...taskByOriginal].map(([id,t])=>[id,{actionBudget:t.budget,maxFreeActions:8}]))});
    } finally {await driver.shutdown();}
    checkpoint('induce');
    const input=await induce({code,directory:path.join(job.out,'stage2'),exploration,profile,callModel,emit,signal});
    const taskIds=new Set(tasks.map(t=>t.taskId));
    if(input.trainingTasks.length!==tasks.length || input.trainingTasks.some(t=>!taskIds.has(t.taskId)))throw Error('Stage 2 changed the training cohort');
    const assignments=input.assignments.filter(a=>a.requirements.length);
    if(!assignments.length)throw Error('H0 found no nonempty capability routes to evolve; the reviewed baseline results are saved');
    const routes=buildTree(input.taxonomy,assignments,assignments.map(a=>a.taskId));
    const tree=treeFromTraining(input,job.tree?.name||'scratch');
    for(const [id,capability] of Object.entries(tree.capabilities))emit('tree_patch',{op:'add_capability',capability:{...capability,id}});
    const tasksById=new Map(tasks.map(t=>[t.taskId,t]));
    checkpoint('create_environments');
    for(const route of routes) {
      const capId=route.requirements.at(-1), capability=tree.capabilities[capId];
      let accepted=null,feedback=null;
      const contract=screeningContract({onFreeze:value=>save(path.join(job.out,'environment-builds',route.id,'screening-contract.json'),value)});
      for(let attempt=1;attempt<=3;attempt++) {
        const directory=path.join(job.out,'environment-builds',route.id,'attempt-'+attempt);
        try {
          const built=await build({...common,capability,feedback,directory,contract,
            brief:{purpose:'capability practice environment',requirements:route.requirements.map(id=>tree.capabilities[id]),
              descendantTasks:route.tasks.map(id=>tasksById.get(id)),
              evidence:route.tasks.map(id=>({taskId:id,assignment:input.assignments.find(a=>a.taskId===id),
                feedback:input.initialFeedback[id].map(r=>({episodeId:r.episodeId,success:r.success,reason:r.reason,
                  events:r.events.map(e=>({step:e.step,publicText:e.publicText}))}))}))}});
          contract.check(built);
          const screenTree=globalThis.TrinityTree.emptyTree('screen-'+route.id);
          screenTree.capabilities[capId]=capability;addLevel(screenTree,built);screenTree.nodes.push(levelNode('n_screen',capId,built));
          const materialized=await materializeProject({tree:screenTree,directory:path.join(directory,'environment'),vendorDir});
          const screenPkg=readEnvironmentPackage(materialized.directory), screenDriver=await screenPkg.createDriver({}, {allowLocalEnvironment:job.allowLocalEnvironment});
          const store=new Store(path.join(directory,'screening'),{mode:'studio_world_screening',node:route.id});
          try {
            const task=screenPkg.curriculum[0],world=await screenDriver.loadBenchmark(task),plan=await freezeExplorationInstances({driver:screenDriver,world,trials:3,store,taskId:route.id});
            const rows=await runBatch({agent:new Agent(backend,store),driver:screenDriver,store,world,modules:[],budget:task.budget,maxFreeActions:8,
              instances:plan.instances,initialStateHashes:plan.initialStateHashes,instancePlan:plan.event,phase:'screening',node:route.id,taskId:route.id},3);
            const decision=screeningDecision(rows,contract.value.policy);
            save(path.join(directory,'screening.json'),{...decision,episodes:rows.map(r=>r.episodeId)});
            if(rows.some(r=>r.technicalFailure))throw Error('Technical screening failure; see the screening ledger');
            if(!decision.accepted){feedback={kind:'difficulty_adjustment',...decision};continue;}
            accepted=built;
          } finally {await screenDriver.shutdown();}
          if(accepted)break;
        } catch(error) {feedback={kind:'build_failure',message:String(error.message)};emit('build_retry',{node:route.id,attempt,message:feedback.message});if(attempt===3)throw error;}
      }
      if(!accepted)throw Error('No environment reached the screening band at '+route.id);
      addLevel(tree,accepted);
      const node=levelNode(routeNode(route.id),capId,accepted);tree.nodes.push(node);
      emit('tree_patch',{op:'add_level',ref:accepted.ref,level:tree.levels[accepted.ref]});emit('tree_patch',{op:'add_node',node});
      if(route.parent){const link={id:'l_'+sha(route.id).slice(0,20),from:routeNode(route.parent),to:node.id};tree.links.push(link);emit('tree_patch',{op:'add_link',link});}
      for(const taskId of route.endpointTasks) {
        const bench={id:'b_'+sha(taskId).slice(0,20),kind:'bench',bench:tasksById.get(taskId).name,taskId,pos:[0,0]};
        const link={id:'l_'+bench.id,from:node.id,to:bench.id};tree.nodes.push(bench);tree.links.push(link);
        emit('tree_patch',{op:'add_node',node:bench});emit('tree_patch',{op:'add_link',link});
      }
      save(path.join(job.out,'tree.partial.json'),tree);
    }
    globalThis.TrinityTree.arrangeTree(tree);
    globalThis.TrinityTree.assertTree(tree);
    save(path.join(job.out,'tree.json'),tree);
    emit('tree_patch',{op:'replace_tree',tree});
    checkpoint('tree_ready',{nodes:tree.nodes.length,levels:Object.keys(tree.levels).length});
    return tree;
  } catch(error) {checkpoint('failed',{error:String(error.message).replaceAll(apiKey||'\u0000','[redacted]')});throw error;}
}
