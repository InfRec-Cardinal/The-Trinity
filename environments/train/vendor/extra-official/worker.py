#!/usr/bin/env python3
                                                 

                                                                                                     
                                                                                                    
                                              
   
import ast
import contextlib
import hashlib
import importlib.util
import inspect
import itertools
import json
import math
import os
from pathlib import Path
import queue
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import typing
from enum import Enum, auto

VENDOR = Path(__file__).resolve().parent
SOURCES = {
    'mastermind': VENDOR / 'mastermind-source-03de37ea',
    'wilt': VENDOR / 'wilt-source-6344f04b',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def source_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def source_ast(path, names, namespace):
    parsed = ast.parse(path.read_text(), filename=str(path))
    statements = [node for node in parsed.body if getattr(node, "name", None) in names]
    if len(statements) != len(names):
        raise ValueError("Official AST definitions changed")
    exec(compile(ast.Module(body=statements, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


class NoopProgress:
    def __init__(self, **kwargs):
        self.desc = ""

    def update(self, amount):
        pass

    def refresh(self):
        pass

    def close(self):
        pass


class HostBudgetExhausted(Exception):
    pass


class SourceModel:
    pass                                                                                                              

    def __init__(self, bridge):
        self.bridge = bridge

    def initialize_conversation(self, prompt):
        return [{"role": "system", "content": prompt}]

    def _action(self, history):
        if self.bridge.step_index >= self.bridge.max_steps:
            raise HostBudgetExhausted()
        self.bridge.events.put({"kind": "prompt", "history": json.loads(json.dumps(history))})
        value = self.bridge.actions.get()
        if value is None:
            raise RuntimeError("Transport closed")
        return value

    def __call__(self, history):
        return [*history, {"role": "assistant", "content": self._action(history)}]

    def perform_step(self, history):
        return self._action(history)

    def get_model_info(self):
        return {"kind": "external_frozen_h0_transport", "local_model_calls": 0}


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
        return [*cmd, python, "-I", "-B", script, *args]
    raise RuntimeError(f"No candidate sandbox for platform {sys.platform}")


def sandbox_profile(directory):
    runtime = Path(sys.base_prefix).resolve()
    python = Path(sys.executable).resolve()
    worker = Path(__file__).resolve()
    quote = lambda p: json.dumps(str(p))
    return "\n".join([
        '(version 1)', '(allow default)', '(deny network*)', '(deny process-fork)', '(deny process-exec)',
        f'(allow process-exec (literal {quote(python)}))',
        '(deny file-read-data (subpath "/Users") (subpath "/private") (subpath "/Volumes"))',
        f'(allow file-read-data (subpath {quote(runtime)}) (literal {quote(worker)}) (subpath {quote(directory)}))',
        '(deny file-write* (subpath "/Users") (subpath "/private") (subpath "/Volumes") (subpath "/System") (subpath "/usr") (subpath "/Library"))',
        f'(allow file-write* (subpath {quote(directory)}))',
    ])


def evaluate_candidate(expression, inputs, seed, workspace):
    workspace.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="candidate-", dir=workspace)).resolve()
    try:
        payload_path, output_path, policy_path = directory / "input.json", directory / "output.json", directory / "policy.sb"
        atomic_json(payload_path, {"expression": expression, "inputs": inputs, "seed": seed, "outputPath": str(output_path)})
        policy_path.write_text(sandbox_profile(directory))
        process = subprocess.run(sandbox_command(policy_path, directory, str(Path(sys.executable).resolve()), str(Path(__file__).resolve()),
                                                 ['candidate', str(payload_path)]), cwd=directory,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
                                 env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
        if process.returncode != 0 or not output_path.exists():
            raise ValueError("Candidate sandbox execution failed")
        result = json.loads(output_path.read_text())
        if result.get("error") or len(result.get("outputs", [])) != len(inputs):
            raise ValueError("Candidate lambda evaluation failed")
        values = result["outputs"]
        if any(not isinstance(value, (bool, int, float, str, type(None))) or isinstance(value, float) and not math.isfinite(value) for value in values):
            raise ValueError("Candidate output is not a finite primitive")
        return values
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def candidate_main(payload_path):
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024 * 1024, 8 * 1024 * 1024))
    payload = json.loads(Path(payload_path).read_text())
    random.seed(payload["seed"])
    try:
                                                                              
                                                                              
                                                                    
        predicted = eval(payload["expression"], {"math": math, "random": random})
        values = [predicted(*row) for row in payload["inputs"]]
        result = {"outputs": values}
        json.dumps(result, allow_nan=False)
    except BaseException:
        result = {"error": "candidate_evaluation_failed"}
    Path(payload["outputPath"]).write_text(json.dumps(result, allow_nan=False))


class Bridge:
    def init(self, command):
        self.task = command["taskId"]
        if self.task not in SOURCES:
            raise ValueError("Unsupported official text game")
        self.source = SOURCES[self.task]
        self.configuration = command["configuration"]
        self.run_dir = Path(command["runDir"]).resolve()
        self.episode_path = Path(command["episodePath"])
        if self.episode_path.is_absolute() or ".." in self.episode_path.parts:
            raise ValueError("Invalid episode directory")
        self.max_steps = 12 if self.task == "mastermind" else 31
        self.step_index = 0
        self.events, self.actions = queue.Queue(), queue.Queue()
        self.result = None
        self.host_reason = None
        self.model = SourceModel(self)
        self.history = []
        if self.task == "mastermind":
            self._load_mastermind()
        else:
            self._load_wilt()
        threading.Thread(target=self._run_native, daemon=True).start()
        return self._await_source()

    def _load_mastermind(self):
        game_module = source_module('official_mastermind_game', self.source / 'src/mastermind/game.py')
        utility_namespace = {"re": re, "Dict": typing.Dict, "List": typing.List}
        source_ast(self.source / 'src/mastermind/utils.py', {'parse_guess'}, utility_namespace)
        namespace = {**vars(typing), "Enum": Enum, "auto": auto, "random": random, "json": json, "threading": threading,
                     "Path": Path, "product": itertools.product, "Mastermind": game_module.Mastermind,
                     "LanguageModel": object, "Solver": object, "ChatHistory": list, "GameResult": dict,
                     "Guess": list, "Scores": tuple, "GuessHistory": list, "ProgressHistory": list,
                     "tqdm": NoopProgress, "parse_guess": utility_namespace['parse_guess'], "GREEN": '', "RED": '', "YELLOW": '', "RESET": ''}
        source_ast(self.source / 'src/mastermind/evaluator.py', {'GameState', 'Evaluator'}, namespace)
        random.seed(self.configuration["seed"])
        template = game_module.Mastermind(code_length=4, num_colors=6, max_guesses=12)
        native_clone = template.clone
        def capture_clone():
            self.game = native_clone()
            return self.game
        template.clone = capture_clone
        self.native = namespace['Evaluator'](template, self.model, use_cot=False, use_fewshot_example=False, compute_progress=True)

    def _load_wilt(self):
                                                                          
                                                                             
        test_module = source_module('official_wilt_cases', self.source / 'harness/test_cases.py')
        tracker = source_module('official_wilt_tracker', self.source / 'harness/hypothesis_space.py')
        namespace = {"random": random, "re": re, "itertools": itertools, "inspect": inspect, "time": time, "math": math,
                     "HypothesisSpaceTracker": tracker.HypothesisSpaceTracker,
                     "generate_hypothesis_space": tracker.generate_hypothesis_space, "combine_hypotheses": tracker.combine_hypotheses,
                     "TESTS_FULL": test_module.TESTS_FULL, "TESTS_BAYESIAN": test_module.TESTS_BAYESIAN,
                     "TESTS_BAYESIAN_SINGLE": test_module.TESTS_BAYESIAN_SINGLE, "eval": self._candidate_proxy}
        source_ast(self.source / 'harness/llm_reasoning_harness.py', {'LLMReasoningHarness'}, namespace)
        if self.configuration.get('split') != 'full' or self.configuration.get('index') not in test_module.TESTS_FULL:
            raise ValueError("Unsupported official WILT full-split rule")
        self.rule = test_module.TESTS_FULL[self.configuration['index']]
        self.rule_source = inspect.getsource(self.rule).strip()
        random.seed(self.configuration['scorerSeed'])
        os.chdir(self.source)
        self.native = namespace['LLMReasoningHarness'](self.model, self.rule, tuple_length=3, max_attempts=30, use_bayesian=False)

    def _candidate_proxy(self, expression):
        seed = self.configuration['scorerSeed']
        random.seed(seed)
        inputs = self.native._generate_test_inputs()
        outputs = evaluate_candidate(expression, inputs, seed, self.run_dir / self.episode_path / 'candidate-sandbox')
        random.seed(seed)                                                        
        position = 0
        def predicted(*values):
            nonlocal position
            if position >= len(inputs) or tuple(inputs[position]) != values:
                raise ValueError("Official checker input order changed")
            answer = outputs[position]
            position += 1
            return answer
        return predicted

    def _run_native(self):
        try:
            result = self.native._run_single_game(0, None, compute_progress=True) if self.task == 'mastermind' else self.native.interact_with_llm()
            self.events.put({"kind": "result", "result": result})
        except HostBudgetExhausted:
            self.host_reason = 'host_action_budget_exhausted'
            self.events.put({"kind": "result", "result": self.native._create_result_dict(0)})
        except Exception as error:
            self.events.put({"kind": "error", "type": type(error).__name__})

    def _await_source(self):
        event = self.events.get(timeout=25)
        if event['kind'] == 'error':
            raise ValueError('Official source failed to advance: ' + event['type'])
        if event['kind'] == 'prompt':
            self.history = event['history']
        else:
            self.result = event['result']
            self.history = self.result['chat_history'] if self.task == 'mastermind' else self.native.conversation_history
        return self._observation()

    def _observation(self):
        from PIL import Image, ImageDraw, ImageFont
        ended = self.result is not None
        if self.task == 'mastermind':
            valid = self.result.get('valid', True) if ended else True
            solved = bool(self.result.get('solved')) if ended else False
            outcome = 'invalid' if ended and not valid else 'success' if solved else 'failure' if ended else None
            score = None if ended and not valid else 1 if solved else 0 if ended else None
            reason = 'native_first_attempt_invalid' if ended and not valid else 'native_WON' if solved else 'native_LOST' if ended else None
            public_state = {"possibleColors": self.game.possible_colors, "codeLength": 4, "maxGuesses": 12,
                            "attempts": self.step_index, "ended": ended}
            native_private = {"game": self.game.to_json(), "nativeResult": self.result, "history": self.history}
            native_info = {} if not ended else {"valid": valid, "solved": solved, "numGuesses": self.result['num_guesses'], "progressHistory": self.result['progress_history']}
            if ended:
                text = 'Feedback: ' + self.result['turn_history'][-1]['feedback'] + '\n' + str(reason)
            else:
                text = self.history[-1]['content']
        else:
            points = self.result.get('points', 0) if ended else None
            solved = ended and points >= 1000
            outcome, score = ('success' if solved else 'failure') if ended else None, points
            reason = self.host_reason or ('native_rule_equivalent' if solved else 'native_rule_incorrect_or_aborted') if ended else None
            public_state = {"probesUsed": self.native.attempts, "maxProbes": 30, "actionsUsed": self.step_index, "actionLimit": 31, "ended": ended}
            native_private = {"selectedRuleSource": self.rule_source, "selectedRuleIndex": self.configuration['index'],
                              "scorerSeed": self.configuration['scorerSeed'], "testCases": self.native.test_cases, "results": self.native.results,
                              "nativeResult": self.result, "history": self.history, "hostReason": self.host_reason}
            native_info = {} if not ended else {"points": points, "probesUsed": self.native.attempts, "reusedTests": self.result.get('reused_tests'), "confirmsBias": self.result.get('confirms_bias')}
            text = self.history[-1]['content']
            if ended and self.host_reason:
                text += '\n' + self.host_reason
                                                                               
                                                                             
        if self.step_index == 0:
            text = '\n\n'.join(message['content'] for message in self.history if message['role'] in ('system', 'user'))
        text += f'\nEvaluated actions used: {self.step_index}/{self.max_steps}.'
        private_state = {"taskId": self.task, "configurationHash": self.configuration['configurationHash'], "step": self.step_index,
                         "source": native_private, "publicText": text, "publicState": public_state}
        state_hash = digest(private_state)
        relative_frame = self.episode_path / 'frames' / f'frame-{self.step_index:04d}.png'
        frame_path = self.run_dir / relative_frame
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for line in text.splitlines():
            lines.extend(textwrap.wrap(line, width=92, break_long_words=True) or [''])
        image = Image.new('RGB', (900, max(180, 58 + 20 * len(lines))), '#f7f8fc')
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=14)
        draw.text((16, 12), self.task + ' — official public observation', fill='#203859', font=font)
        for index, line in enumerate(lines):
            draw.text((16, 42 + index * 20), line, fill='#172339', font=font)
        image.save(frame_path)
        return {"step": self.step_index, "publicText": text, "publicState": public_state, "frame": None,
                "previewFrame": {"path": relative_frame.as_posix(), "sha256": hashlib.sha256(frame_path.read_bytes()).hexdigest(), "mimeType": "image/png"},
                "stateHash": state_hash, "configurationHash": self.configuration['configurationHash'], "reward": score if ended else 0,
                "info": native_info, "instance": {"caseId": self.configuration['id'], "sourceKind": "official"},
                "terminal": {"ended": ended, "outcome": outcome, "reason": reason, "score": score}}

    def _apply(self, action):
        if self.result is not None:
            raise ValueError('Official text game already ended')
        if not isinstance(action, dict) or set(action) != {'action'} or not isinstance(action['action'], str) or len(action['action']) > 8192:
            raise ValueError('Expected one public source-format directive')
        self.step_index += 1
        self.actions.put(action['action'])
        return self._await_source()

    def step(self, command):
        expected = command.get('expectedStep')
        if expected is not None and self.step_index != expected:
            raise ValueError('Official text-game action sequence mismatch')
        return self._apply(command['action'])


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'candidate':
        candidate_main(sys.argv[2])
    else:
        bridge = None
        for line in sys.stdin:
            command = {}
            try:
                command = json.loads(line)
                with contextlib.redirect_stdout(sys.stderr):
                    if command['command'] == 'init':
                        bridge = Bridge()
                        result = bridge.init(command)
                    elif command['command'] == 'step':
                        if bridge is None:
                            raise ValueError('Episode is not initialised')
                        result = bridge.step(command)
                    elif command['command'] == 'close':
                        if bridge is not None and hasattr(bridge, 'actions'):
                            bridge.actions.put(None)
                        result = None
                    else:
                        raise ValueError('Unknown worker command')
                print(json.dumps({"id": command['id'], "ok": True, "result": result}), flush=True)
                if command['command'] == 'close':
                    break
            except Exception as error:
                print(json.dumps({"id": command.get('id'), "ok": False, "message": str(error)}), flush=True)
