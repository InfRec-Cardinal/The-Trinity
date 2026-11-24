from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
import re
import json
import random
import numpy as np
import os
from pver.policies.server_client import ServerClient

class NBVModule(ABC):
    pass                                                           
       
                                                   
                                                     
    SECTORS = ["front", "front-left", "back-left", "back", "back-right", "front-right"]
    
    @abstractmethod
    def decide_next_view(self, 
                         tracker_state: Dict[str, str], 
                         img_path: str, 
                         prompt_template: Any,
                         current_abs_idx: int,
                         visited_abs_indices: set,
                         num_sectors: int = 6,
                         context: Optional[Dict] = None) -> Tuple[str, int, Dict[str, Any]]:
        pass                                      

                
                                                                                       
           
        pass
    
    def _get_rel_move(self, start_idx: int, end_idx: int, num_sectors: int) -> str:
        pass                                                          
        diff = (end_idx - start_idx) % num_sectors
        return self.SECTORS[diff]
    
    def _compute_relative_direction_dynamic(self, cur_pos, other_pos, goal_pos, num_sectors=6):
        pass                                                                            
                                                                  
        
             
                                                      
                                                      
                                                    
        
                
                                                             
           
        if not cur_pos or not other_pos or not goal_pos:
            return "front"            
        
                       
        cur_2d = np.array([cur_pos[0], cur_pos[2]])
        other_2d = np.array([other_pos[0], other_pos[2]])
        goal_2d = np.array([goal_pos[0], goal_pos[2]])
        
                                                       
        goal_to_cur = cur_2d - goal_2d
        cur_norm = np.linalg.norm(goal_to_cur)
        if cur_norm < 1e-6:
            return "front"
        goal_to_cur = goal_to_cur / cur_norm
        cur_angle = np.arctan2(goal_to_cur[1], goal_to_cur[0])
        
                                                   
        goal_to_other = other_2d - goal_2d
        other_norm = np.linalg.norm(goal_to_other)
        if other_norm < 1e-6:
            return "front"
        goal_to_other = goal_to_other / other_norm
        other_angle = np.arctan2(goal_to_other[1], goal_to_other[0])
        
                                                      
        diff = other_angle - cur_angle
                                
        while diff > np.pi:
            diff -= 2 * np.pi
        while diff < -np.pi:
            diff += 2 * np.pi
        
                                        
        sector_span = 2 * np.pi / num_sectors                            
        
                                          
                                                               
                                                    
        angle_to_sector = {
            0: "front",
            1: "front-left",
            2: "back-left",
            3: "back",
            4: "back-right",
            5: "front-right"
        }
        
                                      
                                                                                   
                                                                   
        sector_idx = int(round(diff / sector_span)) % num_sectors
        
        return angle_to_sector.get(sector_idx, "front")

