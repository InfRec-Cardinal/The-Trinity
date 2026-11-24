import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.dirname(fileURLToPath(import.meta.url));
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export function getPackageInfo(){
 const bytes=fs.readFileSync(path.join(root,'integrity.json')),lock=JSON.parse(bytes);
 for(const [name,digest] of Object.entries(lock.files)){
  if(path.isAbsolute(name)||name.includes('\\')||name.split('/').some(p=>!p||p==='.'||p==='..'))throw Error('Invalid package file');
  const file=path.join(root,name);
  if(fs.realpathSync(file)!==file||hash(fs.readFileSync(file))!==digest)throw Error('Environment package changed: '+name);
 }
 const descriptor=JSON.parse(fs.readFileSync(path.join(root,'environment-package.json')));
 return {schema:descriptor.schema,id:descriptor.id,version:descriptor.version,revision:hash(bytes),instanceSemantics:descriptor.instanceSemantics,environments:JSON.parse(fs.readFileSync(path.join(root,descriptor.curriculum)))};
}
