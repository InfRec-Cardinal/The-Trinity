import fs from 'node:fs';
import {createHash} from 'node:crypto';

const types = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp']);
export function imageBlock(value) {
  if (typeof value === 'string' && value.startsWith('data:image/')) {
    const match = /^data:(image\/[a-z]+);base64,([A-Za-z0-9+/=\s]+)$/.exec(value);
    if (!match) throw Error('Invalid image data URI');
    return imageBlock({type: 'image', mimeType: match[1], data: match[2]});
  }
  if (!value || typeof value !== 'object') return null;
  if (value.type === 'image_url' || value.type === 'input_image') {
    const url = value.image_url?.url ?? value.image_url;
    if (typeof url !== 'string') throw Error('Image URL required');
    return url.startsWith('data:') ? imageBlock(url) : imageBlock({type: 'image', source: {type: 'url', url}});
  }
  if (value.type !== 'image') return null;
  const source = value.source ?? {};
  if (source.type === 'url') {
    if (!/^https?:\/\//.test(source.url ?? '')) throw Error('Invalid image URL');
    return {type: 'image', source: {type: 'url', url: source.url}};
  }
  let data = source.data ?? value.data;
  if (value.path) data = fs.readFileSync(value.path).toString('base64');
  const media = source.media_type ?? value.mimeType ?? value.media_type;
  if (!types.has(media)) throw Error('Unsupported image media type');
  if (typeof data !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(data.replace(/\s/g, ''))) throw Error('Invalid base64 image');
  data = data.replace(/\s/g, '');
  const bytes = Buffer.from(data, 'base64');
  if (!bytes.length || bytes.length > 5 * 1024 * 1024 || bytes.toString('base64').replace(/=+$/, '') !== data.replace(/=+$/, '')) throw Error('Invalid image size or encoding');
  const detected = bytes.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10])) ? 'image/png'
    : bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255 ? 'image/jpeg'
    : /^GIF8[79]a/.test(bytes.subarray(0, 6).toString()) ? 'image/gif'
    : bytes.subarray(0, 4).toString() === 'RIFF' && bytes.subarray(8, 12).toString() === 'WEBP' ? 'image/webp' : null;
  if (detected !== media) throw Error('Image signature does not match media type');
  return {type: 'image', source: {type: 'base64', media_type: media, data: bytes.toString('base64')}};
}

export function normalizeMedia(value) {
  const block = imageBlock(value);
  if (block) return block;
  if (Array.isArray(value)) return value.map(normalizeMedia);
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalizeMedia(item)]));
  return value;
}

export function splitMedia(value) {
  const images = new Map();
  const visit = (item, location) => {
    const block = imageBlock(item);
    if (block) {
      const id = createHash('sha256').update(JSON.stringify(block.source)).digest('hex');
      if (!images.has(id)) images.set(id, {imageId: id, locations: [], block});
      images.get(id).locations.push(location);
      return {imageId: id, mediaType: block.source.media_type ?? 'remote_image'};
    }
    if (Array.isArray(item)) return item.map((child, i) => visit(child, location + '/' + i));
    if (item && typeof item === 'object') return Object.fromEntries(Object.entries(item).map(([key, child]) => [key, visit(child, location + '/' + key.replace(/~/g, '~0').replace(/\//g, '~1'))]));
    return item;
  };
  const data = visit(value, '');
  const attachments = [...images.values()].flatMap(({imageId, locations, block}) => [{type: 'text', text: JSON.stringify({imageId, locations})}, block]);
  return {data, attachments};
}

export function modelContent(value) {
  const {data, attachments} = splitMedia(value);
  if (attachments.length / 2 > 100) throw Error('Request exceeds the image limit; reduce the observation history');
  return [{type: 'text', text: JSON.stringify(data)}, ...attachments];
}

export const publicText = value => JSON.stringify(splitMedia(value).data);
