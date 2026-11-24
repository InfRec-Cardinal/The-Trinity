

const dirs=[[-1,0,'west'],[1,0,'east'],[0,-1,'north'],[0,1,'south']];
class Heap{a=[];push(x){let a=this.a,i=a.length;a.push(x);while(i){let p=(i-1)>>1;if(a[p].cost<=x.cost)break;a[i]=a[p];i=p;}a[i]=x;}pop(){let a=this.a,r=a[0],x=a.pop();if(a.length){let i=0;while(i*2+1<a.length){let j=i*2+1;if(j+1<a.length&&a[j+1].cost<a[j].cost)j++;if(a[j].cost>=x.cost)break;a[i]=a[j];i=j;}a[i]=x;}return r;}}
export default function gridPush({grid,glyphs={wall:'#',floor:' ',box:'$',goal:'.',player:'@',boxOnGoal:'*',playerOnGoal:'+'},goalMode='occupy',budget=100,maxStates=50000}){
 if(!['occupy','consume'].includes(goalMode))throw Error('Public goalMode required');
 if(!Array.isArray(grid)||!grid.length||grid.length>50||grid.some(x=>typeof x!=='string'||x.length!==grid[0].length)||grid[0].length>100)throw Error('Rectangular public grid required');
 if(!Number.isSafeInteger(budget)||budget<0||budget>1000)throw Error('Invalid public action budget');
 const w=grid[0].length,h=grid.length,walk=new Set(),boxes=[],goals=[];let player;
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){
  const c=grid[y][x],id=y*w+x,has=k=>(glyphs[k]??'').includes(c);
  if(has('wall'))continue;
  if(!['floor','box','goal','player','boxOnGoal','playerOnGoal'].some(has))continue;
  walk.add(id);if(has('box')||has('boxOnGoal'))boxes.push(id);if(has('goal')||has('boxOnGoal')||has('playerOnGoal'))goals.push(id);
  if(has('player')||has('playerOnGoal')){if(player!==undefined)throw Error('Multiple players');player=id;}
 }
 if(player===undefined||boxes.length!==goals.length||boxes.length>8)throw Error('One player and equal public boxes/goals required (up to eight)');
 const adj=(a,d,k=1)=>{let x=a%w+d[0]*k,y=Math.floor(a/w)+d[1]*k;return x<0||x>=w||y<0||y>=h?-1:y*w+x;};
 const good=new Set(goals),reverse=[...goals];for(let i=0;i<reverse.length;i++)for(const d of dirs){const p=adj(reverse[i],d,-1),stand=adj(reverse[i],d,-2);if(walk.has(p)&&walk.has(stand)&&!good.has(p)){good.add(p);reverse.push(p);}}
 const reachable=(p,bs)=>{let paths=new Map([[p,[]]]),q=[p];for(let i=0;i<q.length;i++)for(const d of dirs){let n=adj(q[i],d);if(walk.has(n)&&!bs.has(n)&&!paths.has(n)){paths.set(n,[...paths.get(q[i]),d[2]]);q.push(n);}}return paths;};
 const key=s=>[s.player,[...s.boxes].sort((a,b)=>a-b).join(','),[...s.goals].sort((a,b)=>a-b).join(',')].join('|');
 let initial={player,boxes:new Set(boxes),goals:new Set(goals),cost:0,path:[]};const queue=new Heap(),seen=new Map([[key(initial),0]]);queue.push(initial);let visited=0;
 while(queue.a.length&&visited<maxStates){
  const s=queue.pop();if(s.cost!==seen.get(key(s)))continue;visited++;
  if(goalMode==='consume'?!s.goals.size:[...s.boxes].every(x=>s.goals.has(x))){
    let recommendation=null;
    if(s.path.length){
      const d=dirs.find(x=>x[2]===s.path[0]),dest=adj(initial.player,d),after=new Set(initial.boxes),remainingGoals=new Set(initial.goals);
      const pushed=after.has(dest);
      if(pushed){after.delete(dest);const target=adj(dest,d);if(goalMode==='consume'&&remainingGoals.has(target))remainingGoals.delete(target);else after.add(target);}
      recommendation={direction:d[2],predictedPlayer:dest,predictedBoxes:[...after].sort((a,b)=>a-b),predictedGoals:[...remainingGoals].sort((a,b)=>a-b),gridWidth:w,push:pushed};
    }
    return {status:'plan',actions:s.path,steps:s.cost,states:visited,goalMode,recommendation,spareActions:budget-s.cost,scope:'Exact only for supplied public grid and push-only model; verify every native successor before continuing.'};
  }
  const paths=reachable(s.player,s.boxes);
  for(const box of s.boxes)for(const d of dirs){
   let stand=adj(box,d,-1),dest=adj(box,d);if(!paths.has(stand)||!walk.has(dest)||s.boxes.has(dest)||!good.has(dest))continue;
   const segment=[...paths.get(stand),d[2]],cost=s.cost+segment.length;if(cost>budget)continue;
   const nb=new Set(s.boxes),ng=new Set(s.goals);nb.delete(box);
   if(goalMode==='consume'&&ng.has(dest))ng.delete(dest);else nb.add(dest);
   const next={player:box,boxes:nb,goals:ng,cost,path:[...s.path,...segment]},k=key(next);
   if((seen.get(k)??Infinity)<=cost)continue;seen.set(k,cost);queue.push(next);
  }
 }
 return {status:queue.a.length?'search_limit':'no_plan_within_budget',states:visited,scope:'Only the supplied public model was searched; verify parsing and native mechanics. This is not an environment verdict.'};
}
