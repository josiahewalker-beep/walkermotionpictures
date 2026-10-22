"""Rocky Mountain conifers for the drive-in: pine_a (ponderosa), pine_b (lodgepole), pine_c (Douglas fir).

Each tree: a trunk tube with root flare (`bark`, tiling bark texture + normal map, UV u around / v up), main branches
as tubes (bark), and foliage as alpha-tested needle cards (`needles`, double-sided, MASK): crossed pairs for the pine
tufts, tilted pairs of flat sprays for the fir. Vertex colours (COLOR_0) carry baked sky-visibility AO (voxel field
from the foliage), crown-depth darkening and per-tuft tint jitter. `_lod1` re-uses the hero's skeleton: tufts are
clustered (k-means) into fewer, larger cards with the cluster's mean colour, trunk and main limbs as 5/3-sided tubes.

Blender Z-up during the build; GLB is +Y up, origin at the trunk base, metres.
Run: python3 pines.py [pine_a pine_b pine_c]   (under the shared lock)
"""
import sys, os, math, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import nrm, rodrigues, perp, smoothstep, Part, bpy_reset, build_object, make_material, export_glb, \
    glb_info, voxel_ao, TEXCACHE, ASSETS
import pinetex

UP = np.array([0, 0, 1.0])

TREES = {
    # ponderosa: tall clear orange trunk, open irregular rounded crown, clumped long-needle tufts at branch ends
    'pine_a': dict(kind='ponderosa', seed=7, H=28.0, dbh=0.82, crown_base=0.46, Rmax=5.2, n_br=64,
                   shape='dome', elev=(-12, 48), droop=0.35, upturn=0.55, sub=(3, 7), sub_len=(0.5, 1.5),
                   tuft=0.55, tufts_per_tip=(4, 9), along=0.25, gap=0.22, budget=58000, bark_tile=(1.2, 1.6),
                   tint=(1.0, 1.0, 1.0)),
    # lodgepole: very straight slender pole, short narrow crown in the top ~40 %, dense short tufts, dead stubs below
    'pine_b': dict(kind='lodgepole', seed=11, H=23.0, dbh=0.36, crown_base=0.56, Rmax=1.9, n_br=120,
                   shape='narrow', elev=(-8, 40), droop=0.25, upturn=0.35, sub=(1, 3), sub_len=(0.3, 0.7),
                   tuft=0.36, tufts_per_tip=(2, 4), along=0.7, gap=0.12, budget=58000, bark_tile=(0.6, 0.9),
                   stubs=55, tint=(1.0, 1.0, 1.0)),
    # Douglas fir: dense cone almost to the ground, drooping branches with upturned tips, pointed leader
    'pine_c': dict(kind='fir', seed=5, H=31.0, dbh=0.72, crown_base=0.10, Rmax=4.6, n_br=150,
                   shape='cone', elev=(-30, 25), droop=0.5, upturn=0.5, sub=(4, 8), sub_len=(0.5, 1.4),
                   tuft=0.62, tufts_per_tip=(1, 2), along=0.85, gap=0.08, budget=58000, bark_tile=(1.0, 1.4),
                   tint=(1.0, 1.0, 1.0)),
}


def envelope(T, t):
    """Crown radius fraction at relative crown height t (0 = crown base, 1 = top)."""
    t = np.clip(t, 0, 1)
    if T['shape'] == 'dome':
        r = (1 - t ** 2.3) ** 0.6 * (0.72 + 0.28 * smoothstep(0, 0.35, t))
    elif T['shape'] == 'narrow':
        r = np.minimum(1.0, (1 - t) * 1.7) ** 0.85 * (0.8 + 0.2 * smoothstep(0, 0.2, t))
    else:
        r = (1 - t) ** 1.0 * (0.92 + 0.08 * np.sin(t * 9))
    return r


# ------------------------------------------------------------------------------------------------ tubes
def frames(pts):
    T = nrm(np.gradient(pts, axis=0))
    N = np.zeros_like(T); N[0] = perp(T[:1])[0]
    for i in range(1, len(T)):
        v = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        N[i] = v / (np.linalg.norm(v) + 1e-12)
    return T, N, np.cross(T, N)


