                                                                                   

                                                                                   
                                                                         
                                                                       
                                                                 
                                                           

                                                                                     
   

import json
import re
from typing import Callable, Optional

from scienceagent import llm_client
from scienceagent.executor import SimulationExecutor

                                                                                   
                    
MAX_ROUNDS = 10
MIN_ROUNDS = 2

                                                        
_SYSTEM_PROMPT_PATH = "PhysicsSchool/prompts/run_experiments.md"

                         
_DEFAULT_LAW_STUB = (
    "def discovered_law(pos1, pos2, p1, p2, velocity2, duration):\n"
    "    # your best implementation\n"
    "    return final_pos2, final_vel2\n"
)

                                    
_DEFAULT_EXPERIMENT_FORMAT = (
    '<run_experiment>[{"p1": 1.0, "p2": 1.0, "pos2": [3.0, 0.0], '
    '"velocity2": [0.0, 0.0], "measurement_times": [0.5, 1.0, 2.0]}]</run_experiment>'
)


                                                                           
                                                                            
                                                                      
                                                                
_MSE_FIT_PROMPT_BLOCK = """\
## OPTIONAL TOOL — MSE FITTING OF YOUR CANDIDATE LAW

At the end of any round, you may include a <run_mse_fit> tag ALONGSIDE your
<run_experiment> (or by itself) to ask the system to fit your candidate
law's free parameters against the trajectory data you have already
collected this run. This is the same scipy.optimize-based optimisation that
the evaluator runs at the end of the mission, so use it to refine your law
mid-discovery rather than waiting until submission.

Rules:
- The fit only sees data from THIS run (filtered by run_id), not other runs.
- An <run_mse_fit> call does NOT consume a round on its own — running it
  alongside <run_experiment> still counts as one round.
- You may include AT MOST one <run_mse_fit> per round.
- The body of <run_mse_fit> must contain the SAME source you would put in
  <final_law>: a `discovered_law(...)` function and (optionally) a
  `fit_parameters()` function declaring init values and bounds for free
  parameters. Without a `fit_parameters()` block the system reports the
  loss of your current hard-coded constants but cannot tune them.
- The system replies with a <mse_fit_output> JSON block containing
  `loss_before`, `loss_after`, `fitted_params`, `declared_params`,
  `n_training`, and `error`. Use the fitted parameter values to refine
  your physical reasoning (e.g. if alpha came out near 0.75 the operator
  is closer to a fractional Laplacian than a standard one).
- Do NOT submit <run_mse_fit> in your final-law round — that round must
  contain ONLY <final_law> and <explanation>.
- If <run_mse_fit> reports an error (compile failure, invalid
  fit_parameters spec, or no_training_trajectories), fix the law in the
  next round before submitting <final_law>.

Example:
<run_mse_fit>
def discovered_law(pos1, pos2, p1, p2, velocity2, duration, **params):
    import numpy as np
    alpha = params.get("alpha", 0.5)
    G     = params.get("G", 1.0)
    # ... your candidate integration ...
    return final_pos2, final_vel2

def fit_parameters():
    return {
        "alpha": {"init": 0.5, "bounds": [0.1, 1.5]},
        "G":     {"init": 1.0, "bounds": [0.01, 10.0]},
    }
</run_mse_fit>
"""


def _load_system_prompt(prompt_path: str = None, instructions_path: str = None) -> str:
    pass                                                                     

                                                                               
                                                                             
                                                                         
                                                                      
       
    import os

    prompt_path = prompt_path or _SYSTEM_PROMPT_PATH
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))

    def _read(rel: str) -> str:
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            full = rel                                     
        with open(full) as f:
            return f.read()

    template = _read(prompt_path)
    if "{{world_instructions}}" in template:
        if not instructions_path:
            raise ValueError(
                f"Prompt {prompt_path!r} contains a {{world_instructions}} "
                "placeholder but no instructions_path was supplied."
            )
        template = template.replace(
            "{{world_instructions}}", _read(instructions_path).strip()
        )
    return template


