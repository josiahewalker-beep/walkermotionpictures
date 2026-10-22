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
