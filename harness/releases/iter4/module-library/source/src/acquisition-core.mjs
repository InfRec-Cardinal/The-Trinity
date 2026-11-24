const finite=x=>typeof x==='number'&&Number.isFinite(x);
import {equal as same} from './common.mjs';
export function validateRequirements(requirements){
  const ids=new Set();
  for(const r of requirements){
    if(!r.id||ids.has(r.id)||!r.source||!['visual','audio'].includes(r.channel)||
      !finite(r.start)||!finite(r.end)||r.end<r.start)throw Error('Unique sourced requirement with channel and interval required');
    ids.add(r.id);
    if(r.region && (!Array.isArray(r.region)||r.region.length!==4||r.region.some(v=>!finite(v))||
      r.region[0]<0||r.region[1]<0||r.region[2]<=0||r.region[3]<=0||r.region[0]+r.region[2]>1||r.region[1]+r.region[3]>1))
      throw Error('Region must be normalized [x,y,width,height]');
    if(r.maxFrameGap!==undefined&&(!finite(r.maxFrameGap)||r.maxFrameGap<=0))throw Error('Positive frame gap required');
    if(r.minFrames!==undefined&&(!Number.isInteger(r.minFrames)||r.minFrames<1))throw Error('Positive frame count required');
  }
}
function contains(outer=[0,0,1,1],inner=[0,0,1,1]){
  return outer[0]<=inner[0] && outer[1]<=inner[1] && outer[0]+outer[2]>=inner[0]+inner[2] && outer[1]+outer[3]>=inner[1]+inner[3];
}
function sufficientDelivery(r,d){
  if(!d.source||!d.receiptId||d.channel!==r.channel||d.requirementId!==r.id||d.acquired!==true)return false;

  if(d.requirementSignature!==requirementSignature(r))return false;
  if(r.channel==='audio')return d.start<=r.start && d.end>=r.end && d.audible===true;
  if(!Array.isArray(d.times)||!d.times.length||d.times.some(t=>!finite(t))||!contains(d.region,r.region))return false;
  if(r.minDetailPixels && !(d.targetDetailPixels>=r.minDetailPixels))return false;
  if(r.requireLegible && d.legible!==true)return false;
  const times=[...new Set(d.times)].sort((a,b)=>a-b);
  if(times[0]>r.start||times.at(-1)<r.end||times.length<(r.minFrames??1))return false;
  if(r.maxFrameGap && times.slice(1).some((t,i)=>t-times[i]>r.maxFrameGap+1e-9))return false;
  return true;
}
export function requirementSignature(r){return JSON.stringify([r.id,r.channel,r.start,r.end,r.region??null,
  r.maxFrameGap??null,r.minFrames??null,r.minDetailPixels??null,r.requireLegible??false]);}
export function auditCoverage({requirements,delivered=[]}){
  validateRequirements(requirements);
  const seen=new Map(),conflicts=new Set();
  for(const d of delivered){if(d.receiptId&&seen.has(d.receiptId)&&!same(d,seen.get(d.receiptId)))conflicts.add(d.receiptId);else if(d.receiptId)seen.set(d.receiptId,d);}
  const rows=requirements.map(r=>{const witness=delivered.find(d=>!conflicts.has(d.receiptId)&&sufficientDelivery(r,d));
    return {requirementId:r.id,channel:r.channel,covered:!!witness,witness:witness?.receiptId??null,
      signature:requirementSignature(r),status:witness?'delivered':'missing_or_insufficient_delivery'};});
  return {rows,complete:rows.length>0&&rows.every(r=>r.covered),conflictingReceipts:[...conflicts],
    missing:rows.filter(r=>!r.covered).map(r=>r.requirementId),canSubmit:false,
    note:'Coverage certifies evidence delivery only, not the truth of an answer. Purchase/unlock alone is not sufficient.'};
}
export function planAcquisition({requirements,delivered=[],offers,budget,submitCost=1,attempts=[],maxFrames=128}){
  if(!finite(budget)||budget<0||!finite(submitCost)||submitCost<0)throw Error('Nonnegative action budget required');
  const coverage=auditCoverage({requirements,delivered}),missing=new Set(coverage.missing),candidates=[],unsupported=[];
  const offerIds=new Set();
  for(const o of offers){if(!o.id||offerIds.has(o.id)||!o.source||!o.tool||!finite(o.cost)||o.cost<0)throw Error('Unique sourced tool offer and nonnegative total cost required');offerIds.add(o.id);}
  for(const r of requirements.filter(r=>missing.has(r.id))){
    const choices=[];
    for(const o of offers){
      if(o.channel!==r.channel||!(o.start<=r.start&&o.end>=r.end))continue;
      if(r.channel==='visual'&&r.region&&!o.supportsCrop)continue;
      if(r.channel==='visual'&&r.minDetailPixels&&!(o.maxDetailPixels>=r.minDetailPixels))continue;
      let times;
      if(r.channel==='visual'){
        const count=Math.max(r.minFrames??1,r.start===r.end?1:2,r.maxFrameGap?Math.ceil((r.end-r.start)/r.maxFrameGap)+1:1);
        if(count>maxFrames||count>(o.maxFrames??0))continue;
        times=Array.from({length:count},(_,i)=>count===1?r.start:r.start+(r.end-r.start)*i/(count-1));
      }
      const parameters={start:r.start,end:r.end,...(times?{times,region:r.region??[0,0,1,1]}:{}),
        ...(r.minDetailPixels?{minDetailPixels:r.minDetailPixels}:{})};
      const requestKey=JSON.stringify([o.id,o.tool,parameters,requirementSignature(r)]);
      const repeated=attempts.some(a=>a.source&&a.requestKey===requestKey&&['no_gain','unsupported','failed'].includes(a.outcome));
      if(repeated)continue;
      choices.push({requirementId:r.id,requirementSignature:requirementSignature(r),offerId:o.id,tool:o.tool,
        channel:r.channel,cost:o.cost,parameters,requestKey,priority:r.priority??1});
    }
    choices.sort((a,b)=>a.cost-b.cost||a.offerId.localeCompare(b.offerId));
    if(choices.length)candidates.push(choices[0]);else unsupported.push({requirementId:r.id,reason:'no_supported_untried_request'});
  }
  candidates.sort((a,b)=>b.priority-a.priority||a.cost-b.cost||a.requirementId.localeCompare(b.requirementId));
  let available=Math.max(0,budget-submitCost);const requests=[],deferred=[];
  for(const c of candidates){if(c.cost<=available){requests.push(c);available-=c.cost;}else deferred.push({requirementId:c.requirementId,reason:'budget_reserved_for_submission'});}
  return {status:coverage.complete?'evidence_delivered':requests.length?'acquire_evidence':unsupported.length?'needs_supported_acquisition':'budget_shortfall',
    coverage,requests,next:requests[0]??null,unsupported,deferred,reserve:submitCost,
    plannedCost:requests.reduce((s,r)=>s+r.cost,0),remainingBudget:budget-requests.reduce((s,r)=>s+r.cost,0),canSubmit:false,
    note:'Use only advertised public tools. Requests are not execution receipts; verify returned frame times, detail, audio and legibility before marking evidence delivered.'};
}
