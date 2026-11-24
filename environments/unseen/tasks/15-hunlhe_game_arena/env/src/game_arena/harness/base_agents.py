                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                                        

import abc
from collections.abc import Callable, Mapping, Sequence
import dataclasses
import json
import random
import traceback
from typing import Any, Generic, Protocol, TypeAlias, TypeVar, TypedDict

from absl import logging
from game_arena.harness import base_game
from game_arena.harness import model_generation
from game_arena.harness import rethink
from game_arena.harness import samplers
from game_arena.harness import telemetry

import pyspiel


_TELEMETRY = telemetry.get_logger(__name__)

INVALID_ACTION = pyspiel.INVALID_ACTION      
ERROR_ACTION_INT = -2


class CustomJSONEncoder(json.JSONEncoder):
  pass                                                                                       

  def default(self, o):
    if dataclasses.is_dataclass(o):
      return dataclasses.asdict(o)
    if hasattr(o, "to_dict") and callable(o.to_dict):
      return o.to_dict()
    try:
      return super().default(o)
    except TypeError:
      return str(o)


KaggleActionT = TypeVar("KaggleActionT")
KaggleSpielActionT = TypeVar(
    "KaggleSpielActionT", "KaggleSpielAction", "KaggleSpielActionWithExtras"
)


PromptBuilder: TypeAlias = Callable[[pyspiel.State], str]
ResponseParser: TypeAlias = Callable[
    [model_generation.GenerateReturn, pyspiel.State], str
]


class KaggleAgent(Protocol, Generic[KaggleActionT]):
  pass                         

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleActionT:
    ...


class KaggleSpielAction(TypedDict):
  pass                                                                          

  submission: int


class KaggleSpielActionWithExtras(KaggleSpielAction):
  pass                                     

  actionString: str | None                                
  thoughts: str | None                                                          
  status: str | None                                
  generate_returns: Sequence[str] = dataclasses.field(default_factory=list)


class KaggleSpielAgent(
    KaggleAgent[KaggleSpielActionT], abc.ABC, Generic[KaggleSpielActionT]
):
  pass                          

  @abc.abstractmethod
  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionT:
    ...


class LLMAgent(KaggleAgent[KaggleActionT], Generic[KaggleActionT]):
  pass                                                          

  model: model_generation.Model
                                                                                
         
                                                                               
                                                                          
                                      
                      
                                                            
                                                                               
                                                                             
                                                                                  
                                                                     
                                                                              
                                                                             
                                                                              
                                                                              
                                                
  prompt_builder: PromptBuilder
  response_parser: ResponseParser


