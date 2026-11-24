import json
import os
import random
import re
import string
import sys
from collections import OrderedDict
from functools import wraps
from typing import Callable, Dict, List, Optional, Sequence, Tuple, TypeVar

import libsbml
import libsedml
import numpy as np
import pandas as pd

from scigym.api import (
    ExperimentAction,
    ExperimentConstraint,
    ModifyReactionAction,
    ModifySpeciesAction,
    NullifyReactionAction,
    NullifySpeciesAction,
    ParseExperimentActionError,
)

T = TypeVar("T")


def find_latest_timestamp_folder(directory_path):
    pass                                                                                  
                                                                          

         
                                                                                

            
                                                                                   
       
                            
    subdirs = [
        d for d in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, d))
    ]

                                                              
    timestamp_dirs = [d for d in subdirs if re.match(r"\d{8}_\d{6}", d)]

    if not timestamp_dirs:
        return None

                                                                         
                                                        
    timestamp_dirs.sort(reverse=True)                                             

                              
    return timestamp_dirs[0]


def compute_smape(a, b):
    pass                                                                                             

               
               
                        
                                        

            
            
         
                        
       
                                             
    if a.shape != b.shape:
        raise ValueError("Arrays must have the same shape")

                                               
    numerator = np.abs(a - b)
    denominator = np.abs(a) + np.abs(b)

                                                          
    zero_indices = denominator == 0

                                      
    smape_values = np.zeros_like(a, dtype=float)
    non_zero_indices = ~zero_indices
    smape_values[non_zero_indices] = numerator[non_zero_indices] / denominator[non_zero_indices]
                                                                         

                               
    total_smape = np.sum(smape_values) / a.size

    return total_smape


def perturb_concentration_proportional(concentration, relative_noise, min_conc=1e-10):
    pass                                                                                    

               
                                                          
                                                                                        
                                                                       

            
                                           
       
                                                      
    cap_concentration = max(concentration, min_conc)
    noise = np.random.normal(0, relative_noise * cap_concentration)

                                         
    perturbed = concentration + noise

                         
    perturbed = np.maximum(perturbed, 0)

    return perturbed


def print_chat_history_with_tokens(chat_history, output_file="chat_history.txt"):
    pass                                                                                          

         
                                                                
                                            
       
    with open(output_file, "w", encoding="utf-8") as f:
        for key in chat_history:
                                            

                                            
            print(chat_history[key]["user"], file=f)

                                                 
            print(chat_history[key]["assistant"], file=f)

    print(f"Chat history saved to {output_file}")


class SkipNonSerializableEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
                                                                           
            return None


def read_file(file_path):
    pass                                                  
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        sys.exit(1)


def replace_section(content, section_name, replacement):
    pass                                                                                                  
                                                                  

         
                                                            
                                                                                         
                                                                 

            
                                                      
       
    begin_marker = f"<!-- BEGIN {section_name} -->"
    end_marker = f"<!-- END {section_name} -->"

                            
    if begin_marker not in content or end_marker not in content:
        print(f"Warning: Could not find markers for section {section_name}")
        return content

                                                                           
    pattern = re.compile(f"{re.escape(begin_marker)}(.*?){re.escape(end_marker)}", re.DOTALL)

                                                                            
    updated_content = pattern.sub(replacement.strip(), content)

    return updated_content


def update_markdown(template_path, **section_files):
    pass                                                                                        

         
                                                               
                                                            
                                                                                                 
       
                            
    template_content = read_file(template_path)
    updated_content = template_content

                                                
    for section_name, file_path in section_files.items():
        if file_path:
            section_content = read_file(file_path)
            updated_content = replace_section(updated_content, section_name, section_content)

                                                  
    return updated_content


def calculate_stats_dict(dict_list):
    pass                                                                    

         
                                                                                  
                                           

            
                                                                           
       
    if not dict_list:
        return {}

                                        
    sum_pred_mse = 0
    sum_inco_mse = 0
    sum_normalized_mse = 0

                                              
    max_pred_mse = float("-inf")
    max_inco_mse = float("-inf")
    max_normalized_mse = float("-inf")

                                        
    for d in dict_list:
                     
        sum_pred_mse += d["pred_mse"]
        sum_inco_mse += d["inco_mse"]
        sum_normalized_mse += d["normalized_mse"]

                           
        max_pred_mse = max(max_pred_mse, d["pred_mse"])
        max_inco_mse = max(max_inco_mse, d["inco_mse"])
        max_normalized_mse = max(max_normalized_mse, d["normalized_mse"])

                     
    n = len(dict_list)
    mean_pred_mse = sum_pred_mse / n
    mean_inco_mse = sum_inco_mse / n
    mean_normalized_mse = sum_normalized_mse / n

                                                         
    return {
        "mean_pred_mse": mean_pred_mse,
        "mean_inco_mse": mean_inco_mse,
        "mean_normalized_mse": mean_normalized_mse,
        "max_pred_mse": max_pred_mse,
        "max_inco_mse": max_inco_mse,
        "max_normalized_mse": max_normalized_mse,
    }


