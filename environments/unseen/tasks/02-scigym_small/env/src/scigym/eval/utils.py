import math
import re
from typing import Dict, List, Optional, Set, Tuple

import libsbml
import networkx as nx
import numpy as np
from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu

from scigym.api import SBML_GRAPH_PARAMS
from scigym.data import SBML
from scigym.utils.sr_graph import *        


def extract_reaction_edges(reaction: libsbml.Reaction) -> List[Tuple[str, str]]:
    pass                                                        
    reactant_ids: List[str] = [
        reaction.getReactant(j).getSpecies() for j in range(reaction.getNumReactants())
    ]
    product_ids: List[str] = [
        reaction.getProduct(k).getSpecies() for k in range(reaction.getNumProducts())
    ]
    edges: List[Tuple[str, str]] = []
    for reactant_id in reactant_ids:
        for product_id in product_ids:
            edges.append((reactant_id, product_id))
    return edges


def get_reaction_hash(reaction: libsbml.Reaction) -> Tuple[Tuple[int, int, int], Tuple[int, int]]:
    reactant_ids: List[str] = [
        reaction.getReactant(j).getSpecies() for j in range(reaction.getNumReactants())
    ]
    product_ids: List[str] = [
        reaction.getProduct(k).getSpecies() for k in range(reaction.getNumProducts())
    ]
    modifier_ids: List[str] = [
        reaction.getModifier(l).getSpecies() for l in range(reaction.getNumModifiers())
    ]
    rp_hash = (hash(frozenset(reactant_ids)), hash(frozenset(product_ids)))
    rpm_hash = (
        hash(frozenset(reactant_ids)),
        hash(frozenset(product_ids)),
        hash(frozenset(modifier_ids)),
    )
    return rpm_hash, rp_hash


def extract_reaction_hashes(
    model: libsbml.Model,
) -> Tuple[Set[Tuple[int, int, int]], Set[Tuple[int, int]]]:
    reactions: libsbml.ListOfReactions = model.getListOfReactions()

    reaction_hashes_no_modifier: Set[Tuple[int, int]] = set()
    reaction_hashes_full: Set[Tuple[int, int, int]] = set()

    for i in range(reactions.size()):
        rpm_hash, rp_hash = get_reaction_hash(reactions.get(i))
        reaction_hashes_no_modifier.add(rp_hash)
        reaction_hashes_full.add(rpm_hash)

    return reaction_hashes_full, reaction_hashes_no_modifier


def get_correctly_predicted_reaction_ids(
    true_model: libsbml.Model,
    inco_model: libsbml.Model,
    pred_model: libsbml.Model,
) -> Tuple[Set[str], Set[str]]:
    pass                                                                                                   
    true_rpm_hashes, true_rp_hashes = extract_reaction_hashes(true_model)
    inco_rpm_hashes, inco_rp_hashes = extract_reaction_hashes(inco_model)
    rp_rids, rpm_rids = set(), set()
    for reaction in pred_model.getListOfReactions():
        rpm_hash, rp_hash = get_reaction_hash(reaction)
        if rpm_hash in true_rpm_hashes and rpm_hash not in inco_rpm_hashes:
            rpm_rids.add(reaction.getId())
        if rp_hash in true_rp_hashes and rp_hash not in inco_rp_hashes:
            rp_rids.add(reaction.getId())
    return rpm_rids, rp_rids


def plot_sbml_diagram(
    true_sbml_model: SBML,
    pred_sbml_model: SBML,
    inco_sbml_model: SBML,
    save_file_path: str,
) -> None:
    inco_species_ids = set(inco_sbml_model.get_species_ids())
    inco_reaction_ids = set(inco_sbml_model.get_reaction_ids())

    correct_pred_rpm_rids, correct_pred_rp_rids = get_correctly_predicted_reaction_ids(
        true_sbml_model.model, inco_sbml_model.model, pred_sbml_model.model
    )
    diagram = MySBMLDiagram(
        pred_sbml_model.model,
        inco_reaction_ids=inco_reaction_ids,
        inco_species_ids=inco_species_ids,
        correct_pred_rpm_rids=correct_pred_rpm_rids,
        correct_pred_rp_rids=correct_pred_rp_rids,
        **SBML_GRAPH_PARAMS,
    )
    diagram.draw_and_save(str(save_file_path))


