import fs from 'node:fs';import path from 'node:path';
import {fileURLToPath} from 'node:url';import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';
import eventLedger from '../../../module-harness/modules/eventLedger.mjs';
const owner='eventLedger';
export function pendingSequenceCorrection({step,runDir,activeBranch,scope}){
  if(!scope.has(owner))return null;
  const p=path.join(runDir,'event-ledger-calls.jsonl');if(!fs.existsSync(p))return null;
  const last=fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).findLast(r=>r.step===step);
  if(!last||last.output.count!==null||!last.output.visualAudit?.inspectSamples?.length||last.output.visualReview)return null;
  return {sequenceId:last.sequenceId,source:`obs-${step}`,reviewedSamples:last.output.visualAudit.inspectSamples,
    noWorldActionExecuted:true,
    note:'The visual-label review has withdrawn the exact count. One bounded correction call is available before the native answer. Inspect the already supplied review images and return the complete corrected partition to '+owner+' with mode audit_public_sequence, the same source and sequenceId, segments, and reviewedSamples containing the listed indices. Preserve labels outside your actual corrections. You may keep a label if the image supports it; do not add a repetition just because it was suggested. The module will recompute from your revised public observations. No extra images will be acquired.'};
}
export function reviewPublicSequence({observation,step,runDir,activeBranch,scope,alreadyReviewed,auxiliaryCalls}){
  if(alreadyReviewed||auxiliaryCalls>=2||!scope.has(owner)||!/how many times|number of times|count.*(?:occurrences|repetitions)/i.test(observation.publicText??''))return null;
  const p=path.join(runDir,'source-module-calls.jsonl');if(!fs.existsSync(p))return null;
  const row=fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).findLast(r=>r.step===step&&r.executed&&r.output?.scopeOverview);
  if(!row)return null;
  const ledger=path.join(runDir,'event-ledger-calls.jsonl');
  if(fs.existsSync(ledger)&&fs.readFileSync(ledger,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse).some(r=>r.sequenceId===row.output.sequenceId))return null;
  return scope.run('eventLedger',()=>eventLedger({mode:'request_sequence_audit',source:`obs-${step}`,sequenceId:row.output.sequenceId,sampleCount:row.output.frames.length}));
}
export function enableEventLedger(tool,activeBranch){
  if(!activeBranch.some(m=>m.moduleId===owner))return tool;
  const schema={type:'object',additionalProperties:false,required:['mode','source','sequenceId','segments'],properties:{
    mode:{type:'string',enum:['audit_public_sequence']},source:{type:'string',pattern:'^obs-[0-9]+$'},sequenceId:{type:'string'},
    reviewedSamples:{type:'array',maxItems:12,uniqueItems:true,items:{type:'integer',minimum:0,maximum:95}},
    segments:{type:'array',maxItems:256,items:{type:'object',additionalProperties:false,required:['first','last','state'],properties:{first:{type:'integer',minimum:0},last:{type:'integer',minimum:0},state:{type:'string',enum:['target','other','uncertain']}}}}}};
  const old=tool.input_schema.properties.input;
  return {...tool,description:tool.description+' Repeated-action questions additionally support '+owner+' with input {mode:"audit_public_sequence",source:"obs-N",sequenceId:"the returned acquisition sequenceId",segments:[{first:0,last:...,state:"other|target|uncertain"},...]}. Label every returned sample index in chronological order. target means the requested actor is performing the requested movement; other means not performing it. Merge held poses, keep a restarted movement distinct. This is a public evidence table, not private reasoning. The host checks actual source frame references and the module counts contiguous runs; it cannot verify the visual labels.',
    input_schema:{...tool.input_schema,properties:{...tool.input_schema.properties,input:{anyOf:[...(old.anyOf??[old]),schema]}}}};
}
export function auditPublicSequence(args,{step,runDir,activeBranch,scope}){
  try{
    if(args.moduleId!==owner||!scope.has(owner))throw Error('Event ledger outside active path');
    const q=args.input;if(q.source!==`obs-${step}`)throw Error('Current observation required');
    const logfile=path.join(runDir,'source-module-calls.jsonl');
    const rows=fs.existsSync(logfile)?fs.readFileSync(logfile,'utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
    const row=rows.find(r=>r.step===step&&r.executed&&r.output?.sequenceId===q.sequenceId);
    if(!row)throw Error('No such acquired public sequence');
    const input={mode:'count_repeated_events',source:q.source,frames:row.output.frames,segments:q.segments};
    const pending=pendingSequenceCorrection({step,runDir,activeBranch,scope});
    const isCorrection=Boolean(pending);
    if(isCorrection&&(q.sequenceId!==pending.sequenceId||!Array.isArray(q.reviewedSamples)||
      q.reviewedSamples.length>12||new Set(q.reviewedSamples).size!==q.reviewedSamples.length||
      q.reviewedSamples.some(i=>!Number.isInteger(i)||i<0||i>=row.output.frames.length)||
      pending.reviewedSamples.some(i=>!q.reviewedSamples.includes(i))))throw Error('The one correction must acknowledge every supplied review sample and the same sequence');
    if(!isCorrection&&q.reviewedSamples!==undefined)throw Error('No pending visual-label review for these samples');
    let output=scope.run('eventLedger',()=>eventLedger(input)),imagePaths=[],descriptorArtifact=null;
    if(isCorrection){
      const prior=fs.readFileSync(path.join(runDir,'event-ledger-calls.jsonl'),'utf8').trim().split('\n').map(JSON.parse).findLast(r=>r.step===step);
      const labelAt=(segments,i)=>segments.find(s=>s.first<=i&&s.last>=i)?.state??null;
      output.visualReview={reviewedSamples:q.reviewedSamples,claimedByPlayer:true,independentlyVerified:false,
        changedSamples:row.output.frames.flatMap((_,i)=>labelAt(prior.input.segments,i)!==labelAt(q.segments,i)?[i]:[]),
        priorProvisionalCount:prior.output.provisionalCount,recomputedConditionalCount:output.count,
        oneCorrectionOnly:true,newImages:0};
    }
    if(!isCorrection&&output.structuralAuditComplete&&(output.events.length>=2||output.events.some(e=>e.last-e.first>=2))&&row.output.actorFocus){
      const match=/^source-(\d+)-(\d+)$/.exec(q.sequenceId);if(!match||Number(match[1])!==step)throw Error('Invalid host sequence identity');
      const sourceDir=path.join(runDir,'public-source',`step-${step}-${match[2]}`);
      const crops=row.output.frames.map((f,index)=>{
        const p=path.join(sourceDir,f.nativePath),sha=createHash('sha256').update(fs.readFileSync(p)).digest('hex');
        if(sha!==f.nativeSha256)throw Error('Native source pixels changed before event audit');
        return {...f,index,path:p,sha256:sha,box:row.output.actorFocus.selected[index].box};
      });
      const encoded=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/public-frame-descriptors.py',import.meta.url))],{input:JSON.stringify({frames:crops,query:'a person performing a movement'}),encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024}));
      descriptorArtifact=`public-source/step-${step}-${match[2]}/continuity-descriptors.json`;
      fs.writeFileSync(path.join(runDir,descriptorArtifact),JSON.stringify(encoded));
      output=scope.run('eventLedger',()=>eventLedger({...input,descriptors:encoded.frames}));
      const inspect=output.visualAudit?.inspectSamples??[];
      if(inspect.length){
        if(inspect.length>12)throw Error('Visual review exceeds bounded image budget');
        const subset=inspect.map(i=>crops[i]),selected=inspect.map(i=>row.output.actorFocus.selected[i]);
        const relative=`public-source/step-${step}-${match[2]}/continuity-review`;
        const rendered=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/render-actor-focus.py',import.meta.url))],{input:JSON.stringify({frames:subset,selected,outDir:path.join(runDir,relative)}),encoding:'utf8',timeout:30000,maxBuffer:1024*1024}));
        imagePaths=rendered.sheets.map(f=>path.join(relative,f));
      }
    }
    fs.appendFileSync(path.join(runDir,'event-ledger-calls.jsonl'),JSON.stringify({step,moduleId:owner,entry:'modules/eventLedger.mjs',sequenceId:q.sequenceId,input,descriptorArtifact,output,imagePaths})+'\n');
    return {ok:true,moduleId:owner,output,imagePaths,noWorldActionExecuted:true,
      evidenceCaption:'Label consistency review from the same acquired public sequence. Global sample indices and timestamps are preserved. The tool lists continuity candidates and excluded-frame candidates with their reference indices. Compare the excluded samples with their neighbors and labelled reference; a similar pose is not necessarily the same movement. Review actual resets and starts. These cues supply no event count or answer.'};
  }catch(e){return {ok:false,moduleId:owner,error:e.message,noWorldActionExecuted:true};}
}
