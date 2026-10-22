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

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `pine_a.glb` | 11.51 × 29.68 × 11.41 | 56,738 | 5.2 MB | bark, needles |
| `pine_a_lod1.glb` | 11.70 × 30.24 × 11.69 | 5,798 | 0.8 MB | bark, needles |
| `pine_b.glb` | 4.34 × 23.26 × 4.45 | 46,222 | 5.0 MB | bark, needles |
| `pine_b_lod1.glb` | 4.34 × 23.37 × 4.56 | 5,800 | 0.9 MB | bark, needles |
| `pine_c.glb` | 10.84 × 32.57 × 10.43 | 56,900 | 5.3 MB | bark, needles |
| `pine_c_lod1.glb` | 11.21 × 33.45 × 10.91 | 5,800 | 0.8 MB | bark, needles |
| `rock_a.glb` | 2.40 × 1.29 × 1.83 | 2,998 | 0.6 MB | rock |
| `rock_b.glb` | 1.24 × 1.08 × 1.08 | 1,164 | 0.6 MB | rock |
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

**Rocks.** `rock_a` (2.4 m rounded block), `rock_b` (1.2 m faceted): grey Rocky Mountain granite with biotite speckle,
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
| `screen.glb` | 23.19 × 16.17 × 8.15 | 13,332 | 2.9 MB | concrete, screen_panel, steel_weathered, wood_old, wood_painted |
| `booth.glb` | 5.00 × 11.19 × 3.10 | 8,160 | 1.1 MB | concrete, glass, interior, steel_weathered, wood_old, wood_painted |
| `lamp_pole.glb` | 1.33 × 5.33 × 0.57 | 2,068 | 0.2 MB | light_bulb, reflector, steel_weathered, wood_old |
| `popcorn_bucket.glb` | 0.18 × 0.27 × 0.18 | 2,824 | 1.3 MB | paper, popcorn |
| `popcorn_kernel.glb` | 0.02 × 0.02 × 0.02 | 292 | 0.6 MB | popcorn |

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
Materials: `screen_panel`, `wood_old`, `wood_painted`, `steel_weathered`, `concrete`.

**`booth.glb`** — origin on the ground under the cabin centre; port faces +Z; node **`lens`** (empty) at the port centre
(0, 8.50, 1.10), 8.5 m above the origin. Aim the whole booth (yaw/pitch) so +Z points from the lens at the screen centre.
Six timber legs (four splayed under the cabin, two under the landing) on footings, girts and X-bracing; deck and a railed
landing on −X with a board door (Z-brace, strap hinges, pull); a wooden ladder leans on the landing from (−3.25, 0, 0).
Cabin: faded barn-red board-and-batten (`wood_painted`), corrugated tin shed roof (rusting galvanized, `steel_weathered`,
one dent), lamphouse vent stack, conduit down the front-right leg, a small side window on +X. Behind the port: a dark
projector with lens barrel and reels (`steel_weathered`), and an inward-facing `interior` box so the port reads as a dim
room. `glass` (BLEND 0.6, double-sided) panes in the port and the side window — hide the port pane if it fights the beam.

**`lamp_pole.glb`** — origin at the pole foot; ~5.3 m creosoted pole (`wood_old`) with a slight lean, conduit, old
disconnect box, step pegs, pole tag; a galvanized gooseneck arm reaching +X ends in a dark-green enamel RLM shade
(`steel_weathered` outside, chipped/rusty; `reflector` white enamel inside) with a photocell on the bracket. Bulb mesh uses
**`light_bulb`** (emissive warm 1.0/0.62/0.30, strength 4 in Blender; drive it in code); node **`bulb`** (empty) at the
bulb centre (0.95, 4.38, 0). Rotate about Y so the arm points over the lot.

**`popcorn_bucket.glb`** — origin at the bottom centre; root `popcorn_bucket` → `bucket` (material `paper`: 16 red/white
stripes, a white band with POPCORN lettering, rolled rim, grease spots; double-sided so the inner wall shows) and
`popcorn` (material `popcorn`: a low dome heaped with 18 kernels). Ø 0.18 m top, 0.22 m wall, heap to ~0.27 m.
**`popcorn_kernel.glb`** — one popped kernel (~2 cm, 292 tris, material `popcorn`), origin at its lowest point; instance
it with random rotation and ±20 % scale for the spill.
<!-- SET:END -->

<!-- CREATURES:BEGIN -->
## CREATURES (moth, mouse, owl) — generator: `src/set/creatures.py`
Rebuild: `flock … python3 src/set/creatures.py [moth] [mouse] [owl]` (seconds). All face **+Z**, metres, no skinning:
every moving part is its own node with its pivot (node origin) at the hinge, so rotate nodes in code.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
| `moth.glb` | 0.05 × 0.01 × 0.03 | 744 | 0.1 MB | eye, wing, fur |
| `mouse.glb` | 0.04 × 0.04 × 0.21 | 2,578 | 2.5 MB | eye, skin, fur |
| `owl.glb` | 1.21 × 0.25 × 0.63 | 3,172 | 1.8 MB | beak, eye, feather |

**`moth.glb`** — `moth` → `body` (thorax/abdomen, head, antennae, six tucked legs; `fur`) → `eyes`, `wing_L` (+X side),
`wing_R`. Wing pivots at the roots (±0.0024, 0.0016, 0.0035); rest pose is spread flat with a slight dihedral, so flap by
rotating `wing_L` about its local Z by +θ and `wing_R` by −θ (θ ≈ −30°…+70°, 15-25 Hz looks right for a moth). Forewing
over hindwing in one mesh per side; material `wing` (pale dusty buff, wavy antemedial/postmedial lines, discal spot;
double-sided). Span 5 cm.
**`mouse.glb`** — field mouse, ~21 cm nose to tail tip, origin on the ground under the body. Hierarchy: `mouse` → `body`
(pivot (0, 0.02, 0)) → `head` (pivot at the neck (0, 0.023, 0.028); pitch it for nibbling) → `head_skin` (ears, nose),
`eyes`; `tail` (pivot at the base (0, 0.019, −0.044); yaw/pitch it, it curves to the ground); `leg_FL`, `leg_FR`,
`leg_HL`, `leg_HR` (pivots at shoulders/hips; swing about local X for the scurry); `paws` (pivot at the chest
(0, 0.016, 0.028); two little hands tucked under the chin) → `kernel_socket` (empty at the grip point, parent a kernel
there while it nibbles). When it sits up, pitch `body` back ~35-45° about X and raise `paws` toward the mouth. Materials
`fur` (1024 agouti brown back / buff belly, normal-mapped hair flow), `skin` (ears, nose, tail, feet), `eye`.
**`owl.glb`** — great horned owl in flight, span ~1.2 m, origin at the body centre. `owl` → `body` (round head with ear
tufts, barred breast, scalloped tail fan, tucked feet; `feather`) → `beak`, `eyes`, `wing_L` (+X), `wing_R`, pivots at the
shoulders (±0.075, 0.03, 0.05). Wings are thick cambered arm/hand grids with a scalloped trailing edge and six slotted,
splayed primaries; flap by rotating about local Z (+θ left, −θ right; owls flap slowly, ~2-3 Hz, or glide). Built for the
outline against the moonlit sky; `feather` is double-sided.
<!-- CREATURES:END -->
