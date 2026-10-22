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
