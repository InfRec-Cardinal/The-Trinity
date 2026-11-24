import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {installRelease,recipes,sourceLock} from './module-library/release.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const runtimeRoot=path.resolve(root,'../..');
const runtimeFiles=['src/runtime.mjs','src/native.mjs','src/worker.mjs','src/generation.mjs','config/templates.json','prompts/evolver.txt'];
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,name),'utf8'));
function inventory(dir,exclude=[]){
 const files={},symlinks={},modes={};
 const walk=rel=>{for(const name of fs.readdirSync(path.join(dir,rel)).sort()){
  const key=rel?rel+'/'+name:name;if(exclude.includes(key))continue;
  const file=path.join(dir,key),stat=fs.lstatSync(file);
  if(stat.isSymbolicLink())symlinks[key]=fs.readlinkSync(file);
  else if(stat.isDirectory())walk(key);
  else{assert(stat.isFile(),'Unexpected source type');files[key]=hash(fs.readFileSync(file));modes[key]=stat.mode&0o777;}
 }};walk('');return {files,symlinks,modes};
}
export function verifySource(){
 const lock=read('source-manifest.json');
 const runtime=Object.fromEntries(runtimeFiles.map(name=>[name,hash(fs.readFileSync(path.join(runtimeRoot,name)))]));
 const actual=inventory(root,['source-manifest.json']);
 assert.deepEqual({files:actual.files,symlinks:actual.symlinks,runtime},{files:lock.files,symlinks:lock.symlinks,runtime:lock.runtime},'Source package changed');
 return {sha256:hash(fs.readFileSync(path.join(root,'source-manifest.json'))),files:Object.keys(lock.files).length};
}
export function build(destination){
 const source=verifySource(),out=path.resolve(destination);assert(!fs.existsSync(out),'Destination must not exist');
 assert(out!==root&&!out.startsWith(root+path.sep),'Destination must be outside source package');
 const release=read('release.json'),installed=installRelease();
 const staging=fs.mkdtempSync(path.join(os.tmpdir(),'iter4-build-'));
 const write=(name,data)=>{const target=path.join(staging,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,data);};
 const json=(name,data)=>write(name,JSON.stringify(data,null,2)+'\n');
 try{
  const scaffold=inventory(path.join(root,'scaffold'));
  for(const file of Object.keys(scaffold.files)){write(file,fs.readFileSync(path.join(root,'scaffold',file)));fs.chmodSync(path.join(staging,file),scaffold.modes[file]);}
  const entries=new Set(installed.modules.map(m=>m.function.entry));
  for(const file of Object.keys(sourceLock.files))if(!entries.has(file))write('module-harness/'+file,fs.readFileSync(path.join(root,'module-library/source',file)));
  for(const m of installed.modules)write('module-harness/'+m.function.entry,m.function.source);
  for(const file of fs.readdirSync(path.join(root,'module-library')).sort())if(fs.statSync(path.join(root,'module-library',file)).isFile())write('module-library/'+file,fs.readFileSync(path.join(root,'module-library',file)));
  for(const file of runtimeFiles)write('harness/'+file,fs.readFileSync(path.join(runtimeRoot,file)));
  for(const name of ['runtime','native','generation'])write('module-library/'+name+'.mjs',`export * from '../harness/src/${name}.mjs';\n`);
  json('module-harness/installed-modules.json',installed.modules);
  json('module-harness/harness.json',release.harness);
  json('module-harness/catalog.json',{harnessId:release.harness.harnessId,nodes:installed.modules.map((m,i)=>({node:m.targetCapabilityNodeId,moduleId:m.moduleId,entry:m.function.entry,...m.interface,...recipes[i].catalog,...(m.version!==1?{version:m.version}:{})}))});
  write('module-harness/harness.mjs',fs.readFileSync(path.join(root,'templates/harness.mjs')));
  write('verify-build.mjs',fs.readFileSync(path.join(root,'templates/verify-build.mjs')));
  json('package.json',{name:'iter4-harness-generated',version:'1.4.0',type:'module',license:'MIT',engines:{node:'>=22'},scripts:{verify:'node verify-build.mjs'}});
  json('build.json',{releaseId:release.releaseId,sourceManifestSha256:source.sha256,modules:installed.audit});
  for(const [file,target] of Object.entries(release.links)){
   const filename=path.join(staging,file),resolved=path.resolve(path.dirname(filename),target);assert(resolved.startsWith(staging+path.sep),'External output link');
   fs.mkdirSync(path.dirname(filename),{recursive:true});fs.symlinkSync(target,filename);assert(fs.existsSync(filename),'Broken output link');
  }
  const freeze=inventory(staging);json('freeze.json',{files:freeze.files,symlinks:freeze.symlinks});
  fs.mkdirSync(path.dirname(out),{recursive:true});fs.mkdirSync(out);
  try{fs.cpSync(staging,out,{recursive:true,verbatimSymlinks:true});}catch(error){fs.rmSync(out,{recursive:true,force:true});throw error;}
  return {releaseId:release.releaseId,sourceManifestSha256:source.sha256,activeModules:installed.modules.length,files:Object.keys(freeze.files).length+1,destination:out};
 }finally{fs.rmSync(staging,{recursive:true,force:true});}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2);assert(args.length===2&&args[0]==='--out','Usage: node build.mjs --out NEW_DIR');console.log(JSON.stringify(build(args[1])));
}
