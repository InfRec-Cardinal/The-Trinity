import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {parseMessage,responseTransportMetadata} from './native-decision-protocol.mjs';
export const root=path.resolve(process.env.ARC_PUBLIC_RUN_ROOT);
assert(process.env.ARC_PUBLIC_RUN_ROOT && path.isAbsolute(process.env.ARC_PUBLIC_RUN_ROOT),'Explicit absolute output required');
export const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
process.umask(0o077);
export function withPromptCache(body){
  const request=structuredClone(body);

  for(const block of [...(request.tools??[]),...(request.system??[])])
    if(block.cache_control)block.cache_control={type:'ephemeral',ttl:'5m'};

  for(const m of request.messages)for(const b of m.content??[])delete b.cache_control;
  const last=request.messages.at(-1)?.content?.at(-1);
  assert(last?.type==='text'||last?.type==='tool_result');
  last.cache_control={type:'ephemeral',ttl:'5m'};
  const strip=x=>{const c=structuredClone(x);for(const b of [...(c.tools??[]),...(c.system??[])])delete b.cache_control;for(const m of c.messages)for(const b of m.content??[])delete b.cache_control;return c;};
  assert.deepEqual(strip(request),strip(body));
  return request;
}
export async function callOnce(label,originalBody){
  assert(!fs.existsSync(new URL('../PAUSED.json',import.meta.url)),'Experiments paused by user');
  const body=withPromptCache(originalBody);
  assert(/^[a-z0-9-]+$/.test(label));
  const budgetPath=path.join(root,'budget.json');
  const lock=fs.openSync(path.join(root,'budget.lock'),'wx');
  let n,budget;
  try{
    budget=JSON.parse(fs.readFileSync(budgetPath,'utf8'));
    n=budget.attemptsStarted+1;assert(n<=budget.limit,'Continuation request budget exhausted');
    fs.writeFileSync(path.join(root,'attempts',`${String(n).padStart(2,'0')}.spent.json`),JSON.stringify({label,requestHash:hash(body),at:new Date().toISOString()}),{flag:'wx'});
    budget.attemptsStarted=n;
    fs.writeFileSync(budgetPath,JSON.stringify(budget,null,2)+'\n');
  }finally{fs.closeSync(lock);fs.unlinkSync(path.join(root,'budget.lock'));}
  const dir=path.join(root,'attempts',`${String(n).padStart(2,'0')}-${label}`);
  fs.mkdirSync(dir,{mode:0o700});
  fs.writeFileSync(path.join(dir,'request.json'),JSON.stringify(body));
  const key=process.env.UPSTREAM_API_KEY?.trim();assert(key,'Set UPSTREAM_API_KEY');
  let message,metadata={attempt:n,label,requestHash:hash(body),startedAt:new Date().toISOString()};
  console.log(JSON.stringify({phase:'request_started',attempt:n,label}));
  try{
    const response=await fetch(budget.provider+'/v1/messages',{
      method:'POST',redirect:'error',headers:{'content-type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'},
      body:JSON.stringify(body),signal:AbortSignal.timeout(360000)});
    const raw=(await response.text()).replaceAll(key,'[redacted]');
    fs.writeFileSync(path.join(dir,'response.private.raw'),raw);
    metadata={...metadata,...responseTransportMetadata(response)};
    if(response.ok){
      message=parseMessage(raw);
      metadata={...metadata,...responseTransportMetadata(response,message),blocks:message.content.map(b=>({type:b.type,textCharacters:b.text?.length??0,thinkingCharacters:b.thinking?.length??0,signaturePresent:!!b.signature,tool:b.name??null}))};
      fs.writeFileSync(path.join(dir,'message.private.json'),JSON.stringify(message));
    }
  }catch(e){metadata.errorClass=e.name;fs.writeFileSync(path.join(dir,'error.private.txt'),String(e.stack??e));}
  finally{
    metadata.finishedAt=new Date().toISOString();
    fs.writeFileSync(path.join(dir,'metadata.json'),JSON.stringify(metadata,null,2)+'\n');
    budget=JSON.parse(fs.readFileSync(budgetPath,'utf8'));budget.attemptsCompleted++;
    fs.writeFileSync(budgetPath,JSON.stringify(budget,null,2)+'\n');
    console.log(JSON.stringify(metadata));
  }
  return {message,metadata,dir,attempt:n};
}
