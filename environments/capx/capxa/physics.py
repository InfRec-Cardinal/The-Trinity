                                                                                                    
                                                                                            

                                                                                                                     
                                                                                                                
                                                                                                                    
                                                                                                                    
                                                                                                                     
                                

                                                                                                                   
                                                                                                                   
                                                                                                  
                                                                              
   
import base64
import hashlib
import io
import json
import math
import os
import re
import sys

import mujoco
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCENE = os.path.join(ROOT, 'vendor', 'aloha', 'scene.xml')
LOGO = os.path.join(ROOT, 'branding', 'logo-full-board.png')
CTRL_HZ = 20
MOVE_MAX_S = 100 / CTRL_HZ                                                              
GRIP_S = 30 / CTRL_HZ                                             
JOINT_TOL = 0.02
OPEN_CTRL, CLOSE_CTRL = 0.037, 0.002
                                                                                          
CUBE = 0.04
CUP_H, CUP_RIM, CUP_BASE = 0.075, 0.028, 0.020
LIME_R = 0.018
W, H = 640, 360                                                                                         
REPLAY_FPS = 8
ARMS = ('left', 'right')
JOINTS = ('waist', 'shoulder', 'elbow', 'forearm_roll', 'wrist_angle', 'wrist_rotate')
CAMS = ('overhead_cam', 'wrist_cam_left', 'wrist_cam_right')
COLORS = {'red': (0.80, 0.20, 0.17, 1), 'green': (0.25, 0.62, 0.29, 1), 'blue': (0.18, 0.38, 0.78, 1)}


def quat_mul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def mat2quat(R):
    q = np.zeros(4); mujoco.mju_mat2Quat(q, np.asarray(R, float).reshape(9)); return q


def quat2mat(q):
    m = np.zeros(9); mujoco.mju_quat2Mat(m, np.asarray(q, float) / np.linalg.norm(q)); return m.reshape(3, 3)


def enc(a):
    a = np.ascontiguousarray(a); buf = io.BytesIO(); np.save(buf, a, allow_pickle=False)
    return {'__npy__': base64.b64encode(buf.getvalue()).decode()}


def digest(a): return hashlib.sha1(np.ascontiguousarray(a).tobytes()).hexdigest()


