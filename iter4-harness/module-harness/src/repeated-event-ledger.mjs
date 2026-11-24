

export function requestSequenceAudit({source,sequenceId,sampleCount}){
  if(!/^obs-\d+$/.test(source??'')||!sequenceId||!Number.isInteger(sampleCount)||sampleCount<1)throw Error('Delivered sequence identity required');
  return {status:'review_sequence_once',source,sequenceId,sampleCount,noWorldActionExecuted:true,
    note:'The proposed answer has not been submitted. The delivered count sequence has no event ledger yet. Use consult_capability_path with moduleId eventLedger and input {mode:"audit_public_sequence",source:"'+source+'",sequenceId:"'+sequenceId+'",segments:[{first:0,last:...,state:"other|target|uncertain"},...]}. Cover every sample index from 0 through '+(sampleCount-1)+'. Read the primary actor chronologically, including the earliest isolated demonstration. Separate a repeated start after the actor leaves the target movement; adjacent held target poses are one event. This is a record of public visible observations, not a correctness hint. The module will audit the sequence; no answer is supplied.'};
}
export function countRepeatedEvents({source,frames,segments,descriptors}){
  if(!/^obs-\d+$/.test(source??'')||!Array.isArray(frames)||!frames.length||!Array.isArray(segments)||segments.length>256)throw Error('Current public sequence and bounded segment ledger required');
  if(frames.some((f,i)=>!f.sha256||!Number.isFinite(f.seconds)||(i&&f.seconds<=frames[i-1].seconds)))throw Error('Strictly ordered timestamped source frames required');
  const labels=Array(frames.length).fill(null),conflicts=[],invalid=[];
  for(const s of segments){
    if(!Number.isInteger(s.first)||!Number.isInteger(s.last)||s.first<0||s.last<s.first||s.last>=frames.length||!['target','other','uncertain'].includes(s.state)){
      invalid.push(s);continue;
    }
    for(let i=s.first;i<=s.last;i++){
      if(labels[i]!==null&&labels[i]!==s.state)conflicts.push(i);
      else labels[i]=s.state;
    }
  }
  const missing=labels.flatMap((s,i)=>s===null?[i]:[]),uncertain=labels.flatMap((s,i)=>s==='uncertain'?[i]:[]);
  const events=[];
  for(let i=0;i<labels.length;i++)if(labels[i]==='target'){
    const first=i;while(i+1<labels.length&&labels[i+1]==='target')i++;
    events.push({id:`event-${events.length+1}`,first,last:i,startSeconds:frames[first].seconds,endSeconds:frames[i].seconds,
      sourceFrames:frames.slice(first,i+1).map(f=>({sourceFrame:f.sourceFrame,seconds:f.seconds,sha256:f.sha256})),
      precedingState:first?labels[first-1]:'sequence_boundary',followingState:i+1<labels.length?labels[i+1]:'sequence_boundary'});
  }
  const complete=!invalid.length&&!conflicts.length&&!missing.length&&!uncertain.length;
  const result={status:complete?'sequence_partition_audited':'incomplete_or_conflicting_partition',source,structuralAuditComplete:complete,
    count:complete?events.length:null,candidateRuns:events.length,events,missing,uncertain,conflicts:[...new Set(conflicts)],invalid,
    semanticInterpretationVerified:false,samplingMayMissEvents:true,
    rule:'Adjacent target samples form one event even if split into several input segments. A new target run after an observed non-target state is a distinct occurrence. Inspect every sample, including the first isolated demonstration and subsequent run-throughs. Classify the requested actor, not inset clips. The count is conditional on your visual labels and sampling; it is not an independent action detector.'};
  if(complete&&descriptors){
    const visualAudit=auditRunContinuity({events,descriptors});
    visualAudit.rejectedLabelAudit=auditOmittedEvents({events,labels,descriptors});
    visualAudit.inspectSamples=[...new Set([
      ...visualAudit.counterexamples.flatMap(c=>c.inspectSamples),
      ...visualAudit.rejectedLabelAudit.candidates.flatMap(c=>c.inspectSamples),
    ])].sort((a,b)=>a-b);
    result.visualAudit=visualAudit;
    if(visualAudit.inspectSamples.length){
      result.provisionalCount=result.count;result.count=null;result.status='visual_labels_need_review';
      result.reviewInstruction='Review the listed public sample indices in the supplied images. A continuity cue asks whether a target span contains a reset and a restart. A rejected-label cue asks whether a frame you labelled other resembles the same movement across your separate target runs; compare its before/after neighbors with the reference sample. Check the requested movement and actor, not pose similarity alone. These are possible label inconsistencies, not detected events. Do not add an event merely from feature distance. Correct the visual partition and its conditional count before selecting an answer.';
    }
  }
  return result;
}

