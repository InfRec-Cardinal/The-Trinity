#!/usr/bin/env python3
                                                                                                                            
                                                                                                                             
                                                                                                

                                                                                                                                             
                                                               

                                                                                                                      
                                                                                                                       
                                                                                                                     
                                                                                                                 
                                                                                                                   
                                                                                                         
                                                                                                                  
                                                                                                                        
                                                                                                                           
                                                                                                                      
                                                                                                                    
                                                                                      
   
import ast
import contextlib
import io
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

warnings.filterwarnings('ignore')
HERE = Path(__file__).resolve().parent                                
ROOT = HERE.parents[1]                       
SRC = ROOT / 'vendor/discoverphysics'                                          
VENV = Path(sys.prefix).resolve()                                                                            
NORMALIZED_MSE_PASS = 0.1                                                  
EXPLANATION_PASS = 0.9                                                                                             


class JudgeProtocolError(BaseException):
    pass                                                                                                                  
                                                                                                                        


class JudgeChannel:
    pass                                                                                                                   

    def __init__(self, source=None, replies=None):
        self.source, self.replies, self.used = source, list(replies or []), []

    def ask(self, request):
        if self.source is None:
            if not self.replies:
                raise JudgeProtocolError('No recorded judge reply was supplied for the explanation judge request')
            record = self.replies.pop(0)
        else:
            self.source.emit({'ok': True, 'judgeRequest': request})
            message = read_action(self.source.requests, self.source.idle)
            if not isinstance(message, dict) or set(message) != {'judgeReply'}:
                raise JudgeProtocolError('Expected exactly one judgeReply line after a judgeRequest')
            record = message['judgeReply']
        if not isinstance(record, dict) or not isinstance(record.get('text'), str) or record.get('model') != request['model']:
            raise JudgeProtocolError('Malformed judge reply record')
        self.used.append(record)
        return record['text']


SANDBOX_SCRIPT = HERE / 'discoverphysics-sandbox.py'
LAW_CALL_TIMEOUT_S = 12.0                                                                                                    
COMPILE_TIMEOUT_S = 60.0                                                                           
MEMORY_CAP_BYTES = 2 << 30                                                                                     
WATCHDOG_INTERVAL_S = 0.02


def _symlinks_on(path, seen=None):
    pass                                                                                                                    
    seen = [] if seen is None else seen
    path = Path(path); current = Path(path.parts[0])
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink():
            seen.append(current)
            target = Path(os.path.join(os.path.dirname(current), os.readlink(current)))
            return _symlinks_on(target / path.relative_to(current), seen)
    return seen


def sandbox_command(policy_path, scratch, python, script, args):
    pass                                                                  
                                                                                 
                                                                                                                         
    import shutil
    if sys.platform == "darwin":
        return ["/usr/bin/sandbox-exec", "-f", str(policy_path), python, "-I", "-B", script, *args]
    if sys.platform.startswith("linux"):
        bwrap = shutil.which("bwrap")
        if not bwrap:
            raise RuntimeError("bubblewrap (bwrap) is required on Linux: sudo apt install bubblewrap")
        runtime, venv = str(Path(sys.base_prefix).resolve()), str(Path(sys.prefix).resolve())
        script_dir = str(Path(script).resolve().parent)
        cmd = [bwrap, "--die-with-parent", "--unshare-net", "--unshare-pid", "--new-session",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
               "--ro-bind", "/usr", "/usr", "--ro-bind-try", "/etc", "/etc",
               "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
               "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
               "--ro-bind", runtime, runtime, "--ro-bind", venv, venv, "--ro-bind", script_dir, script_dir,
               "--bind", str(scratch), str(scratch), "--chdir", str(scratch)]
                                                                                 
                                                                             
                                                                               
        aliases = []
        if str(Path(sys.prefix)) != venv:
            aliases += ["--ro-bind", venv, str(Path(sys.prefix))]
        for link in _symlinks_on(Path(python)):
            target = link.resolve()
            if target == Path(runtime):
                aliases += ["--ro-bind", runtime, str(link)]
        return [*cmd, *aliases, python, "-I", "-B", script, *args]
    raise RuntimeError(f"No candidate sandbox for platform {sys.platform}")