class LLMBasedNBV(NBVModule):
    def __init__(self, client: ServerClient, config: Optional[Dict] = None):
        self.client = client
        self.config = config or {}

    def decide_next_view(self, tracker_state, img_path, prompt_template, current_abs_idx, visited_abs_indices, num_sectors: int = 6, context: Optional[Dict] = None) -> Tuple[str, int, Dict[str, Any]]:
        if not prompt_template:
            return "front", current_abs_idx, {}
        
        context = context or {}
        
                                                
        def get_name(idx):
             return self.SECTORS[idx % 6]

                                                            
        ep_meta = context.get("ep_meta", {})
        captures = ep_meta.get("captures", [])
        goal_pos = ep_meta.get("goal_position_nominal")
        current_img_path = context.get("current_img_path", "")
        
                                         
        cur_pos = None
        current_basename = os.path.basename(current_img_path) if current_img_path else ""
        for cap in captures:
            cap_path = cap.get("rgb_filename") or cap.get("rgb", "")
            if os.path.basename(cap_path) == current_basename:
                cur_pos = cap.get("camera_position")
                break
        
                                                            
        visited_names = []
        visited_rel_indices = []                                 
        use_dynamic = cur_pos and goal_pos and captures
        
        if use_dynamic:
                                                                 
            sector_to_pos = {}
            
                                                          
            first_cap = captures[0]
            first_pos = first_cap.get("camera_position")
            if first_pos and goal_pos:
                ref_dx = first_pos[0] - goal_pos[0]
                ref_dz = first_pos[2] - goal_pos[2]
                ref_angle = np.arctan2(ref_dz, ref_dx)
                
                                                        
                sector_span = 2 * np.pi / num_sectors
                for cap in captures:
                    cap_pos_data = cap.get("camera_position")
                    if cap_pos_data:
                        dx = cap_pos_data[0] - goal_pos[0]
                        dz = cap_pos_data[2] - goal_pos[2]
                        angle = np.arctan2(dz, dx)
                        diff = (angle - ref_angle) % (2 * np.pi)
                        sector_id = int(round(diff / sector_span)) % num_sectors
                        
                                                                             
                        if sector_id not in sector_to_pos:
                            sector_to_pos[sector_id] = cap_pos_data
            
                                                                
            for visited_sector in sorted(list(visited_abs_indices)):
                if visited_sector in sector_to_pos:
                    v_pos = sector_to_pos[visited_sector]
                    rel_dir = self._compute_relative_direction_dynamic(cur_pos, v_pos, goal_pos, num_sectors)
                    visited_names.append(rel_dir)
                                                                             
                    rel_idx = self.SECTORS.index(rel_dir)
                    visited_rel_indices.append(rel_idx)
                else:
                                                   
                    rel_idx = (visited_sector - current_abs_idx) % 6
                    visited_names.append(get_name(rel_idx))
                    visited_rel_indices.append(rel_idx)
        else:
                                                
            visited_rel_indices = [(i - current_abs_idx) % 6 for i in sorted(list(visited_abs_indices))]
            visited_names = [get_name(i) for i in visited_rel_indices]
        
        current_name_absolute = get_name(current_abs_idx)

                               
        visited_directions = ", ".join(visited_names) if visited_names else "None"

                                                          
        visited_sector_visibility = context.get("visited_sector_visibility", {})
        visibility_warning = ""
        if visited_sector_visibility and any(v is False for v in visited_sector_visibility.values()):
            vis_lines = []
            for i, visited_sector in enumerate(sorted(list(visited_abs_indices))):
                rel_name = visited_names[i] if i < len(visited_names) else get_name((visited_sector - current_abs_idx) % num_sectors)
                vis = visited_sector_visibility.get(visited_sector)
                if vis is False:
                    vis_lines.append(f"  - {rel_name}: target NOT visible (trap view)")
                elif vis is True:
                    vis_lines.append(f"  - {rel_name}: target visible")
            visibility_warning = (
                "**Visibility Warning**:\n" + "\n".join(vis_lines) + "\n"
                "Note: Some visited directions were trap views where the target was not visible. "
                "Adjacent sectors may also be trap views. Prioritize directions away from trap views."
            )

                                     
        if context.get("navigation_failed"):
            failed_dir = context.get("failed_direction", "unknown")
            nav_fail_msg = (
                f"**Navigation Failure**: Your last attempt to move to '{failed_dir}' FAILED "
                f"because that direction is UNREACHABLE (no viewpoint exists in that direction). "
                f"You are still at the same position. Choose a DIFFERENT direction from the Available Directions list."
            )
            visibility_warning = (visibility_warning + "\n\n" + nav_fail_msg) if visibility_warning else nav_fail_msg

                                                 
        verification_status = ""
        query_mode = context.get("query_mode", "attribute")
        
        if query_mode == "attribute":
                                                                  
                                               
            attr_spec = context.get("attr_spec", {})
            attributes = attr_spec.get("attributes", [])
            attr_evidence = {a.get("name", ""): a.get("evidence_phrase", "N/A") for a in attributes}
            
            lines = []
            for name, status in tracker_state.items():
                evidence = attr_evidence.get(name, "N/A")
                if status == "Matched":
                    lines.append(f"  [VERIFIED] {name}: '{evidence}'")
                elif status == "Contradictory":
                    lines.append(f"  [CONTRADICTED] {name}: expected '{evidence}'")
                else:           
                    lines.append(f"  [UNVERIFIED] {name}: '{evidence}'")
            
            verification_status = "\n".join(lines) if lines else "No attributes verified yet. This is the first view."
        else:
                                                                     
                                                                                     
            matched = sum(1 for v in tracker_state.values() if v == "Matched")
            contra = sum(1 for v in tracker_state.values() if v == "Contradictory")
            missing = sum(1 for v in tracker_state.values() if v == "Missing")
            total = len(tracker_state)
            
            if total == 0:
                verification_status = "This is the FIRST view. No verification done yet."
            else:
                lines = []
                lines.append(f"Checked {total} description aspects:")
                if matched > 0:
                    lines.append(f"  + {matched} matched")
                if contra > 0:
                    lines.append(f"  - {contra} contradicted")
                if missing > 0:
                    lines.append(f"  ? {missing} still unclear")
                
                if contra > 0:
                    lines.append("WARNING: Some descriptions contradict the object. Verify from different angle.")
                elif missing > 0:
                    lines.append("Need more views to confirm remaining aspects.")
                    
                verification_status = "\n".join(lines)

                                                                      
        all_directions = ["front-left", "front-right", "back", "back-left", "back-right"]
                                                                                          
                                                                          
        visited_rel_set = set(visited_rel_indices)
        available_directions = []
        direction_to_offset = {
            "front": 0, "front-left": 1, "back-left": 2,
            "back": 3, "back-right": 4, "front-right": 5
        }
        for d in all_directions:
            offset = direction_to_offset.get(d, -1)
            if offset not in visited_rel_set:
                available_directions.append(d)
        
                                               
        allowed_directions_str = str(available_directions) if available_directions else '["back"]'
        
                                                                                                  
        direction_descriptions = {
            "front-left": "move to YOUR left side (you will see the object from a left angle)",
            "front-right": "move to YOUR right side (you will see the object from a right angle)",
            "back": "move to the opposite side of the object",
            "back-left": "move to the left side of the opposite view",
            "back-right": "move to the right side of the opposite view"
        }
        direction_guide_lines = []
        for d in available_directions:
            if d in direction_descriptions:
                direction_guide_lines.append(f"- {d}: {direction_descriptions[d]}")
        direction_guide = "\n".join(direction_guide_lines) if direction_guide_lines else "- No available directions"

                                                                         
        prompt_kwargs = {
            "object_info": context.get("object_info", "Target Object"),
            "object_description": context.get("object_description", "No description provided."),
            "object_category": context.get("object_category", "object"),
            "desc1": context.get("desc1", ""),
            "desc2": context.get("desc2", ""),
            "desc3": context.get("desc3", ""),
            "verification_status": verification_status,
            "visited_directions": visited_directions,
            "current_view_context": f"front (Virtual Abs: {current_name_absolute})",
            "missing_attrs": verification_status,                  
            "allowed_directions": allowed_directions_str,
            "direction_guide": direction_guide,                           
            "visibility_warning": visibility_warning,                       
        }

        try:
            nav_prompt = prompt_template.template.format(**prompt_kwargs)
        except KeyError as e:
            print(f"[NBV] Template Key Error: {e}. Falling back to simple format.")
            nav_prompt = prompt_template.template                           
        
        n_res = self.client.call_qwen_vl(img_path, nav_prompt)
        text_response = n_res.get("text", "{}")
        n_obj = self._parse_json(text_response)

        rel_chosen = n_obj.get("chosen_direction", "front")

                                                     
                                                                         
                                                        
        offset_map = {
            "front": 0,
            "front-left": 1, "left": 1,                          
            "back-left": 2,                       
            "back": 3,                             
            "back-right": 4, "right": 5,                  
            "front-right": 5                                
        }
        
        offset = 0
        norm_chosen = rel_chosen.lower().replace(" ", "-")
        
                                                                              
        sorted_keys = sorted(offset_map.keys(), key=len, reverse=True)
        
                                                                
        final_rel_str = "front"           
        for k in sorted_keys:
            if k in norm_chosen:
                offset = offset_map[k]
                final_rel_str = k                                            
                break
        
                                 
        fallback_triggered = False
        
        if final_rel_str not in available_directions:
            if available_directions:
                import random
                fallback_dir = random.choice(available_directions)
                                                 
                offset = offset_map.get(fallback_dir, 0)
                
                fallback_triggered = True
                final_rel_str = fallback_dir
            else:
                 pass                                                                                     
                 
        target_abs_idx = (current_abs_idx + offset) % num_sectors
        
        debug_info = {
            "prompt": nav_prompt,
            "response": text_response,
            "parsed_direction": rel_chosen,
            "canonical_direction": final_rel_str,
            "calculated_target_sector": target_abs_idx,
            "fallback_triggered": fallback_triggered,
                                                       
            "current_abs_idx": current_abs_idx,
            "visited_abs_indices": sorted(list(visited_abs_indices)),
            "visited_names_relative": visited_names,
            "available_directions": available_directions,
            "use_dynamic_coords": use_dynamic
        }

        return final_rel_str, target_abs_idx, debug_info

    def _parse_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                json_str = text[start : end + 1]
                return json.loads(json_str)
            else:
                text = re.sub(r"```json|```", "", text).strip()
                return json.loads(text)
        except Exception as e:
            print(f"[NBV] JSON Parse Error: {e} | Text: {text[:100]}...")
            return {}



