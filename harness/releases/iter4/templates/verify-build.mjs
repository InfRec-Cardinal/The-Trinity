import {equal} from './module-harness/src/common.mjs';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {catalog,manifest} from './harness.mjs';
import {installRelease} from './module-library/release.mjs';
import {catalog as templateCatalog} from './module-library/runtime.mjs';
import {reviewCommitment} from './module-harness/src/commitment-ledger.mjs';
import {verifyModuleBuild} from './profiles/arc/verify-module-build.mjs';
const read=name=>JSON.parse(fs.readFileSync(new URL(name,import.meta.url)));
export function verifyBuild(){
 const installed=installRelease(new URL('./module-harness/',import.meta.url));
 assert.equal(read('./harness.json').harnessId,manifest.harnessId,'Root manifest mismatch');
 assert.equal(read('./module-library/library.json').templateCount,templateCatalog().length,'Template catalog metadata mismatch');
 assert.deepEqual(read('./module-harness/installed-modules.json'),installed.modules,'Installed module mismatch');
 verifyModuleBuild();
 const policy=read('./module-harness/registries/shared-d.json').active.frozenObligations;
 assert.equal(policy.source,`function(input){const equal=(${equal.toString()});return (${reviewCommitment.toString()})(input);}`,'Stale d embedded policy');assert.equal(policy.version,7);
 assert.equal(catalog.nodes.length,29);assert.equal(manifest.activeModuleCount,29);assert.equal(catalog.harnessId,manifest.harnessId);
 assert.equal(new Set(catalog.nodes.map(m=>m.moduleId)).size,29);
 assert(!fs.existsSync(new URL('./module-harness/frozen/',import.meta.url)));
 const lock=read('./freeze.json');
 for(const [file,digest] of Object.entries(lock.files))assert.equal(createHash('sha256').update(fs.readFileSync(new URL(file,import.meta.url))).digest('hex'),digest,'Release file changed: '+file);
 for(const [file,target] of Object.entries(lock.symlinks))assert.equal(fs.readlinkSync(new URL(file,import.meta.url)),target,'Release link changed: '+file);
 return {harnessId:manifest.harnessId,releaseId:read('./build.json').releaseId,activeModules:29,dVersion:7,daVersion:7};
}
if(process.argv[1]&&fs.realpathSync(process.argv[1])===fs.realpathSync(new URL(import.meta.url)))console.log(JSON.stringify(verifyBuild()));
