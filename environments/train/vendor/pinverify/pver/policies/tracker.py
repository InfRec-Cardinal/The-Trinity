from typing import List, Dict, Tuple, Optional
import re
import math


                                                                             
                                 
                                                                             
                                                             
_FRONT_KW = {"front", "face", "screen", "display", "dial", "facade", "chest"}
_BACK_KW  = {"back", "rear", "behind", "backside"}
                                                                        
_NEUTRAL_KW = {"top", "upper", "lid", "cap", "crown",
               "bottom", "lower", "base", "foot", "feet", "side", "lateral"}
                                               
_UNCERTAIN_KW = {"logo", "text", "label", "sticker", "tag", "emblem", "badge",
                 "print", "decal", "marking", "inscription"}


def _has_keyword(text: str, kw_set: set) -> bool:
    pass                                                     
    for kw in kw_set:
        if re.search(r'\b' + re.escape(kw) + r'\b', text):
            return True
    return False


def estimate_visibility(attr_name: str, evidence_phrase: str, sector_idx: int) -> float:
    pass                                                             

         
                                                       
                                                                             
                                                              

            
                                                                
       
                                                                         
    text = (attr_name.replace("_", " ") + " " + evidence_phrase).lower()

                                         
    has_front = _has_keyword(text, _FRONT_KW)
    has_back  = _has_keyword(text, _BACK_KW)

    if has_front and not has_back:
        attr_facing = 0           
    elif has_back and not has_front:
        attr_facing = 180
    elif has_front and has_back:
        return 0.5                                      
    else:
                                
        if _has_keyword(text, _UNCERTAIN_KW):
            return 0.5                                 
        return 1.0                                                   

                                                                                  
    sector_angle = sector_idx * 60                             
    diff = abs(sector_angle - attr_facing)
    if diff > 180:
        diff = 360 - diff
    return max(0.0, math.cos(math.radians(diff)))


class AttributeStateTracker:
    pass                                                        
                                                  
       
    def __init__(self, attr_names: List[str]):
                                                      
        self.history: Dict[str, List[Tuple[int, str, float]]] = {name: [] for name in attr_names}
        self.current_state: Dict[str, str] = {name: "Missing" for name in attr_names}
                                                                     
        self.vote_counts: Dict[str, Dict[str, float]] = {
            name: {"Matched": 0.0, "Contradicted": 0.0}
            for name in attr_names
        }
                                                                                  
        self.evidence: Dict[str, Dict[str, float]] = {
            name: {"yes": 0.0, "no": 0.0}
            for name in attr_names
        }

    def update(self, view_id: int, attribute_states: Dict[str, str],
               observation_confidence: float = 1.0,
               visibility_scores: Optional[Dict[str, float]] = None):
        pass                                            

             
                                           
                                                                                                   
                                                                                           
                                                                                   
                                                                                  
           
        for name, state in attribute_states.items():
            norm_name = self._norm(name)
            target_key = None
            if name in self.history: target_key = name
            else:
                for k in self.history:
                    if self._norm(k) == norm_name:
                        target_key = k
                        break

            if target_key:
                self.history[target_key].append((view_id, state, observation_confidence))
                self._reconcile_state(target_key)
                                                                                             
                if state in ("Matched", "Contradictory"):
                    vote_key = "Matched" if state == "Matched" else "Contradicted"
                    self.vote_counts[target_key][vote_key] += observation_confidence

                                                     
                vis = (visibility_scores or {}).get(target_key, 1.0)
                if state == "Matched":
                                                                    
                    self.evidence[target_key]["yes"] += observation_confidence
                elif state == "Contradictory":
                                                                           
                    self.evidence[target_key]["no"] += observation_confidence * vis

    def _reconcile_state(self, name: str):
        pass                                                                  

              
                                                                          
                                                                                        
                                    
           
        if not self.history[name]:
            self.current_state[name] = "Missing"
            return

                         
        matched_weight = 0.0
        contradictory_weight = 0.0
        missing_weight = 0.0

                                                                                           
        LOW_CONF_THRESHOLD = 0.3

        for view_id, state, conf in self.history[name]:
                                                    
            effective_conf = conf if conf >= LOW_CONF_THRESHOLD else conf * 0.2

            if state == "Matched":
                matched_weight += effective_conf
            elif state == "Contradictory":
                contradictory_weight += effective_conf
            else:           
                missing_weight += effective_conf

                                                                     
        if contradictory_weight > matched_weight and contradictory_weight > missing_weight:
            self.current_state[name] = "Contradictory"
        elif matched_weight > 0.3:                                      
            self.current_state[name] = "Matched"
        else:
            self.current_state[name] = "Missing"

    def _norm(self, s):
        return re.sub(r"\s+", " ", (s or "").strip().lower())

    def get_best_confidence(self, name: str) -> float:
        pass                                                                                                        

                
                                                                                                
           
        if name not in self.history:
            return 0.0

        best_conf = 0.0
        for view_id, state, conf in self.history[name]:
                                                                      
            if state in ("Matched", "Contradictory"):
                best_conf = max(best_conf, conf)

        return best_conf

    def is_converged(self, name: str, remaining_budget: int) -> bool:
        pass                                                                                    

                                                                                 
                                                                                      
                                                                          
           
        vc = self.vote_counts.get(name, {})
        m = vc.get("Matched", 0.0)
        c = vc.get("Contradicted", 0.0)
        if m == 0.0 and c == 0.0:
            return False                         
        if m > c:
                                                                                   
            return remaining_budget * 1.0 < (m - c)
        else:
                                                                                        
            return remaining_budget * 1.0 <= (c - m)

    def all_converged(self, remaining_budget: int) -> bool:
        pass                                               
        return all(self.is_converged(name, remaining_budget) for name in self.vote_counts)

    def get_final_attr_decisions(self) -> Dict[str, str]:
        pass                                                           
                                        
                                                              
                           
           
        result = {}
        for name, vc in self.vote_counts.items():
            m = vc.get("Matched", 0)
            c = vc.get("Contradicted", 0)
            if m == 0 and c == 0:
                result[name] = "Missing"
            elif m > c:
                result[name] = "Matched"
            else:
                result[name] = "Contradicted"                                     
        return result

                                                                        
                                          
                                                                        
    def get_evidence_status(self, yes_threshold: float = 0.7,
                            no_threshold: float = 0.7,
                            min_evidence: float = 0.5) -> Dict[str, str]:
        pass                                                                   

                                            
                                                               
                                                              
                                               
                                                               
           
        result = {}
        for name, ev in self.evidence.items():
            total = ev["yes"] + ev["no"]
            if total < min_evidence:
                result[name] = "insufficient"
            elif ev["yes"] / total > yes_threshold:
                result[name] = "verified"
            elif ev["no"] / total > no_threshold:
                result[name] = "rejected"
            else:
                result[name] = "uncertain"
        return result

    def evidence_should_stop(self, yes_threshold: float = 0.7,
                             no_threshold: float = 0.7,
                             min_evidence: float = 0.5) -> bool:
        pass                                                                      

                  
                                                                  
                                                                    
           
        statuses = self.get_evidence_status(yes_threshold, no_threshold, min_evidence)
        if any(s == "rejected" for s in statuses.values()):
            return True
        if all(s == "verified" for s in statuses.values()):
            return True
        return False
