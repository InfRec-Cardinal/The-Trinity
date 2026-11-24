

import {visualRouteEvidence} from '../src/visual-route-core.mjs';
import explorationRoute from '../src/route-planner.mjs';
import {outcomeMemory} from '../src/outcome-memory-core.mjs';
export default function(input) {
  if(input.mode==='scene_evidence')return visualRouteEvidence(input);
  if(input.mode==='outcome_memory')return outcomeMemory(input);
  if(input.mode!==undefined && input.mode!=='route')throw Error('Use route, outcome_memory or scene_evidence mode');
  return explorationRoute(input);
}
