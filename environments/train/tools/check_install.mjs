                                                                                                                       
                                                   
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createTrainDriverRegistry } from '../interface/registry.mjs';
const registry = createTrainDriverRegistry({ record: false });
const ids = process.argv.slice(2).length ? process.argv.slice(2) : [...registry.tasks.keys()];
let failed = 0;
for (const id of ids) {
  const runDir = mkdtempSync(join(tmpdir(), `train-check-${id}-`));
  try {
    const driver = await registry.getDriver(id);
    const opened = await driver.open({ runDir, run: { configurations: driver.configurations }, episode: { id: 'install-check', configurationIndex: 0 } });
    const text = opened.observation?.publicText ?? '';
    await opened.close?.();
    console.log(`ok    ${id}  (${driver.configurations.length} configurations, first observation ${text.length} chars)`);
  } catch (error) { failed++; console.log(`FAIL  ${id}: ${error.message}`); }
  finally { rmSync(runDir, { recursive: true, force: true }); }
}
console.log(failed ? `${failed} task(s) not ready` : 'all tasks ready');
process.exit(failed ? 1 : 0);
