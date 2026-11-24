                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width
    scene_height = C.scene.height

    C.add('dynamic jar', scale=0.6) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(0.)

    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
