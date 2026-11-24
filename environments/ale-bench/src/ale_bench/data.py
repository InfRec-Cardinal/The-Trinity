                                                      

import datetime as dt
import json
import math
import os
import shutil
import tempfile
import zipfile
from collections import Counter
from enum import Enum
from pathlib import Path
from typing import Final

import polars as pl
from PIL import Image
from huggingface_hub import hf_hub_download
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

import ale_bench.constants
from ale_bench.result import JudgeResult, Result
from ale_bench.utils import docker_client, get_cache_dir, get_local_data_dir, read_svg


class ProblemType(str, Enum):
    pass                           

                            
                                  
       

    BATCH = "batch"
    REACTIVE = "reactive"


class ScoreType(str, Enum):
    pass                         

                                             
                                             
       

    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"


class RankPerformanceMap(BaseModel):
    pass                              

                                                                                                              
                                                    
                                                                                                  
       

    model_config = ConfigDict(frozen=True)

    raw_data: list[tuple[int, int]] = Field(
        description="Raw data of the map of rank to performance (rank, performance)"
    )
    data: dict[float, int] = Field(default_factory=dict, description="Map of rank to performance")

    @field_validator("raw_data")
    @classmethod
    def validate_raw_data(cls, raw_data: list[tuple[int, int]]) -> list[tuple[int, int]]:
        pass                        
        if len(raw_data) <= 1:
            msg = "The raw data must contain at least 2 entries."
            raise ValueError(msg)
        for i in range(1, len(raw_data)):
            if raw_data[i - 1][0] > raw_data[i][0]:
                msg = "The rank must be sorted in ascending order."
                raise ValueError(msg)
            if raw_data[i - 1][1] < raw_data[i][1]:
                msg = "The performance must be sorted in descending order."
                raise ValueError(msg)
        return raw_data

    def model_post_init(self, __context: object, /) -> None:
        pass                             
                                             
        self.data.clear()                                                      
        for i in range(len(self.raw_data) - 1):
            rank, performance = self.raw_data[i]
            next_rank, next_performance = self.raw_data[i + 1]
            if rank == next_rank:
                if performance != next_performance:
                    msg = "Something went wrong: `performance` != `next_performance`."
                    raise RuntimeError(msg)
                continue             
            actual_rank = float((rank + next_rank - 1) / 2)                                                           
            self.data[actual_rank] = performance
        self.data[float(self.raw_data[-1][0])] = self.raw_data[-1][1]                                    

    def get_performance(self, rank: float) -> int:
        pass                                    

                                                                                                       
                                                                
                                                                    
                                                                                                       
                                                                                                             
                                                                                                             
                                                                                                                       

             
                                                                    

                
                                                                   

           
        rank = float(rank)
        if rank in self.data:
            return self.data[rank]
                                                                           
        sorted_keys = sorted(self.data.keys())
        lose, win = -1, len(sorted_keys)
        while win - lose > 1:
            mid = (lose + win) // 2
            if rank < sorted_keys[mid]:
                win = mid
            else:
                lose = mid
        if win == len(sorted_keys):
            msg = "Something went wrong: `win` should be less than `len(sorted_keys)`."
            raise RuntimeError(msg)
        if win == 0:
            win = 1                                                                   
        rank_high = sorted_keys[win - 1]
        rank_low = sorted_keys[win]
        perf_high = self.data[rank_high]
        perf_low = self.data[rank_low]
        return round(perf_high - (perf_high - perf_low) * (rank - rank_high) / (rank_low - rank_high))


class RelativeScoreType(str, Enum):
    pass                                  

                                                                                               
                                                                                                
                                                                                          
                                                                                           
       

    MIN = "min"
    MAX = "max"
    RANK_MIN = "rank_min"
    RANK_MAX = "rank_max"


