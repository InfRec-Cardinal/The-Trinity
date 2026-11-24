import os
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import pandas as pd
import requests
import yaml
from goatools import obo_parser
from tqdm import tqdm

                          
root_terms = {"GO:0008150", "GO:0003674", "GO:0005575"}
cache = {}


                                    
go_obo_url = "http://purl.obolibrary.org/obo/go/go-basic.obo"
obo_file = "go-basic.obo"

                                           
if not os.path.exists(obo_file):
    print(f"Downloading {go_obo_url}...")
    urllib.request.urlretrieve(go_obo_url, obo_file)

                    
print("Parsing GO terms...")
go = obo_parser.GODag(obo_file)


def get_go_name_from_id(go_id):
                                          
    if go_id not in go:
        print(f"Error: {go_id} not found in the GO DAG.")
        return None

                                    
    return go[go_id].name


def get_go_grandchildren():
                                                      
    biological_process_id = "GO:0008150"

    if biological_process_id not in go:
        print(f"Error: {biological_process_id} (biological process) not found in the GO DAG.")
        return {}

                                     
    bp_term = go[biological_process_id]

                                    
    result = {}

                                            
    for child in bp_term.children:
        child_id = child.id
        result[child_id] = {}

                                                                                     
        for grandchild in child.children:
            grandchild_id = grandchild.id
            grandchild_name = grandchild.name
            result[child_id][grandchild_id] = grandchild_name

    return result


def get_go_term_info(go_id):
    pass                                                           
       
    url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}"
    headers = {"Accept": "application/json"}

                                                  
    max_retries = 3
    retry_delay = 1

    if go_id in cache:
        return cache[go_id]
    cache[go_id] = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            cache[go_id] = data["results"][0]
            return cache[go_id]
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            cache[go_id] = None
            if attempt < max_retries - 1:
                print(f"Error fetching GO term info, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2                       
            else:
                print(f"Failed to fetch GO term info after {max_retries} attempts: {e}")
                return None


def find_ancestors(go_id, target_relation="is_a"):
    pass                                                                         
       
                                                                           
                                                    
    url = f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_id}/ancestors"
    params = {"relations": target_relation}
    headers = {"Accept": "application/json"}

    max_retries = 1
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["results"][0]["ancestors"]
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            if attempt < max_retries - 1:
                print(f"Error finding parent, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print(f"Failed to find parent after {max_retries} attempts: {e}")
                return None


                            
go_hierarchy = get_go_grandchildren()

                   
level_2_go_ids = set([term for subdict in go_hierarchy.values() for term in subdict.keys()])


metadata_files = list(Path("/mfs1/u/stephenzlu/scigym/benchmark/metadata").glob("*.json"))
benchmark_df = pd.read_csv("/h/290/stephenzlu/scigym/data/benchmark_final.csv")

metadata_files = [
    path for path in metadata_files if path.stem in benchmark_df["biomodel_id"].values
]

print(f"Classifying GO terms of {len(metadata_files)} models")


go_codes = []
go_quals = []
go_qualifier_pref = [
    "bqbiol:is",
    "bqbiol:isVersionOf",
    "bqmodel:isInstanceOf",
    "bqmodel:is",
    "bqmodel:isDescribedBy",
    "bqbiol:encodes",
    "bqmodel:isDerivedFrom",
    "bqbiol:isPartOf",
    "bqbiol:isPropertyOf",
    "bqbiol:occursIn",
    "bqbiol:hasPart",
    "bqbiol:hasProperty",
    "bqbiol:hasVersion",
]

results = {k: {k2: 0 for k2 in v} for k, v in go_hierarchy.items()}

for path_to_metadata in tqdm(metadata_files):
    with open(path_to_metadata, "r") as file:
        metadict = yaml.safe_load(file)

    annots = metadict.get("modelLevelAnnotations", [])
    go_accession_code = None
    go_priority = float("inf")

    for annot in annots:
        if annot.get("accession").startswith("GO:"):
            go_id = str(annot["accession"]).strip()

            if not go_id.startswith("GO:") or not go_id[3:].isdigit():
                continue

            go_qual = str(annot["qualifier"]).strip()
            go_prio = (
                go_qualifier_pref.index(go_qual) if go_qual in go_qualifier_pref else float("inf")
            )

            if go_prio < go_priority:
                go_accession_code = go_id
                go_priority = go_prio

    go_codes.append(go_accession_code)
    go_quals.append(go_priority)

codes = pd.Series(go_codes)
quals = pd.Series(go_quals)

print(codes.isna().sum())
print(codes.notna().sum())
print(quals.value_counts())


level_2_go_id_counts = defaultdict(int)


for code in tqdm(codes):
    if code is not None:
        ancestor_ids = find_ancestors(code, target_relation="is_a")
        found = False
        if ancestor_ids is not None:
            for term in ancestor_ids:
                if term in level_2_go_ids:
                    level_2_go_id_counts[term] += 1
                    found = True
                    break
        if not found:
            print(f"Could not find a level 2 GO term for {code}")


                                       
for code, subdict in results.items():
    for key in subdict.keys():
        if key in level_2_go_id_counts:
            results[code][key] = level_2_go_id_counts[key]
        else:
            results[code][key] = 0


                            
rows = []
for primary_id, subcounts in results.items():
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
