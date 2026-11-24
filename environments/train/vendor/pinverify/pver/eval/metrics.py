import numpy as np
from typing import List, Dict
from collections import defaultdict

def calculate_metrics(results: List[Dict]):
    pass                      
                          
                     
                                          
                                                      
                     
                          
     
       
    total = len(results)
    if total == 0:
        return {}
        
    correct = sum(1 for r in results if r["is_correct"])
    acc = correct / total
    
    steps = [r["steps"] for r in results]
    asd = np.mean(steps)
    
                             
    pair_types = defaultdict(lambda: {"correct": 0, "total": 0, "correct_eps": [], "wrong_eps": []})
    
    for r in results:
        pt = r.get("pair_type", "unknown")
        pair_types[pt]["total"] += 1
        ep_id = r.get("episode_id", "N/A")
        
        ep_key = f"{r.get('scene_id', 'unknown')}/{ep_id}"
        
        if r["is_correct"]:
            pair_types[pt]["correct"] += 1
            pair_types[pt]["correct_eps"].append(ep_key)
        else:
            pair_types[pt]["wrong_eps"].append(ep_key)
    
                                                    
    pair_type_metrics = {}
    for pt, data in pair_types.items():
        pt_acc = data["correct"] / data["total"] if data["total"] > 0 else 0.0
        pair_type_metrics[pt] = {
            "accuracy": round(pt_acc, 4),
            "correct": data["correct"],
            "total": data["total"],
            "correct_episodes": data["correct_eps"],
            "wrong_episodes": data["wrong_eps"]
        }

                                                                         
    pred_map = {"Yes": 1, "No": 0}

                                            
    pt_groups = defaultdict(list)
    for r in results:
        pt_groups[r.get("pair_type", "unknown")].append(r)

    for pt, pt_results in pt_groups.items():
        if pt not in pair_type_metrics:
            continue
                      
        pt_unreachable = sum(r.get("nav_fail_unreachable", 0) for r in pt_results)
        pt_trap = sum(r.get("nav_fail_trap", 0) for r in pt_results)
                             
        pt_fv_correct = 0
        pt_fv_total = 0
        for r in pt_results:
            fv_pred = r.get("first_view_prediction")
            if fv_pred in pred_map:
                pt_fv_total += 1
                if pred_map[fv_pred] == r.get("label", 1):
                    pt_fv_correct += 1
        pt_fv_acc = round(pt_fv_correct / pt_fv_total, 4) if pt_fv_total > 0 else None
                         
        pt_eff = [r.get("effective_views", r.get("steps", 1)) for r in pt_results]
        pt_avg_eff = round(np.mean(pt_eff), 2) if pt_eff else 0

                                       
        pt_steps = [r.get("steps", 1) for r in pt_results]
        pt_asd = round(np.mean(pt_steps), 2) if pt_steps else 0

        pair_type_metrics[pt]["asd"] = pt_asd
        pair_type_metrics[pt]["nav_fail_unreachable"] = pt_unreachable
        pair_type_metrics[pt]["nav_fail_trap"] = pt_trap
        pair_type_metrics[pt]["first_view_accuracy"] = pt_fv_acc
        pair_type_metrics[pt]["avg_effective_views"] = pt_avg_eff
    
                                                            
    ordered_keys = ["positive", "neg_same", "neg_diff"]
    ordered_metrics = {}
    for k in ordered_keys:
        if k in pair_type_metrics:
            ordered_metrics[k] = pair_type_metrics[k]
                       
    for k in pair_type_metrics:
        if k not in ordered_metrics:
            ordered_metrics[k] = pair_type_metrics[k]
    
    pair_type_metrics = ordered_metrics
    
                                 
    correct_eps = [f"{r.get('scene_id', 'unknown')}/{r.get('episode_id', 'N/A')}" for r in results if r["is_correct"]]
    wrong_eps = [f"{r.get('scene_id', 'unknown')}/{r.get('episode_id', 'N/A')}" for r in results if not r["is_correct"]]

                                                         
    nav_failures_per_ep = [r.get("nav_failures", 0) for r in results]
    total_nav_failures = sum(nav_failures_per_ep)
    eps_with_nav_failure = sum(1 for nf in nav_failures_per_ep if nf > 0)
    total_steps = sum(r.get("steps", 0) for r in results)

    total_unreachable = sum(r.get("nav_fail_unreachable", 0) for r in results)
    total_trap = sum(r.get("nav_fail_trap", 0) for r in results)

    nav_stats = {
        "total_nav_failures": total_nav_failures,
        "nav_fail_unreachable": total_unreachable,
        "nav_fail_trap": total_trap,
        "episodes_with_nav_failure": eps_with_nav_failure,
        "nav_failure_rate_per_step": round(total_nav_failures / total_steps, 4) if total_steps > 0 else 0,
        "nav_failure_rate_per_episode": round(eps_with_nav_failure / total, 4) if total > 0 else 0,
        "avg_nav_failures_per_episode": round(total_nav_failures / total, 2) if total > 0 else 0,
    }

                                                               
    fv_correct = 0
    fv_total = 0
    for r in results:
        fv_pred = r.get("first_view_prediction")
        if fv_pred in pred_map:
            fv_total += 1
            if pred_map[fv_pred] == r.get("label", 1):
                fv_correct += 1
    first_view_accuracy = round(fv_correct / fv_total, 4) if fv_total > 0 else None

                                                                             
    effective_views_list = [r.get("effective_views", r.get("steps", 1)) for r in results]
    avg_effective_views = round(np.mean(effective_views_list), 2) if effective_views_list else 0

    diagnostic_stats = {
        "first_view_accuracy": first_view_accuracy,
        "avg_effective_views": avg_effective_views,
    }

                                                                            
    cat_groups = defaultdict(list)
    for r in results:
        cat = r.get("target_object_category", "unknown")
        cat_groups[cat].append(r)

    per_category = {}
    for cat in sorted(cat_groups.keys()):
        cat_results = cat_groups[cat]
        cat_total = len(cat_results)
        cat_correct = sum(1 for r in cat_results if r["is_correct"])
        cat_acc = cat_correct / cat_total if cat_total > 0 else 0.0

        cat_entry = {
            "total": cat_total,
            "correct": cat_correct,
            "accuracy": round(cat_acc, 4),
        }

                                            
        for pt in ["positive", "neg_same", "neg_diff"]:
            pt_results = [r for r in cat_results if r.get("pair_type") == pt]
            pt_total = len(pt_results)
            pt_correct = sum(1 for r in pt_results if r["is_correct"])
            pt_acc = pt_correct / pt_total if pt_total > 0 else 0.0
            cat_entry[pt] = {
                "total": pt_total,
                "correct": pt_correct,
                "accuracy": round(pt_acc, 4),
            }

        per_category[cat] = cat_entry

    return {
        "accuracy": round(acc, 4),
        "asd": round(asd, 2),
        "total_episodes": total,
        "correct_count": correct,
        "wrong_count": total - correct,
        "nav_stats": nav_stats,
        "diagnostic_stats": diagnostic_stats,
        "correct_episodes": correct_eps,
        "wrong_episodes": wrong_eps,
        "per_pair_type": pair_type_metrics,
        "per_category": per_category,
    }
