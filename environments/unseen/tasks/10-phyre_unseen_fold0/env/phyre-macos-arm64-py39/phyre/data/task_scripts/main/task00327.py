                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                             
                                       
   
import phyre.creator as creator_lib

__BALL_SIZE = 0.1
__HOLE_SIZE = 0.2
__GLASS_SIZE = 0.2
__HOLE_LEFT = [0.1 * val for val in range(3, 7)]
__BAR_HEIGHT = [0.1 * val for val in range(4, 6)]
__BALL_XS = [0.1 * val for val in range (2, 8)]
__LEFT_WALL = [True, False]


@creator_lib.define_task_template(
    ball_x =__BALL_XS,
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT,
    left_wall=__LEFT_WALL)
def build_task(C, ball_x, hole_left, bar_height, left_wall):

                                 
    hole_right = hole_left + __HOLE_SIZE
    if hole_right >= 1.0:
        raise creator_lib.SkipTemplateParams

               
    ball = C.add('dynamic ball', scale=__BALL_SIZE) \
            .set_center_x(ball_x * C.scene.width) \
            .set_bottom(0.6 * C.scene.height)

                                   
    if ball.right > hole_left * C.scene.width and \
       ball.left < hole_right * C.scene.width:
        raise creator_lib.SkipTemplateParams

                                   
    C.add('static bar', scale=hole_left) \
     .set_left(0.) \
     .set_bottom(bar_height * C.scene.height)
    C.add('static bar', scale=1.0 - hole_right) \
     .set_right(C.scene.width) \
     .set_bottom(bar_height * C.scene.height)

              
    jar = C.add('dynamic jar', scale=__GLASS_SIZE) \
           .set_center_x(ball_x * C.scene.width) \
           .set_bottom(0.)
    phantom_vertices = jar.get_phantom_vertices()

                  
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
