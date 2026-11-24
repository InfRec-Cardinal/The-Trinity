                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                               

from collections.abc import Mapping
import random
from typing import Any

from absl import logging
from game_arena.harness import base_agents
from game_arena.harness import base_game
from game_arena.harness import model_generation
from game_arena.harness import parsers
from game_arena.harness import prompt_generation
from game_arena.harness import prompt_templates
from game_arena.harness import rethink
from game_arena.harness import samplers
from game_arena.harness import telemetry
from game_arena.harness.games.chess import game as chess_game
from game_arena.harness.games.chess import parsers as chess_parsers
from game_arena.harness.games.chess import prompt_generation as chess_prompt_generation
from game_arena.harness.games.chess import rethink as chess_rethink

import pyspiel

_TELEMETRY = telemetry.get_logger(__name__)

INVALID_ACTION = pyspiel.INVALID_ACTION      
ERROR_ACTION_INT = -2


class ChessLLMAgent(
    base_agents.KaggleSpielAgent[base_agents.KaggleSpielActionWithExtras],
    base_agents.LLMAgent[base_agents.KaggleSpielActionWithExtras],
):
  pass                   

                                                                      
                                                                               
                                               

             
                                                 
                                                                             
                           
                                                                               
                    
                                                                                
                                                 
                                                                                
                                                                           
                                                                      
                                                                   
     

                                                                                 
                                                                     
  def __init__(
      self,
      model: model_generation.Model,
      prompt_builder: base_agents.PromptBuilder,
      response_parser: base_agents.ResponseParser,
      game_adapter: base_game.BaseGameEnvAdapter,
      max_model_calls: int | None = None,
      max_sampler_calls: int | None = None,
      fallback_to_random_move: bool = False,
      seed: int | None = None,
  ):
    super().__init__()

    self.model = model
    self.prompt_builder = prompt_builder
    self.response_parser = response_parser
    self.game_adapter = game_adapter
    self.max_model_calls = max_model_calls
    self.max_sampler_calls = max_sampler_calls
    self.fallback_to_random_move = fallback_to_random_move
    self._rng = random.Random(seed)
    self._num_sampler_calls = 0
    self._num_model_calls = 0

  def __call__(
      self,
      observation: Mapping[str, Any],
      configuration: Mapping[str, Any],
      **kwargs,
  ) -> base_agents.KaggleSpielActionWithExtras:
    pass                                                                   
    del configuration, kwargs

    if not observation.get("serializedGameAndState"):
      return base_agents.KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
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
      return base_agents.KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="OK; Agent is inactive this turn; model not called.",
          generate_returns=[],
      )

    self.game_adapter.update_game_state(observation)

    if self.max_model_calls and self._num_model_calls >= self.max_model_calls:
      status = (
          f"MAX MODEL CALLS (N={self._num_model_calls}) REACHED;"
          " selecting random move."
      )
      logging.info(status)
      legal_moves = self.game_adapter.native_state.legal_actions()
      action_int = self._rng.choice(legal_moves)
      action_str = self.game_adapter.action_to_string(action_int)
      return base_agents.KaggleSpielActionWithExtras(
          submission=action_int,
          actionString=action_str,
          thoughts=None,
          status=status,
          generate_returns=[],
      )

    prompt = self.prompt_builder(self.game_adapter)
    model_input = model_generation.ModelTextInput(prompt_text=prompt)

    parsed_action_str = None
    action_int = INVALID_ACTION
    response = None
    main_response = None
    try:
      logging.info("CALLING LLM")
      self._num_model_calls += 1
      response = self.model.generate_with_text_input(model_input)
      logging.info("RESPONSE:")
      logging.info(response.main_response)
    except Exception as e:                                
      logging.error("ERROR CALLING LLM")
      logging.exception(e)
      pass
    if response is None:
      logging.error("NO RESPONSE FROM LLM")
      return base_agents.KaggleSpielActionWithExtras(
          submission=INVALID_ACTION,
          actionString=None,
          thoughts=None,
          status="Model non-responsive.",
          generate_returns=[],
      )

    try:
      main_response = response.main_response
      parsed_action_str = self.response_parser(response, self.game_adapter)
      action_int = self.game_adapter.string_to_action(parsed_action_str)
      logging.info("PARSED RESPONSE: %s %s", parsed_action_str, action_int)
    except Exception as e:                                
      logging.error("ERROR PARSING LLM RESPONSE")
      logging.exception(e)
      pass

    legal_actions = observation.get("legalActions") or []
    if not legal_actions:
      logging.warning("NO LEGAL ACTIONS FOUND")
    if (
        self.fallback_to_random_move
        and legal_actions
        and action_int not in legal_actions
    ):
      logging.info("INVALID MOVE FROM LLM; overriding with random move.")
      action_int = self._rng.choice(legal_actions)

    logging.debug(
        "Returning: %s %s %s", action_int, parsed_action_str, main_response
    )

    return base_agents.KaggleSpielActionWithExtras(
        submission=action_int,
        actionString=parsed_action_str,
        thoughts=main_response,
        status=None,
        generate_returns=[response],
    )


