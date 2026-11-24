                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                  
import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

                                  
    ball1, line1 = _make_catapult(C, 0.5, 0.1)

    C.add(
        'static bar',
        scale=0.4,
        angle=90,
        bottom=line1.top,
        right=line1.center_x + 10)
    C.add(
        'dynamic ball', scale=0.1, bottom=line1.top, right=line1.center_x + 40)
    C.add('static bar', scale=0.4, angle=90, bottom=line1.top, left=line1.right)
    C.add('static bar', scale=0.9, bottom=0, right=C.scene.width)

    C.add('static bar', scale=0.3, angle=90, bottom=0, right=line1.left)

                                                                              
                        
    C.update_task(
        body1=ball1,
        body2=C.bottom_wall,
        relationships=[C.SpatialRelationship.TOUCHING])


def _make_catapult(C, x, y):
    pass                    

                           

    base = C.add('static standingsticks ', scale=0.1) \
            .set_bottom(y * C.scene.height) \
            .set_center_x(x * C.scene.width)

                         
    bar_center_x = base.left + (base.right - base.left) / 2.
    ball = C.add('static ball', scale=0.05) \
            .set_bottom(base.top) \
            .set_center_x(bar_center_x)
    line = C.add_box(height=3, width=120) \
            .set_center_x(bar_center_x) \
            .set_bottom(ball.top)

                              
    top_ball = C.add('dynamic ball', scale=0.04) \
                .set_bottom(line.top)
    top_ball.set_left(line.left)
    return top_ball, line
