import os
from typing import Annotated, List, Dict, Literal, Union, Any
import yaml
import uuid
import json
import numpy as np
import quaternion
import copy
import importlib
import types
from datetime import datetime
import re

from pathlib import Path

import trimesh
from trimesh.collision import CollisionManager
from trimesh import Trimesh

from .components import Vector, Geometry, describe_spin, Orientation
from .utils import *

block_list = os.listdir('./blocks/configs')
all_blocks = {}
for filename in block_list:
    if filename.endswith('.yaml'):
        with open(os.path.join('./blocks/configs', filename), 'r', encoding='utf-8') as file:
            block_data = yaml.safe_load(file)
        all_blocks[block_data['name']] = block_data

AvailableBlocks = [key for key, value in all_blocks.items() if value['type'] in ['basic', 'pointer'] and key != 'Starting Block' and not value['disable']]
WaiveableBlocks = ['Ballast']
AvailableConnectors = [key for key, value in all_blocks.items() if value['type'] == 'connection' and not value['disable']]
AvailableKeys = [
    'UpArrow', 'DownArrow', 'LeftArrow', 'RightArrow', 
    'Alpha0 to Alpha9, for example, Alpha1', 
    'Keypad0 to Keypad9, for example, Keypad1', 
    ]

class Block:
                                                                                       
    def __init__(self, block_dict: Dict, local_id: str, start_point: Face, collider_scale: int = 0.8, note: str = None):
        self.id = str(block_dict['id'])
        self.local_id = local_id
        self.name: str = block_dict['name']
        self.type: str = block_dict['type']
        
        self.geo = Geometry(block_dict['vec_base'], block_dict['shape'], block_dict['root'], block_dict['scale'] if 'scale' in block_dict.keys() else None)
        self.root = Vector(block_dict['root'])
        self.center_offset: float = block_dict['center_offset']
        self.start_point = start_point
        if self.start_point is not None:
            self.geo.position = self.start_point.center
            self.geo.rotation = Orientation(rot=self.start_point.normal.quat, vec_base=Vector(block_dict['vec_base']))
        
        self.wiki: str = block_dict['wiki']
        self.description: str = block_dict['description']
        self.note: str = note
        
                  
        self.collider_dict = block_dict['collider']
        self.outline_dict = block_dict['outline']
        self.collider_scale = collider_scale
        self.init_collider()
        
                          
        self.init_faces(block_dict['faces'])
        
                                                                            
        self.spin: Dict = block_dict['spin'] if 'spin' in block_dict else None
        self.flipped = False
        
                         
        self.shoot: Dict = block_dict['shoot'] if 'shoot' in block_dict else None
        
                    
        self.locomotion: Dict[str, List[str]] = block_dict['locomotion']
        self.data: str = block_dict['data']
        
                            
        self.end_point: Face = None
        self.projection: Vector = None
        
                               
        descriptor = block_dict['descriptor'] if 'descriptor' in block_dict else None
        if descriptor:
            try:
                module = importlib.import_module(f"blocks.descriptors.{descriptor}")
                if hasattr(module, 'descriptor'):
                    self.descriptor = types.MethodType(module.descriptor, self)
                else:
                    raise AttributeError(f"No 'descriptor' function in {descriptor}.py")
            except ModuleNotFoundError:
                raise ImportError(f"Descriptor module '{descriptor}' not found.")
        else:
            self.descriptor = None
        
              
        self.cost = block_dict['cost']

                    
        self.tracking = False
        self.change_mass = False
        self.guid = str(uuid.uuid4())
        if self.name == "Small Wooden Block":
            ref_name = "Single Wooden Block"
        elif self.name == "Powered Wheel":
            ref_name = "Wheel"
        else:
            ref_name = self.name
        self.ref_key = f"{ref_name.replace(' ', '').replace('_', '')}_{self.guid.split('-')[0]}"
    
    @property
    def center_pos(self) -> Vector:
        if self.start_point is None:
                            
            return self.geo.position
                      
        return Vector.from_real(self.start_point.center.real + self.center_offset * self.start_point.normal.vec_abs.real)

    def caption(self, finished=False, prefix: str = None):
        pass                                      
        message = []
        if self.note:
            message.append(f'({self.note}) <ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'({self.note}) <ID {self.local_id}: {self.name}>')
        else:
            message.append(f'<ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'<ID {self.local_id}: {self.name}>')
        message.append(f'Position: {self.center_pos.coordinates}')
        
        if self.descriptor:
            description = self.descriptor()
            message.append(description)
        
        if self.spin:
                                                                
            rotation_vector = Vector(self.spin['rel'] * (1 + (-2 * self.flipped)) * self.faces[self.spin['parallel_to']].normal.vec_abs.virtual)
            message.append(describe_spin(rotation_vector))
        
        if not finished and len([face for face in self.faces.values() if face.sticky]) > 0:
            message.append('Attachable Faces:')
            for face in self.faces.values():
                if face.sticky:
                    message.append(face.caption) 
        
        message = '\n'.join(message)
        return str(message)
    
    def init_faces(self, dict: Dict):
                                           
        self.faces : Dict[str, Face] = {} 
        if dict is not None:
            for name, face in dict.items():
                self.faces[name] = Face(name, face[0], face[1], self.geo, self.local_id, self.name)
    
    def init_collider(self):
                       
        collider = self.collider_dict
        outline = self.outline_dict
        collider_list = []
        outline_list = []
        if collider['type'] == 'box':
            for extent in collider['extents']:
                collider_list.append(trimesh.creation.box(extents=extent))
            for extent in outline['extents']:
                outline_list.append(trimesh.creation.box(extents=extent))
        elif collider['type'] == 'cylinder':
                collider_list.append(trimesh.creation.cylinder(radius=collider['radius'], height=collider['height']))
                outline_list.append(trimesh.creation.cylinder(radius=outline['radius'], height=outline['height']))
        translation = Vector(self.collider_dict['translation']) if 'translation' in self.collider_dict else Vector([0, 0, 0])
        translation = self.root.virtual + translation.virtual
        self.collider: Trimesh = copy.deepcopy(trimesh.util.concatenate(collider_list)).apply_translation(translation).apply_scale(self.collider_scale)
        self.outline: Trimesh = copy.deepcopy(trimesh.util.concatenate(outline_list)).apply_translation(translation)
        self.update_collider()
        
    def update_collider(self):
                                          
        T = np.eye(4)
        T[:3, :3] = self.geo.rotation.rot_mat
        T[:3, 3] = self.geo.position.virtual
        self.collider.apply_transform(T)
        self.outline.apply_transform(T)
    
    def update_faces(self):
                           
        for face in self.faces.values():
            face.update_block_geo(self.geo)
            
    def rotate(self, yaw, pitch, roll):
        pass                                                                 
        R = rotation_matrix(yaw, pitch, roll)
        self.geo.rotation = self.geo.rotation.rotate(R)
                             
        self.init_collider()
                          
        self.update_faces()
    
    def twist(self, angle: float):
        pass                                                                             
                                                   
        angle = np.mod(angle, 360)
        if angle > 180:
            angle -= 360
                                     
        angle = np.deg2rad(angle)
                                     
        norm = self.start_point.normal.vec_abs.norm
        axis_angle_quat = quaternion.from_rotation_vector(angle * norm.virtual)
                                                                   
        R = quaternion.as_rotation_matrix(axis_angle_quat)
                                     
        self.geo.rotation = self.geo.rotation.rotate(R)
                             
        self.init_collider()
                          
        self.update_faces()
        
    def shift(self, shift_real: List):
        pass                                                 
        shift = Vector.from_real(shift_real)
        pos_old = self.geo.position.virtual
        pos_new = pos_old + shift.virtual
        self.geo.position = Vector(pos_new)
                             
        self.init_collider()
                          
        self.update_faces()
        
                     
    @property
    def caption_locomotion(self, prefix: str = None):
        if self.locomotion:
            caption = [self.caption(finished=True, prefix=prefix)]
            caption.append('Controllable Locomotion: ')
            for key, value in self.locomotion.items():
                caption.append(f'Action: {key}, Key: {", ".join(value)}')
            return '\n'.join(caption)
        else:
            return None
    
    def change_control_key(self, action: str, key: str):
        pass                             
        self.locomotion[action].append(key)
    
                    
    def to_xml(self, indent_level = 0):
        indent = '    ' * indent_level
        lines = []
                                                                
        lines.append(f'{indent}<Block id="{self.id}" guid="{self.guid}">')
                           
        lines.append(f'{indent}    <Transform>')
        pos = self.geo.position.virtual
        lines.append(f'{indent}        <Position x="{pos[0]}" y="{pos[1]}" z="{pos[2]}" />')
        rot = self.geo.rotation.quat
        lines.append(f'{indent}        <Rotation x="{rot.x}" y="{rot.y}" z="{rot.z}" w="{rot.w}" />')
        scale = self.geo.scale.virtual
        lines.append(f'{indent}        <Scale x="{scale[0]}" y="{scale[1]}" z="{scale[2]}" />')
        lines.append(f'{indent}    </Transform>')
                                                                              
        lines.append(f'{indent}    <Data>')
        if self.spin:
            spinning_forward = "".join(f"<String>{key}</String>" for key in set(self.locomotion['spinning_forward']))
            spinning_backward = "".join(f"<String>{key}</String>" for key in set(self.locomotion['spinning_backward']))
            data = self.data.format(
                flipped = self.flipped, 
                spinning_forward = spinning_forward, 
                spinning_backward = spinning_backward)
            for line in data.split('\n'):
                lines.append(f'{indent}        {line}')
        elif self.shoot:
            data = self.data.format(
                hold_to_fire = "".join(f"<String>{key}</String>" for key in set(self.locomotion['hold_to_fire']))
                )
            for line in data.split('\n'):
                lines.append(f'{indent}        {line}')
        elif self.end_point:
            data = self.data.format(
                end_x = self.projection.virtual[0], 
                end_y = self.projection.virtual[1], 
                end_z = self.projection.virtual[2],
                start_r_x = self.start_point.normal.euler.virtual[0],
                start_r_y = self.start_point.normal.euler.virtual[1],
                start_r_z = self.start_point.normal.euler.virtual[2],
                end_r_x = self.end_point.normal.euler.virtual[0],
                end_r_y = self.end_point.normal.euler.virtual[1],
                end_r_z = self.end_point.normal.euler.virtual[2]
                )
            for line in data.split('\n'):
                lines.append(f'{indent}        {line}')
        else:
            lines.append(f'{indent}        {self.data}')
        lines.append(f'{indent}        <String key="bmt-lua_module">default</String>')
        lines.append(f'{indent}        <String key="bmt-lua_ref_key">{self.ref_key}</String>')
        lines.append(f'{indent}    </Data>')
        lines.append(f'{indent}</Block>')
        return lines
    
class Connector(Block):
                                                                       
    def __init__(self, block_dict: Dict, local_id, start_point: Face = None, end_point: Face = None, note: str = None):
        super().__init__(block_dict, local_id, start_point, note=note)
        self.end_point = end_point
                                       
        projection_global = self.end_point.center.virtual - self.start_point.center.virtual
                                                                                       
        R = self.start_point.normal.rot_mat
        self.projection = Vector(R.T @ projection_global)
        self.outline = create_connector_mesh(
            point_a=self.start_point.center.virtual,
            point_b=self.end_point.center.virtual)
    
    def caption(self, finished, prefix: str = None):
        message = []
        if self.note:
            message.append(f'({self.note}) <ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'({self.note}) <ID {self.local_id}: {self.name}>')
        else:
            message.append(f'<ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'<ID {self.local_id}: {self.name}>')
        message.append(
            f'Connecting <ID {self.start_point.local_id}: {self.start_point.name}> at {self.start_point.center.real} and <ID {self.end_point.local_id}: {self.end_point.name}> at {self.end_point.center.real}.\t' 
            )
        
        if self.descriptor:
            description = self.descriptor()
            message.append(description)
            
        message = '\n'.join(message)
        return str(message)
    
class Pointer(Block):
                                                                                                    
    def __init__(self, block_dict: Dict, local_id, start_point: Face = None, note: str = None):
        super().__init__(block_dict, local_id, start_point, note=note)
        
    def caption(self, finished, prefix: str = None):
        message = []
        if self.note:
            message.append(f'({self.note}) <ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'({self.note}) <ID {self.local_id}: {self.name}>')
        else:
            message.append(f'<ID {prefix}_{self.local_id}: {self.name}>' if prefix else f'<ID {self.local_id}: {self.name}>')
        message.append(f'Position: {self.center_pos.coordinates}')
        message.append(f'Pointing at {self.geo.rotation.vec_abs.caption}')
        
        if self.descriptor:
            description = self.descriptor()
            message.append(description)

        message = '\n'.join(message)
        return str(message)
    
class Blocks:
                                                 
    def __init__(self):
        block_list = os.listdir('./blocks/configs')
        self.blocks: Dict[str, Dict] = {}
        for filename in block_list:
            if filename.endswith('.yaml'):
                with open(os.path.join('./blocks/configs', filename), 'r', encoding='utf-8') as file:
                    block_data = yaml.safe_load(file)
                self.blocks[block_data['name']] = block_data

        self.available_blocks = [key for key, value in self.blocks.items() if (value['type'] == 'basic' or value['type'] == 'pointer') and key != 'Starting Block']
        self.available_connectors = [key for key, value in self.blocks.items() if value['type'] == 'connection']
        
    def __call__(self):
                                                                   
        message = []
        message.append(f"\n{len(self.available_blocks) - len(WaiveableBlocks)} kinds of available blocks: ")
        for key in self.available_blocks:
            if self.blocks[key]["disable"]:
                continue
            message.append(f'<{key}> shape: {self.blocks[key]["shape"]}, mass: {self.blocks[key]["weight"]}')
            message.append(f'Description: {self.blocks[key]["description"]}')
        message.append(f"\n{len(self.available_connectors)} kinds of available connectors: ")
        message.append(f'Important: Connectors can not be attached to other blocks, it can only be used to connect two blocks. Connectors does not have physical volume nor collider.')
        for key in self.available_connectors:
            if self.blocks[key]["disable"]:
                continue
            message.append(f'<{key}> mass: {self.blocks[key]["weight"]}')
            message.append(f'Description: {self.blocks[key]["description"]}')
        
        message = '\n'.join(message)
        return str(message)
    
    def get(self, block_name: str, local_id: str, start_point: Face = None, end_point: Face = None, note: str = None):
                                               
        block_data = self.blocks.get(block_name)
        if block_data['type'] == 'connection':
            block = Connector(block_data, local_id, start_point=start_point, end_point=end_point, note=note)
        elif block_data['type'] == 'basic':
            block = Block(block_data, local_id, start_point=start_point, note=note)
        elif block_data['type'] == 'pointer':
            block = Pointer(block_data, local_id, start_point=start_point, note=note)
        return block

class Machine:
                                                                                      
    def __init__(self, 
                 name: str | None = None, 
                 save_dir: str = './datacache/default/machine', 
                 note: str | None = None, 
                 assembly: bool = False, 
                 sub_structure: bool = False,
                 db_path: str | None = None, 
                 do_collision: bool = True):
        self.name = name
        self.save_dir = save_dir
        self.note = note
        self.db_path = os.path.join("datacache", "default", name) if not db_path else db_path
        
        self.blocks_storage = Blocks()
        
                                          
        self.do_collision = do_collision
        self.collision_manager = CollisionManager()
        
                           
        self.blocks: Dict[str, Block] = {}
        self.operation_history = []
        self.full_op_history_path = os.path.join(os.path.dirname(self.db_path), "machine", self.name, f"{self.name}_full.json")
        self.init_full_op_history()
        self.uid = 1
        self.assembly = assembly
        self.sub_structure = sub_structure
        self.machines: Dict[str, Machine] = {}
        
                          
        self.control_sequence = []
        
                             
        self.record_op = False
        self.operations = {}
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if callable(attr) and getattr(attr, "_is_operation", False):
                self.operations[attr_name] = attr
        self.tools = {}
        self.started = False

        for operation in self.operations.values():
            if operation._group not in self.tools.keys():
                self.tools[operation._group] = []
            self.tools[operation._group].append(operation)
            
        self.local_index = None
            
    def log_failed_operation(self, func_name: str, message: str):
        self.operation_history_full.append({
            "op": "failed",
            "params": {"func_name": func_name, "message": message}
        })
        self.save_full_op_history()
    
    @property
    def cost(self):
        return sum([block.cost for block in self.blocks.values()])
    
    @property
    def num_blocks(self):
        return len(self.blocks)

    @property
    def has_spinful(self):
        return any([block.spin for block in self.blocks.values()])

    def add_collider(self, block: Block):
        if not isinstance(block, Connector):
            self.collision_manager.add_object(block.local_id, block.collider)
        else:
            pass
    
    def clean_colliders(self):
        obj_names = [name for name in self.collision_manager._objs.keys()]
        for obj in obj_names:
            self.collision_manager.remove_object(name=obj)
        
    def refresh_colliders(self):
        pass                                                                      
        self.clean_colliders()
        for block in self.blocks.values():
            self.add_collider(block)
            
    def refresh_collider(self, block: Block):
        pass                                                                            
                                                     
        if block.local_id in self.collision_manager._objs.keys():
                                                                
            self.collision_manager.remove_object(block.local_id)
                                                        
        self.add_collider(block)

    @operation(group="build_only")
    def start(self, init_shift: List[float] = [0, 0, 0], init_rotation: List[float] = [0, 0, 0], note: str = None):
        pass                                                                                  
        
             
                                                                                           
                                                                                       
                                                                       
            
                
                                                        
           
        if self.started:
            error_message = "Machine already exists"
            self.update_prompt(pre_msg=error_message, complete=True, return_summary=True)
            self.log_failed_operation("start", error_message)
            return self.prompt
        starting_block = self.blocks_storage.get('Starting Block', '1', start_point=None, note="The starting block")
        starting_block.shift(init_shift)
        starting_block.rotate(init_rotation[0], init_rotation[1], init_rotation[2])
        collision_msg = self._add_block(starting_block)
        self.record_op = True
        self.started = True
        self.note = note
        
        return self.prompt

    @operation(group="build")
    def reset(self):
        pass                                                                  
        
             
                
            
                
                
           
        self.save_full_op_history()
        self.__init__(name=self.name, 
                      save_dir=self.save_dir, 
                      note=self.note, 
                      assembly=self.assembly, 
                      sub_structure=self.sub_structure, 
                      db_path=self.db_path,
                      do_collision=self.do_collision)
        return "The machine has been reset, please start again."

    def update_prompt(self, pre_msg = None, complete = False, return_summary = False, locomotion = False, prefix: str = None, assembly_only: bool = False):
        pass                                          
        
             
                                                                       
                                                                                                                                                                                                                      
                                                                                                                          
           
        message = []
        if pre_msg:
            message.append(pre_msg)
            
        if locomotion:
            message.append(self.review_powered_blocks())
        
        if return_summary:
            message.append(f'Existing Blocks: {len(self.blocks)}')
            if complete:
                message.append(f'\nMachine Summary: {self.note}')
                for block in self.blocks.values():
                    message.append(block.caption(finished = complete, prefix = prefix))
            elif not (self.assembly and assembly_only):
                                                     
                                                                                       
                                                                              
                if assembly_only:
                    max_uid = [key for key in self.blocks.keys()][0]                 
                else: 
                    max_uid = [key for key in self.blocks.keys()][-1]
                message.append(self.blocks[str(max_uid)].caption(finished = complete, prefix = prefix))
            elif assembly_only:
                message.append(f'Existing Machines: {len(self.machines)}')
                for key, machine in self.machines.items():
                    machine.update_prompt(complete=complete, return_summary=True, locomotion=locomotion, prefix=key, assembly_only=True)
                    message.append(machine.prompt)
        self.prompt = '\n'.join(message)
    
    @operation(log=False)
    def get_machine_summary(self):
        pass                                                                                                       
                                                                                               
                                                                                                                                                    
        
             
                
            
                
                                                
           
        self.update_prompt(complete=True, return_summary=True)
        return self.prompt
    
    @operation(log=False)
    def get_block_details(self, block_id: Union[str, int]):
        pass                                                                                                         
        
             
                                                                          

                
                                         
           
        if isinstance(block_id, int):
            block_id = str(block_id)
        if block_id in self.blocks.keys():
            return self.blocks[block_id].caption(finished=False)
        else:
            return f"Block {block_id} not found"

                   
    def shift(self, shift_real: List):
        pass                                                       
        
             
                                                             
            
                
                
           
        shift = Vector.from_real(shift_real)
        for i, op in enumerate(self.operation_history):
            if op['params'].get('init_shift') is not None:
                shift_old: List[float] = self.operation_history[i]['params']['init_shift']
                shift_new = shift_old + shift.virtual
                self.operation_history[i]['params']['init_shift'] = shift_new.tolist()
        
        self.rebuild_from_history(self.operation_history)
        self.record_op = False
        
    def rotate(self, yaw, pitch, roll):
        pass                                                                      
        
             
                                                          
                                                            
                                                           
            
                
                
           
        R = rotation_matrix(yaw, pitch, roll)
        for i, op in enumerate(self.operation_history):
            if op['params'].get('init_rotation') is not None:
                rot_old: List[float] = self.operation_history[i]['params']['init_rotation']
                R_old = rotation_matrix(rot_old[0], rot_old[1], rot_old[2])
                R_new = R @ R_old
                rot_new = [
                    np.degrees(np.arctan2(R_new[1,0], R_new[0,0])),       
                    np.degrees(np.arcsin(-R_new[2,0])),          
                    np.degrees(np.arctan2(R_new[2,1], R_new[2,2]))         
                ]
                self.operation_history[i]['params']['init_rotation'] = [rot_new[1], rot_new[2], -rot_new[0]]
        
        self.rebuild_from_history(self.operation_history)
        self.record_op = False

                          
    def _add_block(self, block: Block, return_summary=True, replacing=False):
        pass                                                      
        self.blocks[str(self.uid)] = block
        
        self.add_collider(block)

                                                    
        collision_msg = self.collision_detect() if self.do_collision else None

        if collision_msg:
                                     
            self._remove_block(block.local_id)
            self.update_prompt(pre_msg=collision_msg)
        else:
            self.record_op = True
            if not replacing:
                                                                                                
                                                    
                self.update_prompt(pre_msg=f"You have successfully added <ID {block.local_id}: {block.name}>.", 
                                return_summary=return_summary, 
                                complete=False)
                self.uid += 1
        
        return collision_msg
        
    @operation(placeholder=AvailableConnectors, group="build")
    def connect_blocks(self, block_a: Union[str, int], face_a: str, block_b: Union[str, int], face_b: str, connector: str, note: str = None):
        pass                                              
                                                                                           
                                                                                                                          
        
             
                                                            
                                                                 
                                                             
                                                                
                                                                                           
                                                                           
            
                
                                                              
           
        if connector in AvailableBlocks:
            self.update_prompt(pre_msg="Basic blocks can not be used as connectors, please try again.")
            return self.prompt
        if isinstance(block_a, int):
            block_a = str(block_a)
        if isinstance(block_b, int):
            block_b = str(block_b)
        if block_a in self.blocks.keys() and block_b in self.blocks.keys():
            block_a: Block = self.blocks.get(block_a)
            block_b: Block = self.blocks.get(block_b)
            
                                                               
            if face_a in block_a.faces.keys() and face_b in block_b.faces.keys():
                face_a: Face = block_a.faces.get(face_a)
                face_b: Face = block_b.faces.get(face_b)
                if np.linalg.norm(face_a.center.virtual - face_b.center.virtual) < 0.01:
                    error_message = "The two faces are too close to each other, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("connect_blocks", error_message)
                    return self.prompt
                else:
                                                 
                    local_id = str(self.uid)
                    connector: Connector = self.blocks_storage.get(connector, local_id, start_point=face_a, end_point=face_b, note=note)
                    collision_msg = self._add_block(block=connector)
                    if collision_msg:
                        error_message = collision_msg
                        self.update_prompt(pre_msg=error_message)
                        self.log_failed_operation("connect_blocks", error_message)
                        return self.prompt
            elif face_a not in block_a.faces.keys():
                if len(block_a.faces.keys()) == 0:
                    error_message = f"Block {block_a.local_id} {block_a.name} does not have any faces, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("connect_blocks", error_message)
                    return self.prompt
                else:
                    error_message = f"Block {block_a.local_id} {block_a.name} does not have face {face_a}, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("connect_blocks", error_message)
                    return self.prompt
            elif face_b not in block_b.faces.keys():
                if len(block_b.faces.keys()) == 0:
                    error_message = f"Block {block_b.local_id} {block_b.name} does not have any faces, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("connect_blocks", error_message)
                    return self.prompt
                else:
                    error_message = f"Block {block_b.local_id} {block_b.name} does not have face {face_b}, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("connect_blocks", error_message)
                    return self.prompt
        elif block_a not in self.blocks.keys():
            error_message = f"Block {block_a} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("connect_blocks", error_message)
            return self.prompt
        elif block_b not in self.blocks.keys():
            error_message = f"Block {block_b} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("connect_blocks", error_message)
            return self.prompt
        
        return self.prompt
    
    @operation(group="build")
    def remove_block(self, block_id: Union[str, int]):
        pass                                                                  
        
             
                                                                 
            
                
                                                           
           
        if isinstance(block_id, int):
            block_id = str(block_id)
        if block_id == '1' and not self.assembly:
            error_message = 'The Starting Block can not be removed'
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("remove_block", error_message)
            return self.prompt
        else:
            if block_id in self.blocks.keys():
                                       
                remove_msg = self._remove_block(block_id)
                self.update_prompt(pre_msg=remove_msg, return_summary=False)
                self.record_op = True
                return self.prompt
            else:
                error_message = f"Specified block {block_id} not found, please try again."
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("remove_block", error_message)
                return self.prompt
            
    def _remove_block(self, block_id: int):
        pass                                                                  
           
                                       
        block = self.blocks.pop(block_id)
                                                
        self.collision_manager.remove_object(block.local_id)
                                             
        block.start_point.sticky = True
        for face in (face for face in block.faces.values() if face.att_to):
            face.att_to.sticky = True
            face.att_to.att_to = None
                               
        remove_msg = f"You have successfully removed <ID {block.local_id}: {block.name}>."
        
        return remove_msg
    
    @operation(placeholder=AvailableBlocks, group="build")
    def attach_block_to(self, base_block: Union[str, int], face: str, new_block: str, note: str = None):
        pass                                                          
                                                                                                                          
        
             
                                                                               
                                                           
                                                                                    
                                                                          
            
                
                                                              
           
        if not self.started and not self.assembly:
            error_message = "The machine has not been started, please start the machine first."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("attach_block_to", error_message)
            return self.prompt  
        if new_block in AvailableConnectors:
            error_message = "Connectors can not be attached to a single face. Use 'connect_blocks' to connect two faces instead."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("attach_block_to", error_message)
            return self.prompt
        if new_block not in AvailableBlocks and new_block not in WaiveableBlocks:
            error_message = f"Block {new_block} not available, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("attach_block_to", error_message)
            return self.prompt
        else:
            if isinstance(base_block, int):
                base_block = str(base_block)
            if base_block in self.blocks.keys():
                base_block: Block = self.blocks.get(base_block)
                
                                                                   
                if face in base_block.faces.keys() and base_block.faces.get(face).sticky:
                                                                   
                                                   
                    bb_face = base_block.faces.get(face)

                                                 
                    local_id = str(self.uid)
                    new_block: Block = self.blocks_storage.get(new_block, local_id, start_point=bb_face, note=note)

                                          
                    bb_face.sticky = False
                    
                    for nb_face in new_block.faces.values():
                        if face_is_attached(bb_face, nb_face):
                            nb_face.sticky = False
                            nb_face.att_to = bb_face
                            bb_face.att_to = nb_face
                    
                    collision_msg = self._add_block(new_block)
                    if collision_msg:
                        error_message = collision_msg
                        self.log_failed_operation("attach_block_to", error_message)
                elif face not in base_block.faces.keys():
                    error_message = f"Base block {base_block.local_id} {base_block.name} does not have face {face}, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("attach_block_to", error_message)
                else:
                    error_message = f"Face {face} of base block {base_block.local_id} {base_block.name} is already occupied, please try again."
                    self.update_prompt(pre_msg=error_message)
                    self.log_failed_operation("attach_block_to", error_message)
            else:
                error_message = f"Base block {base_block} not found, please try again."
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("attach_block_to", error_message)
        
        return self.prompt
    
    def refresh_block(self, block: Block):
        pass                                                                            
                                                                                             
        original_block = self.blocks.pop(block.local_id)
        self.blocks[block.local_id] = block
        self.refresh_colliders()
        collision_msg = self.collision_detect(target_block_id=block.local_id)
        if collision_msg:
            _ = self.blocks.pop(block.local_id)
            self.blocks[original_block.local_id] = original_block
            self.refresh_colliders()
            return collision_msg
        else:
            return None

    @operation(group="refine")
    def twist_block(self, block_id: Union[str, int], angle: float):
        pass                                                                                  
                                                                          
                                                                                                                                                  
                                                                                                                                                                        
                                                              
        
             
                                                                
                                                                 
            
                
                                                         
           
        if isinstance(block_id, int):
            block_id = str(block_id)
        if block_id in self.blocks.keys():
            block = self.blocks.get(block_id)
            block.twist(angle)
            collision_msg = self.refresh_block(block)
            if collision_msg:
                error_message = collision_msg
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("twist_block", error_message)
                block.twist(angle * -1)
                self.refresh_colliders()
                return self.prompt
            self.update_prompt(pre_msg=f'The block {block_id} <{block.name}> is twisted by {angle} degrees. \n {block.caption(finished=False)}')
            self.record_op = True
        else:
            error_message = f"Specified block {block_id} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("twist_block", error_message)
        return self.prompt

    @operation(group="refine")
    def shift_block(self, block_id: Union[str, int], shift_real: List):
        pass                                             
                                                                                                                                                 
        
             
                                                                                                                                                                                                         
            
                
                
           
        if isinstance(block_id, int):
            block_id = str(block_id)
        if block_id in self.blocks.keys():
            block = self.blocks.get(block_id)
            block.shift(shift_real)
            collision_msg = self.refresh_block(block)
            if collision_msg:
                error_message = collision_msg
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("shift_block", error_message)
                block.shift([shift * -1 for shift in shift_real])
                self.refresh_colliders()
                return self.prompt
            self.update_prompt(pre_msg=f'The block {block_id} <{block.name}> is shifted by {shift_real}. \n {block.caption(finished=False)}')
            self.record_op = True
        else:
            error_message = f"Specified block {block_id} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("shift_block", error_message)
        return self.prompt
    
    @operation(group="refine")
    def flip_spin(self, block_id: Union[str, int]):
        pass                                                                                                                 
        
             
                                                               
            
                
                                                        
           
        if isinstance(block_id, int):
            block_id = str(block_id)
        if block_id in self.blocks.keys():
            block = self.blocks.get(block_id)
            if block.spin:
                block.flipped = not block.flipped 
                self.update_prompt(pre_msg=f'The block {block_id} <{block.name}> is flipped. \n {block.caption(finished=False)}')
                self.record_op = True
            else: 
                error_message = f'The block {block_id} <{block.name}> does not spin, please try again.'
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("flip_spin", error_message)
        else: 
            error_message = f"Specified block {block_id} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("flip_spin", error_message)
            
        return self.prompt
    
                         
    def in_collision(self):
        is_collision, collision_pairs = self.collision_manager.in_collision_internal(return_names=True)
        return is_collision, collision_pairs
    
    def collision_detect(self, target_block_id = False, assembly = False):
        is_collision, collision_pairs = self.in_collision()
        
        if is_collision:
            block = self.blocks.get(target_block_id) if target_block_id else self.blocks.get(str(self.uid))
            if target_block_id:
                block_label = f"block {block.local_id} <{block.name}>" if not self.assembly else f"sub-structure {self.machines.get(target_block_id).local_index}"
            elif assembly:
                machine = self.machines[int_to_char(self.machine_count)]
                block_label = f"sub-structure {machine.name}" 
            else:
                block_label = f"new block <{self.blocks[str(self.uid)].name}>"
            collision_msg = [f"Operation failed! The {block_label} overlaps with existing blocks and it's been restored to previous state already, please try again"]
            for i, j in iter(collision_pairs):
                collision_msg.append(f"Overlapping detected between <ID {self.blocks[i].local_id}: {self.blocks[i].name}> and <ID {self.blocks[j].local_id}: {self.blocks[j].name}>")
            
            return '\n'.join(collision_msg)
        else:
            return None
    
                     
    @operation(log=False, group="control")
    def review_powered_blocks(self):
        pass                                                           
        
             
                
            
                
                                                                                                                         
           
        message = ['The machine has the following powered blocks:']
        for block in self._powered_blocks():
            message.append(block.caption_locomotion)
        return '\n'.join(message)

    def _powered_blocks(self)->List[Block]:
        pass                                                           
           
        return [block for block in self.blocks.values() if block.locomotion]
    
    def _init_control_config(self):
                              
        keys = []
        for block in self._powered_blocks():
            for key in block.locomotion.values():
                keys.extend(key)
        self.keys = set(keys)
    
    def _control_config(self):
                                   
        ctrl_config: Dict[str, List[str]] = {}
        self._init_control_config()  
        for key in self.keys:
            ctrl_config[key] = []
                               
        for block in self._powered_blocks():
            for action, keys in block.locomotion.items():
                for key in keys:
                    ctrl_config[key].append(f"{action} of block {block.local_id} '{block.name}'")
        
        return ctrl_config
    
    @operation(log=False, group="control")
    def review_control_config(self):
        pass                                                           
        
             
                
            
                
                                                                                          
           
        ctrl_config = self._control_config()
        if len(ctrl_config.keys()) == 0:
            return "No control key has been added to any block yet."
        else:
            return "\n".join([f"Key: {key}, Actions: {", ".join(actions)}" for key, actions in ctrl_config.items()])

    @operation(log=False, group="control")
    def review_control_sequence(self):
        pass                                                      
        
             
                
            
                
                                                                               
           
        if len(self.control_sequence) == 0:
            return "No control sequence has been added."
        else:
            ctrl_config = self._control_config()
            message = ['Control Sequence:']
            for i, seq in enumerate(self.control_sequence):
                message.append(f"Sequence {i+1}:")
                message.append(f"Press key '{seq['key']}' at {seq['time']} seconds and hold for {seq['hold_for']} seconds.")
                action = ", ".join(ctrl_config[seq['key']]) if ctrl_config[seq['key']] else "No action"
                message.append(f"Action: {action}")
            return '\n'.join(message)
    
    @operation(placeholder=AvailableKeys, group="control")
    def change_control_key(self, block_id: Union[str, int], action: str, new_key: str):
        pass                                                                
        
             
                                                                 
                                                                                                                                                                                                                                            
                                                                                         
            
                
                                                              
           
        if new_key not in AvailableKeys[:4]: 
            if not bool(re.match(r'^(Alpha|Keypad)[0-9]$', new_key)):
                error_message = f"Key '{new_key}' is not in the control key list, please try again."
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("change_control_key", error_message)
                return self.prompt
        
        self._init_control_config()
        if str(block_id) in self.blocks.keys():
            if not self.blocks[str(block_id)].locomotion:
                error_message = f"The block {block_id} '{self.blocks[str(block_id)].name}' does not have any locomotion actions, please try again."
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("change_control_key", error_message)
                return self.prompt
            if action not in self.blocks[str(block_id)].locomotion.keys():
                error_message = f"Action '{action}' is not in the locomotion actions of the block {block_id} '{self.blocks[str(block_id)].name}', please try again."
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("change_control_key", error_message)
                return self.prompt
            self.blocks[str(block_id)].change_control_key(action=action, key=new_key)
            msg = f"The control key of action '{action}' of block {block_id} '{self.blocks[str(block_id)].name}' has been changed into '{new_key}' \n" + self.blocks[str(block_id)].caption_locomotion
            self.update_prompt(pre_msg=msg)
        else:
            error_message = f"Specified block {block_id} not found, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("change_control_key", error_message)
            return self.prompt
        
        return self.prompt
    
    @operation(group="control")
    def add_control_sequence(self, time: float, key: str, hold_for: float):
        pass                                         
        
             
                                                                        
                                                                                                                                                         
                                                                 
            
                
                                                           
           
        self._init_control_config()
        if key not in self.keys:
            error_message = f"Key '{key}' is not in the control key list, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("add_control_sequence", error_message)
            return self.prompt
        else:
            self.control_sequence.append({"time": time, "key": key, "hold_for": hold_for})
            self.update_prompt(pre_msg=f"Control sequence added: Press key '{key}' at {time} seconds and hold for {hold_for} seconds.")
        return self.prompt
    
    @operation(group="control")
    def remove_control_sequence(self, index: int):
        pass                                        
        
             
                                                                
            
                
                                                          
           
        if index < 0 or index >= len(self.control_sequence):
            error_message = f"Index '{index}' is out of range, please try again."
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("remove_control_sequence", error_message)
            return self.prompt
        else:
            self.control_sequence.pop(index)
            self.update_prompt(pre_msg=f"Control sequence removed: Press key '{self.control_sequence[index]['key']}' at {self.control_sequence[index]['time']} seconds and hold for {self.control_sequence[index]['hold_for']} seconds.")
            return self.prompt
        
    @operation(group="control")
    def reset_control_sequence(self):
        pass                                                           
        
             
                
            
                
                                                        
           
        self.control_sequence = []
        self.update_prompt(pre_msg="Control sequence reset to an empty list.")
        return self.prompt
    
                           
    def outline_mesh(self):
        return trimesh.util.concatenate([block.outline for block in self.blocks.values()])

                    
    def to_xml(self, shift_virtual: List[float] = [0, 0, 0], rotation: List[float] = [0, 0, 0, 1]):
        lines = []
        lines.append('<?xml version="1.0" encoding="utf-8"?>')
        lines.append('<!--Besiege machine save file.-->')
        lines.append(f'<Machine version="1" bsgVersion="1.4" name="{self.name}">')
        
                        
        lines.append('    <!--The machine\'s position and rotation.-->')
        lines.append('    <Global>')
        lines.append(f'        <Position x="{shift_virtual[0]}" y="{5 - shift_virtual[1]}" z="{shift_virtual[2]}" />')
        lines.append(f'        <Rotation x="{rotation[0]}" y="{rotation[1]}" z="{rotation[2]}" w="{rotation[3]}" />')
        lines.append('    </Global>')

                      
        lines.append('    <!--The machine\'s additional data or modded data.-->')
        lines.append('    <Data>')
        
                           
        lines.append('        <StringArray key="lua_files">LuaRoot/main.lua</StringArray>')
        lines.append(f'        <StringArray key="lua_data">-- Created {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
        
                              
                                                     
        lines.append('local frame_count = 0')
        lines.append('local refresh_rate = 25')
        
        if "Ballast" in set(block.name for block in self.blocks.values()):
            ballast = next(block for block in self.blocks.values() if block.name == "Ballast")
            lines.append(f'local ballast_ref_key = "{ballast.ref_key}"')
            lines.append(f'local mass_min = 5.0')
            if ballast.change_mass:
                lines.append(f'local mass_max = 1500.0')
                lines.append(f'local ramp_duration = 15.0')
            else:
                lines.append(f'local mass_max = 50.0')
                lines.append(f'local ramp_duration = 2.0')
        else:
            ballast = None

                                     
        lines.append('-- Start of the control configuration')
        if hasattr(self, 'keys'):
            for key in self.keys:
                lines.append(f"local {key.lower()} = machine.new_key_emulator('{key}')")
        lines.append('-- End of the control configuration')

        lines.append('local function play()')
        if ballast:
            lines.append(f'  ballast_control = machine.get_refs_control(ballast_ref_key)')
        lines.append('  end')

        lines.append('local function update()')
        lines.append('  end')

        lines.append('local function late_update()')
        lines.append('  end')

        lines.append('local function fixed_update()')
        lines.append('  -- frame-rate independent update (called 100 times per second)')
        lines.append('  frame_count = frame_count + 1')
        lines.append('  current_time = frame_count / 100')
        
        lines.append('  -- Start of the control sequence')
        if ballast:
            lines.append(f'  local t = math.max(math.min((current_time - 0.5) / ramp_duration, 1.0), 0.005)')
            lines.append(f'  mass_value = mass_min + (mass_max - mass_min) * t')
            lines.append(f'  ballast_control.set_slider("mass", mass_value)')
            
        
                              
        for seq in self.control_sequence:
            lines.append(f"  if current_time  &gt;= {seq['time']:.1f} then {seq['key'].lower()}.start() end")
            lines.append(f"  if current_time  &gt;= {seq['time'] + seq['hold_for']:.1f} then {seq['key'].lower()}.stop() end")
        lines.append('  -- End of the control sequence')

        lines.append('  -- Print the position of the starting block every 1/5 seconds')
        lines.append('  if frame_count % (100 / refresh_rate) == 0 then')
                          
        lines.append('    machine_info = machine.get_machine_info()')
        for block in self.blocks.values():
            if block.tracking:
                if block.name == "Starting Block":
                    lines.append(f'    block_{block.local_id} = machine_info.get_block_info(0)')
                else:
                    lines.append(f'    block_{block.local_id} = machine_info.get_block_info("{block.ref_key}")')
                lines.append(f'    position_{block.local_id} = block_{block.local_id}.position()')
                if block.name == "Water Cannon":
                                             
                    lines.append(f'    burn_{block.local_id} = block_{block.local_id}.burning()')
                    lines.append(f'    print(string.format("%.1f, %s, %s", current_time, "ID_{block.local_id}", tostring(burn_{block.local_id})))')
                if block.name == "Ballast":
                    lines.append(f'    print(string.format("%.1f, %s, %.1f", current_time, "ID_{block.local_id}", mass_value))')
                                   
                lines.append(f'    print(string.format("%.1f, %s, %.1f, %.1f, %.1f", current_time, "ID_{block.local_id}", position_{block.local_id}.x, position_{block.local_id}.y, position_{block.local_id}.z))')
        lines.append('    end')
        
        lines.append('  end')

        lines.append('local function on_gui()')
        lines.append('  end')
        
        lines.append('return {play = play, update = update, late_update = late_update, fixed_update = fixed_update, on_gui = on_gui} ')
                               
        lines.append('</StringArray>')
        lines.append('        <StringArray key="lua_modules_names">default</StringArray>')
        lines.append('        <StringArray key="lua_modules_paths">LuaRoot/main.lua</StringArray>')
        lines.append('        <Boolean key="lua">True</Boolean>')
        lines.append('        <StringArray key="requiredMods" />')
        lines.append('    </Data>')

                        
        lines.append('    <!--The machine\'s blocks.-->')
        lines.append('    <Blocks>')
        first_starting_block_key = [block for block in self.blocks.keys() if self.blocks[block].name == "Starting Block"][0]
        first_starting_block = self.blocks.pop(first_starting_block_key)
        first_starting_block_xml = first_starting_block.to_xml(indent_level=2)
        lines.extend(first_starting_block_xml)
        for block in self.blocks.values():
            block_xml = block.to_xml(indent_level=2)
            lines.extend(block_xml)
        lines.append('    </Blocks>')
        lines.append('</Machine>')
        self.blocks[first_starting_block_key] = first_starting_block
        
        return '\n'.join(lines)
    
                           
    def to_file(self, output_dir, shift_virtual: List[float] = [0, 0, 0], rotation: List[float] = [0, 0, 0, 1]):
        pass                                                                                                                                                                 
                                    
        
             
                                                                              
           
        self.max_time = 10 
        for seq in self.control_sequence:
            end_time = seq['time'] + seq['hold_for']
            if end_time > self.max_time:
                self.max_time = end_time
        bsg_data = self.to_xml(shift_virtual=shift_virtual, rotation=rotation)
        bsg_file_path = os.path.join(self.save_dir, f'{self.name}.bsg')
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, f'{self.name}.bsg')
        self.output_sequence_path = os.path.join(output_dir, f'{self.name}.json')
                             
        with open(bsg_file_path, 'w', encoding='utf-8') as file:
            file.write(bsg_data)
        
                               
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(bsg_data)
        self.save_operation_history(self.output_sequence_path)
        print(f'machine saved as {bsg_file_path}')
    
    def from_file(self, file_path):
        self.output_sequence_path = Path(file_path)
                     
        self.db_path = self.output_sequence_path.parent.parent.parent / "task_database.db"
        operation_history = self.load_operation_history(self.output_sequence_path)
        self.rebuild_from_history(operation_history)
        return self
        
                                      
    def save_operation_history(self, file_path):
                                                                              
        if self.assembly == self.sub_structure:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.operation_history, f, indent=2)

    def load_operation_history(self, file_path) -> List[Dict[str, Any]]:
        with open(file_path, 'r', encoding='utf-8') as f:
            operation_history = json.load(f)
        return operation_history
    
                                                  
    def rebuild_from_history(self, operation_history=None):
                                                 
        if operation_history is None:
            operation_history = self.operation_history
        
                           
        self.reset()
                                            
        for op in operation_history:
            if op["op"] in self.operations:
                self.operations[op["op"]](**op["params"])
    
                                          
    def init_full_op_history(self):
        if not os.path.exists(self.full_op_history_path):
            self.operation_history_full = []
        else:
            self.operation_history_full = json.load(open(self.full_op_history_path, 'r', encoding='utf-8'))
    
    def save_full_op_history(self):
                                                                              
        if self.assembly == self.sub_structure:
            os.makedirs(os.path.dirname(self.full_op_history_path), exist_ok=True)
            with open(self.full_op_history_path, 'w', encoding='utf-8') as f:
                json.dump(self.operation_history_full, f, indent=2)

class Assembly(Machine):
                                                                                          
    def __init__(self, 
                 name: str | None = None, 
                 save_dir: str = './datacache/default/machine', 
                 db_path: str | None = None, 
                 note: str | None = None, 
                 assembly: bool = True, 
                 sub_structure: bool = True, 
                 do_collision: bool = True):
                                                                                          
        super().__init__(name, save_dir=save_dir, assembly=assembly, sub_structure=sub_structure, db_path=db_path, note=note, do_collision=do_collision)
        self.machines: Dict[str, Machine | Assembly] = {}                                     
        self.machine_count = 0
        
    def index(self):
        return int_to_char(self.machine_count)
        
    @operation(group="build")
    def add_machine(self, machine_id: str, init_shift: List[float] = None, init_rotation: List[float] = None):
        pass                                                                       
                                                                                                              
                                                                                                        
                                                                                                                                                               
        
             
                                                      
                                                                                                                                                         
                                                                                                                                                       
            
                
                                                          
           
                                       
        machine_file_path = os.path.join(os.path.dirname(self.db_path), "machine", machine_id, f"{machine_id}.json")
        operation_history = self.load_operation_history(file_path=machine_file_path)
        adding_assembly = False if operation_history[0]['op'] == 'start' else True
        
        if adding_assembly:
            machine = Assembly(name=f'Sub-structure {self.machine_count}', save_dir=self.save_dir, do_collision=self.do_collision)
        else:
            machine = Machine(name=f'Sub-structure {self.machine_count}', save_dir=self.save_dir, sub_structure=True, do_collision=self.do_collision)

        machine.rebuild_from_history(operation_history)
        if init_shift is not None:
            machine.shift(init_shift)
        if init_rotation is not None:
            machine.rotate(init_rotation[0], init_rotation[1], init_rotation[2])
            
                                
        machine.local_index = self.index()
        
                                     
        self.machines[self.index()] = machine
        
        self.update_blocks()
        if adding_assembly:
            self.update_machines(local_index = self.index())
        
                                                    
        collision_msg = self.collision_detect(assembly=True) if self.do_collision else None

        if collision_msg:
                                     
            self.remove_machine(self.index())
            error_message = collision_msg
            self.log_failed_operation("add_machine", error_message)
            self.update_prompt(pre_msg=error_message)
        else:
                                                
            self.record_op = True
            self.update_prompt(pre_msg=f"You have successfully added sub-structure {self.index()} using machine {machine_id}", 
                               complete=False, 
                               return_summary=True, 
                               assembly_only=True)
            self.machines[self.index()].started = True
            self.machine_count += 1
        
        return self.prompt
    
    def update_blocks(self):
        pass                                                                           
        for machine_index, machine in self.machines.items():
                                              
            for block_id, block in machine.blocks.items():
                compound_key = f"{machine_index}_{block_id}"
                block_copy = copy.deepcopy(block)
                block_copy.local_id = compound_key                           
                self.blocks[compound_key] = block_copy
        self.refresh_colliders()

    def update_machines(self, local_index: str):
        machine = self.machines[local_index]
        for block_id, block in machine.blocks.items():
            old_key = block_id
            compound_key = f"{local_index}_{old_key}"
            block_copy = copy.deepcopy(block)
            block_copy.local_id = compound_key                           
            self.blocks[compound_key] = block_copy
    
    @operation(group="build")
    def remove_machine(self, machine_index: str):
        pass                                           
        
             
                                                               
            
                
                                                         
           
        if machine_index in self.machines:
                                                         
            blocks_to_remove = [key for key in self.blocks.keys() if key.startswith(machine_index)]
            for block_key in blocks_to_remove:
                self.blocks.pop(block_key)
            
                                              
            self.machines.pop(machine_index)
            self.update_blocks()
            self.record_op = True
            self.update_prompt(pre_msg=f"Removed sub-structure {machine_index}", 
                               complete=False, 
                               return_summary=True, 
                               assembly_only=True)
        else:
            error_message = f"Sub-structure {machine_index} not found"
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("remove_machine", error_message)
            
        return self.prompt
    
    @operation(group="build")
    def shift_machine(self, machine_index: str, position: List[float]):
        pass                                                              
                                                                                    
        
             
                                                              
                                                                               
            
                
                                                       
           
        if machine_index in self.machines:
            self.machines[machine_index].shift(position)
            self.update_blocks()
                                                        
            collision_msg = self.collision_detect(target_block_id=machine_index, assembly=True) if self.do_collision else None
            if collision_msg:
                error_message = collision_msg
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("shift_machine", error_message)
                return self.prompt
            self.record_op = True
            self.update_prompt(pre_msg=f"Shifted sub-structure {machine_index} by {position}", 
                               complete=False, 
                               return_summary=True, 
                               assembly_only=True)
        else:
            error_message = f"Sub-structure {machine_index} not found"
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("shift_machine", error_message)
            
        return self.prompt
    
    @operation(group="build")
    def rotate_machine(self, machine_index: str, rotation: List[float]):
        pass                                                            
                                                                                    
        
             
                                                               
                                                                                 
            
                
                                                          
           
        if machine_index in self.machines:
            self.machines[machine_index].rotate(rotation[0], rotation[1], rotation[2])
            self.update_blocks()
                                                        
            collision_msg = self.collision_detect(target_block_id=machine_index, assembly=True) if self.do_collision else None
            if collision_msg:
                error_message = collision_msg
                self.update_prompt(pre_msg=error_message)
                self.log_failed_operation("rotate_machine", error_message)
                return self.prompt
            self.record_op = True
            self.update_prompt(pre_msg=f"Rotated sub-structure {machine_index} by {rotation}", 
                               complete=False, 
                               return_summary=True, 
                               assembly_only=True)
        else:
            error_message = f"Sub-structure {machine_index} not found"
            self.update_prompt(pre_msg=error_message)
            self.log_failed_operation("rotate_machine", error_message)
            
        return self.prompt
