

import {planActorFocus} from '../src/actor-focus.mjs';
import {locateTextScope,auditScopeRequest} from '../src/text-scope.mjs';
import {planAcquisition} from '../src/acquisition-core.mjs';
import {selectDeliveredFrames} from '../src/select-delivered-frames.mjs';
export default function adaptiveAcquisition(input){
  if(input.mode==='plan_actor_focus')return planActorFocus(input);
  if(input.mode==='locate_text_scope')return locateTextScope(input);
  if(input.mode==='audit_scope_request')return auditScopeRequest(input);
  if(input.mode==='select_delivered_frames')return {...selectDeliveredFrames(input),intent:'Budget the inspection of already delivered frames across proposed anchors, separated appearance candidates and temporal context. No new frames or semantic labels are acquired.'};
  return {...planAcquisition(input),intent:'Translate a sourced evidence need into affordable time/frame/region/audio requests using only tools the current host actually offers.'};
}
