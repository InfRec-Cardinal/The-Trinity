                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib
import numpy as np

__DIST = np.linspace(0.05, 0.15, 3)
__SIZE = np.linspace(0.6, 0.8, 4)
__HEIGHT = np.linspace(0.0, 0.3, 6)


@creator_lib.define_task_template(
    size=__SIZE,
    y=__HEIGHT,
    left_d=__DIST,
    right_d=__DIST,
    max_tasks=100,
    version="3",
    search_params=dict(require_two_ball_solvable=True),
)
def build_task(C, size, y, left_d, right_d):

    ball_size = 0.1
    if size == 0.8 and (left_d + right_d) >= 0.2:
        raise creator_lib.SkipTemplateParams

    ground = C.add('static bar', scale=1.0, bottom=y * C.scene.height, left=0.0)

                                                  
    left = C.add('dynamic standingsticks',
                 scale=size,
                 angle=-20,
                 bottom=ground.top,
                 left=left_d * C.scene.width)
    left_ball = C.add('dynamic ball',
                      scale=ball_size,
                      bottom=left.top,
                      center_x=left.center_x + 20)
    right = C.add('dynamic standingsticks',
                  scale=size,
                  angle=20,
                  bottom=ground.top,
                  right=(1 - right_d) * C.scene.width)
    right_ball = C.add('dynamic ball',
                       scale=ball_size,
                       bottom=right.top,
                       center_x=right.center_x - 20)

                                                           
    s = 0.25 / ((left_d + right_d) / 0.2) if (left_d + right_d) > 0.2 else 0.3
    slope_left = C.add('static bar',
                       left=left.right,
                       top=right.top - 20,
                       angle=-10,
                       scale=s)
    slope_right = C.add('static bar',
                        right=right.left,
                        top=left.top - 20,
                        angle=10,
                        scale=s)

                                                                     
    b_slope_left = C.add('static bar',
                         left=left.center_x - 5,
                         bottom=ground.top,
                         angle=30,
                         scale=0.25)
    b_slope_right = C.add('static bar',
                          right=right.center_x + 5,
                          bottom=ground.top,
                          angle=-30,
                          scale=0.25)

                                                                                
             
    border = C.add('static bar',
                   center_x=0.5 * C.scene.width,
                   bottom=right_ball.top + 20,
                   scale=1.0)

                  
    C.update_task(body1=left_ball,
                  body2=right_ball,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
