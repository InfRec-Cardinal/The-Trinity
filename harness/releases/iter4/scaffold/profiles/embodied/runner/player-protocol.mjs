
export function retainedProviderOutcome({stopReason,action},{nativeOutputCapPolicy=false}={}) {
  if(stopReason==='refusal')return {ended:false,outcome:'refusal',reason:'provider returned a completed refusal; retained without resampling'};
  if(stopReason==='max_tokens')return nativeOutputCapPolicy?null:{ended:false,outcome:'output_cap',reason:'provider output cap reached; retained without resampling'};
  if(!action)return {ended:false,outcome:'invalid_response',reason:'no tool action after the single permitted continuation; retained without resampling'};
  return null;
}
export function requestPolicy({effort='low',environmentTool,moduleTool,forceEnvironment=false,forceModule=false}) {
  const thinking=effort!=='off'&&effort!=='low';
  const tools=forceEnvironment||!moduleTool?[environmentTool]:forceModule?[moduleTool]:[environmentTool,moduleTool];
  if(thinking)return {tools,thinking:{type:'adaptive'},output_config:{effort},tool_choice:{type:'auto',disable_parallel_tool_use:true}};

  return {tools,thinking:{type:'disabled'},tool_choice:{type:'auto',disable_parallel_tool_use:true}};
}
export function consultationMessages(messages,moduleName) {
  const notice={type:'text',text:`This request is a capability-module consultation substep, not an environment-action submission. The only available tool for this substep is ${moduleName}. Pass only relevant observed evidence to it; an empty evidence set is allowed when none exists. Do not call submit_action in this substep. After the module result, the environment tool will be available again and you may submit the actual action. This consultation consumes no environment step.`};
  const last=messages.at(-1);
  if(last?.role==='user'&&Array.isArray(last.content))return [...messages.slice(0,-1),{...last,content:[...last.content,notice]}];
  return [...messages,{role:'user',content:[notice]}];
}
export function parseMessage(raw) {
  if(raw.trimStart().startsWith('{')) {
    const r=JSON.parse(raw);
    if(r.type==='error')throw new Error('Provider error: '+JSON.stringify(r.error));
    if(!Array.isArray(r.content)||!r.stop_reason)throw new Error('Incomplete provider message');
    return r;
  }
  let response={content:[],usage:{}},stopped=false,blocks=new Map();
  for(const line of raw.split('\n')) {
    if(!line.startsWith('data:'))continue;
    let e;try{e=JSON.parse(line.slice(5).trim())}catch{continue}
    if(e.type==='error')throw new Error('Provider stream error: '+JSON.stringify(e.error));
    if(e.type==='message_start')response={...e.message,content:[],usage:{...e.message.usage}};
    if(e.type==='content_block_start')blocks.set(e.index,{...e.content_block,_json:''});
    if(e.type==='content_block_delta') {
      const b=blocks.get(e.index);if(!b)throw new Error('Delta without block');
      const d=e.delta;
      if(d.type==='input_json_delta')b._json+=d.partial_json;
      if(d.type==='text_delta')b.text=(b.text??'')+d.text;
      if(d.type==='thinking_delta')b.thinking=(b.thinking??'')+d.thinking;
      if(d.type==='signature_delta')b.signature=(b.signature??'')+d.signature;
    }
    if(e.type==='message_delta'){Object.assign(response,e.delta);Object.assign(response.usage,e.usage??{});}
    if(e.type==='message_stop')stopped=true;
  }
  if(!stopped||!response.stop_reason)throw new Error('Incomplete stream without terminal message_stop/stop_reason');
  response.content=[...blocks.entries()].sort(([a],[b])=>a-b).map(([,b])=>{
    if(b.type==='tool_use'&&b._json)b.input=JSON.parse(b._json);
    delete b._json;return b;
  });
  return response;
}
export function selectAction(response,offered) {
  const usage={input:response.usage?.input_tokens??0,cacheCreate:response.usage?.cache_creation_input_tokens??0,
    cacheRead:response.usage?.cache_read_input_tokens??0,output:response.usage?.output_tokens??0};
  const result={toolId:null,toolName:null,action:null,stopReason:response.stop_reason,stopDetails:response.stop_details??null,usage,assistantContent:response.content};
  if(['refusal','max_tokens'].includes(response.stop_reason))return result;
  const calls=response.content.filter(b=>b.type==='tool_use');
  const reject=message=>{const error=new Error(message);error.responseUsage=usage;error.responseStopReason=response.stop_reason;error.responseToolCalls=calls;throw error;};
  if(calls.length>1)reject('Parallel tool calls not supported; none executed');
  if(!calls.length)return result;
  const c=calls[0];
  if(!offered.some(t=>t.name===c.name))reject('Unadvertised tool: '+c.name);
  if(!c.id||!c.input||typeof c.input!=='object'||Array.isArray(c.input))reject('Invalid tool call');
  return {...result,toolId:c.id,toolName:c.name,action:c.input};
}

