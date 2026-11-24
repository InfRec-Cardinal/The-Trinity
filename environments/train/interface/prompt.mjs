                                                                                                                     
                                                                  
import { readFileSync } from 'node:fs';

export const H0_PUBLIC_HISTORY_TURNS = 64;
                                                                                                                        
export const SOKOBAN_ACTION_CONTRACT = '0 no-op; 1 push up; 2 push down; 3 push left; 4 push right; 5 move up; 6 move down; 7 move left; 8 move right. Push actions move without pushing when possible. Move actions never push. No pull or undo.';

                                                                                              
export const loadFrozenHarness = (path = new URL('../player/player-harness.json', import.meta.url)) => JSON.parse(readFileSync(path, 'utf8'));

                                                                                                                     
export function renderFrozenH0(harness, assignment, kind = 'interactive', contract = null) {
  return `You are the Player. Use only the public observations and the provided action contract.\n`
    + `The following initial harness is frozen. Apply its skills without editing skills, prompts or memory and without carrying any information between episodes.\n`
    + JSON.stringify(harness) + '\nPlayer task protocol: ' + JSON.stringify({ task: assignment?.task ?? '',
      observation: assignment?.observation, actions: assignment?.actions, evaluation: assignment?.evaluation })
    + '\nPublic action contract: ' + (contract ?? (kind === 'interactive' ? SOKOBAN_ACTION_CONTRACT : 'Submit only the answer to the current official question.'))
    + '\nThe executor supplies the current observation and the last 64 public action/tool turns. Full trajectories are retained outside the Player context.'
    + '\nCall submit_action exactly once per response. Do not output explanations or private reasoning. '
    + 'Only host terminal evidence ends an interactive episode. A Player completion claim cannot end it.';
}

                                                                                                                 
                                                                                                                                                              
export const observationTurn = observation => ({ role: 'user', text: [{ type: 'text', text: observation.publicText ?? '' },
  ...(observation.frame ? [{ type: 'frame_reference', path: observation.frame.path, sha256: observation.frame.sha256 }] : [])] });

                                                                                                                                   
export const actionTurn = (toolId, action) => ({ role: 'assistant', content: [{ type: 'tool_use', id: toolId, name: 'submit_action', input: action }] });
export const toolResultTurn = (toolId, observation) => ({ role: 'tool', results: [{ id: toolId, output: JSON.stringify({ publicText: observation.publicText, terminal: observation.terminal }) }] });

                                                                                                                                          
export function requestTurns(storedTurns, currentObservation) {
  const history = storedTurns.slice(-H0_PUBLIC_HISTORY_TURNS);
  while (history.length && !(history[0].role === 'user' && Array.isArray(history[0].text))) history.shift();
  return [...history, observationTurn(currentObservation)];
}

                                                                                                                              
export const invalidResponseReprompt = policy => `The previous response omitted one complete legal submit_action. Submit exactly one action using the public contract. After ${policy.reprompts} unsuccessful reprompt(s), the task applies its declared ${policy.exhaustedOutcome} action. No environment action has executed for that rejected response.`;

                                                                                                                           
                                                                                                                                           
