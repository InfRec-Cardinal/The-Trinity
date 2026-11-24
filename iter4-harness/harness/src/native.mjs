import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const hosts=new WeakMap();
const loadedFiles=new Map();
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const keys=(x,required,optional=[])=>{assert(object(x)&&required.every(k=>Object.hasOwn(x,k))&&Object.keys(x).every(k=>[...required,...optional].includes(k)),'Invalid native object keys');};
const identifier=x=>typeof x==='string'&&/^[a-zA-Z][a-zA-Z0-9_-]{0,159}$/.test(x)&&!['constructor','prototype','__proto__'].includes(x);
const inputs=x=>assert(Array.isArray(x)&&x.length<=64&&x.every(identifier)&&new Set(x).size===x.length,'Invalid required inputs');
export const relativeName=x=>typeof x==='string'&&!path.isAbsolute(x)&&!x.includes('\\')&&x.split('/').every(p=>p&&p!=='.'&&p!=='..');
export function validateNative(m){
 keys(m.interface,['required'],['inputModes','defaultInputMode']);inputs(m.interface.required);
 if(m.interface.inputModes!==undefined){
  assert(object(m.interface.inputModes)&&Object.keys(m.interface.inputModes).length>0,'Invalid input modes');
  for(const [mode,spec] of Object.entries(m.interface.inputModes)){assert(identifier(mode),'Invalid mode');keys(spec,['required']);inputs(spec.required);}
 }
 if(m.interface.defaultInputMode!==undefined)assert(typeof m.interface.defaultInputMode==='string'&&Object.hasOwn(m.interface.inputModes??{},m.interface.defaultInputMode),'Invalid default mode');
 keys(m.function,['language','source','entry','sha256']);
 assert.equal(m.function.language,'javascript-module');
 assert(relativeName(m.function.entry)&&m.function.entry.endsWith('.mjs'),'Invalid native entry');
 assert(typeof m.function.source==='string'&&m.function.source.length<=1048576,'Invalid native source');
 assert.equal(sha(m.function.source),m.function.sha256,'Native source digest mismatch');
 assert(Array.isArray(m.hostCapabilities)&&m.hostCapabilities.every(identifier)&&new Set(m.hostCapabilities).size===m.hostCapabilities.length,'Invalid host capabilities');
 return m;
}
export function createNativeHost({root,files,grants,capabilities=[]}){
 assert(object(files)&&object(grants)&&Array.isArray(capabilities),'Invalid native host configuration');
 const config={root:fs.realpathSync(root),files:structuredClone(files),grants:structuredClone(grants),capabilities:[...capabilities]};
 for(const [file,digest] of Object.entries(config.files)){assert(relativeName(file)&&/^[a-f0-9]{64}$/.test(digest),'Invalid source lock');}
 for(const [entry,required] of Object.entries(config.grants)){assert(Object.hasOwn(config.files,entry)&&Array.isArray(required)&&required.every(identifier),'Invalid native grant');}
 const token=Object.freeze({});hosts.set(token,config);verifyNativeHost(token);return token;
}
export function verifyNativeHost(host){
 const config=hosts.get(host);assert(config,'Explicit native host required');
 for(const [file,digest] of Object.entries(config.files)){
  const filename=path.join(config.root,file),resolved=fs.realpathSync(filename);
  assert(resolved===filename&&resolved.startsWith(config.root+path.sep)&&fs.lstatSync(filename).isFile(),'Native file must be inside approved source root');
  assert.equal(sha(fs.readFileSync(filename)),digest,'Native dependency changed: '+file);
 }
 return {files:Object.keys(config.files).length,entries:Object.keys(config.grants).length};
}
export function authorizeNative(m,host){
 validateNative(m);const config=hosts.get(host);assert(config,'Explicit native host required');
 assert.equal(config.files[m.function.entry],m.function.sha256,'Native source is not approved by host');
 assert.deepEqual(m.hostCapabilities,config.grants[m.function.entry],'Native capability declaration mismatch');
 for(const capability of m.hostCapabilities)assert(config.capabilities.includes(capability),'Host capability unavailable: '+capability);
 verifyNativeHost(host);return path.join(config.root,m.function.entry);
}
export async function executeNative(m,input,host){
 m=structuredClone(m);
 const entry=authorizeNative(m,host);assert(object(input),'Public input object required');
 input=JSON.parse(JSON.stringify(input));assert(object(input),'Public input object required');
 if(Object.hasOwn(input,'mode'))assert(typeof input.mode==='string'&&input.mode.length>0,'Invalid module input mode');
 const mode=input.mode??m.interface.defaultInputMode;
 if(m.interface.inputModes){assert(typeof mode==='string'&&Object.hasOwn(m.interface.inputModes,mode),'Unknown module input mode');input.mode=mode;}
 for(const key of m.interface.inputModes?m.interface.inputModes[mode].required:m.interface.required)assert(Object.hasOwn(input,key),'Missing public input: '+key);
 const config=hosts.get(host);
 for(const [file,digest] of Object.entries(config.files)){
  const filename=path.join(config.root,file);
  assert(!loadedFiles.has(filename)||loadedFiles.get(filename)===digest,'Native source already loaded with different content; use a fresh source directory');
 }
 for(const [file,digest] of Object.entries(config.files))loadedFiles.set(path.join(config.root,file),digest);
 const {default:run}=await import(pathToFileURL(entry));assert.equal(typeof run,'function','Native default export required');
 return JSON.parse(JSON.stringify(await run(input)));
}
