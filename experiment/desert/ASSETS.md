# Desert billboard world — asset contract (overnight photoreal pass, 2026-10-21)

The scene is real-time three.js r160 (WebGL2), lit live: ACES tone mapping, image-based lighting from the scene's own
golden-hour sky, one warm sun with soft shadows, ambient occlusion and bloom in post. There is no path tracing in the
browser, so realism has to come from geometry detail, honest PBR values and good textures.

## Where things go
- `desert/assets/<name>.glb` — finished assets. One GLB per asset (or per variant).
- `desert/tex/<name>_{albedo,normal,orm}.jpg|png` — tiling textures not embedded in a GLB (road, ground).
- `desert/src/<thread>/` — the generator scripts (Blender Python, numpy). Everything must be rebuildable from here.
- `desert/preview/` — `harness.html?glb=assets/x.glb&dist=6&h=1.2&yaw=30` previews any GLB in the scene's light.
- Add a section to this file for each asset: size in metres, triangle count, node names, material names, notes.

## Units and axes (GLB as exported)
- Metres. +Y up. The integrator scales by 108 world units per metre.
- Origin on the ground at the asset's footprint centre. Vehicles: nose toward **+Z** in the GLB
  (Blender: nose toward −Y before export), wheels touching y = 0.
- Blender export: `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', export_yup=True, export_apply=True,
  export_image_format='JPEG' where alpha is not needed)`.

## Materials (glTF metallic-roughness)
- Name materials by role so the integrator can tune them live: `paint`, `glass`, `chrome`, `trim_black`, `rubber`,
  `rim`, `brake`, `light_front`, `light_rear`, `interior`, `plate`; `bark`, `fur`, `leaf`, `rock`, `sand`;
  `steel_weathered`, `rust`, `paint_peeling`, `grating`, `wood_old`, `concrete`.
- Physically sensible values. No pure black or pure white albedo (keep 0.03–0.9).
- Glass: dark tint, roughness ≤ 0.05, alphaMode BLEND opacity 0.75–0.9 is fine. The integrator swaps in a physical
  glass with live environment reflections.
- Car paint: base colour + metallic flake feel; the integrator adds clearcoat. Give the `paint` material its own
  name so it can be found.
- Double-sided only where needed (leaves, fur blades, grating).
- Textures embedded, ≤ 2048 px (road/ground tiles may be 2048 or 4096 as separate files). Prefer baked AO into the
  base colour or vertex colours (COLOR_0) for small assets; it reads far better than live AO alone.

## Budgets (triangles, after modifiers)
- Sports car ≤ 150k, minivan ≤ 150k. Wheels as separate nodes `wheel_FL`, `wheel_FR`, `wheel_RL`, `wheel_RR`, origin at
  the hub, so they can spin about their local X axis.
- Joshua tree: 3–4 variants, ≤ 70k each (they are instanced ~70 times, far ones get a cheaper LOD `_lod1` ≤ 8k).
- Creosote/shrub: 2–3 variants ≤ 8k. Rocks: 4–6 variants ≤ 4k each with normal maps.
- Billboard structure: ≤ 200k total.

## Hard rules from the scene
- No skinning, morph targets or animation in the GLBs (motion is done in code).
- Nothing may sit in front of the billboard face (the slide is HTML layered over the canvas). Structure lives behind
  and below the face. The face rectangle is 10.93 m × 4.28 m (the slide), its bottom edge 2.80 m and centre 4.94 m above the ground;
  the frame should wrap that rectangle with ~0.13 m of border.
- Everything original or CC0; log any third-party source with its licence in `desert/CREDITS.md`.

## Shared machine: 2 CPU cores, 7 GB RAM
- Wrap every heavy run (Blender, headless Chromium) in the shared lock so threads take turns:
  `flock /tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/heavy.lock <command>`
