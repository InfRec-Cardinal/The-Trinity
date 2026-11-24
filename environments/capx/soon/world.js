                                                                                                               
                                                                                                           
import * as THREE from 'three';
import {firstReachObject, judgeReach} from './reach-rule.mjs';
import { ROBOT, ACTIONS, ACTION_BUDGET, WALLS, FURNITURE, START_POSES, TASKS, SUCCESS, DOORWAY, REACH } from './layout.js';

const WALL_H = 2.8, WALL_T = 0.10, DEG = Math.PI / 180;

                                                                                         
function canvasTexture(w, h, draw, repeat = [1, 1]) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat); t.anisotropy = 4; return t;
}
function woodFloor() {
  return canvasTexture(512, 512, (g, w, h) => {
    const rnd = mulberry(7);
    for (let row = 0; row < 8; row++) {
      let x = -rnd() * 200;
      while (x < w) {
        const len = 160 + rnd() * 160, base = 120 + rnd() * 40;
        g.fillStyle = `rgb(${base + 40},${base - 15},${base - 60})`; g.fillRect(x, row * 64, len, 64);
        for (let k = 0; k < 18; k++) {          
          g.strokeStyle = `rgba(70,40,15,${0.08 + rnd() * 0.12})`; g.lineWidth = 1 + rnd() * 2;
          const y = row * 64 + rnd() * 64; g.beginPath(); g.moveTo(x, y); g.bezierCurveTo(x + len / 3, y + rnd() * 6 - 3, x + 2 * len / 3, y + rnd() * 6 - 3, x + len, y); g.stroke();
        }
        g.strokeStyle = 'rgba(60,35,15,0.55)'; g.lineWidth = 2; g.strokeRect(x, row * 64, len, 64);
        x += len;
      }
    }
  }, [13, 13]);
}
function stripedGlass() {
  return canvasTexture(512, 256, (g, w, h) => {
    g.fillStyle = '#6f7a80'; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(255,255,255,0.18)'; g.fillRect(0, 0, w, h);
    g.strokeStyle = 'rgba(235,240,240,0.85)'; g.lineWidth = 5;
    for (let i = -4; i < 10; i++) { g.beginPath(); g.moveTo(i * 70, h * 0.85); g.lineTo(i * 70 + 120, h * 0.15); g.stroke(); }
    g.strokeStyle = 'rgba(20,20,20,0.8)'; g.lineWidth = 6; for (let x = 0; x <= w; x += 128) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); }
  }, [3, 1]);
}
function cardboard() {
  return canvasTexture(128, 128, (g, w, h) => {
    g.fillStyle = '#b48552'; g.fillRect(0, 0, w, h); g.fillStyle = '#c99a63'; g.fillRect(0, 56, w, 16);
    g.fillStyle = '#d23b3b'; g.beginPath(); g.arc(90, 95, 13, 0, 7); g.fill(); g.fillStyle = '#fff'; g.font = 'bold 11px sans-serif'; g.fillText('易碎', 79, 99);
  });
}
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

                                                                                    
const M = {};
function mat(key, make) { return M[key] ??= make(); }
const std = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.75, metalness: 0.0, ...extra });

function addBox(parent, [cx, cy, cz], [sx, sy, sz], material, name) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), material); m.position.set(cx, cy, cz); m.name = name ?? ''; m.castShadow = m.receiveShadow = true; parent.add(m); return m;
}
function addCyl(parent, [cx, cy, cz], rTop, rBot, h, material, seg = 24) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBot, h, seg), material); m.position.set(cx, cy, cz); m.castShadow = m.receiveShadow = true; parent.add(m); return m;
}

