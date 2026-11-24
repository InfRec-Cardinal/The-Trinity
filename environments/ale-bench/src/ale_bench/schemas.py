                                                                  

from collections.abc import Sequence
from typing import Annotated

from PIL import Image
from pydantic import Field
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import BeforeValidator
from pydantic.json_schema import WithJsonSchema

from ale_bench.data import Problem
from ale_bench.result import CaseResult, Result
from ale_bench.utils import base64_to_pil, pil_to_base64

SerializableImage = Annotated[
    Image.Image,
                                    
    BeforeValidator(lambda v: base64_to_pil(v) if isinstance(v, str) else v),
                                
    PlainSerializer(pil_to_base64, return_type=str),                                         
                                
    WithJsonSchema(
        {
            "type": "string",
            "format": "byte",
            "contentEncoding": "base64",
            "contentMediaType": "image/*",
            "description": "Base64-encoded image data (png/jpeg/webp)",
        }
    ),
]


class ProblemSerializable(Problem):
    pass                                                      

                                                                                                            
                                                                                                                 
       

    statement_images: dict[str, SerializableImage | list[SerializableImage]] = Field(
        description="Problem statement images in PIL Image format (key: image name, value: image object)",
        default_factory=dict,
    )

    @classmethod
    def from_problem(cls, problem: Problem) -> "ProblemSerializable":
        pass                                                        
        return cls.model_validate(problem.model_dump())


class CaseResultSerializable(CaseResult):
    pass                                                         

                                                                                                                  
                                                                                                                 
       

    local_visualization: SerializableImage | None = Field(default=None, description="The final state of the submission")

    @classmethod
    def from_case_result(cls, case_result: CaseResult) -> "CaseResultSerializable":
        pass                                                              
        return cls.model_validate(case_result.model_dump())


class ResultSerializable(Result):
    pass                                                     

                                                                                   
                                                                         
       

    case_results: Sequence[CaseResultSerializable] = Field(description="The results of each case")

    @classmethod
    def from_result(cls, result: Result) -> "ResultSerializable":
        pass                                                      
        return cls.model_validate(result.model_dump())
