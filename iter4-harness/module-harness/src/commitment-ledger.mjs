import {equal} from './common.mjs';


export function reviewCommitment(input) {
 const out=(status,message,analysis={},alternatives=[])=>({status,reasons:[message],analysis,alternatives});
 const h=input.history??[],packet=input.evidencePacket??{},contract=input.contract;
 if(!contract)return out('block','Local evidence protocol: first declare goal conditions and action roles from exact quotes in the initial PUBLIC observation. No native action ran. This is an interface requirement, not a claim that your action is illegal.',{issues:input.contractIssues??[]});
 const matches=(a,b)=>Object.entries(b??{}).every(([k,v])=>equal(a?.[k],v));
 const role=contract.actions.find(a=>matches(input.action,a.action));
 if(!role)return out('block','Action-role binding does not cover the native action discriminator. No goal verification was performed; repair the interface mapping before execution.',{interfaceError:true});
 const refs=new Map(h.map((r,i)=>[`obs-${i}`,{...r,index:i,frame:r.publicText?.match(/PUBLIC_FRAME_SHA256: ([a-f0-9]{64})/)?.[1]}]));
 const previous=input.packets??[],ledger=[...previous,{step:h.length-1,packet}],issues=[],states=[];
 const sourceText=r=>(r?.publicText??'').split('\nPUBLIC_FRAME_SHA256:')[0];
 const definitions=new Map(contract.requirements.map(r=>[r.id,r]));
 const domains=new Map((contract.domains??[]).map(d=>[d.id,d]));
 const short=xs=>[...new Set(xs)].slice(-4);
 const issue=(id,reason)=>{if(issues.length<12&&!issues.some(x=>x.id===id&&x.reason===reason))issues.push({id,reason});};
 const applicability=req=>{
  const c=req.appliesWhen;if(!c)return 'active';
  const value=input.action?.[c.field];if(!['string','number','boolean'].includes(typeof value))return 'unresolved';
  const norm=v=>typeof v==='string'?v.trim().toLowerCase():v;
  return (c.operator==='eq'?(norm(value)===norm(c.value)):(norm(value)!==norm(c.value)))?'active':'inactive';
 };
 const evaluated=new Map();
 function evaluate(req){
  if(evaluated.has(req.id))return evaluated.get(req.id);
  const base={id:req.id,kind:req.kind,temporal:req.temporal,applicability:applicability(req),positiveSources:[],negativeSources:[],witnessEvents:[],disputedEvents:[],visualSemanticsVerified:false};
  if(req.logic){
   const children=req.logic.children.map(id=>evaluate(definitions.get(id)));
   const values=children.map(c=>c.state);
   const state=req.logic.op==='and'
    ? values.every(x=>x==='supported')?'supported':values.includes('contradicted')?'contradicted':values.includes('conflict')?'conflict':'unknown'
    : values.includes('supported')?'supported':values.every(x=>x==='contradicted')?'contradicted':values.includes('conflict')?'conflict':'unknown';
   const result={...base,state,logic:req.logic,missingChildren:children.filter(c=>c.state!=='supported').map(c=>c.id)};
   evaluated.set(req.id,result);return result;
  }
  const coverage=req.coverage,domain=domains.get(coverage.domainId),facts=[];
  for(const submitted of ledger)for(const ev of submitted.packet?.observations??[]){
   const origin=definitions.get(ev.requirementId);

   if(!origin||origin.logic||origin.predicate!==req.predicate||origin.coverage.domainId!==coverage.domainId)continue;
   if(ev.predicate!==req.predicate||!domain.members.some(m=>m.id===ev.subjectId)){issue(req.id,'unbound_subject_or_predicate');continue;}
   const r=refs.get(ev.source);if(!r||r.index>submitted.step){issue(req.id,'unknown_or_future_source');continue;}
   if(req.scope==='current'&&r.index!==h.length-1)continue;
   if(!ev.detail?.trim()||ev.polarity==='unknown'||ev.kind==='inference'||ev.kind==='absence')continue;
   if(ev.channel==='text'&&!sourceText(r).includes(ev.detail)){issue(req.id,'quote_not_in_observation');continue;}
   if(ev.channel==='image'&&(!r.frame||ev.visibility!=='resolved'))continue;
   if(req.kind==='measurement'&&(ev.channel!=='text'||ev.kind!=='measurement'))continue;
   if(req.kind==='effect'){
    const prev=refs.get(ev.previousSource);
    if(ev.kind!=='transition'||!prev||r.index!==prev.index+1||!r.action)continue;
   }
   if(ev.kind==='transition'){
    const prev=refs.get(ev.previousSource);
    if(!prev||r.index!==prev.index+1||!r.action||!ev.before||!ev.after||ev.before===ev.after)continue;
    if(r.frame&&r.frame===prev.frame){issue(req.id,'identical_frames_do_not_demonstrate_visual_change');continue;}
   }
   const event=ev.kind==='transition'?`${ev.previousSource}->${ev.source}`:ev.source;
   const key=ev.subjectId+'|'+(req.temporal==='ever'?event+'|':'')+(ev.channel==='image'?r.frame:ev.source+'|'+ev.detail);
   if(facts.some(f=>f.key===key&&f.polarity===ev.polarity))continue;
   facts.push({...ev,key,event});
  }
  const members=domain.members.map(member=>{
   const same=facts.filter(e=>e.subjectId===member.id),positive=same.filter(e=>e.polarity==='supports');
   const negative=same.filter(e=>e.polarity==='contradicts'&&e.contrastFeature?.trim());
   const refuted=negative.some(e=>e.channel==='text')||new Set(negative.filter(e=>e.channel==='image').map(e=>e.key)).size>=2;
   const disputed=positive.filter(p=>negative.some(n=>n.event===p.event));
   const witnessed=positive.filter(p=>!disputed.includes(p));
   const state=req.temporal==='ever'?(witnessed.length?'supported':disputed.length?'conflict':'unknown')
    :positive.length&&refuted?'conflict':refuted?'contradicted':positive.length?'supported':'unknown';
   return {id:member.id,state,positive,negative,witnessed,disputed};
  });
  let selected=members,selectedSubject=null;
  if(coverage.mode==='single'){
   selectedSubject=coverage.subjectId;
   if(coverage.actionField){
    const value=input.action?.[coverage.actionField],norm=x=>String(x).trim().toLowerCase().replace(/\s+/g,' ');
    const candidates=['string','number','boolean'].includes(typeof value)?domain.members.filter(m=>{
     const escaped=norm(m.label).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
     return new RegExp('(^|[^\\p{L}\\p{N}_])'+escaped+'($|[^\\p{L}\\p{N}_])','u').test(norm(value));
    }):[];
    selectedSubject=candidates.length===1?candidates[0].id:null;
   }
   selected=members.filter(m=>m.id===selectedSubject);
  }
  const yes=selected.filter(m=>m.state==='supported'),no=selected.filter(m=>m.state==='contradicted'),conflicts=selected.filter(m=>m.state==='conflict');
  const closed=domain.closed&&domain.expectedCount===domain.members.length;
  const needed=coverage.mode==='all'?domain.expectedCount:coverage.mode==='at_least'?coverage.minimum:1;
  let state='unknown';
  if(coverage.mode==='single'&&!selected.length)issue(req.id,'answer_subject_unresolved');
  else if(coverage.mode==='all'&&!closed)state=no.length?'contradicted':conflicts.length?'conflict':'unknown';
  else if(Number.isInteger(needed)&&needed>0&&yes.length>=needed)state='supported';
  else if((closed||coverage.mode==='single')&&selected.length-no.length<needed)state='contradicted';
  else if(conflicts.length)state='conflict';
  const result={...base,state,predicate:req.predicate,
   coverage:{mode:coverage.mode,domainId:domain.id,closed,expectedCount:domain.expectedCount,knownCount:members.length,requiredCount:needed,selectedSubject,supportedSubjects:yes.map(m=>m.id),missingSubjects:selected.filter(m=>m.state!=='supported').map(m=>m.id),universeUnknown:!closed},
   positiveSources:short(selected.flatMap(m=>m.positive.map(e=>e.source))),negativeSources:short(selected.flatMap(m=>m.negative.map(e=>e.source))),
   witnessEvents:req.temporal==='ever'?short(selected.flatMap(m=>m.witnessed.map(e=>e.event))):[],disputedEvents:short(selected.flatMap(m=>m.disputed.map(e=>e.event)))};
  evaluated.set(req.id,result);return result;
 }
 for(const req of contract.requirements)states.push(evaluate(req));
 const pre=states.filter(s=>contract.requirements.find(r=>r.id===s.id).role==='precondition'&&s.applicability!=='inactive');
 const isCommit=['confirm','refute'].includes(role.kind);
 const supported=pre.length>0&&pre.every(s=>s.applicability==='active')&&(role.kind==='refute'?pre.some(s=>s.state==='contradicted'):pre.every(s=>s.state==='supported'));
 const missing=pre.filter(s=>s.applicability==='unresolved'||(role.kind==='refute'?['unknown','conflict'].includes(s.state):s.state!=='supported'));
 const progressCount=h.slice(1).reduce((n,r)=>n+(contract.actions.find(a=>matches(r.action,a.action))?.cost??1),0);
 const hostRemaining=Math.max(0,input.budget?.remaining??0);
 const resourceRemaining=Math.max(0,contract.resourceLimit-progressCount);
 const remaining=Math.min(hostRemaining,resourceRemaining);
 const reserve=1;
 const now=h.length-1,frame=refs.get(`obs-${now}`)?.frame;
 const stalled=[];
 for(let i=1;i<h.length;i++){const a=refs.get(`obs-${i-1}`),b=refs.get(`obs-${i}`);if(frame&&a.frame===frame&&b.frame===frame)stalled.push(b.action);}
 const unresolved=new Set(missing.map(s=>s.id));
 const candidates=(packet.options??[]).filter(o=>{
  const a=contract.actions.find(a=>matches(o.action,a.action));
  return a&&['observe','progress'].includes(a.kind)&&o.feasible===true&&o.expectedObservation?.trim()&&o.addresses?.some(id=>unresolved.has(id))&&a.cost>0&&hostRemaining>reserve&&a.cost<=resourceRemaining-reserve&&!stalled.some(action=>equal(action,o.action));
 }).map(o=>({...o,cost:contract.actions.find(a=>matches(o.action,a.action)).cost,coverage:new Set(o.addresses.filter(id=>unresolved.has(id))).size})).sort((a,b)=>b.coverage/b.cost-a.coverage/a.cost||a.cost-b.cost);
 const analysis={logicVersion:contract.logicVersion,role:role.kind,contractHash:input.contractHash,states,missing:missing.map(s=>s.id),issues,remaining,hostRemaining,resourceRemaining,reserve,contractFrozen:true,visualSemanticsVerified:false,selected:candidates[0]??null,contractAmendmentIgnored:!!packet.setup&&previous.length>0};
 if(!isCommit&&(hostRemaining<=reserve||role.cost>resourceRemaining-reserve))return out('block','Local budget guard: this progress/observation action would consume the reserved final decision opportunity. Submit a legal terminal action using the best available evidence, retaining uncertainty. No native action executed and no answer was fabricated.',{...analysis,budgetGuard:true});
 if(!isCommit)return out('allow','Execute the proposed public action; compare the new observation with its expected effect. The goal conditions remain frozen.',analysis);
 if(supported)return out('allow','The frozen quantified goal has the required subject-bound witnesses under the supplied observations. Visual interpretation remains uncertain; native judgement decides the result.',analysis);
 if(candidates.length)return out('block','Local commitment guard: the FROZEN goal conditions still have unresolved evidence and an affordable feasible probe is available. Submit the listed probe or another supported progress action, then inspect its actual feedback. Do not weaken or rename the goal conditions, classify image appearance as a measurement, or recycle the same observation as new evidence. This is a strategic evidence guard, not native illegality. A refused/inert action invalidates that probe; it does not prove the goal.',analysis,[candidates[0].action]);
 if(remaining>reserve)return out('advice','The FROZEN goal conditions are unresolved. You supplied no feasible probe. Review the public action set and current view once: if a reversible observation/progress action could reduce a specific gap, provide it in options with the expected visible change and execute it. Do not blindly probe an obstruction. If no such action is grounded, keep the best native decision with uncertainty; do not invent evidence or weaken the contract.',analysis);
 return out('allow','No budget remains for an extra probe while reserving a decision. Commit using the best available evidence; this is an uncertainty/budget release, not a verified success claim.',{...analysis,uncertainRelease:true});
}
