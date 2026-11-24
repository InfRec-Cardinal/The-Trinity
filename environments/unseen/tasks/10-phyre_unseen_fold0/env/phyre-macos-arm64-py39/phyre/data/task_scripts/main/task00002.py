                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                
import phyre.creator as creator_lib

__OBSTACLE_WIDTHS = [val * 0.1 for val in range(1, 8)]
__OBSTACLE_YS = [val * 0.1 for val in range(3, 8)]
__OBSTACLE_XS = [val * 0.1 for val in range(0, 11)]


@creator_lib.define_task_template(
    obstacle_width=__OBSTACLE_WIDTHS,
    obstacle_x=__OBSTACLE_XS,
    obstacle_y=__OBSTACLE_YS,
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball'
    ),
    max_tasks=100)
def build_task(C, obstacle_width, obstacle_x, obstacle_y):
                   
    if obstacle_x + obstacle_width > 1.:
        raise creator_lib.SkipTemplateParams
    obstacle_x *= C.scene.width
    obstacle_y *= C.scene.height
    obstacle = C.add('static bar', scale=obstacle_width) \
        .set_left(obstacle_x) \
        .set_bottom(obstacle_y)

                                           
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(obstacle_x + obstacle.width / 2.) \
        .set_bottom(0.9 * C.scene.height)

    bottom_wall = C.add('static bar', 1, bottom=0, left=0)

                        
    C.update_task(
        body1=ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