def reaction_retrieval_score(
    true_eset: Set[Tuple[str, str]],
    pred_eset: Set[Tuple[str, str]],
) -> Dict[str, float]:
    pass                                                                               
    tp = len(true_eset.intersection(pred_eset))
    fp = len(pred_eset.difference(true_eset))
    fn = len(true_eset.difference(pred_eset))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return dict(precision=precision, recall=recall, f1=f1)


def reaction_jaccard_distance(
    true_eset: Set[Tuple[str, str]],
    pred_eset: Set[Tuple[str, str]],
) -> float:
    pass                                                               
    intersection = len(true_eset.intersection(pred_eset))
    union = len(true_eset.union(pred_eset))
    jaccard_distance = 1 - (intersection / union) if union > 0 else 1
    return jaccard_distance


def calculate_hausdorff_score(
    true_model: libsbml.Model,
    pred_model: libsbml.Model,
) -> Tuple[float, float]:
    pass                                                                                      
                                                                     
                                                                     
       
                                            
    reaction1_edge_sets = {}
    reaction2_edge_sets = {}

    reactions1: libsbml.ListOfReactions = true_model.getListOfReactions()
    reactions2: libsbml.ListOfReactions = pred_model.getListOfReactions()

    for i in range(reactions1.size()):
        reaction: libsbml.Reaction = reactions1.get(i)
        reaction1_edge_sets[reaction.getId()] = set(extract_reaction_edges(reaction))

    for j in range(reactions2.size()):
        reaction: libsbml.Reaction = reactions2.get(j)
        reaction2_edge_sets[reaction.getId()] = set(extract_reaction_edges(reaction))

                                                 
    if len(reaction1_edge_sets) == 0 and len(reaction2_edge_sets) == 0:
        return 0, 0
    if len(reaction1_edge_sets) == 0:
        return 1, 1
    if len(reaction2_edge_sets) == 0:
        return 1, 1

                                                        
    pairwise_reaction_distances = np.zeros(
        (
            len(reaction1_edge_sets),
            len(reaction2_edge_sets),
        )
    )
    for i, true_eset in enumerate(reaction1_edge_sets.values()):
        for j, pred_eset in enumerate(reaction2_edge_sets.values()):
                                                                       
            jaccard_dist = reaction_jaccard_distance(true_eset, pred_eset)
            pairwise_reaction_distances[i, j] = jaccard_dist

                                                                             
    forward_min_distances = np.nanmin(pairwise_reaction_distances, axis=1)
    forward_average_hausdorff = np.nanmean(forward_min_distances)
    assert len(forward_min_distances) == len(reaction1_edge_sets)

                                                                                     
    reverse_minimum_distances = np.nanmin(pairwise_reaction_distances, axis=0)
    reverse_average_hausdorff = np.nanmean(reverse_minimum_distances)
    assert len(reverse_minimum_distances) == len(reaction2_edge_sets)

    return float(forward_average_hausdorff), float(reverse_average_hausdorff)


def extract_rid_to_kinetic_law(model: libsbml.Model) -> Dict[str, libsbml.KineticLaw | None]:
    rid_to_klaw: Dict[str, libsbml.KineticLaw | None] = {}
    reactions: libsbml.ListOfReactions = model.getListOfReactions()
    for j in range(reactions.size()):
        reaction: libsbml.Reaction = reactions.get(j)
        kinetic_law: libsbml.KineticLaw | None = None
        if reaction.isSetKineticLaw():
            kinetic_law = reaction.getKineticLaw()
        rid_to_klaw[reaction.getId()] = kinetic_law
    return rid_to_klaw


