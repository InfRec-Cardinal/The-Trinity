import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const harness=fileURLToPath(new URL('../harness',import.meta.url)),root=path.join(harness,'releases/iter4');
const files={},symlinks={},modes={};
const hash=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function walk(rel='') {
 for(const name of fs.readdirSync(path.join(root,rel)).sort()) {
  const key=rel?rel+'/'+name:name;
  if(key==='source-manifest.json')continue;
  const file=path.join(root,key),stat=fs.lstatSync(file);
  if(stat.isSymbolicLink())symlinks[key]=fs.readlinkSync(file);
  else if(stat.isDirectory())walk(key);
  else {files[key]=hash(file);modes[key]=stat.mode&0o777;}
 }
}
walk();
const runtime=Object.fromEntries(['src/runtime.mjs','src/native.mjs','src/worker.mjs','src/generation.mjs','config/templates.json','prompts/evolver.txt'].map(name=>[name,hash(path.join(harness,name))]));
fs.writeFileSync(path.join(root,'source-manifest.json'),JSON.stringify({files,symlinks,modes,runtime},null,2)+'\n');
console.log('Updated iter4 source manifest from canonical source');
