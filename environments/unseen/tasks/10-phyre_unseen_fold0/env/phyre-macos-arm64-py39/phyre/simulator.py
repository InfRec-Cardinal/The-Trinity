                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                
                                                                            
from typing import List
import copy
import numpy as np
from thrift import TSerialization
from thrift.protocol import TBinaryProtocol

import phyre.interface.scene.ttypes as scene_if
import phyre.interface.task.ttypes as task_if
from phyre import creator
from phyre import simulator_bindings
import phyre.simulation

DEFAULT_MAX_STEPS = simulator_bindings.DEFAULT_MAX_STEPS
STEPS_FOR_SOLUTION = simulator_bindings.STEPS_FOR_SOLUTION
DEFAULT_STRIDE = simulator_bindings.FPS
OBJECT_FEATURE_SIZE = simulator_bindings.OBJECT_FEATURE_SIZE

FACTORY = TBinaryProtocol.TBinaryProtocolAcceleratedFactory()


def serialize(obj):
    return TSerialization.serialize(obj, protocol_factory=FACTORY)


def deserialize(obj, pickle):
    return TSerialization.deserialize(obj, pickle, protocol_factory=FACTORY)


def build_user_input(points=None, rectangulars=None, balls=None):
    points, rectangulars, balls = _prepare_user_input(points, rectangulars,
                                                      balls)
    user_input = scene_if.UserInput(
        flattened_point_list=points.flatten().tolist(), balls=[], polygons=[])
    for start in range(0, len(rectangulars), 8):
        rect = rectangulars[start:start + 8]
        vertices = []
        for i in range(4):
            vertices.append(
                scene_if.Vector(rect[2 * i] - rect[0],
                                rect[2 * i + 1] - rect[1]))
        user_input.polygons.append(
            scene_if.PolygonWithPosition(
                vertices=vertices,
                position=scene_if.Vector(rect[0], rect[1]),
                angle=0,
            ))
    for start in range(0, len(balls), 3):
        ball = balls[start:start + 3]
        user_input.balls.append(
            scene_if.CircleWithPosition(position=scene_if.Vector(
                ball[0], ball[1]),
                                        radius=ball[2]))
    return user_input


def simulate_scene(scene: scene_if.Scene,
                   steps: int = DEFAULT_MAX_STEPS) -> List[scene_if.Scene]:
    serialized_scenes = simulator_bindings.simulate_scene(
        serialize(scene), steps)
    scenes = [deserialize(scene_if.Scene(), b) for b in serialized_scenes]
    return scenes


def simulate_task(task: task_if.Task,
                  steps: int = DEFAULT_MAX_STEPS,
                  stride: int = DEFAULT_STRIDE) -> task_if.TaskSimulation:
    result = simulator_bindings.simulate_task(serialize(task), steps, stride)
    return deserialize(task_if.TaskSimulation(), result)


def check_for_occlusions(task, user_input, keep_space_around_bodies=True):
    pass                                                    
    if not isinstance(task, bytes):
        task = serialize(task)
    if isinstance(user_input, scene_if.UserInput):
        return simulator_bindings.check_for_occlusions_general(
            task, serialize(user_input), keep_space_around_bodies)
    else:
        points, rectangulars, balls = _prepare_user_input(*user_input)
        return simulator_bindings.check_for_occlusions(
            task, points, rectangulars, balls, keep_space_around_bodies)


def add_user_input_to_scene(scene: scene_if.Scene,
                            user_input: scene_if.UserInput,
                            keep_space_around_bodies: bool = True,
                            allow_occlusions: bool = False) -> scene_if.Scene:
    pass                                    

         
                              
                                                                                 
                                                                         
                                         

            
                                                
       
    if not isinstance(user_input, scene_if.UserInput):
        user_input = build_user_input(*user_input)

    return deserialize(
        scene_if.Scene(),
        simulator_bindings.add_user_input_to_scene(serialize(scene),
                                                   serialize(user_input),
                                                   keep_space_around_bodies,
                                                   allow_occlusions))


def simulate_task_with_input(task,
                             user_input,
                             steps=DEFAULT_MAX_STEPS,
                             stride=DEFAULT_STRIDE,
                             keep_space_around_bodies=True):
    pass                                                       

                                                                        
                                             
       
    if not isinstance(user_input, scene_if.UserInput):
        user_input = build_user_input(*user_input)

                              
    task = copy.copy(task)
    task.scene = add_user_input_to_scene(task.scene, user_input,
                                         keep_space_around_bodies)
    return simulate_task(task, steps, stride)


