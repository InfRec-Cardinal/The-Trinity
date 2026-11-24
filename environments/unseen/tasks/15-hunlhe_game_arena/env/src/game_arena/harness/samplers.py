                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                     

import collections
import concurrent
import dataclasses
import enum
import random
from typing import Any, Callable, Protocol, Sequence

from game_arena.harness import model_generation
from game_arena.harness import parsers


class MoveType(enum.Enum):
  LEGAL = "legal"
  ILLEGAL = "illegal"
  NO_ACTION_TAG = "no_action_tag"
                                                     


@dataclasses.dataclass(frozen=True, kw_only=True)
class SamplerOutput:
  action: str | None
  extracted_action: str | None
  matched_action: str | None
  generate_returns: Sequence[model_generation.GenerateReturn]
                                                                           
  auxiliary_outputs: dict[str, Any]
                                        
  move_type: MoveType | None = None


class Sampler(Protocol):
  pass                  

  def __init__(self, model: model_generation.Model):
    self._model = model

  def sample_action_with_text_input(
      self, model_input: model_generation.ModelTextInput
  ) -> SamplerOutput:
    ...


class MultimodalSampler(Sampler, Protocol):
  pass                             

  def sample_action_with_image_text_input(
      self, model_input: model_generation.ModelImageTextInput
  ) -> SamplerOutput:
    ...


class MajorityVoteSampler(Sampler):
  pass                                                                       

                                                                              
                                                                           
                                                                            
                                                                              
                  
     

  def __init__(
      self,
      model: model_generation.Model,
      num_samples: int,
      parser: parsers.TextParser,
      max_workers: int = 10,
  ):
    super().__init__(model)
    self._num_samples = num_samples
    self._parser = parser
    self._max_workers = max_workers

                                                                               
                      
  def _sample_action(
      self,
      generate_fn: Callable[[Any], model_generation.GenerateReturn],
      model_input: Any,
  ) -> SamplerOutput:
    pass                                                             

    def _generate_then_parse(
        model_input: Any,
    ) -> tuple[str | None, model_generation.GenerateReturn]:
      response = generate_fn(model_input)
      return (
          self._parser.parse(
              parsers.TextParserInput(text=response.main_response)
          ),
          response,
      )

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=self._max_workers
    ) as executor:
      futures = [
          executor.submit(_generate_then_parse, model_input)
          for _ in range(self._num_samples)
      ]

    parsed_actions, responses = tuple(
        zip(*[future.result() for future in futures])
    )
    responses = list(responses)

    frequency_from_parsed_action: collections.Counter[str | None] = (
        collections.Counter(parsed_actions)
    )

    most_common_actions = frequency_from_parsed_action.most_common(1)

    if len(most_common_actions) == 1:
      return SamplerOutput(
          action=most_common_actions[0][0],
          extracted_action=most_common_actions[0][0],
          matched_action=None,
          generate_returns=responses,
          auxiliary_outputs={"frequencies": dict(frequency_from_parsed_action)},
      )
    elif len(most_common_actions) > 1:
      rng = random.Random()
      return SamplerOutput(
          action=rng.choice(most_common_actions)[0],
          extracted_action=rng.choice(most_common_actions)[0],
          matched_action=None,
          generate_returns=responses,
          auxiliary_outputs={"frequencies": dict(frequency_from_parsed_action)},
      )
    else:
      return SamplerOutput(
          action=None,
          extracted_action=None,
          matched_action=None,
          generate_returns=[],
          auxiliary_outputs={},
      )

  def sample_action_with_text_input(
      self, model_input: model_generation.ModelTextInput
  ) -> SamplerOutput:
    return self._sample_action(
        self._model.generate_with_text_input, model_input
    )


class MajorityVoteMultimodalSampler(MajorityVoteSampler, MultimodalSampler):
  pass                                            

  def __init__(
      self,
      model: model_generation.MultimodalModel,
      num_samples: int,
      parser: parsers.TextParser,
      max_workers: int = 10,
  ):
    super().__init__(model, num_samples, parser, max_workers)

  def sample_action_with_image_text_input(
      self, model_input: model_generation.ModelImageTextInput
  ) -> SamplerOutput:
    assert isinstance(self._model, model_generation.MultimodalModel)
    return self._sample_action(
        self._model.generate_with_image_text_input, model_input
    )
