## SET (billboard + road + ground textures)
Generators: `src/set/` (`asphalt.py`, `lines.py`, `shoulder.py`, `sand.py` → `tex/`; `bb_geo.py` + `bb_build.py` (Blender, bakes)
+ `bb_finish.py` (weathering textures, materials, export) → `assets/billboard.glb`). Rebuild: run each under the lock.

### `assets/billboard.glb` (18,056 tris, 5.2 MB, 11.3 × 7.6 × 3.8 m)
- Origin on the ground directly below the face centre; face plane z = 0 facing +Z; face rectangle x ∈ [−5.465, 5.465],
  y ∈ [2.80, 7.08]. The face frame wraps it outside: |x| 5.465–5.595, y 2.67–7.21, front lip at z = −0.004, 0.20 m deep.
- Nothing is in front of the face rectangle (`bb_geo.check_front_clear`). In addition, nothing in front of the face plane
  rises above the hero camera's sightline (camera 1.1 m high, 15 m out) to the face's bottom edge
  (`bb_geo.check_sightline`, margin 0.18 m), so the HTML slide never cuts a lamp or the toe plate. Catwalk deck at 2.25 m,
  front edge z = 0.90; five floods on gooseneck arms reach z ≈ 1.7 m, tops ≈ 2.4 m, aimed up at the face; pole centre
  z = −0.65, Ø 0.94 → 0.80 m, two flanged sections, 8 anchor bolts on a 1.6 m concrete pier.
- One mesh node per material: `paint_peeling` (pole, head frame, saddle, catwalk brackets/channel/toe plate, lamp arms),
  `steel_weathered` (face frame in dark painted steel; ladder, cage, lamp housings and conduit in dull galvanized; junction
  box + meter in faded grey enamel), `steel_weathered_rear` (face-sheet backs, verticals, stringers, kickers; normally
  hidden), `rust` (bolts, nuts, anchor rods, base plate), `concrete` (pier + grout pad), `grating` (bar-grating deck,
  double-sided, unique non-tiling map with sand drifts and droppings), `glass` (lamp lenses, meter dome; BLEND 0.55,
  double-sided; the 4th lamp from the left has a broken lens with shards), `reflector` (lamp interiors), `vinyl_old` (torn
  remnants on the frame border and shreds hanging below and beside it; double-sided), `plate` (owner's plate on the toe
  plate; fictional text "HIGH DESERT OUTDOOR · STRUCTURE No. 1127", rasterised from DejaVu Sans Bold, free licence).
- `paint_peeling`, `steel_weathered`, `steel_weathered_rear`, `concrete` carry unique baked atlases (albedo with mild AO
  baked in, ORM with G = roughness and B = metallic, normal). The weathering is driven by Cycles-baked world position,
  normal and AO: rust on edges and joints, gravity streaks below every bolt, flange and seam and along the catwalk edge,
  pitting and heavier rust at the pole foot, sand on horizontal surfaces, bird droppings on the toe plate, lamp tops and
  deck, plus a bent catwalk bracket (2nd from the left). Metallic ≤ 0.25 on weathered parts and roughness 0.6–0.95, so the
  sky does not mirror in them. All colour is honest albedo (paint ≈ 0.15–0.24 linear, rust 0.07–0.30).
- Rebuild: `flock … python3 src/set/bb_build.py` (geometry, UVs, bakes, ~90 s) then `python3 src/set/bb_finish.py`
  (weathering, materials, export, ~3 min). bb_build asserts both clearance checks.

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
strips, both shoulders, sand × macro) exactly as intended; run with `--glb` to write `src/set/preview/road.glb` (13 MB, preview only — regenerate, do not ship) for the harness
(`glb=src/set/preview/road.glb&ground=0`). Lines in it: yellow centres at ±0.11 m (v offsets 0 and 3.1 m), white fog lines at
±3.8 m; shoulder strips start at |x| = 4.67 m (u mirrored on the left side, flip the normal's X there).