def display_sample_rows(df, n=3):
    pass                                                                                              

               
               
                         
                                    
                      
                                                   

            
            
       
                                                           
       
                              
    total_rows = len(df)

                            
    mid_start = (total_rows // 2) - (n // 2)

                  
    first_rows = df.head(n)
    middle_rows = df.iloc[mid_start : mid_start + n]
    last_rows = df.tail(n)

                      
    result = "=== First {} rows ===\n".format(n)
    result += first_rows.to_string()
    result += "\n\n=== Middle {} rows ===\n".format(n)
    result += middle_rows.to_string()
    result += "\n\n=== Last {} rows ===\n".format(n)
    result += last_rows.to_string()

    return result


def create_dataframe(time: List[float], result: Dict[str, List[float]]) -> pd.DataFrame:
    pass                                                             

               
                                                                 
                                                                            

            
                                                    
       
                                                                 
    for key, values in result.items():
        if len(values) != len(time):
            raise ValueError(
                f"Length mismatch: 'time' has {len(time)} elements, but '{key}' has {len(values)} elements"
            )

                                                    
    data = result.copy()                              
    data["Time"] = time                                

                          
    df = pd.DataFrame(data)

    return df


def compute_mean_error(
    list_a: List[Dict[str, List[float]]],
    list_b: List[Dict[str, List[float]]],
    species_ids: List[str] | None = None,
):
    pass                                                                              
                                                              

         
                                                                         
                                                                          
                                                                                                      

            
                                                               
       

    total_diff = 0.0
    count = 0

                                               
    for dict_a, dict_b in zip(list_a, list_b):
                          
        if species_ids is None:
            common_keys = set(dict_a.keys()) & set(dict_b.keys())
        else:
            common_keys = set(species_ids) & set(dict_b.keys() & set(dict_a.keys()))

                                                                       
        for key in common_keys:
            list_a_values = dict_a[key]
            list_b_values = dict_b[key]

                                                           
            min_length = min(len(list_a_values), len(list_b_values))

                                                                 
            for i in range(min_length):
                total_diff += abs(list_a_values[i] - list_b_values[i])
                count += 1

                           
    return total_diff / count if count > 0 else 0.0


def find_json(string) -> str:
    start_idx = string.find("{")
    json_str = ""
    if start_idx != -1:
                                                          
        depth = 0
        for i in range(start_idx, len(string)):
            if string[i] == "{":
                depth += 1
            elif string[i] == "}":
                depth -= 1
                if depth == 0:
                                                      
                    json_str = string[start_idx : i + 1]
    return json_str


def conversation_to_ordered_dict(messages):
    pass                                                                         
                                                                   

         
                                                                                               

            
                                                                           
       
    ordered_dict = OrderedDict()
    current_round = 0
    messages = messages[1:]
    for i, message in enumerate(messages):
        role = message["role"]
        try:
            content = find_json(message["content"])
        except:
            content = message["content"]

                                                                  
                                                                    
        key = f"{role} message {i}"

        ordered_dict[key] = content

    return ordered_dict


def dict_to_array(input_dict: Dict[str, List[float]]):
    pass                                                                                      
                               

         
                                                                                   

            
                                                                                 
       
                                               
    all_values = []
    for val_list in input_dict.values():
        all_values.extend(val_list)

                                              
    values_array = np.array(all_values).reshape(-1, 1)

    return values_array


def default_model_parameter(method: Callable[..., T]) -> Callable[..., T]:
    @wraps(method)
    def wrapper(self, object=None, *args, **kwargs):
        if object is None:
            object = self.model
        return method(self, object, *args, **kwargs)

    return wrapper


def default_document_parameter(method: Callable[..., T]) -> Callable[..., T]:
    @wraps(method)
    def wrapper(self, object=None, *args, **kwargs):
        if object is None:
            object = self.document
        return method(self, object, *args, **kwargs)

    return wrapper


def get_experimental_constraint(object: libsbml.SBase) -> ExperimentConstraint:
    can_modify = False
    can_nullify = False

    if object.isSetNotes():
        notes_string = libsbml.XMLNode.convertXMLNodeToString(object.getNotes())
        if "<p>nullable: true</p>" in notes_string:
            can_nullify = True
        if "<p>modifiable: true</p>" in notes_string:
            can_modify = True

    return ExperimentConstraint(
        type_code=object.getTypeCode(),
        id=object.getId(),
        can_modify=can_modify,
        can_nullify=can_nullify,
    )


def generate_new_id(prefix="id_", ban_list=None):
    if ban_list is None:
        ban_list = []
    random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    while f"{prefix}{random_str}" in ban_list:
        random_str = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{prefix}{random_str}"


def load_sedml_from_string_or_file(sedml_string_or_file) -> libsedml.SedDocument:
    doc: libsedml.SedDocument
    if os.path.exists(sedml_string_or_file):
        doc = libsedml.readSedMLFromFile(str(sedml_string_or_file))
    else:
        doc = libsedml.readSedMLFromString(sedml_string_or_file)

    if not isinstance(doc, libsedml.SedDocument):
        raise ValueError("Failed to load SedML document")

    error_log: libsedml.SedErrorLog = doc.getErrorLog()
    if doc.getNumErrors() > 0:
        raise ValueError(error_log.toString())

    return doc.clone()


def check_validity(
    document: libsbml.SBMLDocument,
    model: libsbml.Model,
    original_counts: Dict[str, int] | None = None,
):
    pass                                                                      
                                                               

            
                                                        
       
    issues = []

                                                      
    num_errors = document.validateSBML()
    if num_errors > 0:
        error_log: libsbml.SBMLErrorLog = document.getErrorLog()
        for i in range(error_log.getNumErrors()):
            error: libsbml.SBMLError = error_log.getError(i)
                                                                        
            if error.getSeverity() >= libsbml.LIBSBML_SEV_ERROR:
                issues.append(f"SBML Error: {error.getMessage()}")

                                           
    if model.getNumCompartments() == 0:
        issues.append("Model has no compartments")

    if model.getNumSpecies() == 0:
        issues.append("Model has no species")

    if model.getNumReactions() == 0:
        issues.append("Model has no reactions")

                                      
                                
    for i in range(model.getNumSpecies()):
        species: libsbml.Species = model.getSpecies(i)
        comp_id = species.getCompartment()
        if model.getCompartment(comp_id) is None:
            issues.append(
                f"Species {species.getId()} references non-existent compartment {comp_id}"
            )

                                       
    for i in range(model.getNumReactions()):
        reaction: libsbml.Reaction = model.getReaction(i)

                         
        for j in range(reaction.getNumReactants()):
            reactant: libsbml.SpeciesReference = reaction.getReactant(j)
            species_id = reactant.getSpecies()
            if model.getSpecies(species_id) is None:
                issues.append(
                    f"Reaction {reaction.getId()} references non-existent reactant species {species_id}"
                )

                        
        for j in range(reaction.getNumProducts()):
            product: libsbml.SpeciesReference = reaction.getProduct(j)
            species_id = product.getSpecies()
            if model.getSpecies(species_id) is None:
                issues.append(
                    f"Reaction {reaction.getId()} references non-existent product species {species_id}"
                )

                         
        for j in range(reaction.getNumModifiers()):
            modifier: libsbml.SpeciesReference = reaction.getModifier(j)
            species_id = modifier.getSpecies()
            if model.getSpecies(species_id) is None:
                issues.append(
                    f"Reaction {reaction.getId()} references non-existent modifier species {species_id}"
                )

                               
                                                 
    math_containers = []

                                    
    for i in range(model.getNumReactions()):
        reaction = model.getReaction(i)
        if reaction.isSetKineticLaw():
            math_containers.append((reaction.getId(), "KineticLaw", reaction.getKineticLaw()))

    for i in range(model.getNumRules()):
        rule = model.getRule(i)
        math_containers.append((f"Rule{i}", "Rule", rule))

    for i in range(model.getNumEvents()):
        event: libsbml.Event = model.getEvent(i)
        if event.isSetTrigger():
            math_containers.append((event.getId(), "Trigger", event.getTrigger()))

        for j in range(event.getNumEventAssignments()):
            ea = event.getEventAssignment(j)
            math_containers.append((f"{event.getId()}_assignment_{j}", "EventAssignment", ea))

                                        
    for element_id, element_type, container in math_containers:
        container: libsbml.KineticLaw | libsbml.Rule | libsbml.Trigger | libsbml.EventAssignment
        if hasattr(container, "isSetMath") and container.isSetMath():
            math_obj: libsbml.ASTNode = container.getMath()

                                          
            if math_obj is None:
                issues.append(f"{element_type} in {element_id} has NULL math")
            elif not math_obj.isWellFormedASTNode():
                issues.append(f"{element_type} in {element_id} has malformed math")

                                                
    if document.getLevel() >= 2:
        consistency_check = document.checkConsistency()
        if consistency_check != 0:
            issues.append(f"Model consistency check failed with code {consistency_check}")

                                                        
                                                                         
    if original_counts:
        if model.getNumCompartments() != original_counts.get(
            "compartments", model.getNumCompartments()
        ):
            issues.append("Number of compartments changed during modification")

        if model.getNumSpecies() != original_counts.get("species", model.getNumSpecies()):
            issues.append("Number of species changed during modification")

        if model.getNumReactions() != original_counts.get("reactions", model.getNumReactions()):
            issues.append("Number of reactions changed during modification")

        if model.getNumParameters() != original_counts.get("parameters", model.getNumParameters()):
            issues.append("Number of parameters changed during modification")

                                       
    is_valid = len(issues) == 0
    return is_valid, issues


def compare_dicts(dict1: dict, dict2: dict, abs_tolerance=1e-12, rel_tolerance=1e-9):
    if dict1 == dict2:
        return True

                                         
    only_in_dict1 = {k: dict1[k] for k in dict1 if k not in dict2}
    if only_in_dict1:
        print("Keys only in first dictionary:")
        for k, v in only_in_dict1.items():
            print(f"  {k}: {v}")

                                         
    only_in_dict2 = {k: dict2[k] for k in dict2 if k not in dict1}
    if only_in_dict2:
        print("Keys only in second dictionary:")
        for k, v in only_in_dict2.items():
            print(f"  {k}: {v}")

                                                                                            
    common_keys = set(dict1.keys()) & set(dict2.keys())
    diff_values = {}

    for k in common_keys:
        v1, v2 = dict1[k], dict2[k]

                                          
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                                                         
            abs_diff = abs(v1 - v2)

                                                                                  
            if abs(v1) < abs_tolerance and abs(v2) < abs_tolerance:
                if abs_diff > abs_tolerance:
                    diff_values[k] = (v1, v2)
            else:
                                                          
                max_val = max(abs(v1), abs(v2))
                rel_diff = abs_diff / max_val

                if rel_diff > rel_tolerance and abs_diff > abs_tolerance:
                    diff_values[k] = (v1, v2)
        elif v1 != v2:
            diff_values[k] = (v1, v2)

    if diff_values:
        print(
            f"Keys with values differing beyond tolerances (abs: {abs_tolerance}, rel: {rel_tolerance}):"
        )
        for k, (v1, v2) in diff_values.items():
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                abs_diff = abs(v1 - v2)
                if abs(v1) < abs_tolerance and abs(v2) < abs_tolerance:
                    print(f"  {k}: {v1} != {v2} (abs diff: {abs_diff})")
                else:
                    rel_diff = abs_diff / max(abs(v1), abs(v2))
                    print(f"  {k}: {v1} != {v2} (abs diff: {abs_diff}, rel diff: {rel_diff:.2e})")
            else:
                print(f"  {k}: {v1} != {v2}")

                                                                                     
    are_equal = not (only_in_dict1 or only_in_dict2 or diff_values)
    return are_equal


def subsample_dict(d, n=None):
    pass                                           
    n = n or len(d) // 2                                      
    keys = random.sample(list(d.keys()), min(n, len(d)))
    return {k: d[k] for k in keys}


def subsample_array(d, n=None, seed=42):
    pass                                      
    n = n or len(d) // 2                                      
    random.seed(seed)
    return random.sample(d, min(n, len(d)))


                                                             
def ast_references_species(ast_node: Optional[libsbml.ASTNode], species_id: str) -> bool:
    if ast_node is None:
        return False

                                                            
    if ast_node.isName():
                                                         
        name: Optional[str] = ast_node.getName()
        if name is not None and name == species_id:
            return True

                                    
    for i in range(ast_node.getNumChildren()):
        child_node: libsbml.ASTNode = ast_node.getChild(i)
        if ast_references_species(child_node, species_id):
            return True
    return False


def find_species_references(model: libsbml.Model, species_id: str) -> List[libsbml.SBase]:
    pass                                                                                   

         
                                                    
                                                                  

            
                                                                             
       
                                                             
    sbase_objects: List[libsbml.SBase] = []

                                 
    species: Optional[libsbml.Species] = model.getSpecies(species_id)
    if species is None:
        print(f"Species with ID '{species_id}' not found in the model")
        return sbase_objects

                                  
    reactions: libsbml.ListOfReactions = model.getListOfReactions()
    for i in range(reactions.size()):
        reaction: libsbml.Reaction = reactions.get(i)
        reaction_references_species: bool = False

                         
        reactants: libsbml.ListOfSpeciesReferences = reaction.getListOfReactants()
        for j in range(reactants.size()):
            reactant: libsbml.SpeciesReference = reactants.get(j)
            if reactant.getSpecies() == species_id:
                reaction_references_species = True
                break

        if reaction_references_species:
            sbase_objects.append(reaction)
            continue

                        
        products: libsbml.ListOfSpeciesReferences = reaction.getListOfProducts()
        for j in range(products.size()):
            product: libsbml.SpeciesReference = products.get(j)
            if product.getSpecies() == species_id:
                reaction_references_species = True
                break

        if reaction_references_species:
            sbase_objects.append(reaction)
            continue

                         
        modifiers: libsbml.ListOfSpeciesReferences = reaction.getListOfModifiers()
        for j in range(modifiers.size()):
            modifier: libsbml.ModifierSpeciesReference = modifiers.get(j)
            if modifier.getSpecies() == species_id:
                reaction_references_species = True
                break

        if reaction_references_species:
            sbase_objects.append(reaction)
            continue

                                                                       
        kinetic_law: Optional[libsbml.KineticLaw] = reaction.getKineticLaw()
        if kinetic_law:
                             
            math_node: Optional[libsbml.ASTNode] = kinetic_law.getMath()
            if ast_references_species(math_node, species_id):
                sbase_objects.append(reaction)

                              
    rules: libsbml.ListOfRules = model.getListOfRules()
    for i in range(rules.size()):
        rule: libsbml.Rule = rules.get(i)
        rule_references_species: bool = False

                                                      
        if rule.isAssignment() or rule.isRate():
            variable: str = rule.getVariable()
            if variable == species_id:
                rule_references_species = True

        if rule_references_species:
            sbase_objects.append(rule)
            continue

                                                                
        math_node: Optional[libsbml.ASTNode] = rule.getMath()
        if ast_references_species(math_node, species_id):
            sbase_objects.append(rule)

                                            
    initial_assignments: libsbml.ListOfInitialAssignments = model.getListOfInitialAssignments()
    for i in range(initial_assignments.size()):
        i_assignment: libsbml.InitialAssignment = initial_assignments.get(i)

        symbol: str = i_assignment.getSymbol()
        if symbol == species_id:
            sbase_objects.append(i_assignment)
            continue

                         
        math_node: Optional[libsbml.ASTNode] = i_assignment.getMath()
        if ast_references_species(math_node, species_id):
            sbase_objects.append(i_assignment)

                               
    events: libsbml.ListOfEvents = model.getListOfEvents()
    for i in range(events.size()):
        event: libsbml.Event = events.get(i)
        event_references_species: bool = False

                       
        trigger: Optional[libsbml.Trigger] = event.getTrigger()
        if trigger:
            math_node: Optional[libsbml.ASTNode] = trigger.getMath()
            if ast_references_species(math_node, species_id):
                event_references_species = True

                     
        delay: Optional[libsbml.Delay] = event.getDelay()
        if delay and not event_references_species:
            math_node: Optional[libsbml.ASTNode] = delay.getMath()
            if ast_references_species(math_node, species_id):
                event_references_species = True

                        
        priority: Optional[libsbml.Priority] = event.getPriority()
        if priority and not event_references_species:
            math_node: Optional[libsbml.ASTNode] = priority.getMath()
            if ast_references_species(math_node, species_id):
                event_references_species = True

                                 
        if not event_references_species:
            event_assignments: libsbml.ListOfEventAssignments = event.getListOfEventAssignments()
            for j in range(event_assignments.size()):
                assignment: libsbml.EventAssignment = event_assignments.get(j)

                variable: str = assignment.getVariable()
                if variable == species_id:
                    event_references_species = True
                    break

                math_node: Optional[libsbml.ASTNode] = assignment.getMath()
                if ast_references_species(math_node, species_id):
                    event_references_species = True
                    break

                                                     
        if event_references_species:
            sbase_objects.append(event)

                                    
    constraints: libsbml.ListOfConstraints = model.getListOfConstraints()
    for i in range(constraints.size()):
        constraint: libsbml.Constraint = constraints.get(i)
        math_node: Optional[libsbml.ASTNode] = constraint.getMath()
        if ast_references_species(math_node, species_id):
            sbase_objects.append(constraint)

                                             
    function_defs: libsbml.ListOfFunctionDefinitions = model.getListOfFunctionDefinitions()
    for i in range(function_defs.size()):
        func: libsbml.FunctionDefinition = function_defs.get(i)
        math_node: Optional[libsbml.ASTNode] = func.getMath()
        if ast_references_species(math_node, species_id):
            sbase_objects.append(func)

    return sbase_objects


def find_reaction_references(model: libsbml.Model, reaction_id: str) -> List[libsbml.SBase]:
    pass                                                                                                 
                                                                                                         

         
                                                    
                                                                    

            
                                                                              
       
                                                              
    sbase_objects: List[libsbml.SBase] = []

                                  
    reaction: Optional[libsbml.Reaction] = model.getReaction(reaction_id)
    if reaction is None:
        print(f"Reaction with ID '{reaction_id}' not found in the model")
        return sbase_objects

                                                                  
    def ast_references_reaction(ast_node: Optional[libsbml.ASTNode], reaction_id: str) -> bool:
        if ast_node is None:
            return False

                                                                 
        if ast_node.isName():
                                                              
            name: Optional[str] = ast_node.getName()
            if name is not None and name == reaction_id:
                return True

                                        
        for i in range(ast_node.getNumChildren()):
            child_node: libsbml.ASTNode = ast_node.getChild(i)
            if ast_references_reaction(child_node, reaction_id):
                return True

        return False

                              
                                                                                       
                                                      
    rules: libsbml.ListOfRules = model.getListOfRules()
    for i in range(rules.size()):
        rule: libsbml.Rule = rules.get(i)
        math_node: Optional[libsbml.ASTNode] = rule.getMath()
        if ast_references_reaction(math_node, reaction_id):
            sbase_objects.append(rule)

                                            
                                                                      
    initial_assignments: libsbml.ListOfInitialAssignments = model.getListOfInitialAssignments()
    for i in range(initial_assignments.size()):
        i_assignment: libsbml.InitialAssignment = initial_assignments.get(i)
        math_node: Optional[libsbml.ASTNode] = i_assignment.getMath()
        if ast_references_reaction(math_node, reaction_id):
            sbase_objects.append(i_assignment)

                               
                                                                                        
    events: libsbml.ListOfEvents = model.getListOfEvents()
    for i in range(events.size()):
        event: libsbml.Event = events.get(i)
        event_references_reaction: bool = False

                       
        trigger: Optional[libsbml.Trigger] = event.getTrigger()
        if trigger:
            math_node: Optional[libsbml.ASTNode] = trigger.getMath()
            if ast_references_reaction(math_node, reaction_id):
                event_references_reaction = True

                     
        delay: Optional[libsbml.Delay] = event.getDelay()
        if delay and not event_references_reaction:
            math_node: Optional[libsbml.ASTNode] = delay.getMath()
            if ast_references_reaction(math_node, reaction_id):
                event_references_reaction = True

                        
        priority: Optional[libsbml.Priority] = event.getPriority()
        if priority and not event_references_reaction:
            math_node: Optional[libsbml.ASTNode] = priority.getMath()
            if ast_references_reaction(math_node, reaction_id):
                event_references_reaction = True

                                 
        if not event_references_reaction:
            event_assignments: libsbml.ListOfEventAssignments = event.getListOfEventAssignments()
            for j in range(event_assignments.size()):
                assignment: libsbml.EventAssignment = event_assignments.get(j)
                math_node: Optional[libsbml.ASTNode] = assignment.getMath()
                if ast_references_reaction(math_node, reaction_id):
                    event_references_reaction = True
                    break

                                                      
        if event_references_reaction:
            sbase_objects.append(event)

                                    
                                                                              
    constraints: libsbml.ListOfConstraints = model.getListOfConstraints()
    for i in range(constraints.size()):
        constraint: libsbml.Constraint = constraints.get(i)
        math_node: Optional[libsbml.ASTNode] = constraint.getMath()
        if ast_references_reaction(math_node, reaction_id):
            sbase_objects.append(constraint)

                                             
                                                                                 
    function_defs: libsbml.ListOfFunctionDefinitions = model.getListOfFunctionDefinitions()
    for i in range(function_defs.size()):
        func: libsbml.FunctionDefinition = function_defs.get(i)
        math_node: Optional[libsbml.ASTNode] = func.getMath()
        if ast_references_reaction(math_node, reaction_id):
            sbase_objects.append(func)

                                                        
                                                                     
    reactions: libsbml.ListOfReactions = model.getListOfReactions()
    for i in range(reactions.size()):
        other_reaction: libsbml.Reaction = reactions.get(i)

                                               
        if other_reaction.getId() == reaction_id:
            continue

                                                          
        kinetic_law: Optional[libsbml.KineticLaw] = other_reaction.getKineticLaw()
        if kinetic_law:
            math_node: Optional[libsbml.ASTNode] = kinetic_law.getMath()
            if ast_references_reaction(math_node, reaction_id):
                sbase_objects.append(other_reaction)

                                                                       
                                                                                        
                                            
    if reaction:
        kinetic_law: Optional[libsbml.KineticLaw] = reaction.getKineticLaw()
        if kinetic_law:
            parameters: libsbml.ListOfParameters = kinetic_law.getListOfParameters()
            for i in range(parameters.size()):
                param: libsbml.Parameter = parameters.get(i)
                param_id: str = param.getId()

                                                                   
                for j in range(rules.size()):
                    rule: libsbml.Rule = rules.get(j)
                    if rule.isRate() and rule.getVariable() == param_id:
                                                                        
                        if rule not in sbase_objects:
                            sbase_objects.append(rule)

    return sbase_objects


def find_dangling_objects(model: libsbml.Model) -> Sequence[libsbml.SBase]:
    pass                                                                                      
                                                                      

                                                 
       
                                                                     
    referenced_ids = set()

                                                 
    def collect_ids(node: libsbml.ASTNode):
        if node is None:
            return

        if node.isName():
            referenced_ids.add(node.getName())

        for i in range(node.getNumChildren()):
            collect_ids(node.getChild(i))

                                
    for i in range(model.getNumReactions()):
        reaction: libsbml.Reaction = model.getReaction(i)
        if reaction.isSetKineticLaw():
            klaw: libsbml.KineticLaw = reaction.getKineticLaw()
            if klaw.isSetMath():
                collect_ids(klaw.getMath())

                    
    for i in range(model.getNumRules()):
        rule: libsbml.Rule = model.getRule(i)
        if rule.isSetMath():
            collect_ids(rule.getMath())

                                  
    for i in range(model.getNumInitialAssignments()):
        ia: libsbml.InitialAssignment = model.getInitialAssignment(i)
        if ia.isSetMath():
            collect_ids(ia.getMath())

                          
    for i in range(model.getNumConstraints()):
        constraint: libsbml.Constraint = model.getConstraint(i)
        if constraint.isSetMath():
            collect_ids(constraint.getMath())

                     
    for i in range(model.getNumEvents()):
        event: libsbml.Event = model.getEvent(i)
                       
        if event.isSetTrigger():
            trigger: libsbml.Trigger = event.getTrigger()
            if trigger.isSetMath():
                collect_ids(trigger.getMath())

                     
        if event.isSetDelay():
            delay: libsbml.Delay = event.getDelay()
            if delay.isSetMath():
                collect_ids(delay.getMath())

                                 
        for j in range(event.getNumEventAssignments()):
            ea: libsbml.EventAssignment = event.getEventAssignment(j)
            if ea.isSetMath():
                collect_ids(ea.getMath())

                                   
    for i in range(model.getNumFunctionDefinitions()):
        fd: libsbml.FunctionDefinition = model.getFunctionDefinition(i)
        if fd.isSetMath():
            collect_ids(fd.getMath())

                                                                      
    target_ids = set()
    for i in range(model.getNumRules()):
        rule = model.getRule(i)
        if rule.isSetVariable():
            target_ids.add(rule.getVariable())

    for i in range(model.getNumInitialAssignments()):
        ia = model.getInitialAssignment(i)
        if ia.isSetSymbol():
            target_ids.add(ia.getSymbol())

                                                                                     
    used_ids = referenced_ids.union(target_ids)

                              
    dangling_params: List[libsbml.Parameter] = []
    for i in range(model.getNumParameters()):
        param: libsbml.Parameter = model.getParameter(i)
        if param.getId() not in used_ids:
            dangling_params.append(param)

    return dangling_params


def find_parameter_initializations(model: libsbml.Model, parameter_id: str) -> List[libsbml.SBase]:
    pass                                                                               

                        
                                                    
                                                 
                                           
                                                        

               
               
                         
                                
                      
                                        

            
            
                                    
                                                                           
                                                                  
       
                                   
    parameter: libsbml.Parameter | None = model.getParameter(parameter_id)
    if parameter is None:
        print(f"Parameter '{parameter_id}' not found in the model")
        return []

    objects_to_delete = []

                                                    
    initial_assignments: libsbml.ListOfInitialAssignments = model.getListOfInitialAssignments()
    for i in range(initial_assignments.size()):
        ia: libsbml.InitialAssignment = initial_assignments.get(i)
        if ia.getSymbol() == parameter_id:
            objects_to_delete.append(ia)
                                                                  

                                                              
    rules: libsbml.ListOfRules = model.getListOfRules()
    for i in range(rules.size()):
        rule: libsbml.Rule = rules.get(i)

        if (rule.isAssignment() or rule.isRate()) and rule.getVariable() == parameter_id:
            objects_to_delete.append(rule)
            rule_type = "assignmentRule" if rule.isAssignment() else "rateRule"
                                                            

                                                   
    events: libsbml.ListOfEvents = model.getListOfEvents()
    for i in range(events.size()):
        event: libsbml.Event = events.get(i)
        event_assignments: libsbml.ListOfEventAssignments = event.getListOfEventAssignments()

        for j in range(event_assignments.size()):
            ea: libsbml.EventAssignment = event_assignments.get(j)
            if ea.getVariable() == parameter_id:
                objects_to_delete.append(ea)
                                                                                             

    return objects_to_delete


def find_species_knockout_references(model: libsbml.Model, species_id: str) -> List[libsbml.SBase]:
    pass                                                                             
       
    sbase_objects: List[libsbml.SBase] = []

                                 
    species: Optional[libsbml.Species] = model.getSpecies(species_id)
    if species is None:
        print(f"Species with ID '{species_id}' not found in the model")
        return sbase_objects

                                  
    reactions: libsbml.ListOfReactions = model.getListOfReactions()
    for i in range(reactions.size()):
        reaction: libsbml.Reaction = reactions.get(i)
        reaction_references_species: bool = False

                         
        reactants: libsbml.ListOfSpeciesReferences = reaction.getListOfReactants()
        for j in range(reactants.size()):
            reactant: libsbml.SpeciesReference = reactants.get(j)
            if reactant.getSpecies() == species_id:
                reaction_references_species = True
                break

        if reaction_references_species:
            sbase_objects.append(reaction)
            continue

                        
        products: libsbml.ListOfSpeciesReferences = reaction.getListOfProducts()
        for j in range(products.size()):
            product: libsbml.SpeciesReference = products.get(j)
            if product.getSpecies() == species_id:
                reaction_references_species = True
                break

                         
                                                                                    
                                           
                                                                           
                                                     
                                                    
                       

        if reaction_references_species:
            sbase_objects.append(reaction)
            continue

                              
    rules: libsbml.ListOfRules = model.getListOfRules()
    for i in range(rules.size()):
        rule: libsbml.Rule = rules.get(i)
        rule_references_species: bool = False

                                                      
        if rule.isAssignment() or rule.isRate():
            variable: str = rule.getVariable()
            if variable == species_id:
                rule_references_species = True

                                  
        if rule.isAlgebraic():
            math_node: Optional[libsbml.ASTNode] = rule.getMath()
            if ast_references_species(math_node, species_id):
                rule_references_species = True

        if rule_references_species:
            sbase_objects.append(rule)
            continue

                                            
    initial_assignments: libsbml.ListOfInitialAssignments = model.getListOfInitialAssignments()
    for i in range(initial_assignments.size()):
        i_assignment: libsbml.InitialAssignment = initial_assignments.get(i)

        symbol: str = i_assignment.getSymbol()
        if symbol == species_id:
            sbase_objects.append(i_assignment)
            continue

    return sbase_objects


def process_annotation(annotation: libsbml.XMLNode, rm_prefix=["celldesigner"]):
    pass                                                               

               
                                                 
       
                                                                               
    for i in range(annotation.getNumChildren() - 1, -1, -1):
        child: libsbml.XMLNode = annotation.getChild(i)

                                                       
        prefix = child.getPrefix()
        name = child.getName()

        if prefix in rm_prefix or any([m in name for m in rm_prefix]):
            annotation.removeChild(i)
        else:
                                                        
            if child.getNumChildren() > 0:
                process_annotation(child)


def parse_experiment_action(
    experiment_action: str,
    valid_species_ids: List[str],
    valid_reaction_ids: List[str],
) -> ExperimentAction:
    pass                                                                                          

         
                                                                                   
                                                                
                                                                  

            
                                                            

           
                                                                                       
       
                           
    experiment_action = experiment_action.strip()

                                                              
    change_reaction_regex = (
        r'change_reaction_rate\((?:\\"|")([^\\"]*)(?:\\"|")\s*,\s*([0-9.]+(?:[eE][+-]?[0-9]+)?)\)'
    )
    nullify_reaction_regex = r'deactivate_reaction\((?:\\"|")([^\\"]*)(?:\\"|")\)'
    change_concentration_regex = r'change_initial_concentration\((?:\\"|")([^\\"]*)(?:\\"|")\s*,\s*([0-9.]+(?:[eE][+-]?[0-9]+)?)\)'
    nullify_species_regex = r'knockout_species\((?:\\"|")([^\\"]*)(?:\\"|")\)'

                                       
    match = re.match(change_reaction_regex, experiment_action)
    if match:
        reaction_id = match.group(1)
        multiply_factor = float(match.group(2))

        if reaction_id not in valid_reaction_ids:
            raise ParseExperimentActionError(
                f"Reaction ID '{reaction_id}' is not valid. Valid IDs are: {valid_reaction_ids}"
            )

        return ModifyReactionAction(reaction_id=reaction_id, multiply_factor=multiply_factor)

                                      
    match = re.match(nullify_reaction_regex, experiment_action)
    if match:
        reaction_id = match.group(1)

        if reaction_id not in valid_reaction_ids:
            raise ParseExperimentActionError(
                f"Reaction ID '{reaction_id}' is not valid. Valid IDs are: {valid_reaction_ids}"
            )

        return NullifyReactionAction(reaction_id=reaction_id)

                                               
    match = re.match(change_concentration_regex, experiment_action)
    if match:
        species_id = match.group(1)

        if species_id not in valid_species_ids:
            raise ParseExperimentActionError(
                f"Species ID '{species_id}' is not valid. Valid IDs are: {valid_species_ids}"
            )

        value = float(match.group(2))
        return ModifySpeciesAction(species_id=species_id, value=value)

                                   
    match = re.match(nullify_species_regex, experiment_action)
    if match:
        species_id = match.group(1)

        if species_id not in valid_species_ids:
            raise ParseExperimentActionError(
                f"Species ID '{species_id}' is not valid. Valid IDs are: {valid_species_ids}"
            )

        return NullifySpeciesAction(species_id=species_id)

                                           
    raise ParseExperimentActionError(f"Failed to parse experiment action: {experiment_action}")


def make_random_sequence_of_actions_strings(
    can_nullify_rids: List[str],
    can_nullify_sids: List[str],
    can_modify_rids: List[str],
    can_modify_sids: List[str],
    num_actions: int = 5,
    seed: int = 42,
) -> List[str]:
    pass                                                                                              

         
                                                                    
                                                                   
                                                                  
                                                                 
                                                                                                  
                                                                      
                                                             

            
                                                                            
       
    if seed is not None:
        random.seed(seed)

    action_strings = set()
    action_types = []

    if can_nullify_rids:
        action_types.append("deactivate_reaction")

    if can_nullify_sids:
        action_types.append("knockout_species")

    if can_modify_rids:
        action_types.append("change_reaction_rate")

    if can_modify_sids:
        action_types.append("change_initial_concentration")

    if not action_types:
        return []                                   

    chosen_ids = []

                             
    for _ in range(num_actions):
        action_type = random.choice(action_types)

        if action_type == "deactivate_reaction":
            sid = random.choice(can_nullify_rids)
            if sid in chosen_ids:
                continue
            action = f'deactivate_reaction("{sid}")'

        elif action_type == "knockout_species":
            sid = random.choice(can_nullify_sids)
            if sid in chosen_ids:
                continue
            action = f'knockout_species("{sid}")'

        elif action_type == "change_reaction_rate":
            sid = random.choice(can_modify_rids)
            if sid in chosen_ids:
                continue
            multiplier = round(random.uniform(0.5, 1.5), 2)
            action = f'change_reaction_rate("{sid}", {multiplier})'

        elif action_type == "change_initial_concentration":
            sid = random.choice(can_modify_sids)
            if sid in chosen_ids:
                continue
            multiplier = round(random.uniform(0.5, 1.5), 2)
            action = f'change_initial_concentration("{sid}", {multiplier})'

        else:
            raise ValueError(f"Unexpected action type: {action_type}")

        chosen_ids.append(sid)
        action_strings.add(action)

    return list(action_strings)


def generate_all_possible_action_strings(
    can_nullify_rids: list[str],
    can_nullify_sids: list[str],
    can_modify_rids: list[str],
    can_modify_sids: list[str],
    initial_sid_concentrations: dict[str, float],
    default_rate_multiplier: float = 1.25,
    default_concentration_multiplier: float = 2.0,
) -> list[str]:
    pass                                                                                                    
                                                                               
                                  

         
                                                                    
                                                                   
                                                                  
                                                                 
                                                                                                  
                                                                                                    
                                                                                                     

            
                                                                                         
       
    all_action_strings = []

                                              
    for rid in can_nullify_rids:
        all_action_strings.append(f'deactivate_reaction("{rid}")')

                                             
    for sid in can_nullify_sids:
        all_action_strings.append(f'knockout_species("{sid}")')

                                                         
    for rid in can_modify_rids:
        all_action_strings.append(f'change_reaction_rate("{rid}", {default_rate_multiplier})')

                                                                 
    for sid in can_modify_sids:
                                                                
        all_action_strings.append(
            f'change_initial_concentration("{sid}", {default_rate_multiplier})'
        )

    return all_action_strings


def generate_invalid_action_strings(valid_actions) -> List[Tuple[str, str]]:
    pass                                                                              

         
                                                   

            
                                                             
       
    invalid_actions = []

    for action in valid_actions:
                                   
        if 'deactivate_reaction("' in action:
            rid = action.split('"')[1]
            invalid_actions.append(
                (f"deactivate_reaction({rid})", "Missing quotes around reaction ID")
            )

        if 'knockout_species("' in action:
            sid = action.split('"')[1]
            invalid_actions.append((f"knockout_species({sid})", "Missing quotes around species ID"))

        if 'change_reaction_rate("' in action:
            rid = action.split('"')[1]
            multiplier = action.split(", ")[1].rstrip(")")
            invalid_actions.append(
                (f"change_reaction_rate({rid}, {multiplier})", "Missing quotes around reaction ID")
            )

        if 'change_initial_concentration("' in action:
            sid = action.split('"')[1]
            multiplier = action.split(", ")[1].rstrip(")")
            invalid_actions.append(
                (
                    f"change_initial_concentration({sid}, {multiplier})",
                    "Missing quotes around species ID",
                )
            )

                           
        if 'deactivate_reaction("' in action:
            invalid_actions.append(
                (action.replace('"', "'"), "Using single quotes instead of double quotes")
            )

                             
        if "deactivate_reaction" in action:
            invalid_actions.append((action.rstrip(")"), "Missing closing parenthesis"))
            invalid_actions.append((action.replace("(", ""), "Missing opening parenthesis"))

                      
        if "deactivate_reaction" in action or "knockout_species" in action:
            invalid_actions.append(
                (action.replace("(", " ("), "Extra space before opening parenthesis")
            )

                               
        if 'change_reaction_rate("' in action:
            rid = action.split('"')[1]
            invalid_actions.append(
                (
                    f'change_reaction_rate("{rid}", "1.5")',
                    "String instead of float for rate multiplier",
                )
            )
            invalid_actions.append(
                (
                    f'change_reaction_rate("{rid}", None)',
                    "None instead of float for rate multiplier",
                )
            )
            invalid_actions.append(
                (f'change_reaction_rate("{rid}", -0.5)', "Negative value for rate multiplier")
            )

        if 'change_initial_concentration("' in action:
            sid = action.split('"')[1]
            invalid_actions.append(
                (
                    f'change_initial_concentration("{sid}", "1.0")',
                    "String instead of float for rate multiplier",
                )
            )
            invalid_actions.append(
                (
                    f'change_initial_concentration("{sid}", None)',
                    "None instead of float for rate multiplier",
                )
            )
            invalid_actions.append(
                (
                    f'change_initial_concentration("{sid}", -1.0)',
                    "Negative value for rate multiplier",
                )
            )

                                    
        if 'deactivate_reaction("' in action:
            rid = action.split('"')[1]
            invalid_actions.append(
                (f'deactivate_reaction("{rid}", 1.0)', "Extra parameter for deactivate_reaction")
            )
            invalid_actions.append(
                (f"deactivate_reaction()", "Missing parameter for deactivate_reaction")
            )

        if 'change_reaction_rate("' in action:
            rid = action.split('"')[1]
            invalid_actions.append((f'change_reaction_rate("{rid}")', "Missing rate parameter"))
            invalid_actions.append(
                (f'change_reaction_rate("{rid}", 1.5, "extra")', "Extra parameter")
            )

                                 
        if "deactivate_reaction" in action:
            invalid_actions.append(
                (
                    action.replace("deactivate_reaction", "nullify_reacction"),
                    "Typo in function name",
                )
            )

        if "knockout_species" in action:
            invalid_actions.append(
                (
                    action.replace("knockout_species", "nullifyspecies"),
                    "Missing underscore in function name",
                )
            )

        if "change_reaction_rate" in action:
            invalid_actions.append(
                (
                    action.replace("change_reaction_rate", "change_reactionrate"),
                    "Missing underscore in function name",
                )
            )

        if "change_initial_concentration" in action:
            invalid_actions.append(
                (
                    action.replace("change_initial_concentration", "change_initialconcentration"),
                    "Missing underscore in function name",
                )
            )

                               
        if 'deactivate_reaction("' in action:
            invalid_actions.append(('deactivate_reaction("")', "Empty string as reaction ID"))

        if 'knockout_species("' in action:
            invalid_actions.append(('knockout_species("")', "Empty string as species ID"))

                                                
        if "deactivate_reaction" in action:
            invalid_actions.append(
                (
                    action.replace("deactivate_reaction", "deactivate_reaction"),
                    "Capitalized function name",
                )
            )

                                      
    invalid_actions.extend(
        [
            ("", "Empty string"),
            ('unknown_action("id")', "Unknown action type"),
            ('nullify_both("rid", "sid")', "Non-existent function"),
            ("deactivate_reaction", "Missing parentheses and parameters"),
            ('deactivate_reaction"rid")', "Missing opening parenthesis"),
            ('deactivate_reaction("rid"', "Missing closing parenthesis"),
            ('"deactivate_reaction("rid")"', "Extra quotes around entire action"),
            (
                'deactivate_reaction("rid")knockout_species("sid")',
                "Multiple actions without separator",
            ),
            ("change_reaction_rate(, 1.5)", "Missing ID"),
            ('change_initial_concentration("sid",)', "Missing value after comma"),
            ('change_initial_concentration("sid" 1.5)', "Missing comma between parameters"),
        ]
    )

    return invalid_actions


def shuffle_parameters(model: libsbml.Model):
    n_params = model.getNumParameters()
    param_objects = []
    for i in range(n_params):
        param: libsbml.Parameter = model.getParameter(i)
        param_objects.append(param.clone())
    random.shuffle(param_objects)
    for i in range(n_params - 1, -1, -1):
        model.removeParameter(i)
    for param in param_objects:
        assert model.addParameter(param) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_reactions(model: libsbml.Model):
    n_reactions = model.getNumReactions()
    reaction_objects = []
    for i in range(n_reactions):
        reaction: libsbml.Reaction = model.getReaction(i)
        reaction_objects.append(reaction.clone())
    random.shuffle(reaction_objects)
    for i in range(n_reactions - 1, -1, -1):
        model.removeReaction(i)
    for reaction in reaction_objects:
        assert model.addReaction(reaction) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_species(model: libsbml.Model):
    n_species = model.getNumSpecies()
    species_objects = []
    for i in range(n_species):
        species: libsbml.Species = model.getSpecies(i)
        species_objects.append(species.clone())
    random.shuffle(species_objects)
    for i in range(n_species - 1, -1, -1):
        model.removeSpecies(i)
    for species in species_objects:
        assert model.addSpecies(species) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_rules(model: libsbml.Model):
    n_rules = model.getNumRules()
    rule_objects = []
    for i in range(n_rules):
        rule: libsbml.Rule = model.getRule(i)
        rule_objects.append(rule.clone())
    random.shuffle(rule_objects)
    for i in range(n_rules - 1, -1, -1):
        model.removeRule(i)
    for rule in rule_objects:
        assert model.addRule(rule) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_compartments(model: libsbml.Model):
    n_compartments = model.getNumCompartments()
    compartment_objects = []
    for i in range(n_compartments):
        compartment: libsbml.Compartment = model.getCompartment(i)
        compartment_objects.append(compartment.clone())
    random.shuffle(compartment_objects)
    for i in range(n_compartments - 1, -1, -1):
        model.removeCompartment(i)
    for compartment in compartment_objects:
        assert model.addCompartment(compartment) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_function_definitions(model: libsbml.Model):
    n_function_defs = model.getNumFunctionDefinitions()
    function_def_objects = []
    for i in range(n_function_defs):
        function_def: libsbml.FunctionDefinition = model.getFunctionDefinition(i)
        function_def_objects.append(function_def.clone())
    random.shuffle(function_def_objects)
    for i in range(n_function_defs - 1, -1, -1):
        model.removeFunctionDefinition(i)
    for function_def in function_def_objects:
        assert model.addFunctionDefinition(function_def) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_constraints(model: libsbml.Model):
    n_constraints = model.getNumConstraints()
    constraint_objects = []
    for i in range(n_constraints):
        constraint: libsbml.Constraint = model.getConstraint(i)
        constraint_objects.append(constraint.clone())
    random.shuffle(constraint_objects)
    for i in range(n_constraints - 1, -1, -1):
        model.removeConstraint(i)
    for constraint in constraint_objects:
        assert model.addConstraint(constraint) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_initial_assignments(model: libsbml.Model):
    n_initial_assignments = model.getNumInitialAssignments()
    initial_assignment_objects = []
    for i in range(n_initial_assignments):
        initial_assignment: libsbml.InitialAssignment = model.getInitialAssignment(i)
        initial_assignment_objects.append(initial_assignment.clone())
    random.shuffle(initial_assignment_objects)
    for i in range(n_initial_assignments - 1, -1, -1):
        model.removeInitialAssignment(i)
    for initial_assignment in initial_assignment_objects:
        assert model.addInitialAssignment(initial_assignment) == libsbml.LIBSBML_OPERATION_SUCCESS


def shuffle_unit_definitions(model: libsbml.Model):
    n_unit_definitions = model.getNumUnitDefinitions()
    unit_definition_objects = []
    for i in range(n_unit_definitions):
        unit_definition: libsbml.UnitDefinition = model.getUnitDefinition(i)
        unit_definition_objects.append(unit_definition.clone())
    random.shuffle(unit_definition_objects)
    for i in range(n_unit_definitions - 1, -1, -1):
        model.removeUnitDefinition(i)
    for unit_definition in unit_definition_objects:
        assert model.addUnitDefinition(unit_definition) == libsbml.LIBSBML_OPERATION_SUCCESS


def getAllIds(allElements: libsbml.SBaseList) -> List[str]:
    result = []
    if allElements is None or allElements.getSize() == 0:
        return result
    for i in range(0, allElements.getSize()):
        current: libsbml.SBase = allElements.get(i)
        if current.isSetId():
            result.append(current.getId())
    return result


def getAllNames(allElements: libsbml.SBaseList) -> List[str]:
    result = []
    if allElements is None or allElements.getSize() == 0:
        return result
    for i in range(0, allElements.getSize()):
        current: libsbml.SBase = allElements.get(i)
        if current.isSetName():
            result.append(current.getName())
    return result


def canonicalize_name(original_name):
                                                           
    original = original_name.strip()

                                                                        
    name = re.sub(
        r"\s*\[(cytoplasm|extracellular|mitochondrion|nucleus|vacuole|peroxisome|cell envelope|.*?membrane|.*?particle|.*?reticulum|Golgi|intracellular|.*?matrix|.*?fluid)\]",
        "",
        original,
    )
    name = re.sub(
        r"\s*\((cytoplasm|extracellular|mitochondrion|nucleus|vacuole|peroxisome|cell envelope|.*?membrane|.*?particle|.*?reticulum|Golgi|intracellular|.*?matrix|.*?fluid)\)",
        "",
        name,
    )
    name = re.sub(r"\s*\[.*?\]", "", name)                                 

                                                                                 
    name = re.sub(r"_c0\b|_e0\b|\[c0\]|\[e0\]|\[c\]|\[e\]", "", name)
    name = re.sub(r"N\d+O\d+P*R*\d*S*\d*", "", name)                                      
    name = re.sub(r"C\d+H\d+.*?O\d*|O\d+|\(C\d+H\d+.*?\)", "", name)                            
    name = re.sub(r"__91__.*?__93__", "", name)
    name = re.sub(r"\bM_|\bs_\d+", "", name)                                   
    name = re.sub(r"_\d+$|_\d+\b", "", name)                            

                                                  
    name = re.sub(r"\b(cytop|cyt|nuc|cyto|ext|mito|vac|er|golgi|int|peri|aw|bm)\b", "", name)
    name = re.sub(
        r"(_star|\*|\~.*?|\^[A-Za-z0-9]+|_[A-Za-z]+\d+$)", "", name
    )                        

                                                                                      
                                                                       
    name = re.sub(r"\s*\(\d+-\d+:\d+,\s*\d+-\d+:\d+(?:,\s*\d+-\d+:\d+)*\)", "", name)
    name = re.sub(r"\b(n-C\d+[-:]\d+)\b", "", name)
    name = re.sub(r"\b\d+:\d+\b", "", name)                                           

                                                            
    if ":" in name and not re.search(r"tRNA\([A-Za-z]+\)", name):
        parts = name.split(":")
        if len(parts) > 2:
            name = parts[0] + " complex"
        else:
            name = parts[0] + "-" + parts[1]

                                                                
    name = re.sub(r"([A-Za-z0-9]+)/([A-Za-z0-9]+)", r"\1 \2", name)                        

                                                    
    name = re.sub(r"mw[0-9a-f]{8}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9a-f]{12}", "", name)
    name = re.sub(r"R[a-z0-9]{2}[A-Z]{2}|cam\s+[A-Z]{2}.*?\d+|Dp\s+[A-Za-z]+.*?", "", name)
    name = re.sub(r"Di\d{2}[A-Z]{2}|Da\d{2}[A-Z]{2}", "", name)
    name = re.sub(r"species_\d+", "", name)
    name = re.sub(r"GENE_\w+_\w+|PROTEIN_\w+_\w+|mRNA_\w+_\w+", "", name)
    name = re.sub(r"WTasyn\d+[a-zA-Z]*", "alpha-synuclein", name)                                  

                                         
    name = re.sub(r"chy-\((GlcNAc|Man|Gal|Glc)\)(\d+)", r"\1 oligosaccharide", name)
    name = re.sub(r"\(GlcNAc\)(\d+)\(Man\)(\d+)", "GlcNAc-Man oligosaccharide", name)

                                                  
    name = re.sub(r"(EGF|ErbB\d+|IL\d+|TNF|IFN)[-_]p?(.*?)[-_](\d+|[A-Z]+)", r"\1 \2", name)
    name = re.sub(
        r"p(ERK|MEK|STAT|RAF|RAS)(\d*)", r"\1", name
    )                                       
    name = re.sub(r"complex\s+br\s+\(.*?\)", "protein complex", name)
    name = re.sub(r"dnabound_(\w+)", r"\1", name)                           
    name = re.sub(r"Foxo\d+_Pa\d+_Pd\d+", "Foxo", name)                          

                                                                  
    name = re.sub(r"_+", " ", name)                                   
    name = re.sub(r"\\b|\\n|\\t", " ", name)                                        
    name = re.sub(r"\s+", " ", name)                                       
    name = name.strip()                                      

                                                     
    name = re.sub(r"\bL-|\bD-", "", name)                                             
    name = re.sub(r"@\s+\w+", "", name)                        

                                                                                              
    if not name or len(name) < 3 or re.match(r"^[0-9\s]+$", name):
                                                      
        match = re.search(r"([A-Za-z]+\d*[A-Za-z]*)", original)
        if match:
            return match.group(1)
        return original

    return name
