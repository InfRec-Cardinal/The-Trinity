                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                              
import phyre.creator as creator_lib


__PLATFORM_X = [val * 0.05 for val in range(6, 16)]
__PLATFORM_Y = [val * 0.1 for val in range(0, 8)]

@creator_lib.define_task_template(
    max_tasks=100,
    platform1_x=__PLATFORM_X,
    platform1_y=__PLATFORM_Y,
    platform2_x=__PLATFORM_X,
    platform2_y=__PLATFORM_Y,
    search_params=dict(require_two_ball_solvable=True),
)
def build_task(C, platform1_x, platform1_y, platform2_x, platform2_y):

                                                            
    if platform1_x + 0.3 >= platform2_x:
        raise creator_lib.SkipTemplateParams

                                                     
    if abs(platform1_y - platform2_y) >= 0.3:
        raise creator_lib.SkipTemplateParams

                                                         
    jar1, ball1 = _jar_with_ball(C, platform1_x, platform1_y, right=False)
    jar2, ball2 = _jar_with_ball(C, platform2_x, platform2_y, right=True)

                  
    C.update_task(body1=ball1,
                  body2=ball2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)


def _jar_with_ball(C, x, y, right=False):

                                    
    platform = C.add('static bar', scale=0.2) \
                .set_bottom(y * C.scene.height) \
                .set_center_x(x * C.scene.width)
    obstacle = C.add('static bar', scale=0.02) \
                .set_angle(90.0) \
                .set_bottom(platform.top)
    if right:
        obstacle.set_right(platform.right)
    else:
        obstacle.set_left(platform.left)

                             
    offset = (platform.right - platform.left) / 2.0
    offset += 0.04 * C.scene.width if right else -0.04 * C.scene.height
    jar = C.add('dynamic jar', scale=0.2) \
           .set_angle(146.0 if right else -146.0) \
           .set_bottom(platform.top) \
           .set_center_x(platform.left + offset)

                      
    offset = (jar.right - jar.left) * 0.7
    ball = C.add('dynamic ball', scale=0.1) \
            .set_bottom(jar.bottom) \
            .set_center_x(jar.right - offset if right else jar.left + offset)
    return jar, ball
