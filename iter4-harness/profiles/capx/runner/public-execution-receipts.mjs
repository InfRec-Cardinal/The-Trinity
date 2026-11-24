

export class PublicExecutionReceipts {
  #rows=[];
  record(action,publicText) {
    this.#rows.push({action:structuredClone(action),publicText:String(publicText??'')});
  }
  snapshot() {
    const arms={0:{moveCommands:0,closeCommands:0,openCommands:0,homeCommands:0,turnCommands:0},1:{moveCommands:0,closeCommands:0,openCommands:0,homeCommands:0,turnCommands:0}};
    for(const arm of Object.values(arms))Object.assign(arm,{commandOffsetSinceHomeCm:{right:0,forward:0,up:0},commandOffsetReliable:true,lastCloseCommandOffsetCm:null});
    let actCalls=0,finishCalls=0;
    for(const {action,publicText} of this.#rows){
      if(action.kind==='act')actCalls++;
      if(action.kind==='finish')finishCalls++;
      for(const [i,m] of (action.moves??[]).entries()){
        const arm=arms[m.arm];if(!arm)continue;
        const field={move:'moveCommands',close:'closeCommands',open:'openCommands',home:'homeCommands',turn:'turnCommands'}[m.op];
        if(field)arm[field]++;
        const feedback=publicText.split('\n').find(line=>line.startsWith(`${i+1}. arm ${m.arm} `))??'';
        if(m.op==='home'){
          if(feedback.endsWith(': done')){arm.commandOffsetSinceHomeCm={right:0,forward:0,up:0};arm.commandOffsetReliable=true;arm.lastCloseCommandOffsetCm=null;}
          else arm.commandOffsetReliable=false;
        }
        if(m.op==='move'){
          for(const [axis,key] of [['right','right_cm'],['forward','forward_cm'],['up','up_cm']])arm.commandOffsetSinceHomeCm[axis]+=Number(m[key]??0);
          if(!feedback.endsWith(': done'))arm.commandOffsetReliable=false;
        }
        if(m.op==='close')arm.lastCloseCommandOffsetCm=arm.commandOffsetReliable?structuredClone(arm.commandOffsetSinceHomeCm):null;
      }
    }
    return {nativeActions:this.#rows.length,actCalls,finishCalls,arms,
      recent:this.#rows.slice(-3).map((r,i)=>({source:'obs-'+(this.#rows.length-Math.min(3,this.#rows.length)+i+1),action:structuredClone(r.action),publicFeedback:r.publicText})),
      semantics:'Public command receipts only. Offsets are requested command sums since initial pose or a completed home, NOT measured pose. Reliable means moves reported done, not absence of drift. Stopped/unknown motion invalidates the reference until completed home. Counts and offsets are not cup-specific and do not establish contact, a held object or task success.'};
  }
}
