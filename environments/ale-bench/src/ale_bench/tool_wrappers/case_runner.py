                                                                      

import json
import math
import os
import re
import shlex
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout

import ale_bench.constants
from ale_bench.code_language import (
    CodeLanguage,
    JudgeVersion,
    get_compile_command,
    get_docker_image_name,
    get_object_file_path,
    get_run_command,
    get_submission_file_path,
)
from ale_bench.data import ProblemType
from ale_bench.result import CaseResult, JudgeResult, Profiles
from ale_bench.tool_wrappers.reusable_container_pool import (
    ReusableSubmissionContainerPool,
    ReusableToolContainerPool,
)
from ale_bench.utils import docker_client, read_svg

TIMEOUT_EXIT_CODE = 124


class HostPathsCompile(BaseModel):
    pass                                                               

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")


def setup_paths_compile(
    temp_dir: Path,
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
) -> HostPathsCompile:
    pass                                                       

         
                                                 
                                    
                                                        
                                                        

            
                                                                                

       
    code_file = temp_dir / get_submission_file_path(code_language, judge_version)
    code_file.parent.mkdir(parents=True, exist_ok=True)
    code_file.write_text(code)
    object_file = temp_dir / get_object_file_path(code_language, judge_version)
    object_file.parent.mkdir(parents=True, exist_ok=True)
    object_file.touch()
    return HostPathsCompile(code_file=code_file, object_file=object_file)


def get_compile_volumes(host_paths: HostPathsCompile, temp_dir: Path) -> dict[str, dict[str, str]]:
    pass                                                          

         
                                                                     
                                                 

            
                                                                                      

       
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"{ale_bench.constants.TMP_DIR}/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "rw",
        },
    }


def build_compile_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    object_file_relative_path: Path,
) -> str:
    pass                                                                       

         
                                                        
                                                        
                                                                               

            
                                 

       
    compile_command = get_compile_command(code_language, judge_version)
    object_file_parent = object_file_relative_path.parent
    if str(object_file_parent) != ".":
        compile_command += f"; mkdir -p {ale_bench.constants.TMP_DIR}/{object_file_parent}"
    compile_command += (
        f"; cp {ale_bench.constants.WORK_DIR}/{object_file_relative_path} "
        f"{ale_bench.constants.TMP_DIR}/{object_file_relative_path}"
    )
    compile_command += f"; chmod 744 {ale_bench.constants.TMP_DIR}/{object_file_relative_path}"
    return compile_command


class HostPathsBatchRun(BaseModel):
    pass                                                                              

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")
    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_batch_run(
    host_paths_compile: HostPathsCompile,
    temp_dir: Path,
    input_str: str,
    prefix: str = "",
) -> HostPathsBatchRun:
    pass                                                                      

         
                                                                                                     
                                                 
                                                          
                                                                                     

            
                                                         

       
    input_file_name = ale_bench.constants.INPUT_FILE.split("/")[-1]
    input_file = temp_dir / f"{prefix}{input_file_name}"
    input_file.touch()
    input_file.write_text(input_str)
    output_file_name = ale_bench.constants.OUTPUT_FILE.split("/")[-1]
    output_file = temp_dir / f"{prefix}{output_file_name}"
    output_file.touch()
    profiles_file_name = ale_bench.constants.PROFILES_FILE.split("/")[-1]
    profiles_file = temp_dir / f"{prefix}{profiles_file_name}"
    profiles_file.touch()
    return HostPathsBatchRun(
        code_file=host_paths_compile.code_file,
        object_file=host_paths_compile.object_file,
        input_file=input_file,
        output_file=output_file,
        profiles_file=profiles_file,
    )


def get_batch_run_volumes(host_paths: HostPathsBatchRun, temp_dir: Path) -> dict[str, dict[str, str]]:
    pass                                                  

         
                                                                      
                                                 

            
                                                                                  

       
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "rw"},
        str(host_paths.profiles_file): {"bind": ale_bench.constants.PROFILES_FILE, "mode": "rw"},
    }


def build_batch_run_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    input_file: str = ale_bench.constants.INPUT_FILE,
    output_file: str = ale_bench.constants.OUTPUT_FILE,
    profiles_file: str = ale_bench.constants.PROFILES_FILE,
) -> str:
    pass                                                                   

         
                                                        
                                                        
                                                      
                                                               
                                                                 
                                                                     

            
                             

       
    run_command = get_run_command(code_language, judge_version)
    run_command += f" < {shlex.quote(input_file)} > {shlex.quote(output_file)}"
    run_command = (
        "/usr/bin/time "
        f'-f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" '
        f"-o {shlex.quote(profiles_file)} {run_command}"
    )                                                           
                                                                                           
    time_limit_ceil = math.ceil(time_limit + 0.1)
    run_command = (
        f"timeout {time_limit_ceil + 0.2} "
        f"prlimit --cpu={time_limit_ceil + 0.1} {run_command}"
    )                                                             
    run_command += "; sync"                                                                 
    return run_command


