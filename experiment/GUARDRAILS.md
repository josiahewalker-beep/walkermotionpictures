# Guardrails: the grid and the desert billboard

Josiah confirmed both pages working on 2026-10-22 (his laptop: 1728 × 1117, Retina 2×). These are the rules that keep
them that way, and how to get back to this state if something breaks. Read this before touching the grid, the canvas,
the camera, the card CSS or the desert hookup on either page.

## Known-good versions (git tags)
- `good-grid-2026-10-22` — the main site and /experiment, both confirmed by Josiah.
- Revert a single file to it: `git checkout good-grid-2026-10-22 -- index.html` (or `experiment/index.html`,
  `experiment/desert.js`), then commit and push. Don't reset the branch; other sessions push to main.

## The rules

1. **The grid canvas shows at exactly the window size.** `#gl { width:100%; height:100%; display:block; }` in both
   `index.html` and `experiment/index.html`. Without it, `renderer.setSize(w, h, false)` leaves the canvas at its pixel-buffer
   size; on a 2× screen it shows at twice the window, only its top-left quarter is visible, and the grid sits crooked and
   off-centre under the cards (main-site fix d29f364; /experiment c63a9c2). /experiment also has a runtime guard in
   `resize()` that forces the size and logs `[guard] grid canvas was …` if the rule ever goes missing.
2. **The desert is fixed in the world, never fitted to the window.** The world and the landing camera are laid out once at
   16:9 (`REF_ASPECT`, the approved golden-hour frame, `HERO_SHOT`). A window of another shape only changes the lens
   (`heroFov`). Never compute camera position, road, trees or the tumbleweed path from `innerWidth / innerHeight`.
3. **The intro slide is the billboard's face: exactly 1180 × 462 px in desert mode.** `billboard.glb` is built around it
   (10.93 × 4.28 m at 108 units per metre). The `html.desert-on` CSS keeps the slide at its reference layout on every
   window (no narrow or short-screen variants). If the slide's size or copy changes, the page guard turns the desert off
   (`[guard] intro slide is …`) rather than show a misfitting billboard; then rebuild the billboard face to the new size
   (`desert/src/set/`) and update `BILLBOARD_FACE` in `desert.js`.
4. **Phones and upright screens skip the desert** for now and land on the plain slide (Josiah 10-22).

## The check (run before every push that touches these files)
```
cd <repo root> && python3 -m http.server 8765 &
python3 experiment/qa/grid_check.py
```
About a minute; no landing render. Main site and /experiment at 1000×524@2×, 1728×1117@2×, 1440×900, 1920×1080,
2560×1080 and 390×844@3×: canvas = window, bird's-eye centred, intro slide = billboard face. Always test at 2× as well as 1×;
the crooked grid never shows at 1×.
