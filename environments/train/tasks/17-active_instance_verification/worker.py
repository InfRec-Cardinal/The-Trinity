#!/usr/bin/env python3
                                                                                                            

                                                                                                          
                                                                                                            
                                                                                                          
                                                                                                     
   
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
SOURCE = Path(os.environ['PINVERIFY_SOURCE']).resolve()
DATA = Path(os.environ['PINVERIFY_DATA']).resolve()
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

MAX_STEPS = 6
SECTORS = 6
SEED = 42
VIEW_PRIORITY = 'far'
ACTIONS = {'nav_front': {'decision': 'Unsure', 'nav_rel': 'front'},
           'nav_front_left': {'decision': 'Unsure', 'nav_rel': 'front-left'},
           'nav_back_left': {'decision': 'Unsure', 'nav_rel': 'back-left'},
           'nav_back': {'decision': 'Unsure', 'nav_rel': 'back'},
           'nav_back_right': {'decision': 'Unsure', 'nav_rel': 'back-right'},
           'nav_front_right': {'decision': 'Unsure', 'nav_rel': 'front-right'},
           'decide_yes': {'decision': 'Yes'}, 'decide_no': {'decision': 'No'}}

_NATIVE = None
_DATA_CACHE = None


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def native_env_module():
    global _NATIVE
    if _NATIVE is None:
        spec = importlib.util.spec_from_file_location('pinverify_native_env', SOURCE / 'pver/envs/env.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['pinverify_native_env'] = module
        spec.loader.exec_module(module)
        _NATIVE = module
    return _NATIVE


def load_data():
    global _DATA_CACHE
    if _DATA_CACHE is None:
        index = [json.loads(line) for line in (DATA / 'val/pv_index_all.jsonl').read_text().splitlines() if line]
        descriptions = json.loads((DATA / 'object_descriptions_with_category.json').read_text())
        categories = json.loads((DATA / 'category_cache.json').read_text())
        _DATA_CACHE = (index, descriptions, categories)
    return _DATA_CACHE


def create(configuration):
    original, descriptions, categories = load_data()
                                                                                                       
                                                   
    dataset = list(original)
    dataset[configuration['rowIndex']] = copy.deepcopy(original[configuration['rowIndex']])
    row = dataset[configuration['rowIndex']]
    query = descriptions[row['query_object_id']]['descriptions']
    if len(query) != 3 or not all(isinstance(item, str) and item for item in query):
        raise ValueError('Original query does not have three public descriptions')
    category = categories[row['query_object_id']]['pred_coarse']
    env = native_env_module().PInVerifyEnv(dataset, max_steps=MAX_STEPS, sectors=SECTORS,
                                           data_root=str(DATA), view_priority=VIEW_PRIORITY, seed=SEED)
    obs = env.reset(configuration['rowIndex'])
    return env, obs, query, category


class Episode:
    def __init__(self, run_dir, episode_path, configuration):
        self.run_dir = Path(run_dir).resolve()
        self.directory = Path(episode_path)
        if self.directory.is_absolute() or '..' in self.directory.parts:
            raise ValueError('Unsafe PInVerify episode path')
        self.configuration = configuration
        self.env, self.obs, self.query, self.category = create(configuration)
        self.done, self.decision, self.info, self.history = False, None, {}, []

    def snapshot(self):
        return {'configurationId': self.configuration['id'], 'rowIndex': self.configuration['rowIndex'],
                'captureIndex': self.env.current_obs_idx, 'currentStep': self.env.current_step,
                'visited': sorted(self.env.visited_sectors), 'decision': self.decision, 'done': self.done,
                'nativeInfo': self.info, 'history': self.history,
                'navigationFailed': self.env._last_nav_failed, 'failedDirection': self.env._last_nav_dir,
                'navDebugLog': self.env.nav_debug_log}

    def result(self):
        predicted = {'Yes': 1, 'No': 0}.get(self.decision, -1)
        correct = predicted != -1 and predicted == self.env.ep_data['label']
        return {'ended': self.done, 'outcome': 'success' if self.done and correct else 'failure' if self.done else None,
                'reason': 'correct_commitment' if self.done and correct else 'wrong_commitment' if self.done and predicted != -1
                    else 'native_six_step_no_commitment' if self.done else None,
                'score': int(correct) if self.done else None}

    def observation(self):
        relative = self.directory / 'frames' / ('frame-%04d.png' % self.env.current_step)
        target = self.run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.obs['rgb_path'], target)
        frame = {'path': relative.as_posix(), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'mimeType': 'image/png'}
        warning = 'unreachable_or_already_visited_sector' if self.info.get('navigation_failed') else 'trap_view' if self.info.get('trap_view') else None
        public = {'queryDescriptions': self.query, 'matchedCategory': self.category,
                  'currentSector': self.obs['current_sector'], 'visitedSectors': sorted(self.env.visited_sectors),
                  'remainingBudget': MAX_STEPS - self.env.current_step, 'availableSectors': self.obs['available_sectors'],
                  'visibilityWarning': warning, 'failedDirection': self.obs['failed_direction'],
                  'previousActions': [row['action'] for row in self.history]}
        return {'publicText': 'Verify whether the candidate in the current RGB frame is the instance described by all three query descriptions.\n'
                  + json.dumps(public, ensure_ascii=True, sort_keys=True),
                'step': self.env.current_step,
                'frame': frame, 'previewFrame': frame, 'stateHash': digest(self.snapshot()),
                'configurationHash': self.configuration['configurationHash'], 'reward': 0.0,
                'info': {'numSteps': self.env.current_step, 'navigationFailed': bool(self.info.get('navigation_failed')),
                         'trapView': bool(self.info.get('trap_view')), 'decision': self.decision,
                         'visibilityWarning': warning},
                'instance': {'caseId': self.configuration['id']}, 'terminal': self.result()}

    def step(self, action):
        if self.done:
            raise ValueError('PInVerify episode has already ended')
        if not isinstance(action, dict) or set(action) != {'action'} or action['action'] not in ACTIONS:
            raise ValueError('Malformed PInVerify public action')
        self.obs, reward, self.done, self.info = self.env.step(copy.deepcopy(ACTIONS[action['action']]))
        self.decision = self.info['decision']
        self.history.append({'index': self.env.current_step - 1, 'action': action,
                             'nativeInfo': self.info, 'captureIndex': self.env.current_obs_idx,
                             'currentSector': self.obs['current_sector']})
        return self.observation()


