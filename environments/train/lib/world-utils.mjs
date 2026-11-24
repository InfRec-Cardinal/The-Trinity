                                                                                                
export function random(seed){let s=seed>>>0;return()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296;};}
export function shuffle(values,rng){const a=values.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[a[i],a[j]]=[a[j],a[i]];}return a;}
export function normalizeObject(input,keys){if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!keys.includes(k)))return null;return clone(input);}
export function terminal(state,maxSteps){if(!state.ended&&state.step>=maxSteps){state.ended=true;state.outcome='failure';state.reason='action_budget_exhausted';}return {ended:Boolean(state.ended),outcome:state.outcome??null,reason:state.reason??null,...(state.score!=null?{score:state.score}:{}),...(state.ended&&state.evaluation?{evaluation:state.evaluation}:{})};}
const clone = value => JSON.parse(JSON.stringify(value));
