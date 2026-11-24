import argparse
import json
import os
import time
from datetime import datetime

import yaml

from scigym.agent import get_llm
from scigym.controller import Controller




def parse_arguments():
    parser = argparse.ArgumentParser(description="Run scientific hypothesis benchmark")
    parser.add_argument("--config_path", type=str, default="configs/default.yml")
    parser.add_argument("--model_name", type=str, default="claude-3-5-haiku-20241022")
    args = parser.parse_args()

    with open(args.config_path, "r") as file:
        config = yaml.safe_load(file)
    return config, args


def setup_controller(path_to_config: str, model_name: str) -> Controller:
    pass                                       
       
    if not os.path.exists(path_to_config):
        raise FileNotFoundError(f"Configuration file {path_to_config} does not exist.")

    with open(path_to_config, "r") as file:
        config = yaml.safe_load(file)

                                                 
    os.makedirs(config["output_dir"], exist_ok=True)

    benchmark_name = os.path.basename(os.path.normpath(config["benchmark_dir"]))

    output_dir = os.path.join(config["output_dir"], benchmark_name)
    os.makedirs(output_dir, exist_ok=True)

    output_dir = os.path.join(output_dir, model_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Starting benchmark {benchmark_name} with {model_name}")

                                      
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(output_dir, timestamp)
    os.makedirs(output_dir, exist_ok=True)

    with open(f"{output_dir}/config.yml", "w") as file:
        yaml.dump(config, file, default_flow_style=False)

                                         
    controller = Controller(
        path_to_sbml_cfg=config["benchmark_dir"],
        max_iterations=config["max_iterations"],
        test_memorize=config["test_memorize"],
        output_directory=output_dir,
        experiment_actions_path=config["experiment_actions_path"],
        customized_functions_path=config["customized_functions_path"],
        eval_debug_rounds=config["eval_debug_rounds"],
        temperature=config["temperature"],
    )
    return controller


def main():
                                  
    _, args = parse_arguments()

    controller = setup_controller(path_to_config=args.config_path, model_name=args.model_name)

                     
    system_prompt = controller._create_system_prompt()
    llm = get_llm(
        name=args.model_name,
        system_prompt=system_prompt,
        log_file_path=f"{controller.output_directory}/chat_history.txt",
    )

                       
    controller.run_benchmark(model=llm)


if __name__ == "__main__":
    main()
