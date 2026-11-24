                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width
    scene_height = C.scene.height

              
    jar = C.add('dynamic jar', scale=0.2, center_x=0.50 * scene_width, bottom=0)

                        
    C.add('static bar', scale=0.5) \
        .set_angle(-20.) \
        .set_bottom(0.3 * scene_height) \
        .set_right(1.01 * scene_width)
    C.add('static bar', scale=0.5) \
        .set_angle(20.) \
        .set_bottom(0.5 * scene_height) \
        .set_left(-0.01 * scene_width)

               
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(0.9 * scene_height)

                        
    C.update_task(body1=ball,
                  body2=jar,
                  relationships=[C.SpatialRelationship.INSIDE],
                  phantom_vertices=jar.phantom_vertices)