class Sim:
                                                                              
    def build(self, conf):
        spec = mujoco.MjSpec.from_file(SCENE)
        self.objects = {o['id']: o for o in conf['objects']}
        for o in conf['objects']:
            x, y, _ = o['pos']; yaw = o.get('yaw', 0.0)
            q = [math.cos(yaw / 2), 0, 0, math.sin(yaw / 2)]
            if o['type'] == 'cube':
                b = spec.worldbody.add_body(name=o['id'], pos=[x, y, o.get('z0', 0.0) + CUBE / 2 + 0.0005], quat=q); b.add_freejoint()
                b.add_geom(name=o['id'] + '/g', type=mujoco.mjtGeom.mjGEOM_BOX, size=[CUBE / 2] * 3, rgba=COLORS[o['color']], mass=0.06,
                           friction=[1.0, 0.01, 0.001], condim=4)
            elif o['type'] == 'lime':
                b = spec.worldbody.add_body(name='lime', pos=[x, y, LIME_R + 0.0005]); b.add_freejoint()
                b.add_geom(name='lime/g', type=mujoco.mjtGeom.mjGEOM_SPHERE, size=[LIME_R, 0, 0], rgba=[0.55, 0.78, 0.25, 1], mass=0.06,
                           friction=[1.0, 0.01, 0.002], condim=4)
            else:                                                                                                  
                b = spec.worldbody.add_body(name=o['id'], pos=[x, y, CUP_H / 2 + 0.0005]); b.add_freejoint()
                n, slope, rmid = 16, math.atan2(CUP_RIM - CUP_BASE, CUP_H), (CUP_RIM + CUP_BASE) / 2
                for i in range(n):
                    a = 2 * math.pi * i / n
                    qq = quat_mul([math.cos(a / 2), 0, 0, math.sin(a / 2)], [math.cos(-slope / 2), 0, math.sin(-slope / 2), 0])
                    b.add_geom(name=f'{o["id"]}/w{i}', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.004, 2 * math.pi * CUP_RIM / n * 0.60, CUP_H / 2 / math.cos(slope)],
                               pos=[(rmid - 0.002) * math.cos(a), (rmid - 0.002) * math.sin(a), 0], quat=list(qq), rgba=[0.92, 0.90, 0.86, 1], mass=0.003, friction=[1.0, 0.01, 0.001], condim=4)
                b.add_geom(name=f'{o["id"]}/top', type=mujoco.mjtGeom.mjGEOM_CYLINDER, size=[CUP_BASE + 0.002, 0.002, 0], pos=[0, 0, CUP_H / 2 - 0.002],
                           rgba=[0.92, 0.90, 0.86, 1], mass=0.004)
                tex = os.path.join(ROOT, 'branding', f'cup-number-{o["number"]}.png')
                if os.path.exists(tex):
                    spec.add_texture(name=f'num{o["number"]}', type=mujoco.mjtTexture.mjTEXTURE_2D, file=tex)
                    mat = spec.add_material(name=f'num{o["number"]}'); mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = f'num{o["number"]}'
                    b.add_geom(name=f'{o["id"]}/label', type=mujoco.mjtGeom.mjGEOM_BOX, size=[CUP_BASE * 0.8, CUP_BASE * 0.8, 0.0005], pos=[0, 0, CUP_H / 2 + 0.0006],
                               material=f'num{o["number"]}', contype=0, conaffinity=0, mass=0.0001)
                                                                                                         
        if os.path.exists(LOGO):
            spec.add_texture(name='logo', type=mujoco.mjtTexture.mjTEXTURE_2D, file=LOGO)
            mat = spec.add_material(name='logo'); mat.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = 'logo'
                                                                                               
            spec.worldbody.add_geom(name='brand/poster', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.21, 0.004, 0.26], pos=[0, 0.48, 0.42],
                                    quat=[1, 0, 0, 0], material='logo', group=3, contype=0, conaffinity=0)
            for arm, sx in (('left', -1), ('right', 1)):
                spec.worldbody.add_geom(name=f'brand/{arm}', type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.04, 0.002, 0.049], pos=[sx * 0.469, -0.105, 0.075],
                                        quat=[1, 0, 0, 0], material='logo', group=3, contype=0, conaffinity=0)
                                                                                                                            
        for body in spec.bodies:
            if body.name.startswith(('left/', 'right/')): body.gravcomp = 1.0
        self.m = spec.compile(); self.d = mujoco.MjData(self.m)
                                                                                                                   
        key = self.m.key(0); self.d.qpos[:] = self.m.qpos0; self.d.ctrl[:] = key.ctrl
        for j in range(self.m.njnt):
            if self.m.joint(j).name.startswith(('left/', 'right/')): self.d.qpos[self.m.jnt_qposadr[j]] = key.qpos[self.m.jnt_qposadr[j]]
        mujoco.mj_forward(self.m, self.d)

    def reset(self, conf, replay_dir=None):
        self.conf = conf; self.build(conf)
        m = self.m
        self.qadr = {a: [m.jnt_qposadr[m.joint(f'{a}/{j}').id] for j in JOINTS] for a in ARMS}
        self.dadr = {a: [m.jnt_dofadr[m.joint(f'{a}/{j}').id] for j in JOINTS] for a in ARMS}
        self.act = {a: [m.actuator(f'{a}/{j}').id for j in JOINTS] for a in ARMS}
        self.grip_act = {a: m.actuator(f'{a}/gripper').id for a in ARMS}
        self.site = {a: m.site(f'{a}/gripper').id for a in ARMS}
        self.link = {a: m.body(f'{a}/gripper_link').id for a in ARMS}
        self.pads = {a: (set(g for g in range(m.ngeom) if m.geom_bodyid[g] == m.body(f'{a}/left_finger_link').id and (m.geom_contype[g] or m.geom_conaffinity[g])),
                         set(g for g in range(m.ngeom) if m.geom_bodyid[g] == m.body(f'{a}/right_finger_link').id and (m.geom_contype[g] or m.geom_conaffinity[g]))) for a in ARMS}
        self.robot_bodies = {i for i in range(m.nbody) if m.body(i).name.startswith(('left/', 'right/'))}
        self.body_of_obj = {k: m.body(k).id for k in self.objects}
        self.geom_obj = {g: k for k, b in self.body_of_obj.items() for g in range(m.ngeom) if m.geom_bodyid[g] == b}
        self.table_geom = m.geom('table').id
                                                                                                                                   
        mujoco.mj_forward(m, self.d)
        self.tcp_in_link = {}
        for a in ARMS:
            Rl = self.d.xmat[self.link[a]].reshape(3, 3)
            yl = Rl.T @ (self.d.site_xpos[m.site(f'{a}/left_finger').id] - self.d.site_xpos[m.site(f'{a}/right_finger').id])
            z = np.array([1.0, 0, 0]); y = yl - z * (yl @ z); y /= np.linalg.norm(y); x = np.cross(y, z)
            self.tcp_in_link[a] = np.stack([x, y, z], axis=1)                                             
        self.renderer = mujoco.Renderer(m, H, W)
        self.hide_brand = mujoco.MjvOption(); self.hide_brand.geomgroup[3] = 0
        self.show_brand = mujoco.MjvOption(); self.show_brand.geomgroup[3] = 1
        self.replay_dir = replay_dir; self.frame_no = 0; self.next_frame = 0.0
        if replay_dir: os.makedirs(replay_dir, exist_ok=True)
        self.t = 0.0; self.cache = {}; self.lifted = set(); self.rng = np.random.default_rng(sum(map(ord, conf['id'])) * 7919)
        self.counts = {'observations': 0, 'segmentations': 0, 'grasp_plans': 0, 'ik_calls': 0, 'moves': 0, 'grasp_attempts': 0}
        self.start = {k: self.pos(k).copy() for k in self.objects}
        self.run(0.5)
        return self.summary()

                                                                              
    def pos(self, k): return self.d.xpos[self.body_of_obj[k]]
    def quat(self, k): return self.d.xquat[self.body_of_obj[k]]
    def joints(self, a): return np.array([self.d.qpos[i] for i in self.qadr[a]])
    def tcp(self, a):
        Rl = self.d.xmat[self.link[a]].reshape(3, 3); return self.d.site_xpos[self.site[a]].copy(), Rl @ self.tcp_in_link[a]
    def summary(self):
        return {'t': round(self.t, 3), 'arms': {a: {'joints': [round(float(v), 4) for v in self.joints(a)], 'tcp': [round(float(v), 4) for v in self.tcp(a)[0]],
                'gripper': round(float(self.d.ctrl[self.grip_act[a]]), 4)} for a in ARMS},
                'objects': {k: {'pos': [round(float(v), 4) for v in self.pos(k)], 'quat': [round(float(v), 4) for v in self.quat(k)]} for k in self.objects}}
    def contacts_of(self, body):
        out = set()
        for i in range(self.d.ncon):
            c = self.d.contact[i]
            if self.m.geom_bodyid[c.geom1] == body: out.add(int(c.geom2))
            if self.m.geom_bodyid[c.geom2] == body: out.add(int(c.geom1))
        return out
    def held(self):
        out = {}
        for k, b in self.body_of_obj.items():
            g = self.contacts_of(b)
            for a in ARMS:
                if g & self.pads[a][0] and g & self.pads[a][1]: out[k] = a
        return out
    def bottom(self, k):
        o = self.objects[k]; R = quat2mat(self.quat(k)); p = self.pos(k)
        if o['type'] == 'cube': return float(p[2] - CUBE / 2 * np.abs(R[2]).sum())
        if o['type'] == 'cup': return float(min(p[2] + R[2] @ np.array([math.cos(a) * CUP_RIM, math.sin(a) * CUP_RIM, -CUP_H / 2]) for a in np.linspace(0, 2 * math.pi, 16)))
        return float(p[2] - LIME_R)
    def upright_cup(self, k): return quat2mat(self.quat(k))[2, 2] > 0.8
    def lime_covered(self):
        if 'lime' not in self.objects: return True
        lp = self.pos('lime')
        for k, o in self.objects.items():
            if o['type'] == 'cup' and self.upright_cup(k):
                c = self.pos(k)
                if math.hypot(c[0] - lp[0], c[1] - lp[1]) < CUP_RIM - 0.004 and self.bottom(k) < 2 * LIME_R: return True
        return False

                                                                                                   
    def run(self, seconds):
        n = max(1, int(round(seconds / self.m.opt.timestep)))
        for _ in range(n):
            mujoco.mj_step(self.m, self.d); self.t += self.m.opt.timestep
            if self.t >= self.next_frame:
                self.next_frame = self.t + 1.0 / REPLAY_FPS
                for k, o in self.objects.items():
                    if o['type'] == 'cup' and self.bottom(k) >= 0.03: self.lifted.add(o['number'])
                if self.replay_dir: self.replay_frame()
    def replay_frame(self):
        self.renderer.update_scene(self.d, camera=self.replay_cam(), scene_option=self.show_brand)
        Image.fromarray(self.renderer.render()).save(os.path.join(self.replay_dir, f'{self.frame_no:06d}.jpg'), quality=80)
        self.frame_no += 1
    def replay_cam(self):
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = [0, 0.10, 0.16]; cam.distance = 1.25; cam.azimuth = 90; cam.elevation = -28
        return cam

                                                                                
    def cam_pose(self, name):
        cid = self.m.camera(name).id; R = self.d.cam_xmat[cid].reshape(3, 3) @ np.diag([1, -1, -1])                          
        T = np.eye(4); T[:3, :3] = R; T[:3, 3] = self.d.cam_xpos[cid]; return T
    def intrinsics(self, name):
        cid = self.m.camera(name).id; f = self.m.cam_intrinsic[cid][:2]; s = self.m.cam_sensorsize[cid]
        return np.array([[f[0] / s[0] * W, 0, W / 2], [0, f[1] / s[1] * H, H / 2], [0, 0, 1.0]])
    def render(self, name):
        r = self.renderer
        r.update_scene(self.d, camera=name, scene_option=self.hide_brand); rgb = r.render().copy()
        r.enable_depth_rendering(); r.update_scene(self.d, camera=name, scene_option=self.hide_brand); depth = r.render().copy(); r.disable_depth_rendering()
        r.enable_segmentation_rendering(); r.update_scene(self.d, camera=name, scene_option=self.hide_brand); seg = r.render().copy(); r.disable_segmentation_rendering()
        inst = np.zeros((H, W), np.int32)                                                                        
        ids = list(self.objects)
        geom_ids = np.where(seg[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM), seg[..., 0], -1)
        for g, k in self.geom_obj.items(): inst[geom_ids == g] = ids.index(k) + 1
        return rgb, depth.astype(np.float32), inst
    def get_observation(self):
        self.counts['observations'] += 1; obs = {}
        for name in CAMS:
            rgb, depth, inst = self.render(name)
            K, pose = self.intrinsics(name), self.cam_pose(name)
            self.cache[digest(rgb)] = self.cache[digest(depth)] = {'name': name, 'rgb': rgb, 'depth': depth, 'inst': inst, 'K': K, 'pose': pose}
            obs[name] = {'images': {'rgb': enc(rgb), 'depth': enc(depth)}, 'intrinsics': enc(K), 'pose_mat': enc(pose)}
        while len(self.cache) > 60: self.cache.pop(next(iter(self.cache)))
        return obs
    def lookup(self, h, what):
        if h not in self.cache: raise ValueError(f'{what} must be an image returned by get_observation() (images edited in the program are not supported)')
        return self.cache[h]

                                                                                                    
    def match(self, text):
        s = text.lower(); objs = list(self.objects.values())
        color = next((c for c in COLORS if c in s), None); num = next((ch for ch in s if ch in '12345'), None)
        if any(w in s for w in ('lime', 'fruit', 'ball')): return [o for o in objs if o['type'] == 'lime']
        if 'cup' in s or 'mug' in s: return [o for o in objs if o['type'] == 'cup' and (num is None or str(o['number']) == num)]
        if any(w in s for w in ('cube', 'block', 'box')) or color: return [o for o in objs if o['type'] == 'cube' and (color is None or o['color'] == color)]
        return []
    def noisy_mask(self, mask):
        if mask.sum() < 30: return mask
        m = mask.copy(); r = self.rng.random()
        if r < 0.3:                      
            g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; m = g
        elif r < 0.6:                       
            e = m.copy(); e[1:] &= m[:-1]; e[:-1] &= m[1:]; e[:, 1:] &= m[:, :-1]; e[:, :-1] &= m[:, 1:]; m = e
        return m
    def segment_text(self, h, text):
        self.counts['segmentations'] += 1
        c = self.lookup(h, 'rgb'); ids = list(self.objects); out = []
        for o in self.match(str(text)):
            mask = c['inst'] == ids.index(o['id']) + 1
            if mask.sum() < 40: continue                                                          
            ys, xs = np.where(mask); frac = min(1.0, mask.sum() / 900)
            out.append({'mask': self.noisy_mask(mask), 'box': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
                        'score': round(float(np.clip(0.55 + 0.4 * frac + self.rng.normal(0, 0.03), 0.06, 0.99)), 3)})
        out.sort(key=lambda r: -r['score'])
        return [{**r, 'mask': enc(r['mask'])} for r in out]
    def segment_point(self, h, xy):
        self.counts['segmentations'] += 1
        c = self.lookup(h, 'rgb'); x, y = int(round(float(xy[0]))), int(round(float(xy[1])))
        if not (0 <= x < W and 0 <= y < H): return []
        i = c['inst'][y, x]
        mask = (c['inst'] == i) if i > 0 else self.region(c, x, y)
        return [{'mask': enc(self.noisy_mask(mask)), 'score': round(float(0.9 if i > 0 else 0.3), 3)}]
    def region(self, c, x, y):                                                                            
        d = c['depth']; return np.abs(d - d[y, x]) < 0.01
    def molmo(self, h, text):
        c = self.lookup(h, 'image'); ids = list(self.objects); res = {}
        cands = [o for o in self.match(str(text)) if (c['inst'] == ids.index(o['id']) + 1).sum() >= 40]
        if not cands: return {str(text): [None, None]}
        o = cands[0]; ys, xs = np.where(c['inst'] == ids.index(o['id']) + 1)
        return {str(text): [int(np.median(xs) + self.rng.normal(0, 1.5)), int(np.median(ys) + self.rng.normal(0, 1.5))]}

    def backproject(self, depth, K, mask=None):
        v, u = np.where(mask) if mask is not None else np.indices(depth.shape).reshape(2, -1)
        z = depth[v, u]; ok = (z > 0.05) & (z < 3.0); u, v, z = u[ok], v[ok], z[ok]
        return np.stack([(u - K[0, 2]) * z / K[0, 0], (v - K[1, 2]) * z / K[1, 1], z], axis=1)
    def plan_grasp(self, h, K, mask):
        pass                                                                                                                
                                                                                                                   
        self.counts['grasp_plans'] += 1
        c = self.lookup(h, 'depth'); K = np.asarray(K, float); mask = np.asarray(mask, bool)
        if mask.sum() < 20: return enc(np.zeros((0, 4, 4))), enc(np.zeros(0))
        T = c['pose']; to_w = lambda P: P @ T[:3, :3].T + T[:3, 3]
        obj = to_w(self.backproject(c['depth'], K, mask)); scene = to_w(self.backproject(c['depth'][::3, ::3], K * np.array([[1 / 3], [1 / 3], [1]])))
        scene = scene[scene[:, 2] > 0.004]
                                                              
        lo, hi = obj.min(0) - 0.004, obj.max(0) + 0.004
        scene = scene[~np.all((scene >= lo) & (scene <= hi), axis=1)]
        top = np.percentile(obj[:, 2], 95)
                                                                                                                      
        topf = obj[obj[:, 2] > top - 0.008]
        if len(topf) < 15: topf = obj
        ctr = np.median(topf[:, :2], axis=0); xy = topf[:, :2] - ctr
                                                                                                        
        widths = [(np.ptp(xy @ np.array([math.cos(a), math.sin(a)])), a) for a in np.radians(np.arange(0, 180, 3))]
        th = min(widths)[1]
                                                                                                              
        u1, u2 = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
        a1, a2 = xy @ u1, xy @ u2
        ctr = ctr + u1 * (a1.min() + a1.max()) / 2 + u2 * (a2.min() + a2.max()) / 2
        xy = topf[:, :2] - ctr
        yaws = [th, th + math.pi / 2, th + math.pi / 4, th - math.pi / 4]
        zlow = np.percentile(obj[:, 2], 3)                                                                                 
        depth_in = min(0.025, max(0.010, (top - zlow) * 0.45))                                          
        poses, scores = [], []
        for yaw in yaws:
            for dz in (0.0, -0.008):
                p = np.array([ctr[0], ctr[1], max(0.018, zlow + 0.012, top - depth_in + dz)])
                ycl = np.array([math.cos(yaw), math.sin(yaw), 0.0]); z = np.array([0, 0, -1.0]); x = np.cross(ycl, z)
                R = np.stack([x, ycl, z], axis=1)
                                                                                                                             
                free = True
                for s in (-1, 1):
                    f = p + R @ np.array([0, s * 0.0425, 0])
                    near = scene[(np.abs((scene - f) @ ycl) < 0.016) & (np.abs((scene - f) @ x) < 0.014) & (scene[:, 2] > f[2] - 0.018) & (scene[:, 2] < f[2] + 0.05)]
                    if len(near) > 3: free = False
                band = obj[(obj[:, 2] > p[2] - 0.016) & (obj[:, 2] < p[2] + 0.03)]                                     
                width = np.ptp((band[:, :2] - ctr) @ ycl[:2]) if len(band) > 5 else np.ptp(xy @ ycl[:2]); fits = width < 0.054
                if not free or not fits: continue
                Tw = np.eye(4); Tw[:3, :3] = R; Tw[:3, 3] = p
                Tc = np.linalg.inv(T) @ Tw
                poses.append(Tc); scores.append(float(np.clip(0.9 - 0.25 * width / 0.054 + self.rng.normal(0, 0.02) - (0.05 if dz else 0), 0.05, 0.99)))
        order = np.argsort(scores)[::-1]
        return enc(np.array([poses[i] for i in order]).reshape(-1, 4, 4)), enc(np.array([scores[i] for i in order]))

                                                                                      
    def solve_ik(self, a, position, quat_wxyz):
        pass                                                                                                         
                                                                                                        
        self.counts['ik_calls'] += 1
        m = self.m; d = mujoco.MjData(m); d.qpos[:] = self.d.qpos; mujoco.mj_forward(m, d)
        p_goal = np.asarray(position, float).reshape(3); R_tcp = quat2mat(np.asarray(quat_wxyz, float).reshape(4))
        R_goal = R_tcp @ self.tcp_in_link[a].T                                                       
        jac_p = np.zeros((3, m.nv)); jac_r = np.zeros((3, m.nv)); cols = self.dadr[a]
        lo = np.array([m.jnt_range[m.joint(f'{a}/{j}').id][0] for j in JOINTS]); hi = np.array([m.jnt_range[m.joint(f'{a}/{j}').id][1] for j in JOINTS])
        for _ in range(300):
            mujoco.mj_kinematics(m, d); mujoco.mj_comPos(m, d)
            p = d.site_xpos[self.site[a]]; Rl = d.xmat[self.link[a]].reshape(3, 3)
            ep = p_goal - p
            er = 0.5 * (np.cross(Rl[:, 0], R_goal[:, 0]) + np.cross(Rl[:, 1], R_goal[:, 1]) + np.cross(Rl[:, 2], R_goal[:, 2]))
            if np.linalg.norm(ep) < 1e-4 and np.linalg.norm(er) < 1e-3: break
            mujoco.mj_jacSite(m, d, jac_p, jac_r, self.site[a])
            J = np.vstack([jac_p[:, cols], 0.3 * jac_r[:, cols]]); e = np.concatenate([ep, 0.3 * er])
            dq = J.T @ np.linalg.solve(J @ J.T + 1e-4 * np.eye(6), e)
            q = np.array([d.qpos[i] for i in self.qadr[a]]) + np.clip(dq, -0.2, 0.2)
            for i, qi in zip(self.qadr[a], np.clip(q, lo, hi)): d.qpos[i] = qi
        return [float(d.qpos[i]) for i in self.qadr[a]]

    def move(self, targets):
        pass                                                                                                           
                                                                                                                       
                                                                                   
        self.counts['moves'] += 1
        goal, start = {}, {}
        for a, q in targets.items():
            lo = self.m.actuator_ctrlrange[self.act[a], 0]; hi = self.m.actuator_ctrlrange[self.act[a], 1]
            goal[a] = np.clip(np.asarray(q, float).reshape(6), lo, hi); start[a] = self.d.ctrl[self.act[a]].copy()
        span = max(float(np.max(np.abs(goal[a] - start[a]))) for a in goal)
        n = max(1, int(math.ceil(max(0.3, span / 1.0) * CTRL_HZ)))
        for i in range(1, n + 1):
            for a in goal: self.d.ctrl[self.act[a]] = start[a] + (goal[a] - start[a]) * i / n
            self.run(1.0 / CTRL_HZ)
        steps = 0
        while steps < 100:
            if all(np.linalg.norm(self.joints(a) - goal[a]) < JOINT_TOL for a in goal): break
            self.run(1.0 / CTRL_HZ); steps += 1
        self.run(0.1)
        return None
    def gripper(self, a, target):
        if target == CLOSE_CTRL: self.counts['grasp_attempts'] += 1
        c0 = float(self.d.ctrl[self.grip_act[a]]); n = int(GRIP_S * CTRL_HZ)
        for i in range(1, n + 1):
            self.d.ctrl[self.grip_act[a]] = c0 + (target - c0) * min(1.0, i / (n * 0.5)); self.run(1.0 / CTRL_HZ)
        return None

                                                                                                                                  
    def judge(self, answer):
        c = self.conf; task = c['task']
        if task == 'T1':
            k = c['target']; ok = []
            for _ in range(4):
                ok.append(k in self.held() and self.bottom(k) >= 0.04); self.run(1.0)
            return {'rightCube': k in self.held(), 'bottomAtLeast4cm': self.bottom(k) >= 0.04, 'held3s': all(ok)}, {'held': self.held(), 'bottomCm': round(self.bottom(k) * 100, 1)}
        if task == 'T2':
            top, bot = c['top'], c['bottom']; third = next(k for k, o in self.objects.items() if o['type'] == 'cube' and k not in (top, bot))
            def on(a_, b_):
                pa, pb = self.pos(a_), self.pos(b_)
                return math.hypot(pa[0] - pb[0], pa[1] - pb[1]) < CUBE * 0.6 and CUBE * 0.8 < self.bottom(a_) < CUBE * 1.4 and self.body_of_obj[b_] in {int(self.m.geom_bodyid[g]) for g in self.contacts_of(self.body_of_obj[a_])}
            before = on(top, bot); released = top not in self.held(); self.run(3.0)
            stays = on(top, bot) and top not in self.held(); moved = float(np.linalg.norm(self.pos(bot)[:2] - self.start[bot][:2]))
            third_stacked = self.bottom(third) > 0.02 or any(on(x, third) for x in self.objects if x != third and self.objects[x]['type'] == 'cube')
            return {'topOnBottom': before, 'released': released, 'staysAfterRelease': stays, 'bottomAtOriginalPosition': moved <= 0.02 and self.bottom(bot) < 0.01, 'thirdNotStacked': not third_stacked}, {'bottomMovedCm': round(moved * 100, 1)}
        if task in ('H1', 'H2'):
            def on(a_, b_):
                pa, pb = self.pos(a_), self.pos(b_)
                return math.hypot(pa[0] - pb[0], pa[1] - pb[1]) < CUBE * 0.6 and self.bottom(a_) - self.bottom(b_) > CUBE * 0.8 and self.bottom(a_) - self.bottom(b_) < CUBE * 1.4 \
                    and self.body_of_obj[b_] in {int(self.m.geom_bodyid[g]) for g in self.contacts_of(self.body_of_obj[a_])}
            pairs = [(c['top'], c['bottom'])] if task == 'H1' else [(c['middle'], c['bottom']), (c['top'], c['middle'])]
            before = all(on(a_, b_) for a_, b_ in pairs); held = self.held(); released = not any(a_ in held for a_, _ in pairs)
            self.run(3.0)
            stays = all(on(a_, b_) for a_, b_ in pairs) and not any(a_ in self.held() for a_, _ in pairs)
            checks = {'stacked': before, 'released': released, 'staysAfterRelease': stays}
            if task == 'H1': checks['bottomOnTable'] = self.bottom(c['bottom']) < 0.01
            else: checks['bottomOnTable'] = self.bottom(c['bottom']) < 0.01
            return checks, {'heights': {k: round(self.bottom(k), 3) for k in self.objects}}
        self.run(1.0)
        visible = 'lime' in self.objects and not self.lime_covered(); lc = c.get('lime_cup')
        if task == 'T3':
            cup = f'cup{lc}'; lp, cp = self.pos('lime'), self.pos(cup)
            away = math.hypot(lp[0] - cp[0], lp[1] - cp[1]) >= CUP_RIM + LIME_R and cup not in self.held()
            return {'limeVisible': visible, 'cupSetAside': away}, {'liftedCups': sorted(self.lifted)}
        a = str(answer or '').lower(); m = re.search(r'cup\s*#?\s*([1-5])', a)
        if lc: return {'limeVisible': visible, 'answerYes': 'yes' in a, 'rightCup': bool(m) and int(m.group(1)) == lc}, {'answer': answer, 'liftedCups': sorted(self.lifted)}
        numbers = sorted(o['number'] for o in self.objects.values() if o['type'] == 'cup')
        return {'answerNone': bool(re.search(r'\bnone\b', a)) and 'yes' not in a, 'allCupsLifted': all(n in self.lifted for n in numbers)}, {'answer': answer, 'liftedCups': sorted(self.lifted)}

                                                                                                                    
    def agent_image(self, path):
        tiles = {}
        for name in CAMS:
            self.renderer.update_scene(self.d, camera=name, scene_option=self.hide_brand); tiles[name] = Image.fromarray(self.renderer.render())
        out = Image.new('RGB', (W + W // 2, H + 24), (0, 0, 0))
        out.paste(tiles['overhead_cam'], (0, 24)); out.paste(tiles['wrist_cam_left'].resize((W // 2, H // 2)), (W, 24)); out.paste(tiles['wrist_cam_right'].resize((W // 2, H // 2)), (W, 24 + H // 2))
        from PIL import ImageDraw
        g = ImageDraw.Draw(out); g.text((6, 6), 'overhead camera', fill=(255, 255, 255)); g.text((W + 6, 6), 'wrist camera left (arm 0) / right (arm 1)', fill=(255, 255, 255))
        out.save(path); return path


API = {'get_observation', 'segment_sam3_text_prompt', 'segment_sam3_point_prompt', 'point_prompt_molmo', 'plan_grasp',
       'solve_ik_arm0', 'solve_ik_arm1', 'move_to_joints_both', 'move_to_joints_arm0', 'move_to_joints_arm1',
       'open_gripper_arm0', 'close_gripper_arm0', 'open_gripper_arm1', 'close_gripper_arm1'}


def dispatch(sim, name, a):
    if name == 'get_observation': return sim.get_observation()
    if name == 'segment_sam3_text_prompt': return sim.segment_text(a[0], a[1])
    if name == 'segment_sam3_point_prompt': return sim.segment_point(a[0], a[1])
    if name == 'point_prompt_molmo': return sim.molmo(a[0], a[1])
    if name == 'plan_grasp':
        bits = np.unpackbits(np.frombuffer(base64.b64decode(a[2]['bits']), np.uint8))[:a[2]['n']]
        return sim.plan_grasp(a[0], a[1], bits.reshape(a[2]['shape']).astype(bool))
    if name == 'solve_ik_arm0': return sim.solve_ik('left', a[0], a[1])
    if name == 'solve_ik_arm1': return sim.solve_ik('right', a[0], a[1])
    if name == 'move_to_joints_both': return sim.move({'left': a[0], 'right': a[1]})
    if name == 'move_to_joints_arm0': return sim.move({'left': a[0]})
    if name == 'move_to_joints_arm1': return sim.move({'right': a[0]})
    if name == 'open_gripper_arm0': return sim.gripper('left', OPEN_CTRL)
    if name == 'close_gripper_arm0': return sim.gripper('left', CLOSE_CTRL)
    if name == 'open_gripper_arm1': return sim.gripper('right', OPEN_CTRL)
    if name == 'close_gripper_arm1': return sim.gripper('right', CLOSE_CTRL)
    raise ValueError(f'unknown function {name}')


def main():
    sim = Sim()
    for line in sys.stdin:
        if not line.strip(): continue
        req = json.loads(line)
        try:
            if req['cmd'] == 'reset': out = {'ok': True, 'state': sim.reset(req['conf'], req.get('replay_dir'))}
            elif req['cmd'] == 'call':
                f0 = sim.frame_no
                if req['name'] not in API: raise ValueError(f'unknown function {req["name"]}')
                res = dispatch(sim, req['name'], req.get('args', []))
                out = {'ok': True, 'result': res, 'frames': [f0, sim.frame_no], 'state': sim.summary()}
            elif req['cmd'] == 'image': out = {'ok': True, 'path': sim.agent_image(req['path']), 'state': sim.summary()}
            elif req['cmd'] == 'judge':
                f0 = sim.frame_no; checks, detail = sim.judge(req.get('answer'))
                out = {'ok': True, 'success': all(checks.values()), 'checks': {k: bool(v) for k, v in checks.items()}, 'detail': detail, 'counts': sim.counts, 'frames': [f0, sim.frame_no], 'state': sim.summary()}
            else: raise ValueError('unknown command')
        except Exception as e:                
            out = {'ok': False, 'error': f'{type(e).__name__}: {e}'}
        sys.stdout.write(json.dumps(out) + '\n'); sys.stdout.flush()


if __name__ == '__main__':
    main()
