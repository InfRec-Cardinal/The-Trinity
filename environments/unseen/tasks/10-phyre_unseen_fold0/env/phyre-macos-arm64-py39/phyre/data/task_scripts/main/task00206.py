                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):
                                                                          
                      

                                  
    scene_width = C.scene.width
    scene_height = C.scene.height

                                 
    C.add('static bar', scale=0.6) \
        .set_bottom(0.5 * scene_height) \
        .set_left(0.)
    C.add('static bar', scale=0.6) \
        .set_bottom(0.7 * scene_height) \
        .set_right(scene_width)
    C.add('static bar', scale=0.7) \
        .set_bottom(0.3 * scene_height) \
        .set_left(0.5 * scene_width)

               
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(0.5 * scene_width, 0.9 * scene_height)

                             
    beam1 = C.add('dynamic bar', scale=0.2) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(0.8 * scene_width)

                     
    C.add('dynamic bar', scale=0.2) \
        .set_angle(90.) \
        .set_bottom(0.) \
        .set_left(0.2 * scene_width)

                  
    C.update_task(body1=beam1,
                  body2=ball,
                  relationships=[C.SpatialRelationship.TOUCHING])
