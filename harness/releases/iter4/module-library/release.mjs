import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {CLASSES,catalog,instantiate,validate,registry,installModules,immutableSnapshot} from './runtime.mjs';
import {createNativeHost,verifyNativeHost} from './native.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const defaultRoot=fs.existsSync(path.join(root,'source'))?path.join(root,'source'):path.resolve(root,'../module-harness');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
export const recipes=immutableSnapshot(read('native-recipes.json'));
export const sourceLock=immutableSnapshot(read('source-lock.json'));
export function releaseHost(sourceRoot=defaultRoot){
 return createNativeHost({root:sourceRoot,...sourceLock,capabilities:['python-glove']});
}
export function instantiateRelease(moduleId,sourceRoot=defaultRoot){
 sourceRoot=sourceRoot instanceof URL?fileURLToPath(sourceRoot):sourceRoot;
 const recipe=recipes.find(r=>r.moduleId===moduleId);assert(recipe,'Unknown release module');
 const seed=instantiate(recipe.templateId,{moduleId,targetCapabilityNodeId:recipe.node});
 assert.equal(seed.protocolClass,recipe.protocolClass);
 return validate({...seed,version:recipe.version,prompt:recipe.prompt,interface:structuredClone(recipe.interface),function:{...recipe.function,source:fs.readFileSync(path.join(sourceRoot,recipe.function.entry),'utf8')},hostCapabilities:[...recipe.hostCapabilities]});
}
export function installRelease(sourceRoot=defaultRoot){
 const templates=catalog(),metadata=read('library.json');
 assert.equal(templates.length,42);assert.equal(recipes.length,29);
 assert.equal(metadata.templateCount,templates.length);
 assert.equal(metadata.nativeModuleCount,recipes.length);
 assert(templates.every(t=>CLASSES.includes(t.protocolClass)),'Unknown template protocol');
 assert.deepEqual(metadata.protocolCounts,Object.fromEntries(CLASSES.map(c=>[c,templates.filter(t=>t.protocolClass===c).length])));
 const nativeHost=releaseHost(sourceRoot),modules=recipes.map(r=>instantiateRelease(r.moduleId,sourceRoot));
 const installed=installModules(modules,{nativeHost});
 return {modules:installed.modules,audit:installed.audit,registry:registry(installed.modules,{nativeHost}),nativeHost};
}
export function verifyRelease(sourceRoot=defaultRoot){
 const installed=installRelease(sourceRoot);
 return {templates:catalog().length,activeModules:installed.modules.length,...verifyNativeHost(installed.nativeHost)};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 assert.deepEqual(process.argv.slice(2),['--verify']);console.log(JSON.stringify(verifyRelease()));
}
