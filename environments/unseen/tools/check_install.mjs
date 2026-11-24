                                                                                                                          
                                                   
                                                                                                          
                                                                                                                            
                                                                                                                                                                                              
                                                                                                                     
                                                                                                                                                                                               
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createUnseenDriverRegistry } from '../interface/registry.mjs';
process.env.COUP_STUB_OPPONENTS ??= '1';
process.env.POKER_STUB_OPPONENT ??= '1';
const args = process.argv.slice(2);
const registryRoot = fileURLToPath(new URL('..', import.meta.url));
const registry = createUnseenDriverRegistry({ record: false });
const wanted = args.filter(a => !a.startsWith('--'));
const ids = wanted.length ? wanted : [...registry.tasks.keys()];
let failed = 0;
for (const id of ids) {
  const entry = registry.tasks.get(id);
  if (!entry) { failed++; console.log(`FAIL  ${id}: not an unseen task`); continue; }
  if (entry.runner !== 'driver') { console.log(`skip  ${id}: own workflow, see ${entry.folder}/README.md`); continue; }
  if (entry.environment?.liveService && !wanted.includes(id)) { console.log(`skip  ${id}: live service, name it to check (${entry.environment.liveService})`); continue; }
  const data = entry.environment?.data;
  if (data && !existsSync(join(registryRoot, data.check))) { failed++; console.log(`FAIL  ${id}: data not downloaded yet, run: ${data.fetch}`); continue; }
  const ext = entry.environment?.external;
  if (ext && !existsSync(join(process.env[ext.variable] || ext.default, ext.check))) { console.log(`skip  ${id}: ${ext.variable} not installed (${ext.setup})`); continue; }
  const runDir = mkdtempSync(join(tmpdir(), `unseen-check-${id}-`));
  try {
    const driver = await registry.getDriver(id);
    const opened = await driver.open({ runDir, run: { configurations: driver.configurations }, episode: { id: 'install-check', configurationIndex: 0 } });
    const o = opened.observation;
    await opened.close?.();
    console.log(`ok    ${id}  (${driver.configurations.length} configurations; first observation ${o.publicText.length} chars, ${(o.frames ?? (o.frame ? [o.frame] : [])).length} image(s))`);
  } catch (error) { failed++; console.log(`FAIL  ${id}: ${String(error.message).slice(0, 300)}`); }
  finally { rmSync(runDir, { recursive: true, force: true }); }
}
console.log(failed ? `${failed} task(s) not ready` : 'all checked tasks ready');
process.exit(failed ? 1 : 0);
