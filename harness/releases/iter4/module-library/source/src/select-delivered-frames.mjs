

export function selectDeliveredFrames({source,frames,proposed=[],limit=12,purpose='relational'}) {
  if(!/^obs-\d+$/.test(source??'') || !Array.isArray(frames) || !frames.length) throw Error('Current sourced frame catalog required');
  if(!Number.isInteger(limit)||limit<1||limit>12)throw Error('Inspection limit must be 1..12');
  const ids=new Set();const dimension=frames[0].descriptor?.length;
  for(const f of frames){
    if(!Number.isSafeInteger(f.index)||f.index<0||ids.has(f.index)||!f.sha256||!Array.isArray(f.descriptor)||!dimension||f.descriptor.length!==dimension||f.descriptor.some(x=>!Number.isFinite(x)))throw Error('Unique hashed frames with finite equal-length descriptors required');
    ids.add(f.index);
  }
  if(!Array.isArray(proposed)||proposed.some(i=>!ids.has(i)))throw Error('Requested frame is outside delivered evidence');
  const ordered=[...frames].sort((a,b)=>a.index-b.index),byId=new Map(ordered.map(f=>[f.index,f]));
  const anchors=[...new Set(proposed)].sort((a,b)=>a-b);
  const distance=(a,b)=>Math.sqrt(a.descriptor.reduce((v,x,i)=>v+(x-b.descriptor[i])**2,0)/dimension);
  const chosen=new Map();
  const add=(index,role,relatedTo=null)=>{if(!byId.has(index)||chosen.size>=limit)return;const item=chosen.get(index)??{index,roles:[]};item.roles.push({role,relatedTo});chosen.set(index,item);};
  if(!anchors.length){
    for(let k=0;k<Math.min(limit,ordered.length);k++)add(ordered[Math.round(k*(ordered.length-1)/Math.max(1,Math.min(limit,ordered.length)-1))].index,'unlocalized_overview');
  }else if(purpose==='temporal_count'){

    for(const i of anchors)add(i,'proposed_temporal_anchor');
    for(const delta of [-1,1,-2,2])for(const i of anchors){
      if(chosen.size>=limit)break;
      if(!chosen.has(i+delta))add(i+delta,'local_temporal_boundary',i);
    }
  }else{

    const retained=[anchors[0]];if(anchors.length>1)retained.push(anchors.at(-1));
    const anchorBudget=Math.min(6,Math.max(1,Math.floor(limit/2)));
    while(retained.length<Math.min(anchorBudget,anchors.length)){
      const next=anchors.filter(i=>!retained.includes(i)).sort((a,b)=>{
        const value=i=>Math.min(...retained.map(j=>distance(byId.get(i),byId.get(j))));
        return value(b)-value(a)||a-b;
      })[0];retained.push(next);
    }
    for(const i of retained.slice(0,anchorBudget))add(i,'proposed_anchor');

    const exclusion=Math.max(2,Math.floor(ordered.length/12));
    const outside=ordered.filter(f=>f.index<anchors[0]-exclusion||f.index>anchors.at(-1)+exclusion);
    const references=[...retained].sort((a,b)=>(byId.get(b).relevance??0)-(byId.get(a).relevance??0)||a-b);
    for(const i of references){
      if(chosen.size>=Math.max(anchorBudget,limit-2))break;
      const nearest=outside.filter(f=>!chosen.has(f.index)).sort((a,b)=>distance(byId.get(i),a)-distance(byId.get(i),b)||a.index-b.index)[0];
      if(nearest)add(nearest.index,'separated_appearance_candidate',i);
    }
    add(anchors[0]-1,'before_proposed_interval');add(anchors.at(-1)+1,'after_proposed_interval');
    for(const i of anchors)if(chosen.size<limit)add(i,'remaining_proposed');
  }
  return {status:'selected_delivered_frames',source,purpose,requestedFrameIndices:anchors,frameIndices:[...chosen.keys()].sort((a,b)=>a-b),selection:[...chosen.values()].sort((a,b)=>a.index-b.index),
    sourceCount:ordered.length,newEvidenceAcquired:false,semanticCoverageVerified:false,
    warning:'Appearance matches are hypotheses for cross-view comparison, not identity proof. Compare scene/subject and distinguish repeated events. A pose sample cannot certify an unsampled action or exact count.'};
}
