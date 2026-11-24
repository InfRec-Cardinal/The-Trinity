                                                                                                               
                                                                                                        
                                                                                                                     
                                                          
import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { withRecorder } from './recorder.mjs';
const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const taskIdOf = task => typeof task === 'string' ? task : task?.taskId ?? task?.id;
export function loadTasks(root = ROOT) {
  const tasks = new Map();
  for (const folder of readdirSync(join(root, 'tasks')).sort()) {
    const file = join(root, 'tasks', folder, 'task.json'); if (!existsSync(file)) continue;
    const task = JSON.parse(readFileSync(file, 'utf8'));
    tasks.set(task.taskId, { ...task, folder: join(root, 'tasks', folder), runner: existsSync(join(root, 'tasks', folder, 'driver.mjs')) ? 'driver' : 'own' });
  }
  return tasks;
}
export function createUnseenDriverRegistry({ root = ROOT, record = true } = {}) {
  const tasks = loadTasks(root), cache = new Map();
  async function getDriver(task) {
    const id = taskIdOf(task), entry = tasks.get(id); if (!entry || entry.runner !== 'driver') return null;
    if (!cache.has(id)) cache.set(id, (async () => {
      const { createDriver } = await import(pathToFileURL(join(entry.folder, 'driver.mjs')).href);
      const driver = { ...(await createDriver({ root })), taskId: id };
      return record ? withRecorder(driver) : driver;
    })());
    return cache.get(id);
  }
  return {
    tasks,
    supportsTask: task => tasks.get(taskIdOf(task))?.runner === 'driver',
    async taskReadiness(task) {
      const id = taskIdOf(task), e = tasks.get(id);
      if (!e) return { supported: false, ready: false, blockers: ['not an unseen task'] };
      if (e.runner !== 'driver') return { supported: false, ready: false, blockers: [`${id} runs with its own workflow (see ${e.folder}/README.md)`] };
      try { const d = await getDriver(id); return { supported: true, ready: true, blockers: [], kind: d.kind, configurations: d.configurations }; }
      catch (error) { return { supported: true, ready: false, blockers: [error.message] }; }
    },
    async prepare(task, options = {}) { const d = await getDriver(task); return d?.prepare ? d.prepare(options) : { prepared: true }; },
    getDriver,
                                                                                                                          
                                                                                                         
    taskSpec(task) { const e = tasks.get(taskIdOf(task)); return e && { taskId: e.taskId, kind: e.kind, spec: { assignment: e.assignment }, evaluation: e.evaluation, player: e.player }; },
  };
}
