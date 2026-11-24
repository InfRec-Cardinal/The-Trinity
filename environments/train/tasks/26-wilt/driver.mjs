                                                                                                             
                                                                                                             
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeExtraOfficialDriver } from '../../vendor/extra-official/runtime.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const configurations = JSON.parse(readFileSync(resolve(here, 'configurations.json'), 'utf8')).configurations;

export async function createDriver({ root }) {
  return makeExtraOfficialDriver({ root, spec: {
    taskId: 'wilt',
    id: 'official-wilt-public-driver',
    version: 1,
    maxSteps: 31,
    configurations,
    configurationSelection: { mode: 'adaptive', availableCount: 50,
      providerId: 'official-wilt-native-instance-provider', providerVersion: 1, sourceActionBudget: 31 },
    actionContract: 'Submit only Test Case: ```(x,y,z)``` for one probe, or Final Guess: ```lambda x,y,z: ...``` for the one final answer. Use at most three digits per number, excluding signs and decimal characters. There are at most 30 probes and 31 total actions. No selected rule index, rule catalogue, private hypothesis statistics or gold is exposed before the native terminal response. Final code is evaluated in an OS sandbox that receives only generated input cases, without the hidden rule or source catalogue.',
    source: {
      kind: 'official', engine: 'WILT LLMReasoningHarness', commit: '6344f04b3eb9119664c87c4d1b6cd2a227f70e8d',
      urls: ['https://github.com/RiotGames/WILT'], reconstructed: false, protocolCompatible: true,
      recording: 'unchanged native evaluator result and permitted public observations and actions',
      fidelityNotes: 'The official full-split rules, instruction, interaction loop, probe channel, parser, point/bonus logic and integer-grid/random-float/special-case checker execute unchanged. A transport proxy evaluates candidate code outside the gold-bearing host; the native checker compares its actual outputs. Case RNG is fixed and logged. Twenty-four distinct official full-split rule instances (8-31) are selected. The source probe channel reports its original pre-increment remaining-attempt count.',
      limitations: ['Candidate execution has a 10-second host wall limit and a 5-second CPU limit; resource exhaustion is an invalid final artifact with zero native points.', 'The provider selects genuine instances from all 50 official full-split rules; a selected configuration is not a claim to evaluate the whole split.'],
    },
  } });
}