class HostPathsBatchJudge(BaseModel):
    pass                                                                              

    model_config = ConfigDict(frozen=True)

    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_batch_judge(host_paths_batch_run: HostPathsBatchRun) -> HostPathsBatchJudge:
    pass                                                                      

         
                                                                                

            
                                                                              

       
    return HostPathsBatchJudge(
        input_file=host_paths_batch_run.input_file,
        output_file=host_paths_batch_run.output_file,
        profiles_file=host_paths_batch_run.profiles_file,
    )


def get_batch_judge_volumes(host_paths: HostPathsBatchJudge, tool_dir: Path) -> dict[str, dict[str, str]]:
    pass                                                      

         
                                                                        
                                                    

            
                                                                                      

       
    return {
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "ro"},
        str(tool_dir / "tools" / "target" / "release" / "tester"): {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
    }


def build_batch_judge_command(
    input_file: str = ale_bench.constants.INPUT_FILE,
    output_file: str = ale_bench.constants.OUTPUT_FILE,
) -> str:
    pass                         

            
                                 

       
    return f"{ale_bench.constants.TESTER_BIN} {shlex.quote(input_file)} {shlex.quote(output_file)}"


class HostPathsReactiveJudge(BaseModel):
    pass                                                                                 

    model_config = ConfigDict(frozen=True)

    code_file: Path = Field(description="The code file")
    object_file: Path = Field(description="The object file")
    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    profiles_file: Path = Field(description="The profiles file")


def setup_paths_reactive_judge(
    host_paths_compile: HostPathsCompile,
    temp_dir: Path,
    input_str: str,
    prefix: str = "",
) -> HostPathsReactiveJudge:
    pass                                                                         

         
                                                                                                     
                                                 
                                                          
                                                                                     

            
                                                              

       
    input_file_name = ale_bench.constants.INPUT_FILE.split("/")[-1]
    input_file = temp_dir / f"{prefix}{input_file_name}"
    input_file.touch()
    input_file.write_text(input_str)
    output_file_name = ale_bench.constants.OUTPUT_FILE.split("/")[-1]
    output_file = temp_dir / f"{prefix}{output_file_name}"
    output_file.touch()
    profiles_file_name = ale_bench.constants.PROFILES_FILE.split("/")[-1]
    profiles_file = temp_dir / f"{prefix}{profiles_file_name}"
    profiles_file.touch()
    return HostPathsReactiveJudge(
        code_file=host_paths_compile.code_file,
        object_file=host_paths_compile.object_file,
        input_file=input_file,
        output_file=output_file,
        profiles_file=profiles_file,
    )


def get_reactive_judge_volumes(
    host_paths: HostPathsReactiveJudge, temp_dir: Path, tool_dir: Path
) -> dict[str, dict[str, str]]:
    pass                                                  

         
                                                                           
                                                 
                                                    

            
                                                                                  

       
    return {
        str(host_paths.code_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.code_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.object_file): {
            "bind": f"{ale_bench.constants.WORK_DIR}/{host_paths.object_file.relative_to(temp_dir)}",
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "rw"},
        str(host_paths.profiles_file): {"bind": ale_bench.constants.PROFILES_FILE, "mode": "rw"},
        str(tool_dir / "tools" / "target" / "release" / "tester"): {
            "bind": ale_bench.constants.TESTER_BIN,
            "mode": "ro",
        },
    }


def build_reactive_judge_command(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    input_file: str = ale_bench.constants.INPUT_FILE,
    output_file: str = ale_bench.constants.OUTPUT_FILE,
    profiles_file: str = ale_bench.constants.PROFILES_FILE,
) -> str:
    pass                                                                   

         
                                                        
                                                        
                                                      
                                                               
                                                                 
                                                                     

            
                             

       
    run_command = get_run_command(code_language, judge_version)
    run_command += f" < {shlex.quote(input_file)} > {shlex.quote(output_file)}"
    run_command = (
        f"{ale_bench.constants.TESTER_BIN} /usr/bin/time "
        f'-f "{ale_bench.constants.TIME_OUTPUT_FORMAT}" '
        f"-o {shlex.quote(profiles_file)} {run_command}"
    )                                                           
                                                                                           
    time_limit_ceil = math.ceil(time_limit + 0.1)
    run_command = (
        f"timeout {time_limit_ceil + 0.2} "
        f"prlimit --cpu={time_limit_ceil + 0.1} {run_command}"
    )                                                             
    run_command += "; sync"                                                                 
    return run_command


class HostPathsVis(BaseModel):
    pass                                                            

    model_config = ConfigDict(frozen=True)

    input_file: Path = Field(description="The input file")
    output_file: Path = Field(description="The output file")
    local_visualization_file: Path = Field(description="The local visualization file")


