import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
import {randomUUID} from 'node:crypto';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_VENDOR = path.resolve(HERE, '..', '..', 'level-api-44', 'vendor');
export const MAX_TAPE_ACTIONS = 300;

const PAGE_RUNTIME = (base, node, variant) => `
import * as T from ${JSON.stringify(base + 'three.module.js')};
import * as M from ${JSON.stringify(base + 'level.mjs')};
const scene = new T.Scene(); scene.background = new T.Color('#213641');
const renderer = new T.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
renderer.setSize(1200, 612); renderer.setPixelRatio(1); renderer.outputColorSpace = T.SRGBColorSpace;
renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.2;
const camera = new T.PerspectiveCamera(48, 1200/612, .1, 100);
scene.add(new T.HemisphereLight(14939391, 6840396, 2.3));
const sun = new T.DirectionalLight(16769980, 3); sun.position.set(3,10,5); scene.add(sun);
let group = new T.Group(), steps = 0, ended = false, success = null, overlay = '', status = '', labels = [], commands = new Map(), fields = new Map(), level;
scene.add(group);
const colors = [15040361,7714712,7186140,14992497,10981063,8632766];
function box(x,y,z,w,h,d,color=7441297){const m=new T.Mesh(new T.BoxGeometry(w,h,d),new T.MeshStandardMaterial({color,roughness:.65}));m.position.set(x,y,z);group.add(m);return m;}
function ball(x,y,z,r,color){const m=new T.Mesh(new T.SphereGeometry(r,24,16),new T.MeshStandardMaterial({color,roughness:.65}));m.position.set(x,y,z);group.add(m);return m;}
function text(label,x,y,z,size=.45,color='#eef6f3'){labels.push(String(label));const c=document.createElement('canvas');let ctx=c.getContext('2d');ctx.font='64px sans-serif';c.width=Math.min(1800,Math.max(88,Math.ceil(ctx.measureText(label).width+40)));c.height=128;ctx=c.getContext('2d');ctx.fillStyle='#10252ce8';ctx.fillRect(0,0,c.width,128);ctx.fillStyle=color;ctx.font='64px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(label,c.width/2,64,c.width-24);const tex=new T.CanvasTexture(c);tex.colorSpace=T.SRGBColorSpace;const s=new T.Sprite(new T.SpriteMaterial({map:tex,depthTest:false}));s.scale.set(Math.min(size*c.width/128,5.8),size,1);s.position.set(x,y,z);group.add(s);return s;}
function clear(){group.traverse(o=>{o.geometry?.dispose();if(o.material){o.material.map?.dispose();o.material.dispose();}});scene.remove(group);group=new T.Group();scene.add(group);camera.position.set(0,10,13);camera.lookAt(0,0,0);box(0,-.35,0,12,.3,10,3427411);}
function draw(){if(!level)return;clear();commands.clear();fields.clear();labels=[];overlay='';level.draw();renderer.render(scene,camera);}
const ui = {THREE:T,camera,colors,group:()=>group,box,ball,text,
  command(label,fn){if(commands.has(label))throw Error('Duplicate command');commands.set(label,fn);},
  number(label,id,value,min=0,max=20){fields.set(id,{value:String(value),min,max});},
  choice(label,id,options){fields.set(id,{value:String(options[0]),options:options.map(String)});},
  value:id=>fields.get(id)?.value, index:id=>fields.get(id)?.options.indexOf(fields.get(id).value),
  say:t=>{status=String(t);}, log:()=>{}, overlay:t=>{overlay=String(t);},
  isEnded:()=>ended, steps:()=>steps,
  finish(ok,message){if(ended)return;ended=true;success=!!ok;status=(ok?'Success: ':'Ended: ')+message;},
  step(message,fn){if(ended)return false;steps++;fn();if(!ended&&steps>=level.budget)ui.finish(false,'Decision budget exhausted.');draw();return true;},
  redraw:draw};
const NODE = ${JSON.stringify(String(node))}, VARIANT = ${Number(variant) || 0};
if (typeof M.createLevel !== 'function') throw Error('Level module must export createLevel');
level = M.createLevel(NODE, VARIANT, ui);
if(!level || typeof level.draw !== 'function' || !Number.isInteger(level.budget) || level.budget < 1) throw Error('createLevel must return {budget>0, rules, draw()}');
draw();
const frame = () => {renderer.render(scene,camera);return renderer.domElement.toDataURL('image/png').split(',')[1];};
function inspect(){return {node:NODE,variant:VARIANT,steps,budget:level.budget,ended,success,rules:level.rules,status,overlay,labels:[...labels],commands:[...commands.keys()],fields:Object.fromEntries([...fields].map(([k,v])=>[k,structuredClone(v)]))};}
function set(id,value){if(ended)throw Error('Episode ended');const f=fields.get(id);if(!f)throw Error('Unknown parameter');if(f.options&&!f.options.includes(String(value)))throw Error('Invalid option');if(!f.options&&(!Number.isInteger(Number(value))||Number(value)<f.min||Number(value)>f.max))throw Error('Invalid number');f.value=String(value);}
function call(label){if(ended)throw Error('Episode ended');const fn=commands.get(label);if(!fn)throw Error('Action unavailable');fn();renderer.render(scene,camera);}
const r = {inspect, set, call, frame, task: () => (level.task ? level.task() : {})};
function act(action){
  if (typeof M.execute === 'function') {const out = M.execute(r, NODE, VARIANT, String(action.action), action.args ?? {}); return out;}
  try {for (const [k,v] of Object.entries(action.args ?? {})) set(k, v); call(String(action.action)); return {accepted:true, error:null};}
  catch (e) {return {accepted:false, error:String(e.message||e)};}
}
function actions(){
  if(typeof M.actionsFor==='function')return M.actionsFor(NODE,VARIANT);
  const properties=Object.fromEntries([...fields].map(([id,f])=>[id,f.options?{type:'string',enum:f.options}:{type:'integer',minimum:f.min,maximum:f.max}]));
  return [...commands.keys()].map(name=>({name,input_schema:{type:'object',properties,additionalProperties:false},cost:'environment step delta'}));
}
globalThis.__level = {frame, inspect, act, task:r.task, actions};
`;