let textActionSerial=0;
export function decodeTextAction(response,offered){
 if(['refusal','max_tokens'].includes(response.stop_reason)||response.content.some(b=>b.type!=='text'))return null;
 const native=offered.filter(t=>t.name==='submit_action');if(native.length!==1)return null;
 const rawNamed=response.content.map(b=>b.text).join('').trim();

 if(offered.length!==1&&!/^<invoke name="(?:submit_action|submit__action)">/.test(rawNamed))return null;
 const schema=native[0].input_schema;
 if(Object.keys(schema?.properties??{}).sort().join(',')==='action,card,statement'&&schema.properties.action.enum?.join(',')==='play_card,declare_no_play,guess_rule'){
  const raw=response.content.map(b=>b.text).join('').trim();let action;
  try{action=JSON.parse(raw);}catch{
   const match=/^<invoke name="(?:submit_action|submit__action)">\s*([\s\S]*?)\s*(?:<\/invoke>)?$/.exec(raw);
   if(!match)return null;
   const params=[...match[1].matchAll(/<parameter name="(action|card|statement)">([^<>]*)<\/parameter>/g)];
   if(!params.length||match[1].replace(/<parameter name="(action|card|statement)">([^<>]*)<\/parameter>/g,'').trim())return null;
   action={};
   for(const p of params){if(Object.hasOwn(action,p[1]))return null;try{action[p[1]]=p[1]==='statement'?JSON.parse(p[2]):p[2];}catch{return null;}}
  }
  if(action&&Object.keys(action).join(',')==='action'&&typeof action.action==='string'&&action.action.startsWith('{')){try{action=JSON.parse(action.action);}catch{return null;}}
  if(!action||Array.isArray(action)||typeof action!=='object'||Object.keys(action).some(k=>!['action','card','statement'].includes(k))||!schema.properties.action.enum.includes(action.action))return null;
  if(action.action==='play_card'&&(typeof action.card!=='string'||!/^(?:[1-9]|1[0-3])[CDHS]$/.test(action.card)))return null;
  if(action.action==='guess_rule'&&(!action.statement||typeof action.statement!=='object'||Array.isArray(action.statement)))return null;
  const id='local_text_action_'+(++textActionSerial);
  return {response:{...response,content:[...response.content,{type:'tool_use',id,name:'submit_action',input:action}]},provenance:{adapter:'eleusis_exact_text_transport_v1',syntheticToolId:id,rawText:raw}};
 }

 if(Object.keys(schema?.properties??{}).join(',')==='move'&&schema.properties.move.type==='string'){
  let raw=response.content.map(b=>b.text).join('').trim(),move,format;
  try{const a=JSON.parse(raw);if(Object.keys(a).join(',')!=='move')return null;move=a.move;format='exact_move_json';}catch{
   raw=raw.replace(/^<submit__action>\s*/,'').replace(/\s*<\/submit__action>$/,'');
   const invoke=/^<invoke name="(?:submit_action|submit__action)">\s*([\s\S]*?)\s*(?:<\/invoke>)?$/.exec(raw);
   if(!invoke)return null;
   const params=[...invoke[1].matchAll(/<parameter name="move">([^<>]*)<\/parameter>/g)];
   if(!params.length||invoke[1].replace(/<parameter name="move">([^<>]*)<\/parameter>/g,'').trim())return null;
   move=params[0][1];if(params.some(p=>p[1]!==move))return null;
   format='unambiguous_move_invoke';
  }
  if(typeof move!=='string'||!/^[a-h][1-8][a-h][1-8][qrbn]?$/.test(move))return null;
  const id='local_text_action_'+(++textActionSerial);
  return {response:{...response,content:[...response.content,{type:'tool_use',id,name:'submit_action',input:{move}}]},provenance:{adapter:'chess_move_transport_v1',format,syntheticToolId:id,rawText:raw}};
 }

 if(Object.keys(schema?.properties??{}).join(',')==='action'&&schema.properties.action.type==='string'){
  const original=response.content.map(b=>b.text).join('').trim();let raw=original;
  if(raw.startsWith('<invoke name=\\"')){try{raw=JSON.parse('"'+raw+'"');}catch{return null;}}
  let action,format;
  try{action=JSON.parse(raw);format='exact_action_json';}catch{
   const match=/^<invoke name="(submit_action|submit__action)">\s*<parameter name="action">([^<>]*)<\/parameter>\s*(?:<\/invoke>)?$/.exec(raw);
   if(!match)return null;action={action:match[2]};format='exact_action_invoke';
  }
  const rule=schema.properties.action;
  if(!action||Array.isArray(action)||Object.keys(action).join(',')!=='action'||typeof action.action!=='string'||action.action.length>(rule.maxLength??10000)||(rule.enum&&!rule.enum.includes(action.action)))return null;
  const id='local_text_action_'+(++textActionSerial);
  return {response:{...response,content:[...response.content,{type:'tool_use',id,name:'submit_action',input:action}]},provenance:{adapter:'single_string_action_transport_v1',format,originalStopReason:response.stop_reason,syntheticToolId:id,rawText:original}};
 }
 if(Object.keys(schema?.properties??{}).sort().join(',')!=='clue,number')return null;
 const raw=response.content.map(b=>b.text).join('').trim();if(raw.length>1000)return null;
 let action,format;
 try{action=JSON.parse(raw);format='exact_json';}catch{

  const match=/^<invoke name="(submit_action|submit__action)">\s*<parameter name="clue">([^<>]*)<\/parameter>\s*<parameter name="number">([0-9]+)<\/parameter>\s*(?:<\/invoke>)?$/.exec(raw);
  if(!match)return null;action={clue:match[2],number:Number(match[3])};format='exact_text_invoke';
 }
 if(!action||Array.isArray(action)||Object.keys(action).sort().join(',')!=='clue,number'||typeof action.clue!=='string'||action.clue.length>40||!Number.isSafeInteger(action.number)||action.number<0||action.number>25)return null;
 const id='local_text_action_'+(++textActionSerial);
 return {response:{...response,content:[...response.content,{type:'tool_use',id,name:'submit_action',input:action}]},provenance:{adapter:'codenames_text_action_v1',format,originalStopReason:response.stop_reason,syntheticToolId:id,rawText:raw}};
}

