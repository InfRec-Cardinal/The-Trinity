#!/usr/bin/env python3
                                                                                                  

                                                                                                              
                                                                                                               
   
import contextlib
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import uuid
from enum import Enum
from sublevel_protocol import select_level, level_passed, terminal_reason, level_score, save_receipt, available_actions

sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parents[3]
GAMES = PACKAGE / 'vendor' / 'arc-agi3' / 'games'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def go_offline():
                                                                                      
    for key in list(os.environ):
        if 'KEY' in key or key in ['OPERATION_MODE', 'ARC_BASE_URL', 'ONLY_RESET_LEVELS', 'ENVIRONMENTS_DIR', 'RECORDINGS_DIR']:
            os.environ.pop(key, None)
    os.environ['OPERATION_MODE'] = 'offline'
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
    import requests
    requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('Offline ARC-AGI-3 network disabled'))
    import socket
    socket.socket.connect = lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('Offline ARC-AGI-3 network disabled'))


def create(configuration, recordings_dir):
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger('h0_offline_arc')
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(GAMES), recordings_dir=str(recordings_dir), logger=logger)
    env = arc.make(configuration['gameId'], seed=configuration['seed'], save_recording=False)
    if env is None or env.observation_space is None:
        raise ValueError('Official ARC-AGI-3 full game failed to initialize')
    return arc, env


