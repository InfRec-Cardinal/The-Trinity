


const families=[
 ['absorbent-cloth',/\b(?:clean|white) cloths?\b/i,['cloth','towel','rag','washcloth','flannel']],
 ['disposable-paper',/\b(?:disposable|paper towels?|toilet paper)\b/i,['paper towel','toilet paper','tissue','paper napkin']],
 ['spray-bottle',/spray bottle/i,['spray bottle','misting bottle']],
 ['vinegar',/vinegar/i,['vinegar']],['baking-soda',/baking soda/i,['baking soda','sodium bicarbonate']],
 ['vacuum',/vacuum/i,['vacuum']],['detergent',/laundry detergent/i,['laundry detergent']],
 ['bowl',/\bbowl\b/i,['bowl']],['electric-fan',/electric fan/i,['electric fan','powered fan']],
 ['hair-dryer',/hair dry(?:er|ing)/i,['hair dryer','blow dryer']],
 ['iron',/clothes iron|clothing iron|\ban iron\b/i,['clothes iron','clothing iron']],
 ['food-container',/food.drink container|\bcup\b/i,['cup','mug','food container','drink container']],
 ['freestanding-rack',/freestanding.*(?:rack|drying)|drying rack/i,['drying rack','freestanding rack']],
 ['electric-dryer',/(?:electric )?clothes dryer/i,['clothes dryer','tumble dryer']],
];
export async function reviewPublicPlan({action,publicText,step,history,scope}){
  if(!scope)throw Error('Capability scope required');
  if(!scope.has('gateSchedule')||typeof action?.plan!=='string')return null;

  const seen=new Map();
  for(const row of [...history,{source:`obs-${step}`,publicFeedback:publicText}]){
    const text=row.publicFeedback??'';

    const feedback=text.split('## Output Format')[0];
    if(!/unavailable|aren.t available|not available|banned|without using|violates my preferences|don.t want/i.test(feedback))continue;
    for(const [id,pattern,terms] of families)if(pattern.test(feedback)&&!seen.has(id))seen.set(id,{id,terms,source:row.source,publicText:feedback});
  }
  if(!seen.size)return null;
  const input={mode:'constraint_audit',text:action.plan,constraints:[...seen.values()],forbidBranching:true};
  return {moduleId:'gateSchedule',input,output:await scope.invoke('gateSchedule',input),automatic:true};
}
