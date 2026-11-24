from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List, Optional

class FusionModule(ABC):
    pass                                                          
                     
                                                                       
                                                                          
       

    @abstractmethod
    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]], step_count: int, max_steps: int, attr_spec: Dict, context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        pass                                                                       

             
                                                                          
                                                                                              
                                                        
                                             
                                                                   
                                           
                                                                                               

                
                             
                                                       
                                                         
                                                              
           
        pass


class MajorityVoteFusion(FusionModule):
    pass                                         
                                                                           
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]], step_count: int, max_steps: int, attr_spec: Dict, context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        total = len(tracker_state)
        if total == 0:
            return "Unsure", "No attributes tracked", {}

        yes_cnt = sum(1 for s in tracker_state.values() if s == "Matched")
        no_cnt = sum(1 for s in tracker_state.values() if s == "Contradictory")
        unsure_cnt = sum(1 for s in tracker_state.values() if s == "Missing")

        debug_info = {
            "mode": "majority_vote",
            "yes": yes_cnt,
            "no": no_cnt,
            "unsure": unsure_cnt,
            "total": total
        }

                                                                             
        if yes_cnt == 0 and no_cnt == 0:
             return "No", f"all_unsure({unsure_cnt})->default_no", debug_info

        if yes_cnt > no_cnt:
            return "Yes", f"majority_yes({yes_cnt}:{no_cnt})", debug_info
        elif no_cnt > yes_cnt:
            return "No", f"majority_no({no_cnt}:{yes_cnt})", debug_info
        else:
            return "No", f"tie({yes_cnt}:{no_cnt})->default_no", debug_info


class WeightedEvidenceFusion(FusionModule):
    pass                                                         
                                                                                
                                                             
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
                         
        self.alpha = self.config.get("alpha", 2.0)
        self.beta = self.config.get("beta", 1.0)
        self.contra_block_weight = self.config.get("contra_block_weight", 2.0)
        self.yes_threshold = self.config.get("yes_threshold", 3.0)
        self.yes_threshold_soft = self.config.get("yes_threshold_soft", 2.0)
        self.max_missing_frac = self.config.get("max_missing_frac", 0.3)

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]], step_count: int, max_steps: int, attr_spec: Dict, context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
                                          
                                               
        max_view = 0
        for hist in tracker_history.values():
            for item in hist:
                                                                                 
                vid = item[0]
                if vid > max_view: max_view = vid
        
                                                
        if max_view == 0: max_view = 1           
        
        step_objs = [{"attributes": []} for _ in range(max_view)]

        for name, hist_list in tracker_history.items():
                                   
            attr_def = next((a for a in attr_spec.get("attributes", []) if a.get("name") == name or a.get("_original_name") == name), None)
            weight = int(attr_def.get("weight", 1)) if attr_def else 1
            weight = max(1, min(3, weight))

            for item in hist_list:
                                                    
                if len(item) == 3:
                    view_id, state, confidence = item
                else:
                                                                         
                    view_id, state = item
                    confidence = 1.0

                                          
                if 1 <= view_id <= max_view:
                    step_objs[view_id-1]["attributes"].append({
                        "name": name,
                        "state": state,
                        "weight": weight,
                        "confidence": confidence                  
                    })

                              
        best = {"score": -1e9, "Mw":0, "Cw":0, "Uw":0, "total":0, "idx":-1}
        soft_yes_cnt = 0
        contra_block = False

        for i, obj in enumerate(step_objs):
            Mw = Cw = Uw = 0.0
            attrs = obj.get("attributes", [])
            for a in attrs:
                w = a["weight"]
                conf = a.get("confidence", 1.0)                        
                                                                            
                effective_w = w * conf
                st = a["state"]
                if st == "Matched": Mw += effective_w
                elif st == "Contradictory": Cw += effective_w
                elif st == "Missing": Uw += effective_w
            
            total_w = Mw + Cw + Uw
            score = Mw - self.alpha * Cw - self.beta * Uw
            
                                 
            if Cw >= self.contra_block_weight:
                contra_block = True
            
            if score > best["score"]:
                best.update({"score":score, "Mw":Mw, "Cw":Cw, "Uw":Uw, "total":total_w, "idx":i})
                
            if score >= self.yes_threshold_soft:
                soft_yes_cnt += 1

                           
        debug_info = {
            "mode": "weighted_evidence_fusion",
            "best_step_idx": best["idx"],
            "best_score": best["score"],
            "best_stats": f"Mw={best['Mw']}, Cw={best['Cw']}, Uw={best['Uw']}",
            "contra_block": contra_block,
            "soft_yes_cnt": soft_yes_cnt,
             "hyperparams": {
                "alpha": self.alpha,
                "beta": self.beta,
                "contra_thresh": self.contra_block_weight
            }
        }
        
                                 
        debug_info["_resolved_weights"] = {
             a["name"]: a["weight"] for a in step_objs[0]["attributes"] 
        } if step_objs and step_objs[0].get("attributes") else {}

        if contra_block:
             return "No", "critical_contradiction_in_single_view", debug_info
        
                                                     
        miss_frac = (best["Uw"] / best["total"]) if best["total"] > 0 else 1.0
        debug_info["miss_frac"] = round(miss_frac, 2)

        if (best["score"] >= self.yes_threshold and miss_frac <= self.max_missing_frac) or (soft_yes_cnt >= 2):
            return "Yes", "weighted_evidence_sufficient", debug_info
            
        return "No", f"insufficient_score_{best['score']:.1f}", debug_info


