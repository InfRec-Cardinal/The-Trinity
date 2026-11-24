import {equal} from './common.mjs';


export function visualRouteEvidence({frames, actions, phases, epochs, events}) {
 const sameAction=equal;
 const geometry=rows=>rows.slice(1,-1).map(r=>r.slice(1,-1)).join('|');
 const components=rows=>{
  const h=rows.length,w=rows[0].length,seen=new Uint8Array(h*w),result=[];
  for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
   const k=y*w+x;if(seen[k])continue;const color=rows[y][x],q=[k],pts=[];seen[k]=1;
   let left=x,right=x,top=y,bottom=y;
   for(let j=0;j<q.length;j++){
    const p=q[j],px=p%w,py=(p/w)|0;pts.push([px,py]);if(px<left)left=px;if(px>right)right=px;if(py<top)top=py;if(py>bottom)bottom=py;
    if(px>1&&!seen[p-1]&&rows[py][px-1]===color){seen[p-1]=1;q.push(p-1);}
    if(px<w-2&&!seen[p+1]&&rows[py][px+1]===color){seen[p+1]=1;q.push(p+1);}
    if(py>1&&!seen[p-w]&&rows[py-1][px]===color){seen[p-w]=1;q.push(p-w);}
    if(py<h-2&&!seen[p+w]&&rows[py+1][px]===color){seen[p+w]=1;q.push(p+w);}
   }
   if(pts.length<4||pts.length>400)continue;
   const cx=pts.reduce((s,p)=>s+p[0],0)/pts.length,cy=pts.reduce((s,p)=>s+p[1],0)/pts.length;
   const point=pts.reduce((a,b)=>(a[0]-cx)**2+(a[1]-cy)**2<=(b[0]-cx)**2+(b[1]-cy)**2?a:b);
   const mask=pts.map(p=>(p[1]-top)*w+p[0]-left).sort((a,b)=>a-b).join('.');
   result.push({color,area:pts.length,box:[left,top,right,bottom],point,clipped:left===1||top===1||right===w-2||bottom===h-2,shape:color+':'+mask,pts});
  }
  return result;
 };
 const compact=r=>({color:r.color,area:r.area,point:r.point,box:r.box});
 const sceneCache=new Map();
 const all=frames.map(rows=>{const g=geometry(rows);if(!sceneCache.has(g))sceneCache.set(g,{id:sceneCache.size,regions:components(rows)});const c=sceneCache.get(g);return {rows,geometry:g,id:c.id,regions:c.regions};});
 const pairCache=new Map();
 const registration=(before,after,changed)=>{
  const pair=before.id+','+after.id;if(pairCache.has(pair))return pairCache.get(pair);
  const h=before.rows.length,w=before.rows[0].length,votes=new Map([['0,0',{dx:0,dy:0,votes:0}]]);
  for(const p of before.regions)for(const q of after.regions){
   if(p.clipped||q.clipped||p.shape!==q.shape)continue;const dx=q.box[0]-p.box[0],dy=q.box[1]-p.box[1];
   if(Math.abs(dx)>w/2||Math.abs(dy)>h/2)continue;
   const k=dx+','+dy,v=votes.get(k)??{dx,dy,votes:0};v.votes++;votes.set(k,v);
  }
  const candidates=[votes.get('0,0'),...Array.from(votes.values()).filter(v=>v.dx||v.dy).sort((a,b)=>b.votes-a.votes).slice(0,24)];

  const points=[];for(let y=2;y<h-2;y+=3)for(let x=2;x<w-2;x+=3)points.push([x,y]);
  for(const v of candidates){let equal=0,n=0;
   for(const [x,y] of points){const xx=x+v.dx,yy=y+v.dy;if(xx<=0||xx>=w-1||yy<=0||yy>=h-1)continue;n++;if(before.rows[y][x]===after.rows[yy][xx])equal++;}
   v.fit=n?equal/n:0;v.coverage=n/Math.max(1,points.length);
  }
  const zero=candidates[0],ranked=candidates.filter(v=>v.coverage>=.45).sort((a,b)=>b.fit-a.fit),best=ranked[0]??zero;
  const supported=(best.dx||best.dy)&&best.votes>=3&&best.fit>=.88&&best.fit-zero.fit>=.10&&best.fit-(ranked[1]?.fit??0)>=.035;
  const stable=!supported&&zero.fit>=.90&&zero.votes>=3;
  const v=supported?best:zero;
  const result={status:supported?'supported_common_translation':stable?'no_common_translation_detected':changed?'unresolved':'unchanged_interior',
   dx:supported?best.dx:0,dy:supported?best.dy:0,fit:+v.fit.toFixed(3),anchorMatches:v.votes,
   usable:!!(supported||stable||!changed)};
  pairCache.set(pair,result);return result;
 };
 const effects=[];
 for(let i=1;i<all.length;i++){
  const before=all[i-1],after=all[i],action=actions[i];if(!action)continue;
  let interiorChanged=0,borderChanged=0;
  for(let y=0;y<after.rows.length;y++)for(let x=0;x<after.rows[y].length;x++)if(before.rows[y]?.[x]!==after.rows[y][x]){
   if(y===0||x===0||y===after.rows.length-1||x===after.rows[y].length-1)borderChanged++;else interiorChanged++;
  }
  const discontinuity=events[i]==='reset'||phases[i]!==phases[i-1]||epochs[i]!==epochs[i-1];
  const transform=discontinuity?{status:'episode_or_phase_boundary',usable:false,dx:0,dy:0}:registration(before,after,interiorChanged);
  const motion=[];
  for(const p of before.regions){
   const ps=before.regions.filter(q=>q.shape===p.shape),qs=after.regions.filter(q=>q.shape===p.shape);

   if(p.clipped||ps.length!==1||qs.length!==1||qs[0].clipped)continue;const q=qs[0],dx=q.box[0]-p.box[0],dy=q.box[1]-p.box[1];
   if(!dx&&!dy&&!transform.dx&&!transform.dy)continue;
   motion.push({color:p.color,area:p.area,beforeBox:p.box,afterBox:q.box,screenDelta:[dx,dy],
    relativeToScene:transform.usable?[dx-transform.dx,dy-transform.dy]:null});
  }
  const point=Number.isInteger(action.x)&&Number.isInteger(action.y)?[action.x,action.y]:null;
  const target=point?before.regions.find(r=>r.pts.some(p=>p[0]===point[0]&&p[1]===point[1])):null;
  let targetReview=null;
  if(target){let n=0,matched=0;
   if(transform.usable)for(const [x,y] of target.pts){const xx=x+transform.dx,yy=y+transform.dy;if(xx<=0||yy<=0||xx>=after.rows[0].length-1||yy>=after.rows.length-1)continue;n++;if(after.rows[yy][xx]===target.color)matched++;}
   targetReview={...compact(target),alignedRetainedFraction:transform.usable&&n===target.area?+(matched/n).toFixed(3):null};
  }
  effects.push({at:i,source:'obs-'+i,beforeSource:'obs-'+(i-1),action,event:events[i]??null,interiorChanged,borderChanged,
   response:events[i]??(interiorChanged?'interior_response':borderChanged?'border_only_response':'no_visible_response'),
   transform,motion:motion.sort((a,b)=>a.area-b.area).slice(0,4),targetReview});
 }
 const current=all.at(-1),lastIndex=all.length-1;
 let noInteriorRun=0;for(let j=effects.length-1;j>=0;j--){const e=effects[j];if(e.event||e.interiorChanged||epochs[e.at]!==epochs[lastIndex]||!sameAction(e.action,effects.at(-1).action))break;noInteriorRun++;}
 const candidates=effects.filter(e=>phases[e.at-1]===phases[lastIndex]&&all[e.at-1].geometry===current.geometry);
 const brief=e=>({source:e.source,beforeSource:e.beforeSource,action:e.action,outcome:e.response,epoch:epochs[e.at-1],
  currentEpoch:epochs[lastIndex],borderMayDiffer:true,interpretation:'Same interior layout only; compare counters, resources and hidden/time state before reuse. Not an action ban.'});
 const failures=effects.filter(e=>e.event==='failure').map(e=>({
  ...brief(e),target:e.targetReview,transform:e.transform,motion:e.motion,
  precedingActions:effects.filter(p=>p.at<e.at&&p.at>=e.at-2&&epochs[p.at]===epochs[e.at]).map(p=>({source:p.source,action:p.action,response:p.response})),
  causalStatus:'Failure follows this action; inspect direct effects and forced motion. Exact hazard and cause are unproven.'
 }));
 const coupled=effects.filter(e=>!e.event&&e.targetReview?.alignedRetainedFraction===0&&e.motion.some(m=>m.relativeToScene?.some(v=>v!==0)));
 return {effects,regions:current.regions.map(compact),noInteriorRun,
  conditionalContextMatches:candidates.slice(-4).map(brief),conditionalFailureMatches:candidates.filter(e=>e.event==='failure').slice(-3).map(brief),
  failureChains:failures.slice(-2),failureCount:failures.length,
  removalWithMotion:coupled.slice(-2).map(e=>({source:e.source,action:e.action,target:e.targetReview,motion:e.motion})),
  borderOnlyCount:effects.filter(e=>e.response==='border_only_response').length,
  contract:{beforeAction:'Choose a current subgoal and identify the controlled entity from action-response evidence. Predict both the immediate effect AND any forced continuation. Trace the full swept route to its next stopping surface or observed goal; inspect hazards and an exit before removing a constraint. If unsafe/unknown, reposition or collect one discriminating observation first.',
   afterAction:'Compare predicted entity/obstacle changes with scene-relative motion. Revise the mechanism on mismatch; do not count animation, counters, disappearance or camera motion as progress. After a scene shift reacquire all targets before reusing coordinates.',
   afterFailure:'Retain the preceding action chain and pre-action spatial relations across reset. Test a different causal hypothesis rather than repeat a failed chain unchanged. Treat repeated shape as an analogy, not proof of hazard identity.',
   evidenceLimits:'Border-only response is not an established no-op: border can encode time or resources. Geometry retrieval is conditional and never grants exact state equivalence. No scene transform or shape match establishes hidden identity. Shape matches are unique visible candidates only; color alone is not identity. Common translation is a camera/scene hypothesis. Aligned target retention measures pixels, not progress.'}};
}
