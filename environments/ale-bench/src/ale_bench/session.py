                                                               

import atexit
import datetime as dt
import json
import logging
import os
import shutil
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn

from PIL import Image
from docker.errors import NotFound

import ale_bench.constants
from ale_bench.code_language import CodeLanguage, JudgeVersion, get_compile_command
from ale_bench.data import Problem, RankPerformanceMap, Standings, start_visualization_server
from ale_bench.error import AleBenchError
from ale_bench.result import CaseResult, CodeRunResult, ResourceUsage, Result
from ale_bench.tool_wrappers import generate_inputs, local_visualization, run_cases, run_code
from ale_bench.utils import docker_client

logger = logging.getLogger(__name__)


class AleBenchFunction(str, Enum):
    pass                          

    CODE_RUN = "code_run"
    CASE_GEN = "case_gen"
    CASE_EVAL = "case_eval"
    CASE_GEN_EVAL = "case_gen_eval"
    PUBLIC_EVAL = "public_eval"
    PRIVATE_EVAL = "private_eval"


CHECK_RESOURCE_USAGE_FIELDS = {
    AleBenchFunction.CODE_RUN: {"execution_time_case_eval"},
    AleBenchFunction.CASE_GEN: {"num_case_gen"},
    AleBenchFunction.CASE_EVAL: {"num_case_eval", "execution_time_case_eval"},
    AleBenchFunction.CASE_GEN_EVAL: {"num_case_gen", "num_case_eval", "execution_time_case_eval"},
    AleBenchFunction.PUBLIC_EVAL: {"num_call_public_eval"},
    AleBenchFunction.PRIVATE_EVAL: {"num_call_private_eval"},
}

UINT64_MAX = 18446744073709551615
MAX_CODE_SIZE_BYTES = 524288           
MIN_MEMORY_LIMIT_BYTES = 6291456         