class LLMBasedFusion(FusionModule):
    pass                              
                                                                            
                                                                       
       
    def __init__(self, client, prompt_template, config: Optional[Dict] = None):
        self.client = client
        self.prompt_template = prompt_template
        self.config = config or {}

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]], step_count: int, max_steps: int, attr_spec: Dict, context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        pass                                                                     
        
             
                                                                                          
           
        context = context or {}
        
                                           
                                                             
        view_evidence = {}
        for attr_name, hist_list in tracker_history.items():
            for item in hist_list:
                                                                                 
                if len(item) == 3:
                    view_id, state, _ = item
                else:
                    view_id, state = item
                if view_id not in view_evidence:
                    view_evidence[view_id] = []
                view_evidence[view_id].append((attr_name, state))
        
                                                                  
        attr_value_map = {}
        attr_spec_list = attr_spec.get("attributes", []) if attr_spec else []
        for a in attr_spec_list:
            attr_value_map[a.get("name", "")] = a.get("evidence_phrase", a.get("name", ""))
        
                                                               
        query_descs = context.get("query_descs", [])
        desc_text_map = {}
        for i, desc in enumerate(query_descs):
            desc_text_map[f"desc_{i+1}"] = desc if desc else ""
        
                                                      
        evidence_lines = []
        for view_id in sorted(view_evidence.keys()):
            attrs = view_evidence[view_id]
            matched = []
            contra = []
            missing = []
            
            for attr_name, state in attrs:
                                                                                           
                if attr_name.startswith("desc_"):
                    display_name = f'{attr_name} ("{desc_text_map.get(attr_name, attr_name)}")'
                elif attr_name in attr_value_map:
                    display_name = f"{attr_name} ({attr_value_map[attr_name]})"
                else:
                    display_name = attr_name
                
                if state == "Matched":
                    matched.append(display_name)
                elif state == "Contradictory":
                    contra.append(display_name)
                else:
                    missing.append(display_name)
            
            view_summary = f"**View {view_id}**:"
            if matched:
                view_summary += f"\n  - Matched: {', '.join(matched)}"
            if contra:
                view_summary += f"\n  - Contradicted: {', '.join(contra)}"
            if missing:
                view_summary += f"\n  - Not Visible: {', '.join(missing)}"
            
            evidence_lines.append(view_summary)
        
        multi_view_evidence = "\n\n".join(evidence_lines) if evidence_lines else "No evidence collected."
        num_views = len(view_evidence)
        
                                      
        query_descs = context.get("query_descs", [])
        desc1 = query_descs[0] if len(query_descs) > 0 else ""
        desc2 = query_descs[1] if len(query_descs) > 1 else ""
        desc3 = query_descs[2] if len(query_descs) > 2 else ""
        obj_cat = context.get("object_category", "object")
        
                           
        try:
            fusion_prompt = self.prompt_template.template.format(
                desc1=desc1,
                desc2=desc2,
                desc3=desc3,
                object_category=obj_cat,
                num_views=num_views,
                multi_view_evidence=multi_view_evidence,
                fusion_schema=self.prompt_template.fusion_schema
            )
        except KeyError as e:
            print(f"[LLMFusion] Template Key Error: {e}")
            return "Unsure", "template_error", {"error": str(e)}
        
                                                                  
        result = self.client.call_qwen_text(fusion_prompt)
        text_response = result.get("text", "{}")
        
                        
        import re
        import json
        try:
            json_match = re.search(r'\{[^{}]*\}', text_response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                parsed = json.loads(text_response.replace("```json", "").replace("```", "").strip())
        except Exception as e:
            print(f"[LLMFusion] JSON Parse Error: {e}")
            parsed = {}
        
        decision = parsed.get("decision", "Unsure")
                            
        if decision.lower() in ["yes", "y", "true", "match"]:
            decision = "Yes"
        elif decision.lower() in ["no", "n", "false", "mismatch"]:
            decision = "No"
        else:
            decision = "Unsure"
        
        reason = parsed.get("reason", "LLM-based fusion")
        confidence = parsed.get("confidence", "medium")
        
        debug_info = {
            "mode": "llm_based_fusion",
            "prompt": fusion_prompt,
            "response": text_response,
            "parsed_decision": decision,
            "confidence": confidence,
            "num_views": num_views
        }
        
        return decision, reason, debug_info


class VetoFusion(FusionModule):
    pass                                                                         

              
                                                           
                                                                             

                                                              
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.veto_mode = self.config.get("veto_mode", "strict")
        self.veto_threshold = self.config.get("veto_threshold",
                                               1 if self.veto_mode == "strict" else 2)
        self._fallback = MajorityVoteFusion(config)

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]],
               step_count: int, max_steps: int, attr_spec: Dict,
               context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
                                                            
        contra_attrs = [name for name, state in tracker_state.items()
                        if state == "Contradictory"]
        veto_triggered = len(contra_attrs) >= self.veto_threshold

                                                
        fb_dec, fb_reason, fb_debug = self._fallback.decide(
            tracker_state, tracker_history, step_count, max_steps, attr_spec, context)

        debug_info = {
            "mode": f"veto_{self.veto_mode}",
            "veto_triggered": veto_triggered,
            "veto_attrs": contra_attrs,
            "veto_threshold": self.veto_threshold,
            "contra_count": len(contra_attrs),
            "fallback_decision": fb_dec,
            "fallback_reason": fb_reason,
        }
        debug_info.update(fb_debug)

        if veto_triggered:
            return "No", f"veto({len(contra_attrs)}>={self.veto_threshold})", debug_info

        return fb_dec, f"no_veto->{fb_reason}", debug_info


