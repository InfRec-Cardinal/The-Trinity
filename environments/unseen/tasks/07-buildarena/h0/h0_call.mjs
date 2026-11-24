                                                                                                                     
                                                                                   
                                                                                                      
                                                                                                                        
                                                                                          
                                                                                                                              
                                                                                                                           
                                                                                                                         
                               
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { loadFrozenHarness, renderFrozenH0 } from '../../../interface/prompt.mjs';
import { callClaudeSubscriptionHeadless, CLAUDE_CLI_PROFILE, CLAUDE_CLI_SENTINEL } from '../../../player/claude-cli-transport-v4.mjs';

const harness = loadFrozenHarness();

const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const tools = input.tools ?? [];
const toolText = tools.length
  ? 'Official tools available in this role (name, description, JSON parameters):\n\n' + tools.map(t =>
      `### ${t.name}\n${(t.description ?? '').trim()}\nParameters: ${JSON.stringify(t.parameters ?? {})}`).join('\n\n')
  : 'This role has no tools: always reply with kind "message".';
const assignment = {
  task: 'Official BuildArena (ICML 2026) machine-construction workflow in the Besiege physics sandbox. You play one role of the official multi-agent workflow; the other roles are separate participants. The official system prompt of your role follows verbatim; follow it exactly.\n\n' + input.roleSystem,
  observation: 'Text only: the official conversation of your role, i.e. the task messages, the messages of the other roles (prefixed with their name), and the results of your tool calls.',
  actions: {
    kind: '"message" to send a text message (its content goes in text), or "tool_call" to call exactly one official tool (its name in tool, its arguments as a JSON object string in arguments_json).',
    text: 'The message text (empty string when kind is "tool_call").',
    tool: 'The official tool name (empty string when kind is "message").',
    arguments_json: 'The tool arguments as a JSON object string (empty string when kind is "message").',
    tools: toolText,
  },
  evaluation: 'The finished machine is simulated in Besiege and judged by the official BuildArena pass rule of the task.',
};
const contract = 'One action per turn: a message or one official tool call.';
const tool = { name: 'submit_action', description: 'Submit one message or one official tool call.',
  parameters: { type: 'object', additionalProperties: false, required: ['kind', 'text', 'tool', 'arguments_json'],
    properties: { kind: { type: 'string', enum: ['message', 'tool_call'] }, text: { type: 'string' }, tool: { type: 'string' }, arguments_json: { type: 'string' } } } };
const system = renderFrozenH0(harness, assignment, 'interactive', contract, null);

try {
  let out;
  if (process.env.H0_PLAYER_MODULE) {
    const { callPlayer } = await import(pathToFileURL(process.env.H0_PLAYER_MODULE).href);
    out = await callPlayer({ system, turns: input.turns, tool, maxTokens: 16384 });
  } else {
    const r = await callClaudeSubscriptionHeadless({ profile: CLAUDE_CLI_PROFILE, apiKey: CLAUDE_CLI_SENTINEL, system,
      turns: input.turns, tools: [tool], maxTokens: 16384, toolChoice: 'required' });
    out = { args: r.toolCalls[0].args, usage: r.usage };
  }
  process.stdout.write(JSON.stringify(out));
} catch (err) {
  process.stdout.write(JSON.stringify({ error: String(err.message ?? err).slice(0, 600), code: err.code ?? null }));
  process.exitCode = 2;
}
