

export class PublicExecutionReceipts {
 #rows=[];
 record(action,publicText){
  this.#rows.push({action:structuredClone(action),publicText:String(publicText??'')});
 }
 evidenceHistory(){return this.#rows.map((r,i)=>({source:'obs-'+(i+1),action:structuredClone(r.action),publicFeedback:r.publicText}));}
 snapshot(){
  const commandCounts=Object.create(null),arms=Object.create(null);
  for(const {action} of this.#rows){
   const kind=typeof action==='string'?action:action.kind??action.action;
   if(typeof kind==='string')commandCounts[kind]=(commandCounts[kind]??0)+1;
   for(const move of Array.isArray(action?.moves)?action.moves:[]){
    if(![0,1].includes(move.arm))continue;
    const field={move:'moveCommands',close:'closeCommands',open:'openCommands',home:'homeCommands',turn:'turnCommands'}[move.op];
    if(!field)continue;
    arms[move.arm]??={moveCommands:0,closeCommands:0,openCommands:0,homeCommands:0,turnCommands:0};
    arms[move.arm][field]++;
   }
  }
  return {nativeActions:this.#rows.length,commandCounts,arms,
   recent:this.#rows.slice(-3).map((r,i)=>({source:'obs-'+(this.#rows.length-Math.min(3,this.#rows.length)+i+1),action:structuredClone(r.action),publicFeedback:r.publicText})),
   semantics:'Executed command receipts only. Counts are not entity-specific and do not establish measured pose, displacement, contact, a held object or task success.'};
 }
}