let shared = null;
let handleSignals = true;
export function configureLevelEngine(options = {}) {
  if (shared) throw Error('Configure the level engine before opening a browser');
  if (typeof options.handleSignals !== 'boolean') throw Error('handleSignals must be a boolean');
  handleSignals = options.handleSignals;
}
async function loadChromium() {
  const pick = m => m.chromium ?? m.default?.chromium;
  if (process.env.PLAYWRIGHT_MODULE) return pick(await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE)));
  const candidate = path.resolve(HERE, '..', '..', 'level-api-44', 'node_modules', 'playwright', 'index.js');
  try {const got = pick(await import(pathToFileURL(candidate))); if (got) return got;} catch {}
  return pick(await import('playwright'));
}
function browser() {
  shared ??= loadChromium().then(chromium => chromium.launch({headless: true,
    handleSIGINT: handleSignals, handleSIGTERM: handleSignals, handleSIGHUP: handleSignals,
    args: ['--no-sandbox', '--enable-unsafe-swiftshader']}));
  shared.catch(() => {shared = null;});
  return shared;
}

export async function openLevel({source, node = 'level', variant = 0, vendorDir = DEFAULT_VENDOR}) {
  if (typeof source !== 'string' || !source.trim()) throw Error('Level module source is required');
  if (!/^[a-z][a-z0-9_-]{0,159}$/.test(node) || !Number.isInteger(variant) || variant < 0 || variant > 63) throw Error('Invalid level instance');
  const token = randomUUID();
  const assets = http.createServer(async (req, res) => {
    const key = (req.url ?? '').split('?')[0].slice(token.length + 2);
    try {
      if (!req.url?.startsWith('/' + token + '/')) throw Error('forbidden');
      const body = key === 'level.mjs' ? source : key === 'three.module.js' || key === 'three.core.js' ? await fs.readFile(path.join(vendorDir, key)) : null;
      if (body === null) throw Error('not found');
      res.writeHead(200, {'Content-Type': 'text/javascript', 'Access-Control-Allow-Origin': '*'});
      res.end(body);
    } catch {res.writeHead(404); res.end();}
  });
  await new Promise(resolve => assets.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${assets.address().port}/${token}/`;
  let context, closed = false;
  const close = async () => {
    if (closed) return;
    closed = true;
    try {await context?.close();} finally {await new Promise(resolve => assets.close(resolve));}
  };
  const bounded = async fn => {
    let timer;
    try {return await Promise.race([fn(), new Promise((_, reject) => {timer = setTimeout(() => {void close().catch(()=>{}); reject(Error('Level execution timed out'));}, 30000);})]);}
    finally {clearTimeout(timer);}
  };
  try {
    const b = await browser();
    context = await b.newContext({viewport: {width: 1200, height: 900}});
    await context.route('**/*', route => {
      const url = route.request().url();
      return url.startsWith(base) || url.startsWith('data:') ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    await page.setContent('<!doctype html><meta charset="utf-8">');
    await bounded(() => page.evaluate(src => import('data:text/javascript,' + encodeURIComponent(src)), PAGE_RUNTIME(base, node, variant)));
    const snapshot = () => bounded(() => page.evaluate(() => ({inspect: __level.inspect(), frame: __level.frame(), task: __level.task(), actions: __level.actions()})));
    return {snapshot, close,
      async step(action) {
        if (closed) throw Error('Level session is closed');
        return bounded(() => page.evaluate(action => {
          const before = __level.inspect();
          if(before.ended) throw Error('Episode ended');
          const receipt = __level.act(action), after = __level.inspect();
          return {receipt, cost: after.steps-before.steps, inspect: after, frame: __level.frame(), task: __level.task(), actions: __level.actions()};
        }, action));
      }};
  } catch (error) {await close(); throw error;}
}

export async function renderLevel({source, node = 'level', variant = 0, actions = [], vendorDir = DEFAULT_VENDOR}) {
  if (!Array.isArray(actions) || actions.length > MAX_TAPE_ACTIONS) throw Error('Invalid action tape');
  const session = await openLevel({source, node, variant, vendorDir});
  try {
    let state = await session.snapshot();
    const frames = [state.frame], receipts = [];
    for (const action of actions) {
      if (state.inspect.ended) break;
      state = await session.step(action);
      receipts.push(state.receipt);
      frames.push(state.frame);
    }
    return {frames, receipts, inspect: state.inspect};
  } finally {await session.close();}
}

export async function closeLevelEngine() {
  const pending = shared;
  shared = null;
  const open = pending && await pending.catch(() => null);
  if (open) await open.close();
}
