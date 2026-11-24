import {inspectPublicFrame,visualOwners} from './public-frame-inspection.mjs';
export function automaticVisualEvidence({observation,step,runDir,activeBranch,scope}){
 const moduleId=activeBranch.find(x=>visualOwners.includes(x.moduleId))?.moduleId;
 const frames=observation.frames?.length?observation.frames:observation.frame?[observation.frame]:[];
 if(!moduleId||!frames.length)return [];
 const base={observation,step,runDir,activeBranch,scope};
 if(frames.length>4)return Array.from({length:Math.ceil(frames.length/8)},(_,i)=>inspectPublicFrame({moduleId,input:{mode:'inspect_public_sequence',source:`obs-${step}`,frameIndices:Array.from({length:Math.min(8,frames.length-i*8)},(_,j)=>i*8+j)}},{...base,index:`automatic-sequence-${i}`}));

 return [[0,0,.5,.5],[.5,0,.5,.5],[0,.5,.5,.5],[.5,.5,.5,.5]].map((box,i)=>inspectPublicFrame({moduleId,input:{mode:'inspect_public_frame',source:`obs-${step}`,frameIndex:0,box}},{...base,index:`automatic-anchor-${i}`}));
}
