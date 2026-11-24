import re
from collections import defaultdict
from typing import Dict

import libsbml

from scigym.api import (
    ANONYMIZE_EVERYTHING,
    ANONYMIZE_EVERYTHING_EXCEPT_SPECIES_CONFIG,
    SBML_TYPES_TO_CANONICALIZE,
    SBML_TYPES_TO_NOT_ANONYMIZE,
    CreateQuestionAction,
    RemoveKineticLawAction,
    RemoveReactionAction,
    RemoveSpeciesAction,
)
from scigym.data import SBML


def prepare_sbml_for_benchmark(sbml_raw: SBML, stages=[1, 2, 3, 4]):
    if 1 in stages:
        sbml_raw._remove_metadata(config=ANONYMIZE_EVERYTHING_EXCEPT_SPECIES_CONFIG)
    elif 1.5 in stages:
        sbml_raw._remove_metadata(config=ANONYMIZE_EVERYTHING)

    if 2 in stages:
        sbml_raw.shuffle_all()

    real_to_canonical_names: Dict[int, Dict[str, str]] = defaultdict(dict)
    real_to_fake_ids: Dict[int, Dict[str, str]] = defaultdict(dict)

    if 3 in stages:
        real_to_canonical_names = sbml_raw._canonicalize_names(
            type_codes_to_include=SBML_TYPES_TO_CANONICALIZE
        )
    if 4 in stages:
        real_to_fake_ids = sbml_raw._scramble_ids(type_codes_to_ignore=SBML_TYPES_TO_NOT_ANONYMIZE)
    return real_to_fake_ids, real_to_canonical_names


def parse_action_string(
    action_string: str, id_mapping_dict: Dict[str, Dict[str, str]]
) -> CreateQuestionAction:
    pass                                                                                     

                      
                                                                                 
                                                                                 
                                   

         
                                                            
                                                                                     

            
                                                                                           

           
                                                          
       
                                             
    action_match = re.match(r"(\w+)\(", action_string.strip())
    if not action_match:
        raise ValueError(f"Invalid action string format: {action_string}")

    action_type = action_match.group(1)

                                                                      
                                                                  
    param_pattern = r'\w+\(([\'"])([^\'"]+)\1\)'
    param_match = re.match(param_pattern, action_string.strip())

    if not param_match:
        raise ValueError(f"Invalid parameter format in action string: {action_string}")

                                                                           
    param_value = param_match.group(2)

    reaction_mapping = id_mapping_dict.get(str(libsbml.SBML_REACTION), {})
    species_mapping = id_mapping_dict.get(str(libsbml.SBML_SPECIES), {})

                                                                      
    if action_type == "remove_reaction":
        param_value = reaction_mapping.get(param_value, param_value)
        return RemoveReactionAction(reaction_id=param_value)
    elif action_type == "remove_species":
        param_value = species_mapping.get(param_value, param_value)
        return RemoveSpeciesAction(species_id=param_value)
    elif action_type == "remove_kinetic_law":
        param_value = reaction_mapping.get(param_value, param_value)
        return RemoveKineticLawAction(reaction_id=param_value)
    else:
        raise ValueError(f"Unknown action type: {action_type}")


def merge_two_nested_dictionaries(dict1: Dict, dict2: Dict) -> Dict:
    pass                                                            
    for key, value in dict2.items():
        if key in dict1:
            if isinstance(value, dict):
                dict1[key] = merge_two_nested_dictionaries(dict1[key], value)
            else:
                dict1[key] = value
        else:
            dict1[key] = value
    return dict1
