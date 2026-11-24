

import {codes,feedback,equal,partition} from '../src/common.mjs';
export default function candidateProbe({alphabet,length,archives=[],history=[],proposed,transform='none',
  objective='entropy',maxCandidates=20000,probeLimit=64}){
  if(!['none','rotate','alternate'].includes(transform))throw Error('Unknown public transform');
  if(!['entropy','minimax'].includes(objective))throw Error('Unknown probe objective');
  if(!Number.isInteger(probeLimit)||probeLimit<1)throw Error('Positive probeLimit required');
  const domain=codes(alphabet,length,maxCandidates);if(!domain)return {status:'candidate_limit'};
  let rows=domain.filter(c=>archives.every(r=>equal(feedback(c,r.guess),r.feedback))).map(c=>({initial:c,current:c}));
  let terminal=false;const audit=[];
  for(const [i,r] of history.entries()){
    if(terminal)return {status:'invalid_history',reason:'Action after successful terminal feedback'};
    if(r.index!==i||!r.evidenceId)return {status:'unknown',reason:'Complete ordered sourced history required'};
    rows=rows.filter(c=>equal(feedback(c.current,r.guess),r.feedback));terminal=r.feedback[0]===length;
    const change=terminal?'none':transform==='alternate'?(i%2===0?'rotate':'reverse'):transform;
    audit.push({evidenceId:r.evidenceId,observationIndex:i,survivors:rows.length,transformApplied:change});
    if(change!=='none')rows=rows.map(c=>({...c,current:change==='reverse'?[...c.current].reverse():[...c.current.slice(1),c.current[0]]}));
  }
  if(!rows.length)return {status:'inconsistent_evidence',audit};
  const current=rows.map(r=>r.current),stride=Math.max(1,Math.ceil(current.length/probeLimit));
  const probes=current.filter((_,i)=>i%stride===0);
  if(proposed){if(proposed.length!==length||proposed.some(v=>!alphabet.includes(v)))throw Error('Proposal outside public domain');
    if(!probes.some(p=>equal(p,proposed)))probes.push(proposed);}
  const scores=probes.map(probe=>({probe,...partition(current,probe)}));
  const byEntropy=[...scores].sort((a,b)=>b.entropy-a.entropy||a.expected-b.expected);
  const byMinimax=[...scores].sort((a,b)=>a.worst-b.worst||a.expected-b.expected);
  return {status:terminal?'terminal':current.length===1?'unique_in_complete_domain':'probe',candidateCount:rows.length,
    candidates:current,initialToCurrent:rows.length<=8?rows:undefined,audit,currentWorldIndex:history.length,
    objective,recommendation:terminal?null:(objective==='entropy'?byEntropy:byMinimax)[0],
    bestEntropy:byEntropy[0],bestMinimax:byMinimax[0],original:proposed?scores.find(r=>equal(r.probe,proposed)):null,
    positionDomains:Array.from({length},(_,i)=>[...new Set(current.map(c=>c[i]))]),
    proposalIsPossibleAnswerNow:proposed?current.some(c=>equal(c,proposed)):null,probesEvaluated:scores.length,
    globallyOptimalProbe:false,note:'One candidate history and one feedback partition pass support both ranking objectives. Archives refer to the initial world; transformations occur after nonterminal feedback.'};
}