def sandbox_profile(scratch):
    pass                                                                                                                 
                                                                                                                                     
                                                                                                                          
                                                                                                                                 
                                                                                                                                
                                                                                                  
    q = lambda p: json.dumps(str(p))
    python = Path(sys.executable)
    venv, runtime = Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()
    links = _symlinks_on(python)
    readable = [runtime, venv, scratch]
    ancestors = set()
    for p in readable + [SANDBOX_SCRIPT, python, python.resolve()] + links:
        p = Path(p)
        while True:
            ancestors.add(str(p))
            if p.parent == p:
                break
            p = p.parent
    return '\n'.join([
        '(version 1)', '(deny default)',
        f'(allow process-exec* (literal {q(python)}) (literal {q(python.resolve())}))',
        '(allow process-info* (target self))', '(allow signal (target self))',
                                                                                                                       
                                                                                                                                  
                                                                                                                                 
        SYSCTL_ALLOWLIST,
        f'(allow file-map-executable (subpath {q(runtime)}) (subpath {q(venv)}) (subpath "/usr/lib") (subpath "/System") (subpath "/private/var/db/dyld"))',
        '(allow file-read* (literal "/") (subpath "/usr/lib") (subpath "/usr/share") (subpath "/System") (subpath "/private/var/db/dyld")'
        ' (subpath "/private/var/db/timezone") (literal "/private/etc/localtime") (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))',
        '(allow file-write-data (literal "/dev/null"))',
        '(allow file-read* ' + ' '.join(f'(subpath {q(r)})' for r in readable) + f' (literal {q(SANDBOX_SCRIPT)}) '
        + ' '.join(f'(literal {q(l)})' for l in links) + ')',
        '(allow file-read-metadata ' + ' '.join(f'(literal {q(a)})' for a in sorted(ancestors)) + ')',
        f'(allow file-write* (subpath {q(scratch)}))',
    ])


SYSCTL_ALLOWLIST = ('(allow sysctl-read (sysctl-name "kern.ostype") (sysctl-name "kern.osrelease") (sysctl-name "kern.version")'
                    ' (sysctl-name "kern.osversion") (sysctl-name "kern.osproductversion") (sysctl-name "kern.hostname") (sysctl-name "kern.argmax")'
                    ' (sysctl-name "kern.boottime") (sysctl-name "kern.maxfilesperproc") (sysctl-name "kern.secure_kernel")'
                    ' (sysctl-name "kern.osvariant_status") (sysctl-name-prefix "hw.") (sysctl-name-prefix "machdep.cpu.")'
                    ' (sysctl-name "machdep.ptrauth_enabled") (sysctl-name "vm.pagesize") (sysctl-name "sysctl.proc_native")'
                    ' (sysctl-name "sysctl.proc_translated"))')


def phys_footprint(pid):
    pass                                                                                                                 
    if sys.platform.startswith("linux"):
        try:
            for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except (FileNotFoundError, ProcessLookupError):
            return None
        return None
    import ctypes
    global _LIBPROC
    try:
        _LIBPROC
    except NameError:
        _LIBPROC = ctypes.CDLL('/usr/lib/libproc.dylib')
    buf = (ctypes.c_uint64 * 12)()                                                                             
    if _LIBPROC.proc_pid_rusage(int(pid), 0, ctypes.byref(buf)) != 0:
        return None
    return int(buf[2 + 7])


class SandboxLimit(Exception):
    pass


