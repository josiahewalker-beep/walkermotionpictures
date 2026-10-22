## PINES (conifers, ground textures, scatter props, rocks) — generator: `src/pines/`
Rebuild (under the shared lock, ~3 min total): `cd src/pines && python3 pinetex.py && python3 pines.py && python3 props.py
&& python3 rocks.py && python3 ground.py && python3 write_docs.py` (`run.sh "<cmd>" "<harness query>|<png>"` builds and
screenshots in one lock acquisition). Everything is procedural (numpy/PIL + Blender as a Python module); no third-party
meshes or textures. Pipeline and helpers adapted from `desert/src/flora` (vertex-colour AO, KHR_mesh_quantization).

{{TABLE}}

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
