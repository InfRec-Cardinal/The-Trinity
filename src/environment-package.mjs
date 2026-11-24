import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {ensure,identifier,clone} from '../harness/src/core.mjs';
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const relative=name=>typeof name==='string'&&!path.isAbsolute(name)&&!name.includes('\\')&&name.split('/').every(p=>p&&p!=='.'&&p!=='..');
export function assertEnvironmentReuse(options={},allowLocalEnvironment=false){
 ensure(object(options),'Invalid environment driver options');
 ensure(typeof allowLocalEnvironment==='boolean','Invalid local environment reuse option');
 if(options.baseUrl===undefined||options.baseUrl===null){
  ensure(allowLocalEnvironment,'Local environment reuse requires --allow-local-env');
 }else{
  ensure(typeof options.baseUrl==='string'&&options.baseUrl.length>0,'Invalid remote environment URL');
  const url=new URL(options.baseUrl);
  ensure(['http:','https:'].includes(url.protocol)&&!url.username&&!url.password&&!url.search&&!url.hash,'Invalid remote environment URL');
 }
}
export function readEnvironmentPackage(directory){
 const root=fs.realpathSync(directory);
 const read=name=>{ensure(relative(name),'Invalid package path');const file=path.join(root,name);ensure(fs.realpathSync(file)===file,'Package links are not supported');return fs.readFileSync(file);};
 const descriptor=JSON.parse(read('environment-package.json'));
 ensure(descriptor.schema==='trinity-environment-package-v1'&&identifier(descriptor.id)&&typeof descriptor.version==='string','Unsupported environment package');
 ensure(descriptor.instanceSemantics==='fixed-instance-repeats','Unsupported instance semantics');
 const integrity=read(descriptor.integrity),lock=JSON.parse(integrity);
 ensure(object(lock.files)&&Object.keys(lock.files).length>0,'Package file integrity required');
 for(const name of ['environment-package.json',descriptor.driverModule,descriptor.curriculum])ensure(Object.hasOwn(lock.files,name),'Unpinned package entry');
 for(const [name,digest] of Object.entries(lock.files))ensure(typeof digest==='string'&&/^[a-f0-9]{64}$/.test(digest)&&sha(read(name))===digest,'Environment package changed: '+name);
 const curriculum=JSON.parse(read(descriptor.curriculum)),capabilities=descriptor.capabilities;
 ensure(object(capabilities)&&Object.keys(capabilities).every(identifier),'Invalid package capabilities');
 for(const [id,entry] of Object.entries(capabilities))ensure(entry.id===id&&typeof entry.name==='string'&&entry.name.trim()&&typeof entry.definition==='string'&&entry.definition.trim(),'Invalid capability definition');
 ensure(Array.isArray(curriculum)&&curriculum.length>0,'Empty curriculum');
 const ids=new Set(),worlds=new Set();
 for(const task of curriculum){
  ensure(object(task)&&identifier(task.id)&&!ids.has(task.id),'Invalid or duplicate curriculum task');ids.add(task.id);
  ensure(identifier(task.node)&&Object.hasOwn(capabilities,task.node)&&Number.isInteger(task.variant)&&task.variant>=0&&Number.isInteger(task.budget)&&task.budget>0,'Invalid curriculum environment');
  const key=task.node+':'+task.variant;ensure(!worlds.has(key),'Duplicate curriculum environment');worlds.add(key);
  ensure(Array.isArray(task.moduleScope)&&task.moduleScope.includes(task.node)&&new Set(task.moduleScope).size===task.moduleScope.length&&task.moduleScope.every(n=>Object.hasOwn(capabilities,n)),'Invalid module scope');
 }
 const revision=sha(integrity);
 return {root,descriptor:clone(descriptor),curriculum:clone(curriculum),revision,
  verify(){ensure(sha(read(descriptor.integrity))===revision,'Environment integrity manifest changed');for(const [name,digest] of Object.entries(lock.files))ensure(sha(read(name))===digest,'Environment package changed: '+name);},
  async createDriver(options={}, {allowLocalEnvironment=false}={}){
   assertEnvironmentReuse(options,allowLocalEnvironment);
   this.verify();const module=await import(pathToFileURL(path.join(root,descriptor.driverModule)));
   ensure(typeof module.createDriver==='function','Missing package driver factory');
   const driver=await module.createDriver(clone(options));
   try{for(const method of ['loadBenchmark','fingerprint','instanceManifest','initialState','reset','step','close','shutdown'])ensure(typeof driver[method]==='function','Missing driver method: '+method);}
   catch(error){await driver.shutdown?.();throw error;}
   return driver;
  }};
}
