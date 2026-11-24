

import {planAcquisition} from '../src/acquisition-core.mjs';
export default function gapAcquisition(input){
  const result=planAcquisition(input);
  return {...result,stalledRequirements:result.unsupported.map(r=>r.requirementId),
    intent:'Request missing evidence supplied by the comprehension layer. Suppress identical requests that already failed or added no information; report unresolved gaps rather than infer a hidden transfer.'};
}