def setup_paths_vis(
    host_paths_judge: HostPathsBatchJudge | HostPathsReactiveJudge, temp_dir: Path, problem_id: str, prefix: str = ""
) -> HostPathsVis:
    pass                                                    

         
                                                                                                 
                                                 
                                         
                                                                                  

            
                                                                        

       
    local_visualization_container = (
        ale_bench.constants.LOCAL_VIS_SVG
        if problem_id in ale_bench.constants.VIS_SVG_GENERATION
        else ale_bench.constants.LOCAL_VIS_HTML
    )
    local_visualization_ext = local_visualization_container.rsplit(".", 1)[1]
    local_visualization_file = temp_dir / f"{prefix}local_visualization.{local_visualization_ext}"
    local_visualization_file.touch()
    return HostPathsVis(
        input_file=host_paths_judge.input_file,
        output_file=host_paths_judge.output_file,
        local_visualization_file=local_visualization_file,
    )


def get_vis_volumes(host_paths: HostPathsVis, tool_dir: Path) -> dict[str, dict[str, str]]:
    pass                                                            

         
                                                                 
                                                    

            
                                                                                            

           
                                                                                    

       
    if host_paths.local_visualization_file.suffix == ".svg":
        local_visualization_container = ale_bench.constants.LOCAL_VIS_SVG
    elif host_paths.local_visualization_file.suffix == ".html":
        local_visualization_container = ale_bench.constants.LOCAL_VIS_HTML
    else:
        msg = "The local visualization file must have either .svg or .html extension."
        raise ValueError(msg)
    return {
        str(tool_dir / "tools" / "target" / "release" / "vis"): {
            "bind": ale_bench.constants.VIS_BIN,
            "mode": "ro",
        },
        str(host_paths.input_file): {"bind": ale_bench.constants.INPUT_FILE, "mode": "ro"},
        str(host_paths.output_file): {"bind": ale_bench.constants.OUTPUT_FILE, "mode": "ro"},
        str(host_paths.local_visualization_file): {"bind": local_visualization_container, "mode": "rw"},
    }


def build_vis_command(
    input_file: str = ale_bench.constants.INPUT_FILE,
    output_file: str = ale_bench.constants.OUTPUT_FILE,
) -> str:
    pass                               

            
                                       

       
    return f"{ale_bench.constants.VIS_BIN} {shlex.quote(input_file)} {shlex.quote(output_file)}"


def run_compile_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    host_paths_compile: HostPathsCompile,
    compile_volumes: dict[str, dict[str, str]],
    compile_command: str,
) -> CaseResult | None:
    pass                                             

         
                                                        
                                                        
                                                                                                     
                                                                                                        
                                                   

            
                                                                                    

       
    with docker_client() as client:
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=["/bin/bash", "--noprofile", "--norc", "-c", compile_command],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=compile_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            try:
                container.wait(timeout=ale_bench.constants.COMPILE_TIMEOUT)
                                                                                  
                                                                                      
            except (Timeout, RequestsConnectionError):
                if code_language not in {CodeLanguage.PYTHON, CodeLanguage.PYPY, CodeLanguage.JULIA}:
                    return CaseResult(
                        input_str=None,
                        output_str=None,
                        error_str=None,
                        judge_result=JudgeResult.COMPILATION_ERROR,
                        message=f"Compilation timed out ({ale_bench.constants.COMPILE_TIMEOUT}s).",
                        absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                        execution_time=0.0,
                        memory_usage=0,
                    )
            except Exception:
                return CaseResult(
                    input_str=None,
                    output_str=None,
                    error_str=None,
                    judge_result=JudgeResult.COMPILATION_ERROR,
                    message="Failed to compile the code.",
                    absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                    execution_time=0.0,
                    memory_usage=0,
                )
                                                                                        
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    object_size = host_paths_compile.object_file.stat().st_size
    if any(
        [
            exit_code != 0,
                                                                                                     
            code_language not in {CodeLanguage.PYTHON, CodeLanguage.PYPY, CodeLanguage.JULIA} and object_size == 0,
                                                                                 
            code_language in {CodeLanguage.PYTHON, CodeLanguage.PYPY} and "SyntaxError" in stderr,
                                                                          
            code_language == CodeLanguage.JULIA and "ParseError" in stderr,
        ]
    ):
        return CaseResult(
            input_str=None,
            output_str=None,
            error_str=None,
            judge_result=JudgeResult.COMPILATION_ERROR,
            message=f"Failed to compile the code.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=0.0,
            memory_usage=0,
        )
    return None                                                          