function buildWall(scene, [x0, z0, x1, z1, kind]) {
  const len = Math.hypot(x1 - x0, z1 - z0), cx = (x0 + x1) / 2, cz = (z0 + z1) / 2, rot = Math.atan2(z1 - z0, x1 - x0);
  const g = new THREE.Group(); g.position.set(cx, 0, cz); g.rotation.y = -rot; scene.add(g);
  const white = mat('white', () => std(0xeceae4));
  if (kind === 'white') addBox(g, [0, WALL_H / 2, 0], [len, WALL_H, WALL_T], white);
  if (kind === 'pillar') { addBox(g, [0, WALL_H / 2, 0], [len, WALL_H, 0.16], mat('woodpanel', () => std(0xa8703c))); addBox(g, [0, 1.45, -0.09], [0.12, 0.08, 0.02], white); }
  if (kind === 'door') {
    addBox(g, [0, 2.2 + (WALL_H - 2.2) / 2, 0], [len, WALL_H - 2.2, WALL_T], mat('darkframe', () => std(0x24272b)));
    addBox(g, [0, 1.1, 0], [len, 2.2, 0.06], mat('darkdoor', () => std(0x15171a, { roughness: 0.35 })), 'door');
    addBox(g, [len / 2 - 0.12, 1.05, -0.05], [0.03, 0.35, 0.03], mat('handle', () => std(0xb5b5b5, { metalness: 0.8, roughness: 0.3 })));
    addBox(g, [-len / 2 + 0.04, 1.1, -0.04], [0.06, 2.2, 0.06], mat('darkframe'));
  }
  if (kind === 'glass') {
    addBox(g, [0, WALL_H / 2, 0], [len, WALL_H, 0.04], mat('glass', () => std(0xffffff, { map: stripedGlass(), roughness: 0.15, metalness: 0.1 })));
    addBox(g, [0, 0.03, 0], [len, 0.06, 0.08], mat('darkframe'));
                                           
    for (let i = 0; i < 5; i++) addBox(g, [-len / 2 + 0.6 + i * 1.05, 0.45, 0.6], [0.6, 0.9, 0.5], mat('behind', () => std(0x2a2c30)));
  }
}

function buildDesk(scene, f) {
  const [cx, cz, sx, sz, h] = f.box, g = new THREE.Group(); g.position.set(cx, 0, cz); scene.add(g);
  addBox(g, [0, h - 0.015, 0], [sx, 0.03, sz], mat('desktop', () => std(0xf1e9de)), f.id);
  const legM = mat('leg', () => std(0xf4f4f2));
  for (const sxn of [-1, 1]) for (const szn of [-1, 1]) {
    const leg = addBox(g, [sxn * (sx / 2 - 0.08), (h - 0.03) / 2, szn * (sz / 2 - 0.12)], [0.05, h - 0.03, 0.05], legM);
    leg.rotation.z = sxn * 0.10;
  }
  return g;
}
function buildMonitor(scene, x, z, yawDeg, w = 0.62) {
  const g = new THREE.Group(); g.position.set(x, 0.75, z); g.rotation.y = yawDeg * DEG; scene.add(g);
  const blk = mat('monitor', () => std(0x111213, { roughness: 0.4 }));
  addBox(g, [0, 0.30, 0], [w, 0.38, 0.03], blk); addBox(g, [0, 0.08, -0.05], [0.04, 0.16, 0.04], blk); addBox(g, [0, 0.01, -0.05], [0.24, 0.02, 0.18], blk);
}
function buildChair(scene, f) {
  const [x, z] = f.at, g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = (f.yawDeg ?? 0) * DEG; scene.add(g);
  const grey = mat('chairgrey', () => std(0x5d6166)), mesh = mat('chairmesh', () => std(0x6f757b, { roughness: 0.9 })), blk = mat('chairblk', () => std(0x1c1d1f));
  addBox(g, [0, 0.47, 0], [0.48, 0.07, 0.46], grey, f.id);
  addBox(g, [0, 0.82, -0.22], [0.46, 0.58, 0.04], mesh, f.id).rotation.x = -0.12;
  addCyl(g, [0, 0.27, 0], 0.025, 0.025, 0.36, blk);
  for (let k = 0; k < 5; k++) { const leg = addBox(g, [Math.sin(k * 1.2566) * 0.16, 0.06, Math.cos(k * 1.2566) * 0.16], [0.04, 0.03, 0.32], blk); leg.rotation.y = k * 1.2566; }
  for (const s of [-1, 1]) addBox(g, [s * 0.25, 0.64, 0.0], [0.04, 0.03, 0.30], blk);
}
function buildFan(scene, f) {
  const [x, z] = f.at, g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = 200 * DEG; scene.add(g);
  const w = mat('fanwhite', () => std(0xfbfbfb, { roughness: 0.5 }));
  addCyl(g, [0, 0.02, 0], 0.17, 0.18, 0.04, w, 32); addCyl(g, [0, 0.45, 0], 0.018, 0.018, 0.86, w);
  const head = new THREE.Group(); head.position.set(0, f.height - 0.14, 0); g.add(head);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.012, 8, 40), w); head.add(ring);
  const disc = new THREE.Mesh(new THREE.CircleGeometry(0.165, 40), new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, side: THREE.DoubleSide })); disc.name = f.id; head.add(disc);
  addCyl(head, [0, 0, -0.06], 0.07, 0.07, 0.10, w).rotation.x = Math.PI / 2;
  for (let k = 0; k < 7; k++) { const b = addBox(head, [0, 0, 0.005], [0.30, 0.004, 0.06], w); b.rotation.z = k * Math.PI / 7; }
}
function buildBin(scene, f) { addCyl(scene, [f.at[0], 0.19, f.at[1]], 0.16, 0.13, 0.38, mat('bin', () => std(0x161616, { roughness: 0.6 }))).name = f.id; }
function buildJug(scene, f) {
  const m = mat('jug', () => new THREE.MeshStandardMaterial({ color: 0x5ea6e8, transparent: true, opacity: 0.75, roughness: 0.2 }));
  addCyl(scene, [f.at[0], 0.24, f.at[1]], 0.14, 0.14, 0.42, m).name = f.id; addCyl(scene, [f.at[0], 0.49, f.at[1]], 0.04, 0.10, 0.10, m);
  addCyl(scene, [f.at[0], 0.56, f.at[1]], 0.035, 0.035, 0.05, mat('cap', () => std(0x2a62c9)));
}
function buildBoxes(scene, f) {
  const [cx, cz, sx, sz, h] = f.box, m = mat('cardboard', () => std(0xffffff, { map: cardboard() }));
  const n = Math.max(1, Math.round(h / 0.4));
  for (let i = 0; i < n; i++) addBox(scene, [cx + (i % 2 ? 0.03 : -0.03), (i + 0.5) * h / n, cz], [sx * (i % 2 ? 0.9 : 1), h / n - 0.01, sz * (i % 2 ? 0.92 : 1)], m, f.id);
}
function buildCabinet(scene, f) {
  const [cx, cz, sx, sz, h] = f.box;
  addBox(scene, [cx, h / 2, cz], [sx, h, sz], mat('cab', () => std(0xf7f7f5)), f.id);
  for (let k = 1; k < 3; k++) addBox(scene, [cx, k * h / 3, cz - sz / 2 - 0.002], [sx * 0.6, 0.015, 0.005], mat('cabline', () => std(0x4f6f8f)));
}
function buildPerson(scene, f) {
  const [x, z] = f.at, cloth = mat('cloth', () => std(0x3d4652)), skin = mat('skin', () => std(0xd9b08c));
  addBox(scene, [x, 0.80, z - 0.05], [0.40, 0.55, 0.24], cloth, f.id); addCyl(scene, [x, 1.18, z - 0.05], 0.10, 0.10, 0.22, skin);
  addBox(scene, [x - 0.11, 0.48, z + 0.15], [0.14, 0.14, 0.45], cloth); addBox(scene, [x + 0.11, 0.48, z + 0.15], [0.14, 0.14, 0.45], cloth);
}

                                                                                                                        
                                                                                                                     
