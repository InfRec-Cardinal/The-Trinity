
import fs from 'node:fs';import vm from 'node:vm';
try{
 const {source,input}=JSON.parse(fs.readFileSync(0,'utf8'));
 if(typeof source!=='string'||source.length>32000)throw Error('Program source cap');
 const context=vm.createContext(Object.create(null),{codeGeneration:{strings:false,wasm:false},microtaskMode:'afterEvaluate'});
 const setup=new vm.Script('globalThis.Date=undefined; Math.random=undefined; globalThis.console=undefined;');setup.runInContext(context,{timeout:100});
 const script=new vm.Script(`JSON.stringify((${source})(JSON.parse(${JSON.stringify(JSON.stringify(input))})))`);
 const output=script.runInContext(context,{timeout:500});
 if(typeof output!=='string'||output.length>16000)throw Error('Output cap/type');
 process.stdout.write(JSON.stringify({ok:true,output:JSON.parse(output)}));
}catch(e){process.stdout.write(JSON.stringify({ok:false,error:String(e.message).slice(0,800)}));}
