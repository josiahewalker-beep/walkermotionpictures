// Drive-in world — the second slide (Work) is the image on a mountain-town drive-in screen at night.
// Built around the Work card where it already sits; the card never moves, only the camera does. The layout is authored in
// metres around the screen (see drivein/ASSETS.md, drivein/src/blockout.html) and mapped onto the card:
// 1120 px of slide = 22 m of screen, so K = 50.9 world units per metre. Same build-in, approach and leave as the desert.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { setupRenderer, makeComposer } from './desert/render.js';
import { prepAsset, instance, upgradeMaterial } from './desert/assets.js';
import { installWorldChunks, REV_UNIFORMS } from './world/chunks.js';

export const SCREEN_FACE = { w: 1120, h: 645 };          // the Work slide in px at its reference layout
export const REF_ASPECT = 16 / 9;
const SW = 22, SH = SW * SCREEN_FACE.h / SCREEN_FACE.w, SB = 6, SCY = SB + SH / 2;   // screen metres; bottom 6 m above lot zero
const K = SCREEN_FACE.w / SW;                           // world units per metre
// Josiah 10-22 (camera room): the shot, in layout metres
export const DRIVEIN_SHOT = { pos: [-12.538, 2.16, 40.45], look: [1.163, 10.736, 3.861], fov: 26.5, moonNdc: [0.47, 0.86] };
const CARS = [   // x, z, yaw, mound, file, fallback colour
  { x: -4.08, z: 28.45, ry: 0.40, mound: 1.12, file: 'car_hero', col: 0x8a3a24, hero: true },
  { x: -11.93, z: 18.80, ry: 0.10, mound: 0, file: 'car_wagon', col: 0x2f4a32 },
  { x: -8.27, z: 10.07, ry: -0.05, mound: 0, file: 'car_sedan_a', col: 0xb08a3a },
  { x: -2.57, z: 9.31, ry: 0.05, mound: 0, file: 'car_saab900', col: 0xba1c28 },
  { x: -1.43, z: 17.28, ry: 0.12, mound: 0.63, file: 'car_sedan_b', col: 0x6b4a2b },
];
const LENS = [10.18, 9.95, 26.72], LAMP = [-13, 4.6, 24], STAND = [-24, 0, 52];
const rng = seed => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const ease = t => t * t * t * (t * (t * 6 - 15) + 10);
// the lot climbs gently toward the screen and two cars sit on lifts hidden under them, so the cars stay in frame under the
// camera's upward tilt; from the camera it reads as a flat lot (Josiah 10-22: keep round 3's ground, add the tyre tracks)
const MOUNDS = [[-4.08, 28.45, 1.12, 4.5], [-1.43, 17.28, 0.63, 3.5]];
export function lot(x, z) {
  let y = 2.7 * Math.min(1, Math.max(0, (40 - z) / 30));
  for (const [mx, mz, mh, mr] of MOUNDS) { const d = Math.hypot(x - mx, z - mz) / mr; y += mh * (d < 0.6 ? 1 : d < 1.4 ? 0.5 + 0.5 * Math.cos((d - 0.6) / 0.8 * Math.PI) : 0); }
  return y;
}
const terrain = (x, z) => { const d = Math.hypot(x, z + 10); let y = Math.abs(x) < 70 ? lot(x, z) : lot(x, z) * Math.max(0, 1 - (Math.abs(x) - 70) / 20);
  if (d > 90) y += (d - 90) * 0.22 * (0.6 + 0.4 * Math.sin(x * 0.05) * Math.cos(z * 0.04)); return y; };

const BASE = new URL('./drivein/', import.meta.url).href;
const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder), glbCache = new Map();
const loadGLB = name => { if (!glbCache.has(name)) glbCache.set(name, new Promise(res => loader.load(BASE + 'assets/' + name + '.glb', g => res(g.scene), undefined, () => res(null)))); return glbCache.get(name); };
const loadTex = (name, { srgb = false, repeat = [1, 1] } = {}) => new Promise(res => new THREE.TextureLoader().load(BASE + 'tex/' + name, t => { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(...repeat); t.anisotropy = 8; if (srgb) t.colorSpace = THREE.SRGBColorSpace; res(t); }, undefined, () => res(null)));

