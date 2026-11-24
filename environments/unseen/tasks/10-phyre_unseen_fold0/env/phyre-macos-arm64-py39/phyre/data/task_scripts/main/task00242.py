                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib
import math


@creator_lib.define_task
def build_task(C):

                                
    scene_width = C.scene.width
    scene_height = C.scene.height

                                     
    stars = [
                            
        (.5, .3),
        (.5, .4),
        (.5, .5),
        (.5, .6),
        (.5, .7),
                          
        (.05, .05 + math.sqrt(.0)),
        (.13, .05 + math.sqrt(.01)),
        (.25, .05 + math.sqrt(.02)),
                           
        (.05, .95 - math.sqrt(.0)),
        (.13, .95 - math.sqrt(.01)),
        (.25, .95 - math.sqrt(.02)),
                             
        (.25, .5),
        (.75, .25),
        (.75, .75),
    ]
    for star in stars:
        C.add('static ball', scale=0.05) \
            .set_center(scene_width * star[1], scene_height * star[0])

                  
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

                  
    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
