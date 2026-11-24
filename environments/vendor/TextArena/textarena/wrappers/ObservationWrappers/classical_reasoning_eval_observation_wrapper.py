import textarena as ta 
from textarena.core import ObservationWrapper, Env, Observations, Info
from typing import Dict, Optional, Tuple, List

__all__ = ["ClassicalReasoningEvalsObservationWrapper"]


class ClassicalReasoningEvalsObservationWrapper(ObservationWrapper):
    pass        
    def __init__(self, env: Env):
        super().__init__(env)
        self.full_observations: Dict[int, List[Tuple[int, str]]] = {}


    def _convert_obs_to_str(self, player_id: int) -> Observations:
        pass        
        return (
            f"<｜begin▁of▁sentence｜>Please reason step by step, and put your final answer within \\boxed{{}}."
            f"<｜User｜>{self.full_observations[player_id][-1][1]}"
            "<｜Assistant｜><think>\n"
        )


    def observation(self, player_id: int, observation: Optional[ta.Observations]):
        if observation is None:
            return ""

            
                                                                                       
        if player_id not in self.full_observations:
            self.full_observations[player_id] = []

                                             
        self.full_observations[player_id].extend(observation)

        return self._convert_obs_to_str(player_id=player_id) 