class RandomNBV(NBVModule):
    pass                                      
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    def decide_next_view(self, tracker_state, img_path, prompt_template, current_abs_idx, visited_abs_indices, num_sectors: int = 6, context: Optional[Dict] = None) -> Tuple[str, int, Dict[str, Any]]:
        context = context or {}
        all_indices = set(range(num_sectors))
        failed_sectors = context.get("failed_abs_sectors", set())
                                                                                        
        unvisited = list(all_indices - visited_abs_indices - failed_sectors)

                                                                                               
                                                                                                 
                                                                                                
                                                                                                  
                                                                                                   
                                                         
        ep_meta = context.get("ep_meta", {})
        ep_id_str = (ep_meta.get("episode_path")
                     or str(ep_meta.get("episode_id", ""))
                     or str(ep_meta.get("episode", "0")))
        step_idx = len(visited_abs_indices)                                
        rng_seed = abs(hash(f"{ep_id_str}_{step_idx}")) % (2 ** 31)
        rng = np.random.RandomState(rng_seed)

        if not unvisited:
            candidates = sorted(all_indices)
            if current_abs_idx in candidates and len(candidates) > 1:
                candidates.remove(current_abs_idx)
            target_abs_idx = int(rng.choice(candidates))
        else:
            target_abs_idx = int(rng.choice(unvisited))

        rel_str = self._get_rel_move(current_abs_idx, target_abs_idx, num_sectors)

        return rel_str, target_abs_idx, {"mode": "random", "target": target_abs_idx}


