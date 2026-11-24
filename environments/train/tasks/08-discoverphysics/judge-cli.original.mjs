                                                                                                                     
                                                                                                         
                                                                                                             
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { contentHash } from '../../lib/hash.mjs';

export const JUDGE_MODEL = 'claude-opus-4-6';
const cliEnv = () => Object.fromEntries(['HOME', 'USER', 'LOGNAME', 'PATH', 'SHELL', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM']
  .filter(key => process.env[key] != null).map(key => [key, process.env[key]]));

function runCli(system, prompt, signal) {
  const cwd = mkdtempSync(join(tmpdir(), 'train-dp-judge-'));
  return new Promise((resolve, reject) => {
    const args = ['-p', '--system-prompt', system, '--model', JUDGE_MODEL, '--tools', '',
      '--strict-mcp-config', '--restricted', '--no-session-persistence',
      '--max-turns', '1', '--output-format', 'json', prompt];
    const child = spawn(process.env.CLAUDE_CLI ?? 'claude', args, { cwd, env: { ...cliEnv(),
      CLAUDE_CODE_MAX_OUTPUT_TOKENS: '1024', MAX_STRUCTURED_OUTPUT_RETRIES: '0', MCP_CONNECTION_NONBLOCKING: 'true' },
      stdio: ['ignore', 'pipe', 'pipe'], signal, killSignal: 'SIGKILL' });
    child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
    let stdout = '', stderr = '';
    const timer = setTimeout(() => { if (child.pid) child.kill('SIGKILL'); }, 180000);
    const cap = (field, chunk) => {
      if (field === 'out') stdout += chunk.toString('utf8'); else stderr += chunk.toString('utf8');
      if (stdout.length > 2_000_000 || stderr.length > 100_000) child.kill('SIGKILL');
    };
    child.stdout.on('data', chunk => cap('out', chunk));
    child.stderr.on('data', chunk => cap('err', chunk));
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('close', code => {
      clearTimeout(timer);
      rmSync(cwd, { recursive: true, force: true });
      let result;
      try { result = JSON.parse(stdout); }
      catch { return reject(Object.assign(new Error('Claude CLI judge did not return complete JSON'), { code: 'judge_cli_incomplete' })); }
      if (code !== 0 || result?.is_error || result?.subtype !== 'success' || result?.terminal_reason !== 'completed'
        || result?.num_turns !== 1 || typeof result?.result !== 'string')
        return reject(Object.assign(new Error('Claude CLI judge did not complete one model turn'), { code: 'judge_cli_failed' }));
      const names = Object.keys(result.modelUsage ?? {});
      if (names.length !== 1 || names[0] !== JUDGE_MODEL)
        return reject(Object.assign(new Error('Claude CLI judge used a different model'), { code: 'judge_wrong_model' }));
      resolve(result);
    });
  });
}

                                                                                                                      
                                                                                                                                               
export async function claudeCliJudgeCall({ requestId, model, system, turns, maxTokens, signal }) {
  if (model !== JUDGE_MODEL || maxTokens !== 1024 || typeof system !== 'string' || turns?.length !== 1 || turns[0].role !== 'user') {
    throw Object.assign(new Error('The official ExplanationJudge request differs from the pinned judge route'), { code: 'source_model_response_invalid' });
  }
  const answer = await runCli(system, turns[0].text, signal);
  const u = answer.usage ?? {};
  const usage = { prompt_tokens: u.input_tokens ?? null, completion_tokens: u.output_tokens ?? null,
    total_tokens: Number.isFinite(u.input_tokens) && Number.isFinite(u.output_tokens) ? u.input_tokens + u.output_tokens : null };
  const text = answer.result;
  return { requestId, model, text, usage, finishReason: 'stop', responseFingerprint: contentHash({ requestId, model, text, usage, finishReason: 'stop' }) };
}
