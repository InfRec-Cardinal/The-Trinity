                                                                                                     

                                                                                                                      
                                                                                                                      
                                                                                                               
                    

                                                                                                                   
                                                                                                                  
                                                                                                     

                                                                                                                   
                                                                                              
                                                                                    
   
import re
import copy
import importlib.util
import json
import math
import os
import sys

import mujoco
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_spec = importlib.util.spec_from_file_location('capxa_physics', os.path.join(ROOT, 'capxa', 'physics.py'))
base = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(base)
                                                                                                                             
                                                                                                                        
                                                                                                      
base.CUBE, base.CUP_H, base.CUP_RIM, base.CUP_BASE = 0.02, 0.09, 0.035, 0.025
quat_mul, CUBE, CUP_H, CUP_RIM, CUP_BASE, LIME_R = base.quat_mul, base.CUBE, base.CUP_H, base.CUP_RIM, base.CUP_BASE, base.LIME_R

ROBOT_XML = os.path.join(ROOT, 'vendor', 'alohamini2', 'alohamini2_raw.xml')
W, H = 1280, 720                                                                                           
CW, CH = 640, 480                                                                                                                   
VIEW = os.environ.get('CAPXI_VIEW', 'overhead')                                                                              
                                                                                                                              
                                                                                                                                           
                                                                                                                       
                                                                                                                       
YAW0 = float(os.environ.get('CAPXI_YAW0', 0.0)) if VIEW == 'robot' else 0.0
                                                                                                                          
SOLID_CUPS = os.environ.get('CAPXI_SOLID_CUPS') == '1'
                                                                                                                        
                                                                                                                            
                                                                                                                     
                                                                                                                             
                                                                                                                                                                         
                                                                                                         
WOBBLE = os.environ.get('CAPXI_WOBBLE') == '1'
WOB = dict(kp_wrist=float(os.environ.get('CAPXI_WOB_KP', 12.0)), damp_wrist=float(os.environ.get('CAPXI_WOB_DAMP', 0.12)),
           kp_elbow=float(os.environ.get('CAPXI_WOB_KP_ELBOW', 30.0)), damp_elbow=float(os.environ.get('CAPXI_WOB_DAMP_ELBOW', 0.30)),
           armature=float(os.environ.get('CAPXI_WOB_ARMATURE', 0.05)), pos_noise=float(os.environ.get('CAPXI_WOB_POS_MM', 3.0)) / 1000, yaw_noise_deg=float(os.environ.get('CAPXI_WOB_YAW_DEG', 2.0)),
           settle=float(os.environ.get('CAPXI_WOB_SETTLE', 0.10)), think=float(os.environ.get('CAPXI_WOB_THINK', 0.6)), grip_force=float(os.environ.get('CAPXI_WOB_GRIP', 1.2)), pad_friction=float(os.environ.get('CAPXI_WOB_PAD_FRICTION', 2.0)), noslip=int(os.environ.get('CAPXI_WOB_NOSLIP', 5)))
                                                                                                                         
TILT = math.radians(float(os.environ.get('CAPXI_TILT_DEG', 35))) if VIEW == 'robot' else 0.0
_WQ = json.loads(os.environ.get('CAPXI_WRIST_QUAT', '[0, 1, 0, 0]'))                                                                           
ROBOT_CAMS = {'head': ('front_camera', [0, 0.707107, -0.707107, 0]), 'wrist0': ('left_camera', _WQ), 'wrist1': ('right_camera', _WQ)}                                                              
RW, RH = 640, 360                                
REPLAY_FPS = 8
CTRL_HZ = 20
ARMS = ('left', 'right')                                                                                       
ARM_JOINTS = ('shoulder_pan', 'shoulder_lift', 'elbow_flex', 'wrist_flex', 'wrist_yaw_joint', 'wrist_roll')
                                                                                                                     
                                                                                                              
TABLE_H = 0.70                                                 
BASE_Y = float(os.environ.get('CAPXI_BASE_Y', -0.28 if os.environ.get('CAPXI_VIEW') == 'robot' else -0.20))                                                                            
LIFT = 0.20                                                                                                              
                                                                                                                                      
