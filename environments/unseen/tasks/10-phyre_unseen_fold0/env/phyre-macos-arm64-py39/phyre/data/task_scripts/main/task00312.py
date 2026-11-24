                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                            
import phyre.creator as creator_lib

__JAR_XS = [val * 0.1 for val in range(2, 8)]
__JAR_SCALES = [val * 0.1 for val in range(2, 6)]
__BALL_XS = [val * 0.1 for val in range(1, 8)]


@creator_lib.define_task_template(
    jar_x=__JAR_XS, jar_scale=__JAR_SCALES, ball_x=__BALL_XS, max_tasks=100)
def build_task(C, jar_x, jar_scale, ball_x):

              
    jar = C.add('dynamic jar', scale=jar_scale) \
        .set_left(jar_x * C.scene.width) \
        .set_bottom(0.)
    if jar.left < 0. or jar.right > C.scene.width:
        raise creator_lib.SkipTemplateParams
    phantom_vertices = jar.get_phantom_vertices()

                                             
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(ball_x * C.scene.width) \
        .set_bottom(0.9 * C.scene.height)
    if ball.left > jar.left and ball.right < jar.right:
        raise creator_lib.SkipTemplateParams

                        
    C.update_task(body1=ball,
                  body2=jar,
                  relationships=[C.SpatialRelationship.INSIDE],
                  phantom_vertices=phantom_vertices)
    C.set_meta(C.SolutionTier.SINGLE_OBJECT)
