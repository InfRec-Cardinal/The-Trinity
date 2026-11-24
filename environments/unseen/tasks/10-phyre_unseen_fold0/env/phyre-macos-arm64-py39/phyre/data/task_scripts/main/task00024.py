                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                              
                                                            
   
import numpy as np
import phyre.creator as creator_lib

__BALL_SIZE = 0.1
__HOLE_SIZE = 0.1


@creator_lib.define_task_template(
    hole_left=np.linspace(0.2, 0.8, 12),
    bar_height=np.linspace(0.15, 0.6, 10),
    ball_distance=np.linspace(0.1, 0.3, 4),
    confounder=[True, False],
    search_params=dict(
        max_search_tasks=800,
        required_flags=['BALL:GOOD_STABLE'],
        diversify_tier='ball'
    ),
    version='4',
)
def build_task(C, hole_left, bar_height, ball_distance, confounder):

                                 
    hole_right = hole_left + __HOLE_SIZE
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

                
    ball = C.add('dynamic ball', scale=__BALL_SIZE) \
            .set_center_x(0.5 * C.scene.width) \
            .set_bottom(0.8 * C.scene.height)
    if confounder:
        block_ball = C.add('dynamic ball', scale=__BALL_SIZE + 0.01) \
         .set_left((hole_left + 0.025)  * C.scene.width) \
         .set_bottom((bar_height + ball_distance)* C.scene.height)
    else:   
        block_ball = C.add('dynamic ball', scale=__BALL_SIZE + 0.01) \
         .set_right((hole_right - 0.025) * C.scene.width) \
         .set_bottom((bar_height + ball_distance)* C.scene.height)

                         
    left_bar = C.add('static bar', scale=hole_left) \
                .set_left(0) \
                .set_bottom(bar_height * C.scene.height)
    right_bar = C.add('static bar', scale=1.0 - hole_right) \
                 .set_right(C.scene.width) \
                 .set_bottom(bar_height * C.scene.height)

                                    
    if ball.left >= left_bar.right and ball.right <= right_bar.left:
        raise creator_lib.SkipTemplateParams

                                                
    if block_ball.top >= ball.bottom:
        raise creator_lib.SkipTemplateParams

    bottom_wall = C.add('static bar', 1.0, left=0, bottom=0)
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])

    C.set_meta(C.SolutionTier.BALL)
