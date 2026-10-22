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
- Lot: ground rises from y = 0 at z = 40 (where the camera stands, low at the back) to y = 2.7 at z = 10, flat beyond;
  two dirt mounds lift two cars (see below). Gravel/dirt, tyre ruts, pine needles, speaker posts.
- Camera (fixed): (-12.54, 2.16, 40.45) looking at (1.16, 10.74, 3.86), vertical FOV 26.5°.
- Cars, facing the screen (nose toward -Z), x, z, yaw (rad, + turns the nose toward -X):
  - hero red car (-4.08, 28.45, 0.40) on a 1.1 m mound. The camera sees its whole left (driver's) side: driver's window
    rolled down, popcorn bucket on the window ledge, both wheels, door seam and handle.
  - forest-green wagon/SUV (-11.93, 18.80, 0.10); mustard sedan (-8.27, 10.07, -0.05);
    cream SUV/wagon (-2.57, 9.31, 0.05); wood-brown sedan (-1.43, 17.28, 0.12) on a 0.6 m mound.
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