class SandboxedLaw:
    pass                                                                                                             
                                                                                                                          
    registry = {}

    def __init__(self, source, scratch, policy_dir):
        self.source, self.scratch, self.policy_dir, self.proc = source, scratch, policy_dir, None

    @classmethod
    def get(cls, source, scratch, policy_dir):
        if source not in cls.registry:
            cls.registry[source] = cls(source, scratch, policy_dir)
        return cls.registry[source]

    def _spawn(self):
        import subprocess
        self.scratch.mkdir(parents=True, exist_ok=True)
        policy = self.policy_dir / 'policy.sb'                                          
        policy.write_text(sandbox_profile(self.scratch.resolve()))
        self.proc = subprocess.Popen(sandbox_command(policy, self.scratch.resolve(), sys.executable, str(SANDBOX_SCRIPT), []),
                                     cwd=str(self.scratch), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     env={'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '1',
                                          'OPENBLAS_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1', 'PYTHONHASHSEED': '0'}, text=True)
        self.compiled = self._raw({'op': 'compile', 'source': self.source}, COMPILE_TIMEOUT_S)

    def _raw(self, payload, timeout):
        import select
        import time
        try:
            self.proc.stdin.write(json.dumps(payload, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o)) + '\n')
            self.proc.stdin.flush()
            deadline = time.monotonic() + timeout
            while True:
                ready, _, _ = select.select([self.proc.stdout], [], [], WATCHDOG_INTERVAL_S)
                if ready:
                    break
                footprint = phys_footprint(self.proc.pid)
                if footprint is not None and footprint > MEMORY_CAP_BYTES:
                    raise SandboxLimit(f'discovered_law sandbox exceeded the {MEMORY_CAP_BYTES >> 30} GiB memory cap and was stopped')
                if self.proc.poll() is not None:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError(f'discovered_law sandbox gave no answer within {timeout:g}s')
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError('discovered_law sandbox process ended without an answer')
            return json.loads(line)
        except BaseException:
            self.kill()
            raise

    def kill(self):
        if self.proc is not None:
            try:
                self.proc.kill(); self.proc.wait(timeout=5)
            except Exception:
                pass
        self.proc = None

    def request(self, payload, timeout=LAW_CALL_TIMEOUT_S):
        if self.proc is None or self.proc.poll() is not None:
            self._spawn()
        return self._raw(payload, timeout)

    def compile_info(self):
        if self.proc is None or self.proc.poll() is not None:
            self._spawn()
        return self.compiled


def install_sandbox(ev, mse_fitting, scratch, policy_dir):
    pass                                                                                                                      
    def compile_law(source):
        source = ev.clean_law_source(source)
        law = SandboxedLaw.get(source, scratch, policy_dir)
        info = law.compile_info()
        if not info.get('ok'):
            raise ValueError(info.get('error', 'compile failed'))
        if not info.get('law'):
            raise ValueError('Source does not define a function named `discovered_law`')
        def call(*args, **kwargs):
            reply = law.request({'op': 'law', 'args': list(args), 'kwargs': kwargs})
            if not reply.get('ok'):
                raise ValueError(reply.get('error'))
            return reply['value']
        return ev._wrap_with_timeout(call)

    def compile_fit_parameters(source):
        source = ev.clean_law_source(source)
        law = SandboxedLaw.get(source, scratch, policy_dir)
        try:
            info = law.compile_info()
        except Exception:
            return None
        if not info.get('ok') or not info.get('fit'):
            return None
        def fit():
            reply = law.request({'op': 'fit_parameters'})
            if not reply.get('ok'):
                raise ValueError(reply.get('error'))
            return reply['value']
        return fit

    for module in (ev, mse_fitting):
        module._compile_law = compile_law
        module._compile_fit_parameters = compile_fit_parameters


def finite(value):
    pass                                                                                            
    import math
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite(v) for v in value]
    return value


class Pending(BaseException):
    def __init__(self, text):
        super().__init__('pending')
        self.text = text