class RelativeResults(BaseModel):
    pass                                          

                                                                                                          
       

    model_config = ConfigDict(frozen=True)

    absolute_scores: list[list[int]] = Field(
        description="Relative results data. List of cases (each case is a list of scores)",
    )
    relative_score_type: RelativeScoreType = Field(
        description="Relative score type of the problem (min, max, rank_min, rank_max)",
    )
    relative_max_score: int = Field(description="Maximum score per case for the relative score")

    @field_validator("absolute_scores")
    @classmethod
    def validate_absolute_scores(cls, absolute_scores: list[list[int]]) -> list[list[int]]:
        pass                               
        if len(absolute_scores) == 0:
            msg = "The relative results absolute_scores cannot be empty."
            raise ValueError(msg)
        num_participants = len(absolute_scores[0])
        if num_participants == 0:
            msg = "The number of participants must be greater than 0."
            raise ValueError(msg)
        for i in range(len(absolute_scores)):
            if len(absolute_scores[i]) != num_participants:
                msg = "The number of participants must be the same for all cases."
                raise ValueError(msg)
        return absolute_scores

    def recalculate_relative_score(self, new_scores: list[int]) -> tuple[int, list[int], list[int]]:
        pass                                                              

             
                                                                      
                                                                                                     

                
                                                                                                                        
                                                                     
                                                                                                      
                                                                                  
                                                                                                                      
                                                                                                              

           
        if len(new_scores) != len(self.absolute_scores):
            msg = (
                f"The number of new scores ({len(new_scores)}) must be "
                f"the same as the number of cases ({len(self.absolute_scores)})."
            )
            raise ValueError(msg)
        new_relative_case_scores = []
        new_overall_relative_scores_existing = [0 for _ in range(len(self.absolute_scores[0]))]
        for new_score, existing_scores in zip(new_scores, self.absolute_scores, strict=True):
                                                                    
            if new_score < 0:                       
                case_scores = [*existing_scores, -1]
            elif new_score == 0:                                    
                if self.relative_score_type == RelativeScoreType.MIN:
                    msg = "If `relative_score_type` is `min`, absolute score should be greater than 0."
                    raise RuntimeError(msg)
                case_scores = [*existing_scores, 0]
            else:
                case_scores = [*existing_scores, new_score]
                                              
            relative_scores = []
            if self.relative_score_type == RelativeScoreType.MAX:
                best_score = None
                for case_score in case_scores:
                    if case_score >= 0 and (best_score is None or case_score > best_score):
                        best_score = case_score
                for user_score in case_scores:
                    relative_score = 0
                    if user_score >= 0:
                        if best_score is None:
                            msg = "Something went wrong: `best_score` should not be None."
                            raise RuntimeError(msg)
                        relative_score = self.relative_max_score * user_score // best_score
                        if self.relative_max_score * user_score % best_score * 2 >= best_score:
                            relative_score += 1            
                    relative_scores.append(relative_score)
            elif self.relative_score_type == RelativeScoreType.MIN:
                best_score = None
                for case_score in case_scores:
                    if case_score >= 0 and (best_score is None or case_score < best_score):
                        best_score = case_score
                for user_score in case_scores:
                    relative_score = 0
                    if user_score == 0:
                        msg = f"Zero score is not allowed for `relative_score_type` {self.relative_score_type}."
                        raise ValueError(msg)
                    if user_score > 0:
                        if best_score is None:
                            msg = "Something went wrong: `best_score` should not be None."
                            raise RuntimeError(msg)
                        relative_score = self.relative_max_score * best_score // user_score
                        if self.relative_max_score * best_score % user_score * 2 >= user_score:
                            relative_score += 1            
                    relative_scores.append(relative_score)
            elif self.relative_score_type in {RelativeScoreType.RANK_MAX, RelativeScoreType.RANK_MIN}:
                score_counts = Counter(case_score for case_score in case_scores if case_score >= 0)
                relative_scores_by_absolute_score: dict[int, int] = {}
                n_submit = len(case_scores)
                n_lose = 0
                sorted_absolute_scores = sorted(
                    score_counts.keys(),
                    reverse=self.relative_score_type == RelativeScoreType.RANK_MAX,
                )
                for absolute_score in sorted_absolute_scores:
                    n_tie = score_counts[absolute_score] - 1                                                          
                    relative_scores_by_absolute_score[absolute_score] = round(
                        self.relative_max_score * (1.0 - (n_lose + n_tie / 2) / n_submit)
                    )
                    n_lose += score_counts[absolute_score]
                relative_scores = [
                    relative_scores_by_absolute_score[case_score] if case_score >= 0 else 0
                    for case_score in case_scores
                ]
            for user_idx, relative_score in enumerate(relative_scores):
                                                                          
                                                                                    
                if user_idx == len(existing_scores):
                    new_relative_case_scores.append(relative_score)
                else:
                    new_overall_relative_scores_existing[user_idx] += relative_score
                                                                 
        new_overall_relative_score = sum(new_relative_case_scores)
        new_overall_relative_scores = sorted(
            [*new_overall_relative_scores_existing, new_overall_relative_score], reverse=True
        )
        return new_overall_relative_score, new_relative_case_scores, new_overall_relative_scores


