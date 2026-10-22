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
    asphalt: 0x4b4646, shoulder: 0xc8955f, frame: 0x221f20, car: [0xe8e0d2, 0x2d5a7a, 0x8a2f22],
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

export function makeDesert({ scene, cssCards, heroId = 'hero', camera, renderer }) {
  const hero = cssCards[heroId], C = hero.obj.position.clone();
  const W = hero.el.offsetWidth, H = hero.el.offsetHeight;
  const bottom = C.y - H / 2, clearance = (window.__clear || 3.8) * M, Y0 = bottom - clearance;     // ground sits ~3.8 m under the face
  const root = new THREE.Group(); root.name = 'desert';
  let world = null, lookKey = 'mojave', road = null, cars = [];
  const hidden = [];

  const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 1, metalness: 0, flatShading: true, ...o });

  // ---------- sky dome ----------
  function sky(L) {
    const s = new THREE.Vector3(...L.sun).normalize();
    const m = new THREE.ShaderMaterial({ side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { zen: { value: new THREE.Color(L.zenith) }, hor: { value: new THREE.Color(L.horizon) }, sun: { value: s }, sunCol: { value: new THREE.Color(L.sunCol) } },
      vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 zen, hor, sun, sunCol; varying vec3 vD; void main(){ float h = clamp(vD.y, 0.0, 1.0); vec3 c = mix(hor, zen, pow(h, 0.45)); float g = max(dot(normalize(vD), sun), 0.0); c += sunCol * (pow(g, 600.0) * 1.2 + pow(g, 8.0) * 0.12); gl_FragColor = vec4(c, 1.0); }' });
    const d = new THREE.Mesh(new THREE.SphereGeometry(95000, 48, 24), m); d.position.set(C.x, Y0, C.z); d.renderOrder = -10; d.frustumCulled = false; return d;
  }

  // ---------- ground and ranges ----------
  function ground(L, r) {
    const g = new THREE.PlaneGeometry(160000, 160000, 220, 220); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position, col = [], a = new THREE.Color(L.sand[0]), b = new THREE.Color(L.sand[1]), t = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), z = p.getZ(i), d = Math.hypot(x, z), rd = road ? road.dist(x + C.x, z + C.z) : 1e9;
      const n = Math.sin(x * 0.0021 + 1.3) * Math.cos(z * 0.0017) + Math.sin(x * 0.0007 - z * 0.0009) * 1.6;
      const amp = Math.min(1, Math.max(0, (rd - 900) / 3000)) * Math.min(1, d / 8000);
      p.setY(i, n * 26 * amp + amp * Math.max(0, d - 20000) * 0.01);
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
  function scatter(L, eye) {
    const g = new THREE.Group(), r = rng(7);
    const ok = (x, z, clear) => (!road || road.dist(x, z) > road.halfW + clear) && Math.hypot(x - C.x, z - (C.z - 70)) > 2.2 * M && (!eye || Math.hypot(x - eye.x, z - eye.z) > clear * 6 + 4 * M);
    const place = (n, rMin, rMax, clear, fn) => { let k = 0, tries = 0; while (k < n && tries++ < n * 30) {
      const a = r() * Math.PI * 2, d = rMin + Math.pow(r(), 1.6) * (rMax - rMin), x = C.x + Math.cos(a) * d, z = C.z + Math.sin(a) * d;
      if (!ok(x, z, clear)) continue; fn(x, z, d); k++; } };
    // bushes (instanced)
    const bushGeo = new THREE.IcosahedronGeometry(1, 1), bushCount = 1400;
    L.bush.forEach((c, bi) => {
      const im = new THREE.InstancedMesh(bushGeo, mat(c), bushCount / 3 | 0), d = new THREE.Object3D(); let i = 0;
      place(bushCount / 3 | 0, 300, 26000, 0.8 * M, (x, z, dd) => { const s = (0.2 + Math.pow(r(), 2) * 0.45) * M * (dd > 8000 ? 1.5 : 1); d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r() * .6), s * 0.55, s * (1 + r() * .6)); d.rotation.y = r() * 6; d.updateMatrix(); im.setMatrixAt(i++, d.matrix); });
      im.count = i; im.castShadow = true; im.receiveShadow = true; g.add(im);
    });
    // rocks
    const rockGeo = new THREE.DodecahedronGeometry(1, 0), rk = new THREE.InstancedMesh(rockGeo, mat(L.rock), 260), d = new THREE.Object3D(); let ri = 0;
    place(260, 400, 18000, 0.5 * M, (x, z) => { const s = (0.12 + Math.pow(r(), 4) * 1.0) * M; d.position.set(x, Y0 + s * 0.2, z); d.scale.set(s * (1 + r()), s * (0.5 + r() * 0.5), s * (1 + r())); d.rotation.set(r(), r() * 6, r()); d.updateMatrix(); rk.setMatrixAt(ri++, d.matrix); });
    rk.count = ri; rk.castShadow = rk.receiveShadow = true; g.add(rk);
    // a few boulder piles near the billboard
    for (let k = 0; k < 2; k++) { const bx = C.x + (k - 1) * 9 * M + (r() - .5) * 4 * M, bz = C.z - (3 + r() * 9) * M; if (!ok(bx, bz, M)) continue;
      for (let j = 0; j < 4; j++) { const s = (0.4 + r() * 0.7) * M, b = new THREE.Mesh(rockGeo, mat(L.rock)); b.position.set(bx + (r() - .5) * 2 * M, Y0 + s * .3, bz + (r() - .5) * 2 * M); b.scale.set(s * 1.3, s * .8, s); b.rotation.set(r(), r() * 6, r()); b.castShadow = b.receiveShadow = true; g.add(b); } }
    // trees
    const tree = L.tree === 'joshua' ? joshua : saguaro;
    place(L.tree === 'joshua' ? 70 : 55, 1800, 24000, 1.5 * M, (x, z, dd) => { const t = tree(L, r, dd > 9000 ? 1.25 : 1); t.position.set(x, Y0, z); t.rotation.y = r() * 6; g.add(t); });
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

  // ---------- assemble ----------
  function build(key, roadDef, carDefs = [], eye = null) {
    if (world) { root.remove(world); world.traverse(o => { o.geometry?.dispose?.(); }); }
    lookKey = key; const L = LOOKS[key]; world = new THREE.Group();
    road = null; const rd = makeRoad(L, roadDef.P, roadDef.az);
    world.add(sky(L), ground(L), rd, billboard(L), scatter(L, eye));
    world.add(range(L, 80000, 1500, 5600, L.mt[1], 3, L.mesa), range(L, 46000, 300, 2600, L.mt[0], 11, L.mesa));
    const sd = new THREE.Vector3(...L.sun).normalize();
    const sun = new THREE.DirectionalLight(L.sunCol, L.sunI); sun.position.copy(C).addScaledVector(sd, 9000); sun.target.position.set(C.x, Y0, C.z + 600);
    sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -5000, right: 5000, top: 5000, bottom: -5000, near: 100, far: 22000 }); sun.shadow.bias = -0.0004;
    world.add(sun, sun.target, new THREE.HemisphereLight(L.zenith, L.sand[0], L.hemi));
    cars = carDefs.map((cd, i) => { const c = car(L.car[i % L.car.length], cd.kind); const p = road.at(cd.s, cd.side); c.position.copy(p);
      c.rotation.y = Math.atan2(road.dir.x, road.dir.z) + (cd.side > 0 ? 0 : Math.PI); world.add(c); return c; });
    root.add(world);
    scene.fog = new THREE.Fog(L.haze, 14000, 150000);
  }

  return {
    root, Y0, W, H, C, LOOKS,
    enter(key, roadDef, carDefs, eye) {
      for (const o of scene.children) if (o !== root && o.visible) { hidden.push(o); o.visible = false; }
      for (const k in cssCards) if (k !== heroId) cssCards[k].obj.element.style.opacity = '0';
      if (!root.parent) scene.add(root);
      renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.setClearColor(0x000000, 1);
      camera.far = 200000; camera.near = 10; camera.updateProjectionMatrix();
      build(key, roadDef, carDefs, eye);
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
    tick(dt) { for (const c of cars) { const v = 25 * M * dt; c.translateZ(v); } },
  };
}

// Josiah 10-21: picked framing A + Golden hour, tightened so the slide reads (render I1). Board lowered to 2.8 m clearance,
// road moved 8 m out from the camera so the double yellow stays in the bottom-left corner.
export const HERO_SHOT = { look: 'golden', clear: 2.8, theta: 22, h: 1.1, fov: 38, ux: 0.28, uy: 0.24, fw: 0.56, roadAhead: 8, roadTurn: -64 };