class FarthestPointNBV(NBVModule):
    pass                                                      
    
                                                                      
                                                                         
                                                  
    
                                                               
       
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    def decide_next_view(self, tracker_state, img_path, prompt_template,
                         current_abs_idx, visited_abs_indices,
                         num_sectors: int = 6,
                         context: Optional[Dict] = None) -> Tuple[str, int, Dict[str, Any]]:
        pass                                                                            

                
                                                                                       
           
        context = context or {}
        debug_info = {"mode": "farthest_point"}

                                                         
        ep_meta = context.get("ep_meta", {})
        captures = ep_meta.get("captures", [])
        goal_pos = ep_meta.get("goal_position_nominal")

                        
        debug_info["current_abs_idx"] = current_abs_idx
        debug_info["visited_abs_indices"] = list(visited_abs_indices)
        debug_info["num_sectors"] = num_sectors

                                                
                                                                       
        sector_to_pos = {}
        visited_positions = []
        sector_to_angle = {}                 

        if captures and goal_pos:
                                                                             
            first_cap = captures[0]
            first_pos = first_cap.get("camera_position")

            if first_pos:
                ref_dx = first_pos[0] - goal_pos[0]
                ref_dz = first_pos[2] - goal_pos[2]
                ref_angle = np.arctan2(ref_dz, ref_dx)
                sector_span = 2 * np.pi / num_sectors

                debug_info["ref_angle_deg"] = float(np.degrees(ref_angle))
                debug_info["sector_span_deg"] = float(np.degrees(sector_span))

                                                        
                for cap in captures:
                    cap_pos = cap.get("camera_position")
                    if cap_pos:
                        dx = cap_pos[0] - goal_pos[0]
                        dz = cap_pos[2] - goal_pos[2]
                        angle = np.arctan2(dz, dx)
                        diff = (angle - ref_angle) % (2 * np.pi)
                        sector_id = int(round(diff / sector_span)) % num_sectors

                                                                             
                        if sector_id not in sector_to_pos:
                            sector_to_pos[sector_id] = cap_pos
                            sector_to_angle[sector_id] = float(np.degrees(angle))

                                                 
                        if sector_id in visited_abs_indices:
                            visited_positions.append(cap_pos)

                                                                       
                                                                                    
                if sector_to_pos:
                    radii = [np.sqrt((p[0] - goal_pos[0])**2 + (p[2] - goal_pos[2])**2)
                             for p in sector_to_pos.values()]
                    avg_radius = float(np.mean(radii))
                    for sid in range(num_sectors):
                        if sid not in sector_to_pos:
                            expected_angle = ref_angle + sid * sector_span
                            sector_to_pos[sid] = [
                                goal_pos[0] + avg_radius * np.cos(expected_angle),
                                goal_pos[1],
                                goal_pos[2] + avg_radius * np.sin(expected_angle),
                            ]
                            sector_to_angle[sid] = float(np.degrees(expected_angle))

                debug_info["sector_angles"] = sector_to_angle

                                                                 
        all_indices = set(range(num_sectors))
        failed_sectors = context.get("failed_abs_sectors", set())
                                                                                        
        unvisited = list(all_indices - visited_abs_indices - failed_sectors)
        
        if not unvisited:
                                                                         
            candidates = list(all_indices)
            if current_abs_idx in candidates and len(candidates) > 1:
                candidates.remove(current_abs_idx)
            target_abs_idx = random.choice(candidates)
            debug_info["fallback"] = "all_visited"
            rel_str = self._get_rel_move(current_abs_idx, target_abs_idx, num_sectors)
            debug_info["target"] = target_abs_idx
            return rel_str, target_abs_idx, debug_info
        
                                                 
        if not visited_positions or not sector_to_pos:
                                                               
            target_abs_idx = random.choice(unvisited)
            debug_info["fallback"] = "no_coordinates"
            debug_info["unvisited_sectors"] = unvisited
            rel_str = self._get_rel_move(current_abs_idx, target_abs_idx, num_sectors)
            debug_info["target"] = target_abs_idx
            debug_info["relative_direction"] = rel_str
            return rel_str, target_abs_idx, debug_info

                                                                              
                                                                          
        best_sector = None
        best_min_angle_diff = -1.0
        candidate_scores = {}                        

        for sector_id in unvisited:
            if sector_id not in sector_to_pos:
                continue                                     

            candidate_pos = sector_to_pos[sector_id]
                                                                        
            min_angle_diff = float('inf')
            angle_diffs_to_visited = []

            for visited_pos in visited_positions:
                angle_diff = self._compute_angle_distance(candidate_pos, visited_pos, goal_pos)
                angle_diffs_to_visited.append(float(np.degrees(angle_diff)))
                min_angle_diff = min(min_angle_diff, angle_diff)

            candidate_scores[sector_id] = {
                "min_angle_diff_deg": float(np.degrees(min_angle_diff)),
                "angles_to_visited_deg": angle_diffs_to_visited,
                "sector_angle_deg": sector_to_angle.get(sector_id, None)
            }

                                                                    
            if min_angle_diff > best_min_angle_diff:
                best_min_angle_diff = min_angle_diff
                best_sector = sector_id

        debug_info["candidate_scores"] = candidate_scores

        if best_sector is not None:
            target_abs_idx = best_sector
            debug_info["method"] = "fps_angular"
            debug_info["best_min_angle_diff_deg"] = float(np.degrees(best_min_angle_diff))
        else:
                                                         
            target_abs_idx = random.choice(unvisited)
            debug_info["fallback"] = "no_valid_candidates"

        rel_str = self._get_rel_move(current_abs_idx, target_abs_idx, num_sectors)
        debug_info["target"] = target_abs_idx
        debug_info["relative_direction"] = rel_str

        return rel_str, target_abs_idx, debug_info
    
    def _compute_angle_distance(self, pos1, pos2, center_pos) -> float:
        pass                                                                                 
        
             
                                                 
                                                    
                                                                      
        
                
                                                      
           
        if not pos1 or not pos2 or not center_pos:
            return 0.0
        
                                                        
        dx1 = pos1[0] - center_pos[0]
        dz1 = pos1[2] - center_pos[2]
        angle1 = np.arctan2(dz1, dx1)
        
        dx2 = pos2[0] - center_pos[0]
        dz2 = pos2[2] - center_pos[2]
        angle2 = np.arctan2(dz2, dx2)
        
                                                                    
        diff = abs(angle1 - angle2)
        if diff > np.pi:
            diff = 2 * np.pi - diff
        
        return diff


