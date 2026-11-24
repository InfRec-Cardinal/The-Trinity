                                                                                                                     
                                                                                                                   
                                                                                                                             
                                                  
                                                                                                                       
                                                                                                                          
                                                                                                                            
                                                                                                                               
                                                                                                                      
                                                                                 
                                                                           
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const CLI_CWD = mkdtempSync(join(tmpdir(), 'h0-player-'));

export const CLAUDE_CLI_PROFILE = 'claude_subscription_cli';
export const CLAUDE_CLI_SENTINEL = 'local-claude-code-login';
export const CLAUDE_CLI_MODEL = 'claude-opus-5';
export const CLAUDE_CLI_PATH = process.env.H0_CLAUDE_CLI || 'claude';
const MAX_CAPTURE_BYTES = 4 * 1024 * 1024;
const inheritedEnvironment = ['HOME','USER','LOGNAME','PATH','SHELL','TMPDIR','LANG','LC_ALL','TERM',
  'ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','CLAUDE_CONFIG_DIR','DISABLE_PROMPT_CACHING','CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS','CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC'];

function cliEnvironment(maxTokens) {
                                                                             
                                                                              
                                                  
  const env = Object.fromEntries(inheritedEnvironment.filter(name => process.env[name] != null)
    .map(name => [name,process.env[name]]));
  env.CLAUDE_CODE_MAX_OUTPUT_TOKENS = String(Math.max(1024, Math.min(64000, maxTokens)));
  env.MAX_STRUCTURED_OUTPUT_RETRIES = '0';
  env.MCP_CONNECTION_NONBLOCKING = 'true';
  return env;
}

function turnText(turn) {
  const blocks = turn.text ?? turn.content ?? [];
  const list = typeof blocks === 'string' ? [{ type: 'text', text: blocks }] : blocks;
  if (!Array.isArray(list)) throw new Error('Unsupported H0 turn shape for Claude CLI');
  return list.map(block => {
    if (block.type === 'text') return block.text;
    if (block.type === 'tool_use') return `Previous action ${block.name}: ${JSON.stringify(block.input)}`;
    if (block.type === 'tool_result') return `Previous environment result: ${typeof block.content === 'string' ? block.content : JSON.stringify(block.content)}`;
    if (block.type === 'image') throw Object.assign(new Error('Claude CLI image input has not been validated for H0; keep this task on API'), { code: 'cli_image_not_supported' });
    throw Object.assign(new Error(`Unsupported H0 content block: ${String(block.type)}`), { code: 'cli_content_not_supported' });
  }).join('\n');
}

function promptFromTurns(turns) {
  return turns.map((turn, index) => {
    if (turn.role === 'tool') {
      const results = turn.results ?? [];
      return `[${index + 1} environment result]\n${results.map(item => typeof item.output === 'string' ? item.output : JSON.stringify(item.output)).join('\n')}`;
    }
    return `[${index + 1} ${turn.role === 'assistant' ? 'previous H0 action' : 'public observation'}]\n${turnText(turn)}`;
  }).join('\n\n');
}

                                                                            
                                                                             
                                                                            
                                                                           
export function buildClaudeCliPrompt(turns) {
  const full = promptFromTurns(turns);
  if (full.length <= 200_000 || turns.at(-1)?.role !== 'user') return {prompt:full,compacted:false};
  const latestText=turnText(turns.at(-1));
  let latest;
  try { latest=JSON.parse(latestText); } catch { return {prompt:full,compacted:false}; }
  if (!Array.isArray(latest?.accessTable) || !latest?.bittings || typeof latest.bittings!=='object'
    || latest?.model?.maximumShearPointsPerChamber == null) return {prompt:full,compacted:false};
  const history=[];
  for (let index=0;index<turns.length-1;index++) {
    const turn=turns[index];
    if (turn.role !== 'assistant') continue;
    const action=turn.content?.find?.(block=>block.type==='tool_use')?.input;
    if (!action) continue;
    const output=turns[index+1]?.role==='tool' ? turns[index+1].results?.[0]?.output : null;
    if (typeof output !== 'string') return {prompt:full,compacted:false};
    let publicResult, observation;
    try { publicResult=JSON.parse(output); observation=JSON.parse(publicResult.publicText); }
    catch { return {prompt:full,compacted:false}; }
    const check=observation.check;
    history.push(JSON.stringify({action,feedback:observation.feedback??null,
      checksUsed:observation.checksUsed??null,checkIsCurrent:observation.checkIsCurrent??null,
      ...(check?{check:{valid:check.valid,exactAccessTable:check.exactAccessTable,
        requiredFailures:check.requiredFailures,forbiddenOpenings:check.forbiddenOpenings,
        missingBittings:check.missingBittings,adjacentCutViolations:check.adjacentCutViolations,
        duplicateBittings:check.duplicateBittings,shearLimitViolations:check.shearLimitViolations,
        unintendedBittings:check.unintendedBittings,
        unintendedManufacturableBittings:check.unintendedManufacturableBittings}}:{})}));
  }
  return {prompt:`[Earlier public actions and check feedback; unchanged current public state follows]\n${history.join('\n')}\n\n[Current complete public observation]\n${latestText}`,
    compacted:true,originalChars:full.length};
}

