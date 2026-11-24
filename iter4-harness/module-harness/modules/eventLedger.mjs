

import {countRepeatedEvents,requestSequenceAudit} from '../src/repeated-event-ledger.mjs';
import {equal} from '../src/common.mjs';

export default function eventLedger(input){
  if(input.mode==='request_sequence_audit')return requestSequenceAudit(input);
  if(input.mode==='count_repeated_events')return countRepeatedEvents(input);
  return transferLedger(input);
}
function transferLedger({target,initialHolder,events=[],observations=[],endpoint,proposed,coverageComplete=false}) {
  const episodes=aggregateEpisodes({target,initialHolder,observations});
  const derived=episodes.events.map(e=>({id:e.id,target,time:e.end,start:e.start,source:e.sources,type:'handoff',
    from:e.from,to:e.to,releaseObserved:true,receiveObserved:true}));

  events=[...events,...derived];
  let holder=initialHolder,location=null,lastEnd=-Infinity;
  const receipts=[],gaps=[...episodes.incomplete],seen=new Set();
  const ordered=events.filter(e=>e.target===target).sort((a,b)=>a.time-b.time);
  for (const e of ordered) {
    if (!e.id || !e.source || !Number.isFinite(e.time) || seen.has(e.id)) {
      gaps.push({event:e.id??null,reason:'duplicate_or_unsourced_or_untimed_event'}); continue;
    }
    seen.add(e.id);
    if (e.type==='handoff') {
      if (!e.releaseObserved || !e.receiveObserved || e.from!==holder || e.to==null || e.to===holder || (e.start??e.time)<lastEnd) {
        gaps.push({event:e.id,reason:'unproved_handoff'}); continue;
      }
      holder=e.to; location=null;lastEnd=e.time;
      receipts.push({id:e.id,time:e.time,recipient:holder});
    } else if (e.type==='deposit') {
      if (e.actor!==holder || !e.releaseObserved || e.location==null) {
        gaps.push({event:e.id,reason:'unproved_deposit'}); continue;
      }
      location=e.location;
    } else if (e.type==='occlusion') {

      const flags=[e.publicNoExchangeGuarantee,e.noExchangeGuaranteed].filter(v=>v!==undefined);
      if (!flags.length || !flags.every(v=>v===true)) gaps.push({event:e.id,time:e.time,reason:'occlusion'});
    } else gaps.push({event:e.id,reason:'unsupported_event_type'});
  }
  const sequence=receipts.map(r=>r.recipient), answer={count:receipts.length,route:sequence,destination:location};
  const endpointMatches=Boolean(endpoint?.observed===true && endpoint.source && endpoint.target===target &&
    endpoint.holder===holder && equal(endpoint.location,location));
  const canCommit=!gaps.length && location!=null && endpointMatches && coverageComplete===true;
  return {status:canCommit?'audited':'incomplete',holder,location,sequence,count:receipts.length,receipts,
    gaps,uncertain:gaps,episodes,answer,endpointMatches,coverageComplete,canCommit,
    proposalMatches:proposed?equal(proposed,answer):null,
    note:'Repeated recipients count as separate events. A later handoff clears a previous deposit; missing endpoint or coverage proof blocks final commitment.'};
}

function aggregateEpisodes({target, observations}) {
  const groups = new Map(), incomplete = [];
  for (const o of observations) {
    if (o.target !== target) continue;
    if (!o.source || !Number.isFinite(o.time)) { incomplete.push({reason:'unsourced_or_untimed_observation'}); continue; }
    if (!o.episodeId) { incomplete.push({reason: 'missing_episode_identity', source: o.source}); continue; }
    const xs = groups.get(o.episodeId) || []; xs.push(o); groups.set(o.episodeId, xs);
  }
  const events = [];
  for (const [id, rows] of groups) {
    const pairs = new Set(rows.map(r => JSON.stringify([r.from, r.to])));
    const release = rows.filter(r => r.releaseObserved).sort((a, b) => a.time - b.time)[0];
    const receipt = rows.filter(r => r.receiveObserved).sort((a, b) => a.time - b.time).at(-1);
    if (pairs.size !== 1 || !release || !receipt || release.time > receipt.time || rows[0].from === rows[0].to) {
      incomplete.push({episodeId: id, reason: 'unproved_or_conflicting_exchange'}); continue;
    }
    events.push({id, from: rows[0].from, to: rows[0].to, start: release.time, end: receipt.time,
      sources: rows.map(r => r.source)});
  }
  return {events, incomplete};
}
