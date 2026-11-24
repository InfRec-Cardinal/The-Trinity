

export default function permutationPlan({state,goal,operators,maxDepth=8,maxStates=150000}) {
  if(!Array.isArray(state)||!Array.isArray(goal)||state.length!==goal.length||!state.length||state.length>128)throw Error('Equal nonempty public state/goal arrays required');
  if(!Array.isArray(operators)||!operators.length||operators.length>64)throw Error('Public reversible operators required');
  const n=state.length,values=[...new Set([...state,...goal])];
  if(values.some(x=>typeof x!=='string'))throw Error('Slot labels must be strings');
  const encode=s=>s.map(x=>String.fromCharCode(33+values.indexOf(x))).join('');
  const start=encode(state),target=encode(goal);
  if([...start].sort().join('')!==[...target].sort().join(''))throw Error('State and goal have different multisets');
  const ops=operators.map(o=>{
    const p=o.permutation;
    if(typeof o.id!=='string'||!Array.isArray(p)||p.length!==n||new Set(p).size!==n||p.some(x=>!Number.isInteger(x)||x<0||x>=n))throw Error('Invalid slot permutation');
    const inv=Array(n);p.forEach((v,i)=>inv[v]=i);return {id:o.id,p,inv};
  });
  const apply=(s,p)=>{const out=Array(n);for(let i=0;i<n;i++)out[p[i]]=s[i];return out.join('');};
  maxStates=Math.max(2,Math.min(Number(maxStates)||150000,300000));
  maxDepth=Math.max(0,Math.min(Number(maxDepth)||0,12));
  const a=new Map([[start,null]]),b=new Map([[target,null]]);
  let fa=[start],fb=[target],da=0,db=0,meet=start===target?start:null,capped=false;
  while(!meet&&da+db<maxDepth&&fa.length&&fb.length){
    const forward=fa.length<=fb.length,own=forward?a:b,other=forward?b:a,front=forward?fa:fb,next=[];
    outer:for(const s of front)for(let i=0;i<ops.length;i++){
      const t=apply(s,forward?ops[i].p:ops[i].inv);
      if(own.has(t))continue;
      own.set(t,{parent:s,op:i});
      if(other.has(t)){meet=t;break outer;}
      if(a.size+b.size>=maxStates){capped=true;break outer;}
      next.push(t);
    }
    if(forward){fa=next;da++;}else{fb=next;db++;}
    if(capped)break;
  }
  if(!meet)return {status:capped?'search_limit':'not_found_within_depth',path:null,visited:a.size+b.size,depth:da+db,noWorldActionExecuted:true};
  const path=[];let s=meet;
  while(a.get(s)){const r=a.get(s);path.push(r.op);s=r.parent;}path.reverse();s=meet;
  while(b.get(s)){const r=b.get(s);path.push(r.op);s=r.parent;}
  let end=start;for(const i of path)end=apply(end,ops[i].p);
  if(end!==target)throw Error('Internal plan verification failed');
  return {status:'planned',path:path.map(i=>ops[i].id),verifiedGoal:true,visited:a.size+b.size,depth:path.length,noWorldActionExecuted:true};
}
