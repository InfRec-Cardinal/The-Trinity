                                                  
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

import phyre.creator as creator_lib

import numpy as np


@creator_lib.define_task_template(
    seed=range(1000),
    version="2",
    search_params=dict(
        max_search_tasks=1000,
        reject_ball_solvable=True,
        require_two_ball_solvable=True,
    ),
)
def build_task(C, seed):
    rng = np.random.RandomState(seed=seed)

                                
    scene_width = C.scene.width
    scene_height = C.scene.height

                  
    center = rng.uniform(0.2, 0.8)
    ball = C.add('dynamic ball', scale=0.1) \
        .set_center(center * scene_width, 0.9 * scene_height)

    top = (ball.bottom - ball.height) / scene_height

                                     
    stars = []
                        
                                     
                                  
                             

    angle = 0
    stars = [(center, 0.7)]
    line_length = 1
    n_valid = 0
    while n_valid < 15:
        if line_length >= 3 and rng.uniform() < 0.5:
                               
                                       
            x = rng.normal()
            y = rng.normal()
            l = (x * x + y * y) ** .5
            x = x / l * 0.2 + 0.5
            y = y / l * 0.2 + 0.5
            line_length = 1
            angle = rng.uniform() * 2 * np.pi
        else:
            line_length += 1
            step = rng.uniform(0.05, 0.2)
            angle += rng.uniform() * 2 * np.pi / 8
            dx, dy = step * np.cos(angle), step * np.sin(angle)
            x, y = stars[-1]
            x += dx
            y += dy
        stars.append((x, y))
        if  0.0 < x < 1 and 0.0 < y < 1:
            n_valid += 1
    for i, (x, y) in enumerate(stars):
        C.add('static ball', scale=0.05) \
            .set_center(scene_width * x, scene_height * y)


                                    
                                          
                   
                              
                                                        
                                                       
                                      
                                                                

                  
    C.update_task(body1=ball,
                                       
                  body2=C.bottom_wall,
                  relationships=[C.SpatialRelationship.TOUCHING])
