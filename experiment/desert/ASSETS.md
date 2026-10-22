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

## FLORA (provisional — in progress, filenames are final, contents keep improving overnight)
- `assets/joshua_{a,b,c,d}.glb` (+ `_lod1`), `creosote_{a,b}.glb`, `bursage_a.glb`, `rock_{a..e}.glb`.
- One mesh node per asset, origin at the trunk/footprint base on y = 0, metres, +Y up.
- Joshua materials: `bark` (texture + normal), `fur` (double-sided, dead-leaf thatch), `leaf` (double-sided).
  Vertex colours COLOR_0 carry per-blade tint and baked AO: keep vertex colours enabled (alpha is always 1).
- Shrubs: `bark` (stems), `leaf` (alphaMode MASK, cutoff 0.5, double-sided). Rocks: `rock` (albedo + normal, single-sided).
- Final numbers, tri counts and LOD notes follow when the pass is done.

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