GRIP_OPEN, GRIP_CLOSED = -0.10, 1.25
TCP_IN_FIXED_JAW = (0.010, 0.0, 0.085)                                                                                           
TCP_MIN_Z = 0.022                                                                        
STEP_MAX_CM, TURN_MAX_DEG = 10.0, 90.0
SPEED = 0.10                                                  
                                                                                     
CAM_POS = np.array([0.0, -0.04, 1.15]); CAM_LOOK = np.array([0.0, 0.07, 0.0]); CAM_FOVY = 32.0
IK_SEEDS = {a: [[0, 0.2, 0.3, 1.4, 0, 0], [0, -0.6, 1.2, 0.9, 0, 0], [sx * 0.5, -0.8, 0.5, 1.0, 0, 0], [sx * 0.5, 0.3, 0.3, 1.2, 0, 1.5], [sx * 0.5, 0.3, 0.3, 1.2, 0, -1.5]]
            for a, sx in (('left', 1), ('right', -1))}
HOME = {'left': (-0.24, -0.05, 0.14), 'right': (0.24, -0.05, 0.14)} if VIEW != 'robot' else \
       {'left': (-0.20, 0.05, 0.18), 'right': (0.20, 0.05, 0.18)}                                                        
COLORS = {'red': (0.78, 0.04, 0.08, 1), 'green': (0.05, 0.50, 0.24, 1), 'blue': (0.07, 0.22, 0.62, 1)}                                            


def yaw_quat(yaw): return [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]


def look_xyaxes(pos, target):
    f = target - pos; f /= np.linalg.norm(f); z = -f
    x = np.cross([0, 0, 1.0], z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return list(x) + list(y)


def rpy_mat(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr], [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr], [-sp, cp * sr, cp * cr]])


def moving_pad_pose(q_grip=0.70):
    pass                                                                                                               
                                                                                                                       
                                                                                                                     
                                                                                    
    t0 = np.array([0.020214, 0.0020289, 0.021614]); R0 = rpy_mat(-1.5708, 0, 3.1416)                                             
    c, s_ = math.cos(q_grip), math.sin(q_grip); Rm = R0 @ np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
    ctr_f = np.array([0.035, 0.0, 0.078])                                                                              
    return list(Rm.T @ (ctr_f - t0)), list(base.mat2quat(Rm.T))


