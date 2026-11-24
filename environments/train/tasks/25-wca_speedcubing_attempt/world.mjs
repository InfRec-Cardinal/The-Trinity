                                                                                                          
                                                                                                                                   
import { Raster } from '../../lib/raster.mjs';
const FACES=['U','R','F','D','L','B'];
const stickers=FACES.flatMap(face=>Array.from({length:9},(_,i)=>{const r=Math.floor(i/3),c=i%3;const values={U:[[c-1,1,r-1],[0,1,0]],R:[[1,1-r,1-c],[1,0,0]],F:[[c-1,1-r,1],[0,0,1]],D:[[c-1,-1,1-r],[0,-1,0]],L:[[-1,1-r,c-1],[-1,0,0]],B:[[1-c,1-r,-1],[0,0,-1]]};return {face,position:values[face][0],normal:values[face][1]};}));
const key=s=>`${s.position.join(',')}/${s.normal.join(',')}`,indexBySticker=new Map(stickers.map((s,i)=>[key(s),i]));
const axis={R:[0,1],L:[0,-1],U:[1,1],D:[1,-1],F:[2,1],B:[2,-1],x:[0,1],y:[1,1],z:[2,1]};
const rotate=([x,y,z],a,sign)=>a===0?(sign===1?[x,z,-y]:[x,-z,y]):a===1?(sign===1?[-z,y,x]:[z,y,-x]):sign===1?[y,-x,z]:[-y,x,z];
const permutations=Object.fromEntries(Object.entries(axis).map(([move,[a,sign]])=>[move,stickers.map((s,i)=>{if(FACES.includes(move)&&s.position[a]!==sign)return i;return indexBySticker.get(key({position:rotate(s.position,a,sign),normal:rotate(s.normal,a,sign)}));})]));
export const solvedCube=()=>FACES.flatMap(face=>Array(9).fill(face));
export function applyWCAMoves(facelets,moves) {
  let current=facelets.slice();for(const token of moves){const p=permutations[token[0]],count=token.endsWith('2')?2:token.endsWith("'")?3:1;if(!p)throw new Error('Unknown WCA face move');for(let k=0;k<count;k++){const next=Array(54);for(let i=0;i<54;i++)next[p[i]]=current[i];current=next;}}return current;
}
export const isWCACubeSolved=facelets=>FACES.every((_,f)=>facelets.slice(f*9,f*9+9).every(color=>color===facelets[f*9]));
const tokens=text=>typeof text==='string'?text.trim().split(/\s+/):[];
export function normalize(input){if(!input||typeof input!=='object'||Array.isArray(input))return null;const keys=Object.keys(input).sort().join(',');if(input.action==='finish'&&keys==='action')return {action:'finish'};if(input.action!=='turn'||keys!=='action,moves')return null;const moves=tokens(input.moves);if(!moves.length||moves.length>20||moves.some(m=>!/^([FBRLUDxyz])('|2)?$/.test(m)))return null;return {action:'turn',moves:moves.join(' ')};}
export function createWCACube(instance){
  const initial=applyWCAMoves(solvedCube(),tokens(instance.scramble));if(instance.referenceFacelets&&initial.join('')!==instance.referenceFacelets)throw new Error('Cube reconstruction differs from recorded reference facelets');
  const state={step:0,facelets:initial,movesUsed:0,lastAppliedMoves:[],feedback:'Scrambled cube; no solution hints.',ended:false,outcome:null,reason:null};
  const end=reason=>{state.ended=true;state.reason=reason;state.outcome=isWCACubeSolved(state.facelets)&&state.movesUsed<=300?'success':'failure';};
  return {state,step(input){const action=normalize(input);if(!action)throw new Error('Malformed WCA action');if(state.ended)throw new Error('WCA attempt ended');state.step++;state.lastAppliedMoves=[];
    if(action.action==='finish'){end(isWCACubeSolved(state.facelets)?'solved':'DNF_unsolved');state.feedback='Attempt finished.';return;}
    for(const move of tokens(action.moves)){state.facelets=applyWCAMoves(state.facelets,[move]);state.lastAppliedMoves.push(move);if(FACES.includes(move[0]))state.movesUsed++;if(state.movesUsed===300){end('move_budget_exhausted');break;}}
    state.feedback=`Applied ${state.lastAppliedMoves.join(' ')}.`;if(!state.ended&&state.step>=60)end('action_budget_exhausted');},
    publicView(){const net=Object.fromEntries(FACES.map((face,f)=>[face,[0,1,2].map(r=>state.facelets.slice(f*9+r*3,f*9+r*3+3).join(''))]));return {text:JSON.stringify({task:'Solve all six cube faces in any orientation. turn:1–20 WCA face moves or x/y/z rotations; finish ends the attempt.',faces:net,movesUsedOBTM:state.movesUsed,movesRemaining:300-state.movesUsed,actionsRemaining:60-state.step,feedback:state.feedback}),terminal:{ended:state.ended,outcome:state.outcome,reason:state.reason,score:state.ended&&state.outcome==='success'?state.movesUsed:null,...(state.ended?{evaluation:{verdict:state.outcome==='success'?'solved':'DNF',movesUsedOBTM:state.movesUsed,scrambleDepth:instance.depth,randomStateScramble:instance.kind==='official_random_state',optimalSolutionLengthOBTM:instance.optimalLength}}:{})}};},
    render(){const r=new Raster(460,300),colors={U:[238,238,236],R:[207,54,49],F:[37,151,82],D:[244,212,49],L:[236,139,41],B:[43,107,191]},positions={U:[130,24],L:[28,118],F:[130,118],R:[232,118],B:[334,118],D:[130,212]};for(const [f,face] of FACES.entries()){const [xx,yy]=positions[face];r.text(face,xx-15,yy+20,[40,50,60],2);for(let i=0;i<9;i++)r.rect(xx+(i%3)*25,yy+Math.floor(i/3)*25,23,23,colors[state.facelets[f*9+i]]);}return r;}};
}
