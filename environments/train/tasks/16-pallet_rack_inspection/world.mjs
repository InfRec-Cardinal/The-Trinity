                                                                                                   
                                                                                                            
                                                                                                        
import { createHash } from 'node:crypto';
import { Raster } from '../../lib/raster.mjs';
const canonical = value => Array.isArray(value) ? `[${value.map(v => canonical(v) ?? 'null').join(',')}]`
  : value && typeof value === 'object' ? `{${Object.keys(value).sort().filter(k => value[k] !== undefined).map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`
  : JSON.stringify(value);
export const sha256 = value => createHash('sha256').update(typeof value === 'string' || Buffer.isBuffer(value) ? value : JSON.stringify(value)).digest('hex');
export const contentHash = value => sha256(canonical(value));
const DAMAGE=['bent_upright','dented_upright','displaced_beam','deflected_beam','missing_beam_lock','damaged_baseplate','broken_stringer','missing_block'];
const PART={bent_upright:'upright_left',dented_upright:'upright_right',displaced_beam:'beam',deflected_beam:'beam',missing_beam_lock:'lock',damaged_baseplate:'baseplate',broken_stringer:'pallet',missing_block:'pallet'};
const PREFIX=(a,b,l)=>`A${a}-B${b}-L${l}`;
const band=(level,count)=>level===1?'low':level<=Math.ceil(count/2)?'middle':'high';
function normalize(input){if(!input||typeof input!=='object'||Array.isArray(input))return null;const keys=Object.keys(input).sort().join(',');
  if(input.action==='move_to'&&keys==='action,aisle,bay'&&Number.isSafeInteger(input.aisle)&&Number.isSafeInteger(input.bay)&&input.aisle>=1&&input.bay>=1)return {...input};
  if(input.action==='look'&&keys==='action,level,side,zoom'&&['front','back'].includes(input.side)&&['low','middle','high'].includes(input.level)&&['wide','close'].includes(input.zoom))return {...input};
  if(['report','retract'].includes(input.action)&&keys==='action,component,type'&&typeof input.component==='string'&&/^A\d+-B\d+-L\d+-(upright_left|upright_right|beam|lock|baseplate|pallet)$/.test(input.component)&&DAMAGE.includes(input.type))return {...input};
  if(input.action==='submit'&&keys==='action')return {action:'submit'};return null;
}
export function scorePalletRack(instance,report){const truth=new Map(instance.damageMap.map(d=>[`${d.component}:${d.type}`,d])),matched=report.filter(r=>truth.has(`${r.component}:${r.type}`)),precision=report.length?matched.length/report.length:0,recall=matched.length/instance.damageMap.length;
  const weight=d=>({minor:1,major:2,critical:4}[d.severity]),matchedWeight=matched.reduce((n,r)=>n+weight(truth.get(`${r.component}:${r.type}`)),0),totalWeight=instance.damageMap.reduce((n,d)=>n+weight(d),0),weightedPrecision=matchedWeight/(matchedWeight+report.length-matched.length||1),weightedRecall=matchedWeight/totalWeight;
  const missingCritical=instance.damageMap.filter(d=>d.severity==='critical'&&!matched.some(r=>r.component===d.component&&r.type===d.type)).length;
  return {precision,recall,criticalCoverage:missingCritical===0,missingCritical,severityWeightedF1:weightedPrecision+weightedRecall?2*weightedPrecision*weightedRecall/(weightedPrecision+weightedRecall):0};}
