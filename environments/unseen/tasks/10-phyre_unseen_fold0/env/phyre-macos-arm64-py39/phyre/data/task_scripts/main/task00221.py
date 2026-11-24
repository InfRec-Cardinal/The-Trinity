                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                                 
              
   

import phyre.creator as creator_lib

__BALL_Y = [0.1 * val for val in range(5, 9)]
__LADDER_X = [0.1 * val for val in range(2, 8)]
__LADDER_HEIGHT = [val for val in range(3, 7)]


@creator_lib.define_task_template(
    ball_y=__BALL_Y,
    ladder_x=__LADDER_X,
    ladder_height=__LADDER_HEIGHT,
)
def build_task(C, ball_y, ladder_x, ladder_height):

                 
    step_height = 0.07
    ladder_width = 0.15
    base = C.add('dynamic bar', scale=ladder_width) \
            .set_bottom(0.) \
            .set_left(ladder_x * C.scene.width)
    offset = .01 * C.scene.width
    for _ in range(ladder_height):
        left = C.add('dynamic bar', scale=step_height) \
                .set_angle(90.) \
                .set_bottom(base.top) \
                .set_left(base.left + offset)
        C.add('dynamic bar', scale=step_height) \
         .set_angle(90.) \
         .set_bottom(base.top) \
         .set_right(base.right - offset)
        base = C.add('dynamic bar', scale=ladder_width) \
                .set_bottom(left.top) \
                .set_left(base.left)

                       
    ball =C.add('dynamic ball', scale=0.15) \
     .set_bottom((ball_y + 0.02) * C.scene.height) \
     .set_center_x(base.right)

    if ball.bottom < base.top + 5:
        raise creator_lib.SkipTemplateParams

                           
    reference = C.add('static bar', scale=0.02) \
                 .set_top(base.bottom)
    if ladder_x <= 0.5:
        reference.set_left(0.0)
    else:
        reference.set_right(C.scene.width)

                  
    C.update_task(
        body1=base,
        body2=reference,
        relationships=[C.SpatialRelationship.ABOVE])
    C.set_meta(C.SolutionTier.PRE_BALL)
