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
| `pine_a.glb` | 11.51 × 29.67 × 11.36 | 42,818 | 4.3 MB | bark, needles |
| `pine_a_lod1.glb` | 11.85 × 30.25 × 11.67 | 5,798 | 0.8 MB | bark, needles |
| `pine_b.glb` | 4.31 × 23.26 × 4.44 | 34,778 | 4.1 MB | bark, needles |
| `pine_b_lod1.glb` | 4.29 × 23.36 × 4.51 | 5,800 | 0.9 MB | bark, needles |
| `pine_c.glb` | 10.84 × 32.57 × 10.43 | 56,900 | 5.4 MB | bark, needles |
| `pine_c_lod1.glb` | 11.09 × 33.69 × 10.98 | 5,800 | 0.8 MB | bark, needles |
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
`pine_c` Douglas fir, 33 m: dense dark-green cone from ~2 m to a pointed leader, ~10 m wide at the base, drooping
branches with upturned tips.
- `bark`: tiling bark (1024 albedo + normal; u around the trunk, v up; ponderosa tile 1.2 × 1.6 m), roughness 0.92,
  single-sided. Branches and stubs are in the same material. The trunk is lightly darkened at the foot.
- `needles`: RGBA atlas (2 × 2 variants of the species' tuft/spray), alphaMode MASK, cutoff 0.4, double-sided,
  roughness 0.62. Pines: crossed card pairs along the twig direction; fir: pairs of flat sprays rolled ±20-45°.
  Visible foliage albedo ≈ linear (0.05, 0.09, 0.04) ponderosa/lodgepole, (0.035, 0.07, 0.045) fir, after the AO:
  dark green that turns olive-brown under the amber key, as intended. Card shading normals are bent outward from the
  trunk axis and up, so the crowns light as volumes.
- `_lod1` (≤ 6k tris, 512 px textures): same trunk axis, ponderosa keeps its 45 thickest limbs; the hero's tufts are
  k-means clustered into ~1,200-1,400 larger crossed cards with each cluster's mean colour → the same silhouette and
  colour from ~60 m on. Switch at 50-70 m (the whole ring at 70-200 m can be LOD1; flank trees at 25-60 m hero).
- Placement: scale 0.8-1.15 and rotate freely about Y; tilt ≤ 2°. Mix roughly 45 % ponderosa, 30 % fir, 25 %
  lodgepole for a Front-Range montane look; lodgepoles look best in small groups.
- Alpha-tested foliage thins in the mip chain at distance; the atlases' alpha is pre-thickened. If the far ring looks
  sparse, set `material.alphaToCoverage = true` (with MSAA) or lower `alphaTest` to 0.3 on the LOD1 material.
- Moon backlight: the needle cards are single-layer and opaque; a cheap rim/translucency term (e.g. add
  `0.25 * moonColor * pow(saturate(dot(-viewDir, moonDir)), 4)` to emissive on `needles`) makes the tuft edges glow
  against the sky the way Josiah described.

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
