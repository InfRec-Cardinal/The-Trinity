                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                 
import numpy as np

import phyre.creator as creator_lib

__BALL_XS = np.linspace(0.15, 0.9, 8)
__BAR_YS = [0.1 * val for val in range(3, 7)]
__OBSTACLE_WIDTH = np.linspace(0.1, 0.4, 6)


@creator_lib.define_task_template(
    ball1_x=__BALL_XS,
    ball2_x=__BALL_XS,
    bar_y=__BAR_YS,
    obstacle_width=__OBSTACLE_WIDTH,
    search_params=dict(
        require_two_ball_solvable=True,
        diversify_tier='two_balls',
        max_search_tasks=1000,
    ),
    version='4')
def build_task(C, ball1_x, ball2_x, bar_y, obstacle_width):

                                   
    if ball2_x <= ball1_x:
        raise creator_lib.SkipTemplateParams

                    
    ball_scale = 0.1
    ball1 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x(ball1_x * C.scene.width) \
             .set_bottom(0.9 * C.scene.height)
    ball2 = C.add('dynamic ball', scale=ball_scale) \
             .set_center_x(ball2_x * C.scene.width) \
             .set_bottom(0.9 * C.scene.height)
    if (ball2.left - ball1.right) < ball_scale * C.scene.width:
        raise creator_lib.SkipTemplateParams

                    
    bar_scale = 1. - (ball2.left / float(C.scene.width))
    bar1 = C.add('static bar', scale=bar_scale) \
            .set_bottom(bar_y * C.scene.height) \
            .set_right(C.scene.width)
    bar2 = C.add('static bar', scale=bar_scale + obstacle_width) \
            .set_bottom((bar_y - 0.4 * obstacle_width) * C.scene.height) \
            .set_right(C.scene.width)
    bar_scale = (bar1.top - bar2.top) / float(C.scene.height)
    vertical_bar = C.add('static bar', scale=bar_scale + 0.04) \
                    .set_angle(90.) \
                    .set_left(bar1.left) \
                    .set_bottom(bar2.top)
    C.add('static bar', scale=1.0) \
     .set_angle(90.) \
     .set_top(vertical_bar.top - 0.05 * C.scene.height) \
     .set_left(bar2.left)

                                                
    C.add('static bar', scale=1.0, angle=90.) \
     .set_left(ball2.right + 0.02 * C.scene.width) \
     .set_bottom(bar1.top)

                                            
    if ball1.left + (ball1.right - ball1.left) / 2. >= bar2.left:
        raise creator_lib.SkipTemplateParams

                
    ramp_scale = bar2.left / (1.9 * C.scene.width)
    C.add('static bar', scale=ramp_scale, angle=-10.0) \
     .set_left(0.0) \
     .set_bottom(0.0)
    C.add('static bar', scale=ramp_scale, angle=10.0) \
     .set_right(bar2.left) \
     .set_bottom(0.0)

                        
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