export const toThree = (x, y, z) => new THREE.Vector3(x, y, -z);
export function buildScene() {
  const top = new THREE.Scene(); top.background = new THREE.Color(0xdfe3e6);
  const scene = new THREE.Group(); scene.scale.z = -1; top.add(scene);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a6a4a, 1.6));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.2); sun.position.set(3, 6, 2); scene.add(sun);
  for (const [x, z] of [[1, 2.5], [3, 7.5], [5, 3.5], [-1, -2]]) { const l = new THREE.PointLight(0xfff6e6, 6, 9); l.position.set(x, 2.6, z); scene.add(l); }
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 18), std(0xffffff, { map: woodFloor(), roughness: 0.6 }));
  floor.rotation.x = -Math.PI / 2; floor.position.set(1.5, 0, 3.2); floor.receiveShadow = true; scene.add(floor);
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(14, 18), std(0xb9b4ad)); ceil.rotation.x = Math.PI / 2; ceil.position.set(1.5, WALL_H, 3.2); scene.add(ceil);
  for (const w of WALLS) buildWall(scene, w);
                                                                          
  const wood = mat('woodpanel', () => std(0xa8703c));
  addBox(scene, [DOORWAY.x0 - 0.02, 1.1, 0], [0.06, 2.2, 0.14], wood); addBox(scene, [DOORWAY.x1 + 0.02, 1.1, 0], [0.06, 2.2, 0.14], wood);
  addBox(scene, [(DOORWAY.x0 + DOORWAY.x1) / 2, 2.2 + (WALL_H - 2.2) / 2, 0], [DOORWAY.x1 - DOORWAY.x0 + 0.1, WALL_H - 2.2, WALL_T], mat('white', () => std(0xeceae4)));
  const leaf = addBox(scene, [DOORWAY.x0 + 0.05, 1.05, -0.48], [0.04, 2.1, 0.9], wood); leaf.rotation.y = 0.0;
  for (const f of FURNITURE) {
    if (f.kind === 'desk') buildDesk(scene, f);
    if (f.kind === 'divider') addBox(scene, [f.box[0], 0.75 + (f.box[4] - 0.75) / 2, f.box[1]], [f.box[2], f.box[4] - 0.75, f.box[3]], std(f.color), f.id);
    if (f.kind === 'chair') buildChair(scene, f);
    if (f.kind === 'fan') buildFan(scene, f);
    if (f.kind === 'bin') buildBin(scene, f);
    if (f.kind === 'jug') buildJug(scene, f);
    if (f.kind === 'boxes') buildBoxes(scene, f);
    if (f.kind === 'cabinet') buildCabinet(scene, f);
    if (f.kind === 'person') buildPerson(scene, f);
  }
                                                                                                
  for (const [x, z, yaw] of [[2.05, 6.98, 180], [3.25, 6.98, 180], [2.05, 7.42, 0], [3.25, 7.42, 0]]) buildMonitor(scene, x, z, yaw);
  buildMonitor(scene, 2.7, 4.1, 180, 0.70);
  addBox(scene, [1.9, 0.80, 6.65], [0.24, 0.10, 0.12], mat('tissue', () => std(0x6fb6e6)));
  addBox(scene, [1.5, 0.80, 7.45], [0.30, 0.06, 0.20], mat('router', () => std(0xf2f2f2)));
  for (let k = 0; k < 4; k++) addCyl(scene, [1.4 + k * 0.08, 0.92, 7.55], 0.008, 0.008, 0.26, mat('chairblk', () => std(0x1c1d1f)));
  addCyl(scene, [2.8, 0.81, 6.7], 0.03, 0.03, 0.12, mat('can', () => std(0xcc3333)));
  top.updateMatrixWorld(true);
  return top;
}

                                                                                     
function obstacles() {
  const list = [];
  for (const [x0, z0, x1, z1] of WALLS) list.push({ minX: Math.min(x0, x1) - WALL_T / 2, maxX: Math.max(x0, x1) + WALL_T / 2, minZ: Math.min(z0, z1) - WALL_T / 2, maxZ: Math.max(z0, z1) + WALL_T / 2, id: 'wall' });
                         
  list.push({ minX: DOORWAY.x0 - 0.06, maxX: DOORWAY.x0 + 0.01, minZ: -0.07, maxZ: 0.07, id: 'doorframe' }, { minX: DOORWAY.x1 - 0.01, maxX: DOORWAY.x1 + 0.06, minZ: -0.07, maxZ: 0.07, id: 'doorframe' });
  list.push({ minX: DOORWAY.x0 + 0.02, maxX: DOORWAY.x0 + 0.08, minZ: -0.95, maxZ: -0.02, id: 'door leaf' });
  for (const f of FURNITURE) {
    if (f.solid === false) continue;
    if (f.box) { const [cx, cz, sx, sz] = f.box; list.push({ minX: cx - sx / 2, maxX: cx + sx / 2, minZ: cz - sz / 2, maxZ: cz + sz / 2, id: f.id }); }
    else if (f.at) { const r = { chair: 0.33, fan: 0.19, bin: 0.17, jug: 0.15, person: 0.30 }[f.kind] ?? 0.2; list.push({ minX: f.at[0] - r, maxX: f.at[0] + r, minZ: f.at[1] - r, maxZ: f.at[1] + r, id: f.id }); }
  }
  return list;
}
const OBST = obstacles();
function hits(x, z, r = ROBOT.radius) {
  for (const o of OBST) { const cx = Math.max(o.minX, Math.min(x, o.maxX)), cz = Math.max(o.minZ, Math.min(z, o.maxZ)); if ((x - cx) ** 2 + (z - cz) ** 2 < r * r) return o.id; }
  return null;
}
const footprint = id => OBST.find(o => o.id === id);

                                                                               
export class SoonSim {
  constructor({ width = 640, height = 480, preserve = true, noRender = false } = {}) {
    this.scene = buildScene();
    this.camera = new THREE.PerspectiveCamera(ROBOT.vFovDeg, ROBOT.aspect, 0.05, 40);
    this.renderer = null;
    if (!noRender) {                                                                         
      this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: preserve });
      this.renderer.setPixelRatio(1); this.renderer.setSize(width, height, false); this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    this.raycaster = new THREE.Raycaster();
    this.reset(TASKS[0].id);
  }
  get canvas() { return this.renderer.domElement; }
  reset(taskId) {
    this.task = TASKS.find(t => t.id === taskId) ?? TASKS[0];
    const s = START_POSES[this.task.start];
    this.pose = { x: s.x, z: s.z, yaw: s.yawDeg * DEG };                                                                    
    this.actions = 0; this.contacts = []; this.vetoes = []; this.ended = false; this.endReason = null; this.tape = []; this.touched = null;
    this.render(); return this.status();
  }
  forward() { return { x: -Math.sin(this.pose.yaw), z: Math.cos(this.pose.yaw) }; }
  right() { const f = this.forward(); return { x: f.z, z: -f.x }; }
                                                                                                          
                                                                                                                        
                                                                                                            
  translate(dx, dz) {
    const n = Math.max(2, Math.ceil(Math.hypot(dx, dz) / 0.02));
    for (let i = 1; i <= n; i++) { const hit = hits(this.pose.x + dx * i / n, this.pose.z + dz * i / n); if (hit) return hit; }
    this.pose.x += dx; this.pose.z += dz; return null;
  }
  act(action) {
    if (this.ended) return { ok: false, error: 'episode has ended', ...this.status() };
    const a = ACTIONS[action];
    if (!a) return { ok: false, error: `unknown action ${action}; allowed: ${Object.keys(ACTIONS).join(', ')}`, ...this.status() };
    this.tape.push(action);
    let blocked = null;
    if (a.arrive) { this.ended = true; this.endReason = 'agent_arrived'; }
    else if (a.touch) { this.ended = true; this.endReason = 'agent_touched'; this.touched = this.reach(); }
    else if (a.turnDeg) { this.actions++; this.pose.yaw += a.turnDeg * DEG; }
    else {
      this.actions++;
      const f = this.forward(), r = this.right(), d = a.forward ?? 0, s = a.side ?? 0;
      blocked = this.translate(f.x * d + r.x * s, f.z * d + r.z * s);
      if (blocked) this.vetoes.push({ action: this.actions, with: blocked });
    }
    if (!this.ended && this.actions >= ACTION_BUDGET) { this.ended = true; this.endReason = 'budget_exhausted'; }
    this.render();
    return { ok: true, action, vetoed: !!blocked, blocked, measured_turn_deg: a.turnDeg ?? undefined, ...this.status() };
  }
  status() { return { task: this.task.id, actions: this.actions, budget: ACTION_BUDGET, ended: this.ended, endReason: this.endReason, pose: { x: +this.pose.x.toFixed(3), z: +this.pose.z.toFixed(3), yawDeg: +(this.pose.yaw / DEG).toFixed(1) }, contacts: this.contacts.length, vetoes: this.vetoes.length }; }
  syncCamera() {
    const f = this.forward(), p = this.pose, pitch = ROBOT.cameraPitchDeg * DEG;
    const ex = p.x + f.x * ROBOT.frontOffset, ez = p.z + f.z * ROBOT.frontOffset;
    this.camera.position.copy(toThree(ex, ROBOT.cameraHeight, ez));
    this.camera.lookAt(toThree(ex + f.x * Math.cos(pitch), ROBOT.cameraHeight + Math.sin(pitch), ez + f.z * Math.cos(pitch)));
    this.camera.updateMatrixWorld(true);
  }
  render() { this.syncCamera(); if (this.renderer) this.renderer.render(this.scene, this.camera); }
  frame(type = 'image/jpeg', q = 0.9) { this.render(); return this.canvas.toDataURL(type, q); }

                                                                               
  reach() {
    return firstReachObject(this.frontPoint(), this.forward(), this.right(), OBST, REACH);
  }
                                                                                                 
  targetGeometry(spec) {
    if (spec.kind === 'door') return { segment: [[-0.75, 10.0], [0.25, 10.0]], samples: [[-0.6, 1.0, 9.95], [-0.25, 1.6, 9.95], [0.1, 1.0, 9.95], [-0.25, 0.5, 9.95]] };
    const fp = footprint(spec.ref), cx = (fp.minX + fp.maxX) / 2, cz = (fp.minZ + fp.maxZ) / 2, top = spec.kind === 'chair' ? 0.8 : 0.78;
    return { rect: fp, samples: [[cx, top, cz], [fp.minX + 0.05, top * 0.7, cz], [fp.maxX - 0.05, top * 0.7, cz], [cx, top * 0.7, fp.minZ + 0.05], [cx, top * 0.7, fp.maxZ - 0.05], [cx, 0.45, cz]] };
  }
  frontPoint() { const f = this.forward(); return { x: this.pose.x + f.x * ROBOT.frontOffset, z: this.pose.z + f.z * ROBOT.frontOffset }; }
  measure(geom) {
    const fp = this.frontPoint(); let nx, nz;
    if (geom.rect) { nx = Math.max(geom.rect.minX, Math.min(fp.x, geom.rect.maxX)); nz = Math.max(geom.rect.minZ, Math.min(fp.z, geom.rect.maxZ)); }
    else { const [[x0, z0], [x1]] = geom.segment; nx = Math.max(x0, Math.min(fp.x, x1)); nz = z0; }
    const dx = nx - fp.x, dz = nz - fp.z, dist = Math.hypot(dx, dz), f = this.forward();
    const bearing = dist < 1e-6 ? 0 : Math.acos(Math.max(-1, Math.min(1, (dx * f.x + dz * f.z) / dist))) / DEG;
    return { distance: dist, bearingDeg: bearing };
  }
  visible(geom) {
    this.syncCamera(); const frustum = new THREE.Frustum().setFromProjectionMatrix(new THREE.Matrix4().multiplyMatrices(this.camera.projectionMatrix, this.camera.matrixWorldInverse));
    let seen = 0;
    for (const [x, y, z] of geom.samples) {
      const p = toThree(x, y, z); if (!frustum.containsPoint(p)) continue;
      const dir = p.clone().sub(this.camera.position), d = dir.length(); this.raycaster.set(this.camera.position, dir.normalize()); this.raycaster.far = d - 0.12;
      const block = this.raycaster.intersectObjects(this.scene.children, true).find(h => h.object.isMesh && h.object.material?.opacity !== 0.55);
      if (!block) seen++;
    }
    return seen;
  }
  judge() {
    if (SUCCESS.rule === 'touch') {
      const t = this.task, touched = this.touched ?? { id: null, reachM: null, handGapM: null, physicalContact: false };
      const verdict = judgeReach(touched, t.target.ref, this.endReason === 'agent_touched', REACH.tolerance);
      return { ...verdict, touchedObject: touched.physicalContact ? touched.id : null,
        firstObject: touched.id, reachM: touched.reachM, handGapM: touched.handGapM,
        physicalContact: touched.physicalContact, ruleVersion: 'touch-forward-30cm-v1',
        distanceM: +this.measure(this.targetGeometry(t.target)).distance.toFixed(2), contacts: this.contacts, actions: this.actions };
    }
    const t = this.task, geom = this.targetGeometry(t.target), m = this.measure(geom), vis = this.visible(geom);
    const rivals = t.sameClass.map(ref => ({ ref, ...this.measure(this.targetGeometry({ kind: t.target.kind === 'chair' ? 'chair' : 'box', ref })) }));
    const nearestRival = rivals.reduce((a, b) => (a && a.distance <= b.distance ? a : b), null);
    const checks = {
      arrived: this.endReason === 'agent_arrived',
      atTarget: !nearestRival || m.distance < nearestRival.distance,
      within1m: m.distance <= SUCCESS.maxFrontDistance,
      facing: m.bearingDeg <= SUCCESS.maxBearingDeg,
      visible: vis > 0,
      noContact: this.contacts.length === 0,
    };
    const success = Object.values(checks).every(Boolean);
    return { success, checks, distanceM: +m.distance.toFixed(2), bearingDeg: +m.bearingDeg.toFixed(1), visibleSamples: vis,
      nearestSameClass: nearestRival ? { id: nearestRival.ref, distanceM: +nearestRival.distance.toFixed(2) } : null, contacts: this.contacts, actions: this.actions };
  }
}

export { TASKS, ACTIONS, ACTION_BUDGET, FURNITURE, WALLS, ROBOT, START_POSES, OBST };
