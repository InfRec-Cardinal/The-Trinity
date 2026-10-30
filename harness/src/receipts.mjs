import fs from 'node:fs';
import path from 'node:path';
import {clone, digest, ensure, snapshot, verifyLedger} from './core.mjs';

export function sealTerminalReceipt(report, {decisionId = null, budget, termination}) {
  ensure(!report.technicalFailure, 'Technical failures have no verified terminal receipt');
  if (report.phase === 'initial_training_exploration') ensure(report.instance !== null && typeof report.instancePlan === 'string' &&
    typeof report.initialStateHash === 'string' && report.initialStateHash === report.expectedInitialStateHash, 'Initial exploration must match its frozen state');
  const actions = report.events.filter(event => event.publicData?.action).map(event => event.publicData);
  ensure(actions.length === report.actions && actions.length > 0, 'Incomplete execution evidence');
  ensure(Number.isInteger(budget) && budget > 0 && actions.length <= budget, 'Terminal execution exceeds its committed budget');
  ensure(actions.every((step, index) => step.step === index + 1 && Number.isFinite(step.receipt.cost) && step.receipt.cost >= 0), 'Invalid execution evidence');
  ensure(actions.slice(0, -1).every(step => step.receipt.done === false), 'Execution continued after termination');
  const last = actions.at(-1).receipt;
  if (termination === 'environment') {
    ensure(last.done === true && last.success === report.success, 'Missing environment terminal receipt');
    ensure((last.score ?? null) === report.score, 'Terminal score mismatch');
  } else {
    ensure(termination === 'host_budget_exhausted' && actions.length === budget && last.done === false && report.success === false,
      'Invalid host budget settlement');


    ensure((last.score ?? null) === report.score, 'Budget settlement score mismatch');
  }
  const cost = actions.reduce((sum, step) => sum + step.receipt.cost, 0);
  ensure(cost === report.cost, 'Terminal cost mismatch');
  const receipt = {schema: 'trinity-terminal-v1', episodeId: report.episodeId, decisionId,
    harnessId: report.harnessId, worldDigest: report.worldDigest, budget, termination,
    actions: report.actions, success: report.success, score: report.score, cost,
    instanceDigest: digest(report.instance ?? null), initialStateHash: report.initialStateHash ?? null,
    expectedInitialStateHash: report.expectedInitialStateHash ?? null, instancePlan: report.instancePlan ?? null,
    evidenceDigest: digest(report.events), publicTaskDigest: digest(report.publicTask)};
  return {receipt, hash: digest(receipt)};
}

export function verifyTerminalReceipt(report, expected) {
  ensure(report.terminalReceipt && !report.technicalFailure, 'Verified terminal receipt required');
  const {receipt, hash} = report.terminalReceipt;
  ensure(hash === digest(receipt), 'Terminal receipt integrity mismatch');
  for (const key of ['episodeId', 'decisionId', 'harnessId', 'worldDigest', 'budget']) {
    ensure(Object.hasOwn(expected, key) && receipt[key] === expected[key], 'Terminal receipt binding mismatch: ' + key);
  }
  const sealed = sealTerminalReceipt(report, receipt);
  ensure(sealed.hash === hash, 'Terminal receipt disagrees with execution evidence');
  return clone(receipt);
}

export function verifyRoutedReceipt(report, {store, decisionId, harnessId, worldDigest, budget}) {
  const decision = store.readEvent(decisionId);
  ensure(decision?.type === 'routing_committed' && decision.payload.selection.snapshotId === harnessId &&
    decision.payload.worldDigest === worldDigest && decision.payload.budget === budget,
    'Unknown or mismatched committed routing decision');
  const event = store.readEvent(report.episodeId);
  ensure(event?.type === 'episode_started' && event.payload.decisionId === decisionId &&
    event.payload.harnessId === harnessId && event.payload.worldDigest === worldDigest && event.payload.budget === budget,
    'Episode does not belong to the committed execution');
  ensure(digest(report.publicTask) === digest(decision.payload.publicTask), 'Routing public context mismatch');
  return verifyTerminalReceipt(report, {episodeId: report.episodeId, decisionId, harnessId, worldDigest, budget});
}

function memoryEntry(report, provenance) {
  return {publicTask: clone(report.publicTask), snapshotId: report.harnessId, success: report.success,
    score: report.score, usage: report.usage, cost: report.cost, split: 'train', verified: true,
    decisionId: null, episodeId: report.episodeId, terminalReceiptHash: report.terminalReceipt.hash, provenance};
}


export function loadTrainingMemory(directory) {
  const ledgerFile = path.resolve(directory, 'events.jsonl');
  verifyLedger(ledgerFile);
  const events = fs.readFileSync(ledgerFile, 'utf8').trim().split('\n').map(JSON.parse);
  const starts = new Map(events.filter(e => e.type === 'episode_started').map(e => [e.hash, e]));
  return events.filter(e => e.type === 'episode_finished' && e.payload.phase === 'initial_training_exploration' && e.payload.split === 'train' && !e.payload.technicalFailure).map(event => {
    const report = event.payload, start = starts.get(report.episodeId);
    ensure(start && start.payload.split === 'train' && start.payload.harnessId === snapshot([]).id, 'Training memory requires H0 executions');
    verifyTerminalReceipt(report, {episodeId: report.episodeId, decisionId: null,
      harnessId: start.payload.harnessId, worldDigest: start.payload.worldDigest, budget: start.payload.budget});
    const frozen = events.find(row => row.hash === report.instancePlan && row.type === 'initial_instances_frozen');
    ensure(frozen && frozen.sequence < start.sequence, 'Initial instances were not frozen before execution');
    const plan = JSON.parse(fs.readFileSync(path.join(path.dirname(ledgerFile), 'objects', frozen.payload.artifact + '.json'), 'utf8'));
    ensure(digest(plan) === frozen.payload.artifact && digest(plan) === frozen.payload.planDigest && plan.taskId === report.taskId, 'Invalid frozen instance artifact');
    ensure(plan.instances.some((instance, index) => digest(instance) === digest(report.instance) && plan.initialStateHashes[index] === report.initialStateHash), 'Training episode differs from the fixed instance manifest');
    return memoryEntry(report, {ledgerFile, episodeEventHash: event.hash});
  });
}

export function validateTrainingMemory(memory) {
  const sources = new Map(), seen = new Set();
  return memory.map(row => {
    const file = row.provenance?.ledgerFile;
    ensure(typeof file === 'string' && path.basename(file) === 'events.jsonl', 'Training memory needs a verified source ledger');
    if (!sources.has(file)) sources.set(file, loadTrainingMemory(path.dirname(file)));
    const verified = sources.get(file).find(entry => entry.provenance.episodeEventHash === row.provenance.episodeEventHash);
    ensure(verified && digest(verified) === digest(row), 'Training memory differs from its verified execution');
    ensure(!seen.has(verified.episodeId), 'Training episode imported more than once');
    seen.add(verified.episodeId);
    return clone(verified);
  });
}
