                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

from typing import Tuple

from phyre import action_mappers as _action_mappers
from phyre.creator.constants import NUM_COLORS, SCENE_HEIGHT, SCENE_WIDTH
from phyre.metrics import get_fold, list_eval_setups, eval_setup_to_action_tier, Evaluator, MAIN_EVAL_SETUPS, MAX_TEST_ATTEMPTS
from phyre.action_simulator import initialize_simulator, ActionSimulator, SimulationStatus
from phyre.objects_util import featurized_objects_vector_to_raster
from phyre.simulation import FeaturizedObjects, Simulation
from phyre.simulation_cache import SimulationCache, get_default_100k_cache
from phyre.vis import observations_to_float_rgb, observations_to_uint8_rgb

ACTION_TIERS: Tuple[str] = tuple(sorted(_action_mappers.MAIN_ACITON_MAPPERS))
"""List of action tiers in phyre.
"""
