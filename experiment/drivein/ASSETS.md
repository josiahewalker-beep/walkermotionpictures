# Drive-in world: asset contract (detailed pass, 2026-10-22)

The second slide ("A finance product, sold as a story.", card id `work`) becomes the image on a drive-in theatre's
screen in a mountain town at night. The scene is real-time three.js r160 (WebGL2): ACES tone mapping, image-based
light, live shadows, ambient occlusion, bloom and grain in post. Realism comes from geometry detail, honest PBR values
and good textures. Match the quality of the desert world (`../desert/ASSETS.md`, `../desert/assets/*.glb`).

## The brief (Josiah, 2026-10-22)
- Cozy and intimate; warm 80s feel (greens and browns from the pines, amber lot light), but the cars are from the 90s.
  You should be able to smell the pine needles.
- Light: warm amber from behind the camera (concession stand), a pole lamp on the left, the projector beam from a booth
  up on the right. The moon is upper right, behind the screen: soft cool backlight on the screen's edges, the pine tops
  and the crest of the hills.
- Sequence (done in code, not in the GLBs): the projector beam flickers gently; sparse dust in the beam; a moth flutters
  in the beam, leaves it, disappears for a few seconds, flutters back. 3 s: the popcorn bucket on the red car's open
  driver's window ledge falls and spills popcorn on the dirt. 10 s: a mouse/rat scurries in from the left to the
  popcorn, sits and nibbles a piece. ~16 s: an owl flies across the upper right, right to left, through the beam, as a
  silhouette.

## Layout (metres; the blockout `src/blockout.html` is the reference)
- Screen: the slide itself, 22.00 × 12.67 m, corner radius 0.43 m, bottom edge 6.0 m above lot zero, centre (0, 12.34, 0),
  facing +Z. NOTHING may sit in front of the screen face (the slide is HTML layered over the canvas). Structure lives
  behind it (z < -0.15) and below its bottom edge.
- Lot: ground rises gently from y = 0 at z = 40 (the camera, low at the back) to y = 2.7 at z = 10, flat beyond; the red
  car sits on a 1.1 m lift and the wood-brown sedan on 0.6 m, hidden under them. From the camera it reads as a flat lot.
  Tyre tracks are drawn by the integrator as a 90 m overlay.