class Session:
    pass                                                        

    def __init__(
        self,
        problem: Problem,
        lite_version: bool,
        public_seeds: list[int],
        private_seeds: list[int],
        standings: Standings,
        rank_performance_map: RankPerformanceMap,
        tool_dir: Path,
        use_same_time_scale: bool,
        maximum_resource_usage: ResourceUsage,
        session_duration: dt.timedelta,
        num_workers: int,
        visualization_server_port: int | None,
    ) -> None:
        pass                                                 

             
                                                                  
                                                                          
                                                                       
                                                                         
                                                                 
                                                                                                
                                                         
                                                                                                      
                                                                                               
                                                                         
                                                                                  
                                                                                                 
                                                        

               
                                                                                                                 

           
                                                                                                       
        self._problem = problem
        self._lite_version = lite_version
        self._public_seeds = public_seeds
        self._private_seeds = private_seeds
        self._standings = standings
        self._rank_performance_map = rank_performance_map
        self._tool_dir = tool_dir
        self._use_same_time_scale = use_same_time_scale
        self._maximum_resource_usage = maximum_resource_usage
        self._session_duration = session_duration
        self._run_visualization_server = visualization_server_port is not None
        self._visualization_server_port = visualization_server_port
        self.num_workers = num_workers                                                                           

        self._current_resource_usage = ResourceUsage()
        self._action_log: list[str] = []
        self._last_public_eval_time = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
        self._last_private_eval_time = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

        self._public_inputs = generate_inputs(public_seeds, {}, tool_dir)
        if len(self._public_inputs) != len(public_seeds):
            msg = "Failed to initialize: generating public inputs failed."
            raise AleBenchError(msg)
        self._private_inputs = generate_inputs(private_seeds, {}, tool_dir)
        if len(self._private_inputs) != len(private_seeds):
            msg = "Failed to initialize: generating private inputs failed."
            raise AleBenchError(msg)

                                                  
        self._visualization_server_container_id = None
        if visualization_server_port is not None:
            try:
                self._visualization_server_container_id = start_visualization_server(
                    visualization_server_dir=tool_dir / "visualization_server",
                    port_num=visualization_server_port,
                )
            except Exception as e:
                msg = f"Failed to start the visualization server: {e}"
                raise AleBenchError(msg) from e

                                                            
        atexit.register(self.close)

                                      
        self._session_started_at = dt.datetime.now(tz=dt.timezone.utc)

    def __repr__(self) -> str:
        pass                                                  
        return f"Session(problem_id={self.problem_id})"

               
    def code_run(
        self,
        input_str: str,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
    ) -> CodeRunResult:
        pass                                                                                      

                                                                                                             
                                                     

             
                                                                  
                                           
                                                                            
                                                                                                      
                                   
                                                                                                          
                                                                                                           

                
                                                                                                                       

               
                                                                                

           
                       
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.CODE_RUN):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        (input_list, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            input_str=input_str,
            allow_empty_input=True,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )
        if len(input_list) != 1:
            msg = "The number of inputs must be exactly one for `code_run`."
            raise RuntimeError(msg)

             
        result = run_code(
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            stdin=input_list[0],
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

                                                     
        resource_usage = ResourceUsage(execution_time_case_eval=result.execution_time)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.CODE_RUN):
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "code_run",
                    "arguments": {
                        "input_str": input_str,
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                        "time_limit": time_limit,
                        "memory_limit": memory_limit,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return result

    def case_gen(self, seed: list[int] | int = 0, gen_kwargs: dict[str, Any] | None = None) -> list[str] | str:
        pass                                                             

             
                                                                                                 
                                                                                                   

                
                                                                                                 

               
                                                                                                               

           
                       
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_GEN):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        is_scalar = isinstance(seed, int)
        seed, gen_kwargs = self._check_input_generation_arguments(seed=seed, gen_kwargs=gen_kwargs)

                    
        generated_cases = generate_inputs(seed, gen_kwargs, self._tool_dir)

                        
        if len(generated_cases) == 0:
            msg = "Failed to generate the case. Maybe you specified invalid arguments."
            raise AleBenchError(msg)
        if len(generated_cases) != len(seed):
            msg = "Something went wrong: The number of generated cases must match the number of seeds provided."
            raise AleBenchError(msg)
        self._current_resource_usage = self._current_resource_usage + ResourceUsage(num_case_gen=len(generated_cases))
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_GEN):
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "case_gen",
                    "arguments": {"seed": seed, "gen_kwargs": gen_kwargs},
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return generated_cases[0] if is_scalar else generated_cases

    def case_eval(
        self,
        input_str: list[str] | str,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
        skip_local_visualization: bool = False,
        reuse_containers: bool = False,
    ) -> Result:
        pass                                      

                                                                                                    

             
                                                                                
                                             
                                                                  
                                                                                                       
                                                                                      
                                                                                            
                                                                                                              
                                                                                                           
                                  

                
                                                 

               
                                                                                        
                                                                   

           
                       
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_EVAL):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        (input_str, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            input_str=input_str,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

                    
        case_results = run_cases(
            inputs=input_str,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=True,
            skip_local_visualization=skip_local_visualization,
            num_workers=self.num_workers,
            reuse_containers=reuse_containers,
        )

                        
        if len(case_results) != len(input_str):
            msg = "The number of case results must be equal to the number of input strings."
            raise RuntimeError(msg)
        resource_usage = ResourceUsage(
            num_case_eval=len(case_results),
            execution_time_case_eval=sum([case_result.execution_time for case_result in case_results]),
        )
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_EVAL):
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "case_eval",
                    "arguments": {
                        "input_str": input_str,
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                        "time_limit": time_limit,
                        "memory_limit": memory_limit,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return Result(
            allow_score_non_ac=True,                                                                                    
            resource_usage=resource_usage,
            case_results=case_results,
        )

    def case_gen_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        seed: list[int] | int = 0,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
        gen_kwargs: dict[str, Any] | None = None,
        skip_local_visualization: bool = False,
        reuse_containers: bool = False,
    ) -> Result:
        pass                                                          

             
                                             
                                                                  
                                                                                                       
                                                                                              
                                                                                      
                                                                                            
                                                                                                   
                                                                                                              
                                                                                                           
                                  

                
                                                 

               
                                                                                        

           
                                                                                                              
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.CASE_GEN_EVAL):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        seed, gen_kwargs = self._check_input_generation_arguments(seed=seed, gen_kwargs=gen_kwargs)
        (_, code, code_language, judge_version, time_limit, memory_limit) = self._check_run_cases_arguments(
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
        )

                                                                             
        input_str = self.case_gen(seed, gen_kwargs=gen_kwargs)
        result = self.case_eval(
            input_str=input_str,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=time_limit,
            memory_limit=memory_limit,
            skip_local_visualization=skip_local_visualization,
            reuse_containers=reuse_containers,
        )
        if not self._check_within_resource_usage_after(AleBenchFunction.CASE_GEN_EVAL):
                                                                                                        
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)
        return result

    def local_visualization(
        self,
        input_str: list[str] | str,
        output_str: list[str] | str,
    ) -> list[Image.Image | None] | Image.Image | None:
        pass                                                                  

             
                                                                                   
                                                                                     

                
                                                                                          
                                                                                          
                                                                                         

           
                       
        self._check_session_finished()
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        is_scalar = isinstance(input_str, str)
        input_str, output_str = self._check_local_visualization_arguments(input_str=input_str, output_str=output_str)

                             
        local_visualization_images = local_visualization(
            inputs=input_str,
            outputs=output_str,
            problem_id=self._problem.metadata.problem_id,
            tool_dir=self._tool_dir,
            num_workers=self.num_workers,
        )

                        
        if len(local_visualization_images) != len(input_str):
            msg = "The number of local visualization images must match the number of input strings."
            raise RuntimeError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "local_visualization",
                    "arguments": {"input_str": input_str, "output_str": output_str},
                    "elapsed_time": elapsed_time,
                }
            )
        )

        return local_visualization_images[0] if is_scalar else local_visualization_images

    def public_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        skip_local_visualization: bool = True,
        reuse_containers: bool = False,
    ) -> Result:
        pass                                           

             
                                             
                                                                  
                                                                                                       
                                                                                                             
                                                                                                           
                                  

                
                                                 

               
                                                                                        
                                                                                                     

           
                       
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.PUBLIC_EVAL):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        _, code, code_language, judge_version, _, _ = self._check_run_cases_arguments(
            code=code, code_language=code_language, judge_version=judge_version
        )
        self._last_public_eval_time = dt.datetime.now(tz=dt.timezone.utc)

                    
        public_case_results = run_cases(
            inputs=self._public_inputs,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=self._problem.constraints.time_limit,
            memory_limit=self._problem.constraints.memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=True,
            skip_local_visualization=skip_local_visualization,
            num_workers=self.num_workers,
            reuse_containers=reuse_containers,
        )

                        
        if len(public_case_results) != self.num_public_cases:
            msg = "The number of case results must be equal to the number of public seeds."
            raise RuntimeError(msg)
        resource_usage = ResourceUsage(num_call_public_eval=1)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.PUBLIC_EVAL):
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "public_eval",
                    "arguments": {
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        return Result(
            allow_score_non_ac=self.problem_id in ale_bench.constants.ALLOW_SCORE_NON_AC_PUBLIC,
            resource_usage=resource_usage,
            case_results=public_case_results,
        )

    def private_eval(
        self,
        code: str,
        code_language: CodeLanguage | str,
        judge_version: JudgeVersion | str | None = None,
        reuse_containers: bool = False,
    ) -> tuple[Result, int, int]:
        pass                                            

             
                                             
                                                                  
                                                                                                       
                                                                                                           
                                  

                
                                                 
                                                
                                                       

               
                                                                                        
                                                                                                      

           
                       
        self._check_session_finished()
        if not self._check_within_resource_usage_before(AleBenchFunction.PRIVATE_EVAL):
            msg = "The resource usage is exceeded."
            raise AleBenchError(msg)
        elapsed_time = (dt.datetime.now(tz=dt.timezone.utc) - self._session_started_at).total_seconds()
        _, code, code_language, judge_version, _, _ = self._check_run_cases_arguments(
            code=code, code_language=code_language, judge_version=judge_version
        )
        self._last_private_eval_time = dt.datetime.now(tz=dt.timezone.utc)

                    
        private_case_results = run_cases(
            inputs=self._private_inputs,
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            time_limit=self._problem.constraints.time_limit,
            memory_limit=self._problem.constraints.memory_limit,
            problem_id=self._problem.metadata.problem_id,
            problem_type=self._problem.metadata.problem_type,
            tool_dir=self._tool_dir,
            return_details=False,
            skip_local_visualization=True,
            num_workers=self.num_workers,
            reuse_containers=reuse_containers,
        )

                        
        if len(private_case_results) != self.num_private_cases:
            msg = "The number of case results must be equal to the number of private seeds."
            raise RuntimeError(msg)
        resource_usage = ResourceUsage(num_call_private_eval=1)
        self._current_resource_usage = self._current_resource_usage + resource_usage
        if not self._check_within_resource_usage_after(AleBenchFunction.PRIVATE_EVAL):
            msg = "The resource usage is exceeded after the action."
            raise AleBenchError(msg)

                                                   
        self._action_log.append(
            json.dumps(
                {
                    "function": "private_eval",
                    "arguments": {
                        "code": code,
                        "code_language": code_language.value,
                        "judge_version": judge_version.value,
                    },
                    "elapsed_time": elapsed_time,
                }
            )
        )
        private_result = Result(
            allow_score_non_ac=self.problem_id in ale_bench.constants.ALLOW_SCORE_NON_AC_PRIVATE,
            resource_usage=resource_usage,
            case_results=private_case_results,
        )
        new_rank, new_performance, relative_scores = self.estimate_rank_and_performance(private_result)
        processed_relative_cases = [
            CaseResult(
                input_str=None,
                output_str=None,
                error_str=None,
                judge_result=case_result.judge_result,
                message="",
                absolute_score=case_result.absolute_score,
                relative_score=relative_score,
                local_visualization=None,
                execution_time=case_result.execution_time,
                memory_usage=case_result.memory_usage,
            )
            for relative_score, case_result in zip(relative_scores, private_result.case_results, strict=True)
        ]                                                                                                          
        processed_private_result = Result(
            allow_score_non_ac=private_result.allow_score_non_ac,
            resource_usage=private_result.resource_usage,
            case_results=processed_relative_cases,
        )
        return processed_private_result, new_rank, new_performance

    def estimate_rank_and_performance(self, private_result: Result) -> tuple[int, int, list[int]]:
        pass                                                                                    
        new_rank, new_performance_rank, relative_scores = self._standings.get_new_rank(private_result)
        return new_rank, self._rank_performance_map.get_performance(new_performance_rank), relative_scores

    def save(self, filepath: str | os.PathLike[str] = "session.json") -> None:
        pass                               

                                                                              

             
                                                                                                                  

           
        filepath_path = Path(filepath)
        with filepath_path.open("w") as f:
            json.dump(
                {
                    "problem_id": self._problem.metadata.problem_id,
                    "lite_version": self._lite_version,
                    "public_seeds": self._public_seeds,
                    "private_seeds": self._private_seeds,
                    "use_same_time_scale": self._use_same_time_scale,
                    "maximum_resource_usage": self._maximum_resource_usage.model_dump(),
                    "session_duration": self._session_duration.total_seconds(),
                    "visualization_server_port": self._visualization_server_port,
                    "num_workers": self.num_workers,
                    "current_resource_usage": self._current_resource_usage.model_dump(),
                    "action_log": self._action_log,
                    "last_public_eval_time": self._last_public_eval_time.timestamp(),
                    "last_private_eval_time": self._last_private_eval_time.timestamp(),
                    "session_started_at": self._session_started_at.timestamp(),
                    "session_paused_at": dt.datetime.now(tz=dt.timezone.utc).timestamp(),
                },
                f,
                ensure_ascii=False,
            )
        logger.info("Session saved to %s", filepath_path.resolve())

    def close(self) -> None:
        pass                                           
        shutil.rmtree(self._tool_dir, ignore_errors=True)
        if self._visualization_server_container_id is not None:
            logger.info("Stopping the visualization server...")
            with docker_client() as client:
                try:
                    visualization_server_container = client.containers.get(self._visualization_server_container_id)
                    visualization_server_container.stop()
                    visualization_server_container.remove(force=True)
                except NotFound:
                    logger.warning("Visualization server container not found.")
            logger.info("Visualization server stopped.")
            self._run_visualization_server = False
            self._visualization_server_port = None
            self._visualization_server_container_id = None

                
    @property
    def problem(self) -> Problem:
        pass                      

                
                                        

           
        return self._problem

    @property
    def problem_id(self) -> str:
        pass                  

                
                                

           
        return self._problem.metadata.problem_id

    @property
    def lite_version(self) -> bool:
        pass                                          

                
                                                         

           
        return self._lite_version

    @property
    def public_seeds(self) -> list[int]:
        pass                    

                
                                        

           
        return self._public_seeds

    @property
    def num_public_cases(self) -> int:
        pass                              

                
                                            

           
        return len(self._public_seeds)

    @property
    def private_seeds(self) -> NoReturn:
        pass                     

               
                                                                  

           
        msg = "Accessing private seeds is not allowed."
        raise AleBenchError(msg)

    @property
    def num_private_cases(self) -> int:
        pass                               

                
                                             

           
        return len(self._private_seeds)

    @property
    def standings(self) -> NoReturn:
        pass                 

               
                                                              

           
        msg = "Accessing standings is not allowed."
        raise AleBenchError(msg)

    @property
    def rank_performance_map(self) -> NoReturn:
        pass                            

               
                                                                         

           
        msg = "Accessing rank performance map is not allowed."
        raise AleBenchError(msg)

    @property
    def tool_dir(self) -> Path:
        pass                               

                
                                              

           
        return self._tool_dir

    @property
    def rust_src_dir(self) -> Path:
        pass                                                

                
                                              

           
        return self._tool_dir / "tools" / "src"

    @property
    def use_same_time_scale(self) -> bool:
        pass                                      

                
                                                     

           
        return self._use_same_time_scale

    @property
    def maximum_resource_usage(self) -> ResourceUsage:
        pass                              

                
                                                      

           
        return self._maximum_resource_usage

    @property
    def current_resource_usage(self) -> ResourceUsage:
        pass                              

                
                                                      

           
        return self._current_resource_usage

    @property
    def remaining_resource_usage(self) -> ResourceUsage:
        pass                                

                
                                                        

           
        return self._maximum_resource_usage - self._current_resource_usage

    @property
    def action_log(self) -> list[str]:
        pass                  

                
                                      

           
        return self._action_log

    @property
    def last_public_eval_time(self) -> dt.datetime:
        pass                                                          

                
                                                                                

           
        return self._last_public_eval_time

    @property
    def next_public_eval_time(self) -> dt.datetime:
        pass                                                             

                
                                                                                   

           
        if self._use_same_time_scale:
            return self._last_public_eval_time + dt.timedelta(
                seconds=self._problem.metadata.submission_interval_seconds
            )
        return self._last_public_eval_time

    @property
    def last_private_eval_time(self) -> dt.datetime:
        pass                                                           

                
                                                                                 

           
        return self._last_private_eval_time

    @property
    def session_duration(self) -> dt.timedelta:
        pass                               

                
                                                      

           
        return self._session_duration

    @property
    def session_started_at(self) -> dt.datetime:
        pass                                     

                
                                                           

           
        return self._session_started_at

    @property
    def session_remaining_time(self) -> dt.timedelta:
        pass                                     

                
                                                            

           
        return self._session_started_at + self._session_duration - dt.datetime.now(tz=dt.timezone.utc)

    @property
    def session_finished(self) -> bool:
        pass                                

                
                                                  

               
                                                      

           
        return not self._check_within_resource_usage_before(AleBenchFunction.PRIVATE_EVAL)

    @property
    def run_visualization_server(self) -> bool:
        pass                                           

                
                                                          

           
        return self._run_visualization_server

    @property
    def visualization_server_port(self) -> int | None:
        pass                                               

                
                                                                                           

           
        return self._visualization_server_port

              
    def _check_session_finished(self) -> None:
        msg = "The session is finished."
        try:
            session_finished = self.session_finished
        except AleBenchError as e:
            raise AleBenchError(msg) from e
        if session_finished:
            raise AleBenchError(msg)

    def _check_within_resource_usage_before(self, function_type: AleBenchFunction) -> bool:
        pass                                                                                                          
        if self.session_remaining_time.total_seconds() <= 0:
                                                                           
                                                                      
                                                                                                          
            msg = "The session has already finished."
            raise AleBenchError(msg)
        is_within_resource_usage = all(
            getattr(self._current_resource_usage, field) < getattr(self._maximum_resource_usage, field)
            for field in CHECK_RESOURCE_USAGE_FIELDS[function_type]
        )
        if not is_within_resource_usage:
            msg = f"Exceeded the maximum resource usage for the `{function_type.value}` function."
            raise AleBenchError(msg)
        if (
            self._use_same_time_scale
            and function_type == AleBenchFunction.PUBLIC_EVAL
            and dt.datetime.now(tz=dt.timezone.utc) < self.next_public_eval_time
        ):
            msg = "The next public evaluation is not allowed yet."
            raise AleBenchError(msg)
        return is_within_resource_usage

    def _check_within_resource_usage_after(self, function_type: AleBenchFunction) -> bool:
        pass                                                                                                         
        is_within_resource_usage = all(
            getattr(self._current_resource_usage, field) <= getattr(self._maximum_resource_usage, field)
            for field in CHECK_RESOURCE_USAGE_FIELDS[function_type]
        )                                               
        if not is_within_resource_usage:
            msg = f"Exceeded the maximum resource usage for the `{function_type.value}` function after the action."
            raise AleBenchError(msg)
        return is_within_resource_usage

    def _check_input_generation_arguments(
        self,
        seed: list[int] | int | None = None,
        gen_kwargs: dict[str, Any] | None = None,
    ) -> tuple[list[int], dict[str, Any]]:
        pass                                                         
                      
        if seed is None:
            seed = [0]
        else:
            if isinstance(seed, int):
                seed = [seed]
            for s in seed:
                if s < 0 or s > UINT64_MAX:                                 
                    msg = "`seed` must be between 0 and 2^64 - 1."
                    raise AleBenchError(msg)

                            
        ret_gen_kwargs = {}
        if gen_kwargs is not None:
            for key in gen_kwargs:
                if key == "dir":
                    warnings.warn("`dir` is a reserved keyword and will be ignored.", stacklevel=2)
                else:
                    ret_gen_kwargs[key] = gen_kwargs[key]

        return seed, ret_gen_kwargs

    def _check_local_visualization_arguments(
        self,
        input_str: list[str] | str,
        output_str: list[str] | str,
    ) -> tuple[list[str], list[str]]:
        pass                                                             
        if isinstance(input_str, str) and isinstance(output_str, str):
            input_str = [input_str]
            output_str = [output_str]
        elif isinstance(input_str, str) or isinstance(output_str, str):
            msg = "Both `input_str` and `output_str` must be either a string or a list of strings."
            raise AleBenchError(msg)
                                                          
        if len(input_str) != len(output_str):
            msg = "The number of input strings and output strings must be the same."
            raise AleBenchError(msg)
                                                         
        if len(input_str) == 0 or any(in_s.strip() == "" for in_s in input_str):
            msg = "The input string is empty."
            raise AleBenchError(msg)
        if len(output_str) == 0 or any(out_s.strip() == "" for out_s in output_str):
            msg = "The output string is empty."
            raise AleBenchError(msg)
        return input_str, output_str

    def _check_run_cases_arguments(
        self,
        input_str: list[str] | str | None = None,
        allow_empty_input: bool = False,
        code: str | None = None,
        code_language: CodeLanguage | str | None = None,
        judge_version: JudgeVersion | str | None = None,
        time_limit: float | None = None,
        memory_limit: int | str | None = None,
    ) -> tuple[list[str], str, CodeLanguage, JudgeVersion, float, int]:
        pass                                                   
                           
        if input_str is None:
            input_str = [""]
        else:
            if isinstance(input_str, str):
                input_str = [input_str]
            for in_s in input_str:
                if in_s.strip() == "" and not allow_empty_input:
                    msg = "The input string is empty."
                    raise AleBenchError(msg)

                      
        if code is None:
            msg = "`code` must be specified."
            raise AleBenchError(msg)
        code_byte_size = len(code.encode("utf-8"))
        if code_byte_size > MAX_CODE_SIZE_BYTES:                 
            msg = "The size of the submission code exceeds the limit (512 KiB)."
            raise AleBenchError(msg)
        if code.strip() == "":
            msg = "The submission code is empty."
            raise AleBenchError(msg)

                                                   
        if code_language is None:
            msg = "`code_language` must be specified."
            raise AleBenchError(msg)
        if isinstance(code_language, str):
            try:
                code_language = CodeLanguage(code_language)
            except ValueError as e:
                msg = f"Invalid code language. Available options: {', '.join(CodeLanguage.__members__)}"
                raise AleBenchError(msg) from e
        if judge_version is None:
            judge_version = JudgeVersion.V202301                                                 
        elif isinstance(judge_version, str):
            try:
                judge_version = JudgeVersion(judge_version)
            except ValueError as e:
                msg = f"Invalid judge version. Available options: {', '.join(JudgeVersion.__members__)}"
                raise AleBenchError(msg) from e
        try:
            get_compile_command(code_language, judge_version)
        except ValueError as e:
            raise AleBenchError(str(e)) from e

                            
        if time_limit is None:
            time_limit = self._problem.constraints.time_limit                                    
        if time_limit <= 0.0:
            msg = "`time_limit` must be positive."
            raise AleBenchError(msg)

                              
        if memory_limit is None:
            memory_limit = self._problem.constraints.memory_limit                                      
        else:
            if isinstance(memory_limit, str):
                memory_limit = memory_limit.lower()
                try:
                    if memory_limit.endswith("b"):
                        memory_limit = int(memory_limit[:-1])
                    elif memory_limit.endswith("k"):
                        memory_limit = int(memory_limit[:-1]) * 1024
                    elif memory_limit.endswith("m"):
                        memory_limit = int(memory_limit[:-1]) * 1048576
                    elif memory_limit.endswith("g"):
                        memory_limit = int(memory_limit[:-1]) * 1073741824
                    else:
                        memory_limit = int(memory_limit)
                except ValueError:
                    msg = "Invalid `memory_limit` format. Use 'b', 'k', 'm', or 'g' suffixes."
                    raise AleBenchError(msg) from None
            memory_limit = min(memory_limit, ale_bench.constants.MAX_MEMORY_LIMIT)
            if memory_limit < MIN_MEMORY_LIMIT_BYTES:
                msg = "`memory_limit` must be greater than or equal to 6MB."
                raise AleBenchError(msg)

        return input_str, code, code_language, judge_version, time_limit, memory_limit
