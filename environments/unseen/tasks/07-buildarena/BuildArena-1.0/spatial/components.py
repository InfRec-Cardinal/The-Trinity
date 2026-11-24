import os
from typing import List, Union, Any
import numpy as np
import quaternion

class Vector:
    def __init__(self, vector: Union[List[float], np.ndarray, "Vector"]):
        if isinstance(vector, Vector):
                        
            self._data = vector._data
        else:
                                                                     
            arr = np.array(vector, dtype=np.float64)
            self._data = arr.reshape(-1) if arr.size == 3 else arr
            
    @classmethod
    def from_real(cls, vector: List[float]):
        pass                                                                                              
        return cls([vector[0], vector[2], vector[1]])
    
    @property
    def virtual(self) -> np.ndarray:
        pass                                           
        return self._data
    
    @property
    def real(self) -> np.ndarray:
        pass                                                        
        return self._data[[0, 2, 1]]                          
    
    @property
    def norm(self):
        pass                    
        norm_value = np.linalg.norm(self.virtual)
        if norm_value == 0:
            return Vector(self.virtual)                            
        
        norm_vector = Vector(self.virtual / norm_value)
        return norm_vector
    
    @property
    def caption(self):
        pass                                                                 
        return describe_orientation(self)
    
    @property
    def coordinates(self):
        pass                                                                 
        return np.array2string(self.real, precision=2, separator=',', suppress_small=True)

class Orientation:
    def __init__(self, rot: Union[List[float], Any]=[1, 0, 0, 0], vec_base: Vector=Vector([0, 0, 1])):
        pass                                
                                                                                   
                                                                                         
                                                                                               
           
        self.vec_base = vec_base
        if isinstance(rot, quaternion.quaternion):
            self.quat = rot
        elif isinstance(rot, List) or isinstance(rot, np.ndarray):
            if len(rot) == 3:                           
                rot = Vector(rot).norm
                self.quat = self.rel_quat(rot)
        
            elif len(rot) == 4:                              
                self.quat = quaternion.from_float_array(rot)
        
        else:
            raise ValueError("Input array must be of shape (3,) for vector or (4,) for quaternion.")
            
        self.rot_mat = quaternion.as_rotation_matrix(self.quat)
    
    def rel_quat(self, rot: Vector) -> quaternion:
        pass                                                  
        if np.allclose(rot.virtual, 0):                             
            return np.quaternion(1, 0, 0, 0)                       
    
        dot_prod = np.dot(self.vec_base.virtual, rot.virtual)
        
        if np.isclose(dot_prod, -1.0):
                                                                          
            if np.abs(self.vec_base.virtual[0]) < 0.1:
                perp_axis = np.array([1, 0, 0])
            else:
                perp_axis = np.array([0, 1, 0])
            
            perp_axis = perp_axis - np.dot(perp_axis, self.vec_base.virtual) * self.vec_base.virtual                             
            perp_axis /= np.linalg.norm(perp_axis)                

                                                                                                  
            quat = np.quaternion(0, *perp_axis)
        else:
            cross_prod = np.cross(self.vec_base.virtual, rot.virtual)
            
            quat = np.quaternion(1 + dot_prod, *cross_prod)
        quat = quat.normalized()                            
        return quat
    
    @property
    def vec_abs(self) -> Vector:
        pass                                               
        quat = self.quat.normalized()

                                                          
        vec_abs = quaternion.as_rotation_matrix(quat) @ self.vec_base.virtual
        return Vector(vec_abs)
    
    @property
    def euler(self) -> Vector:
        pass                                                                                       
        return Vector(np.degrees(quaternion.as_euler_angles(self.quat)) + [270, 0, 0])
        
    def rotate(self, R):
        pass                                                                         
        if R.shape != (3, 3):
            raise ValueError("Rotation matrix R must be of shape (3, 3)")
        
                                                                  
        new_rot_mat = R @ self.rot_mat  
        
        self.quat = quaternion.from_rotation_matrix(new_rot_mat)
        self.rot_mat = new_rot_mat
        
        return self
    
    @property
    def caption(self):
        pass                                                                 
        return self.vec_abs.caption
        
class Geometry:
    def __init__(self, vec_base: List, shape: List, root: List, scale: List | None = None):
        self.position = Vector([0, 0, 0])
        self.rotation = Orientation(vec_base=Vector(vec_base))
        self.scale = Vector(np.array([1, 1, 1])) if scale is None else Vector(scale)
        self.shape = Vector(shape)
        self.root = Vector(root)
        
    @property
    def caption(self):
        pass                                                              
        return f"{np.array2string(self.position.real, precision=2, separator=',', suppress_small=True)}"
        