class Standings(BaseModel):
    pass                                   

                                                                  
       

    model_config = ConfigDict(frozen=True)

    standings_scores: list[tuple[int, int]] = Field(description="List of standings scores (rank, score)")
    score_rank_list: list[tuple[int, int, int]] = Field(
        default_factory=list, description="List of score to rank (score, start rank, end rank)"
    )
    relative_results: RelativeResults | None = Field(
        default=None, description="Result (absolute score) of the private cases"
    )

    @field_validator("standings_scores")
    @classmethod
    def validate_data(cls, standings_scores: list[tuple[int, int]]) -> list[tuple[int, int]]:
        pass                              
        if len(standings_scores) == 0:
            msg = "The standings scores cannot be empty."
            raise ValueError(msg)
        for i in range(1, len(standings_scores)):
            if standings_scores[i - 1][0] > standings_scores[i][0]:
                msg = "The rank must be sorted in ascending order."
                raise ValueError(msg)
            if standings_scores[i - 1][1] < standings_scores[i][1]:
                msg = "The score must be sorted in descending order."
                raise ValueError(msg)
            if standings_scores[i - 1][1] <= 0:
                msg = "The score must be greater than 0 except for the last entry."
                raise ValueError(msg)
        if standings_scores[-1][1] != 0:
            msg = "The last entry must be an entry with score 0."
            raise ValueError(msg)
        return standings_scores

    def model_post_init(self, __context: object, /) -> None:
        pass                             
        self.score_rank_list.clear()                                                      
        rank_start = self.standings_scores[0][0]
        for i in range(1, len(self.standings_scores)):
            score = self.standings_scores[i - 1][1]
            next_rank, next_score = self.standings_scores[i]
            if score == next_score:
                continue                                                                    
            self.score_rank_list.append((score, rank_start, next_rank - 1))
            rank_start = next_rank
        self.score_rank_list.append(
            (self.standings_scores[-1][1], self.standings_scores[-1][0], self.standings_scores[-1][0])
        )                              
        for i in range(len(self.score_rank_list) - 1):
            _, _, end_rank = self.score_rank_list[i]
            _, next_start_rank, _ = self.score_rank_list[i + 1]
            if next_start_rank != end_rank + 1:
                msg = "Something went wrong: `next_start_rank` != `end_rank + 1`."
                raise RuntimeError(msg)

    def get_new_rank(self, private_result: Result) -> tuple[int, float, list[int]]:
        pass                                           

             
                                                                                

                
                                                                                                  
                                                                                 
                                                                                                  
                                                                                                               
                                                                                     
                                                                               

               
                                                 

           
        if self.relative_results is not None:                                                
            new_absolute_scores = [
                case_result.absolute_score if case_result.judge_result == JudgeResult.ACCEPTED else -1
                for case_result in private_result.case_results
            ]
            (new_relative_score, new_relative_case_scores, new_relative_scores) = (
                self.relative_results.recalculate_relative_score(new_absolute_scores)
            )
            if new_relative_score == 0:                          
                return (
                    self.score_rank_list[-1][1],
                    float(self.score_rank_list[-1][1]),
                    new_relative_case_scores,
                )                                                           
            new_rank, performance_additional = 1, 0.0
            for score in new_relative_scores:
                if new_relative_score > score:
                    break
                if new_relative_score == score:
                    performance_additional += 0.5
                else:
                    new_rank += 1
                                                                            
                                                                                              
                                                                                                    
            return new_rank, float(new_rank) + max(performance_additional - 1.0, 0.0), new_relative_case_scores
                                                                                           
                                                                                                          
        new_score = private_result.overall_absolute_score
        new_case_scores = [
            case_result.absolute_score if case_result.judge_result == JudgeResult.ACCEPTED else 0
            for case_result in private_result.case_results
        ]
        if new_score == 0:                          
            return (
                self.score_rank_list[-1][1],
                float(self.score_rank_list[-1][1]),
                new_case_scores,
            )                                                           
        for score, start_rank, end_rank in self.score_rank_list:
            if new_score > score:
                return start_rank, float(start_rank), new_case_scores
            if new_score == score:
                return start_rank, float((start_rank + end_rank) / 2), new_case_scores                              
        msg = "Something went wrong in `get_new_rank` method."
        raise RuntimeError(msg)


