

export function decodeTupleAction(action){
 const raw=action?.action;if(typeof raw!=='string')throw Error('Expected public action string');
 const match=raw.match(/FINAL GUESS:\s*(\[[^\]\n]+\])/);if(!match)throw Error('Not a public guess action');
 const a=JSON.parse(match[1].replaceAll("'",'"'));if(!Array.isArray(a)||!a.every(x=>typeof x==='string'))throw Error('Invalid color array');return a;
}
export const mastermindPublicAdapter={decode(ledger){
 const text=ledger[0]?.observation?.publicText??'';
 const n=text.match(/secret code consists of (\d+) colors/i),palette=text.match(/only allowed colors are:\s*(\[[^\]]+\])/i);
 if(!n||!palette)return {applicable:false,complete:false,records:[],reason:'This adapter has no verified public format mapping for the observation'};
 const colors=JSON.parse(palette[1].replaceAll("'",'"'));const size=+n[1];if(!size||size>8||!colors.every(x=>typeof x==='string')||colors.length>16)throw Error('Unsupported public domain');
 const records=[];let complete=true;
 for(const row of ledger.slice(1)){
  const s=row.observation?.publicText??'',m=s.match(/Feedback: Correct color and position:\s*(\d+)\. Correct color but wrong position:\s*(\d+)/);
  if(!m){complete=false;continue;}
  records.push({probe:decodeTupleAction(row.action),actual:[+m[1],+m[2]],index:row.index,evidenceId:'world-feedback-'+row.index});
 }
 return {applicable:true,complete,records,domains:Array.from({length:size},()=>colors),exhaustive:true,params:{mode:'sequence',permutations:[]},identity:{format:'public-code-feedback-v1',size,colors,permutations:[]},source:{observation:'initial public game rules',domain:'listed colors and declared code length; includes duplicates as public rules permit',transition:'public game describes one chosen secret code, no between-action state transform'},assumptions:['Public task describes fixed code and deterministic feedback; parser verifies format, not natural-language rule correctness.'],encode:c=>({action:'FINAL GUESS: '+JSON.stringify(c)}),decodeAction:decodeTupleAction};
}};
export const unsupportedPublicAdapter={decode(){return{applicable:false,complete:false,records:[],reason:'No public format adapter registered; do not claim verification for this task'};}};

const cardFields=s=>{const rank=Number(s.slice(0,-1)),suit=s.slice(-1);if(!Number.isInteger(rank)||rank<1||rank>13||!['C','D','H','S'].includes(suit))throw Error('Bad public card');return{rank,suit,color:['D','H'].includes(suit)?'red':'black',parity:rank%2};};
const fieldExpr=x=>typeof x==='string'&&/^(previous|candidate)\.(rank|suit|color|parity)$/.test(x)?['get',['get',['var','probe'],['lit',x.split('.')[0]]],['lit',x.split('.')[1]]]:['lit',x];
function translateRule(r,depth=0){if(depth>4||!r||typeof r!=='object')throw Error('Public predicate grammar depth/type');
 if(r.op==='and'||r.op==='or'){if(!Array.isArray(r.args)||r.args.length<2||r.args.length>4)throw Error('Invalid Boolean arity');return r.args.map(x=>translateRule(x,depth+1)).reduce((a,b)=>[r.op,a,b]);}
 if(r.op==='not')return['not',translateRule(r.arg,depth+1)];
 if(!['eq','neq','lt','gt'].includes(r.op))throw Error('Unknown public predicate');return[r.op==='neq'?'ne':r.op,fieldExpr(r.left),fieldExpr(r.right)];
}
const publicCardState=obs=>JSON.parse((obs?.publicText??'').split('\n').slice(1).join('\n'));
const isCardState=state=>state&&Array.isArray(state.mainline)&&Array.isArray(state.sidelines)&&typeof state.guessAllowed==='boolean';
export const eleusisPublicAdapter={decode(ledger,hypotheses){
 if(!isCardState(publicCardState(ledger[0]?.observation)))return unsupportedPublicAdapter.decode();
 if(!Array.isArray(hypotheses)||!hypotheses.length||hypotheses.length>64)return{applicable:false,complete:false,records:[],reason:'Supply 1..64 candidate native rule ASTs in hypotheses. These are proposed hypotheses, not predictions or feedback. Public ledger is attached automatically.'};
 const now=publicCardState(ledger.at(-1).observation),records=[];if(!isCardState(now))throw Error('Incomplete public predicate state');
 for(let i=1;i<now.mainline.length;i++)records.push({probe:{previous:cardFields(now.mainline[i-1]),candidate:cardFields(now.mainline[i])},actual:true,index:i,evidenceId:'mainline-'+i});
 for(let i=0;i<now.sidelines.length;i++){const s=now.sidelines[i];records.push({probe:{previous:cardFields(now.mainline[s.after]),candidate:cardFields(s.card)},actual:false,index:i,evidenceId:'sideline-'+i});}
 const rejected=new Set(ledger.slice(1).filter(r=>r.action?.action==='guess_rule'&&publicCardState(r.observation).verdict==='rule guess incorrect').map(r=>JSON.stringify(translateRule(r.action.statement))));
 const original=new Map(hypotheses.map(h=>[JSON.stringify(translateRule(h)),structuredClone(h)]));for(const k of rejected)original.delete(k);
 return{applicable:true,complete:true,records,hypotheses:[...original.keys()].map(JSON.parse),exhaustive:false,params:{mode:'predicate',permutations:[]},identity:{format:'public-predicate-grammar-v1',hypotheses:[...original.keys()]},source:{observations:'public mainline and sidelines; publicly incorrect rule guesses excluded',hypotheses:'Player-proposed native ASTs translated syntactically; not a complete rule space'},assumptions:['Observed acceptance examples cannot prove extensional equivalence on unobserved card pairs.'],canCommit:now.guessAllowed===true,encode:c=>({action:'guess_rule',statement:original.get(JSON.stringify(c))}),decodeAction:a=>translateRule(a.statement)};
}};

export const publicFormatAdapter={decode(ledger,hypotheses){
 const text=ledger[0]?.observation?.publicText??'';
 const sequence=/secret code consists of (\d+) colors/i.test(text)&&/only allowed colors are:\s*(\[[^\]]+\])/i.test(text);
 let predicate=false;try{predicate=Boolean(isCardState(publicCardState(ledger[0]?.observation)));}catch{}
 if(sequence&&predicate)throw Error('Ambiguous public format');
 if(sequence)return mastermindPublicAdapter.decode(ledger,hypotheses);
 if(predicate)return eleusisPublicAdapter.decode(ledger,hypotheses);
 return unsupportedPublicAdapter.decode();
}};
