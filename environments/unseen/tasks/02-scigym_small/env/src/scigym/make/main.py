        
                
                                                               
                                                                  
                                                                        
                                                                          
              

                
                                                               
                                                                  
                                                                        
                                                                          
                                   
                        
                  

                
                                                               
                                                                  
                                                                        
                                                                          
                                   
                          
                  

                
                                                               
                                                                  
                                                                        
                                                                          
                       
                  

                    
                             
                              
                                
 
   
import json
import os
import shutil
from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, List, Tuple

import libsbml
from tqdm import tqdm

from scigym.api import MODEL_TO_API_KEY_NAME, SBML_GRAPH_PARAMS
from scigym.data import SBML
from scigym.utils import MySBMLDiagram, find_dangling_objects

from .utils import *        


def process_sbml_challenges(
    complete_sbml: SBML,
    question_json: Dict[str, Dict[str, str | List[str]]],
    id_mapping_dict: Dict[str, Dict[str, str]] = {},
) -> Tuple[Dict[str, SBML], Dict[str, List[CreateQuestionAction]]]:
    pass                                                                           

         
                                          
                                                     

            
                                     
       
    transforms: Dict[str, List[CreateQuestionAction]] = {}
    partial_sbmls: Dict[str, SBML] = {}

    for level in [1, 2, 3]:
        level_key = f"level_{level}_challenge"

        if level_key in question_json:
            current_sbml = SBML(complete_sbml.to_string())
            masking_code = question_json[level_key]["masking_code"]

            actions = []
            try:
                if isinstance(masking_code, list):
                    for action_string in masking_code:
                        actions.append(parse_action_string(action_string, id_mapping_dict))
                else:
                    actions.append(parse_action_string(masking_code, id_mapping_dict))
            except Exception as e:
                print(f"Failed to parse action string: {e}")
                print(f"Level {level_key} failed")
                continue

                                                                                      
            class_to_order = [RemoveKineticLawAction, RemoveReactionAction, RemoveSpeciesAction]
            actions = sorted(actions, key=lambda x: class_to_order.index(x.__class__))

                                        
            for action in actions:
                try:
                    if isinstance(action, RemoveKineticLawAction):
                        rid = action.reaction_id
                        if rid in current_sbml.get_reaction_ids():
                            current_sbml.remove_kinetic_law(rid)
                    elif isinstance(action, RemoveReactionAction):
                        rid = action.reaction_id
                        if rid in current_sbml.get_reaction_ids():
                            current_sbml.remove_reaction(rid)
                    elif isinstance(action, RemoveSpeciesAction):
                        sid = action.species_id
                        if sid in current_sbml.get_species_ids():
                            current_sbml.remove_species(sid)
                except Exception as e:
                    print(f"Failed to execute action: {action}, {e}")
                    print(f"Level {level_key} failed")
                                  
                    continue

                                                                    
            dangling_objects = find_dangling_objects(current_sbml.model)
            for object in dangling_objects:
                sid = object.getId()
                assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
                if current_sbml._count_usages(sid) > 0:
                    print(f"Warning: {sid} is still referenced in the model after removal.")

                                                                          
            transforms[level_key] = actions
            partial_sbmls[level_key] = SBML(current_sbml.to_string())

    return partial_sbmls, transforms


