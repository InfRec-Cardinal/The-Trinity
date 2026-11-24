import fs from 'node:fs';
import assert from 'node:assert/strict';
import {registry} from '../module-library/runtime.mjs';
import {releaseHost} from '../module-library/release.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(name,import.meta.url),'utf8'));
const deepFreeze=value=>{if(value&&typeof value==='object'){for(const child of Object.values(value))deepFreeze(child);Object.freeze(value);}return value;};
export const manifest=deepFreeze(read('./harness.json'));
export const catalog=deepFreeze(read('./catalog.json'));
const modules=read('./installed-modules.json');
const active=registry(modules,{nativeHost:releaseHost(new URL('.',import.meta.url))});
assert.equal(active.list().length,manifest.activeModuleCount);
assert.deepEqual(active.list().map(m=>m.moduleId),catalog.nodes.map(r=>r.moduleId));
export function modulesForPath(nodes){
 const ids=new Set(active.modulesForPath(nodes).map(m=>m.moduleId));
 return catalog.nodes.filter(r=>ids.has(r.moduleId));
}
export async function invoke(moduleId,input){return active.invoke(moduleId,input);}
