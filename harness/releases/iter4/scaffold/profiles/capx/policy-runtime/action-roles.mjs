
export function actionRoleSchema(schema){
 const props=schema?.properties??{};
 const key=['kind','action','type','op'].find(k=>(schema.required??[]).includes(k)&&Array.isArray(props[k]?.enum)&&props[k].enum.length);
 if(!key)throw Error('Action-role binding requires a required public enum discriminator');
 return {type:'object',additionalProperties:false,required:[key],properties:{[key]:structuredClone(props[key])}};
}
export function normalizeActionRoles(actions,schema){
 const selector=actionRoleSchema(schema),key=selector.required[0],values=selector.properties[key].enum;
 const result=[],seen=new Map();
 if(!Array.isArray(actions)||!actions.length)throw Error('No action roles');
 for(const row of actions){
  const value=row?.action?.[key];
  if(!values.includes(value)||!['observe','progress','confirm','refute'].includes(row.kind)||!Number.isFinite(row.cost)||row.cost<0)throw Error('Invalid action role for '+key);
  const prev=seen.get(value);
  const bothNonterminal=prev&&['observe','progress'].includes(prev.kind)&&['observe','progress'].includes(row.kind);
  if(prev&&((prev.kind!==row.kind&&!bothNonterminal)||prev.cost!==row.cost))throw Error('Conflicting roles/costs for '+key+'='+value);
  if(bothNonterminal&&prev.kind!==row.kind)prev.kind='progress';
  if(!prev){const normalized={action:{[key]:value},kind:row.kind,cost:row.cost};seen.set(value,normalized);result.push(normalized);}
 }
 if(values.some(v=>!seen.has(v)))throw Error('Action roles must cover every public '+key+' value');
 return result;
}
