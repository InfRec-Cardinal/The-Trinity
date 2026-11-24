                                                                                                                                    
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readSync, rmSync, writeFileSync } from 'node:fs';
import { basename, join, resolve } from 'node:path';

                                                                                                                      
const FFMPEG = process.env.FFMPEG ?? 'ffmpeg';
const FFPROBE = process.env.FFPROBE ?? 'ffprobe';
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

function hashVideoFile(path) {
  const digest = createHash('sha256');
  const fd = openSync(path, 'r');
  const chunk = Buffer.allocUnsafe(1024 * 1024);
  try {
    for (let size; (size = readSync(fd, chunk, 0, chunk.length, null)) > 0;) {
      digest.update(chunk.subarray(0, size));
    }
  } finally { closeSync(fd); }
  return digest.digest('hex');
}

export function sampleVideoForH0(videoPath, outputDir, { frameCount = 16, maxEdge = 512 } = {}) {
  if (!existsSync(videoPath)) throw new Error(`Video file missing: ${videoPath}`);
  if (!Number.isInteger(frameCount) || frameCount < 1 || frameCount > 40)
    throw new Error('H0 video frameCount must be 1–40');
  if (!Number.isInteger(maxEdge) || maxEdge < 128 || maxEdge > 1024)
    throw new Error('H0 video maxEdge must be 128–1024');
  const duration = Number(execFileSync(FFPROBE,
    ['-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',videoPath],
    { encoding:'utf8', timeout:30_000 }).trim());
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('Video duration unavailable');
  const videoSha256 = hashVideoFile(videoPath);
  const directory = resolve(outputDir);
  mkdirSync(directory, { recursive:true });
  const frames = [];
  for (let index = 0; index < frameCount; index++) {
                                                                               
                                                                            
    const requestedTimestampSeconds = Number(((index + 0.5) * duration / frameCount).toFixed(3));
    const name = `frame-${String(index + 1).padStart(3,'0')}.png`;
    const path = join(directory, name);
                                                                            
                                                                              
                                                                   
    let timestampSeconds = requestedTimestampSeconds;
    for (let attempt = 0; attempt < 8; attempt++) {
      rmSync(path, { force:true });
      execFileSync(FFMPEG, ['-nostdin','-hide_banner','-loglevel','error',
        '-ss',String(timestampSeconds),'-i',videoPath,'-frames:v','1',
        '-vf',`scale=w='min(${maxEdge},iw)':h='min(${maxEdge},ih)':force_original_aspect_ratio=decrease`,
        '-an','-sn','-y',path], { timeout:60_000, maxBuffer:1024*1024 });
      if (existsSync(path)) break;
      timestampSeconds = Math.max(0, Number((timestampSeconds - Math.max(0.25,duration / frameCount)).toFixed(3)));
    }
    if (!existsSync(path)) throw new Error(`No decodable RGB frame near ${requestedTimestampSeconds}s: ${name}`);
    const bytes = readFileSync(path);
    if (bytes.length < 8 || bytes.subarray(0,8).toString('hex') !== '89504e470d0a1a0a')
      throw new Error(`Invalid extracted PNG: ${name}`);
    frames.push({ index:index+1, requestedTimestampSeconds, timestampSeconds, path:name, sha256:hash(bytes), mimeType:'image/png' });
  }
  const manifest = { schema:'h0-video-frame-input-v1', sourceVideo:basename(videoPath),
    videoSha256, durationSeconds:duration, frameCount, maxEdge,
    sampling:'uniform_segment_midpoints', audioIncluded:false, subtitlesIncluded:false,
    frames };
  writeFileSync(join(directory,'manifest.json'),JSON.stringify(manifest,null,2));
  return manifest;
}

export function videoManifestToH0Turn(manifest, directory, question, options = '') {
  if (manifest?.schema !== 'h0-video-frame-input-v1' || !Array.isArray(manifest.frames)
    || manifest.frames.length !== manifest.frameCount || typeof question !== 'string' || !question.trim())
    throw new Error('Invalid H0 video manifest or question');
  const text = [{type:'text',text:`Video observation: ${manifest.frameCount} ordered RGB frames sampled uniformly over ${manifest.durationSeconds.toFixed(2)} seconds. No audio or subtitles. Answer using visual evidence only.\nQuestion: ${question}\n${options}`}];
  for (const frame of manifest.frames) {
    if (!/^frame-\d{3}\.png$/.test(frame.path)) throw new Error('Invalid frame path');
    const bytes = readFileSync(join(directory,frame.path));
    if (hash(bytes) !== frame.sha256) throw new Error(`Frame integrity check failed: ${frame.path}`);
    text.push({type:'text',text:`Frame ${frame.index}/${manifest.frameCount} at ${frame.timestampSeconds.toFixed(3)} s:`});
    text.push({type:'image',source:{type:'base64',media_type:'image/png',data:bytes.toString('base64')}});
  }
  return {role:'user',text};
}
