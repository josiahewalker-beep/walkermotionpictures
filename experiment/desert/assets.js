// Desert world — loading the photoreal assets (see desert/ASSETS.md for the contract) and preparing their materials.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const BASE = new URL('./', import.meta.url).href;
const loader = new GLTFLoader();
const cache = new Map();
export const M = 108;                               // world units per metre

// resolves to the GLB's scene, or null if the file isn't there yet (the blockout stays in its place)
export function loadGLB(name) {
  if (!cache.has(name)) cache.set(name, new Promise(res => loader.load(BASE + 'assets/' + name, g => res(g.scene), undefined, () => res(null))));
  return cache.get(name);
}
export function loadTex(name, { srgb = false, repeat = [1, 1], aniso = 8 } = {}) {
  return new Promise(res => new THREE.TextureLoader().load(BASE + 'tex/' + name, t => {
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.anisotropy = aniso;
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; res(t);
  }, undefined, () => res(null)));
}

// role-based tuning on top of what the GLB carries
export function upgradeMaterial(m) {
  const n = (m.name || '').toLowerCase();
  if (n.startsWith('paint')) {
    const p = new THREE.MeshPhysicalMaterial({ name: m.name, color: m.color, map: m.map, normalMap: m.normalMap, roughness: 0.32, metalness: 0.45,
      clearcoat: 1, clearcoatRoughness: 0.04, envMapIntensity: 1.25 });
    return p;
  }
  if (n.startsWith('glass')) {
    return new THREE.MeshPhysicalMaterial({ name: m.name, color: new THREE.Color(0x0b1013), roughness: 0.02, metalness: 0.0, transparent: true, opacity: 0.82,
      envMapIntensity: 1.8, specularIntensity: 1, ior: 1.52, side: THREE.FrontSide, depthWrite: true });
  }
  if (n.startsWith('chrome')) { m.metalness = 1; m.roughness = Math.min(m.roughness ?? 0.1, 0.12); m.envMapIntensity = 1.4; }
  if (n.startsWith('rim')) { m.metalness = Math.max(m.metalness ?? 0.8, 0.8); m.roughness = Math.min(Math.max(m.roughness ?? 0.3, 0.2), 0.4); }
  if (n.startsWith('light_front')) { m.emissive = new THREE.Color(0xfff2dc); m.emissiveIntensity = 0.6; }
  if (n.startsWith('light_rear')) { m.emissive = new THREE.Color(0xff1a0a); m.emissiveIntensity = 0.8; }
  if (n.startsWith('leaf') || n.startsWith('fur')) { m.side = THREE.DoubleSide; if (m.map && m.transparent) { m.alphaTest = 0.45; m.transparent = false; } }
  if (n.startsWith('grating')) { m.side = THREE.DoubleSide; if (m.map || m.alphaMap) { m.alphaTest = 0.5; m.transparent = false; } }
  return m;
}

// every mesh in an asset: upgraded material, the build-in hook, the shadow-depth twin, shadows on
export function prepAsset(obj, hook, depthFor) {
  obj.traverse(o => {
    if (!o.isMesh) return;
    o.material = [].concat(o.material).map(m => hook(upgradeMaterial(m)));
    if (o.material.length === 1) o.material = o.material[0];
    o.castShadow = true; o.receiveShadow = true;
    const d = depthFor(o); if (d) o.customDepthMaterial = d;
  });
  return obj;
}

// many copies of one asset as instanced meshes (one draw call per mesh in the asset)
export function instance(template, matrices) {
  const g = new THREE.Group(); template.updateMatrixWorld(true);
  template.traverse(o => {
    if (!o.isMesh) return;
    const im = new THREE.InstancedMesh(o.geometry, o.material, matrices.length), m = new THREE.Matrix4();
    matrices.forEach((T, i) => im.setMatrixAt(i, m.multiplyMatrices(T, o.matrixWorld)));
    im.castShadow = o.castShadow; im.receiveShadow = o.receiveShadow; im.customDepthMaterial = o.customDepthMaterial;
    im.frustumCulled = false; g.add(im);
  });
  return g;
}

// a vehicle from its GLB: scaled to world units, wheels found for spinning
export function vehicleFrom(template) {
  const v = template.clone(true); v.scale.setScalar(M);
  const spin = []; let r = 0.34;
  v.traverse(o => { if (/^wheel_(FL|FR|RL|RR)/i.test(o.name)) { spin.push(o); const b = new THREE.Box3().setFromObject(o); r = (b.max.y - b.min.y) / 2 / M || r; } });
  const g = new THREE.Group(); g.add(v); g.userData = { spin, wheelR: r * M, scaleInside: M };
  return g;
}
