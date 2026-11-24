                                                                                                   
                                                                                                    
                                                                                                             

export const ROBOT = {
  radius: 0.30,                                             
  cameraHeight: 1.20,                    
  cameraPitchDeg: -19,                                                                                   
  vFovDeg: 52,                                                                                                     
  aspect: 4 / 3,
  frontOffset: 0.15,                                                            
};

                                                                                                         
export const ACTIONS = {
  move_forward:       { forward: 0.90, label: 'walk forward 3 s at 0.3 m/s (about 0.9 m)' },
  move_forward_small: { forward: 0.30, label: 'walk forward 1 s at 0.3 m/s (about 0.3 m)' },
  move_backward:      { forward: -0.60, label: 'walk backward 2 s at 0.3 m/s (about 0.6 m)' },
  strafe_left:        { side: -0.40, label: 'side-step left 2 s at 0.2 m/s (about 0.4 m), heading unchanged' },
  strafe_right:       { side: 0.40, label: 'side-step right 2 s at 0.2 m/s (about 0.4 m), heading unchanged' },
  turn_left:          { turnDeg: 30, label: 'turn left 30 degrees (IMU closed loop)' },
  turn_right:         { turnDeg: -30, label: 'turn right 30 degrees (IMU closed loop)' },
                                                                                                                     
  touch:              { touch: true, label: 'stop walking and reach one arm straight forward to touch the object in front of you (ends the episode)' },
};
export const ACTION_BUDGET = 30;                                              

                                                                                             
export const ROOMS = [
  { id: 'start_room', minX: -3.4, maxX: 1.2, minZ: -3.6, maxZ: 0.0 },
  { id: 'office', minX: -1.5, maxX: 6.3, minZ: 0.0, maxZ: 10.0 },
];
export const DOORWAY = { x0: -1.45, x1: -0.45, z: 0.0 };                                

                                                                                                                  
export const WALLS = [
               
  [-3.4, -3.6, 1.2, -3.6, 'white'], [-3.4, -3.6, -3.4, 0.0, 'white'], [1.2, -3.6, 1.2, 0.0, 'white'],
  [-3.4, 0.0, -1.5, 0.0, 'white'],
                                                                             
  [-0.45, 0.0, 6.3, 0.0, 'white'],
                               
  [-1.5, 0.0, -1.5, 10.0, 'white'], [6.3, 0.0, 6.3, 10.0, 'white'],
                                                                                                    
  [-1.5, 10.0, -0.75, 10.0, 'white'], [-0.75, 10.0, 0.25, 10.0, 'door'], [0.25, 10.0, 0.65, 10.0, 'pillar'], [0.65, 10.0, 6.3, 10.0, 'glass'],
];

                                                                                           
export const FURNITURE = [
                                                                                
  { id: 'desk_fan', kind: 'desk', box: [2.5, 7.2, 2.8, 1.4, 0.75], label: 'bench desk with the white standing fan at its left end' },
  { id: 'divider_green', kind: 'divider', box: [1.85, 7.2, 1.2, 0.03, 1.10], color: 0x9bbb3c, solid: false },
  { id: 'divider_grey', kind: 'divider', box: [3.15, 7.2, 1.3, 0.03, 1.10], color: 0x8d9196, solid: false },
  { id: 'fan', kind: 'fan', at: [0.85, 6.25], height: 1.10, label: 'white standing fan' },
  { id: 'cabinet_fan', kind: 'cabinet', box: [1.35, 6.85, 0.42, 0.52, 0.62] },
  { id: 'water_jug', kind: 'jug', at: [0.80, 7.55], label: 'blue bottled water' },
  { id: 'boxes_glass', kind: 'boxes', box: [0.95, 9.0, 0.9, 0.55, 0.55] },
  { id: 'chair_fan_n1', kind: 'chair', at: [1.9, 8.35], yawDeg: 180, label: 'office chair at the fan desk' },
  { id: 'chair_fan_n2', kind: 'chair', at: [3.2, 8.40], yawDeg: 180, label: 'office chair at the fan desk' },
  { id: 'chair_fan_s', kind: 'chair', at: [3.3, 6.05], yawDeg: 0, label: 'office chair at the fan desk' },
                                                                                        
  { id: 'desk_right', kind: 'desk', box: [2.7, 3.7, 2.2, 1.2, 0.75], label: 'office desk right of the entrance (in use)' },
  { id: 'chair_right', kind: 'chair', at: [3.2, 2.75], yawDeg: 0, label: 'office chair at the right desk' },
  { id: 'person_right', kind: 'person', at: [3.2, 2.70], label: 'person working at the right desk' },
                                           
  { id: 'boxes_west', kind: 'boxes', box: [-1.18, 4.75, 0.55, 0.95, 0.85] },
  { id: 'bin_west_1', kind: 'bin', at: [-1.22, 4.00] },
  { id: 'bin_west_2', kind: 'bin', at: [-0.82, 4.05] },
                                                                                                                   
  { id: 'chair_wall', kind: 'chair', at: [5.95, 8.15], yawDeg: 270, label: 'grey mesh chair against the east wall' },
  { id: 'bin_east_1', kind: 'bin', at: [6.08, 7.40] },
  { id: 'bin_east_2', kind: 'bin', at: [6.08, 5.60] },
                                                                                                         
  { id: 'start_cabinet', kind: 'cabinet', box: [-3.05, -2.2, 0.5, 1.2, 1.0] },
  { id: 'start_table', kind: 'desk', box: [0.4, -2.6, 1.4, 0.8, 0.75], label: 'table in the start room' },
];

export const START_POSES = {
                                                                               
  S1: { x: -0.95, z: -1.30, yawDeg: 0 },
};

                                                                                            
const FACING = 'You are facing the door that leads into the other room. Walk out through this door, ';                                        
export const TASKS = [
  { id: 'T1-S1', task: 'T1', name: 'desk next to the fan (September task)', start: 'S1',
    text: 'You are facing the door that leads into the other room. Walk out through this door, find the desk next to the white electric fan in the other room, and stop in front of that desk. After you stop, reach out your arm and touch that desk.',
    target: { kind: 'box', ref: 'desk_fan' }, sameClass: ['desk_right'],
    targetLabel: 'the office desk next to the white standing fan (the fan is at the left end of the desk)' },
];

                                                                            
                                                                                   
export const REACH = { length: 0.50, tolerance: 0.30, halfWidth: 0.15, step: 0.02 };
export const SUCCESS = { rule: 'touch', maxFrontDistance: 1.0, maxBearingDeg: 45 };
