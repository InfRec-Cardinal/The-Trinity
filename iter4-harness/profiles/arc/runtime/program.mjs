
export const OPS={interpret:'evaluate a bounded supplied expression with ONLY probe in scope',lit:'literal JSON',var:'named variable',get:'own field/index',let:'sequential bindings and body',if:'lazy branch',map:'array/name/body',filter:'array/name/body',all:'array/name/body',any:'array/name/body',fold:'array/itemName/accName/initial/body',eq:'structural equality',ne:'inequality',lt:'numeric comparison',le:'numeric comparison',gt:'numeric comparison',ge:'numeric comparison',add:'number addition',sub:'subtraction',mul:'multiplication',div:'division',mod:'nonnegative modulo',and:'lazy conjunction',or:'lazy disjunction',not:'boolean negation',len:'array/string length',range:'0..n-1',sum:'sum numeric array',min:'min numeric array',max:'max numeric array',unique:'distinct array values',concat:'concatenate arrays',append:'array plus value',reverse:'reverse array',rotate:'left rotate by n',slice:'array,start,end',object:'object from expression fields',predict:'candidate,record; protected predictor callback available ONLY to selection program'};
const forbidden=new Set(['__proto__','constructor','prototype']);
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function fail(s){throw Error(s)}
function array(x){if(!Array.isArray(x)||x.length>20000)fail('Expected bounded array');return x;}
function num(x){if(typeof x!=='number'||!Number.isFinite(x))fail('Expected finite number');return x;}
function bool(x){if(typeof x!=='boolean')fail('Expected boolean');return x;}
export function validateExpression(expr,variables,{allowPredict=false,maxNodes=2500}={}){
 let n=0;
 const identifier=s=>{if(typeof s!=='string'||!/^[_a-zA-Z][_a-zA-Z0-9]*$/.test(s)||forbidden.has(s))fail('Invalid variable');};
 function visit(e,scope,depth=0){if(++n>maxNodes||depth>48)fail('Expression too large/deep');if(!Array.isArray(e)||typeof e[0]!=='string'||!OPS[e[0]])fail('Unknown expression operation');
  const [op,...a]=e;
  const arities={interpret:[2],lit:[1],var:[1],get:[2],let:[2],if:[3],map:[3],filter:[3],all:[3],any:[3],fold:[5],eq:[2],ne:[2],lt:[2],le:[2],gt:[2],ge:[2],add:[2],sub:[2],mul:[2],div:[2],mod:[2],and:[2],or:[2],not:[1],len:[1],range:[1],sum:[1],min:[1],max:[1],unique:[1],concat:[2],append:[2],reverse:[1],rotate:[2],slice:[3],object:[1],predict:[2]};
  if(!arities[op].includes(a.length))fail('Wrong arity: '+op);
  if(op==='lit'){if(JSON.stringify(a[0]).length>12000)fail('Literal too large');return;}
  if(op==='var'){identifier(a[0]);if(!scope.has(a[0]))fail('Forbidden/unbound variable: '+a[0]);return;}
  if(op==='predict'&&!allowPredict)fail('Predict cannot recursively read records');
  if(op==='let'){if(!a[0]||Array.isArray(a[0])||typeof a[0]!=='object')fail('Invalid let');const next=new Set(scope);for(const [k,v] of Object.entries(a[0])){identifier(k);if(next.has(k))fail('No shadowing');visit(v,next,depth+1);next.add(k);}visit(a[1],next,depth+1);return;}
  if(['map','filter','all','any'].includes(op)){visit(a[0],scope,depth+1);identifier(a[1]);if(scope.has(a[1]))fail('No shadowing');visit(a[2],new Set([...scope,a[1]]),depth+1);return;}
  if(op==='fold'){visit(a[0],scope,depth+1);visit(a[3],scope,depth+1);identifier(a[1]);identifier(a[2]);if(scope.has(a[1])||scope.has(a[2])||a[1]===a[2])fail('No shadowing');visit(a[4],new Set([...scope,a[1],a[2]]),depth+1);return;}
  if(op==='object'){if(!a[0]||Array.isArray(a[0])||typeof a[0]!=='object')fail('Invalid object');for(const [k,v] of Object.entries(a[0])){if(forbidden.has(k))fail('Forbidden property');visit(v,scope,depth+1);}return;}
  for(const v of a)visit(v,scope,depth+1);
 }
 visit(expr,new Set(variables));return {nodes:n};
}
export function evaluate(expr,scope,{budget={remaining:5000000},predict=null}={}){
 function run(e,env,depth=0){if(--budget.remaining<0)fail('Computation budget exhausted');if(depth>64)fail('Runtime depth exhausted');const [op,...a]=e;const r=x=>run(x,env,depth+1);let x,y;
  switch(op){
   case'lit':return structuredClone(a[0]);case'var':if(!Object.hasOwn(env,a[0]))fail('Missing variable');return env[a[0]];
   case'get':x=r(a[0]);y=r(a[1]);if(forbidden.has(String(y))||x===null||typeof x!=='object'||!Object.hasOwn(x,y))fail('Missing/forbidden field: '+y);return x[y];
   case'let':x={...env};for(const[k,v]of Object.entries(a[0]))x[k]=run(v,x,depth+1);return run(a[1],x,depth+1);
   case'if':return r(bool(r(a[0]))?a[1]:a[2]);
   case'map':return array(r(a[0])).map(v=>run(a[2],{...env,[a[1]]:v},depth+1));
   case'filter':return array(r(a[0])).filter(v=>bool(run(a[2],{...env,[a[1]]:v},depth+1)));
   case'all':return array(r(a[0])).every(v=>bool(run(a[2],{...env,[a[1]]:v},depth+1)));
   case'any':return array(r(a[0])).some(v=>bool(run(a[2],{...env,[a[1]]:v},depth+1)));
   case'fold':x=r(a[3]);for(const v of array(r(a[0])))x=run(a[4],{...env,[a[1]]:v,[a[2]]:x},depth+1);return x;
   case'eq':return equal(r(a[0]),r(a[1]));case'ne':return !equal(r(a[0]),r(a[1]));
   case'lt':return num(r(a[0]))<num(r(a[1]));case'le':return num(r(a[0]))<=num(r(a[1]));case'gt':return num(r(a[0]))>num(r(a[1]));case'ge':return num(r(a[0]))>=num(r(a[1]));
   case'add':return num(r(a[0]))+num(r(a[1]));case'sub':return num(r(a[0]))-num(r(a[1]));case'mul':return num(r(a[0]))*num(r(a[1]));
   case'div':x=num(r(a[0]));y=num(r(a[1]));if(y===0)fail('Division by zero');return x/y;
   case'mod':x=num(r(a[0]));y=num(r(a[1]));if(y<=0)fail('Invalid modulus');return((x%y)+y)%y;
   case'and':return bool(r(a[0]))&&bool(r(a[1]));case'or':return bool(r(a[0]))||bool(r(a[1]));case'not':return !bool(r(a[0]));
   case'len':x=r(a[0]);if(!Array.isArray(x)&&typeof x!=='string')fail('Expected sequence');return x.length;
   case'range':x=num(r(a[0]));if(!Number.isInteger(x)||x<0||x>20000)fail('Range cap');return Array.from({length:x},(_,i)=>i);
   case'sum':return array(r(a[0])).reduce((s,v)=>s+num(v),0);
   case'min':x=array(r(a[0])).map(num);if(!x.length)fail('Empty minimum');return Math.min(...x);
   case'max':x=array(r(a[0])).map(num);if(!x.length)fail('Empty maximum');return Math.max(...x);
   case'unique':return [...new Map(array(r(a[0])).map(v=>[JSON.stringify(v),v])).values()];
   case'concat':return array([...array(r(a[0])),...array(r(a[1]))]);case'append':return array([...array(r(a[0])),r(a[1])]);
   case'reverse':return [...array(r(a[0]))].reverse();case'rotate':x=array(r(a[0]));y=num(r(a[1]));if(!Number.isInteger(y))fail('Noninteger rotation');if(!x.length)return[];y=((y%x.length)+x.length)%x.length;return [...x.slice(y),...x.slice(0,y)];
   case'slice':return array(r(a[0])).slice(num(r(a[1])),num(r(a[2])));
   case'object':return Object.fromEntries(Object.entries(a[0]).map(([k,v])=>[k,r(v)]));
   case'interpret':{const ast=r(a[0]),probe=r(a[1]);validateExpression(ast,['probe'],{maxNodes:300});return evaluate(ast,{probe},{budget});}
   case'predict':if(!predict)fail('Predict unavailable');return predict(r(a[0]),r(a[1]));
   default:fail('Unsupported operation');
  }
 }
 const value=run(expr,scope);if(JSON.stringify(value).length>2000000)fail('Result size cap');return value;
}
export function product(domains,max=20000){let rows=[[]];for(const d of domains){array(d);if(!d.length||rows.length*d.length>max)fail('Candidate domain cap/empty domain');rows=rows.flatMap(r=>d.map(v=>[...r,v]));}return rows;}
export {equal};
