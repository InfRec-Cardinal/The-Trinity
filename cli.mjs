import {Router, loadTrainingMemory} from './harness/src/router.mjs';
import {Store} from './harness/src/core.mjs';
import {Agent} from './harness/src/agent.mjs';
import fs from 'node:fs';
import {collectAccounting} from './src/accounting.mjs';
import path from 'node:path';
import {ROOT, runCommand, runStage2, loadAdapter, explore, prepareTraining, train} from './src/integration.mjs';

const [command = 'help', ...args] = process.argv.slice(2);
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const option = name => {
  const index = args.indexOf('--' + name);
  if (index < 0 || !args[index + 1] || args[index + 1].startsWith('--')) throw Error('Required option: --' + name);
  return args[index + 1];
};

async function main() {
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
    const store = new Store(path.resolve(option('out')), {mode: 'routing', protocolId: plan.protocolId});
    const memory = args.includes('--training-memory') ? loadTrainingMemory(option('training-memory')) : undefined;
    const trainingRun = args.includes('--training-run') ? path.resolve(option('training-run')) : path.dirname(path.resolve(option('plan')));
    const router = new Router({agent: new Agent(backend, store), driver, store, plan, memory, trainingRun});
    const results = await router.runAll();
    if (args.includes('--evaluation-labels')) store.write('routing-retrospective-evaluation.json', {
      predictions: router.readEvaluationLabels(option('evaluation-labels'))});
    console.log(JSON.stringify({tasks: results.length, predictionFile: router.predictionFile,
      technicalFailures: results.filter(row => row.technicalFailure).length}, null, 2));
    return;
  }
  if (command === 'explore') {
    const {backend, driver, settings} = await loadAdapter(option('adapter'));
    const result = await explore({handoff: read(option('handoff')), backend, driver,
      directory: path.resolve(option('out')), budget: settings.actionBudget,
      cohort: args.includes('--cohort') ? option('cohort') : 'train',
      trainingRun: args.includes('--training-run') ? path.resolve(option('training-run')) : null});
    console.log(JSON.stringify(result, null, 2));
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
    const result = await train({config, backend, driver, directory: path.resolve(option('out'))});
    console.log(JSON.stringify({nodes: result.nodes, iterations: result.iterations, completedNodeIterations: result.summary.length}, null, 2));
    return;
  }
  if (command !== 'help' && command !== '--help') throw Error('Unknown command: ' + command);

}

main().catch(error => {console.error(String(error.message)); process.exitCode = 1;});
