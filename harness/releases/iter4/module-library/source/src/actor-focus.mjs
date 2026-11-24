

export function planActorFocus({frames}){
  if(!Array.isArray(frames)||!frames.length||frames.length>96)throw Error('Bounded public frame proposals required');
  let previous=null;
  const area=b=>(b[2]-b[0])*(b[3]-b[1]);
  const overlap=(a,b)=>{if(!b)return 0;const i=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));return i/(area(a)+area(b)-i);};
  const selected=frames.map((f,index)=>{
    if(!f.sha256||f.sampleIndex!==index)throw Error('Ordered hashed frame proposals required');
    const ds=(f.detections??[]).filter(d=>d.confidence>=.5&&Array.isArray(d.box)&&d.box.length===4&&d.box.every(x=>Number.isFinite(x)&&x>=0&&x<=1)&&d.box[2]>d.box[0]&&d.box[3]>d.box[1]);
    const ranked=ds.map(d=>({...d,score:area(d.box)*(1+overlap(d.box,previous))})).sort((a,b)=>b.score-a.score);
    if(!ranked.length||(ranked[1]&&ranked[1].score>=.8*ranked[0].score))return {sampleIndex:index,sha256:f.sha256,box:[0,0,1,1],status:'ambiguous_or_missing_person_use_context'};
    const d=ranked[0],b=d.box,w=b[2]-b[0],h=b[3]-b[1];previous=b;
    return {sampleIndex:index,sha256:f.sha256,box:[Math.max(0,b[0]-.15*w),Math.max(0,b[1]-.06*h),Math.min(1,b[2]+.15*w),Math.min(1,b[3]+.06*h)],status:'prominent_continuous_person_candidate',confidence:d.confidence};
  });
  return {selected,semanticIdentityVerified:false,actionRecognized:false,originalContextRetained:true,
    instruction:'Compare the enlarged person candidate with the retained full-frame thumbnail. If the question concerns another actor or a prop, use the original context. These regions do not identify an action or count occurrences.'};
}
