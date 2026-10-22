// Desert billboard world — framing blockout (audition sketch, not the detailed build).
// Everything is built around the hero card where it already sits; the card never moves, only the camera does.
// Units: the site's world units (1 unit ≈ 1 CSS px at the card plane). The card is ~4.3 m tall, so ~108 units per metre.
import * as THREE from 'three';
import { setupRenderer, skyEnvironment, makeComposer } from './desert/render.js';
import { loadGLB, loadTex, prepAsset, instance, vehicleFrom } from './desert/assets.js';
import { installWorldChunks, REV_UNIFORMS } from './world/chunks.js';

const M = 108;                                    // world units per metre
const rng = seed => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

export const LOOKS = {
  mojave: {   // the reference: high sun, bleached sky, Joshua trees and creosote, lavender-brown ranges
    name: 'Mojave noon', zenith: 0x78a5d4, horizon: 0xe6ecef, haze: 0xd9dfe2, sand: [0xd8c4a2, 0xcbb38c], bush: [0x8a8f5c, 0x9a9468, 0x7b7f52],
    tree: 'joshua', treeCol: 0x6d6a3e, trunk: 0x7d6a55, rock: 0xa89580, mt: [0x9c8a86, 0xb6aaa8], sun: [-0.35, 0.86, 0.38], sunCol: 0xfff3e0, sunI: 2.6, hemi: 1.25,
    asphalt: 0x58585c, shoulder: 0xc9b896, frame: 0x26282d, car: [0xe8e4dc, 0x9b2b25, 0x3b4a5c],
  },
  golden: {   // late afternoon: low warm sun from camera left, long shadows across the road
    name: 'Golden hour', zenith: 0x3f6fae, horizon: 0xf2c28e, haze: 0xeac39a, sand: [0xd9a46a, 0xc78e55], bush: [0x7d7a45, 0x8a7d47, 0x6b6a3c],
    tree: 'joshua', treeCol: 0x5c5a32, trunk: 0x6b5340, rock: 0xb07a52, mt: [0x8b5f5a, 0xb08479], sun: [-0.86, 0.26, 0.42], sunCol: 0xffc68a, sunI: 3.0, hemi: 0.9,
    asphalt: 0x4b4646, shoulder: 0xc8955f, frame: 0x221f20, car: [0xe8e0d2, 0x2d5a7a, 0x8a2f22], stars: 1,
  },
  sonoran: {  // Arizona: saguaro and ocotillo, redder ground, deeper blue sky, rocky ranges
    name: 'Sonoran saguaro', zenith: 0x2f6fc0, horizon: 0xbcd3e6, haze: 0xc6d4de, sand: [0xc49a74, 0xb58660], bush: [0x6f7f45, 0x7c8a50, 0x5f6e3d],
    tree: 'saguaro', treeCol: 0x5d7a45, trunk: 0x5d7a45, rock: 0x9a6a50, mt: [0x7a5a55, 0x9d8a92], sun: [-0.25, 0.9, 0.35], sunCol: 0xfff1dc, sunI: 2.7, hemi: 1.2,
    asphalt: 0x4f4f52, shoulder: 0xb88d68, frame: 0x26282d, car: [0xd9d6cf, 0x1e3a5f, 0xa33a2a],
  },
  pastel: {   // stylised: the site's clean palette carried into the desert — peach sand, coral mesas, mint-blue sky
    name: 'Pastel stage', zenith: 0x8fc3e0, horizon: 0xf3e7d8, haze: 0xf1e3d3, sand: [0xf0c9a0, 0xe8bb8f], bush: [0x9fbf9a, 0xb3c99a, 0x8fae8c],
    tree: 'saguaro', treeCol: 0x7fae8a, trunk: 0x7fae8a, rock: 0xe39a7a, mt: [0xe08b73, 0xeab39c], sun: [-0.3, 0.88, 0.4], sunCol: 0xfff8ee, sunI: 2.2, hemi: 1.5,
    asphalt: 0x6f6a70, shoulder: 0xeec29a, frame: 0x2a2d33, car: [0xf4efe6, 0x6fb3a8, 0xe4846b], mesa: true,
  },
};

