const boundedInteger = (value, label, minimum, maximum) => { if (!Number.isInteger(value) || value < minimum || value > maximum) throw Error('Invalid ' + label); };

import { realpath } from 'node:fs/promises';
import { resolve, relative, isAbsolute } from 'node:path';
import { spawn } from 'node:child_process';
export const PRIME_SANDBOX_VERSION = 'prime-workspace-bwrap-v1';
export const PRIME_TOOL_ENV = Object.freeze({ PATH: '/runtime:/usr/bin:/bin', HOME: '/tmp', NODE_PATH: '/usr/share/nodejs', LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8', npm_config_offline: 'true', npm_config_cache: '/tmp/npm-cache' });
const within = (root, path) => { const rel = relative(root, path); return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel)); };
export async function createWorkspaceSandbox({ cwd, writableRoot, readOnlyRoots = [] }) {
  const work = await realpath(resolve(cwd));
  if (work === '/') throw new Error('Refusing an unrestricted workspace');
  const writable = writableRoot ? await realpath(resolve(writableRoot)) : undefined;
  if (writable && writable !== work) throw new Error('Prime writableRoot must be the allocated cwd');
  const reads = [...new Set(await Promise.all(readOnlyRoots.map(path => realpath(resolve(path)))))];
  if (reads.some(path => path === '/' || (path !== work && within(path, work)))) throw new Error('Read-only roots must not expose ancestors of the assigned workspace');
  const args = ['--die-with-parent', '--new-session', '--unshare-all', '--clearenv'];
  for (const [key, value] of Object.entries(PRIME_TOOL_ENV)) args.push('--setenv', key, value);
  args.push('--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin', '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
    '--dir', '/runtime', '--ro-bind', process.execPath, '/runtime/node', '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp');
  for (const path of reads.filter(path => path !== work)) args.push('--ro-bind', path, path);
  args.push(writable ? '--bind' : '--ro-bind', work, work, '--chdir', work, '--');
  async function run(command, input = '', timeoutMs = 60_000) {
    boundedInteger(timeoutMs, 'sandbox timeoutMs', 1, 600_000);
    if (!Array.isArray(command) || !command.length) throw new Error('Sandbox command required');
    return await new Promise((done, fail) => {
      const child = spawn('/usr/bin/bwrap', [...args, ...command], { env: {}, stdio: ['pipe', 'pipe', 'pipe'] });
      let output = '', error = '', size = 0, settled = false;
      const stop = err => { if (settled) return; settled = true; clearTimeout(timer); child.kill('SIGKILL'); fail(err); };
      const timer = setTimeout(() => stop(new Error('Sandbox tool timed out')), timeoutMs);
      child.on('error', stop);
      child.stdin.on('error', err => { if (err.code !== 'EPIPE') stop(err); });
      const collect = (chunk, stderr) => { size += chunk.length; if (size > 4 * 1024 * 1024) return stop(new Error('Sandbox tool output limit exceeded')); if (stderr) error += chunk; else output += chunk; };
      child.stdout.on('data', chunk => collect(chunk, false)); child.stderr.on('data', chunk => collect(chunk, true));
      child.on('close', code => { if (settled) return; settled = true; clearTimeout(timer); code === 0 ? done({ stdout: output, stderr: error }) : fail(new Error(`Sandbox command failed (${code}): ${error || output}`)); });
      child.stdin.end(input);
    });
  }
  
  try { await run(['/runtime/node', '-e', 'process.stdout.write("sandbox-ready")']); }
  catch (error) { throw new Error(`Required Prime sandbox unavailable: ${error.message}`); }
  return { cwd: work, writableRoot: writable, readOnlyRoots: reads, run };
}


const FILE_PROGRAM = String.raw`
const fs = require('node:fs/promises'), p = require('node:path');
const within = (root, file) => { const r = p.relative(root, file); return !r || (!r.startsWith('..') && !p.isAbsolute(r)); };
(async () => {
 let raw=''; for await(const c of process.stdin) raw+=c; const { op, args, cwd, writableRoot, readOnlyRoots } = JSON.parse(raw);
 async function path(value, write=false) {
  if(typeof value!=='string' || !value) throw Error('path required');
  const target=p.resolve(cwd,value), roots=write ? (writableRoot?[writableRoot]:[]) : [cwd,...readOnlyRoots];
  if(!roots.some(r=>within(r,target))) throw Error('path escapes assigned roots');
  let ancestor=target; while(true) { try { const canonical=await fs.realpath(ancestor); if(!roots.some(r=>within(r,canonical))) throw Error('symlink escapes assigned roots'); break; } catch(e) { if(e.code!=='ENOENT') throw e; const meta=await fs.lstat(ancestor).catch(err=>{if(err.code!=='ENOENT')throw err;}); if(meta?.isSymbolicLink())throw Error('dangling symlink is not an assigned file'); const parent=p.dirname(ancestor); if(parent===ancestor) throw e; ancestor=parent; } }
  return target;
 }
 if(op==='Read') process.stdout.write(await fs.readFile(await path(args.path),'utf8'));
 else if(op==='Write') { const f=await path(args.path,true); if(typeof args.content!=='string') throw Error('content required'); await fs.mkdir(p.dirname(f),{recursive:true}); await fs.writeFile(f,args.content); process.stdout.write('Wrote '+p.relative(cwd,f)); }
 else if(op==='Edit') { const f=await path(args.path,true); const before=await fs.readFile(f,'utf8'); if(typeof args.oldText!=='string'||!args.oldText||typeof args.newText!=='string') throw Error('oldText/newText required'); if(before.split(args.oldText).length!==2) throw Error('Edit requires exactly one exact match'); await fs.writeFile(f,before.replace(args.oldText,()=>args.newText)); process.stdout.write('Edited '+p.relative(cwd,f)); }
 else {
  const base=await path(args.path||'.'); const regex=op==='Grep'?new RegExp(args.pattern):null;
  const glob=op==='Glob'?new RegExp('^'+args.pattern.split('**').map(x=>x.split('*').map(y=>y.replace(/[.+?^\x24{}()|[\]\\]/g,'\\$&')).join('[^/]*')).join('.*')+'$'):null;
  let count=0;
  async function walk(file) { const info=await fs.lstat(file); if(info.isSymbolicLink()) return; if(info.isDirectory()) { for(const name of (await fs.readdir(file)).sort()) { if(name==='.git'||name==='node_modules') continue; await walk(p.join(file,name)); } } else if(info.isFile()) { if(++count>20000) throw Error('Search file limit exceeded; narrow path'); const name=p.relative(cwd,file); if(glob) {if(glob.test(name)) console.log(name);} else {if(info.size>1000000)return; const lines=(await fs.readFile(file,'utf8')).split('\n'); lines.forEach((line,i)=>{if(regex.test(line))console.log(name+':'+(i+1)+':'+line);});} } }
  await walk(base);
 }
})().catch(e=>{console.error(e.message);process.exitCode=1;});`;
export async function sandboxFileTool(sandbox, op, args) {
  return (await sandbox.run(['/runtime/node', '-e', FILE_PROGRAM], JSON.stringify({ op, args, cwd: sandbox.cwd, writableRoot: sandbox.writableRoot, readOnlyRoots: sandbox.readOnlyRoots }))).stdout;
}