class ProblemMetaData(BaseModel):
    pass                                     

    model_config = ConfigDict(frozen=True)

    problem_id: str = Field(description="Problem ID")
    start_at: dt.datetime = Field(description="Start time of the problem in ISO 8601 format")
    end_at: dt.datetime = Field(description="End time of the problem in ISO 8601 format")
    contest_url: str = Field(description="URL of the original contest")
    title: str = Field(description="Title of the problem")
    problem_type: ProblemType = Field(description="Problem type of the problem")
    score_type: ScoreType = Field(description="Score type of the problem")

    def model_post_init(self, __context: object, /) -> None:
        pass                             
        if self.start_at >= self.end_at:
            msg = "The start time must be earlier than the end time."
            raise ValueError(msg)

    @field_serializer("start_at")
    def serialize_start_at(self, start_at: dt.datetime) -> str:
        pass                                        
        return start_at.isoformat()

    @field_serializer("end_at")
    def serialize_end_at(self, end_at: dt.datetime) -> str:
        pass                                      
        return end_at.isoformat()

    @property
    def duration(self) -> dt.timedelta:
        pass                       

                
                                                  

           
        return self.end_at - self.start_at

    @property
    def submission_interval_seconds(self) -> int:
        pass                              

                
                                                

           
        if self.duration < dt.timedelta(days=1):
            return 300                                      
        return 1800                                      


class ProblemConstraints(BaseModel):
    pass                                        

    model_config = ConfigDict(frozen=True)

    time_limit: float = Field(description="Time limit of the problem in seconds")
    memory_limit: int = Field(description="Memory limit of the problem in bytes")


class Problem(BaseModel):
    pass                              

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: ProblemMetaData
    constraints: ProblemConstraints = Field(description="Problem constraints")
    statement: str = Field(description="Problem statement (English) in Markdown format")
    statement_ja: str = Field(description="Problem statement (Japanese) in Markdown format")
    statement_images: dict[str, Image.Image | list[Image.Image]] = Field(
        description="Problem statement images in PIL Image format (key: image name, value: image object)",
        default_factory=dict,
    )
    example_input: str = Field(description="Example input")
    example_output: str = Field(description="Example output")
    tool_readme: str = Field(description="Readme of the tools in Markdown format")

    def model_post_init(self, __context: object, /) -> None:
        pass                             
        for image_name in self.statement_images:
            if image_name not in self.statement:
                msg = f"Image `{image_name}` not found in the problem statement."
                raise ValueError(msg)


class Seeds(BaseModel):
    pass                           

    model_config = ConfigDict(frozen=True)

    public: list[int] = Field(description="Public seed values")
    private: list[int] = Field(description="Private seed values")


