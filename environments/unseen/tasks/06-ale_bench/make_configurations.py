                                                                                                                      
import json
from pathlib import Path

import ale_bench

ids = ale_bench.list_problem_ids(lite_version=False)
configurations = [{"id": pid, "ordinal": i, "label": pid.upper(), "episodes": 1} for i, pid in enumerate(ids)]
out = Path(__file__).with_name("configurations.json")
out.write_text(json.dumps({"taskId": "ale_bench", "source": "ale_bench.list_problem_ids(lite_version=False)",
                           "configurations": configurations}, indent=1) + "\n")
print(len(configurations), "problems:", " ".join(ids))
