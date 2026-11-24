import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {randomBytes} from 'node:crypto';
import {fileURLToPath} from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export async function runStage2({code, directory, exploration, profile, callModel, emit = () => {}, signal}) {
  signal?.throwIfAborted();
  const controller = new AbortController();
  const abort = () => controller.abort(signal.reason);
  signal?.addEventListener('abort', abort, {once:true});
  const token = randomBytes(24).toString('hex');
  const bridge = http.createServer(async (req,res) => {
    const reply = value => {if (res.destroyed || res.writableEnded) return; res.writeHead(200,{'Content-Type':'application/json'});res.end(JSON.stringify(value));};
    if (req.method !== 'POST' || req.headers.authorization !== 'Bearer '+token) {res.writeHead(403);res.end();return;}
    try {
      let body = '';
      for await (const chunk of req) {body += chunk;if(Buffer.byteLength(body)>32*1024*1024)throw Error('Stage 2 request too large');}
      const input = JSON.parse(body);
      reply(await callModel({profile,system:input.system,turns:input.messages.map(m=>m.role==='assistant'?{role:'assistant',content:m.content}:{role:'user',text:m.content}),
        tools:(input.tools??[]).map(t=>({name:t.name,description:t.description,parameters:t.input_schema})),
        maxTokens:input.max_tokens,searchEnabled:false,signal:controller.signal}));
    } catch(error) {reply({error:String(error.message),attemptRecords:error.attemptRecords??[]});}
  });
  try { await new Promise((resolve,reject)=>{bridge.once('error',reject);bridge.listen(0,'127.0.0.1',resolve);}); }
  catch (error) { signal?.removeEventListener('abort',abort); controller.abort(); bridge.close(); throw error; }
  const env = {...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONPATH:path.join(code,'stage2'),
    TRINITY_NODE:process.execPath,STUDIO_STAGE2_BRIDGE:'http://127.0.0.1:'+bridge.address().port,
    STUDIO_STAGE2_TOKEN:token};
  for (const name of ['ANTHROPIC_API_KEY','TRINITY_API_KEY']) delete env[name];
  const run = (args, outputFile) => new Promise((resolve,reject)=>{
                                                                                      
    controller.signal.throwIfAborted();
    const fd = outputFile ? fs.openSync(outputFile,'wx',0o600) : null;
    let child;
    try {
      child = spawn(process.env.TRINITY_PYTHON || 'python3',['-B',path.join(HERE,'stage2-bridge.py'),...args],{env,stdio:['ignore',fd ?? 'pipe','pipe'],signal:controller.signal,killSignal:'SIGKILL'});
    } finally {if(fd !== null)fs.closeSync(fd);}
    child.stdout?.setEncoding('utf8'); child.stderr.setEncoding('utf8');
    let output='',error='',overflow=false;
    child.stdout?.on('data',chunk=>{
      if(overflow)return;
      output+=chunk;
      if(Buffer.byteLength(output)>32*1024*1024){overflow=true;output='';child.kill('SIGKILL');}
    });
    child.stderr.on('data',chunk=>{error=(error+chunk).slice(-4000);});
    child.on('error',reject);
    child.on('close',status=>status===0&&!overflow?resolve(output):reject(Error('Stage 2 failed: '+(overflow?'Diagnostic output limit exceeded':(error || output).slice(-4000)))));
  });
  const pending = path.join(directory,'.training-input-'+token+'.tmp');
  try {
    emit('phase',{phase:'induce'});
    await run(['all','--out',directory,'--handoff',path.join(exploration,'handoff.json'),'--runs',path.join(exploration,'runs.json')]);
    await run(['export-training','--out',directory],pending);
    const input = JSON.parse(fs.readFileSync(pending,'utf8'));
    fs.renameSync(pending,path.join(directory,'training-input.json'));
    return input;
  } finally {
    signal?.removeEventListener('abort',abort); controller.abort();
    bridge.closeAllConnections();
    try { await new Promise(resolve=>bridge.close(resolve)); } finally { fs.rmSync(pending,{force:true}); }
  }
}
