import fs from 'node:fs';
import vm from 'node:vm';
try {
 const {source,input}=JSON.parse(fs.readFileSync(0,'utf8'));
 const context=vm.createContext(Object.create(null),{codeGeneration:{strings:false,wasm:false},microtaskMode:'afterEvaluate'});
 new vm.Script(`globalThis.Date=undefined; Math.random=undefined; globalThis.console=undefined;
 globalThis.structuredClone=function clone(value,seen=new Map()) {
  if(value===null||typeof value!=='object')return value;
  if(seen.has(value))return seen.get(value);
  const result=Array.isArray(value)?[]:{};seen.set(value,result);
  for(const key of Object.keys(value))Object.defineProperty(result,key,{value:clone(value[key],seen),writable:true,enumerable:true,configurable:true});
  return result;
 };`).runInContext(context,{timeout:100});
 const script=new vm.Script(`const result=(${source})(JSON.parse(${JSON.stringify(JSON.stringify(input))}));
 if(result && typeof result.then === 'function') throw Error('Async functions are unsupported');
 JSON.stringify(result);`);
 const output=script.runInContext(context,{timeout:1500});
 if(typeof output!=='string'||output.length>1048576)throw Error('Output must be bounded JSON');
 process.stdout.write(JSON.stringify({ok:true,output:JSON.parse(output)}));
} catch(error) {process.stdout.write(JSON.stringify({ok:false,error:String(error.message).slice(0,1000)}));}
