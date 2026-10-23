# Drive-in world (second slide) — decisions

- 10-22 Josiah: the second slide (Work, "A finance product, sold as a story.") becomes a drive-in theatre in a mountain
  town at night. Feel: cozy and intimate, warm 80s (greens and browns of the pines, amber lot light), pine needles in
  the air. Cars are from the 90s.
- 10-22 Josiah (framing, via the 3D camera room): camera at (-12.54, 2.16, 40.45) looking at (1.16, 10.74, 3.86), vertical
  FOV 26.5° (≈ 50 mm); the screen fills the upper left like his sketch, moon upper right, five cars across the bottom,
  the red car on the right close enough to see its driver's door, window and both wheels.
- 10-22 Josiah: the screen is the slide exactly, with the slide's rounded corners; no border.
- 10-22 Josiah: the projector beam comes from the right, narrow at the booth and widening to the screen; it flickers
  gently and never washes over the screen. Dust is very subtle. A moth flutters in the beam, leaves, disappears for a
  few seconds, comes back.
- 10-22 Josiah: the red car's driver's window is down with a popcorn bucket on the ledge; at 3 s it falls and spills.
  At 10 s a mouse/rat scurries in from the left to the popcorn and sits nibbling. Then an owl flies across the frame
  through the beam as a silhouette (Claude: ~16 s, right to left). Sizes as he drew them (mouse ≈ rat, owl ≈ 1 m span,
  moth slightly larger than life, kept in the nearer part of the beam).
- 10-22 Josiah: all cars have the little speakers on posts.
- 10-22 Josiah: playing the video fills the projector screen; the beam keeps flickering.
- 10-22 Josiah: keep the warm light from behind the camera, the lamp and the projector; add soft moon backlight on the
  screen's edges, the pines and the crest of the hills.
- Technical: the lot rises from the camera toward the screen (≈ 2.7 m over 30 m) and two cars sit on dirt mounds, because
  the camera tilts up 12° and cars on flat ground would be out of frame (Josiah accepted in round 3).
- Technical: world scale 1120 px of slide = 22 m of screen (50.9 units per metre). Like the desert, the world and camera are
  fixed relative to the slide and only the lens follows the window shape; the slide keeps its reference layout
  (1120 × 645 px) in desert mode, guarded.
- Technical: assets in `drivein/` to `drivein/ASSETS.md`; three asset threads (cars; pines and ground; screen, booth,
  props and creatures). The integrator is `drivein.js`, sharing the page hookup with the desert.
- 10-22 Josiah: the dirt lot should feel lived in, with tyre marks and tracks. A truly flat lot was tried and hid the cars
  under the camera's upward tilt; Josiah chose to keep round 3's ground (gentle rise, hidden lifts) and add the tracks: a
  90 m overlay drawn in code (worn lanes, the ruts of every car into its spot, old faint arcs) over the fine dirt tile.
- 10-22 Josiah: no telephone pole / streetlamp in frame. The pole is removed; its warm light stays, moved just off frame left.
- 10-22 Josiah: the hero car (window down, popcorn bucket) is a silver 1994–98 Saab 9000 Aero 5-door hatchback with the Aero body kit and the Super Aero 3-spoke 16" wheels. Built procedurally from reference; no badges or wordmarks.
- 10-22 Josiah: the SUV in the middle of the row becomes the red Saab from Drive My Car: a classic Saab 900 SPG (the top trim of the classic 900), 1987 Cherry Red three-door hatchback with the SPG kit and three-spoke wheels. File: assets/car_saab900.glb.
- 10-22 Josiah: the hero car's badging uses an invented make, "SOB" (a nod, not a copy): chrome wordmark on the hatch in plain all-caps block letters, not Saab's lettering. No real Saab badges, wordmarks, model scripts or griffin; bonnet roundel, front plate and wheel caps are blank.
- 10-22 Josiah (via the render markup page): Saab 9000 Aero — keep the v2 wheel (D-shaped slots; the correct shape), tail lamps as in v2.2 ("perfect"); rear quarter/C-pillar must be one smooth flat sweep with no crease; the dark hatch-glass band shows from the side.
- 10-22 Josiah: Saab 9000 Aero v2.5 approved ("perfect"): traced from his 1995 Aero photo set, v2 wheel, v2.2 tail corner and lamps, smooth upper rear quarter, hatch-glass band, spoiler seated 1.2 cm past the tail.
- 10-22 Josiah: lamp pole removed from frame; its warm light kept off frame left.
- Technical (overnight 10-22/23): the hero Saab's paint is cooled and less metallic in the scene so it reads silver under the
  amber stand light; the moth's wings face the camera (the model's wings lie flat and showed only their edge) and it glows
  in the beam; material clones keep the build/reveal shader hook (pines previously floated outside the build); models
  compressed with meshopt and right-sized textures (~16 MB loaded, was ~40 MB); red 900 SPG v2 traced from published
  dimensions (no photos available). Shipped to /experiment 10-23; revert point: branch `pre-drivein-2026-10-23`.