function multimodalPromptFromTurns(turns) {
  const content = [];
  let images = 0;
  for (const [index, turn] of turns.entries()) {
    if (turn.role === 'tool') {
      const results = turn.results ?? [];
      content.push({ type:'text', text:`[${index + 1} environment result]\n${results.map(item => typeof item.output === 'string' ? item.output : JSON.stringify(item.output)).join('\n')}` });
      continue;
    }
    content.push({ type:'text', text:`[${index + 1} ${turn.role === 'assistant' ? 'previous H0 action' : 'public observation'}]` });
    const blocks = turn.text ?? turn.content ?? [];
    for (const block of typeof blocks === 'string' ? [{type:'text',text:blocks}] : blocks) {
      if (block.type === 'image') {
        const source = block.source;
        if (source?.type !== 'base64' || source.media_type !== 'image/png' || typeof source.data !== 'string'
          || !/^[A-Za-z0-9+/]+={0,2}$/.test(source.data))
          throw Object.assign(new Error('Unsupported Claude CLI image block'), {code:'cli_image_not_supported'});
        content.push({type:'image',source:{type:'base64',media_type:'image/png',data:source.data}});
        images++;
      } else content.push({type:'text',text:turnText({text:[block]})});
    }
  }
  return {content,images};
}

function runCli(args, input, { signal, maxTokens, cliPath = CLAUDE_CLI_PATH, streamJson = false, timeoutMs = 1800000 } = {}) {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) return Promise.reject(Error('Invalid CLI timeout'));
  if (signal?.aborted) return Promise.reject(signal.reason ?? Error('Aborted'));
  return new Promise((resolve, reject) => {
    const child = spawn(cliPath, args, {
      cwd: CLI_CWD, env: cliEnvironment(maxTokens),
      stdio: ['pipe', 'pipe', 'pipe'], signal, killSignal: 'SIGKILL',
    });
    child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
    let stdout = '', stderr = '', tooLarge = false, settled = false;
    const stop = error => {
      if (settled) return;
      settled = true; clearTimeout(timer); child.stdin.destroy();
      if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
      reject(error);
    };
    const timer = setTimeout(() => stop(Object.assign(Error('Claude CLI timed out'), {code:'cli_timeout'})), timeoutMs);
    const capture = (chunk, field) => {
      if (settled) return;
      const next = field === 'stdout' ? Buffer.byteLength(stdout) + Buffer.byteLength(chunk) : Buffer.byteLength(stderr) + Buffer.byteLength(chunk);
      if (next > MAX_CAPTURE_BYTES) { tooLarge = true; stop(Object.assign(Error('Claude CLI output exceeded the transport limit'), {code:'cli_output_too_large'})); return; }
      if (field === 'stdout') stdout += chunk.toString('utf8'); else stderr += chunk.toString('utf8');
    };
    child.stdout.on('data', chunk => capture(chunk, 'stdout'));
    child.stderr.on('data', chunk => capture(chunk, 'stderr'));
    child.stdin.on('error', stop);
    child.stdout.on('error', stop); child.stderr.on('error', stop);
    child.once('error', stop);
    child.once('close', code => {
      if (settled) return;
      settled = true; clearTimeout(timer);
      if (tooLarge) return reject(Object.assign(new Error('Claude CLI output exceeded the transport limit'), { code: 'cli_output_too_large' }));
      if (code !== 0) {
                                                                         
                                                                              
                                                                        
        let result;
        try {
          result = streamJson ? stdout.trim().split('\n').map(line => JSON.parse(line)).filter(event => event.type === 'result').at(-1)
            : JSON.parse(stdout);
        } catch {}
        const status = [result?.subtype, result?.terminal_reason, result?.is_error === true ? 'is_error' : null]
          .filter(Boolean).join('/');
        const failureText=typeof result?.result==='string'?result.result:'';
        const failureKind=/context|prompt.{0,20}long|token.{0,20}limit/i.test(failureText)?'context_limit'
          :/rate limit|usage limit|session limit|quota/i.test(failureText)?'usage_limit'
          :/overload/i.test(failureText)?'provider_overload'
          :null;
        return reject(Object.assign(new Error(`Claude CLI exited ${code}${status ? ` (${status})` : ''}${failureKind ? ` [${failureKind}]` : ''}${stderr ? `: ${stderr.slice(0, 200)}` : ''}`),
          {code:'cli_process_failed', cliExitCode:code, cliResultSubtype:result?.subtype ?? null,
            cliTerminalReason:result?.terminal_reason ?? null, cliFailureKind:failureKind}));
      }
      try {
        if (streamJson) {
          const events = stdout.trim().split('\n').map(line => JSON.parse(line));
          const result = events.filter(event => event.type === 'result').at(-1);
          if (!result) throw new Error('Claude CLI stream omitted a result event');
          resolve(result);
        } else resolve(JSON.parse(stdout));
      }
      catch { reject(Object.assign(new Error('Claude CLI returned invalid JSON'), { code: 'cli_invalid_json' })); }
    });
    try { child.stdin.end(input); } catch (error) { stop(error); }
  });
}

