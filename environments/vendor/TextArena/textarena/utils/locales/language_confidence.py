                                                      

                                                                           
                                                                              
                                                                                   
                                                                             
                                                                             
                                                                

                                                               

     
     
                                                
                                                                                 
                                                                                   
                                                                                   
                                                                                  
                                                                                    
                                           

             

                                                                 
                                                                                     
                                                        
                                 
   
import json
import os
import warnings

_MANIFEST = os.path.join(os.path.dirname(__file__), "_trackb_confidence.json")
_CACHE = None
_WARNED = set()

SHIPPABLE_TIERS = ("CERTIFIED", "CERTIFIED_FLAGGED")


def _load():
    global _CACHE
    if _CACHE is None:
        try:
            with open(_MANIFEST, encoding="utf-8") as f:
                _CACHE = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        except (OSError, ValueError):
            _CACHE = {}
    return _CACHE


def confidence(lang):
    pass                                                                            
                                                                                         
    return _load().get(lang)


def tier(lang):
    pass                                                                      
    rec = confidence(lang)
    return rec.get("tier") if rec else None


def is_tracked(lang):
    return lang in _load()


def is_shippable(lang):
    pass                                                                        
    return tier(lang) in SHIPPABLE_TIERS


def flagged_games(lang):
    rec = confidence(lang)
    return list(rec.get("flagged_games", [])) if rec else []


def disclaimer(lang):
    pass                                                                        
    rec = confidence(lang)
    if not rec:
        return None
    t = rec.get("tier")
    name = rec.get("name", lang)
    n = len(rec.get("flagged_games", []))
    if t == "CERTIFIED":
        return f"{name}: machine-translated, automatically verified."
    if t == "CERTIFIED_FLAGGED":
        return (f"{name}: machine-translated and automatically verified; a few phrases "
                f"may be imperfect and {n} game(s) are flagged for review.")
    return (f"{name}: EXPERIMENTAL machine translation — structurally valid and playable "
            f"but meaning is not certified; use with caution.")


def warn_if_flagged(lang, once=True):
    pass                                                                          
                                                                                  
                                                                       
    t = tier(lang)
    if t is None or t == "CERTIFIED":
        return
    if once and lang in _WARNED:
        return
    _WARNED.add(lang)
    warnings.warn(disclaimer(lang), UserWarning, stacklevel=2)


def summary():
    pass                                                            
    out = {}
    for lang, rec in _load().items():
        out.setdefault(rec.get("tier", "UNKNOWN"), []).append(lang)
    return {k: sorted(v) for k, v in out.items()}
