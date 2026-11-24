                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                  

import phyre.creator as creator_lib

__DIST_TO_OBSTACLE = [0.1 * val for val in range(2, 3)]
__HORIZONTAL_DIST = [0.05 * val for val in range(5, 11)]
__VERTICAL_DIST = [0.1 * val for val in range(2, 5)]
__BASE_X = [0.1 * val for val in range(1, 5)]
__BASE_Y = [0.1 * val for val in range(3, 6)]


@creator_lib.define_task_template(
    max_tasks=100,
    dist_to_obstacle=__DIST_TO_OBSTACLE,
    horizontal_dist=__HORIZONTAL_DIST,
    vertical_dist=__VERTICAL_DIST,
    base_x=__BASE_X,
    base_y=__BASE_Y,
    version='2',
)
def build_task(C, dist_to_obstacle, horizontal_dist, vertical_dist, base_x, base_y):

                                                    
    if horizontal_dist + 0.1 <= vertical_dist:
        raise creator_lib.SkipTemplateParams

                                 
    ball1 = C.add('dynamic ball', scale=0.1) \
             .set_bottom(base_y * C.scene.height) \
             .set_center_x(base_x * C.scene.width)
    ball2 = C.add('dynamic ball', scale=0.1) \
             .set_bottom((base_y + vertical_dist) * C.scene.height) \
             .set_center_x((base_x + horizontal_dist) * C.scene.width)

                    
    bar1 = C.add('static bar', scale=0.1) \
            .set_bottom(ball1.bottom - dist_to_obstacle * C.scene.width) \
            .set_left(ball1.left)
    bar2 = C.add('static bar', scale=0.1) \
            .set_bottom(ball2.bottom - dist_to_obstacle * C.scene.width) \
            .set_left(ball2.left)
    vertical_bar1 = C.add('static bar', scale=1.0) \
                     .set_angle(90.0) \
                     .set_top(bar1.bottom) \
                     .set_center_x(bar1.left + (bar1.right - bar1.left) / 2.0)
    vertical_bar2 = C.add('static bar', scale=1.0) \
                     .set_angle(90.0) \
                     .set_top(bar2.bottom) \
                     .set_center_x(bar2.left + (bar2.right - bar2.left) / 2.0)

                                           
    if ball1.top > C.scene.height or ball2.top > C.scene.height:
        raise creator_lib.SkipTemplateParams

                
    C.add('static bar', scale=horizontal_dist / 2.0, angle=-10.0) \
     .set_left(vertical_bar1.right) \
     .set_bottom(0.0)
    C.add('static bar', scale=horizontal_dist / 2.0, angle=10.0) \
     .set_right(vertical_bar2.left) \
     .set_bottom(0.0)

                        
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
