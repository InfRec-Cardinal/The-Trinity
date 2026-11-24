                                                                                                                          
                                                                                         
                                                                                           
                                                                                                                     
                                                                                                                   
                                                                                                                       
                                                                                                
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createUnseenDriverRegistry } from '../interface/registry.mjs';

const [taskId, runDir, ...rest] = process.argv.slice(2);
if (!taskId || !runDir) { console.error('usage: node tools/replay_verify.mjs <taskId> <H0 run dir> [--episodes N] [--max-steps N]'); process.exit(2); }
const opt = name => { const i = rest.indexOf(name); return i >= 0 ? Number(rest[i + 1]) : null; };
const maxEpisodes = opt('--episodes') ?? 3, maxSteps = opt('--max-steps') ?? Infinity;

const checkpoint = JSON.parse(readFileSync(join(runDir, 'checkpoint.json'), 'utf8'));
const driver = await createUnseenDriverRegistry({ record: false }).getDriver(taskId);
if (!driver) { console.error(`${taskId}: not a driver task of this package`); process.exit(2); }
const indexById = new Map(driver.configurations.map((c, i) => [c.id, i]));
const term = t => JSON.stringify({ ended: !!t?.ended, outcome: t?.outcome ?? null, reason: t?.reason ?? null, score: t?.score ?? null });
const first = (a, b) => { let i = 0; while (i < a.length && a[i] === b[i]) i++; return i; };

let episodes = 0, steps = 0, mismatches = 0;
for (const e of checkpoint.episodes.filter(x => x.status === 'completed')) {
  if (episodes >= maxEpisodes) break;
  const confId = checkpoint.configurations[e.configurationIndex]?.id;
  const index = indexById.get(confId);
  if (index == null) { console.log(`skip ${e.id}: configuration ${confId} not in this package`); continue; }
  const stepDir = join(runDir, 'episodes', e.id, 'h0-trace', 'steps');
  if (!existsSync(stepDir)) { console.log(`skip ${e.id}: no step trace`); continue; }
  const files = readdirSync(stepDir).filter(f => f.endsWith('.json')).sort();
  const tmp = mkdtempSync(join(tmpdir(), `replay-${taskId}-`));
  let bad = 0, n = 0;
  try {
    const opened = await driver.open({ runDir: tmp, run: { configurations: driver.configurations }, episode: { id: e.id, configurationIndex: index } });
    const want0 = e.initialObservation?.publicText ?? '';
    if (opened.observation.publicText !== want0) { bad++; console.log(`  ${e.id} initial observation differs at char ${first(opened.observation.publicText, want0)}`); }
    for (const f of files) {
      if (n >= maxSteps) break;
      const rec = JSON.parse(readFileSync(join(stepDir, f), 'utf8')).data;
                                                                                                               
      const got = rec.action?.hostInjected && rec.action?.tool === '__host_end__' && opened.hostEnd
        ? await opened.hostEnd('h0_output_cap_exhausted') : await opened.step(rec.action);
      n++;
      const want = rec.observation;
      if (got.publicText !== want.publicText) { bad++; console.log(`  ${e.id} step ${rec.index}: publicText differs at char ${first(got.publicText, want.publicText)}`); }
      if (term(got.terminal) !== term(want.terminal)) { bad++; console.log(`  ${e.id} step ${rec.index}: terminal ${term(got.terminal)} vs H0 ${term(want.terminal)}`); }
      if (bad > 5) break;
    }
    await opened.close?.();
  } catch (error) { bad++; console.log(`  ${e.id}: ${error.message}`); }
  finally { rmSync(tmp, { recursive: true, force: true }); }
  episodes++; steps += n; mismatches += bad;
  console.log(`${bad ? 'DIFF' : 'ok  '} ${e.id} (${confId}): ${n} steps replayed${n < files.length ? ` of ${files.length}` : ''}`);
}
console.log(`${taskId}: ${episodes} episodes, ${steps} steps, ${mismatches} mismatches`);
process.exit(mismatches ? 1 : 0);
