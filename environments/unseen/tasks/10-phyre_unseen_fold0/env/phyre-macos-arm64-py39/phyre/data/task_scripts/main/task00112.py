                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                      
import numpy as np

import phyre.creator as creator_lib


@creator_lib.define_task_template(
    max_tasks=100,
    num_bars=range(5, 9),
    bar_y=np.linspace(0.4, 0.8, 10),
    ball_x=np.linspace(0.1, 0.4, 10),
    left=[True, False],
    search_params=dict(require_two_ball_solvable=True, max_search_tasks=300),
    version='3',
)
def build_task(C, num_bars, bar_y, ball_x, left):
    bottom_wall = C.add('static bar', 1.0, left=0, bottom=0)

                             
    multiplier, offset = 0.1, 0.2
    if not left:
        multiplier = -multiplier
        offset = 1.0 - offset

                                      
    bars = []
    for idx in range(0, num_bars):
        bar_scale = 0.15 + 0.05 * idx
        bars.append(
            C.add(
                'dynamic bar',
                scale=bar_scale,
                angle=90,
                bottom=bottom_wall.top,
                left=(offset + multiplier * idx) * C.scene.width))

                          
    obstacle = C.add('static bar', scale=0.7) \
                .set_bottom(bar_y * C.scene.height)
    if left:
        obstacle.set_right(C.scene.width)
    else:
        obstacle.set_left(0.0)

                
    ball1 = C.add('dynamic ball', scale=0.1) \
             .set_center_x((1.0 - ball_x if left else ball_x) * C.scene.width) \
             .set_bottom(0.9 * C.scene.height)
    ball2 = C.add('dynamic ball', scale=0.1) \
             .set_center_y(bars[-1].top + (obstacle.bottom - bars[-1].top) / 2.0)
    if left:
        ball2.set_left(bars[-1].left)
    else:
        ball2.set_right(bars[-1].right)

                                                     
    if ball2.bottom <= bars[-1].top or ball2.top >= obstacle.bottom:
        raise creator_lib.SkipTemplateParams

                        
    C.update_task(
        body1=ball1,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
