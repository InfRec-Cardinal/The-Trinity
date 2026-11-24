import gym
import os
import json
import random
import numpy as np
from gym import spaces
from typing import Dict, Any, List

class PInVerifyEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, dataset: List[Dict[str, Any]], max_steps=6, sectors=6, data_root=None, view_priority="far", seed=42):
        super(PInVerifyEnv, self).__init__()
        
                                              
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)
        
        self.dataset = dataset
        self.max_steps = max_steps
        self.sectors = sectors
        self.data_root = data_root
        self.view_priority = view_priority                   
        
                       
                           
                          
                                                                                
                                                                  
                                                            
                                                                                      
                                                 
                                                                                                  
                                                             
                                                                                                        
                               
                                            
                                                  
                                                                                      
        
        self.action_space = spaces.Dict({
            "decision": spaces.Discrete(3),                        
            "nav_dir": spaces.Discrete(6)                 
        })
        
        self.observation_space = spaces.Dict({
            "rgb_path": spaces.Text(max_length=512),
            "current_sector": spaces.Discrete(sectors),
            "step_count": spaces.Discrete(max_steps + 1)
        })

    def reset(self, episode_idx=None):
        if episode_idx is None:
            self.current_ep_idx = np.random.randint(len(self.dataset))
        else:
            self.current_ep_idx = episode_idx

                                                            
                                                                            
                                                                     
        episode_seed = self.seed + self.current_ep_idx
        np.random.seed(episode_seed)
        random.seed(episode_seed)

        self.ep_data = self.dataset[self.current_ep_idx]

                                                                                                     
        self.captures = self.ep_data.get("captures_meta") or self.ep_data.get("captures")
        
        if not self.captures:
                                                                               
             meta_rel_path = self.ep_data.get("meta_path")
             if meta_rel_path and self.data_root:
                 full_meta_path = os.path.join(self.data_root, meta_rel_path)
                 if os.path.exists(full_meta_path):
                     try:
                         with open(full_meta_path, 'r', encoding='utf-8') as f:
                             full_meta = json.load(f)
                             self.captures = full_meta.get("captures", [])
                                                                                                     
                                                                                                   
                                                                                                    
                                                                                               
                                                                              
                             for k, v in full_meta.items():
                                 if k not in self.ep_data:
                                     self.ep_data[k] = v
                     except Exception as e:
                         print(f"Error loading meta.json: {e}")

                                                                        
        if not self.captures:
                                              
             rgb_rel_dir = self.ep_data.get("rgb_dir")
             if rgb_rel_dir and self.data_root:
                 full_rgb_dir = os.path.join(self.data_root, rgb_rel_dir)
                 if os.path.isdir(full_rgb_dir):
                     self.captures = []
                                                         
                     for fname in os.listdir(full_rgb_dir):
                         if fname.endswith(".png") and "rgb_" in fname:
                                                                              
                             parts = fname.split("_")
                                                                                
                             if len(parts) >= 2 and parts[1].startswith("s"):
                                 try:
                                     s_idx = int(parts[1][1:])
                                     rel_to_ep = os.path.join("rgb", fname).replace("\\", "/")                    
                                     
                                     self.captures.append({
                                         "rgb_filename": rel_to_ep,
                                         "rgb": rel_to_ep,                    
                                         "sector_index": s_idx,
                                         "view_type": "far" if "far" in fname else "near"
                                     })
                                 except:
                                     pass
        
        if not self.captures:
             print(f"Warning: No captures found (even after scanning rgb_dir) for episode {self.ep_data.get('episode_id')}")
             self.captures = []

                                                                       
        for cap in self.captures:
            if "sector_index" not in cap:
                                                 
                tag = cap.get("tag", "")
                if tag.startswith("s"):
                    try:
                                           
                        part = tag.split("_")[0]
                        cap["sector_index"] = int(part[1:])
                    except:
                        pass
                
                                                              
                if "sector_index" not in cap:
                    fname = cap.get("rgb_filename") or cap.get("rgb", "")
                    fname = os.path.basename(fname)
                                            
                    parts = fname.split("_")
                    for p in parts:
                        if p.startswith("s") and p[1:].isdigit():
                            cap["sector_index"] = int(p[1:])
                            break
            
                                 
            if "view_type" not in cap:
                 fname = cap.get("rgb_filename") or cap.get("rgb", "") or cap.get("tag", "")
                 cap["view_type"] = "far" if "far" in fname else "near"

                              
        self.captures = sorted(self.captures, key=lambda x: x.get("sector_index", -1))
        
                                                                        
                                                      
        
        self.current_step = 0
        
                                    
                                    
        self.sector_map = {}
        
                                                                          
        goal_pos = self.ep_data.get("goal_position_nominal")
        if goal_pos:
            gx, gy, gz = goal_pos
        else:
            gx, gy, gz = 0, 0, 0
        
                                                                        
        self.goal_position = (gx, gy, gz)
            
                                               
                                           
                                              
        cap_angles = []
        caps_without_coords = []                                      
        for i, cap in enumerate(self.captures):
                                                         
             if not cap.get("navigable", True):
                  continue
             if not (cap.get("rgb_filename") or cap.get("rgb")):
                  continue

             pos = cap.get("camera_position")
             if not pos:
                  caps_without_coords.append(i)
                  continue
             cx, cy, cz = pos
             dx = cx - gx
             dz = cz - gz
                                                                
             angle = np.arctan2(dz, dx)                           
             cap_angles.append((i, angle))

        if not cap_angles:
                                                              
             self.virtual_sector_map = {i: 0 for i in range(len(self.captures))}
        else:
                                                                                  
                                                                          
                                                          
             ref_idx, ref_angle = cap_angles[0]                   
             
             self.virtual_sector_map = {}
             
             for i, angle in cap_angles:
                                        
                 diff = (angle - ref_angle) % (2 * np.pi)
                 
                                      
                                                         
                                       
                                                              
                 sector_span = 2 * np.pi / self.sectors
                 virtual_idx = int(round(diff / sector_span)) % self.sectors
                 
                                                                          
                 self.virtual_sector_map[i] = virtual_idx
                 
                                                                             
                 if virtual_idx not in self.sector_map:
                     self.sector_map[virtual_idx] = {}
                 
                                                    
                 vt = self.captures[i].get("view_type", "far")
                 self.sector_map[virtual_idx][vt] = i

                                                                                         
             for i in caps_without_coords:
                 self.virtual_sector_map[i] = 0                       
                 vt = self.captures[i].get("view_type", "far")
                 if 0 not in self.sector_map:
                     self.sector_map[0] = {}
                 if vt not in self.sector_map[0]:                            
                     self.sector_map[0][vt] = i

                                                                                                        
        available_sectors = sorted(list(self.sector_map.keys()))

                                                                             
        valid_start_sectors = []
        for vs in available_sectors:
            cap_idx = self._get_capture_for_sector(vs)
            if cap_idx is not None and self.captures[cap_idx].get("mask_meets_threshold", True):
                valid_start_sectors.append(vs)

                                                                                        
        if not valid_start_sectors:
            valid_start_sectors = available_sectors

        if valid_start_sectors:
                                                                
            episode_rng = np.random.RandomState(self.seed + self.current_ep_idx)
            start_sector = episode_rng.choice(valid_start_sectors)
            self.current_obs_idx = self._get_capture_for_sector(start_sector)
        else:
            self.current_obs_idx = 0
        
                                             
        starting_sector = self.virtual_sector_map.get(self.current_obs_idx, -1)
        self.visited_sectors = {starting_sector}

                                                   
        self.sector_map_debug = {
            "episode_idx": episode_idx,
            "total_captures": len(self.captures),
            "available_virtual_sectors": sorted(self.sector_map.keys()),
            "valid_start_sectors": valid_start_sectors,
            "starting_sector": starting_sector,
            "sector_details": {}
        }
        for vsec in sorted(self.sector_map.keys()):
            views = self.sector_map[vsec]
            cap_info = []
            for vtype, cap_idx in views.items():
                tag = self.captures[cap_idx].get("tag", f"cap{cap_idx}")
                raw_sec = self.captures[cap_idx].get("sector_index", "?")
                cap_info.append({"tag": tag, "raw_sector": raw_sec, "view_type": vtype, "cap_idx": cap_idx})
            self.sector_map_debug["sector_details"][vsec] = cap_info

                                                                               
        self.nav_debug_log = []

                                                                          
        self._last_nav_failed = False
        self._last_nav_dir = None

        return self._get_obs()
    
    def _get_capture_for_sector(self, sector):
        pass                                                           
        if sector not in self.sector_map:
            return None
        views = self.sector_map[sector]
                                                 
        if self.view_priority in views:
            return views[self.view_priority]
                  
        fallback = "near" if self.view_priority == "far" else "far"
        return views.get(fallback)

    def _get_obs(self):
                      
        if not self.captures:
             return {
                "rgb_path": "",
                "current_sector": -1,
                "step_count": self.current_step,
                "meta": self.ep_data
             }
             
        cap = self.captures[self.current_obs_idx]
                                           
        rgb_path = cap.get("rgb_filename") or cap.get("rgb") or ""
        
        if self.data_root and not os.path.isabs(rgb_path):
                                                      
            ep_path = self.ep_data.get("episode_path", "")
            full_path = os.path.join(self.data_root, ep_path, rgb_path)
            
                                                                                             
                                                                
            rgb_path = full_path
            
        return {
            "rgb_path": rgb_path,                                      
            "current_sector": self.virtual_sector_map.get(self.current_obs_idx, -1),
            "step_count": self.current_step,
            "meta": self.ep_data,                                 
            "available_sectors": sorted(list(self.sector_map.keys())),
            "navigation_failed": self._last_nav_failed,
            "failed_direction": self._last_nav_dir
        }

    def step(self, action: Dict[str, Any]):
        pass                 
                                                
                                                              
         
           
        decision = action.get("decision", "Unsure")
        
        done = False
        reward = 0.0
        info = {}
        
        self.current_step += 1
        
        if decision in ["Yes", "No"]:
            done = True
                                                                                        
                                                                                      
        else:
                        
            if self.current_step >= self.max_steps:
                done = True
                decision = "Unsure"              
            else:
                                   
                rel_dir = action.get("nav_rel", "front")
                next_idx = self._resolve_next_view(rel_dir)
                if next_idx is not None:
                    self.current_obs_idx = next_idx
                                                              
                    next_sector = self.virtual_sector_map.get(next_idx, -1)
                    self.visited_sectors.add(next_sector)
                    self._last_nav_failed = False
                    self._last_nav_dir = None
                                                                                            
                    dest_cap = self.captures[next_idx]
                    if not dest_cap.get("mask_meets_threshold", True):
                        info["trap_view"] = True
                else:
                                                                                    
                    info["navigation_failed"] = True
                    self._last_nav_failed = True
                                                               
                    clean_dir = rel_dir.split("(")[0].strip()
                    self._last_nav_dir = clean_dir
        
        info["decision"] = decision
        return self._get_obs(), reward, done, info

    def _resolve_next_view(self, rel_dir):
        pass                                         
                                                                                 
                                                                      
                                                                                       
           
                                                         
        nav_debug_entry = {
            "step": self.current_step,
            "rel_dir_input": rel_dir,
            "current_obs_idx": self.current_obs_idx,
            "current_capture_tag": self.captures[self.current_obs_idx].get("tag", f"cap{self.current_obs_idx}"),
        }

                                                             
                                                             
        rel_dir_normalized = rel_dir.split("(")[0].strip().lower()
        valid_dirs = {"front", "front-left", "front-right", "back", "back-left", "back-right"}
        if rel_dir_normalized not in valid_dirs:
            for d in valid_dirs:
                if d in rel_dir.lower():
                    rel_dir_normalized = d
                    break
            else:
                rel_dir_normalized = "front"

        nav_debug_entry["rel_dir_normalized"] = rel_dir_normalized

                                                                                
        cur_capture = self.captures[self.current_obs_idx]
        cur_pos = cur_capture.get("camera_position")

        if not cur_pos or not hasattr(self, 'goal_position'):
            nav_debug_entry["method"] = "fallback_no_coords"
            result = self._resolve_next_view_fallback(rel_dir_normalized)
            nav_debug_entry["result_cap_idx"] = result
            self.nav_debug_log.append(nav_debug_entry)
            return result

        cur_pos_2d = np.array([cur_pos[0], cur_pos[2]])
        goal_pos_2d = np.array([self.goal_position[0], self.goal_position[2]])
        goal_to_current = cur_pos_2d - goal_pos_2d
        norm = np.linalg.norm(goal_to_current)
        if norm < 1e-6:
            nav_debug_entry["method"] = "fallback_norm_too_small"
            result = self._resolve_next_view_fallback(rel_dir_normalized)
            nav_debug_entry["result_cap_idx"] = result
            self.nav_debug_log.append(nav_debug_entry)
            return result

        current_angle = np.arctan2(goal_to_current[1], goal_to_current[0])
        nav_debug_entry["method"] = "coordinate_sector_check"
        nav_debug_entry["current_angle_deg"] = float(np.degrees(current_angle))

                                            
        if rel_dir_normalized == "front":
            cur_sector = self.virtual_sector_map.get(self.current_obs_idx, 0)
            result = self._get_capture_for_sector(cur_sector)
            nav_debug_entry["result"] = "front_stay"
            nav_debug_entry["chosen_sector"] = cur_sector
            nav_debug_entry["result_cap_idx"] = result
            self.nav_debug_log.append(nav_debug_entry)
            return result

                                                      
        sector_span = 2 * np.pi / self.sectors
        angle_offsets = {
            "front-left": sector_span,                     
            "back-left": 2 * sector_span,                   
            "back": np.pi,                              
            "back-right": -2 * sector_span,                          
            "front-right": -sector_span                    
        }
        angle_offset = angle_offsets.get(rel_dir_normalized, 0)
        target_angle = current_angle + angle_offset
        nav_debug_entry["target_offset_deg"] = float(np.degrees(angle_offset))
        nav_debug_entry["target_angle_deg"] = float(np.degrees(target_angle))

                                                                                
                                                               
        half_span = sector_span / 2
        all_sectors = set(self.sector_map.keys())
        unvisited_sectors = all_sectors - self.visited_sectors
        nav_debug_entry["visited_sectors"] = sorted(list(self.visited_sectors))
        nav_debug_entry["unvisited_sectors"] = sorted(list(unvisited_sectors))

        best_cap_idx = None
        best_sector = None
        best_diff = float('inf')
        candidates_info = []

        for sec_idx in unvisited_sectors:
            cap_idx = self._get_capture_for_sector(sec_idx)
            if cap_idx is None:
                continue
            cap = self.captures[cap_idx]
            cap_pos = cap.get("camera_position")
            if not cap_pos:
                continue

            cap_2d = np.array([cap_pos[0], cap_pos[2]])
            goal_to_cap = cap_2d - goal_pos_2d
            cap_norm = np.linalg.norm(goal_to_cap)
            if cap_norm < 1e-6:
                continue

            cap_angle = np.arctan2(goal_to_cap[1], goal_to_cap[0])
                                                        
            diff = (cap_angle - target_angle + np.pi) % (2 * np.pi) - np.pi
            abs_diff = abs(diff)

            candidates_info.append({
                "sector_idx": sec_idx,
                "cap_tag": cap.get("tag", "?"),
                "cap_idx": cap_idx,
                "angle_deg": float(np.degrees(cap_angle)),
                "angle_diff_deg": float(np.degrees(abs_diff))
            })

                                                            
            if abs_diff < half_span and abs_diff < best_diff:
                best_diff = abs_diff
                best_cap_idx = cap_idx
                best_sector = sec_idx

        nav_debug_entry["candidates"] = candidates_info

        if best_cap_idx is not None:
            nav_debug_entry["result"] = "success"
            nav_debug_entry["chosen_sector"] = best_sector
            nav_debug_entry["best_angle_diff_deg"] = float(np.degrees(best_diff))
            nav_debug_entry["result_cap_idx"] = best_cap_idx
            self.nav_debug_log.append(nav_debug_entry)
            return best_cap_idx

                                                                              
        nav_debug_entry["result"] = "no_viewpoint_in_target_sector"
        nav_debug_entry["result_cap_idx"] = None
        self.nav_debug_log.append(nav_debug_entry)
        return None
    
    def _resolve_next_view_fallback(self, rel_dir):
        pass                                        
        cur_sector = self.virtual_sector_map.get(self.current_obs_idx, 0)
        
        step_offsets = {
            "front": 0, "front-left": 1, "back-left": 2,
            "back": 3, "back-right": 4, "front-right": 5
        }
        
        target_sector = (cur_sector + step_offsets.get(rel_dir, 0)) % self.sectors
        
        all_sectors = set(self.sector_map.keys())
        unvisited = all_sectors - self.visited_sectors
        
        if not unvisited:
            return None
        
        if target_sector in unvisited:
            return self._get_capture_for_sector(target_sector)

                                                       
                                                                                
        return None