class LLMViewHintNBV(NBVModule):
    pass                                                                                        
                                                                                  
    
                                                                                                  
                                                                       
                                                                                              
       
    
                                                     
    VIEW_HINT_TO_SECTOR = {
        "front": 0,
        "front-left": 1, "left": 1,
        "back-left": 2,
        "back": 3,
        "back-right": 4, "right": 4,
        "front-right": 5,
        "top": None,
        "bottom": None,
        "any": None
    }
    
    def __init__(self, client: ServerClient, config: Optional[Dict] = None):
        self.client = client
        self.config = config or {}
    
    def decide_next_view(self, tracker_state, img_path, prompt_template, current_abs_idx, 
                         visited_abs_indices, num_sectors: int = 6, 
                         context: Optional[Dict] = None) -> Tuple[str, int, Dict[str, Any]]:
        if not prompt_template:
            return "front", current_abs_idx, {}
        
        context = context or {}
        attr_spec = context.get("attr_spec", {})
        attributes = attr_spec.get("attributes", [])
        
                                                                     
        ep_meta = context.get("ep_meta", {})
        captures = ep_meta.get("captures", [])
        goal_pos = ep_meta.get("goal_position_nominal")
        current_img_path = context.get("current_img_path", "")
        
                                         
        cur_pos = None
        current_basename = os.path.basename(current_img_path) if current_img_path else ""
        for cap in captures:
            cap_path = cap.get("rgb_filename") or cap.get("rgb", "")
            if os.path.basename(cap_path) == current_basename:
                cur_pos = cap.get("camera_position")
                break
        
        use_dynamic = cur_pos and goal_pos and captures
        
                                                                             
        visited_rel_indices = set()                                     
        visited_rel_names_dynamic = []
        
        if use_dynamic:
                                                                 
                                                            
            sector_to_pos = {}
            
                                                                 
            first_cap = captures[0]
            first_pos = first_cap.get("camera_position")
            if first_pos and goal_pos:
                ref_dx = first_pos[0] - goal_pos[0]
                ref_dz = first_pos[2] - goal_pos[2]
                ref_angle = np.arctan2(ref_dz, ref_dx)
                
                                                        
                sector_span = 2 * np.pi / num_sectors
                for cap in captures:
                    cap_pos_data = cap.get("camera_position")
                    if cap_pos_data:
                        dx = cap_pos_data[0] - goal_pos[0]
                        dz = cap_pos_data[2] - goal_pos[2]
                        angle = np.arctan2(dz, dx)
                        diff = (angle - ref_angle) % (2 * np.pi)
                        sector_id = int(round(diff / sector_span)) % num_sectors
                        
                                                                             
                        if sector_id not in sector_to_pos:
                            sector_to_pos[sector_id] = cap_pos_data
            
                                                                    
            for visited_sector in sorted(list(visited_abs_indices)):
                if visited_sector in sector_to_pos:
                    v_pos = sector_to_pos[visited_sector]
                    rel_dir = self._compute_relative_direction_dynamic(cur_pos, v_pos, goal_pos, num_sectors)
                    visited_rel_names_dynamic.append(rel_dir)
                                                                   
                    rel_idx = self.SECTORS.index(rel_dir)
                    visited_rel_indices.add(rel_idx)
                else:
                                                   
                    rel_idx = (visited_sector - current_abs_idx) % 6
                    visited_rel_indices.add(rel_idx)
                    visited_rel_names_dynamic.append(self.SECTORS[rel_idx])
        else:
                                                
            visited_rel_indices = set((i - current_abs_idx) % 6 for i in visited_abs_indices)

                                                          
        visited_sector_visibility = context.get("visited_sector_visibility", {})
        visibility_warning = ""
        if visited_sector_visibility and any(v is False for v in visited_sector_visibility.values()):
            vis_lines = []
            sorted_visited = sorted(list(visited_abs_indices))
            for i, visited_sector in enumerate(sorted_visited):
                if use_dynamic and i < len(visited_rel_names_dynamic):
                    rel_name = visited_rel_names_dynamic[i]
                else:
                    rel_name = self.SECTORS[(visited_sector - current_abs_idx) % num_sectors]
                vis = visited_sector_visibility.get(visited_sector)
                if vis is False:
                    vis_lines.append(f"  - {rel_name}: target NOT visible (trap view)")
                elif vis is True:
                    vis_lines.append(f"  - {rel_name}: target visible")
            visibility_warning = (
                "**Visibility Warning**:\n" + "\n".join(vis_lines) + "\n"
                "Note: Some visited directions were trap views where the target was not visible. "
                "Adjacent sectors may also be trap views. Prioritize directions away from trap views."
            )

                                     
        if context.get("navigation_failed"):
            failed_dir = context.get("failed_direction", "unknown")
            nav_fail_msg = (
                f"**Navigation Failure**: Your last attempt to move to '{failed_dir}' FAILED "
                f"because that direction is UNREACHABLE (no viewpoint exists in that direction). "
                f"You are still at the same position. Choose a DIFFERENT direction from the Available Directions list."
            )
            visibility_warning = (visibility_warning + "\n\n" + nav_fail_msg) if visibility_warning else nav_fail_msg

                                                                                   
        attr_status_lines = []
        missing_attrs_with_hints = []
        
        for attr in attributes:
            name = attr.get("name", "unknown")
            expected = attr.get("evidence_phrase", "N/A")
            view_hint = attr.get("view_hint", "any").lower()
            weight = attr.get("weight", 2)
            status = tracker_state.get(name, "Unknown")
            
                                                                                    
            hint_abs_sector = self.VIEW_HINT_TO_SECTOR.get(view_hint)
            if hint_abs_sector is not None:
                rel_offset = (hint_abs_sector - current_abs_idx) % num_sectors
                rel_direction = self.SECTORS[rel_offset]
            else:
                rel_direction = "any"
            
            if status == "Matched":
                attr_status_lines.append(f"  [VERIFIED] {name}: {expected}")
            elif status == "Contradictory":
                attr_status_lines.append(f"  [CONTRADICTED] {name}: expected '{expected}'")
            else:
                                                      
                if rel_direction == "front":
                    hint_note = "(visible from current position)"
                elif rel_direction == "any":
                    hint_note = "(visible from any angle)"
                else:
                    hint_note = f"(best viewed by moving to: {rel_direction})"
                    
                attr_status_lines.append(
                    f"  [UNVERIFIED] {name}: '{expected}' {hint_note} weight={weight}"
                )
                missing_attrs_with_hints.append({
                    "name": name, 
                    "view_hint_abs": view_hint,
                    "view_hint_rel": rel_direction,
                    "weight": weight
                })
        
        attr_status_with_hints = "\n".join(attr_status_lines) if attr_status_lines else "No attributes to verify."
        
                                                                               
        direction_mapping_lines = []
                                                                     
        all_rel_directions = ["front", "front-right", "back-right", "back", "back-left", "front-left"]
        
        for rel_name in all_rel_directions:
            rel_offset = self.SECTORS.index(rel_name)
            target_abs = (current_abs_idx + rel_offset) % num_sectors
            
                                                                               
            verifiable = []
            for attr in missing_attrs_with_hints:
                hint_rel = attr["view_hint_rel"]
                if hint_rel == rel_name:
                    verifiable.append(attr["name"])
                elif hint_rel == "any":
                    verifiable.append(f"{attr['name']} (any)")
            
            status = ""
            if rel_offset in visited_rel_indices:
                status = "[VISITED]"
            elif rel_name == "front":
                if verifiable:
                    status = f"[CURRENT VIEW] can verify: {', '.join(verifiable)}"
                else:
                    status = "[CURRENT VIEW]"
            elif verifiable:
                status = f"can verify: {', '.join(verifiable)}"
            else:
                status = "no pending attributes"
            
            direction_mapping_lines.append(f"  {rel_name}: {status}")
        
        direction_mapping = "\n".join(direction_mapping_lines)
        
                                                                   
        available = []
        for rel_name in all_rel_directions:
            rel_offset = self.SECTORS.index(rel_name)
            if rel_offset not in visited_rel_indices:
                available.append(rel_name)
        
        allowed_directions = str(available) if available else '["back"]'
        
                                                                              
        if use_dynamic and visited_rel_names_dynamic:
            visited_directions = ", ".join(visited_rel_names_dynamic)
        else:
            visited_rel_names = [self.SECTORS[i] for i in sorted(visited_rel_indices)]
            visited_directions = ", ".join(visited_rel_names) if visited_rel_names else "None"
        
                                 
        direction_descriptions = {
            "front-left": "move to YOUR left side (you will see the object from a left angle)",
            "front-right": "move to YOUR right side (you will see the object from a right angle)",
            "back": "move to the opposite side of the object",
            "back-left": "move to the left side of the opposite view",
            "back-right": "move to the right side of the opposite view"
        }
        direction_guide_lines = []
        for d in available:
            if d in direction_descriptions:
                direction_guide_lines.append(f"- {d}: {direction_descriptions[d]}")
        direction_guide = "\n".join(direction_guide_lines) if direction_guide_lines else "- No available directions"
        
                      
        prompt_kwargs = {
            "object_category": context.get("object_category", "object"),
            "desc1": context.get("desc1", ""),
            "desc2": context.get("desc2", ""),
            "desc3": context.get("desc3", ""),
            "attr_status_with_hints": attr_status_with_hints,
            "current_absolute_sector": "front (you are currently viewing the object)",
            "visited_absolute_sectors": visited_directions,
            "allowed_directions": allowed_directions,
            "direction_mapping": direction_mapping,
            "direction_guide": direction_guide,                           
            "visibility_warning": visibility_warning,                       
        }

        try:
            nav_prompt = prompt_template.template.format(**prompt_kwargs)
        except KeyError as e:
            print(f"[ViewHintNBV] Template Key Error: {e}")
            nav_prompt = prompt_template.template
        
                  
        n_res = self.client.call_qwen_vl(img_path, nav_prompt)
        text_response = n_res.get("text", "{}")
        n_obj = self._parse_json(text_response)
        
        rel_chosen = n_obj.get("chosen_direction", "back")
        target_attrs = n_obj.get("target_attributes", [])
        
                                                       
                                                     
                                                     
        offset_map = {
            "front": 0, "front-left": 1, "back-left": 2,
            "back": 3, "back-right": 4, "front-right": 5
        }
        norm_chosen = rel_chosen.lower().replace(" ", "-")
        
                                                                                 
        offset = 3                   
        final_rel_str = "back"
        for k in sorted(offset_map.keys(), key=len, reverse=True):
            if k in norm_chosen:
                offset = offset_map[k]
                final_rel_str = k
                break
        
                                 
        fallback_triggered = False
        
                                                                             
        available_list = []
        try:
                                                                           
                                                                         
             available_list = eval(allowed_directions)
        except:
             available_list = []
                                                                     
             for rel_name in all_rel_directions:
                rel_offset = self.SECTORS.index(rel_name)
                if rel_offset not in visited_rel_indices:
                    available_list.append(rel_name)

        if final_rel_str not in available_list:
            if available_list:
                import random
                fallback_dir = random.choice(available_list)
                offset = offset_map.get(fallback_dir, 0)
                
                fallback_triggered = True
                final_rel_str = fallback_dir
            else:
                 pass 
                 
        target_abs_idx = (current_abs_idx + offset) % num_sectors
        
        debug_info = {
            "prompt": nav_prompt,
            "response": text_response,
            "parsed_direction": rel_chosen,
            "canonical_direction": final_rel_str,
            "target_sector": target_abs_idx,
            "target_sector_name": self.SECTORS[target_abs_idx],
            "target_attributes": target_attrs,
            "missing_attrs_with_hints": missing_attrs_with_hints,
             "fallback_triggered": fallback_triggered
        }
        
        return final_rel_str, target_abs_idx, debug_info
    
    def _parse_json(self, text):
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start:end+1])
            return {}
        except:
            return {}