export function makeDesert({ scene, cssCards, heroId = 'hero', camera, renderer, clear, gridFade = () => {}, gridDes = () => {} }) {
  const hero = cssCards[heroId], C = hero.obj.position.clone();
  const W = hero.el.offsetWidth, H = hero.el.offsetHeight;
  const bottom = C.y - H / 2, clearance = (clear || window.__clear || 3.8) * M, Y0 = bottom - clearance;     // ground sits ~3.8 m under the face
  const root = new THREE.Group(); root.name = 'desert';
  // the desert lives in the site's own scene so it sits in depth with the grid it grows out of
  scene.add(root);
  let fogBefore = null, hazeFog = null;
  const useHaze = () => { if (fogBefore === null) fogBefore = scene.fog; scene.fog = hazeFog; };
  let world = null, lookKey = 'mojave', road = null, cars = [], skyMat = null, trees = [], viewInfo = null, sunLight = null, hemiLight = null;
  const placed = { tree: [], bush: [], rock: [] };      // where the scatter put things, so assets can take the same spots
  const TPL = {};                                         // loaded asset templates
  let groundMesh = null, envTex = null, composer = null, landedAt = -1;
  const hidden = [];

  // ---------- build-in: every desert material shares these uniforms, read in the haze chunk below ----------
  // uMode 0 = grid becomes ground, 1 = streaming pop-in, 2 = draw distance. uRev 0 → 1 over the approach.
  const REV = REV_UNIFORMS();
  // bloom: the world opens out of the slide in screen space and fills the frame exactly at landing. uVar 0 frame bleed, 1 light bloom, 2 tile resolve
  const BLOOM = { uBloom: { value: 1 }, uVar: { value: 0 }, uEdge: { value: [0, 1, 2, 3].map(() => new THREE.Vector3()) }, uCenter: { value: new THREE.Vector2() },
    uRq: { value: 1 }, uRr: { value: 1 }, uBTime: { value: 0 }, uPx: { value: 1 }, uGlow: { value: new THREE.Color(0xffd29a) } };
  const BLOOM_GLSL = `
    uniform float uBloom, uRq, uRr, uBTime, uPx; uniform int uVar; uniform vec3 uEdge[4]; uniform vec2 uCenter; uniform vec3 uGlow;
    vec4 bloomTint;
    float bHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
    float bNoise(float x) { float i = floor(x), f = fract(x); return mix(bHash(vec2(i, 3.7)), bHash(vec2(i + 1.0, 3.7)), f * f * (3.0 - 2.0 * f)); }
    float quadSd(vec2 p) { float d = -1e9; for (int i = 0; i < 4; i++) d = max(d, dot(uEdge[i].xy, p) - uEdge[i].z); return d; }
    bool bloomOut(vec2 p) {
      bloomTint = vec4(0.0);
      if (uBloom >= 0.9999) return false;
      float fade = 1.0 - uBloom;
      if (uVar == 0) {
        float sd = quadSd(p), R = uBloom * uRq;
        if (sd > R) return true;
        bloomTint = vec4(1.0, 0.97, 0.92, (1.0 - smoothstep(0.0, 3.0 * uPx, R - sd)) * 0.9 * fade);
      } else if (uVar == 1) {
        vec2 d = p - uCenter; float r = length(d) / uRr, a = atan(d.y, d.x);
        float wob = (bNoise(a * 2.5 + uBTime * 0.6) - 0.5) * 0.12 + (bNoise(a * 7.0 - uBTime) - 0.5) * 0.05;
        float R = uBloom * 1.03 + wob * fade, th = 0.06 * fade * bHash(floor(p / (2.0 * uPx)) + floor(uBTime * 24.0));
        if (r > R - th) return true;
        bloomTint = vec4(uGlow, (1.0 - smoothstep(0.0, 0.14 * fade + 1e-3, R - r)) * 0.8 * fade);
      } else {
        float cs = 30.0 * uPx; vec2 cell = floor(p / cs), cc = (cell + 0.5) * cs;
        float sd = quadSd(cc) + (bHash(cell) - 0.5) * 0.16 * uRq, R = uBloom * uRq * 1.1;
        if (sd > R) return true;
        vec2 f = fract(p / cs) * cs; float ln = step(min(min(f.x, f.y), min(cs - f.x, cs - f.y)), 1.2 * uPx);
        bloomTint = vec4(mix(vec3(0.94, 0.95, 0.97), vec3(0.36, 0.47, 0.86), ln), (1.0 - smoothstep(0.0, 0.1 * uRq, R - sd)) * mix(0.45, 1.0, ln) * fade);
      }
      return false;
    }`;
  const revHook = m => { m.defines = { ...(m.defines || {}), DESERT_REV: '' }; m.onBeforeCompile = sh => Object.assign(sh.uniforms, REV, BLOOM); m.customProgramCacheKey = () => 'desert-rev'; return m; };
  const groundHook = m => { m.defines = { ...(m.defines || {}), DESERT_GROUND: '' }; m.customProgramCacheKey = () => 'desert-rev-ground'; return m; };
  const DEPTH = revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking })), DEPTH_G = groundHook(revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking })));
  const mat = (c, o = {}) => revHook(new THREE.MeshStandardMaterial({ color: c, roughness: 1, metalness: 0, flatShading: true, ...o }));

  // ---------- sky dome ----------
  function sky(L) {
    const s = new THREE.Vector3(...L.sun).normalize();
    skyMat = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false, toneMapped: false,   // encoded like everything else, so it looks the same with and without post
      uniforms: { zen: { value: new THREE.Color(L.zenith) }, hor: { value: new THREE.Color(L.horizon) }, haze: { value: new THREE.Color(L.haze) }, sun: { value: s }, sunCol: { value: new THREE.Color(L.sunCol) },
        uT: { value: 0 }, uStar: { value: 0 }, uSkyRev: { value: 1 }, uVoid: REV.uVoid, uRev: REV.uRev, uMode: REV.uMode },
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `uniform vec3 zen, hor, haze, sun, sunCol, uVoid; uniform float uT, uStar, uSkyRev, uRev; uniform int uMode; varying vec3 vD;
        float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        void main(){
          vec3 d = normalize(vD); float h = clamp(d.y, 0.0, 1.0);
          vec3 c = mix(hor, zen, pow(h, 0.45));
          c = mix(c, haze, (1.0 - smoothstep(0.0, 0.09, h)) * 0.55);              // soft haze band sitting on the horizon
          float g = max(dot(d, sun), 0.0); c += sunCol * (pow(g, 600.0) * 1.2 + pow(g, 8.0) * 0.12);
          // thin high cirrus, lit warm on the sun side; only a few streaks so the sky stays clean behind the slide
          { vec2 cp = vec2(atan(d.z, d.x) * 3.0, d.y * 18.0); float cl = 0.0, w = 0.5; vec2 q = cp * vec2(1.0, 3.5);
            for (int i = 0; i < 5; i++) { cl += w * (0.5 + 0.5 * sin(q.x * 1.7 + sin(q.y * 1.3 + q.x * 0.7) * 1.8)) * (0.5 + 0.5 * sin(q.y * 2.1 + q.x * 0.4)); q *= 2.07; q += 1.7; w *= 0.5; }
            float band = smoothstep(0.06, 0.14, d.y) * (1.0 - smoothstep(0.34, 0.55, d.y));
            float cov = smoothstep(0.62, 0.86, cl) * band * 0.55;
            vec3 cc = mix(vec3(0.95, 0.72, 0.62), vec3(1.0, 0.82, 0.55), pow(g, 3.0));
            c = mix(c, cc * (0.75 + 0.45 * pow(g, 2.0)), cov); }
          // stars: sparse half-degree cells, a few lit, each twinkling at its own rate; they fade in with uStar
          vec2 uv = vec2(atan(d.z, d.x), asin(clamp(d.y, -1.0, 1.0))) * 114.6; vec2 cell = floor(uv); float hs = hash(cell);
          if (hs > 0.9925 && uStar > 0.0) {
            vec2 o = vec2(hash(cell + 3.1), hash(cell + 7.7)) * 0.6 + 0.2; float r = length(fract(uv) - o);
            float b = 0.4 + 0.6 * hash(cell + 11.3) * hash(cell + 2.9);
            float tw = 0.6 + 0.4 * sin(uT * (1.1 + 2.6 * hash(cell + 5.2)) + hs * 60.0);
            float st = smoothstep(0.17, 0.0, r) * b * tw * smoothstep(0.12, 0.5, d.y) * (1.0 - min(1.0, pow(g, 3.0) * 3.0));
            c += vec3(1.0, 0.96, 0.9) * st * uStar * 1.1;
          }
          // build C: the sky arrives in cells too, three degrees square, from the horizon up, each outlined in the grid's blue as it lands
          if (uMode == 2 && uRev < 0.9999) {
            vec2 sc = vec2(atan(d.z, d.x), asin(clamp(d.y, -1.0, 1.0))) * 57.2958 / 3.0, cell = floor(sc);
            float order = clamp(cell.y * 3.0 / 30.0, 0.0, 1.0) * 0.7 + hash(cell + 9.1) * 0.3;     // spread over the sky the frame actually sees
            float t = clamp((uRev - 0.45) / 0.55, 0.0, 1.0), g = smoothstep(order * 0.85, order * 0.85 + 0.15, t);
            if (g <= 0.002) discard;
            vec2 cf = abs(fract(sc - 0.5) - 0.5) / max(fwidth(sc), vec2(1e-4)); float edge = 1.0 - clamp(min(cf.x, cf.y) - 0.8, 0.0, 1.0);
            c = mix(mix(uVoid * 0.94, vec3(0.24, 0.40, 0.96), edge), c, smoothstep(0.05, 0.85, g));
          }
          gl_FragColor = vec4(pow(max(mix(uVoid, c, uSkyRev), vec3(0.0)), vec3(2.2)), 1.0);
          #include <colorspace_fragment>
        }` });
    const d = new THREE.Mesh(new THREE.SphereGeometry(95000, 64, 32), skyMat); d.position.set(C.x, Y0, C.z); d.renderOrder = -10; d.frustumCulled = false; return d;
  }

  // ---------- haze: exponential, thicker near the ground, warmer toward the sun ----------
  // Replaces three's exp2 fog path for this scene, so the board stays clear and each band of desert behind it fades a step further
  const HAZE_H = 30 * M, HAZE_DENSITY = 2.0e-5;
  function installHaze(L) {
    installWorldChunks();
    REV.uHzY0.value = Y0; REV.uHzH.value = HAZE_H; REV.uHzSun.value.set(...L.sun).normalize(); REV.uHzSunC.value.set(L.sunCol);
  }

  // ---------- ground and ranges ----------
  // ground height relative to Y0 at local (x, z) around the card; shared by the mesh and anything that has to sit on it
  const groundN = (x, z) => Math.sin(x * 0.0021 + 1.3) * Math.cos(z * 0.0017) + Math.sin(x * 0.0007 - z * 0.0009) * 1.6;
  function groundH(x, z) { const d = Math.hypot(x, z), rd = road ? road.dist(x + C.x, z + C.z) : 1e9;
    const amp = Math.min(1, Math.max(0, (rd - 900) / 3000)) * Math.min(1, d / 8000); return groundN(x, z) * 26 * amp + amp * Math.max(0, d - 20000) * 0.01; }
  function ground(L, r) {
    const g = new THREE.PlaneGeometry(160000, 160000, 220, 220); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position, col = [], a = new THREE.Color(L.sand[0]), b = new THREE.Color(L.sand[1]), t = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), z = p.getZ(i);
      const n = groundN(x, z);
      p.setY(i, groundH(x, z));
      t.copy(a).lerp(b, 0.5 + 0.5 * Math.sin(x * 0.0011 + z * 0.0013 + n)); col.push(t.r, t.g, t.b);
    }
    g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.computeVertexNormals();
    const m = new THREE.Mesh(g, groundHook(revHook(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true }))));
    m.position.set(C.x, Y0, C.z); m.receiveShadow = true; groundMesh = m; return m;
  }
  // value noise for terrain
  const vn = (seed => { const P = new Uint8Array(512), r = rng(seed); for (let i = 0; i < 256; i++) P[i] = i; for (let i = 255; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [P[i], P[j]] = [P[j], P[i]]; } for (let i = 0; i < 256; i++) P[i + 256] = P[i];
    const g = (h, x, y) => ((h & 1) ? x : -x) + ((h & 2) ? y : -y), f = t => t * t * t * (t * (t * 6 - 15) + 10);
    return (x, y) => { const X = Math.floor(x) & 255, Y = Math.floor(y) & 255; x -= Math.floor(x); y -= Math.floor(y); const u = f(x), v = f(y), A = P[X] + Y, B = P[X + 1] + Y;
      return (1 - v) * ((1 - u) * g(P[A], x, y) + u * g(P[B], x - 1, y)) + v * ((1 - u) * g(P[A + 1], x, y - 1) + u * g(P[B + 1], x - 1, y - 1)); }; })(91);
  const ridged = (x, y, oct = 6) => { let a = 0, f = 1, w = 0.5, s2 = 0; for (let i = 0; i < oct; i++) { const n = 1 - Math.abs(vn(x * f, y * f)); a += n * n * w; s2 += w; f *= 2.03; w *= 0.5; } return a / s2; };
  function range(L, R, hMin, hMax, color, seed, mesa) {
    // eroded ridges: ridged multi-octave noise around the horizon, a deep band so the sun models real slopes,
    // alluvial fans at the foot (lighter), rock on the steep faces (darker), smooth-shaded
    const r = rng(seed), N = 1400, rows = 14, pos = [], col = [], idx = [], off = r() * 50;
    const base = new THREE.Color(color), fan = base.clone().lerp(new THREE.Color(L.sand[0]), 0.55), rock = base.clone().multiplyScalar(0.72), t3 = new THREE.Color();
    for (let i = 0; i <= N; i++) { const a = i / N * Math.PI * 2, cx = Math.cos(a), sz = Math.sin(a);
      for (let j = 0; j < rows; j++) { const t = j / (rows - 1), rr = R * (1 + t * 0.16);
        const nx = cx * 3.2 + off, ny = sz * 3.2 + t * 1.3;
        let hgt = ridged(nx, ny) * (0.55 + 0.45 * vn(nx * 0.35 + 9, ny * 0.35)), prof = Math.sin(Math.min(1, t * 1.25) * Math.PI / 2);
        if (mesa) hgt = hgt > 0.42 ? 0.9 : hgt * 0.4;
        const y = -200 + (hMin + (hMax - hMin) * hgt) * prof * (1 - Math.pow(t, 6) * 0.35);
        pos.push(cx * rr, y, sz * rr);
        const k = Math.min(1, y / (hMin + (hMax - hMin) * 0.6));
        t3.copy(fan).lerp(base, Math.min(1, k * 1.6)).lerp(rock, Math.max(0, hgt - 0.55) * 1.4); col.push(t3.r, t3.g, t3.b); }
      if (i < N) for (let j = 0; j < rows - 1; j++) { const k = i * rows + j, k2 = (i + 1) * rows + j; idx.push(k, k + 1, k2, k2, k + 1, k2 + 1); } }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx); g.computeVertexNormals();
    const m = new THREE.Mesh(g, groundHook(mat(0xffffff, { side: THREE.DoubleSide, vertexColors: true, flatShading: false, roughness: 0.95 }))); m.position.set(C.x, Y0, C.z); m.receiveShadow = false; return m;
  }


  // ---------- road ----------
  function makeRoad(L, P, az) {      // P: a point on the centre line (world x,z); az: heading in degrees (0 = -z, 90 = +x)
    const dir = new THREE.Vector3(Math.sin(az * Math.PI / 180), 0, -Math.cos(az * Math.PI / 180)), n = new THREE.Vector3(-dir.z, 0, dir.x);
    const lane = 3.7 * M, shoulderW = 1.4 * M, len = 140000;
    const g = new THREE.Group(), roles = { yellow: [], white: [] }; g.userData.roles = roles;
    const strip = (w, off, color, y, dash) => {
      if (!dash) { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, len), groundHook(mat(color, { polygonOffset: true, polygonOffsetFactor: -y, polygonOffsetUnits: -y })));
        m.rotation.x = -Math.PI / 2; m.rotation.z = -Math.atan2(dir.x, -dir.z); m.position.set(P.x + n.x * off, Y0 + y, P.z + n.z * off); m.receiveShadow = true; m.userData.w = w; m.userData.len = len; g.add(m); return m; }
    };
    roles.shoulder = strip(2 * lane + 2 * shoulderW + 1.2 * M, 0, L.shoulder, 0.6);      // gravel shoulder band
    roles.asphalt = strip(2 * lane + 2 * shoulderW, 0, L.asphalt, 1.2);                 // asphalt
    roles.yellow.push(strip(0.12 * M, -0.12 * M, 0xe8b532, 1.8), strip(0.12 * M, 0.12 * M, 0xe8b532, 1.8));   // double yellow
    roles.white.push(strip(0.15 * M, lane + 0.1 * M, 0xeeeeea, 1.8), strip(0.15 * M, -lane - 0.1 * M, 0xeeeeea, 1.8));  // fog lines
    road = { P: P.clone(), dir, n, lane, halfW: lane + shoulderW + 0.6 * M, group: g,
      dist(x, z) { const dx = x - P.x, dz = z - P.z; return Math.abs(dx * n.x + dz * n.z); },
      at(s, laneSide) { return new THREE.Vector3(P.x + dir.x * s + n.x * laneSide * lane * 0.5, Y0, P.z + dir.z * s + n.z * laneSide * lane * 0.5); } };
    return g;
  }

  // ---------- billboard structure (behind and below the card; nothing crosses in front of the face) ----------
  function billboard(L) {
    const g = new THREE.Group(); g.userData.kind = 'billboard'; const _g = g, dark = mat(L.frame), steel = mat(0x6d7178), galv = mat(0x8e9298);
    const box = (w, h, d, x, y, z, m = dark) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); b.position.set(C.x + x, y, C.z + z); b.castShadow = b.receiveShadow = true; g.add(b); return b; };
    box(W + 28, H + 28, 30, 0, C.y, -22);                                       // face frame, card sits on its front
    for (let i = -3; i <= 3; i++) box(14, H + 10, 30, i * W / 7, C.y, -70, steel);           // back verticals
    box(W, 18, 30, 0, C.y + H * 0.3, -110, steel); box(W, 18, 30, 0, C.y - H * 0.3, -110, steel);    // back stringers
    box(W * 0.62, 40, 46, 0, bottom - 60, -70, steel);                           // head frame across the pole top
    const cw = box(W + 40, 8, 1.0 * M, 0, bottom - 46, 0.5 * M - 40, galv);      // catwalk grating
    box(W + 40, 26, 6, 0, bottom - 58, 1.0 * M - 40, galv);                      // catwalk toe plate
    for (let i = -2; i <= 2; i++) { const x = i * W / 4.4;                       // lights: arms reaching out below the face
      box(8, 8, 1.1 * M, x, bottom - 70, 0.9 * M, steel); const hd = box(46, 22, 30, x, bottom - 64, 1.45 * M, dark); hd.rotation.x = 0.5; }
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.42 * M, 0.5 * M, bottom - 60 - Y0, 20), steel);
    pole.position.set(C.x, (bottom - 60 + Y0) / 2, C.z - 70); pole.castShadow = true; g.add(pole);
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(0.9 * M, 1.0 * M, 24, 20), mat(0xbdb6a8)); pad.position.set(C.x, Y0 + 8, C.z - 70); pad.receiveShadow = true; g.add(pad);
    // the ladder up the back of the pole
    for (let y = Y0 + 2 * M; y < bottom - 80; y += 0.35 * M) box(36, 4, 4, 0, y, -70 - 0.5 * M, galv);
    return g;
  }

  // ---------- flora, rocks, cars ----------
  function joshua(L, r, s) {
    const g = new THREE.Group(), bark = mat(L.trunk), leaf = mat(L.treeCol);
    const h = (2.5 + r() * 3) * M * s, tr = new THREE.Mesh(new THREE.CylinderGeometry(0.16 * M, 0.24 * M, h, 6), bark); tr.position.y = h / 2; g.add(tr);
    const nb = 2 + Math.floor(r() * 4);
    for (let i = 0; i < nb; i++) {
      const a = r() * Math.PI * 2, tilt = 0.5 + r() * 0.6, bl = (0.8 + r() * 1.4) * M * s, by = h * (0.65 + r() * 0.3);
      const b = new THREE.Mesh(new THREE.CylinderGeometry(0.1 * M, 0.14 * M, bl, 5), bark); const tip = new THREE.Vector3(Math.cos(a) * Math.sin(tilt), Math.cos(tilt), Math.sin(a) * Math.sin(tilt));
      b.position.set(tip.x * bl / 2, by + tip.y * bl / 2, tip.z * bl / 2); b.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tip); g.add(b);
      const tuft = new THREE.Mesh(new THREE.IcosahedronGeometry(0.42 * M * s, 0), leaf); tuft.position.set(tip.x * bl, by + tip.y * bl + 0.15 * M, tip.z * bl); tuft.scale.y = 1.3; g.add(tuft);
    }
    const top = new THREE.Mesh(new THREE.IcosahedronGeometry(0.45 * M * s, 0), leaf); top.position.y = h + 0.2 * M; top.scale.y = 1.3; g.add(top);
    g.traverse(o => { if (o.isMesh) o.castShadow = true; }); return g;
  }
  function saguaro(L, r, s) {
    const g = new THREE.Group(), sk = mat(L.treeCol), R = 0.3 * M * s, h = (4 + r() * 5) * M * s;
    const col = (x, y0, y1, z) => { const c = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.8, R, y1 - y0, 10), sk); c.position.set(x, (y0 + y1) / 2, z); g.add(c);
      const cap = new THREE.Mesh(new THREE.SphereGeometry(R * 0.8, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), sk); cap.position.set(x, y1, z); g.add(cap); };
    col(0, 0, h, 0);
    const na = Math.floor(r() * 3);
    for (let i = 0; i < na; i++) { const sd = i % 2 ? 1 : -1, a = r() * 0.6, out = (0.7 + r() * 0.4) * M * s, ay = h * (0.35 + r() * 0.25), ah = ay + (1 + r() * 1.6) * M * s;
      const x = Math.cos(a) * out * sd, z = Math.sin(a) * out;
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(R * 0.7, R * 0.7, out, 8), sk); arm.position.set(x / 2, ay, z / 2); arm.rotation.z = Math.PI / 2 * sd; arm.rotation.y = -a * sd; g.add(arm);
      col(x, ay, ah, z); }
    g.traverse(o => { if (o.isMesh) o.castShadow = true; }); return g;
  }
  function ocotillo(L, r, s) {
    const g = new THREE.Group(), m = mat(0x6b6a45), n = 8 + Math.floor(r() * 6);
    for (let i = 0; i < n; i++) { const l = (2 + r() * 2.5) * M * s, a = r() * Math.PI * 2, t = 0.1 + r() * 0.35, d = new THREE.Vector3(Math.cos(a) * Math.sin(t), Math.cos(t), Math.sin(a) * Math.sin(t));
      const c = new THREE.Mesh(new THREE.CylinderGeometry(0.03 * M, 0.05 * M, l, 4), m); c.position.copy(d).multiplyScalar(l / 2); c.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d); c.castShadow = true; g.add(c); }
    return g;
  }
  function scatter(L, eye, view) {
    const g = new THREE.Group(), r = rng(7);
    // a composed first row of Joshua trees across the frame, and behind it a strip kept clear of rocks and trees for the tumbleweed
    const dl = (x, z) => view ? { d: (x - view.eye.x) * view.fwd.x + (z - view.eye.z) * view.fwd.z, l: (x - view.eye.x) * view.right.x + (z - view.eye.z) * view.right.z } : null;
    const inStrip = (x, z) => { if (!view) return false; const q = dl(x, z); return q.d > view.row + 1.0 * M && q.d < view.row + 6.0 * M; };
    // the sightline from the low camera to the tumbleweed's path: anything here stays under ~0.4 m so it can't hide the roll
    const inSight = (x, z) => { if (!view) return false; const q = dl(x, z); return q.d > 5 * M && q.d < view.row + 1.0 * M && Math.abs(q.l) < q.d * view.tanH * 1.05; };
    const ok = (x, z, clear, kind) => (!road || road.dist(x, z) > road.halfW + clear) && Math.hypot(x - C.x, z - (C.z - 70)) > 2.2 * M && (!eye || Math.hypot(x - eye.x, z - eye.z) > clear * 6 + 4 * M) && (kind === 'bush' || !inStrip(x, z));
    const place = (n, rMin, rMax, clear, fn, kind) => { let k = 0, tries = 0; while (k < n && tries++ < n * 30) {
      const a = r() * Math.PI * 2, d = rMin + Math.pow(r(), 1.6) * (rMax - rMin), x = C.x + Math.cos(a) * d, z = C.z + Math.sin(a) * d;
      if (!ok(x, z, clear, kind)) continue; fn(x, z, d); k++; } };
    // bushes (instanced)
    const bushGeo = new THREE.IcosahedronGeometry(1, 1), bushCount = 1400;
    L.bush.forEach((c, bi) => {
      const im = new THREE.InstancedMesh(bushGeo, mat(c), bushCount / 3 | 0), d = new THREE.Object3D(); let i = 0;
      place(bushCount / 3 | 0, 300, 26000, 0.8 * M, (x, z, dd) => { const s = (0.2 + Math.pow(r(), 2) * 0.45) * M * (dd > 8000 ? 1.5 : 1) * (inStrip(x, z) || inSight(x, z) ? 0.55 : 1); d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r() * .6), s * 0.55, s * (1 + r() * .6)); d.rotation.y = r() * 6; d.updateMatrix(); im.setMatrixAt(i++, d.matrix); placed.bush.push({ x, z, s: s / M, rot: d.rotation.y, i: i - 1, im, sight: inSight(x, z) || inStrip(x, z) }); }, 'bush');
      im.count = i; im.castShadow = true; im.receiveShadow = true; im.userData.kind = 'bush'; g.add(im);
    });
    // rocks
    const rockGeo = new THREE.DodecahedronGeometry(1, 0), rk = new THREE.InstancedMesh(rockGeo, mat(L.rock), 260), d = new THREE.Object3D(); let ri = 0;
    place(260, 400, 18000, 0.5 * M, (x, z) => { const s = (0.12 + Math.pow(r(), 4) * 1.0) * M * (inSight(x, z) ? 0.35 : 1); d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r()), s * (0.5 + r() * 0.5), s * (1 + r())); d.rotation.set(r(), r() * 6, r()); d.updateMatrix(); rk.setMatrixAt(ri++, d.matrix); placed.rock.push({ x, z, s: s / M, rot: d.rotation.y, i: ri - 1, im: rk }); });
    rk.count = ri; rk.castShadow = rk.receiveShadow = true; rk.userData.kind = 'rock'; g.add(rk);
    // a few boulder piles near the billboard
    for (let k = 0; k < 2; k++) { const bx = C.x + (k - 1) * 9 * M + (r() - .5) * 4 * M, bz = C.z - (3 + r() * 9) * M; if (!ok(bx, bz, M) || inStrip(bx, bz) || inSight(bx, bz)) continue;
      for (let j = 0; j < 4; j++) { const s = (0.4 + r() * 0.7) * M, b = new THREE.Mesh(rockGeo, mat(L.rock)); b.position.set(bx + (r() - .5) * 2 * M, Y0 + s * .3, bz + (r() - .5) * 2 * M); b.scale.set(s * 1.3, s * .8, s); b.rotation.set(r(), r() * 6, r()); b.castShadow = b.receiveShadow = true; b.userData.kind = 'rock'; g.add(b); placed.rock.push({ x: b.position.x, z: b.position.z, s: s * 1.3 / M, rot: b.rotation.y, mesh: b }); } }
    // trees
    const tree = L.tree === 'joshua' ? joshua : saguaro;
    place(L.tree === 'joshua' ? 70 : 55, 1800, 24000, 1.5 * M, (x, z, dd) => { const t = tree(L, r, dd > 9000 ? 1.25 : 1); t.position.set(x, Y0, z); t.rotation.y = r() * 6; t.userData.kind = 'tree'; g.add(t); trees.push(new THREE.Vector3(x, Y0, z)); placed.tree.push({ x, z, rot: t.rotation.y, big: dd > 9000, node: t }); });
    if (view && L.tree === 'joshua') {
      const half = view.row * view.tanH, poleL = dl(C.x, C.z - 70).l;
      for (const u of [-0.92, -0.55, -0.12, 0.38, 0.8]) { let lat = u * half + (r() - .5) * 1.5 * M; if (Math.abs(lat - poleL) < 3 * M) lat += 3.5 * M * Math.sign(lat - poleL || 1);
        const dd = view.row + (r() - .5) * 1.6 * M, x = view.eye.x + view.fwd.x * dd + view.right.x * lat, z = view.eye.z + view.fwd.z * dd + view.right.z * lat;
        if (road && road.dist(x, z) < road.halfW + M) continue;
        const t = joshua(L, r, 1.1); t.position.set(x, Y0, z); t.rotation.y = r() * 6; t.userData.kind = 'tree'; g.add(t); trees.push(new THREE.Vector3(x, Y0, z)); placed.tree.push({ x, z, rot: t.rotation.y, row: true, node: t }); }
    }
    if (L.tree === 'saguaro') place(40, 900, 12000, 1.2 * M, (x, z) => { const t = ocotillo(L, r, 1); t.position.set(x, Y0, z); g.add(t); });
    return g;
  }
  function car(color, kind) {
    const g = new THREE.Group(), body = mat(color), glass = mat(0x2b3440), tire = mat(0x1d1d1f);
    const L = kind === 'truck' ? 5.6 * M : 4.7 * M, Wd = 1.85 * M;
    const b = new THREE.Mesh(new THREE.BoxGeometry(Wd, 0.7 * M, L), body); b.position.y = 0.75 * M; g.add(b);
    const cab = new THREE.Mesh(new THREE.BoxGeometry(Wd * 0.92, 0.6 * M, kind === 'truck' ? 1.8 * M : 2.6 * M), glass);
    cab.position.set(0, 1.35 * M, kind === 'truck' ? 0.9 * M : 0.1 * M); g.add(cab);
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.36 * M, 0.36 * M, 0.25 * M, 12), tire); w.rotation.z = Math.PI / 2; w.position.set(sx * Wd / 2, 0.36 * M, sz * L * 0.32); g.add(w); }
    g.traverse(o => { if (o.isMesh) o.castShadow = true; }); return g;
  }

  // ---------- vehicles: side profiles extruded across their width (metres), nose toward +z ----------
  function profileBody(pts, width, color) {
    const sh = new THREE.Shape(pts.map(([z, y]) => new THREE.Vector2(z * M, y * M)));
    const g = new THREE.ExtrudeGeometry(sh, { depth: width * M, bevelEnabled: false }); g.rotateY(-Math.PI / 2); g.translate(width * M / 2, 0, 0);
    const m = new THREE.Mesh(g, mat(color)); m.castShadow = true; m.receiveShadow = true; return m;
  }
  function vehicle({ body, glass, width, color, wheels, wheelR, lights }) {
    const g = new THREE.Group();
    g.add(profileBody(body, width, color));
    const gl2 = profileBody(glass, width + 0.03, 0x1b2129); gl2.material.roughness = 0.35; gl2.material.metalness = 0.2; g.add(gl2);
    const tire = mat(0x18181a), rim = mat(0x7b7f86), spin = [];
    for (const z of wheels) for (const sx of [-1, 1]) {
      const pv = new THREE.Group(); pv.position.set(sx * (width / 2 - 0.12) * M, wheelR * M, z * M);
      const t = new THREE.Mesh(new THREE.CylinderGeometry(wheelR * M, wheelR * M, 0.27 * M, 18), tire); t.rotation.z = Math.PI / 2; t.castShadow = true; pv.add(t);
      const h = new THREE.Mesh(new THREE.CylinderGeometry(wheelR * 0.55 * M, wheelR * 0.55 * M, 0.285 * M, 8), rim); h.rotation.z = Math.PI / 2; pv.add(h);
      g.add(pv); spin.push(pv);
    }
    const lamp = (c, z, y, w, e) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w * M, 0.08 * M, 0.06 * M), revHook(new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: e, roughness: .5 })));
      b.position.set(0, y * M, z * M); g.add(b); };
    lamp(0xff2a1a, lights.rear[0], lights.rear[1], width * 0.86, 0.9); lamp(0xfff4e0, lights.front[0], lights.front[1], width * 0.8, 0.6);
    g.userData = { spin, wheelR: wheelR * M }; return g;
  }
  const sportsCar = color => vehicle({ width: 1.96, color, wheelR: 0.34, wheels: [-1.38, 1.42],
    body: [[-2.25, 0.3], [-2.25, 0.86], [-1.6, 0.97], [-0.9, 1.2], [0.15, 1.22], [0.95, 0.94], [1.9, 0.76], [2.27, 0.6], [2.27, 0.34], [1.95, 0.26], [-1.95, 0.26]],
    glass: [[-1.52, 0.97], [-0.88, 1.18], [0.12, 1.2], [0.9, 0.95], [0.3, 0.93], [-1.3, 0.93]],
    lights: { rear: [-2.26, 0.8], front: [2.2, 0.64] } });
  // a modern minivan (Odyssey / Sienna proportions): 5.1 m long, 1.78 m tall, long sloped hood and windshield, near-upright hatch
  const minivan = color => vehicle({ width: 1.99, color, wheelR: 0.36, wheels: [-1.62, 1.48],
    body: [[-2.56, 0.36], [-2.56, 1.05], [-2.47, 1.6], [-2.2, 1.76], [0.5, 1.78], [1.55, 1.13], [2.42, 0.94], [2.58, 0.72], [2.56, 0.36], [2.2, 0.24], [-2.2, 0.24]],
    glass: [[-2.4, 1.12], [-2.34, 1.6], [-2.12, 1.72], [0.46, 1.74], [1.48, 1.15], [0.2, 1.1]],
    lights: { rear: [-2.57, 1.02], front: [2.52, 0.84] } });

  // ---------- tumbleweed: a shell of short twigs, flattened a touch ----------
  function tumbleweed(radius, seed) {
    // Russian thistle: a short stub of a stem, ~16 primary branches radiating from it, each forking three or four times,
    // curving along the shell as they near it, so the ball is a dense, see-through lattice of wiry straw-coloured stems
    const r = rng(seed), pos = [], nrm = [], col = [], up = new THREE.Vector3(0, 1, 0);
    const straw = new THREE.Color(0xe6cc98), grey = new THREE.Color(0xcbb894), rust = new THREE.Color(0xb7835c), t3 = new THREE.Color();
    const tube = (a, b, ra, rb, c) => {
      const d = b.clone().sub(a).normalize(), s1 = Math.abs(d.y) < 0.9 ? up : new THREE.Vector3(1, 0, 0), u = new THREE.Vector3().crossVectors(d, s1).normalize(), v = new THREE.Vector3().crossVectors(d, u);
      const ring = (o, rr) => [0, 1, 2, 3].map(k => { const ang = k * Math.PI / 2; return { p: o.clone().addScaledVector(u, Math.cos(ang) * rr).addScaledVector(v, Math.sin(ang) * rr), n: u.clone().multiplyScalar(Math.cos(ang)).addScaledVector(v, Math.sin(ang)) }; });
      const A = ring(a, ra), B = ring(b, rb);
      for (let k = 0; k < 4; k++) { const k2 = (k + 1) % 4;
        for (const q of [A[k], B[k], A[k2], A[k2], B[k], B[k2]]) { pos.push(q.p.x, q.p.y, q.p.z); nrm.push(q.n.x, q.n.y, q.n.z); col.push(c.r, c.g, c.b); } } };
    const grow = (p, dir, len, rad, depth) => {
      const n = 3 + Math.floor(r() * 2), seg = len / n; let q = p.clone(), d = dir.clone(), rr = rad;
      const c = t3.copy(straw).lerp(grey, r() * 0.55).lerp(rust, r() < 0.15 ? 0.4 : 0).clone();
      for (let i = 0; i < n; i++) {
        d.add(new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).multiplyScalar(0.55)).normalize();
        const out = q.clone().normalize(), dist = q.length() / radius;
        if (dist > 0.55) d.addScaledVector(out, -d.dot(out) * Math.min(1, (dist - 0.55) * 4.5)).normalize();   // curl along the shell
        if (dist > 0.95) d.addScaledVector(out, -0.8).normalize();                                                // and never past it
        const nq = q.clone().addScaledVector(d, seg), nr = rr * 0.86; tube(q, nq, rr, nr, c); q = nq; rr = nr;
      }
      if (depth < 4) { const kids = depth < 1 ? 3 : 2 + (r() < 0.4 ? 1 : 0);
        for (let k = 0; k < kids; k++) { const nd = d.clone().add(new THREE.Vector3(r() - 0.5, r() - 0.5, r() - 0.5).multiplyScalar(1.3)).normalize();
          grow(q, nd, len * (0.6 + r() * 0.12), rr * 0.78, depth + 1); } }
    };
    for (let i = 0; i < 30; i++) { const d = new THREE.Vector3(r() * 2 - 1, (r() * 2 - 1) * 0.8, r() * 2 - 1).normalize(); grow(d.clone().multiplyScalar(radius * 0.05), d, radius * 0.3, radius * 0.036, 0); }   // dense enough to read as a ball at 20+ m
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g.computeBoundingSphere(); { const bs = g.boundingSphere, k = radius / Math.max(1, bs.radius); g.translate(-bs.center.x, -bs.center.y, -bs.center.z); g.scale(k, k, k); }   // centred, true to size
    const m = new THREE.Mesh(g, mat(0xffffff, { flatShading: false, vertexColors: true, roughness: 0.85 })); m.scale.y = 0.86; m.castShadow = true; m.receiveShadow = true; m.customDepthMaterial = DEPTH;
    const holder = new THREE.Group(); holder.add(m); return holder;
  }


  // ---------- the sequence after landing ----------
  // t = 2 s red sports car, left to right in the near lane · t = 10 s blue minivan, right to left in the far lane ·
  // t = 13 s tumbleweed crosses behind the first row of Joshua trees in ~8 s · stars fade in over ~20 s · then light traffic
  const clock = { t: 0, playing: false, manual: false }, actors = [];
  let evI = 0, nextCar = Infinity, trafficN = 0, Lcur = null;
  const ndc = p => p.clone().project(camera);
  function laneRun(make, side, dirSign, speed) {      // dirSign -1: travels against road.dir (screen left→right here)
    camera.updateMatrixWorld();
    let sIn = null, sOut = null;
    for (let k = 0; k <= 600; k++) { const sv = dirSign < 0 ? 400 * M - k * M : -100 * M + k * M; const q = ndc(road.at(sv, side).setY(Y0 + 0.6 * M));
      const vis = q.z < 1 && Math.abs(q.x) < 1.08 && Math.abs(q.y) < 1.08; if (vis && sIn === null) sIn = sv; if (vis) sOut = sv; }
    if (sIn === null) return;
    const s0 = sIn - dirSign * 6 * M, s1 = sOut + dirSign * 8 * M, v = make(), heading = road.dir.clone().multiplyScalar(dirSign);
    v.rotation.y = Math.atan2(heading.x, heading.z); world.add(v); window.__lastCar = { v, sIn, sOut, s0, s1 };
    let sv = s0;
    actors.push({ update(dt) { sv += dirSign * speed * M * dt; v.position.copy(road.at(sv, side)).setY(Y0 + 2);
      for (const w of v.userData.spin) w.rotation.x += speed * M * dt / v.userData.wheelR;
      return dirSign > 0 ? sv > s1 + 40 * M : sv < s1; }, dispose() { world.remove(v); } });
  }
  function tumbleRun(seconds) {
    camera.updateMatrixWorld();
    const eye = camera.position.clone(), fwd = new THREE.Vector3(); camera.getWorldDirection(fwd); fwd.y = 0; fwd.normalize();
    const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
    // the first row: the nearest Joshua trees that are in frame; the weed travels a few metres behind them
    const depths = trees.map(p => ({ p, q: ndc(p.clone().setY(Y0 + 1.5 * M)), d: p.clone().sub(eye).dot(fwd) }))
      .filter(o => o.q.z < 1 && Math.abs(o.q.x) < 1 && o.q.y > -1 && o.q.y < 1 && o.d > 6 * M).sort((a, b) => a.d - b.d);
    const first = viewInfo ? viewInfo.row : (depths.slice(0, 3).reduce((a, o) => a + o.d, 0) / Math.max(1, Math.min(3, depths.length)) || 22 * M);
    const depth = first + 3.5 * M, half = depth * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect;
    const a = eye.clone().addScaledVector(fwd, depth).addScaledVector(right, -half * 1.12), b = eye.clone().addScaledVector(fwd, depth).addScaledVector(right, half * 1.12);
    const len = a.distanceTo(b), dur = seconds * 1.12, rad = 0.5 * M, tw = tumbleweed(rad, 31); world.add(tw); window.__lastTw = tw;
    const r = rng(77), hops = []; { let t = 0; while (t < dur + 1) { const d = 0.5 + r() * 0.5; hops.push({ t, d, h: (0.3 + r() * 0.75) * M }); t += d; } }
    const axis = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), right).normalize().negate();
    let t = 0, rolled = 0, lastX = 0;
    window.__desertDebug = { firstRow: Math.round(first / M * 10) / 10, weedDepth: Math.round(depth / M * 10) / 10, crossM: Math.round(len / M) };
    actors.push({ update(dt) { t += dt; const k = t / dur;
      const x = len * (k + 0.012 * Math.sin(t * 1.9) - 0.012 * Math.sin(0));               // a little gusting in the pace
      const p = a.clone().lerp(b, Math.min(1.2, x / len));
      const hp = hops.find(h => t >= h.t && t < h.t + h.d) || hops[hops.length - 1], u = (t - hp.t) / hp.d;
      const lift = hp.h * 4 * u * (1 - u);
      p.y = Y0 + groundH(p.x - C.x, p.z - C.z) + rad * 0.86 + lift; tw.position.copy(p);
      const squash = 1 - 0.1 * Math.max(0, 1 - u / 0.12) * (hp.h / (0.6 * M)); tw.scale.set(1 + (1 - squash) * 0.5, squash, 1 + (1 - squash) * 0.5);
      rolled += (x - lastX) / rad; lastX = x; tw.children[0].rotation.set(0, 0, 0); tw.children[0].rotateOnWorldAxis(axis, rolled); tw.children[0].rotateOnWorldAxis(right, Math.sin(t * 2.3) * 0.25);
      return t > dur + 0.5; }, dispose() { world.remove(tw); } });
  }
  const carOf = (key, fallback) => () => TPL[key] ? vehicleFrom(TPL[key]) : fallback();
  const EVENTS = [
    { at: 2, fn: () => laneRun(carOf('sports', () => sportsCar(0xc8102e)), -1, -1, 26) },
    { at: 10, fn: () => laneRun(carOf('minivan', () => minivan(0x1f4f96)), 1, 1, 24) },
    { at: 13, fn: () => tumbleRun(8) },
  ];
  function update(dt) {
    if (!clock.playing) return;
    clock.t += dt;
    while (evI < EVENTS.length && clock.t >= EVENTS[evI].at) EVENTS[evI++].fn();
    if (clock.t >= nextCar) { const sw = trafficN++ % 2 === 0, cols = [0xe9e6df, 0x8d9299, 0x23262b, 0x6b7f8e];
      laneRun(trafficN % 2 ? carOf('minivan', () => minivan(cols[trafficN % cols.length])) : carOf('sports', () => sportsCar(cols[trafficN % cols.length])), sw ? -1 : 1, sw ? -1 : 1, 22 + Math.random() * 8);
      nextCar = clock.t + 14 + Math.random() * 10; }
    for (let i = actors.length - 1; i >= 0; i--) if (actors[i].update(dt)) { actors[i].dispose(); actors.splice(i, 1); }
    if (skyMat) { skyMat.uniforms.uT.value = clock.t; const k = Math.min(1, Math.max(0, (clock.t - 1) / 19)); skyMat.uniforms.uStar.value = (Lcur?.stars || 0) * k * k * (3 - 2 * k); }
  }

  // ---------- assemble ----------
  function build(key, roadDef, carDefs = [], eye = null, view = null) {
    if (world) { root.remove(world); world.traverse(o => { o.geometry?.dispose?.(); }); }
    lookKey = key; const L = LOOKS[key]; Lcur = L; world = new THREE.Group(); trees = []; placed.tree.length = placed.bush.length = placed.rock.length = 0; installHaze(L);
    road = null; const rd = makeRoad(L, roadDef.P, roadDef.az);
    world.add(sky(L), ground(L), rd, billboard(L), scatter(L, eye, view));
    world.add(range(L, 82000, 1800, 6200, L.mt[1], 3, L.mesa), range(L, 50000, 500, 3000, L.mt[0], 11, L.mesa), range(L, 30000, 120, 1100, L.mt[0], 17, L.mesa));
    const sd = new THREE.Vector3(...L.sun).normalize();
    const sun = new THREE.DirectionalLight(L.sunCol, L.sunI); sun.position.copy(C).addScaledVector(sd, 9000); sun.target.position.set(C.x, Y0, C.z + 600);
    sun.castShadow = true; sun.shadow.mapSize.set(4096, 4096); Object.assign(sun.shadow.camera, { left: -4600, right: 4600, top: 4600, bottom: -4600, near: 100, far: 24000 }); sun.shadow.bias = -0.0005; sun.shadow.normalBias = 10;   // low sun grazes the car hoods: less acne
    if (view) { const c0 = view.eye.clone().addScaledVector(view.fwd, 22 * M); c0.y = Y0; sun.target.position.copy(c0); sun.position.copy(c0).addScaledVector(sd, 12000); }
    world.add(sun, sun.target, hemiLight = new THREE.HemisphereLight(L.zenith, L.sand[0], L.hemi)); sunLight = sun;
    cars = carDefs.map((cd, i) => { const c = car(L.car[i % L.car.length], cd.kind); const p = road.at(cd.s, cd.side); c.position.copy(p);
      c.rotation.y = Math.atan2(road.dir.x, road.dir.z) + (cd.side > 0 ? 0 : Math.PI); world.add(c); return c; });
    world.traverse(o => { if (o.isMesh && o.material && o.material.defines && 'DESERT_REV' in o.material.defines) o.customDepthMaterial = 'DESERT_GROUND' in o.material.defines ? DEPTH_G : DEPTH; });
    root.add(world);
    hazeFog = new THREE.FogExp2(L.haze, HAZE_DENSITY);
  }

  // ---------- photoreal assets: each one takes over its blockout's place as soon as its file exists ----------
  const depthFor = o => {
    const m = [].concat(o.material)[0], g = m.defines && 'DESERT_GROUND' in m.defines;
    if (m.alphaTest > 0 && (m.map || m.alphaMap)) {          // leaf cards and grating cast their cut-out shadow, not a square
      const d = revHook(new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: m.map, alphaMap: m.alphaMap, alphaTest: m.alphaTest }));
      return g ? groundHook(d) : d;
    }
    return g ? DEPTH_G : DEPTH;
  };
  const hide = kind => world && world.traverse(o => { if (o.userData.kind === kind) o.visible = false; });
  const hash = (x, z) => { const v = Math.sin(x * 12.9898 + z * 78.233) * 43758.5453; return v - Math.floor(v); };
  const mtx = (x, z, rot, sc, y = Y0) => new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rot), new THREE.Vector3(sc, sc, sc));
  const near = (x, z, m) => heroPose && Math.hypot(x - heroPose.pos.x, z - heroPose.pos.z) < m * M;
  const ahead = (x, z) => { if (!heroPose) return true; const fx = heroPose.look.x - heroPose.pos.x, fz = heroPose.look.z - heroPose.pos.z, l = Math.hypot(fx, fz) || 1; return ((x - heroPose.pos.x) * fx + (z - heroPose.pos.z) * fz) / l > -8 * M; };
  let assetsApplied = false;
  async function applyAssets() {
    if (!world) return; const w0 = world, done = [];
    const [bb, ja, jb, jc, jd, jal, jbl, jcl, jdl, cra, crb, bua, ra, rb, rc, rd, re, sports, van] = await Promise.all(['billboard', 'joshua_a', 'joshua_b', 'joshua_c', 'joshua_d',
      'joshua_a_lod1', 'joshua_b_lod1', 'joshua_c_lod1', 'joshua_d_lod1', 'creosote_a', 'creosote_b', 'bursage_a', 'rock_a', 'rock_b', 'rock_c', 'rock_d', 'rock_e', 'car_sports', 'car_minivan'].map(n => loadGLB(n + '.glb')));
    if (world !== w0) return;
    const prep = o => prepAsset(o, revHook, depthFor);
    if (sports) { TPL.sports = prep(sports); done.push('car_sports'); }
    if (van) { TPL.minivan = prep(van); done.push('car_minivan'); }
    if (bb) { const b = prep(bb.clone(true)); b.scale.setScalar(M); b.position.set(C.x, Y0, C.z); b.userData.kind = 'asset'; hide('billboard'); world.add(b); done.push('billboard'); }
    // Joshua trees: the hero mesh close to the camera, the light one far away, instanced per variant
    const heroT = [ja, jb, jc, jd].filter(Boolean).map(prep), lodT = [jal, jbl, jcl, jdl].map((l, i) => l ? prep(l) : null);
    if (heroT.length) {
      const sets = heroT.map(() => ({ hi: [], lo: [] }));
      placed.tree.forEach((t, k) => { const h = hash(t.x, t.z), v = t.row ? (heroT.length > 2 ? 1 + (k % 2) : heroT.length - 1) % heroT.length : Math.floor(h * heroT.length);
        const sc = M * (0.85 + hash(t.z, t.x) * 0.3) * (t.big ? 1.15 : 1), m = mtx(t.x, t.z, t.rot, sc);
        (near(t.x, t.z, 45) || !lodT[v] ? sets[v].hi : sets[v].lo).push(m); });
      hide('tree'); const g = new THREE.Group(); g.userData.kind = 'asset';
      sets.forEach((st, v) => { if (st.hi.length) g.add(instance(heroT[v], st.hi)); if (st.lo.length) g.add(instance(lodT[v], st.lo)); });
      world.add(g); done.push('joshua');
    }
    // shrubs and rocks near the camera become assets; the far ones stay light
    const shrubs = [cra, crb, bua].filter(Boolean).map(prep);
    if (shrubs.length) {
      const sets = shrubs.map(() => []), dummy = new THREE.Matrix4().makeScale(0, 0, 0);
      placed.bush.forEach(b => { if (b.sight && near(b.x, b.z, 70)) { b.im.setMatrixAt(b.i, dummy); b.im.instanceMatrix.needsUpdate = true; return; }   // the low blockout lumps in the sightline go; bare sand reads truer
        if (!near(b.x, b.z, 70) || !ahead(b.x, b.z)) return; const v = Math.floor(hash(b.x, b.z) * shrubs.length);
        sets[v].push(mtx(b.x, b.z, b.rot, M * (0.55 + b.s * 1.4))); b.im.setMatrixAt(b.i, dummy); b.im.instanceMatrix.needsUpdate = true; });
      const g = new THREE.Group(); g.userData.kind = 'asset'; sets.forEach((st, v) => st.length && g.add(instance(shrubs[v], st))); world.add(g); done.push('shrubs');
    }
    const rocks = [ra, rb, rc, rd, re].filter(Boolean).map(prep);
    if (rocks.length) {
      const sz = rocks.map(r => { const b = new THREE.Box3().setFromObject(r), s3 = b.getSize(new THREE.Vector3()); return Math.max(s3.x, s3.z) || 1; });
      const order = sz.map((s2, i) => i).sort((a, b) => sz[a] - sz[b]), sets = rocks.map(() => []), dummy = new THREE.Matrix4().makeScale(0, 0, 0);
      placed.rock.forEach(r => { if (!near(r.x, r.z, 80)) return; const want = r.s * 2.2, v = order[Math.min(order.length - 1, Math.floor(Math.min(1, want / 2.5) * order.length))];
        sets[v].push(mtx(r.x, r.z, r.rot, M * want / sz[v]));
        if (r.mesh) r.mesh.visible = false; else { r.im.setMatrixAt(r.i, dummy); r.im.instanceMatrix.needsUpdate = true; } });
      const g = new THREE.Group(); g.userData.kind = 'asset'; sets.forEach((st, v) => st.length && g.add(instance(rocks[v], st))); world.add(g); done.push('rocks');
    }
    await applySurfaces(done);
    if (done.length) bakeEnv();
    tuneLight();
    window.__desertAssets = done; return done;
  }
  // road and ground textures from the set thread (desert/tex), mapped in metres
  async function applySurfaces(done) {
    const R = road && road.group.userData.roles;
    const [aA, aN, aR, lA, lY, lW, lN, sA, sN, gA, gN, gR, gM] = await Promise.all([
      loadTex('asphalt_albedo.jpg', { srgb: true }), loadTex('asphalt_normal_w.jpg'), loadTex('asphalt_rough.jpg'),
      loadTex('lines_alpha.png'), loadTex('lines_yellow_albedo.jpg', { srgb: true }), loadTex('lines_white_albedo.jpg', { srgb: true }), loadTex('lines_normal.jpg'),
      loadTex('shoulder_albedo.jpg', { srgb: true }), loadTex('shoulder_normal.jpg'),
      loadTex('sand_albedo.jpg', { srgb: true }), loadTex('sand_normal.jpg'), loadTex('sand_rough.jpg'), loadTex('sand_macro.jpg', { srgb: true })]);
    const rep = (t, a, b) => { if (t) { t.repeat.set(a, b); t.needsUpdate = true; } return t; };
    if (R && aA) { const m = R.asphalt.material, u = R.asphalt.userData.w / (4 * M), v = R.asphalt.userData.len / (4 * M);
      Object.assign(m, { map: rep(aA, u, v), normalMap: rep(aN, u, v), roughnessMap: rep(aR, u, v), roughness: 1, color: new THREE.Color(0xffffff), flatShading: false });
      // road-scale wear from the set thread: R albedo ×2R, G tar-sealant (glossier), across the full width, 80 m along
      const mac = await loadTex('asphalt_macro_rgb.jpg', { aniso: 4 });
      if (mac) { const prev = m.onBeforeCompile, ku = new THREE.Vector2(1 / u, R.asphalt.userData.len / (80 * M) / v);
        m.onBeforeCompile = (sh, r) => { prev && prev.call(m, sh, r); sh.uniforms.tMacro = { value: mac }; sh.uniforms.uMacK = { value: ku };
          sh.fragmentShader = 'uniform sampler2D tMacro; uniform vec2 uMacK;\n' + sh.fragmentShader
            .replace('#include <map_fragment>', '#include <map_fragment>\n vec4 macS = texture2D(tMacro, vec2(clamp(vMapUv.x * uMacK.x, 0.0, 1.0), vMapUv.y * uMacK.y)); diffuseColor.rgb *= 2.0 * macS.r;')
            .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n roughnessFactor = mix(roughnessFactor, 0.42, macS.g);'); };
        const pk = m.customProgramCacheKey ? m.customProgramCacheKey.bind(m) : () => ''; m.customProgramCacheKey = () => pk() + '|macro'; }
      m.needsUpdate = true; done.push('asphalt'); }
    if (R && lA) for (const [list, alb] of [[R.yellow, lY], [R.white, lW]]) for (const [li, ms] of list.entries()) { const v = ms.userData.len / (8 * M), m = ms.material, off = li * 0.37;   // the two yellows wear differently
      const ofs = t => { if (t) t.offset.y = off; return t; };
      Object.assign(m, { map: ofs(rep(alb && alb.clone(), 1, v)), alphaMap: ofs(rep(lA.clone(), 1, v)), normalMap: ofs(rep(lN && lN.clone(), 1, v)), alphaTest: 0.5, color: new THREE.Color(0xffffff), roughness: 0.75, flatShading: false }); m.needsUpdate = true; }
    if (R && sA) { const m = R.shoulder.material, u = R.shoulder.userData.w / (1.5 * M), v = R.shoulder.userData.len / (3 * M);
      Object.assign(m, { map: rep(sA, u, v), normalMap: rep(sN, u, v), color: new THREE.Color(0xffffff), flatShading: false }); m.needsUpdate = true; }
    if (groundMesh && gA) {
      const m = groundMesh.material, k = 160000 / (6 * M);
      Object.assign(m, { map: rep(gA, k, k), normalMap: rep(gN, k, k), roughnessMap: rep(gR, k, k), roughness: 1, flatShading: false, vertexColors: !!gM, color: new THREE.Color(1.0, 0.9, 0.78) }); m.needsUpdate = true;   // warmed a touch: the late sun has been on this sand all day
      if (gM && gM.image) {          // large-scale tone from the macro map, baked into the ground's vertex colours
        const cv = document.createElement('canvas'), W2 = cv.width = gM.image.width, H2 = cv.height = gM.image.height, cx = cv.getContext('2d'); cx.drawImage(gM.image, 0, 0);
        const px = cx.getImageData(0, 0, W2, H2).data, g = groundMesh.geometry, pos = g.attributes.position, col = g.attributes.color, span = 300 * M;
        let mean = 0; for (let i = 0; i < px.length; i += 4) mean += px[i] + px[i + 1] + px[i + 2]; mean /= (px.length / 4) * 3;
        for (let i = 0; i < pos.count; i++) { const u = ((pos.getX(i) / span) % 1 + 1) % 1, v = ((pos.getZ(i) / span) % 1 + 1) % 1, j = ((Math.floor(v * H2) * W2) + Math.floor(u * W2)) * 4;
          const f = c => Math.min(1.6, Math.max(0.5, px[j + c] / mean)); col.setXYZ(i, f(0), f(1), f(2)); }
        col.needsUpdate = true;
      } else if (gM === null) { const col = groundMesh.geometry.attributes.color; for (let i = 0; i < col.count; i++) col.setXYZ(i, 1, 1, 1); col.needsUpdate = true; }
      done.push('sand');
    }
  }
  // golden hour: the low warm sun does the work; the sky's blue fill stays weak except in reflections (paint, glass, chrome)
  function tuneLight() {
    const T = window.__desertTune || {};
    if (sunLight) sunLight.intensity = T.sun ?? 4.2;
    if (hemiLight) hemiLight.intensity = T.hemi ?? 0.18;
    const strong = /^(paint|glass|chrome|rim|trim)/i;
    world && world.traverse(o => { if (!o.isMesh) return; for (const m of [].concat(o.material)) if (m && 'envMapIntensity' in m) m.envMapIntensity = strong.test(m.name || '') ? (m.envMapIntensity || 1) : (T.env ?? 0.32); });
    for (const k in TPL) TPL[k].traverse(o => { if (o.isMesh) for (const m of [].concat(o.material)) if (m && 'envMapIntensity' in m && !strong.test(m.name || '')) m.envMapIntensity = T.env ?? 0.32; });
    renderer.toneMappingExposure = T.exp ?? 1.0;
  }
  // image-based light and reflections from a physically based sky matched to the sun
  function bakeEnv() {
    if (!heroPose || window.__noEnv || envTex) return;
    envTex = skyEnvironment(renderer, new THREE.Vector3(...(Lcur || LOOKS.golden).sun).normalize());
    scene.environment = envTex;
    if (hemiLight) hemiLight.intensity = (Lcur ? Lcur.hemi : 1) * 0.35;     // the environment carries most of the fill now
  }

  // ---------- the approach: slower curved flight from wherever the camera is into the hero frame, building the world as it comes ----------
  let heroPose = null, fly = null, lastFly = null, mode = 0, aux = null, inside = false;
  const ease = t => t * t * t * (t * (t * 6 - 15) + 10);
  const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
  function setReveal(p) {
    const R = p >= 1 ? 1e7 : 300 * Math.pow(320, p);              // out from the billboard's foot to the horizon, exactly at landing
    REV.uRev.value = p; REV.uMode.value = mode; REV.uR.value = R;
    if (skyMat) skyMat.uniforms.uSkyRev.value = mode === 2 ? 1 : smooth(0.8, 1, p);
    gridDes(p >= 1 || p <= 0 ? -1 : R, mode === 0 ? 150 : mode === 1 ? 45 : 0, mode === 2 ? 1 : 0.8, REV.uOrigin.value);
    const gf = smooth(0.92, 1, p); gridFade(gf);
    if (!aux) aux = scene.children.filter(o => o.material && o.material.transparent && !o.material.isShaderMaterial && o.visible).map(o => ({ o, a: o.material.opacity }));
    for (const x of aux) x.o.material.opacity = x.a * (1 - gf);
    for (const k in cssCards) if (k !== heroId) { const e = cssCards[k].obj.element; e.style.transition = 'none'; e.style.opacity = String(1 - smooth(0, 0.45, p)); }
  }
  const bloomAt = t => Math.pow(Math.min(1, Math.max(0, (t - 0.03) / 0.97)), 1.15);
  function pose(t) {
    const e = ease(t), [P0, P1, P2, P3] = fly.P, u = 1 - e;
    const pos = P0.clone().multiplyScalar(u * u * u).addScaledVector(P1, 3 * u * u * e).addScaledVector(P2, 3 * u * e * e).addScaledVector(P3, e * e * e);
    const look = fly.L0.clone().lerp(fly.L1, ease(Math.min(1, t / 0.92)));
    return { pos, look, fov: fly.f0 + (fly.f1 - fly.f0) * e };
  }
  function finishLeave() { fly = null; root.visible = false; gridFade(0); gridDes(-1, 0, 0, REV.uOrigin.value); if (fogBefore !== null) { scene.fog = fogBefore; fogBefore = null; } for (const x of aux || []) x.o.material.opacity = x.a; for (const k in cssCards) cssCards[k].obj.element.style.opacity = ''; }
  const api = {
    root, Y0, W, H, C, LOOKS, clock,
    enter(key, roadDef, carDefs, eye, view) {
      for (const o of scene.children) if (o !== root && o.visible) { hidden.push(o); o.visible = false; }
      for (const k in cssCards) if (k !== heroId) cssCards[k].obj.element.style.opacity = '0';
      root.visible = true; REV.uRev.value = 1;
      useHaze();
      setupRenderer(renderer);
      camera.far = 200000; camera.near = 10; camera.updateProjectionMatrix();
      build(key, roadDef, carDefs, eye, view); viewInfo = view;
      if (!heroPose) heroPose = { pos: eye ? eye.clone() : C.clone(), look: C.clone(), fov: 38 };
      api.assets = applyAssets();
    },
    // aim a camera: standing h metres above ground, at horizontal angle theta (deg, + = to the card's left) from the card's facing,
    // with the card centre landing at screen point (ux, uy) in -1..1 and spanning `fw` of the frame width
    frame({ theta, h, fov, ux, uy, fw, fh = 2, aspect }) {
      const c = new THREE.PerspectiveCamera(fov, aspect, 10, 200000), th = theta * Math.PI / 180;
      const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, b]) => new THREE.Vector3(C.x + a * W / 2, C.y + b * H / 2, C.z));
      const place = D => { c.position.set(C.x - Math.sin(th) * D, Y0 + h * M, C.z + Math.cos(th) * D); c.up.set(0, 1, 0); c.lookAt(C);
        for (let it = 0; it < 30; it++) { c.updateMatrixWorld(); const p = C.clone().project(c);
          const tx = Math.atan(p.x * Math.tan(fov * Math.PI / 360) * aspect) - Math.atan(ux * Math.tan(fov * Math.PI / 360) * aspect);
          const ty = Math.atan(p.y * Math.tan(fov * Math.PI / 360)) - Math.atan(uy * Math.tan(fov * Math.PI / 360));
          c.rotateOnWorldAxis(new THREE.Vector3(0, 1, 0), -tx); c.rotateX(ty); }
        c.updateMatrixWorld(); const pr = corners.map(v => v.clone().project(c)), xs = pr.map(v => v.x), ys = pr.map(v => v.y);
        return Math.max((Math.max(...xs) - Math.min(...xs)) / 2 / fw, (Math.max(...ys) - Math.min(...ys)) / 2 / fh); };
      let lo = 300, hi = 40000; for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (place(mid) > 1) lo = mid; else hi = mid; } place((lo + hi) / 2);
      const dir = new THREE.Vector3(); c.getWorldDirection(dir);
      return { pos: c.position.clone(), look: c.position.clone().addScaledVector(dir, 2000), dist: (lo + hi) / 2 };
    },
    // the picked shot: frame the camera, lay the road relative to it, build the world
    heroShot(s, aspect = REF_ASPECT) {
      const f = api.frame({ ...s, aspect });
      const to = C.clone().sub(f.pos); to.y = 0; to.normalize();
      const viewAz = Math.atan2(to.x, -to.z) * 180 / Math.PI, left = new THREE.Vector3(to.z, 0, -to.x);
      const P = new THREE.Vector3(f.pos.x, 0, f.pos.z).addScaledVector(to, s.roadAhead * M).addScaledVector(left, (s.roadLeft || 0) * M);
      const fwd = f.look.clone().sub(f.pos); fwd.y = 0; fwd.normalize();
      const view = { eye: f.pos.clone(), fwd, right: new THREE.Vector3(-fwd.z, 0, fwd.x), row: (s.row || 20) * M, tanH: Math.tan(THREE.MathUtils.degToRad(s.fov / 2)) * aspect };
      api.enter(s.look, { P, az: viewAz + s.roadTurn }, s.cars || [], f.pos, view);
      return f;
    },
    // build the heroPose world up front, hidden, so a click can fly straight in
    prepareHero(s, m = 0) {
      mode = m; const aspect = REF_ASPECT, f = api.frame({ ...s, aspect });
      const to = C.clone().sub(f.pos); to.y = 0; to.normalize();
      const viewAz = Math.atan2(to.x, -to.z) * 180 / Math.PI, left = new THREE.Vector3(to.z, 0, -to.x);
      const P = new THREE.Vector3(f.pos.x, 0, f.pos.z).addScaledVector(to, s.roadAhead * M).addScaledVector(left, (s.roadLeft || 0) * M);
      const fwd = f.look.clone().sub(f.pos); fwd.y = 0; fwd.normalize();
      const view = { eye: f.pos.clone(), fwd, right: new THREE.Vector3(-fwd.z, 0, fwd.x), row: (s.row || 20) * M, tanH: Math.tan(THREE.MathUtils.degToRad(s.fov / 2)) * aspect };
      camera.far = 200000; camera.updateProjectionMatrix();
      setupRenderer(renderer);
      for (const o of scene.children) if (o !== root && o.material && !o.material.isShaderMaterial) [].concat(o.material).forEach(x => { x.toneMapped = false; x.needsUpdate = true; });   // the grid's own pieces keep their look
      build(s.look, { P, az: viewAz + s.roadTurn }, [], f.pos, view); viewInfo = view;
      REV.uOrigin.value.set(C.x, 0, C.z - 70); REV.uCam.value.copy(f.pos);
      heroPose = { pos: f.pos, look: f.look, baseFov: s.fov, get fov() { return heroFov(s.fov); } };
      root.visible = false; api.ready = true;
      bakeEnv(); api.assets = applyAssets();
      return heroPose;
    },
    get landedFov() { return heroPose ? heroPose.fov : null; },   // the landing lens for the current window shape
    get flying() { return !!fly && fly.dir > 0; }, get inside() { return inside; },
    approachFrom(pos, look, fov, dur = 6.5) {
      api.stop(); root.visible = true; inside = false; aux = null; useHaze();
      const vd = heroPose.look.clone().sub(heroPose.pos).normalize(), up = new THREE.Vector3(0, 1, 0);
      fly = { dir: 1, t: 0, dur, L0: look.clone(), L1: heroPose.look.clone(), f0: fov, f1: heroPose.fov,
        P: [pos.clone(), pos.clone().lerp(heroPose.pos, 0.35).addScaledVector(up, 500), heroPose.pos.clone().addScaledVector(vd, -900).addScaledVector(up, 380), heroPose.pos.clone()] };
      setReveal(0);
    },
    flyStep(dt) {
      fly.t = Math.min(1, fly.t + dt / fly.dur); const s = pose(fly.t); setReveal(bloomAt(fly.t));
      if (fly.t >= 1) { lastFly = fly; fly = null; inside = true; setReveal(1); api.play(); s.done = true; landedAt = 0; }
      return s;
    },
    // leaving the way we came: the camera pulls back up the approach curve while the world un-builds cell by cell,
    // from the horizon in toward the billboard's foot (the build run backwards), then the page flies on to the next slide
    get leaving() { return !!fly && fly.dir === -2; },
    leave(speed = 6.5 / 4.2) {
      const f = fly && fly.dir > 0 ? fly : lastFly; if (!f) { api.depart(); return false; }
      api.stop(); inside = false; landedAt = -1; fly = Object.assign({}, f, { dir: -2, t: f === fly ? fly.t : 1, speed }); return true;
    },
    leaveStep(dt) {
      fly.t = Math.max(0, fly.t - dt * fly.speed / fly.dur); const s = pose(fly.t); setReveal(bloomAt(fly.t));
      if (fly.t <= 0) { finishLeave(); s.done = true; }
      return s;
    },
    depart(dur = 3.2) { if (!inside && !fly) return; api.stop(); inside = false; landedAt = -1; fly = { dir: -1, t: 0, dur, from: REV.uRev.value }; },
    // the frame: composed (ambient occlusion, bloom, grain) once landed, plain otherwise. Returns false to let the page render itself.
    render(dt) {
      if (!root.visible || window.__desertNoPost) return false;
      const leaving = fly && fly.dir < 0;
      if (!inside && !(leaving && REV.uRev.value > 0.965)) return false;
      if (!composer) composer = makeComposer(renderer, scene, camera);
      let k;
      if (inside) { landedAt += dt; k = Math.min(1, landedAt / 1.2); }
      else k = Math.min(1, (REV.uRev.value - 0.965) / 0.035);          // fades out over the first moments of the un-build
      composer.render(dt, k * k * (3 - 2 * k)); return true;
    },
    bakeEnv() { bakeEnv(); }, applyAssets() { return applyAssets(); },
    // QA: jump straight to the landed state
    get debug() { return { sunLight, hemiLight, envTex, scene, renderer, camera, actors, clock, road, Y0, lastCar: window.__lastCar }; },
    landNow() { api.approachFrom(camera.position.clone(), camera.position.clone().add(new THREE.Vector3(0, 0, -1)), camera.fov); fly.t = 1; const s2 = pose(1); fly = null; inside = true; setReveal(1); landedAt = 5; return s2; },
    // storyboards: pose and build state at time t of the approach from the current camera
    storyFrom(pos, look, fov) { api.approachFrom(pos, look, fov); fly.dir = 0; },
    storyAt(t) { const s = pose(t); setReveal(bloomAt(t)); return s; },
    setMode(m) { mode = m; },
    stop() { for (const a of actors) a.dispose(); actors.length = 0; clock.playing = false; if (skyMat) skyMat.uniforms.uStar.value = 0; },
    play() { for (const a of actors) a.dispose(); actors.length = 0; clock.t = 0; evI = 0; trafficN = 0; nextCar = 26; clock.playing = true; },
    tick(dt) {
      BLOOM.uBTime.value += dt;
      if (fly && fly.dir === -1) { fly.t = Math.min(1, fly.t + dt / fly.dur); setReveal(fly.from * (1 - smooth(0, 1, fly.t)));
        if (fly.t >= 1) finishLeave(); }
      if (!clock.manual) update(dt);
    },
    step(dt) { update(dt); },
  };
  return api;
}

// The desert, the billboard and the landing camera are fixed in the world, composed once at 16:9 (the approved golden-hour
// frame). A window of another shape only changes the lens: wider screens keep the height and see more desert at the sides;
// narrower ones widen the lens until the same width of the scene fits, and see more sky and ground. Nothing else moves.
export const REF_ASPECT = 16 / 9;
export const BILLBOARD_FACE = { w: 1180, h: 462 };   // the intro slide in px; desert/assets/billboard.glb is built around it (10.93 x 4.28 m)
export function heroFov(baseFov, aspect = innerWidth / innerHeight) {
  if (aspect >= REF_ASPECT) return baseFov;
  return THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(baseFov / 2)) * REF_ASPECT / aspect));
}
// Josiah 10-21: picked framing A + Golden hour, tightened so the slide reads (render I1). Board lowered to 2.8 m clearance,
// road moved 8 m out from the camera so the double yellow stays in the bottom-left corner.
export const HERO_SHOT = { look: 'golden', clear: 2.8, theta: 22, h: 1.1, fov: 38, ux: 0.28, uy: 0.24, fw: 0.56, roadAhead: 8, roadTurn: -64, row: 20 };
