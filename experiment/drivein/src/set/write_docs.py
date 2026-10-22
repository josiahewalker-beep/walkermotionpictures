"""Regenerate the SET and CREATURES sections of drivein/ASSETS.md from the GLBs (tris, size, nodes, materials).
python3 src/set/write_docs.py   (light; no lock needed)"""
import json, os, struct, re
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


def glb_info(path):
    b = open(path, 'rb').read()
    ln = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + ln])
    tris = 0
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    # world bounds via node transforms (translation only + rotation/scale are identity in these files)
    def walk(ni, off):
        nonlocal tris, lo, hi
        n = j['nodes'][ni]
        t = off + np.array(n.get('translation', [0, 0, 0]))
        if 'mesh' in n:
            for p in j['meshes'][n['mesh']]['primitives']:
                acc = j['accessors'][p['indices']] if 'indices' in p else j['accessors'][p['attributes']['POSITION']]
                tris += acc['count'] // 3
                pa = j['accessors'][p['attributes']['POSITION']]
                lo = np.minimum(lo, t + np.array(pa['min'])); hi = np.maximum(hi, t + np.array(pa['max']))
        for c in n.get('children', []):
            walk(c, t)
    for ni in j['scenes'][0]['nodes']:
        walk(ni, np.zeros(3))
    def tree(ni, d=0):
        n = j['nodes'][ni]
        s = n.get('name', '?')
        if 'translation' in n and not 'mesh' in n or ('children' in n and 'translation' in n):
            s += ' @(' + ', '.join(f'{v:.3f}' for v in n['translation']) + ')'
        kids = [tree(c, d + 1) for c in n.get('children', [])]
        return s + (' → [' + ', '.join(kids) + ']' if kids else '')
    nodes = '; '.join(tree(ni) for ni in j['scenes'][0]['nodes'])
    mats = [m['name'] for m in j.get('materials', [])]
    return dict(tris=tris, size=hi - lo, lo=lo, hi=hi, mb=os.path.getsize(path) / 1e6, nodes=nodes, mats=mats)


def row(name):
    i = glb_info(f'{ROOT}/assets/{name}')
    s = i['size']
    return (f"| `{name}` | {s[0]:.2f} × {s[1]:.2f} × {s[2]:.2f} | {i['tris']:,} | {i['mb']:.1f} MB | {', '.join(i['mats'])} |", i)


SET_TXT = """## SET (screen structure, projection booth, lamp pole, popcorn) — generator: `src/set/`
Rebuild (each under the lock): `python3 src/set/screen_build.py` (~1.5 min), `booth_build.py` (~1 min), `lamp_pole.py`,
`popcorn.py` (seconds). Blender 5 as a Python module. Pipeline (`pipe.py`, `setbuild.py`, `weather2.py`) follows the
desert billboard: numpy geometry → Smart-UV atlas → Cycles bakes of world position / normal / AO / member grain axis /
paint mask → numpy weathering (30-40 years of mountain weather: silvered and checked timber, creosote on posts, rot and
moss at the feet, lichen, pine-needle duff on every horizontal, rust runs under every bolt and nail, owl droppings on the
rails, painted-over plywood chalking and peeling along sheet edges) → unique albedo (AO baked in) + ORM (G rough, B metal)
+ normal per material. `python3 src/set/write_docs.py` regenerates the tables below.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
{rows}

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
"""

CRE_TXT = """## CREATURES (moth, mouse, owl) — generator: `src/set/creatures.py`
Rebuild: `flock … python3 src/set/creatures.py [moth] [mouse] [owl]` (seconds). All face **+Z**, metres, no skinning:
every moving part is its own node with its pivot (node origin) at the hinge, so rotate nodes in code.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
{rows}

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
"""


def splice(text, tag, body):
    b, e = f'<!-- {tag}:BEGIN -->', f'<!-- {tag}:END -->'
    block = f'{b}\n{body.rstrip()}\n{e}'
    if b in text:
        return re.sub(re.escape(b) + '.*?' + re.escape(e), lambda m: block, text, flags=re.S)
    return text.rstrip() + '\n\n' + block + '\n'


if __name__ == '__main__':
    set_rows = '\n'.join(row(n)[0] for n in ('screen.glb', 'booth.glb', 'lamp_pole.glb', 'popcorn_bucket.glb', 'popcorn_kernel.glb'))
    cre_rows = '\n'.join(row(n)[0] for n in ('moth.glb', 'mouse.glb', 'owl.glb'))
    p = f'{ROOT}/ASSETS.md'
    t = open(p).read()
    t = splice(t, 'SET', SET_TXT.format(rows=set_rows))
    t = splice(t, 'CREATURES', CRE_TXT.format(rows=cre_rows))
    open(p, 'w').write(t)
    for n in ('screen.glb', 'booth.glb', 'lamp_pole.glb', 'popcorn_bucket.glb', 'popcorn_kernel.glb', 'moth.glb', 'mouse.glb', 'owl.glb'):
        print(n, glb_info(f'{ROOT}/assets/{n}')['nodes'][:300])