def tube(part, pts, radii, sides, col, tile, cap=False):
    """Bark tube. UV: u around (repeats ≈ circumference / tile_u), v = arc length / tile_v."""
    T, N, B = frames(pts)
    a = np.linspace(0, 2 * math.pi, sides + 1)          # duplicate seam column for UVs
    nor = np.cos(a)[None, :, None] * N[:, None] + np.sin(a)[None, :, None] * B[:, None]
    pos = pts[:, None] + nor * radii[:, None, None]
    W = sides + 1
    n = len(pts)
    i = np.arange(n - 1)[:, None] * W + np.arange(sides)[None]
    tris = np.concatenate([np.stack([i, i + 1, i + W], -1).reshape(-1, 3),
                           np.stack([i + 1, i + 1 + W, i + W], -1).reshape(-1, 3)])
    circ = 2 * math.pi * radii.max()
    rep = max(1, round(circ / tile[0]))
    arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    uv = np.stack([np.tile(a / (2 * math.pi) * rep, n), np.repeat(arc / tile[1], W)], -1)
    c = np.broadcast_to(np.asarray(col, float).reshape(-1, 3) if np.ndim(col) == 2 else np.asarray(col, float), (n, 3))
    cc = np.repeat(c, W, axis=0)
    part.add(pos.reshape(-1, 3), tris, n=nor.reshape(-1, 3), c=np.c_[cc, np.ones(len(cc))], uv=uv)
    if cap:   # close the tip
        k0 = part.count
        part.add(np.r_[pts[-1:] + T[-1:] * radii[-1] * 0.5], np.zeros((0, 3), int), n=T[-1:], c=np.c_[c[-1:], [1]],
                 uv=[[0.5, arc[-1] / tile[1]]])


