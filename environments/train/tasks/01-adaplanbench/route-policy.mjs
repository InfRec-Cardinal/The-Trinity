                                                                                                                    
                                                                                                                
                                                                                                                          
                                                                                                                   
                              
                                                                                                                               
                                                                                                                                 
import { contentHash } from '../../lib/hash.mjs';

export const ADAPLANBENCH_TASK_ID = 'adaplanbench';
const SONNET = 'claude-sonnet-5', HAIKU = 'claude-haiku-4-5-20251001';
                                                                                                                                 
                                                                                          
export const ADAPLANBENCH_ROUTES = Object.freeze({
  tools: Object.freeze({ stage: 'tools', role: 'judge', models: Object.freeze([SONNET]), temperature: 0, maxTokens: 4096, responseProjection: 'plain', requestIdPrefix: 'apbtools_',
    official: 'tools_judge_LLM_list: gpt-5.4 (judge_reasoning_effort low), judge_temperature 0.0, judge_max_tokens 4096',
    promptPrefix: 'You are a strict judge.\n## Task:\nCheck whether the proposed plan to the question violates ANY environment constraints.' }),
  prefs: Object.freeze({ stage: 'prefs', role: 'judge', models: Object.freeze([SONNET]), temperature: 0, maxTokens: 4096, responseProjection: 'plain', requestIdPrefix: 'apbprefs_',
    official: 'prefs_judge_LLM_list: gpt-5.4, judge_temperature 0.0, judge_max_tokens 4096',
    promptPrefix: 'You are a strict judge.\n\n## Task:\nCheck whether the proposed plan to the question violates ANY user preferences.' }),
  rubrics: Object.freeze({ stage: 'rubrics', role: 'judge', models: Object.freeze([SONNET, HAIKU]), temperature: 0, maxTokens: 4096, responseProjection: 'plain', requestIdPrefix: 'apbrubric_',
    official: 'rubrics_judge_LLM_list: gpt-4.1, DeepSeek-v4-Flash, Qwen3.6-Flash (rubrics_score_merge_mode mean, rubrics_pass_mode min, threshold 4), judge_temperature 0.0, judge_max_tokens 4096',
    promptPrefix: 'You are a strict evaluator.\n## Task:\nEvaluate how well the proposed plan addresses the user query on each rubric below' }),
  user_feedback: Object.freeze({ stage: 'user_feedback', role: 'npc', models: Object.freeze([HAIKU]), temperature: 0, maxTokens: 1024, responseProjection: 'plain', requestIdPrefix: 'apbuser_',
    official: 'gen_LLM: gpt-4.1, gen_temperature 0.0, gen_max_tokens 1024',
    promptPrefix: "You are writing the user's next message to the assistant to provide feedback on the assistant's plan." }),
});
export const ADAPLANBENCH_ROUTE_POLICY_FINGERPRINT = contentHash(ADAPLANBENCH_ROUTES);
const fault = message => Object.assign(new Error(message), { code: 'source_model_route_invalid', status: 409 });

                                                                                                                                
export const adaplanbenchRequestId = ({ stage, model, temperature, maxTokens, turns, turn, resumePass }) =>
  `${ADAPLANBENCH_ROUTES[stage].requestIdPrefix}${contentHash({ taskId: ADAPLANBENCH_TASK_ID, stage, model, temperature, maxTokens, system: '', turns, turn, resumePass })}`;

                                                                                                
export function adaplanbenchBridgeRequest(raw) {
  const route = ADAPLANBENCH_ROUTES[raw?.stage];
  if (!route || raw.role !== route.role || !route.models.includes(raw.model) || raw.temperature !== route.temperature || raw.maxTokens !== route.maxTokens
    || !Array.isArray(raw.turns) || raw.turns.length !== 1 || raw.turns[0]?.role !== 'user' || typeof raw.turns[0].text !== 'string'
    || !raw.turns[0].text.startsWith(route.promptPrefix) || !Number.isSafeInteger(raw.turn) || raw.turn < 1 || !Number.isSafeInteger(raw.resumePass) || raw.resumePass < 0) {
    throw Object.assign(new Error('The official AdaPlanBench environment-model request differs from the proposed route policy'), { code: 'environment_error' });
  }
  const turns = [{ role: 'user', text: raw.turns[0].text }];
  const identity = { stage: raw.stage, turn: raw.turn, resumePass: raw.resumePass };
  return { taskId: ADAPLANBENCH_TASK_ID, requestId: adaplanbenchRequestId({ ...identity, model: raw.model, temperature: route.temperature, maxTokens: route.maxTokens, turns }),
    role: route.role, model: raw.model, temperature: route.temperature, system: '', turns, maxTokens: route.maxTokens,
    promptFingerprint: contentHash({ system: '', turns }), responseProjection: route.responseProjection, sourceCallIdentity: identity };
}

                                                                                                                           
                                                                                                                    
export function validateAdaplanbenchEnvironmentRequest(request) {
  const identity = request?.sourceCallIdentity, route = ADAPLANBENCH_ROUTES[identity?.stage];
  if (!request || request.taskId !== ADAPLANBENCH_TASK_ID || !route || request.role !== route.role || !route.models.includes(request.model)
    || request.temperature !== route.temperature || request.maxTokens !== route.maxTokens || request.responseProjection !== route.responseProjection
    || request.system !== '' || !Array.isArray(request.turns) || request.turns.length !== 1 || request.turns[0]?.role !== 'user'
    || typeof request.turns[0].text !== 'string' || !request.turns[0].text.startsWith(route.promptPrefix)
    || Reflect.ownKeys(request.turns[0]).some(key => !['role', 'text'].includes(key))
    || request.promptFingerprint !== contentHash({ system: '', turns: request.turns })
    || !Number.isSafeInteger(identity.turn) || identity.turn < 1 || !Number.isSafeInteger(identity.resumePass) || identity.resumePass < 0
    || request.requestId !== adaplanbenchRequestId({ ...identity, model: request.model, temperature: request.temperature, maxTokens: request.maxTokens, turns: request.turns })) {
    throw fault('AdaPlanBench environment-model task, stage route, exact model, budget, prompt or request identity changed');
  }
  return request;
}