def list_problem_ids(*, lite_version: bool = False) -> list[str]:
    pass                                                     

         
                                                                                                

            
                                        

       
    local_data_dir = get_local_data_dir()
    filename = "problem_ids_lite.txt" if lite_version else "problem_ids.txt"
    if local_data_dir is None or not (local_data_dir / filename).is_file():
        cache_dir = get_cache_dir()
        problem_ids_file_path = Path(
            hf_hub_download(
                repo_id=ale_bench.constants.HUGGING_FACE_REPO,
                filename=filename,
                repo_type="dataset",
                cache_dir=cache_dir,
            )
        )
    else:
        problem_ids_file_path = local_data_dir / filename
    with problem_ids_file_path.open() as f:
        return f.read().splitlines()


def load_problem(problem_id: str, *, lite_version: bool) -> tuple[Problem, Seeds, Standings, RankPerformanceMap, Path]:
    pass                                        

         
                                                        
                                                                      

            
                                                                                      
                                                                                                                

       
    cache_dir = get_cache_dir()
    local_data_dir = get_local_data_dir()
    if local_data_dir is None or not (local_data_dir / f"{problem_id}.zip").is_file():
                                                         
        data_path = hf_hub_download(
            repo_id=ale_bench.constants.HUGGING_FACE_REPO,
            filename=f"{problem_id}.zip",
            repo_type="dataset",
            cache_dir=cache_dir,
        )
    else:
        data_path = str(local_data_dir / f"{problem_id}.zip")

                                                                     
    data_root = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(data_path, "r") as zf:
        zf.extractall(data_root)
    shutil.copytree(data_root / problem_id, data_root, copy_function=shutil.move, dirs_exist_ok=True)
    shutil.rmtree(data_root / problem_id)                                              

                           
    with (data_root / "data.json").open() as f:
        data = json.load(f)
    (data_root / "data.json").unlink()                                      
    metadata = data["metadata"]
    if metadata["problem_id"] != problem_id:
        msg = f"Problem ID mismatch: {metadata['problem_id']} != {problem_id}"
        raise ValueError(msg)
    constraints = ProblemConstraints(**data["constraints"])
    image_files = data["image_files"]
    seeds = Seeds(
        public=data["seeds"]["public_lite"] if lite_version else data["seeds"]["public"],
        private=data["seeds"]["private_lite"] if lite_version else data["seeds"]["private"],
    )

                                
    statement_en = (data_root / "statement_en.md").read_text()
    (data_root / "statement_en.md").unlink()                                                   
    statement_ja = (data_root / "statement_ja.md").read_text()
    (data_root / "statement_ja.md").unlink()                                                    
    example_input = (data_root / "example_input.txt").read_text()
    (data_root / "example_input.txt").unlink()                                               
    example_output = (data_root / "example_output.txt").read_text()
    (data_root / "example_output.txt").unlink()                                                

                                   
    df_standings_score = pl.read_csv(
        data_root / "standings_scores_lite.csv" if lite_version else data_root / "standings_scores.csv"
    )
    (data_root / "standings_scores.csv").unlink()                                                 
    (data_root / "standings_scores_lite.csv").unlink()                                                 
    standings_score_data = df_standings_score.sort(by=["rank"], descending=[False]).rows()

                                          
    relative_results = None
    if "relative_score_type" in metadata:
        if "relative_max_score" not in metadata:
            msg = "relative_max_score is required for relative results"
            raise ValueError(msg)
        if not (data_root / "relative_results.csv").is_file():
            msg = "relative_results.csv is required for relative results"
            raise FileNotFoundError(msg)
        if not (data_root / "relative_results_lite.csv").is_file():
            msg = "relative_results_lite.csv is required for relative results"
            raise FileNotFoundError(msg)
        df_relative_results = pl.read_csv(
            data_root / "relative_results_lite.csv" if lite_version else data_root / "relative_results.csv"
        )
        (data_root / "relative_results.csv").unlink()                                                  
        (data_root / "relative_results_lite.csv").unlink()                                                  

        expected_columns = [f"private_{i}" for i in range(len(seeds.private))]
        if df_relative_results.columns != expected_columns:
            msg = "The columns of relative_results.csv must be private_0, private_1, ..."
            raise ValueError(msg)
        relative_results = RelativeResults(
            absolute_scores=[df_relative_results[col].to_list() for col in df_relative_results.columns],
            relative_score_type=metadata["relative_score_type"],
            relative_max_score=metadata["relative_max_score"],
        )
        if len(relative_results.absolute_scores) != len(seeds.private):
            msg = "Number of private cases mismatch"
            raise ValueError(msg)
    standings = Standings(standings_scores=standings_score_data, relative_results=relative_results)

                               
    df_performance = pl.read_csv(data_root / "performance.csv")
    (data_root / "performance.csv").unlink()                                             
    performance_data = df_performance.sort(by=["rank"], descending=[False]).rows()
    rank_performance_map = RankPerformanceMap(raw_data=performance_data)

                                       
    statement_images: dict[str, Image.Image | list[Image.Image]] = {}
    for filename, frames in image_files.items():
        images: list[Image.Image] = []
        for frame in frames:
            if frame.endswith(".svg"):
                                                                                                      
                                                         
                images.append(read_svg((data_root / "images" / frame).read_text()))
            else:
                images.append(Image.open(data_root / "images" / frame))
                                                                         
        statement_images[filename] = images if len(images) > 1 else images[0]

                          
    tool_readme = ""
    tool_readme_path = data_root / "tools" / "README.md"
    if not tool_readme_path.is_file():
        msg = "README.md is required for the tools"
        raise FileNotFoundError(msg)
    tool_readme = tool_readme_path.read_text()

                                                   
    problem = Problem(
        metadata=ProblemMetaData(**metadata),
        constraints=constraints,
        statement=statement_en,
        statement_ja=statement_ja,
        statement_images=statement_images,
        example_input=example_input,
        example_output=example_output,
        tool_readme=tool_readme,
    )

    return problem, seeds, standings, rank_performance_map, data_root