def run_batch_run_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    run_volumes: dict[str, dict[str, str]],
    run_command: str,
    input_str: str | None,
) -> CaseResult | tuple[float, str]:
    pass                                                            

         
                                                        
                                                        
                                                      
                                                                                                
                                           
                                                                                            

            
                                       
                                                                                                             

       
    with docker_client() as client:
        start_at = time.perf_counter()
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=["/bin/bash", "--noprofile", "--norc", "-c", run_command],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=run_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()                                                        
            end_at = time.perf_counter()
            execution_time_host = end_at - start_at                                                                 
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        if execution_time_host > time_limit:                               
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),                                       
                memory_usage=0,
            )
        return CaseResult(
            input_str=input_str,
            output_str=None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    return execution_time_host, stderr                                                       


def run_batch_run_reusable_container(
    reusable_submission_container_pool: ReusableSubmissionContainerPool,
    time_limit: float,
    run_command: str,
    input_str: str | None,
) -> CaseResult | tuple[float, str]:
    pass                                                                  
    execution_time_host, exit_code, stderr = reusable_submission_container_pool.run(run_command)
    if exit_code != 0:
        if execution_time_host > time_limit:                               
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),                                       
                memory_usage=0,
            )
        return CaseResult(
            input_str=input_str,
            output_str=None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    return execution_time_host, stderr


def run_batch_judge_container(
    judge_volumes: dict[str, dict[str, str]],
    judge_command: str,
    execution_time_host: float,
    input_str: str | None,
    output_str: str | None,
    error_str: str | None,
) -> CaseResult | int:
    pass                                                              

         
                                                                                                    
                                               
                                                                               
                                                                                            
                                                                                              
                                                                                            

            
                                                                                  

       
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=["/bin/bash", "--noprofile", "--norc", "-c", judge_command],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=judge_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()                                                        
                                                                                        
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    if "wrong answer: " in stderr:
        error_message = stderr.split("wrong answer: ")[1]
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\n{error_message}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    return int(score_match.group(1))


def run_batch_judge_reusable_container(
    reusable_tool_container_pool: ReusableToolContainerPool,
    judge_command: str,
    execution_time_host: float,
    input_str: str | None,
    output_str: str | None,
    error_str: str | None,
) -> CaseResult | int:
    pass                                                                  
    _execution_time_host_judge, exit_code, stderr = reusable_tool_container_pool.run(judge_command)
    if exit_code != 0:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    if "wrong answer: " in stderr:
        error_message = stderr.split("wrong answer: ")[1]
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\n{error_message}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message=f"Wrong answer.\nStandard error:\n{stderr}",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    return int(score_match.group(1))


def run_reactive_judge_container(
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    judge_volumes: dict[str, dict[str, str]],
    judge_command: str,
    input_str: str | None,
    output_file_path: Path | None,
) -> CaseResult | tuple[float, int, str]:
    pass                                                                 

         
                                                        
                                                        
                                                      
                                                                                                    
                                               
                                                                                            
                                                                                                                      

            
                                                                              
                                                                                      

       
    with docker_client() as client:
        start_at = time.perf_counter()
        container = client.containers.run(
            image=get_docker_image_name(code_language, judge_version),
            command=["/bin/bash", "--noprofile", "--norc", "-c", judge_command],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=judge_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            container.wait()                                                        
            end_at = time.perf_counter()
                                                                                        
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8").strip()
            execution_time_host = end_at - start_at                                                                 
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0 or stderr == "":
        if execution_time_host > time_limit:                               
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),                                       
                memory_usage=0,
            )
        return CaseResult(
            input_str=input_str,
            output_str=None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_file_path.read_text() if output_file_path else None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.WRONG_ANSWER,
            message="Wrong answer.",                                                                          
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    score = int(score_match.group(1))
    return (execution_time_host, score, stderr)                                            


def run_reactive_judge_reusable_container(
    reusable_submission_container_pool: ReusableSubmissionContainerPool,
    time_limit: float,
    judge_command: str,
    input_str: str | None,
    output_file_path: Path | None,
) -> CaseResult | tuple[float, int, str]:
    pass                                                                
    execution_time_host, exit_code, stderr = reusable_submission_container_pool.run(judge_command)
    if exit_code != 0 or stderr == "":
        if execution_time_host > time_limit:                               
            return CaseResult(
                input_str=input_str,
                output_str=None,
                error_str=stderr if input_str is not None else None,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),                                       
                memory_usage=0,
            )
        return CaseResult(
            input_str=input_str,
            output_str=None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    stderr_last_line = stderr.splitlines()[-1]
    score_match = re.match(r"Score = (\d+)", stderr_last_line)
    if score_match is None:
        return CaseResult(
            input_str=input_str,
            output_str=output_file_path.read_text() if output_file_path else None,
            error_str=stderr if input_str is not None else None,
            judge_result=JudgeResult.WRONG_ANSWER,
            message="Wrong answer.",                                                                          
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    score = int(score_match.group(1))
    return (execution_time_host, score, stderr)


def run_vis_container(vis_command: str, vis_volumes: dict[str, dict[str, str]]) -> None:
    pass                                                   

         
                                                     
                                                                                                          

       
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command=["/bin/bash", "--noprofile", "--norc", "-c", vis_command],
            remove=False,
            auto_remove=False,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            group_add=[os.getgid()],
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            network_disabled=True,
            user=os.getuid(),
            volumes=vis_volumes,
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            try:
                container.wait(timeout=ale_bench.constants.VISUALIZE_TIMEOUT)
            except Exception as e:
                msg = "Timeout while running the visualization command. Something went wrong."
                raise RuntimeError(msg) from e
            exit_code = container.attrs["State"]["ExitCode"]
        finally:
            container.remove(force=True)
    if exit_code != 0:
        msg = "Failed to run the visualization command. Something went wrong."
        raise RuntimeError(msg)


def run_vis_reusable_container(
    reusable_tool_container_pool: ReusableToolContainerPool,
    vis_command: str,
    local_visualization_file: str,
    generated_file_path: str,
) -> None:
    pass                                                                    
    inner_command = (
        f"rm -f {shlex.quote(generated_file_path)}; "
        f"{vis_command}; "
        f"cp {shlex.quote(generated_file_path)} {shlex.quote(local_visualization_file)}"
    )
    timed_command = f"timeout {ale_bench.constants.VISUALIZE_TIMEOUT} bash -c {shlex.quote(inner_command)}"
    _execution_time_host, exit_code, _stderr = reusable_tool_container_pool.run(
        timed_command, workdir=ale_bench.constants.TMP_DIR
    )
    if exit_code == TIMEOUT_EXIT_CODE:
        msg = "Timeout while running the visualization command. Something went wrong."
        raise RuntimeError(msg)
    if exit_code != 0:
        msg = "Failed to run the visualization command. Something went wrong."
        raise RuntimeError(msg)


def parse_profiles(
    time_limit: float,
    memory_limit: int,
    profiles_content: str,
    execution_time_host: float,
    input_str: str | None,
    output_str: str | None,
    error_str: str | None,
) -> CaseResult | tuple[float, int]:
    pass                                                                                  

         
                                                      
                                                      
                                                                 
                                                                               
                                                                                            
                                                                                              
                                                                                            

            
                                                                                                                       

       
    if execution_time_host < 0.0:
        msg = "execution_time_host must be non-negative"
        raise ValueError(msg)
                                                                         
    is_tle = False
    exited_with_status_137 = False
    if profiles_content == "":
        if execution_time_host > time_limit:                                                       
            return CaseResult(
                input_str=input_str,
                output_str=output_str,
                error_str=error_str,
                judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
                message="Time limit exceeded.",
                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                execution_time=min(execution_time_host, time_limit + 0.1),                                       
                memory_usage=0,
            )
                                         
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time_host,
            memory_usage=0,
        )
    if profiles_content.startswith("Command terminated by signal 9"):
                                                                              
                                                                                                         
        _status_line, _, rest = profiles_content.partition("\n")
        profiles_content = rest
        is_tle = True
    elif profiles_content.startswith("Command exited with non-zero status"):
                                                           
                                                                                                     
        status_line, _, rest = profiles_content.partition("\n")
        status_code_str = status_line.rsplit(" ", 1)[-1].rstrip(".")
        if status_code_str.isdigit() and int(status_code_str) == ale_bench.constants.ERROR_CODE_137:
            exited_with_status_137 = True
        profiles_content = rest
                                
    profiles_content = profiles_content.strip()
    try:
        profiles_dict = json.loads(profiles_content)
    except json.JSONDecodeError:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.WRONG_ANSWER,
            message="Wrong answer.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time_host, time_limit + 0.1),                                       
            memory_usage=0,
        )
    try:
        profiles = Profiles(**profiles_dict)
    except ValueError:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.INTERNAL_ERROR,
            message="Internal Error: Invalid profiles format.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time_host, time_limit + 0.1),                                       
            memory_usage=0,
        )                                                  
                                                                          
    exit_status = profiles.exit_status
    execution_time = max(profiles.elapsed_time_seconds, profiles.user_cpu_seconds + profiles.system_cpu_seconds)
    memory_usage = profiles.max_resident_set_size_kbytes * 1024
    is_timeout_via_wrapper = exited_with_status_137 and execution_time > time_limit
                              
    if exit_status != 0 and not is_timeout_via_wrapper:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.RUNTIME_ERROR,
            message="Runtime error.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time, time_limit + 0.1),                                       
            memory_usage=memory_usage,
        )
    if execution_time > time_limit or is_tle or is_timeout_via_wrapper:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.TIME_LIMIT_EXCEEDED,
            message="Time limit exceeded.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=min(execution_time, time_limit + 0.1),                                       
            memory_usage=memory_usage,
        )
    if memory_usage > memory_limit:
        return CaseResult(
            input_str=input_str,
            output_str=output_str,
            error_str=error_str,
            judge_result=JudgeResult.MEMORY_LIMIT_EXCEEDED,
            message="Memory limit exceeded.",
            absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
            execution_time=execution_time,
            memory_usage=memory_usage,
        )
    return execution_time, memory_usage                                                                 


