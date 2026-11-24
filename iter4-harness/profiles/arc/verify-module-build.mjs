import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {policySource} from './src/policy-source.mjs';
export function verifyModuleBuild(){
 const root=new URL('./',import.meta.url),read=p=>JSON.parse(fs.readFileSync(new URL(p,root),'utf8'));
 const meta=read('module-build.json'),registry=read('../../module-harness/registries/arc_agi_3.json');
 const m=registry.active[meta.policyId];
 assert.equal(m.source,policySource(),'Stale generated policy: run build.mjs and revalidate');assert.equal(m.version,7);
 for(const [path,hash] of Object.entries(meta.files))assert.equal(createHash('sha256').update(fs.readFileSync(new URL(path,root))).digest('hex'),hash,path);
 assert.equal(createHash('sha256').update(m.source).digest('hex'),meta.policySourceSha256);
 const catalog=read('../../module-harness/catalog.json');assert.equal(catalog.nodes.length,29);
 assert.equal(catalog.nodes.find(x=>x.moduleId===meta.moduleId).replacement.sourceSha256,meta.policySourceSha256);
 return meta;
}
