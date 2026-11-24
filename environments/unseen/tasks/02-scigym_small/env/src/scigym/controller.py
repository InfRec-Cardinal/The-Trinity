import copy
import json
import os
import re
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict

import pandas as pd

from scigym.actions import Code, Experiment, create_simulate_function
from scigym.api import (
    DEFAULT_AVAILABLE_PACKAGES,
    LLM,
    CodeRequest,
    CodeResult,
    ExperimentConfig,
    ExperimentResult,
    VariableStorage,
    create_dataframe,
)
from scigym.data import SBML, Question
from scigym.eval import Evaluator
from scigym.utils import print_chat_history_with_tokens, update_markdown


class Controller:
                                       
    current_experiment_request: ExperimentConfig | None = None
    current_code_request: CodeRequest | None = None
    current_experiment_result: ExperimentResult | None = None
    current_code_result: CodeResult | None = None
    current_parse_error: str | None = None

    experiment_history: Dict[str, pd.DataFrame] = {}
    code_history: Dict[str, str] = {}
    code_result_history: Dict[str, str] = {}
    parameter_experiment_history: Dict[str, pd.DataFrame] = {}
    experiment_request_history: Dict[int, Any] = {}

                                                                   
    llm: LLM
    evaluator: Evaluator
    tools: Code

    def __init__(
        self,
        path_to_sbml_cfg: str,
        max_iterations: int,
        test_memorize: bool,
        output_directory: str,
        experiment_actions_path: str,
        customized_functions_path: str,
        eval_debug_rounds: int,
        temperature: float,
        task_difficulty: str = "fully_observable",
    ):
        self.path_to_sbml_cfg = path_to_sbml_cfg
        self.sedml_file_path = f"{path_to_sbml_cfg}/truth.sedml"
        self.task_difficulty = task_difficulty

        self.current_iterations = 0
        self.test_memorize = test_memorize
        self.output_directory = output_directory
        self.eval_debug_rounds = eval_debug_rounds
        self.final_evaluation = None
        self.final_sbml = None

        self.max_iterations = max_iterations
        if self.test_memorize:
            self.max_iterations = 0
        self.experiment_actions_path = experiment_actions_path
        self.customized_functions_path = customized_functions_path
        self.submit = False
        self.variable_storage = VariableStorage()
        self.temperature = temperature
                                   
                                                     
        self.initialize_question()

    @property
    def safe_globals(self):
        pass                                                                      
                                              
           
        return {
            "__builtins__": __builtins__,
            "input_sbml_string": copy.deepcopy(self.incomplete_model.to_string()),
            "experiment_history": copy.deepcopy(self.experiment_history),
            "simulate": create_simulate_function(self.sedml_file_path),
            "shared_variables": self.variable_storage,
        }

    def initialize_question(self) -> None:
                                              
        question_handler = Question(
            sbml_directory_path=self.path_to_sbml_cfg,
            task_difficulty=self.task_difficulty,
        )
        complete_model = question_handler.get_original_sbml()
        incomplete_model = question_handler.get_partial_sbml()
        incomplete_runnable_model = question_handler.get_runnable_partial_sbml()
        self.incomplete_model = incomplete_model
        self.complete_model = complete_model
        self.incomplete_runnable_model = incomplete_runnable_model
        self.num_species = len(self.complete_model.get_species_ids())

    def initialize_agent(self, model: LLM) -> LLM:
        self.llm = model
                                     
        self.evaluator = Evaluator(
            true_sbml=self.complete_model,
            incomplete_sbml=self.incomplete_model,
            incomplete_runnable_sbml=self.incomplete_runnable_model,
        )
        self.tools = Code()

        return self.llm

    def _save_results(self) -> None:
                     
        if self.final_evaluation:
            eval_dict = self.final_evaluation.to_dict()
            eval_dict["success"] = True
        else:
            final_evaluation = self.evaluator(pred_sbml=self.incomplete_model)
            eval_dict = final_evaluation.to_dict()
            eval_dict["success"] = False


        with open(f"{self.output_directory}/evaluation.json", "w") as file:
            json.dump(eval_dict, file, indent=4)

        print(f"Evaluation saved to {self.output_directory}/evaluation.json")

        chat_history_json = self.llm.get_message()
        with open(f"{self.output_directory}/chat_history.yaml", "w") as file:
            json.dump(chat_history_json, file, indent=4)

        print_chat_history_with_tokens(
            chat_history_json, f"{self.output_directory}/chat_history_readable.txt"
        )

        if self.final_sbml:
            with open(f"{self.output_directory}/final_model.xml", "w", encoding="utf-8") as f:
                f.write(self.final_sbml)

        if self.test_memorize:
            return

                         
        output_code_dir = os.path.join(self.output_directory, "codes")
        if not os.path.exists(output_code_dir):
            os.makedirs(output_code_dir)

        for name, code in self.code_history.items():
            with open(f"{output_code_dir}/{name}.py", "w", encoding="utf-8") as f:
                f.write(code)

        for name, result in self.code_result_history.items():
            with open(f"{output_code_dir}/{name}_result.txt", "w", encoding="utf-8") as f:
                f.write(result)

        print(f"Code and execution results saved to {output_code_dir}")

        with open(f"{self.output_directory}/experiment_request.json", "w") as file:
            json.dump(self.experiment_request_history, file, indent=4)

                                 
        chat_history_json = self.llm.get_message()
        with open(f"{self.output_directory}/chat_history.yaml", "w") as file:
            json.dump(chat_history_json, file, indent=4)

        print_chat_history_with_tokens(
            chat_history_json, f"{self.output_directory}/chat_history_readable.txt"
        )

    def _create_system_prompt(self) -> str:
        current_dir = Path(__file__).parent
        if self.test_memorize:
            prompt_path = current_dir / "prompts" / "system_prompt_memorize.md"
            with open(prompt_path, "r", encoding="utf-8") as file:
                system_prompt = file.read()
        else:
            section_files = {
                "EXPERIMENTAL_ACTIONS": current_dir / self.experiment_actions_path,
                "CUSTOMIZED_FUNCTIONS": current_dir / self.customized_functions_path,
            }
            template_file = current_dir / "prompts" / "template.md"
            system_prompt = update_markdown(template_file, **section_files)

        return system_prompt

    def _format_initial_prompt(self, incomplete_sbml: SBML) -> str:
        pass                                                                                  

             
                                                      

                
                                                
           
        if self.task_difficulty == "fully_observable":
            self.task_info = "You are investigating a biological system where all species are observable. Your goal is to discover the missing reactions. You do not need to add new species.\n"
        elif self.task_difficulty == "partial_observable":
            self.task_info = "You are investigating a biological system where only some species are observable. Your goal is to identify both the missing species and the reactions connecting them to complete the SBML model.\n"
        if self.test_memorize:
            prompt = f"""
            # Task Info
            {self.task_info}

            # Incomplete SBML Model. You can assess it as input_sbml_string.
            {self.incomplete_model.to_string()}

            Format your response according to the instructions in the system message.
            """
        else:
            prompt = f"""
                # Interation {self.current_iterations}

                ## Task Info
                {self.task_info}

                ## Incomplete SBML Model. You can assess it as input_sbml_string.

                {self.incomplete_model.to_string()}

                ## Max iterations
                {self.max_iterations}

                Format your response according to the instructions in the system message.
                """

        return prompt

    def _eval_model(self, code: str) -> None | str:
        try:
            request = CodeRequest(code=code, return_vars=["final_sbml"])
            code_result = self.tools.execute_request(request, safe_globals=self.safe_globals)
            if not code_result.success:
                return f"ERROR: {code_result.error}"
            self.final_sbml = code_result.return_data("final_sbml")
            if not self.final_sbml:
                return "ERROR: final_sbml is not defined in your code. Please define it as a string variable called `final_sbml`."
            pred_sbml = SBML(self.final_sbml)
            self.final_evaluation = self.evaluator(pred_sbml=pred_sbml)
        except Exception as sbml_error:
            return f"{str(sbml_error)}"

    def _parse_response(self, response: str) -> None | str:
                                          
        exp_config = None
        code_request = None
        self.current_code_request = None
        self.current_experiment_request = None

                                   
        markdown_sections = self._extract_markdown_sections(response)
        submit_section = markdown_sections.get("submit", "")

                                                          
        python_pattern = r"```python\s*([\s\S]*?)\s*```"
        python_matches = re.findall(python_pattern, response)

                                                   
        json_pattern = r"```json\s*([\s\S]*?)\s*```"
        json_matches = re.findall(json_pattern, response)

        if submit_section:
            self.submit = True

                                           
        if self.submit or self.test_memorize:
                                                                      
            try:
                code_data = python_matches[0].strip()
            except Exception as e:
                return f"Error parsing response. {str(e)}"
            err_msg = self._eval_model(code_data)
            if err_msg:
                return f"ERROR: {str(err_msg)}"
            else:
                return None

                                                                 
        if not json_matches and not python_matches:
            error = (
                "Your response must include either a Python code block or a JSON experiment block."
            )
            return error

        if json_matches:
            try:
                json_data = json_matches[0].strip()
                                                   
                json_data = re.sub(r"//.*?$", "", json_data, flags=re.MULTILINE)
                experiment_data = json.loads(json_data)

                                                                    
                if isinstance(experiment_data, dict):
                                                                      
                    if "action" not in experiment_data:
                        return "Your experiment must contain either an 'action' field or 'actions' field."

                    action_list = []

                                          
                    if "action" in experiment_data:
                        action = experiment_data["action"]
                        meta_data = experiment_data.get("meta_data", {})

                                               
                        action_result = self._process_action(action, meta_data)
                        if isinstance(action_result, list):
                            action_list.extend(action_result)
                        else:
                            return action_result                        
                else:
                    return "The experiment must be either a dictionary with 'action'/'actions' and 'meta_data' or a list of actions."
                exp_config = ExperimentConfig(
                    experiment_action=action_list,
                    observed_species=[],
                )
                self.current_experiment_request = exp_config
            except json.JSONDecodeError as e:
                return f"Invalid JSON format: {str(e)}"
            except Exception as e:
                return f"Your experiment request is not valid: {str(e)}"

                                    
        if python_matches:
            code_data = str(python_matches[0]).strip()
            code_request = CodeRequest(code=code_data)
            self.code_history[f"iteration_{self.current_iterations}"] = code_data
            self.current_code_request = code_request

        return None

    def _extract_markdown_sections(self, text):
        pass                                                      

             
                                         

                
                                                                           
           
                                                              
        pattern = r"###\s+(.*?)\s*\n(.*?)(?=\n##\s+|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)

        sections = {}
        for header, content in matches:
                                                                       
            header_key = header.strip().lower()
            sections[header_key] = content.strip()

        return sections

    def _process_action(self, action_type, meta_data):
        pass                                                                         

             
                                                                                                 
                                                              

                
                                                          
           
        action_list = []

        try:
            if action_type == "observe":
                                                   
                pass

            elif action_type == "change_initial_concentration":
                                                                                   
                for species_id, value in meta_data.items():
                    action_list.append(f'change_initial_concentration("{species_id}", {value})')

            elif action_type == "knockout_species":
                                                                    
                for species_id, knockout in meta_data.items():
                    if knockout:
                        action_list.append(f'knockout_species("{species_id}")')

            else:
                return f"Unknown experiment action type: {action_type}"

            return action_list
        except Exception as e:
            return f"Error processing experiment action {action_type}: {str(e)}"

    def _receive_valid_response(self, message: str) -> None:
        response = self.llm.return_response(message)
        error_msg = self._parse_response(response)
        self.current_parse_error = error_msg

    def _conduct_experiment(self, exp_config: ExperimentConfig):
        pass                                                                     
                                                  

             
                                                        

                
                             
           
        experiment = Experiment(
            true_sbml=copy.deepcopy(self.complete_model),
            inco_sbml=copy.deepcopy(self.incomplete_model),
        )
        experiment_result = experiment.call_simulator(exp_config)

        self.experiment_request_history[self.current_iterations] = {}
        self.experiment_request_history[self.current_iterations]["request"] = exp_config.to_dict()

        if experiment_result.success:
            experiment_result.set_id(self.current_iterations)
            self.experiment_request_history[self.current_iterations]["success"] = True
            assert experiment_result.time is not None
            assert experiment_result.result is not None
            assert experiment_result.expr_id is not None
            experiment_data = create_dataframe(experiment_result.time, experiment_result.result)
            self.experiment_history[experiment_result.expr_id] = experiment_data
            if len(exp_config.experiment_action) == 0 or any(
                not s.startswith("knockout") for s in exp_config.experiment_action
            ):
                self.parameter_experiment_history[experiment_result.expr_id] = experiment_data
        else:
            self.experiment_request_history[self.current_iterations]["success"] = False
            self.experiment_request_history[self.current_iterations][
                "error_message"
            ] = experiment_result.error_message

        self.current_experiment_result = experiment_result

    def _execute_code(self, code_request: CodeRequest):
        pass                                          

             
                                              

                
                       
           
        assert self.tools is not None
        result = self.tools.execute_request(code_request, safe_globals=self.safe_globals)
        self.current_code_result = result
        self.code_result_history[f"iteration_{self.current_iterations}"] = result.to_string()

    def _format_feedback(
        self,
    ) -> str:
        remaining_iterations = self.max_iterations - self.current_iterations
        self.current_iterations += 1
        print(f"Iteration {self.current_iterations}")
        feedback = "# Observation\n\n"

        if self.test_memorize:
            feedback += "## Parsing error\n"
            feedback += f"{self.current_parse_error}\n"
            return feedback

        if remaining_iterations == 0:
                               
            feedback += dedent(
                """
            You have used up all interactions. Please put your final model as a string variable called `final_sbml` in your code.
            ```python
            final_sbml = ....
            ```
            It is recommended using libsbml to modify `input_sbml_string` rather than write the entire xml on your own.
            """
            ).strip()

        if self.current_parse_error:
            feedback += "## Parsing error\n"
            feedback += f"{self.current_parse_error}\n"
            feedback += f"# Iteration {self.current_iterations}"
            return feedback

        if self.current_experiment_result:
            feedback += self.current_experiment_result.to_string()

        if self.current_code_result:
            feedback += self.current_code_result.to_string()

        feedback += f"## Reminder\n\n ### Remaining Iterations for Interactions:\n"
        feedback += f"- Iterations: {remaining_iterations}/{self.max_iterations}\n\n"

        experiment_history = ", ".join(self.experiment_history.keys())
        variables_global = ", ".join(self.variable_storage.return_variables())

        feedback += dedent(
            f"""
        ### Available Global Variables
        - `input_sbml_string`: Original incomplete model
        - `experiment_history`: Results from all previous experiments ({experiment_history})
        - `shared_variables`: all variables you have saved from the previous iterations. ({variables_global})

        ### Allowed libraires
        {DEFAULT_AVAILABLE_PACKAGES}\n

        Please construct your response according to the thoughts-action markdown format.\n\n\n
        """
        ).strip()

        self.current_experiment_result = None
        self.current_code_result = None
        feedback += f"# Iteration {self.current_iterations}"
        return feedback

    def run_benchmark(self, model: LLM) -> None:
                                                       
        self.initialize_agent(model)
                                                              

                                                                                       
        initial_prompt = self._format_initial_prompt(self.incomplete_model)
        self._receive_valid_response(initial_prompt)

        if self.test_memorize and not self.current_parse_error:
            self._save_results()
            return

        while self.current_iterations <= self.max_iterations + self.eval_debug_rounds:
            if self.current_iterations <= self.max_iterations and not self.submit:
                if self.current_experiment_request:
                    self._conduct_experiment(self.current_experiment_request)
                if self.current_code_request:
                    self._execute_code(self.current_code_request)
            else:
                if not self.current_parse_error:
                    break

            feedback_message = self._format_feedback()
            if self.current_iterations > self.max_iterations:
                self.submit = True
            self._receive_valid_response(feedback_message)

        self._save_results()
