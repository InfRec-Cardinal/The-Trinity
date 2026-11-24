import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';
import adaptiveAcquisition from '../../../module-harness/modules/adaptiveAcquisition.mjs';
export const visualOwners=['evidenceDiagnosis','evidenceCommit','adaptiveAcquisition'];
export function enableFrameInspection(tool,branch){
 const owners=branch.filter(x=>visualOwners.includes(x.moduleId)).map(x=>x.moduleId);if(!owners.length)return tool;
 const schema={type:'object',additionalProperties:false,required:['mode','source','frameIndex','box'],properties:{mode:{type:'string',enum:['inspect_public_frame']},source:{type:'string',pattern:'^obs-[0-9]+$'},frameIndex:{type:'integer',minimum:0},box:{type:'array',minItems:4,maxItems:4,items:{type:'number',minimum:0,maximum:1}}}};
 const sequenceSchema={type:'object',additionalProperties:false,required:['mode','source'],properties:{mode:{type:'string',enum:['inspect_public_sequence']},source:{type:'string',pattern:'^obs-[0-9]+$'},frameIndices:{type:'array',minItems:1,maxItems:12,items:{type:'integer',minimum:0}}}};
 return {...tool,description:tool.description+'\nPublic visual inspection mode for '+owners.join(', ')+': input={mode:"inspect_public_frame",source:"obs-N",frameIndex:0,box:[left,top,width,height]}. Zero-based frameIndex addresses CURRENT delivered frames only. Box uses normalized fractions inferred from the current image, never stored coordinates. Returns a crop enlarged from existing pixels, not a new view, detector, independent interpretation or new evidence. Use to resolve small distinguishing detail or bind a part to its subject before answering. At most two auxiliary calls per native step. Alternative mode inspect_public_sequence with source and optional frameIndices (up to 12) returns a labelled contact sheet of current delivered frames. Omit frameIndices to sample the whole delivered sequence uniformly; then use frame indices to inspect a relevant subsequence. No new video frames are acquired. For adaptiveAcquisition sequence inspections, supplied indices are candidate anchors: its actual selection algorithm retains diverse anchors, retrieves temporally separated appearance candidates for relational questions, and adds boundary context within twelve frames. For repeated-action count questions it preserves local chronology and inspects interval boundaries instead of retrieving later repeats. Read selectionPlan and the returned frame labels; similarity does not certify identity.',input_schema:{...tool.input_schema,properties:{...tool.input_schema.properties,input:{anyOf:[tool.input_schema.properties.input,schema,sequenceSchema]}}}};
}
export function inspectPublicFrame(args,{observation,step,runDir,activeBranch,scope,index}){
 try{
  if(!scope.has(args.moduleId)||!visualOwners.includes(args.moduleId))throw Error('Visual mode outside selected module path');
  const q=args.input;if(q.source!==`obs-${step}`)throw Error('Inspection requires the current public observation');
  const frames=observation.frames?.length?observation.frames:observation.frame?[observation.frame]:[];
  if(q.mode==='inspect_public_sequence'){
   if(!frames.length)throw Error('No delivered frames');
   let chosen=q.frameIndices??[...new Set(Array.from({length:Math.min(12,frames.length)},(_,i)=>Math.round(i*(frames.length-1)/Math.max(1,Math.min(12,frames.length)-1))))];
   if(!Array.isArray(chosen)||chosen.length>12||chosen.some(i=>!Number.isSafeInteger(i)||!frames[i]))throw Error('Invalid delivered frame indices');
   let selectionPlan=null;
   if(args.moduleId==='adaptiveAcquisition'&&!String(index).startsWith('automatic-')){
    const catalogSources=frames.map((f,index)=>{const input=path.resolve(runDir,f.path);if(!input.startsWith(path.resolve(runDir)+path.sep))throw Error('Frame path outside episode');const sha256=createHash('sha256').update(fs.readFileSync(input)).digest('hex');if(f.sha256&&sha256!==f.sha256)throw Error('Frame hash mismatch');return {index,path:input,sha256};});
    const query=(observation.publicText??'').match(/Question:\s*([^\n]+)/)?.[1]??'';
    const purpose=/how many times|number of times|count.*(?:occurrences|repetitions)/i.test(query)?'temporal_count':'relational';
    const catalog=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/public-frame-descriptors.py',import.meta.url))],{input:JSON.stringify({frames:catalogSources,query}),encoding:'utf8',timeout:60000,maxBuffer:4*1024*1024}));
    selectionPlan=scope.run('adaptiveAcquisition',()=>adaptiveAcquisition({mode:'select_delivered_frames',source:q.source,frames:catalog.frames,proposed:chosen,limit:12,purpose}));
    chosen=selectionPlan.frameIndices;
    fs.appendFileSync(path.join(runDir,'selector-module-calls.jsonl'),JSON.stringify({step,moduleId:args.moduleId,entry:'modules/adaptiveAcquisition.mjs',inputMode:'select_delivered_frames',descriptorMethod:catalog.method,input:{source:q.source,query,purpose,proposed:q.frameIndices??null,sourceHashes:catalog.frames.map(({index,sha256})=>({index,sha256}))},output:selectionPlan})+'\n');
   }
   const sources=chosen.map(index=>{const f=frames[index],input=path.resolve(runDir,f.path);if(!input.startsWith(path.resolve(runDir)+path.sep))throw Error('Frame path outside episode');const sha=createHash('sha256').update(fs.readFileSync(input)).digest('hex');if(f.sha256&&f.sha256!==sha)throw Error('Frame hash mismatch');return {index,path:input,sha256:sha};});
   const relative=`public-inspections/sequence-${step}-${index}.jpg`,output=path.join(runDir,relative);fs.mkdirSync(path.dirname(output),{recursive:true});
   const detail=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/public-sequence-inspection.py',import.meta.url))],{input:JSON.stringify({frames:sources,output}),encoding:'utf8',timeout:10000}));
   return {ok:true,moduleId:args.moduleId,output:{...detail,source:q.source,totalDeliveredFrames:frames.length,selectionPlan,sourceHashes:sources.map(f=>({index:f.index,sha256:f.sha256}))},imagePath:relative,noWorldActionExecuted:true};
  }
  if(!Number.isSafeInteger(q.frameIndex)||!frames[q.frameIndex])throw Error('No such delivered frame');
  if(!Array.isArray(q.box)||q.box.length!==4||q.box.some(v=>!Number.isFinite(v)||v<0||v>1))throw Error('Invalid normalized region');
  const f=frames[q.frameIndex],input=path.resolve(runDir,f.path);if(!input.startsWith(path.resolve(runDir)+path.sep))throw Error('Frame path outside episode');
  const data=fs.readFileSync(input),sha=createHash('sha256').update(data).digest('hex');if(f.sha256&&f.sha256!==sha)throw Error('Delivered frame hash mismatch');
  const relative=`public-inspections/step-${step}-${index}.png`,output=path.join(runDir,relative);fs.mkdirSync(path.dirname(output),{recursive:true});
  const detail=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('../../../module-harness/src/public-frame-inspection.py',import.meta.url))],{input:JSON.stringify({input,output,box:q.box}),encoding:'utf8',timeout:10000}));
  return {ok:true,moduleId:args.moduleId,output:{...detail,source:q.source,frameIndex:q.frameIndex,sourceSha256:sha,derivedSha256:createHash('sha256').update(fs.readFileSync(output)).digest('hex')},imagePath:relative,noWorldActionExecuted:true};
 }catch(e){return {ok:false,moduleId:args.moduleId,error:e.message,noWorldActionExecuted:true};}
}
