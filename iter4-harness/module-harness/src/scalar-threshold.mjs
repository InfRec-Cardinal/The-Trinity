
export function scalarThreshold({observations,targets=[]}){
 if(!Array.isArray(observations)||!observations.length)return {status:'no_evidence'};
 for(const r of observations)if(!Number.isFinite(r.cut)||r.cut<0||![0,1].includes(r.label)||!r.source)throw Error('Sourced nonnegative cut and binary response required');
 for(const t of targets)if(!Number.isFinite(t.cut)||t.cut<0||!t.source)throw Error('Invalid public target cut');
 const cuts=[...new Set([0,...observations.map(r=>r.cut),...targets.map(t=>t.cut)])].sort((a,b)=>a-b);cuts.push(Math.max(1,cuts.at(-1)*2));
 const intervals=cuts.slice(0,-1).map((lo,i)=>{const hi=cuts[i+1],theta=(lo+hi)/2;return {lo,hi,theta,errors:observations.filter(r=>Number(r.cut>theta)!==r.label).length};});
 const minErrors=Math.min(...intervals.map(r=>r.errors)),best=intervals.filter(r=>r.errors===minErrors);
 const lower=Math.max(0,...observations.filter(r=>r.label===0).map(r=>r.cut));const upper=Math.min(Infinity,...observations.filter(r=>r.label===1).map(r=>r.cut));
 const consistent=lower<upper;let theta=consistent&&Number.isFinite(upper)?(lower+upper)/2:best[Math.floor(best.length/2)].theta;
 const predictions=targets.map(t=>({id:t.id,cut:t.cut,prediction:Number(t.cut>theta),modelAgreement:best.filter(r=>Number(t.cut>r.theta)===Number(t.cut>theta)).length/best.length,source:t.source}));
 const ambiguous=predictions.filter(t=>t.modelAgreement<1).map(t=>t.cut).sort((a,b)=>a-b);
 return {status:consistent?'consistent_threshold':'noisy_or_misspecified_threshold',parameter:theta,consistentInterval:consistent?{lower,upper:Number.isFinite(upper)?upper:null}:null,minTrainingErrors:minErrors,observations:observations.length,predictions,nextCut:ambiguous.length?ambiguous[Math.floor(ambiguous.length/2)]:theta,scope:'Fits label=1 iff the unknown scalar is below the public cut. Model agreement is not calibrated confidence; noisy outcomes and alternate model families can invalidate a hard threshold. No hidden parameter or target answer is available.'};
}
