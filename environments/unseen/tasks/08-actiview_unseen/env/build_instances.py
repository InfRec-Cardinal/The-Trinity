                                                                                                    
                                                                                  
                                                                                                   
import json
import actiview_core as C

data = C.load_data()
starts = C.start_views()
out = []
for setting in C.SETTINGS:
    for idx, d in enumerate(data):
        e = {"id": f"{setting}-{d['id']}", "questionId": d["id"], "setting": setting, "dataIndex": idx,
             "category": d["category"], "numOptions": len(d["options"]), "stepCap": C.STEP_CAP[setting]}
        if setting != "zoom":
            e["startView"] = starts[setting][idx]
            e["startViewName"] = C.IMAGE_VIEWS[starts[setting][idx]]
        out.append(e)
with open(C.INSTANCES_PATH, "w") as fw:
    json.dump(out, fw, indent=1)
from collections import Counter
print(len(out), dict(Counter(e["setting"] for e in out)))
for s in C.SETTINGS[1:]:
    print(s, dict(sorted(Counter(e["startViewName"] for e in out if e["setting"] == s).items())))
