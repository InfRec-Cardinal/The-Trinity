import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {createArcBranch} from './runner/branch-modules.mjs';
import {preparePublicTemplate} from './runner/public-contract.mjs';
export async function runArc({root,out,env,opts,episodes,concurrency,validate}){
 const branch=createArcBranch(env.H0_CAPABILITY_NODE),{branchNotice,branchTool}=branch;
 const {createTrainDriverRegistry}=await import(pathToFileURL(path.join(env.H0_ENV_ROOT,'interface/registry.mjs')));
 const driver=await createTrainDriverRegistry({root:env.H0_ENV_ROOT,record:true}).getDriver('arc_agi_3');
 const ids=opts['--cases'].split(',');assert(ids.length&&new Set(ids).size===ids.length,'Unique case IDs required');
 const configs=ids.map(id=>{const index=driver.configurations.findIndex(c=>c.id===id);assert(index>=0,'Unknown ARC level '+id);return {config:driver.configurations[index],index};});
 const count=opts['--one-per-case']?Math.min(episodes,configs.length):episodes;
 const samples=Array.from({length:count},(_,i)=>{
  const {config:c,index}=configs[i%configs.length],round=Math.floor(i/configs.length)+1;
  const level=c.levelIndex??c.selector?.levelIndex;assert(Number.isSafeInteger(level)&&level>=0,'Independent native level required');
  const actionLimit=Number(opts['--action-budget']??2*c.baselineActions?.[level]);assert(Number.isSafeInteger(actionLimit)&&actionLimit>0,'Provide --action-budget');
  const requestLimit=Number(opts['--request-budget']??4*actionLimit-1);assert(Number.isSafeInteger(requestLimit)&&requestLimit>0);
  return {sample:`case-${index}-repeat-${round}`,round,configurationIndex:index,caseId:c.id,actionLimit,requestLimit};
 });
 if(opts['--resume-source']){
  const old=JSON.parse(fs.readFileSync(path.join(path.resolve(opts['--resume-source']),'run-manifest.json')));
  assert.equal(old.node??'d-a',branch.node,'Resume node mismatch');
  assert.equal(samples.length,1);assert.equal(samples[0].caseId,old.caseId,'Resume case mismatch');
  samples[0].round=old.round;
  if(!opts['--action-budget'])samples[0].actionLimit=old.actionLimit;
  if(!opts['--request-budget'])samples[0].requestLimit=old.requestLimit;
 }
 const template=JSON.parse(fs.readFileSync(path.join(root,'profiles/arc/request-template.json')));
 let replaced=0;
 for(const b of template.system)if(b.text?.includes('{{CURRENT_BRANCH_NOTICE}}')){
  b.text=b.text.replace('{{CURRENT_BRANCH_NOTICE}}',()=>branchNotice);replaced++;
 }
 assert.equal(replaced,1,'Current branch notice placeholder required');template.tools=template.tools.map(t=>t.name==='consult_branch_module'?structuredClone(branchTool):t);preparePublicTemplate(template,branch);
 if(!branch.automaticId)for(const block of template.system)if(block.text)block.text=block.text.replace('and locally computed module memory','without an automatic module');
 const templatePath=path.join(out,'request-template.json');fs.writeFileSync(templatePath,JSON.stringify(template,null,2)+'\n');
 const plan={samples,maxLogicalEpisodes:count,maxNativeActions:samples.reduce((n,s)=>n+s.actionLimit,0),maxRequests:samples.reduce((n,s)=>n+s.requestLimit,0),...branch.selection,executedModules:branch.selection.selectedModules,resetConsumesAction:true,officialScoring:'independent native-level RHAE, not whole-game leaderboard replication',validateOnly:validate};
 fs.writeFileSync(path.join(out,validate?'validation.json':'plan.json'),JSON.stringify(plan,null,2)+'\n');
 if(validate)return;
 let next=0;const results=[];
 const run=async sample=>{
  const mode=opts['--resume-mode']??'context';assert(['context','network'].includes(mode),'Resume mode must be context or network');
  const script=opts['--resume-source']&&mode==='network'?'run-public-timeout-resume.mjs':'run-public-contract.mjs';
  const runDir=path.join(out,sample.sample),childEnv={...env,ARC_PUBLIC_RUN_ROOT:runDir,ARC_PUBLIC_ROUND:String(sample.round),ARC_PUBLIC_SAMPLE_JSON:JSON.stringify(sample),ARC_NATIVE_ACTION_LIMIT:String(sample.actionLimit),ARC_REQUEST_TEMPLATE:templatePath};
  if(opts['--resume-source'])childEnv.ARC_PUBLIC_SOURCE=path.resolve(opts['--resume-source']);
  const code=await new Promise((resolve,reject)=>{const child=spawn(process.execPath,[path.join(root,'profiles/arc/runner',script),'--execute'],{env:childEnv,cwd:root,stdio:'inherit'});child.once('error',reject);child.once('exit',c=>resolve(c??1));});
  const p=path.join(runDir,'result.json');results.push(fs.existsSync(p)?{...JSON.parse(fs.readFileSync(p)),directory:runDir,exitCode:code}:{caseId:sample.caseId,outcome:'runner_error',directory:runDir,exitCode:code});
  fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({results},null,2)+'\n');if(code)process.exitCode=1;
 };
 await Promise.all(Array.from({length:Math.min(concurrency,count)},async()=>{while(next<count){const i=next++;await run(samples[i]);}}));
}
