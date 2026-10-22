// Desert billboard world — framing blockout (audition sketch, not the detailed build).
// Everything is built around the hero card where it already sits; the card never moves, only the camera does.
// Units: the site's world units (1 unit ≈ 1 CSS px at the card plane). The card is ~4.3 m tall, so ~108 units per metre.
import * as THREE from 'three';

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

export function makeDesert({ scene, cssCards, heroId = 'hero', camera, renderer, clear }) {
  const hero = cssCards[heroId], C = hero.obj.position.clone();
  const W = hero.el.offsetWidth, H = hero.el.offsetHeight;
  const bottom = C.y - H / 2, clearance = (clear || window.__clear || 3.8) * M, Y0 = bottom - clearance;     // ground sits ~3.8 m under the face
  const root = new THREE.Group(); root.name = 'desert';
  let world = null, lookKey = 'mojave', road = null, cars = [], skyMat = null, trees = [], viewInfo = null;
  const hidden = [];

  const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 1, metalness: 0, flatShading: true, ...o });

  // ---------- sky dome ----------
  function sky(L) {
    const s = new THREE.Vector3(...L.sun).normalize();
    skyMat = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { zen: { value: new THREE.Color(L.zenith) }, hor: { value: new THREE.Color(L.horizon) }, haze: { value: new THREE.Color(L.haze) }, sun: { value: s }, sunCol: { value: new THREE.Color(L.sunCol) },
        uT: { value: 0 }, uStar: { value: 0 } },
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: `uniform vec3 zen, hor, haze, sun, sunCol; uniform float uT, uStar; varying vec3 vD;
        float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
        void main(){
          vec3 d = normalize(vD); float h = clamp(d.y, 0.0, 1.0);
          vec3 c = mix(hor, zen, pow(h, 0.45));
          c = mix(c, haze, (1.0 - smoothstep(0.0, 0.09, h)) * 0.55);              // soft haze band sitting on the horizon
          float g = max(dot(d, sun), 0.0); c += sunCol * (pow(g, 600.0) * 1.2 + pow(g, 8.0) * 0.12);
          // stars: sparse half-degree cells, a few lit, each twinkling at its own rate; they fade in with uStar
          vec2 uv = vec2(atan(d.z, d.x), asin(clamp(d.y, -1.0, 1.0))) * 114.6; vec2 cell = floor(uv); float hs = hash(cell);
          if (hs > 0.9925 && uStar > 0.0) {
            vec2 o = vec2(hash(cell + 3.1), hash(cell + 7.7)) * 0.6 + 0.2; float r = length(fract(uv) - o);
            float b = 0.4 + 0.6 * hash(cell + 11.3) * hash(cell + 2.9);
            float tw = 0.6 + 0.4 * sin(uT * (1.1 + 2.6 * hash(cell + 5.2)) + hs * 60.0);
            float st = smoothstep(0.17, 0.0, r) * b * tw * smoothstep(0.12, 0.5, d.y) * (1.0 - min(1.0, pow(g, 3.0) * 3.0));
            c += vec3(1.0, 0.96, 0.9) * st * uStar * 1.1;
          }
          gl_FragColor = vec4(c, 1.0); }` });
    const d = new THREE.Mesh(new THREE.SphereGeometry(95000, 64, 32), skyMat); d.position.set(C.x, Y0, C.z); d.renderOrder = -10; d.frustumCulled = false; return d;
  }

  // ---------- haze: exponential, thicker near the ground, warmer toward the sun ----------
  // Replaces three's exp2 fog path for this scene, so the board stays clear and each band of desert behind it fades a step further
  const HAZE_H = 30 * M, HAZE_DENSITY = 2.0e-5;
  function installHaze(L) {
    const S = THREE.ShaderChunk, sd = new THREE.Vector3(...L.sun).normalize(), sc = new THREE.Color(L.sunCol), f = v => v.toFixed(6);
    S.fog_pars_vertex = '#ifdef USE_FOG\n varying float vFogDepth;\n #ifdef FOG_EXP2\n  varying vec3 vFogWP;\n #endif\n#endif';
    S.fog_vertex = '#ifdef USE_FOG\n vFogDepth = - mvPosition.z;\n #ifdef FOG_EXP2\n  vec4 fogWP = vec4( transformed, 1.0 );\n  #ifdef USE_INSTANCING\n   fogWP = instanceMatrix * fogWP;\n  #endif\n  vFogWP = ( modelMatrix * fogWP ).xyz;\n #endif\n#endif';
    S.fog_pars_fragment = '#ifdef USE_FOG\n uniform vec3 fogColor;\n varying float vFogDepth;\n #ifdef FOG_EXP2\n  uniform float fogDensity;\n  varying vec3 vFogWP;\n #else\n  uniform float fogNear;\n  uniform float fogFar;\n #endif\n#endif';
    S.fog_fragment = `#ifdef USE_FOG
 #ifdef FOG_EXP2
  float fogH = exp( - max( vFogWP.y - (${f(Y0)}), 0.0 ) / ${f(HAZE_H)} );
  float fogFactor = 1.0 - exp( - fogDensity * vFogDepth * ( 0.45 + 0.55 * fogH ) );
  float fogSun = pow( max( dot( normalize( vFogWP - cameraPosition ), vec3( ${f(sd.x)}, ${f(sd.y)}, ${f(sd.z)} ) ), 0.0 ), 4.0 );
  vec3 fogC = mix( fogColor, vec3( ${f(sc.r)}, ${f(sc.g)}, ${f(sc.b)} ), fogSun * 0.5 );
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogC, fogFactor );
 #else
  float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor );
 #endif
#endif`;
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
    const m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true }));
    m.position.set(C.x, Y0, C.z); m.receiveShadow = true; return m;
  }
  function range(L, R, hMin, hMax, color, seed, mesa) {
    // a sloped band of ridges: base at R, crest set back, so the sun models the slopes instead of a flat wall
    const r = rng(seed), N = 420, rows = 4, pos = [], idx = [], ph = r() * 9, ph2 = r() * 9;
    const crest = [];
    for (let i = 0; i <= N; i++) { const a = i / N * Math.PI * 2;
      let y = 0.5 + 0.28 * Math.sin(a * 4 + ph) + 0.16 * Math.sin(a * 11 + ph2) + 0.08 * Math.sin(a * 29 + ph * 3) + 0.05 * (r() - .5);
      y = hMin + (hMax - hMin) * Math.max(0, Math.min(1, y));
      if (mesa) y = Math.sin(a * 6 + ph) > 0.3 ? hMax * (0.8 + 0.08 * Math.sin(a * 40)) : hMin * 0.3;
      crest.push(y); }
    for (let i = 0; i <= N; i++) { const a = i / N * Math.PI * 2, cx = Math.cos(a), sz = Math.sin(a);
      for (let j = 0; j < rows; j++) { const t = j / (rows - 1), rr = R + t * R * 0.12;
        let y = mesa ? (t < 0.34 ? -200 + (crest[i] + 200) * (t / 0.34) * 0.98 : crest[i]) : -200 + (crest[i] + 200) * Math.pow(Math.sin(t * Math.PI / 2), 1.4);
        y += (j > 0 && j < rows - 1 && !mesa) ? (r() - .5) * (hMax - hMin) * 0.12 : 0;
        pos.push(cx * rr, y, sz * rr); }
      if (i < N) for (let j = 0; j < rows - 1; j++) { const k = i * rows + j, k2 = (i + 1) * rows + j; idx.push(k, k + 1, k2, k2, k + 1, k2 + 1); } }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
    const m = new THREE.Mesh(g.toNonIndexed(), mat(color, { side: THREE.DoubleSide })); m.geometry.computeVertexNormals(); m.position.set(C.x, Y0, C.z); return m;
  }

  // ---------- road ----------
  function makeRoad(L, P, az) {      // P: a point on the centre line (world x,z); az: heading in degrees (0 = -z, 90 = +x)
    const dir = new THREE.Vector3(Math.sin(az * Math.PI / 180), 0, -Math.cos(az * Math.PI / 180)), n = new THREE.Vector3(-dir.z, 0, dir.x);
    const lane = 3.7 * M, shoulderW = 1.4 * M, len = 140000;
    const g = new THREE.Group();
    const strip = (w, off, color, y, dash) => {
      if (!dash) { const m = new THREE.Mesh(new THREE.PlaneGeometry(w, len), mat(color, { polygonOffset: true, polygonOffsetFactor: -y, polygonOffsetUnits: -y }));
        m.rotation.x = -Math.PI / 2; m.rotation.z = -Math.atan2(dir.x, -dir.z); m.position.set(P.x + n.x * off, Y0 + y, P.z + n.z * off); m.receiveShadow = true; g.add(m); return; }
    };
    strip(2 * lane + 2 * shoulderW + 1.2 * M, 0, L.shoulder, 0.6);      // gravel shoulder band
    strip(2 * lane + 2 * shoulderW, 0, L.asphalt, 1.2);                 // asphalt
    strip(0.12 * M, -0.12 * M, 0xe8b532, 1.8); strip(0.12 * M, 0.12 * M, 0xe8b532, 1.8);   // double yellow
    strip(0.15 * M, lane + 0.1 * M, 0xeeeeea, 1.8); strip(0.15 * M, -lane - 0.1 * M, 0xeeeeea, 1.8);  // fog lines
    road = { P: P.clone(), dir, n, lane, halfW: lane + shoulderW + 0.6 * M,
      dist(x, z) { const dx = x - P.x, dz = z - P.z; return Math.abs(dx * n.x + dz * n.z); },
      at(s, laneSide) { return new THREE.Vector3(P.x + dir.x * s + n.x * laneSide * lane * 0.5, Y0, P.z + dir.z * s + n.z * laneSide * lane * 0.5); } };
    return g;
  }

  // ---------- billboard structure (behind and below the card; nothing crosses in front of the face) ----------
  function billboard(L) {
    const g = new THREE.Group(), dark = mat(L.frame), steel = mat(0x6d7178), galv = mat(0x8e9298);
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
    const ok = (x, z, clear, kind) => (!road || road.dist(x, z) > road.halfW + clear) && Math.hypot(x - C.x, z - (C.z - 70)) > 2.2 * M && (!eye || Math.hypot(x - eye.x, z - eye.z) > clear * 6 + 4 * M) && (kind === 'bush' || !inStrip(x, z));
    const place = (n, rMin, rMax, clear, fn, kind) => { let k = 0, tries = 0; while (k < n && tries++ < n * 30) {
      const a = r() * Math.PI * 2, d = rMin + Math.pow(r(), 1.6) * (rMax - rMin), x = C.x + Math.cos(a) * d, z = C.z + Math.sin(a) * d;
      if (!ok(x, z, clear, kind)) continue; fn(x, z, d); k++; } };
    // bushes (instanced)
    const bushGeo = new THREE.IcosahedronGeometry(1, 1), bushCount = 1400;
    L.bush.forEach((c, bi) => {
      const im = new THREE.InstancedMesh(bushGeo, mat(c), bushCount / 3 | 0), d = new THREE.Object3D(); let i = 0;
      place(bushCount / 3 | 0, 300, 26000, 0.8 * M, (x, z, dd) => { const s = (0.2 + Math.pow(r(), 2) * 0.45) * M * (dd > 8000 ? 1.5 : 1) * (inStrip(x, z) ? 0.55 : 1); d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r() * .6), s * 0.55, s * (1 + r() * .6)); d.rotation.y = r() * 6; d.updateMatrix(); im.setMatrixAt(i++, d.matrix); }, 'bush');
      im.count = i; im.castShadow = true; im.receiveShadow = true; g.add(im);
    });
    // rocks
    const rockGeo = new THREE.DodecahedronGeometry(1, 0), rk = new THREE.InstancedMesh(rockGeo, mat(L.rock), 260), d = new THREE.Object3D(); let ri = 0;
    place(260, 400, 18000, 0.5 * M, (x, z) => { const s = (0.12 + Math.pow(r(), 4) * 1.0) * M; d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r()), s * (0.5 + r() * 0.5), s * (1 + r())); d.rotation.set(r(), r() * 6, r()); d.updateMatrix(); rk.setMatrixAt(ri++, d.matrix); });
    rk.count = ri; rk.castShadow = rk.receiveShadow = true; g.add(rk);
    // a few boulder piles near the billboard
    for (let k = 0; k < 2; k++) { const bx = C.x + (k - 1) * 9 * M + (r() - .5) * 4 * M, bz = C.z - (3 + r() * 9) * M; if (!ok(bx, bz, M) || inStrip(bx, bz)) continue;
      for (let j = 0; j < 4; j++) { const s = (0.4 + r() * 0.7) * M, b = new THREE.Mesh(rockGeo, mat(L.rock)); b.position.set(bx + (r() - .5) * 2 * M, Y0 + s * .3, bz + (r() - .5) * 2 * M); b.scale.set(s * 1.3, s * .8, s); b.rotation.set(r(), r() * 6, r()); b.castShadow = b.receiveShadow = true; g.add(b); } }
    // trees
    const tree = L.tree === 'joshua' ? joshua : saguaro;
    place(L.tree === 'joshua' ? 70 : 55, 1800, 24000, 1.5 * M, (x, z, dd) => { const t = tree(L, r, dd > 9000 ? 1.25 : 1); t.position.set(x, Y0, z); t.rotation.y = r() * 6; g.add(t); trees.push(new THREE.Vector3(x, Y0, z)); });
    if (view && L.tree === 'joshua') {
      const half = view.row * view.tanH, poleL = dl(C.x, C.z - 70).l;
      for (const u of [-0.92, -0.55, -0.12, 0.38, 0.8]) { let lat = u * half + (r() - .5) * 1.5 * M; if (Math.abs(lat - poleL) < 3 * M) lat += 3.5 * M * Math.sign(lat - poleL || 1);
        const dd = view.row + (r() - .5) * 1.6 * M, x = view.eye.x + view.fwd.x * dd + view.right.x * lat, z = view.eye.z + view.fwd.z * dd + view.right.z * lat;
        if (road && road.dist(x, z) < road.halfW + M) continue;
        const t = joshua(L, r, 1.1); t.position.set(x, Y0, z); t.rotation.y = r() * 6; g.add(t); trees.push(new THREE.Vector3(x, Y0, z)); }
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
    const lamp = (c, z, y, w, e) => { const b = new THREE.Mesh(new THREE.BoxGeometry(w * M, 0.08 * M, 0.06 * M), new THREE.MeshStandardMaterial({ color: c, emissive: c, emissiveIntensity: e, roughness: .5 }));
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
    const r = rng(seed), pos = [], nrm = [], tmp = new THREE.Object3D(), up = new THREE.Vector3(0, 1, 0);
    const add = (a, b, rad) => { const d = b.clone().sub(a), l = d.length();
      const cg = new THREE.CylinderGeometry(rad, rad * 0.8, l, 3, 1, false).toNonIndexed();
      tmp.position.copy(a).add(b).multiplyScalar(0.5); tmp.quaternion.setFromUnitVectors(up, d.normalize()); tmp.scale.set(1, 1, 1); tmp.updateMatrix();
      cg.applyMatrix4(tmp.matrix); pos.push(...cg.attributes.position.array); nrm.push(...cg.attributes.normal.array); };
    const rnd = () => new THREE.Vector3(r() * 2 - 1, r() * 2 - 1, r() * 2 - 1).normalize();
    for (let i = 0; i < 170; i++) { const p = rnd().multiplyScalar(radius * (0.72 + r() * 0.28)), t = rnd().cross(p).normalize(), l = radius * (0.35 + r() * 0.6);
      add(p.clone().addScaledVector(t, -l / 2), p.clone().addScaledVector(t, l / 2).addScaledVector(p, -0.1 * r()), 0.9 + r() * 0.8); }
    for (let i = 0; i < 26; i++) { const a = rnd().multiplyScalar(radius * 0.25), b = rnd().multiplyScalar(radius * 0.9); add(a, b, 1.2); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
    const m = new THREE.Mesh(g, mat(0xb39466, { flatShading: false })); m.scale.y = 0.86; m.castShadow = true;
    const holder = new THREE.Group(); holder.add(m); return holder;
  }

  // ---------- foreground layer: vehicles pass in front of the slide, which is HTML on top of the main canvas ----------
  let fg = null; const SHADOW_ONLY = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false });
  function foreground() {
    if (fg) return fg;
    const cv = document.createElement('canvas'); cv.id = 'desert-fg'; cv.setAttribute('aria-hidden', 'true');
    Object.assign(cv.style, { position: 'fixed', inset: '0', width: '100%', height: '100%', pointerEvents: 'none' });
    (document.getElementById('css') || document.body).after(cv);
    const r = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: true }); r.setPixelRatio(renderer.getPixelRatio()); r.setClearColor(0x000000, 0);
    fg = { cv, r, sc: new THREE.Scene(), live: 0, size() { r.setSize(innerWidth, innerHeight, false); } }; fg.size(); addEventListener('resize', fg.size);
    return fg;
  }
  function fgLights(L, sun) {
    const F = foreground(); F.sc.clear();
    const s2 = new THREE.DirectionalLight(L.sunCol, L.sunI); s2.position.copy(sun.position); s2.target.position.copy(sun.target.position);
    F.sc.add(s2, s2.target, new THREE.HemisphereLight(L.zenith, L.sand[0], L.hemi)); F.sc.fog = new THREE.FogExp2(L.haze, HAZE_DENSITY);
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
    v.rotation.y = Math.atan2(heading.x, heading.z); const F = foreground(); F.sc.add(v); F.live++;
    const twin = v.clone(true); twin.traverse(o => { if (o.isMesh) { o.material = SHADOW_ONLY; o.castShadow = true; } }); world.add(twin);
    let sv = s0;
    actors.push({ update(dt) { sv += dirSign * speed * M * dt; v.position.copy(road.at(sv, side)).setY(Y0 + 2); twin.position.copy(v.position);
      for (const w of v.userData.spin) w.rotation.x += speed * M * dt / v.userData.wheelR;
      return dirSign > 0 ? sv > s1 + 40 * M : sv < s1; }, dispose() { F.sc.remove(v); world.remove(twin); F.live--; } });
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
    const len = a.distanceTo(b), dur = seconds * 1.12, rad = 0.5 * M, tw = tumbleweed(rad, 31); world.add(tw);
    const r = rng(77), hops = []; { let t = 0; while (t < dur + 1) { const d = 0.45 + r() * 0.45; hops.push({ t, d, h: (0.2 + r() * 0.6) * M }); t += d; } }
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
  const EVENTS = [
    { at: 2, fn: () => laneRun(() => sportsCar(0xc8102e), -1, -1, 30) },
    { at: 10, fn: () => laneRun(() => minivan(0x1f4f96), 1, 1, 24) },
    { at: 13, fn: () => tumbleRun(8) },
  ];
  function update(dt) {
    if (!clock.playing) return;
    clock.t += dt;
    while (evI < EVENTS.length && clock.t >= EVENTS[evI].at) EVENTS[evI++].fn();
    if (clock.t >= nextCar) { const sw = trafficN++ % 2 === 0, cols = [0xe9e6df, 0x8d9299, 0x23262b, 0x6b7f8e];
      laneRun(() => (r => r > 0.5 ? sportsCar : minivan)(Math.random())(cols[trafficN % cols.length]), sw ? -1 : 1, sw ? -1 : 1, 22 + Math.random() * 8);
      nextCar = clock.t + 14 + Math.random() * 10; }
    for (let i = actors.length - 1; i >= 0; i--) if (actors[i].update(dt)) { actors[i].dispose(); actors.splice(i, 1); }
    if (fg) { if (fg.live > 0) { camera.updateMatrixWorld(); fg.r.render(fg.sc, camera); fg.drawn = true; } else if (fg.drawn) { fg.r.clear(); fg.drawn = false; } }
    if (skyMat) { skyMat.uniforms.uT.value = clock.t; const k = Math.min(1, Math.max(0, (clock.t - 1) / 19)); skyMat.uniforms.uStar.value = (Lcur?.stars || 0) * k * k * (3 - 2 * k); }
  }

  // ---------- assemble ----------
  function build(key, roadDef, carDefs = [], eye = null, view = null) {
    if (world) { root.remove(world); world.traverse(o => { o.geometry?.dispose?.(); }); }
    lookKey = key; const L = LOOKS[key]; Lcur = L; world = new THREE.Group(); trees = []; installHaze(L);
    road = null; const rd = makeRoad(L, roadDef.P, roadDef.az);
    world.add(sky(L), ground(L), rd, billboard(L), scatter(L, eye, view));
    world.add(range(L, 80000, 1500, 5600, L.mt[1], 3, L.mesa), range(L, 46000, 300, 2600, L.mt[0], 11, L.mesa));
    const sd = new THREE.Vector3(...L.sun).normalize();
    const sun = new THREE.DirectionalLight(L.sunCol, L.sunI); sun.position.copy(C).addScaledVector(sd, 9000); sun.target.position.set(C.x, Y0, C.z + 600);
    sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -5000, right: 5000, top: 5000, bottom: -5000, near: 100, far: 22000 }); sun.shadow.bias = -0.0004;
    world.add(sun, sun.target, new THREE.HemisphereLight(L.zenith, L.sand[0], L.hemi)); fgLights(L, sun);
    cars = carDefs.map((cd, i) => { const c = car(L.car[i % L.car.length], cd.kind); const p = road.at(cd.s, cd.side); c.position.copy(p);
      c.rotation.y = Math.atan2(road.dir.x, road.dir.z) + (cd.side > 0 ? 0 : Math.PI); world.add(c); return c; });
    root.add(world);
    scene.fog = new THREE.FogExp2(L.haze, HAZE_DENSITY);
  }

  const api = {
    root, Y0, W, H, C, LOOKS, clock,
    enter(key, roadDef, carDefs, eye, view) {
      for (const o of scene.children) if (o !== root && o.visible) { hidden.push(o); o.visible = false; }
      for (const k in cssCards) if (k !== heroId) cssCards[k].obj.element.style.opacity = '0';
      if (!root.parent) scene.add(root);
      renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.setClearColor(0x000000, 1);
      camera.far = 200000; camera.near = 10; camera.updateProjectionMatrix();
      build(key, roadDef, carDefs, eye, view); viewInfo = view;
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
    heroShot(s, aspect = innerWidth / innerHeight) {
      const f = api.frame({ ...s, aspect });
      const to = C.clone().sub(f.pos); to.y = 0; to.normalize();
      const viewAz = Math.atan2(to.x, -to.z) * 180 / Math.PI, left = new THREE.Vector3(to.z, 0, -to.x);
      const P = new THREE.Vector3(f.pos.x, 0, f.pos.z).addScaledVector(to, s.roadAhead * M).addScaledVector(left, (s.roadLeft || 0) * M);
      const fwd = f.look.clone().sub(f.pos); fwd.y = 0; fwd.normalize();
      const view = { eye: f.pos.clone(), fwd, right: new THREE.Vector3(-fwd.z, 0, fwd.x), row: (s.row || 20) * M, tanH: Math.tan(THREE.MathUtils.degToRad(s.fov / 2)) * aspect };
      api.enter(s.look, { P, az: viewAz + s.roadTurn }, s.cars || [], f.pos, view);
      return f;
    },
    play() { for (const a of actors) a.dispose(); actors.length = 0; clock.t = 0; evI = 0; trafficN = 0; nextCar = 26; clock.playing = true; },
    tick(dt) { if (!clock.manual) update(dt); },
    step(dt) { update(dt); },
  };
  return api;
}

// Josiah 10-21: picked framing A + Golden hour, tightened so the slide reads (render I1). Board lowered to 2.8 m clearance,
// road moved 8 m out from the camera so the double yellow stays in the bottom-left corner.
export const HERO_SHOT = { look: 'golden', clear: 2.8, theta: 22, h: 1.1, fov: 38, ux: 0.28, uy: 0.24, fw: 0.56, roadAhead: 8, roadTurn: -64, row: 20 };
