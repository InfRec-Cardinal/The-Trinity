import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {verifyBuild} from './verify-build.mjs';
import {runArc} from './profiles/arc/dispatch.mjs';
import {createCapabilityScope} from './shared/capability-scope.mjs';
const root=path.dirname(fileURLToPath(import.meta.url)),args=process.argv.slice(2);
const profiles=JSON.parse(fs.readFileSync(path.join(root,'task-profiles.json')));
if(!args.length||args.includes('--help')){
 console.log('node run.mjs --task TASK --cases ID[,ID] --episodes N --out NEW_DIR [--concurrency N] [--validate-only]');
 console.log('Optional: --profile arc|embodied|capx|buildarena --node NODE --skills FILE --evolved-skills FILE --env-root DIR --unseen --one-per-case --action-budget N --request-budget N --source-video-registry FILE --resume-source DIR --resume-mode context|network');
 console.log('Task defaults select frozen skills and capability path. No dispatch without explicit cases/episodes/output. ARC defaults to twice the per-level human action baseline. Video source acquisition is opt-in. Credentials: UPSTREAM_API_KEY.');process.exit(0);
}
if(args.includes('--list-tasks')){console.log(JSON.stringify(profiles,null,2));process.exit(0);}
const opts={},bool=new Set(['--validate-only','--unseen','--one-per-case']);
const valued=new Set(['--task','--profile','--node','--skills','--evolved-skills','--env-root','--cases','--episodes','--out','--concurrency','--action-budget','--request-budget','--source-video-registry','--resume-source','--resume-mode']);
for(let i=0;i<args.length;i++){
 const k=args[i];assert(!Object.hasOwn(opts,k),'Duplicate '+k);
 if(bool.has(k)){opts[k]=true;continue;}assert(valued.has(k)&&args[i+1]&&!args[i+1].startsWith('--'),'Unknown/incomplete '+k);opts[k]=args[++i];
}
for(const k of ['--task','--cases','--episodes','--out'])assert(opts[k],'Required '+k);
const task=opts['--task'],defaults=profiles[task]??{},profile=opts['--profile']??defaults.profile;
assert(['arc','embodied','capx','buildarena'].includes(profile),'Select a supported profile');
if(defaults.profile&&['arc','capx','buildarena'].includes(defaults.profile))assert.equal(profile,defaults.profile,'Task requires its native adapter');
const node=opts['--node']??defaults.node??'d';
const scope=createCapabilityScope(node,{profile});
if(profile==='arc')assert(task==='arc_agi_3'&&!opts['--unseen']);
if(profile==='capx')assert(task==='capx_cupsearch_v2'&&!opts['--unseen']);
if(profile==='buildarena')assert(task==='buildarena_1_0');
const int=(v,label)=>{const n=Number(v);assert(Number.isSafeInteger(n)&&n>0,label+' must be a positive integer');return n;};
const episodes=int(opts['--episodes'],'episodes'),concurrency=Math.min(episodes,int(opts['--concurrency']??1,'concurrency'));
const out=path.resolve(opts['--out']);assert(!fs.existsSync(out),'Output exists; choose a new directory');
const relative=p=>path.resolve(root,p),skills=opts['--skills']?path.resolve(opts['--skills']):defaults.skills?relative(defaults.skills):null;
assert(skills&&fs.statSync(skills).isFile(),'Explicit or registered skills required');
const evolved=opts['--evolved-skills']?path.resolve(opts['--evolved-skills']):defaults.evolvedSkills?relative(defaults.evolvedSkills):null;
if(evolved)assert(fs.statSync(evolved).isFile());
const envRoot=path.resolve(opts['--env-root']??process.env.H0_ENV_ROOT??(defaults.envRoot?relative(defaults.envRoot):(()=>{throw Error('Set --env-root or H0_ENV_ROOT')})()));
assert(fs.existsSync(envRoot),'Missing environment '+envRoot);
const unseen=!!opts['--unseen']||defaults.split==='unseen',validate=!!opts['--validate-only'];
const env={...process.env};
const bundled={GLOVE_ROOT:'train/data/glove',SIGLIP_MODEL_PATH:'models/siglip-base-patch16-224',ALE_BENCH_ROOT:'ale-bench',ALE_BENCH_DATA:'ale-bench/data'};
for(const [key,value] of Object.entries(bundled)){const location=relative('../environments/'+value);if(!env[key]&&fs.existsSync(location))env[key]=location;}
if(profile==='buildarena'){
 const taskRoot=path.join(envRoot,'tasks','07-buildarena');
 env.BUILDARENA_ROOT=path.resolve(env.BUILDARENA_ROOT||path.join(taskRoot,'BuildArena-1.0'));
 env.BUILDARENA_TRANSPORT_ROOT=path.resolve(env.BUILDARENA_TRANSPORT_ROOT||path.join(taskRoot,'linux','transport'));
 for(const [dir,file] of [[env.BUILDARENA_ROOT,'run_h0.py'],[env.BUILDARENA_TRANSPORT_ROOT,'linux_sim_v3.py']])assert(fs.statSync(path.join(dir,file)).isFile(),'Missing BuildArena source: '+file);
 if(!validate){
  assert(env.BESIEGE_GAME_ROOT&&env.BESIEGE_MOD_ROOT,'Set BESIEGE_GAME_ROOT and BESIEGE_MOD_ROOT; start the external game before running the native adapter');
  env.BESIEGE_GAME_ROOT=path.resolve(env.BESIEGE_GAME_ROOT);env.BESIEGE_MOD_ROOT=path.resolve(env.BESIEGE_MOD_ROOT);
  env.BESIEGE_SAVED_MACHINES=path.resolve(env.BESIEGE_SAVED_MACHINES||path.join(env.BESIEGE_GAME_ROOT,'Besiege_Data','SavedMachines'));
  const check=spawnSync(env.BUILDARENA_PYTHON||'python3',[path.join(taskRoot,'linux','launch.py'),'--check'],{env,encoding:'utf8'});
  if(check.error)throw check.error;assert.equal(check.status,0,check.stderr);
 }
}