def get_vector_norm(series: List[float], type: str = "l2") -> float:
    if type == "l0":
        norm = max(series)
    elif type == "l1":
        norm = sum(map(abs, series))
    elif type == "l2":
        norm = math.sqrt(sum(map(lambda x: pow(x, 2), series)))
    else:
        raise ValueError(f"Norm type not recognized: {type}")
    return norm


def apply_vector_norm(series: List[float], norm: float) -> List[float]:
    if norm > 0:
        return list(map(lambda x: x / norm, series))
    return series


def compute_ged(eval_g: nx.MultiDiGraph, target_g: nx.MultiDiGraph, timeout=30) -> int:
    ged = nx.similarity.graph_edit_distance(
        eval_g,
        target_g,
        node_match=node_match,
        edge_match=edge_match,
        timeout=timeout,
    )
    return ged


def normalized_metric(pred_metric: float, inco_metric: float) -> float:
    pass                                                              
       
    if inco_metric == pred_metric:
        return 1.0
    elif inco_metric == 0:
        return np.inf
    return pred_metric / inco_metric


def tokenize_math_formula(formula):
    formula = re.sub(r"([+\-*/^()=,])", r" \1 ", formula)
    tokens = []
    for token in formula.split():
        tokens.append(token)
    return tokens


def calculate_bleu(reference, candidate, weights=(0.25, 0.25, 0.25, 0.25)) -> float:
    smoothing = SmoothingFunction().method1
    return sentence_bleu(                
        [reference], candidate, weights=weights, smoothing_function=smoothing
    )


def get_average_bleu_from_klaw(k1: libsbml.KineticLaw, k2: libsbml.KineticLaw) -> float:
    if k1 is None or k2 is None:
        return 0
    t1 = tokenize_math_formula(k1.getFormula())
    t2 = tokenize_math_formula(k2.getFormula())
    b1 = calculate_bleu(t1, t2)
    b2 = calculate_bleu(t2, t1)
    return (b1 + b2) / 2


def extract_species_edges_with_modifiers(model: libsbml.Model) -> Set[Tuple[str, str]]:
    pass                                                                
                                                                                      
                           

         
                                                   

            
                                                                                 
       
    edges: Set[Tuple[str, str]] = set()
    reactions: libsbml.ListOfReactions = model.getListOfReactions()

    for i in range(reactions.size()):
        reaction: libsbml.Reaction = reactions.get(i)

                                                
        reactant_ids: List[str] = [
            reaction.getReactant(j).getSpecies() for j in range(reaction.getNumReactants())
        ]
        product_ids: List[str] = [
            reaction.getProduct(k).getSpecies() for k in range(reaction.getNumProducts())
        ]
        modifier_ids: List[str] = [
            reaction.getModifier(l).getSpecies() for l in range(reaction.getNumModifiers())
        ]

                                                       
        all_species = reactant_ids + product_ids + modifier_ids

                                                              
        for idx1 in range(len(all_species)):
            for idx2 in range(idx1 + 1, len(all_species)):
                                                  
                if all_species[idx1] != all_species[idx2]:
                                                                                 
                    edge = sorted([all_species[idx1], all_species[idx2]])
                    edges.add((edge[0], edge[1]))

    return edges


def evaluate_species_interaction_f1(
    true_model: libsbml.Model, pred_model: libsbml.Model
) -> Dict[str, Optional[float]]:
    pass                                                                                                 
                                                                                

         
                                               
                                            

            
                                                              
       
                                                                   
    true_edges = extract_species_edges_with_modifiers(true_model)
    pred_edges = extract_species_edges_with_modifiers(pred_model)

                                                                    
    true_positives = len(true_edges.intersection(pred_edges))
    false_positives = len(pred_edges.difference(true_edges))
    false_negatives = len(true_edges.difference(pred_edges))

                                         
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    if len(true_edges) == 0:
        precision = None
        recall = None
        f1 = None

                    
    return {
        "species_edges_undirected_precision": precision,
        "species_edges_undirected_recall": recall,
        "species_edges_undirected_f1": f1,
    }


