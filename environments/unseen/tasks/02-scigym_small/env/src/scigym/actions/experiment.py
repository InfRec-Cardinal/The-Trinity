from textwrap import dedent

from scigym.api import (
    ApplyExperimentActionError,
    ExperimentConfig,
    ExperimentResult,
    ParseExperimentActionError,
)
from scigym.data import SBML, Simulator


class Experiment:
    def __init__(
        self,
        true_sbml: SBML,
        inco_sbml: SBML,
    ):
        self.sbml = true_sbml
        self.allowed_functions = [
            "change_initial_concentration",
            "nullify_species",
        ]
        self.whitelisted_species = inco_sbml.get_species_ids()
        self.whitelisted_parameters = inco_sbml.get_parameter_ids()
        self.whitelisted_reactions = inco_sbml.get_reaction_ids()

    def _check_allowed_functions(self, code):
        pass                                                                          

             
                                                                    

                
                                                                         
                                                             
           

        invalid_calls = []

        for call in code:
            if not isinstance(call, str):
                invalid_calls.append(f"Invalid type: {type(call)}, expected string")
                continue
            try:
                function_name = call.split("(")[0].strip()

                if function_name not in self.allowed_functions:
                    invalid_calls.append(call)
            except:
                invalid_calls.append(call)

        if invalid_calls:
            return False, invalid_calls
        else:
            return True, []

    def add_sbml_prefix(self, function_calls, indent_level=0):
        indent = " " * 4 * indent_level
        result = []

        for call in function_calls:
            if not isinstance(call, str):
                continue

            prefixed_call = f"{indent}current_sbml.{call}"
            result.append(prefixed_call)

        return "\n".join(result)

    def call_simulator(self, config: ExperimentConfig) -> ExperimentResult:
                                                                     
        wrong_species = set(config.observed_species) - set(self.whitelisted_species)
        if len(wrong_species) > 0:
            return ExperimentResult(
                success=False,
                error_message=f"Some of the species you requested to observe are not recognized: {wrong_species}",
            )

                                                                     
        try:
            actions = config.experiment_action
            if len(actions) > 0:
                current_sbml = SBML.apply_experiment_actions(
                    sbml=self.sbml,
                    experiment_actions=actions,
                    valid_species_ids=self.whitelisted_species,
                    valid_reaction_ids=self.whitelisted_reactions,
                )
            else:
                current_sbml = self.sbml
        except ParseExperimentActionError as e:
            return ExperimentResult(
                success=False,
                error_message="We were not able to run the experiment with your set experiment actions. "
                + str(e),
            )
        except ApplyExperimentActionError as e:
            return ExperimentResult(
                success=False,
                error_message="We were not able to run the experiment with your set experiment actions. "
                + str(e),
            )

                                                                
        try:
            simulation = Simulator(current_sbml)
            return simulation.run(
                observed_species=config.observed_species,
                rm_concentration_brackets=True,
            )
        except Exception as e:
            print(f"Error during simulation of experiment: {e}")
            return ExperimentResult(
                success=False,
                error_message=dedent(
                    """
                We were not able to run the experiment with your set experiment actions.
                Please scrutinize your protocol and make sure that the experiment you request is sensical.
                """
                ).strip(),
            )