for(const k of Object.keys(env))if(k.startsWith('H0_')||k.startsWith('SOON_')||k.startsWith('ARC_')||['POKER_START_HAND','POKER_PRIOR','RELAY_CACHE_TTL'].includes(k))delete env[k];
Object.assign(env,{H0_ENV_ROOT:envRoot,H0_AUTHORED_SKILLS:skills,H0_THINKING_EFFORT:'low',H0_NATIVE_THINKING:'1',H0_MODULE_FORCE_STEPS:'0',H0_CAPABILITY_NODE:node,H0_TEXT_ACTION_ADAPTER:'1',H0_MAX_TOKENS:'16384',RELAY_CACHE_TTL:'5m',RELAY_PROVIDER_MAX_RETRIES:'0',H0_TRANSIENT_ATTEMPTS:'1',H0_QUOTA_ATTEMPTS:'1',RELAY_REFUSAL_RETRIES:'0',OMP_NUM_THREADS:'1',OPENBLAS_NUM_THREADS:'1',MKL_NUM_THREADS:'1'});
env.RELAY_BASE_URL??='https://api.anthropic.com';env.RELAY_MODEL??='claude-opus-5';assert.equal(env.RELAY_MODEL,'claude-opus-5','This release is qualified for claude-opus-5');
if(unseen)env.H0_UNSEEN_ENV_ROOT=envRoot;if(evolved)env.H0_EVOLVED_SKILLS=evolved;
if(opts['--action-budget'])env.H0_STEP_CEILING=String(int(opts['--action-budget'],'action-budget'));
if(opts['--request-budget'])assert(profile==='arc','request-budget is supported by ARC adapter');
if(profile==='capx')Object.assign(env,{CAPXO_PYTHON:env.CAPXO_PYTHON??'python3',MUJOCO_GL:'egl',H0_PIPELINE_ROOT:relative('profiles/capx'),H0_EPISODE_STALL_MS:'300000',H0_EPISODE_WALL_CLOCK_MS:'2100000'});
if(opts['--resume-mode']){assert(profile==='arc','resume-mode is supported only by ARC');assert(['context','network'].includes(opts['--resume-mode']),'Invalid resume-mode');assert(opts['--resume-source'],'resume-mode requires resume-source');}
if(opts['--resume-source']){
 assert(episodes===1&&concurrency===1,'Resume one logical episode at a time');assert(profile!=='buildarena','BuildArena resume is handled by native adapter');
 const source=path.resolve(opts['--resume-source']);assert(fs.statSync(source).isDirectory());
 if(profile!=='arc')env.SOON_RESUME_SOURCE=source;
}
if(opts['--source-video-registry']){assert(profile==='embodied'&&node==='e-f','Source video requires e-f adapter');env.H0_PUBLIC_VIDEO_REGISTRY=path.resolve(opts['--source-video-registry']);assert(fs.statSync(env.H0_PUBLIC_VIDEO_REGISTRY).isFile());}
if(validate)env.UPSTREAM_API_KEY='offline-validation-no-network';else assert(env.UPSTREAM_API_KEY?.trim(),'Set UPSTREAM_API_KEY');

