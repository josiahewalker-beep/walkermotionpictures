"""Weathered Joshua-Tree monzogranite boulders and cobbles: rock_a … rock_e.

Method: a dense icosphere is shaped into a rounded, joint-faceted boulder (flattened base, a couple of planar
joint cuts softened by spheroidal weathering), then displaced with multi-octave noise and exfoliation shells.
The high-res surface is projected into a 2048 tri-planar-free atlas: each low-poly triangle (≤ 4k) gets UVs from a
spherical-cylindrical unwrap of the rounded base shape; albedo and tangent-space normal are baked by sampling the
high-res displacement field directly (it is analytic), so no Cycles bake is needed.
Material: rock (albedo with baked cavity/AO + sand at the base, normal map). Origin at ground centre, +Y up.
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import nrm, smoothstep, srgb, Part, bpy_reset, build_object, make_material, export_glb, glb_info, \
    save_img, TEXCACHE, ASSETS

ROCKS = {
    # size (x, y, z) metres; cuts = planar joint faces (k = softness, smaller = crisper); exfol = spalling
    'a': dict(size=(2.5, 1.9, 1.55), seed=1, cuts=3, ck=0.10, exfol=0.9, sink=0.12, tex=1024, tris=4000),   # big rounded block
    'b': dict(size=(1.3, 1.15, 1.45), seed=2, cuts=4, ck=0.07, exfol=0.7, sink=0.10, tex=1024, tris=4000),  # upright, faceted
    'c': dict(size=(1.4, 1.0, 0.5), seed=3, cuts=2, ck=0.08, exfol=0.5, sink=0.08, tex=1024, tris=3000),    # low slab
    'd': dict(size=(0.55, 0.45, 0.36), seed=4, cuts=2, ck=0.12, exfol=0.3, sink=0.06, tex=1024, tris=2000),
    'e': dict(size=(0.30, 0.26, 0.19), seed=5, cuts=1, ck=0.14, exfol=0.2, sink=0.05, tex=512, tris=1200),
}


# ------------------------------------------------------------------------------------------- 3D value-noise
class Noise3:
    def __init__(self, seed, n=64):
        rng = np.random.default_rng(seed)
        self.g = rng.standard_normal((n, n, n)).astype(np.float32)
        self.n = n

    def __call__(self, p, freq):
        from scipy import ndimage
        q = (p * freq) % self.n
        return ndimage.map_coordinates(self.g, q.T, order=3, mode='grid-wrap')

    def fbm(self, p, f0, oct=5, gain=0.5, lac=2.03):
        out = np.zeros(len(p)); a = 1.0; f = f0; tot = 0
        for i in range(oct):
            out += a * self(p + i * 7.31, f); tot += a; a *= gain; f *= lac
        return out / tot


def icosphere(sub):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    V = [np.array(x, float) / np.linalg.norm(x) for x in v]
    F = f
    for _ in range(sub):
        cache = {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]; V.append(m / np.linalg.norm(m)); cache[k] = len(V) - 1
            return cache[k]
        nf = []
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    return np.array(V), np.array(F)


class RockShape:
    """Analytic surface: radius along a unit direction (Z-up)."""

    def __init__(self, R):
        self.R = R
        rng = np.random.default_rng(R['seed'])
        self.rng = rng
        self.nz = Noise3(R['seed'] * 13 + 1)
        self.size = np.array(R['size']) / 2
        # joint planes (granite weathers along orthogonal joints into rounded blocks)
        self.cuts = []
        ph0 = rng.uniform(0, 2 * math.pi)
        for i in range(R['cuts']):
            az = ph0 + 2 * math.pi * i / max(R['cuts'], 1) + rng.normal(0, 0.3); el = rng.uniform(-0.1, 0.7)
            n = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
            self.cuts.append((n, rng.uniform(0.55, 0.8)))
        self.planes = []
        for i in range(rng.integers(1, 3)):
            az = rng.uniform(0, 2 * math.pi); el = rng.uniform(-0.3, 0.3)
            n = np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)])
            self.planes.append((n, rng.uniform(-0.35, 0.35) * self.size.mean()))

    def base_radius(self, d):
        # superellipsoid-ish rounded block
        e = 2.6
        s = self.size
        r = (np.abs(d[:, 0] / s[0]) ** e + np.abs(d[:, 1] / s[1]) ** e + np.abs(d[:, 2] / s[2]) ** e) ** (-1 / e)
        # soft joint cuts (smooth min with plane distance)
        for n, off in self.cuts:
            dn = d @ n
            plane = np.where(dn > 1e-3, off * (s @ np.abs(n)) / np.maximum(dn, 1e-3), 1e9)
            k = self.R['ck'] * s.mean()
            h = np.clip(0.5 + 0.5 * (plane - r) / k, 0, 1)
            r = plane * (1 - h) + r * h - k * h * (1 - h)
        # big lumpy weathering
        r = r * (1 + 0.10 * self.nz.fbm(d * 1.0, 1.4, oct=3))
        return r

    def detail(self, p):
        """Displacement (metres, along normal) at surface points p. Returns (h, crack_mask, spall_mask)."""
        sc = self.size.mean()
        nz = self.nz
        h = 0.022 * sc * nz.fbm(p / sc, 2.6, oct=4)
        # coarse grus / granular pitting (grains 3–8 mm)
        k = min(sc, 1.0)
        h += 0.0035 * k * nz.fbm(p, 55.0, oct=2)
        h -= 0.002 * k * np.clip(nz(p + 1.7, 140.0) - 1.0, 0, None)
        # exfoliation: patches where an outer shell (~1.5 cm) has spalled off; sharp lip, fresher stone inside
        sp = nz.fbm(p / sc + 3.3, 1.8, oct=3) + 0.25 * nz(p, 12.0)
        spall = smoothstep(0.42, 0.50, sp) * self.R['exfol']
        h -= 0.015 * min(sc, 1.0) * spall
        # joint fractures: a few near-planar cracks (distance to warped planes), only partly open
        crack = np.zeros(len(p))
        for i, (n, off) in enumerate(self.planes):
            dist = p @ n - off + 0.03 * sc * nz(p / sc + 40 + i, 2.0)
            open_ = smoothstep(0.0, 0.5, nz(p / sc + 50 + i, 1.2))
            w = 0.006 + 0.004 * sc
            crack = np.maximum(crack, (1 - smoothstep(0.0, w, np.abs(dist))) * open_)
        h -= 0.02 * min(sc, 1.0) * crack
        return h, crack, spall

def build_rock(key):
    R = ROCKS[key]
    shape = RockShape(R)
    # ------- low poly: icosphere sub 4 (5120 tris) → decimate by choosing sub level and removing below-ground
    sub = 4 if R['tris'] >= 3000 else 3 if R['tris'] >= 1200 else 3
    D, F = icosphere(sub)
    r = shape.base_radius(D)
    P = D * r[:, None]
    # flatten base and sink into ground
    zmin = P[:, 2].min()
    sink = R['sink'] * shape.size[2] * 2
    P[:, 2] = P[:, 2] - zmin - sink
    P[:, 2] = np.where(P[:, 2] < -sink * 0.5, -sink * 0.5 + (P[:, 2] + sink * 0.5) * 0.2, P[:, 2])
    # add large-scale part of detail into the low poly
    h, _, _ = shape.detail(P)
    nrm_v = vertex_normals(P, F)
    P = P + nrm_v * h[:, None] * 0.5
    # drop faces fully below ground
    keep = ~(np.all(P[F][:, :, 2] < -0.02, axis=1))
    F = F[keep]
    used = np.unique(F)
    remap = -np.ones(len(P), int); remap[used] = np.arange(len(used))
    P = P[used]; D = D[used]; F = remap[F]
    while len(F) > R['tris']:
        P, D, F = collapse_short(P, D, F, R['tris'])
    N = vertex_normals(P, F)
    # ------- UVs: cube-ish projection charts from the base direction → simple box unwrap atlas
    uv, F2, P2, N2, D2 = box_unwrap(P, F, N, D)
    # ------- bake textures by rasterising each chart in UV space
    tex = R['tex']
    alb, nor = bake(shape, P2, F2, N2, uv, tex, sink)
    a = save_img(alb, f'rock_{key}_albedo.jpg')
    n = save_img(nor, f'rock_{key}_normal.jpg', linear_to_srgb=False)
    part = Part()
    part.add(P2, F2, n=N2, c=np.ones((len(P2), 4)), uv=uv)
    return part, a, n


def vertex_normals(P, F):
    fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
    acc = np.zeros_like(P)
    for j in range(3):
        np.add.at(acc, F[:, j], fn)
    return nrm(acc)


def collapse_short(P, D, F, target):
    """Greedy shortest-edge collapse (one pass over independent edges)."""
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.unique(np.sort(E, 1), axis=0)
    L = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
    # prefer flat areas: weight by normal deviation
    order = np.argsort(L)
    need = (len(F) - target) // 2 + 1
    locked = np.zeros(len(P), bool)
    mp = np.arange(len(P))
    done = 0
    for e in order:
        a, b = E[e]
        if locked[a] or locked[b]:
            continue
        mp[b] = a
        P[a] = (P[a] + P[b]) / 2; D[a] = nrm(D[a] + D[b])
        locked[a] = locked[b] = True
        done += 1
        if done >= need:
            break
    F = mp[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0])]
    used = np.unique(F)
    remap = -np.ones(len(P), int); remap[used] = np.arange(len(used))
    return P[used], D[used], remap[F]


def box_unwrap(P, F, N, D):
    """Assign each face to one of 6 axis charts by its normal; pack 6 charts in a 3×2 atlas with padding."""
    fn = nrm(np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]]))
    ax = np.argmax(np.abs(fn), 1)
    sg = np.sign(fn[np.arange(len(F)), ax])
    chart = ax * 2 + (sg > 0)
    lo, hi = P.min(0), P.max(0)
    span = (hi - lo).max()
    Pn, Fn, Nn, Dn, UV = [], [], [], [], []
    count = 0
    pad = 0.02
    for c in range(6):
        sel = np.flatnonzero(chart == c)
        if len(sel) == 0:
            continue
        a = c // 2
        uax, vax = [(1, 2), (0, 2), (0, 1)][a]
        verts = np.unique(F[sel])
        m = -np.ones(len(P), int); m[verts] = np.arange(len(verts)) + count
        q = (P[verts] - lo) / span
        u = q[:, uax]; v = q[:, vax]
        if c % 2 == 0:
            u = 1 - u if a != 2 else u
        cx, cy = c % 3, c // 3
        UV.append(np.c_[(cx + pad + u * (1 - 2 * pad)) / 3, (cy + pad + v * (1 - 2 * pad)) / 2])
        Pn.append(P[verts]); Nn.append(N[verts]); Dn.append(D[verts]); Fn.append(m[F[sel]])
        count += len(verts)
    return np.concatenate(UV), np.concatenate(Fn), np.concatenate(Pn), np.concatenate(Nn), np.concatenate(Dn)


def bake(shape, P, F, N, UV, tex, sink):
    """Rasterise triangles in UV space; at each texel reconstruct the surface point, evaluate detail
    displacement and its gradient → tangent-space normal; colour from noise layers."""
    H = W = tex
    pos = np.zeros((H, W, 3)); nor = np.zeros((H, W, 3)); tu = np.zeros((H, W, 3)); tv = np.zeros((H, W, 3))
    mask = np.zeros((H, W), bool)
    uvp = UV * np.array([W, H])
    for f in F:
        a, b, c = uvp[f]
        x0, y0 = np.floor(np.minimum(np.minimum(a, b), c)).astype(int) - 1
        x1, y1 = np.ceil(np.maximum(np.maximum(a, b), c)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W - 1), min(y1, H - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        v0, v1 = b - a, c - a
        den = v0[0] * v1[1] - v1[0] * v0[1]
        if abs(den) < 1e-12:
            continue
        px, py = xs - a[0], ys - a[1]
        l1 = (px * v1[1] - v1[0] * py) / den
        l2 = (v0[0] * py - px * v0[1]) / den
        l0 = 1 - l1 - l2
        eps = 1.5 / max(np.linalg.norm(v0), np.linalg.norm(v1), 1)
        ins = (l0 > -eps) & (l1 > -eps) & (l2 > -eps)
        if not ins.any():
            continue
        Pt = P[f]; Nt = N[f]
        pp = l0[..., None] * Pt[0] + l1[..., None] * Pt[1] + l2[..., None] * Pt[2]
        nn = l0[..., None] * Nt[0] + l1[..., None] * Nt[1] + l2[..., None] * Nt[2]
        # tangent frame from UV gradients
        e1, e2 = Pt[1] - Pt[0], Pt[2] - Pt[0]
        du1, du2 = v0 / np.array([W, H]), v1 / np.array([W, H])
        r = du1[0] * du2[1] - du2[0] * du1[1]
        if abs(r) < 1e-12:
            continue
        T = (e1 * du2[1] - e2 * du1[1]) / r
        B = (e2 * du1[0] - e1 * du2[0]) / r
        yy = (ys - 0.5).astype(int); xx = (xs - 0.5).astype(int)
        sel = ins & ~mask[yy, xx]
        pos[yy[sel], xx[sel]] = pp[sel]; nor[yy[sel], xx[sel]] = nn[sel]
        tu[yy[sel], xx[sel]] = T; tv[yy[sel], xx[sel]] = B
        mask[yy[sel], xx[sel]] = True
    idx = np.flatnonzero(mask.ravel())
    p = pos.reshape(-1, 3)[idx]; n = nrm(nor.reshape(-1, 3)[idx])
    t = tu.reshape(-1, 3)[idx]; bt = tv.reshape(-1, 3)[idx]
    # detail height + numeric gradient along T and B (world units)
    eps = 0.003 * max(shape.size.mean(), 0.15)
    h0, crack, spall = shape.detail(p)
    tn = nrm(t - n * np.sum(t * n, 1, keepdims=True)); bn = nrm(np.cross(n, tn))
    bn = bn * np.sign(np.sum(bn * bt, 1, keepdims=True))
    hu = shape.detail(p + tn * eps)[0]; hv = shape.detail(p + bn * eps)[0]
    dhu = (hu - h0) / eps; dhv = (hv - h0) / eps
    ts = nrm(np.c_[-dhu, -dhv, np.ones_like(dhu)])
    # colour
    nz = shape.nz
    sc = shape.size.mean()
    base = np.array([0.42, 0.30, 0.20])          # buff-tan weathered monzogranite (linear)
    warm = np.array([0.48, 0.30, 0.17])          # orange iron staining
    pale = np.array([0.52, 0.44, 0.34])
    m1 = nz.fbm(p / sc + 5, 1.6, oct=4)
    m2 = nz.fbm(p / sc + 9, 3.5, oct=3)
    col = base + (warm - base) * smoothstep(-0.3, 0.8, m1)[:, None] + (pale - base) * smoothstep(0.3, 1.2, m2)[:, None] * 0.6
    # granular speckle: quartz/feldspar light grains, biotite dark grains
    g = nz(p * 1.0, 260.0)
    g2 = nz(p * 1.0 + 3.1, 310.0)
    col = col * (1 + 0.18 * smoothstep(1.1, 2.0, g))[:, None]
    col = col * (1 - 0.55 * smoothstep(1.4, 2.2, g2))[:, None]
    col = col * (1 + 0.06 * nz(p, 90.0))[:, None]
    # desert varnish (dark brown-black) on steep, older faces, streaking down
    up = n[:, 2]
    # desert varnish: thin dark streaks running down steep faces (narrow in plan, long vertically)
    streak = nz.fbm(np.c_[p[:, 0] * 9, p[:, 1] * 9, p[:, 2] * 0.5] / sc, 1.6, oct=3)
    patch = smoothstep(0.1, 0.6, nz.fbm(p / sc + 77, 1.3, oct=2))
    varnish = smoothstep(0.35, 0.75, streak) * patch * smoothstep(0.6, -0.1, up)
    col = col * (1 - 0.45 * varnish[:, None]) + np.array([0.10, 0.06, 0.04]) * 0.45 * varnish[:, None]
    # fresher, paler stone where the shell spalled; the old weathered rind is warmer/darker
    col = col * (1 - 0.35 * spall[:, None]) + np.array([0.50, 0.42, 0.33]) * 0.35 * spall[:, None]
    # lichens: small, muted crusts — yellow-green on tops, grey-green, rare orange dots
    up_ok = smoothstep(-0.1, 0.5, up)
    l1 = smoothstep(0.62, 0.78, nz.fbm(p / sc * 2 + 21, 2.4, oct=4) + 0.3 * nz(p, 30.0)) * up_ok
    l2 = smoothstep(0.70, 0.85, nz.fbm(p / sc * 2 + 31, 2.4, oct=4) + 0.3 * nz(p, 25.0)) * up_ok
    l3 = smoothstep(1.6, 2.1, nz(p, 18.0)) * up_ok
    col = col * (1 - 0.6 * l1[:, None]) + np.array([0.30, 0.29, 0.13]) * 0.6 * l1[:, None]
    col = col * (1 - 0.6 * l2[:, None]) + np.array([0.27, 0.28, 0.25]) * 0.6 * l2[:, None]
    col = col * (1 - 0.7 * l3[:, None]) + np.array([0.42, 0.17, 0.05]) * 0.7 * l3[:, None]
    # cavity: cracks dark, spall lips shadowed
    col *= (1 - 0.65 * crack)[:, None]
    hs = h0 / (0.02 * sc + 1e-6)
    col *= np.clip(0.85 + 0.15 * hs, 0.6, 1.1)[:, None]
    col *= (0.55 + 0.45 * smoothstep(-0.9, 0.3, up))[:, None]
    # ground contact: darker and sand-dusted near z ≈ 0
    z = p[:, 2]
    contact = smoothstep(0.18 * sc + 0.05, -0.02, z)
    col *= (1 - 0.35 * contact)[:, None]
    sand = smoothstep(0.10 * sc + 0.03, 0.0, z + 0.03 * nz(p, 20.0)) * 0.75
    sand_col = np.array([0.46, 0.33, 0.22]) * (1 + 0.15 * nz(p, 200.0))[:, None]
    col = col * (1 - sand[:, None]) + sand_col * sand[:, None]
    # dust settled on top
    dust = smoothstep(0.55, 0.95, up) * 0.3
    col = col * (1 - dust[:, None]) + np.array([0.47, 0.36, 0.26]) * dust[:, None]
    col = np.clip(col, 0.03, 0.85)
    alb = np.zeros((H * W, 3)); alb[idx] = col
    nmap = np.zeros((H * W, 3)) + np.array([0.5, 0.5, 1.0]); nmap[idx] = ts * 0.5 + 0.5
    alb = dilate(alb.reshape(H, W, 3), mask); nmap = dilate(nmap.reshape(H, W, 3), mask)
    # image row 0 = top = v 1
    return alb[::-1], nmap[::-1]


def dilate(img, mask, it=8):
    from scipy import ndimage
    m = mask.copy(); out = img.copy()
    for _ in range(it):
        acc = np.zeros_like(out); cnt = np.zeros(m.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(out * m[..., None], dy, 0), dx, 1)
            cnt += np.roll(np.roll(m, dy, 0), dx, 1)
        new = (~m) & (cnt > 0)
        out[new] = acc[new] / cnt[new][:, None]
        m = m | new
    return out


def export_rock(key):
    t0 = time.time()
    part, a, n = build_rock(key)
    bpy_reset()
    mat = make_material('rock', base=a, normal=n, normal_strength=1.0, rough=0.88, vcol=False)
    build_object(f'rock_{key}', {'rock': part}, {'rock': mat})
    path = os.path.join(ASSETS, f'rock_{key}.glb')
    export_glb(path)
    info = glb_info(path)
    print(f'rock_{key}: tris={info["tris"]} size={info["bytes"]/1e6:.2f}MB {time.time()-t0:.1f}s', flush=True)


if __name__ == '__main__':
    for k in (sys.argv[1:] or list(ROCKS)):
        export_rock(k)
