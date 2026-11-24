import {immutableSnapshot} from '../../../shared/immutable-snapshot.mjs';
import {createHash,randomUUID} from 'node:crypto';
import {evaluate,product,equal} from './program.mjs';
import {validateModule} from './registry.mjs';
export const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
export class VerifiedSession{
 #ledger=[];#receipts=new Map();#epoch=0;
 constructor(registry,adapter){const snapshot=immutableSnapshot(registry);for(const m of Object.values(snapshot.active))validateModule(m);Object.defineProperties(this,{registry:{value:snapshot,enumerable:true},adapter:{value:Object.freeze({...adapter})},sessionId:{value:randomUUID(),enumerable:true}});}
 observeInitial(observation){if(this.#ledger.length)throw Error('Already initialized');this.#ledger.push({observation:structuredClone(observation),action:null,index:-1});}
 record(action,observation){this.#ledger.push({action:structuredClone(action),observation:structuredClone(observation),index:this.#epoch});this.#epoch++;this.#receipts.clear();}
 snapshot(){return hash({session:this.sessionId,epoch:this.#epoch,ledger:this.#ledger});}
 publicLedger(){return structuredClone(this.#ledger);}
 run(input){
  if(!input||typeof input!=='object'||Array.isArray(input)||typeof input.moduleId!=='string'||!['run','commit'].includes(input.mode))return {ok:false,error:'Valid moduleId and mode=run or commit required'};
  if(Object.keys(input).some(k=>!['moduleId','mode','receiptId','hypotheses'].includes(k)))return {ok:false,error:'No caller-supplied evidence, predictions, pass labels or candidate substitutions accepted'};
  if(input.mode==='commit')throw Error('Commit is a host action, use consumeReceipt');
  const m=Object.hasOwn(this.registry.active,input.moduleId)?this.registry.active[input.moduleId]:null;if(!m)return{ok:false,error:'Unknown module'};
  const snapshot=this.snapshot(),stamp={moduleId:m.moduleId,version:m.version,moduleHash:hash(m),snapshot};
  try{
   const model=this.adapter.decode(this.publicLedger(),input.hypotheses);
   if(!model.applicable)return{ok:true,output:{...stamp,status:'not_applicable',reason:model.reason}};
   if(!model.complete||!model.records.length)return{ok:true,output:{...stamp,status:'unknown',reason:model.reason??'No complete observed feedback',evidenceRows:model.records.length}};

   const hypotheses=model.hypotheses??product(model.domains,m.limits.maxCandidates);
   if(hypotheses.length>m.limits.maxCandidates)throw Error('Candidate cap');
   if(!hypotheses.length)return{ok:true,output:{...stamp,status:'unknown',reason:'No eligible hypotheses remain in the supplied partial domain',evidenceRows:model.records.length}};
   const budget={remaining:m.limits.maxOperations},cache=new Map();
   const predict=(candidate,record)=>{
    const key=JSON.stringify([candidate,record.probe,record.index]);if(cache.has(key))return cache.get(key);

    const projected=evaluate(m.project,{candidate,index:record.index,params:model.params},{budget});
    const v=evaluate(m.predictor,{candidate:projected,probe:record.probe,index:record.index,params:model.params},{budget});cache.set(key,v);return v;
   };
   const returned=evaluate(m.program,{hypotheses,records:model.records,params:model.params},{budget,predict});
   if(!Array.isArray(returned))throw Error('Selection program must return a candidate array');
   const keys=new Set(hypotheses.map(hash));if(returned.some(c=>!keys.has(hash(c))))throw Error('Program returned candidate outside declared domain');
   const checked=hypotheses.map(candidate=>{const firstMismatch=model.records.find(r=>!equal(predict(candidate,r),r.actual));return{candidate,failures:firstMismatch?[firstMismatch.evidenceId]:[]};});
   const survivors=checked.filter(c=>!c.failures.length).map(c=>c.candidate);
   const expected=new Set(survivors.map(hash)),actual=new Set(returned.map(hash));
   if(actual.size!==returned.length||actual.size!==expected.size||[...actual].some(k=>!expected.has(k)))throw Error('Selection program disagrees with independent full evidence replay');
   if(!survivors.length)return{ok:true,output:{...stamp,status:'contradicted',candidateCount:hypotheses.length,survivorCount:0,evidenceRows:model.records.length,reason:'No candidate explains all public feedback under this model; check public rule binding, do not delete evidence',operations:m.limits.maxOperations-budget.remaining}};
   const candidate=survivors[0];
   const projected=evaluate(m.project,{candidate,index:this.#epoch,params:model.params},{budget});
   if(model.canCommit===false)return{ok:true,output:{...stamp,status:'consistent_but_action_unavailable',survivorCount:survivors.length,recommendedCandidate:projected,reason:'Public action contract does not currently allow this commitment; use a legal information-gathering action'}};
   const action=model.encode(projected);
   if(!equal(model.decodeAction(action),projected))throw Error('Action encoding does not match verified projection');
   const receiptId=randomUUID();
   const receipt={...stamp,receiptId,epoch:this.#epoch,modelHash:hash(model.identity),candidateHash:hash(candidate),actionHash:hash(action),candidate,action};this.#receipts.set(receiptId,structuredClone(receipt));
   return {ok:true,output:{...stamp,status:'consistent_under_public_model',candidateCount:hypotheses.length,survivorCount:survivors.length,completeDomain:Boolean(model.exhaustive),uniqueWithinDomain:survivors.length===1,provesCorrectAnswer:false,evidenceRows:model.records.length,checkedEvidenceIds:model.records.map(r=>r.evidenceId),recommendedCandidate:projected,proposedAction:action,receiptId,operations:m.limits.maxOperations-budget.remaining,modelSource:model.source,modelAssumptions:model.assumptions??[],predictorCannotReadActual:true}};
  }catch(e){return{ok:false,error:e.message,output:{...stamp,status:'unknown'}};}
 }
 consumeReceipt({moduleId,mode,receiptId,...extra}){
  if(mode!=='commit'||Object.keys(extra).length)throw Error('Commit accepts only moduleId, mode and receiptId; no replacement action');
  const r=this.#receipts.get(receiptId),m=this.registry.active[moduleId];if(!r||r.moduleId!==moduleId||!m||r.moduleHash!==hash(m)||r.snapshot!==this.snapshot())throw Error('Unknown, consumed or stale receipt');
  this.#receipts.delete(receiptId);return structuredClone(r);
 }
}
