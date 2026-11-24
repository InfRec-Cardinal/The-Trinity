import fs from 'node:fs';
import {PolicySession} from './policy-runtime/program.mjs';
import {createCapabilityScope} from '../shared/capability-scope.mjs';
export {evidenceTool,splitAction} from './src/evidence-bridge.mjs';
export function createIter4DSession(node=process.env.H0_CAPABILITY_NODE??'d'){
 const scope=createCapabilityScope(node);
 return new PolicySession(scope.bindPolicy(JSON.parse(fs.readFileSync(new URL('./registries/shared-d.json',import.meta.url),'utf8'))));
}
