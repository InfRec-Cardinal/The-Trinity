export function redact(value, secrets = []) {
  let text = String(value ?? '');
  for(const secret of secrets)if(typeof secret === 'string' && secret.length)text=text.split(secret).join('[redacted]');
  return text.replace(/\bBearer\s+[A-Za-z0-9._~+/=-]+/gi,'Bearer [redacted]').replace(/\b(?:sk|ak|key)-[A-Za-z0-9_-]{12,}\b/g,'[redacted]');
}