export function makeDriveIn({ scene, cssCards, cardId = 'work', camera, renderer, gridFade = () => {}, gridDes = () => {} }) {
  const card = cssCards[cardId], C = card.obj.position.clone();
  // layout metres -> world units
  const P = (x, y, z) => new THREE.Vector3(C.x + x * K, C.y + (y - SCY) * K, C.z + z * K);
  const Y0 = C.y - SCY * K;
  const root = new THREE.Group(); root.name = 'drivein'; root.visible = false; scene.add(root);
  const world = new THREE.Group(); root.add(world);
  const REV = REV_UNIFORMS();
  const revHook = m => { m.defines = { ...(m.defines || {}), DESERT_REV: '' }; m.onBeforeCompile = sh => Object.assign(sh.uniforms, REV); m.customProgramCacheKey = () => 'desert-rev'; return m; };
  const groundHook = m => { m.defines = { ...(m.defines || {}), DESERT_GROUND: '' }; m.customProgramCacheKey = () => 'desert-rev-ground'; return m; };
  const DEPTH = revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking })), DEPTH_G = groundHook(revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking })));
  const mat = (c, o = {}) => revHook(new THREE.MeshStandardMaterial({ color: c, roughness: 0.95, metalness: 0, ...o }));
  const depthFor = o => { const m = [].concat(o.material)[0], g = m.defines && 'DESERT_GROUND' in m.defines;
    if (m.alphaTest > 0 && (m.map || m.alphaMap)) { const d = revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: m.map, alphaMap: m.alphaMap, alphaTest: m.alphaTest })); return g ? groundHook(d) : d; }
    return g ? DEPTH_G : DEPTH; };
  const shadowy = o => { o.traverse(m => { if (m.isMesh) { m.castShadow = true; m.receiveShadow = true; if (!m.customDepthMaterial) m.customDepthMaterial = depthFor(m); } }); return o; };

  // the shot, in world units, and the moon's direction as Josiah placed it
  const shot = { pos: P(...DRIVEIN_SHOT.pos), look: P(...DRIVEIN_SHOT.look), baseFov: DRIVEIN_SHOT.fov };
  const moonDir = (() => { const c = new THREE.PerspectiveCamera(DRIVEIN_SHOT.fov, REF_ASPECT, 1, 1e6); c.position.copy(shot.pos); c.lookAt(shot.look); c.updateMatrixWorld();
    return new THREE.Vector3(...DRIVEIN_SHOT.moonNdc, 0.5).unproject(c).sub(c.position).normalize(); })();

  // ---------- sky: deep night, warm town glow on the horizon, stars, the moon, built in cells like the desert's ----------
  const skyMat = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false, toneMapped: false,
    uniforms: { uMoon: { value: moonDir }, uT: { value: 0 }, uSkyRev: { value: 1 }, uVoid: REV.uVoid, uRev: REV.uRev, uMode: REV.uMode },
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: `uniform vec3 uMoon, uVoid; uniform float uT, uSkyRev, uRev; uniform int uMode; varying vec3 vD;
      float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f); return mix(mix(hash(i), hash(i + vec2(1,0)), f.x), mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y); }
      void main(){
        vec3 d = normalize(vD); float h = clamp(d.y, 0.0, 1.0);
        vec3 c = mix(vec3(0.060, 0.058, 0.066), vec3(0.010, 0.016, 0.040), pow(h, 0.42));
        c += vec3(0.075, 0.045, 0.020) * exp(-h * 12.0);                       // warm glow of the town below the ridge
        float m = max(dot(d, uMoon), 0.0);
        c += vec3(0.55, 0.62, 0.80) * (pow(m, 14.0) * 0.10 + pow(m, 120.0) * 0.18); // moonlit haze around the moon
        // a few thin clouds catching the moonlight
        { vec2 q = vec2(atan(d.z, d.x) * 2.2, d.y * 7.0); float cl = vnoise(q * 2.0 + vec2(uT * 0.004, 0.0)) * 0.6 + vnoise(q * 5.3) * 0.4;
          float band = smoothstep(0.08, 0.2, d.y) * (1.0 - smoothstep(0.45, 0.7, d.y)); float cov = smoothstep(0.58, 0.82, cl) * band;
          c = mix(c, vec3(0.16, 0.17, 0.21) * (0.6 + 0.9 * pow(m, 4.0)), cov * 0.6); }
        // the moon: a waxing crescent, soft limb
        { vec3 up = normalize(cross(cross(uMoon, vec3(0.0, 1.0, 0.0)), uMoon)), rt = normalize(cross(uMoon, up));
          vec2 p = vec2(dot(d, rt), dot(d, up)) / 0.0105; float disc = 1.0 - smoothstep(0.92, 1.04, length(p));
          float shade = 1.0 - smoothstep(0.92, 1.06, length(p - vec2(-0.42, 0.18)));
          c += vec3(0.98, 0.96, 0.88) * disc * (1.0 - shade) * 1.6 * step(0.0, dot(d, uMoon)); }
        // stars: small, many faint, each twinkling at its own rate; thinner near the moon and the horizon glow
        vec2 uv = vec2(atan(d.z, d.x), asin(clamp(d.y, -1.0, 1.0))) * 160.0; vec2 cell = floor(uv); float hs = hash(cell);
        if (hs > 0.985) { vec2 o = vec2(hash(cell + 3.1), hash(cell + 7.7)) * 0.6 + 0.2; float r = length(fract(uv) - o);
          float b = pow(hash(cell + 11.3), 3.0) * 0.9 + 0.1, tw = 0.65 + 0.35 * sin(uT * (0.8 + 2.4 * hash(cell + 5.2)) + hs * 60.0);
          c += vec3(0.95, 0.95, 1.0) * smoothstep(0.16, 0.0, r) * b * tw * smoothstep(0.05, 0.3, d.y) * (1.0 - smoothstep(0.85, 0.99, m)) * 0.9; }
        if (uMode == 2 && uRev < 0.9999) {
          vec2 sc = vec2(atan(d.z, d.x), asin(clamp(d.y, -1.0, 1.0))) * 57.2958 / 3.0, cell2 = floor(sc);
          float order = clamp(cell2.y * 3.0 / 30.0, 0.0, 1.0) * 0.7 + hash(cell2 + 9.1) * 0.3;
          float t = clamp((uRev - 0.45) / 0.55, 0.0, 1.0), g = smoothstep(order * 0.85, order * 0.85 + 0.15, t);
          if (g <= 0.002) discard;
          vec2 cf = abs(fract(sc - 0.5) - 0.5) / max(fwidth(sc), vec2(1e-4)); float edge = 1.0 - clamp(min(cf.x, cf.y) - 0.8, 0.0, 1.0);
          c = mix(mix(uVoid * 0.94, vec3(0.24, 0.40, 0.96), edge), c, smoothstep(0.05, 0.85, g));
        }
        gl_FragColor = vec4(pow(max(mix(uVoid, c, uSkyRev), vec3(0.0)), vec3(2.2)), 1.0);   // c is display-referred, as in the desert's sky
        #include <colorspace_fragment>
      }` });
  { const d = new THREE.Mesh(new THREE.SphereGeometry(60000, 64, 32), skyMat); d.position.set(C.x, Y0, C.z); d.renderOrder = -10; d.frustumCulled = false; world.add(d); }

  // ---------- tyre tracks: a lived-in lot (Josiah 10-22). Drawn once in layout metres: worn lanes between the rows, the paired
  // ruts of every car that pulled into a spot, and years of old faint arcs. R = albedo (x2), G = packed (smoother) mask ----------
  const TRK = { x0: -45, z0: -5, size: 90, px: 2048 };
  const trackTex = (() => { const c = document.createElement('canvas'); c.width = c.height = TRK.px; const x = c.getContext('2d'), r = rng(41), s = TRK.px / TRK.size;
    const X = m => (m - TRK.x0) * s, Z = m => (m - TRK.z0) * s;
    x.fillStyle = 'rgb(128,0,0)'; x.fillRect(0, 0, TRK.px, TRK.px);
    const rut = (pts, w, dark, packed, alpha) => { x.globalAlpha = alpha; x.lineCap = 'round'; x.lineJoin = 'round';
      for (const side of [-0.78, 0.78]) { x.beginPath(); pts.forEach(([px, pz, dx, dz], i) => { const nx = -dz, nz = dx, l = Math.hypot(nx, nz) || 1; const qx = X(px + nx / l * side), qz = Z(pz + nz / l * side); i ? x.lineTo(qx, qz) : x.moveTo(qx, qz); });
        x.strokeStyle = `rgb(${dark},${packed},0)`; x.lineWidth = w * s; x.stroke();
        x.strokeStyle = `rgb(${Math.min(255, dark + 52)},0,0)`; x.lineWidth = w * s * 0.3; x.stroke(); }   // a lighter crust thrown up along the rut's edge
      x.globalAlpha = 1; };
    const path = (a, b, c2, n = 40) => { const out = []; for (let i = 0; i <= n; i++) { const t = i / n, u = 1 - t; const px = u * u * a[0] + 2 * u * t * b[0] + t * t * c2[0], pz = u * u * a[1] + 2 * u * t * b[1] + t * t * c2[1];
      const dx = 2 * u * (b[0] - a[0]) + 2 * t * (c2[0] - b[0]), dz = 2 * u * (b[1] - a[1]) + 2 * t * (c2[1] - b[1]); out.push([px, pz, dx, dz]); } return out; };
    // old faint arcs everywhere
    for (let i = 0; i < 160; i++) { const a = [-40 + r() * 80, -2 + r() * 80], b = [a[0] + (r() - 0.5) * 30, a[1] + (r() - 0.5) * 30], e = [b[0] + (r() - 0.5) * 30, b[1] + (r() - 0.5) * 30];
      rut(path(a, b, e), 0.26, 96 + r() * 20, 60, 0.12 + r() * 0.12); }
    // the lanes between the rows, worn into dark compacted bands
    for (const lz of [4.5, 13.8, 23.2, 32.5]) { x.globalAlpha = 0.35; x.fillStyle = 'rgb(104,90,0)'; x.fillRect(X(-42), Z(lz - 1.9), 84 * s, 3.8 * s); x.globalAlpha = 1;
      for (let k = 0; k < 7; k++) { const off = (r() - 0.5) * 1.6; const pts = []; for (let i = 0; i <= 60; i++) { const px = -42 + i * 1.4, pz = lz + off + Math.sin(px * 0.11 + k) * 0.35; pts.push([px, pz, 1, Math.cos(px * 0.11 + k) * 0.04]); }
        rut(pts, 0.28, 84 + r() * 16, 120, 0.4 + r() * 0.25); } }
    // every parked car pulled in from its lane: two fresh paired ruts curving into the spot
    for (const cdef of CARS) { const fz = cdef.z + 2.5, lane = [4.5, 13.8, 23.2, 32.5].reduce((b, v) => Math.abs(v - fz - 2) < Math.abs(b - fz - 2) ? v : b), side = r() < 0.5 ? -1 : 1;
      rut(path([cdef.x + side * 9, lane], [cdef.x + side * 2, lane - 0.5], [cdef.x, cdef.z - 1]), 0.3, 70, 170, 0.75); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.NoColorSpace; t.anisotropy = 8; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; return t; })();
  function tracksOn(m) { const prev = m.onBeforeCompile;
    m.onBeforeCompile = (sh, rr) => { prev && prev.call(m, sh, rr); sh.uniforms.tTrk = { value: trackTex }; sh.uniforms.uTrk = { value: new THREE.Vector4(C.x + TRK.x0 * K, C.z + TRK.z0 * K, TRK.size * K, 0) };
      sh.vertexShader = 'varying vec2 vTrk;\n' + sh.vertexShader.replace('#include <fog_vertex>', '#include <fog_vertex>\n vTrk = ( modelMatrix * vec4( transformed, 1.0 ) ).xz;');
      sh.fragmentShader = 'uniform sampler2D tTrk; uniform vec4 uTrk; varying vec2 vTrk;\n' + sh.fragmentShader
        .replace('#include <map_fragment>', '#include <map_fragment>\n vec2 trkUv = ( vTrk - uTrk.xy ) / uTrk.z; vec4 trk = ( trkUv.x > 0.0 && trkUv.x < 1.0 && trkUv.y > 0.0 && trkUv.y < 1.0 ) ? texture2D( tTrk, trkUv ) : vec4( 0.5, 0.0, 0.0, 1.0 ); diffuseColor.rgb *= 2.0 * trk.r;')
        .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n roughnessFactor = mix( roughnessFactor, roughnessFactor * 0.78, trk.g );'); };
    const pk = m.customProgramCacheKey ? m.customProgramCacheKey.bind(m) : () => ''; m.customProgramCacheKey = () => pk() + '|tracks'; m.needsUpdate = true; }

  // ---------- ground: the lot, the forest floor, the hills that close the valley ----------
  let groundMesh;
  { const N = 260, g = new THREE.PlaneGeometry(600 * K, 600 * K, N, N); g.rotateX(-Math.PI / 2); const pos = g.attributes.position, col = new Float32Array(pos.count * 3);
    const lotC = new THREE.Color(0x4a3a2a), duffC = new THREE.Color(0x3a2c1c), cc = new THREE.Color();
    for (let i = 0; i < pos.count; i++) { const x = pos.getX(i) / K, z = pos.getZ(i) / K; pos.setY(i, terrain(x, z) * K);
      const inLot = Math.abs(x) < 70 && z > -5 && z < 75 ? 1 : 0; cc.copy(duffC).lerp(lotC, inLot * 0.9 + 0.1 * Math.sin(x * 0.7) * Math.cos(z * 0.5));
      col[i * 3] = cc.r; col[i * 3 + 1] = cc.g; col[i * 3 + 2] = cc.b; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3)); g.computeVertexNormals();
    groundMesh = new THREE.Mesh(g, groundHook(mat(0xffffff, { vertexColors: true }))); groundMesh.position.set(C.x, Y0, C.z); groundMesh.receiveShadow = true; groundMesh.userData.kind = 'ground'; world.add(groundMesh);
    tracksOn(groundMesh.material); }
  // ridges: pine-dark green-brown, their crests catching the moon from behind
  for (const [rad, hgt, col, seed] of [[300, 150, 0x1c2418, 3], [215, 85, 0x161d13, 9]]) {
    const r = rng(seed), pts = 180, pos = [], cols = [], cA = new THREE.Color(col), cCrest = new THREE.Color(0x5a6a80);
    const hs = []; for (let i = 0; i <= pts; i++) { const a = -Math.PI * 0.98 + i / pts * Math.PI * 1.96; hs.push(hgt * (0.45 + 0.55 * Math.abs(Math.sin(a * 2.1 + seed) * Math.cos(a * 1.3))) * (0.9 + r() * 0.2)); }
    for (let i = 0; i < pts; i++) { const a0 = -Math.PI * 0.98 + i / pts * Math.PI * 1.96, a1 = -Math.PI * 0.98 + (i + 1) / pts * Math.PI * 1.96;
      const A = [Math.sin(a0) * rad, -Math.cos(a0) * rad - 10], B = [Math.sin(a1) * rad, -Math.cos(a1) * rad - 10];
      const facing0 = Math.max(0, -(Math.sin(a0) * moonDir.x - Math.cos(a0) * moonDir.z)), facing1 = Math.max(0, -(Math.sin(a1) * moonDir.x - Math.cos(a1) * moonDir.z));
      const quad = [[A, -5, 0, 0], [B, -5, 0, 1], [A, hs[i] * 0.93, 0.9, 0], [B, -5, 0, 1], [B, hs[i + 1] * 0.93, 0.9, 1], [A, hs[i] * 0.93, 0.9, 0],
        [A, hs[i] * 0.93, 0.9, 0], [B, hs[i + 1] * 0.93, 0.9, 1], [A, hs[i], 1, 0], [B, hs[i + 1] * 0.93, 0.9, 1], [B, hs[i + 1], 1, 1], [A, hs[i], 1, 0]];
      for (const [p, y, top, which] of quad) { const v = P(p[0], y, p[1]); pos.push(v.x - C.x, v.y - Y0, v.z - C.z); const f = which ? facing1 : facing0;
        const c2 = cA.clone().lerp(cCrest, top >= 1 ? 0.35 * f : 0); cols.push(c2.r, c2.g, c2.b); } }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(cols, 3)); g.computeVertexNormals();
    const m = new THREE.Mesh(g, groundHook(revHook(new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })))); m.position.set(C.x, Y0, C.z); world.add(m); }

  // ---------- pines: blockout tiers until the pine assets arrive; placements are kept for them ----------
  const pinesPlaced = []; { const r = rng(21);
    for (let i = 0; i < 340; i++) { const a = r() * Math.PI * 2, d = 70 + r() * 130, x = Math.sin(a) * d, z = -Math.cos(a) * d - 10; if (z > 55 && Math.abs(x) < 90) continue; pinesPlaced.push({ x, z, h: 16 + r() * 16, rot: r() * 6.28, v: r() }); }
    for (let i = 0; i < 44; i++) pinesPlaced.push({ x: -58 - r() * 40, z: -20 + r() * 110, h: 16 + r() * 16, rot: r() * 6.28, v: r() });
    for (let i = 0; i < 44; i++) pinesPlaced.push({ x: 58 + r() * 40, z: -20 + r() * 110, h: 16 + r() * 16, rot: r() * 6.28, v: r() });
    for (let i = 0; i < 26; i++) pinesPlaced.push({ x: -40 + r() * 80, z: -14 - r() * 40, h: 18 + r() * 14, rot: r() * 6.28, v: r() });   // behind the screen
  }
  const pineBlock = new THREE.Group(); pineBlock.userData.kind = 'pines'; world.add(pineBlock);
  { const tier = new THREE.ConeGeometry(1, 1, 9), trunk = new THREE.CylinderGeometry(0.5, 1, 1, 6);
    const tierM = mat(0x24402a), trunkM = mat(0x5a3820); const tiers = 7;
    const imT = new THREE.InstancedMesh(tier, tierM, pinesPlaced.length * tiers), imK = new THREE.InstancedMesh(trunk, trunkM, pinesPlaced.length);
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(); let n = 0;
    pinesPlaced.forEach((p, i) => { const base = P(p.x, terrain(p.x, p.z), p.z), h = p.h * K;
      imK.setMatrixAt(i, m4.compose(base.clone().setY(base.y + h * 0.15), q, s.set(h * 0.02, h * 0.3, h * 0.02)));
      for (let k = 0; k < tiers; k++) { const f = k / tiers, rad = h * 0.2 * (1 - f * 0.85), ch = h * 0.22; imT.setMatrixAt(n++, m4.compose(base.clone().setY(base.y + h * 0.18 + f * h * 0.78 + ch / 2), q, s.set(rad, ch, rad))); } });
    imT.castShadow = imK.castShadow = true; imT.customDepthMaterial = imK.customDepthMaterial = DEPTH; pineBlock.add(imT, imK); }

  // ---------- the screen: the slide is the image; behind it a dark panel of the same shape and the old framework ----------
  const rr = SW * 22 / 1120, rs = (w, h, r) => { const sh = new THREE.Shape(), x = -w / 2, y = -h / 2; sh.moveTo(x + r, y); sh.lineTo(x + w - r, y); sh.quadraticCurveTo(x + w, y, x + w, y + r); sh.lineTo(x + w, y + h - r); sh.quadraticCurveTo(x + w, y + h, x + w - r, y + h); sh.lineTo(x + r, y + h); sh.quadraticCurveTo(x, y + h, x, y + h - r); sh.lineTo(x, y + r); sh.quadraticCurveTo(x, y, x + r, y); return sh; };
  const screenBlock = new THREE.Group(); screenBlock.userData.kind = 'screen'; world.add(screenBlock);
  { const back = new THREE.Mesh(new THREE.ExtrudeGeometry(rs(SW * K, SH * K, rr * K), { depth: 0.3 * K, bevelEnabled: false, curveSegments: 10 }), mat(0x2a2520));
    back.position.copy(P(0, SCY, -0.55)); screenBlock.add(back);
    const wood = mat(0x2b211a);
    for (const x of [-10, -4, 4, 10]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.5 * K, (SB + SH + 1 - 2.7) * K, 0.5 * K), wood); p.position.copy(P(x, 2.7 + (SB + SH + 1 - 2.7) / 2, -2.2)); screenBlock.add(p); }
    for (let y = 4; y < SB + SH; y += 3) { const b = new THREE.Mesh(new THREE.BoxGeometry((SW + 2) * K, 0.25 * K, 0.25 * K), wood); b.position.copy(P(0, y, -2.2)); screenBlock.add(b); }
    shadowy(screenBlock); }

  // ---------- booth, lamp, concession glow ----------
  const lens = P(...LENS), aim = P(0, SCY, 0);
  const boothBlock = new THREE.Group(); boothBlock.userData.kind = 'booth'; world.add(boothBlock);
  { const dir = aim.clone().sub(lens).setY(0).normalize(), b = new THREE.Mesh(new THREE.BoxGeometry(4.5 * K, 3.2 * K, 4.5 * K), mat(0x4a3828));
    b.position.copy(lens).addScaledVector(dir, -2.3 * K).add(new THREE.Vector3(0, 0.3 * K, 0)); b.lookAt(b.position.clone().add(dir)); boothBlock.add(b); shadowy(boothBlock); }
  const lampPos = P(...LAMP), lampGroup = new THREE.Group(); lampGroup.userData.kind = 'lamp'; lampGroup.visible = false; world.add(lampGroup);   // 10-22 Josiah: no pole in frame; its warm light stays, from off frame left
  { const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * K, 0.12 * K, 4.6 * K, 8), mat(0x2a2018)); pole.position.copy(lampPos).add(new THREE.Vector3(0, -2.3 * K, 0)); lampGroup.add(pole);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.2 * K, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffd9a0, toneMapped: false })); bulb.position.copy(lampPos); lampGroup.add(bulb); }

  // ---------- cars, speaker posts ----------
  const carSpots = CARS.map(c => ({ ...c, y: lot(c.x, c.z) }));
  const carBlocks = carSpots.map(c => { const g = new THREE.Group(), m = mat(c.col, { roughness: 0.45, metalness: 0.4 }), L = c.hero ? 4.7 : 4.8, Wd = 1.85;
    const body = new THREE.Mesh(new THREE.BoxGeometry(Wd * K, 0.75 * K, L * K), m); body.position.y = 0.65 * K; g.add(body);
    const cab = new THREE.Mesh(new THREE.BoxGeometry(Wd * 0.9 * K, 0.6 * K, 2.3 * K), mat(0x0c0f14, { roughness: 0.15 })); cab.position.set(0, 1.3 * K, 0.1 * K); g.add(cab);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.34 * K, 0.34 * K, 0.24 * K, 14), mat(0x0a0a0a)); w.rotation.z = Math.PI / 2; w.position.set(sx * Wd / 2 * K, 0.34 * K, sz * L * 0.32 * K); g.add(w); }
    g.position.copy(P(c.x, c.y, c.z)); g.rotation.y = c.ry; g.userData.kind = 'car'; world.add(shadowy(g)); return g; });
  const postSpots = carSpots.map(c => { const s = Math.sin(c.ry), co = Math.cos(c.ry); const back = c === carSpots[0] ? 1.7 : 0; return { x: c.x - co * 1.75 + s * back, z: c.z + s * 1.75 + co * back }; });   // on the driver's side, beside the front door (the hero's sits back by the rear door, clear of the bucket's fall)
  const postBlocks = postSpots.map(p => { const g = new THREE.Group(); const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.04 * K, 0.04 * K, 1.1 * K, 8), mat(0x6a6a66, { metalness: 0.6, roughness: 0.5 })); pipe.position.y = 0.55 * K; g.add(pipe);
    const spk = new THREE.Mesh(new THREE.BoxGeometry(0.22 * K, 0.18 * K, 0.1 * K), mat(0x8a8c88, { metalness: 0.7, roughness: 0.4 })); spk.position.set(0, 1.0 * K, 0.08 * K); g.add(spk);
    g.position.copy(P(p.x, lot(p.x, p.z), p.z)); g.userData.kind = 'post'; world.add(shadowy(g)); return g; });

  // ---------- light ----------
  const hemi = new THREE.HemisphereLight(0x2c3650, 0x2a1d12, 0.25); world.add(hemi);
  const moon = new THREE.DirectionalLight(0x9fb2e8, 0.3); moon.position.copy(P(0, SCY, 0)).addScaledVector(moonDir, 400 * K); moon.target.position.copy(P(0, 3, 10)); world.add(moon, moon.target);
  // the warm light from behind the camera: the concession stand's open windows
  // a spot, not a sun: it reaches the cars and the lot and falls off before the treeline (Josiah 10-22: the trees are backlit)
  const standAt = P(STAND[0], 9, STAND[2] + 6), standAim = P(-4, 2, 18), dStand = standAt.distanceTo(standAim);
  const stand = new THREE.SpotLight(0xffb070, 1.6 * dStand * dStand, 85 * K, 0.62, 0.7, 2); stand.position.copy(standAt); stand.target.position.copy(standAim); stand.castShadow = true;
  stand.shadow.mapSize.set(2048, 2048); stand.shadow.camera.near = 2 * K; stand.shadow.camera.far = 100 * K; stand.shadow.bias = -0.0004; stand.shadow.normalBias = 0.06 * K;
  world.add(stand, stand.target);
  const lampLight = new THREE.PointLight(0xffa860, 95 * K * K, 38 * K, 2); lampLight.position.copy(P(-18, 4.6, 27)); world.add(lampLight);
  const screenSpill = new THREE.PointLight(0x8ea0c8, 260 * K * K, 70 * K, 2); screenSpill.position.copy(P(0, SCY * 0.8, 9)); world.add(screenSpill);   // the slide lights the lot a little
  // night environment for reflections: dark sky, moon glow behind, warm lot glow low in front
  let envTex = null;
  function bakeEnv() { if (envTex) return envTex; const es = new THREE.Scene(); es.background = new THREE.Color(0x0b0d14);
    const warm = new THREE.Mesh(new THREE.SphereGeometry(30, 16, 8, 0, Math.PI * 2, Math.PI * 0.55, Math.PI * 0.45), new THREE.MeshBasicMaterial({ color: 0x3a2814, side: THREE.BackSide })); es.add(warm);
    const mg = new THREE.Mesh(new THREE.CircleGeometry(4, 16), new THREE.MeshBasicMaterial({ color: 0x9aa6c8 })); mg.position.copy(moonDir.clone().multiplyScalar(25)); mg.lookAt(0, 0, 0); es.add(mg);
    const sc = new THREE.Mesh(new THREE.PlaneGeometry(14, 8), new THREE.MeshBasicMaterial({ color: 0x3a4660 })); sc.position.set(0, 6, -26); es.add(sc);
    const pm = new THREE.PMREMGenerator(renderer), tm = renderer.toneMapping; renderer.toneMapping = THREE.NoToneMapping; envTex = pm.fromScene(es, 0.04).texture; renderer.toneMapping = tm; pm.dispose(); return envTex; }

  // ---------- the projector: beam, flicker, dust, the moth ----------
  const FL = { k: 1 };
  const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => P(a * SW / 2 * 0.985, SCY + b * SH / 2 * 0.985, -0.05));
  const beamMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false, fog: false,
    uniforms: { uK: { value: 0.028 }, uFl: { value: 1 }, uRev: REV.uRev },
    vertexShader: 'attribute float aT; attribute vec2 aE; varying float vT; varying vec2 vE; void main(){ vT = aT; vE = aE; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform float uK, uFl, uRev; varying float vT; varying vec2 vE;
      void main(){ float edge = smoothstep(0.0, 0.18, vE.x) * smoothstep(0.0, 0.18, 1.0 - vE.x);       // soft sides
        float a = uK * uFl * (0.35 + 0.65 * (1.0 - vT)) * edge * smoothstep(0.0, 0.08, vT) * smoothstep(1.0, 0.94, vT) * smoothstep(0.97, 1.0, uRev);
        gl_FragColor = vec4(vec3(1.0, 0.93, 0.80) * a, 1.0); }` });
  { const pos = [], aT = [], aE = []; const segs = 24;
    for (let f = 0; f < 4; f++) { const A = corners[f], B = corners[(f + 1) % 4];
      for (let i = 0; i < segs; i++) { const e0 = i / segs, e1 = (i + 1) / segs, Q0 = A.clone().lerp(B, e0), Q1 = A.clone().lerp(B, e1);
        for (const [p, t, e] of [[lens, 0, e0], [Q0, 1, e0], [Q1, 1, e1], [lens, 0, e0], [Q1, 1, e1], [lens, 0, e1]]) { pos.push(p.x, p.y, p.z); aT.push(t); aE.push(e, 0); } } }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('aT', new THREE.Float32BufferAttribute(aT, 1)); g.setAttribute('aE', new THREE.Float32BufferAttribute(aE, 2));
    const beam = new THREE.Mesh(g, beamMat); beam.frustumCulled = false; beam.renderOrder = 5; world.add(beam); }
  const inBeam = (p, pad = 0) => { // is a world point inside the beam pyramid? returns 0..1 softness
    const ax = aim.clone().sub(lens), L = ax.length(); ax.divideScalar(L); const v = p.clone().sub(lens), t = v.dot(ax) / L; if (t <= 0 || t >= 1) return 0;
    const right = new THREE.Vector3(1, 0, 0), up = new THREE.Vector3(0, 1, 0), c = lens.clone().lerp(aim, t), q = p.clone().sub(c);
    const hx = SW / 2 * K * t * (1 + pad), hy = SH / 2 * K * t * (1 + pad); return smooth(1, 0.8, Math.abs(q.dot(right)) / hx) * smooth(1, 0.8, Math.abs(q.dot(up)) / hy); };
  // dust: sparse, small, slow; only the motes the light catches show
  const DUST = 420, dustPos = new Float32Array(DUST * 3), dustSeed = []; { const r = rng(5);
    for (let i = 0; i < DUST; i++) { const t = 0.08 + Math.pow(r(), 0.7) * 0.86, a = r() * 2 - 1, b = r() * 2 - 1; const tgt = P(a * SW / 2, SCY + b * SH / 2, 0), p = lens.clone().lerp(tgt, t);
      dustSeed.push({ p, ph: r() * 6.28, sp: 0.2 + r() * 0.5 }); dustPos.set([p.x, p.y, p.z], i * 3); } }
  const dustGeo = new THREE.BufferGeometry(); dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dustMat = new THREE.PointsMaterial({ color: 0xffe6c0, size: 0.022 * K, sizeAttenuation: true, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, toneMapped: false });
  const dust = new THREE.Points(dustGeo, dustMat); dust.frustumCulled = false; world.add(dust);
  // the moth: a pale sprite until moth.glb arrives; lit only while it is in the beam
  const mothTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'); x.fillStyle = '#efe6d2'; x.beginPath(); x.ellipse(20, 32, 16, 9, -0.5, 0, 7); x.ellipse(44, 32, 16, 9, 0.5, 0, 7); x.fill(); x.fillStyle = '#6b5a46'; x.fillRect(30, 22, 4, 22); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t; })();
  const moth = new THREE.Group(), mothSprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: mothTex, transparent: true, depthWrite: false, fog: false, toneMapped: false })); mothSprite.scale.setScalar(0.08 * K); moth.add(mothSprite); world.add(moth);
  const mothHome = lens.clone().lerp(P(4, SCY + 1, 0), 0.42);       // nearer part of the beam, where Josiah drew it

  // ---------- sequence actors: popcorn bucket, the spill, the mouse, the owl ----------
  const heroCar = () => carBlocks[0];
  const bucketGroup = new THREE.Group(); world.add(bucketGroup);
  const bucketBlock = (() => { const g = new THREE.Group(); const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.09 * K, 0.065 * K, 0.22 * K, 16, 1, true), mat(0xd8d0c4, { side: THREE.DoubleSide })); cup.position.y = 0.11 * K; g.add(cup);
    const heap = new THREE.Mesh(new THREE.SphereGeometry(0.09 * K, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(0xf2d78a)); heap.position.y = 0.21 * K; g.add(heap); return shadowy(g); })();
  bucketGroup.add(bucketBlock);
  const kernelGeo = new THREE.IcosahedronGeometry(0.012 * K, 0); let kernelMat = mat(0xf5dc96);
  const KERNELS = 46, kernels = new THREE.InstancedMesh(kernelGeo, kernelMat, KERNELS); kernels.castShadow = true; kernels.customDepthMaterial = DEPTH; kernels.visible = false; world.add(kernels);
  const mouse = new THREE.Group(); { const b = new THREE.Mesh(new THREE.SphereGeometry(1, 12, 8), mat(0x5a4c40)); b.scale.set(0.035 * K, 0.03 * K, 0.07 * K); b.position.y = 0.03 * K; mouse.add(b);
    const tail = new THREE.Mesh(new THREE.CylinderGeometry(0.003 * K, 0.004 * K, 0.09 * K, 4), mat(0x7a6252)); tail.rotation.x = Math.PI / 2.4; tail.position.set(0, 0.02 * K, -0.1 * K); mouse.add(tail); }
  mouse.visible = false; world.add(shadowy(mouse));
  const owl = new THREE.Group(); { const sil = new THREE.MeshBasicMaterial({ color: 0x07080b, fog: false });
    const body = new THREE.Mesh(new THREE.SphereGeometry(1, 10, 8), sil); body.scale.set(0.16 * K, 0.18 * K, 0.3 * K); owl.add(body);
    for (const s of [-1, 1]) { const w = new THREE.Group(), wing = new THREE.Mesh(new THREE.BoxGeometry(0.5 * K, 0.02 * K, 0.22 * K), sil); wing.position.x = s * 0.25 * K; w.add(wing); w.position.x = s * 0.1 * K; w.userData.side = s; owl.add(w); } }
  owl.visible = false; world.add(owl);

  // ---------- assets take over their blockouts as they arrive ----------
  const TPL = {}; const assetsDone = [];
  const prep = o => prepAsset(o, m => { const r = revHook(nightMaterial(m)); return rimOn(r, rimFor((m.name || '').toLowerCase())); }, depthFor);
  function nightMaterial(m) { m = upgradeMaterial(m); const n = (m.name || '').toLowerCase();
    if ('envMapIntensity' in m) m.envMapIntensity = /^(paint|glass|chrome|rim)/.test(n) ? 1.0 : 0.35;
    if (n.startsWith('needles') || n.startsWith('leaf')) { m.side = THREE.DoubleSide; if (m.map) { m.alphaTest = Math.max(m.alphaTest || 0, 0.45); m.transparent = false; } }
    if (/^light_(front|rear|marker)/.test(n)) { m.emissiveIntensity = 0; if (m.emissive) m.emissive.setRGB(0, 0, 0); }   // parked for the film: lights off
    if (n.startsWith('needles')) { m.envMapIntensity = 0.15; m.roughness = 1; if ('specularIntensity' in m) m.specularIntensity = 0.1; if (m.color) m.color.multiplyScalar(0.7); }   // matte, deep needles; the moon only rims them
    if (n.startsWith('light_bulb')) { m.emissive = new THREE.Color(0xffc890); m.emissiveIntensity = 2.0; m.toneMapped = false; }
    return m; }
  const RIM = { uMoonW: { value: moonDir }, uRimC: { value: new THREE.Color(0x9fb2e8) }, uCrK: { value: 0.18 }, uCrP: { value: 6.0 } };
  function rimOn(m, k) { if (!k) return m; const prev = m.onBeforeCompile;
    m.onBeforeCompile = (sh, r) => { prev && prev.call(m, sh, r); sh.uniforms.uMoonW = RIM.uMoonW; sh.uniforms.uRimC = RIM.uRimC; sh.uniforms.uRimK = { value: k };
      sh.fragmentShader = 'uniform vec3 uMoonW; uniform vec3 uRimC; uniform float uRimK;\n' + sh.fragmentShader.replace('#include <emissivemap_fragment>',
        `#include <emissivemap_fragment>
         { vec3 Vv = normalize( vViewPosition ); vec3 Mv = normalize( ( viewMatrix * vec4( uMoonW, 0.0 ) ).xyz );
           float back = smoothstep( 0.05, 0.75, dot( -Vv, Mv ) ), edge = pow( 1.0 - abs( dot( normalize( normal ), Vv ) ), 2.2 );
           totalEmissiveRadiance += uRimC * uRimK * back * edge; }`); };
    const pk = m.customProgramCacheKey ? m.customProgramCacheKey.bind(m) : () => ''; m.customProgramCacheKey = () => pk() + '|rim' + k; return m; }
  // pines: needle cards have random normals, so a normal-based rim lights the whole crown. Rim them by crown shape instead:
  // bright only at the outer silhouette fringe (and the tip), interior dark, so they read backlit against the moon sky.
  function crownOn(tpl, k) { tpl.updateMatrixWorld(true);
    tpl.traverse(o => { if (!o.isMesh) return;
      if (!/^(needles|leaf)/.test((o.material.name || '').toLowerCase())) {   // bark etc.: same bloom-in as the crown
        const src = o.material, m = src.clone(); m.name = src.name; m.onBeforeCompile = src.onBeforeCompile; const pk1 = src.customProgramCacheKey ? src.customProgramCacheKey.bind(src) : () => '';
        m.customProgramCacheKey = () => pk1() + '|bloom'; m.defines = Object.assign({}, src.defines, { REV_BLOOM: '' }); o.material = m; return; }
      o.geometry.computeBoundingBox(); const b = o.geometry.boundingBox;
      const cx = (b.min.x + b.max.x) / 2, cz = (b.min.z + b.max.z) / 2, R = Math.max(b.max.x - cx, b.max.z - cz), cr = new THREE.Vector3(R, b.min.y, b.max.y), cc = new THREE.Vector2(cx, cz);
      const src = o.material, m = src.clone(); m.name = src.name; const prev = src.onBeforeCompile; const pk0 = src.customProgramCacheKey ? src.customProgramCacheKey.bind(src) : () => '';   // clone() drops onBeforeCompile: keep the reveal/rim hooks from the source
      m.onBeforeCompile = (sh, r) => { prev && prev.call(m, sh, r); Object.assign(sh.uniforms, { uMoonW: RIM.uMoonW, uRimC: RIM.uRimC, uRimK: RIM.uCrK, uCrP: RIM.uCrP, uCrown: { value: cr }, uCrC: { value: cc } });
        sh.vertexShader = 'uniform vec3 uCrown; uniform vec2 uCrC; varying vec3 vCrW; varying vec3 vCrR; varying float vCrO; varying float vCrH;\n' + sh.vertexShader.replace('#include <begin_vertex>',
          `#include <begin_vertex>
           { vec4 cw = vec4( transformed, 1.0 ), rr = vec4( transformed.x - uCrC.x, 0.0, transformed.z - uCrC.y, 0.0 );
           #ifdef USE_INSTANCING
             cw = instanceMatrix * cw; rr = instanceMatrix * rr;
           #endif
             vCrW = ( modelMatrix * cw ).xyz; vCrR = ( modelMatrix * rr ).xyz;
             float h = clamp( ( transformed.y - uCrown.y ) / max( uCrown.z - uCrown.y, 1e-3 ), 0.0, 1.0 );
             vCrO = length( transformed.xz - uCrC ) / ( uCrown.x * clamp( ( 1.0 - h ) * 1.15, 0.12, 1.0 ) ); vCrH = h; }`);
        sh.fragmentShader = 'uniform vec3 uMoonW; uniform vec3 uRimC; uniform float uRimK; uniform float uCrP; varying vec3 vCrW; varying vec3 vCrR; varying float vCrO; varying float vCrH;\n' + sh.fragmentShader
          .replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
           float crOuter = smoothstep( 0.45, 1.0, vCrO ), crEdge = smoothstep( 0.8, 1.15, vCrO );
           { vec3 V = normalize( cameraPosition - vCrW ), Rd = normalize( vCrR + vec3( 1e-5 ) );
             float sil = 1.0 - abs( dot( Rd, normalize( vec3( V.x, 0.0, V.z ) ) ) );
             float side = 0.5 + 0.5 * dot( Rd, normalize( vec3( uMoonW.x, 0.0, uMoonW.z ) ) );
             float top = smoothstep( 0.72, 1.0, vCrH );
             totalEmissiveRadiance += uRimC * uRimK * crEdge * ( pow( sil, uCrP ) * ( 0.2 + 0.8 * side ) + 0.4 * top * side ); }`)
          .replace('#include <aomap_fragment>', `reflectedLight.directDiffuse *= mix( 0.15, 0.7, crOuter ); reflectedLight.indirectDiffuse *= mix( 0.3, 0.8, crOuter ); reflectedLight.directSpecular *= 0.05 * crOuter; reflectedLight.indirectSpecular *= 0.1;
           #include <aomap_fragment>`); };
      m.defines = Object.assign({}, src.defines, { REV_BLOOM: '' }); m.customProgramCacheKey = () => pk0() + '|bloom|crown' + R.toFixed(2) + b.min.y.toFixed(2) + b.max.y.toFixed(2);
      o.material = m; }); return tpl; }
  const rimFor = n => /^(needles|leaf)/.test(n) ? 0 : /^fur/.test(n) ? 0.7 :/^bark/.test(n) ? 0.06 : /^(wood|steel|paint_peeling|concrete)/.test(n) ? 0.35 : 0;
  const place = (tpl, pos, ry = 0, s = 1) => { const o = tpl.clone(true); o.scale.setScalar(K * s); o.position.copy(pos); o.rotation.y = ry; return o; };
  let applied = false;
  async function applyAssets() {
    if (applied) return assetsDone; applied = true;
    const names = ['car_hero', 'car_wagon', 'car_sedan_a', 'car_saab900', 'car_sedan_b', 'speaker_post', 'pine_a', 'pine_b', 'pine_c', 'pine_a_lod1', 'pine_b_lod1', 'pine_c_lod1',
      'rock_a', 'rock_b', 'pinecone', 'needle_clump', 'screen', 'booth', 'popcorn_bucket', 'popcorn_kernel', 'moth', 'mouse', 'owl'];
    const got = Object.fromEntries((await Promise.all(names.map(loadGLB))).map((g, i) => [names[i], g]));
    for (const [k, g] of Object.entries(got)) if (g) TPL[k] = prep(g);
    for (const k of Object.keys(TPL)) if (/^pine_/.test(k)) crownOn(TPL[k], 0.55);
    // cars: nose +Z in the files, facing the screen (-Z) here
    carSpots.forEach((c, i) => { const t = TPL[c.file]; if (!t) return; const o = place(t, P(c.x, c.y, c.z), Math.PI + c.ry); o.userData.kind = 'carAsset';
      if (c.file === 'car_hero') o.traverse(m => { if (!m.isMesh) return; const n = (m.material.name || '').toLowerCase();   // keep the Aero silver under the warm stand light: cooler base, less metal so it doesn't mirror the amber
        const keep = (a, b) => { b.onBeforeCompile = a.onBeforeCompile; b.customProgramCacheKey = a.customProgramCacheKey; return b; };
        if (n.startsWith('paint')) { m.material = keep(m.material, m.material.clone()); m.material.color.setRGB(0.36, 0.42, 0.55); m.material.metalness = 0.22; m.material.roughness = 0.3; }
        else if (n.startsWith('rim')) { m.material = keep(m.material, m.material.clone()); m.material.color.setRGB(0.5, 0.53, 0.58); m.material.metalness = 0.45; } }); world.add(o); carBlocks[i].visible = false; carBlocks[i] = o; assetsDone.push(c.file); });
    if (TPL.speaker_post) postSpots.forEach((p, i) => { const o = place(TPL.speaker_post, P(p.x, lot(p.x, p.z), p.z), Math.PI + carSpots[i].ry); world.add(o); postBlocks[i].visible = false; });
    if (TPL.screen) { const o = place(TPL.screen, P(0, 0, 0)); world.add(o); screenBlock.visible = false; assetsDone.push('screen'); }
    if (TPL.booth) { const dir = aim.clone().sub(lens).setY(0).normalize(); const o = TPL.booth.clone(true); o.scale.setScalar(K); world.add(o); o.updateMatrixWorld(true);
      const ln = o.getObjectByName('lens'); const lensLocal = ln ? ln.getWorldPosition(new THREE.Vector3()).sub(o.position) : new THREE.Vector3(0, 8.5 * K, 2 * K);
      o.rotation.y = Math.atan2(dir.x, dir.z); o.updateMatrixWorld(true); const lw = ln ? ln.getWorldPosition(new THREE.Vector3()) : o.position.clone().add(lensLocal);
      o.position.add(lens.clone().sub(lw)); boothBlock.visible = false; assetsDone.push('booth'); }
    if (TPL.lamp_pole) { const o = place(TPL.lamp_pole, P(LAMP[0], terrain(LAMP[0], LAMP[2]), LAMP[2]), 0.6); world.add(o); o.updateMatrixWorld(true); const b = o.getObjectByName('bulb'); if (b) { b.getWorldPosition(lampLight.position); }
      lampGroup.visible = false; assetsDone.push('lamp_pole'); }
    const pv = ['pine_a', 'pine_b', 'pine_c'].filter(k => TPL[k]);
    if (pv.length) { const sets = pv.map(() => ({ hi: [], lo: [] })), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
      const tall = pv.map(k => { TPL[k].updateMatrixWorld(true); const bb = new THREE.Box3().setFromObject(TPL[k]); return (bb.max.y - bb.min.y) || 20; });
      pinesPlaced.forEach(p => { const v = Math.floor(p.v * pv.length), th = tall[v];
        const sc = p.h / th * K, m = new THREE.Matrix4().compose(P(p.x, terrain(p.x, p.z) - 0.2, p.z), q.setFromAxisAngle(up, p.rot).clone(), new THREE.Vector3(sc, sc, sc));
        const near = Math.hypot(p.x - DRIVEIN_SHOT.pos[0], p.z - DRIVEIN_SHOT.pos[2]) < 95; (near || !TPL[pv[v] + '_lod1'] ? sets[v].hi : sets[v].lo).push(m); });
      const g = new THREE.Group(); sets.forEach((st, v) => { if (st.hi.length) g.add(instance(TPL[pv[v]], st.hi)); if (st.lo.length) g.add(instance(TPL[pv[v] + '_lod1'], st.lo)); });
      world.add(g); pineBlock.visible = false; assetsDone.push('pines'); }
    if (TPL.popcorn_bucket) { bucketGroup.remove(bucketBlock); bucketGroup.add(place(TPL.popcorn_bucket, new THREE.Vector3())); assetsDone.push('popcorn_bucket'); }
    if (TPL.popcorn_kernel) { let km = null; TPL.popcorn_kernel.traverse(o => { if (o.isMesh && !km) km = o; });
      if (km) { TPL.popcorn_kernel.updateMatrixWorld(true); kernels.geometry = km.geometry.clone().applyMatrix4(km.matrixWorld).scale(K, K, K); kernels.material = km.material; } }
    if (TPL.moth) { mothSprite.visible = false; const o = place(TPL.moth, new THREE.Vector3(), 0, 3.2); moth.add(o); moth.userData.wings = ['wing_L', 'wing_R'].map(n => o.getObjectByName(n)).filter(Boolean); assetsDone.push('moth'); }
    if (TPL.mouse) { mouse.clear(); const o = place(TPL.mouse, new THREE.Vector3(), 0, 1.5); /* rat-sized, as Josiah drew it */ mouse.add(o); mouse.userData.parts = Object.fromEntries(['head', 'tail', 'leg_FL', 'leg_FR', 'leg_RL', 'leg_RR', 'body', 'paws'].map(n => [n, o.getObjectByName(n) || o.getObjectByName(n.replace('_R', '_H'))])); assetsDone.push('mouse'); }
    if (TPL.owl) { owl.clear(); const o = place(TPL.owl, new THREE.Vector3()); o.traverse(m => { if (m.isMesh) m.material = new THREE.MeshBasicMaterial({ color: 0x07080b, fog: false }); }); owl.add(o); owl.userData.wings = ['wing_L', 'wing_R'].map(n => o.getObjectByName(n)).filter(Boolean); assetsDone.push('owl'); }
    const [la, ln, lr] = await Promise.all([loadTex('lot_albedo.jpg', { srgb: true }), loadTex('lot_normal.jpg'), loadTex('lot_rough.jpg')]);
    if (la) { const rep = 600 / 4; for (const t of [la, ln, lr]) if (t) t.repeat.set(rep, rep); Object.assign(groundMesh.material, { map: la, normalMap: ln, roughnessMap: lr, color: new THREE.Color(1, 1, 1) }); groundMesh.material.needsUpdate = true; assetsDone.push('lot'); }
    world.traverse(o => { if (o.isMesh && o.material && !o.customDepthMaterial && o.castShadow) o.customDepthMaterial = depthFor(o); });
    window.__driveinAssets = assetsDone; return assetsDone;
  }

  // ---------- the sequence ----------
  const clock = { t: 0, playing: false, manual: false }; let seqT = 0;
  const bucketLedge = () => { const car = heroCar(); car.updateMatrixWorld(true); const a = car.getObjectByName && car.getObjectByName('bucket_anchor');
    if (a) return a.getWorldPosition(new THREE.Vector3());
    const local = new THREE.Vector3(-0.92, 1.02, -0.35).multiplyScalar(K).applyAxisAngle(new THREE.Vector3(0, 1, 0), CARS[0].ry); return car.position.clone().add(local); };   // driver's window ledge (car faces -Z, driver side toward the camera)
  const camLeft = () => { const f = new THREE.Vector3().subVectors(shot.look, shot.pos).setY(0).normalize(); return new THREE.Vector3(f.z, 0, -f.x); };   // screen-left on the ground
  const outward = () => new THREE.Vector3(-1, 0, 0).applyAxisAngle(new THREE.Vector3(0, 1, 0), CARS[0].ry);    // out of the driver's window
  let bucket = { phase: 0 }, spill = [], mouseRun = null, owlRun = null;
  function resetSeq() { seqT = 0; bucket = { phase: 0 }; bucketGroup.visible = true; bucketGroup.position.copy(bucketLedge()); bucketGroup.rotation.set(0, CARS[0].ry, 0); kernels.visible = false; spill = []; mouse.visible = false; mouseRun = null; owl.visible = false; owlRun = null; }
  const groundAt = p => Y0 + lot((p.x - C.x) / K, (p.z - C.z) / K) * K;
  function update(dt) {
    if (!clock.playing) return; clock.t += dt; const t = clock.t;
    skyMat.uniforms.uT.value = t;
    // flicker: a slow breathing plus the occasional quick dip, as an old lamp does; never more than ~15 %
    const fl = 0.93 + 0.04 * Math.sin(t * 1.7) + 0.03 * Math.sin(t * 7.3 + 1.1) - (Math.sin(t * 23.0) > 0.97 ? 0.08 : 0) - (Math.sin(t * 0.37) > 0.995 ? 0.12 : 0);
    FL.k = fl; beamMat.uniforms.uFl.value = fl; dustMat.opacity = 0.5 * fl;
    if (card.el) card.el.style.filter = `brightness(${(0.97 + (fl - 0.93) * 0.35).toFixed(3)})`;
    // dust drifts slowly
    for (let i = 0; i < DUST; i++) { const d = dustSeed[i], w = t * d.sp + d.ph; dustPos[i * 3] = d.p.x + Math.sin(w) * 0.25 * K; dustPos[i * 3 + 1] = d.p.y + Math.sin(w * 0.7 + 1.3) * 0.18 * K + Math.sin(t * 0.05 + d.ph) * 0.3 * K; dustPos[i * 3 + 2] = d.p.z + Math.cos(w * 0.9) * 0.2 * K; }
    dustGeo.attributes.position.needsUpdate = true;
    // the moth: flutters in the beam, wanders out (and goes dark), comes back
    { const cyc = t % 14, outPhase = smooth(6.5, 8.0, cyc) * (1 - smooth(10.5, 12.0, cyc));
      const p = mothHome.clone().add(new THREE.Vector3(Math.sin(t * 2.3) * 0.5 + Math.sin(t * 5.1) * 0.15, Math.sin(t * 3.1) * 0.35 + Math.sin(t * 7.7) * 0.1, Math.cos(t * 1.9) * 0.4).multiplyScalar(K))
        .add(new THREE.Vector3(1.6, 1.1, 0.6).multiplyScalar(K * 2.2 * outPhase));
      moth.position.copy(p); const lit = inBeam(p, 0.05) * fl; mothSprite.material.opacity = 0.15 + 0.85 * lit; moth.traverse(o => { if (o.isMesh && o.material && 'emissiveIntensity' in o.material) { o.material.emissive = o.material.emissive || new THREE.Color(); o.material.emissive.setRGB(1, 0.92, 0.78); o.material.emissiveIntensity = 2.4 * lit; } });
      const flap = Math.sin(t * 38) * 0.9; (moth.userData.wings || []).forEach((w, i) => w.rotation.z = (i ? -1 : 1) * flap); moth.lookAt(camera.position); if (moth.userData.wings && moth.userData.wings.length) moth.rotateX(-1.25); }   // the model's wings lie flat: tip it so they face the camera instead of showing their edge
    // 3 s: the bucket tips off the ledge, falls, lands on its side; popcorn sprays out and settles
    if (bucket.phase === 0 && t >= 3) { bucket = { phase: 1, t0: t, p: bucketGroup.position.clone(), v: outward().multiplyScalar(0.6 * K).addScaledVector(camLeft(), 1.1 * K).add(new THREE.Vector3(0, 0.4 * K, 0)), spin: 0 }; }   // lands left of the door, clear of the page's buttons
    if (bucket.phase === 1) { const g = -9.8 * K; bucket.v.y += g * dt; bucket.p.addScaledVector(bucket.v, dt); bucket.spin += dt * 6.5;
      const gy = groundAt(bucket.p) + 0.09 * K; if (bucket.p.y <= gy) { bucket.p.y = gy; bucket.phase = 2; bucket.t1 = t; burst(bucket.p); }
      bucketGroup.position.copy(bucket.p); bucketGroup.rotation.set(0, CARS[0].ry, 0); bucketGroup.rotateOnAxis(new THREE.Vector3(0, 0, 1), Math.min(Math.PI / 2, bucket.spin)); }
    if (bucket.phase === 2) { const k = Math.min(1, (t - bucket.t1) / 0.35); bucketGroup.rotation.set(0, CARS[0].ry, 0); bucketGroup.rotateOnAxis(new THREE.Vector3(0, 0, 1), Math.PI / 2 + Math.sin(k * Math.PI) * 0.12 * (1 - k)); }
    if (spill.length) { const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), one = new THREE.Vector3(1, 1, 1);
      spill.forEach((s, i) => { if (!s.rest) { s.v.y += -9.8 * K * dt; s.p.addScaledVector(s.v, dt); const gy = groundAt(s.p) + 0.008 * K; if (s.p.y <= gy) { s.p.y = gy; if (Math.abs(s.v.y) > 0.5 * K) { s.v.y *= -0.25; s.v.x *= 0.5; s.v.z *= 0.5; } else s.rest = true; } s.r += dt * 9; }
        kernels.setMatrixAt(i, m4.compose(s.p, q.setFromEuler(new THREE.Euler(s.r, s.r * 0.7, 0)), one)); }); kernels.instanceMatrix.needsUpdate = true; }
    // 10 s: a mouse runs in from the left to the spill, stops, sits and nibbles
    if (!mouseRun && t >= 10 && spill.length) { const target = bucketGroup.position.clone().addScaledVector(camLeft(), 0.5 * K).addScaledVector(outward(), 0.15 * K); /* beside the spill, screen-left of the bucket, in clear view */ const camRight = new THREE.Vector3().subVectors(shot.look, shot.pos).setY(0).normalize(); camRight.set(-camRight.z, 0, camRight.x);
      const start = target.clone().addScaledVector(camRight, -5.5 * K).add(new THREE.Vector3(0, 0, 0.4 * K)); mouseRun = { t0: t, start, target, dur: 3.6 }; mouse.visible = true; }
    if (mouseRun) { const u = (t - mouseRun.t0) / mouseRun.dur, P0 = mouseRun.start, P1 = mouseRun.target;
      const stopAt = [0.36, 0.7], pauses = stopAt.map(s => smooth(s - 0.04, s, u) * (1 - smooth(s + 0.05, s + 0.1, u)));
      const k = Math.min(1, u) - 0.05 * (pauses[0] + pauses[1]); const p = P0.clone().lerp(P1, ease(Math.min(1, Math.max(0, k))));
      p.y = groundAt(p) + 0.005 * K; mouse.position.copy(p); mouse.lookAt(u < 1 ? P1.clone().setY(p.y) : bucketGroup.position.clone().setY(p.y));
      const run = u < 1 ? (1 - Math.max(pauses[0], pauses[1])) : 0, parts = mouse.userData.parts || {};
      const sit = smooth(1.0, 1.25, u), nib = u > 1.3 ? Math.sin(t * 14) * 0.5 + 0.5 : 0;
      mouse.position.y += Math.abs(Math.sin(t * 26)) * 0.012 * K * run;
      if (parts.body) parts.body.rotation.x = -0.6 * sit; if (parts.head) parts.head.rotation.x = -0.25 * sit + nib * 0.18;
      for (const [n, ph] of [['leg_FL', 0], ['leg_RR', 0], ['leg_FR', Math.PI], ['leg_RL', Math.PI]]) if (parts[n]) parts[n].rotation.x = Math.sin(t * 26 + ph) * 0.8 * run;
      if (!mouse.userData.parts) mouse.rotation.x = -0.5 * sit; }
    // ~16 s: the owl crosses the beam right to left as a silhouette and climbs out past the moon
    if (!owlRun && t >= 16) { const c = new THREE.PerspectiveCamera(DRIVEIN_SHOT.fov, REF_ASPECT, 1, 1e6); c.position.copy(shot.pos); c.lookAt(shot.look); c.updateMatrixWorld();
      const at = (nx, ny, dist) => new THREE.Vector3(nx, ny, 0.5).unproject(c).sub(c.position).normalize().multiplyScalar(dist).add(c.position);
      owlRun = { t0: t, pts: [at(1.25, 0.12, 24 * K), at(0.62, 0.4, 23 * K), at(0.42, 0.75, 22 * K), at(0.28, 1.25, 22 * K)], dur: 3.2 }; owl.visible = true; }
    if (owlRun) { const u = (t - owlRun.t0) / owlRun.dur; if (u > 1) owl.visible = false; else { const [a, b, c2, d] = owlRun.pts, e = u, v = 1 - e;
      const p = a.clone().multiplyScalar(v * v * v).addScaledVector(b, 3 * v * v * e).addScaledVector(c2, 3 * v * e * e).addScaledVector(d, e * e * e);
      const ahead = owl.position.clone(); owl.position.copy(p); if (u > 0.01) owl.lookAt(p.clone().add(p.clone().sub(ahead)));
      const flap = Math.sin(t * 9) * 0.55 + 0.1; (owl.userData.wings || []).forEach((w, i) => w.rotation.z = (i ? -1 : 1) * flap);
      owl.children.forEach(w => { if (w.userData.side) w.rotation.z = w.userData.side * flap; }); } }
  }
  function burst(at) { kernels.visible = true; const r = rng(17), out = outward(); spill = [];
    for (let i = 0; i < KERNELS; i++) { const sp = (0.4 + r() * 1.1) * K, a = (r() - 0.5) * 1.6; const dir = out.clone().multiplyScalar(0.4).add(camLeft()).normalize().applyAxisAngle(new THREE.Vector3(0, 1, 0), a);   // spray mostly screen-left, away from the buttons
      spill.push({ p: at.clone().add(new THREE.Vector3(0, 0.03 * K, 0)), v: dir.multiplyScalar(sp).add(new THREE.Vector3(0, (0.3 + r() * 0.9) * K, 0)), r: r() * 6, rest: false }); } }

  // ---------- reveal, approach, landing, leave (as the desert) ----------
  let fly = null, lastFly = null, inside = false, aux = null, composer = null, landedAt = -1, fogBefore = null, envBefore = null, film = null;
  const haze = new THREE.FogExp2(0x1d1a15, 1 / (520 * K));
  REV.uHzY0.value = Y0; REV.uHzH.value = 40 * K; REV.uHzSun.value.copy(moonDir); REV.uHzSunC.value.set(0x6a7590); REV.uFloor.value = Y0 + 2.7 * K;
  REV.uOrigin.value.copy(P(0, 2.7, 1)); REV.uCam.value.copy(shot.pos);
  const bloomAt = t => Math.pow(Math.min(1, Math.max(0, (t - 0.03) / 0.97)), 1.15);
  function setReveal(p) {
    const R = p >= 1 ? 1e7 : 300 * Math.pow(220, p); REV.uRev.value = p; REV.uMode.value = 2; REV.uR.value = R;
    skyMat.uniforms.uSkyRev.value = 1;
    gridDes(p >= 1 || p <= 0 ? -1 : R, 0, 1, REV.uOrigin.value);
    const gf = smooth(0.92, 1, p); gridFade(gf);
    if (!aux) aux = scene.children.filter(o => o !== root && o.material && o.material.transparent && !o.material.isShaderMaterial && o.visible).map(o => ({ o, a: o.material.opacity }));
    for (const x of aux) x.o.material.opacity = x.a * (1 - gf);
    for (const k in cssCards) if (k !== cardId) { const e = cssCards[k].obj.element; e.style.transition = 'none'; e.style.opacity = String(1 - smooth(0, 0.45, p)); }
    const show = p > 0.0001; kernels.visible = kernels.visible && show;
  }
  const heroPose = { pos: shot.pos, look: shot.look, baseFov: shot.baseFov, get fov() { return heroFov(shot.baseFov); } };
  function pose(t) { const e = ease(t), [P0, P1, P2, P3] = fly.P, u = 1 - e;
    const pos = P0.clone().multiplyScalar(u * u * u).addScaledVector(P1, 3 * u * u * e).addScaledVector(P2, 3 * u * e * e).addScaledVector(P3, e * e * e);
    return { pos, look: fly.L0.clone().lerp(fly.L1, ease(Math.min(1, t / 0.92))), fov: fly.f0 + (fly.f1 - fly.f0) * e }; }
  function useWorldLook() { if (fogBefore === null) { fogBefore = scene.fog; envBefore = scene.environment; } scene.fog = haze; scene.environment = bakeEnv(); }
  function finishLeave() { fly = null; root.visible = false; gridFade(0); gridDes(-1, 0, 0, REV.uOrigin.value);
    if (fogBefore !== null) { scene.fog = fogBefore; scene.environment = envBefore; fogBefore = null; }
    for (const x of aux || []) x.o.material.opacity = x.a; for (const k in cssCards) cssCards[k].obj.element.style.opacity = ''; if (card.el) card.el.style.filter = ''; }
  const api = {
    root, C, K, clock, kind: 'drivein',
    get landedFov() { return heroPose.fov; }, get flying() { return !!fly && fly.dir > 0; }, get inside() { return inside; }, get leaving() { return !!fly && fly.dir === -2; },
    prepare() { installWorldChunks(); setupRenderer(renderer); bakeEnv(); world.traverse(o => { if (o.isMesh && o.material && o.material.defines && 'DESERT_REV' in o.material.defines && !o.customDepthMaterial) o.customDepthMaterial = 'DESERT_GROUND' in o.material.defines ? DEPTH_G : DEPTH; });
      api.ready = true; api.assets = applyAssets(); resetSeq(); return heroPose; },
    approachFrom(pos, look, fov, dur = 6.5) { api.stop(); root.visible = true; inside = false; aux = null; useWorldLook(); resetSeq();
      camera.far = Math.max(camera.far, 200000); camera.updateProjectionMatrix();
      const vd = heroPose.look.clone().sub(heroPose.pos).normalize(), up = new THREE.Vector3(0, 1, 0);
      fly = { dir: 1, t: 0, dur, L0: look.clone(), L1: heroPose.look.clone(), f0: fov, f1: heroPose.fov,
        P: [pos.clone(), pos.clone().lerp(heroPose.pos, 0.35).addScaledVector(up, 500), heroPose.pos.clone().addScaledVector(vd, -900).addScaledVector(up, 300), heroPose.pos.clone()] };
      setReveal(0); },
    flyStep(dt) { fly.t = Math.min(1, fly.t + dt / fly.dur); const s = pose(fly.t); setReveal(bloomAt(fly.t));
      if (fly.t >= 1) { lastFly = fly; fly = null; inside = true; setReveal(1); api.play(); s.done = true; landedAt = 0; } return s; },
    leave(speed = 6.5 / 4.2) { const f = fly && fly.dir > 0 ? fly : lastFly; if (!f) return false; api.stopFilm(); api.stop(); inside = false; landedAt = -1; fly = Object.assign({}, f, { dir: -2, t: f === fly ? fly.t : 1, speed }); return true; },
    leaveStep(dt) { fly.t = Math.max(0, fly.t - dt * fly.speed / fly.dur); const s = pose(fly.t); setReveal(bloomAt(fly.t)); if (fly.t <= 0) { finishLeave(); s.done = true; } return s; },
    render(dt) { if (!root.visible || window.__desertNoPost) return false; const leaving = fly && fly.dir < 0;
      if (!inside && !(leaving && REV.uRev.value > 0.965)) return false; if (!composer) composer = makeComposer(renderer, scene, camera);
      let k; if (inside) { landedAt += dt; k = Math.min(1, landedAt / 1.2); } else k = Math.min(1, (REV.uRev.value - 0.965) / 0.035);
      composer.render(dt, k * k * (3 - 2 * k)); return true; },
    landNow() { api.approachFrom(camera.position.clone(), camera.position.clone().add(new THREE.Vector3(0, 0, -1)), camera.fov); fly.t = 1; const s = pose(1); lastFly = fly; fly = null; inside = true; setReveal(1); landedAt = 5; return s; },
    stop() { clock.playing = false; if (card.el) card.el.style.filter = ''; },
    play() { clock.t = 0; clock.playing = true; resetSeq(); },
    tick(dt) { if (!clock.manual) update(dt); },
    step(dt) { update(dt); },
    // the film plays on the screen itself: the slide gives way to the player, the beam keeps flickering
    playOnScreen(v, title) { api.stopFilm(); const el = card.el; if (!el) return; const [id, h] = String(v).split('/');
      const q = new URLSearchParams({ autoplay: '1', title: '0', byline: '0', portrait: '0', dnt: '1', playsinline: '1' }); if (h) q.set('h', h);
      const box = document.createElement('div'); box.className = 'onscreen'; Object.assign(box.style, { position: 'absolute', inset: '0', borderRadius: '22px', overflow: 'hidden', background: '#000', zIndex: '5' });
      const f = document.createElement('iframe'); f.src = (String(v).startsWith('file:') ? String(v).slice(5) : `https://player.vimeo.com/video/${id}?${q}`); f.allow = 'autoplay; fullscreen; picture-in-picture'; f.title = title || 'Film';
      Object.assign(f.style, { position: 'absolute', inset: '0', width: '100%', height: '100%', border: '0' }); box.appendChild(f);
      const x = document.createElement('button'); x.type = 'button'; x.textContent = 'Close film'; x.setAttribute('aria-label', 'Close the film');
      Object.assign(x.style, { position: 'absolute', right: '14px', top: '14px', zIndex: '6', font: '500 14px system-ui, sans-serif', color: '#fff', background: 'rgba(0,0,0,.55)', border: '1px solid rgba(255,255,255,.3)', borderRadius: '999px', padding: '8px 14px', cursor: 'pointer' });
      x.addEventListener('click', ev => { ev.stopPropagation(); api.stopFilm(); }); box.appendChild(x);
      if (getComputedStyle(el).position === 'static') el.style.position = 'relative'; el.appendChild(box); film = box; if (window.__radio) window.__radio.duck(true); },
    stopFilm() { if (film) { film.remove(); film = null; if (window.__radio) window.__radio.duck(false); } },
    get debug() { return { RIM, mouse, owl, bucketGroup, kernels, scene, camera, renderer, clock, world, REV, heroPose, moonDir, lens, P, K }; },
  };
  return api;
}
export function heroFov(baseFov, aspect = innerWidth / innerHeight) {
  if (aspect >= REF_ASPECT) return baseFov;
  return THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(baseFov / 2)) * REF_ASPECT / aspect));
}
