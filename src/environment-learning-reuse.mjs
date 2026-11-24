import fs from 'node:fs';
import path from 'node:path';
import {clone, digest, ensure, verifyLedger} from '../harness/src/core.mjs';
import {verifyTerminalReceipt} from '../harness/src/receipts.mjs';

const phases = ['environment_learning', 'environment_training_side_evaluation'];
export function learningContract(plan, executionIdentity, driverOptions = {}) {
                                                                                             
  const {taskIds, treeLayer, ...policy} = plan;
  return {schema: 'trinity-learning-reuse-v1', policy: clone(policy), executionIdentity: clone(executionIdentity), driverOptions: clone(driverOptions)};
}
export const reusableContract = contract => contract?.schema === 'trinity-learning-reuse-v1' && contract.executionIdentity !== null && contract.executionIdentity !== undefined;
const object = (directory, id) => {
  ensure(typeof id === 'string' && /^[a-f0-9]{64}$/.test(id), 'Invalid reuse object id');
  const value = JSON.parse(fs.readFileSync(path.join(directory, 'objects', id + '.json'), 'utf8'));
  ensure(digest(value) === id, 'Reuse object integrity mismatch');
  return value;
};
function eventBinding(event, hash, type) {
  ensure(event?.hash === hash && event.type === type, 'Missing reuse provenance event');
  const {hash: actual, ...body} = event;
  ensure(digest(body) === actual, 'Reuse provenance integrity mismatch');
}
export function verifyReusableEpisode(report, proof, contract) {
  ensure(reusableContract(contract) && digest(report.learningContract) === digest(contract), 'Reuse execution contract mismatch');
  ensure(phases.includes(report.phase) && !report.technicalFailure, 'Invalid reuse phase or technical failure');
  eventBinding(proof.start, report.episodeId, 'episode_started');
  eventBinding(proof.frozen, report.instancePlan, 'initial_instances_frozen');
  ensure(proof.frozen.sequence < proof.start.sequence, 'Reuse instances were not frozen before execution');
  for (const key of ['learningContract', 'taskId', 'node', 'phase', 'iteration', 'benchmarkId', 'split', 'budget', 'budgetUnit', 'interactionLimit', 'instance', 'expectedInitialStateHash', 'instancePlan', 'worldDigest', 'harnessId', 'decisionId'])
    ensure(digest(proof.start.payload[key] ?? null) === digest(report[key] ?? null), 'Reuse start binding mismatch: ' + key);
  ensure(digest(proof.plan) === proof.frozen.payload.artifact && digest(proof.plan) === proof.frozen.payload.planDigest && proof.plan.taskId === report.taskId && proof.plan.worldDigest === report.worldDigest, 'Invalid reuse instance plan');
  ensure(report.initialStateHash === report.expectedInitialStateHash && proof.plan.instances.some((instance, i) => digest(instance) === digest(report.instance) && proof.plan.initialStateHashes[i] === report.initialStateHash), 'Reuse initial state mismatch');
  verifyTerminalReceipt(report, report);
  return report;
}

                                                                                                       
                                                                                                        
export function loadLearningReuse(sources, {onDiagnostic = () => {}} = {}) {
  const out = Object.create(null);
  for (const {directory, source = directory} of sources) {
    try {
      const ledgerFile = path.join(directory, 'events.jsonl');
      ensure(!verifyLedger(ledgerFile).truncatedTail, 'Truncated reuse ledger');
      const events = fs.readFileSync(ledgerFile, 'utf8').trim().split('\n').map(JSON.parse);
      ensure(events[0]?.type === 'run_started', 'Missing reuse run configuration');
      const config = object(directory, events[0].payload.configDigest), contract = config.learningContract;
      if (!reusableContract(contract)) {onDiagnostic({source, directory, reason: 'incompatible_contract'}); continue;}
      const byHash = new Map(events.map(event => [event.hash, event])), available = new Map(), staged = Object.create(null);
      const task = id => staged[id] ??= {environment_learning: [], environment_training_side_evaluation: [], proposals: []};
      for (const event of events) {
        const p = event.payload;
        if (['episode_finished', 'episode_reused'].includes(event.type) && phases.includes(p.phase) && !p.technicalFailure) {
          const {reuseProofDigest, reusedFrom, ...report} = p;
          const start = byHash.get(report.episodeId), frozen = byHash.get(report.instancePlan);
          const proof = event.type === 'episode_reused' ? object(directory, reuseProofDigest)
            : {start, frozen, plan: object(directory, frozen?.payload.artifact)};
          if (event.type === 'episode_finished') ensure(start.sequence < event.sequence, 'Reuse finish precedes start');
          verifyReusableEpisode(report, proof, contract);
          const entry = {report, proof, source};
          task(report.taskId)[report.phase].push(entry); available.set(report.episodeId, report);
        }
        if (event.type === 'explorer_proposal_saved') {
          ensure(digest(p.learningContract) === digest(contract), 'Proposal execution contract mismatch');
          const request = object(directory, p.requestDigest), value = object(directory, p.proposalDigest);
          ensure(Array.isArray(p.trainingEpisodes) && p.trainingEpisodes.length === 5 && new Set(p.trainingEpisodes).size === 5, 'Missing proposal training episodes');
          const reports = p.trainingEpisodes.map(id => available.get(id));
          ensure(reports.every(row => row?.phase === 'environment_learning' && row.taskId === p.taskId && row.iteration === p.epoch && row.node === p.node), 'Proposal training evidence mismatch');
          ensure(p.feedbackDigest === digest(request.packet.feedback) && digest(request.packet.trajectories) === digest(reports.map((row, i) => ({round: i + 1, events: row.events}))), 'Proposal request evidence mismatch');
          task(p.taskId).proposals.push({...p, value, source});
        }
      }
                                                                                                       
      for (const [id, rows] of Object.entries(staged)) {
        const target = out[id] ??= {environment_learning: [], environment_training_side_evaluation: [], proposals: []};
        for (const key of [...phases, 'proposals']) target[key].push(...rows[key]);
      }
    } catch (error) {onDiagnostic({source, directory, reason: 'invalid_source', message: String(error.message)});}
  }
  return out;
}
