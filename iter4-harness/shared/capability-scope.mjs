import {catalog,modulesForPath,invoke} from '../module-harness/harness.mjs';
const nodes=new Set(catalog.nodes.map(row=>row.node));
const profiles={embodied:null,arc:['d','d-a'],capx:['d'],buildarena:['c-d']};
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
export function capabilityPath(node){
 if(typeof node!=='string'||!nodes.has(node))throw Error('Unsupported capability node: '+node);
 const parts=node.split('-'),path=parts.map((_,i)=>parts.slice(0,i+1).join('-'));
 if(path.some(n=>!nodes.has(n)))throw Error('Missing prerequisite capability node');
 return Object.freeze(path);
}
export function createCapabilityScope(node,{profile='embodied'}={}){
 if(!Object.hasOwn(profiles,profile))throw Error('Unsupported capability profile');
 if(profiles[profile]&&!profiles[profile].includes(node))throw Error(profile.toUpperCase()+' node must be '+profiles[profile].join(' or '));
 const path=capabilityPath(node),activeBranch=freeze(structuredClone(modulesForPath(path))),byId=new Map(activeBranch.map(row=>[row.moduleId,row]));
 const has=moduleId=>byId.has(moduleId);
 const requireModule=moduleId=>{const row=byId.get(moduleId);if(!row)throw Error('Module outside selected capability path: '+moduleId);return row;};
 const run=(moduleId,operation)=>{requireModule(moduleId);return operation();};
 const bindPolicy=(registry,{ownerId}={})=>{
  if(!registry)return null;
  const entries=Object.entries(registry.active??{});
  if(!entries.length)throw Error('Empty policy registry');
  for(const [id,policy] of entries){
   if(!policy||typeof policy!=='object'||Array.isArray(policy)||id!==policy.moduleId)throw Error('Policy identity mismatch');
   const identity=policy.catalogModuleId??id;
   if(ownerId!=null&&ownerId!==identity)throw Error('Policy catalog identity mismatch');
   const row=requireModule(identity);
   if(policy.targetCapabilityNodeId!==row.node)throw Error('Policy capability path mismatch');
   if(policy.version!==(row.version??1))throw Error('Policy revision mismatch');
  }
  return freeze(structuredClone(registry));
 };
 return Object.freeze({node,profile,path,activeBranch,moduleIds:Object.freeze([...byId.keys()]),has,require:requireModule,run,bindPolicy,
  invoke:(moduleId,input)=>run(moduleId,()=>invoke(moduleId,input))});
}
export function supportsEvidenceProtocol(schema){
 return ['kind','action','type','op'].some(k=>(schema?.required??[]).includes(k)&&Array.isArray(schema?.properties?.[k]?.enum)&&schema.properties[k].enum.length>0);
}
export function resolvePolicy(scope,registry,{nativeSchema,ownerId}={}){
 if(!registry)return {registry:null,automaticPolicyModules:[],automaticPolicyNote:''};
 const bound=scope.bindPolicy(registry,{ownerId});
 if(bound.evidenceProtocol&&!supportsEvidenceProtocol(nativeSchema))return {registry:null,automaticPolicyModules:[],automaticPolicyNote:'Automatic commitment policy is inapplicable: the public native schema has no required action-kind enum. It is not executed. The other prerequisite helpers remain available; never invent a native discriminator.'};
 return {registry:bound,automaticPolicyModules:Object.keys(bound.active),automaticPolicyNote:''};
}
export function capabilityNotice(scope,helperIds,automaticIds=[]){
 helperIds.forEach(scope.require);automaticIds.forEach(scope.require);
 return `Active capability path ${scope.path.join(' -> ')} selects ${scope.moduleIds.length} registered modules. ${helperIds.length} optional callable modules plus ${automaticIds.length} automatic policies. Only modules matching the public input contract should be used. Tool availability does not imply tool use or benefit. No helper establishes hidden facts or overrides native completion.`;
}
