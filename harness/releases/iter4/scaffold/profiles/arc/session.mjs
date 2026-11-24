import fs from 'node:fs';
import {PolicySession} from './policy-runtime/program.mjs';
import {verifyModuleBuild} from './verify-module-build.mjs';
import {createCapabilityScope} from '../../shared/capability-scope.mjs';
export function createArcSession(node=process.env.H0_CAPABILITY_NODE??'d-a'){
 const scope=createCapabilityScope(node,{profile:'arc'});
 if(!scope.has('explorationRoute'))return null;
 verifyModuleBuild();
 return new PolicySession(scope.bindPolicy(JSON.parse(fs.readFileSync(new URL('../../module-harness/registries/arc_agi_3.json',import.meta.url),'utf8')),{ownerId:'explorationRoute'}));
}
