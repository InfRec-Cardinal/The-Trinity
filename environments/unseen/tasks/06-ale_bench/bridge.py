                                                                                                          

                                                                                                              
                                                                                                                
                                                                                                              
                    

                                                  
                                                                                                                         
                                                                                                                          
                                                                                             
                                                                           
   
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import sys
import time
import traceback
from contextlib import contextmanager
from pathlib import Path

import ale_bench
from ale_bench.result import JudgeResult, ResourceUsage
from ale_bench_eval.evaluate import get_ce_code
from ale_bench_eval.prompts.builder import PromptArgs, create_feedback_message, create_initial_message
from ale_bench_eval.safe_ale_session import SESSION_DURATION_HOURS
from ale_bench_eval.selection import get_worst_score

CODE_LANGUAGE = "cpp20"
JUDGE_VERSION = "202301"
JUDGE_RETRIES = 3
                                                                                                              
                                                                                                              
JUDGE_SLOTS = int(os.environ.get("ALE_JUDGE_SLOTS", "2"))
JUDGE_LOCK_DIR = Path(os.environ.get("ALE_JUDGE_LOCK_DIR", "/tmp/ale-judge-slots"))


@contextmanager
def judge_slot():
    JUDGE_LOCK_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        for slot in range(JUDGE_SLOTS):
            handle = open(JUDGE_LOCK_DIR / f"slot-{slot}.lock", "w")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
                continue
            try:
                yield slot
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()
            return
        time.sleep(0.2)

out = sys.stdout
sys.stdout = sys.stderr                                                          


def reply(payload: dict) -> None:
    out.write(json.dumps(payload, ensure_ascii=False) + "\n")
    out.flush()


class Bridge:
    def __init__(self) -> None:
        self.session = None
        self.prompt_args = None
        self.score_type = None
        self.submissions: list[dict] = []

    def open(self, problem_id: str, num_workers: int) -> dict:
        self.session = ale_bench.start(
            problem_id=problem_id,
            lite_version=False,
            num_workers=num_workers,
            run_visualization_server=False,
            session_duration=dt.timedelta(hours=SESSION_DURATION_HOURS),
        )
        self.prompt_args = PromptArgs(
            code_language=CODE_LANGUAGE, judge_version=JUDGE_VERSION, prompt_language="en", use_image=False
        )
        self.score_type = self.session.problem.metadata.score_type
        contents = create_initial_message(self.prompt_args, self.session.problem)
        text = "".join(c for c in contents if isinstance(c, str))
        problem = self.session.problem
        return {
            "text": text,
            "problem": {
                "problem_id": problem_id,
                "score_type": self.score_type.value,
                "time_limit": problem.constraints.time_limit,
                "memory_limit_mib": problem.constraints.memory_limit // 1024 // 1024,
            },
        }

    def _judge(self, fn):
        for attempt in range(1, JUDGE_RETRIES + 1):
            with judge_slot():
                result = fn()
            if result.overall_judge_result != JudgeResult.INTERNAL_ERROR:
                return result, attempt - 1
        raise RuntimeError("Judge returned INTERNAL_ERROR after retries.")

    def public(self, code: str) -> dict:
        eval_code = code if code.strip() else get_ce_code(CODE_LANGUAGE)
        result, retries = self._judge(
            lambda: self.session.public_eval(eval_code, code_language=CODE_LANGUAGE, judge_version=JUDGE_VERSION)
        )
        accepted = result.overall_judge_result == JudgeResult.ACCEPTED
        score = result.overall_absolute_score if accepted else get_worst_score(self.score_type)
        self.submissions.append({"code": code, "overall_absolute_score": score})
                                                                                                                     
        text = create_feedback_message(self.prompt_args, result if code.strip() else None)[0]
        return {
            "text": text,
            "round": len(self.submissions),
            "judge_result": result.overall_judge_result.value,
            "score": score,
            "raw_overall_absolute_score": result.overall_absolute_score,
            "judge_retries": retries,
        }

    def _select(self, n_max: int) -> int:
                                                                                                             
        pairs = [(i, s["overall_absolute_score"]) for i, s in enumerate(self.submissions) if i < n_max]
        if not pairs:
            return 0
        pick = min if self.score_type.value == "minimize" else max
        best = pick(score for _, score in pairs)
        return next(i for i, score in pairs if score == best)

    def select(self, checkpoints: list[int]) -> dict:
                                                                                                                 
        names = [("x1_first_submission", 0)] + [(f"self_refine_{n}", self._select(n)) for n in checkpoints]
        return {"selections": {name: index + 1 for name, index in names},
                "publicScores": [s["overall_absolute_score"] for s in self.submissions]}

    def private(self, checkpoints: list[int]) -> dict:
        names = [("x1_first_submission", 0)] + [(f"self_refine_{n}", self._select(n)) for n in checkpoints]
        results: dict[str, dict] = {}
        evaluated: dict[str, dict] = {}
        for name, index in names:
            code = self.submissions[index]["code"] if self.submissions else ""
            key = code.strip()
            if key not in evaluated:
                eval_code = code if code.strip() else get_ce_code(CODE_LANGUAGE)
                (private_result, rank, performance), retries = self._private(eval_code)
                evaluated[key] = {
                    "overall_absolute_score": private_result.overall_absolute_score,
                    "overall_relative_score": private_result.overall_relative_score,
                    "overall_judge_result": private_result.overall_judge_result.value,
                    "rank": rank,
                    "performance": performance,
                    "judge_retries": retries,
                }
            results[name] = {"submission_round": index + 1, **evaluated[key]}
        return {"results": results}

    def _private(self, code: str):
        for attempt in range(1, JUDGE_RETRIES + 1):
            try:
                with judge_slot():
                    res = self.session.private_eval(code, code_language=CODE_LANGUAGE, judge_version=JUDGE_VERSION)
            finally:
                self._reset_private_eval_count()
            if res[0].overall_judge_result != JudgeResult.INTERNAL_ERROR:
                return res, attempt - 1
        raise RuntimeError("Private judge returned INTERNAL_ERROR after retries.")

    def _reset_private_eval_count(self) -> None:
                                                                                                                    
                                                                                                            
        usage = self.session.current_resource_usage
        self.session._current_resource_usage = ResourceUsage(                
            num_case_gen=usage.num_case_gen,
            num_case_eval=usage.num_case_eval,
            num_call_public_eval=usage.num_call_public_eval,
            num_call_private_eval=0,
            execution_time_case_eval=usage.execution_time_case_eval,
        )

    def close(self) -> dict:
        if self.session is not None:
            self.session.close()
            self.session = None
        return {}


def main() -> None:
    bridge = Bridge()
    for line in sys.stdin:
        if not line.strip():
            continue
        msg = json.loads(line)
        try:
            cmd = msg["cmd"]
            if cmd == "open":
                payload = bridge.open(msg["problem_id"], int(msg.get("num_workers", 1)))
            elif cmd == "public":
                payload = bridge.public(msg["code"])
            elif cmd == "private":
                payload = bridge.private(list(msg["checkpoints"]))
            elif cmd == "select":
                payload = bridge.select(list(msg["checkpoints"]))
            elif cmd == "close":
                reply({"ok": True, **bridge.close()})
                return
            else:
                raise ValueError(f"unknown command {cmd!r}")
            reply({"ok": True, **payload})
        except Exception as exc:                                                     
            reply({"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-2000:]})


if __name__ == "__main__":
    main()