class AsymmetricThresholdFusion(FusionModule):
    pass                                                                 

                                                                            
                                                                 
                                                                             
                                                                     

                                                                               
                                 
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.no_to_yes_threshold = self.config.get("no_to_yes_threshold", 1.0)
        self.yes_to_no_threshold = self.config.get("yes_to_no_threshold", 0.5)

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]],
               step_count: int, max_steps: int, attr_spec: Dict,
               context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        per_view_votes = self._compute_per_view_votes(tracker_history)

        if not per_view_votes:
            return "No", "no_views", {"mode": "asymmetric", "error": "no_views"}

        anchor = per_view_votes[0]
        subsequent = per_view_votes[1:]
        final = anchor
        flip = False

        if subsequent:
            if anchor == "No":
                yes_frac = sum(1 for v in subsequent if v == "Yes") / len(subsequent)
                if yes_frac >= self.no_to_yes_threshold:
                    final, flip = "Yes", True
            elif anchor == "Yes":
                no_frac = sum(1 for v in subsequent if v == "No") / len(subsequent)
                if no_frac >= self.yes_to_no_threshold:
                    final, flip = "No", True

        debug_info = {
            "mode": "asymmetric",
            "anchor": anchor,
            "per_view_votes": per_view_votes,
            "no_to_yes_threshold": self.no_to_yes_threshold,
            "yes_to_no_threshold": self.yes_to_no_threshold,
            "flip_happened": flip,
        }

        reason = f"anchor={anchor}->{'flip_' + final if flip else 'hold'}"
        return final, reason, debug_info

    def _compute_per_view_votes(self, tracker_history: Dict[str, List]) -> List[str]:
        pass                                                                   
                                     
        all_vids = set()
        for hist in tracker_history.values():
            for item in hist:
                all_vids.add(item[0])                                       

        if not all_vids:
            return []

        votes = []
        for vid in sorted(all_vids):
            matched = 0
            contra = 0
            for hist_list in tracker_history.values():
                for item in hist_list:
                    if item[0] == vid:
                        if item[1] == "Matched":
                            matched += 1
                        elif item[1] == "Contradictory":
                            contra += 1
                                                                   
            votes.append("Yes" if matched > contra and matched > 0 else "No")

        return votes