def aggregate_official(episodes):
    rows, row_indices = [], []
    for record in episodes:
        env, observation, query, category = create(record['configuration'])
        decisions, traps, unreachable, correct, done = None, 0, 0, False, False
        for saved in record['steps']:
            if done or saved['action'].get('action') not in ACTIONS:
                raise ValueError('Invalid or post-terminal source scoring action')
            observation, reward, done, info = env.step(copy.deepcopy(ACTIONS[saved['action']['action']]))
            decisions = info['decision']
            traps += int(bool(info.get('trap_view')))
            unreachable += int(bool(info.get('navigation_failed')))
            predicted = {'Yes': 1, 'No': 0}.get(decisions, -1)
            correct = predicted != -1 and predicted == env.ep_data['label']
        if not done:
            raise ValueError('Official metrics require completed source episodes')
        row = env.ep_data
        row_indices.append(record['configuration']['rowIndex'])
        rows.append({'episode_id': row['episode'], 'scene_id': row['scene'], 'target_object_category': row['target_object_category'],
                     'label': row['label'], 'pair_type': row['pair_type'], 'prediction': decisions,
                     'steps': env.current_step, 'is_correct': correct, 'nav_fail_unreachable': unreachable,
                     'nav_fail_trap': traps, 'nav_failures': unreachable + traps,
                     'effective_views': env.current_step - unreachable - traps, 'first_view_prediction': decisions})
    source = SOURCE / 'pver/eval/metrics.py'
    spec = importlib.util.spec_from_file_location('pinverify_official_metrics', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    metrics = module.calculate_metrics(rows)
    full = len(rows) == 3000 and len(set(row_indices)) == 3000
    return {'officialMetrics': metrics, 'sourceScorer': 'unchanged pver.eval.metrics.calculate_metrics',
            'sourceScorerSHA256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'completedSourceEpisodes': len(rows), 'distinctOfficialIndexRows': len(set(row_indices)),
            'officialPaperIndexCount': 3000, 'completeOfficialPaperProtocol': full,
            'evaluationScope': 'all3000_original_rows_exactly_once' if full else 'subset_of_published_rows',
            'unsureAsNegative': False, 'referencePolicyDinoBaselineClaimed': False}


def main():
    episode = None
    for line in sys.stdin:
        request = {}
        command = None
        try:
            request = json.loads(line)
            command = request['command']
            with contextlib.redirect_stdout(sys.stderr):
                if command == 'init':
                    episode = Episode(request['runDir'], request['episodePath'], request['configuration'])
                    result = episode.observation()
                elif command == 'step':
                    if episode is None:
                        raise ValueError('PInVerify environment is not initialized')
                    result = episode.step(request['action'])
                elif command == 'aggregate_official':
                    result = aggregate_official(request['episodes'])
                elif command == 'close':
                    result = {'closed': True}
                else:
                    raise ValueError('Unknown PInVerify worker command')
            print(json.dumps({'id': request['id'], 'ok': True, 'result': result}, allow_nan=False), flush=True)
            if command == 'close':
                break
        except Exception as error:
            print(json.dumps({'id': request.get('id'), 'ok': False, 'message': str(error)}), flush=True)


if __name__ == '__main__':
    main()