export function sanitizeToolCallHistory(body) {
  let removed = 0;
  const messages = body.messages.map(message => {
    if (message.role !== 'assistant' || !Array.isArray(message.content)) return message;
    return {...message, content: message.content.map(block => {
      if (block.type !== 'tool_use' || !Object.hasOwn(block, 'caller')) return block;
      const {caller, ...rest} = block;
      removed++;
      return rest;
    })};
  });
  return {body: removed ? {...body, messages} : body, removed};
}

export async function requestAction({body,post,allowTextAction=false}) {
  const first=parseMessage(await post(body));
  const decoded=allowTextAction?decodeTextAction(first,body.tools):null;
  let result=selectAction(decoded?.response??first,body.tools);
  if(decoded)result.transportAdapter=decoded.provenance;

  if(result.action||['refusal','max_tokens'].includes(result.stopReason))return {...result,requestMessages:body.messages};

  const next={...body,messages:[...body.messages,{role:'assistant',content:first.content},
    {role:'user',content:[{type:'text',text:'Use one of the available tools to submit the next action. No environment action has executed.'}]}]};
  try {
    const second=parseMessage(await post(next));
    const decodedFollow=allowTextAction?decodeTextAction(second,next.tools):null;
    const follow=selectAction(decodedFollow?.response??second,next.tools);
    if(decodedFollow)follow.transportAdapter=decodedFollow.provenance;
    for(const key of Object.keys(result.usage))follow.usage[key]+=result.usage[key];
    return {...follow,requestMessages:next.messages};
  } catch(error) {
    error.responseUsage??={input:0,cacheCreate:0,cacheRead:0,output:0};
    for(const key of Object.keys(result.usage))error.responseUsage[key]+=result.usage[key];
    throw error;
  }
}
