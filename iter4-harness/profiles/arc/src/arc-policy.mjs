
export function arcPolicy(input, outcomeMemory, visualRouteEvidence) {
 const decode=text=>{const r=JSON.parse(text.slice(text.indexOf('{'))),d=r.data??r;let rows;
  if(r.codec==='arc-public-row-delta-v2'){for(const f of d.frame){if(rows?.length!==f.height)rows=Array(f.height);for(const [y,i] of f.updates)rows[y]=d.rowTable[i];}}
  else{const f=d.frame.at(-1);rows=Array.isArray(f)?f.map(row=>row.map(x=>x.toString(16).toUpperCase()).join('')):f.rows;}
  return {rows,d};};
 const out=(status,reason,analysis,alternatives=[])=>({status,reasons:[reason],alternatives,analysis});
 const history=input.history??[];
 if(!history.length||input.publicText!==history.at(-1).publicText)return out('unknown','Complete public ledger ending at the current observation is required.',{});
 const states=history.map(h=>decode(h.publicText)),now=states.at(-1),actions=history.map(h=>h.action),events=[null],epochs=[],phases=[];
 const scenes=new Map();let epoch=0;
 const snapshots=states.map((s,i)=>{
  if(i&&actions[i]?.action==='RESET')epoch++;
  epochs.push('reset-'+epoch);phases.push('public-level-progress-'+String(s.d.levels_completed??'unknown'));
  const key=JSON.stringify({rows:s.rows,state:s.d.state,completed:s.d.levels_completed,actions:s.d.available_actions});
  if(!scenes.has(key))scenes.set(key,'public-scene-'+scenes.size);
  return {source:'obs-'+i,revision:i,phase:phases[i],epoch:epochs[i],stateKey:scenes.get(key)};
 });
 const receipts=[];
 for(let i=1;i<history.length;i++){
  const action=actions[i],before=states[i-1],after=states[i];
  const event=action?.action==='RESET'?'reset':after.d.state==='GAME_OVER'?'failure':
   after.d.state==='WIN'||(Number.isInteger(after.d.levels_completed)&&Number.isInteger(before.d.levels_completed)&&after.d.levels_completed>before.d.levels_completed)?'completion':null;
  events.push(event);if(!action)continue;
  receipts.push({id:'transition-'+i,source:'obs-'+i,before:snapshots[i-1],after:snapshots[i],action,
   accepted:after.d.transport_feedback?.accepted===false?false:true,changed:JSON.stringify(before.rows)!==JSON.stringify(after.rows),event,eventSource:event?'obs-'+i:null});
 }
 const remembered=outcomeMemory({current:snapshots.at(-1),transitions:receipts,proposedAction:input.action??null});
 if(!remembered.safeToUse)return out('unknown','Public transition evidence needs repair before memory advice.',{memoryErrors:remembered.errors,pending:remembered.pending});
 const legal=now.d.available_actions??[],a=input.action;
 if(a){const number=a.action==='RESET'?0:Number(a.action?.replace('ACTION',''));
  if(!legal.includes(number))return out('block','Action not currently available.',{available:legal});
  if(number===6&&(!Number.isInteger(a.x)||!Number.isInteger(a.y)||a.x<0||a.y<0||a.x>63||a.y>63))return out('block','Click requires integer coordinates 0..63.',{});
 }
 const evidence=visualRouteEvidence({frames:states.map(s=>s.rows),actions,phases,epochs,events});
 const counts={};for(let i=1;i<actions.length;i++)if(actions[i]&&actions[i].action!=='RESET'&&states[i-1].d.state!=='GAME_OVER')counts[actions[i].action]=(counts[actions[i].action]??0)+1;
 const samples=counts.ACTION6??0,cap=4;
 const lastClick=evidence.effects.filter(e=>e.action.action==='ACTION6').at(-1);
 const lastClickReview=lastClick?{step:lastClick.at,action:lastClick.action,source:lastClick.source,
  outcome:lastClick.event==='failure'?'failure':lastClick.response,target:lastClick.targetReview,
  interiorChangedPixels:lastClick.interiorChanged,borderChangedPixels:lastClick.borderChanged,
  interpretation:lastClick.event==='failure'?'Native failure; review the full preceding route and forced continuation, not only the clicked cell.':lastClick.interiorChanged?'A visible response occurred. Verify target effect, controlled entity displacement and safe successor route before treating it as progress.':'No interior response. Compare current target and time/resource changes before retrying. Screen coordinates do not identify a persistent object.'}:null;
 const geometry=evidence.conditionalContextMatches;
 const causal=evidence.removalWithMotion;
 const objective=samples<cap?'Use a bounded, goal-relevant control experiment only when its predicted effect distinguishes a mechanism. Inspect the successor route first; visible area/size alone is never a reason to click.':
  'Diagnostic click budget used. Plan toward the goal from the observed mechanism. Reposition to a safe route before opening an obstacle if forced motion would enter an unsafe region. Reset and camera shifts do not renew calibration.';
 const analysis={purpose:'Mechanism -> safe successor route -> action -> observed outcome',
  outcomeMemory:remembered.summary,visualEvidence:{noInteriorRun:evidence.noInteriorRun,borderOnlyCount:evidence.borderOnlyCount,
   conditionalContextMatches:geometry,conditionalFailureMatches:evidence.conditionalFailureMatches,
   failureChains:evidence.failureChains,removalWithMotion:causal,routeReview:evidence.contract},
  lastClickReview,liveRegions:evidence.regions.slice(0,8).map(r=>({...r,identityEstablished:false,role:'unclassified visible component; not a recommended click'})),
  recentMeasuredEffects:evidence.effects.slice(-2).map(e=>({...e,death:e.event==='failure'})),
  calibrationSampleCap:cap,calibrationSamples:samples,observedActionCounts:counts,
  untriedControls:legal.filter(n=>n>0&&!counts['ACTION'+n]).map(n=>'ACTION'+n),
  sameActionRun:remembered.summary.exactActionRun,recommendedAction:null,visibleClickCandidates:[],objective,
  retainsAcrossReset:'Exact public receipts retained; similar interior contexts and causal chains are conditional retrieval only. Reobserve resources, targets and scene transform.'};
 const last=evidence.effects.at(-1);
 const caution=(last?.event==='failure'?'FAILURE: revise the causal route before repeating. ':'')+
  (evidence.noInteriorRun>=2?'REPEATED NO INTERIOR RESPONSE: inspect target and time/resource state; stop blind repetition. ':'')+
  (causal.length?'OBSERVED COUPLING: obstacle alteration coincided with relative object motion. Check the entire forced continuation before the next alteration. ':'');
 return out('advice',caution+objective+' '+evidence.contract.beforeAction,analysis);
}
