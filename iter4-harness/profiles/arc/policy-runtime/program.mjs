import {immutableSnapshot} from '../../../shared/immutable-snapshot.mjs';
import {fileURLToPath} from 'node:url';
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
 #ledger=[];
 constructor(registry){Object.defineProperty(this,'module',{value:immutableSnapshot(validateModule(structuredClone(Object.values(registry.active)[0]))),enumerable:true});if(Object.keys(registry.active).length!==1)throw Error('One policy per branch experiment');}
 observeInitial(observation){this.#ledger.push({action:null,publicText:observation.publicText});}
 record(action,observation){this.#ledger.push({action:structuredClone(action),publicText:observation.publicText});}
 check(action){
  const input={publicText:this.#ledger.at(-1).publicText,action:structuredClone(action),history:structuredClone(this.#ledger)};
  const stamp={moduleId:this.module.moduleId,moduleHash:hash(this.module),actionHash:hash(action),snapshotHash:hash(this.#ledger)};
  try{return{...stamp,...execute(this.module,input)}}catch(e){return{...stamp,ok:false,error:e.message}}
 }
 preview(){
  const input={publicText:this.#ledger.at(-1).publicText,action:null,history:structuredClone(this.#ledger)};
  try{return{moduleId:this.module.moduleId,moduleHash:hash(this.module),snapshotHash:hash(this.#ledger),phase:"before_proposal",...execute(this.module,input)}}catch(e){return{ok:false,error:e.message}}
 }
 run(input){if(Object.keys(input).some(k=>!['moduleId','proposedAction'].includes(k))||input.moduleId!==this.module.moduleId)return{ok:false,error:'Only moduleId and proposedAction; public evidence is host-held'};return this.check(input.proposedAction);}
}

export class AdviceBudget {
 #seen=false;
 shouldReview(status){if(status!=='advice'||this.#seen)return false;this.#seen=true;return true;}
 nativeStepCompleted(){this.#seen=false;}
}
