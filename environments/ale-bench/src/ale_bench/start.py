                                                                  

import datetime as dt
import json
import logging
import math
import os
import warnings
from pathlib import Path

from ale_bench.data import build_rust_tools, list_problem_ids, load_problem
from ale_bench.error import AleBenchError
from ale_bench.result import ResourceUsage
from ale_bench.session import Session
from ale_bench.utils import find_free_port, get_cache_dir

logger = logging.getLogger(__name__)


def start(
    problem_id: str,
    lite_version: bool = False,
    use_same_time_scale: bool = False,
    maximum_num_case_gen: int = int(1e18),
    maximum_num_case_eval: int = int(1e18),
    maximum_execution_time_case_eval: float = 1e18,
    maximum_num_call_public_eval: int = int(1e18),
    session_duration: dt.timedelta | float | None = None,
    num_workers: int = 1,
    run_visualization_server: bool = False,
    visualization_server_port: int | None = None,
) -> Session:
    pass                                            

         
                                                                       
                                                                                
                                                                                                                       
                                                                                                  
                                                                                                   
                                                                                                                        
                                                                                                                  
                                                                                                               
                                                                                                       
                                                                                                              
                                                                                                                  
                                                                                                  

            
                                                             

           
                                                      

       
                                   
    cache_dir = get_cache_dir()
    if not cache_dir.is_dir():
        logger.info("Creating cache directory: %s", cache_dir)
        cache_dir.mkdir(parents=True)

                                    
    if problem_id not in list_problem_ids(lite_version=lite_version):
        msg = f"Problem ID {problem_id} not found."
        raise AleBenchError(msg)

                      
    problem, seeds, standings, rank_performance_map, data_root = load_problem(
        problem_id=problem_id,
        lite_version=lite_version,
    )

                          
    build_rust_tools(data_root / "tools")

                                                
    num_call_public_eval = (
        math.floor(problem.metadata.duration.total_seconds()) // problem.metadata.submission_interval_seconds
    )
    maximum_resource_usage = ResourceUsage(
        num_case_gen=maximum_num_case_gen,
        num_case_eval=maximum_num_case_eval,
        num_call_public_eval=num_call_public_eval if use_same_time_scale else maximum_num_call_public_eval,
        num_call_private_eval=1,                                              
        execution_time_case_eval=maximum_execution_time_case_eval,
    )

                                          
    if session_duration is None:
        session_duration = problem.metadata.duration
    elif isinstance(session_duration, (int, float)):
        session_duration = dt.timedelta(seconds=session_duration)

                                                       
    if run_visualization_server:
        if visualization_server_port is None:
            visualization_server_port = find_free_port(min_port=9000, max_port=65535)
    else:
        visualization_server_port = None                                      

                                          
                                                                                    
    return Session(
        problem=problem,
        lite_version=lite_version,
        public_seeds=seeds.public,
        private_seeds=seeds.private,
        standings=standings,
        rank_performance_map=rank_performance_map,
        tool_dir=data_root,
        use_same_time_scale=use_same_time_scale,
        maximum_resource_usage=maximum_resource_usage,
        session_duration=session_duration,
        num_workers=num_workers,
        visualization_server_port=visualization_server_port,
    )


def restart(
    session_saved_file: str | os.PathLike[str],
    num_workers: int | None = None,
    visualization_server_port: int | None = None,
) -> Session:
    pass                                   

         
                                                                                        
                                                                                                       
                                                                                                                  
                                                                                                                 

            
                                              

             
                                                                                           
                                                                                                    

       
    session_data = json.loads(Path(session_saved_file).read_text())

                      
    problem, seeds, standings, rank_performance_map, data_root = load_problem(
        problem_id=session_data["problem_id"],
        lite_version=session_data["lite_version"],
    )

                          
    build_rust_tools(data_root / "tools")

                                                                                         
    if num_workers is None:
        num_workers = session_data["num_workers"]
    elif num_workers != session_data["num_workers"]:
        warnings.warn(
            f"Number of workers in the saved session ({session_data['num_workers']}) "
            f"is different from the provided one ({num_workers}).",
            stacklevel=2,
        )

                                                       
    if visualization_server_port is None:
        visualization_server_port = session_data["visualization_server_port"]
    elif session_data["visualization_server_port"] is None:
        warnings.warn(
            "The saved session did not use the visualization server but the new session will use it.",
            stacklevel=2,
        )

                                          
    session = Session(
        problem=problem,
        lite_version=session_data["lite_version"],
        public_seeds=seeds.public,
        private_seeds=seeds.private,
        standings=standings,
        rank_performance_map=rank_performance_map,
        tool_dir=data_root,
        use_same_time_scale=session_data["use_same_time_scale"],
        maximum_resource_usage=ResourceUsage.model_validate(session_data["maximum_resource_usage"]),
        session_duration=dt.timedelta(seconds=session_data["session_duration"]),
        num_workers=num_workers,
        visualization_server_port=visualization_server_port,
    )

    session._current_resource_usage = ResourceUsage.model_validate(                
        session_data["current_resource_usage"]
    )
    session._action_log = session_data["action_log"]                

    session._session_started_at -= dt.datetime.fromtimestamp(                
        session_data["session_paused_at"], tz=dt.timezone.utc
    ) - dt.datetime.fromtimestamp(
        session_data["session_started_at"], tz=dt.timezone.utc
    )                                                              
    if session_data["last_public_eval_time"] >= session_data["session_started_at"]:
        session._last_public_eval_time = session._session_started_at + dt.timedelta(                
            seconds=session_data["last_public_eval_time"] - session_data["session_started_at"]
        )
    if session_data["last_private_eval_time"] >= session_data["session_started_at"]:
        session._last_private_eval_time = session._session_started_at + dt.timedelta(                
            seconds=session_data["last_private_eval_time"] - session_data["session_started_at"]
        )
    return session
