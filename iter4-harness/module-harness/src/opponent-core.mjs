import {equal, key, sum, partition} from './common.mjs';

export function hypotheses() {
  return [0, 1, 2].flatMap(p => [1, 2].flatMap(d => [0, 1].flatMap(a => [0, 1].map(r => ({p, d, a, r})))));
}
export function predict(base, h, t, signal, reverseOdd) {
  const b = reverseOdd && t % 2 ? [...base].reverse() : base;
  const shift = ((h.p + h.d * t + h.a * Math.floor(t / 2) + h.r * signal) % 3 + 3) % 3;
  return b.map((_, i) => b[(i - shift + 3) % 3]);
}
export function infer(input, reverseOdd) {
  const records = [...input.archives, ...input.history];
  return hypotheses().filter(h => records.every(e => equal(predict(input.base, h, e.t, e.signal, reverseOdd), e.opponent)));
}
export function allocations(total) {
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

