const text={type:'string',minLength:1};
const value={type:['string','number','boolean','null']};
const epoch={type:['string','integer']};
const source={type:'string',pattern:'^obs-[0-9]+$'};
const strings={type:'array',maxItems:40,items:text};
const object=(properties,required=[])=>({type:'object',additionalProperties:false,properties,required});
const array=(items,maxItems=40)=>({type:'array',items,maxItems});
const observation=object({entity:text,attribute:text,value,visible:{type:'boolean'},source,epoch},['entity','attribute','value','visible','source']);
const rules=array(object({when:{type:'object',additionalProperties:value},label:text},['when','label']),20);
export const perceptionInputSchema=object({
  mode:{type:'string'},
  observations:array(observation),entities:strings,epoch,rules,requiredAttributes:strings,
  requirements:array(object({entity:text,attribute:text},['entity','attribute'])),
  stations:array(object({id:text,covers:strings,cost:{type:'number',minimum:0}},['id','covers','cost']),16),
  budget:{type:'integer',minimum:0},submitCost:{type:'number',minimum:0},reports:{type:'object',additionalProperties:text},
  frames:array(object({source,epoch,face:text,publicSlotToEntity:{type:'object',additionalProperties:text},
    rows:array(object({slot:{type:['string','integer']},entity:text,value,visible:{type:'boolean'}},['value','visible']))},['source','face','rows']),16),
});
