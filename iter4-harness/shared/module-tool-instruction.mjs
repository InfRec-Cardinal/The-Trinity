const singleToolInstruction='Call submit_action exactly once per response.';

export const validToolName=name=>typeof name==='string'&&/^[A-Za-z_][A-Za-z0-9_-]{0,127}$/.test(name);

export function moduleAwareSystem(system, moduleToolNames){
 const names=(Array.isArray(moduleToolNames)?moduleToolNames:[moduleToolNames]).filter(Boolean);
 if(new Set(names).size!==names.length)throw Error('Duplicate module tool');
 if(!names.length)return system;
 if(names.some(name=>!validToolName(name)))throw Error('Unexpected module tool');
 if(system.split(singleToolInstruction).length!==2)throw Error('Ambiguous/missing legacy single-tool instruction');
 return system.replace(singleToolInstruction,
  `Call exactly one of the tools offered in this response. You may submit an environment action with submit_action, or use ${names.join(' or ')} when an active module is applicable and useful. A module call only transforms supplied public evidence and does not execute an environment action; inspect its returned result before choosing the next tool. Module calls are optional. Host execution receipts supply command counts; do not maintain a process log in tool arguments. Where the schema requests expectedObservation, provide only a brief publicly observable result expected after that candidate action.`);
}

export function toolInstructionCandidates(text){
 const candidates=new Set([singleToolInstruction]);
 for(const match of text.matchAll(/or use ([A-Za-z_][A-Za-z0-9_-]*(?: or [A-Za-z_][A-Za-z0-9_-]*)*) when an active module is applicable and useful\./g)){
  const names=match[1].split(' or '),current=moduleAwareSystem(singleToolInstruction,names);
  const short=current.slice(0,current.indexOf(' Host execution receipts'));
  candidates.add(current);candidates.add(short);candidates.add(short.replace('supplied public evidence','supplied evidence'));
 }
 return [...candidates].sort((a,b)=>b.length-a.length);
}