def normalize(value, seen=None):
    pass                                                                    
    if seen is None:
        seen = {}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Enum):
        return {'enum': type(value).__name__, 'value': value.value}
    if hasattr(value, 'tolist'):
        return {'array': value.tolist(), 'dtype': str(getattr(value, 'dtype', ''))}
                                                                           
                                                                                
    if isinstance(value, (list, tuple, dict, set, frozenset)):
        identity = id(value)
        if identity in seen:
            return {'reference': seen[identity]}
        seen[identity] = len(seen)
    if isinstance(value, (list, tuple)):
        return [normalize(item, seen) for item in value]
    if isinstance(value, dict):
        if all(isinstance(key, (str, bool, int, float)) or key is None for key in value):
            return {str(key): normalize(item, seen) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
                                                                        
                                                                                
                                                                    
        pairs = sorted(value.items(), key=lambda pair: json.dumps(normalize(pair[0], {}), sort_keys=True))
        return {'mapping': [{'key': normalize(key, seen), 'value': normalize(item, seen)} for key, item in pairs]}
    if isinstance(value, (set, frozenset)):
        ordered = sorted(value, key=lambda item: json.dumps(normalize(item, {}), sort_keys=True))
        return [normalize(item, seen) for item in ordered]
    if hasattr(value, 'bit_generator'):
        return {'randomState': normalize(value.bit_generator.state, seen)}
    if type(value).__module__ == 'numpy.random.mtrand' and hasattr(value, 'get_state'):
        return {'randomState': normalize(value.get_state(), seen)}
    if type(value).__module__ == 'random' and hasattr(value, 'getstate'):
        return {'randomState': normalize(value.getstate(), seen)}
    if callable(value):
        return {'callable': getattr(value, '__qualname__', type(value).__name__)}
    identity = id(value)
    if identity in seen:
        return {'reference': seen[identity]}
    seen[identity] = len(seen)
    fields = dict(vars(value)) if hasattr(value, '__dict__') else {}
    for cls in type(value).__mro__:
        slots = getattr(cls, '__slots__', ())
        for key in [slots] if isinstance(slots, str) else slots:
            if key not in ['__dict__', '__weakref__'] and hasattr(value, key):
                fields[key] = getattr(value, key)
    if fields or any(hasattr(cls, '__slots__') for cls in type(value).__mro__):
        return {'class': type(value).__name__, 'fields': {key: normalize(item, seen) for key, item in sorted(fields.items()) if not callable(item)}}
    raise ValueError('Unserializable official ARC-AGI-3 native state: ' + type(value).__name__)


def public_frame(obs):
    return {'frame': [layer.tolist() if hasattr(layer, 'tolist') else layer for layer in obs.frame],
            'state': obs.state.name, 'levels_completed': obs.levels_completed, 'win_levels': obs.win_levels,
            'available_actions': available_actions(obs), 'guid': obs.guid, 'full_reset': obs.full_reset}


class Bridge:
    def init(self, command):
        self.configuration = command['configuration']
        self.run_dir = Path(command['runDir']).resolve()
        self.directory = Path(command['episodePath'])
        if self.directory.is_absolute() or '..' in self.directory.parts:
            raise ValueError('Unsafe ARC-AGI-3 episode path')
        self.arc, self.env = create(self.configuration, self.run_dir / self.directory / 'official-recordings')
                                                                                                                    
        self.guid = str(uuid.uuid5(uuid.NAMESPACE_URL, self.run_dir.as_posix() + '/' + self.directory.as_posix()))
        original = self.env._guid
        self.env._guid = self.guid
        self.env.observation_space.guid = self.guid
        manager = self.arc.scorecard_manager
        card = manager.scorecards[self.env.scorecard_id]
        card.cards[self.configuration['gameId']].guids[0] = self.guid
        old_card_id = manager.guids.pop(original)
        self.card_id = str(uuid.uuid5(uuid.NAMESPACE_URL, self.run_dir.as_posix() + '/' + self.directory.as_posix() + '/scorecard'))
        manager.scorecards[self.card_id] = manager.scorecards.pop(old_card_id)
        manager.scorecards[self.card_id].card_id = self.card_id
        manager.guids[self.guid] = self.card_id
        self.env.scorecard_id = self.card_id
        self.arc._default_scorecard_id = self.card_id
        self.sublevel = 'levelIndex' in self.configuration
        if not self.sublevel:
            raise ValueError('This evaluation requires an independent level configuration')
        self.initial_completed = select_level(self.env, self.configuration)
        self.attempt_limit = self.configuration['maxSteps']
        if isinstance(self.attempt_limit, bool) or not isinstance(self.attempt_limit, int) or self.attempt_limit <= 0:
            raise ValueError('Invalid independent-level action budget')
        save_receipt(self.run_dir / self.directory / 'sublevel-initialization.json', {
            'protocol': 'independent-native-level-reset-v2', 'gameId': self.configuration['gameId'],
            'levelIndex': self.configuration['levelIndex'], 'seed': self.configuration['seed'],
            'initialCompleted': self.initial_completed, 'priorLevelsCredited': 0,
            'maxSteps': self.attempt_limit, 'setup': 'fresh game RESET then native set_level; no solution replay',
            'gameSourceHash': self.configuration['gameSourceHash']})
        self.closed_scorecard = None
        self.step_index = 0
        self.native_action_count = 0
        self.previous_action = None
        self.reset_count = 0
        self.game_over_count = 0
        self.source_command_count = 1                                   
        self.rejected_attempts = 0
        self.transport_feedback = None
        self.cached_native = None
        self.cached_native_hash = None
        self.cached_snapshot = None
        self.cached_state_hash = None
        return self.observation()

    def ended(self):
        return terminal_reason(self.env.observation_space, self.initial_completed,
                               self.native_action_count, self.attempt_limit) is not None

    def snapshot(self):
        if self.cached_snapshot is None:
            self.cached_snapshot = {**self.native_snapshot(), 'submittedActions': self.step_index,
                                    'sourceCommands': self.source_command_count, 'nativeActions': self.native_action_count, 'rejectedAttempts': self.rejected_attempts,
                                    'transportFeedback': self.transport_feedback}
        return self.cached_snapshot

    def native_snapshot(self):
        if self.cached_native is None:
            frame = public_frame(self.env.observation_space)
            frame.pop('guid')
            self.cached_native = {'native': normalize(self.env._game), 'public': frame}
        return self.cached_native

    def native_state_hash(self):
        if self.cached_native_hash is None:
            self.cached_native_hash = digest(self.native_snapshot())
        return self.cached_native_hash

    def state_hash(self):
        if self.cached_state_hash is None:
            self.cached_state_hash = digest(self.snapshot())
        return self.cached_state_hash

    def score(self):
        if self.closed_scorecard is not None:
            return self.closed_scorecard
        result = level_score(self.configuration,
                             level_passed(self.env.observation_space, self.initial_completed),
                             self.native_action_count)
        if self.ended():
            self.closed_scorecard = result
            save_receipt(self.run_dir / self.directory / 'sublevel-score.json', result)
        return result

    def observation(self):
        obs = self.env.observation_space
        frame = public_frame(obs)
        frame['available_actions'] = self.effective_actions()
        if self.transport_feedback:
            frame['transport_feedback'] = self.transport_feedback
        for layer in frame['frame']:
            if not layer or len(layer) > 64 or any(not row or len(row) > 64 or any(not isinstance(value, int) or not 0 <= value <= 15 for value in row) for row in layer):
                raise ValueError('Official ARC-AGI-3 frame violates admitted palette/shape')
        from PIL import Image
        from arc_agi.rendering import COLOR_MAP
        import numpy as np
        colors = [tuple(bytes.fromhex(COLOR_MAP[index][1:7])) for index in range(16)]
                                                                              
                                                                          
        image = Image.fromarray(np.asarray(colors, dtype=np.uint8)[np.asarray(frame['frame'][-1], dtype=int)], 'RGB')
        image = image.resize((image.width * 6, image.height * 6), Image.Resampling.NEAREST)
        relative = self.directory / 'frames' / ('frame-%04d.png' % self.step_index)
        target = self.run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, format='PNG')
        success = level_passed(obs, self.initial_completed)
        ended = self.ended()
        terminal = {'ended': ended, 'outcome': 'success' if success else 'failure' if ended else None,
                    'reason': terminal_reason(obs, self.initial_completed, self.native_action_count, self.attempt_limit),
                    'score': self.score()['score'] if ended else None}
        return {'publicText': json.dumps(frame, separators=(',', ':'), allow_nan=False), 'frame': None,
                'previewFrame': {'path': relative.as_posix(), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'mimeType': 'image/png'},
                'stateHash': self.state_hash(), 'configurationHash': self.configuration['configurationHash'], 'reward': None,
                'info': {'submittedActions': self.step_index, 'sourceCommands': self.source_command_count,
                         'sourceCommandsRemaining': max(0, self.attempt_limit - self.native_action_count), 'nativeActions': self.native_action_count,
                         'levelIndex': self.configuration['levelIndex'], 'actionBudget': self.attempt_limit,
                         'rejectedAttempts': self.rejected_attempts, 'resets': self.reset_count,
                         'gameOvers': self.game_over_count, 'nativeStateHash': self.native_state_hash(),
                         'lastAttemptAccepted': None if self.step_index == 0 else self.transport_feedback is None,
                         'levelsCompleted': obs.levels_completed, 'winLevels': obs.win_levels},
                'instance': {'caseId': self.configuration['id'], 'gameId': self.configuration['gameId']}, 'terminal': terminal}

    def effective_actions(self):
        obs = self.env.observation_space
        actions = available_actions(obs)
        if obs.state.name != "GAME_OVER" and (self.native_action_count == 0 or self.previous_action == "RESET"):
            actions = [a for a in actions if a != 0]
        return actions

    def execute(self, action):
        from arcengine import GameAction
        if not isinstance(action, dict) or action.get('action') not in ['RESET'] + ['ACTION' + str(i) for i in range(1, 8)]:
            raise ValueError('Malformed ARC-AGI-3 public action')
        expected_keys = {'action', 'x', 'y'} if action['action'] == 'ACTION6' else {'action'}
        if set(action) != expected_keys or any(not isinstance(action[key], int) or isinstance(action[key], bool) or not 0 <= action[key] <= 63 for key in expected_keys - {'action'}):
            raise ValueError('Malformed ARC-AGI-3 coordinate action')
        native = GameAction.from_name(action['action'])
        if native.value not in self.effective_actions():
            return self.reject(action, 'action_not_available', 'Rejected by the admitted available_actions gate. The native game was not called and its last response is unchanged.')
        obs = self.env.step(native, data={key: action[key] for key in expected_keys - {'action'}}, reasoning=None)
        if obs is None:
            raise ValueError('Official ARC-AGI-3 action failed')
        self.step_index += 1
        self.source_command_count += 1
                                                                        
                                                                               
        self.native_action_count += 1
        self.previous_action = action["action"]
        if native.value == 0:
            self.reset_count += 1
            if obs.full_reset:
                                                                                
                                                                              
                                                                          
                                                     
                select_level(self.env, self.configuration)
                obs = self.env.observation_space
        if obs.state.name == 'GAME_OVER':
            self.game_over_count += 1
        self.transport_feedback = None
        self.cached_native = None
        self.cached_native_hash = None
        self.cached_snapshot = None
        self.cached_state_hash = None
        return self.observation()

    def reject(self, action, code, message):
                                                                            
                                                                          
                                                                              
        self.step_index += 1
        self.rejected_attempts += 1
        self.transport_feedback = {'accepted': False, 'code': code, 'message': message,
                                   'requested_action': action, 'available_actions': self.effective_actions()}
        self.cached_snapshot = None
        self.cached_state_hash = None
        return self.observation()

    def step(self, command):
        if self.ended() or command.get('expectedStep') != self.step_index:
            raise ValueError('ARC-AGI-3 episode ended or step index differs')
        return self.execute(command['action'])


def main():
    go_offline()
    bridge = None
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            with contextlib.redirect_stdout(sys.stderr):
                if request['command'] == 'init':
                    bridge = Bridge()
                    result = bridge.init(request)
                elif request['command'] == 'step':
                    if not bridge:
                        raise ValueError('ARC-AGI-3 environment is not initialized')
                    result = bridge.step(request)
                elif request['command'] == 'close':
                    result = {'closed': True}
                else:
                    raise ValueError('Unknown ARC-AGI-3 worker command')
            print(json.dumps({'id': request['id'], 'ok': True, 'result': result}, allow_nan=False), flush=True)
            if request['command'] == 'close':
                break
        except Exception as error:
            print(json.dumps({'id': request.get('id'), 'ok': False, 'message': str(error)}), flush=True)


if __name__ == '__main__':
    main()
