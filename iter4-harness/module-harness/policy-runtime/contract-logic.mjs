
export function validateLogicalContract(c,publicText,nativeSchema){
 const issues=[],id=x=>typeof x==='string'&&/^[A-Za-z][A-Za-z0-9_-]{0,47}$/.test(x);
 const quote=x=>typeof x==='string'&&x.trim()&&publicText.includes(x);
 const norm=x=>String(x).trim().toLowerCase().replace(/\s+/g,' ');
 if(c.logicVersion!==2)issues.push('logicVersion must be 2; quantified obligations require explicit subject/predicate bindings');
 if(!Array.isArray(c.domains)||!c.domains.length||c.domains.length>8)return [...issues,'Declare 1..8 publicly grounded domains'];
 const domains=new Map();
 for(const d of c.domains){
  if(!d||!id(d.id)||domains.has(d.id)){issues.push('Invalid/duplicate domain identity');continue;}
  domains.set(d.id,d);
  if(!quote(d.contractQuote)||typeof d.closed!=='boolean')issues.push('Domain needs public quote and explicit closed/open scope: '+d.id);
  if(!Array.isArray(d.members)||d.members.length>16){issues.push('Domain members must be bounded explicit identities: '+d.id);d.members=[];}
  if(d.members.some(m=>!m||!id(m.id)||typeof m.label!=='string'||!m.label.trim()||m.label.length>512))issues.push('Invalid domain member: '+d.id+'; use a valid id and a nonempty public label of at most 512 characters');
  if(new Set(d.members.map(m=>m?.id)).size!==d.members.length||new Set(d.members.map(m=>norm(m?.label))).size!==d.members.length)issues.push('Duplicate member or label alias in '+d.id);
  if(d.expectedCount!==null&&(!Number.isInteger(d.expectedCount)||d.expectedCount<1||d.expectedCount>16))issues.push('Invalid expected domain cardinality: '+d.id);
  if(d.closed){
   if(d.expectedCount!==d.members.length||!d.members.length)issues.push('Closed domain must enumerate its full positive expectedCount: '+d.id);
   const numeric=typeof d.contractQuote==='string'&&new RegExp('(^|\\D)'+d.expectedCount+'(\\D|$)').test(d.contractQuote);
   const enumerated=d.members.length&&d.members.every(m=>typeof m?.label==='string'&&norm(d.contractQuote).includes(norm(m.label)));
   if(!numeric&&!enumerated)issues.push('Closed cardinality/list not grounded in domain quote: '+d.id+'; copy distinct exact label excerpts from the quoted public enumeration, not paraphrases or aliases; do not invent a numeric count');
  }
 }
 if(!Array.isArray(c.requirements)||!c.requirements.length||c.requirements.length>12)return [...issues,'Declare 1..12 goal obligations'];
 const reqs=new Map(c.requirements.map(r=>[r?.id,r])),predicateKinds=new Map();
 for(const r of c.requirements){
  if(!r||!id(r.id)){issues.push('Invalid requirement identity');continue;}
  if(r.description?.length>400)issues.push('Requirement description exceeds 400 characters: '+r.id);
  if(!['state','ever'].includes(r.temporal)||!Object.hasOwn(r,'appliesWhen'))issues.push('Declare temporal and appliesWhen explicitly: '+r.id);
  if(r.logic!==null&&r.logic!==undefined){
   if(!['and','or'].includes(r.logic.op)||!Array.isArray(r.logic.children)||!r.logic.children.length||new Set(r.logic.children).size!==r.logic.children.length)issues.push('Invalid logical composition: '+r.id);
   else for(const child of r.logic.children){const found=reqs.get(child);if(!found||found.role!=='component'||found.appliesWhen!==null)issues.push('Logical children must be unconditional component obligations: '+r.id);}
   if(r.predicate!==null||r.coverage!==null||r.temporal!=='state')issues.push('Composite goals cannot receive atomic observations: '+r.id);
   continue;
  }
  if(r.logic!==null)issues.push('Atomic requirement needs logic:null: '+r.id);
  if(!id(r.predicate))issues.push('Atomic requirement needs one predicate ID: '+r.id);
  const v=r.coverage,d=domains.get(v?.domainId);
  if(!v||!d||!['single','any','all','at_least'].includes(v.mode)){issues.push('Invalid quantified coverage: '+r.id);continue;}
  const key=d.id+'|'+r.predicate,known=predicateKinds.get(key);
  if(known&&known!==r.kind)issues.push('One predicate cannot have conflicting evidence types: '+r.predicate);
  predicateKinds.set(key,r.kind);
  if(v.mode==='single'){
   const fixed=typeof v.subjectId==='string',selected=typeof v.actionField==='string';
   if(fixed===selected||fixed&&!d.members.some(m=>m.id===v.subjectId))issues.push('Single subject must bind one member or one action field: '+r.id);
   if(selected){const prop=nativeSchema?.properties?.[v.actionField],types=Array.isArray(prop?.type)?prop.type:[prop?.type];if(!types.some(t=>['string','number','integer','boolean'].includes(t)))issues.push('Subject selection needs a public scalar action field: '+r.id);}
  }else if(v.subjectId!==null||v.actionField!==null)issues.push('Quantified goals must cover the domain, not a preselected subset: '+r.id);
  if(v.mode==='at_least'){
   if(!Number.isInteger(v.minimum)||v.minimum<1||v.minimum>16||d.closed&&v.minimum>d.expectedCount)issues.push('Invalid required cardinality: '+r.id);
   if(!new RegExp('(^|\\D)'+v.minimum+'(\\D|$)').test(r.contractQuote??''))issues.push('Required count not quoted in public goal: '+r.id);
  }else if(v.minimum!==null)issues.push('minimum is only used by at_least: '+r.id);
 }
 const visiting=new Set(),done=new Set(),referenced=new Set();
 function visit(r){if(!r||done.has(r.id))return;if(visiting.has(r.id)){issues.push('Cyclic goal graph');return;}visiting.add(r.id);for(const child of r.logic?.children??[]){referenced.add(child);visit(reqs.get(child));}visiting.delete(r.id);done.add(r.id);}
 for(const r of c.requirements)visit(r);
 for(const r of c.requirements)if(r.role==='component'&&!referenced.has(r.id))issues.push('Unreferenced component: '+r.id);
 return issues;
}
