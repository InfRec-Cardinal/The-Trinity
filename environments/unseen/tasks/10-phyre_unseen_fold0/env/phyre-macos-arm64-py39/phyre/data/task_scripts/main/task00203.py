                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):
                                                                         
                       
     
                                                                     
                                                                        

    scene_width = C.scene.width
    fulcrum = C.add('static ball', scale=0.1)
    radius = fulcrum.width / 2
    fulcrum.set_left(scene_width / 2. - radius) \
        .set_bottom(0.)
    beam = C.add('dynamic bar', scale=0.35) \
        .set_center_x(scene_width / 2.) \
        .set_bottom(radius * 2.)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_left(beam.left) \
        .set_bottom(beam.top)

                                                                             
                                                                               
                                        
    C.update_task(body1=ball,
                  body2=fulcrum,
                  relationships=[C.SpatialRelationship.ABOVE])
