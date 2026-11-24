                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                               
import numpy as np
import phyre.creator as creator_lib


@creator_lib.define_task_template(
    search_params=dict(require_two_ball_solvable=True),
    stick_length=np.linspace(0.2, 0.5, 10),
    stick1_x=np.linspace(0.05, 0.95, 19),
    stick2_x=np.linspace(0.05, 0.95, 19),
    version='2',
)
def build_task(C, stick_length, stick1_x, stick2_x):

                                                           
    if stick2_x <= stick1_x + 1.75 * stick_length:
        raise creator_lib.SkipTemplateParams
    if stick2_x > stick1_x + 2.5 * stick_length:
        raise creator_lib.SkipTemplateParams

                     
    bar1 = C.add('dynamic bar', scale=stick_length) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left(stick1_x * C.scene.width)
    bar2 = C.add('dynamic bar', scale=stick_length) \
            .set_angle(90.) \
            .set_bottom(0.) \
            .set_left(stick2_x * C.scene.width)

                                                                   
    C.add('static bar', scale=1.0) \
     .set_left(0.) \
     .set_bottom((stick_length + 0.25) * C.scene.height)

                  
    C.update_task(
        body1=bar1, body2=bar2, relationships=[C.SpatialRelationship.TOUCHING])
    C.set_meta(C.SolutionTier.TWO_BALLS)
