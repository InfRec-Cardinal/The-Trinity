import {hostVerificationCall} from './host-verification.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import {randomUUID, createHash} from 'node:crypto';
import {clone, digest, ensure, identifier} from './core.mjs';
import {auditCreator} from './creator.mjs';
import {inspectCreatorBuild} from './creator-audits.mjs';
import {createWorkspaceSandbox, sandboxFileTool} from './creator-sandbox.mjs';

export async function creatorSourceDigest(workspace) {
  const files = [];
  let bytes = 0;
  async function walk(directory) {
    for (const name of (await fs.readdir(directory)).sort()) {
      const file = path.join(directory, name), stat = await fs.lstat(file);
      ensure(!stat.isSymbolicLink(), 'Creator source may not contain symlinks');
      if (stat.isDirectory()) await walk(file);
      else {
        ensure(stat.isFile() && stat.nlink === 1, 'Creator source must contain ordinary private files');
        bytes += stat.size;
        ensure(bytes <= 67108864 && files.length < 20000, 'Creator workspace limit exceeded');
        files.push({path: path.relative(workspace, file), hash: createHash('sha256').update(await fs.readFile(file)).digest('hex')});
      }
    }
  }
  await walk(workspace);
  return digest(files);
}

export async function runCreatorCoding({agent, driver, store, node, iteration, attempt, design, creator, feedback,
  previousWorld, previousBuildDigest, maxBuildAttempts, actionBudget, screening = null, settings = {}}) {
  ensure(identifier(node.id), 'Invalid Creator node');
  const workspace = path.join(store.directory, 'creator-workspaces', node.id, String(iteration));
  const evidenceDirectory = path.join(store.directory, 'creator-evidence', node.id, String(iteration));
  const noteFile = path.join(evidenceDirectory, 'construction-note.json');
  await fs.mkdir(workspace, {recursive: true});
  await fs.mkdir(evidenceDirectory, {recursive: true});
  const maxTurns = settings.maxTurns ?? 64;
  ensure(Number.isInteger(maxTurns) && maxTurns >= 2 && maxTurns <= 512, 'Invalid Creator turn budget');
  const contract = {design: clone(design), buildContract: clone(driver.buildContract), actionBudget, maxBuildAttempts, screening: clone(screening)};
  const contractDigest = digest(contract);
  let constructionNote = '';
  try {constructionNote = JSON.parse(await fs.readFile(noteFile, 'utf8')).text;} catch (error) {if (error.code !== 'ENOENT') throw error;}
  if (attempt === 0 && driver.initializeCreatorWorkspace) await hostVerificationCall('workspace_initialization', () => driver.initializeCreatorWorkspace({workspace, node: clone(node), iteration, design: clone(design)}));
  const sandbox = await createWorkspaceSandbox({cwd: workspace, writableRoot: workspace, readOnlyRoots: settings.readOnlyRoots ?? []});
  const initialProposal = await agent.ask('creator_build', {node, iteration, attempt, design: clone(design), creator: clone(creator), feedback, screening: clone(screening), buildContract: driver.buildContract}, driver.buildContract);
  const history = [];
  const registry = clone(creator);
  const tools = [
    {name: 'Read', input: {path: 'Relative file path'}},
    {name: 'Write', input: {path: 'Relative file path', content: 'Complete UTF-8 contents'}},
    {name: 'Edit', input: {path: 'Relative file path', oldText: 'One exact match', newText: 'Replacement'}},
    {name: 'Glob', input: {pattern: 'Glob pattern', path: 'Optional search directory'}},
    {name: 'Grep', input: {pattern: 'Regular expression', path: 'Optional search directory'}},
    {name: 'Bash', input: {command: 'Command in the isolated workspace', timeout: 'Optional milliseconds, maximum 600000'}},
    {name: 'creator_modules_run', input: {moduleId: 'Exactly one installed module ID; host supplies all measurements and budgets'}},
    {name: 'Preflight', input: {}}
  ];
  const saveEvidence = async (kind, value) => {
    const id = randomUUID();
    await fs.writeFile(path.join(evidenceDirectory, id + '.json'), JSON.stringify({kind, node: node.id, iteration, attempt, contractDigest, ...value}, null, 2) + '\n', {flag: 'wx'});
    store.record('creator_coding_evidence', {id, kind, node: node.id, iteration, attempt, evidenceDigest: digest(value)});
    return id;
  };
  const inspect = async () => {
    const proposal = JSON.parse(await sandboxFileTool(sandbox, 'Read', {path: 'proposal.json'}));
    const world = await hostVerificationCall('materialization', () => driver.materialize(clone(design), clone(proposal), {node: node.id, iteration, attempt, directory: store.directory, workspace}));
    const sourceDigest = await creatorSourceDigest(workspace);
    const buildDigest = digest(await hostVerificationCall('build_fingerprint', () => driver.fingerprint(clone(world))));
    const inspection = await inspectCreatorBuild({driver, world, design, buildDigest, context: {attempt, maxBuildAttempts, actionBudget, feedback, previousWorld, previousBuildDigest}});
    ensure(await creatorSourceDigest(workspace) === sourceDigest, 'Source changed during Creator audit');
    ensure(digest(await hostVerificationCall('build_fingerprint', () => driver.fingerprint(clone(world)))) === buildDigest, 'World changed during Creator audit');
    return {world, buildDigest, sourceDigest, inspection, workspace};
  };
  const publicResult = build => ({buildDigest: build.buildDigest, sourceDigest: build.sourceDigest,
    checks: build.inspection.checks, submissionsUsed: attempt, submissionLimit: maxBuildAttempts});
  for (let turn = 0; turn < maxTurns; turn++) {
    const response = await agent.ask('creator_code', {node, iteration, attempt, design: clone(design), buildContract: clone(driver.buildContract), initialProposal,
      buildInstructions: driver.creatorInstructions ?? null, screening: clone(screening),
      creator: registry, feedback, constructionNote, actionBudget, submissionsUsed: attempt, submissionLimit: maxBuildAttempts,
      remainingTurns: maxTurns - turn, tools, history: clone(history),
      instructions: 'Implement the world in the allocated workspace. Write proposal.json matching buildContract; the host reads it from disk and passes workspace to the adapter. Use source files when required by the adapter. Run checks and repair files. Host evidence is outside this workspace. Submit one node-local construction note. Never modify the frozen design or verifier; return contract_error to its owner.'},
    {kind: 'tool | submit | contract_error', tool: 'One registered tool for kind=tool', input: 'Arguments for that tool', constructionNote: 'Required on submit', owner: 'evolver_design | verifier for contract_error', message: 'Required for contract_error'});
    if (response.kind === 'contract_error') {
      ensure(['evolver_design', 'verifier'].includes(response.owner) && typeof response.message === 'string', 'Invalid contract error owner');
      store.record('creator_contract_error', {node: node.id, iteration, attempt, owner: response.owner, message: response.message, contractDigest});
      throw Error('Creator returned a frozen contract error to ' + response.owner + ': ' + response.message);
    }
    if (response.kind === 'submit') {
      ensure(typeof response.constructionNote === 'string' && response.constructionNote.trim() && response.constructionNote.length <= 12000, 'One bounded construction note is required');
      let build;
      try {build = await inspect();}
      catch (error) {
        const result = {error: String(error.message)};
        result.receiptId = await saveEvidence('submission_rejected', result);
        history.push({tool: 'Submit', input: {}, result});
        continue;
      }
      const audits = auditCreator(registry, build.inspection, build.buildDigest);
      const accepted = build.inspection.checks.every(check => check.passed) && audits.every(audit => audit.verdict === 'pass');
      await saveEvidence('final_preflight', {...publicResult(build), audits, accepted});
      await fs.writeFile(noteFile, JSON.stringify({node: node.id, iteration, actionBudget, contractDigest, text: response.constructionNote}, null, 2) + '\n');
      return {...build, audits, accepted};
    }
    ensure(response.kind === 'tool' && tools.some(tool => tool.name === response.tool), 'Unknown Creator tool or response kind');
    const input = clone(response.input ?? {});
    let result;
    try {
      if (response.tool === 'creator_modules_run') {
        ensure(Object.keys(input).length === 1 && typeof input.moduleId === 'string', 'Only moduleId is model-supplied');
        const module = registry.modules.find(row => row.id === input.moduleId);
        ensure(module, 'Unknown Creator module');
        const build = await inspect();
        const audit = auditCreator({modules: [module]}, build.inspection, build.buildDigest)[0];
        result = {...publicResult(build), audit};
        result.receiptId = await saveEvidence('module_call', {...result, inspection: build.inspection});
      } else if (response.tool === 'Preflight') {
        ensure(Object.keys(input).length === 0, 'Preflight takes no model-supplied evidence');
        const build = await inspect();
        result = {...publicResult(build), audits: auditCreator(registry, build.inspection, build.buildDigest)};
        result.receiptId = await saveEvidence('preflight_call', {...result, inspection: build.inspection});
      } else if (response.tool === 'Bash') {
        ensure(typeof input.command === 'string' && input.command.length <= 24000, 'Bounded shell command required');
        result = await sandbox.run(['/bin/bash', '-c', input.command], '', input.timeout ?? 60000);
      } else result = {text: await sandboxFileTool(sandbox, response.tool, input)};
      await creatorSourceDigest(workspace);
    } catch (error) {result = {error: String(error.message)};}
    const event = store.record('creator_tool_result', {node: node.id, iteration, attempt, turn, tool: response.tool,
      inputDigest: digest(input), resultDigest: store.put(result)});
    history.push({tool: response.tool, input, result, event});
    ensure(digest(contract) === contractDigest, 'Frozen Creator contract changed');
  }
  throw Error('Creator coding turn budget exhausted');
}
