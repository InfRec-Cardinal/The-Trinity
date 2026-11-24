import {equal} from './common.mjs';

export function frameAssociation({frames, initialDetection, maxDistance}) {
  if (!(maxDistance >= 0) || !frames.length) return {status: 'unknown', reason: 'Missing motion bound or frames'};
  let candidates = frames[0].detections.filter(d => d.id === initialDetection);
  if (!frames[0].source || candidates.length !== 1) return {status: 'unknown', reason: 'Need one sourced initial target detection'};
  const trace = [{time: frames[0].time, candidates: candidates.map(d => d.id)}];
  for (let i = 1; i < frames.length; i++) {
    const f = frames[i], dt = f.time - frames[i - 1].time;
    if (!(dt > 0) || !f.source) return {status: 'unknown', reason: 'Unordered or unsourced frame', trace};
    if (!f.detections.length) return {status: 'occluded', trace, time: f.time};
    candidates = f.detections.filter(d => candidates.some(p => d.position.length === p.position.length &&
      Math.hypot(...d.position.map((x, j) => x - p.position[j])) <= maxDistance * dt &&
      (d.stableFeatures == null || p.stableFeatures == null || equal(d.stableFeatures, p.stableFeatures))));
    trace.push({time: f.time, candidates: candidates.map(d => d.id)});
    if (!candidates.length) return {status: 'identity_lost', trace};
  }
  return {status: candidates.length === 1 ? 'unique_under_motion_model' : 'ambiguous', trace,
    finalCandidates: candidates.map(d => d.id), note: 'Input detections must come from actual frames; no RGB extraction here.'};
}

