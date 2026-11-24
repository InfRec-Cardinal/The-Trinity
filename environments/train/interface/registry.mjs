                                                                                               
                                                                                                      
                                                                                   
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
    const task = JSON.parse(readFileSync(file, 'utf8')); tasks.set(task.taskId, { ...task, folder: join(root, 'tasks', folder) });
  }
  return tasks;
}
export function createTrainDriverRegistry({ root = ROOT, record = true } = {}) {
  const tasks = loadTasks(root), cache = new Map();
  async function getDriver(task) {
    const id = taskIdOf(task), entry = tasks.get(id); if (!entry) return null;
    if (!cache.has(id)) cache.set(id, (async () => {
      const { createDriver } = await import(pathToFileURL(join(entry.folder, 'driver.mjs')).href);
      const driver = { ...(await createDriver({ root })), taskId: id };
      return record ? withRecorder(driver) : driver;
    })());
    return cache.get(id);
  }
  return {
    tasks,
    supportsTask: task => tasks.has(taskIdOf(task)),
    async taskReadiness(task) {
      const id = taskIdOf(task); if (!tasks.has(id)) return { supported: false, ready: false, blockers: ['not a train task'] };
      try { const d = await getDriver(id); return { supported: true, ready: true, blockers: [], kind: d.kind, configurations: d.configurations }; }
      catch (error) { return { supported: true, ready: false, blockers: [error.message] }; }
    },
    async prepare(task, options = {}) { const d = await getDriver(task); return d?.prepare ? d.prepare(options) : { prepared: true }; },
    getDriver,
                                                                                                             
    taskSpec(task) { const e = tasks.get(taskIdOf(task)); return e && { taskId: e.taskId, kind: e.kind, spec: { assignment: e.assignment }, evaluation: e.evaluation, player: e.player }; },
  };
}