- Camera (fixed): (-12.54, 2.16, 40.45) looking at (1.16, 10.74, 3.86), vertical FOV 26.5°.
- Cars, facing the screen (nose toward -Z), x, z, yaw (rad, + turns the nose toward -X):
  - hero red car (-4.08, 28.45, 0.40) on its 1.1 m lift. The camera sees its whole left (driver's) side: driver's window
    rolled down, popcorn bucket on the window ledge, both wheels, door seam and handle.
  - forest-green wagon/SUV (-11.93, 18.80, 0.10); mustard sedan (-8.27, 10.07, -0.05);
    cream SUV/wagon (-2.57, 9.31, 0.05); wood-brown sedan (-1.43, 17.28, 0.12) on its 0.6 m lift.
- Projection booth: lens at (10.18, 9.95, 26.72), a small timber booth on tall legs, aimed at the screen centre.
  Only its beam is in frame; the booth itself is just off the right edge.
- Pole lamp: the warm lamp on the left at roughly (-13, 4, 24). Concession stand behind the camera at (-24, 0, 52).
- Pines: a dense ring 70-200 m out and flanks on both sides; ridges at 210 and 300 m.

## Where things go
- `drivein/assets/<name>.glb`, `drivein/tex/<name>_{albedo,normal,rough}.jpg` (tiling ground textures),
  `drivein/src/<thread>/` generator scripts (Blender Python, numpy); everything rebuildable from there.
- `drivein/preview/harness.html?glb=assets/x.glb&dist=6&h=1.2&yaw=30` previews a GLB in the drive-in's night light
  (night=1 is the default). Screenshot with `python3 src/shot.py '<query>' out.png`.
- Add a section to this file per asset: size in metres, triangle count, node names, material names, notes.

## Units, axes, export
- Metres. +Y up. Origin on the ground at the footprint centre. Vehicles: nose toward **+Z** in the GLB (Blender: nose
  toward −Y before export), wheels touching y = 0. The integrator scales by 50.9 world units per metre.
- `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', export_yup=True, export_apply=True)`; JPEG textures
  where alpha is not needed, ≤ 2048 px embedded (≤ 1024 for small props).
- No skinning, morph targets or animation. Anything that moves is its own named node with its pivot at the hinge
  (wings, bucket, mouse head), and the integrator animates it in code.

## Materials (glTF metallic-roughness), named by role
`paint`, `glass`, `chrome`, `trim_black`, `rubber`, `rim`, `light_front`, `light_rear`, `interior`, `plate`;
`bark`, `needles`, `rock`, `dirt`; `wood_old`, `steel_weathered`, `paper`, `popcorn`; `fur`, `feather`, `wing`.
Physically sensible values, albedo 0.03-0.9. Bake AO into vertex colours (COLOR_0) or base colour where it helps.
Double-sided only where needed (needle cards, wings).

## Budgets (triangles)
- Hero red car ≤ 150k (it is ~14 m from camera and the most seen). The other four cars ≤ 60k each (20-35 m away).
- Speaker post with speaker ≤ 2k. Popcorn bucket ≤ 3k; popcorn kernels: one ≤ 300-tri kernel, instanced.
- Pine: 3 variants ≤ 60k each plus `_lod1` ≤ 6k. Hills are the integrator's (procedural).
- Screen structure + booth + lamp pole ≤ 120k total.
- Moth ≤ 2k, mouse ≤ 8k, owl ≤ 10k (silhouette against the sky: the outline matters, not the texture).

## Shared machine: 2 CPU cores, 7 GB RAM
Wrap every heavy run (Blender, headless Chromium) in the shared lock and keep runs short:
`flock /tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/heavy.lock <command>`.
Local server for previews: `cd /home/claude/walkermotionpictures && python3 -m http.server 8765` (start it if it isn't
answering). Do not touch anything outside `experiment/drivein/` (the desert, the site pages and the main site are live).
Log any third-party source with its licence in `drivein/CREDITS.md`; original or CC0 only.

<!-- PINES:BEGIN -->
## PINES (conifers, ground textures, scatter props, rocks) — generator: `src/pines/`
Rebuild (under the shared lock, ~3 min total): `cd src/pines && python3 pinetex.py && python3 pines.py && python3 props.py
&& python3 rocks.py && python3 ground.py && python3 write_docs.py` (`run.sh "<cmd>" "<harness query>|<png>"` builds and
screenshots in one lock acquisition). Everything is procedural (numpy/PIL + Blender as a Python module); no third-party
meshes or textures. Pipeline and helpers adapted from `desert/src/flora` (vertex-colour AO, KHR_mesh_quantization).
`groundpreview.py lot|forest` writes a preview-only textured plane to `src/pines/preview/` (harness: `&ground=0`).

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `pine_a.glb` | 11.51 × 29.68 × 11.41 | 56,738 | 5.2 MB | bark, needles |
| `pine_a_lod1.glb` | 11.70 × 30.24 × 11.69 | 5,798 | 0.8 MB | bark, needles |
| `pine_b.glb` | 4.34 × 23.26 × 4.45 | 46,222 | 5.0 MB | bark, needles |
| `pine_b_lod1.glb` | 4.34 × 23.37 × 4.56 | 5,800 | 0.9 MB | bark, needles |
| `pine_c.glb` | 10.84 × 32.57 × 10.43 | 56,900 | 5.3 MB | bark, needles |
| `pine_c_lod1.glb` | 11.21 × 33.45 × 10.91 | 5,800 | 0.8 MB | bark, needles |
| `rock_a.glb` | 2.40 × 1.29 × 1.83 | 3,000 | 0.6 MB | rock |
| `rock_b.glb` | 1.24 × 1.05 × 1.09 | 2,899 | 0.6 MB | rock |
| `pinecone.glb` | 0.10 × 0.07 × 0.07 | 480 | 0.2 MB | bark |
| `needle_clump.glb` | 0.95 × 0.03 × 0.92 | 96 | 0.2 MB | needles |

Common to all: one mesh node named like the file, origin on the ground at the trunk/footprint centre, metres, +Y up, no
animation. COLOR_0 (RGB, normalized uint8) carries baked sky-visibility AO and tint: keep `vertexColors` on (the rocks
and the pinecone have their AO in the albedo instead). Normals int8 via `KHR_mesh_quantization`.

**Trees.** `pine_a` ponderosa pine, 30 m: clear cinnamon/orange plated trunk (dbh 0.82 m) to ~46 % of height, open
rounded crown ~10 m wide, long-needle bottlebrush tufts clumped at the branch ends. `pine_b` lodgepole pine, 23.5 m:
very straight grey-brown pole (dbh 0.36 m), narrow ~3.5 m crown in the top 40 %, dead grey branch stubs below.
`pine_c` Douglas fir, 32.5 m: dense dark-green cone from ~2 m to a pointed leader, ~10 m wide at the base, drooping
branches with upturned tips.
- `bark`: tiling bark (1024 albedo + normal; u around the trunk, v up; ponderosa tile 1.2 × 1.6 m), roughness 0.92,
  single-sided. Branches and stubs are in the same material. The trunk is lightly darkened at the foot.
- `needles`: RGBA atlas (2 × 2 variants of the species' tuft/spray), alphaMode MASK, cutoff 0.4, double-sided,
  roughness 0.82, `KHR_materials_specular` 0.3 (low sheen: higher specular made the backlit crowns read frosted).
  Pines: three card planes 60° apart around each twig (hero) / crossed pairs (LOD1); fir: pairs of flat sprays
  rolled ±20-45°. Visible foliage albedo after AO ≈ linear (0.04, 0.07, 0.035), olive-brown shifted on inner/older
  tufts, darker toward the crown core (vertex colour).
- Normals: every needle card carries the same **radial** normal (outward from the trunk axis plus a little up), and
  its winding faces outward too. So from the camera the near side of a crown faces the viewer and stays dark against
  the moon, and the moon only catches the moonward flank and the tops. Keep three.js's default double-sided
  handling (back faces flip the normal): that is what keeps cards seen from behind, through crown gaps, facing the
  viewer and dark. Do not patch it out.
- `_lod1` (≤ 6k tris, 512 px textures): same trunk axis, ponderosa keeps its 45 thickest limbs; the hero's tufts are
  k-means clustered into ~1,200-1,400 larger crossed cards with each cluster's mean colour → the same silhouette and
  colour from ~60 m on. Switch at 50-70 m (the whole ring at 70-200 m can be LOD1; flank trees at 25-60 m hero).
- Placement: scale 0.8-1.15 and rotate freely about Y; tilt ≤ 2°. Mix roughly 45 % ponderosa, 30 % fir, 25 %
  lodgepole for a Front-Range montane look; lodgepoles look best in small groups.
- Alpha-tested foliage thins in the mip chain at distance; the atlases' alpha is pre-thickened. If the far ring looks
  sparse, set `material.alphaToCoverage = true` (with MSAA) or lower `alphaTest` to 0.3 on the LOD1 material.
- Moon backlight: for a stronger rim on the tuft edges, a small view-dependent term on `needles` works better than
  more light (e.g. emissive += `0.15 * moonColor * pow(1 - |dot(N, V)|, 3) * saturate(dot(-V, moonDir))`).

**Ground textures** (`tex/`, 2048², 4 m × 4 m, seamless; albedo sRGB, normal OpenGL +Y = +v, rough grey = roughness):
- `lot_*`: compacted decomposed-granite dirt (mean albedo ≈ 0.19/0.145/0.10 linear), fine-scale tyre-packed crust,
  grit and 2-20 mm gravel with shadowed rims, a few scattered ponderosa needles (singles and 3-needle fascicles) and
  ~3 cones per tile. Deliberately no ruts, lanes or large landmarks (the integrator's 90 m track overlay multiplies
  it). Strong relief in the normal for grazing views; roughness ≈ 0.90 (stones 0.6-0.8, packed 0.85).
- `forest_*`: needle duff under the trees: dark humus nearly covered by layers of fallen needles (old grey-brown below,
  fresh rust-orange on top), bark flakes, twigs, a few cones. Mean ≈ 0.15/0.09/0.05. Roughness ≈ 0.77.

**Scatter props.** `pinecone` (ponderosa cone lying on its side, 9.5 cm, `bark` with its own 512 albedo + normal of
phyllotactic scales; scale 0.8-1.2). `needle_clump` (48 flat fallen-needle cards over a ~0.9 m patch, a few mm off the
ground, `needles` MASK double-sided; scatter a handful near the camera and under the flank trees).

**Rocks.** `rock_a` (2.4 m rounded block), `rock_b` (1.1 m faceted, upright): grey Rocky Mountain granite with biotite speckle,
grey-green and pale-green lichen on the tops, black crusts, rare orange spots, moss and needle duff at the base, sunk
5-12 cm. Material `rock`: 1024 albedo (AO baked in) + normal, roughness 0.88. Scale ±30 % and rotate about Y.
<!-- PINES:END -->

<!-- SET:BEGIN -->
## SET (screen structure, projection booth, lamp pole, popcorn) — generator: `src/set/`
Rebuild (each under the lock): `python3 src/set/screen_build.py` (~1.5 min), `booth_build.py` (~1 min), `lamp_pole.py`,
`popcorn.py` (seconds). Blender 5 as a Python module. Pipeline (`pipe.py`, `setbuild.py`, `weather2.py`) follows the
desert billboard: numpy geometry → Smart-UV atlas → Cycles bakes of world position / normal / AO / member grain axis /
paint mask → numpy weathering (30-40 years of mountain weather: silvered and checked timber, creosote on posts, rot and
moss at the feet, lichen, pine-needle duff on every horizontal, rust runs under every bolt and nail, owl droppings on the
rails, painted-over plywood chalking and peeling along sheet edges) → unique albedo (AO baked in) + ORM (G rough, B metal)
+ normal per material. `python3 src/set/write_docs.py` regenerates the tables below.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `screen.glb` | 23.19 × 16.17 × 8.15 | 13,584 | 3.2 MB | concrete, screen_panel, steel_weathered, steel_weathered_rear, wood_old, wood_old_rear, wood_painted |
| `booth.glb` | 5.00 × 11.19 × 3.10 | 8,160 | 1.1 MB | concrete, glass, interior, steel_weathered, wood_old, wood_painted |
| `lamp_pole.glb` | 1.34 × 5.33 × 1.25 | 2,600 | 0.2 MB | glass_insulator, light_bulb, reflector, steel_weathered, wood_old |
| `popcorn_bucket.glb` | 0.18 × 0.27 × 0.18 | 2,824 | 1.2 MB | paper, popcorn |
| `popcorn_kernel.glb` | 0.02 × 0.02 × 0.02 | 276 | 0.4 MB | popcorn |

**`screen.glb`** — authored in WORLD coordinates: put it at the world origin with no offset. The face panel (`screen_panel`,
dark weathered enamel, rounded chamfered rim) is exactly the slide's shape (22.00 × 12.67 m, r 0.43, centre (0, 12.34))
with its front at z = −0.20, so its rim catches the moon at the edges; seen from the hero camera it peeks ~2 cm below the
slide's bottom edge. Behind it: 14 creosoted 8×12 timber posts (rows at z −0.55 / −2.15, x = 0, ±3.6, ±7.2, ±10.8) on
concrete footings (top at y 3.0, ground y = 2.7) with steel saddles, side ties and diagonal braces, nailers, seven raked
buttress struts to footings at z = −8.0, two plank catwalks (decks at y 5.55 and 12.30) with galvanized pipe rails and a
missing board, steel-rod X-bracing with turnbuckles under the face (visible between the cars), a caged ladder on the
left flank (x −11.3, outside the face, seen from the camera) up to y 13.4, a sheet-metal top cap, and the painted-over
plywood back skin (board-and-batten, one replaced sheet) at z −2.4. **Build-time guard:** `screen_geo.check_front_clear`
(nothing at z > −0.15 inside the rounded face, vertices + polygon samples) and `check_sightline` (nothing in front of
z = 0 projects into the face from the hero camera); `screen_build.py` refuses to export on any violation.
Materials: `screen_panel`, `wood_old` + `steel_weathered` (the parts the camera sees: everything below y 6.5, the left
flank, the top rim; dense 2048/1024 atlases, ~15 mm texels), `wood_old_rear` + `steel_weathered_rear` (same look, hidden
parts, cheap atlases), `wood_painted` (back skin), `concrete`.

**`booth.glb`** — origin on the ground under the cabin centre; port faces +Z; node **`lens`** (empty) at the port centre
(0, 8.50, 1.10), 8.5 m above the origin. Aim the whole booth (yaw/pitch) so +Z points from the lens at the screen centre.
Six timber legs (four splayed under the cabin, two under the landing) on footings, girts and X-bracing; deck and a railed
landing on −X with a board door (Z-brace, strap hinges, pull); a wooden ladder leans on the landing from (−3.25, 0, 0).
Cabin: faded barn-red board-and-batten (`wood_painted`), corrugated tin shed roof (rusting galvanized, `steel_weathered`,
one dent), lamphouse vent stack, conduit down the front-right leg, a small side window on +X. Behind the port: a dark
projector with lens barrel and reels (`steel_weathered`), and an inward-facing `interior` box so the port reads as a dim
room. `glass` (BLEND 0.6, double-sided) panes in the port and the side window — hide the port pane if it fights the beam.

**`lamp_pole.glb`** — origin at the pole foot; ~5.3 m creosoted pole (`wood_old`) with a slight lean, conduit, old
disconnect box, step pegs, pole tag, an old crossarm on the −X face with two green glass insulators (`glass_insulator`, BLEND); a
galvanized gooseneck arm reaching +X ends in a dark-green enamel RLM shade
(`steel_weathered` outside, chipped/rusty; `reflector` white enamel inside) with a photocell on the bracket. Bulb mesh uses
**`light_bulb`** (emissive warm 1.0/0.62/0.30, strength 4 in Blender; drive it in code); node **`bulb`** (empty) at the
bulb centre (0.90, 4.38, 0). Rotate about Y so the arm points over the lot.

**`popcorn_bucket.glb`** — origin at the bottom centre; root `popcorn_bucket` → `bucket` (material `paper`: 16 red/white
stripes, a white band with POPCORN lettering, rolled rim, grease spots; double-sided so the inner wall shows) and
`popcorn` (material `popcorn`: a low dome heaped with 18 kernels). Ø 0.18 m top, 0.22 m wall, heap to ~0.27 m.
**`popcorn_kernel.glb`** — one popped kernel (~2 cm, 276 tris, material `popcorn`), origin at its lowest point; instance
it with random rotation and ±20 % scale for the spill.
<!-- SET:END -->

<!-- CREATURES:BEGIN -->
## CREATURES (moth, mouse, owl) — generator: `src/set/creatures.py`
Rebuild: `flock … python3 src/set/creatures.py [moth] [mouse] [owl]` (seconds). All face **+Z**, metres, no skinning:
every moving part is its own node with its pivot (node origin) at the hinge, so rotate nodes in code.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `moth.glb` | 0.05 × 0.01 × 0.03 | 744 | 0.1 MB | eye, wing, fur |
| `mouse.glb` | 0.04 × 0.05 × 0.19 | 2,610 | 2.5 MB | eye, skin, fur |
| `owl.glb` | 1.07 × 0.23 × 0.62 | 3,172 | 1.8 MB | beak, eye, feather |

**`moth.glb`** — `moth` → `body` (thorax/abdomen, head, antennae, six tucked legs; `fur`) → `eyes`, `wing_L` (+X side),
`wing_R`. Wing pivots at the roots (±0.0024, 0.0016, 0.0035); rest pose is spread flat with a slight dihedral, so flap by
rotating `wing_L` about its local Z by +θ and `wing_R` by −θ (θ ≈ −30°…+70°, 15-25 Hz looks right for a moth). Forewing
over hindwing in one mesh per side; material `wing` (pale dusty buff, wavy antemedial/postmedial lines, discal spot;
double-sided). Span 5 cm.
**`mouse.glb`** — deer mouse (brown back, white belly and feet, bicoloured tail), ~19 cm nose to tail tip, origin on the ground under the body. Hierarchy: `mouse` → `body`
(pivot (0, 0.02, 0)) → `head` (pivot at the neck (0, 0.023, 0.028); pitch it for nibbling) → `head_skin` (ears, nose),
`eyes`; `tail` (pivot at the base (0, 0.019, −0.044); yaw/pitch it, it curves to the ground); `leg_FL`, `leg_FR`,
`leg_HL`, `leg_HR` (pivots at shoulders/hips; swing about local X for the scurry); `paws` (pivot at the chest
(0, 0.016, 0.028); two little hands tucked under the chin) → `kernel_socket` (empty at the grip point, parent a kernel
there while it nibbles). When it sits up, pitch `body` back ~35-45° about X and raise `paws` toward the mouth. Materials
`fur` (1024 agouti brown back / buff belly, normal-mapped hair flow), `skin` (ears, nose, tail, feet), `eye`.
**`owl.glb`** — great horned owl in flight, span ~1.07 m, origin at the body centre. `owl` → `body` (round head with ear
tufts, barred breast, scalloped tail fan, tucked feet; `feather`) → `beak`, `eyes`, `wing_L` (+X), `wing_R`, pivots at the
shoulders (±0.062, 0.035, 0.05). Wings are thick cambered arm/hand grids with a scalloped trailing edge and six slotted,
splayed primaries; flap by rotating about local Z (+θ left, −θ right; owls flap slowly, ~2-3 Hz, or glide). Built for the
outline against the moonlit sky; `feather` is double-sided.
<!-- CREATURES:END -->

## CARS (cars thread, 2026-10-22)
Generators: `src/cars/` — `car90.py` (shared 1990s car generator: implicit body field → marching cubes → Blender decimate →
adaptive edge refinement for thin features → exact level-set cuts → labelled insets → details → GLB → `gltfpack -cc -kn -km`),
one config file per car (`saab9000.py` = the hero, with `saab9000_trace.py` / `saab9000_rear.py` / `saab9000_badges.py`, `wagon.py`, `sedan_a.py`, `suv.py`, `sedan_b.py`), `wheels90.py` (wheel covers / steel /
alloy / `custom`), `wheels_saab.py` (the hero's 3-spoke Super Aero alloy), `speaker_post.py`; `hero.py` is the retired red sedan
(now writes `car_hero_old.glb`, kept for comparison); shared code adapted from `../desert/src/cars/` (`carlib.py`, `body.py`, `surfops.py`, `details.py`,
`wheels.py`, `interior.py`, `blendout.py`, `carbuild.py`). Rebuild everything under the lock: `sh src/cars/build_all.sh`
(~30 s per car; gltfpack is found via `$GLTFPACK`, default the npm copy in the session scratchpad, else on PATH; without it the
GLB is written uncompressed). `pickup_wip.py` is an unfinished compact pickup (not exported to assets). All geometry and textures are
procedural and original: no logos, plates are blank (border + plain colour band, no characters). The only lettering is the
hero's invented-make chrome "SOB" wordmark on the hatch (DejaVu Sans Bold capitals, see CREDITS.md).

- Frame (all cars): nose toward **+Z**, +Y up, origin at the footprint centre on the ground, tyres touch y = 0. The car's
  LEFT (driver) side is **+X**. In the preview harness the scene's view of the hero (camera behind-left, ~14.7 m, eye at
  wheel-hub height) is `yaw≈122` (yaw −70 shows the right-hand side).
- Nodes: root (`car_hero` etc.) → `body`, `wheel_FL`, `wheel_FR`, `wheel_RL`, `wheel_RR` (FL/RL on +X; origin = hub centre,
  spin about local X if ever needed). Hero only: empties `bucket_anchor`, `ledge_drop` (children of the root).
- Materials (by role): `paint`, `glass` (BLEND α 0.84, near-black, roughness 0.03), `chrome`, `trim_black` (window surrounds,
  gaps, grille, rub strips, wheel wells, underbody), `rubber` (tyres: normal + roughness maps), `rim` (wheel covers /
  alloys / steel wheels), `light_front` (headlamp reflectors + reverse lamps; lights OFF, no emission), `light_rear` (red
  lenses, no emission), `light_marker` (amber corner/side markers, no emission), `light_cover` (clear headlamp cover,
  BLEND α 0.16), `interior` (cabin shell, seats, dash, steering wheel), `plate` (blank textured plate). COLOR_0 carries
  baked occlusion on paint / trim / tyres / rims / interior (darker low on the body, in arches, at the cowl): keep vertex
  colours on. `paint` and `glass` are single materials per car (safe to swap for a clearcoat/physical material).
- Background cars: wheels ~3.4–3.8k each; underside and wheel-well faces are decimated harder (unseen). Inner cabin shell is cut away at window height so you can see through the cabin to the far glass.

| asset | look | size L × W × H (m) | tris total (body / each wheel) | file |
|---|---|---|---|---|
| `car_hero.glb` | silver 1994–98 Saab 9000 Aero 5-door (CS body), v2 (traced from the director's year-correct photos): low wide nose with slim headlamps + amber wrap corners + chrome-ringed grille, black rub strip capping the bumpers and running along the doors, tall glasshouse (belt ~0.92 m rising to ~1.0 m at the quarter light), body-colour B-pillar, fixed quarter light in the rear door, body-colour C-pillar with black-edged hatch glass, full-width tail band (outer lamps smoked/amber over red, wrapping the corner onto the quarter panel as a teardrop that slopes down to a forward tip; smoked/red centre panel; reverse lens right of centre), leaning hatch face with rounded corners, black Aero blade spoiler on the hatch, roof-edge third brake pod, Aero skirts/valance/fog lamps, dark matte arch liners, 3-spoke Super Aero 16" alloys (broad dished face, three curved teardrop slots sweeping one way, flat plain cap), 205/55R16. Chrome "SOB" wordmark upper left of the hatch; plain bonnet cap; blank plates front and rear | 4.78 × 1.99 (mirrors; 1.78 body) × 1.42, wb 2.672, track 1.534 | 159,371 rendered (161,127 raw: body 121,287, each wheel 9,960) | 1.00 MB |
| `car_wagon.glb` | forest-green full-size wagon, chrome grille, roof rack, upright tailgate, vertical tail lamps | 5.33 × 2.07 (mirrors) × 1.53 (roof rack), wb 2.94 | ≈58,800 (60,181 before gltfpack dedup) | 0.48 MB |
| `car_sedan_a.glb` | mustard-gold compact notchback, chrome rub strip, bottle-cap wheel covers | 4.55 × 1.81 × 1.37, wb 2.62 | 49,633 | 0.41 MB |
| `car_suv.glb` | cream/tan boxy 4-door SUV, black lower two-tone + arch lips, roof rack, 5-spoke alloys | 4.82 × 2.07 (mirrors) × 1.81, wb 2.84 | 59,947 | 0.50 MB |
| `car_sedan_b.glb` | maroon full-size sedan, formal roof, chrome waterfall grille + side moulding, fine-slot covers | 5.21 × 1.95 × 1.43, wb 2.98 | 59,714 | 0.49 MB |
| `car_saab900.glb` | Cherry Red 1987 classic Saab 900 Turbo SPG three-door hatchback (the "Drive My Car" car): wraparound windscreen, tall glasshouse, clamshell bonnet, fastback hatch + lip spoiler, black bumpers/rub strips, body-colour SPG air dam/skirts/valance, sunroof outline, three-spoke 15" alloys; solid (non-metallic) paint. Generator `src/cars/saab900.py` + rims `src/cars/wheels_saab900.py`. Replaces `car_suv.glb` mid-row | 4.70 × 1.84 (mirrors; 1.69 body) × 1.42, wb 2.52 | 58,212 (body ~44k, each wheel ~3.7k) | 0.47 MB |
| `speaker_post.glb` | steel pipe on a concrete footing, junction head with two hooks, two aluminium window speakers (louvred grille, volume knob, window lip), coiled cords | 0.37 × 0.19 footprint, 1.14 tall | 1,131 | 11 KB |

- Hero v2.2 (Saab 9000 Aero, `src/cars/saab9000.py`, 2026-10-22; v2.1 kept as `assets/car_hero_v21.glb`, v2 as `assets/car_hero_v2.glb`, v1 as `assets/car_hero_v1.glb`, the old red sedan as
  `assets/car_hero_old.glb`). Side silhouette, beltline, side glass, pillars, shut lines, arches, rub strips and nose/tail
  profiles are traced from the director's straight driver-side photo (`saab9000_trace.py`: pixel data + the solved camera,
  437.9 px/m at the wheel plane, perspective-corrected per curve) and fed to `car90.py` as exact curves and masks. Rear lamps,
  plate recess, spoiler and brake pod: `saab9000_rear.py`; wordmark + front blanks: `saab9000_badges.py`; wheel:
  `wheels_saab.py` (each a separate module so it can be redone alone). Real-car dimensions 4761 × 1778 × 1415 mm, wb 2672,
  track 1534/1504. **Axles moved in v2**: glTF z = +1.361 (front) / −1.311 (rear) (front overhang 1.020, rear 1.069 per the
  trace; v1 had +1.455 / −1.217), hubs at x = ±0.767, y = 0.316. Paint `paint` (0.462, 0.466, 0.472) linear, metallic 0.75,
  roughness 0.25. Rim `rim` (0.58, 0.59, 0.60), metallic 0.55, roughness 0.34 (painted silver alloy; fully metallic read white
  in daylight). Arch liners use `interior` (matte) with outboard shading normals: the glossy `trim_black` mirrored the sky at
  grazing angles, which was the pale-crescent problem. Spoiler, brake pod, wordmark, bonnet cap and front plate are part of
  `body`. Fuel flap on the passenger (−X) rear quarter, centred 0.216 m behind the rear axle at y 0.806 (measured on 04); exhaust tip on the driver (+X) side; amber repeater ahead of the
  front door; a red US-spec reflector low on the rear bumper sides. All lamps unlit (no emission).
- Hero v2.1 changes (director review): tail-lamp corner wrap rebuilt (`saab9000_rear.py` `WRAP_EDGE`, an offset from the
  tail profile: level bottom edge at z 0.815, front edge sweeping down to a tip ~0.13 m forward, smoked/red split carried
  through); rear bumper below the rub strip shortened (valance turns under from z ~0.34), hatch face leans forward ~4.5 cm
  with rounder plan corners (`saab9000.py` `LR`, `ZBOT`, `tail_pow`, `k_tail`); wheel slots are curved teardrops
  (`wheels_saab.py` `_slot_discs`: disc chain tangent to r 0.164, full depth to r ~0.102, tapering over 66 deg).
- Hero v2.2 (director review of the lamp wrap): measured on 04 against the rim (977 px/m at the wheel face), the side
  portion of each tail lamp is ~0.145 m long along its level bottom edge and ~0.16 m tall at the corner; the plan corner
  of the tail is now tighter (`tail_corner` 0.10, `tail_pow` 3.2) so the lens sits on the flat quarter instead of the curve,
  and `WRAP_EDGE` puts the tip ~0.25 m forward of the centre-line tail profile. Board camera for 04: harness
  `yaw=-90&dist=10.84&h=0.706&ty=0.706&tz=-1.349&fov=10` at 1024 × 858 (level, ~10 m from the wheel face).
- Hero, open window: the driver's (left, +X) front door glass is removed; the opening has a 7.8 cm deep black channel all
  round, whose bottom face is the door's inner window ledge (top at y ≈ 0.935), with a black felt/rubber strip along its
  outer and inner lips. Through it: driver's seat, steering wheel, dash (all `interior`, dim). Empties (glTF coordinates,
  metres, relative to the car root):
  - `bucket_anchor` = (0.796, 0.935, 0.310): top of the ledge, mid-window, mid-thickness. Put the bucket's base here; the
    ledge is ~7.8 cm deep, so let the bucket overhang outward (+X) a little.
  - `ledge_drop` = (1.155, 0.0, 0.260): on the ground 0.35 m outside the door, just behind mid-window (where it lands).
  - The ledge runs along the window bottom from z ≈ −0.21 (B-pillar) to z ≈ 0.74 (front of the window).
- Shared-generator hooks added for the hero (other cars unchanged by default): `C['extra_cuts']` (config-specific level-set
  cuts, used with `extra_labels` / `extra_rules`), `C['mirror_mats']`, `C['clad_cut']=False` (skip the arch-lip cut when
  there is no lip; with no lip its domain edge inside the wells made the refinement run away), wheel type `custom`
  (`st['mesh_fn'](target)`). v2 adds (all optional): `dlo_mask`, `fdoor_mask`, `rdoor_mask` (traced (s, z) outlines),
  `lid_fn`, `rear_lamp_fns`, `mirror_at`, `handle_size` + `(s, z)` handle tuples, callable rub half-height, `rub_nz`,
  `ledge_z`, `well_offsets`, `rim_metal`, and a per-label `nfn` shading-normal override in `surfops.build_labelled`. Cap edge length with `max_edge` (0.12 on the hero) so long decimated window triangles cannot
  jump the thin B-pillar / rub-strip bands.
- Speaker post: root `speaker_post_root` → mesh `speaker_post`; origin at the base centre on the ground; speakers hang on
  ±X (glTF) of the pipe at y ≈ 0.97–1.09, grilles facing ±X. Materials `steel_weathered`, `aluminium`, `concrete`,
  `trim_black`, `rubber` (COLOR_0 occlusion). Place one post between each pair of cars.
- Files are meshopt-compressed and quantized (gltfpack 0.22 `-cc -kn -km`, like the desert assets): load with
  `GLTFLoader.setMeshoptDecoder(MeshoptDecoder)`. Named nodes keep their transforms; each mesh sits on an unnamed child
  node carrying the dequantization transform, so address parts by the named parent (`body`, `wheel_FL`, ...).
