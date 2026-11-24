#!/usr/bin/env python3
                                                                                                       

                                                                                                                       
                                                                                                                    
                                                                                                               
                                                                                                          
                                                 
                                                                                                       
                                                                                                                   
                                                                                                                  
                                                        
                                                                             

                                                                                                     
                                                                       
                                                                              
                                                                                         
                                                                                                  
                                                                                                           
                                    
   
import copy
import hashlib
import importlib
import json
import os
import queue
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'official' / 'AdaPlanBench'
META = ROOT / 'adapters' / 'adaplanbench-bridge-v1-model-metadata.yaml'
AGENT = 'h0-player'
sys.path.insert(0, str(SRC))

official_run = importlib.import_module('env.run')
official_runner = importlib.import_module('env.run_utils.runner')
official_judger = importlib.import_module('env.run_utils.judgers.HousingJudger')
official_merge = importlib.import_module('env.run_utils.run_merge')
official_eval = importlib.import_module('env.eval_main_table')
for module in (official_run, official_runner, official_judger, official_merge, official_eval):
    origin = Path(module.__file__).resolve()
    if SRC not in origin.parents:
        raise SystemExit(f'official module resolved outside the candidate: {origin}')


class Host:
    pass                                                                                                             

    def __init__(self):
        self.events = queue.Queue()
        self.turns_answered = 0
        self.resume_pass = 0
        self.lock = threading.Lock()

    def ask(self, kind, payload):
        slot = {'kind': kind, 'payload': payload, 'reply': None, 'done': threading.Event()}
        self.events.put(slot)
        slot['done'].wait()
        if isinstance(slot['reply'], BaseException):
            raise slot['reply']
        return slot['reply']


HOST = Host()
RUNNER = [None]


def bridged_request(*, provider=None, base_url='', api_key=None, model_id='', model_name=None, reasoning_effort=None,
                    prompt=None, messages=None, temperature=0.0, max_tokens=None, timeout_s=120, max_retries=2, retry_backoff_s=2.0):
    pass                                                                                                  
    caller = sys._getframe(1)
    if model_name == AGENT:
        if messages is None:
            raise RuntimeError('agent call without messages')
                                                                                                             
        return HOST.ask('agent', {'messages': list(messages), 'snapshot': boundary_snapshot(RUNNER[0])})
    if caller.f_code.co_name == '_call_and_parse_one_model':
        stage = {'env': 'tools', 'prefs': 'prefs', 'rubrics': 'rubrics'}[caller.f_locals['parse_kind']]
        role = 'judge'
    elif caller.f_code.co_name == 'generate_user_feedback':
        stage, role = 'user_feedback', 'npc'
    else:
        raise RuntimeError(f'environment model call from an unrouted official caller: {caller.f_code.co_name}')
    if prompt is None or messages is not None:
        raise RuntimeError('environment model calls are single user prompts in the official harness')
    with HOST.lock:
        turn, resume_pass = HOST.turns_answered, HOST.resume_pass
    request = {'stage': stage, 'role': role, 'model': model_id, 'temperature': float(temperature),
               'maxTokens': int(max_tokens), 'turns': [{'role': 'user', 'text': str(prompt)}], 'turn': turn, 'resumePass': resume_pass}
    reply = HOST.ask('model', request)
    return str(reply)


def refuse_merge(**_kwargs):
    raise RuntimeError('runtime merge/check is not part of this candidate: the official pre-merged profile must match')


official_runner.openai_chat_request = bridged_request
official_judger.openai_chat_request = bridged_request
official_merge.openai_chat_request = refuse_merge


