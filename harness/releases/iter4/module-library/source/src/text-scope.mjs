
const pattern=/\b(section|chapter|part|stage|round|scene)\s*[#:\-]?\s*(\d+)\b/ig;
function labels(text){return [...String(text).matchAll(pattern)].map(m=>({family:m[1].toLowerCase(),ordinal:Number(m[2])}));}
function center(box){return box?.length===4?[box.reduce((s,p)=>s+p[0],0)/4,box.reduce((s,p)=>s+p[1],0)/4]:null;}
function sameRegion(a,b){return !a||!b||Math.hypot(a[0]-b[0],a[1]-b[1])<.2;}

export function locateTextScope({source,query,rows,scanGapSeconds,mediaSha256}){
  if(!/^obs-\d+$/.test(source)||!mediaSha256||!Array.isArray(rows)||!(scanGapSeconds>0&&scanGapSeconds<=30))throw Error('Sourced OCR index and scan gap required');
  const requested=labels(query);
  if(requested.length!==1)return {status:'no_unique_explicit_scope',source,semanticScopeVerified:false,candidates:[]};
  const target=requested[0],hits=[];
  for(const row of rows){
    if(!Number.isFinite(row.seconds)||row.seconds<0||!Number.isInteger(row.frame))throw Error('Timestamped OCR rows required');
    for(const e of row.entries??[]){
      if(!(e.confidence>=.75&&e.confidence<=1))continue;
      for(const l of labels(e.text))if(l.family===target.family)hits.push({...l,seconds:row.seconds,frame:row.frame,text:e.text,confidence:e.confidence,center:center(e.box)});
    }
  }
  hits.sort((a,b)=>a.seconds-b.seconds||b.confidence-a.confidence);
  const groups=[];
  for(const h of hits){
    const g=groups.findLast(g=>g.family===h.family&&g.ordinal===h.ordinal&&h.seconds-g.lastSeconds<=2*scanGapSeconds&&sameRegion(g.center,h.center));
    if(g){g.lastSeconds=h.seconds;if(h.confidence>g.witness.confidence)g.witness=h;g.samples++;}
    else groups.push({...h,firstSeconds:h.seconds,lastSeconds:h.seconds,witness:h,samples:1});
  }
  groups.sort((a,b)=>a.firstSeconds-b.firstSeconds);
  const candidates=[];
  for(const g of groups.filter(g=>g.ordinal===target.ordinal)){
    const next=groups.find(h=>h.firstSeconds>g.lastSeconds&&h.ordinal!==g.ordinal&&sameRegion(g.center,h.center));
    if(!next||next.ordinal!==g.ordinal+1)continue;
    candidates.push({startSeconds:Math.max(0,g.firstSeconds-scanGapSeconds),endSeconds:next.firstSeconds+scanGapSeconds,
      firstLabelSeconds:g.firstSeconds,nextLabelSeconds:next.firstSeconds,
      witnesses:[g.witness,next.witness],boundaryUncertaintySeconds:scanGapSeconds});
  }
  return {status:candidates.length===1?'candidate_scope_located':candidates.length?'ambiguous_repeated_scope':'missing_boundary_evidence',source,mediaSha256,target,candidates,
    semanticScopeVerified:false,scanGapSeconds,
    instruction:'Check both actual heading images. OCR locations are candidate subsection bounds, not proven semantic scope. Exclude the next subsection; repeated headings may be a recap. First inspect the full candidate interval, then spend the remaining acquisition on ambiguous resets. Missing OCR text is not proof of a missing boundary.'};
}

export function auditScopeRequest({scopePlan,startSeconds,endSeconds,hasScopeOverview=false}){
  if(scopePlan?.status!=='candidate_scope_located'||scopePlan.candidates.length!==1)return {status:'no_unique_scope_constraint'};
  if(![startSeconds,endSeconds].every(Number.isFinite)||endSeconds<=startSeconds)throw Error('Valid request interval required');
  const c=scopePlan.candidates[0],pad=c.boundaryUncertaintySeconds;
  const outside=startSeconds<c.startSeconds-pad||endSeconds>c.endSeconds+pad;
  const missingBoundary=!hasScopeOverview&&(startSeconds>c.firstLabelSeconds||endSeconds<c.nextLabelSeconds);
  return {status:outside||missingBoundary?'review_scope':'consistent_with_candidate_scope',hasScopeOverview,
    recommendedInterval:{startSeconds:c.startSeconds,endSeconds:c.endSeconds},
    reason:outside?'Requested frames cross a separately witnessed subsection boundary.':missingBoundary?'The first acquisition omits a witnessed scope boundary. Inspect the whole candidate subsection before a local refinement.':'The interval matches OCR candidate boundaries; event interpretation remains the Player responsibility.',
    semanticScopeVerified:false,witnesses:c.witnesses};
}
