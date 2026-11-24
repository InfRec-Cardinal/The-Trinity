from typing import Any, Literal, TypeGuard

import numpy as np

from ale_bench.data import ScoreType
from ale_bench_eval.language_config import ALL_CODE_LANGUAGES_SET, StoredCodeLanguage

VALID_CODE_LANGUAGES = {"", "any", *ALL_CODE_LANGUAGES_SET}


def is_code_language(value: str) -> TypeGuard[StoredCodeLanguage]:
    return value in VALID_CODE_LANGUAGES


def get_solution_info(target_result: dict[str, Any]) -> tuple[StoredCodeLanguage, str]:
    raw_code_language = target_result.get("code_language")
    if not isinstance(raw_code_language, str):
        msg = f"Invalid code language type: {type(raw_code_language)}"
        raise TypeError(msg)
    if not is_code_language(raw_code_language):
        msg = f"Invalid code language: {raw_code_language}"
        raise ValueError(msg)
    raw_code = target_result.get("code")
    if not isinstance(raw_code, str):
        msg = f"Invalid code type: {type(raw_code)}"
        raise TypeError(msg)
    return raw_code_language, raw_code


def get_worst_score(score_type: ScoreType) -> int:
    return -1 if score_type == ScoreType.MAXIMIZE else 1000000000000000000


def select_solution_from_repeated_sampling(
    results_repeated_sampling: dict[int, dict[str, Any]],
    n_repeated_sampling: int,
    selection_method: Literal["best", "median"] = "median",
    score_type: ScoreType = ScoreType.MINIMIZE,
) -> tuple[StoredCodeLanguage, str, int]:
    pass                                                                              

         
                                                                                       
                                                                          
                                                                         
                                                      

            
                                                                        

       
    if not results_repeated_sampling:
        msg = "No results to select from"
        raise ValueError(msg)

    worst_score = get_worst_score(score_type)
                                                 
    index_score_pairs = []

    for idx, result in results_repeated_sampling.items():
        if idx >= n_repeated_sampling:
            continue                                                   
        score = result.get("overall_absolute_score", worst_score)
        index_score_pairs.append((idx, score))

    if not index_score_pairs:
                                                                    
        index_score_pairs = [(0, 0)]

                                                     
    indices = np.array([p[0] for p in index_score_pairs])
    scores = np.array([p[1] for p in index_score_pairs])

                                                      
    if selection_method == "median":
                                                        
        median_score = np.median(scores)
        distances = np.abs(scores - median_score)
        array_idx = np.argmin(distances)
    elif selection_method == "best":
        if score_type == ScoreType.MINIMIZE:
            array_idx = np.argmin(scores)
        elif score_type == ScoreType.MAXIMIZE:
            array_idx = np.argmax(scores)
    else:
        msg = f"Unknown selection method: {selection_method}"
        raise ValueError(msg)

                                                             
    target_index = int(indices[array_idx])

                                      
    target_result = results_repeated_sampling[target_index]
    target_code_language, target_code = get_solution_info(target_result)

    return target_code_language, target_code, target_index


def select_solution_from_self_refine(
    results_self_refine: dict[int, dict[str, Any]],
    score_type: ScoreType = ScoreType.MINIMIZE,
    n_max_refine: int | None = None,
) -> tuple[StoredCodeLanguage, str, int]:
    pass                                                                        
                                                        

         
                                                                                    
                                                      
                                                                                 

            
                                                                        

       
    worst_score = get_worst_score(score_type)
                                                 
    index_score_pairs = []

    for idx, result in results_self_refine.items():
        score = result.get("overall_absolute_score", worst_score)
        if n_max_refine is not None and idx >= n_max_refine:
            continue                                            
        index_score_pairs.append((idx, score))

    if not index_score_pairs:
                                                                    
        index_score_pairs = [(0, 0)]

                                                     
    indices = np.array([p[0] for p in index_score_pairs])
    scores = np.array([p[1] for p in index_score_pairs])

    if score_type == ScoreType.MINIMIZE:
        array_idx = np.argmin(scores)
    elif score_type == ScoreType.MAXIMIZE:
        array_idx = np.argmax(scores)

                                                             
    target_index = int(indices[array_idx])

                                      
    target_result = results_self_refine[target_index]
    target_code_language, target_code = get_solution_info(target_result)

    return target_code_language, target_code, target_index
