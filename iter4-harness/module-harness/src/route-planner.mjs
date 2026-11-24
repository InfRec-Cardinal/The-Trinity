

import {observedGraph,shortest} from './common.mjs';
export default function explorationRoute({observations,phase,start,goal,budget,stamps={},expectedStampIds=[],
  collected=[],home,carrying=false,maxStates=50000}){
  if(carrying&&home===undefined)throw Error('Home required while carrying');
  const graph=observedGraph(observations,phase),target=carrying?home:goal;
  const missingLocations=carrying?[]:expectedStampIds.filter(id=>!Object.hasOwn(stamps, id)&&!collected.includes(id));
  const ids=carrying?[]:Object.keys(stamps).filter(id=>!collected.includes(id));
  const frontiers=new Set([...graph.values()].flat().filter(room=>!graph.has(room)));
  if(!graph.has(start))frontiers.add(start);
  const plan=shortest({room:start,got:[]},s=>(graph.get(s.room)||[]).map(room=>({
    state:{room,got:[...new Set([...s.got,...ids.filter(id=>stamps[id]===room)])].sort()},action:{from:s.room,to:room}
  })),s=>s.got.length===ids.length&&s.room===target,budget,maxStates);
  const frontier=shortest(start,u=>(graph.get(u)||[]).map(v=>({state:v,action:{from:u,to:v}})),u=>frontiers.has(u),budget,maxStates);
  const ready=!missingLocations.length&&plan.status==='planned';
  const selected=ready?plan:frontier;
  return {status:ready?(carrying?'return_route':ids.length?'known_target_tour':'known_route'):
    frontier.status==='planned'?'explore_or_reobserve':plan.status,
    plan,knownTour:plan,frontier,missingLocations,objective:carrying?'return':ids.length?'collect':'navigate',
    path:selected.path?[start,...selected.path.map(a=>a.to)]:[],recommendation:selected.path?.[0]??null,
    coverageComplete:graph.has(start)&&frontiers.size===0,
    note:'One current-phase graph supports target collection and plain routing. Exits require sourced complete observations; collection must be confirmed by native receipts.'};
}
