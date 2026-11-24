                                                                                              
                                                                                                         
                                                                                             
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const fault = (code, message, extra = {}) => Object.assign(new Error(message), { code, ...extra });
const DISABLED = ['shell_tool','unified_exec','apps','plugins','hooks','browser_use','browser_use_external','computer_use','multi_agent','code_mode_host','image_generation','view_image','sleep_tool','goals','workspace_dependencies','skill_search'];
export function codexArguments({ model, effort = 'low', workspace, stateDir }) {
  return ['--no-daemon','exec','--model',model,'-c',`model_reasoning_effort=${effort}`,'-c','model_reasoning_summary=none','-c','web_search="disabled"','-c','history.persistence="none"',
    '-c',`sqlite_home=${JSON.stringify(join(stateDir,'cli-state'))}`,'-c',`log_dir=${JSON.stringify(join(stateDir,'cli-logs'))}`,'-c','features.skip_host_skill_discovery=true',
    ...DISABLED.flatMap(f => ['-c',`features.${f}=false`]),'--ephemeral','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--sandbox','read-only','--cd',workspace,'--json','-'];
}
export async function runCodex(prompt, { model, effort = 'low', timeoutMs = 120000, signal, cliPath = process.env.CODEX_CLI ?? 'codex' } = {}) {
  if (signal?.aborted) throw fault('codex_aborted', 'Codex request was already aborted');
  const stateDir = mkdtempSync(join(tmpdir(), 'train-codex-')), workspace = join(stateDir, 'empty-workspace'); mkdirSync(workspace, { recursive: true });
  const args=codexArguments({ model, effort, workspace, stateDir });
  const child = spawn(cliPath.endsWith('.py')?(process.env.PYTHON??(process.platform==='win32'?'python':'python3')):cliPath, cliPath.endsWith('.py')?[cliPath,...args]:args, { cwd: workspace, env: process.env, stdio: ['pipe','pipe','pipe'] });
  let buffer = '', answers = [], completed = null, toolEvent = false, parseFailed = false, killReason = null; const reported = new Set();
  const terminate = code => { killReason ??= code; if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL'); };
  const onAbort = () => terminate('codex_aborted'); signal?.addEventListener('abort', onAbort, { once: true });
  const timer = setTimeout(() => terminate('codex_timeout'), timeoutMs); timer.unref?.();
  const event = line => { if (!line.trim()) return; let e; try { e = JSON.parse(line); if (!e || typeof e !== 'object' || Array.isArray(e)) throw Error('Expected an event object'); } catch { parseFailed = true; return; }
    for (const v of [e.model, e.model_id, e.session?.model, e.thread?.model]) if (typeof v === 'string') reported.add(v);
    if (e.type === 'turn.completed') completed = e;
    if (e.type === 'item.started' || e.type === 'item.completed') { const kind = e.item?.type;
      if (!['agent_message','reasoning','error'].includes(kind)) { toolEvent = true; terminate('codex_tool_event'); }
      if (e.type === 'item.completed' && kind === 'agent_message') answers.push(e.item.text); } };
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', chunk => { buffer += chunk; let at; while ((at = buffer.indexOf('\n')) >= 0) { event(buffer.slice(0, at)); buffer = buffer.slice(at + 1); } });
  child.stderr.on('data', () => {});
  const result = await new Promise((resolve, reject) => { child.once('error', reject); child.stdin.once('error', error => { terminate('codex_input_error'); reject(error); }); child.once('close', code => resolve({ code })); child.stdin.end(prompt); })
    .finally(() => { clearTimeout(timer); signal?.removeEventListener('abort', onAbort); rmSync(stateDir, { recursive: true, force: true }); });
  if (buffer) event(buffer);
  if (killReason || toolEvent) throw fault(killReason ?? 'codex_tool_event', 'Codex model call failed its tool-free boundary');
  if (result.code !== 0 || !completed || parseFailed || answers.length !== 1 || typeof answers[0] !== 'string' || !answers[0].trim()) throw fault('codex_incomplete', 'Codex did not return exactly one answer');
  if ([...reported].some(m => m !== model)) throw fault('codex_model_mismatch', `Codex reported a model other than ${model}`);
  const u = completed.usage ?? {};
  return { text: answers[0], model, usage: { inputTokens: u.input_tokens ?? null, cachedInputTokens: u.cached_input_tokens ?? null, outputTokens: u.output_tokens ?? null } };
}
