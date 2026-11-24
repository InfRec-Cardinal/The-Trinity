import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import adaptiveAcquisition from '../../../module-harness/modules/adaptiveAcquisition.mjs';
import {auditCoverage,requirementSignature} from '../../../module-harness/src/acquisition-core.mjs';

const owner='adaptiveAcquisition';
const verified=new Set();
const scopeCache=new Map();
const loggedScopes=new Set();
function verifyMedia(s){
  const identity=JSON.stringify([s.path,s.sha256,fs.statSync(s.path).mtimeMs]);
  if(!verified.has(identity)){
    if(createHash('sha256').update(fs.readFileSync(s.path)).digest('hex')!==s.sha256)throw Error('Source video hash mismatch');
    verified.add(identity);
  }
}
function scopeFor(s,observation,step,runDir,scope){
  if(!s.textIndex||!s.textIndexSha256)return null;
  const query=(observation.publicText??'').match(/Question:\s*([^\n]+)/)?.[1]??'';
  const key=JSON.stringify([s.sha256,s.textIndexSha256,query,step]);
  if(!scopeCache.has(key)){
    const bytes=fs.readFileSync(s.textIndex);
    if(createHash('sha256').update(bytes).digest('hex')!==s.textIndexSha256)throw Error('OCR index hash mismatch');
    const idx=JSON.parse(bytes);
    if(idx.mediaSha256!==s.sha256||idx.questionIndependent!==true)throw Error('OCR source provenance mismatch');
    scopeCache.set(key,scope.run('adaptiveAcquisition',()=>adaptiveAcquisition({mode:'locate_text_scope',source:`obs-${step}`,query,rows:idx.rows,scanGapSeconds:idx.scanGapSeconds,mediaSha256:s.sha256})));
  }
  const plan=scopeCache.get(key),logKey=JSON.stringify([runDir,key]);
  if(runDir&&!loggedScopes.has(logKey)){
    fs.appendFileSync(path.join(runDir,'scope-module-calls.jsonl'),JSON.stringify({step,moduleId:owner,entry:'modules/adaptiveAcquisition.mjs',inputMode:'locate_text_scope',input:{source:`obs-${step}`,query,textIndexSha256:s.textIndexSha256},output:plan})+'\n');loggedScopes.add(logKey);
  }
  return plan;
}
function sourceFor(observation){
  const registry=process.env.H0_PUBLIC_VIDEO_REGISTRY;
  if(!registry)return null;
  const hashes=(observation.frames??[]).map(f=>f.sha256);
  if(!hashes.length)return null;
  const source=JSON.parse(fs.readFileSync(registry)).sources.find(s=>
    s.deliveredSha256.length===hashes.length&&hashes.every((h,i)=>h===s.deliveredSha256[i]));
  if(!source)return null;
  for(const key of ['path','textIndex','personModel'])if(source[key])source[key]=path.resolve(path.dirname(registry),source[key]);
  source.visionPython??=process.env.VISION_PYTHON??process.env.PYTHON??(process.platform==='win32'?'python':'python3');
  return source;
}
export function sourceAcquisitionNotice(observation,step,scope,runDir){
  if(!scope.has(owner))return null;
  const s=sourceFor(observation);if(!s)return null;
  const scopePlan=scopeFor(s,observation,step,runDir,scope);
  const candidate=scopePlan?.status==='candidate_scope_located'?scopePlan.candidates[0]:null;
  return {source:`obs-${step}`,moduleId:owner,mode:'acquire_public_video',scopePlan,
    firstScopePass:candidate?{startSeconds:candidate.startSeconds,endSeconds:candidate.endSeconds,supportedGapSeconds:Number(((candidate.endSeconds-candidate.startSeconds)/95+2/s.fps).toFixed(3)),instruction:'Verify both heading images, then inspect this whole candidate subsection once. The module allocates up to 96 samples for a count question. Use the second call for uncertain transitions inside it.'}:null,
    mediaId:s.id,durationSeconds:s.durationSeconds,
    deliveredFrameTimes:s.deliveredTimes.map((t,index)=>({index,seconds:Number(t.toFixed(3))})),
    maxFramesPerCall:96,maxCallsPerNativeStep:2,
    scope:'Supplemental original-video condition: original delivered frames remain unchanged. The host offers read-only source decoding and an independently computed public OCR index. OCR is fallible; verify attached heading images. No audio or event-count detector is available. The module audits requested intervals against unique candidate boundaries before scheduling dense samples.',
    usage:'consult_capability_path input={mode:"acquire_public_video",source:"obs-N",startSeconds:...,endSeconds:...,maxFrameGap:...,reason:"visible boundary or unresolved transition"}. Use coarse views to locate the requested subsection, then dense local views to distinguish complete repeated events. Do not span unrelated intervals just because isolated poses look alike. At most 96 frames per call; narrow the interval if the requested gap exceeds this budget.'};
}
export function sourceScopeEvidence({observation,step,runDir,activeBranch,scope}){
  if(!scope.has(owner))return null;
  const s=sourceFor(observation);if(!s)return null;
  const scopePlan=scopeFor(s,observation,step,runDir,scope);
  if(scopePlan?.status!=='candidate_scope_located')return null;
  verifyMedia(s);
  const times=scopePlan.candidates[0].witnesses.map(w=>w.seconds);
  const relative=`public-source/scope-${step}`,outDir=path.join(runDir,relative);fs.mkdirSync(outDir,{recursive:true});
  const decoded=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/decode-public-source.py',import.meta.url))],{
    input:JSON.stringify({input:s.path,outDir,times,expectedFps:s.fps,expectedFrameCount:s.frameCount}),encoding:'utf8',timeout:60000,maxBuffer:1024*1024}));
  return {moduleId:owner,scopePlan,sourceSha256:s.sha256,frames:decoded.frames,imagePaths:decoded.sheets.map(f=>path.join(relative,f)),newEvidenceAcquired:true,
    instruction:'These actual source frames witness OCR candidate boundaries. Read the headings yourself; they do not state the answer or event count.'};
}
export function enableSourceAcquisition(tool){
  if(!process.env.H0_PUBLIC_VIDEO_REGISTRY)return tool;
  const schema={type:'object',additionalProperties:false,required:['mode','source','startSeconds','endSeconds','maxFrameGap','reason'],properties:{
    mode:{type:'string',enum:['acquire_public_video']},source:{type:'string',pattern:'^obs-[0-9]+$'},
    startSeconds:{type:'number',minimum:0},endSeconds:{type:'number',minimum:0},
    maxFrameGap:{type:'number',minimum:0.25,maximum:30},reason:{type:'string',minLength:1,maxLength:600},focus:{type:'string',enum:['person','full']}}};
  const old=tool.input_schema.properties.input;
  return {...tool,description:tool.description+' When PUBLIC_SOURCE_ACQUISITION is present, adaptiveAcquisition also supports acquire_public_video. This decodes additional original frames, not just a montage. Supply the current source, grounded startSeconds/endSeconds, maxFrameGap (0.25–30 seconds), and reason. Read returned timestamps, sampling gap and coverage; no semantic count is certified. When person focus is configured, count sequences show a prominent person candidate at native detail plus full context; focus:"full" requests the original full-frame presentation instead.',
    input_schema:{...tool.input_schema,properties:{...tool.input_schema.properties,input:{anyOf:[...(old.anyOf??[old]),schema]}}}};
}
export function acquirePublicSource(args,{observation,step,runDir,activeBranch,scope,index}){
  try{
    if(args.moduleId!==owner||!scope.has(owner))throw Error('Source acquisition outside active module path');
    const q=args.input,s=sourceFor(observation);
    if(!s||q.source!==`obs-${step}`)throw Error('No hash-bound original source for current observation');
    if(![q.startSeconds,q.endSeconds,q.maxFrameGap].every(Number.isFinite)||q.startSeconds<0||q.endSeconds<=q.startSeconds||q.endSeconds>(s.frameCount-1)/s.fps||q.maxFrameGap<.25||q.maxFrameGap>30||typeof q.reason!=='string'||!q.reason.trim()||q.reason.length>600)throw Error('Invalid interval, density or sourced reason');
    verifyMedia(s);
    scope.require(owner);
    const scopePlan=scopeFor(s,observation,step,runDir,scope),ledger=path.join(runDir,'source-module-calls.jsonl');
    const prior=fs.existsSync(ledger)?fs.readFileSync(ledger,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
    const hasScopeOverview=prior.some(r=>r.step===step&&r.executed&&r.output?.scopeOverview===true);
    const scopeAudit=scope.run('adaptiveAcquisition',()=>adaptiveAcquisition({mode:'audit_scope_request',scopePlan,startSeconds:q.startSeconds,endSeconds:q.endSeconds,hasScopeOverview}));
    if(scopeAudit.status==='review_scope'){
      fs.appendFileSync(ledger,JSON.stringify({step,moduleId:owner,inputMode:'audit_scope_request',input:q,output:scopeAudit,executed:false})+'\n');
      return {ok:false,moduleId:owner,error:'Requested scope conflicts with visible heading evidence. Check the heading frames and the recommended interval before local refinement.',scopeAudit,noWorldActionExecuted:true};
    }
    const first=Math.floor(q.startSeconds*s.fps)/s.fps,last=Math.ceil(q.endSeconds*s.fps)/s.fps;

    const scopeOverview=scopeAudit.status==='consistent_with_candidate_scope'&&!hasScopeOverview;
    const isCount=/how many times|number of times|count.*(?:occurrences|repetitions)/i.test(observation.publicText??'');
    const minFrames=scopeOverview&&isCount?Math.min(96,Math.floor((last-first)*s.fps)+1):2;
    const requirement={id:`video-gap-${step}-${index}`,source:q.source,channel:'visual',start:first,end:last,maxFrameGap:q.maxFrameGap-1/s.fps,minFrames};
    const offer={id:s.id,source:q.source,tool:'decode_registered_public_video',channel:'visual',start:0,end:(s.frameCount-1)/s.fps,cost:1,maxFrames:96};
    const input={requirements:[requirement],offers:[offer],budget:2,submitCost:1,maxFrames:96};
    const plan=scope.run('adaptiveAcquisition',()=>adaptiveAcquisition(input));
    if(!plan.next){
      fs.appendFileSync(path.join(runDir,'source-module-calls.jsonl'),JSON.stringify({step,moduleId:owner,inputMode:'plan_acquisition',reason:q.reason,input,plan,executed:false})+'\n');
      return {ok:false,moduleId:owner,error:'Requested interval cannot fit the sample budget. Narrow it; the host will not silently undersample.',maxSpanSeconds:95*(q.maxFrameGap-1/s.fps),plan,noWorldActionExecuted:true};
    }
    const relative=`public-source/step-${step}-${index}`,outDir=path.join(runDir,relative);fs.mkdirSync(outDir,{recursive:true});
    const decoded=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/decode-public-source.py',import.meta.url))],{
      input:JSON.stringify({input:s.path,outDir,times:plan.next.parameters.times,expectedFps:s.fps,expectedFrameCount:s.frameCount,saveNativeFrames:!!(isCount&&q.focus!=='full'&&s.personModel)}),encoding:'utf8',timeout:60000,maxBuffer:2*1024*1024}));
    const receipt={source:s.id,receiptId:`source-${step}-${index}`,channel:'visual',requirementId:requirement.id,requirementSignature:plan.next.requirementSignature,acquired:true,times:decoded.frames.map(f=>f.seconds),region:[0,0,1,1]};

    const coverage=auditCoverage({requirements:[{...requirement,maxFrameGap:q.maxFrameGap}],delivered:[{...receipt,requirementSignature:requirementSignature({...requirement,maxFrameGap:q.maxFrameGap})}]});
    const result={ok:true,moduleId:owner,output:{source:q.source,mediaId:s.id,mediaSha256:s.sha256,plan,receipt,coverage,scopeAudit,scopeOverview,sequenceId:receipt.receiptId,
      frames:decoded.frames,sheets:decoded.sheets,newEvidenceAcquired:true,semanticCoverageVerified:false,
      nextEvidenceAudit:isCount?{moduleId:'eventLedger',mode:'audit_public_sequence',source:q.source,sequenceId:receipt.receiptId,totalSamples:decoded.frames.length,instruction:'Before answering, scan every sample in order and label all of them using consecutive segments {first:sampleIndex,last:sampleIndex,state:target|other|uncertain}. Target is the requested actor performing the requested action; ignore inset clips. Do not count held poses repeatedly. A new performance after return to a non-target state is a new event. Submit the segments to the event ledger using the remaining auxiliary call. Do not skip the first isolated demonstration or later demonstrations inside the same requested subsection.'}:null,
      warning:'Supplemental original-video samples. A delivered time range is not a proven count. Distinguish complete cycles by renewed onset after completion; keep section boundaries and inset content separate.'},
      imagePaths:decoded.sheets.map(f=>path.join(relative,f)),noWorldActionExecuted:true,newEvidenceAcquired:true};
    if(isCount&&q.focus!=='full'&&s.personModel&&s.visionPython){
      if(createHash('sha256').update(fs.readFileSync(s.personModel)).digest('hex')!==s.personModelSha256)throw Error('Person model hash mismatch');
      const inputs=decoded.frames.map(f=>({...f,path:path.join(outDir,f.nativePath),sha256:f.nativeSha256}));
      const detection=JSON.parse(execFileSync(s.visionPython,[fileURLToPath(new URL('../../../module-harness/src/detect-public-people.py',import.meta.url))],{input:JSON.stringify({frames:inputs,model:s.personModel,configDir:path.join(outDir,'detector-config')}),encoding:'utf8',timeout:60000,maxBuffer:2*1024*1024}));
      const focusPlan=scope.run('adaptiveAcquisition',()=>adaptiveAcquisition({mode:'plan_actor_focus',frames:detection.frames}));
      const focused=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/render-actor-focus.py',import.meta.url))],{input:JSON.stringify({frames:inputs,selected:focusPlan.selected,outDir:path.join(outDir,'actor-focus')}),encoding:'utf8',timeout:30000,maxBuffer:1024*1024}));
      result.output.actorFocus={...focusPlan,rendering:focused,modelSha256:s.personModelSha256};
      result.imagePaths=focused.sheets.map(f=>path.join(relative,'actor-focus',f));
      fs.appendFileSync(path.join(runDir,'focus-module-calls.jsonl'),JSON.stringify({step,moduleId:owner,inputMode:'plan_actor_focus',detections:detection.frames,output:focusPlan})+'\n');
    }
    fs.appendFileSync(path.join(runDir,'source-module-calls.jsonl'),JSON.stringify({step,moduleId:owner,entry:'modules/adaptiveAcquisition.mjs',inputMode:'plan_acquisition',reason:q.reason,input,output:result.output,executed:true})+'\n');
    return result;
  }catch(e){return {ok:false,moduleId:args.moduleId,error:e.message,noWorldActionExecuted:true};}
}
