import {readFileSync} from 'node:fs';
import {makeArcAgi3Driver} from './src/h0-arc-agi3.mjs';
import {withCompactLargeObservation} from './src/h0-large-observation-driver-v1.mjs';
const configurations=JSON.parse(readFileSync(new URL('./configurations.json',import.meta.url))).configurations;
export async function createDriver({root}) {
 return withCompactLargeObservation('arc_agi_3',makeArcAgi3Driver({root,spec:{
  taskId:'arc_agi_3',id:'official-native-independent-level-driver',version:2,maxSteps:Math.max(...configurations.map(c=>c.maxSteps)),configurations,
  configurationSelection:{mode:'fixed',availableCount:configurations.length,providerId:'pinned-native-independent-levels',providerVersion:1,sourceScope:'Each original level independently initialized; no prior-level credit.'},
  actionContract:'Complete the selected level using public actions. GAME_OVER is NOT the end of this evaluation: the harness automatically submits RESET without a model call and continues the same sample. Voluntary RESET is available during play except before the first action or immediately after RESET. All accepted actions, including RESET and actions before death, accumulate for efficiency scoring and the evaluation budget. ACTION6 requires integer x,y in0..63. The public available_actions includes0 for RESET, and only0 after GAME_OVER. One selected native-level completion ends success; the configured evaluation action budget ends the sample if unsolved. Each level starts independently. If a full RESET returns the engine to its first level, the independent sampler re-selects this pinned level without awarding prior-level credit. Module consultations do not consume game actions. No hidden goal or solution is supplied.',
  source:{kind:'official-native-with-independent-level-wrapper',protocol:'independent-native-level-reset-v2',reconstructed:false,limitations:['Independent-start results are not comparable to sequential whole-game scores. No online leaderboard claim.']}
 }}));
}
