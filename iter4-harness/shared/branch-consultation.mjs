import {capabilityNotice} from './capability-scope.mjs';
import {branchInputSchema} from './branch-input-contract.mjs';
import {perceptionInputSchema} from './perception-input-contract.mjs';
const contracts=structuredClone({'public-object-v1':{type:'object'},'perception-v1':perceptionInputSchema,'evidence-route-v1':branchInputSchema});
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
function validate(value,schema,path,errors){
 const fail=code=>errors.push({path,code});
 if(schema.anyOf){if(!schema.anyOf.some(s=>{const es=[];validate(value,s,path,es);return !es.length;}))fail('invalid_type');return;}
 const types=Array.isArray(schema.type)?schema.type:[schema.type];
 if(!types.some(t=>t==='null'?value===null:t==='object'?object(value):t==='array'?Array.isArray(value):t==='integer'?Number.isSafeInteger(value):typeof value===t)){fail('invalid_type');return;}
 if(value===null)return;
 if(Array.isArray(value)){if(value.length>(schema.maxItems??Infinity)){fail('too_many_items');return;}if(schema.items)value.forEach((v,i)=>validate(v,schema.items,`${path}[${i}]`,errors));}
 else if(object(value)){
  for(const k of schema.required??[])if(!Object.hasOwn(value,k))errors.push({path:path+'.'+k,code:'missing_field'});
  for(const [k,v] of Object.entries(value)){
   if(schema.properties?.[k])validate(v,schema.properties[k],path+'.'+k,errors);
   else if(schema.additionalProperties===false)errors.push({path:path+'.'+k,code:'unknown_field'});
   else if(object(schema.additionalProperties))validate(v,schema.additionalProperties,path+'.'+k,errors);
  }
 }else if(typeof value==='number'){if(!Number.isFinite(value)||value<(schema.minimum??-Infinity))fail('invalid_number');}
 else if(typeof value==='string'){if(value.trim().length<(schema.minLength??0))fail('empty_string');if(schema.pattern&&!new RegExp(schema.pattern).test(value))fail('invalid_source');}
}
export function validatePublicInput(row,input,step,remaining){
 const errors=[];
 if(!Number.isSafeInteger(step)||step<0||!Number.isSafeInteger(remaining)||remaining<0)return [{path:'host',code:'invalid_step_or_budget'}];
 if(!object(input))return [{path:'input',code:'invalid_type'}];
 if(JSON.stringify(input).length>40000)return [{path:'input',code:'input_too_large'}];
 if(Object.hasOwn(input,'mode')&&(typeof input.mode!=='string'||!input.mode.length))return [{path:'input.mode',code:'invalid_type'}];
 const mode=input.mode??row.defaultInputMode;
 if(row.inputModes&&(typeof mode!=='string'||!Object.hasOwn(row.inputModes,mode)))return [{path:'input.mode',code:'unknown_mode'}];
 const modeContract=mode===undefined?null:row.inputModes?.[mode];
 const schema=contracts[modeContract?.publicInputContract??row.publicInputContract??'public-object-v1'];
 if(!schema)return [{path:'module',code:'unknown_public_input_contract'}];
 validate(input,schema,'input',errors);
 for(const key of modeContract?.required??row.required??[])if(!Object.hasOwn(input,key)&&!errors.some(e=>e.path==='input.'+key))errors.push({path:'input.'+key,code:'missing_module_field'});
 if(Object.hasOwn(input,'budget')&&(!Number.isSafeInteger(input.budget)||input.budget<0||input.budget>remaining))errors.push({path:'input.budget',code:'invalid_remaining_budget'});
 for(const key of ['maxVisits','maxStates'])if(Object.hasOwn(input,key)&&(!Number.isSafeInteger(input[key])||input[key]<=0))errors.push({path:'input.'+key,code:'invalid_search_bound'});
 const walk=(value,path,depth)=>{
  if(depth>40){errors.push({path,code:'input_too_deep'});return;}
  if(!value||typeof value!=='object')return;
  for(const [k,v] of Object.entries(value)){
   if((k==='source'||k==='evidenceId')&&typeof v==='string'&&/^obs-\d+$/.test(v)){
    if(!Number.isSafeInteger(Number(v.slice(4)))||Number(v.slice(4))>step)errors.push({path:path+'.'+k,code:'future_observation'});
   }else walk(v,path+'.'+k,depth+1);
  }
 };
 walk(input,'input',0);return errors;
}
export function createBranchConsultation(scope,{excludeIds=[],toolName='consult_capability_path'}={}){
 const entries=Object.freeze(scope.activeBranch.filter(row=>row.bindingId!=='bounded_action_policy'&&!excludeIds.includes(row.moduleId)));
 const branchTool={name:toolName,description:[
  'Optional deterministic helpers selected by the prerequisite capability path. No world action or independent vision. Use only public facts matching the selected module contract. Never invent a model or evidence to force a helper call. Observation references obs-N must already exist. Other source identifiers must match the selected module contract. Unresolved facts remain unknown.',
  ...entries.map(row=>`${row.moduleId}: ${row.title}. Required inputs: ${JSON.stringify(row.required)}. Modes: ${JSON.stringify(row.inputModes??{})}. Input contract: ${JSON.stringify(contracts[row.publicInputContract??'public-object-v1'])}. ${row.publicInputHint??''}`)
 ].join('\n'),input_schema:{type:'object',required:['moduleId','input'],additionalProperties:false,properties:{moduleId:{type:'string',enum:entries.map(row=>row.moduleId)},input:{type:'object',additionalProperties:true}}}};
 const consultBranch=async(args,step,remaining)=>{
  try{
   args=JSON.parse(JSON.stringify(args));
   if(!object(args)||Object.keys(args).some(k=>!['moduleId','input'].includes(k)))throw Error('Only moduleId and input are accepted');
   const row=entries.find(row=>row.moduleId===args.moduleId);if(!row)throw Error('Module outside the selected auxiliary path');
   const contractErrors=validatePublicInput(row,args.input,step,remaining);
   if(contractErrors.length)return {ok:false,moduleId:row.moduleId,error:'invalid_module_input',contractErrors,noWorldActionExecuted:true};
   const output=await scope.invoke(row.moduleId,{...args.input,maxStates:Math.min(args.input.maxStates??10000,10000),maxVisits:Math.min(args.input.maxVisits??10000,10000)});
   if(output?.candidates?.length>40){output.candidates=output.candidates.slice(0,40);output.candidatesTruncated=true;output.candidateListNotice='First 40 displayed; candidateCount and recommendation use the full computed set.';}
   return {ok:true,moduleId:row.moduleId,node:row.node,output,noWorldActionExecuted:true,scope:'Public source references checked; semantic and visual claims are not independently verified.'};
  }catch(error){return {ok:false,moduleId:args?.moduleId,error:error.message,noWorldActionExecuted:true};}
 };
 return {entries,branchTool,branchNotice:capabilityNotice(scope,entries.map(row=>row.moduleId)),consultBranch};
}
