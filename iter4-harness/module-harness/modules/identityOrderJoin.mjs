

import {equal} from '../src/common.mjs';
export default function identityOrderJoin({observations,attributes,orders,slotTransform,capacity=2}) {
  if (!Number.isInteger(capacity)||capacity<1) throw Error('Positive capacity required');
  const entries=new Map(),conflicts=[];
  for (const row of observations) {
    if (!row.source || row.visible!==true) continue;
    const old=entries.get(row.id);
    if (old && !equal(old.attributes,row.attributes)) {conflicts.push(row.id);continue;}
    entries.set(row.id,row);
  }
  if (conflicts.length) return {status:'conflicting_memory',ids:conflicts};
  const rows=orders.map((order,index)=>{
    const resolved=Object.create(null),proof=[],missing=[];
    for (const [attribute,q] of Object.entries(order)) {
      if (q===null || typeof q!=='object') {resolved[attribute]=q;continue;}
      const ref=entries.get(q.ref),value=ref && Object.hasOwn(ref.attributes,attribute)?ref.attributes[attribute]:undefined;
      if (value===undefined) {missing.push({ref:q.ref,attribute});continue;}
      if (q.op==='same') resolved[attribute]=value;
      else if (q.op==='opposite' && [1,2].includes(value)) resolved[attribute]=3-value;
      else {missing.push({ref:q.ref,attribute,reason:'unsupported_relation'});continue;}
      proof.push({attribute,reference:q.ref,operation:q.op,observed:value,source:ref.source});
    }
    const candidates=missing.length?[]:[...entries.values()].filter(r=>Object.entries(resolved).every(([k,v])=>equal(r.attributes[k],v)))
      .map(r=>{let slot=r.slot;if(slotTransform){const {slotsPerRoom,shift}=slotTransform;
        if(!Number.isInteger(slotsPerRoom)||slotsPerRoom<1||!Number.isInteger(shift)||!Number.isInteger(slot)) throw Error('Explicit public integer slot transform required');
        slot=((slot+shift)%slotsPerRoom+slotsPerRoom)%slotsPerRoom;}
        return {id:r.id,original:r.id,room:r.room,slot};});
    return {index,resolved,proof,missing,candidates};
  });
  const unique=rows.every(r=>!r.missing.length && r.candidates.length===1),matches=rows.map(r=>r.candidates);
  return {status:unique?'unique_matches':'needs_reference_or_disambiguation',rows,matches,
    incomplete:[...entries.values()].filter(r=>attributes.some(k=>!Object.hasOwn(r.attributes,k))).map(r=>r.id),
    batches:unique?Array.from({length:Math.ceil(rows.length/capacity)},(_,i)=>matches.slice(i*capacity,(i+1)*capacity).flat()):[],
    note:'References use stable original identities; only explicit public slotTransform changes pickup positions. No invented room topology.'};
}
