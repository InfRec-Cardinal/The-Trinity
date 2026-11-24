import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {openLevel,closeLevelEngine} from './level-engine.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
let activeDrivers = 0;
const actionSchema = actions => ({type:'object', additionalProperties:false, required:['action','args'],
  properties:{action:{type:'string',enum:actions.map(a=>a.name)},args:{type:'object'}},
  oneOf:actions.map(a=>({properties:{action:{const:a.name},args:a.input_schema}}))});

export async function createDriver(options = {}) {
  if(options.baseUrl)throw Error('Project levels require local execution; remote URLs are not supported');
  const integrity = fs.readFileSync(path.join(ROOT, 'integrity.json'));
  const revision = sha(integrity), lock = JSON.parse(integrity);
  const curriculum = JSON.parse(fs.readFileSync(path.join(ROOT, 'curriculum.json')));
  const levels = JSON.parse(fs.readFileSync(path.join(ROOT, 'levels.json')));
  const sessions = new Map();
  let closed = false;
  activeDrivers++;
  const verify = () => {
    if (sha(fs.readFileSync(path.join(ROOT,'integrity.json'))) !== revision) throw Error('Project environment integrity changed');
    for (const [name, hash] of Object.entries(lock.files)) if (sha(fs.readFileSync(path.join(ROOT,name))) !== hash) throw Error('Project environment changed: ' + name);
  };
  const taskFor = input => {
    const id = typeof input === 'string' ? input : input?.taskId ?? input?.id;
    const task = curriculum.find(t => t.id === id);
    if (!task) throw Error('Unknown project environment: ' + id);
    return task;
  };
  const observation = state => ({goal:state.inspect.rules, task:state.task, frame:{type:'image',mimeType:'image/png',data:state.frame},
    publicState:{status:state.inspect.status,overlay:state.inspect.overlay,labels:state.inspect.labels,fields:state.inspect.fields},
    ...(state.receipt?.records ? {records:state.receipt.records} : {}),
    ...(state.receipt?.frames ? {video:state.receipt.frames.map(f=>({timestamp:f.timestamp,image:{type:'image',mimeType:f.mimeType,data:f.data}}))} : {}),
    feedback:{accepted:state.receipt?.accepted ?? true,error:state.receipt?.error ?? null,cost:state.cost ?? 0,
      steps:state.inspect.steps,budget:state.inspect.budget,remaining:state.inspect.budget-state.inspect.steps,terminated:state.inspect.ended},
    actionCosts:Object.fromEntries(state.actions.map(a=>[a.name,a.cost]))});
  const driver = {budgetUnit:'environment_cost',
    async loadBenchmark(input) {
      const t = taskFor(input);
      return {taskId:t.id,node:t.node,variant:t.variant,levelRef:t.levelRef,revision};
    },
    async fingerprint(world) {
      verify();
      const expected = await driver.loadBenchmark(world);
      if (JSON.stringify(world) !== JSON.stringify(expected)) throw Error('Project world fingerprint mismatch');
      return expected;
    },
    async instanceManifest(world, trials) {
      await driver.fingerprint(world);
      return Array.from({length:trials},(_,trial)=>({node:world.node,variant:world.variant,trial}));
    },
    async reset(world, instance) {
      await driver.fingerprint(world);
      if (instance && (instance.node!==world.node || instance.variant!==world.variant)) throw Error('Project instance mismatch');
      const t = taskFor(world);
      const engine = await openLevel({source:levels[t.levelRef].source,node:t.runtimeNode,variant:t.variant,vendorDir:path.join(ROOT,'vendor')});
      try {
        const state = await engine.snapshot();
        if (state.inspect.budget !== t.budget || state.inspect.ended || !state.actions.length) throw Error('Invalid opening state or curriculum budget');
        const session = {observation:observation(state),actionSchema:actionSchema(state.actions)};
        sessions.set(session,{engine,world,initial:structuredClone(session.observation)});
        return session;
      } catch(error) {await engine.close();throw error;}
    },
    async initialState(session) {
      const s = sessions.get(session);if (!s) throw Error('Unknown project session');
      return structuredClone({world:s.world,observation:s.initial});
    },
    async step(session, action) {
      const s = sessions.get(session);if (!s) throw Error('Unknown project session');
      const state = await s.engine.step(action);
      session.observation = observation(state);session.actionSchema = actionSchema(state.actions);
      const done = state.inspect.ended, success = done && state.inspect.success === true;
      return {done,success,cost:state.cost,reward:success?1:0,score:done?(success?1:0):null,observation:session.observation};
    },
    async close(session) {const s=sessions.get(session);if(s){sessions.delete(session);await s.engine.close();}},
    async shutdown() {
      if(closed)return;closed=true;
      try {await Promise.all([...sessions.keys()].map(session=>driver.close(session)));}
      finally {if(--activeDrivers===0)await closeLevelEngine();}
    },
  };
  return driver;
}