class DiscoveryAgent:
    pass                                                                

         
                                                            
                                                                        
                                                                            
                                                                                  
                                            
                                                                
                                                                                                 
       

    def __init__(
        self,
        model: str,
        executor,
        mission: Optional[str] = None,
        max_tokens: int = 4096,
        verbose: bool = True,
        show_experiment_output: bool = False,
        system_prompt_path: str = None,
        instructions_path: str = None,
        law_stub: str = None,
        experiment_format: str = None,
        critic=None,
        max_rounds: int = MAX_ROUNDS,
        min_rounds: int = MIN_ROUNDS,
        random_experiments: bool = False,
        random_generator: Optional[Callable[[], dict]] = None,
        trajectory_logger=None,
        no_mse: bool = False,
    ):
        self.model = model
        self.executor = executor
        self.mission = mission
        self.max_tokens = max_tokens
        self.verbose = verbose
        self.show_experiment_output = show_experiment_output
        self.critic = critic
        self._system_prompt_path = system_prompt_path or _SYSTEM_PROMPT_PATH
        self._instructions_path = instructions_path
        self._law_stub = law_stub or _DEFAULT_LAW_STUB
        self._experiment_format = experiment_format or _DEFAULT_EXPERIMENT_FORMAT
        self.max_rounds = max(1, int(max_rounds))
        self.min_rounds = max(1, min(int(min_rounds), self.max_rounds))
        self.random_experiments = bool(random_experiments)
        self.random_generator = random_generator
        self.trajectory_logger = trajectory_logger
        self.no_mse = bool(no_mse)
        if self.random_experiments and self.random_generator is None:
            raise ValueError(
                "random_experiments=True requires a random_generator callable."
            )
        self._system = self._build_system_prompt()
                                                                            
        self.conversation_log: list[dict] = []
                                                                                        
        self.discovered_explanation: Optional[str] = None

    def run(self) -> Optional[str]:
        pass                               

                
                                                                              
                                                         

           
        self.conversation_log = []
        self.discovered_explanation = None
        messages = []
        if self.mission:
            messages.append({"role": "user", "content": self.mission})

        for round_num in range(1, self.max_rounds + 1):
            if self.verbose:
                print(f"\n{'='*52}")
                print(
                    f"󰙨 󰧑  science agent experimenting at round {round_num}/{self.max_rounds} 󰧑  󰙨"
                )
                print(f"{'='*52}")

            round_entry = {
                "round": round_num,
                "system_message": None,
                "llm_reply": None,
                "action": None,                                                                                       
                "experiment_input": None,                             
                "experiment_output": None,                             
                "experiment_error": None,
                "final_law": None,
                "explanation": None,
                "critic_feedback": None,
                "mse_fit_input": None,                         
                "mse_fit_output": None,                                   
            }

                                                                                 
                                                                               
            if self.random_experiments:
                self._inject_random_experiment(round_num, messages, round_entry)

                                                                                   
            if self.max_rounds >= 2 and round_num == self.max_rounds - 1:
                warn_msg = (
                    f"Warning: this is round {round_num} of {self.max_rounds}. "
                    "You have one round remaining. Your next response MUST be a <final_law> submission — "
                    "you will not be able to run further experiments after this."
                )
                messages.append({"role": "user", "content": warn_msg})
                round_entry["system_message"] = _join_sys(
                    round_entry["system_message"], warn_msg
                )

                                                              
            if round_num == self.max_rounds:
                force_msg = (
                    "This is your final round. You MUST now submit your best guess "
                    "as a <final_law> regardless of confidence. Do not run more experiments.\n\n"
                    "<final_law>\n" + self._law_stub + "</final_law>"
                )
                messages.append({"role": "user", "content": force_msg})
                round_entry["system_message"] = _join_sys(
                    round_entry["system_message"], force_msg
                )

            reply = llm_client.complete(
                model=self.model,
                messages=messages,
                system=self._system,
                max_tokens=self.max_tokens,
            )
            round_entry["llm_reply"] = reply

            if self.verbose:
                print(f"\n[Science Agent]\n{reply}")

            messages.append({"role": "assistant", "content": reply})

                                            
            final_law = _extract_tag(reply, "final_law")
            if final_law is not None:
                if round_num >= self.min_rounds:
                    if self.verbose:
                        print("\n[Agent submitted final law]")
                    explanation = _extract_tag(reply, "explanation")
                                                                                    
                                                              
                    if explanation is None:
                        if self.verbose:
                            print(
                                "[Warning] Final law submitted without <explanation>. Re-prompting once."
                            )
                        followup_msg = (
                            "Your <final_law> submission is accepted, but you did not include "
                            "the required <explanation> tag. Reply NOW with ONLY a single "
                            "<explanation>...</explanation> block containing a 2–3 sentence "
                            "plain-English description of the physical system you discovered. "
                            "Do not include any other text or tags."
                        )
                        messages.append({"role": "user", "content": followup_msg})
                        followup_reply = llm_client.complete(
                            model=self.model,
                            messages=messages,
                            system=self._system,
                            max_tokens=self.max_tokens,
                        )
                        messages.append(
                            {"role": "assistant", "content": followup_reply}
                        )
                        if self.verbose:
                            print(
                                f"\n[Science Agent — explanation follow-up]\n{followup_reply}"
                            )
                        explanation = _extract_tag(followup_reply, "explanation")
                    self.discovered_explanation = (
                        explanation.strip() if explanation else None
                    )
                    round_entry["action"] = "final_law"
                    round_entry["final_law"] = final_law.strip()
                    round_entry["explanation"] = self.discovered_explanation
                    self.conversation_log.append(round_entry)
                    return final_law.strip()
                else:
                    if self.random_experiments:
                        warn = (
                            f"You have only seen {round_num} round(s) of random experiments. "
                            f"You must wait for at least {self.min_rounds} rounds before submitting a final law. "
                            "Another random experiment will be generated next round — please wait."
                        )
                    else:
                        warn = (
                            f"You have only run {round_num} round(s) of experiments. "
                            f"You must run at least {self.min_rounds} rounds before submitting a final law. "
                            "Please design and run at least one more experiment."
                        )
                    if self.verbose:
                        print(
                            f"[Warning] Agent submitted final law too early (round {round_num}/{self.min_rounds} minimum). Requiring more experiments."
                        )
                    round_entry["action"] = "warning"
                    round_entry["system_message"] = warn
                    self.conversation_log.append(round_entry)
                    messages.append({"role": "user", "content": warn})
                    continue

                                                                                
                                                                              
                                                                                
            if self.random_experiments:
                if round_entry["action"] is None:
                    round_entry["action"] = "random_experiment"
                self.conversation_log.append(round_entry)
                continue

                                                 
            experiment_block = _extract_tag(reply, "run_experiment")
            mse_fit_block = _extract_tag(reply, "run_mse_fit")

                                                                            
                                                                          
                                                                           
                                                                     
            if self.no_mse and mse_fit_block is not None:
                if self.verbose:
                    print(
                        "[Warning] Agent emitted <run_mse_fit> but mid-round MSE "
                        "fitting is disabled in this run. Rejecting."
                    )
                no_mse_msg = (
                    "ERROR: <run_mse_fit> is not available in this run. "
                    "Mid-round MSE fitting has been disabled — your "
                    "candidate-law parameters will be fitted automatically "
                    "by the evaluator at submission time via the "
                    "fit_parameters() mechanism. Do not emit <run_mse_fit> "
                    "again. Continue with <run_experiment> or <final_law>."
                )
                messages.append({"role": "user", "content": no_mse_msg})
                round_entry["system_message"] = _join_sys(
                    round_entry["system_message"], no_mse_msg
                )
                mse_fit_block = None

            if experiment_block is None and mse_fit_block is None:
                if self.verbose:
                    print(
                        "[Warning] No recognized tag in response. Prompting agent to continue."
                    )
                if self.no_mse:
                    no_tag_msg = (
                        "ERROR: No <run_experiment> or <final_law> tag found "
                        "in your response. You must respond with one of these XML tags — no "
                        "code fences, no markdown, just the raw tag.\n\n"
                        "Option 1 — run an experiment:\n" + self._experiment_format + "\n\n"
                        "Option 2 — submit your final law:\n"
                        "<final_law>\n" + self._law_stub + "</final_law>\n\n"
                        "Respond with the XML tag NOW. No explanation before or after."
                    )
                else:
                    no_tag_msg = (
                        "ERROR: No <run_experiment>, <run_mse_fit>, or <final_law> tag found "
                        "in your response. You must respond with one of these XML tags — no "
                        "code fences, no markdown, just the raw tag.\n\n"
                        "Option 1 — run an experiment:\n" + self._experiment_format + "\n\n"
                        "Option 2 — submit your final law:\n"
                        "<final_law>\n" + self._law_stub + "</final_law>\n\n"
                        "Option 3 — fit your candidate law's free parameters against the data "
                        "you have collected so far (returns MSE before/after and fitted params):\n"
                        "<run_mse_fit>\n" + self._law_stub + "</run_mse_fit>\n\n"
                        "Respond with the XML tag NOW. No explanation before or after."
                    )
                round_entry["action"] = "no_tag"
                round_entry["system_message"] = _join_sys(
                    round_entry["system_message"], no_tag_msg
                )
                self.conversation_log.append(round_entry)
                messages.append({"role": "user", "content": no_tag_msg})
                continue

                                                                            
                                                  
            if experiment_block is not None:
                try:
                    exp_input = json.loads(experiment_block)
                    results = self.executor.run(exp_input)
                    output_content = (
                        "<experiment_output>\n"
                        + _compact_json(results)
                        + "\n</experiment_output>"
                    )
                    round_entry["action"] = "experiment"
                    round_entry["experiment_input"] = exp_input
                    round_entry["experiment_output"] = results
                    self._log_trajectories(round_num, "agent", exp_input, results)
                except Exception as e:
                    output_content = f"<experiment_output>\nError running experiment: {e}\n</experiment_output>"
                    round_entry["action"] = "experiment"
                    round_entry["experiment_error"] = str(e)

                if self.verbose and self.show_experiment_output:
                    print(f"\n[Simulator]\n{output_content}")

                messages.append({"role": "user", "content": output_content})

                                                                           
                                                                          
                                          
            if mse_fit_block is not None:
                fit_output_content = self._run_mse_fit(
                    round_num, mse_fit_block, round_entry
                )
                if self.verbose and self.show_experiment_output:
                    print(f"\n[Fitter]\n{fit_output_content}")
                messages.append({"role": "user", "content": fit_output_content})
                if round_entry["action"] is None:
                    round_entry["action"] = "mse_fit"

                                                      
                                                                
            if self.critic and round_num >= 2 and round_entry["action"] == "experiment":
                critic_feedback = self.critic.review(
                    agent_system_prompt=self._system,
                    messages=messages,
                    round_num=round_num,
                )
                if self.verbose:
                    print(f"\n[Supervisor Agent]\n{critic_feedback}")
                critic_msg = (
                    f"Supervisor feedback:\n{critic_feedback}\n\n"
                    "Before proceeding with your next experiment or final law submission, "
                    "briefly acknowledge the supervisor's feedback above: state what you will "
                    "change or why you disagree. Then continue with your action."
                )
                messages.append({"role": "user", "content": critic_msg})
                round_entry["critic_feedback"] = critic_feedback

            self.conversation_log.append(round_entry)

        if self.verbose:
            print(
                f"\n[Agent did not submit a final law within {self.max_rounds} rounds]"
            )
        return None

    def _inject_random_experiment(
        self, round_num: int, messages: list, round_entry: dict
    ) -> None:
        pass                                                                     

                                                                               
                                                                            
                                                              
                                        
           
        exp_input = self.random_generator()
        try:
            results = self.executor.run([exp_input])
            output_body = _compact_json(results)
            round_entry["experiment_input"] = exp_input
            round_entry["experiment_output"] = results
            self._log_trajectories(round_num, "random", [exp_input], results)
        except Exception as e:
            output_body = f"Error running experiment: {e}"
            round_entry["experiment_input"] = exp_input
            round_entry["experiment_error"] = str(e)

        round_entry["action"] = "random_experiment"

        preamble = (
            f"A random experiment ({round_num} of {self.max_rounds}) has been "
            "drawn and executed automatically. The inputs and resulting "
            "trajectory are below. Briefly acknowledge what this data tells "
            "you. Do NOT output a <run_experiment> tag — the next random "
            "experiment will be generated on the next round regardless of "
            "what you ask for."
        )
        user_block = (
            preamble
            + "\n\n<experiment_input>\n"
            + json.dumps(exp_input)
            + "\n</experiment_input>"
            + "\n<experiment_output>\n"
            + output_body
            + "\n</experiment_output>"
        )
        messages.append({"role": "user", "content": user_block})
        round_entry["system_message"] = _join_sys(
            round_entry.get("system_message"), preamble
        )

        if self.verbose and self.show_experiment_output:
            print(f"\n[Simulator — random experiment {round_num}]\n{user_block}")

    def _run_mse_fit(self, round_num: int, law_source: str, round_entry: dict) -> str:
        pass                                                              
                                                                          
                                                                
        round_entry["mse_fit_input"] = law_source.strip()
        if self.trajectory_logger is None:
            result = {
                "error": "trajectory CSV logging is disabled, so no data is "
                "available for MSE fitting in this run.",
                "loss_before": None,
                "loss_after": None,
                "fitted_params": {},
                "declared_params": {},
                "n_training": 0,
            }
            round_entry["mse_fit_output"] = result
            return (
                "<mse_fit_output>\n"
                + json.dumps(result, separators=(",", ":"))
                + "\n</mse_fit_output>"
            )

        from scienceagent.mse_fitting import fit_law, redact_world_leak

        try:
            result = fit_law(
                law_source=law_source,
                world=self.trajectory_logger.world,
                csv_path=self.trajectory_logger.csv_path,
                run_id=self.trajectory_logger.run_id,
            )
        except Exception as e:
            result = {
                "error": "unexpected_error: " + redact_world_leak(
                    e,
                    self.trajectory_logger.csv_path,
                    self.trajectory_logger.world,
                ),
                "loss_before": None,
                "loss_after": None,
                "fitted_params": {},
                "declared_params": {},
                "n_training": 0,
            }
        round_entry["mse_fit_output"] = result
        if self.verbose:
            err = result.get("error")
            if err:
                print(f"[mse_fit] error: {err}")
            else:
                lb = result.get("loss_before")
                la = result.get("loss_after")
                fp = result.get("fitted_params") or {}
                pretty = (
                    ", ".join(f"{k}={v:.4g}" for k, v in fp.items())
                    or "(no fit_parameters)"
                )
                                                                         
                                                                            
                lb_str = f"{lb:.4g}" if isinstance(lb, (int, float)) else "n/a"
                la_str = f"{la:.4g}" if isinstance(la, (int, float)) else "n/a"
                print(f"[mse_fit] loss {lb_str} -> {la_str}  fitted: {pretty}")
        return (
            "<mse_fit_output>\n"
            + json.dumps(result, separators=(",", ":"))
            + "\n</mse_fit_output>"
        )

    def _log_trajectories(
        self, round_num: int, source: str, exp_inputs, exp_outputs
    ) -> None:
        pass                                                                     
        if self.trajectory_logger is None:
            return
        if not isinstance(exp_inputs, list) or not isinstance(exp_outputs, list):
            return
        for idx, (inp, out) in enumerate(zip(exp_inputs, exp_outputs)):
            try:
                self.trajectory_logger.log_experiment(
                    round_num=round_num,
                    source=source,
                    exp_input=inp,
                    exp_output=out,
                    exp_idx_in_round=idx,
                )
            except Exception as e:
                if self.verbose:
                    print(f"[trajectory_logger] failed to log r{round_num} e{idx}: {e}")

    def _build_system_prompt(self) -> str:
        try:
            base = _load_system_prompt(
                self._system_prompt_path, self._instructions_path
            )
        except FileNotFoundError:
            base = (
                "You are a scientific discovery agent. Design experiments, "
                "analyze results, and discover the underlying law of physics."
            )
        return base.rstrip() + "\n\n" + self._run_policy_note()

    def _run_policy_note(self) -> str:
        pass                                                            

                                                                         
                                                                          
                                    
           
        mse_fit_available = self.trajectory_logger is not None and not self.no_mse
        base = (
            "## RUN-SPECIFIC CONSTRAINTS (these override any conflicting numbers above)\n"
            f"- For this session you have EXACTLY {self.max_rounds} round(s) of "
            f"experiments. Plan accordingly: on round {self.max_rounds} you will be "
            "forced to submit your <final_law>.\n"
            f"- You must run at least {self.min_rounds} round(s) of experiments "
            "before submitting a <final_law>.\n"
            "- If your `discovered_law` integrates the trajectory with a for-loop "
            "over some timestep `dt`, the SMALLEST value of `dt` you are allowed "
            "to use is 0.01. Do not set dt below 0.01 under any circumstances.\n"
            "- ALWAYS set `dt > 0.005` in EVERY test simulation AND in your final "
            "law — no timestep anywhere in your code may be 0.005 or smaller.\n"
        )
        if mse_fit_available:
            base += "\n" + _MSE_FIT_PROMPT_BLOCK
        return base


def _join_sys(existing: Optional[str], new: str) -> str:
    pass                                                               
    if not existing:
        return new
    return existing + "\n\n" + new


def _round_floats(obj, decimals=4):
    pass                                                 
    if isinstance(obj, float):
        return round(obj, decimals)
    if isinstance(obj, list):
        return [_round_floats(v, decimals) for v in obj]
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    return obj


def _compact_json(results) -> str:
    pass                                                                          
    return json.dumps(_round_floats(results), separators=(",", ":"))


def _strip_code_fences(text: str) -> str:
    pass                                                                
                                                                  
    text = re.sub(r"```(?:xml|python|json)?\s*\n?", "", text)
    text = re.sub(r"```\s*", "", text)
    return text


def _extract_tag(text: str, tag: str) -> Optional[str]:
    pass                                                                    
    if not text:
        return None
                                                        
    pattern = rf"<{tag}>(.*?)</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    cleaned = _strip_code_fences(text)
    match = re.search(pattern, cleaned, re.DOTALL)
    return match.group(1) if match else None
