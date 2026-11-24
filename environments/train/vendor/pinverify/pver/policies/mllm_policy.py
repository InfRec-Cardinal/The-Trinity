import os
import json
import random
import re
import io
import base64
from PIL import Image
from omegaconf import OmegaConf

from pver.policies.server_client import ServerClient
from pver.policies.tracker import AttributeStateTracker, estimate_visibility
from pver.policies.fusion import MajorityVoteFusion, WeightedEvidenceFusion, LLMBasedFusion, VetoFusion, AsymmetricThresholdFusion, AttributeMajorityFusion, VisibilityWeightedFusion
from pver.policies.nbv import LLMBasedNBV, RandomNBV

class MLLMPolicy:
                                          
    SECTOR_NAMES = ["front", "front-left", "back-left", "back", "back-right", "front-right"]

    def __init__(self, cfg, client: ServerClient):
        self.cfg = cfg
        self.client = client
        
                      
        prompt_dir = os.path.join(os.path.dirname(__file__), "../../configs/prompts")
        
                                    
        def load_p(name):
            if not name:                        
                return None
            path = os.path.join(prompt_dir, name)
            if os.path.exists(path):
                return OmegaConf.load(path)
                                                     
            path2 = f"configs/prompts/{name}" 
            if os.path.exists(path2):
                return OmegaConf.load(path2)
            return None

        self.p_extract = load_p(self.cfg.prompt.extract_file)
        self.p_verify = load_p(self.cfg.prompt.verify_file)
        self.p_nav = load_p(self.cfg.prompt.nav_file)
        self.p_cat = load_p(self.cfg.prompt.category_file)
        self.p_fusion = load_p(self.cfg.prompt.get("fusion_file", None))
        self.p_merge = load_p(self.cfg.prompt.get("merge_file", None))                   
        
                                                                                          
        self.category_cache_static = {}
        cache_dir = None
        if self.cfg.dataset.get("category_cache_path"):
             try:
                 with open(self.cfg.dataset.category_cache_path, 'r', encoding='utf-8') as f:
                     self.category_cache_static = json.load(f)
                 print(f"Loaded {len(self.category_cache_static)} categories from cache.")
                 cache_dir = os.path.dirname(self.cfg.dataset.category_cache_path)
             except Exception as e:
                 print(f"Failed to load category cache: {e}")

                                                                        
        self.merge_cache_static = {}
        if cache_dir:
            merge_cache_path = os.path.join(cache_dir, "merge_cache.json")
            if os.path.exists(merge_cache_path):
                try:
                    with open(merge_cache_path, 'r', encoding='utf-8') as f:
                        self.merge_cache_static = json.load(f)
                    print(f"Loaded {len(self.merge_cache_static)} merged descriptions from cache.")
                except Exception as e:
                    print(f"Failed to load merge cache: {e}")

                                                                                       
        self.attr_cache_static = {}
        if cache_dir:
            attr_cache_path = os.path.join(cache_dir, "attr_cache.json")
            if os.path.exists(attr_cache_path):
                try:
                    with open(attr_cache_path, 'r', encoding='utf-8') as f:
                        self.attr_cache_static = json.load(f)
                    print(f"Loaded {len(self.attr_cache_static)} attribute extractions from cache.")
                except Exception as e:
                    print(f"Failed to load attr cache: {e}")

        self.tracker = None
        self.visited_views = set()
        self.step_history = []
        
               
        self.target_class = ""
        self.attr_spec = {}
        self.object_id = None
        
        self.yes_votes = 0
        self.no_votes = 0
        
                                    
                          
        fusion_type = self.cfg.method.get("fusion", {}).get("type", "auto")
        if fusion_type == "auto":
                                                                                 
             if self.cfg.env.max_steps == 1:
                 fusion_type = "majority"
             else:
                 fusion_type = "weighted"
                 
        if fusion_type == "majority":
            self.fusion_module = MajorityVoteFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "weighted":
            self.fusion_module = WeightedEvidenceFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "llm":
            if self.p_fusion:
                self.fusion_module = LLMBasedFusion(self.client, self.p_fusion, self.cfg.method.get("fusion"))
            else:
                print(f"[WARN] LLM Fusion requires 'fusion_file' in prompt config. Defaulting to Weighted.")
                self.fusion_module = WeightedEvidenceFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "veto":
            self.fusion_module = VetoFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "asymmetric":
            self.fusion_module = AsymmetricThresholdFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "attr_majority":
            self.fusion_module = AttributeMajorityFusion(self.cfg.method.get("fusion"))
        elif fusion_type == "vis_weighted":
            self.fusion_module = VisibilityWeightedFusion(self.cfg.method.get("fusion"))
        else:
             print(f"[WARN] Unknown fusion type '{fusion_type}', defaulting to Weighted")
             self.fusion_module = WeightedEvidenceFusion(self.cfg.method.get("fusion"))

                       
        nbv_type = self.cfg.method.get("nbv", {}).get("type", "llm")
        if nbv_type == "llm":
            self.nbv_module = LLMBasedNBV(self.client, self.cfg.method.get("nbv"))
        elif nbv_type == "viewhint":
            from pver.policies.nbv import LLMViewHintNBV
            self.nbv_module = LLMViewHintNBV(self.client, self.cfg.method.get("nbv"))
        elif nbv_type == "farthest":
            from pver.policies.nbv import FarthestPointNBV
            self.nbv_module = FarthestPointNBV(self.cfg.method.get("nbv"))
        elif nbv_type == "random":
             self.nbv_module = RandomNBV(self.cfg.method.get("nbv"))
        elif nbv_type == "oracle":
            from pver.policies.nbv import OracleNBV
            self.nbv_module = OracleNBV(self.cfg.method.get("nbv"))
        else:
             self.nbv_module = RandomNBV()           

        
    def reset(self, obs):
        self.tracker = None                              
        self.visited_views = set()
        self.step_history = []
        self.target_class = ""
        self.attr_spec = {}
        
                          
        self.current_abs_idx = obs.get("current_sector", 0)
        self.visited_abs_indices = {self.current_abs_idx}
        self.visited_sector_visibility = {}                                                        
        self._failed_abs_sectors = set()                                 
        self._last_target_abs_idx = None                                           
        
        self.yes_votes = 0
        self.no_votes = 0
        
                          
        self.extraction_dialogue = None
        self.coarse_dialogue = None
        self.merge_dialogue = None                   
        self.merged_description = None                             
        self.query_descs = []
        
                                   
        meta = obs.get("meta", {})
        self.current_episode = meta                        
        query_descs = meta.get("query_descriptions") or meta.get("text_pos") or [""]*3
        self.query_descs = query_descs
                                                                                             
                                                                    
        self.object_id = str(meta.get("query_object_id") or meta.get("object_id") or "unknown")
        
                                                     
        if self.object_id in self.category_cache_static:
            self.target_class = self.category_cache_static[self.object_id].get("pred_coarse", "object")
            self.coarse_dialogue = {"mode": "cache", "result": self.target_class}
        elif self.p_cat:
            prompt = self.p_cat.template.format(
                categories_str='", "'.join(self.p_cat.categories),
                desc1=query_descs[0], desc2=query_descs[1], desc3=query_descs[2]
            )
            res = self.client.call_qwen_text(prompt)
            self.target_class = res.get("text", "bag").strip()
            if self.target_class not in self.p_cat.categories:
                self.target_class = "bag"           
            
            self.coarse_dialogue = {
                "prompt": prompt,
                "response": res.get("text", ""),
                "result": self.target_class
            }
        else:
            self.target_class = "object"                      
        
                                                        
        use_attr_decomp = self.cfg.method.get("use_attribute_decomposition", True)

        if use_attr_decomp:
            if self.object_id in self.attr_cache_static:
                                                 
                cached = self.attr_cache_static[self.object_id]
                self.attr_spec = {"attributes": cached["attributes"]}
                self.extraction_dialogue = {
                    "mode": "cache",
                    "parsed_attributes": cached["attributes"],
                    "cached_target_class": cached.get("target_class", "")
                }
            elif self.p_extract:
                                        
                max_attrs = self.cfg.method.get("max_attributes", 8)
                prompt = self.p_extract.template.format(
                    class_text=self.target_class,
                    desc1=query_descs[0], desc2=query_descs[1], desc3=query_descs[2],
                    max_attrs=max_attrs
                )
                res = self.client.call_qwen_text(prompt)
                response_text = res.get("text", "{}")
                try:
                    self.attr_spec = self._parse_json(response_text)
                except:
                    self.attr_spec = {"attributes": []}

                                                                      
                invalid_values = {"unknown", "unspecified", "not mentioned", "n/a", "none", ""}
                filtered_attrs = []
                for a in self.attr_spec.get("attributes", []):
                    evidence = str(a.get("evidence_phrase", "")).strip().lower()
                    if evidence and evidence not in invalid_values:
                        filtered_attrs.append(a)
                self.attr_spec["attributes"] = filtered_attrs

                                   
                name_counts = {}
                for a in self.attr_spec.get("attributes", []):
                    base_name = a.get("name", "attr")
                    if base_name in name_counts:
                        name_counts[base_name] += 1
                        a["name"] = f"{base_name}_{name_counts[base_name]}"
                    else:
                        name_counts[base_name] = 1
                        a["_original_name"] = base_name

                if any(c > 1 for c in name_counts.values()):
                    for a in self.attr_spec.get("attributes", []):
                        orig = a.get("_original_name")
                        if orig and name_counts.get(orig, 1) > 1:
                            if a["name"] == orig:
                                a["name"] = f"{orig}_1"

                self.extraction_dialogue = {
                    "prompt": prompt,
                    "response": response_text,
                    "parsed_attributes": self.attr_spec.get("attributes", [])
                }
        else:
                                                                    
            query_mode = self.cfg.method.get("query_mode", "direct")
            
            if query_mode == "merged":
                                                                                     
                if self.object_id in self.merge_cache_static:
                                             
                    cached = self.merge_cache_static[self.object_id]
                    merged_text = cached["merged_description"]
                    self.merged_description = merged_text
                    self.merge_dialogue = {
                        "mode": "cache",
                        "merged_result": merged_text
                    }
                elif self.p_merge:
                                            
                    merge_prompt = self.p_merge.template.format(
                        desc1=query_descs[0] if len(query_descs) > 0 else "",
                        desc2=query_descs[1] if len(query_descs) > 1 else "",
                        desc3=query_descs[2] if len(query_descs) > 2 else ""
                    )
                    merge_res = self.client.call_qwen_text(merge_prompt)
                    merged_text = merge_res.get("text", "").strip()

                                             
                    if not merged_text:
                        merged_text = ". ".join([d for d in query_descs if d])

                    self.merged_description = merged_text
                    self.merge_dialogue = {
                        "prompt": merge_prompt,
                        "response": merge_res.get("text", ""),
                        "merged_result": merged_text
                    }
                
                                                                                        
                self.attr_spec = {
                    "attributes": [
                        {"name": "merged_desc", "evidence_phrase": merged_text, "type": "merged"}
                    ]
                }
                self.extraction_dialogue = {"mode": "merged", "merged_description": merged_text}
            else:
                                                                     
                                                                        
                self.attr_spec = {
                    "attributes": [
                        {"name": f"desc_{i+1}", "evidence_phrase": d, "type": "description", "weight": 2}
                        for i, d in enumerate(query_descs) if d
                    ]
                }
                self.extraction_dialogue = {"mode": "direct", "descriptions": query_descs}
                
                      
        attr_names = [a["name"] for a in self.attr_spec.get("attributes", [])]
        self.tracker = AttributeStateTracker(attr_names)

    def act(self, obs):
                                                      
        is_unreachable_nav_fail = False
        if obs.get("navigation_failed") and self._last_target_abs_idx is not None:
            self._failed_abs_sectors.add(self._last_target_abs_idx)
                                                                          
            self.visited_abs_indices.add(self._last_target_abs_idx)
            is_unreachable_nav_fail = True
        self._last_target_abs_idx = None

                                                                           
        env_sector = obs.get("current_sector", -1)
        if env_sector >= 0:
            self.current_abs_idx = env_sector
            self.visited_abs_indices.add(env_sector)
        else:
                                                                             
            print(f"[WARN] current_sector={env_sector}, keeping current_abs_idx={self.current_abs_idx}")
        
                       
        img_path = obs.get("rgb_path")
        if not os.path.exists(img_path):
             pass
             
                                              
        crop_img = None
        
        if self.cfg.method.input_mode == "reference":
            ref_imgs = self._load_ref_images(self.object_id)
            if not ref_imgs:
                 pass
            else:
                 target_img = Image.open(img_path).convert("RGB")
                 crop_img = self._stitch_images(ref_imgs, target_img)
        
        if crop_img is None:
                                         
             box_result = None
             detection_confidence = 1.0                       

             if self.cfg.method.bbox_mode == "gt":
                 meta = obs.get("meta", {})
                 captures = meta.get("captures", [])
                 base_name = os.path.basename(img_path)

                 found_cap = None
                 for cap in captures:
                     c_path = cap.get("rgb_filename") or cap.get("rgb", "")
                     if os.path.basename(c_path) == base_name:
                         found_cap = cap
                         break

                 if found_cap and found_cap.get("mask_bbox_xyxy") is not None:
                     box_result = {"results": [{"score": 1.0, "box": found_cap["mask_bbox_xyxy"]}]}
                     detection_confidence = 1.0                      
                 else:
                                                                                          
                     box_result = {"results": []}
                     detection_confidence = 0.1

             if not box_result:
                            
                 box_result = self.client.call_gdino(img_path, self.target_class)
                 results = box_result.get("results", [])
                 if results:
                     detection_confidence = max(r.get("score", 0.5) for r in results)
                 else:
                     detection_confidence = 0.1

                                                                                           
             if self.cfg.env.max_steps <= 1:
                 detection_confidence = 1.0

             crop_img = self._crop_image(img_path, box_result)
                                               
             if box_result and box_result.get("results"):
                 self._last_bbox_xyxy = box_result["results"][0].get("box")
             else:
                 self._last_bbox_xyxy = None
        else:
                                                      
             detection_confidence = 0.9
             self._last_bbox_xyxy = None
        
                                                                                        
        meta = obs.get("meta", {})
        captures = meta.get("captures", [])
        base_name = os.path.basename(img_path)
        is_visible = True                           
        for cap in captures:
            c_path = cap.get("rgb_filename") or cap.get("rgb", "")
            if os.path.basename(c_path) == base_name:
                is_visible = cap.get("mask_meets_threshold", True)
                break
        self.visited_sector_visibility[self.current_abs_idx] = is_visible

                                                                        
        use_attr_decomp = self.cfg.method.get("use_attribute_decomposition", True)

                                
        step_dialogues = []
        view_states = {}

                                                                    
        vis_scores = None
        if isinstance(self.fusion_module, VisibilityWeightedFusion):
            vis_scores = {}
            for a in self.attr_spec.get("attributes", []):
                vis_scores[a["name"]] = estimate_visibility(
                    a["name"], a.get("evidence_phrase", ""), self.current_abs_idx)

        if use_attr_decomp:
                                                                     
                                                          
            desc1 = self.query_descs[0] if len(self.query_descs) > 0 else ""
            desc2 = self.query_descs[1] if len(self.query_descs) > 1 else ""
            desc3 = self.query_descs[2] if len(self.query_descs) > 2 else ""
            
            attr_list = self.attr_spec.get("attributes", [])
            obj_cat = self.target_class if self.target_class else "object"

                                                            
            skip_verified = self.cfg.method.get("skip_verified_attrs", False)

            if skip_verified:
                                                                                                 
                                                             
                                                                                              
                attrs_to_verify = []
                skipped_attrs = []
                re_verify_attrs = []

                for a in attr_list:
                    attr_name = a["name"]
                    current_state = self.tracker.current_state.get(attr_name, "Missing")

                    if current_state == "Missing":
                                                              
                        attrs_to_verify.append(a)
                    else:
                                                                                       
                        best_conf = self.tracker.get_best_confidence(attr_name)
                        if detection_confidence > best_conf:
                                                                                                
                            attrs_to_verify.append(a)
                            re_verify_attrs.append(attr_name)
                        else:
                                                                               
                            skipped_attrs.append(a)

                unknown_attrs = attrs_to_verify

                if skipped_attrs:
                    skipped_names = [a["name"] for a in skipped_attrs]
                    print(f"[V1 SKIP] Skipping {len(skipped_attrs)} verified attrs (conf <= previous): {skipped_names}")
                if re_verify_attrs:
                    print(f"[V1 RE-VERIFY] Re-verifying {len(re_verify_attrs)} attrs (new conf {detection_confidence:.2f} > previous): {re_verify_attrs}")
            else:
                                                                 
                unknown_attrs = attr_list
                skipped_attrs = []

            for a in unknown_attrs:
                                                                      
                static_hint = a.get("view_hint", "any")
                dynamic_hint = self._generate_dynamic_view_hint(a["name"], static_hint, self.current_abs_idx)

                v_prompt = self.p_verify.template.format(
                    desc1=desc1,
                    desc2=desc2,
                    desc3=desc3,
                    object_category=obj_cat,
                    attr_name=a["name"],
                    expected_value=a.get("evidence_phrase", a["name"]),
                    view_hint=dynamic_hint
                )
                v_res = self.client.call_qwen_vl(crop_img, v_prompt)
                raw_answer = v_res.get("text", "").strip()

                                            
                answer = ""
                reason = ""
                try:
                    parsed = self._parse_json(raw_answer)
                    answer = parsed.get("answer", "").lower()
                    reason = parsed.get("reason", "")
                except:
                    answer = raw_answer.lower()

                state = "Missing"
                if answer.startswith("yes"):
                    state = "Matched"
                elif answer.startswith("no"):
                    state = "Contradictory"
                else:
                    state = "Missing"

                view_states[a["name"]] = state
                step_dialogues.append({
                    "attr": a["name"],
                    "expected": a.get("evidence_phrase", a["name"]),
                    "prompt": v_prompt,
                    "response": raw_answer,
                    "parsed_answer": answer,
                    "reason": reason,
                    "parsed_state": state
                })

                                                                      
            for a in skipped_attrs:
                prev_state = self.tracker.current_state.get(a["name"], "Missing")
                view_states[a["name"]] = prev_state
                step_dialogues.append({
                    "attr": a["name"],
                    "expected": a.get("evidence_phrase", a["name"]),
                    "prompt": "(skipped - already verified)",
                    "response": f"State inherited from previous view: {prev_state}",
                    "parsed_answer": prev_state.lower(),
                    "reason": "attribute already verified in previous views",
                    "parsed_state": prev_state
                })

                                                                                        
            if not is_unreachable_nav_fail:
                self.tracker.update(len(self.visited_views), view_states, detection_confidence, visibility_scores=vis_scores)

                                                                                   
                                                                        

        else:
                                   
            obj_cat = self.target_class if self.target_class else "object"
            query_mode = self.cfg.method.get("query_mode", "direct")
            
            if query_mode == "merged" and self.merged_description:
                                                                     
                direct_prompt = self.p_verify.direct_template.format(
                    desc=self.merged_description,
                    object_category=obj_cat
                )
                d_res = self.client.call_qwen_vl(crop_img, direct_prompt)
                raw_answer = d_res.get("text", "").strip()
                
                                            
                answer = ""
                reason = ""
                try:
                    parsed = self._parse_json(raw_answer)
                    answer = parsed.get("answer", "").lower()
                    reason = parsed.get("reason", "")
                except:
                                              
                    answer = raw_answer.lower()
                
                state = "Missing"
                if answer.startswith("yes"): state = "Matched"
                elif answer.startswith("no"): state = "Contradictory"
                else: state = "Missing"
                
                view_states["merged_desc"] = state
                step_dialogues.append({
                    "type": "merged_verification",
                    "merged_description": self.merged_description,
                    "prompt": direct_prompt,
                    "response": raw_answer,
                    "parsed_answer": answer,
                    "reason": reason,
                    "state": state
                })

                                                                                            
                if not is_unreachable_nav_fail:
                    self.tracker.update(len(self.visited_views), view_states, detection_confidence, visibility_scores=vis_scores)
            else:
                                                              
                direct_results = []
                for i, desc in enumerate(self.query_descs):
                    if not desc: continue
                    direct_prompt = self.p_verify.direct_template.format(
                        desc=desc,
                        object_category=obj_cat
                    )
                    d_res = self.client.call_qwen_vl(crop_img, direct_prompt)
                    raw_answer = d_res.get("text", "").strip()
                    
                                                
                    answer = ""
                    reason = ""
                    try:
                        parsed = self._parse_json(raw_answer)
                        answer = parsed.get("answer", "").lower()
                        reason = parsed.get("reason", "")
                    except:
                        answer = raw_answer.lower()
                    
                    state = "Missing"
                    if answer.startswith("yes"): state = "Matched"
                    elif answer.startswith("no"): state = "Contradictory"
                    else: state = "Missing"
                    
                    name = f"desc_{i+1}"
                    view_states[name] = state
                    step_dialogues.append({
                        "description": desc,
                        "prompt": direct_prompt,
                        "response": raw_answer,
                        "parsed_answer": answer,
                        "reason": reason,
                        "state": state
                    })

                                                                                            
                if not is_unreachable_nav_fail:
                    self.tracker.update(len(self.visited_views), view_states, detection_confidence, visibility_scores=vis_scores)
            
        self.visited_views.add(obs.get("rgb_path"))
        
                                                  
                                                   
        fusion_context = {
            "object_description": ". ".join([d for d in self.query_descs if d]),
            "object_category": self.target_class if self.target_class else "object",
            "query_descs": self.query_descs,
            "attr_spec": self.attr_spec                                              
        }
        
                                                
        fusion_type = self.cfg.method.get("fusion", {}).get("type", "weighted")
        is_final_step = obs.get("step_count", 0) >= self.cfg.env.max_steps - 1
        
                                                                   
                                                                                         
        if fusion_type == "llm" and not is_final_step:
                                                    
            decision = "Unsure"
            reason = "llm_fusion_skipped_not_final"
            fusion_debug = {"mode": "llm_fusion_deferred", "step": obs.get("step_count", 0)}
        else:
            decision, reason, fusion_debug = self.fusion_module.decide(
                tracker_state=self.tracker.current_state,
                tracker_history=self.tracker.history,
                step_count=obs.get("step_count", 0),
                max_steps=self.cfg.env.max_steps,
                attr_spec=self.attr_spec,
                context=fusion_context,
                tracker=self.tracker,
            )

                                           
        decision_mode = self.cfg.method.get("decision_mode", "early_exit")
        final_decision = "Unsure"

                                                                                       
        skip_verified = self.cfg.method.get("skip_verified_attrs", False)

                                                                            
        use_adaptive = isinstance(self.fusion_module, AttributeMajorityFusion)
        use_vis_weighted = isinstance(self.fusion_module, VisibilityWeightedFusion)

        if use_vis_weighted:
                                                                            
            all_verified = self.tracker.evidence_should_stop()
            _adaptive_stop_reason = "evidence_converged" if all_verified else None
        elif use_adaptive:
            remaining      = self.cfg.env.max_steps - obs.get("step_count", 0) - 1
            math_converged = self.tracker.all_converged(remaining)
            _final_attrs = self.tracker.get_final_attr_decisions()
            _all_seen    = bool(_final_attrs) and all(s != "Missing" for s in _final_attrs.values())
            _unanimous   = _all_seen and len(set(_final_attrs.values())) == 1
            all_verified = math_converged or _unanimous
            _adaptive_stop_reason = ("math_converged" if math_converged else "unanimous") if all_verified else None
        else:
                                                                   
            all_verified = all(
                s != "Missing" for s in self.tracker.current_state.values()
            ) if self.tracker.current_state else False

        if decision_mode == "vote_till_end":
                                                                                            
            should_stop = is_final_step or ((use_adaptive or use_vis_weighted or skip_verified) and all_verified)
            if should_stop:
                final_decision = decision if decision != "Unsure" else "No"
                if (use_adaptive or use_vis_weighted) and all_verified and not is_final_step:
                    print(f"[ADAPTIVE STOP] {_adaptive_stop_reason} at step {len(self.visited_views)}, "
                          f"evidence={dict(self.tracker.evidence) if use_vis_weighted else 'N/A'}")
                elif skip_verified and all_verified and not is_final_step:
                    print(f"[EARLY STOP] All attributes verified, stopping at step {len(self.visited_views)}")
        else:
            final_decision = decision
            if decision == "Unsure" and is_final_step:
                final_decision = "No"
             
        action = {"decision": final_decision}
                                                                                              
                                                                                         
        action["_step_prediction"] = decision if decision != "Unsure" else "No"

                                
        nbv_debug = {}
        if final_decision == "Unsure":
                                     
            obj_cat = self.target_class if self.target_class else "object"
            
                                                                         
            desc1 = self.query_descs[0] if len(self.query_descs) > 0 else ""
            desc2 = self.query_descs[1] if len(self.query_descs) > 1 else ""
            desc3 = self.query_descs[2] if len(self.query_descs) > 2 else ""
            raw_desc = ". ".join([d for d in self.query_descs if d])
            obj_desc = raw_desc if raw_desc else "No description available."
            
            context = {
                "object_category": obj_cat,
                "object_description": obj_desc,                                   
                "desc1": desc1,
                "desc2": desc2,
                "desc3": desc3,
                "object_info": f"{obj_cat}: {obj_desc}",
                "query_mode": self.cfg.method.get("query_mode", "attribute"),
                "attr_spec": self.attr_spec,                                    
                                                                    
                "ep_meta": obs.get("meta", {}),
                "current_img_path": obs.get("rgb_path", ""),
                "visited_sector_visibility": self.visited_sector_visibility,
                                             
                "navigation_failed": obs.get("navigation_failed", False),
                "failed_direction": obs.get("failed_direction"),
                "failed_abs_sectors": self._failed_abs_sectors,
                                              
                "target_bbox_xyxy": getattr(self, '_last_bbox_xyxy', None),
                "_current_abs_idx": self.current_abs_idx,
            }
            
            nav_rel, target_abs_idx, nbv_debug = self.nbv_module.decide_next_view(
                tracker_state=self.tracker.current_state,
                img_path=obs["rgb_path"],
                prompt_template=self.p_nav,
                current_abs_idx=self.current_abs_idx,
                visited_abs_indices=self.visited_abs_indices,
                num_sectors=self.cfg.env.sectors,                   
                context=context
            )

                                                                  
            if target_abs_idx == -1:
                final_decision = decision if decision != "Unsure" else "No"
                action["decision"] = final_decision
                action["_nbv_debug"] = nbv_debug
                action["_early_stop"] = True
                action["done"] = True
                print(f"  [Oracle] Early stop: no visible unvisited sectors. Final={final_decision}")
            else:
                action["nav_rel"] = nav_rel
                self._last_target_abs_idx = target_abs_idx

                                                              
                                                                        
                                                                          

                                                             
                if nbv_debug and "prompt" in nbv_debug:
                    action["nav_rel"] = f"{nav_rel} (MLLM-Reasoning)"
                elif nbv_debug and nbv_debug.get("mode") == "random":
                    action["nav_rel"] = f"{nav_rel} (Random)"

                action["_nbv_debug"] = nbv_debug
        else:
            action["nav_rel"] = "front"

                    
        if self.tracker:
            action["_debug_tracker"] = self.tracker.current_state
        
                                                  
        action["_fusion_debug"] = fusion_debug
            
                              
                                                            
        action["_current_abs_sector"] = self.SECTOR_NAMES[self.current_abs_idx % 6]
        action["_visited_abs_sectors"] = [self.SECTOR_NAMES[i % 6] for i in sorted(list(self.visited_abs_indices))]

                                                     
        action["_sector_debug"] = {
            "env_returned_sector": obs.get("current_sector", -1),
            "policy_current_abs_idx": self.current_abs_idx,
            "policy_visited_abs_indices": sorted(list(self.visited_abs_indices)),
            "visited_sector_names": [self.SECTOR_NAMES[i % 6] for i in sorted(list(self.visited_abs_indices))]
        }
        
        action["_coarse_cat"] = self.target_class
        action["_fusion_debug"] = fusion_debug
        action["_reason"] = reason
        action["_coarse_source"] = "Cache" if self.object_id in self.category_cache_static else "Infer"
        action["_detection_confidence"] = detection_confidence                                     
        
        per_attr_results = []
        for attr in self.attr_spec.get("attributes", []):
            name = attr.get("name", "")
            expected = attr.get("evidence_phrase") or attr.get("value", "N/A")
            observed = self.tracker.current_state.get(name, "Unknown")
            local_status = view_states.get(name, "N/A") if 'view_states' in locals() else "N/A"
            
            per_attr_results.append({
                "name": name,
                "expected": expected,
                "observed": local_status,
                "accumulated_status": observed
            })
        action["_per_attribute_results"] = per_attr_results
        action["_step_dialogues"] = step_dialogues

        if len(self.visited_views) == 1:
            if self.extraction_dialogue:
                action["_extraction_dialogue"] = self.extraction_dialogue
            if self.coarse_dialogue:
                action["_coarse_dialogue"] = self.coarse_dialogue
            if self.merge_dialogue:
                action["_merge_dialogue"] = self.merge_dialogue                                 
        
        if crop_img:
            try:
                buf = io.BytesIO()
                crop_img.save(buf, format="JPEG")
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
                action["_debug_crop"] = f"data:image/jpeg;base64,{b64_str}"
            except:
                pass
            
        return action

    def _generate_dynamic_view_hint(self, attr_name: str, static_hint: str, current_sector_idx: int) -> str:
        pass                                                                                                   

             
                                                                  
                                                                                   
                                                                   

                
                                                                                                        
           
                                                      
        if self.tracker and attr_name in self.tracker.current_state:
            state = self.tracker.current_state[attr_name]
            if state == "Matched":
                return "any side (attribute already VERIFIED as matching in previous views - no need to re-verify)"
            elif state == "Contradictory":
                return "any side (attribute already VERIFIED as NOT matching in previous views - no need to re-verify)"
                                                                              

        static_hint = static_hint.lower().strip()

                                                          
        if static_hint == "any":
            return "any side (no preferred viewing angle)"

                                   
        current_pos = self.SECTOR_NAMES[current_sector_idx % 6]

                                                                                                    
                               
        hint_mapping = {
            "front": "front",
            "back": "back",
            "left": "front-left",                                    
            "right": "front-right",
            "front-left": "front-left",
            "front-right": "front-right",
            "back-left": "back-left",
            "back-right": "back-right"
        }

        target_pos = hint_mapping.get(static_hint, static_hint)

                                                  
        if current_pos == target_pos:
            return f"{target_pos} (you are currently at the optimal viewing angle)"
        else:
            return f"{target_pos} (you are currently viewing from {current_pos}, the attribute may not be visible)"

    def _parse_json(self, text):
        text = re.sub(r"```json|```", "", text).strip()
        try:
            return json.loads(text)
        except:
            return {}

    def _load_ref_images(self, obj_id):
        if not obj_id or not self.cfg.dataset.get("image_gt_root"):
            return []
        gt_dir = os.path.join(self.cfg.dataset.image_gt_root, obj_id)
        if not os.path.exists(gt_dir):
            return []
        images = []
        for f in sorted(os.listdir(gt_dir)):
            if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                try:
                    p = os.path.join(gt_dir, f)
                    images.append(Image.open(p).convert("RGB"))
                except:
                    pass
                if len(images) >= 3: break
        return images

    def _stitch_images(self, ref_imgs, target_img):
        s = 336
        grid = Image.new('RGB', (s*2, s*2))
        def place(img, x, y):
            if img:
                img_r = img.resize((s, s))
                grid.paste(img_r, (x, y))
        place(ref_imgs[0] if len(ref_imgs)>0 else None, 0, 0)
        place(ref_imgs[1] if len(ref_imgs)>1 else None, s, 0)
        place(ref_imgs[2] if len(ref_imgs)>2 else None, 0, s)
        place(target_img, s, s)
        return grid

    def _crop_image(self, img_path, gdino_res):
        try:
             img = Image.open(img_path).convert("RGB")
             results = gdino_res.get("results", [])
             if results:
                 best = max(results, key=lambda x: x["score"])
                 box = best["box"]       
                 w,h = img.size
                                                   
                 pad = 3
                 x1 = max(0, min(w, box[0] - pad))
                 y1 = max(0, min(h, box[1] - pad))
                 x2 = max(0, min(w, box[2] + pad))
                 y2 = max(0, min(h, box[3] + pad))
                 if x2 > x1 and y2 > y1:
                     crop = img.crop((x1, y1, x2, y2))
                     cw, ch = crop.size
                     if min(cw, ch) < 512:
                         s = 512.0 / min(cw, ch)
                         new_w, new_h = int(cw * s + 0.5), int(ch * s + 0.5)
                         crop = crop.resize((new_w, new_h), Image.BICUBIC)
                     return crop
             w, h = img.size
             if min(w, h) < 512:
                 s = 512.0 / min(w, h)
                 img = img.resize((int(w * s + 0.5), int(h * s + 0.5)), Image.BICUBIC)
             return img
        except:
             return Image.new("RGB", (224,224))
