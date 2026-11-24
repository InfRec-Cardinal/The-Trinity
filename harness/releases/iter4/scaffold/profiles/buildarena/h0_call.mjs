import {redact} from '../../vendor/security.mjs';
import fs from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
const {loadFrozenHarness,renderFrozenH0}=await import(pathToFileURL(resolve(process.env.H0_ENV_ROOT,'interface/prompt.mjs')));
const {buildClaudeCliPrompt}=await import(pathToFileURL(resolve(process.env.H0_ENV_ROOT,'player/claude-cli-transport-v4.mjs')));
const release=process.env.BUILDARENA_RELEASE;
if(!release)throw Error('Frozen release required');
const {createCapabilityScope}=await import(pathToFileURL(resolve(release,'shared/capability-scope.mjs')));
createCapabilityScope(process.env.H0_CAPABILITY_NODE??'c-d',{profile:'buildarena'});
process.env.H0_CAPABILITY_NODE??='c-d';
const runner=resolve(release,'profiles/embodied/runner');
const {verifyBuild}=await import(pathToFileURL(resolve(release,'verify-build.mjs')));verifyBuild();
const {activeBranch,branchTool,branchNotice,consultBranch}=await import(pathToFileURL(resolve(runner,'branch-path-modules.mjs')));
const {moduleAwareSystem}=await import(pathToFileURL(resolve(runner,'module-tool-instruction.mjs')));
const {NativeWire}=await import(pathToFileURL(resolve(runner,'native-wire.mjs')));
const {requestAction}=await import(pathToFileURL(resolve(runner,'player-protocol.mjs')));
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const toolText=(input.tools??[]).map(t=>`${t.name}: ${t.description??''}\nParameters: ${JSON.stringify(t.parameters??{})}`).join('\n\n');
const original=loadFrozenHarness();
const skill=JSON.parse(fs.readFileSync(process.env.BUILDARENA_SKILL));
const harness={...original,skills:[...original.skills,...skill.proposals.map(p=>({...p,version:1,status:'frozen'}))],promptPatches:[...(original.promptPatches??[]),branchNotice]};
const digest=createHash('sha256').update(JSON.stringify(harness)).digest('hex');
const assignment={task:'BuildArena machine construction and control in Besiege. Follow the official role instructions and native tools below.\n'+input.roleSystem,
 observation:'Public conversation of the current role and actual tool results.',
 actions:{kind:'message or tool_call',text:'Message content; empty for tool_call',tool:'Official tool name; empty for message',arguments_json:'JSON object string for the named tool; empty for message',availableTools:toolText||'No tools for this role; send a message.'},evaluation:'Official native BuildArena physics pass rule.'};
const nativeTool={name:'submit_action',description:'Submit one official role message or tool call.',input_schema:{type:'object',additionalProperties:false,required:['kind','text','tool','arguments_json'],properties:{kind:{type:'string',enum:['message','tool_call']},text:{type:'string'},tool:{type:'string'},arguments_json:{type:'string'}}}};
const system=moduleAwareSystem(renderFrozenH0(harness,assignment,'interactive','One role message or one official tool call per action.'),[branchTool.name]);
if(process.env.BUILDARENA_VALIDATE_ONLY==='1'){console.log(JSON.stringify({valid:true,digest,modules:activeBranch.map(x=>x.moduleId),skills:skill.proposals.length}));process.exit(0);}
const out=process.env.BUILDARENA_EPISODE_DIR;fs.mkdirSync(out,{recursive:true});
const audit=row=>fs.appendFileSync(resolve(out,'player-requests.jsonl'),redact(JSON.stringify({at:new Date().toISOString(),...row}),[process.env.UPSTREAM_API_KEY])+'\n');
fs.writeFileSync(resolve(out,'learned-harness.json'),JSON.stringify({digest,harness,modules:activeBranch},null,2));
const history=buildClaudeCliPrompt(input.turns).prompt;
const wire=new NativeWire();let messages=[{role:'user',content:[{type:'text',text:history}]}];
const usage={input:0,cachedInput:0,cacheCreationInput:0,output:0};
try{
 for(let index=0;index<3;index++){
  const body=wire.prepare({model:'claude-opus-5',max_tokens:16384,system:[{type:'text',text:system}],tools:[nativeTool,branchTool],messages,stream:true},{nativeOnly:index===2});
  const result=await requestAction({body,post:async request=>{
   audit({kind:'request',body:request});
   const r=await fetch((process.env.RELAY_BASE_URL??'https://api.anthropic.com').replace(/\/$/,'')+'/v1/messages',{method:'POST',redirect:'error',signal:AbortSignal.timeout(180000),headers:{'content-type':'application/json','x-api-key':process.env.UPSTREAM_API_KEY,'anthropic-version':'2023-06-01'},body:JSON.stringify(request)});
   const raw=await r.text();audit({kind:'response',status:r.status,raw});if(!r.ok)throw Object.assign(Error('Provider HTTP '+r.status+': '+redact(raw,[process.env.UPSTREAM_API_KEY]).slice(0,300)),{status:r.status,retryable:[408,409,429].includes(r.status)||r.status>=500});return raw;
  }});
  usage.input+=result.usage.input;usage.cachedInput+=result.usage.cacheRead;usage.cacheCreationInput+=result.usage.cacheCreate;usage.output+=result.usage.output;
  if(!result.action)throw Error('Completed provider outcome without action: '+result.stopReason);
  wire.accept(result);
  if(result.toolName===nativeTool.name){
   const a=result.action;
   if(a.kind==='tool_call'){
    if(!(input.tools??[]).some(t=>t.name===a.tool))throw Error('Unadvertised official role tool');
    const x=JSON.parse(a.arguments_json);if(!x||typeof x!=='object'||Array.isArray(x))throw Error('Malformed official tool arguments');
   }else if(a.kind!=='message')throw Error('Invalid role action');
   console.log(JSON.stringify({args:a,usage}));process.exit(0);
  }
  if(index===2)throw Error('Module consultation budget exhausted');
  const step=input.turns.filter(t=>t.role==='assistant').length;
  const resultBlock=await consultBranch(result.action,step,100);
  audit({kind:'module',input:result.action,output:resultBlock});
  const receipt={type:'tool_result',tool_use_id:result.toolId,content:JSON.stringify(resultBlock)};
  wire.nativeResult(result.toolId,receipt);messages=[...wire.messages,{role:'user',content:[receipt]}];
 }
}catch(e){audit({kind:'error',error:e.message,usage});console.log(JSON.stringify({error:redact(e.message,[process.env.UPSTREAM_API_KEY]),status:e.status??null,retryable:e.retryable===true,usage}));process.exitCode=2;}