# ------------------------------------------------------------------------------------------------ skeleton
class Tree:
    def __init__(self, name):
        self.name = name
        self.T = T = TREES[name]
        self.rng = np.random.default_rng(T['seed'])
        self.H = T['H']

    def trunk_axis(self):
        rng, H = self.rng, self.H
        n = 46
        z = np.linspace(0, H, n)
        # gentle sweep and a slight wander, straight for the lodgepole
        amp = {'ponderosa': 0.35, 'lodgepole': 0.10, 'fir': 0.18}[self.T['kind']]
        phase = rng.uniform(0, 6.28, 4)
        x = amp * (np.sin(z / H * 2.1 + phase[0]) - np.sin(phase[0])) + 0.04 * np.sin(z * 0.9 + phase[1])
        y = amp * 0.7 * (np.sin(z / H * 1.7 + phase[2]) - np.sin(phase[2])) + 0.04 * np.sin(z * 1.1 + phase[3])
        self.axis = np.stack([x, y, z], -1)
        self.az = z

    def trunk_radius(self, z):
        T, H = self.T, self.H
        r1 = T['dbh'] / 2
        # taper to a thin leader; flare at the base
        r = r1 * (1 - (z / H)) ** 0.85 * (1.0 + 0.0 * z) + 0.012
        flare = 1 + 0.55 * np.exp(-np.maximum(z, 0) / 0.55)
        return r * flare

    def axis_at(self, z):
        return np.stack([np.interp(z, self.az, self.axis[:, k]) for k in range(3)], -1)

    def grow(self):
        T, rng, H = self.T, self.rng, self.H
        self.trunk_axis()
        cb = T['crown_base'] * H
        self.branches = []          # (pts, radii, level)
        self.tips = []              # (pos, dir, weight) foliage anchors
        n = T['n_br']
        # heights: denser toward the top for pines; whorl-ish clustering for the fir/lodgepole
        u = (np.arange(n) + rng.uniform(0.2, 0.8, n)) / n
        zs = cb + (H * 0.985 - cb) * u ** (0.85 if T['kind'] != 'ponderosa' else 0.75)
        golden = math.pi * (3 - math.sqrt(5))
        az0 = rng.uniform(0, 6.28)
        for k, z in enumerate(zs):
            t = (z - cb) / (H - cb)
            if rng.random() < T['gap'] * (1 - t):        # missing branches → crown gaps
                continue
            az = az0 + k * golden + rng.normal(0, 0.25)
            R = T['Rmax'] * envelope(T, t) * rng.uniform(0.72, 1.12)
            if R < 0.25:
                R = 0.25
            el = math.radians(T['elev'][0] + (T['elev'][1] - T['elev'][0]) * t ** 1.3 + rng.normal(0, 6))
            d0 = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
            p0 = self.axis_at(z) + np.array([math.cos(az), math.sin(az), 0]) * self.trunk_radius(z) * 0.6
            L = R / max(math.cos(el), 0.35)
            segs = 7
            pts = [p0]; d = d0.copy()
            for s in range(1, segs + 1):
                f = s / segs
                # droop through the middle, then upturn at the tip
                d = nrm(d + UP * (-T['droop'] * 0.35 * (1 - f) + T['upturn'] * 0.45 * f ** 2) + rng.normal(0, 0.06, 3))
                pts.append(pts[-1] + d * L / segs)
            pts = np.array(pts)
            rb = (0.035 + 0.11 * (L / 6.0)) * (T['dbh'] / 0.8) ** 0.5 * (1.4 if T['kind'] == 'ponderosa' else 1.0)
            rb = min(rb, self.trunk_radius(z) * 0.7)
            radii = rb * np.linspace(1, 0.18, len(pts))
            self.branches.append((pts, radii, 0))
            # tip foliage
            self.tips.append((pts[-1], d, 1.0, t))
            # foliage along the outer part of the branch
            m = len(pts)
            for i in range(m):
                f = i / (m - 1)
                if f > 1 - T['along'] and i < m - 1 and rng.random() < 0.8:
                    self.tips.append((pts[i], nrm(pts[min(i + 1, m - 1)] - pts[i]), 0.6, t))
            # sub-branches
            ns = rng.integers(T['sub'][0], T['sub'][1] + 1)
            for j in range(ns):
                f = rng.uniform(0.35, 0.92)
                i = f * (m - 1); i0 = int(min(i, m - 2)); fr = i - i0
                q = pts[i0] * (1 - fr) + pts[i0 + 1] * fr
                bd = nrm(pts[i0 + 1] - pts[i0])
                side = nrm(np.cross(bd, UP) * rng.choice([-1, 1]) + rng.normal(0, 0.3, 3))
                sd = nrm(bd * 0.6 + side * 0.8 + UP * (T['upturn'] * 0.4 - T['droop'] * 0.3) * rng.uniform(0.3, 1.2))
                sl = rng.uniform(*T['sub_len']) * (0.6 + 0.5 * (L / max(T['Rmax'], 1)))
                sp = [q]; dd = sd.copy()
                for s in range(3):
                    dd = nrm(dd + UP * (T['upturn'] * 0.25 - T['droop'] * 0.15) + rng.normal(0, 0.1, 3))
                    sp.append(sp[-1] + dd * sl / 3)
                sp = np.array(sp)
                self.branches.append((sp, radii[i0] * 0.45 * np.linspace(1, 0.3, len(sp)), 1))
                self.tips.append((sp[-1], dd, 1.0, t))
                if T['kind'] != 'ponderosa':
                    self.tips.append((sp[1], nrm(sp[2] - sp[1]), 0.6, t))
        # leader
        lead = self.axis_at(np.array([H * 0.985]))[0]
        self.tips.append((lead, UP, 1.4, 1.0))
        # dead stubs below the crown (lodgepole, a few on the others)
        self.stubs = []
        nst = T.get('stubs', 10)
        for k in range(nst):
            z = rng.uniform(2.0, cb * 0.98)
            az = rng.uniform(0, 6.28)
            el = math.radians(rng.uniform(-35, 5))
            d = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
            p0 = self.axis_at(z) + np.array([math.cos(az), math.sin(az), 0]) * self.trunk_radius(z) * 0.5
            L = rng.uniform(0.15, 0.9) * (z / cb) ** 0.5 * (1.0 if T['kind'] == 'lodgepole' else 0.6)
            self.stubs.append(np.array([p0, p0 + d * L * 0.5, p0 + d * L + rng.normal(0, 0.05, 3)]))


