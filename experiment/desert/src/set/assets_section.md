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
