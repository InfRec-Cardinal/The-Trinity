                                                                         
                                           

      

                            
                                                               
                                                                  
                                                                  
   

import os
import signal
import time
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from scigym.data import SBML, Simulator

DEFAULT_RECORD = {
    "biomodel_id": None,
    "sbml_path": None,
    "sedml_path": None,
    "metadata_path": None,
    "pass_libsbml": False,
    "pass_roadrunner": False,
    "simulation_time": None,
    "simulation_timeout": False,
    "n_reactions": None,
    "n_species": None,
    "n_events": None,
    "primary_category": None,
    "secondary_category": None,
    "error": None,
}


def timeout_handler(signum, frame):
    raise TimeoutError("Function timed out")


def long_running_function(some_slow_operation, timeout=5):
                                
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
                                                 
        result = some_slow_operation()
        signal.alarm(0)                                           
        return result
    except TimeoutError:
        print("Function skipped due to timeout")
        return None                         


def main(args):
    data = []

    path_to_biomodels = list(Path(args.path_to_xml).glob("*.xml"))
    segfault_ids = ["BIOMD0000000429", "BIOMD0000000499"]

    for xml_src_file in tqdm(path_to_biomodels):
        record = DEFAULT_RECORD.copy()

                                                                                            
        sedml_src_file = Path(args.path_to_sedml) / xml_src_file.with_suffix(".sedml").name
        meta_src_file = Path(args.path_to_json) / xml_src_file.with_suffix(".json").name

        record["biomodel_id"] = str(xml_src_file.stem)
        record["sbml_path"] = str(xml_src_file)
        record["sedml_path"] = str(sedml_src_file)
        record["metadata_path"] = str(meta_src_file)

        if not sedml_src_file.exists():
            print(f"SED-ML file not found for {xml_src_file}")
            record["pass_libsbml"] = False
            record["error"] = "SED-ML file not found"
            data.append(record)
            continue

        assert sedml_src_file.exists()
        assert meta_src_file.exists()

        if xml_src_file.stem in segfault_ids:
            print(f"Skipping {xml_src_file} due to segfault")
            record["pass_libsbml"] = False
            record["error"] = "libsbml segfault"
            data.append(record)
            continue

        try:
            model = SBML(str(xml_src_file), str(sedml_src_file))
        except Exception as e:
            print(f"Error parsing {xml_src_file}: {e}")
            record["pass_libsbml"] = False
            record["error"] = str(e)
            data.append(record)
            continue

        record["pass_libsbml"] = True

                                                                                 
        did_timeout = False
        max_simulation_time = 60           

        try:
            simulation = Simulator(model)
            start = time.time()
            long_running_function(
                lambda: simulation.run(
                    observed_species=model.get_species_ids(),
                    observed_parameters=model.get_parameter_ids(),
                ),
                timeout=max_simulation_time,
            )
            end = time.time()
            simulation_time = end - start
            if simulation_time > max_simulation_time:
                did_timeout = True
        except Exception as e:
            print(f"Error simulating {xml_src_file}: {e}")
            record["pass_roadrunner"] = False
            record["error"] = str(e)
            data.append(record)
            continue

        record["pass_roadrunner"] = True
        record["simulation_time"] = simulation_time
        record["simulation_timeout"] = did_timeout

        if did_timeout:
            print(f"Simulation timed out for {xml_src_file}")
            record["error"] = "Simulation timeout"
                                 

                                                                            
        n_reactions = len(model.get_reaction_ids())
        n_species = len(model.get_species_ids())
        n_events = model.model.getNumEvents()
        n_rules = model.model.getNumRules()

        record["n_reactions"] = n_reactions
        record["n_species"] = n_species
        record["n_events"] = n_events
        record["n_rules"] = n_rules

                                                            
        data.append(record)

    df = pd.DataFrame.from_records(data)
    df.to_csv(f"{args.path_to_output}/benchmark_all.csv", index=False)

    df_pass = df[
        (df["pass_libsbml"] == True)
        & (df["pass_roadrunner"] == True)
        & (df["simulation_timeout"] == False)
        & (df["n_reactions"] > 0)
        & (df["n_species"] > 0)
        & (df["n_events"] == 0)
        & (df["error"].isnull())
    ]
    df_pass.to_csv(f"{args.path_to_output}/benchmark_filtered.csv", index=False)


if __name__ == "__main__":
    parser = ArgumentParser(description="Filter curated BioModels into our benchmark instances")

    parser.add_argument("--path_to_xml", required=True, type=str, help="Path to the XML files")
    parser.add_argument("--path_to_sedml", required=True, type=str, help="Path to the SED-ML files")
    parser.add_argument(
        "--path_to_json", required=True, type=str, help="Path to the JSON meta files"
    )
    parser.add_argument(
        "--path_to_output", required=True, type=str, help="Path to the output directory"
    )

    args = parser.parse_args()

    assert os.path.exists(args.path_to_xml), f"Path {args.path_to_xml} does not exist"
    assert os.path.exists(args.path_to_sedml), f"Path {args.path_to_sedml} does not exist"
    assert os.path.exists(args.path_to_json), f"Path {args.path_to_json} does not exist"
    assert os.path.exists(args.path_to_output), f"Path {args.path_to_output} does not exist"

    main(args)
