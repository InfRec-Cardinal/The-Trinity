                                                                  

import os
import tempfile
import warnings
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

import ale_bench.constants
from ale_bench.error import AleBenchError
from ale_bench.utils import docker_client


class HostPathsGen(BaseModel):
    pass                                           

    model_config = ConfigDict(frozen=True)

    seeds_file: Path = Field(description="The seeds file")
    input_dir: Path = Field(description="The directory for the generated input cases")


def setup_paths_gen(temp_dir: Path, seeds: list[int]) -> HostPathsGen:
    pass                                       

         
                                                 
                                                                

            
                                                       

       
    seeds_file = temp_dir / ale_bench.constants.SEEDS_FILE.split("/")[-1]
    seeds_file.write_text("\n".join([str(seed) for seed in seeds]) + "\n")
    input_dir = temp_dir / ale_bench.constants.IN_DIR.split("/")[-1]
    input_dir.mkdir()
    return HostPathsGen(seeds_file=seeds_file, input_dir=input_dir)


def get_gen_volumes(host_paths: HostPathsGen, tool_dir: Path) -> dict[str, dict[str, str]]:
    pass                                                     

         
                                                                    
                                                    

            
                                                                                     

       
    return {
        str(host_paths.seeds_file): {"bind": ale_bench.constants.SEEDS_FILE, "mode": "ro"},
        str(host_paths.input_dir): {"bind": f"{ale_bench.constants.IN_DIR}", "mode": "rw"},
        str(tool_dir / "tools" / "target" / "release" / "gen"): {"bind": ale_bench.constants.GEN_BIN, "mode": "ro"},
    }


def build_gen_command(gen_kwargs: dict[str, Any]) -> str:
    pass                                        

         
                                                                                  

            
                                                

       
    gen_command = ale_bench.constants.GEN_BIN
    for key, value in gen_kwargs.items():
        if key == "dir":
            warnings.warn("`dir` is a reserved keyword and will be ignored.", stacklevel=2)
            continue
        gen_command += f" --{key}={value}"
    gen_command += f" {ale_bench.constants.SEEDS_FILE}"
    return gen_command


def run_gen_container(
    gen_volumes: dict[str, dict[str, str]],
    gen_command: str,
    timeout: int,
) -> None:
    pass                                               

         
                                                                                                   
                                                              
                                                     

           
                                                                          

       
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=f"/bin/sh -c '{gen_command}'",
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=gen_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            try:
                container.wait(timeout=timeout)
                exit_code = container.attrs["State"]["ExitCode"]
            except Exception as e:
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
                if len(stderr) > 0:
                    msg = f"Failed to generate the case. The standard error is:\n{stderr}"
                    raise AleBenchError(msg) from e
                msg = f"Failed to generate the case. Timeout after {timeout} seconds."
                raise AleBenchError(msg) from e
        finally:
            container.remove(force=True)
    if exit_code != 0:
        msg = "Failed to generate the case."
        raise AleBenchError(msg)


def generate_inputs(seeds: list[int], gen_kwargs: dict[str, Any], tool_dir: Path) -> list[str]:
    pass                                             

         
                                                                
                                                                                  
                                                    

            
                                                     

       
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

                                    
        gen_host_paths = setup_paths_gen(temp_dir, seeds)
        gen_volumes = get_gen_volumes(gen_host_paths, tool_dir)
        gen_command = build_gen_command(gen_kwargs)

                                     
        timeout = ale_bench.constants.GENERATION_TIMEOUT
        run_gen_container(gen_volumes, gen_command, timeout)

                                       
        input_files = sorted(gen_host_paths.input_dir.glob("*.txt"))
        generated_cases = []
        for idx, input_file in enumerate(input_files):
            if input_file.name != f"{idx:04d}.txt":
                msg = "The generated case files must be named `0000.txt`, `0001.txt`, ..."
                raise AleBenchError(msg)
            generated_cases.append(input_file.read_text())

    return generated_cases
