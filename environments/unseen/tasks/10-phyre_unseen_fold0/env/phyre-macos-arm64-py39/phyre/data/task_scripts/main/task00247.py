                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width
    scene_height = C.scene.height

                     
    bar = C.add('static bar', scale=0.5) \
        .set_left(scene_width / 2.) \
        .set_bottom(scene_width / 2.)

                            
    cover = C.add('dynamic jar', scale=0.2) \
        .set_angle(180.0) \
        .set_left(scene_width / 2.) \
        .set_bottom(bar.top)

                        
    jar = C.add('dynamic jar', scale=0.2) \
        .set_center_x(scene_width / 4.) \
        .set_bottom(0.)
    phantom_vertices = jar.get_phantom_vertices()

                
    C.add('dynamic ball', scale=0.1) \
        .set_center_x(cover.left + cover.width / 2.) \
        .set_bottom(0.9 * scene_height)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center_x(cover.left + cover.width / 2.) \
        .set_bottom(bar.top)

                        
    C.update_task(body1=ball,
                  body2=jar,
                  relationships=[C.SpatialRelationship.INSIDE],
                  phantom_vertices=phantom_vertices)
