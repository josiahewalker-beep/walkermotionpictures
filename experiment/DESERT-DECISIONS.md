# Desert billboard (hero slide) — decisions

- 10-21 Josiah: framing A (low, near-lane edge, 22° off the face, ≈35 mm) with the Golden hour look.
- 10-21 Josiah: billboard should fill more of the frame so it reads. Chosen render: I1 — slide spans ~56% of frame width,
  board clearance lowered 3.8 m → 2.8 m (closer to the reference's pole height), road centre 8 m out from camera so the
  double yellow stays in the bottom-left. Parameters in `desert.js` → `HERO_SHOT`.
- Rejected for this: a longer lens (≈50 mm) from the same spot — bigger slide, but the road shrinks to a sliver.
- Open: phone handling (vertical sign vs skip), render-in/out style (next audition), control bar over the pole.
- 10-21 Josiah: atmosphere and sequence after landing (all in `desert.js`):
  - soft haze for depth: exponential, thicker near the ground, warmer toward the sun; the slide stays clear, each band behind it fades further
  - t = 2 s red modern sports car, left to right (near lane, 30 m/s)
  - t = 10 s blue modern minivan, right to left (far lane, 24 m/s)
  - t = 13 s tumbleweed rolls and bounces left to right ~3.5 m behind a composed first row of Joshua trees (20 m out); ~8 s across the frame
  - stars fade in over ~20 s: sparse, faint, each twinkling at its own rate
  - after the sequence: an occasional car every 14–24 s, alternating direction
- Technical: vehicles render on a second canvas above the slide (the slide is HTML over the 3D canvas), with an invisible twin in the
  main scene that still casts the shadow. Only valid while nothing stands between the camera and the road.
- 10-21 Josiah: the site holds on the bird's-eye view (no auto-landing). Clicking the first slide flies a slower curved approach (6.5 s)
  into the billboard frame; on landing the camera locks (no drag-look) and the sequence plays. Next/Back un-builds the world.
- 10-21 Josiah: the world should bloom out of the slide being approached and only fill the screen on landing. Three variants built
  (screen-space, desert on its own canvas between the grid and the slides): #desert-a frame bleed, #desert-b light bloom, #desert-c tile resolve.
  Superseded: the earlier world-space build styles (grid-to-ground, streaming, draw distance) remain in code behind uRev but are unused.
- 10-21 Josiah: the screen-space bloom didn't read as coming out of the 3D grid. Rebuilt in world space, in the site's own scene so it sits
  in depth with the lattice: a front travels out from the billboard's foot through the grid's own 160-unit cells and reaches the horizon
  exactly at landing; the lattice ripples/glows at the front and hands over to the world behind it. Variants: #desert-a rise out of the
  fabric (crest wave, surfaces lift from the floor), #desert-b the grid drapes (lines settle onto surfaces, then fill), #desert-c cell by
  cell (floor cells switch on outlined, props grow up in their cells). The intro no longer auto-flies to the first slide in desert mode.
- 10-21 Josiah (deck comment): build C — the sky fills in by cells too: 3° cells from the horizon up, outlined in the grid's blue, finishing at landing.
- 10-21 Josiah (overnight brief): photoreal pass — real-looking cars with glass reflections, Joshua trees with shaggy dead-leaf skirts and
  spike leaves, textured asphalt with blemished paint, a billboard weathered ~20 years. Morning deliverable is the whole flow:
  bird's-eye → click → cell build → land/lock → sequence → Next → cell un-build.
- Technical (overnight): three asset threads (cars, flora, set) build original geometry/textures in Blender Python to desert/ASSETS.md;
  the integrator swaps blockouts for GLBs as they land (instanced; near/far LOD for trees). Pipeline: ACES, sky-based environment
  light/reflections, N8AO ambient occlusion, light bloom, print grade + grain, used only once landed so the grid's look is untouched.
- Technical: vehicles moved back into the main scene (the separate canvas is gone) so paint and glass reflect the scene's light and
  shadows are real; the sightline to the tumbleweed is kept clear of tall shrubs and boulders.
- Technical: the near lane is only ~10 m on screen from the landing frame, so the red car crosses in under a second; slowed to 26 m/s
  (~58 mph) so the eye gets a beat on it. Paint is a clearcoat physical material, base darkened so grazing sky reflections stay red.
- Technical: asphalt carries a road-scale wear map (cracks, tar sealant that reads glossier, patches, wheel paths) over a quiet 4 m tile.
