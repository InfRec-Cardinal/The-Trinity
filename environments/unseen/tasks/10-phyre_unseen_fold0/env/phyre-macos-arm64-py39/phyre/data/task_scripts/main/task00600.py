                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib
import numpy as np

__LEFT=np.linspace(0.05, 0.2, 3)
__HEIGHT=np.linspace(0.7, 0.5, 3)
__BLOCKS=range(8,14)
__WIDTH = np.linspace(0.05, 0.2, 4)

@creator_lib.define_task_template(
    left=__LEFT,
    height=__HEIGHT,
    blocks=__BLOCKS,
    base_width=__WIDTH,
    max_tasks=1,
    search_params=dict(max_search_tasks=1),
    version="3"
)
def build_task(C, left, height, blocks, base_width):

                   
    base = C.add('dynamic bar',
        scale=base_width,
        bottom=0,
        left=left*C.scene.width)
    for i in range(blocks):
        left = C.add(
            'dynamic bar',
            scale=1 / 32,
            angle=90,
            bottom=base.top,
            left=base.left)
        C.add(
            'dynamic bar',
            scale=1 / 32,
            angle=90,
            bottom=base.top,
            right=base.right)
        base = C.add(
            'dynamic bar', scale=base_width, bottom=left.top, left=base.left)

                                                     
    slope = C.add('static bar',
        scale=0.4,
        bottom=C.scene.height*height,
        angle=8.,
        right=C.scene.width*1.0,
    )
    block = C.add('static bar',
        scale=0.03,
        angle=90.,
        bottom=slope.bottom,
        left=slope.left)
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(left=block.right, bottom=block.top)

                                                      
    slope2 = C.add('static bar',
        scale=0.6,
        angle=10.,
        bottom=0.3*C.scene.height,
        left=base.right,
    )
    wall = C.add('static bar',
        scale=0.1,
        angle=90.,
        bottom=slope2.bottom,
        left=slope2.left,
    )

                                            
    guard = C.add('static bar',
        scale=0.15,
        top=C.scene.height,
        angle=90,
        center_x=C.scene.width/2.0)

                  
    C.update_task(
        body1=ball, body2=base, relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
