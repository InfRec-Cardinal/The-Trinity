import fs from 'node:fs';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
import {createHash} from 'node:crypto';

export const CLASSES=['perception','memory','inference','planning','orchestration','loop'];
const templates=JSON.parse(fs.readFileSync(new URL('../config/templates.json',import.meta.url),'utf8'));
const byId=new Map(templates.map(t=>[t.templateId,t]));
export const catalog=()=>structuredClone(templates);
export const hash=s=>createHash('sha256').update(s).digest('hex');

const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
export function exact(value,keys,label){if(!object(value)||Object.keys(value).some(k=>!keys.includes(k))||keys.some(k=>!Object.hasOwn(value,k)))throw Error('Invalid '+label+' keys');}
export function identifier(x){return typeof x==='string'&&/^[a-zA-Z][a-zA-Z0-9_-]{0,159}$/.test(x)&&!['constructor','prototype','__proto__'].includes(x);}
export function validate(m){
 exact(m,['moduleId','version','templateId','protocolClass','targetCapabilityNodeId','prompt','interface','function'],'module');
 if(!identifier(m.moduleId)||!identifier(m.targetCapabilityNodeId)||!Number.isInteger(m.version)||m.version<1)throw Error('Invalid identity/version');
 const t=byId.get(m.templateId);if(!t||m.protocolClass!==t.protocolClass)throw Error('Template/class mismatch');
 if(typeof m.prompt!=='string'||!m.prompt.trim()||m.prompt.length>12000)throw Error('Invalid prompt');
 exact(m.interface,['required'],'interface');
 if(!Array.isArray(m.interface.required)||m.interface.required.length>64||m.interface.required.some(k=>!identifier(k))||new Set(m.interface.required).size!==m.interface.required.length)throw Error('Invalid required inputs');
 exact(m.function,['language','source'],'function');
 const src=m.function.source;
 if(m.function.language!=='javascript'||typeof src!=='string'||src.length>262144||!/^\s*function\s*(?:[a-zA-Z_$][\w$]*)?\s*\(/.test(src))throw Error('Expected a bounded synchronous JavaScript function expression');
 new vm.Script('('+src+')');
 return m;
}
export function instantiate(templateId,{moduleId,targetCapabilityNodeId}){
 const t=byId.get(templateId);if(!t)throw Error('Unknown template');
 return validate({moduleId,version:1,templateId,protocolClass:t.protocolClass,targetCapabilityNodeId,prompt:t.prompt,interface:structuredClone(t.interface),function:structuredClone(t.function)});
}
export async function execute(module,input){
 validate(module);if(!object(input))throw Error('Public input object required');
 for(const k of module.interface.required)if(!Object.hasOwn(input,k))throw Error('Missing public input: '+k);
 const data=JSON.stringify({source:module.function.source,input});
 if(Buffer.byteLength(data)>2097152)throw Error('Input cap');
 return new Promise((resolve,reject)=>{
  const child=spawn(process.execPath,['--max-old-space-size=96',fileURLToPath(new URL('./worker.mjs',import.meta.url))],{stdio:['pipe','pipe','pipe'],env:{}});
  let stdout='',stderr='',done=false;
  const finish=(err,value)=>{if(done)return;done=true;clearTimeout(timer);err?reject(err):resolve(value);};
  const timer=setTimeout(()=>{child.kill('SIGKILL');finish(Error('Function wall-time limit exceeded'));},4000);
  child.stdout.on('data',b=>{stdout+=b;if(stdout.length>1200000){child.kill('SIGKILL');finish(Error('Output cap'));}});
  child.stderr.on('data',b=>{stderr=(stderr+b).slice(-1000);});
  child.on('error',e=>finish(e));child.stdin.on('error',e=>finish(e));
  child.on('close',code=>{if(done)return;try{if(code!==0)throw Error('Worker failed: '+stderr);const r=JSON.parse(stdout);if(!r.ok)throw Error(r.error);if(module.protocolClass!=="memory" && r.output && Object.hasOwn(r.output,"carry"))throw Error("Only Memory may return carry");finish(null,r.output);}catch(e){finish(e);}});
  child.stdin.end(data);
 });
}
export function validateRegistry(modules){
 const ids=new Set();
 for(const module of modules){validate(module);if(ids.has(module.moduleId))throw Error('Duplicate module');ids.add(module.moduleId);}
}

export function registry(modules){
 const rows=structuredClone(modules),map=new Map();for(const m of rows){validate(m);if(map.has(m.moduleId))throw Error('Duplicate module');map.set(m.moduleId,m);}
 return {list:()=>structuredClone(rows),async invoke(id,input){if(!map.has(id))throw Error('Unknown module');return execute(map.get(id),input);},
 modulesForPath(nodes){const known=new Set(rows.map(m=>m.targetCapabilityNodeId));if(nodes.some(n=>!known.has(n)))throw Error('Unknown node');return structuredClone(rows.filter(m=>nodes.includes(m.targetCapabilityNodeId)));}};
}
export function promptPatches(modules){return registry(modules).list().map(m=>`[${m.moduleId} v${m.version}; ${m.protocolClass}]\n${m.prompt}\nRequired public inputs: ${m.interface.required.join(', ')}`);}
export function createTool(modules){const r=registry(modules);return {name:'capability_modules_run',inputSchema:{type:'object',required:['moduleId','publicInput'],additionalProperties:false,properties:{moduleId:{type:'string',enum:r.list().map(m=>m.moduleId)},publicInput:{type:'object'}}},run:({moduleId,publicInput})=>r.invoke(moduleId,publicInput)};}