- Keep Blender runs headless (`python3 script.py` with `import bpy`), factory settings, no GPU.
- Local server for previews: `http://localhost:8765/experiment/desert/preview/harness.html?...` (start it with
  `cd /home/claude/walkermotionpictures && python3 -m http.server 8765` if it isn't answering).

## FLORA (Joshua trees, shrubs, rocks) — generator: `src/flora/`
Rebuild: `cd src/flora && python3 textures.py && python3 joshua.py && python3 shrubs.py && python3 rocks.py`
(Blender 5.x as a Python module; run under the shared lock; ~2 min total). `write_docs.py` regenerates this table.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `bursage_a.glb` | 0.92 × 0.46 × 0.94 | 6,900 | 0.5 MB | bark, leaf |
| `creosote_a.glb` | 1.82 × 1.99 × 1.73 | 4,812 | 0.3 MB | bark, leaf |
| `creosote_b.glb` | 1.50 × 1.42 × 1.35 | 3,252 | 0.3 MB | bark, leaf |
| `joshua_a.glb` | 1.07 × 2.99 × 1.51 | 61,284 | 6.5 MB | bark, fur, leaf |
| `joshua_a_lod1.glb` | 1.05 × 2.99 × 1.46 | 7,905 | 0.9 MB | bark, fur, leaf |
| `joshua_b.glb` | 2.99 × 5.00 × 2.80 | 67,586 | 6.9 MB | bark, fur, leaf |
| `joshua_b_lod1.glb` | 3.00 × 5.01 × 2.78 | 7,599 | 0.9 MB | bark, fur, leaf |
| `joshua_c.glb` | 4.68 × 6.92 × 7.90 | 69,024 | 6.6 MB | bark, fur, leaf |
| `joshua_c_lod1.glb` | 4.65 × 6.91 × 7.95 | 7,657 | 0.8 MB | bark, fur, leaf |
| `joshua_d.glb` | 6.69 × 8.94 × 6.84 | 69,536 | 6.0 MB | bark, fur, leaf |
| `joshua_d_lod1.glb` | 6.63 × 8.89 × 6.80 | 7,629 | 0.7 MB | bark, fur, leaf |
| `rock_a.glb` | 2.46 × 1.48 × 1.91 | 3,999 | 0.7 MB | rock |
| `rock_b.glb` | 1.33 × 1.43 × 1.19 | 3,999 | 0.7 MB | rock |
| `rock_c.glb` | 1.49 × 0.53 × 1.02 | 2,998 | 0.4 MB | rock |
| `rock_d.glb` | 0.57 × 0.38 × 0.44 | 1,280 | 0.3 MB | rock |
| `rock_e.glb` | 0.30 × 0.19 × 0.25 | 1,198 | 0.1 MB | rock |

Common to all: one mesh node named like the file, origin on the ground at the trunk/footprint centre, metres, +Y up,
no animation. Vertex colours COLOR_0 (RGB, normalized uint8) carry per-blade tint **and baked ambient occlusion** —
keep `vertexColors` on. Normals are int8 via `KHR_mesh_quantization` (three.js GLTFLoader handles it natively).
Fur/bark/leaf carry `KHR_materials_specular` (lowered F0, matte dead leaves).

**Joshua trees** (`joshua_a` young 3 m single trunk · `b` 5 m Y-fork · `c` 7 m mature classic · `d` 9 m old broad).
- `bark` — corky checkered trunk bark (1024 albedo + normal), single-sided, roughness 0.95. Lower trunk only.
- `fur` — dead-leaf skirt, double-sided: a thatch-textured core tube plus thousands of downward blades (flat
  straws and thin strands, curled tips; tan-brown just under each rosette, weathering to grey-straw).
  Visible albedo ≈ 0.30–0.38 linear. On the trunk from ~1 m up (a: from 0.5 m) and on all younger limbs.
- `leaf` — living rosettes, double-sided: stiff keeled dagger leaves 18–34 cm, ~1.2 cm wide, blue-green to olive,
  pale serrated margin and brown spine in the texture, radiating like a sea urchin; yellowing band below.
- Trunk diameters at 1 m: a 0.25, b 0.34, c 0.48, d 0.72 m (at the ground with flare: 0.32 / 0.42 / 0.61 / 0.97 m).
- Rosette tip positions per hero tree (glTF coords): `src/flora/_tex/joshua_<v>_tips.json` (useful for wind/sway).
- `_lod1` (≤ 8k tris, 512 px textures): same skeleton/silhouette, 5-sided tubes, single-triangle leaves and blades,
  thicker thatch core. Matches the hero from ~35 m; switch at 35–45 m. Fur blades are double-sided: no need to
  disable backface culling elsewhere.
- Sway (if wanted): bend ∝ height², rosettes are at the branch tips; the trees are stiff — keep amplitude tiny.

**Shrubs** — `creosote_a` (1.7 m, open vase) and `creosote_b` (1.35 m): thin dark-grey stems (`bark`, vertex colour
only) + alpha-tested leaf-sprig cards (`leaf`, alphaMode MASK cutoff 0.5, double-sided, PNG with alpha).
`bursage_a`: low pale grey-green mound ~0.55 m × 0.9 m.

**Rocks** — `rock_a` big rounded block 2.5 m, `rock_b` upright faceted 1.4 m, `rock_c` low slab, `rock_d`/`rock_e`
cobbles 0.55/0.3 m. Joshua-Tree monzogranite: buff-tan with orange iron staining, coarse grain speckle, joint
fractures, spalled exfoliation patches, narrow desert-varnish streaks, small lichen crusts, sand/dust at the base.
Material `rock`: 1024 px albedo (cavity/AO baked in) + tangent-space normal (512 for rock_e), roughness 0.88,
single-sided. Bottoms are sunk 5–12 cm below y = 0 so they sit in the sand; scale freely (±30%) and rotate about Y.
## SET (billboard + road + ground textures)
Generators: `src/set/` (`asphalt.py`, `lines.py`, `shoulder.py`, `sand.py` → `tex/`; `bb_geo.py` + `bb_build.py` (Blender, bakes)
+ `bb_finish.py` (weathering textures, materials, export) → `assets/billboard.glb`). Rebuild: run each under the lock.

### `assets/billboard.glb` (~18k tris, ~5.3 MB)
- Origin on the ground directly below the face centre; face plane z = 0 facing +Z; face rectangle x ∈ [−5.465, 5.465],
  y ∈ [2.80, 7.08]. Nothing is in front of it (checked by `bb_geo.check_front_clear`): the frame lip sits at z = −0.004, the
  catwalk / lamps project forward only below y = 2.80 (lamp tops ≈ 2.75 m, catwalk deck 2.25 m, front edge z = 0.90).
- One mesh node per material: `paint_peeling` (pole, head frame, saddle, catwalk brackets/channel/toe plate, lamp arms),
  `steel_weathered` (face frame — dark painted steel; ladder, cage, lamp housings, conduit — dull galvanized; junction box
  + meter — faded grey enamel), `steel_weathered_rear` (face sheet backs, verticals, stringers, kickers; normally hidden),
  `rust` (bolts, nuts, anchor rods, base plate), `concrete` (pier + grout pad), `grating` (bar-grating deck, double-sided),
  `glass` (lamp lenses, meter dome; BLEND 0.55, double-sided; lamp #4 from the left has a broken lens),
  `reflector` (lamp interiors, metallic), `vinyl_old` (torn remnants on the border + shreds hanging below/beside the frame;
  double-sided), `plate` (owner's plate on the toe plate, fictional text).
- Atlas materials carry unique baked textures (albedo with mild AO, ORM: G = roughness, B = metallic, normal). The integrator
  may tune `paint_peeling` / `steel_weathered` colour factors live; no envMap-mirror: metallic ≤ 0.25 on weathered parts.
- Bent catwalk bracket (2nd from the left), rust streaks from bolts / flanges / catwalk edge, bird droppings on the toe
  plate, lamp tops and the deck, sand on horizontal surfaces, pitting at the pole foot.

### Road and ground textures (`tex/`) — all tile seamlessly; albedo is sRGB, everything else linear
| file | size | covers | mapping |
|---|---|---|---|
| `asphalt_albedo.jpg`, `asphalt_normal.jpg`, `asphalt_rough.jpg` | 2048² | 4 m × 4 m | world-planar on the paved surface, **u across the road, v along it**, repeat = road metres / 4. Normal: OpenGL/glTF (+Y up). Rough: grey = roughness. Mean albedo ≈ 0.125 linear: oxidised chip seal (visible 6–12 mm stones, grit, dust in the low spots), faint hairline cracks. |
| `asphalt_macro.png` (RGB) + `asphalt_macro.jpg` (grey = R only) | 1024 × 8192 | 10.2 m (full paved width, centre line at u = 0.5) × 80 m | u = (lateral offset m + 5.1) / 10.2 (clamp), v = along-road m / 80 (repeat). **R**: albedo multiplier, multiply the tile albedo by `2 × R` (0.5 = ×1): wheel-path darkening at ±1.05 / ±2.65 m, oil-drip stripes at ±1.85 m, bleached crown and edges, patches, open cracks, and the tar sealant already darkened. **G**: crack-sealant mask ("tar snakes": sealed transverse thermal cracks every 5–14 m, sealed centre joint, meandering snakes, patch seams) → where G = 1 use roughness ≈ 0.42 (sealant is glossy) and optionally albedo 0.035 linear. **B**: patch mask (newer, smoother patches; roughness −0.08). The tile itself is deliberately quiet so the macro carries all the landmarks: this is what prevents visible 4 m repeats. If only one texture can be wired, use the grey `.jpg` as the multiplier. |
| `lines_yellow_albedo.png`, `lines_white_albedo.png`, `lines_alpha.png`, `lines_normal.png` | 256 × 4096 | 0.15 m × 8 m | one strip per painted line: u across the 0.15 m strip (paint itself ≈ 0.11 m wide, ragged edges), v along it, repeat every 8 m. Alpha = paint coverage (worn gaps show the asphalt). Use a different v offset for each of the two yellow lines. The normal includes the aggregate under the paint, so the strip can replace the asphalt normal where alpha > 0. |
| `shoulder_albedo.jpg`, `shoulder_normal.jpg`, `shoulder_mask.png` | 1024 × 2048 | 1.5 m (u, across) × 3 m (v, along) | u = 0 at the road side (solid asphalt) → u = 1 desert; the ragged broken edge sits at ≈ 0.43 m (±0.1 m). Tiles along v only. `shoulder_mask` = 1 paved / 0 gravel; use it to blend into the asphalt material on the inner side and into sand on the outer side. Mirror u for the other side of the road. |
| `sand_albedo.jpg`, `sand_normal.jpg`, `sand_rough.jpg` | 2048² | 6 m × 6 m | world-planar xz, repeat = metres / 6. Desert pavement: tan sand (mean ≈ 0.37/0.28/0.20 linear), packed gravel and pebbles, wind ripples, twigs and litter. |
| `sand_macro.jpg` | 1024² | 300 m × 300 m | multiply the sand albedo by `2 × macro` (RGB, 0.5 = ×1); world xz / 300. Also good for a faint hue shift on rocks and shrubs. |

Reference composite: `src/set/road_preview.py` builds the whole road cross-section (asphalt × macro + sealant, four line
strips, both shoulders, sand × macro) exactly as intended, and writes `src/set/preview/road.glb` for the harness
(`glb=src/set/preview/road.glb&ground=0`). Lines in it: yellow centres at ±0.11 m (v offsets 0 and 3.1 m), white fog lines at
±3.8 m; shoulder strips start at |x| = 4.67 m (u mirrored on the left side, flip the normal's X there).

## CARS
Generators: `src/cars/` — `sports.py` / `minivan.py` (+ `*_params.py` design numbers), shared `body.py` (implicit body
field), `carlib.py` (meshing, cuts, decimation), `surfops.py` (exact level-set cuts → panel gaps, glass, lamp recesses),
`wheels.py`, `interior.py`, `details.py`, `blendout.py` (Blender → GLB). Rebuild (under the lock, ~1.5 min each):
`cd src/cars && python3 sports.py && python3 minivan.py`. Preview: `python3 src/cars/shots.py assets/car_sports.glb <prefix>`.
Everything is procedural (no third-party meshes or textures); plate text is fictional.

### `assets/car_sports.glb` — red GT coupe, 4.55 × 1.94 (body; 2.0 with mirrors) × 1.25 m, wheelbase 2.70 m
### `assets/car_minivan.glb` — blue minivan, 5.15 × 1.99 (body; 2.20 with mirrors) × 1.78 m (1.81 with roof rails), wheelbase 3.01 m
- Frame: nose toward **+Z**, +Y up, origin at the footprint centre on the ground, tyres touch y = 0. The car's left (driver)
  side is **+X**.
- Nodes: `car` (root) → `body`, `wheel_FL`, `wheel_FR`, `wheel_RL`, `wheel_RR`. FL/RL are on +X (car's left).
  Each wheel node's origin is the hub centre (sports: y = 0.343 m, minivan: y = 0.368 m); it holds tyre + rim + brake disc
  + centre cap. Spin about local **X**: `wheel.rotation.x += speed / radius * dt` for forward travel along +Z.
  Brake calipers are in `body` (they do not spin).
- Triangles: see the table below (`body` includes interior, lamps, grille mesh, mirrors, wipers, plates, exhausts, roof rails).
- Materials (all named by role): `paint` (base colour = the paint colour; COLOR_0 carries baked occlusion, darker low on the
  body and inside the arches — keep vertex colours on), `glass` (BLEND α 0.82, dark tint), `trim_black` (window surrounds,
  gaps, grille, cladding, wheel wells, underbody; COLOR_0 darkens recesses), `chrome`, `rubber` (tyres: normal map +
  roughness map for tread sipes and sidewall ribs), `rim` (sports: dark graphite; minivan: silver), `brake` (disc,
  textured with drilled holes), `caliper` (sports: red; minivan: dark grey), `light_front` (DRL strips/projectors, emissive
  0.6), `light_rear` (tail lamp lenses, faint emissive), `light_rear_led` (thin LED bars inside the tail lamps, emissive 2),
  `light_marker` (amber side markers), `light_cover` (clear headlamp cover, BLEND α 0.18), `interior` (cabin shell,
  seats, dash, wheel), `plate` (textured US-size plate, fictional "7ABC123" / "8MVN417"; rear only on the coupe).
- The integrator's clearcoat / physical glass swap: `paint` and `glass` are single materials per car, safe to replace.
- Headlamp recesses are open cavities behind `light_cover`; tail lamps are inset 6 mm. All glass is inset 7–8 mm from
  the body with a black frit/surround, so the silhouette stays crisp at speed.