def scene_to_raster(scene: scene_if.Scene) -> np.ndarray:
    pass                                                                      
       
    pixels = simulator_bindings.render(serialize(scene))
    return np.array(pixels).reshape((scene.height, scene.width))


def scene_to_featurized_objects(scene):
    pass                                                              
                                          
    object_vector = simulator_bindings.featurize_scene(serialize(scene))
    object_vector = np.array(object_vector, dtype=np.float32).reshape(
        (-1, OBJECT_FEATURE_SIZE))
    return phyre.simulation.FeaturizedObjects(
        phyre.simulation.finalize_featurized_objects(
            np.expand_dims(object_vector, axis=0)))


def _deep_flatten(iterable):
    if isinstance(iterable, (tuple, list, np.ndarray)):
        for i in iterable:
            yield from _deep_flatten(i)
    else:
        yield iterable


def _prepare_user_input(points, rectangulars, balls):
    if points is None:
        points = np.empty([0], np.int32)
    elif isinstance(points, np.ndarray):
        assert points.dtype == np.int32, points.dtype
    else:
        points = np.array(points, np.int32)
                                                                   
    points = points.reshape((-1, 2))
    if rectangulars is None:
        rectangulars = []
    else:
        rectangulars = tuple(_deep_flatten(rectangulars))
        assert len(rectangulars) % 8 == 0
    if balls is None:
        balls = []
    else:
        balls = tuple(_deep_flatten(balls))
        assert len(balls) % 3 == 0
    return points, rectangulars, balls


def magic_ponies(task,
                 user_input,
                 steps=DEFAULT_MAX_STEPS,
                 stride=DEFAULT_STRIDE,
                 keep_space_around_bodies=True,
                 with_times=False,
                 need_images=False,
                 need_featurized_objects=False):
    pass                                                          

         
                                                                           
                     
                                                                               
                                                                            
                                                              
                                 
                                                              
                                                                               
                                                                         
                                       
                                                    
                                                       
                                                                         
                               
                                                                         
                                         
                                                                              
                                                                                 
                                                                                              

            
                                                                                    
                            
                                 
                                                                      
                                                                                     
                                                                                       
                                     
                                                                               
                                                                     
       
    if isinstance(task, bytes):
        serialized_task = task
        height, width = creator.SCENE_HEIGHT, creator.SCENE_WIDTH
    else:
        serialized_task = serialize(task)
        height, width = task.scene.height, task.scene.width
    if isinstance(user_input, scene_if.UserInput):
        is_solved, had_occlusions, packed_images, packed_featurized_objects, number_objects, sim_time, pack_time = (
            simulator_bindings.magic_ponies_general(serialized_task,
                                                    serialize(user_input),
                                                    keep_space_around_bodies,
                                                    steps, stride, need_images,
                                                    need_featurized_objects))
    else:
        points, rectangulars, balls = _prepare_user_input(*user_input)
        is_solved, had_occlusions, packed_images, packed_featurized_objects, number_objects, sim_time, pack_time = (
            simulator_bindings.magic_ponies(serialized_task, points,
                                            rectangulars, balls,
                                            keep_space_around_bodies, steps,
                                            stride, need_images,
                                            need_featurized_objects))

    packed_images = np.array(packed_images, dtype=np.uint8)

    images = packed_images.reshape((-1, height, width))
    packed_featurized_objects = np.array(packed_featurized_objects,
                                         dtype=np.float32)
    if packed_featurized_objects.size == 0:
                                                
        packed_featurized_objects = np.zeros(
            (0, number_objects, OBJECT_FEATURE_SIZE))
    else:
        packed_featurized_objects = packed_featurized_objects.reshape(
            (-1, number_objects, OBJECT_FEATURE_SIZE))
    packed_featurized_objects = phyre.simulation.finalize_featurized_objects(
        packed_featurized_objects)
    if with_times:
        return is_solved, had_occlusions, images, packed_featurized_objects, sim_time, pack_time
    else:
        return is_solved, had_occlusions, images, packed_featurized_objects


def batched_magic_ponies(tasks,
                         user_inputs,
                         num_workers,
                         steps=DEFAULT_MAX_STEPS,
                         stride=DEFAULT_STRIDE,
                         keep_space_around_bodies=True,
                         with_times=False,
                         need_images=False,
                         need_featurized_objects=False):
    del num_workers             
    return tuple(
        zip(*[
            magic_ponies(t,
                         ui,
                         steps=steps,
                         stride=stride,
                         keep_space_around_bodies=keep_space_around_bodies,
                         with_times=with_times,
                         need_images=need_images,
                         need_featurized_objects=need_featurized_objects)
            for t, ui in zip(tasks, user_inputs)
        ]))
