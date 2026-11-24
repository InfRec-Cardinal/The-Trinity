                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

                                  
    scene_width = C.scene.width
    scene_height = C.scene.height

                                
                                                                      
    C.add('static bar', scale=0.5) \
        .set_bottom(0.4 * scene_height) \
        .set_left(0.)
    C.add('static bar', scale=0.5) \
        .set_bottom(0.7 * scene_height) \
        .set_right(scene_width)
    C.add('dynamic jar', scale=0.2) \
        .set_angle(180.) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(0.)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(scene_width / 2., scene_height * 0.95)

                  
    C.update_task(body1=ball,
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
