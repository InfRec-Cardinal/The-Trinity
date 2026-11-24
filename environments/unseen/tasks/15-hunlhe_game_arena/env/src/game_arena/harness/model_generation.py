                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                             

import dataclasses
import datetime
import functools
import time
import traceback
from typing import Any, Callable, Generic, Mapping, Protocol, TypeVar, runtime_checkable

from absl import logging
import dataclasses_json
import tenacity


_THOUGHT_TAG_START = '<think>'
_THOUGHT_TAG_END = '</think>'


ModelTextInputT = TypeVar('ModelTextInputT')
ModelImageTextInputT = TypeVar('ModelImageTextInputT')


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModelTextInput:
  prompt_text: str
  system_instruction: str | None = None


@dataclasses.dataclass(frozen=True, kw_only=True)
class ModelImageTextInput(ModelTextInput):
  prompt_image_bytes: bytes
  prompt_image_mime_type: str
  prompt_text_preceding_image: str | None = None
  prompt_text_following_image: str | None = None


@dataclasses_json.dataclass_json
@dataclasses.dataclass(frozen=True, kw_only=True)
class GenerateReturn:
                                                                               
  main_response: str
  main_response_and_thoughts: str
  request_for_logging: dict[str, Any] | None = None
  response_for_logging: dict[str, Any] | None = None
  generation_tokens: int | None = None
  prompt_tokens: int | None = None
  reasoning_tokens: int | None = None
  total_tokens: int | None = None
  duration_success_only_secs: int | None = None


def _log_retry_warning(retry_state: tenacity.RetryCallState):
  assert retry_state.outcome is not None
  exception = retry_state.outcome.exception()
  traceback_str = ''.join(traceback.format_exception(exception))
  logging.warning(
      'Attempting retry # %d. Traceback: %s. Retry state: %s',
      retry_state.attempt_number,
      traceback_str,
      retry_state,
  )


_GenerateFunc = Callable[..., GenerateReturn]


def _timing_decorator(generate_func: _GenerateFunc) -> _GenerateFunc:
  pass                                                             

  @functools.wraps(generate_func)
  def wrapper(*args, **kwargs) -> GenerateReturn:
    start_time = time.perf_counter()
    generate_return = generate_func(*args, **kwargs)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    generate_return = dataclasses.replace(
        generate_return,
        duration_success_only_secs=elapsed_time,
    )
    return generate_return

  return wrapper


class DoNotRetryError(Exception):
  pass                                          

  def __init__(self, *args, info: Any = None, **kwargs):
    super().__init__(*args, **kwargs)
    self.info = info

  def __str__(self):
    base_str = super().__str__()
    if self.info:
      return f'{base_str}\nInfo: {self.info}'
    return base_str


class UnsupportedCapabilityError(DoNotRetryError):
  pass                                                              


                                                                                   
                                                                             
                                                                   
                                                                             
                                        
                                                                          
             
def _custom_retry_condition(retry_state: tenacity.RetryCallState) -> bool:
  pass                                 
  if retry_state.outcome is None:
    return False                                      
  if not retry_state.outcome.failed:
    return False                            
  exception = retry_state.outcome.exception()
  return not isinstance(exception, DoNotRetryError)


_retry_decorator = tenacity.retry(
    retry=_custom_retry_condition,
    wait=tenacity.wait_random_exponential(min=1, max=60),
    stop=tenacity.stop_after_delay(datetime.timedelta(minutes=60)),
    before_sleep=_log_retry_warning,
    reraise=True,
)


@runtime_checkable
class Model(Generic[ModelTextInputT], Protocol):
  pass                                               

  def __init__(
      self,
      model_name: str,
      *,
      model_options: Mapping[str, Any] | None = None,
      api_options: Mapping[str, Any] | None = None,
  ):
    pass                     

         
                                    
                                                                          
                                        
                                                                          
                 
       
    self._model_name = model_name
    self._model_options = model_options
    self._api_options = api_options

  @property
  def model_name(self) -> str:
    return self._model_name

  def generate_with_text_input(
      self,
      model_input: ModelTextInputT,
  ) -> GenerateReturn:
    ...

  def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    if hasattr(cls, 'generate_with_text_input'):
      setattr(
          cls,
          'generate_with_text_input',
          _retry_decorator(_timing_decorator(cls.generate_with_text_input)),
      )


@runtime_checkable
class MultimodalModel(Model, Generic[ModelImageTextInputT], Protocol):
  pass                                                         

  def generate_with_image_text_input(
      self,
      model_input: ModelImageTextInputT,
  ) -> GenerateReturn:
    ...

  def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    if hasattr(cls, 'generate_with_image_text_input'):
      setattr(
          cls,
          'generate_with_image_text_input',
          _retry_decorator(
              _timing_decorator(cls.generate_with_image_text_input)
          ),
      )


def separate_main_response_and_thoughts(
    response: str,
    thought_tag_start: str = _THOUGHT_TAG_START,
    thought_tag_end: str = _THOUGHT_TAG_END,
) -> tuple[str, str] | None:
  pass                                                        

       
                                          
                                                  
                                              

          
                                                                          
            
     
  if thought_tag_start not in response:
    return None
  else:
    thoughts_and_response = response.split(thought_tag_start)[1]
    if thought_tag_end in thoughts_and_response:
      thoughts = thoughts_and_response.split(thought_tag_end)[0]
      main_response = thoughts_and_response.split(thought_tag_end)[1]
      return main_response, thoughts
