import {scalarThreshold} from '../src/scalar-threshold.mjs';

import {facts,equal} from '../src/common.mjs';
function evidenceLedger({observations,entities,requirements=[],rules,epoch,requiredAttributes=['front','back']}) {
  const ids=entities??[...new Set([...observations.map(o=>o.entity),...requirements.map(r=>r.entity)])];
  const ledger={},conflicts=[],missing=[];
  const rows=ids.map(entity=>{
    const f=facts(observations,entity,epoch);
    for (const [attribute,value] of Object.entries(f.values)) ledger[JSON.stringify([entity,attribute])]={value,sources:f.sources[attribute],epoch};
    conflicts.push(...f.conflicts.map(attribute=>({entity,attribute})));
    const needed=[...new Set([...requirements.filter(r=>r.entity===entity).map(r=>r.attribute),...(rules?[...requiredAttributes,...rules.flatMap(r=>Object.keys(r.when))]:[])])];
    const absent=needed.filter(k=>!(k in f.values)); missing.push(...absent.map(attribute=>({entity,attribute})));
    const hits=rules?.filter(r=>Object.entries(r.when).every(([k,v])=>k in f.values && equal(f.values[k],v)));
    return {entity,...f,missing:absent,diagnosis:!rules || f.conflicts.length || absent.length?null:
      hits.length===0?'none':hits.length===1?hits[0].label:null,matchedRuleCount:hits?.length??0,ambiguousRule:(hits?.length??0)>1};
  });
  return {status:rules?(rows.every(r=>r.diagnosis!==null)?'classified':'needs_evidence'):
    missing.length||conflicts.length?'needs_evidence':'ledger_ready',facts:ledger,conflicts,missing,rows,
    reports:rows.filter(r=>r.diagnosis!==null && r.matchedRuleCount===1).map(r=>({entity:r.entity,label:r.diagnosis})),
    note:'Classification is optional and uses only supplied public rules; unsourced values never become facts.'};
}

export default function evidenceDiagnosis(input){return input.mode==='scalar_threshold'?scalarThreshold(input):evidenceLedger(input);}
