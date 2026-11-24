import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const lines = file => fs.readFileSync(file, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse);
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');

                                                                                      
const legacyTransportFailure = message => /^(fetch failed|terminated|(?:Provider )?HTTP \d{3}\b|Anthropic (?:request received no response headers|stream stalled|stream ended before)|The operation was aborted|This operation was aborted|Request aborted)/.test(message ?? '');

export function readResponseLog(source, requests) {
  if (!source) return [];
  assert(!fs.existsSync(path.join(source, 'resume-validation-error.json')), 'Resume source previously failed replay validation');
  const file = path.join(source, 'api-responses.jsonl');
  const responses = fs.existsSync(file) ? lines(file) : [];
  const ids = new Set(requests.map(row => row.captureId));
  assert.equal(ids.size, requests.length, 'Duplicate archived request identity');
  const seen = new Set();
  for (const row of responses) {
    assert(ids.has(row.captureId) && !seen.has(row.captureId), 'Invalid archived response identity');
    seen.add(row.captureId);
  }
  const missing = requests.filter(row => !seen.has(row.captureId));
  if (!missing.length) return responses;
  const resultFile = path.join(source, '..', 'results.json');
  const result = fs.existsSync(resultFile) ? JSON.parse(fs.readFileSync(resultFile, 'utf8')).results?.find(row => row.episode === path.basename(source)) : null;
  const failuresFile = path.join(source, 'exact-transport-retries.jsonl');
  const failures = fs.existsSync(failuresFile) ? lines(failuresFile) : [];
                                                                                      
  const unused = [...failures];
  const proven = missing.every(request => {
    const index = unused.findIndex(row => (row.captureId == null || row.captureId === request.captureId) && row.requestHash === digest(request.request) && row.unchangedInput === true && (row.phase === 'transport' || row.phase == null && legacyTransportFailure(row.error)) && typeof row.error === 'string' && row.error.length > 0);
    if (index < 0) return false;
    unused.splice(index, 1); return true;
  });
                                                                          
                                                                             
                                                                               
  const playerTimeout = result?.outcome === 'timeout' &&
    Number.isSafeInteger(result.steps) && result.steps >= 0 &&
    new RegExp('^no progress for \\d+ min while awaiting the Player request at step ' + result.steps + '$').test(result.reason ?? '');
  if (proven && (result?.outcome === 'error' || playerTimeout)) return responses;
                                                                               
                                                                                 
  const protocolFile = path.join(source, 'protocol-errors.jsonl');
  const recordFile = path.join(source, 'episodes', path.basename(source), 'record.jsonl');
  if (!fs.existsSync(failuresFile) && !fs.existsSync(file) && requests.length === 1 && result?.outcome === 'error' && result.steps === 0 && fs.existsSync(protocolFile) && fs.existsSync(recordFile)) {
    const record = lines(recordFile);
    const protocol = lines(protocolFile);
    if (record.length === 1 && record[0].action == null && protocol.length === 1 && typeof protocol[0].error === 'string' && protocol[0].error.length > 0 && result.reason === protocol[0].error && legacyTransportFailure(protocol[0].error) && !protocol[0].usageKnown && protocol[0].stopReason == null) return [];
  }
  throw Error('Missing API response log without verified failure evidence: ' + file);
}

export function recordReplayFailure(runDir, error) {
  if (error.message === 'OFFLINE_RESUME_VERIFIED_NO_NETWORK') return;
  fs.writeFileSync(path.join(runDir, 'resume-validation-error.json'), JSON.stringify({phase: 'replay-validation', error: error.message}, null, 2));
}

export function verifyReplayState(source, runDir) {
  const name = path.basename(source);
  const relative = path.join('episodes', name, 'record.jsonl');
  const original = lines(path.join(source, relative));
  const restored = lines(path.join(runDir, relative));
  assert.equal(restored.length, original.length, 'Incomplete native replay');
  verifyReplayObservations(original, restored);
  return restored.length - 1;
}

export function verifyReplayObservations(original, restored, {compareFrames = true} = {}) {
  const frame = value => {
    if (value == null) return null;
    const {path: location, ...identity} = value;
    return identity;
  };
  const snapshot = row => {
    const observation = row.observation ?? {};
    return {action: row.action ?? null, publicText: observation.publicText,
      terminal: observation.terminal, reward: observation.reward,
      stateHash: observation.stateHash, step: observation.step,
      ...(compareFrames ? {frame: frame(observation.frame ?? observation.previewFrame),
        frames: observation.frames?.map(frame) ?? null} : {})};
  };
  assert.deepEqual(restored.map(snapshot), original.map(snapshot), 'Restored environment history differs');
}
