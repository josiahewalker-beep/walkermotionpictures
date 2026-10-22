"""Regenerate the FLORA section of desert/ASSETS.md from the current GLBs (sizes, tris, materials)."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import glb_info, ASSETS, DESERT

def stats(f):
    p = os.path.join(ASSETS, f)
    i = glb_info(p)
    d = open(p, 'rb').read(); l = struct.unpack('<I', d[12:16])[0]; j = json.loads(d[20:20 + l])
    lo = [1e9] * 3; hi = [-1e9] * 3
    for pr in j['meshes'][0]['primitives']:
        a = j['accessors'][pr['attributes']['POSITION']]
        lo = [min(x, y) for x, y in zip(lo, a['min'])]; hi = [max(x, y) for x, y in zip(hi, a['max'])]
    return i, [h - l_ for h, l_ in zip(hi, lo)]

rows = []
for f in sorted(os.listdir(ASSETS)):
    if f.endswith('.glb') and f.split('_')[0] in ('joshua', 'creosote', 'bursage', 'rock'):
        i, s = stats(f)
        rows.append(f"| `{f}` | {s[0]:.2f} × {s[1]:.2f} × {s[2]:.2f} | {i['tris']:,} | {i['bytes']/1e6:.1f} MB | {', '.join(i['materials'])} |")

text = f"""## FLORA (Joshua trees, shrubs, rocks) — generator: `src/flora/`
Rebuild: `cd src/flora && python3 textures.py && python3 joshua.py && python3 shrubs.py && python3 rocks.py`
(Blender 5.x as a Python module; run under the shared lock; ~2 min total). `write_docs.py` regenerates this table.

| file | size x × y(up) × z, m | tris | GLB | materials |
|---|---|---|---|---|
""" + "\n".join(rows) + """

Common to all: one mesh node named like the file, origin on the ground at the trunk/footprint centre, metres, +Y up,
no animation. Vertex colours COLOR_0 (RGB, normalized uint8) carry per-blade tint **and baked ambient occlusion** —
keep `vertexColors` on. Normals are int8 via `KHR_mesh_quantization` (three.js GLTFLoader handles it natively).
Fur/bark/leaf carry `KHR_materials_specular` (lowered F0, matte dead leaves).

**Joshua trees** (`joshua_a` young 3 m single trunk · `b` 5 m Y-fork · `c` 7 m mature classic · `d` 9 m old broad).
- `bark` — corky checkered trunk bark (1024 albedo + normal), single-sided, roughness 0.95. Lower trunk only.
- `fur` — dead-leaf skirt, double-sided: a thatch-textured core tube plus thousands of downward blades (flat
  straws and thin strands, curled tips; tan-brown just under each rosette, weathering to grey-straw).
  Visible albedo ≈ 0.30–0.38 linear. On the trunk from ~1 m up (a: from 0.5 m) and on all younger limbs.
- `leaf` — living rosettes, double-sided: stiff keeled dagger leaves 18–34 cm, ~1.2 cm wide, blue-green to olive,
  pale serrated margin and brown spine in the texture, radiating like a sea urchin; yellowing band below.
- Trunk diameters at 1 m: a 0.25, b 0.34, c 0.48, d 0.72 m (at the ground with flare: 0.32 / 0.42 / 0.61 / 0.97 m).
- Rosette tip positions per hero tree (glTF coords): `src/flora/_tex/joshua_<v>_tips.json` (useful for wind/sway).
- `_lod1` (≤ 8k tris, 512 px textures): same skeleton/silhouette, 5-sided tubes, single-triangle leaves and blades,
  thicker thatch core. Matches the hero from ~35 m; switch at 35–45 m. Fur blades are double-sided: no need to
  disable backface culling elsewhere.
- Sway (if wanted): bend ∝ height², rosettes are at the branch tips; the trees are stiff — keep amplitude tiny.

**Shrubs** — `creosote_a` (1.7 m, open vase) and `creosote_b` (1.35 m): thin dark-grey stems (`bark`, vertex colour
only) + alpha-tested leaf-sprig cards (`leaf`, alphaMode MASK cutoff 0.5, double-sided, PNG with alpha).
`bursage_a`: low pale grey-green mound ~0.55 m × 0.9 m.

**Rocks** — `rock_a` big rounded block 2.5 m, `rock_b` upright faceted 1.4 m, `rock_c` low slab, `rock_d`/`rock_e`
cobbles 0.55/0.3 m. Joshua-Tree monzogranite: buff-tan with orange iron staining, coarse grain speckle, joint
fractures, spalled exfoliation patches, narrow desert-varnish streaks, small lichen crusts, sand/dust at the base.
Material `rock`: 1024 px albedo (cavity/AO baked in) + tangent-space normal (512 for rock_e), roughness 0.88,
single-sided. Bottoms are sunk 5–12 cm below y = 0 so they sit in the sand; scale freely (±30%) and rotate about Y.
"""
p = os.path.join(DESERT, 'ASSETS.md')
s = open(p).read()
start = s.find('## FLORA')
if start >= 0:
    nxt = s.find('\n## ', start + 5)
    s = s[:start] + text + (s[nxt + 1:] if nxt >= 0 else '')
else:
    s = s.rstrip() + '\n\n' + text
open(p, 'w').write(s)
print(text)