def world_vars():
    tree = ast.parse((SRC / 'scripts/run_benchmark.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, 'id', None) == '_WORLD_VARS':
            return ast.literal_eval(node.value)
    raise ValueError('Pinned _WORLD_VARS not found')


def run(instance, actions, source=None, judge_replies=None):
    pass                                                                                                           
                                                                                                           
    os.chdir(SRC)                                                                     
    sys.path[:0] = [str(SRC / 'ScienceAgent'), str(SRC / 'PhysicsSchool')]
    import numpy as np
    from scienceagent import llm_client
    from scienceagent.worlds import get_world
    from scienceagent.agent import DiscoveryAgent
    from scienceagent.trajectory_logger import TrajectoryLogger
    from scienceagent import evaluator as ev
    from scienceagent import mse_fitting
    import physchool, scienceagent, scipy, jax
    check_origins({'scienceagent': scienceagent, 'physchool': physchool}, SRC)
    check_origins({'numpy': np, 'scipy': scipy, 'jax': jax}, VENV)

    world_name, seed = instance['world'], instance['seed']
    variances = world_vars()
    noise_std = instance['noiseFrac'] * variances[world_name] ** 0.5
    world = get_world(world_name, engine='nbody', noise_std=noise_std, noise_seed=seed)
    executor = world['executor']
    queue, used = list(actions), 0
    shown = {'count': 0}

    judge_channel = JudgeChannel(source, judge_replies)

    def complete(model, messages, system=None, max_tokens=4096):
        nonlocal used
        if model == instance['judgeModel']:
                                                                                                                        
                                                                                 
            return judge_channel.ask({'model': model, 'system': system, 'messages': json.loads(json.dumps(messages)),
                                      'max_tokens': max_tokens})
        if used >= len(queue):
            fresh = messages[shown['count']:]
            parts = ([f'SYSTEM PROMPT:\n{system}'] if shown['count'] == 0 else []) + [f"{m['role'].upper()}:\n{m['content']}" for m in fresh]
            text = '\n\n'.join(parts)
            if source is None:
                raise Pending(text)
            action = source.next(lambda: pending_result(text))
            if not isinstance(action, dict) or not isinstance(action.get('reply'), str) or not action['reply'].strip():
                raise ValueError('Malformed reply')
            queue.append(action)
        reply = queue[used]['reply']; used += 1
        shown['count'] = len(messages) + 1                                                  
        return reply

    llm_client.complete = complete
                                                                                                                           
                                                                                                           
    tmp = tempfile.mkdtemp(prefix='agentb-discoverphysics-')
    sandbox_dir = tempfile.mkdtemp(prefix='agentb-dp-sandbox-')
    install_sandbox(ev, mse_fitting, Path(sandbox_dir) / 'scratch', Path(tmp))
    csv_path = Path(tmp) / 'trajectory.csv'
    logger = TrajectoryLogger(world=world_name, executor=executor, csv_path=csv_path, run_id=f'agentb_run_seed{seed}')

    def ddlog():
                                                                                                                       
        return {'csvFile': 'trajectory.csv', 'csv': csv_path.read_text() if csv_path.exists() else None}
    agent = DiscoveryAgent(model='h0-player', executor=executor, mission=world['mission'], max_tokens=8192, verbose=False,
                           show_experiment_output=False, system_prompt_path=world['system_prompt'], instructions_path=world['instructions'],
                           law_stub=world['law_stub'], experiment_format=world['experiment_format'], critic=None,
                           random_experiments=False, random_generator=None, trajectory_logger=logger, no_mse=False,
                           max_rounds=instance['maxRounds'])
    def pending_result(text):
        rounds = [{k: e.get(k) for k in ('round', 'action', 'experiment_error')} for e in agent.conversation_log]
        state = {'world': world_name, 'seed': seed, 'replies': used, 'rounds': rounds, 'law': None, 'explanation': None, 'evaluation': None,
                 'trainingTrajectories': len(ev._extract_training_trajectories(agent.conversation_log))}
        info = {'replies': used, 'roundsLogged': len(agent.conversation_log), 'maxRounds': instance['maxRounds']}
        return {'ok': True, 'state': json.loads(json.dumps(state, default=str)), 'text': text, 'reward': 0, 'info': info,
                'terminal': {'ended': False, 'outcome': None, 'reason': None}, 'ddlog': ddlog()}

    pending, law, evaluation = None, None, None
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            law = agent.run()
    except Pending as p:
        pending = p
    terminal = {'ended': False, 'outcome': None, 'reason': None}
    if pending is None and used != len(queue):
        raise ValueError('Episode already ended')
    if pending is not None:
        text = pending.text
    elif law is None:
        terminal = {'ended': True, 'outcome': 'failure', 'reason': 'no_final_law', 'score': None}
        text = f"No <final_law> was submitted within {instance['maxRounds']} rounds. Episode failed."
    else:
                                                                    
        named = {'circle': ev.CircleEvaluator, 'three_species': ev.ThreeSpeciesEvaluator, 'dark_matter': ev.DarkMatterEvaluator,
                 'ether': ev.EtherEvaluator, 'hubble': ev.HubbleEvaluator}
        if world_name in named:
            evaluator = named[world_name](executor)
        elif world.get('evaluator_class') is not None:
            evaluator = world['evaluator_class'](executor)
        else:
            evaluator = ev.Evaluator(executor)
        kwargs = {'verbose': False}
        if world_name in instance['fitWorlds']:
            kwargs['training_trajectories'] = ev._extract_training_trajectories(agent.conversation_log)
        evaluated = False
        try:
            with contextlib.redirect_stdout(sink):
                result = evaluator.evaluate(law, **kwargs)
            evaluated = True
            mean_err = float(result['mean_pos_error'])
            evaluation = {'mean_pos_error': mean_err, 'max_pos_error': float(result['max_pos_error']), 'per_case': [float(x) for x in result['per_case']],
                          'repository_passed_raw_0_01': bool(result['passed']), 'fit': json.loads(json.dumps(result.get('fit'), default=str))}
        except Exception as error:                                                                                             
            mean_err = float('inf'); evaluation = {'error': f'{type(error).__name__}: {error}'}
        normalized = mean_err / variances[world_name] if np.isfinite(mean_err) else None
        evaluation['normalized_mse'] = normalized
        mse_passed = normalized is not None and normalized < NORMALIZED_MSE_PASS
        evaluation['mse_component_passed'] = mse_passed
        if instance['judgePolicy'] != 'official_judge':
            raise ValueError('Unsupported judge policy')
        judge = None
        if evaluated:
                                                                                                                      
            with contextlib.redirect_stdout(sink):
                official = ev.ExplanationJudge(judge_model=instance['judgeModel'], max_tokens=instance['judgeMaxTokens']).score(
                    agent_explanation=agent.discovered_explanation, optimal_explanation=world.get('optimal_explanation', ''),
                    rubric=world.get('explanation_rubric', ''), verbose=False)
            record = judge_channel.used[-1] if judge_channel.used else None
            score = official.get('score')
            judge = {'model': instance['judgeModel'], 'called': record is not None, 'score': score, 'rawScore': official.get('raw_score'),
                     'error': official.get('error'), 'rationale': official.get('reasoning'), 'threshold': EXPLANATION_PASS,
                     'repositoryThreshold': 0.75, 'passed': isinstance(score, (int, float)) and score >= EXPLANATION_PASS,
                     'source': record.get('source') if record else 'official_no_call', 'record': record}
        evaluation['explanation_judge'] = judge
        if not mse_passed:
            outcome, reason = 'failure', 'law_error' if normalized is None else 'normalized_mse_at_or_above_0.1'
        elif not judge['passed']:
            outcome, reason = 'failure', 'explanation_score_unavailable' if judge['score'] is None else 'explanation_score_below_0.9'
        else:
            outcome, reason = 'success', 'normalized_mse_below_0.1_and_explanation_at_least_0.9'
        components = {'normalizedMse': round(normalized, 6) if normalized is not None else None, 'mseThreshold': NORMALIZED_MSE_PASS,
                      'msePassed': mse_passed, 'explanationScore': judge['score'] if judge else None,
                      'explanationRawScore': judge['rawScore'] if judge else None, 'explanationThreshold': EXPLANATION_PASS,
                      'explanationPassed': judge['passed'] if judge else False, 'judgeModel': instance['judgeModel'],
                      'judgeSource': judge['source'] if judge else 'not_judged_law_error',
                      'judgeUsage': (judge['record'] or {}).get('usage') if judge else None}
        terminal = {'ended': True, 'outcome': outcome, 'reason': reason,
                    'score': round(normalized, 6) if normalized is not None else None, 'components': components}
        if judge is None:
            judged = 'Explanation not judged (the law could not be evaluated).'
        else:
            label = ('SYNTHETIC zero-cost verification judge (not ' + instance['judgeModel'] + ')'
                     if judge['source'] == 'synthetic_verification_judge' else instance['judgeModel'])
            judged = (f"Explanation judge ({label}): score "
                      f"{'n/a (' + str(judge['error']) + ')' if judge['score'] is None else format(judge['score'], '.2f')} (threshold >= 0.9).")
        text = (f"Final law evaluated on held-out noise-free test trajectories: normalized MSE = "
                f"{'n/a (law error)' if normalized is None else f'{normalized:.4g}'} (threshold < 0.1). {judged} "
                f"{'Episode passed.' if outcome == 'success' else 'Episode failed.'}")
    rounds = [{k: e.get(k) for k in ('round', 'action', 'experiment_error')} for e in agent.conversation_log]
    state = {'world': world_name, 'seed': seed, 'replies': used, 'rounds': rounds, 'law': law, 'explanation': agent.discovered_explanation,
             'evaluation': evaluation, 'trainingTrajectories': len(ev._extract_training_trajectories(agent.conversation_log))}
    info = {'replies': used, 'roundsLogged': len(agent.conversation_log), 'maxRounds': instance['maxRounds']}
    final_ddlog = ddlog()
    for law in SandboxedLaw.registry.values():
        law.kill()
    SandboxedLaw.registry.clear()
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(sandbox_dir, ignore_errors=True)
    return finite({'ok': True, 'state': json.loads(json.dumps(state, default=str)), 'text': text, 'reward': 0, 'info': info, 'terminal': terminal,
                   'ddlog': final_ddlog})


class SessionSource:
    def __init__(self, requests, emit, idle):
        self.requests, self.emit, self.idle = requests, emit, idle
    def next(self, observe):
        self.emit(observe())
        return read_action(self.requests, self.idle)


def read_action(requests, idle):
    import select
    ready, _, _ = select.select([requests], [], [], idle)
    line = requests.readline() if ready else ''
    if not line:
        os._exit(0)
    return json.loads(line)


def check_origins(modules, base):
    for name, module in modules.items():
        origin = os.path.realpath(module.__file__)
        if not origin.startswith(os.path.realpath(base) + os.sep):
            raise ValueError(f'Module {name} was loaded from {origin}, outside the interpreter or official source path {base}')


def session(request_fifo, response_fifo, idle_seconds):
    pass                                                                                                                        
                                                                
    requests, responses = open(request_fifo, 'r'), open(response_fifo, 'w')
    first = read_action(requests, idle_seconds)
    if not isinstance(first, dict) or set(first) != {'instance'} or not isinstance(first['instance'], dict):
        raise SystemExit('The first session line must be {"instance": ...}')
    instance = first['instance']
    def emit(value):
        responses.write(json.dumps(value) + '\n'); responses.flush()
    try:
        emit(run(instance, [], SessionSource(requests, emit, idle_seconds)))
        read_action(requests, idle_seconds)
        emit({'ok': False, 'message': 'ValueError: Episode already ended'})
    except (Exception, JudgeProtocolError) as error:
        emit({'ok': False, 'message': f'{type(error).__name__}: {error}'})


def main():
    try:
        request = json.loads(sys.stdin.read())
        instance = request['instance']
        print(json.dumps(run(instance, request.get('actions', []), judge_replies=request.get('judgeReplies', []))))
    except (Exception, JudgeProtocolError) as error:
        print(json.dumps({'ok': False, 'message': f'{type(error).__name__}: {error}'}))


if __name__ == '__main__':
    if len(sys.argv) == 4:
        session(sys.argv[1], sys.argv[2], float(sys.argv[3]))
    else:
        main()