def main(args):
    xml_src_files = sorted(list(Path(args.path_to_xml).glob("*.xml")))

    if isinstance(args.whitelist, list):
        xml_src_files = [x for x in xml_src_files if x.stem in args.whitelist]
    elif isinstance(args.blacklist, list):
        xml_src_files = [x for x in xml_src_files if x.stem not in args.blacklist]

    for xml_src_file in tqdm(xml_src_files):
        print(xml_src_file)

                                                                                               
        sedml_src_file = Path(args.path_to_sedml) / xml_src_file.with_suffix(".sedml").name
        meta_src_file = Path(args.path_to_metadata) / xml_src_file.with_suffix(".json").name
        question_dir = Path(args.path_to_questions) / xml_src_file.stem
        assert sedml_src_file.exists()
        assert meta_src_file.exists()
        os.makedirs(question_dir, exist_ok=True)

        sedml_file = question_dir / "truth.sedml"
        meta_file = question_dir / "metadata.json"

        if not sedml_file.exists() or args.overwrite:
            sedml_file = shutil.copy2(sedml_src_file, sedml_file)

        if not meta_file.exists() or args.overwrite:
            meta_file = shutil.copy2(meta_src_file, meta_file)

        sbml_raw = SBML(
            sbml_string_or_file=str(xml_src_file),
            sedml_string_or_file=str(sedml_file),
        )
        xml_raw_file = question_dir / "raw.xml"

        if not xml_raw_file.exists() or args.overwrite:
            sbml_raw.save(path=str(xml_raw_file))

        if args.stages[0] == 1 and len(args.stages) == 1:
            continue

        question_run_dir = question_dir / args.run_name
        os.makedirs(question_run_dir, exist_ok=True)

        if 2 in args.stages:
                                                                                   
            xml_truth_file = question_run_dir / "truth.xml"
            id_mapping_file = question_run_dir / "id_mapping.json"
            name_mapping_file = question_run_dir / "name_mapping.json"

            if (
                not xml_truth_file.exists()
                or not id_mapping_file.exists()
                or not name_mapping_file.exists()
                or args.overwrite
            ):
                real_to_fake_ids, real_to_canonical_names = prepare_sbml_for_benchmark(
                    sbml_raw=sbml_raw,
                    stages=[float(x) for x in args.prepare_sbml_stages],
                )
                sbml_raw.save(str(xml_truth_file))
                with open(id_mapping_file, "w") as f:
                    json.dump(real_to_fake_ids, f, indent=4)
                with open(name_mapping_file, "w") as f:
                    json.dump(real_to_canonical_names, f, indent=4)

        if 3 in args.stages:
                                                                                                               
            xml_truth_file = question_run_dir / "truth.xml"
            xml_challenge_file = question_run_dir / "fully_observable.xml"

            if not xml_challenge_file.exists() or args.overwrite:
                sbml_truth = SBML(str(xml_truth_file))

                reactions_ids = sbml_truth.get_reaction_ids()
                for rid in reactions_ids:
                    sbml_truth.remove_reaction(rid)

                for object in find_dangling_objects(sbml_truth.model):
                    sid = object.getId()
                    assert object.removeFromParentAndDelete() == libsbml.LIBSBML_OPERATION_SUCCESS
                    if sbml_truth._count_usages(sid) > 0:
                        print(f"Warning: {sid} is still referenced in the model after removal.")

                sbml_truth.save(str(xml_challenge_file))

        if 4 in args.stages:
                                                                                   
            xml_true_file = question_run_dir / "truth.xml"
            xml_inco_file = question_run_dir / "fully_observable.xml"
            diagram_save_file = question_run_dir / "model.svg"

            if not diagram_save_file.exists() or args.overwrite:
                sbml_truth = SBML(str(xml_true_file))
                sbml_inco = SBML(str(xml_inco_file))

                inco_species_ids = set(sbml_inco.get_species_ids())
                inco_reaction_ids = set(sbml_inco.get_reaction_ids())

                diagram = MySBMLDiagram(
                    sbml_truth.model,
                    inco_reaction_ids=inco_reaction_ids,
                    inco_species_ids=inco_species_ids,
                    **SBML_GRAPH_PARAMS,
                )
                diagram.draw_and_save(str(diagram_save_file))


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument("--path_to_xml", required=True, help="Path to the downloaded raw xml files")
    parser.add_argument(
        "--path_to_sedml",
        required=False,
        help="Path to the downloaded sedml simulation files",
        default=None,
    )
    parser.add_argument(
        "--path_to_metadata",
        required=False,
        help="Path to the metadata json files that describe the raw xml files",
        default=None,
    )
    parser.add_argument(
        "--path_to_questions",
        required=True,
        help="Path to the output directory where we will save questions",
    )
    parser.add_argument(
        "--model",
        required=False,
        default="gemini-2.5-pro-preview-03-25",
        help="Which model to use for generating the constraints and questions",
    )
    parser.add_argument(
        "--run_name",
        required=False,
        default="main",
        type=str,
        help="Name of the run, used to create the output directory inside the model_question_dir",
    )
    parser.add_argument(
        "--stages",
        required=False,
        default=[1, 2, 3, 4],
        nargs="+",
        type=int,
        help="List of stages to run, e.g. 1 2 3 4",
    )
    parser.add_argument(
        "--prepare_sbml_stages",
        nargs="+",
        default=[],
        required=False,
        help="List of stages to run for preparing SBML, e.g. 1 2 3 4",
    )
    parser.add_argument("--run_all", action="store_true", help="Should run all stages together")
    parser.add_argument("--overwrite", action="store_true", help="Should overwrite existing files")
    parser.add_argument(
        "--whitelist",
        nargs="+",
        default=None,
        help="List of filenames to only include",
    )
    parser.add_argument(
        "--blacklist",
        nargs="+",
        default=None,
        help="List of filenames to exclude, ignored if whitelist is used",
    )

    args = parser.parse_args()
    args.path_to_sedml = args.path_to_xml if args.path_to_sedml is None else args.path_to_sedml
    args.path_to_metadata = (
        args.path_to_xml if args.path_to_metadata is None else args.path_to_metadata
    )

    assert os.path.exists(args.path_to_xml)
    assert os.path.exists(args.path_to_sedml)
    assert os.path.exists(args.path_to_metadata)
    os.makedirs(args.path_to_questions, exist_ok=True)
    assert os.path.exists(args.path_to_questions)
    assert args.model in MODEL_TO_API_KEY_NAME.keys()

    print(args)
    main(args)
