                                                                                        

                                                                                  
                                                                                      
                                                                                     
                                                                         
import os
import sys
import types

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.join(ROOT, "src", "toolkit")


def import_official_evaluator():
    torch = types.ModuleType("torch")
    torch.cuda = types.SimpleNamespace(empty_cache=lambda: None)
    tr = types.ModuleType("transformers")
    tr_iu = types.ModuleType("transformers.image_utils")
    tr_iu.load_image = lambda p: p
    tr.image_utils = tr_iu
    tq = types.ModuleType("tqdm")
    tq.tqdm = lambda it, *a, **k: it
    mc = types.ModuleType("model_config")
    mc.predict = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("model call not available"))
    sys.modules.update({"torch": torch, "transformers": tr, "transformers.image_utils": tr_iu,
                        "tqdm": tq, "model_config": mc})
    if TOOLKIT not in sys.path:
        sys.path.insert(0, TOOLKIT)
    import evaluator                                                                 
    return evaluator
