import {existsSync} from 'node:fs';
import {join} from 'node:path';
export function pythonFor(root,name){
 const key=`UNSEEN17_PY_${name.toUpperCase().replace(/[^A-Z0-9]/g,'_')}`;
 if(process.env[key])return process.env[key];
 const local=join(root,'envs',name,process.platform==='win32'?'Scripts/python.exe':'bin/python');
 return existsSync(local)?local:process.env.UNSEEN17_PYTHON??process.env.PYTHON??(process.platform==='win32'?'python':'python3');
}
