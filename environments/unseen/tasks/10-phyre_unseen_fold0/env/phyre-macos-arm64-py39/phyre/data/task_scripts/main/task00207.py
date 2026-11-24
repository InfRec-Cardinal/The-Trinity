                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                   
import phyre.creator as creator_lib


@creator_lib.define_task
def build_task(C):

    scene_width = C.scene.width

    radius = 5

              
    jar = C.add(
        'dynamic jar',
        scale=2 / 1.2 * 4 * radius / scene_width,
        center_x=0.5 * scene_width,
        bottom=0)

                   
    obstacle = C.add(
        'static bar',
        scale=90 / scene_width,
        center_x=0.5 * scene_width,
        bottom=jar.top + radius * 4)

               
    ball = C.add(
        'dynamic ball',
        scale=radius / scene_width * 2,
        left=obstacle.left + 10,
        bottom=obstacle.top + radius)

               
    C.update_task(
        body1=ball,
        body2=jar,
        relationships=[C.SpatialRelationship.INSIDE],
        phantom_vertices=jar.phantom_vertices)
