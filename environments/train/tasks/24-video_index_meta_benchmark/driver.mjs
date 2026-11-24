                                                                                                                         
                                                                                                                     
                                                                                                                                  
                                                                                                                               
import { readFileSync, existsSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { sampleVideoForH0, videoManifestToH0Turn } from '../../lib/video-frames.mjs';

export const ACTION_CONTRACT = 'Submit one official multiple-choice answer letter. No reasoning text.';
const letters = item => item.options.map((_, i) => String.fromCharCode(65 + i));
export const optionText = item => item.options.map((v, i) => `${String.fromCharCode(65 + i)}. ${v}`).join('\n');
                                                                        
export const toolFor = item => ({ name: 'submit_action', description: 'Submit one official video multiple-choice answer.',
  parameters: { type: 'object', additionalProperties: false, properties: { answer: { type: 'string', enum: letters(item) } }, required: ['answer'] } });

export async function createDriver({ root }) {
  const items = JSON.parse(readFileSync(new URL('./items.json', import.meta.url))).items;
  const videoDir = process.env.VIDEO_INDEX_DIR ?? join(root, 'data/video-index/videos');
  const configurations = items.map((item, i) => ({ id: item.itemId, ordinal: i, videoId: item.videoId, sourceBenchmark: item.sourceBenchmark }));
  return {
    id: 'official-video-index-items', version: 1, kind: 'anchor', independentItems: true, maxSteps: 1, configurations,
    tool: { name: 'submit_action', description: 'Submit one official video multiple-choice answer.', parameters: { type: 'object', additionalProperties: false, properties: { answer: { type: 'string' } }, required: ['answer'] } },
    toolFor: index => toolFor(items[index]),
    actionContract: ACTION_CONTRACT,
    normalizeAction: input => input && typeof input.answer === 'string' && Object.keys(input).length === 1 && /^[A-Z]$/.test(input.answer) ? { answer: input.answer } : null,
    source: { kind: 'official', dataset: 'Video-Index/Video-Index', frames: 16, maxEdge: 512, audio: false, subtitles: false },
    async open({ runDir, run, episode }) {
      const index = episode.configurationIndex ?? 0, item = items[index]; if (!item) throw new Error('Unknown item index');
      const video = join(videoDir, `${item.videoId}.mp4`); if (!existsSync(video)) throw new Error(`Video missing: ${video}`);
      const dir = join(runDir, 'h0-video-input', item.videoId); mkdirSync(dir, { recursive: true });
      const manifest = sampleVideoForH0(video, dir, { frameCount: 16, maxEdge: 512 });
      const turn = videoManifestToH0Turn(manifest, dir, item.question, optionText(item));
      const observation = { publicText: turn.text[0].text, playerTurn: turn, tool: toolFor(item), manifest,
        frames: manifest.frames.map(f => ({ ...f, path: `h0-video-input/${item.videoId}/${f.path}` })), terminal: { ended: false, outcome: null, reason: null } };
      let done = false;
      return { observation,
        async step(action) {
          if (done) throw new Error('Item already answered');
          const answer = action?.answer; if (!letters(item).includes(answer)) throw new Error('Answer is not one of the displayed options');
          done = true; const correct = answer === item.answer;
          return { publicText: correct ? 'Correct.' : 'Incorrect.', reward: Number(correct),
            terminal: { ended: true, outcome: correct ? 'success' : 'failure', reason: 'official_answer_scored', score: Number(correct), evaluation: { modelAnswer: answer, officialAnswer: item.answer, correct } } };
        },
        async close() {} };
    } };
}