Object.assign(env,{CODEX_CLI:relative('adapters/native-codex-audit.py'),H0_OPPONENT_CODEX_BIN:relative('adapters/native-codex-audit.py'),H0_NATIVE_DIAGNOSTICS_DIR:path.join(out,'native-codex-diagnostics'),ANTHROPIC_BASE_URL:env.RELAY_BASE_URL,ANTHROPIC_AUTH_TOKEN:env.UPSTREAM_API_KEY});
if(task==='ale_bench'){assert(env.ALE_BENCH_ROOT,'Set ALE_BENCH_ROOT');Object.assign(env,{ALE_NUM_WORKERS:'2',ALE_JUDGE_SLOTS:'1'});}
const build=verifyBuild(),hash=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.mkdirSync(out,{recursive:true});
const manifest={...build,releaseDirectory:root,task,profile,node,unseen,envRoot,maxEpisodes:episodes,concurrency,onePerCase:!!opts['--one-per-case'],validateOnly:validate,authoredSkills:{path:skills,sha256:hash(skills)},evolvedSkills:evolved?{path:evolved,sha256:hash(evolved)}:null,sourceVideo:env.H0_PUBLIC_VIDEO_REGISTRY?{path:env.H0_PUBLIC_VIDEO_REGISTRY,sha256:hash(env.H0_PUBLIC_VIDEO_REGISTRY),inputCondition:'supplementary original video'}:null,requestContract:{thinking:'adaptive',display:'omitted',effort:'low',cacheTTL:'5m',history:'complete signed history'},resumeSource:opts['--resume-source']??null};
fs.writeFileSync(path.join(out,'main-harness.json'),JSON.stringify(manifest,null,2)+'\n');
if(profile==='arc'){
 assert.equal(hash(skills),hash(relative(defaults.skills)),'ARC public template uses the frozen task skills; rebuild template before changing them');assert(!evolved,'ARC template does not append external skills');
 await runArc({root,out,env,opts,episodes,concurrency,validate});
}else if(profile==='buildarena'){
 assert.equal(opts['--cases'],'transport_soft','Native local BuildArena adapter supports transport_soft');assert.equal(concurrency,1,'One Besiege process owns the private display');
 if(validate){
  const r=spawnSync(process.execPath,[relative('profiles/buildarena/h0_call.mjs')],{env:{...env,BUILDARENA_RELEASE:root,BUILDARENA_SKILL:skills,BUILDARENA_VALIDATE_ONLY:'1'},input:JSON.stringify({tools:[],turns:[],roleSystem:'Offline contract validation'}),encoding:'utf8'});
  assert.equal(r.status,0,r.stderr);fs.writeFileSync(path.join(out,'validation.json'),r.stdout);
 }else for(let i=1;i<=episodes;i++){
  const r=spawnSync(env.BUILDARENA_PYTHON??'python3',[relative('profiles/buildarena/run_episode.py'),'--attempt',String(i),'--out',path.join(out,`repeat-${i}`),'--release',root,'--skills',skills],{cwd:root,env,stdio:'inherit'});if(r.error)throw r.error;if(r.status){process.exitCode=r.status;break;}
 }
}else{
 const registry=scope.has('frozenObligations')?relative('module-harness/registries/shared-d.json'):null;
 const command=[relative(`profiles/${profile}/runner/run-learned-arm.mjs`),task,'--free-tools',...(registry?['--modules',registry]:[]),...(unseen?['--unseen']:[]),'--cases',opts['--cases'],'--max-episodes',String(episodes),'--fanout',String(concurrency),'--out',out];
 if(opts['--one-per-case'])command.push('--one-per-case');if(validate)command.push('--validate-only');
 const r=spawnSync(process.execPath,command,{cwd:root,env,stdio:'inherit'});if(r.error)throw r.error;process.exitCode=r.status??1;
}
