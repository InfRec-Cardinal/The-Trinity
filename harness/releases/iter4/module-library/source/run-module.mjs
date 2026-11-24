import fs from 'node:fs';
import {catalog,manifest,modulesForPath} from './harness.mjs';
import {createCapabilityScope} from '../shared/capability-scope.mjs';
const [id,file,...args]=process.argv.slice(2);
if(id==='--list')console.log(JSON.stringify({harnessId:manifest.harnessId,modules:file?modulesForPath(file.split(',')):catalog.nodes},null,2));
else{
 if(!id||!file||args.length!==2||args[0]!=='--node')throw Error('Usage: node run-module.mjs MODULE_ID PUBLIC_INPUT.json --node NODE | --list [NODE,NODE]');
 const scope=createCapabilityScope(args[1]);
 scope.require(id);
 console.log(JSON.stringify(await scope.invoke(id,JSON.parse(fs.readFileSync(file,'utf8'))),null,2));
}