class Face:
    def __init__(self, color: str, rel_pos: List, face_normal: List, block_geo: Geometry, local_id: int, name: str):
        pass                 
                                                
                                                                                                  
                                                          
                                                      
                                                                 
                                                    
           
        self.color = color
        self.rel_pos = Vector(rel_pos)
        self.face_normal = Vector(face_normal)
        self.block_geo = block_geo
        self.sticky: bool = True
        self.att_to: Face = None
                                                                
        self.local_id = local_id
        self.name = name
        
    def update_block_geo(self, block_geo: Geometry):
        pass                           
        self.block_geo = block_geo
    
    @property
    def caption(self):
                                                                                                                                                                                                                                                                                      
        return str(f'Face label: {self.color}, Face center: {np.array2string(self.center.real, precision=3, separator=", ", suppress_small=True)}, Facing towards {self.normal.caption}')
    
    @property
    def center(self) -> Vector:
        center = Vector(self.block_geo.rotation.rot_mat @ (self.rel_pos.virtual * self.block_geo.shape.virtual) + self.block_geo.position.virtual)
        return center
    
    @property
    def normal(self) -> Orientation:
        normal = Orientation(rot = self.face_normal.virtual, vec_base = self.block_geo.rotation.vec_base).rotate(self.block_geo.rotation.rot_mat)
        return normal
        
def describe_orientation(vector: Vector) -> str:
    pass                                                               
    
               
                                                     

            
                                                  
       
    x, y, z = vector.norm.real
    
                                                                                
    threshold = 1e-6
    if abs(x) < threshold and abs(y) < threshold:
        if z > 0:
            return "<straight up>"
        elif z < 0:
            return "<straight down>"

                                                   
    azimuth_rad = np.arctan2(x, y)                                          
    azimuth_deg = np.degrees(azimuth_rad) % 360                                          

                                    
    r = np.sqrt(x**2 + y**2)                        
    pitch_rad = np.arctan2(z, r)
    pitch_deg = np.degrees(pitch_rad)

                                                                           
    if azimuth_deg % 90 <= 1e-6 or abs(azimuth_deg % 90 - 90) <= 1e-6:
                                             
        azimuth_deg = round(azimuth_deg / 90) * 90
                                   
        directions = [
            "North", "East", "South", "West"
        ]
        index = int(azimuth_deg // 90) % 4
        compass_direction = directions[index]
        direction_text = compass_direction
    else:
                                   
        directions = [
            "N {deg:.1f}° E", "E {deg:.1f}° S", "S {deg:.1f}° W", "W {deg:.1f}° N"
        ]
        index = int(azimuth_deg // 90) % 4                            
        azimuth_deg = azimuth_deg % 90                           
        direction_text = directions[index].format(deg=azimuth_deg)

    return f"<{direction_text} with {pitch_deg:.1f}° pitch>"

def angle_between_vectors(a: Vector, b: Vector) -> float:
    pass                                                                                            
    a = a.real
    b = b.real
                             
    dot_product = np.dot(a, b)
                                    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
                                     
    cos_theta = dot_product / (norm_a * norm_b)
                                
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
                                  
    angle_rad = np.arccos(cos_theta)
                                  
    angle_deg = np.degrees(angle_rad)
    
    return angle_deg

def describe_spin(rotation_vector: Vector) -> str:
    pass                                                                                                                                                        
    
               
                                                                                                                                       

            
                                                                                 
       
    rotation_array = rotation_vector.real
    gravity = np.array([0, 0, -1], dtype=np.float64)

                                           
    alpha_deg = angle_between_vectors(rotation_array, gravity)
    tilt_angle_deg = 90.0 - alpha_deg

                               
    rolling_array = np.cross(rotation_array, gravity)
                                                                                                                      
    rolling_vector = Vector(Vector(rolling_array).real)

                     
    if abs(tilt_angle_deg) < 60:  
        return f"Rolling towards {rolling_vector.caption} with {tilt_angle_deg:.0f}° camber"
                       
    else: 
        direction = "counterclockwise" if rotation_array[2] > 0 else "clockwise"
        return f"Almost horizontal spinning {direction} around with the axis pointing at {rotation_vector.caption}"
                                                                                                                  
        
def main():
    rotation_vector = Vector([1, 0, 0])
    print(rotation_vector.real)
    des = describe_spin(rotation_vector)
    print(des)
    
if __name__ == "__main__":
    main()