

export function cooperativeForecast(q){
 const {hands,progress,inventory,legal,life,info,maxInfo,source,signals=[]}=q;
 if(!source||!hands?.length||!legal?.length)throw Error('Sourced cooperative state required');
 let seed=7331;const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 const sample=(pool,predicate=()=>true)=>{const opts=pool.filter(c=>c.count>0&&predicate(c));const n=opts.reduce((a,c)=>a+c.count,0);if(!n)return null;let r=rand()*n;for(const c of opts){r-=c.count;if(r<0){c.count--;return {category:c.category,order:c.order,knownCategory:false,knownOrder:false};}}};
 const particles=[];
 for(let trial=0;trial<5000&&particles.length<256;trial++){
  const pool=structuredClone(inventory),own=[];let ok=true;
  for(const c of hands[0]){const id=sample(pool,x=>c.categories.includes(x.category)&&c.orders.includes(x.order));if(!id){ok=false;break;}own.push({...id,knownCategory:c.knownCategory,knownOrder:c.knownOrder});}
  if(!ok)continue;
  if(signals.some(s=>!s.slots.some(i=>own[i]?.category===s.category&&own[i]?.order===s.next)))continue;
  particles.push({pool,own});
 }
 if(!particles.length)return {status:'unknown',reason:'No consistent public belief samples; do not use this model.'};
 const ranked=legal.map(a=>{
  let sum=0,death=0,loss=0,gain=0,ownSafe=0,discardCost=0;
  for(const particle of particles){
   const hs=structuredClone(hands),pool=structuredClone(particle.pool),fire={...progress};hs[0]=structuredClone(particle.own);
   let hp=life,tokens=info,scored=0,lost=0,cost=0,finalTurns=null;
   const playable=c=>c&&c.order===fire[c.category]+1;
   const remove=(seat,i)=>{hs[seat].splice(i,1);const d=sample(pool);if(d)hs[seat].push(d);if(!pool.some(c=>c.count>0)&&finalTurns===null)finalTurns=hs.length+1;};
   const play=(seat,i)=>{const c=hs[seat][i];if(!c)return;if(playable(c)){fire[c.category]++;scored++;if(c.order===q.maxOrder)tokens=Math.min(maxInfo,tokens+1);}else {hp--;lost++;}remove(seat,i);};
   const discard=(seat,i)=>{const c=hs[seat][i];if(c&&c.order>fire[c.category]){const remain=pool.find(x=>x.category===c.category&&x.order===c.order)?.count??0;const visible=hs.flat().filter(x=>x.category===c.category&&x.order===c.order).length;cost+=remain+visible<=1?2:.15;}remove(seat,i);tokens=Math.min(maxInfo,tokens+1);};
   const hint=(seat,kind,value)=>{tokens--;for(const c of hs[seat])if(c[kind]===value)c[kind==='category'?'knownCategory':'knownOrder']=true;};
   if(a.kind==='play'){ownSafe+=Number(playable(hs[0][a.index]));play(0,a.index);}
   else if(a.kind==='discard')discard(0,a.index);
   else hint(a.target,a.kind==='category'?'category':'order',a.value);

   const rolloutOwn=()=>{
    const certain=hs[0].findIndex(c=>c.knownCategory&&c.knownOrder&&playable(c));if(certain>=0){play(0,certain);return;}
    const choices=[];
    if(tokens>0)for(let target=1;target<hs.length;target++)for(const kind of ['category','order'])for(const value of new Set(hs[target].map(c=>c[kind]))){
     const queue=hs[target].filter(c=>c.knownCategory||c.knownOrder||c[kind]===value);if(!queue.length||!playable(queue[0]))continue;
     const safe=queue.filter(playable).length,bad=queue.length-safe;
     choices.push({target,kind,value,u:2*safe-3*bad-.03*target});
    }
    choices.sort((a,b)=>b.u-a.u);if(choices[0]?.u>0||tokens===maxInfo&&choices.length){const c=choices[0];hint(c.target,c.kind,c.value);return;}
    if(tokens<maxInfo){const obsolete=hs[0].findIndex(c=>c.knownCategory&&c.knownOrder&&c.order<=fire[c.category]);discard(0,Math.max(0,obsolete));return;}

    if(tokens>0&&hs[1]?.length){hint(1,'order',hs[1][0].order);return;}play(0,0);
   };
   for(let turn=1;turn<hs.length*4&&hp>0;turn++){
    if(finalTurns!==null&&--finalTurns<=0)break;
    const seat=turn%hs.length;if(seat===0){rolloutOwn();continue;}
    const pending=hs[seat].findIndex(c=>c.knownCategory||c.knownOrder);
    if(pending>=0){play(seat,pending);continue;}
    let target=null;
    if(tokens>0)for(let offset=1;offset<hs.length&&!target;offset++){
     const receiver=(seat+offset)%hs.length;
     const card=hs[receiver].find(c=>playable(c)&&!c.knownCategory);
     if(card)target={receiver,category:card.category};
    }
    if(target)hint(target.receiver,'category',target.category);
    else if(tokens<maxInfo)discard(seat,0);else play(seat,0);
   }

   let pendingRisk=0;for(let seat=1;seat<hs.length;seat++){const c=hs[seat].find(c=>c.knownCategory||c.knownOrder);if(c&&!playable(c))pendingRisk++;}
   const dead=hp<=0;death+=Number(dead);loss+=lost;gain+=scored;discardCost+=cost;
   sum+=scored*2-lost*(life<=1?35:15)-Number(dead)*120-pendingRisk*1.5-cost+.03*(maxInfo-tokens);
  }
  const n=particles.length;return {id:a.id,action:a.action,expected:sum/n,deathProbability:death/n,expectedLifeLoss:loss/n,expectedProgress:gain/n,ownPlayProbability:a.kind==='play'?ownSafe/n:null,discardCost:discardCost/n,model:'public_inventory_and_positive_signal_partner',source};
 }).sort((a,b)=>b.expected-a.expected);
 return {status:'ranked',recommendation:ranked[0],ranked,particles:particles.length,scope:'Sampled public-inventory hypotheses and an explicit positive-signal partner model. Unknown draws are sampled, not read. Four-cycle conditional forecast with a public-information fallback own policy; recompute after real feedback.'};
}
