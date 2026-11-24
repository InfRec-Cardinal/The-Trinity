                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                              
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    ball_left=np.linspace(0.2, 0.8, 20),
    hole_left=np.linspace(0.2, 0.8, 20),
    bar_height=np.linspace(0.3, 0.6, 16),
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'
    ),
    version='4',
)
def build_task(C, ball_left, hole_left, bar_height):

                          
    jar = C.add('dynamic jar', scale=0.15) \
           .set_center_x(0.5 * C.scene.width) \
           .set_top(0.95 * C.scene.height) \
           .set_angle(180.)

                                      
    left_bar = C.add('static bar', scale=hole_left) \
                .set_left(0) \
                .set_bottom(bar_height * C.scene.height)
    hole_right = hole_left + 0.2
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams
    right_bar = C.add('static bar', scale=1.0 - hole_right) \
                 .set_right(C.scene.width) \
                 .set_bottom(bar_height * C.scene.height)

                      
    ball = C.add('dynamic ball', scale=0.1) \
            .set_bottom(right_bar.top) \
            .set_left(ball_left * C.scene.width)

                                       
    if jar.left < left_bar.right or jar.right > right_bar.left:
        raise creator_lib.SkipTemplateParams

                                     
    ball_center_x = ball.left + (ball.right - ball.left) / 2.
    if left_bar.right < ball_center_x < right_bar.left:
        raise creator_lib.SkipTemplateParams

    C.add('static bar', 2.0, left=0, bottom=-2, angle=10)

                  
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
