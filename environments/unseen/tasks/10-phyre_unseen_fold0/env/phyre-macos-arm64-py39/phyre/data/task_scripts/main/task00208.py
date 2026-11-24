                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width
    scene_height = C.scene.height

              
    target_jar = C.add('dynamic jar', scale=0.2) \
        .set_center_x(0.25 * scene_width) \
        .set_bottom(0.)
    phantom_vertices = target_jar.get_phantom_vertices()

                     
    bar = C.add('static bar', scale=0.1) \
        .set_left(0.33 * scene_width) \
        .set_bottom(0.25 * scene_height)
    C.add('static bar', scale=0.1) \
        .set_left(0.33 * scene_width + bar.width) \
        .set_bottom(0.25 * scene_height + 4. * bar.height)

                   
    platform = C.add('static bar', scale=0.5) \
        .set_left(0.33 * scene_width + 2. * bar.width) \
        .set_bottom(0.25 * scene_height + 8. * bar.height)

                     
    source_jar = C.add('dynamic jar', scale=0.2) \
        .set_bottom(platform.top) \
        .set_left(platform.left)

               
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(source_jar.left + 0.5 * source_jar.width, 0.) \
        .set_bottom(source_jar.bottom + 0.02 * scene_height)

                  
    C.update_task(
        body1=ball,
        body2=target_jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
