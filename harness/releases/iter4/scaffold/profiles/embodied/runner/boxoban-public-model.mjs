

export function publicPushMap(text){
  const start=text.indexOf('\nmap:\n');if(start<0)return null;
  const rows=[];
  for(const line of text.slice(start+6).split('\n')){
    if(!line.length&&!rows.length)continue;
    if(!/^[ .#@`{}<>*+]+$/.test(line))break;
    rows.push(line);
  }
  if(!rows.length||rows.some(r=>r.length!==rows[0].length))return null;
  return rows;
}
export function boxobanPublicModel(text,source,history,budget){
  const current=publicPushMap(text);if(!current)return null;
  const goals=new Map();
  for(const row of [...history,{publicFeedback:text,source}]){
    const grid=publicPushMap(row.publicFeedback??'');if(!grid||grid.length!==current.length||grid[0].length!==current[0].length)continue;
    grid.forEach((line,y)=>[...line].forEach((c,x)=>{if(c==='{')goals.set(`${x},${y}`,row.source);}));
  }
  const grid=current.map((line,y)=>[...line].map((c,x)=>{
    if(!goals.has(`${x},${y}`))return c;
    if(c==='`')return '*';if(c==='@')return '+';if(c==='{'||c==='.')return '{';
    throw Error('Public static goal geometry changed unexpectedly');
  }).join(''));
  return {mode:'grid_push',grid,glyphs:{wall:'# ',floor:'.<>',box:'`',goal:'{',player:'@',boxOnGoal:'*',playerOnGoal:'+'},
    goalMode:'occupy',budget,maxStates:50000,source,goalEvidence:[...goals].map(([cell,source])=>({cell,source}))};
}
