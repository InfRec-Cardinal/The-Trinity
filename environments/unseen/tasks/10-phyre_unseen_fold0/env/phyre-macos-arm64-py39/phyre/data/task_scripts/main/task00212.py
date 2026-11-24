                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                           
import phyre.creator as creator_lib

__BALL_SIZES = [0.1, 0.15, 0.2]
__HOLE_SIZES = [0.1, 0.15, 0.2]
__HOLE_LEFT = [0.1 * val for val in range(2, 9)]
__BAR_HEIGHT = [0.1 * val for val in range(1, 8)]


@creator_lib.define_task_template(
    max_tasks=100,
    ball_size=__BALL_SIZES,
    hole_size=__HOLE_SIZES,
    hole_left=__HOLE_LEFT,
    bar_height=__BAR_HEIGHT,
)
def build_task(C, ball_size, hole_size, hole_left, bar_height):
                                              
    if ball_size > hole_size:
        raise creator_lib.SkipTemplateParams

              
    ball = C.add(
        'dynamic ball', scale=ball_size).set(
            center_x=0.5 * C.scene.width, top=0.95 * C.scene.height)

                          
    left_bar, right_bar = _bar_with_hole(C, bar_height, hole_left, hole_size)

                                   
    if ball.left >= left_bar.right and ball.right <= right_bar.left:
        raise creator_lib.SkipTemplateParams

    if ball.bottom <= left_bar.top:
        raise creator_lib.SkipTemplateParams

                             
    shift = 0.1 if hole_left < 0.5 else -0.1
    bar, _ = _bar_with_hole(C, bar_height - ball_size * 2, hole_left + shift,
                            hole_size)
    if bar.bottom <= (ball.right - ball.left) * 0.5:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=C.bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])


def _bar_with_hole(C, bar_height, hole_left, hole_size):
    if not 0 < hole_left < 1.0:
        raise creator_lib.SkipTemplateParams

    left_bar = C.add(
        'static bar', scale=hole_left).set(
            left=0, bottom=bar_height * C.scene.height)

    hole_right = hole_left + hole_size
    if not 0 < hole_right < 1.0:
        raise creator_lib.SkipTemplateParams

    right_bar = C.add(
        'static bar', scale=1.0 - hole_right).set(
            right=C.scene.width, bottom=bar_height * C.scene.height)

    return left_bar, right_bar