def build_rust_tools(tool_cache_dir: Path) -> None:
    pass                    

         
                                                                                                             

           
                                         

       
    with docker_client() as client:
        build_container = client.containers.run(
            image=ale_bench.constants.RUST_TOOL_DOCKER_IMAGE,
            command="cargo build --release",
            remove=False,
            auto_remove=False,
            detach=True,
            environment={"RUSTFLAGS": "-Awarnings"},
            group_add=[os.getgid()],
            user=os.getuid(),
            volumes={str(tool_cache_dir): {"bind": ale_bench.constants.WORK_DIR, "mode": "rw"}},
            working_dir=ale_bench.constants.WORK_DIR,
        )
        try:
            build_container.wait()
                                               
            if build_container.attrs["State"]["ExitCode"] != 0:
                msg = "Failed to build the Rust tool."
                raise RuntimeError(msg)
        finally:
            build_container.remove(force=True)
                                       
    for tool in ["gen", "tester", "vis"]:
        if not (tool_cache_dir / "src" / "bin" / f"{tool}.rs").is_file():
            continue
        tool_path = tool_cache_dir / "target" / "release" / tool
        if not tool_path.is_file():
            msg = f"Failed to build the {tool} tool."
            raise RuntimeError(msg)
        if tool_path.stat().st_size <= 0:
            msg = f"Failed to build the {tool} tool."
            raise RuntimeError(msg)


def start_visualization_server(visualization_server_dir: Path, port_num: int) -> str:
    pass                              

         
                                                                                             
                                                                 

            
                                                    

       
    with docker_client() as client:
        container = client.containers.run(
            image=ale_bench.constants.VIS_SERVER_DOCKER_IMAGE,
            cpu_period=100000,
            cpu_quota=100000,         
            detach=True,
            mem_limit=ale_bench.constants.MAX_MEMORY_LIMIT,
            ports={"80/tcp": port_num},
            volumes={str(visualization_server_dir): {"bind": ale_bench.constants.VIS_SERVER_DIR, "mode": "ro"}},
        )
        container_id: str | None = container.id
    if container_id is None:
        msg = "Failed to start the visualization server container."
        raise RuntimeError(msg)
    return container_id


