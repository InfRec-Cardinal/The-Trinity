import {codes, feedback, equal, partition, key} from './common.mjs';

function choose(candidates, proposed, probeLimit = 64) {
  const stride = Math.max(1, Math.ceil(candidates.length / probeLimit));
  const probes = candidates.filter((_, i) => i % stride === 0);
  if (proposed && !probes.some(p => equal(p, proposed))) probes.push(proposed);
  const ranked = probes.map(probe => ({probe, ...partition(candidates, probe)}))
    .sort((a, b) => b.entropy - a.entropy || a.expected - b.expected);
  return {recommendation: ranked[0] ?? null, original: proposed ? ranked.find(r => equal(r.probe, proposed)) : null,
    probesEvaluated: probes.length, objective: 'maximum feedback entropy over bounded supplied probes, uniform candidate assumption'};
}

export function multiplicityDecomposition({alphabet, length, records, proposed, maxCandidates = 20000}) {
  if (!Number.isInteger(length) || length < 1 || !alphabet.length || alphabet.length ** length > maxCandidates)
    return {status: 'candidate_limit_or_invalid_domain'};
  const counts = g => alphabet.map(a => g.filter(v => v === a).length);
  const rows = records.map(r => ({...r, counts: counts(r.guess)})), histograms = [];
  function compose(i, remaining, vector) {
    if (i === alphabet.length - 1) {
      const h = [...vector, remaining];
      if (rows.every(r => h.reduce((n, x, j) => n + Math.min(x, r.counts[j]), 0) === r.feedback[0] + r.feedback[1])) histograms.push(h);
      return;
    }
    for (let n = 0; n <= remaining; n++) compose(i + 1, remaining - n, [...vector, n]);
  }
  compose(0, length, []); const survivors = [];
  function arrange(left, prefix) {
    if (prefix.length === length) {
      if (rows.every(r => equal(feedback(prefix, r.guess), r.feedback))) survivors.push(prefix);
      return;
    }
    for (let i = 0; i < left.length; i++) if (left[i]) {
      left[i]--; arrange(left, [...prefix, alphabet[i]]); left[i]++;
    }
  }
  histograms.forEach(h => arrange([...h], []));
  return {status: survivors.length ? 'decomposed' : 'inconsistent_evidence', histograms, candidateCount: survivors.length,
    countRanges: alphabet.map((symbol, i) => ({symbol, min: histograms.length ? Math.min(...histograms.map(h => h[i])) : null,
      max: histograms.length ? Math.max(...histograms.map(h => h[i])) : null})),
    ...choose(survivors, proposed), note: 'E+M constrains multiplicity; it never identifies exact matching positions.'};
}

