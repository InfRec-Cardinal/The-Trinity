                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                            
import numpy as np
import phyre.creator as creator_lib

__BALL_SIZE = 0.1


@creator_lib.define_task_template(
    ball1_x=np.linspace(0.1, 0.9, 8),
    ball2_x=np.linspace(0.1, 0.9, 8),
    ball1_y=np.linspace(0.5, 0.8, 8),
    ball2_y=np.linspace(0.5, 0.8, 8),
    version='2',
)
def build_task(C, ball1_x, ball2_x, ball1_y, ball2_y):

                                                           
    if ball2_x <= ball1_x + .2:
        raise creator_lib.SkipTemplateParams

                
    ball1 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x(ball1_x * C.scene.width) \
             .set_bottom(ball1_y * C.scene.height)
    ball2 = C.add('dynamic ball', scale=__BALL_SIZE) \
             .set_center_x(ball2_x * C.scene.width) \
             .set_bottom(ball2_y * C.scene.height)

                               
    C.add('dynamic jar', scale=0.15) \
     .set_center_x(ball1.left + (ball1.right - ball1.left) / 2.) \
     .set_bottom(0.)
    C.add('dynamic jar', scale=0.15) \
     .set_center_x(ball2.left + (ball2.right - ball2.left) / 2.) \
     .set_bottom(0.)

                  
    C.update_task(
        body1=ball1,
        body2=ball2,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
