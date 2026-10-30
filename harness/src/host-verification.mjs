export async function hostVerificationCall(stage, operation) {
  try {return await operation();}
  catch {throw new Error('Host verification failed: ' + stage);}
}

export function publicVerificationChecks(checks) {
  if (!Array.isArray(checks)) throw new Error('Invalid native verification checks');
  return checks.map(check => {
    if (!check || typeof check.id !== 'string' || !/^[a-zA-Z][a-zA-Z0-9_-]{0,127}$/.test(check.id) ||
        typeof check.passed !== 'boolean') throw new Error('Invalid native verification check');
    return {id: check.id, passed: check.passed,
      message: check.passed ? 'Native verification check passed' : 'Native verification check failed'};
  });
}
