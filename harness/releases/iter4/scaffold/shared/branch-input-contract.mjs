
const text={type:'string',minLength:1};
const epoch={anyOf:[text,{type:'integer',minimum:0}]};
const source={type:'string',pattern:'^obs-[0-9]+$'};
const relationFields=['subject','object','relation','frame'];
const evidenceFields=['entity',...relationFields,'visible','source'];
const relationProperties=Object.fromEntries(relationFields.map(k=>[k,text]));
export const branchInputSchema={
  type:'object',additionalProperties:true,required:['observations','budget'],
  properties:{
    observations:{type:'array',maxItems:40,items:{type:'object',required:['source'],properties:{source}}},
    budget:{type:'integer',minimum:0},entity:text,epoch,
    requirements:{type:'object'},
    relations:{type:'array',maxItems:20,items:{type:'object',required:relationFields,properties:relationProperties}},
    relationEvidence:{type:'array',maxItems:40,items:{type:'object',required:evidenceFields,
      properties:{entity:text,...relationProperties,visible:{type:'boolean'},source,epoch}}},
    views:{type:'array',maxItems:16,items:{type:'object'}},
    gates:{type:'array',maxItems:32,items:{type:'object',required:['source'],properties:{source}}},
    stampOrder:{type:'array',maxItems:8},
  },
};

function validate(value,schema,path,errors){
  if(schema.anyOf){
    const options=schema.anyOf.map(s=>{const found=[];validate(value,s,path,found);return found;});
    if(options.every(e=>e.length))errors.push({path,code:'invalid_type',expected:'nonempty string or nonnegative integer'});
    return;
  }
  const type=schema.type;
  const valid=type==='object'?value!==null&&typeof value==='object'&&!Array.isArray(value):
    type==='array'?Array.isArray(value):type==='integer'?Number.isInteger(value):typeof value===type;
  if(!valid){errors.push({path,code:'invalid_type',expected:type});return;}
  if(type==='object'){
    for(const key of schema.required??[])if(!Object.hasOwn(value,key))errors.push({path:path+'.'+key,code:'missing_field'});
    for(const [key,sub] of Object.entries(schema.properties??{}))if(Object.hasOwn(value,key))validate(value[key],sub,path+'.'+key,errors);
  }else if(type==='array'){
    if(schema.maxItems!==undefined&&value.length>schema.maxItems)errors.push({path,code:'too_many_items',maximum:schema.maxItems});
    if(schema.items)for(let i=0;i<Math.min(value.length,schema.maxItems??value.length);i++)validate(value[i],schema.items,`${path}[${i}]`,errors);
  }else if(type==='string'){
    if(schema.minLength&&value.trim().length<schema.minLength)errors.push({path,code:'empty_string'});
    if(schema.pattern&&!new RegExp(schema.pattern).test(value))errors.push({path,code:'invalid_source',expected:schema.pattern});
  }else if(type==='integer'&&schema.minimum!==undefined&&value<schema.minimum)errors.push({path,code:'below_minimum',minimum:schema.minimum});
}

export function validateBranchInput(row,input,step,remaining){
  const errors=[];
  if(!Number.isSafeInteger(step)||step<0||!Number.isSafeInteger(remaining)||remaining<0)
    return [{path:'host',code:'invalid_step_or_budget'}];
  validate(input,branchInputSchema,'input',errors);
  if(!input||typeof input!=='object'||Array.isArray(input))return errors;
  if(JSON.stringify(input).length>16000)errors.push({path:'input',code:'input_too_large',maximum:16000});
  for(const key of row.required??[])if(!Object.hasOwn(input,key)&&!errors.some(e=>e.path==='input.'+key))
    errors.push({path:'input.'+key,code:'missing_module_field'});
  if(Number.isInteger(input.budget)&&input.budget>remaining)errors.push({path:'input.budget',code:'exceeds_remaining_actions',maximum:remaining});
  for(const key of ['observations','relationEvidence','gates']){
    if(!Array.isArray(input[key]))continue;
    for(const [i,item] of input[key].entries()){
      if(!item||typeof item!=='object'||Array.isArray(item))continue;
      const match=/^obs-(\d+)$/.exec(item.source??'');
      if(match&&(!Number.isSafeInteger(Number(match[1]))||Number(match[1])>step))errors.push({path:`input.${key}[${i}].source`,code:'future_observation',latest:step});
      if(item.exits!==undefined&&(!Array.isArray(item.exits)||item.exits.length>16))errors.push({path:`input.${key}[${i}].exits`,code:'invalid_exits'});
    }
  }
  return errors;
}