export function auditRunContinuity({events,descriptors}){
  const distance=descriptorDistance(descriptors);
  const candidates=[];
  for(const e of events){
    if(e.last-e.first<2)continue;
    const endpointDistance=distance(e.first,e.last);
    let best=null;
    for(let i=e.first+1;i<e.last;i++){
      const interiorDistance=Math.min(distance(e.first,i),distance(e.last,i));
      if(!best||interiorDistance>best.interiorDistance)best={interior:i,interiorDistance};
    }
    if(best&&best.interiorDistance>1.5*Math.max(endpointDistance,1e-4))candidates.push({eventId:e.id,first:e.first,last:e.last,...best,endpointDistance,contrast:best.interiorDistance-endpointDistance,
      inspectSamples:[...new Set([e.first,best.interior,Math.min(best.interior+1,e.last),e.last])].sort((a,b)=>a-b)});
  }
  candidates.sort((a,b)=>b.contrast-a.contrast);
  return {method:'similar endpoints with contrasting interior; cosine descriptors are inspection cues only',counterexamples:candidates.slice(0,1),independentActionRecognition:false,canInferAdditionalEvents:false};
}

export function auditOmittedEvents({events,labels,descriptors}){
  const empty={method:'compare excluded samples with separate labelled target runs',candidates:[],independentActionRecognition:false,canInferAdditionalEvents:false};
  if(events.length<2)return {...empty,status:'insufficient_distinct_reference_runs'};
  const distance=descriptorDistance(descriptors);
  const nearest=(i,e)=>{
    let best=null;
    for(let j=e.first;j<=e.last;j++){
      const d=distance(i,j);if(!best||d<best.distance)best={sampleIndex:j,eventId:e.id,distance:d};
    }
    return best;
  };

  const baseline=[];
  for(const event of events)for(let i=event.first;i<=event.last;i++){
    const other=events.filter(e=>e.id!==event.id);
    baseline.push(other.reduce((s,e)=>s+nearest(i,e).distance,0)/other.length);
  }
  baseline.sort((a,b)=>a-b);
  const median=xs=>{const sorted=[...xs].sort((a,b)=>a-b),n=sorted.length;return n?(sorted[Math.floor((n-1)/2)]+sorted[Math.floor(n/2)])/2:null;};
  const referenceMedianDistance=median(baseline);
  const ranked=[];
  for(let i=1;i<labels.length-1;i++){

    if(![labels[i-1],labels[i],labels[i+1]].every(x=>x==='other'))continue;
    const refs=events.map(e=>nearest(i,e));
    const score=refs.reduce((s,r)=>s+r.distance,0)/refs.length;
    refs.sort((a,b)=>a.distance-b.distance);
    ranked.push({sampleIndex:i,meanCrossEventDistance:score,reference:refs[0],
      inspectSamples:[i-1,i,i+1,refs[0].sampleIndex]});
  }
  const excludedMedianDistance=median(ranked.map(r=>r.meanCrossEventDistance));
  ranked.sort((a,b)=>a.meanCrossEventDistance-b.meanCrossEventDistance||a.sampleIndex-b.sampleIndex);
  const candidates=[];
  for(const c of ranked){

    if(!(c.meanCrossEventDistance+1e-8<excludedMedianDistance))continue;
    if(candidates.some(x=>Math.abs(x.sampleIndex-c.sampleIndex)<=2))continue;
    candidates.push(c);if(candidates.length===2)break;
  }
  return {...empty,status:'candidate_retrieval_complete',referenceMedianDistance,excludedMedianDistance,
    selection:'best two disjoint excluded neighborhoods more similar to labelled runs than the typical excluded sample; ranks are not action probabilities',candidates};
}

function descriptorDistance(descriptors){
  if(!Array.isArray(descriptors)||descriptors.length>96)throw Error('Bounded visual descriptors required');
  const map=new Map(descriptors.map(d=>[d.index,d.descriptor]));
  if(map.size!==descriptors.length)throw Error('Unique descriptor sample indices required');
  return (i,j)=>{
    const a=map.get(i),b=map.get(j);if(!a||!b||a.length!==b.length||!a.length||a.some(x=>!Number.isFinite(x))||b.some(x=>!Number.isFinite(x)))throw Error('Finite comparable descriptors required');
    const dot=a.reduce((s,x,k)=>s+x*b[k],0),aa=a.reduce((s,x)=>s+x*x,0),bb=b.reduce((s,x)=>s+x*x,0);
    if(!aa||!bb)throw Error('Nonzero descriptors required');return Math.max(0,1-dot/Math.sqrt(aa*bb));
  };
}
