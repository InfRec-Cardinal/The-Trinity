                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                       
import phyre.creator as creator_lib

__OBSTACLE_LOCS = ['left', 'right']
__OBSTACLE_SCALES = [val * 0.1 for val in range(2, 9)]
__BALL_XS = [val * 0.1 for val in range(1, 10)]


@creator_lib.define_task_template(obstacle_location=__OBSTACLE_LOCS,
                                  obstacle_scale=__OBSTACLE_SCALES,
                                  ball_x=__BALL_XS)
def build_task(C, obstacle_location, obstacle_scale, ball_x):

                           
    obstacle = C.add('static bar', scale=obstacle_scale) \
        .set_angle(30. if obstacle_location == 'left' else -30.) \
        .set_bottom(0.2 * C.scene.height)
    if obstacle_location == 'left':
        obstacle.set_left(-0.01 * C.scene.width)
    else:
        obstacle.set_right(1.01 * C.scene.width)

                                         
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)
    if obstacle_location == 'left' and ball.right > obstacle.right:
        raise creator_lib.SkipTemplateParams
    if obstacle_location == 'right' and ball.left < obstacle.left:
        raise creator_lib.SkipTemplateParams

                        
    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.SINGLE_OBJECT)
