
export function arcPublicMeta(observation) {
  const text = observation.publicText;
  const raw = JSON.parse(text.slice(text.indexOf('{')));
  return raw.data ?? raw;
}

export async function autoResetArc({observation, opened, steps, limit}) {
  if (observation.terminal?.ended || observation.info.nativeActions >= limit
      || !['GAME_OVER', 'NOT_PLAYED'].includes(arcPublicMeta(observation).state)) return null;
  const action = {action: 'RESET'};
  const result = await opened.step(action, {index: steps});
  return {action, before: observation, observation: result.observation ?? result,
    toolId: `host_reset_${steps}`, actor: 'official_protocol_host', modelCalls: 0};
}