class RatingCalculator:
    pass                               

                                                 
       

    S: Final[float] = 724.4744301
    R: Final[float] = 0.8271973364
    MIN_RATING_THRESHOLD: Final[float] = 400.0

    def __init__(self) -> None:
        pass                                   
        self.schedule = self.load_contest_schedule()

    def calculate_rating(self, performances: dict[str, int], final_contest: str) -> int:
        pass                                              

             
                                                                                          
                                                             

                
                                       

               
                                                                
                                                                                                 
                                                                          

           
        if len(performances) == 0:
            msg = "The performances dictionary cannot be empty."
            raise ValueError(msg)
        for problem_id in performances:
            if problem_id not in self.schedule:
                msg = f"Problem ID {problem_id} not found in the contest schedule."
                raise ValueError(msg)
        if final_contest not in self.schedule:
            msg = f"Final contest {final_contest} not found in the contest schedule."
            raise ValueError(msg)
        last_contest_end_at = self.schedule[final_contest][1]
        decayed_performances = []
        for problem_id, performance in performances.items():
            _start_at, end_at, weight = self.schedule[problem_id]
            if end_at > last_contest_end_at:
                continue                                                             
            decayed_performance = performance + 150 - 100 * (last_contest_end_at.date() - end_at.date()).days / 365
            for j in range(1, 101):
                augmented_performance = decayed_performance - self.S * math.log(j)
                decayed_performances.append((augmented_performance, weight))
        decayed_performances.sort(key=lambda x: x[0], reverse=True)
        total_weight = 0.0
        rating = 0.0
        for decayed_performance, weight in decayed_performances:
            rating += decayed_performance * (math.pow(self.R, total_weight) - math.pow(self.R, total_weight + weight))
            total_weight += weight
        if rating < self.MIN_RATING_THRESHOLD:
            rating = self.MIN_RATING_THRESHOLD / math.exp(
                (self.MIN_RATING_THRESHOLD - rating) / self.MIN_RATING_THRESHOLD
            )
        return round(rating)

    @staticmethod
    def load_contest_schedule() -> dict[str, tuple[dt.datetime, dt.datetime, float]]:
        pass                                                   

                
                                                              
                                                                                                    

           
        local_data_dir = get_local_data_dir()
        if local_data_dir is None or not (local_data_dir / "schedule.csv").is_file():
                                                                 
            cache_dir = get_cache_dir()
            schedule_file_path = hf_hub_download(
                repo_id=ale_bench.constants.HUGGING_FACE_REPO,
                filename="schedule.csv",
                repo_type="dataset",
                cache_dir=cache_dir,
            )
        else:
            schedule_file_path = str(local_data_dir / "schedule.csv")
        df_schedule = pl.read_csv(schedule_file_path)
        df_schedule = df_schedule.with_columns(
            pl.col("start_at").str.to_datetime(time_zone="Asia/Tokyo"),
            pl.col("end_at").str.to_datetime(time_zone="Asia/Tokyo"),
        )
        return {
            row["problem_id"]: (row["start_at"], row["end_at"], row["weight"])
            for row in df_schedule.iter_rows(named=True)
        }


class RankPercentileMapMethod(str, Enum):
    pass                                           

    ORIGINAL = "original"
    HAZEN = "hazen"
    WEIBULL = "weibull"


