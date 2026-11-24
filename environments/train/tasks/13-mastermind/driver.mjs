                                                                                                                   
                                                                                          
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeExtraOfficialDriver } from '../../vendor/extra-official/runtime.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const configurations = JSON.parse(readFileSync(resolve(here, 'configurations.json'), 'utf8')).configurations;

export async function createDriver({ root }) {
  return makeExtraOfficialDriver({ root, spec: {
    taskId: 'mastermind',
    id: 'official-mastermind-public-driver',
    version: 1,
    maxSteps: 12,
    configurations,
    configurationSelection: { mode: 'adaptive', availableCount: null,
      providerId: 'official-mastermind-native-instance-provider', providerVersion: 1, sourceActionBudget: 12 },
    invalidOutcomePolicy: 'repeat_same_configuration',
    maxInvalidAttempts: 3,
    actionContract: 'Submit only FINAL GUESS: [\'color1\', \'color2\', \'color3\', \'color4\'] using the listed colors. The unchanged official parser and evaluator grade one guess per action. First-attempt wins are native invalid trials, retained and repeated with fresh Player memory on the same configuration.',
    source: {
      kind: 'official', engine: 'MastermindEval', commit: '03de37eaed76061e9028b5856a291972a2905253',
      urls: ['https://github.com/flairNLP/mastermind'], reconstructed: false, protocolCompatible: true,
      recording: 'unchanged native evaluator result and permitted public observations and actions',
      fidelityNotes: 'The official Mastermind class, parser, full-game evaluator and progress computation execute unchanged. Unused inference SDK imports are omitted when loading the exact source AST. The official evaluator clones its seeded template before each trial; recorded generation follows that actual agentic route. Nine seeded native palettes and secret codes are distinct instances. Source instruction says duplicates are allowed, while the current native generator samples its secret without replacement; both native behaviours are retained.',
      limitations: ['The native current secret generator samples without replacement although its instruction permits duplicate guesses.'],
    },
  } });
}
