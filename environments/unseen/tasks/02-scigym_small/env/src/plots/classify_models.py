import os
import urllib.request
from pathlib import Path

import pandas as pd
import yaml
from goatools import obo_parser

with open(Path(__file__).parent / "go_counts.yaml", "r") as file:
    go_counts = yaml.safe_load(file)


                                    
go_obo_url = "http://purl.obolibrary.org/obo/go/go-basic.obo"
obo_file = "go-basic.obo"

                                           
if not os.path.exists(obo_file):
    print(f"Downloading {go_obo_url}...")
    urllib.request.urlretrieve(go_obo_url, obo_file)


                    
print("Parsing GO terms...")
go = obo_parser.GODag(obo_file)


                            
rows = []
for primary_id, subcounts in go_counts.items():
    for sub_id, count in list(subcounts.items()):
        if count > 0:
            rows.append(
                {
                    "primary_id": primary_id,
                    "primary_name": go[primary_id].name,
                    "sub_id": sub_id,
                    "sub_name": go[sub_id].name,
                    "count": count,
                }
            )


df = pd.DataFrame(rows)
print(df.value_counts())

                                  
df.to_csv("go_counts.csv", index=False)

              
