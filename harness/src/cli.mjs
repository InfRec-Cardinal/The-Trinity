import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Store, ensure} from './core.mjs';
import {Agent, CommandAgent} from './agent.mjs';
import {Trinity} from './engine.mjs';

const [mode = 'run', configPath, outputPath] = process.argv.slice(2);
ensure(mode === 'run', 'Unknown mode: ' + mode);
ensure(configPath && outputPath, 'Provide a configuration file and output directory');
const file = path.resolve(configPath), config = JSON.parse(fs.readFileSync(file, 'utf8'));
const directory = path.resolve(outputPath);
ensure(config.agentCommand && config.driverModule, 'Execution requires agentCommand and driverModule');
ensure(config.mode !== 'scripted_demo', 'Production mode must not claim a scripted configuration');
const backend = new CommandAgent(config.agentCommand, config.agentOptions);
const module = await import(pathToFileURL(path.resolve(path.dirname(file), config.driverModule)).href);
const driver = await module.createDriver(config.driverOptions ?? {});
const store = new Store(directory, config), agent = new Agent(backend, store);
try {
  const result = await new Trinity({config, agent, driver, store}).run();
  console.log(JSON.stringify({mode: config.mode, directory, nodes: result.nodes, iterations: result.iterations, completedNodeIterations: result.summary.length, creatorModules: result.creatorBase.modules.length, creatorSkills: Object.values(result.creatorNodeSkills).reduce((sum, skills) => sum + skills.length, 0), benchmarkPerformanceClaim: false}, null, 2));
} catch (error) {
  store.record('run_failed', {message: String(error.message)});
  process.stderr.write(String(error.stack) + '\n');
  process.exitCode = 1;
}
