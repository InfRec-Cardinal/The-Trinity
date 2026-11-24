import {installRelease,recipes,sourceLock} from '../harness/releases/iter4/module-library/release.mjs';
import {digest,ensure} from '../harness/src/core.mjs';
export function loadModuleRelease(name){
 ensure(name==='iter4','Unknown module release');
 const installed=installRelease();
 return {...installed,identity:{name,revision:digest({recipes,sourceLock})}};
}
