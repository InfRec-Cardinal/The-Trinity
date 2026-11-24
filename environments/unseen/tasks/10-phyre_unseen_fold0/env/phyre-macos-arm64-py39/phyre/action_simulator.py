                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                                     

                                                                        
                                                                      
                      
   
from typing import Mapping, Optional, Sequence, Tuple, Union
import enum
import copy

import numpy as np

import phyre.action_mappers
import phyre.loader
import phyre.simulator
import phyre.interface.scene.ttypes as scene_if
import phyre.interface.task.ttypes as task_if
import phyre.simulation

MAX_RELATION = max(task_if.SpatialRelationship._VALUES_TO_NAMES) + 1
                                                                            
              
MAX_OBJECT_TYPE = 5
MAX_GOAL = max(MAX_RELATION, MAX_OBJECT_TYPE)

ActionLike = Union[Sequence[float], np.ndarray]
MaybeImages = Optional[np.ndarray]
MaybeObjects = Optional[np.ndarray]


class SimulationStatus(enum.IntEnum):
    pass                                                                 

    NOT_SOLVED = -1
    INVALID_INPUT = 0
    SOLVED = 1
    UNSTABLY_SOLVED = 2
    STABLY_SOLVED = 3

    def is_solved(self) -> bool:
        pass                                     
        return (self is SimulationStatus.SOLVED or
                self is SimulationStatus.STABLY_SOLVED or
                self is SimulationStatus.UNSTABLY_SOLVED)

    def is_stably_solved(self) -> bool:
        pass                                                  

                                                                          
           
        return self is SimulationStatus.STABLY_SOLVED

    def is_not_solved(self) -> bool:
        pass                                                          
        return self is SimulationStatus.NOT_SOLVED

    def is_invalid(self) -> bool:
        pass                                             
        return self is SimulationStatus.INVALID_INPUT


class ActionSimulator():
    pass                                                                

    def __init__(
            self,
            tasks: Union[Sequence[task_if.Task], Mapping[str, task_if.Task]],
            action_mapper,
            no_goals: bool = True):
        if isinstance(tasks, Mapping):
            self._tasks = tuple(tasks.values())
        else:
            self._tasks = tuple(tasks)
        if isinstance(action_mapper, str):
            self.tier = action_mapper
            action_mapper = phyre.action_mappers.get_action_mapper(
                action_mapper)
        else:
            self.tier = 'unknown'
        self._action_mapper = action_mapper
        self._initial_scenes, self._initial_featurized_objects, self._goals = _get_observations(
            self._tasks, self._action_mapper)
        if no_goals:
            self._goals = None
        self._serialized = tuple(
            phyre.simulator.serialize(task) for task in self._tasks)
        self._keep_spaces = self._action_mapper.KEEP_SPACE_AROUND_BODIES
        self._task_ids = tuple(task.taskId for task in self._tasks)

    def sample(self, valid_only=True, rng=None) -> ActionLike:
        pass                                                       
        return self._action_mapper.sample(valid_only=valid_only, rng=rng)

    @property
    def action_space_dim(self) -> int:
        pass                                        
        return len(self._action_mapper.DIMENSION_TYPES)

    def build_discrete_action_space(self, max_actions,
                                    seed=1) -> Sequence[ActionLike]:
        pass                                                                   

             
                                                                 
                                                            

                
                                                                     
           
        rng = np.random.RandomState(seed=seed)
        return [self.sample(rng=rng) for _ in range(max_actions)]

    @property
    def initial_scenes(self) -> np.ndarray:
        pass                                                        

                                                     
           
        return self._initial_scenes

    @property
    def initial_featurized_objects(self) -> np.ndarray:
        pass                                                                
        
                                                                                
                                                    
           
        return self._initial_featurized_objects

    @property
    def goals(self) -> Optional[np.ndarray]:
        pass                              

                                                                   
                                                                           
                                                                             
                                          
           
        return self._goals

    @property
    def task_ids(self) -> Tuple[str, ...]:
        pass                              
           
        return self._task_ids

    def _get_user_input(self, action):
        user_input, is_valid = self._action_mapper.action_to_user_input(action)
        return user_input, is_valid

    def _simulate_user_input(
            self, task_index, user_input, need_images, need_featurized_objects,
            stride) -> Tuple[SimulationStatus, MaybeImages, MaybeObjects]:
        serialzed_task = self._serialized[task_index]
                                                          
        if not self._action_mapper.OCCLUSIONS_ALLOWED:
            if phyre.simulator.check_for_occlusions(
                    serialzed_task,
                    user_input,
                    keep_space_around_bodies=self._keep_spaces):
                return SimulationStatus.INVALID_INPUT, None, None

        if not need_images and not need_featurized_objects:
            stride = 100000
        is_solved, had_occlusions, images, objects = phyre.simulator.magic_ponies(
            serialzed_task,
            user_input,
            stride=stride,
            keep_space_around_bodies=self._keep_spaces,
            need_images=need_images,
            need_featurized_objects=need_featurized_objects)
        if not need_images:
            images = None
        if not need_featurized_objects:
            objects = None

                                                                             
                     
        assert not had_occlusions or self._action_mapper.OCCLUSIONS_ALLOWED

        if is_solved:
            status = SimulationStatus.SOLVED
        else:
            status = SimulationStatus.NOT_SOLVED

        return status, images, objects

    def simulate_single(self,
                        task_index: int,
                        action: ActionLike,
                        need_images: bool = True,
                        stride: int = phyre.simulator.DEFAULT_STRIDE,
                        stable: bool = False
                       ) -> Tuple[SimulationStatus, MaybeImages]:
        pass                                                       
                                       

             
                                          
                                                                          
                       
                                                              
                                                                       
                                                                          
                                                                            
                                                     
                                                                           
                                                                      
                                                                        
                                                                        
                              

                
                                                                       
                                                            
                                                                                  
                                                               
           
        simulation = self.simulate_action(task_index,
                                          action,
                                          need_images=need_images,
                                          need_featurized_objects=False,
                                          stride=stride,
                                          stable=stable)
        return simulation.status, simulation.images

    def simulate_action(self,
                        task_index: int,
                        action: ActionLike,
                        *,
                        need_images: bool = True,
                        need_featurized_objects: bool = False,
                        stride: int = phyre.simulator.DEFAULT_STRIDE,
                        stable: bool = False) -> phyre.simulation.Simulation:
        pass                              

             
                                          
                                                                          
                       
                                                              
                                                                                      
                                                                       
                                                                          
                                                                            
                                                     
                                                                           
                                                                      
                                                                        
                                                                        
                              

                
                                                                          
                                
                                                                          
                                                                                
                                                   
           
        user_input, is_valid = self._get_user_input(action)
        if not is_valid:
            return phyre.simulation.Simulation(
                status=SimulationStatus.INVALID_INPUT)

        main_status, images, objects = self._simulate_user_input(
            task_index, user_input, need_images, need_featurized_objects,
            stride)
        if not stable or not main_status.is_solved():
            return phyre.simulation.Simulation(status=main_status,
                                               images=images,
                                               featurized_objects=objects)

        for modified_user_input in _yield_user_input_neighborhood(user_input):
            status, _, _ = self._simulate_user_input(
                task_index,
                modified_user_input,
                need_images=False,
                need_featurized_objects=False,
                stride=stride)
            if status.is_not_solved():
                return phyre.simulation.Simulation(
                    status=SimulationStatus.UNSTABLY_SOLVED,
                    images=images,
                    featurized_objects=objects)
        return phyre.simulation.Simulation(
            status=SimulationStatus.STABLY_SOLVED,
            images=images,
            featurized_objects=objects)


