import {createCapabilityScope} from '../../../shared/capability-scope.mjs';
import {createBranchConsultation} from '../../../shared/branch-consultation.mjs';
export const scope=createCapabilityScope(process.env.H0_CAPABILITY_NODE??'d',{profile:'capx'});
export const {path,activeBranch}=scope;
export const {branchTool,branchNotice,consultBranch}=createBranchConsultation(scope);