export function createPalletRack(instance){
  const state={step:0,aisle:1,bay:1,side:'front',level:'low',zoom:'wide',report:[],feedback:'Choose warehouse views and submit damage reports.',submitted:false,ended:false,outcome:null,reason:null};
  const currentLevels=()=>Array.from({length:instance.levels},(_,i)=>i+1).filter(l=>band(l,instance.levels)===state.level);
  const visibleParts=l=>{const parts=['upright_left','upright_right','beam','lock','pallet',...(l===1?['baseplate']:[])];return instance.loads[PREFIX(state.aisle,state.bay,l)][state.side]?parts.filter(p=>!['beam','lock','pallet'].includes(p)):parts;};
  const visibleDamage=(l,part)=>{const d=instance.damageMap.find(d=>d.a===state.aisle&&d.b===state.bay&&d.l===l&&PART[d.type]===part);return d&&visibleParts(l).includes(part)&&d.visibleSides.includes(state.side)&&(!d.closeOnly||state.zoom==='close')?d:null;};
  const end=reason=>{state.ended=true;state.reason=reason;const metrics=scorePalletRack(instance,state.report);state.outcome=state.submitted&&metrics.criticalCoverage&&metrics.precision>=.75?'success':'failure';};
  return {state,step(input){const action=normalize(input);if(!action)throw new Error('Malformed pallet inspection action');if(state.ended)throw new Error('Pallet inspection ended');state.step++;
    if(action.action==='move_to'){if(action.aisle>instance.aisles||action.bay>instance.bays)state.feedback='Requested bay is outside this warehouse.';else{state.aisle=action.aisle;state.bay=action.bay;state.feedback='Walked to requested aisle and bay.';}}
    else if(action.action==='look'){state.side=action.side;state.level=action.level;state.zoom=action.zoom;state.feedback='Rendered selected viewpoint.';}
    else if(action.action==='report'){if(!state.report.some(r=>r.component===action.component&&r.type===action.type))state.report.push({component:action.component,type:action.type});state.feedback='Report entry saved; correctness is checked only at submission.';}
    else if(action.action==='retract'){state.report=state.report.filter(r=>r.component!==action.component||r.type!==action.type);state.feedback='Matching report entry removed.';}
    else{state.submitted=true;end('submitted');state.feedback='Report submitted.';}
    if(!state.ended&&state.step>=instance.maxActions)end('action_budget_without_submission');},
    publicView(){const visibleComponents=currentLevels().flatMap(l=>visibleParts(l).map(part=>`${PREFIX(state.aisle,state.bay,l)}-${part}`)),metrics=state.ended?scorePalletRack(instance,state.report):null;return {text:JSON.stringify({task:'Inspect rack geometry in the RGB view. Report component IDs and damage types; include all critical defects with precision at least0.75.',warehouse:{aisles:instance.aisles,baysPerAisle:instance.bays,levels:instance.levels},current:{aisle:state.aisle,bay:state.bay,side:state.side,level:state.level,zoom:state.zoom},visibleComponents,damageTypes:DAMAGE,report:state.report,remainingActions:instance.maxActions-state.step,feedback:state.feedback}),terminal:{ended:state.ended,outcome:state.outcome,reason:state.reason,score:metrics?.severityWeightedF1??null,...(metrics?{evaluation:{...metrics,actionsUsed:state.step,submitted:state.submitted}}:{})}};},
    render(){const r=new Raster(640,480,[224,231,234]);r.text(`AISLE ${state.aisle} BAY ${state.bay} ${state.side}`,18,18,[35,47,57],3);r.text(`${state.level} ${state.zoom}`,18,42,[35,47,57],3);
      const levels=currentLevels();for(const [row,l] of levels.entries()){const top=88+row*175,base=top+140,left=110,right=530;const visible=visibleParts(l),damage=part=>visibleDamage(l,part),detail=state.zoom==='close'?1:.55,steel=[98,113,122],beam=[204,115,47],wood=[160,118,70];
        for(const [part,x] of [['upright_left',left],['upright_right',right]]){const d=damage(part);if(d?.type==='bent_upright'){r.line(x,top,x+16*detail,top+75,steel,9);r.line(x+16*detail,top+75,x,base,steel,9);}else{r.rect(x-4,top,9,140,steel);if(d?.type==='dented_upright'){r.line(x-4,top+50,x+4+8*detail,top+57,[45,52,57],3);r.line(x+4+8*detail,top+57,x-4,top+65,[45,52,57],3);}}}
        if(visible.includes('beam')){const d=damage('beam');if(d?.type==='deflected_beam'){r.line(left,base-42,320,base-42+15*detail,beam,12);r.line(320,base-42+15*detail,right,base-42,beam,12);}else r.line(left+(d?.type==='displaced_beam'?13*detail:0),base-42,right,base-42+(d?.type==='displaced_beam'?12*detail:0),beam,12);}
        if(visible.includes('lock')&&damage('lock')?.type!=='missing_beam_lock')r.rect(left+8,base-47,9,14,[236,215,70]);
        if(visible.includes('pallet')){const d=damage('pallet');r.rect(145,base-68,340,9,wood);for(let k=0;k<5;k++){if(d?.type==='missing_block'&&k===2)continue;r.rect(155+k*68,base-59,15,15,wood);}for(let k=0;k<6;k++){const x=150+k*55;if(d?.type==='broken_stringer'&&k===3){r.line(x,base-88,x+20,base-74,wood,7);r.line(x+30,base-82,x+45,base-88,wood,7);}else r.rect(x,base-90,42,8,wood);}}
        if(visible.includes('baseplate')){if(damage('baseplate')){r.line(left-22,base,left+12,base-9,[97,102,106],9);r.line(left+12,base-9,left+22,base,[97,102,106],9);}else r.rect(left-22,base,44,8,[97,102,106]);}
        if(!visible.includes('pallet')){r.rect(130,top+32,380,75,[159,139,99]);r.line(130,top+64,510,top+64,[126,110,80],2);r.text('STORED LOAD',215,top+60,[59,61,52],3);}
        r.text(`LEVEL ${l}`,18,top+8,[35,47,57],2);r.text(`${PREFIX(state.aisle,state.bay,l)}`,18,base+22,[35,47,57],2);
      }r.text(`ACTIONS LEFT ${instance.maxActions-state.step}`,18,450,[35,47,57],3);return r;}};
}
export const palletRackDefinition={taskId:'pallet_rack_inspection',maxSteps:80,playerRGB:true,create:createPalletRack,normalizeAction:normalize,
  actionContract:'Inspect RGB rack geometry. move_to aisle/bay; look front/back, low/middle/high, wide/close; report or retract component/type; submit. Every critical defect and precision≥0.75 are required. No damage-map or correctness feedback before submit;80actions. Warehouse size, subtlety and stored-load occlusion vary.',
  parameters:{type:'object',additionalProperties:false,properties:{action:{type:'string',enum:['move_to','look','report','retract','submit']},aisle:{type:'integer',minimum:1},bay:{type:'integer',minimum:1},level:{type:'string',enum:['low','middle','high']},side:{type:'string',enum:['front','back']},zoom:{type:'string',enum:['wide','close']},component:{type:'string'},type:{type:'string',enum:DAMAGE}},required:['action']}};
