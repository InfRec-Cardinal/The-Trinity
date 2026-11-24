import {isDeepStrictEqual} from 'node:util';
import {validateDesign} from './design.mjs';

                                                                                         
export function screeningContract({onFreeze=()=>{}}={}) {
  let frozen=null;
  return {
    get value(){return frozen?structuredClone(frozen):null;},
    pin(design){
      const errors=validateDesign(design);
      if(errors.length)throw Error('Invalid screening design: '+errors.join('; '));
      if(!Number.isSafeInteger(design.actionBudget)||design.actionBudget<=0)throw Error('Screening design must declare a positive actionBudget before construction');
      const dimensions=design.difficultyDimensions;
      if(new Set(dimensions.map(d=>d.name)).size!==dimensions.length||dimensions.some(d=>d.range[0]>d.range[1]))throw Error('Invalid screening difficulty ranges');
      const next={schema:'trinity-studio-screening-contract-v1',design:structuredClone(design),actionBudget:design.actionBudget,
        policy:{trials:3,minSuccesses:1,maxSuccesses:2},retryLimit:3};
      if(frozen&&!isDeepStrictEqual(frozen,next))throw Error('Screening contract changed within the same iteration');
      if(!frozen){frozen=next;onFreeze(structuredClone(frozen));}
      return structuredClone(frozen);
    },
    check(built){
      if(!frozen)throw Error('Screening contract was not frozen before construction');
      if(!isDeepStrictEqual(built.design,frozen.design))throw Error('Screening design changed within the same iteration');
      if(built.budget!==frozen.actionBudget)throw Error('Screening action budget changed within the same iteration');
    },
  };
}