class RankingCalculator:
    pass                                   

    MIN_AVG_PERFORMANCE: Final[float] = -1000.0

    def __init__(self, minimum_participation: int = 5) -> None:
        pass                                    
                                                                        
        local_data_dir = get_local_data_dir()
        if local_data_dir is None or not (local_data_dir / "ranking.csv").is_file():
                                                        
            cache_dir = get_cache_dir()
            ranking_file_path = hf_hub_download(
                repo_id=ale_bench.constants.HUGGING_FACE_REPO,
                filename="ranking.csv",
                repo_type="dataset",
                cache_dir=cache_dir,
            )
        else:
            ranking_file_path = str(local_data_dir / "ranking.csv")
        df_ranking = pl.read_csv(ranking_file_path).filter(pl.col("competitions") >= minimum_participation)
                                  
        self.num_active_users = len(df_ranking)
        self.avg_perfs = df_ranking["avg_perf"].sort(descending=True).to_list()
        self.ratings = df_ranking["rating"].sort(descending=True).to_list()
        self.avg_perf_ranks, self.rating_ranks = [], []
        current_avg_perf, current_rating = 10000.0, 10000
        current_avg_perf_rank, current_rating_rank = 0, 0
        for idx, (avg_perf, rating) in enumerate(zip(self.avg_perfs, self.ratings, strict=True), 1):
            if avg_perf != current_avg_perf:
                current_avg_perf_rank = idx
                current_avg_perf = avg_perf
            self.avg_perf_ranks.append(current_avg_perf_rank)
            if rating != current_rating:
                current_rating_rank = idx
                current_rating = rating
            self.rating_ranks.append(current_rating_rank)
                                                                      
        self.avg_perfs.append(-1000.0)
        self.avg_perf_ranks.append(self.num_active_users + 1)
        self.ratings.append(0)
        self.rating_ranks.append(self.num_active_users + 1)

    def calculate_avg_perf_rank(self, avg_perf: float) -> int:
        pass                                      

             
                                                                                

                
                                     

               
                                                         

           
        if avg_perf < self.MIN_AVG_PERFORMANCE:
            msg = "The rating must be greater than or equal to -1000."
            raise ValueError(msg)
        ok, ng = len(self.avg_perfs), -1
        while ok - ng > 1:
            mid = (ok + ng) // 2
            if avg_perf < self.avg_perfs[mid]:
                ng = mid
            elif avg_perf > self.avg_perfs[mid]:
                ok = mid
            else:                   
                return self.avg_perf_ranks[mid]
        if ok == len(self.avg_perfs):
            msg = "Something went wrong: `ok` should be less than `len(self.avg_perfs)`."
            raise RuntimeError(msg)
        return self.avg_perf_ranks[ok]

    def calculate_rating_rank(self, rating: int) -> int:
        pass                                      

             
                                                               

                
                                     

               
                                                     

           
        if rating < 0:
            msg = "The rating must be greater than or equal to 0."
            raise ValueError(msg)
        ok, ng = len(self.ratings), -1
        while ok - ng > 1:
            mid = (ok + ng) // 2
            if rating < self.ratings[mid]:
                ng = mid
            elif rating > self.ratings[mid]:
                ok = mid
            else:                   
                return self.rating_ranks[mid]
        if ok == len(self.ratings):
            msg = "Something went wrong: `ok` should be less than `len(self.ratings)`."
            raise RuntimeError(msg)
        return self.rating_ranks[ok]

    def convert_rank_to_percentile(
        self,
        rank: int,
        method: RankPercentileMapMethod | str = RankPercentileMapMethod.WEIBULL,
    ) -> float:
        pass                              

             
                                            
                                                                                                          
                                                                        
                                                                                   
                                                                             

                
                                            

               
                                                                                                  
                                                 

           
        if rank < 1 or rank > self.num_active_users + 1:
            msg = f"The rank must be between 1 and {self.num_active_users + 1} (the number of users + 1)."
            raise ValueError(msg)
        try:
            method = RankPercentileMapMethod(method)
        except ValueError as e:
            msg = f"Invalid method: {method}. Supported methods are 'original', 'hazen', and 'weibull'."
            raise ValueError(msg) from e
        if method == RankPercentileMapMethod.ORIGINAL:
            if rank == self.num_active_users + 1:
                return 100.0                                                                   
            return 100.0 * rank / self.num_active_users
        if method == RankPercentileMapMethod.HAZEN:
            return 100.0 * (rank - 0.5) / (self.num_active_users + 1)
        if method == RankPercentileMapMethod.WEIBULL:
            return 100.0 * rank / (self.num_active_users + 2)
        msg = "Unreachable code path: invalid rank percentile map method."
        raise RuntimeError(msg)