export async function callClaudeSubscriptionHeadless({ profile, apiKey, system, turns, tools = [], maxTokens = 16384, signal, searchEnabled = false, toolChoice = 'required' }, options = {}) {
  if (profile !== CLAUDE_CLI_PROFILE || apiKey !== CLAUDE_CLI_SENTINEL)
    throw new Error('Claude CLI transport requires its local-only profile and sentinel');
  if (searchEnabled || tools.length !== 1 || toolChoice !== 'required')
    throw new Error('Claude CLI H0 supports exactly one required structured action and no web search');
  const [tool] = tools;
  if (!tool?.parameters || typeof tool.name !== 'string') throw new Error('Missing H0 action schema');
  const args = ['-p', '--system-prompt', system, '--json-schema', JSON.stringify(tool.parameters),
    '--output-format', 'json', '--max-turns', '1', '--model', CLAUDE_CLI_MODEL,
    '--effort', 'low', '--tools', '', '--strict-mcp-config', '--restricted', '--no-session-persistence'];
  const hasImage = turns.some(turn => (turn.text ?? turn.content ?? []).some?.(block => block.type === 'image'));
  let prompt, streamJson = false, imageCount = 0;
  if (hasImage) {
    const multimodal = multimodalPromptFromTurns(turns);
    imageCount = multimodal.images;
    prompt = JSON.stringify({type:'user',message:{role:'user',content:multimodal.content}}) + '\n';
    args.splice(args.indexOf('--output-format'), 2, '--input-format','stream-json','--output-format','stream-json','--verbose');
    streamJson = true;
  } else prompt = buildClaudeCliPrompt(turns).prompt;
  const result = await runCli(args, prompt, { signal, maxTokens, streamJson, ...options });
  if (result.is_error || result.subtype !== 'success' || result.terminal_reason !== 'completed')
    throw Object.assign(new Error(`Claude CLI did not complete: ${String(result.subtype ?? result.terminal_reason ?? 'unknown')}`), { code: 'cli_model_failed' });
  const canonical = result.modelUsage && Object.keys(result.modelUsage);
  if (!canonical?.includes(CLAUDE_CLI_MODEL))
    throw Object.assign(new Error('Claude CLI used a different model; action was not accepted'), { code: 'cli_model_mismatch' });
  const action = result.structured_output;
  if (!action || typeof action !== 'object' || Array.isArray(action))
    throw Object.assign(new Error('Claude CLI omitted the structured H0 action'), { code: 'cli_action_missing' });
  const usage = result.usage ?? {};
  return {
    text: '', toolCalls: [{ id: `cli_${randomUUID().replaceAll('-', '')}`, name: tool.name, args: action }],
    stopReason: 'done',
    usage: { input: usage.input_tokens ?? 0, output: usage.output_tokens ?? 0,
      cachedInput: usage.cache_read_input_tokens ?? 0,
      cacheCreationInput: usage.cache_creation_input_tokens ?? 0 },
    cliTrace: { transport: 'claude-subscription-headless-transport-v4', model: CLAUDE_CLI_MODEL,
      effort: 'low', agenticTurnLimit:1, terminalReason: result.terminal_reason ?? null,
      inputFormat:streamJson?'stream-json-image':'text',publicImageCount:imageCount,
      providerIterations: Array.isArray(usage.iterations) ? usage.iterations.length : null,
      cliTurnCounter: result.num_turns ?? null },
  };
}
