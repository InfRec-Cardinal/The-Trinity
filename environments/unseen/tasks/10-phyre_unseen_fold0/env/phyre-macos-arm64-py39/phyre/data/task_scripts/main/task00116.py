                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    dynamic_swing_base_ball=[0, 1],
    right_ball_size=np.linspace(0.04, 0.06, 4),
    dot_high=np.linspace(0.5, 0.7, 4),
    dot_offset=np.linspace(-0.2, 0.2, 4),
    line_width=np.linspace(0.4, 0.6, 4),
    height=np.linspace(0.05, 0.15, 4),
    horizontal_position=np.linspace(0.4, 0.6, 4),
    search_params=dict(require_two_ball_solvable=True),
    version='2',
)
def build_task(C, dynamic_swing_base_ball, right_ball_size, dot_high,
               dot_offset, height, line_width, horizontal_position):

    def _make_catapult(x, y):
        pass                    

                               

        base = C.add('static standingsticks ', scale=0.1) \
                .set_bottom(y * C.scene.height) \
                .set_center_x(x * C.scene.width)

                             
        bar_center_x = base.left + (base.right - base.left) / 2.
        if dynamic_swing_base_ball:
            ball = C.add('dynamic ball', scale=0.05) \
                    .set_bottom(base.top) \
                    .set_center_x(bar_center_x)
        else:
            ball = C.add('static ball', scale=0.05) \
                    .set_bottom(base.top) \
                    .set_center_x(bar_center_x)
        line = C.add(
            'dynamic bar', line_width, center_x=bar_center_x, bottom=ball.top)

                                  
        top_ball = C.add('dynamic ball', scale=0.04) \
                    .set_bottom(line.top)
        top_ball.set_left(line.left)
        return top_ball, line

                                  
    green_ball, line = _make_catapult(horizontal_position, height)

    C.add(
        'static bar', scale=1.4, angle=25, bottom=C.scene.width * 0.8, left=-5)

                                                      
    left_bar = C.add(
        'static bar', scale=0.5, angle=90, bottom=0, right=line.left)

                  
    C.add('static bar', scale=0.9, bottom=10, right=C.scene.width)

                 
    middle_bar = C.add(
        'static bar',
        scale=0.2,
        angle=90,
        bottom=line.top + 10,
        right=line.center_x + 10)

                                      
    C.add(
        'static bar',
        scale=0.05,
        angle=90,
        top=middle_bar.top,
        right=line.right + 20)
    C.add(
        'dynamic ball',
        scale=right_ball_size,
        bottom=line.top,
        right=(line.center_x + line.right) / 2)
          
    C.add(
        'static bar',
        scale=0.02,
        bottom=C.scene.width * dot_high,
        left=line.center_x + line.width * dot_offset / 2)

    bottom_wall = C.add(
        'static bar', left_bar.left / C.scene.width, bottom=0, left=0)

                        
    C.update_task(
        body1=green_ball,
        body2=bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
