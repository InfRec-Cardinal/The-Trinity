

const escaped=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
export default function constraintAudit({text,constraints=[],forbidBranching=false}){
  if(typeof text!=='string'||text.length>60000)throw Error('Bounded proposal text required');
  const body=text.includes('[Step description]:')?text.split('[Step description]:').slice(1).join('[Step description]:'):text;
  const violations=[];
  for(const rule of constraints){
    if(typeof rule.source!=='string'||!rule.terms?.length)throw Error('Each public constraint needs a source and terms');
    const matches=rule.terms.filter(t=>[...body.matchAll(new RegExp('\\b'+escaped(t)+'(?:s|es)?\\b','gi'))].some(m=>{
      const before=body.slice(Math.max(0,m.index-45),m.index);
      return !/(?:do not use|never use|avoid(?: using)?|without(?: using)?|no)\s+(?:any\s+|a\s+)?$/i.test(before);
    }));
    if(matches.length)violations.push({id:rule.id,source:rule.source,matchedTerms:matches,constraint:rule.publicText});
  }
  if(forbidBranching){
    const matches=[...body.matchAll(/\b(?:if|either|alternatively|otherwise)\b/gi)].map(m=>m[0]);
    if(matches.length)violations.push({id:'single-unbranched-plan',source:'obs-0',matchedTerms:matches,constraint:'The public initial contract requires one plan without conditional alternatives.'});
  }
  return {status:violations.length?'revise':'no_detected_conflict',violations,
    scope:'Checks only supplied public negative constraints and their explicit alias sets. Not a proof of physical effectiveness or native success.',noWorldActionExecuted:true};
}