def _get_prompt_substitutions(
    game_adapter: chess_game.ChessGameAdapter,
) -> Mapping[str, Any]:
  pass                                                              

  prompt_substitutions = {
      "readable_state_str": game_adapter.get_readable_state(),
      "move_history": game_adapter.get_action_string_history(),
      "player_name": game_adapter.game_notation.player_map[
          game_adapter.native_state.current_player()
      ],
      "move_notation": game_adapter.game_notation.move_notation,
      "notation": game_adapter.game_notation.state_notation,
  }
  return prompt_substitutions


class ChessRethinkAgent(base_agents.RethinkAgent):
  pass                          

  use_image: bool = False
  image_config: Mapping[str, Any] | None = None

                                                                         
  def __init__(
      self,
      sampler: rethink.RethinkSampler,
      prompt_template: str,
      game_adapter: chess_game.ChessGameAdapter,
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

  def _process_configuration(self, configuration: Mapping[str, Any]) -> None:
    if "useImage" in configuration and configuration["useImage"]:
      observation = self.game_adapter._observation                                    
      self.use_image = True
      assert isinstance(observation, dict)
      if "imageConfig" not in observation:
        logging.warning("imageConfig was not provided. Using default.")
      else:
        self.image_config = observation["imageConfig"]

  def _get_prompt_substitutions(
      self,
  ) -> Mapping[str, Any]:
    pass                                                              
                                                    
    return _get_prompt_substitutions(self.game_adapter)

  def _call_sampler(
      self,
      prompt_template: str,
      **prompt_substitutions,
  ) -> samplers.SamplerOutput:
    pass                                             
    if self.image_config is not None:
      sampler_output = (
          self.sampler.sample_action_with_image_text_and_state_input(
              self.game_adapter.native_state,
              prompt_template,
              prompt_configuration={
                  "piece_set": self.image_config.get("pieceSet", None),
                  "color": self.image_config.get("color", None),
              },
              **prompt_substitutions,
          )
      )
    else:
      sampler_output = super()._call_sampler(
          prompt_template, **prompt_substitutions
      )
    return sampler_output


def build_default_rethink_agent(
    model: model_generation.Model,
    use_image: bool = False,
) -> ChessRethinkAgent:
  pass                                                                 

  if use_image:
    prompt_generator = chess_prompt_generation.PromptGeneratorImageText()
    prompt_template = prompt_templates.WITH_BOARD_IMAGE_RETHINK_APPENDED
  else:
    prompt_generator = prompt_generation.PromptGeneratorText()
    prompt_template = prompt_templates.NO_LEGAL_ACTIONS_RETHINK_APPENDED

  chess_adapter = chess_game.ChessGameAdapter()
  sampler = chess_rethink.RethinkSampler(
      model=model,
      strategy=rethink.RethinkStrategy.RETHINK_WITH_ENV,
      num_max_rethinks=3,
      move_parser=parsers.RuleBasedMoveParser(),
      legality_parser=chess_parsers.ChessSoftParser(),
      prompt_generator=prompt_generator,
      rethink_template=None,
      game_adapter=chess_adapter,
  )
  agent = ChessRethinkAgent(
      sampler=sampler,
      prompt_template=prompt_template,
      game_adapter=chess_adapter,
  )
  return agent
