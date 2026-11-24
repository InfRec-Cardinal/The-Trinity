                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                             

import phyre.creator as creator_lib

__CENTER_XS = [0.05 * val for val in range(2, 5)]
__BOTTOM_YS = [0.05 * val for val in range(0, 5)]
__X_OFFSETS = [0.4, 0.45, 0.5]
__Y_OFFSETS = [-0.1, 0.0, 0.1]


@creator_lib.define_task_template(
    max_tasks=100,
    center_x=__CENTER_XS,
    bottom_y=__BOTTOM_YS,
    x_offset=__X_OFFSETS,
    y_offset=__Y_OFFSETS,
)
def build_task(C, center_x, bottom_y, x_offset, y_offset):

                           
    if bottom_y + y_offset < 0.0 or bottom_y + y_offset > 1.0:
        raise creator_lib.SkipTemplateParams

                   
    plateau1 = C.add('static bar', scale=0.2) \
                .set_center_x(center_x * C.scene.width) \
                .set_bottom(bottom_y * C.scene.height)
    plateau2 = C.add('static bar', scale=0.2) \
                .set_center_x((center_x + x_offset) * C.scene.width) \
                .set_bottom((bottom_y + y_offset) * C.scene.height)

               
    jar1 = C.add('dynamic jar', scale=0.2) \
            .set_center_x(center_x * C.scene.width) \
            .set_bottom(plateau1.top)
    jar2 = C.add('dynamic jar', scale=0.2) \
            .set_center_x((center_x + x_offset) * C.scene.width) \
            .set_bottom(plateau2.top)

                        
    C.update_task(body1=jar1,
                  body2=jar2,
                  relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.PRE_TWO_BALLS)