def build_runner(instance, scratch):
    routes = instance['routes']
    argv = ['--config', str(SRC / 'env' / 'run_config.yaml'), '--out', str(scratch), '--model', AGENT,
            '--judge_LLM_list', routes['tools'], '--tools_judge_LLM_list', routes['tools'], '--prefs_judge_LLM_list', routes['prefs'],
            '--rubrics_judge_LLM_list', ','.join(routes['rubrics']), '--gen_LLM', routes['userSimulator'],
            '--merge_LLM', routes['tools'], '--check_LLM', routes['tools'],
            '--ban_iterative_sample_num', str(instance['banIterativeSampleNum']), '--max_turns', str(instance['maxTurns']),
            '--model_metadata', str(META), '--dotenv', str(scratch / 'no-dotenv')]
    args = official_run.resolve_args(official_run.build_arg_parser().parse_args(argv))
    official_run.validate_args(args)
    cfg = official_run._build_runner_config(args)
    runner = official_runner.Runner(cfg)
    runner.dataworker.validate_query_path(None)
    entries = runner.dataworker.load_queries()
    entry = entries[int(instance['queryIndex'])]
    if entry['query_id'] != instance['queryId']:
        raise RuntimeError('official query order changed')
    check = runner.merger.check_merge_metadata([entry])
    if not check.matched:
        raise RuntimeError('the official pre-merged constraint profile for this ban_iterative_sample_num is missing')
    profile = runner.merger.select_existing_profiles([entry], int(check.matched_pool_index))[0]
    profile = runner._apply_ban_scope_to_profile(profile)
    query_entry = {'query_id': str(entry['query_id']), 'query': str(entry['query']), '_runtime_env_profile': profile}
    return runner, cfg, query_entry, int(check.matched_pool_index)


def boundary_snapshot(runner):
    pass                                                                                                                 
    frame = sys._getframe(0)
    while frame is not None and frame.f_code.co_name != '_run_single_query':
        frame = frame.f_back
    if frame is None:
        return None
    local = frame.f_locals
    entry = copy.deepcopy(local['existing'])
    trajectory = copy.deepcopy(local['trajectory'])
    if trajectory and (trajectory[-1].get('agent_side') or {}).get('status') != 'success':
        trajectory = trajectory[:-1]                                                        
    runner._persist_query_progress(entry, tracker=local['tracker'], trajectory=trajectory,
                                   no_new_violation_streak=int(local['no_new_violation_streak']))
    return entry


def components(entry, cfg):
    q = entry
    result = q.get('result') or {}
    trajectory = q.get('trajectory') or []
    last = trajectory[-1] if trajectory else {}
    rubrics = (((last.get('judge_side') or {}).get('rubrics') or {}).get('final_result')) or {}
    return {
        'officialStatus': result.get('status'), 'officialStopReason': result.get('stop_reason'),
        'officialValidQuery': bool(official_eval.get_query_status(q) in official_eval._VALID_RESULT_STATUSES and not official_eval.is_judge_error(q)),
        'accuracy': 1 if official_eval.is_success_query(q) else 0,
        'turns': official_eval.get_turn_count(q),
        'firstAttemptSuccess': bool(official_eval.is_success_query(q) and official_eval.get_turn_count(q) == 1),
        'earlyStopped': str(result.get('stop_reason') or '').startswith('early_stop'),
        'repeatedToolViolations': official_eval.get_dimension_counter_total(q, 'tools'),
        'repeatedPrefViolations': official_eval.get_dimension_counter_total(q, 'prefs'),
        'terminalRubricScores': rubrics.get('scores_by_rubric'), 'terminalRubricPassed': rubrics.get('passed'),
                                                                                                          
        'terminalViolatedToolCount': len(last.get('violated_env_items') or []), 'terminalViolatedPrefCount': len(last.get('violated_pref_items') or []),
        'rubricsPassThreshold': cfg.rubrics_pass_threshold, 'rubricsPassMode': cfg.rubrics_pass_mode,
    }


def outcome(entry, cfg):
    result = entry.get('result') or {}
    status, reason = result.get('status'), str(result.get('stop_reason') or '')
    comp = components(entry, cfg)
    if status == 'success':
        return {'ended': True, 'outcome': 'success', 'reason': 'all_judges_pass', 'score': 1, 'components': comp}
    if status in ('stopped', 'failed'):
        return {'ended': True, 'outcome': 'failure', 'reason': reason, 'score': 0, 'components': comp}
    if status == 'error' and reason == 'agent_error':
        return {'ended': True, 'outcome': 'failure', 'reason': 'agent_error', 'score': 0, 'components': comp}
    if status == 'error':
        return {'ended': True, 'outcome': 'failure', 'reason': f'{reason}_unresolved_after_official_resumes', 'score': 0, 'components': comp}
    raise RuntimeError(f'unexpected official query status {status!r}')


def terminal_text(term):
    c = term['components']
    lines = ['[AdaPlanBench episode ended]', f"Official status: {c['officialStatus']} ({c['officialStopReason']}).",
             f"Turns used: {c['turns']}. Outcome: {term['outcome']}."]
    return '\n'.join(lines)


