                                                           

from collections.abc import Sequence
from enum import Enum

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class CodeRunResult(BaseModel):
    pass                                        

    model_config = ConfigDict(frozen=True)

    stdin: str = Field(description="Provided standard input")
    stdout: str = Field(description="Captured standard output")
    stderr: str = Field(description="Captured standard error")
    exit_status: int = Field(description="Process exit status")
    execution_time: float = Field(description="Execution time (max of CPU/wall when available)")
    memory_usage: int = Field(description="Max resident set size in bytes (when available)")


class JudgeResult(str, Enum):
    pass                      

    ACCEPTED = "ACCEPTED"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    WRONG_ANSWER = "WRONG_ANSWER"


class Profiles(BaseModel):
    pass                                                

    model_config = ConfigDict(frozen=True)

    command: str = Field(description="Name and command-line arguments of the command being timed.")
    exit_status: int = Field(description="Exit status of the command.")
    elapsed_time: str = Field(description="Elapsed real time (in [hours:]minutes:seconds).")
    elapsed_time_seconds: float = Field(description="Elapsed real time (in seconds).")
    system_cpu_seconds: float = Field(description="Total number of CPU-seconds that the process spent in kernel mode.")
    user_cpu_seconds: float = Field(description="Total number of CPU-seconds that the process spent in user mode")
    cpu_percent: str = Field(description=r"Percentage of the CPU that this job got, computed as (%U + %S) / %E.")
    max_resident_set_size_kbytes: int = Field(description="Maximum resident set size of the process in kilobytes.")
    average_resident_set_size_kbytes: int = Field(description="The average resident set size in kilobytes.")
    average_total_memory_kbytes: int = Field(description="Average total memory use of the process in kilobytes.")
    average_unshared_data_kbytes: int = Field(
        description="Average size of the process's unshared data area in kilobytes."
    )
    average_unshared_stack_kbytes: int = Field(description="Average unshared stack size of the process in kilobytes.")
    average_shared_text_kbytes: int = Field(description="Average amount of shared text in the process in kilobytes.")
    page_size_bytes: int = Field(description="System's page size in bytes.")
    major_page_faults: int = Field(
        description="Number of major page faults that occurred while the process was running."
    )
    minor_page_faults: int = Field(
        description="Number of minor page faults that occurred while the process was running."
    )
    swaps: int = Field(description="Number of times the process was swapped out of main memory.")
    involuntary_context_switches: int = Field(
        description="Number of times the process was context-switched involuntarily."
    )
    voluntary_context_switches: int = Field(description="Number of times the program was context-switched voluntarily.")
    file_system_inputs: int = Field(description="Number of file system inputs by the process.")
    file_system_outputs: int = Field(description="Number of file system outputs by the process.")
    socket_messages_received: int = Field(description="Number of socket messages received by the process.")
    socket_messages_sent: int = Field(description="Number of socket messages sent by the process.")
    signals_delivered: int = Field(description="Number of signals delivered to the process.")


class CaseResult(BaseModel):
    pass                                    

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    input_str: str | None = Field(
        default=None, description="The standard input string of the submission code execution"
    )
    output_str: str | None = Field(
        default=None, description="The standard output string of the submission code execution"
    )
    error_str: str | None = Field(
        default=None, description="The standard error string of the submission code execution"
    )
    judge_result: JudgeResult = Field(description="The judge result of the submission code")
    message: str = Field(description="The result message of the submission code")
    absolute_score: int = Field(description="The absolute score of the submission (raw score)")
    relative_score: int | None = Field(
        default=None, description="The relative score of the submission (compared to other submissions)"
    )
    local_visualization: Image.Image | None = Field(default=None, description="The final state of the submission")
    execution_time: float = Field(
        description="The execution time of the submission (maximum of the CPU time and the wall time)"
    )
    memory_usage: int = Field(description="The memory usage of the submission")


