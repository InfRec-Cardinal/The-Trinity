import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import '../public/tree.js';
import {openLevel} from './level-engine.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

export async function materializeProject({tree, directory, vendorDir}) {
  globalThis.TrinityTree.assertTree(tree);
  if (fs.existsSync(directory)) throw Error('Project environment directory already exists');
  const info = globalThis.TrinityTree.analyzeTree(tree);
  const capabilities = {}, levels = {}, byPath = new Map(), curriculum = [];
  for (const node of tree.nodes.filter(n=>n.kind==='capability')) {
    const route = info.path(node.id);
    if (!/^[a-z][a-z0-9_-]{0,159}$/.test(route)) throw Error('Capability path is too long: ' + route);
    if (!node.level) throw Error('Create a level for capability node ' + node.id + ' before running');
    const level = tree.levels[node.level.ref];
    if (sha(level.source) !== node.level.ref) throw Error('Level source fingerprint mismatch on ' + node.id);
    const variants = node.variants ?? [node.level.variant];
    if (!variants.length) throw Error('No level variants selected on ' + node.id);
    const binding = JSON.stringify([node.level,variants]);
    if (byPath.has(route)) {
      if (byPath.get(route) !== binding) throw Error('Different levels cannot share capability path ' + route);
      continue;
    }
    byPath.set(route,binding);
    const cap = tree.capabilities[node.capability];
    capabilities[route] = {...cap,id:route,definition:cap.definition || cap.name};
    levels[node.level.ref] = {source:level.source};
    for (const variant of variants) {
      const engine=await openLevel({source:level.source,node:node.level.node,variant,vendorDir});
      let opening;
      try {opening=await engine.snapshot();} finally {await engine.close();}
      if(opening.inspect.ended || !opening.actions.length)throw Error('Invalid opening state on '+node.id);
      if(variant===node.level.variant && node.level.budget!==undefined && node.level.budget!==opening.inspect.budget)throw Error('Level budget differs from the project on '+node.id);
      curriculum.push({id:'level-' + sha(route).slice(0,24) + '-' + variant,node:route,variant,
        budget:opening.inspect.budget,moduleScope:info.scope(node.id),levelRef:node.level.ref,runtimeNode:node.level.node});
    }
  }
  if (!curriculum.length) throw Error('No project environments to run');
  const descriptor = {schema:'trinity-environment-package-v1',id:'studio-project',version:'1.0.0',
    instanceSemantics:'fixed-instance-repeats',integrity:'integrity.json',driverModule:'runtime/project-driver.mjs',curriculum:'curriculum.json',capabilities};
  const files = {'environment-package.json':JSON.stringify(descriptor,null,2)+'\n','curriculum.json':JSON.stringify(curriculum,null,2)+'\n',
    'levels.json':JSON.stringify(levels)+'\n',
    'runtime/project-driver.mjs':fs.readFileSync(path.join(HERE,'project-driver.mjs')),
    'runtime/level-engine.mjs':fs.readFileSync(path.join(HERE,'level-engine.mjs'))};
  for(const name of ['three.module.js','three.core.js']) files['vendor/'+name] = fs.readFileSync(path.join(vendorDir,name));
  fs.mkdirSync(directory,{recursive:true});
  for (const [name,body] of Object.entries(files)) {
    fs.mkdirSync(path.dirname(path.join(directory,name)),{recursive:true});
    fs.writeFileSync(path.join(directory,name),body);
  }
  fs.writeFileSync(path.join(directory,'integrity.json'),JSON.stringify({files:Object.fromEntries(Object.entries(files).map(([name,body])=>[name,sha(body)]))},null,2)+'\n');
  return {directory,curriculum,revision:sha(fs.readFileSync(path.join(directory,'integrity.json')))};
}
