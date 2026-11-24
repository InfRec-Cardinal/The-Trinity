                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                      
import phyre.creator as creator_lib

__OBSTACLE_WIDTHS = [val * 0.1 for val in range(1, 8)]
__OBSTACLE_YS = [val * 0.1 for val in range(4, 8)]
__OBSTACLE_XS = [val * 0.1 for val in range(0, 11)]


@creator_lib.define_task_template(
    obstacle_width=__OBSTACLE_WIDTHS,
    obstacle_x=__OBSTACLE_XS,
    obstacle_y=__OBSTACLE_YS,
    max_tasks=100)
def build_task(C, obstacle_width, obstacle_x, obstacle_y):

                             
    if obstacle_x + obstacle_width > 1.:
        raise creator_lib.SkipTemplateParams
    obstacle = C.add('static bar', scale=obstacle_width) \
        .set_left(obstacle_x * C.scene.width) \
        .set_bottom(obstacle_y * C.scene.height)

                                        
    obstacle_bottom = (obstacle_y - 0.2) * C.scene.height
    if obstacle_x > 0.:
        left_obstacle = C.add('static bar', scale=obstacle_x) \
                         .set_left(0.) \
                         .set_bottom(obstacle_bottom)
    obstacle_scale = 1. - obstacle_x - obstacle_width
    if obstacle_scale > 0.:
        right_obstacle = C.add('static bar', scale=obstacle_scale) \
                          .set_right(C.scene.width) \
                          .set_bottom(obstacle_bottom)

                                            
    if obstacle_x > 0.:
        C.add('static bar', scale=0.02) \
         .set_angle(90.) \
         .set_bottom(left_obstacle.top) \
         .set_right(left_obstacle.right)
    if obstacle_scale > 0.:
        C.add('static bar', scale=0.02) \
         .set_angle(90.) \
         .set_bottom(right_obstacle.top) \
         .set_left(right_obstacle.left)

                                                 
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(obstacle_x * C.scene.width + obstacle.width / 2.) \
        .set_bottom(0.9 * C.scene.height)

    bottom_wall = C.add('static bar', 1, bottom=0, left=0)

                        
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
