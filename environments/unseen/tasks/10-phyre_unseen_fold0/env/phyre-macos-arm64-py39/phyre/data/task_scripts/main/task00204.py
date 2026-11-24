                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

                   
    base_width = 0.1
    base = C.add('dynamic bar', scale=base_width).set(bottom=0, left=5)
    for i in range(5):
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

                  
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(left=ball.width / 2, bottom=base.top + 20)

                  
    C.update_task(
        body1=ball, body2=base, relationships=[C.SpatialRelationship.LEFT_OF])