# ------------------------------------------------------------------------------------------------ foliage
def place_tufts(tree, budget_cards):
    """Expand tips into individual tuft cards. Returns arrays: pos (N,3), dir (N,3), size (N,), crown t (N,)."""
    T, rng = tree.T, tree.rng
    P, D, Sz, Tt = [], [], [], []
    for pos, d, w, t in tree.tips:
        k = rng.integers(T['tufts_per_tip'][0], T['tufts_per_tip'][1] + 1)
        k = max(1, int(round(k * w)))
        for j in range(k):
            # clumped: tufts fan out around the tip, pointing outward/upward along the twig direction
            if T['kind'] == 'ponderosa':
                dd = nrm(d * 0.8 + UP * 0.55 + rng.normal(0, 0.45, 3))
                off = rng.normal(0, 0.22, 3)
            elif T['kind'] == 'lodgepole':
                dd = nrm(d * 0.8 + UP * 0.45 + rng.normal(0, 0.4, 3))
                off = rng.normal(0, 0.14, 3)
            else:
                dd = nrm(d * 1.0 + UP * rng.uniform(-0.35, 0.1) + rng.normal(0, 0.25, 3))
                off = rng.normal(0, 0.18, 3)
            P.append(pos + off); D.append(dd)
            Sz.append(T['tuft'] * rng.uniform(0.75, 1.25) * (1.25 if w > 1.2 else 1.0)); Tt.append(t)
    P, D, Sz, Tt = map(np.array, (P, D, Sz, Tt))
    if len(P) > budget_cards:
        keep = np.sort(rng.choice(len(P), budget_cards, replace=False))
        P, D, Sz, Tt = P[keep], D[keep], Sz[keep], Tt[keep]
    return P, D, Sz, Tt