def build_case_file_prefix(problem_id: str, case_idx: int) -> str:
    pass                                                            
    safe_problem_id = re.sub(r"[^A-Za-z0-9._-]+", "_", problem_id)
    return f"{safe_problem_id}_{case_idx:06d}_"


def case_iter_func(
    problem_id: str,
    time_limit: float,
    memory_limit: int,
    problem_type: ProblemType,
    case_idx: int,
    input_str: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    temp_dir: Path,
    tool_dir: Path,
    return_details: bool,
    skip_local_visualization: bool,
    host_paths_compile: HostPathsCompile,
    batch_run_command: str,
    batch_judge_command: str,
    reactive_judge_command: str,
    vis_command: str,
    reusable_submission_container_pool: ReusableSubmissionContainerPool | None = None,
    reusable_tool_container_pool: ReusableToolContainerPool | None = None,
) -> CaseResult:
    pass                                                           
    result_input_str = input_str if return_details else None
    host_paths_judge: HostPathsBatchJudge | HostPathsReactiveJudge
    execution_time_host = -1.0
    case_file_prefix = build_case_file_prefix(problem_id, case_idx)
    case_temp_dir = (
        reusable_submission_container_pool.scratch_dir if reusable_submission_container_pool is not None else temp_dir
    )

    if problem_type == ProblemType.BATCH:
                                                              
        host_paths_run = setup_paths_batch_run(host_paths_compile, case_temp_dir, input_str, case_file_prefix)
        if reusable_submission_container_pool is None:
            run_volumes = get_batch_run_volumes(host_paths_run, temp_dir)
            run_result = run_batch_run_container(
                code_language, judge_version, time_limit, run_volumes, batch_run_command, result_input_str
            )
        else:
            reusable_batch_run_command = build_batch_run_command(
                code_language,
                judge_version,
                time_limit,
                input_file=reusable_submission_container_pool.container_path(host_paths_run.input_file),
                output_file=reusable_submission_container_pool.container_path(host_paths_run.output_file),
                profiles_file=reusable_submission_container_pool.container_path(host_paths_run.profiles_file),
            )
            run_result = run_batch_run_reusable_container(
                reusable_submission_container_pool,
                time_limit,
                reusable_batch_run_command,
                result_input_str,
            )
        if isinstance(run_result, CaseResult):
            return run_result
        if not isinstance(run_result, tuple):
            msg = "Run result must be a tuple"
            raise TypeError(msg)
        execution_time_host, stderr = run_result
        result_output_str = host_paths_run.output_file.read_text() if return_details else None
        result_error_str = stderr if return_details else None
                                 
        profiles_content = host_paths_run.profiles_file.read_text()
        profiles_result = parse_profiles(
            time_limit,
            memory_limit,
            profiles_content,
            execution_time_host,
            result_input_str,
            result_output_str,
            result_error_str,
        )
        if isinstance(profiles_result, CaseResult):
            return profiles_result                                                    
        if not isinstance(profiles_result, tuple):
            msg = "Profiles result must be a tuple"
            raise TypeError(msg)
        execution_time, memory_usage = profiles_result
                                                       
        host_paths_judge = setup_paths_batch_judge(host_paths_run)
        if reusable_tool_container_pool is None:
            judge_volumes = get_batch_judge_volumes(host_paths_judge, tool_dir)
            batch_judge_result = run_batch_judge_container(
                judge_volumes,
                batch_judge_command,
                execution_time_host,
                result_input_str,
                result_output_str,
                result_error_str,
            )
        else:
            reusable_batch_judge_command = build_batch_judge_command(
                input_file=reusable_tool_container_pool.container_path(host_paths_judge.input_file),
                output_file=reusable_tool_container_pool.container_path(host_paths_judge.output_file),
            )
            batch_judge_result = run_batch_judge_reusable_container(
                reusable_tool_container_pool,
                reusable_batch_judge_command,
                execution_time_host,
                result_input_str,
                result_output_str,
                result_error_str,
            )
        if isinstance(batch_judge_result, CaseResult):
            return batch_judge_result
        if not isinstance(batch_judge_result, int):
            msg = "Judge result must be an integer"
            raise TypeError(msg)
        absolute_score = batch_judge_result
    elif problem_type == ProblemType.REACTIVE:
        host_paths_judge = setup_paths_reactive_judge(
            host_paths_compile,
            case_temp_dir,
            input_str,
            case_file_prefix,
        )
        if reusable_submission_container_pool is None:
            judge_volumes = get_reactive_judge_volumes(host_paths_judge, temp_dir, tool_dir)
            reactive_judge_result = run_reactive_judge_container(
                code_language,
                judge_version,
                time_limit,
                judge_volumes,
                reactive_judge_command,
                result_input_str,
                host_paths_judge.output_file if return_details else None,
            )
        else:
            reusable_reactive_judge_command = build_reactive_judge_command(
                code_language,
                judge_version,
                time_limit,
                input_file=reusable_submission_container_pool.container_path(host_paths_judge.input_file),
                output_file=reusable_submission_container_pool.container_path(host_paths_judge.output_file),
                profiles_file=reusable_submission_container_pool.container_path(host_paths_judge.profiles_file),
            )
            reactive_judge_result = run_reactive_judge_reusable_container(
                reusable_submission_container_pool,
                time_limit,
                reusable_reactive_judge_command,
                result_input_str,
                host_paths_judge.output_file if return_details else None,
            )
        wo_profile_result = None
        if isinstance(reactive_judge_result, CaseResult):
            wo_profile_result = reactive_judge_result
            execution_time_host = reactive_judge_result.execution_time                     
            result_output_str = reactive_judge_result.output_str                     
            result_error_str = reactive_judge_result.error_str                     
        else:
            if not isinstance(reactive_judge_result, tuple):
                msg = "Judge result must be a tuple"
                raise TypeError(msg)
            execution_time_host, absolute_score, stderr = reactive_judge_result
            result_output_str = host_paths_judge.output_file.read_text() if return_details else None
            result_error_str = stderr if return_details else None
                                 
        profiles_content = host_paths_judge.profiles_file.read_text()
        profiles_result = parse_profiles(
            time_limit,
            memory_limit,
            profiles_content,
            execution_time_host,
            result_input_str,
            result_output_str,
            result_error_str,
        )
        if isinstance(profiles_result, CaseResult):
            return profiles_result                                                    
        if not isinstance(profiles_result, tuple):
            msg = "Profiles result must be a tuple"
            raise TypeError(msg)
        execution_time, memory_usage = profiles_result
        if wo_profile_result is not None:
            return CaseResult(
                input_str=wo_profile_result.input_str,
                output_str=wo_profile_result.output_str,
                error_str=wo_profile_result.error_str,
                judge_result=wo_profile_result.judge_result,
                message=wo_profile_result.message,
                absolute_score=wo_profile_result.absolute_score,
                execution_time=execution_time,
                memory_usage=memory_usage,
            )
    else:
        msg = f"Invalid problem type: {problem_type}"
        raise ValueError(msg)

                                                           
    local_visualization = None
    if not skip_local_visualization and problem_id not in ale_bench.constants.NO_LOCAL_VIS:
                                                                     
        vis_temp_dir = case_temp_dir if reusable_tool_container_pool is not None else temp_dir
        host_paths_vis = setup_paths_vis(host_paths_judge, vis_temp_dir, problem_id, case_file_prefix)
        if reusable_tool_container_pool is None:
            vis_volumes = get_vis_volumes(host_paths_vis, tool_dir)
            run_vis_container(vis_command, vis_volumes)
        else:
            generated_file_name = Path(
                ale_bench.constants.LOCAL_VIS_SVG
                if host_paths_vis.local_visualization_file.suffix == ".svg"
                else ale_bench.constants.LOCAL_VIS_HTML
            ).name
            generated_file_path = f"{ale_bench.constants.TMP_DIR}/{generated_file_name}"
            reusable_vis_command = build_vis_command(
                input_file=reusable_tool_container_pool.container_path(host_paths_vis.input_file),
                output_file=reusable_tool_container_pool.container_path(host_paths_vis.output_file),
            )
            run_vis_reusable_container(
                reusable_tool_container_pool,
                reusable_vis_command,
                reusable_tool_container_pool.container_path(host_paths_vis.local_visualization_file),
                generated_file_path,
            )
                                                  
        svg_text = host_paths_vis.local_visualization_file.read_text()
        svg_text = svg_text.replace("\n", "").removeprefix("<html><body>").removesuffix("</body></html>")
        if svg_text == "":
            msg = "The local visualization file is empty. Something went wrong."
            raise RuntimeError(msg)
        local_visualization = read_svg(svg_text)
                    
    return CaseResult(
        input_str=result_input_str,
        output_str=result_output_str,
        error_str=result_error_str,
        judge_result=JudgeResult.ACCEPTED,
        message="",
        absolute_score=absolute_score,
        local_visualization=local_visualization,
        execution_time=execution_time,
        memory_usage=memory_usage,
    )


