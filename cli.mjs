import {Router, loadTrainingMemory} from './harness/src/router.mjs';
import {Store} from './harness/src/core.mjs';
import {Agent, CommandAgent} from './harness/src/agent.mjs';
import fs from 'node:fs';
import {collectAccounting} from './src/accounting.mjs';
import path from 'node:path';
import {ROOT, runCommand, runStage2, loadAdapter, explore, prepareTraining, train, ProviderBackend} from './src/integration.mjs';

const [command = 'help', ...args] = process.argv.slice(2);
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const option = name => {
  const index = args.indexOf('--' + name);
  if (index < 0 || !args[index + 1] || args[index + 1].startsWith('--')) throw Error('Required option: --' + name);
  return args[index + 1];
};

async function main() {
  if(command==='build-harness'){
    if(args.length!==4||new Set(args.filter((_,i)=>i%2===0)).size!==2||!args.includes('--release')||!args.includes('--out'))throw Error('Usage: node cli.mjs build-harness --release iter4 --out NEW_DIR');
    if(option('release')!=='iter4')throw Error('Unknown module release');
    const {build}=await import('./harness/releases/iter4/build.mjs');
    console.log(JSON.stringify(build(option('out')),null,2));return;
  }
  if(command==='learn-env'){
    const allowed=new Set(['--env-package','--out','--agent-config','--epochs','--tasks','--nodes','--resume-from','--module-release','--validate-only','--allow-local-env']);
    const seen=new Set();
    for(let i=0;i<args.length;i++){
      const key=args[i];if(!allowed.has(key)||seen.has(key))throw Error('Unknown or duplicate option: '+key);seen.add(key);
      if(key!=='--validate-only'&&key!=='--allow-local-env'){if(!args[i+1]||args[i+1].startsWith('--'))throw Error('Missing value: '+key);i++;}
    }
    const {prepareEnvironmentLearning,learnEnvironments,validateEnvironmentLearning}=await import('./src/environment-learning.mjs');
    const settings=seen.has('--agent-config')?read(option('agent-config')):{};
    const keys=['agentCommand','agentOptions','driverOptions','validationPolicies','epochs','maxFreeActions'];
    if(!settings||typeof settings!=='object'||Array.isArray(settings)||Object.keys(settings).some(k=>!keys.includes(k)))throw Error('Invalid learning agent configuration');
    const allowLocalEnvironment=seen.has('--allow-local-env');
    const {assertEnvironmentReuse}=await import('./src/environment-package.mjs');
    assertEnvironmentReuse(settings.driverOptions,allowLocalEnvironment);
    const prepared=prepareEnvironmentLearning({environmentPackage:option('env-package'),
      epochs:seen.has('--epochs')?Number(option('epochs')):settings.epochs,
      tasks:seen.has('--tasks')?option('tasks').split(','):undefined,
      nodes:seen.has('--nodes')?option('nodes').split(','):undefined,
      moduleRelease:seen.has('--module-release')?option('module-release'):undefined,
      resumeFrom:seen.has('--resume-from')?option('resume-from'):null,validationPolicies:settings.validationPolicies,maxFreeActions:settings.maxFreeActions});
    if(seen.has('--validate-only')){console.log(JSON.stringify(await validateEnvironmentLearning(prepared,settings.driverOptions,{allowLocalEnvironment}),null,2));return;}
    const directory=path.resolve(option('out'));
    if(!settings.agentCommand){const {resolveProfile,requireProviderKey}=await import('./pipeline/src/model.mjs');requireProviderKey(resolveProfile());}
    const backend=settings.agentCommand?new CommandAgent(settings.agentCommand,settings.agentOptions):new ProviderBackend();
    const result=await learnEnvironments({prepared,backend,directory,driverOptions:settings.driverOptions,allowLocalEnvironment});
    console.log(JSON.stringify({mode:result.mode,completed:result.completed,epochs:result.epochs,curriculumTasks:result.curriculumTasks,directory},null,2));return;
  }
  if (command === 'metrics') {
    if (!args.length) throw Error('Provide one or more run directories');
    console.log(JSON.stringify(collectAccounting(args), null, 2));
    return;
  }
  if (command === 'stage1') return runCommand(process.execPath, [path.join(ROOT, 'pipeline/cli.mjs'), ...args], {cwd: process.cwd()});
  if (command === 'stage2') return runStage2(args);
  if (command === 'route') {
    const plan = read(option('plan'));
    const {backend, driver} = await loadAdapter(option('adapter'));
    try {
      const store = new Store(path.resolve(option('out')), {mode: 'routing', protocolId: plan.protocolId});
      const memory = args.includes('--training-memory') ? loadTrainingMemory(option('training-memory')) : undefined;
      const trainingRun = args.includes('--training-run') ? path.resolve(option('training-run')) : path.dirname(path.resolve(option('plan')));
      const nativeHost=args.includes('--module-release')?(await import('./src/module-release.mjs')).loadModuleRelease(option('module-release')).nativeHost:undefined;
      const router = new Router({agent: new Agent(backend, store), driver, store, plan, memory, trainingRun,nativeHost});
      const results = await router.runAll();
      if (args.includes('--evaluation-labels')) store.write('routing-retrospective-evaluation.json', {
        predictions: router.readEvaluationLabels(option('evaluation-labels'))});
      console.log(JSON.stringify({tasks: results.length, predictionFile: router.predictionFile,
        technicalFailures: results.filter(row => row.technicalFailure).length}, null, 2));
    } finally {await driver.shutdown?.();}
    return;
  }
  if (command === 'explore') {
    const {backend, driver, settings} = await loadAdapter(option('adapter'));
    try {
      const result = await explore({handoff: read(option('handoff')), backend, driver,
        directory: path.resolve(option('out')), budget: settings.actionBudget, maxFreeActions: settings.maxFreeActions, taskBudgets: settings.taskBudgets,
        cohort: args.includes('--cohort') ? option('cohort') : 'train',
        trainingRun: args.includes('--training-run') ? path.resolve(option('training-run')) : null});
      console.log(JSON.stringify(result, null, 2));
    } finally {await driver.shutdown?.();}
    return;
  }
  if (command === 'prepare') {
    const config = await prepareTraining(option('stage2'), read(option('adapter'))), out = path.resolve(option('out'));
    fs.mkdirSync(path.dirname(out), {recursive: true});
    fs.writeFileSync(out, JSON.stringify(config, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({trainingTasks: config.trainingTasks.length, baselineTasks: config.baselineTasks.length, capabilities: config.taxonomy.length}, null, 2));
    return;
  }
  if (command === 'train') {
    const adapterFile = option('adapter');
    const config = await prepareTraining(option('stage2'), read(adapterFile));
    const {backend, driver} = await loadAdapter(adapterFile);
    try {
      const result = await train({config, backend, driver, directory: path.resolve(option('out'))});
      console.log(JSON.stringify({nodes: result.nodes, iterations: result.iterations, completedNodeIterations: result.summary.length}, null, 2));
    } finally {await driver.shutdown?.();}
    return;
  }
  if (command !== 'help' && command !== '--help') throw Error('Unknown command: ' + command);
  console.log('node cli.mjs learn-env --env-package DIR --out NEW_DIR [--allow-local-env] [--agent-config FILE] [--epochs N] [--tasks ID,ID | --nodes NODE,NODE] [--resume-from RUN] [--module-release iter4] [--validate-only]');
  console.log('node cli.mjs build-harness --release iter4 --out NEW_DIR');
  console.log('Commands: stage1, stage2, explore, prepare, train, learn-env, build-harness, route, metrics');

}

main().catch(error => {console.error(String(error.message)); process.exitCode = 1;});