def extract_typed_species_edges(model: libsbml.Model) -> Dict[str, Set[Tuple[str, str]]]:
    pass                                                                                                  

         
                                                   

            
                                                                                                        
       
    edge_sets = {"reactant_product": set(), "reactant_modifier": set(), "modifier_product": set()}

    reactions: libsbml.ListOfReactions = model.getListOfReactions()

    for i in range(reactions.size()):
        reaction: libsbml.Reaction = reactions.get(i)

                                                
        reactant_ids: List[str] = [
            reaction.getReactant(j).getSpecies() for j in range(reaction.getNumReactants())
        ]
        product_ids: List[str] = [
            reaction.getProduct(k).getSpecies() for k in range(reaction.getNumProducts())
        ]
        modifier_ids: List[str] = [
            reaction.getModifier(l).getSpecies() for l in range(reaction.getNumModifiers())
        ]

                                       
        for r_id in reactant_ids:
            for p_id in product_ids:
                edge = tuple([r_id, p_id])
                edge_sets["reactant_product"].add(edge)

                                        
        for r_id in reactant_ids:
            for m_id in modifier_ids:
                edge = tuple([r_id, m_id])
                edge_sets["reactant_modifier"].add(edge)

                                       
        for m_id in modifier_ids:
            for p_id in product_ids:
                edge = tuple([m_id, p_id])
                edge_sets["modifier_product"].add(edge)

    return edge_sets


def evaluate_typed_species_interaction_f1(
    true_model: libsbml.Model,
    pred_model: libsbml.Model,
) -> Dict[str, float]:
    pass                                                                       

         
                                               
                                            

            
                                                                                 
       
                                          
    true_edge_sets = extract_typed_species_edges(true_model)
    pred_edge_sets = extract_typed_species_edges(pred_model)

    metrics = {}

                                          
    for edge_type in ["reactant_product", "reactant_modifier", "modifier_product"]:
        true_edges = true_edge_sets[edge_type]
        pred_edges = pred_edge_sets[edge_type]

                                                                        
        true_positives = len(true_edges.intersection(pred_edges))
        false_positives = len(pred_edges.difference(true_edges))
        false_negatives = len(true_edges.difference(pred_edges))

                                             
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0
        )
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

                                                  
        if len(true_edges) == 0:
            precision = None
            recall = None
            f1 = None
                                   
        metrics[f"{edge_type}_precision"] = precision
        metrics[f"{edge_type}_recall"] = recall
        metrics[f"{edge_type}_f1"] = f1

    return metrics


def compute_smape(a: np.ndarray, b: np.ndarray) -> float:
    pass                                                                                             

               
               
                        
                                        

            
            
         
                        
       
                                             
    if a.shape != b.shape:
        return 1

                                               
    numerator = np.abs(a - b)
    denominator = np.abs(a) + np.abs(b)

                                                          
    zero_indices = denominator == 0

                                      
    smape_values = np.zeros_like(a, dtype=float)
    non_zero_indices = ~zero_indices
    smape_values[non_zero_indices] = numerator[non_zero_indices] / denominator[non_zero_indices]
                                                                         

                               
    total_smape = np.sum(smape_values) / a.size

    return total_smape.item()


def compute_dict_smape(dict_a: Dict[str, List[float]], dict_b: Dict[str, List[float]]) -> float:
    pass                                                                     

               
               
                         
                                                           

            
            
         
                                                   
       
                                                
    all_keys = sorted(set(dict_a.keys()) | set(dict_b.keys()))

                                              
                                                  
    array_a = []
    array_b = []

                                                       
    for i, key in enumerate(all_keys):
        if key in dict_a:
            array_a.append(dict_a[key])
        if key in dict_b:
            array_b.append(dict_b[key])

    array_a = np.asarray(array_a)
    array_b = np.asarray(array_b)
                                                     
    return compute_smape(array_a, array_b)
