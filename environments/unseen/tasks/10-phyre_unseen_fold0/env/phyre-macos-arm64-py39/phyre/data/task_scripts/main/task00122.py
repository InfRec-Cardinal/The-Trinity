                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import numpy as np
import phyre.creator as creator_lib

__SCALE = np.linspace(0.5, 0.7, 4)
__SCALE_2 = np.linspace(0.4, 0.6, 4)
__CENTER_X = np.linspace(0.4, 0.7, 5)
__HEIGHT = np.linspace(0.0, 0.075, 2)
__LEFT = [True, False]


@creator_lib.define_task_template(center_x=__CENTER_X,
                                  scale=__SCALE,
                                  scale2=__SCALE_2,
                                  height=__HEIGHT,
                                  left=__LEFT,
                                  max_tasks=100,
                                  search_params=dict(
                                    required_flags=['TWO_BALLS:GOOD_STABLE'],
                                    excluded_flags=['BALL:GOOD_STABLE', 
                                        'TWO_BALLS:TRIVIAL'],
                                    diversify_tier='two_balls',
                                    max_search_tasks=320,
                                  ),
                                  version="10")
def build_task(C, center_x, scale, scale2, height, left):

                             
    ground = C.add('static bar',
                   scale=1.0,
                   bottom=height * C.scene.height,
                   center_x=0.5 * C.scene.width)

    base = C.add('static standingsticks',
                 scale=scale,
                 center_x=center_x * C.scene.width,
                 bottom=ground.top)

                                                                  
    if left:
        sticks = C.add('dynamic standingsticks',
                       scale=scale2,
                       right=base.left + 0.1 * scale2 * C.scene.width,
                       bottom=base.top - 0.10 * scale2 * C.scene.height,
                       angle=35.)
    else:
        sticks = C.add('dynamic standingsticks',
                       scale=scale2,
                       left=base.right - 0.1 * scale2 * C.scene.width,
                       bottom=base.top - 0.10 * scale2 * C.scene.height,
                       angle=-35.)

                  
    C.update_task(body1=sticks,
                  body2=ground,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
