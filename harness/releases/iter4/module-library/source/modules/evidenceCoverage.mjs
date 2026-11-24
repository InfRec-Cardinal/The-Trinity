

import {auditCoverage,planAcquisition} from '../src/acquisition-core.mjs';
export default function evidenceCoverage(input){
  const coverage=auditCoverage(input);
  return {...coverage,status:coverage.complete?'coverage_verified':'evidence_gaps',
    acquisition:input.offers&&input.budget!==undefined?planAcquisition(input):null,
    intent:'Audit received temporal coverage, frame density, target detail, legibility and sound; never confuse buying a segment with having sufficient evidence.'};
}
