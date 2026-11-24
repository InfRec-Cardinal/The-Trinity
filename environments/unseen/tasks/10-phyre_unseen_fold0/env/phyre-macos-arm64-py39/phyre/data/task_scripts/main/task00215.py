                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                          
import phyre.creator as creator_lib

__JAR_XS = [val * 0.1 for val in range(3, 7)]
__JAR_SCALES = [val * 0.1 for val in range(2, 6)]
__BALL_XS = [val * 0.1 for val in range(2, 8)]
__BALL_YS = [val * 0.1 for val in range(5, 8)]


@creator_lib.define_task_template(
    jar_x=__JAR_XS, jar_scale=__JAR_SCALES, ball_x=__BALL_XS, ball_y=__BALL_YS, version='2')
def build_task(C, jar_x, jar_scale, ball_x, ball_y):

              
    jar = C.add('dynamic jar', scale=jar_scale) \
        .set_left(jar_x * C.scene.width) \
        .set_bottom(0.)
    if jar.left < 0. or jar.right > C.scene.width:
        raise creator_lib.SkipTemplateParams

                                             
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)

                                                                      
    if ball.left > jar.right:                          
        bottom_wall = C.add('static bar', 1.0, bottom=0, right=jar.left)
        C.add('static bar', 1.0, bottom=0, left=bottom_wall.right)
    elif ball.right < jar.left:                       
        bottom_wall = C.add('static bar', 1.0, bottom=0, left=jar.right)
        C.add('static bar', 1.0, bottom=0, right=bottom_wall.left)
    else:
        raise creator_lib.SkipTemplateParams

    jar.set_bottom(bottom_wall.top)

                        
    C.update_task(body1=ball,
                  body2=bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
