                                                                               

                                                                                  
                                                                                
                                                                                 
                                                                                   
                                                                
                                                          
   
import json
import os
import sys
import ctypes
import sysconfig

_python_lib = os.path.join(sysconfig.get_config_var("LIBDIR") or "", sysconfig.get_config_var("LDLIBRARY") or "")
if sys.platform.startswith("linux") and os.path.isfile(_python_lib):
    ctypes.CDLL(_python_lib, mode=ctypes.RTLD_GLOBAL)

PROTO = sys.stdout
sys.stdout = sys.stderr                                                         

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from scigym.api import LLM              
from scigym.controller import Controller              
import signal              
import scigym.actions.code as _official_code              


def _enforced_timeout_handler(signum, frame):
                                                                                        
                                                                                          
                                                                                      
                                                                                          
    signal.alarm(2)
    raise TimeoutError("Execution timed out")


_official_code.timeout_handler = _enforced_timeout_handler

                                                                                          
                                                                                             
from scigym.api import CodeResult              
_FORCE = {"on": False}
_orig_execute_request = _official_code.Code.execute_request


def _execute_request(self, request, safe_globals=None):
    if _FORCE["on"]:
        _FORCE["on"] = False
        return CodeResult(False, error="Your requested code runs too long. Execution timed out (exceeded 10 minutes)")
    return _orig_execute_request(self, request, safe_globals=safe_globals)


_official_code.Code.execute_request = _execute_request


def emit(obj):
    PROTO.write(json.dumps(obj, ensure_ascii=False) + "\n")
    PROTO.flush()


class BridgeLLM(LLM):
    def initialize(self, *args, **kwargs):
        self.messages = []
        self.calls = 0

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages

    def get_response(self, user_message):
        _snapshot(self, user_message)
        self.add_message("user", user_message)
        self.calls += 1
        emit({"kind": "player_request", "call": self.calls, "message": user_message})
        line = sys.stdin.readline()
        if not line:
            raise SystemExit("player stream closed")
        reply = json.loads(line)
        text = reply.get("text", "")
        if reply.get("forceTimeout"):
            _FORCE["on"] = True
        self.add_message("assistant", text)
        return text, {}



SNAP_ATTRS = ["experiment_history", "parameter_experiment_history", "code_history", "code_result_history",
              "experiment_request_history", "variable_storage", "current_iterations", "submit", "final_evaluation",
              "final_sbml", "current_experiment_request", "current_code_request", "current_experiment_result",
              "current_code_result", "current_parse_error"]
SNAP_DIR = None


def _snapshot(llm, pending):
    pass                                                                                               
    if SNAP_DIR is None or getattr(llm, "controller", None) is None:
        return
    import cloudpickle
    c = llm.controller
    state = {"calls": llm.calls, "messages": list(llm.messages), "pending": pending,
             "attrs": {a: getattr(c, a) for a in SNAP_ATTRS}}
    tmp = os.path.join(SNAP_DIR, "snapshot.pkl.tmp")
    try:
        with open(tmp, "wb") as f:
            cloudpickle.dump(state, f)
        os.replace(tmp, os.path.join(SNAP_DIR, "snapshot.pkl"))
        with open(os.path.join(SNAP_DIR, "snapshot.json.tmp"), "w") as f:
            json.dump({"steps": llm.calls}, f)
        os.replace(os.path.join(SNAP_DIR, "snapshot.json.tmp"), os.path.join(SNAP_DIR, "snapshot.json"))
    except Exception as exc:                                                                     
        print(f"snapshot failed: {exc}", file=sys.stderr)
        for name in ("snapshot.pkl", "snapshot.json"):
            try: os.remove(os.path.join(SNAP_DIR, name))
            except OSError: pass


def _resume_official_loop(controller, pending):
    pass                                                                                                  
    controller._receive_valid_response(pending)
    while controller.current_iterations <= controller.max_iterations + controller.eval_debug_rounds:
        if controller.current_iterations <= controller.max_iterations and not controller.submit:
            if controller.current_experiment_request:
                controller._conduct_experiment(controller.current_experiment_request)
            if controller.current_code_request:
                controller._execute_code(controller.current_code_request)
        else:
            if not controller.current_parse_error:
                break
        feedback_message = controller._format_feedback()
        if controller.current_iterations > controller.max_iterations:
            controller.submit = True
        controller._receive_valid_response(feedback_message)
    controller._save_results()

def main():
    instance, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    controller = Controller(
        path_to_sbml_cfg=instance,
        max_iterations=int(os.environ.get("SCIGYM_MAX_ITERATIONS", "20")),
        test_memorize=False,
        output_directory=out,
        experiment_actions_path="prompts/experiment_actions_perturb.md",
        customized_functions_path="prompts/customized_functions_sim.md",
        eval_debug_rounds=int(os.environ.get("SCIGYM_DEBUG_ROUNDS", "3")),
        temperature=1.0,
    )
    system_prompt = controller._create_system_prompt()
    emit({"kind": "system_prompt", "text": system_prompt, "numSpecies": controller.num_species})
    global SNAP_DIR
    SNAP_DIR = out
    llm = BridgeLLM(model_name="h0-external-player", api_key="", system_prompt=system_prompt)
    llm.controller = controller
    restore = os.environ.get("SCIGYM_RESTORE")
    if restore:
        import cloudpickle
        with open(restore, "rb") as f:
            state = cloudpickle.load(f)
        controller.initialize_agent(llm)
        for a, v in state["attrs"].items():
            setattr(controller, a, v)
        llm.messages = state["messages"]; llm.calls = state["calls"]
        _resume_official_loop(controller, state["pending"])
    else:
        controller.run_benchmark(model=llm)
    with open(os.path.join(out, "evaluation.json")) as f:
        evaluation = json.load(f)
    emit({"kind": "terminal", "evaluation": evaluation, "submitted": bool(controller.final_evaluation),
          "iterations": controller.current_iterations, "calls": llm.calls})


if __name__ == "__main__":
    main()
