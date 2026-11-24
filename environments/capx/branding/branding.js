                                                                                                                
                                                                                    
import * as THREE from 'three';

const base = new URL('./', import.meta.url);
const loader = new THREE.TextureLoader();
const tex = {};
function texture(name) {
  if (!tex[name]) { const t = loader.load(new URL(`logo-${name}.png`, base).href); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; tex[name] = t; }
  return tex[name];
}
const ASPECT = { full: 926 / 1126, bird: 923 / 724, word: 873 / 365, 'full-white': 926 / 1126, 'word-white': 873 / 365 };                                                                                          

                                                                      
export function logoDecal(name, w) {
  const h = w / ASPECT[name];
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: texture(name), transparent: true, alphaTest: 0.05, roughness: 0.6, polygonOffset: true, polygonOffsetFactor: -2 }));
  m.name = 'branding'; return m;
}
                                                                               
export function logoPoster(w = 0.8) {
  const g = new THREE.Group(); g.name = 'branding';
  const h = w / ASPECT.full * 1.08;
  g.add(new THREE.Mesh(new THREE.BoxGeometry(w + 0.06, h + 0.06, 0.02), new THREE.MeshStandardMaterial({ color: 0x2b2e33, roughness: 0.5 })));
  const board = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8 })); board.position.z = 0.011; g.add(board);
  const d = logoDecal('full', w * 0.82); d.position.z = 0.013; g.add(d);
  return g;
}
const basis = (x, y, z) => new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(new THREE.Vector3(...x), new THREE.Vector3(...y), new THREE.Vector3(...z)));

                                                                                                                             
export function brandG1(g1) {
  const body = g1.userData.body;
  const chest = logoDecal('full', 0.155); chest.position.set(0, 0.97, -0.092); chest.rotation.y = Math.PI; body.add(chest);                                        
                                                                                                
  const plate = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.20, 0.01), new THREE.MeshStandardMaterial({ color: 0xc9ccd1, roughness: 0.45 })); plate.position.set(0, 0.97, 0.085); body.add(plate);
  const back = logoDecal('full', 0.155); back.position.set(0, 0.97, 0.0915); body.add(back);
  for (const s of [-1, 1]) { const w = logoDecal('word-white', 0.075); w.position.set(s * 0.091, 0.53, -0.001); w.rotation.y = s * Math.PI / 2; body.add(w); }                  
}

                                                                                         
export function brandSoonWalls(scene) {
                                                                                    
  const posters = [
    [6.285, 1.6, -Math.PI / 2, 0.8],                                    
    [-1.485, 7.6, Math.PI / 2, 0.8],                                    
    [3.2, 0.015, Math.PI, 0.8],                                                           
    [-2.45, -0.015, 0, 0.7],                                                              
    [-1.1, -3.585, Math.PI, 0.7],                                             
  ];
  for (const [x, z, ry, w] of posters) { const g = logoPoster(w); g.position.set(x, 1.45, -z); g.rotation.y = ry; scene.add(g); }
}

                                                                                                                              
export function brandCapx(sim) {
  const A = sim.A, T = 0.75;
  const chest = logoDecal('full', 0.155); chest.position.set(0.0715, 0.17, 0.95 - T); chest.quaternion.copy(basis([0, 1, 0], [0, 0, 1], [1, 0, 0])); A.add(chest);
                                                                       
  const plate = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.18, 0.20), new THREE.MeshStandardMaterial({ color: 0xc9ccd1, roughness: 0.45 })); plate.position.set(-0.105, 0.17, 0.95 - T); A.add(plate);
  const back = logoDecal('full', 0.155); back.position.set(-0.1115, 0.17, 0.95 - T); back.quaternion.copy(basis([0, -1, 0], [0, 0, 1], [-1, 0, 0])); A.add(back);
                                          
  const wall = new THREE.Mesh(new THREE.BoxGeometry(0.03, 3.0, 2.6), new THREE.MeshStandardMaterial({ color: 0xeceae6, roughness: 0.9 })); wall.position.set(-0.45, 0.0, 1.30 - T - 0.02); A.add(wall);
  const poster = logoPoster(0.9); poster.position.set(-0.433, 0.0, 1.42 - T); poster.quaternion.copy(basis([0, 1, 0], [0, 0, 1], [1, 0, 0])); A.add(poster);                                           
}

                                                                                                                      
                                                                                                                          
export function brandG1Real(g1) {
  const torso = g1.userData.links.torso_link; if (!torso) return;
  const holder = torso.children.find(c => c.isGroup && !c.name) ?? torso;                                                    
  const box = new THREE.Box3();
  for (const m of holder.children) if (m.isMesh) { m.geometry.computeBoundingBox(); const b = m.geometry.boundingBox.clone(); b.translate(m.position); box.union(b); }
  const zc = box.min.z + 0.30 * (box.max.z - box.min.z);                         
  const plateMat = new THREE.MeshStandardMaterial({ color: 0xe6e8ea, roughness: 0.5 });
  for (const [x, q] of [[box.max.x + 0.004, basis([0, 1, 0], [0, 0, 1], [1, 0, 0])], [box.min.x - 0.004, basis([0, -1, 0], [0, 0, 1], [-1, 0, 0])]]) {
    const plate = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.16, 0.004), plateMat); plate.position.set(x, 0, zc); plate.quaternion.copy(q); holder.add(plate);
    const logo = logoDecal('full', 0.115); logo.position.set(x + Math.sign(x) * 0.0025, 0, zc); logo.quaternion.copy(q); holder.add(logo);
  }
}
