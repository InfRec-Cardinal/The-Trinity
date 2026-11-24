                                                                                                                 
import { Raster } from './raster.mjs';
export function textFrame(text, { width = 640, height = 420 } = {}) {
  const r = new Raster(width, height);
  const lines = String(text).toUpperCase().replace(/[^A-Z0-9 \-?*.:/+\n]/g, ' ').split('\n').flatMap(line => line.match(/.{1,50}/g) ?? ['']);
  lines.slice(0, 26).forEach((line, i) => r.text(line, 12, 12 + i * 15, [38, 54, 72], 2));
  return r;
}
