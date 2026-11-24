import {catalog,manifest} from '../../../module-harness/harness.mjs';
import {createCapabilityScope} from '../../../shared/capability-scope.mjs';
import {createBranchConsultation} from '../../../shared/branch-consultation.mjs';
export function createArcBranch(node = 'd-a') {
const scope=createCapabilityScope(node,{profile:'arc'});
const {path,activeBranch,invoke}=scope;
const automaticId='explorationRoute';
const {entries:helpers,branchTool,consultBranch}=createBranchConsultation(scope,{excludeIds:[automaticId],toolName:'consult_branch_module'});
const automaticRevision=activeBranch.find(r=>r.moduleId===automaticId)?.version;
if(scope.has(automaticId)&&!Number.isInteger(automaticRevision))throw Error('Missing automatic module revision');
const branchNotice=`Module library ${manifest.harnessId}: ${catalog.nodes.length} total entries. Selected path ${path.join(' -> ')} has ${activeBranch.length} entries and ${helpers.length} optional helpers. ${automaticRevision?`The selected automatic public action/outcome policy executes revision ${automaticRevision}.`:'No automatic action/outcome policy is selected.'} Only use helpers whose public input contracts fit actual evidence. Observation IDs obs-N refer to states after N native actions. No helper establishes hidden facts or overrides native completion. Evidence protocol policies require a compatible native contract. Task skills are caller supplied.`;

return {scope,node,path,activeBranch,automaticId:automaticRevision?automaticId:null,helpers,branchTool,branchNotice,consultBranch,
  selection:{node,path,moduleIds:activeBranch.map(r=>r.moduleId),automaticModuleIds:automaticRevision?[automaticId]:[],helperModuleIds:helpers.map(r=>r.moduleId),registeredModules:activeBranch.length,selectedModules:helpers.length+(automaticRevision?1:0)}};
}
