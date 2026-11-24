import {equal} from '../../../module-harness/src/common.mjs';
import {visualRouteEvidence} from '../../../module-harness/src/visual-route-core.mjs';
import {outcomeMemory} from '../../../module-harness/src/outcome-memory-core.mjs';
import {arcPolicy} from './arc-policy.mjs';
export function policySource(){
  return `function(input){const equal=(${equal.toString()});const visualRouteEvidence=(${visualRouteEvidence.toString()});const outcomeMemory=(${outcomeMemory.toString()});return (${arcPolicy.toString()})(input,outcomeMemory,visualRouteEvidence);}`;
}