def _yield_user_input_neighborhood(base_user_input):
    for dx in (-0.5, 0, 0.5):
        for dy in (-0.5, 0, 0.5):
            if dx == 0 and dy == 0:
                continue
            user_input = copy.deepcopy(base_user_input)
            for polygon in user_input.polygons:
                for v in polygon.vertices:
                    v.x += dx
                    v.y += dy
            for circle in user_input.balls:
                circle.position.x += dx
                circle.position.y += dy
            yield user_input


def _encode_goal(task):
    obj1_code = min(task.bodyId1, MAX_OBJECT_TYPE - 1)
    obj2_code = min(task.bodyId2, MAX_OBJECT_TYPE - 1)
    assert len(task.relationships) == 1, task
    rel = task.relationships[0]
                                               
    assert 0 <= rel < MAX_RELATION, rel
    assert 0 <= obj1_code < MAX_OBJECT_TYPE, rel
    assert 0 <= obj2_code < MAX_OBJECT_TYPE, rel
    return obj1_code, rel, obj2_code


def _get_observations(
        tasks: Sequence[task_if.Task],
        action_mapper=None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    pass                                               

         
                                  

            
                                         
                                                             
                                                                     
                                           
                                                        
                                                
                                                                
                                                                             
                                                                           
                                       
       
    scenes = np.stack(
        [phyre.simulator.scene_to_raster(task.scene) for task in tasks])
    featurized_objects = [
        phyre.simulator.scene_to_featurized_objects(task.scene)
        for task in tasks
    ]
    goals = np.array([_encode_goal(task) for task in tasks], dtype=np.uint8)
    return (scenes, featurized_objects, goals)


def initialize_simulator(task_ids: Sequence[str],
                         action_tier: str) -> ActionSimulator:
    pass                                                      
    tasks = phyre.loader.load_compiled_task_list(task_ids)
    return ActionSimulator(tasks, action_tier)