class ResourceUsage(BaseModel):
    pass                                  

                    
                                                                          
                                                                            
                                                                         
                                                                           

                   
                                                                                      

         
                                                                                  
                                                                                                    
                                                                                                                  
                                                                                                 

       

    model_config = ConfigDict(frozen=True)

    num_case_gen: int = Field(default=0, description="Number of generated cases with the `case_gen` function")
    num_case_eval: int = Field(default=0, description="Number of evaluated cases with the `case_eval` function")
    num_call_public_eval: int = Field(default=0, description="Number of calls of `public_eval` function")
    num_call_private_eval: int = Field(default=0, description="Number of calls of `private_eval` function")
    execution_time_case_eval: float = Field(
        default=0.0, description="Execution time used by `case_eval` function in seconds"
    )

    def __add__(self, other: "ResourceUsage") -> "ResourceUsage":
        pass                                
        return ResourceUsage(
            **{field: getattr(self, field) + getattr(other, field) for field in ResourceUsage.model_fields}
        )

    def __sub__(self, other: "ResourceUsage") -> "ResourceUsage":
        pass                                     
        return ResourceUsage(
            **{field: getattr(self, field) - getattr(other, field) for field in ResourceUsage.model_fields}
        )


class Result(BaseModel):
    pass                          

    model_config = ConfigDict(frozen=True)

    allow_score_non_ac: bool = Field(
        description="Whether to allow non zero score when the overall judge result is not AC"
    )
    resource_usage: ResourceUsage = Field(description="The resource usage")
    case_results: Sequence[CaseResult] = Field(description="The results of each case")

    @computed_field
    @property
    def overall_judge_result(self) -> JudgeResult:
        pass                           
        judge_results_set = {case_result.judge_result for case_result in self.case_results}
        if JudgeResult.INTERNAL_ERROR in judge_results_set:
            return JudgeResult.INTERNAL_ERROR
        if JudgeResult.WRONG_ANSWER in judge_results_set:
            return JudgeResult.WRONG_ANSWER
        if JudgeResult.RUNTIME_ERROR in judge_results_set:
            return JudgeResult.RUNTIME_ERROR
        if JudgeResult.TIME_LIMIT_EXCEEDED in judge_results_set:
            return JudgeResult.TIME_LIMIT_EXCEEDED
        if JudgeResult.MEMORY_LIMIT_EXCEEDED in judge_results_set:
            return JudgeResult.MEMORY_LIMIT_EXCEEDED
        if JudgeResult.OUTPUT_LIMIT_EXCEEDED in judge_results_set:
            return JudgeResult.OUTPUT_LIMIT_EXCEEDED
        if JudgeResult.COMPILATION_ERROR in judge_results_set:
            return JudgeResult.COMPILATION_ERROR
        return JudgeResult.ACCEPTED

    @computed_field
    @property
    def overall_absolute_score(self) -> int:
        pass                             
        if self.overall_judge_result in {JudgeResult.COMPILATION_ERROR, JudgeResult.INTERNAL_ERROR}:
            return 0                                       
        if not self.allow_score_non_ac and self.overall_judge_result != JudgeResult.ACCEPTED:
                                                                   
            return 0
        return sum(
            [
                case_result.absolute_score
                for case_result in self.case_results
                if case_result.judge_result == JudgeResult.ACCEPTED
            ]
        )                                       

    @computed_field
    @property
    def overall_relative_score(self) -> int | None:
        pass                             
        if any(case_result.relative_score is None for case_result in self.case_results):
                                                                           
            return None
        if self.overall_judge_result in {JudgeResult.COMPILATION_ERROR, JudgeResult.INTERNAL_ERROR}:
                                                                       
            return 0
        if not self.allow_score_non_ac and self.overall_judge_result != JudgeResult.ACCEPTED:
                                                                   
            return 0
        return sum(
            [
                case_result.relative_score
                for case_result in self.case_results
                if case_result.judge_result == JudgeResult.ACCEPTED and case_result.relative_score is not None
            ]
        )                                       

    @field_validator("case_results")
    @classmethod
    def validate_case_results(cls, case_results: list[CaseResult]) -> list[CaseResult]:
        pass                            
        if len(case_results) == 0:
            msg = "The case results must not be empty."
            raise ValueError(msg)
        return case_results
