import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
export function semanticSignal(input){
 if(!input.source||!Array.isArray(input.items)||input.items.length<2||input.items.length>100)throw Error('Sourced public alternatives required');
 return JSON.parse(execFileSync('python3',[fileURLToPath(new URL('./semantic-signals.py',import.meta.url))],{input:JSON.stringify(input),encoding:'utf8',timeout:30000,maxBuffer:1024*1024,env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'}}));
}
