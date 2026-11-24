import json
import os
import sys
import urllib.request
from types import SimpleNamespace

from trinity_stage2 import cli, model


class Block:
    def __init__(self, value):
        self.value = value
        self.type = value['type']

    def model_dump(self, exclude_none=True):
        return self.value


def create(_api, **params):
    request = urllib.request.Request(os.environ['STUDIO_STAGE2_BRIDGE'],
        data=json.dumps(params).encode(), headers={'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + os.environ['STUDIO_STAGE2_TOKEN']}, method='POST')
    with urllib.request.urlopen(request, timeout=960) as response:
        result = json.load(response)
    if 'error' in result:
        error = model.AgentError(result['error'], 'studio_transport')
        error.attemptRecords = result.get('attemptRecords', [])
        raise error
    blocks = result.get('assistantContent') or [{'type': 'text', 'text': result.get('text', '')}]
    stop = {'paused': 'pause_turn', 'truncated': 'max_tokens', 'refused': 'refusal'}.get(result['stopReason'],
        'tool_use' if any(b['type'] == 'tool_use' for b in blocks) else 'end_turn')
    return SimpleNamespace(content=[Block(b) for b in blocks], stop_reason=stop,
        usage=result.get('usage')), result.get('attemptRecords', [])


model.client = lambda profile=None: None
model._create = create
cli.main(sys.argv[1:])