def card_quads(kind, P, D, Sz, rng, cross=True, cells=None):
    """Return verts (N*k*4,3), tris, normals, uv for crossed (pines) or tilted-pair (fir) cards."""
    V, F, Nn, UV, owner = [], [], [], [], []
    n = len(P)
    if cells is None:
        cells = rng.integers(0, 4, n)
    base = 0
    for i in range(n):
        d = D[i]; s = Sz[i]
        cu, cv = (cells[i] % 2) * 0.5, (cells[i] // 2) * 0.5
        # the image row 0 is the top of the atlas: cell row r (from the top) → v range [1 - (r+1)/2, 1 - r/2]
        v0 = 1 - (cells[i] // 2 + 1) * 0.5
        if kind == 'fir':
            side0 = nrm(np.cross(d, UP) + rng.normal(0, 0.05, 3))
            rolls = [rng.uniform(0.35, 0.75), -rng.uniform(0.35, 0.75)] if cross else [rng.uniform(-0.5, 0.5)]
            planes = [rodrigues(side0[None], d[None], np.array([r]))[0] for r in rolls]
            start = P[i] - d * s * 0.35
        else:
            side0 = perp(d[None])[0]
            rot = rng.uniform(0, math.pi)
            side0 = rodrigues(side0[None], d[None], np.array([rot]))[0]
            planes = [side0, np.cross(d, side0)] if cross else [side0]
            start = P[i] - d * s * 0.45
        for sd in planes:
            w = s * (0.5 if kind != 'fir' else 0.5)
            v = np.array([start - sd * w, start + sd * w, start + sd * w + d * s, start - sd * w + d * s])
            nn = nrm(np.cross(sd, d))
            if nn[2] < 0:
                nn = -nn
            # bend the shading normal outward from the tree axis (softer, volumetric crowns)
            out = nrm(np.array([P[i][0], P[i][1], 0.0]) + 1e-6)
            nn = nrm(nn * 0.6 + out * 0.5 + UP * 0.25)
            V.append(v); Nn.append(np.tile(nn, (4, 1)))
            UV.append(np.array([[cu, v0], [cu + 0.5, v0], [cu + 0.5, v0 + 0.5], [cu, v0 + 0.5]]))
            F.append(np.array([[0, 1, 2], [0, 2, 3]]) + base)
            owner += [i] * 4
            base += 4
    return np.concatenate(V), np.concatenate(F), np.concatenate(Nn), np.concatenate(UV), np.array(owner)


def foliage_colour(tree, P, Tt, vis, rng):
    T = tree.T
    n = len(P)
    # crown depth: radial distance relative to the envelope at that height (inner = darker, older needles)
    cb = T['crown_base'] * tree.H
    t = np.clip((P[:, 2] - cb) / (tree.H - cb), 0, 1)
    env = np.maximum(T['Rmax'] * envelope(T, t), 0.4)
    rad = np.hypot(P[:, 0], P[:, 1]) / env
    depth = smoothstep(1.0, 0.25, rad)
    jitter = rng.uniform(0.85, 1.12, n)
    warm = rng.uniform(-0.05, 0.08, n)
    col = np.stack([jitter * (1 + warm), jitter, jitter * (1 - warm * 0.5)], -1)
    shade = (0.30 + 0.70 * vis) * (1 - 0.30 * depth)
    return np.clip(col * shade[:, None], 0, 1)


# ------------------------------------------------------------------------------------------------ build
def build(name, write=True):
    t0 = time.time()
    tree = Tree(name)
    T = tree.T
    tree.grow()
    rng = tree.rng
    kind = T['kind']
    bark = Part(); needles = Part()
    tile = T['bark_tile']
    # trunk (more sides near the base for the flare)
    zt = np.concatenate([np.linspace(0, 1.2, 8), np.linspace(1.4, tree.H, 40)])
    ap = tree.axis_at(zt)
    tube(bark, ap, tree.trunk_radius(zt), 20 if kind != 'lodgepole' else 14, np.ones(3), tile)
    # branches
    for pts, radii, lvl in tree.branches:
        sides = 6 if lvl == 0 else 4
        if radii[0] < 0.025:
            sides = 3
        tube(bark, pts, radii, sides, np.ones(3), (tile[0] * 0.5, tile[1] * 0.5))
    for sp in tree.stubs:
        tube(bark, sp, np.array([0.025, 0.017, 0.006]), 3, np.array([0.75, 0.75, 0.72]), (0.3, 0.5))
    budget_cards = (T['budget'] - bark.ntris) // (4 if kind != 'fir' else 4)
    P, D, Sz, Tt = place_tufts(tree, budget_cards)
    cells = rng.integers(0, 4, len(P))
    V, F, Nn, UV, own = card_quads(kind, P, D, Sz, rng, cross=True, cells=cells)
    # AO: occlusion density from the tuft centres (weighted by card area)
    occ = P + rng.normal(0, 0.1, P.shape)
    bv, bt, bn, bc, buv = bark.arrays()
    vis_t = voxel_ao(P, occ, (Sz ** 2) * 1.0, cell=0.35, sigma=0.55, steps=30)
    vis_b = voxel_ao(bv, occ, (Sz ** 2) * 1.0, cell=0.35, sigma=0.55, steps=30)
    colt = foliage_colour(tree, P, Tt, vis_t, rng)
    needles.add(V, F, n=Nn, c=np.c_[colt[own], np.ones(len(own))], uv=UV)
    bc = bc.copy(); bc[:, :3] *= (0.35 + 0.65 * vis_b)[:, None]
    # ground contact: darken the trunk foot a little
    bc[:, :3] *= (0.75 + 0.25 * smoothstep(0.0, 0.8, bv[:, 2]))[:, None]
    bark.v, bark.t, bark.n, bark.c, bark.uv = [bv], [bt], [bn], [bc], [buv]; bark.count = len(bv)
    print(f'{name}: bark {bark.ntris} tris, {len(P)} tufts → {needles.ntris} tris; vis mean {vis_t.mean():.2f} '
          f'min {vis_t.min():.2f}  ({time.time()-t0:.1f}s)', flush=True)
    if write:
        export(name, bark, needles, kind)
    # ---------------- LOD1
    lod = build_lod(tree, P, D, Sz, colt, cells, rng)
    if write:
        export(name + '_lod1', lod[0], lod[1], kind, tex_size=512)
    return tree


def build_lod(tree, P, D, Sz, colt, cells, rng, target=5800):
    from scipy.cluster.vq import kmeans2
    T = tree.T; kind = T['kind']
    bark = Part(); needles = Part()
    tile = T['bark_tile']
    zt = np.concatenate([[0, 0.5], np.linspace(1.2, tree.H, 10)])
    tube(bark, tree.axis_at(zt), tree.trunk_radius(zt), 6, np.ones(3), tile)
    # only the main limbs, thickest first (they show through ponderosa gaps)
    mains = sorted([b for b in tree.branches if b[2] == 0], key=lambda b: -b[1][0])
    for pts, radii, lvl in mains[: {'ponderosa': 45, 'lodgepole': 0, 'fir': 0}[kind]]:
        tube(bark, pts[::2], radii[::2], 3, np.ones(3), tile)
    bv, bt, bn, bc, buv = bark.arrays()
    bc = bc.copy(); bc[:, :3] *= 0.6
    bark.v, bark.c = [bv], [bc]
    ncard = (target - bark.ntris) // 4        # crossed pairs, 4 tris each
    np.random.seed(T['seed'])
    feats = np.c_[P, D * 0.4]
    cent, lab = kmeans2(feats, ncard, minit='++', seed=T['seed'], iter=8)
    cnt = np.bincount(lab, minlength=ncard)
    ok = cnt > 0
    Pc = np.array([P[lab == k].mean(0) for k in range(ncard) if ok[k]])
    Dc = np.array([nrm(D[lab == k].sum(0)) for k in range(ncard) if ok[k]])
    Cc = np.array([colt[lab == k].mean(0) for k in range(ncard) if ok[k]])
    Ext = np.array([np.sqrt(((P[lab == k] - P[lab == k].mean(0)) ** 2).sum(1).mean()) for k in range(ncard) if ok[k]])
    Area = np.array([(Sz[lab == k] ** 2).sum() for k in range(ncard) if ok[k]])
    # card size: keep total covered area similar (alpha coverage of the atlas is the same), at least the extent
    Sc = np.maximum(np.sqrt(Area) * 0.80, Ext * 1.6)
    Sc = np.maximum(Sc, Sz.mean())
    V, F, Nn, UV, own = card_quads(kind, Pc, Dc, Sc, rng, cross=True)
    # bigger cards average more tufts → their colour is slightly darker inside (self-shadowing at distance)
    needles.add(V, F, n=Nn, c=np.c_[Cc[own] * 0.95, np.ones(len(own))], uv=UV)
    print(f'{tree.name}_lod1: bark {bark.ntris}, cards {len(Pc)} → total {bark.ntris + needles.ntris} tris', flush=True)
    return bark, needles


def export(name, bark, needles, kind, tex_size=None):
    ba, bn = pinetex_cached('bark', kind)
    na = pinetex_cached('needles', kind)
    if tex_size:
        ba, bn, na = [downsize(p, tex_size) for p in (ba, bn, na)]
    bpy_reset()
    mats = {'bark': make_material('bark', base=ba, normal=bn, normal_strength=1.0, rough=0.92),
            'needles': make_material('needles', base=na, rough=0.62, double=True, alpha_clip=0.4)}
    build_object(name, {'bark': bark, 'needles': needles}, mats)
    path = os.path.join(ASSETS, name + '.glb')
    export_glb(path, image_format='AUTO')
    fix_alpha_mode(path, 'needles', 0.4)
    info = glb_info(path)
    print(f'  → {name}.glb tris={info["tris"]} {info["bytes"]/1e6:.2f} MB', flush=True)


def pinetex_cached(what, kind):
    if what == 'bark':
        a = os.path.join(TEXCACHE, f'bark_{kind}_albedo.jpg'); n = os.path.join(TEXCACHE, f'bark_{kind}_normal.jpg')
        if not os.path.exists(a):
            pinetex.bark(kind)
        return a, n
    p = os.path.join(TEXCACHE, f'needles_{kind}.png')
    if not os.path.exists(p):
        pinetex.atlas(kind)
    return p


def downsize(path, size):
    from PIL import Image
    root, ext = os.path.splitext(path)
    out = f'{root}_{size}{ext}'
    im = Image.open(path)
    im.resize((size, size), Image.LANCZOS).save(out, **({'quality': 90} if ext == '.jpg' else {'optimize': True}))
    return out


def fix_alpha_mode(path, matname, cutoff):
    import struct
    d = bytearray(open(path, 'rb').read())
    l = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + l])
    for m in j.get('materials', []):
        if m['name'] == matname:
            m['alphaMode'] = 'MASK'; m['alphaCutoff'] = cutoff; m['doubleSided'] = True
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    rest = d[20 + l:]
    out = bytearray(d[:12]) + struct.pack('<I', len(js)) + d[16:20] + js + rest
    out[8:12] = struct.pack('<I', len(out))
    open(path, 'wb').write(out)


if __name__ == '__main__':
    for k in (sys.argv[1:] or list(TREES)):
        build(k)
