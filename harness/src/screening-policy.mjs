// Count bounds define a predeclared intermediate-performance band.
// Legacy targetSuccesses remains an exact-count policy for reproducibility.
export function screeningPolicy(value = {trials: 3, targetSuccesses: 1}) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Screening policy required');
  const {trials} = value;
  if (!Number.isInteger(trials) || trials < 2) throw Error('Screening requires at least two trials');
  const legacy = Object.hasOwn(value, 'targetSuccesses');
  if (legacy && (Object.hasOwn(value, 'minSuccesses') || Object.hasOwn(value, 'maxSuccesses'))) throw Error('Do not mix exact-count and interval screening policies');
  const minSuccesses = legacy ? value.targetSuccesses : value.minSuccesses;
  const maxSuccesses = legacy ? value.targetSuccesses : value.maxSuccesses;
  if (!Number.isInteger(minSuccesses) || !Number.isInteger(maxSuccesses) || minSuccesses < 1 || maxSuccesses >= trials || minSuccesses > maxSuccesses) throw Error('Screening band must exclude zero success and perfect success');
  return Object.freeze({trials, minSuccesses, maxSuccesses});
}
