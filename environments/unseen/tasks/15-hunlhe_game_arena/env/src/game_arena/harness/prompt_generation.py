                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                     

from typing import Any, Generic, Mapping, Protocol, runtime_checkable
from game_arena.harness import base_game
from game_arena.harness import model_generation
from game_arena.harness import prompt_templates
from game_arena.harness import prompts


@runtime_checkable
class PromptGeneratorSupportsImageText(
    Generic[model_generation.ModelImageTextInputT], Protocol
):
  pass                                                              

  def is_valid_prompt_template(self, prompt_template: str) -> bool:
    ...

                                                                      
                                                                        
  def generate_prompt_with_image_text(
      self,
      prompt_template: str,
      game_adapter: base_game.BaseGameEnvAdapter,
      prompt_configuration: Mapping[str, Any] | None = None,
      **prompt_substitutions,
  ) -> model_generation.ModelImageTextInputT:
    ...


@runtime_checkable
class PromptGeneratorSupportsText(
    Generic[model_generation.ModelTextInputT], Protocol
):
  pass                                            

  def generate_prompt_with_text_only(
      self,
      prompt_template: str,
      game_short_name: str,
      **prompt_substitutions,
  ) -> model_generation.ModelTextInputT:
    ...


class PromptGeneratorText(PromptGeneratorSupportsText):
  pass                                            

  def generate_prompt_with_text_only(
      self,
      prompt_template: str,
      game_short_name: str,
      **prompt_substitutions,
  ) -> model_generation.ModelTextInput:
    prompt_substitutions["game_short_name"] = game_short_name
    return model_generation.ModelTextInput(
        prompt_text=prompt_template.format(**prompt_substitutions)
    )


class PromptGeneratorImageText(PromptGeneratorSupportsImageText):
  pass                                                              

  def is_valid_prompt_template(self, prompt_template: str) -> bool:
    return prompt_template in (
        prompt_templates.WITH_BOARD_IMAGE,
        prompt_templates.WITH_BOARD_IMAGE_RETHINK_APPENDED,
    )

  def generate_prompt_with_image_text(
      self,
      prompt_template: str,
      game_adapter: base_game.BaseGameEnvAdapter,
      prompt_configuration: Mapping[str, Any] | None = None,
      **prompt_substitutions,
  ) -> model_generation.ModelImageTextInput:

    if prompt_template not in prompts.IMAGE_TEXT_PROMPTS:
      raise ValueError(
          "generate_prompt_with_image_text should only be called for multimodal"
          " prompt templates."
      )

    if game_adapter.native_state is None:
      raise ValueError("Environment adapter state is None.")

    prompt_substitutions["game_short_name"] = game_adapter.game_short_name
    prompt_substitutions["readable_state_str"] = (
        game_adapter.get_readable_state()
    )
    prompt_substitutions["additional_state_info_text"] = ""
    if not self.is_valid_prompt_template(prompt_template):
      raise ValueError(f"Unsupported prompt template: {prompt_template}")

    raise NotImplementedError(
        "generate_prompt_with_image_text is not supported for"
        f" {game_adapter.game_short_name}"
    )