class AttributeMajorityFusion(FusionModule):
    pass                                                  

                                                            
                                      
                                                                  
                                 

                                                                            
                                                                        
                                     
                                                                               
       

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def decide(self, tracker_state: Dict[str, str], tracker_history: Dict[str, List[Tuple[int, str]]],
               step_count: int, max_steps: int, attr_spec: Dict,
               context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        if tracker is not None:
            final_attrs = tracker.get_final_attr_decisions()
        else:
            final_attrs = tracker_state                                     

        n_matched      = sum(1 for s in final_attrs.values() if s == "Matched")
        n_contradicted = sum(1 for s in final_attrs.values() if s == "Contradicted")
        n_missing      = sum(1 for s in final_attrs.values() if s == "Missing")
        total          = len(final_attrs)

        debug = {
            "mode": "attr_majority",
            "attr_decisions": final_attrs,
            "matched": n_matched,
            "contradicted": n_contradicted,
            "missing": n_missing,
            "total": total,
        }

                                                                     
                                                                         
        if n_matched > n_contradicted:
            return "Yes", f"decisive_majority({n_matched}M>{n_contradicted}C,{n_missing}miss)", debug
        elif n_contradicted > n_matched:
            return "No",  f"decisive_majority({n_contradicted}C>{n_matched}M,{n_missing}miss)", debug
        else:
            return "No",  f"tie_or_no_decisive({n_matched}M={n_contradicted}C,{n_missing}miss)->No", debug


class VisibilityWeightedFusion(FusionModule):
    pass                                      

                                                            
                                                                      
                                                                              

                         
                                                             
                                       
                                       
                                        

                     
                                                              
                                  
                                                                                  
                                                                     
       

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.yes_threshold = self.config.get("yes_threshold", 0.7)
        self.no_threshold = self.config.get("no_threshold", 0.7)
        self.min_evidence = self.config.get("min_evidence", 0.5)

    def decide(self, tracker_state: Dict[str, str],
               tracker_history: Dict[str, List[Tuple[int, str]]],
               step_count: int, max_steps: int, attr_spec: Dict,
               context: Optional[Dict] = None, tracker=None) -> Tuple[str, str, Dict[str, Any]]:
        if tracker is None:
                                                                        
            n_m = sum(1 for s in tracker_state.values() if s == "Matched")
            n_c = sum(1 for s in tracker_state.values() if s == "Contradictory")
            if n_c > n_m:
                return "No", "fallback_majority", {"mode": "vis_weighted", "error": "no_tracker"}
            elif n_m > n_c:
                return "Yes", "fallback_majority", {"mode": "vis_weighted", "error": "no_tracker"}
            return "No", "fallback_tie", {"mode": "vis_weighted", "error": "no_tracker"}

        statuses = tracker.get_evidence_status(
            self.yes_threshold, self.no_threshold, self.min_evidence)
        evidence = tracker.evidence

        n_verified     = sum(1 for s in statuses.values() if s == "verified")
        n_rejected     = sum(1 for s in statuses.values() if s == "rejected")
        n_insufficient = sum(1 for s in statuses.values() if s == "insufficient")
        n_uncertain    = sum(1 for s in statuses.values() if s == "uncertain")
        total          = len(statuses)

        debug = {
            "mode": "vis_weighted",
            "statuses": dict(statuses),
            "evidence": {k: {"yes": round(v["yes"], 3), "no": round(v["no"], 3)}
                         for k, v in evidence.items()},
            "verified": n_verified,
            "rejected": n_rejected,
            "insufficient": n_insufficient,
            "uncertain": n_uncertain,
        }

                           
        if n_rejected > 0:
            return "No", f"rejected({n_rejected}/{total})", debug

                            
        if n_verified == total:
            return "Yes", f"all_verified({n_verified}/{total})", debug

                                                                  
                                                                          
        if n_uncertain == 0 and n_rejected == 0 and n_verified > 0:
            return "Yes", f"verified+insuf({n_verified}V,{n_insufficient}I)", debug

                                                                               
        return "Unsure", f"uncertain({n_verified}V,{n_rejected}R,{n_uncertain}U,{n_insufficient}I)", debug

