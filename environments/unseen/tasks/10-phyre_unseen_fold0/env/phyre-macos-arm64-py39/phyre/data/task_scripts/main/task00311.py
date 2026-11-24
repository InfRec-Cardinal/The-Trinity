                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                    
import phyre.creator as creator_lib

__OBSTACLE_WIDTHS = [val * 0.1 for val in range(2, 8)]
__OBSTACLE_XS = [val * 0.1 for val in range(0, 11)]
__BALL_XS = [val * 0.1 for val in range(2, 9)]


@creator_lib.define_task_template(obstacle_width=__OBSTACLE_WIDTHS,
                                  obstacle_x=__OBSTACLE_XS,
                                  ball_x=__BALL_XS,
                                  max_tasks=100)
def build_task(C, obstacle_width, obstacle_x, ball_x):

                   
    if obstacle_x + obstacle_width > 1.:
        raise creator_lib.SkipTemplateParams
    obstacle = C.add('static bar', scale=obstacle_width) \
        .set_left(obstacle_x * C.scene.width) \
        .set_bottom(0.5 * C.scene.height)

                                           
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)
    if ball.left + ball.width > obstacle.left and ball.right - ball.width < obstacle.right:
        raise creator_lib.SkipTemplateParams

                        
    C.update_task(body1=ball,
                  body2=obstacle,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.SINGLE_OBJECT)
