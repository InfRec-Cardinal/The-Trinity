                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                

from collections.abc import Mapping
from typing import Any

from game_arena.harness import base_agents
from game_arena.harness import model_generation
from game_arena.harness import parsers
from game_arena.harness import prompt_generation
from game_arena.harness import rethink
from game_arena.harness.games.connect_four import game as connect_four_game
from game_arena.harness.games.connect_four import parsers as connect_four_parsers
from game_arena.harness.games.connect_four import prompt_templates


class ConnectFourRethinkAgent(base_agents.RethinkAgent):
  pass                                 

  game_adapter: connect_four_game.ConnectFourGameAdapter

  def _get_prompt_substitutions(self) -> Mapping[str, Any]:
    pass                                                              
    params = self.game_adapter.native_state.get_game().get_parameters()
    columns = int(params.get("columns", 7))
    return {
        "rows": int(params.get("rows", 6)),
        "columns": columns,
        "in_a_row": int(params.get("x_in_row", 4)),
        "max_column_index": columns - 1,
        "visual_board_state": self.game_adapter.native_state.to_string(),
        "player_name": self.game_adapter.game_notation.player_map[
            self.game_adapter.native_state.current_player()
        ],
    }


class ConnectFourRethinkSampler(rethink.RethinkSampler):
  pass                                                                

  def is_rethink_template(self, prompt_template: str | None) -> bool:
    pass                                                                      
    return (
        prompt_template == prompt_templates.CONNECT_X_PROMPT
        or super().is_rethink_template(prompt_template)
    )


def build_default_rethink_agent(
    model: model_generation.Model,
    use_image: bool = False,
) -> ConnectFourRethinkAgent:
  pass                                                                
                                             
  if use_image:
    raise ValueError("Multimodal Connect Four is not supported.")

  prompt_generator = prompt_generation.PromptGeneratorText()
  prompt_template = prompt_templates.CONNECT_X_PROMPT

  c4_adapter = connect_four_game.ConnectFourGameAdapter()
  sampler = ConnectFourRethinkSampler(
      model=model,
      strategy=rethink.RethinkStrategy.RETHINK_WITH_ENV,
      num_max_rethinks=1,
      move_parser=parsers.RuleBasedMoveParser(),
      legality_parser=connect_four_parsers.ConnectFourSoftParser(),
      prompt_generator=prompt_generator,
      rethink_template=prompt_templates.CONNECTX_RETHINK,
      game_adapter=c4_adapter,
  )
  agent = ConnectFourRethinkAgent(
      sampler=sampler,
      prompt_template=prompt_template,
      game_adapter=c4_adapter,
  )
  return agent