def run_cases(
    inputs: list[str],
    code: str,
    code_language: CodeLanguage,
    judge_version: JudgeVersion,
    time_limit: float,
    memory_limit: int,
    problem_id: str,
    problem_type: ProblemType,
    tool_dir: Path,
    return_details: bool,
    skip_local_visualization: bool,
    num_workers: int,
    reuse_containers: bool = False,
) -> list[CaseResult]:
    pass                                           

         
                                               
                                    
                                                        
                                                        
                                                      
                                                      
                                         
                                                     
                                                    
                                                                                                     
                                                                             
                                                                   
                                                                                  

            
                                                   

       
                         
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

                             
        host_paths_compile = setup_paths_compile(temp_dir, code, code_language, judge_version)
        compile_volumes = get_compile_volumes(host_paths_compile, temp_dir)
        compile_command = build_compile_command(
            code_language, judge_version, host_paths_compile.object_file.relative_to(temp_dir)
        )
        batch_run_command = build_batch_run_command(code_language, judge_version, time_limit)
        batch_judge_command = build_batch_judge_command()
        reactive_judge_command = build_reactive_judge_command(code_language, judge_version, time_limit)
        vis_command = build_vis_command()

                                                  
        compile_result = run_compile_container(
            code_language,
            judge_version,
            host_paths_compile,
            compile_volumes,
            compile_command,
        )
        if compile_result is not None:
            return [compile_result for _ in inputs]                                               

                                                                      
        case_results: list[CaseResult] = []
        reusable_scratch_dir = temp_dir / "reusable_case_files"
        use_reusable_containers = reuse_containers and bool(inputs)
        if use_reusable_containers:
            reusable_scratch_dir.mkdir()
            reusable_submission_pool_context = ReusableSubmissionContainerPool(
                code_language=code_language,
                judge_version=judge_version,
                temp_dir=temp_dir,
                scratch_dir=reusable_scratch_dir,
                tool_dir=tool_dir,
                problem_type=problem_type,
                num_workers=max(1, min(num_workers, len(inputs))),
            )
            use_reusable_tool_pool = problem_type == ProblemType.BATCH or (
                not skip_local_visualization and problem_id not in ale_bench.constants.NO_LOCAL_VIS
            )
            if use_reusable_tool_pool:
                reusable_tool_pool_context = ReusableToolContainerPool(
                    scratch_dir=reusable_scratch_dir,
                    tool_dir=tool_dir,
                    num_workers=max(1, min(num_workers, len(inputs))),
                )
            else:
                reusable_tool_pool_context = nullcontext(None)
        else:
            reusable_submission_pool_context = nullcontext(None)
            reusable_tool_pool_context = nullcontext(None)

        with (
            reusable_submission_pool_context as reusable_submission_container_pool,
            reusable_tool_pool_context as reusable_tool_container_pool,
        ):
            if len(inputs) == 1 or num_workers == 1:
                for case_idx, input_str in enumerate(inputs):
                    case_result = case_iter_func(
                        problem_id,
                        time_limit,
                        memory_limit,
                        problem_type,
                        case_idx,
                        input_str,
                        code_language,
                        judge_version,
                        temp_dir,
                        tool_dir,
                        return_details,
                        skip_local_visualization,
                        host_paths_compile,
                        batch_run_command,
                        batch_judge_command,
                        reactive_judge_command,
                        vis_command,
                        reusable_submission_container_pool,
                        reusable_tool_container_pool,
                    )
                                    
                    case_results.append(case_result)
            else:
                case_results = [
                    CaseResult(
                        input_str=input_str if return_details else None,
                        output_str=None,
                        error_str=None,
                        judge_result=JudgeResult.INTERNAL_ERROR,
                        message="Internal Error: Unexpected error occurred.",
                        absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                        execution_time=0.0,
                        memory_usage=0,
                    )
                    for input_str in inputs
                ]
                                                                     
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    future_to_case_idx = {}
                    for case_idx, input_str in enumerate(inputs):
                        future = executor.submit(
                            case_iter_func,
                            problem_id,
                            time_limit,
                            memory_limit,
                            problem_type,
                            case_idx,
                            input_str,
                            code_language,
                            judge_version,
                            temp_dir,
                            tool_dir,
                            return_details,
                            skip_local_visualization,
                            host_paths_compile,
                            batch_run_command,
                            batch_judge_command,
                            reactive_judge_command,
                            vis_command,
                            reusable_submission_container_pool,
                            reusable_tool_container_pool,
                        )
                        future_to_case_idx[future] = case_idx
                    for future in as_completed(future_to_case_idx):
                        case_idx = future_to_case_idx[future]
                        try:
                            case_result = future.result()
                        except Exception as e:
                            case_result = CaseResult(
                                input_str=inputs[case_idx] if return_details else None,
                                output_str=None,
                                error_str=None,
                                judge_result=JudgeResult.INTERNAL_ERROR,
                                message=f"Internal Error: {e}",
                                absolute_score=ale_bench.constants.REJECTED_ABSOLUTE_SCORE,
                                execution_time=0.0,
                                memory_usage=0,
                            )
                        case_results[case_idx] = case_result

    return case_results
