

const faces=['U','R','F','D','L','B'];
const slots=faces.flatMap(face=>Array.from({length:9},(_,i)=>{
  const r=Math.floor(i/3),c=i%3;
  const geometry={U:[[c-1,1,r-1],[0,1,0]],R:[[1,1-r,1-c],[1,0,0]],F:[[c-1,1-r,1],[0,0,1]],D:[[c-1,-1,1-r],[0,-1,0]],L:[[-1,1-r,c-1],[-1,0,0]],B:[[1-c,1-r,-1],[0,0,-1]]};
  return {position:geometry[face][0],normal:geometry[face][1]};
}));
const key=s=>s.position.join(',')+'/'+s.normal.join(',');
const index=new Map(slots.map((s,i)=>[key(s),i]));
const axes={R:[0,1],L:[0,-1],U:[1,1],D:[1,-1],F:[2,1],B:[2,-1]};
const rotate=([x,y,z],a,s)=>a===0?(s===1?[x,z,-y]:[x,-z,y]):a===1?(s===1?[-z,y,x]:[z,y,-x]):s===1?[y,-x,z]:[-y,x,z];
export const wcaOperators=Object.entries(axes).flatMap(([id,[a,s]])=>{
  const p=slots.map((v,i)=>v.position[a]!==s?i:index.get(key({position:rotate(v.position,a,s),normal:rotate(v.normal,a,s)})));
  return [[id,1],[id+'2',2],[id+"'",3]].map(([id,k])=>({id,permutation:slots.map((_,i)=>{let j=i;for(let n=0;n<k;n++)j=p[j];return j;})}));
});
export function wcaPublicModel(text,source){
  let data;try{data=JSON.parse(text);}catch{return null;}
  if(!data||typeof data!=='object'||Array.isArray(data)||!data.faces||!faces.every(f=>Array.isArray(data.faces[f])&&data.faces[f].length===3&&data.faces[f].every(r=>typeof r==='string'&&r.length===3)))return null;
  const state=faces.flatMap(f=>[...data.faces[f].join('')]);
  const centers=faces.map(f=>data.faces[f][1][1]);
  if(new Set(centers).size!==6)return null;
  return {mode:'reversible_permutation',state,goal:centers.flatMap(c=>Array(9).fill(c)),operators:wcaOperators,
    maxDepth:Math.min(8,data.movesRemaining??8),maxStates:150000,source};
}
