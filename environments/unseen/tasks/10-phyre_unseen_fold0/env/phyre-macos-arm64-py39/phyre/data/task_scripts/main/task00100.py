                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                             
                                       
   
import phyre.creator as creator_lib

__BALL_SIZE = [0.075, 0.1, 0.125]
__HOLE_SIZE = [0.15, 0.2, 0.25]
__GLASS_SIZE = [0.2, 0.25]
__HOLE_LEFT = [0.1 * val for val in range(3, 7)]
__BAR_HEIGHT = [0.1 * val for val in range(4, 6)]
__LEFT_WALL = [True, False]


@creator_lib.define_task_template(
    ball_size=__BALL_SIZE,
    hole_size=__HOLE_SIZE,
    glass_size=__GLASS_SIZE,
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT,
    left_wall=__LEFT_WALL,
    search_params=dict(
        excluded_flags=['BALL:GOOD_STABLE'],
        max_search_tasks=300,
    ),
    version='3')
def build_task(C, ball_size, hole_size, glass_size, hole_left, bar_height, left_wall):

                                 
    hole_right = hole_left + hole_size
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

               
    ball_center_x = (hole_left if left_wall else hole_right) * C.scene.width
    ball = C.add('dynamic ball', scale=ball_size) \
            .set_center_x(ball_center_x) \
            .set_bottom(0.6 * C.scene.height)

                                   
    C.add('static bar', scale=hole_left) \
     .set_left(0) \
     .set_bottom(bar_height * C.scene.height)
    C.add('static bar', scale=1.0 - hole_right) \
     .set_right(C.scene.width) \
     .set_bottom(bar_height * C.scene.height)

              
    jar = C.add('dynamic jar', scale=glass_size) \
           .set_center_x(ball_center_x) \
           .set_bottom(0)
    phantom_vertices = jar.get_phantom_vertices()

                  
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.TOUCHING],
        phantom_vertices=phantom_vertices)
    C.set_meta(C.SolutionTier.TWO_BALLS)
