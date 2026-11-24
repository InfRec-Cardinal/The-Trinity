import fs from 'node:fs';
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
import {CLASSES,catalog,validate,execute,validateRegistry,exact,identifier,hash,installModules} from './runtime.mjs';
const text=x=>typeof x==='string'&&x.trim().length>0&&x.length<=12000;
const readPath=(obj,path)=>path.split('/').slice(1).reduce((x,k)=>x?.[k.replace(/~1/g,'/').replace(/~0/g,'~')],obj);
function validateContext(c){
 if(!c||!['training','offline-reconstruction'].includes(c.mode)||!identifier(c.node)||!Number.isInteger(c.boundary)||c.boundary<1)throw Error('Invalid context');
 validateRegistry(c.inheritedRegistry);
 if(!Array.isArray(c.trajectories)||!c.trajectories.length)throw Error('Public node evidence required');
 const rounds=new Set();for(const t of c.trajectories){
  if(!Number.isInteger(t.round)||t.round<1||t.round>c.boundary||rounds.has(t.round)||!Array.isArray(t.events)||!t.events.length)throw Error('Invalid evidence round');rounds.add(t.round);
  const steps=new Set();for(const e of t.events){if(!Number.isInteger(e.step)||e.step<1||steps.has(e.step)||!text(e.publicText))throw Error('Invalid public event');steps.add(e.step);}
 }
 if(!rounds.has(c.boundary))throw Error('Missing boundary evidence');
}
export function buildNodeModuleGenerationRequest(context,{nativeHost,nativeModules}={}){
 validateContext(context);
 nativeModules??=context.inheritedRegistry.filter(m=>m.function.language==='javascript-module');
 installModules(context.inheritedRegistry,{nativeHost});installModules(nativeModules,{nativeHost});
 return {system:fs.readFileSync(new URL('../prompts/evolver.txt',import.meta.url),'utf8'),packet:{...structuredClone(context),templates:catalog(),...(nativeModules.length?{approvedNativeModules:structuredClone(nativeModules)}:{})},schema:nativeModules.length?nativeProposalSchema:proposalSchema};
}
const string={type:'string',minLength:1,maxLength:12000};
const moduleSchema={type:'object',additionalProperties:false,required:['moduleId','version','templateId','protocolClass','targetCapabilityNodeId','prompt','interface','function'],properties:{moduleId:string,version:{type:'integer',minimum:1},templateId:{enum:catalog().map(t=>t.templateId)},protocolClass:{enum:CLASSES},targetCapabilityNodeId:string,prompt:string,interface:{type:'object',additionalProperties:false,required:['required'],properties:{required:{type:'array',maxItems:64,uniqueItems:true,items:{type:'string'}}}},function:{type:'object',additionalProperties:false,required:['language','source'],properties:{language:{const:'javascript'},source:{type:'string',maxLength:262144}}}}};
const nativeModuleSchema=structuredClone(moduleSchema);
nativeModuleSchema.required.push('hostCapabilities');
nativeModuleSchema.properties.hostCapabilities={type:'array',uniqueItems:true,items:{type:'string'}};
nativeModuleSchema.properties.interface.properties.inputModes={type:'object',additionalProperties:{type:'object',additionalProperties:false,required:['required'],properties:{required:moduleSchema.properties.interface.properties.required}}};
nativeModuleSchema.properties.interface.properties.defaultInputMode=string;
nativeModuleSchema.properties.function={type:'object',additionalProperties:false,required:['language','source','entry','sha256'],properties:{language:{const:'javascript-module'},source:{type:'string',maxLength:1048576},entry:string,sha256:{type:'string',pattern:'^[a-f0-9]{64}$'}}};
const exampleSchema={type:'object',additionalProperties:false,required:['kind','input','expected'],properties:{kind:{enum:['synthetic','observed']},input:{type:'object'},expected:{}}};
export const proposalSchema={type:'object',additionalProperties:false,required:['decision','diagnosis','limitations','updates'],properties:{decision:{const:'propose'},diagnosis:string,limitations:{type:'array',minItems:1,maxItems:8,items:string},updates:{type:'array',minItems:1,maxItems:1,items:{type:'object',additionalProperties:false,required:['action','baseVersion','module','rationale','evidenceRefs','workedExamples'],properties:{action:{enum:['install','revise','fork']},baseVersion:{type:['integer','null'],minimum:1},module:moduleSchema,rationale:string,evidenceRefs:{type:'array',minItems:1,maxItems:12,items:{type:'object',additionalProperties:false,required:['round','step','quote'],properties:{episodeId:{type:'string',minLength:1},round:{type:'integer',minimum:0},step:{type:'integer',minimum:1},quote:string}}},workedExamples:{type:'array',minItems:2,maxItems:6,items:exampleSchema}}}}}};
export const nativeProposalSchema=structuredClone(proposalSchema);
nativeProposalSchema.properties.updates.items.properties.module={oneOf:[moduleSchema,nativeModuleSchema]};
class HostTestFailure extends Error {
 constructor(code) {
  super(code === 'host_test_mismatch' ? 'Host regression mismatch' : 'Private host test execution failed');
  this.code = code;
 }
}
async function checkHostTests(module, hostTests, nativeHost) {
 let tests;
 try {
  tests = hostTests[module.moduleId] ?? [];
  if (!Array.isArray(tests)) throw new Error();
 } catch {throw new HostTestFailure('host_test_execution_failed');}
 for (const test of tests) {
  let actual;
  try {actual = await execute(module, test.input,{nativeHost});}
  catch {throw new HostTestFailure('host_test_execution_failed');}
  try {
   if (!isDeepStrictEqual(actual, test.expected)) throw new Error();
  } catch {throw new HostTestFailure('host_test_mismatch');}
 }
 return tests.length;
}
export async function applyNodeModuleGeneration(context,proposal,{hostTests={},nativeHost}={}){
 validateContext(context);installModules(context.inheritedRegistry,{nativeHost});exact(proposal,['decision','diagnosis','limitations','updates'],'proposal');
 if(proposal.decision!=='propose'||!text(proposal.diagnosis)||!Array.isArray(proposal.limitations)||!proposal.limitations.length||proposal.limitations.length>8||proposal.limitations.some(x=>!text(x))||!Array.isArray(proposal.updates)||proposal.updates.length!==1)throw Error('Invalid proposal');
 const active=new Map(context.inheritedRegistry.map(m=>[m.moduleId,structuredClone(m)])),updated=new Set(),audit=[];
 for(const u of proposal.updates){
  exact(u,['action','baseVersion','module','rationale','evidenceRefs','workedExamples'],'update');const m=validate(u.module);installModules([m],{nativeHost});
  if(updated.has(m.moduleId)||!text(u.rationale))throw Error('Duplicate update or missing rationale');updated.add(m.moduleId);
  const old=active.get(m.moduleId);
  if(u.action==='install'){
   if(old||u.baseVersion!==null||m.version!==1||m.targetCapabilityNodeId!==context.node)throw Error('Invalid install version/node');
   if([...active.values()].some(x=>hash(x.function.source)===hash(m.function.source)))throw Error('Renamed duplicate function');
  } else if(u.action==='revise'){
   if(!old||old.targetCapabilityNodeId!==context.node||u.baseVersion!==old.version||m.version!==old.version+1||m.targetCapabilityNodeId!==old.targetCapabilityNodeId||m.protocolClass!==old.protocolClass)throw Error('Invalid revision lineage/version');
   if(old.prompt===m.prompt&&old.function.source===m.function.source&&JSON.stringify(old.interface)===JSON.stringify(m.interface))throw Error('No-op revision');
  }else if(u.action==='fork'){
   if(!old||old.targetCapabilityNodeId===context.node||m.targetCapabilityNodeId!==context.node||u.baseVersion!==old.version||m.version!==old.version+1||m.protocolClass!==old.protocolClass)throw Error('Invalid local fork');
   if(old.prompt===m.prompt&&old.function.source===m.function.source&&JSON.stringify(old.interface)===JSON.stringify(m.interface))throw Error('No-op fork');
  }else throw Error('Unknown update action');
  if(!Array.isArray(u.evidenceRefs)||!u.evidenceRefs.length||u.evidenceRefs.length>12)throw Error('Evidence references required');
  for(const ref of u.evidenceRefs){exact(ref,ref.episodeId===undefined?['round','step','quote']:['round','step','quote','episodeId'],'evidence reference');const source=ref.episodeId===undefined?context.trajectories.find(t=>t.round===ref.round):ref.round===0?context.feedback?.find(t=>t.episodeId===ref.episodeId):null;const event=source?.events.find(e=>e.step===ref.step);if(!text(ref.quote)||!event?.publicText.includes(ref.quote))throw Error('Unknown or mismatched public evidence');}
  if(!Array.isArray(u.workedExamples)||u.workedExamples.length<2||u.workedExamples.length>6||new Set(u.workedExamples.map(e=>JSON.stringify(e.input))).size!==u.workedExamples.length)throw Error('Need 2-6 distinct examples');
  const outputs=[];
  for(const e of u.workedExamples){exact(e,['kind','input','expected'],'worked example');if(!['synthetic','observed'].includes(e.kind))throw Error('Example kind required');
   if(e.kind==='observed'&&![...context.trajectories,...(context.feedback??[])].some(t=>t.events.some(v=>JSON.stringify(v.moduleInput)===JSON.stringify(e.input))))throw Error('Observed example not found in node evidence');
   const actual=await execute(m,e.input,{nativeHost});assert.deepEqual(actual,e.expected,'Executable example mismatch');outputs.push(actual);
  }
  const policy=context.validationPolicies?.[m.moduleId];
  if(m.protocolClass==='loop'&&!policy)throw Error('Loop module requires host decision policy');
  if(policy){if(typeof policy.path!=='string'||!policy.path.startsWith('/')||!Array.isArray(policy.allowValues)||!policy.allowValues.length)throw Error('Invalid host decision policy');
   const values=outputs.map(o=>readPath(o,policy.path));if(values.some(v=>v===undefined))throw Error('Decision field absent');
   const allowed=values.map(v=>policy.allowValues.some(a=>JSON.stringify(a)===JSON.stringify(v)));
   if(!allowed.some(Boolean)||allowed.every(Boolean))throw Error('Examples must permit and withhold');
  }
  const hostTestCount = await checkHostTests(m, hostTests,nativeHost);
  active.set(m.moduleId,structuredClone(m));audit.push({moduleId:m.moduleId,action:u.action,predecessorDigest:old?hash(JSON.stringify(old)):null,ownerNode:context.node,promptChanged:old?old.prompt!==m.prompt:true,functionChanged:old?old.function.source!==m.function.source:true,functionSha256:hash(m.function.source),evidenceMode:context.mode,examples:u.workedExamples.length,hostTests:hostTestCount});
 }
 return {registry:[...active.values()],audit,promoted:false};
}

export async function retainNodeModuleGeneration(context, proposal, options = {}) {
 validateContext(context);
 if(!Array.isArray(proposal?.updates)||proposal.updates.length!==1)throw Error('Exactly one module update required');
 const module=validate(proposal.updates[0].module);
 if(module.targetCapabilityNodeId!==context.node)throw Error('Module must belong to the current node');
 try{return {...await applyNodeModuleGeneration(context,proposal,options),accepted:true};}
 catch(error){
  return {registry:structuredClone(context.inheritedRegistry),accepted:false,promoted:false,
   audit:[{moduleId:module.moduleId,status:'rejected',message:String(error.message),...(error instanceof HostTestFailure ? {code:error.code,stage:'private_host_test'} : {}),ownerNode:context.node,retained:false}]};
 }
}
