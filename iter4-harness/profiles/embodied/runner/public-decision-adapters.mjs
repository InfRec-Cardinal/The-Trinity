import {boxobanPublicModel} from './boxoban-public-model.mjs';
import {wcaPublicModel} from './wca-public-model.mjs';

export function hanabiConsequences(text,source){
 if(!text.includes('Cur player')||!text.includes('Legal moves:'))return null;
 const stacks=Object.fromEntries([...text.matchAll(/\b([RYGWB])(\d)\b/g)].slice(0,5).map(m=>[m[1],Number(m[2])]));
 if(Object.keys(stacks).length!==5)return null;
 const handtext=text.split('Hands:')[1]?.split('Deck size:')[0];if(!handtext)return null;
 const hands=handtext.trim().split(/\n-----\n/).map(h=>[...h.matchAll(/([RYGWBX])([1-5X]) \|\| ([RYGWBX])([1-5X])\|([RYGWB1-5]+)/g)].map(m=>({suit:m[1],rank:Number(m[2])||null,positive:m[3]!=='X'||m[4]!=='X',possibleSuits:[...m[5]].filter(x=>'RYGWB'.includes(x)),possibleRanks:[...m[5]].filter(x=>'12345'.includes(x)).map(Number)})));
 if(!hands[0]?.length)return null;
 const legal=[...text.matchAll(/^([0-9]+): \(([^\n]+)\)$/gm)].map(m=>({index:Number(m[1]),move:m[2]}));
 const categories=[...'RYGWB'];
 const inventory=categories.flatMap(category=>[1,2,3,4,5].map(order=>({category,order,count:order===1?3:order===5?1:2})));
 const debit=(s,r)=>{const c=inventory.find(x=>x.category===s&&x.order===r);if(c)c.count--;};
 for(const [s,n] of Object.entries(stacks))for(let r=1;r<=n;r++)debit(s,r);
 for(const h of hands.slice(1))for(const c of h)debit(c.suit,c.rank);
 const discards=text.split('Discards:')[1]?.split('Last moves')[0]??'';
 for(const m of discards.matchAll(/([RYGWB])([1-5])/g))debit(m[1],Number(m[2]));
 if(inventory.some(c=>c.count<0))throw Error('Public card inventory inconsistent');
 const recent=text.split('Last moves (most recent first): ')[1]?.split('\nLegal moves:')[0]??'';
 const playerInfo=text.match(/You are player (\d+) of (\d+)/);const signals=[];
 if(playerInfo)for(const h of recent.matchAll(/<\(Reveal player \+(\d+) color ([RYGWB])\) by player (\d+) reveal (\d+(?:,\d+)*)>/g)){
  if((Number(h[3])+Number(h[1]))%Number(playerInfo[2])!==Number(playerInfo[1]))continue;
  if(new RegExp('scored '+h[2]+'[1-5]').test(recent.slice(0,h.index)))continue;
  signals.push({category:h[2],next:stacks[h[2]]+1,slots:h[4].split(',').map(Number)});
 }
 const moves=legal.map(l=>{let m,base={id:String(l.index),action:{move:l.index}};
  if(m=l.move.match(/^(Play|Discard) (\d+)$/))return {...base,kind:m[1].toLowerCase(),index:Number(m[2])};
  if(m=l.move.match(/^Reveal player \+(\d+) (color|rank) ([RYGWB1-5])$/))return {...base,kind:m[2]==='color'?'category':'order',target:Number(m[1]),value:m[2]==='color'?m[3]:Number(m[3])};
 }).filter(Boolean);
 const rawHands=handtext.trim().split(/\n-----\n/).map(h=>[...h.matchAll(/([RYGWBX])([1-5X]) \|\| ([RYGWBX])([1-5X])\|([RYGWB1-5]+)/g)]);
 return {input:{mode:'cooperative_forecast',source,progress:stacks,inventory,legal:moves,signals,
  life:Number(text.match(/Life tokens: (\d+)/)[1]),info:Number(text.match(/Info tokens: (\d+)/)[1]),maxInfo:8,maxOrder:5,
  hands:hands.map((hand,j)=>hand.map((c,i)=>({category:c.suit,order:c.rank,categories:c.possibleSuits,orders:c.possibleRanks,knownCategory:rawHands[j][i][3]!=='X',knownOrder:rawHands[j][i][4]!=='X'})))},
  scope:'One full partner cycle, sampled unknown own hand and draws from publicly remaining multiplicities; fresh hints constrain possible hands, never reveal the hidden identity.'};
}
const adapters=[
 {moduleId:'gateSchedule',read:({text,source,history,remaining})=>{
  const input=boxobanPublicModel(text,source,history,remaining);if(!input)return null;
  return {input,scope:'Public push-grid geometry and observed goal locations only. Execute one proposed direction, verify the successor and replan.',present:output=>output.status==='plan'?{status:output.status,nextNativeAction:output.recommendation?{action:output.recommendation.direction}:null,expectedTransition:output.recommendation,remainingPlanSteps:output.steps,spareActions:output.spareActions,goalMode:output.goalMode,note:'First move of a verified route under the supplied public grid model. Compare the next observation with expectedTransition.'}:output};
 }},
 {moduleId:'gateSchedule',read:({text,source,remaining})=>{
  const input=wcaPublicModel(text,source);if(input)input.maxDepth=Math.min(input.maxDepth,remaining);return input?{input,scope:'Reversible-slot search from public cube faces and standard move permutations. Search-limit is unknown; verify the native observation before finish.'}:null;
 }},
 {moduleId:'evidenceDiagnosis',read:({text,history})=>{
  let state;try{state=JSON.parse(text);}catch{return null;}
  if(typeof state?.sourcePrompt!=='string'||!state.sourcePrompt.includes('immediate reward'))return null;
  const observations=[];
  for(const row of history){if(row.action?.action!=='run_experiment')continue;
   try{const design=JSON.parse(row.action.design),feedback=JSON.parse(row.publicFeedback).toolResult;
    if(design.length===3&&design.every(Number.isFinite)&&design[0]>0&&design[1]>design[0]&&design[2]>0&&feedback?.success&&[0,1].includes(feedback.observation))observations.push({cut:(design[1]/design[0]-1)/design[2],label:feedback.observation,source:row.source});
   }catch{}
  }
  if(!observations.length)return null;
  let first;try{first=JSON.parse(history[0]?.publicFeedback??'{}');}catch{first={};}
  const targets=(first.questions??state.questions??[]).flatMap((q,i)=>{const m=q.match(/iR = ([0-9.]+), delayed reward dR = ([0-9.]+), and delay in days D = ([0-9.]+)/);return m?[{id:String(i),cut:(Number(m[2])/Number(m[1])-1)/Number(m[3]),source:'obs-0'}]:[];});
  return {input:{mode:'scalar_threshold',observations,targets},scope:'Public hyperbolic-discount observations mapped to a scalar threshold. Other families/noisy choices remain possible. Only current-episode receipts are fitted.'};
 }},
 {moduleId:'opponentDecision',read:({text,source})=>hanabiConsequences(text,source)},
 {moduleId:'opponentDecision',read:({text,source})=>{
  const own=text.match(/You are Commander (Alpha|Beta)/)?.[1],total=Number(text.match(/allocate exactly (\d+) units/)?.[1]);
  if(!own||!Number.isSafeInteger(total)||total<=0)return null;
  const observations=[...text.matchAll(/Commander (Alpha|Beta) allocated: A:\s*(\d+)\s*, B:\s*(\d+)\s*, C:\s*(\d+)/g)].filter(m=>m[1]!==own).map(m=>({allocation:m.slice(2).map(Number),source}));
  return {input:{mode:'resource_contest',total,fields:3,observations,priorWeight:observations.length?0:2,symmetryWeight:1},scope:'Current-episode public allocation receipts with explicit exchangeable-field uncertainty; no future sequence or stored opponent template.'};
 }},
 {moduleId:'opponentDecision',read:({text,source})=>{
  const items=[...text.matchAll(/(?:^|\|)\s*([A-Z][A-Z -]*?) \[(Red|Blue|Civilian|Assassin)\]/gm)].map(m=>({label:m[1].trim(),role:m[2]==='Red'?'target':m[2]==='Assassin'?'catastrophic':'avoid'}));
  return items.length<2?null:{input:{mode:'semantic_signal',items,source},scope:'Public labelled word roles and a pretrained embedding model; no partner process or private choices queried.'};
 }}
];
export async function publicDecisionAdvice({text,step,history=[],remaining,scope}){
 if(!scope||!Number.isSafeInteger(step)||step<0||!Number.isSafeInteger(remaining)||remaining<0)throw Error('Capability scope and public step budget required');
 const context={text,source:`obs-${step}`,history,remaining};
 for(const adapter of adapters){
  if(!scope.has(adapter.moduleId))continue;
  let parsed;try{parsed=adapter.read(context);}catch{continue;}
  if(!parsed)continue;
  const output=await scope.invoke(adapter.moduleId,parsed.input);
  return {moduleId:adapter.moduleId,input:parsed.input,output:parsed.present?parsed.present(output):output,...(parsed.present?{fullPlanForAudit:output}:{}),details:parsed.details,scope:parsed.scope,communicationEvidence:parsed.communicationEvidence,automatic:true,noWorldActionExecuted:true};
 }
 return null;
}
export function actionOnlyPresentation(turns){

 const clean=s=>s.replace(/Submit your output as text\.[\s\S]*?Text matching no available action falls back to the last listed action, as in the released agent\./g,'Choose one listed action and submit it in the action field of submit_action. VIEW MONITOR may also supply room. The native parser and fallback behavior remain unchanged.').replace(/Make a summarization of the past observed events[\s\S]*?DO NOT PICK AN ACTION THAT IS NOT IN THE LIST OF AVAILABLE ACTIONS AND MAKE SURE TO FOLLOW THE EXACT OUTPUT FORMAT\./g,'Choose exactly one currently available action. Submit it using the native action tool.');
 const visit=v=>typeof v==='string'?clean(v):Array.isArray(v)?v.map(visit):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).map(([k,x])=>[k,visit(x)])):v;
 return turns.map(t=>t.role==='assistant'?t:visit(t));
}