class Sim(base.Sim):
                                                                              
    def build(self, conf):
        spec = mujoco.MjSpec.from_file(ROBOT_XML)
        spec.meshdir = os.path.join(ROOT, 'vendor', 'alohamini2', 'meshes')
        spec.visual.global_.offwidth = W; spec.visual.global_.offheight = H
        spec.visual.headlight.ambient = [0.35, 0.35, 0.35]; spec.visual.headlight.diffuse = [0.35, 0.35, 0.35]; spec.visual.headlight.specular = [0, 0, 0]
        spec.option.timestep = 0.002
                                                                                    
        b = spec.body('base_link'); b.pos = [0, BASE_Y, -TABLE_H]; b.quat = [0, 0, 0, 1]
        spec.delete(spec.joint('vertical_move')); vl = spec.body('vertical_link'); vl.pos = [vl.pos[0], vl.pos[1], vl.pos[2] + LIFT]
        arm_links = ('Rotation_Pitch', 'Upper_Arm', 'Lower_Arm', 'Wrist_Pitch_Roll', 'wrist_yaw')
        for g in list(spec.geoms):
            body = g.parent.name if g.parent else ''
            if g.group == 0:                                                                                           
                if any(body == f'{a}_{l}' for a in ARMS for l in arm_links):
                    g.contype, g.conaffinity, g.rgba, g.group = 2, 1, [0, 0, 0, 0], 3
                else:
                    spec.delete(g)
            else:
                g.group = 1
                                                                                  
        for a in ARMS:
            fj, mj = spec.body(f'{a}_Fixed_Jaw'), spec.body(f'{a}_Moving_Jaw')
            fj.add_geom(name=f'{a}/pad_fixed', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.005, 0.008, 0.030], pos=[-0.015, 0, 0.074],
                        contype=2, conaffinity=1, friction=[WOB['pad_friction'] if WOBBLE else 1.5, 0.02, 0.002], condim=4, rgba=[0, 0, 0, 0], group=3, mass=0.001)
            fj.add_geom(name=f'{a}/palm', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.020, 0.012, 0.008], pos=[0.012, 0, 0.032],
                        contype=2, conaffinity=1, rgba=[0, 0, 0, 0], group=3, mass=0.001)
            mp, mq = moving_pad_pose()
            mj.add_geom(name=f'{a}/pad_moving', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.005, 0.009, 0.026], pos=mp, quat=mq,
                        contype=2, conaffinity=1, friction=[WOB['pad_friction'] if WOBBLE else 1.5, 0.02, 0.002], condim=4, rgba=[0, 0, 0, 0], group=3, mass=0.001)
            fj.add_site(name=f'{a}/tcp', pos=list(TCP_IN_FIXED_JAW), quat=list(base.mat2quat(np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1.0]]))))
                                                                                              
        for body in spec.bodies:
            if body.name.startswith(('left_', 'right_')): body.gravcomp = 1.0
        for a in ARMS:
            for j in ARM_JOINTS:
                jt = spec.joint(f'{a}_{j}'); jt.damping = [0.6, 0, 0]; jt.armature = 0.02; jt.limited = mujoco.mjtLimited.mjLIMITED_TRUE
                strong = j in ('shoulder_lift', 'elbow_flex')
                kp = 60.0 if strong else 25.0
                if WOBBLE and j in ('wrist_flex', 'wrist_yaw_joint', 'wrist_roll'): kp = WOB['kp_wrist']; jt.damping = [WOB['damp_wrist'], 0, 0]; jt.armature = WOB['armature']
                if WOBBLE and j == 'elbow_flex': kp = WOB['kp_elbow']; jt.damping = [WOB['damp_elbow'], 0, 0]
                act = spec.add_actuator(name=f'{a}/{j}', target=f'{a}_{j}', trntype=mujoco.mjtTrn.mjTRN_JOINT)
                act.gainprm[0] = kp; act.biastype = mujoco.mjtBias.mjBIAS_AFFINE; act.biasprm[0] = 0; act.biasprm[1] = -kp; act.biasprm[2] = 0
                act.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE; act.forcerange = [-9.0, 9.0] if strong else [-3.0, 3.0]
            if VIEW == 'robot':                                                                                                    
                spec.joint(f'{a}_wrist_roll').range = [-1.5 * math.pi, 1.5 * math.pi]
            jg = spec.joint(f'{a}_gripper'); jg.range = [-0.3, 1.4]; jg.limited = mujoco.mjtLimited.mjLIMITED_TRUE; jg.damping = [0.05, 0, 0]; jg.armature = 0.005
            act = spec.add_actuator(name=f'{a}/gripper', target=f'{a}_gripper', trntype=mujoco.mjtTrn.mjTRN_JOINT)
            act.gainprm[0] = 4.0; act.biastype = mujoco.mjtBias.mjBIAS_AFFINE; act.biasprm[1] = -4.0; act.biasprm[2] = -0.05
            act.forcelimited = mujoco.mjtLimited.mjLIMITED_TRUE; act.forcerange = [-WOB['grip_force'], WOB['grip_force']] if WOBBLE else [-1.2, 1.2]
                                      
        spec.add_material(name='tabletop', rgba=[0.90, 0.90, 0.88, 1], specular=0.05, shininess=0.1)                                         
        spec.add_material(name='floor', rgba=[0.35, 0.36, 0.38, 1], specular=0.0)
        edge = BASE_Y + 0.09                                                                                    
        spec.worldbody.add_geom(name='table', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.45, (0.44 - edge) / 2, 0.015], pos=[0, (0.44 + edge) / 2, -0.015], material='tabletop',
                                contype=1, conaffinity=3, friction=[1.0, 0.01, 0.001], group=1)
        for sx in (-1, 1):
            spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.02, 0.02, (TABLE_H - 0.03) / 2], pos=[sx * 0.42, 0.40, -0.03 - (TABLE_H - 0.03) / 2],
                                    material='tabletop', contype=0, conaffinity=0, group=1)
        spec.worldbody.add_geom(name='floor', type=mujoco.mjtGeom.mjGEOM_PLANE, size=[3, 3, 0.05], pos=[0, 0, -TABLE_H], material='floor', contype=1, conaffinity=3, group=1)
        spec.worldbody.add_light(pos=[0.3, -0.2, 1.6], dir=[-0.15, 0.1, -1], diffuse=[0.45, 0.45, 0.45], specular=[0.05, 0.05, 0.05], castshadow=True)
        spec.worldbody.add_light(pos=[-0.5, 0.6, 1.4], dir=[0.3, -0.3, -1], diffuse=[0.2, 0.2, 0.2], specular=[0, 0, 0], castshadow=False)
        spec.worldbody.add_camera(name='overhead_cam', pos=list(CAM_POS), xyaxes=look_xyaxes(CAM_POS, CAM_LOOK), fovy=CAM_FOVY)
        for cam, (body, q) in ROBOT_CAMS.items(): spec.body(body).add_camera(name=cam, quat=q, fovy=73.74)
        for c, rgba in COLORS.items(): spec.add_material(name=f'cube_{c}', rgba=list(rgba), specular=0.05, shininess=0.1)
        spec.add_material(name='lime', rgba=[0.55, 0.78, 0.25, 1], specular=0.1, shininess=0.2)
        spec.add_material(name='cup', rgba=[0.92, 0.90, 0.86, 1], specular=0.05, shininess=0.1)
                                                          
        self.objects = {o['id']: o for o in conf['objects']}
        for o in conf['objects']:
            x, y, _ = o['pos']; q = yaw_quat(o.get('yaw', 0.0))
            if o['type'] == 'cube':
                bd = spec.worldbody.add_body(name=o['id'], pos=[x, y, o.get('z0', 0.0) + CUBE / 2 + 0.0005], quat=q); bd.add_freejoint()
                bd.add_geom(name=o['id'] + '/g', type=mujoco.mjtGeom.mjGEOM_BOX, size=[CUBE / 2] * 3, material=f'cube_{o["color"]}', mass=0.06,
                            friction=[1.0, 0.01, 0.001], condim=4, contype=1, conaffinity=3, group=1)
            elif o['type'] == 'lime':
                bd = spec.worldbody.add_body(name='lime', pos=[x, y, LIME_R + 0.0005]); bd.add_freejoint()
                bd.add_geom(name='lime/g', type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[LIME_R, 0, 0], material='lime', mass=0.06,
                            friction=[1.0, 0.01, 0.002], condim=4, contype=1, conaffinity=3, group=1)
            else:
                bd = spec.worldbody.add_body(name=o['id'], pos=[x, y, CUP_H / 2 + 0.0005]); bd.add_freejoint()
                n, slope, rmid = 16, math.atan2(CUP_RIM - CUP_BASE, CUP_H), (CUP_RIM + CUP_BASE) / 2
                wt, tt = (0.004, 0.007) if SOLID_CUPS else (0.004, 0.002)                                                                                     
                sol = dict(solref=[0.003, 1.0], solimp=[0.97, 0.995, 0.001, 0.5, 2]) if SOLID_CUPS else {}
                for i in range(n):
                    a = 2 * math.pi * i / n
                    qq = quat_mul([math.cos(a / 2), 0, 0, math.sin(a / 2)], [math.cos(-slope / 2), 0, math.sin(-slope / 2), 0])
                    bd.add_geom(name=f'{o["id"]}/w{i}', type=mujoco.mjtGeom.mjGEOM_BOX, size=[wt, 2 * math.pi * CUP_RIM / n * 0.60, CUP_H / 2 / math.cos(slope)],
                                pos=[(rmid + 0.002 - wt) * math.cos(a), (rmid + 0.002 - wt) * math.sin(a), 0], quat=list(qq), material='cup', mass=0.003,
                                friction=[1.0, 0.01, 0.001], condim=4, contype=1, conaffinity=3, group=1, **sol)
                bd.add_geom(name=f'{o["id"]}/top', type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[CUP_BASE + 0.002, tt, 0], pos=[0, 0, CUP_H / 2 - tt],
                            material='cup', mass=0.004, contype=1, conaffinity=3, group=1, **sol)
                texf = os.path.join(ROOT, 'branding', f'cup-number-{o["number"]}.png')
                spec.add_texture(name=f'num{o["number"]}', type=mujoco.mjtTexture.mjTEXTURE_2D, file=texf)
                mat = spec.add_material(name=f'num{o["number"]}'); mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = f'num{o["number"]}'
                bd.add_geom(name=f'{o["id"]}/label', type=mujoco.mjtGeom.mjGEOM_BOX, size=[CUP_BASE * 0.8, CUP_BASE * 0.8, 0.0005], pos=[0, 0, CUP_H / 2 + 0.0006],
                            material=f'num{o["number"]}', contype=0, conaffinity=0, mass=0.0001, group=1)
        self.m = spec.compile(); self.d = mujoco.MjData(self.m)
        if WOBBLE: self.m.opt.noslip_iterations = WOB['noslip']                                                                         

    def reset(self, conf, replay_dir=None):
        self.conf = conf; self.build(conf); m, d = self.m, self.d
        self.qadr = {a: [m.jnt_qposadr[m.joint(f'{a}_{j}').id] for j in ARM_JOINTS] for a in ARMS}
        self.dadr = {a: [m.jnt_dofadr[m.joint(f'{a}_{j}').id] for j in ARM_JOINTS] for a in ARMS}
        self.arm_act = {a: [m.actuator(f'{a}/{j}').id for j in ARM_JOINTS] for a in ARMS}
        self.grip_act = {a: m.actuator(f'{a}/gripper').id for a in ARMS}
        self.grip_q = {a: m.jnt_qposadr[m.joint(f'{a}_gripper').id] for a in ARMS}
        self.site = {a: m.site(f'{a}/tcp').id for a in ARMS}
        self.pads = {a: ({m.geom(f'{a}/pad_fixed').id}, {m.geom(f'{a}/pad_moving').id}) for a in ARMS}
        self.body_of_obj = {k: m.body(k).id for k in self.objects}
        self.geom_obj = {g: k for k, b in self.body_of_obj.items() for g in range(m.ngeom) if m.geom_bodyid[g] == b}
        self.renderer = mujoco.Renderer(m, H, W); self.cam_renderer = mujoco.Renderer(m, CH, CW); self.replay_renderer = mujoco.Renderer(m, RH, RW)
        self.opt = mujoco.MjvOption(); self.opt.geomgroup[:] = [0, 1, 1, 0, 0, 0]
        if VIEW == 'robot': self.opt.sitegroup[:] = 0                                                                        
        self.replay_dir = replay_dir; self.frame_no = 0; self.next_frame = 0.0
        if replay_dir: os.makedirs(replay_dir, exist_ok=True)
        self.t = 0.0; self.lifted = set(); self.wob_rng = np.random.default_rng(sum(map(ord, conf['id'])) * 104729 + 17)
        self.counts = {'actions': 0, 'moves': 0, 'turns': 0, 'grasp_attempts': 0, 'limited_moves': 0}
                                                                                     
        self.target = {}
        for a in ARMS:
            q = self.ik(a, np.array(HOME[a]), 0.0, seed=np.array([0, -0.6, 1.2, 0.9, 0, 0.0]), iters=400)
            for i, v in zip(self.qadr[a], q): d.qpos[i] = v
            d.ctrl[self.arm_act[a]] = q; d.qpos[self.grip_q[a]] = GRIP_OPEN; d.ctrl[self.grip_act[a]] = GRIP_OPEN
            self.target[a] = {'pos': np.array(HOME[a]), 'yaw': 0.0}
        self.home = {a: dict(self.target[a], pos=self.target[a]['pos'].copy()) for a in ARMS}
        mujoco.mj_forward(m, d)
        self.start = {k: self.pos(k).copy() for k in self.objects}
        self.run(0.6)
        return self.summary()

                                                                              
    def joints(self, a): return np.array([self.d.qpos[i] for i in self.qadr[a]])
    def tcp(self, a): return self.d.site_xpos[self.site[a]].copy(), self.d.site_xmat[self.site[a]].reshape(3, 3).copy()
    def summary(self):
        return {'t': round(self.t, 3), 'arms': {a: {'joints': [round(float(v), 4) for v in self.joints(a)], 'tcp': [round(float(v), 4) for v in self.tcp(a)[0]],
                'gripper': round(float(self.d.qpos[self.grip_q[a]]), 4)} for a in ARMS},
                'objects': {k: {'pos': [round(float(v), 4) for v in self.pos(k)], 'quat': [round(float(v), 4) for v in self.quat(k)]} for k in self.objects}}

    def replay_frame(self):
        self.replay_renderer.update_scene(self.d, camera=self.replay_cam(), scene_option=self.opt)
        Image.fromarray(self.replay_renderer.render()).save(os.path.join(self.replay_dir, f'{self.frame_no:06d}.jpg'), quality=80)
        self.frame_no += 1
    def replay_cam(self):
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = [0, 0.02, 0.10]; cam.distance = 1.35; cam.azimuth = 35; cam.elevation = -30
        return cam

                                                                                      
    @staticmethod
    def goal_rot(yaw):
        pass                                                                                                    
        c, s_ = math.cos(yaw), math.sin(yaw); Rz = np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1.0]])
        y = np.array([math.cos(YAW0), math.sin(YAW0), 0.0]); z = np.array([0, math.sin(TILT), -math.cos(TILT)])                                                    
        return Rz @ np.stack([np.cross(y, z), y, z], axis=1)
    def ik(self, a, p_goal, yaw, seed=None, iters=200):
        if VIEW != 'robot': return self._ik(a, p_goal, yaw, seed, iters, 0.25)
                                                                                                                           
        q = self._ik(a, p_goal, yaw, seed, iters, 0.6); e = self.ik_err(a, q, p_goal, yaw)
        if e > 0.5:
            for sd in IK_SEEDS[a]:
                q2 = self._ik(a, p_goal, yaw, np.array(sd), 300, 0.6); e2 = self.ik_err(a, q2, p_goal, yaw)
                if e2 < e: q, e = q2, e2
                if e < 0.2: break
        return q
    def ik_err(self, a, q, p_goal, yaw):                
        d = mujoco.MjData(self.m); d.qpos[:] = self.d.qpos
        for i, v in zip(self.qadr[a], q): d.qpos[i] = v
        mujoco.mj_kinematics(self.m, d); R = d.site_xmat[self.site[a]].reshape(3, 3)
        return float(np.linalg.norm(d.site_xpos[self.site[a]] - p_goal) * 100 + np.degrees(np.arccos(np.clip((np.trace(R.T @ self.goal_rot(yaw)) - 1) / 2, -1, 1))) / 5)
    def _ik(self, a, p_goal, yaw, seed, iters, wr):
        m = self.m; d = mujoco.MjData(m); d.qpos[:] = self.d.qpos
        if seed is not None:
            for i, v in zip(self.qadr[a], seed): d.qpos[i] = v
        R_goal = self.goal_rot(yaw); cols = self.dadr[a]
        lo = np.array([m.jnt_range[m.joint(f'{a}_{j}').id][0] for j in ARM_JOINTS]); hi = np.array([m.jnt_range[m.joint(f'{a}_{j}').id][1] for j in ARM_JOINTS])
        jp = np.zeros((3, m.nv)); jr = np.zeros((3, m.nv))
        for _ in range(iters):
            mujoco.mj_kinematics(m, d); mujoco.mj_comPos(m, d)
            p = d.site_xpos[self.site[a]]; R = d.site_xmat[self.site[a]].reshape(3, 3)
            ep = p_goal - p; er = 0.5 * sum(np.cross(R[:, k], R_goal[:, k]) for k in range(3))
            if np.linalg.norm(ep) < 2e-4 and np.linalg.norm(er) < 2e-3: break
            mujoco.mj_jacSite(m, d, jp, jr, self.site[a])
            J = np.vstack([jp[:, cols], wr * jr[:, cols]]); e = np.concatenate([ep, wr * er])
            dq = J.T @ np.linalg.solve(J @ J.T + 2e-4 * np.eye(6), e)
            q = np.clip(np.array([d.qpos[i] for i in self.qadr[a]]) + np.clip(dq, -0.15, 0.15), lo, hi)
            for i, qi in zip(self.qadr[a], q): d.qpos[i] = qi
        return np.array([d.qpos[i] for i in self.qadr[a]])

    def jog(self, a, dp, dyaw):
        pass                                                                                                             
        t0 = self.target[a]; p0, y0 = t0['pos'].copy(), t0['yaw']
        p1 = p0 + dp; p1[2] = max(p1[2], TCP_MIN_Z); y1 = y0 + dyaw
        clipped = bool(p1[2] != (p0 + dp)[2])
                                                                                                                             
                                                                                                           
        pe, ye = p1, y1
        if WOBBLE:
            pe = p1 + self.wob_rng.normal(0.0, WOB['pos_noise'], 3); pe[2] = max(pe[2], TCP_MIN_Z); ye = y1 + self.wob_rng.normal(0.0, math.radians(WOB['yaw_noise_deg']))
        dist = float(np.linalg.norm(pe - p0)); n = max(4, int(math.ceil(max(dist / SPEED, abs(ye - y0) / 1.5) * CTRL_HZ)))
        q = self.joints(a)
        for i in range(1, n + 1):
            s = i / n; q = self.ik(a, p0 + (pe - p0) * s, y0 + (ye - y0) * s, seed=self.d.ctrl[self.arm_act[a]].copy(), iters=60)
            self.d.ctrl[self.arm_act[a]] = q; self.run(1.0 / CTRL_HZ)
        if VIEW == 'robot':                                                                                                     
            q = self.ik(a, pe, ye, seed=self.d.ctrl[self.arm_act[a]].copy(), iters=400); self.d.ctrl[self.arm_act[a]] = q
        if WOBBLE:                                                                                   
            self.run(WOB['settle'])
                                                                                                                         
                                                                                                          
            probe = copy.copy(self.d)
            for _ in range(int(round(0.6 / self.m.opt.timestep))): mujoco.mj_step(self.m, probe)
            err = float(np.linalg.norm(probe.site_xpos[self.site[a]] - p1)); pos, R = self.tcp(a)
        else:
            self.run(0.35)
            pos, R = self.tcp(a); err = float(np.linalg.norm(pos - p1))
        limited = clipped or err > 0.012
        if err > 0.012:                                                                                         
            self.target[a] = {'pos': pos.copy(), 'yaw': y1}; self.d.ctrl[self.arm_act[a]] = self.joints(a); self.run(0.1)
        else:
            self.target[a] = {'pos': p1, 'yaw': y1}
        return limited

    def gripper(self, a, target):
        if target == GRIP_CLOSED: self.counts['grasp_attempts'] += 1
        c0 = float(self.d.ctrl[self.grip_act[a]]); n = int(0.8 * CTRL_HZ)
        for i in range(1, n + 1):
            self.d.ctrl[self.grip_act[a]] = c0 + (target - c0) * min(1.0, i / (n * 0.6)); self.run(1.0 / CTRL_HZ)
        self.run(0.2)

    def act(self, moves):
        pass                                                                         
        self.counts['actions'] += 1; out = []
        if WOBBLE: self.run(WOB['think'])                                                                                                 
        for mv in moves:
            a = ARMS[int(mv['arm'])]; op = mv['op']; label = f'arm {mv["arm"]} {op}'
            if op == 'move':
                dx, dy, dz = (float(mv.get(k) or 0) for k in ('right_cm', 'forward_cm', 'up_cm'))
                dx, dy, dz = (max(-STEP_MAX_CM, min(STEP_MAX_CM, v)) for v in (dx, dy, dz))
                self.counts['moves'] += 1
                lim = self.jog(a, np.array([dx, dy, dz]) / 100.0, 0.0)
                label = f'arm {mv["arm"]} move right {dx:+.1f} cm, forward {dy:+.1f} cm, up {dz:+.1f} cm'
            elif op == 'turn':
                deg = max(-TURN_MAX_DEG, min(TURN_MAX_DEG, float(mv.get('turn_deg') or 0))); self.counts['turns'] += 1
                lim = self.jog(a, np.zeros(3), math.radians(-deg)); label = f'arm {mv["arm"]} turn {deg:+.0f} deg'
            elif op in ('open', 'close'):
                self.gripper(a, GRIP_OPEN if op == 'open' else GRIP_CLOSED); lim = False; label = f'arm {mv["arm"]} {op} gripper'
            elif op == 'home':
                h = self.home[a]; t = self.target[a]
                up = max(0.0, HOME[a][2] - t['pos'][2])
                lim1 = self.jog(a, np.array([0, 0, up]), 0.0) if up > 0.005 else False
                lim = self.jog(a, h['pos'] - self.target[a]['pos'], h['yaw'] - self.target[a]['yaw']) or lim1
            else:
                raise ValueError(f'unknown op {op}')
            if lim: self.counts['limited_moves'] += 1
            out.append(label + (': done' if not lim else ': stopped early (out of reach, at the table-height limit, or blocked)'))
        return out

                                                                                                 
    def judge(self, answer):
        pass                                                                                                                     
                                                                                                                            
                                                                                                              
        c = self.conf
        if c.get('task') != 'C': return super().judge(answer)
        self.run(1.0)
        a = str(answer or '').lower(); m = re.search(r'cup\s*#?\s*(\d+)', a)
        colours = [k for k in COLORS if re.search(r'\b' + k + r'\b', a)]
        numbers = sorted(o['number'] for o in self.objects.values() if o['type'] == 'cup')
        detail = {'answer': answer, 'liftedCups': sorted(self.lifted), 'cubeCup': c.get('cube_cup'), 'cubeColour': c.get('cube_color')}
        if c.get('cube_cup'):
            return {'rightColour': colours == [c['cube_color']], 'rightCup': bool(m) and int(m.group(1)) == c['cube_cup'],
                    'namedCupLifted': c['cube_cup'] in self.lifted}, detail
        return {'answerNone': bool(re.search(r'\bnone\b', a)) and not colours and not m,
                'allCupsLifted': all(n in self.lifted for n in numbers)}, detail

    def agent_image(self, path):
        if VIEW == 'robot':                                                                                               
            from PIL import ImageDraw
            out = Image.new('RGB', (3 * CW, CH + 28), (0, 0, 0)); g = ImageDraw.Draw(out)
            for i, (cam, label) in enumerate((('head', 'head camera'), ('wrist0', 'left wrist camera (arm 0)'), ('wrist1', 'right wrist camera (arm 1)'))):
                self.cam_renderer.update_scene(self.d, camera=cam, scene_option=self.opt); out.paste(Image.fromarray(self.cam_renderer.render()), (i * CW, 28))
                g.text((i * CW + 8, 8), label, fill=(255, 255, 255))
            out.save(path); return path
        self.renderer.update_scene(self.d, camera='overhead_cam', scene_option=self.opt)
        Image.fromarray(self.renderer.render()).save(path); return path


def main():
    sim = Sim()
    for line in sys.stdin:
        if not line.strip(): continue
        req = json.loads(line)
        try:
            if req['cmd'] == 'reset': out = {'ok': True, 'state': sim.reset(req['conf'], req.get('replay_dir'))}
            elif req['cmd'] == 'act':
                f0 = sim.frame_no; res = sim.act(req['moves'])
                out = {'ok': True, 'result': res, 'frames': [f0, sim.frame_no], 'state': sim.summary()}
            elif req['cmd'] == 'image': out = {'ok': True, 'path': sim.agent_image(req['path']), 'state': sim.summary()}
            elif req['cmd'] == 'judge':
                f0 = sim.frame_no; checks, detail = sim.judge(req.get('answer'))
                out = {'ok': True, 'success': all(checks.values()), 'checks': {k: bool(v) for k, v in checks.items()}, 'detail': detail,
                       'counts': sim.counts, 'frames': [f0, sim.frame_no], 'state': sim.summary()}
            else: raise ValueError('unknown command')
        except Exception as e:                
            out = {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        sys.stdout.write(json.dumps(out) + '\n'); sys.stdout.flush()


if __name__ == '__main__':
    main()
