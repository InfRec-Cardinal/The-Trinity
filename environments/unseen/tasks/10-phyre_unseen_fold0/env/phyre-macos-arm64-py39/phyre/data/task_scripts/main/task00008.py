                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                        
import numpy as np
import phyre.creator as creator_lib


NUM_BARS = 5
BAR_SCALE = 0.7 / NUM_BARS                                            

@creator_lib.define_task_template(
    ball_x=np.linspace(0.1, 0.9, 10),
    ball_scale=np.linspace(0.05, 0.1, 1),
    y_span=np.linspace(0.4, 0.6, 10),
    target_index=np.arange(1, NUM_BARS),
    jar_scale=np.linspace(0.3, 0.4, 2),
    align=["left", "right"],
    search_params=dict(
        required_flags=['BALL:GOOD_STABLE'],
        excluded_flags=['BALL:TRIVIAL'],
        diversify_tier='ball',
        max_search_tasks=1000,
    ),
    version='3',
)
def build_task(C, ball_x, ball_scale, y_span, target_index, jar_scale, align):
    def bar_top(i):
        pass                             
                                                                    
        return 0.8 * C.scene.height - i / NUM_BARS * y_span * C.scene.height

    def bar_left(i):
        pass                             
        return i / NUM_BARS * C.scene.width

    bars = []
    for i in range(NUM_BARS):
        bar = C.add('static bar', scale=BAR_SCALE) \
               .set_top(bar_top(i)) \
               .set_left(bar_left(i)) \
               .set_angle(-5.)
        bars.append(bar)

    jar = C.add(
        'static jar',
        scale=jar_scale,
        bottom=0)

    if jar.top > bars[-1].bottom:
        raise creator_lib.SkipTemplateParams

    if align == "right":
        jar.set_right(bars[target_index].right)
    else:
        jar.set_left(bars[target_index].left)

    jar_guard_l = C.add(
        'static bar',
        scale=jar_scale,
        bottom=0,
        right=jar.left,
        angle=90.)
    jar_guard_r = C.add(
        'static bar',
        scale=jar_scale,
        bottom=0,
        left=jar.right,
        angle=90.)
    if jar_guard_r.right > C.scene.width:
        raise creator_lib.SkipTemplateParams
    ball = C.add('dynamic ball', scale=ball_scale) \
            .set_top(C.scene.height) \
            .set_center_x(ball_x*C.scene.width)
    if ball.left > jar.right:
        raise creator_lib.SkipTemplateParams

    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.BALL)
