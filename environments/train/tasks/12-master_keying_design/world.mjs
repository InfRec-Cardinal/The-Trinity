                                                                                            
                                                                                                 
                                                                                                                          
import { createHash } from 'node:crypto';
import { Raster } from '../../lib/raster.mjs';
const canonical = value => Array.isArray(value) ? `[${value.map(v => canonical(v) ?? 'null').join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`
  : JSON.stringify(value);
export const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
export const contentHash = value => sha256(canonical(value));
export const masterKeyingPinModel={cutMinimum:0,cutMaximum:9,shearPlane:14,keyLiftOffset:12,bottomPinOffset:2,totalStackLength:24,housingHeight:40};
const vectorOK=(v,n)=>Array.isArray(v)&&v.length===n&&v.every(d=>Number.isSafeInteger(d)&&d>=0&&d<=9);
const adjacentOK=(v,limit)=>v.every((d,i)=>i===0||Math.abs(d-v[i-1])<=limit);
export function deriveMasterKeyingChamber(cuts){
  const acceptedCuts=[...new Set(cuts)].sort((a,b)=>a-b);
  if(!acceptedCuts.length)return {acceptedCuts,constructed:false,bottomPinLength:null,masterWaferLengths:[],driverPinLength:null,interfaces:[]};
  if(acceptedCuts.some(d=>!Number.isSafeInteger(d)||d<0||d>9))throw new Error('Invalid pin cut depth');
  const bottomPinLength=2+acceptedCuts[0],masterWaferLengths=acceptedCuts.slice(1).map((d,i)=>d-acceptedCuts[i]),driverPinLength=24-(2+acceptedCuts.at(-1));
  let boundary=bottomPinLength;const interfaces=[boundary];for(const wafer of masterWaferLengths){boundary+=wafer;interfaces.push(boundary);}
  return {acceptedCuts,constructed:true,bottomPinLength,masterWaferLengths,driverPinLength,interfaces};
}
export function masterKeyingLockOperates(pinning,bitting){
  if(!vectorOK(bitting,pinning.length))return false;
  return pinning.every((chamber,i)=>chamber.constructed&&chamber.interfaces.some(boundary=>boundary+(12-bitting[i])===14));
}
export function countManufacturableMasterKeyingBittings(sets,limit){
  let counts=new Map(sets[0].map(d=>[d,1]));
  for(const set of sets.slice(1)){const next=new Map();for(const d of set){let count=0;for(const [previous,n] of counts)if(Math.abs(d-previous)<=limit)count+=n;next.set(d,count);}counts=next;}
  return [...counts.values()].reduce((n,c)=>n+c,0);
}
export function inspectMasterKeying(instance,bittings){
  const requiredFailures=[],forbiddenOpenings=[],missingBittings=[],adjacentCutViolations=[],duplicateBittings=[],shearLimitViolations=[],locks=[],seen=new Map();
  for(const key of instance.keys){const v=bittings[key.id];if(!vectorOK(v,instance.chambers)){missingBittings.push(key.id);continue;}
    if(!adjacentOK(v,instance.maxAdjacentDifference))adjacentCutViolations.push({key:key.id,bitting:v});
    const label=v.join(',');if(seen.has(label))duplicateBittings.push({key:key.id,duplicates:seen.get(label)});else seen.set(label,key.id);
  }
  let unintendedBittings=0,unintendedManufacturableBittings=0;
  for(const lock of instance.locks){
    const required=lock.requiredKeys.map(id=>bittings[id]).filter(v=>vectorOK(v,instance.chambers)),pinning=Array.from({length:instance.chambers},(_,i)=>deriveMasterKeyingChamber(required.map(v=>v[i])));
    for(const [i,chamber] of pinning.entries())if(chamber.acceptedCuts.length>instance.maxShearPoints)shearLimitViolations.push({lock:lock.id,chamber:i+1,shearPoints:chamber.acceptedCuts.length,maximum:instance.maxShearPoints});
    for(const key of instance.keys){const opens=masterKeyingLockOperates(pinning,bittings[key.id]),requiredAccess=lock.requiredKeys.includes(key.id);if(requiredAccess&&!opens)requiredFailures.push({key:key.id,lock:lock.id});else if(!requiredAccess&&opens)forbiddenOpenings.push({key:key.id,lock:lock.id});}
    const acceptedShearCombinations=pinning.reduce((n,c)=>n*c.acceptedCuts.length,1),acceptedManufacturableBittings=countManufacturableMasterKeyingBittings(pinning.map(c=>c.acceptedCuts),instance.maxAdjacentDifference);
    const intended=new Set(required.map(v=>v.join(','))),intendedManufacturable=new Set(required.filter(v=>adjacentOK(v,instance.maxAdjacentDifference)).map(v=>v.join(',')));
    const unintendedAcceptedBittings=acceptedShearCombinations-intended.size,unintendedManufacturable=acceptedManufacturableBittings-intendedManufacturable.size;
    unintendedBittings+=unintendedAcceptedBittings;unintendedManufacturableBittings+=unintendedManufacturable;
    locks.push({lock:lock.id,pinning,acceptedShearCombinations,acceptedManufacturableBittings,intendedDistinctBittings:intended.size,unintendedAcceptedBittings,unintendedManufacturableBittings:unintendedManufacturable});
  }
  return {exactAccessTable:requiredFailures.length===0&&forbiddenOpenings.length===0,valid:![requiredFailures,forbiddenOpenings,missingBittings,adjacentCutViolations,duplicateBittings,shearLimitViolations].some(v=>v.length),requiredFailures,forbiddenOpenings,missingBittings,adjacentCutViolations,duplicateBittings,shearLimitViolations,unintendedBittings,unintendedManufacturableBittings,locks};
}
export function normalizeMasterKeyingAction(input){
  if(!input||typeof input!=='object'||Array.isArray(input))return null;const keys=Object.keys(input).sort().join(',');
  if(['check','submit'].includes(input.action)&&keys==='action')return {action:input.action};
  if(input.action==='set_bitting'&&keys==='action,bitting,key'&&typeof input.key==='string'&&/^K\d{2}$/.test(input.key)&&Array.isArray(input.bitting)&&[5,6].includes(input.bitting.length)&&input.bitting.every(d=>Number.isSafeInteger(d)&&d>=0&&d<=9))return {action:'set_bitting',key:input.key,bitting:input.bitting.slice()};return null;
}
export function createMasterKeying(instance){
  const state={step:0,bittings:Object.fromEntries(instance.keys.map(k=>[k.id,null])),checksUsed:0,revision:0,lastCheck:null,lastCheckRevision:null,lastKey:null,feedback:'Assign all key cuts to reproduce the public access table.',submitted:false,ended:false,outcome:null,reason:null,evaluation:null};
  const evaluate=()=>inspectMasterKeying(instance,state.bittings);
  const end=reason=>{state.ended=true;state.reason=reason;state.evaluation=evaluate();state.outcome=state.submitted&&state.evaluation.valid?'success':'failure';};
  return {state,step(input){const action=normalizeMasterKeyingAction(input);if(!action)throw new Error('Malformed master-keying action');if(state.ended)throw new Error('Master-keying episode ended');state.step++;
    if(action.action==='set_bitting'){if(!Object.hasOwn(state.bittings,action.key))state.feedback='Requested key is outside this access table.';else if(action.bitting.length!==instance.chambers)state.feedback=`This model requires exactly${instance.chambers} cuts.`;else{state.bittings[action.key]=action.bitting.slice();state.revision++;state.lastKey=action.key;state.feedback='Key bitting saved. Use check for current violations.';}}
    else if(action.action==='check'){state.checksUsed++;state.lastCheck=evaluate();state.lastCheckRevision=state.revision;state.feedback='Every supplied key was tested against every derived mechanical lock.';}
    else{state.submitted=true;end('submitted');state.lastCheck=state.evaluation;state.lastCheckRevision=state.revision;state.feedback='Current bittings submitted.';}
    if(!state.ended&&state.step>=80)end('action_budget_without_submission');},
    publicView(){return {text:JSON.stringify({task:'Assign cut depths to reproduce every required and forbidden key-lock pair. check derives pinning; submit ends. Unlisted ghost-key count is efficiency, not an additional success constraint.',model:{chambers:instance.chambers,cuts:[0,9],maximumAdjacentCutDifference:instance.maxAdjacentDifference,maximumShearPointsPerChamber:instance.maxShearPoints,dimensions:masterKeyingPinModel,mechanism:'Cut d lifts12-d. A bottom-pin/master-wafer interface must align with shear plane14 in every chamber.'},keys:instance.keys.map(k=>k.id),locks:instance.locks.map(l=>l.id),accessTable:instance.keys.map(k=>({key:k.id,required:instance.locks.filter(l=>l.requiredKeys.includes(k.id)).map(l=>l.id),forbidden:instance.locks.filter(l=>!l.requiredKeys.includes(k.id)).map(l=>l.id)})),bittings:state.bittings,check:state.lastCheck,checkIsCurrent:state.lastCheckRevision===state.revision,checksUsed:state.checksUsed,remainingActions:80-state.step,feedback:state.feedback}),terminal:{ended:state.ended,outcome:state.outcome,reason:state.reason,score:state.evaluation?.unintendedBittings??null,...(state.evaluation?{evaluation:{...state.evaluation,actionsUsed:state.step,checksUsed:state.checksUsed,submitted:state.submitted,securityCountIncludesAllShearCombinations:true}}:{})}};},
    render(){const r=new Raster(640,480);r.text('MASTER KEYING ACCESS TABLE',18,16,[40,54,65],3);r.text(`ACTIONS LEFT ${80-state.step} CHECKS ${state.checksUsed}`,18,42,[40,54,65],2);
      const cell=Math.min(14,Math.floor(350/instance.locks.length)),row=Math.min(16,Math.floor(340/instance.keys.length));for(const [i,k] of instance.keys.entries()){r.text(k.id,12,88+i*row,[40,54,65],1);for(const [j,l] of instance.locks.entries())r.rect(45+j*cell,86+i*row,cell-1,row-1,l.requiredKeys.includes(k.id)?[63,160,118]:[224,184,179]);}
      r.text('GREEN REQUIRED',18,448,[45,130,96],2);r.text('RED FORBIDDEN',218,448,[180,92,86],2);const key=state.lastKey??instance.keys[0].id,bitting=state.bittings[key];r.text(`KEY ${key}`,425,86,[40,54,65],3);
      for(let i=0;i<instance.chambers;i++){r.rect(426+i*29,155,24,100,[207,169,69]);if(bitting)r.rect(426+i*29,155,24,bitting[i]*8,[245,248,251]);r.text(bitting?bitting[i]:'?',432+i*29,274,[40,54,65],2);}r.text('CUTS 0 TO 9',425,318,[40,54,65],2);return r;}};
}

export const masterKeyingDefinition={taskId:'master_keying_design',maxSteps:80,playerRGB:false,create:createMasterKeying,normalizeAction:normalizeMasterKeyingAction,
  actionContract:'Design mechanical pin-tumbler master keys. set_bitting key Kxx and5/6 integer cuts0–9; check derives each chamber bottom pin/master wafers/driver and reports required failures, forbidden openings, duplicate keys, adjacent-cut and2/3shear-point violations; submit ends. Reproduce the full public access graph with distinct keys satisfying the stated MAC and shear cap.80actions. Ghost-key counts measure efficiency only.',
  parameters:{type:'object',additionalProperties:false,properties:{action:{type:'string',enum:['set_bitting','check','submit']},key:{type:'string',pattern:'^K[0-9]{2}$'},bitting:{type:'array',minItems:5,maxItems:6,items:{type:'integer',minimum:0,maximum:9}}},required:['action']}};
