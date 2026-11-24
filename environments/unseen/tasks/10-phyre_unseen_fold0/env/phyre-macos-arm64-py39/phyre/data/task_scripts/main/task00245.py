                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width
    scene_height = C.scene.height

                                                         
    bar1 = C.add('dynamic bar', scale=0.25) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(.3 * scene_width)
    bar2 = C.add('dynamic bar', scale=0.25) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(.7 * scene_width)

                   
    C.add('static bar', scale=0.6) \
        .set_center_x(0.5 * scene_width) \
        .set_bottom(0.5 * scene_height)

                  
    C.update_task(body1=bar1,
                  body2=bar2,
                  relationships=[C.SpatialRelationship.TOUCHING])
