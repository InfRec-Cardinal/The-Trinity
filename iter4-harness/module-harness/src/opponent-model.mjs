import {equal, key, sum, partition} from './common.mjs';

function hypotheses() {
  return [0, 1, 2].flatMap(p => [1, 2].flatMap(d => [0, 1].flatMap(a => [0, 1].map(r => ({p, d, a, r})))));
}
function predict(base, h, t, signal, reverseOdd) {
  const b = reverseOdd && t % 2 ? [...base].reverse() : base;
  const shift = ((h.p + h.d * t + h.a * Math.floor(t / 2) + h.r * signal) % 3 + 3) % 3;
  return b.map((_, i) => b[(i - shift + 3) % 3]);
}
function infer(input, reverseOdd) {
  const records = [...input.archives, ...input.history];
  return hypotheses().filter(h => records.every(e => equal(predict(input.base, h, e.t, e.signal, reverseOdd), e.opponent)));
}
function allocations(total) {
  if (!Number.isInteger(total) || total < 0 || total > 100) throw Error('Allocation domain outside bound');
  const result = [];
  for (let a = 0; a <= total; a++) for (let b = 0; b <= total - a; b++) result.push([a, b, total - a - b]);
  return result;
}
const win = (a, b) => Number(a.filter((v, i) => v > b[i]).length >= 2);
function ranks(input, survivors, reverseOdd) {
  return allocations(input.total).map(action => {
    const results = survivors.map(h => win(action, predict(input.base, h, input.t, input.signal, reverseOdd)));
    return {action, guaranteedWin: Math.min(...results), modelWinFraction: sum(results) / results.length};
  }).sort((a, b) => b.guaranteedWin - a.guaranteedWin || b.modelWinFraction - a.modelWinFraction);
}

export function paritySignalChoice(input) {
  const survivors = infer(input, true);
  if (!survivors.length) return {status: 'inconsistent_evidence'};
  const choices = ranks(input, survivors, true).map(r => {
    const signal = r.action.indexOf(Math.max(...r.action)), groups = new Map();
    for (const h of survivors) {
      const observed = predict(input.base, h, input.t, input.signal, true), k = key(observed);
      const xs = groups.get(k) || []; xs.push(h); groups.set(k, xs);
    }
    const nextWins = input.roundsRemaining > 1 ? [...groups.values()].map(group => ranks({...input, t: input.t + 1, signal}, group, true)[0].guaranteedWin) : [0];
    return {...r, nextSignal: signal, nextRoundWorstWin: Math.min(...nextWins)};
  }).sort((a, b) => b.guaranteedWin - a.guaranteedWin || b.nextRoundWorstWin - a.nextRoundWorstWin ||
    b.modelWinFraction - a.modelWinFraction);
  const original = input.proposed ? choices.find(r => equal(r.action, input.proposed)) : null;
  return {status: 'ranked', currentParity: input.t % 2, survivors, recommendation: choices[0], original,
    ranking: choices.slice(0, 8), horizon: 2, nextRoundApplicable: input.roundsRemaining > 1,
    limitations: 'Two-period ranking is not a proof of reaching the final five-win threshold.'};
}

export function endogenousSignalPolicy(input) {
  const survivors = infer(input, false), actions = allocations(input.total);
  if (!survivors.length) return {status: 'inconsistent_evidence'};
  let visits = 0, cut = false; const memo = new Map(), limit = input.maxVisits ?? 30000;
  function solve(hs, t, signal, remaining) {
    if (!remaining) return {value: 0, action: null, complete: true};
    if (++visits > limit) { cut = true; return {value: 0, action: null, complete: false}; }
    const cacheKey = key([hs, t, signal, remaining]); if (memo.has(cacheKey)) return memo.get(cacheKey);
    let best = {value: -1, action: null, complete: true};
    const ranked = ranks({...input, t, signal}, hs, false);
    for (const r of ranked) {
      const groups = new Map();
      for (const h of hs) {
        const other = predict(input.base, h, t, signal, false), k = key(other);
        if (!groups.has(k)) groups.set(k, {other, hs: []}); groups.get(k).hs.push(h);
      }
      let worst = remaining, complete = true;
      for (const g of groups.values()) {
        const loss = r.action.findIndex((v, i) => v <= g.other[i]);
        const tail = solve(g.hs, t + 1, loss < 0 ? 0 : loss, remaining - 1);
        worst = Math.min(worst, win(r.action, g.other) + tail.value); complete &&= tail.complete;
      }
      if (worst > best.value) best = {value: worst, action: r.action, complete};
      if (best.value === remaining || cut) break;
    }
    best.complete = best.complete && !cut;
    if (best.complete) memo.set(cacheKey, best);
    return best;
  }
  const result = solve(survivors, input.t, input.signal, input.roundsRemaining);
  return {status: cut ? 'search_limit' : 'policy_computed', survivors, recommendation: result.action,
    guaranteedAdditionalWinsLowerBound: Math.max(0, result.value), visits,
    thresholdCertified: input.winsSoFar + Math.max(0, result.value) >= input.requiredWins,
    complete: !cut, legalAllocationCount: actions.length,
    note: 'Guarantee is conditional on the supplied public model and correctly parsed complete history.'};
}