def main():
    request_fifo, response_fifo = sys.argv[1], sys.argv[2]
    rin = open(request_fifo, 'r', encoding='utf-8')
    rout = open(response_fifo, 'w', encoding='utf-8')

    def emit(value):
        rout.write(json.dumps(value, ensure_ascii=False) + '\n')
        rout.flush()

    first = rin.readline()
    if not first:
        return
    try:
        instance = json.loads(first)['instance']
        scratch = Path(os.environ.get('TMPDIR', '/tmp')) / f'adaplanbench-bridge-v1-{os.getpid()}'
        runner, cfg, query_entry, pool_index = build_runner(instance, scratch)
        RUNNER[0] = runner
    except BaseException as error:                  
        emit({'ok': False, 'message': f'{type(error).__name__}: {error}'[:2000]})
        return

    finished = {}

    def drive():
        qid = query_entry['query_id']
        existing = None
        try:
            for resume_pass in range(1 + int(cfg.max_resume_attempts)):
                with HOST.lock:
                    HOST.resume_pass = resume_pass
                if existing is not None:
                    runner._all_results_by_id[qid] = existing
                existing = runner._run_single_query(query_entry)
                result = existing.get('result') or {}
                if result.get('status') not in runner._RERUN_STATUSES or result.get('stop_reason') == 'agent_error':
                    break
            finished['entry'] = existing
        except BaseException as error:
            finished['error'] = f'{type(error).__name__}: {error}'
        HOST.events.put({'kind': 'finished'})

    threading.Thread(target=drive, daemon=True).start()
    pending = None

    def advance():
        pass                                                                                                   
        nonlocal pending
        slot = HOST.events.get()
        if slot['kind'] == 'finished':
            if 'error' in finished:
                emit({'ok': False, 'message': finished['error'][:2000]})
                return
            entry = finished['entry']
            term = outcome(entry, cfg)
            emit({'ok': True, 'response': {
                'text': terminal_text(term), 'reward': term['score'], 'info': {'turn': HOST.turns_answered},
                'terminal': {'ended': True, 'outcome': term['outcome'], 'reason': term['reason'], 'score': term['score'], 'components': term['components']},
                'state': {'turn': HOST.turns_answered, 'officialStatus': entry['result']['status'], 'officialStopReason': entry['result']['stop_reason'],
                          'profilePoolIndex': pool_index},
                'official': entry}})
            pending = None
            return
        if slot['kind'] == 'agent':
            messages = slot['payload']['messages']
            snapshot = slot['payload']['snapshot']
            text = str(messages[-1]['content'])
            emit({'ok': True, 'response': {
                'text': text, 'reward': 0, 'info': {'turn': HOST.turns_answered + 1},
                'terminal': {'ended': False, 'outcome': None, 'reason': None},
                'state': {'turn': HOST.turns_answered, 'nextTurn': HOST.turns_answered + 1, 'profilePoolIndex': pool_index},
                'official': snapshot}})
            pending = slot
            return
        if slot['kind'] == 'model':
            emit({'ok': True, 'modelRequest': slot['payload']})
            pending = slot
            return
        emit({'ok': False, 'message': 'unknown official event'})

    advance()
    for line in rin:
        try:
            message = json.loads(line)
            if pending is None:
                emit({'ok': False, 'message': 'no outstanding official request'})
                continue
            if 'action' in message:
                if pending['kind'] != 'agent':
                    emit({'ok': False, 'message': 'an environment-model reply is outstanding, not a Player action'})
                    continue
                plan = message['action'].get('plan')
                if not isinstance(plan, str):
                    emit({'ok': False, 'message': 'plan must be a string'})
                    continue
                slot, pending = pending, None
                with HOST.lock:
                    HOST.turns_answered += 1
                slot['reply'] = plan
                slot['done'].set()
                advance()
            elif 'modelReply' in message:
                if pending['kind'] != 'model':
                    emit({'ok': False, 'message': 'a Player action is outstanding, not a model reply'})
                    continue
                record = message['modelReply']
                if not isinstance(record, dict) or not isinstance(record.get('text'), str):
                    emit({'ok': False, 'message': 'model reply text missing'})
                    continue
                slot, pending = pending, None
                slot['reply'] = record['text']
                slot['done'].set()
                advance()
            else:
                emit({'ok': False, 'message': 'unknown operation'})
        except BaseException as error:
            emit({'ok': False, 'message': f'{type(error).__name__}: {error}'[:2000]})


if __name__ == '__main__':
    main()
