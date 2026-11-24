                              
                                                                                                                
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { makeSessionDriver } from '../../lib/session-driver.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const task = JSON.parse(readFileSync(resolve(here, 'task.json'), 'utf8'));
const configurations = JSON.parse(readFileSync(resolve(here, 'configurations.json'), 'utf8')).configurations;

export async function createDriver({ root }) {
  return makeSessionDriver({ root, task, configurations });
}