class RethinkAgent(KaggleAgent, abc.ABC):
  pass                                                        

                                                                                
                                                                         
                                                                  
     

  def __init__(
      self,
      sampler: rethink.RethinkSampler,
      prompt_template: str,
      game_adapter: base_game.BaseGameEnvAdapter,
      sampler_config: Mapping[str, Any] | None = None,
      max_model_calls: int | None = None,
      max_sampler_calls: int | None = None,
      fallback_to_random_move: bool = False,
      seed: int | None = None,
  ):
    self.sampler = sampler
    self.prompt_template = prompt_template
    self.game_adapter = game_adapter
    self.sampler_config = sampler_config
    self.max_model_calls = max_model_calls
    self.max_sampler_calls = max_sampler_calls
    self.fallback_to_random_move = fallback_to_random_move
    self.seed = seed
    self._rng = random.Random(seed)
    self._num_sampler_calls = 0
    self._num_model_calls = 0

  @property
  def invalid_action(self) -> int:
    pass                                  
    return INVALID_ACTION

  @property
  def error_action(self) -> int:
    pass                                
    return ERROR_ACTION_INT

  @property
  def num_model_calls(self) -> int:
    pass                                                                
    return self._num_model_calls

  @property
  def num_sampler_calls(self) -> int:
    pass                                                                           
    return self._num_sampler_calls

  @abc.abstractmethod
  def _get_prompt_substitutions(self) -> Mapping[str, Any]:
    pass                                                              
    raise NotImplementedError()

  def _call_sampler(
      self,
      prompt_template: str,
      **prompt_substitutions,
  ) -> samplers.SamplerOutput:
    pass                                             
    sampler_output = self.sampler.sample_action_with_text_and_state_input(
        game_adapter=self.game_adapter,
        prompt_template=prompt_template,
        **prompt_substitutions,
    )
    return sampler_output

  def _process_configuration(self, configuration: Mapping[str, Any]) -> None:
    pass                                         

                                                      
                                                                             
                        
         
                                                           

            
           
           
                                                                
       
    if "useImage" in configuration and configuration["useImage"]:
      class_name = self.__class__.__name__
      game_short_name = self.game_adapter.game_short_name
      raise ValueError(
          f"Image input not supported for {class_name} and {game_short_name}"
      )

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> KaggleSpielActionT:
    pass                                                                   
    del kwargs
    if not observation.get("serializedGameAndState"):
                                                                  
      return KaggleSpielActionWithExtras(
          submission=self.invalid_action,
          actionString=None,
          thoughts=None,
          status="OK; Setup step; model not called.",
          generate_returns=[],
      )
                                                                
    current_player = observation.get("currentPlayer")
    player_id = observation.get("playerId")
    if current_player is None or player_id is None:
      raise ValueError(
          f"Missing player information:{current_player=} {player_id=}"
      )
    if current_player != player_id:
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="OK; Agent is inactive this turn; model not called.",
          generate_returns=[],
      )

    self.game_adapter.update_game_state(observation)
    self._process_configuration(configuration)

    if (
        self.max_sampler_calls
        and self.num_sampler_calls >= self.max_sampler_calls
    ):
      status = (
          f"OK; MAX SAMPLER CALLS (N={self.num_sampler_calls}) REACHED;"
          " selecting random move"
      )
      logging.info(status)
      legal_moves = self.game_adapter.legal_actions or []
      action_str = self._rng.choice(legal_moves)
      action_int = self.game_adapter.string_to_action(action_str)
      return KaggleSpielActionWithExtras(
          submission=action_int,
          actionString=action_str,
          thoughts=None,
          status=status,
          generate_returns=[],
      )

    try:
      logging.info("CALLING SAMPLER")
      _TELEMETRY(calling_sampler=True)
      self._num_sampler_calls += 1
      prompt_substitutions = self._get_prompt_substitutions()
      _TELEMETRY(prompt_substitutions=prompt_substitutions)
      sampler_output = self._call_sampler(
          prompt_template=self.prompt_template,
          **prompt_substitutions,
      )
      self._num_model_calls += len(sampler_output.generate_returns)
      logging.info("FIRST RESPONSE:")
      logging.info(sampler_output.generate_returns[0].main_response)
      logging.info("SAMPLED ACTION:")
      logging.info(sampler_output.action)
    except Exception as e:                                
      logging.error("ERROR CALLING SAMPLER")
      logging.exception(e)
      return KaggleSpielActionWithExtras(
          submission=self.error_action,
          actionString=None,
          thoughts=None,
          status=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
          generate_returns=[],
      )

    full_response = ""
    for i, generate_return in enumerate(sampler_output.generate_returns):
      response = (
          generate_return.main_response_and_thoughts
          if generate_return.main_response_and_thoughts
          else generate_return.main_response
      )
      if i == 0:
        full_response = response
      else:
        full_response += (
            "\n\n" + "=" * 10 + f" Rethink Attempt #{i} " + "=" * 10
        )
        full_response += f"\n\n{response}"
    logging.info("--ALL RESPONSES--")
    logging.info(full_response)

    generate_returns_jsons = []
    try:
      generate_returns_jsons = [
          json.dumps(
              generate_return.to_dict(),
              indent=2,
              cls=CustomJSONEncoder,
          )
          for generate_return in sampler_output.generate_returns
      ]
    except Exception as e:                                
      logging.error("ERROR DUMPING GENERATE RETURNS")
      logging.exception(e)

    parsed_action_str = sampler_output.action
    if sampler_output.move_type == samplers.MoveType.LEGAL:
      try:
        action_int = self.game_adapter.string_to_action(parsed_action_str)
        logging.info("PARSED RESPONSE: %s %s", parsed_action_str, action_int)
        _TELEMETRY(action_is_legal=True)
        _TELEMETRY(
            legal_action={
                "extracted_action": sampler_output.extracted_action,
                "parsed_action_str": parsed_action_str,
            }
        )
        status = "OK"
        if "illegal_action_remapped" in sampler_output.auxiliary_outputs:
          illegal_action_remapped = str(sampler_output.auxiliary_outputs[
              "illegal_action_remapped"])
          status += (
              "; Illegal action remapped to default action:"
              f" {illegal_action_remapped}"
          )
        return KaggleSpielActionWithExtras(
            submission=action_int,
            actionString=parsed_action_str,
            thoughts=full_response,
            status=status,
            generate_returns=generate_returns_jsons,
        )
      except Exception as e:                                
        logging.error("ERROR SHOULD BE LEGAL BUT CONVERSION FAILED")
        logging.exception(e)
        return KaggleSpielActionWithExtras(
            submission=INVALID_ACTION,
            actionString=parsed_action_str,
            thoughts=full_response,
            status=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            generate_returns=generate_returns_jsons,
        )
    else:
      _TELEMETRY(action_is_legal=False)
      return KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=parsed_action_str,
          thoughts=full_response,
          status="OK; Submitting invalid action.",
          generate_returns=generate_returns_jsons,
      )
