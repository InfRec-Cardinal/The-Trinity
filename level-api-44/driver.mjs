import {createEngine,environments} from './engine.mjs';
import {getPackageInfo} from './package-info.mjs';
const image=f=>({type:'image',mimeType:f.mimeType,data:f.data});
const schema=actions=>({type:'object',additionalProperties:false,required:['action','args'],properties:{action:{type:'string',enum:actions.map(a=>a.name)},args:{type:'object'}},oneOf:actions.map(a=>({properties:{action:{const:a.name},args:a.input_schema}}))});
export async function createDriver({baseUrl=null}={}){
 const info=getPackageInfo();
 if(baseUrl){const url=new URL(baseUrl);if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash)throw Error('Invalid environment base URL');baseUrl=baseUrl.replace(/\/+$/,'');}
 const request=async(route,body,method=body?'POST':'GET')=>{const r=await fetch(baseUrl+route,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(120000)});if(!r.ok)throw Error('Environment request failed: '+r.status);return r.json();};
 if(baseUrl){const remote=await request('/v1/package');if(remote.revision!==info.revision)throw Error('Remote environment revision mismatch');}
 const local=baseUrl?null:await createEngine();
 const transport=local??{create:input=>request('/v1/sessions',input),step:(id,input)=>request('/v1/sessions/'+id+'/step',input),closeSession:id=>request('/v1/sessions/'+id,undefined,'DELETE')};
 const revision=info.revision,sessions=new Map();
 const worldFor=input=>{const match=typeof input==='string'?/^level-(a|b|c|c-a|c-d|c-d-a|d|d-a|d-b|e|e-f)-([0-3])$/.exec(input):null;const node=match?.[1]??input?.node,variant=match?Number(match[2]):input?.variant??0;if(!environments.some(e=>e.node===node&&e.variant===variant))throw Error('Invalid environment');return {node,variant,revision};};
 const observation=(r,contract)=>({goal:contract.rules,task:r.task??{},...(r.records?{records:r.records}:{}),frame:image(r.observation),...(r.frameSheets?{video:r.frameSheets.map(s=>({frames:s.frames,image:image(s)}))}:r.frames?{video:r.frames.map(f=>({timestamp:f.timestamp,image:image(f)}))}:{}),feedback:{accepted:r.accepted,error:r.error,cost:r.cost,steps:r.steps,budget:r.budget,remaining:r.budget-r.steps,terminated:r.terminated},actionCosts:Object.fromEntries(contract.actions.map(a=>[a.name,a.cost]))});
 const driver={budgetUnit:'environment_cost',
  async loadBenchmark(task){return worldFor(typeof task==='string'?task:task?.node?task:task?.id??task?.taskId);},
  async fingerprint(world){if(getPackageInfo().revision!==revision)throw Error('Environment package changed');if(baseUrl&&(await request('/v1/package')).revision!==revision)throw Error('Remote environment revision mismatch');const w=worldFor(world);if(world.revision&&world.revision!==revision)throw Error('Environment revision mismatch');return w;},
  async instanceManifest(world,trials){const w=worldFor(world);if(!Number.isInteger(trials)||trials<1)throw Error('Invalid trial count');return Array.from({length:trials},(_,trial)=>({node:w.node,variant:w.variant,trial}));},
  async reset(world,instance=null){const w=await driver.fingerprint(world);if(instance&&(instance.node!==w.node||instance.variant!==w.variant))throw Error('Instance mismatch');const r=await transport.create({node:w.node,variant:w.variant});const session={observation:observation(r,r),actionSchema:schema(r.actions)};sessions.set(session,{id:r.id,contract:r,initial:structuredClone(session.observation),world:w});return session;},
  async initialState(session){const s=sessions.get(session);if(!s)throw Error('Unknown session');return {world:s.world,observation:structuredClone(s.initial)};},
  async step(session,action){const s=sessions.get(session);if(!s)throw Error('Unknown session');const r=await transport.step(s.id,action);session.observation=observation(r,s.contract);return {done:r.terminated,success:r.terminated&&r.reward===1,cost:r.cost,reward:r.reward,score:r.terminated?r.reward:null,observation:session.observation};},
  async close(session){const s=sessions.get(session);if(!s)return;await transport.closeSession(s.id);sessions.delete(session);},
  async shutdown(){let failure;for(const session of [...sessions.keys()])try{await driver.close(session);}catch(error){failure??=error;}if(local)try{await local.close();}catch(error){failure??=error;}if(failure)throw failure;}
 };return driver;
}
