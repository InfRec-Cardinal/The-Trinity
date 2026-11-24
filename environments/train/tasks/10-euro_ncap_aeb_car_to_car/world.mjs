                                                                                                                
                                                                                                               
                                                                                                                                         
import { Raster } from '../../lib/raster.mjs';
import { normalizeObject, terminal } from '../../lib/world-utils.mjs';
const ID = 'euro_ncap_aeb_car_to_car', DT = 0.1;
const draw=s=>{s.rng=(Math.imul(1664525,s.rng)+1013904223)>>>0;return s.rng/4294967296;};
const normal=s=>Math.sqrt(-2*Math.log(Math.max(draw(s),1e-12)))*Math.cos(2*Math.PI*draw(s));
export function normalizeEuroNCAPAction(input){const a=normalizeObject(input,['type','demand']);if(a?.type==='hold'&&Object.keys(a).length===1)return a;return a?.type==='brake'&&Number.isFinite(a.demand)&&a.demand>=0&&a.demand<=1?a:null;}
export function createEuroNCAPEngine(instance){const s={rng:instance.seed>>>0,step:0,time:0,ownX:0,targetX:instance.initialGap,ownSpeed:instance.speedKmh/3.6,targetSpeed:instance.targetSpeedKmh/3.6,acceleration:0,demand:0,lag:[0,0,0],onsetTTC:null,peakDeceleration:0,minimumGap:instance.initialGap,ended:false};
  const sensor=()=>{s.rangeNoise=normal(s)*instance.rangeSigma;s.rateNoise=normal(s)*instance.rangeRateSigma;};sensor();
  const finish=(outcome,reason,impact=0,relative=0)=>{s.ended=true;s.outcome=outcome;s.reason=reason;const completed=reason!=='decision_budget_exhausted';s.score=completed?Math.max(0,1-relative/(instance.speedKmh/3.6)):null;s.evaluation={impactSpeedKmh:completed?impact*3.6:null,relativeImpactSpeedKmh:completed?relative*3.6:null,relativeImpactSpeedReduction:s.score,ownSpeedKmh:s.ownSpeed*3.6,targetSpeedKmh:s.targetSpeed*3.6,finalGap:s.targetX-s.ownX,elapsedSeconds:s.time,brakeOnsetTTC:s.onsetTTC,peakDeceleration:s.peakDeceleration,nuisanceBraking:s.onsetTTC!==null&&s.onsetTTC>4,minimumGap:s.minimumGap};};
  return{state:s,step(action){if(s.ended)throw Error('AEB test already ended');const gap=s.targetX-s.ownX,closing=s.ownSpeed-s.targetSpeed;if(action.type==='brake'){if(s.onsetTTC===null&&action.demand>0)s.onsetTTC=closing>0?gap/closing:1e9;s.demand=action.demand;}
                                                                             
    const applied=s.lag.shift();s.lag.push(s.demand);const desired=-9*applied,delta=instance.jerkLimit*DT;s.acceleration=Math.max(s.acceleration-delta,Math.min(s.acceleration+delta,desired));
    const targetA=-instance.targetDeceleration*Math.max(0,Math.min(1,(s.time+DT/2-instance.targetBrakeStart)/instance.targetRampSeconds)),ownBefore=s.ownSpeed,targetBefore=s.targetSpeed;
    s.ownSpeed=Math.max(0,s.ownSpeed+s.acceleration*DT);s.targetSpeed=Math.max(0,s.targetSpeed+targetA*DT);const ownDistance=(ownBefore+s.ownSpeed)*DT/2,targetDistance=(targetBefore+s.targetSpeed)*DT/2,afterGap=gap+targetDistance-ownDistance;
    s.ownX+=ownDistance;s.targetX+=targetDistance;s.time+=DT;s.step++;s.peakDeceleration=Math.max(s.peakDeceleration,-s.acceleration);s.minimumGap=Math.min(s.minimumGap,Math.max(0,afterGap));sensor();
    if(afterGap<=0){const fraction=gap/(gap-afterGap),impact=ownBefore+(s.ownSpeed-ownBefore)*fraction,target=targetBefore+(s.targetSpeed-targetBefore)*fraction;finish('failure','target_contact',impact,Math.max(0,impact-target));}
    else if(s.ownSpeed===0||(s.ownSpeed<=s.targetSpeed&&s.time>=2&&instance.scenario!=='CCRb'))finish('success','positive_gap_without_contact');
    else if(s.step>=200)finish('failure','decision_budget_exhausted');},
    publicView(){const gap=s.targetX-s.ownX;return{text:JSON.stringify({ownSpeed:s.ownSpeed,longitudinalAcceleration:s.acceleration,range:gap<=80?Math.max(0,gap+s.rangeNoise):null,rangeRate:gap<=80?s.targetSpeed-s.ownSpeed+s.rateNoise:null,sensorMaximumRange:80,overlapPercent:instance.overlap,brakeDemand:s.demand,time:s.time,decisions:s.step,instructions:'brake demand0..1 or hold. Commands act after0.3s with jerk-limited9m/s2 maximum. Avoid contact within200 decisions; early TTC>4s onset is nuisance braking.'}),reward:s.score??0,info:{},terminal:terminal(s,200)};},
    render(){const r=new Raster(640,220,[242,246,249]),gap=Math.max(0,s.targetX-s.ownX);r.rect(0,115,640,56,[98,107,117]);r.rect(85,120,58,32,[49,129,205]);r.rect(143+Math.min(420,gap*5),120,58,32,[214,99,84]);r.text(`SPEED ${s.ownSpeed.toFixed(1)} GAP ${gap.toFixed(1)}`,18,20);r.text(s.ended?s.reason:'BRAKE CONTROLLER',18,190);return r;}};
}
export const euroNCAPDefinition = {
  taskId: ID, version: 1, family: 'self_proposed', maxSteps: 200, playerRGB: false, mechanismReviewed: true,
  create: (ordinal, instance) => createEuroNCAPEngine(instance),
  normalizeAction: normalizeEuroNCAPAction,
  actionContract: 'brake with demand0..1, or hold; one0.1s decision',
  parameters: { type: 'object', additionalProperties: false, required: ['type'], properties: { type: { enum: ['brake', 'hold'] }, demand: { type: 'number', minimum: 0, maximum: 1 } } },
  sources: ['https://cdn.euroncap.com/cars/assets/euro_ncap_aeb_c2c_test_protocol_v43_1e6ed06def.pdf'],
  fidelityNotes: 'Declared seeded longitudinal reconstruction of selected Euro NCAP CCRs/CCRm/CCRb grids, relative contact speed and AEB braking. Source protocol is physical; no original simulator exists.',
  limitations: ['Longitudinal integration, sensors, brake lag/jerk, initial CCRs/CCRm range and cap200 are declared designs.', 'Signed overlap is recorded from the selected grid; every selected alignment represents longitudinal target contact without steering. No lateral vehicle model or official NCAP rating is claimed.'],
};
