import {immutableSnapshot} from '../../../shared/immutable-snapshot.mjs';
import {fileURLToPath} from 'node:url';
import {validateLogicalContract} from './contract-logic.mjs';
import {normalizeActionRoles,actionRoleSchema} from './action-roles.mjs';
import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';
export const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
export function validateModule(m){
 if(!m||m.bindingId!=='bounded_action_policy'||!/^[_a-zA-Z0-9]{3,80}$/.test(m.moduleId)||!Number.isInteger(m.version)||m.version<1)throw Error('Invalid policy identity');
 if(typeof m.source!=='string'||m.source.length>32000||!m.interface?.description||!m.targetCapabilityNodeId||m.evidenceRounds?.length!==5)throw Error('Invalid policy contract');
 if(!/^\s*(function\b|\(?\s*input\s*\)?\s*=>)/.test(m.source))throw Error('Expected one pure function expression');
 return m;
}
export function execute(m,input){
 validateModule(m);
 const raw=execFileSync(process.execPath,['--max-old-space-size=64',fileURLToPath(new URL('./worker.mjs',import.meta.url))],{input:JSON.stringify({source:m.source,input}),encoding:'utf8',timeout:1800,maxBuffer:100000,stdio:['pipe','pipe','pipe']});
 const r=JSON.parse(raw);if(!r.ok)return r;
 const o=r.output;if(!o||!['allow','block','unknown','not_applicable','advice'].includes(o.status)||!Array.isArray(o.reasons)||o.reasons.some(x=>typeof x!=='string')||!Array.isArray(o.alternatives)||o.alternatives.length>8)throw Error('Invalid policy result schema');
 if(Object.keys(o).some(k=>!['status','reasons','alternatives','analysis'].includes(k)))throw Error('Unexpected output field');
 return r;
}
export class PolicySession{
 #ledger=[]; #packets=[]; #contract=null; #contractIssues=[]; #nativeSchema=null; #lastReview=null;
 constructor(registry){Object.defineProperty(this,'module',{value:immutableSnapshot(validateModule(structuredClone(Object.values(registry.active)[0]))),enumerable:true});if(Object.keys(registry.active).length!==1)throw Error('One policy per branch experiment');}
 configure(schema){actionRoleSchema(schema);this.#nativeSchema=structuredClone(schema);}
 observeInitial(observation){this.#ledger.push({action:null,publicText:observation.publicText});}
 record(action,observation){this.#ledger.push({action:structuredClone(action),publicText:observation.publicText});}
 check(action,evidencePacket=null,budget=null){
  if(!this.#contract&&evidencePacket?.setup){
   const c=structuredClone(evidencePacket.setup),t=this.#ledger[0].publicText,issues=[];
   if(!Array.isArray(c.requirements)||!c.requirements.length)issues.push('No requirements');
   else {if(new Set(c.requirements.map(r=>r.id)).size!==c.requirements.length)issues.push('Duplicate requirement IDs');
    for(const r of c.requirements){
     if(!r.id||!r.description||!r.contractQuote||!t.includes(r.contractQuote))issues.push('Missing/non-public requirement quote: '+r.id);
     if(!['categorical','measurement','effect'].includes(r.kind)||!['episode','current'].includes(r.scope)||!['precondition','outcome','component'].includes(r.role))issues.push('Invalid condition type');
     if(r.temporal!==undefined&&!['state','ever'].includes(r.temporal))issues.push('Invalid temporal mode: '+r.id);
     if(r.temporal==='ever'&&(r.kind!=='effect'||r.scope!=='episode'))issues.push('Historical occurrence requires an episode-scoped effect: '+r.id);
     const w=r.appliesWhen;
     if(w!==undefined&&w!==null){
      const prop=this.#nativeSchema?.properties?.[w.field];
      const types=Array.isArray(prop?.type)?prop.type:[prop?.type];
      const typeMatches=types.includes(typeof w.value)||(types.includes('integer')&&Number.isInteger(w.value));
      if(!w||typeof w!=='object'||Object.keys(w).some(k=>!['field','operator','value','contractQuote'].includes(k))||!['eq','neq'].includes(w.operator)||!['string','number','boolean'].includes(typeof w.value)||!typeMatches)issues.push('Invalid public action branch: '+r.id);
      if(typeof w.contractQuote!=='string'||!w.contractQuote.trim()||!t.includes(w.contractQuote)||!String(w.value).trim()||!w.contractQuote.includes(String(w.value)))issues.push('Branch/value not grounded in initial public quote: '+r.id);
     }
    }}
   if(!Number.isInteger(c.resourceLimit)||c.resourceLimit<1||!c.budgetQuote||!t.includes(c.budgetQuote)||!new RegExp('(^|\\D)'+c.resourceLimit+'(\\D|$)').test(c.budgetQuote))issues.push('Resource limit not grounded in initial public quote');
   if(!Array.isArray(c.actions)||!c.actions.length||c.actions.some(a=>!a.action||!['observe','progress','confirm','refute'].includes(a.kind)||!Number.isFinite(a.cost)||a.cost<0))issues.push('Invalid action roles');
   try{c.actions=normalizeActionRoles(c.actions,this.#nativeSchema);}catch(e){issues.push(e.message);}
   issues.push(...validateLogicalContract(c,t,this.#nativeSchema));
   this.#contractIssues=issues;
   if(!issues.length)this.#contract=structuredClone(c);
  }
  const input={contract:this.#contract,contractHash:this.#contract?hash(this.#contract):null,contractIssues:this.#contractIssues,packets:structuredClone(this.#packets),evidencePacket,budget,publicText:this.#ledger.at(-1).publicText,action:structuredClone(action),history:structuredClone(this.#ledger)};
  const stamp={moduleId:this.module.moduleId,moduleHash:hash(this.module),actionHash:hash(action),snapshotHash:hash({ledger:this.#ledger,contract:this.#contract,packets:this.#packets})};
  let result;try{result={...stamp,...execute(this.module,input)}}catch(e){result={...stamp,ok:false,error:e.message}}
  if(result.ok)this.#lastReview={observation:this.#ledger.length-1,states:structuredClone(result.output.analysis?.states??[])};
  if(evidencePacket)this.#packets.push({step:this.#ledger.length-1,packet:structuredClone(evidencePacket)});
  return result;
 }
 run(input){if(Object.keys(input).some(k=>!['moduleId','proposedAction'].includes(k))||input.moduleId!==this.module.moduleId)return{ok:false,error:'Only moduleId and proposedAction; public evidence is host-held'};return this.check(input.proposedAction);}
 getContract(){return this.#contract?structuredClone(this.#contract):null;}
 getEvidenceStatus(){return this.#lastReview?{reviewedAtObservation:this.#lastReview.observation,states:structuredClone(this.#lastReview.states.map(({id,state,applicability,coverage,missingChildren})=>({id,state,applicability,coverage,missingChildren}))),note:'Prior computed review; refresh current-state evidence after a new action. History witnesses persist only for their bound subjects/predicates; visual truth is not independently verified.'}:null;}
 getBudgetStatus(hostSlots){
  const c=this.#contract;
  const spent=c?this.#ledger.slice(1).reduce((n,r)=>n+(c.actions.find(a=>Object.entries(a.action).every(([k,v])=>JSON.stringify(r.action?.[k])===JSON.stringify(v)))?.cost??1),0):null;
  return {hostSlots,publicResourceRemaining:c?Math.max(0,c.resourceLimit-spent):null,reservedDecisionSlots:1,note:'Use the public task resource limit as well as host slots. A progress action must preserve the final decision; host slots do not extend the task budget.'};
 }
}

export class AdviceBudget {
 #stepSeen=false; #seen=new Set(); #count=0;

 shouldReview(status,analysis={}){
  if(status!=='advice'||this.#stepSeen||this.#count>=2)return false;
  const missing=new Set(analysis.missing??[]);
  const signature=hash({contract:analysis.contractHash,role:analysis.role,missing:[...missing].sort(),states:(analysis.states??[]).filter(s=>missing.has(s.id)).map(s=>[s.id,s.state,s.applicability??'active']).sort()});
  if(this.#seen.has(signature))return false;
  this.#stepSeen=true;this.#seen.add(signature);this.#count++;return true;
 }
 nativeStepCompleted(){this.#stepSeen=false;}
}
