                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

                                  
    scene_width = C.scene.width
    scene_height = C.scene.height

                            
    obstacle = C.add('static bar', scale=0.6) \
        .set_bottom(scene_height * 0.6) \
        .set_left(0.)

              
    jar = C.add('dynamic jar', scale=0.3) \
        .set_bottom(0.) \
        .set_left(scene_width / 2.)
    phantom_vertices = jar.get_phantom_vertices()

               
    ball = C.add('dynamic ball', scale=0.1)
    ball.set(
        left=obstacle.right - ball.width,
        bottom=obstacle.top + C.scene.height // 5)

                  
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=phantom_vertices)
