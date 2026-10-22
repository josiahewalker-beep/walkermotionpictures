"""Shared geometry library for the procedural cars (numpy side, no bpy).

Modelling frame used by the car scripts: x = lateral, s = longitudinal (front +), z = up, metres.
Conversion to Blender happens in blendout.py: (x, s, z) -> Blender (-x, -s, z) (a 180 deg turn, keeps winding),
so the nose ends up toward Blender -Y, i.e. glTF +Z after the Y-up export.  In glTF the car's left (driver) side is
+X, which is model x < 0.

Pipeline: implicit field (2D profile SDFs + smooth booleans) -> marching cubes -> decimate -> analytic normals
-> exact level-set cuts for panel gaps, glass, trim, lights -> parts list -> blendout.py writes the GLB.
"""
import numpy as np
from scipy import ndimage
from matplotlib.path import Path
from skimage import measure
import pyfqmr

# ---------------------------------------------------------------- small math
def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25

def smax(a, b, k):
    return -smin(-a, -b, k)

def sabs(a, e):
    return np.sqrt(a * a + e * e)

def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def gauss(x, c, w):
    return np.exp(-((x - c) / w) ** 2)

def normalize(v):
    l = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(l, 1e-12)

# ---------------------------------------------------------------- curves
def catmull_closed(pts, n_per=24, closed=True):
    """Centripetal Catmull-Rom through pts. Duplicate a point to make a sharp corner."""
    P = np.asarray(pts, float)
    # drop exact consecutive duplicates but remember corners
    out = []
    m = len(P)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = P[(i - 1) % m] if (closed or i > 0) else P[0]
        p1 = P[i]
        p2 = P[(i + 1) % m]
        p3 = P[(i + 2) % m] if (closed or i + 2 < m) else P[-1]
        if np.allclose(p1, p2):
            continue
        if np.allclose(p0, p1):
            p0 = p1 - (p2 - p1) * 0.01
        if np.allclose(p2, p3):
            p3 = p2 + (p2 - p1) * 0.01
        def tj(ti, a, b):
            return ti + max(np.linalg.norm(b - a), 1e-6) ** 0.5
        t0 = 0.0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
        t = np.linspace(t1, t2, n_per, endpoint=False)[:, None]
        A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
        B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
        C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
        out.append(C)
    if not closed:
        out.append(P[-1:])
    return np.concatenate(out)

def mirror_half(half_pts):
    """half_pts: list of (x>=0, y) from (0, top) around to (0, bottom). Returns closed full outline."""
    H = np.asarray(half_pts, float)
    M = H[::-1].copy(); M[:, 0] *= -1
    if abs(H[0, 0]) < 1e-9: M = M[:-1]
    if abs(H[-1, 0]) < 1e-9: M = M[1:]
    return np.concatenate([H, M])

class SDF2D:
    """Signed distance (negative inside) of a closed outline, rasterised and smoothed."""
    def __init__(self, outline, res=0.002, margin=0.25, smooth=True, n_per=24, curve=True):
        P = catmull_closed(outline, n_per) if curve else np.asarray(outline, float)
        self.outline = P
        lo = P.min(0) - margin; hi = P.max(0) + margin
        nu = int(np.ceil((hi[0] - lo[0]) / res)) + 1
        nv = int(np.ceil((hi[1] - lo[1]) / res)) + 1
        u = lo[0] + np.arange(nu) * res; v = lo[1] + np.arange(nv) * res
        UU, VV = np.meshgrid(u, v, indexing='ij')
        inside = Path(P).contains_points(np.c_[UU.ravel(), VV.ravel()]).reshape(nu, nv)
        din = ndimage.distance_transform_edt(inside)
        dout = ndimage.distance_transform_edt(~inside)
        d = (dout - din) * res + np.where(inside, 0.5 * res, -0.5 * res)
        if smooth:
            d = ndimage.gaussian_filter(d, 1.2)
        self.d = d.astype(np.float32); self.lo = lo; self.res = res; self.shape = d.shape

    def __call__(self, u, v):
        u = np.asarray(u, float); v = np.asarray(v, float)
        cu = (u - self.lo[0]) / self.res; cv = (v - self.lo[1]) / self.res
        shp = np.broadcast(cu, cv).shape
        cu = np.broadcast_to(cu, shp).ravel(); cv = np.broadcast_to(cv, shp).ravel()
        val = ndimage.map_coordinates(self.d, [cu, cv], order=1, mode='nearest')
        # outside the raster: add the extra distance so far points stay outside
        eu = np.maximum(0, np.maximum(-cu, cu - (self.shape[0] - 1))) * self.res
        ev = np.maximum(0, np.maximum(-cv, cv - (self.shape[1] - 1))) * self.res
        return (val + np.hypot(eu, ev)).reshape(shp)

def sd_round_box(p, c, half, r):
    """p (...,3); axis-aligned rounded box."""
    q = np.abs(p - c) - (np.asarray(half) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.max(q, axis=-1), 0) - r

def sd_capsule(p, a, b, r):
    a = np.asarray(a, float); b = np.asarray(b, float)
    pa = p - a; ba = b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - r

# ---------------------------------------------------------------- meshing
def mc_mesh(field, lo, hi, res, slab=24):
    """field(X, S, Z) -> d (broadcastable arrays). Returns V (x,s,z), F (outward winding)."""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    n = np.ceil((hi - lo) / res).astype(int) + 1
    xs = lo[0] + np.arange(n[0]) * res; ss = lo[1] + np.arange(n[1]) * res; zs = lo[2] + np.arange(n[2]) * res
    vol = np.empty((n[0], n[1], n[2]), np.float32)
    for i0 in range(0, n[1], slab):
        i1 = min(n[1], i0 + slab)
        X, S, Z = np.meshgrid(xs, ss[i0:i1], zs, indexing='ij')
        vol[:, i0:i1, :] = field(X, S, Z)
    # close the volume
    vol[0, :, :] = vol[-1, :, :] = 1; vol[:, 0, :] = vol[:, -1, :] = 1; vol[:, :, 0] = vol[:, :, -1] = 1
    V, F, _, _ = measure.marching_cubes(vol, 0.0, spacing=(res, res, res))
    V = V + lo
    del vol
    return V.astype(np.float64), F.astype(np.int64)

def field_normals(field, V, h=0.002):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]
    gx = field(x + h, s, z) - field(x - h, s, z)
    gs = field(x, s + h, z) - field(x, s - h, z)
    gz = field(x, s, z + h) - field(x, s, z - h)
    return normalize(np.stack([gx, gs, gz], 1))

def face_normals(V, F):
    return np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])

def vertex_normals(V, F):
    fn = face_normals(V, F)
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return normalize(N)

def fix_winding(V, F, N):
    """Flip faces whose geometric normal disagrees with the given vertex normals (majority)."""
    fn = face_normals(V, F)
    d = np.einsum('ij,ij->i', fn, N[F].mean(1))
    if (d < 0).sum() > (d > 0).sum():
        F = F[:, ::-1].copy()
    return F

def decimate(V, F, target, preserve_border=True, aggr=7):
    s = pyfqmr.Simplify()
    s.setMesh(V.astype(np.float64), F.astype(np.int32))
    s.simplify_mesh(target_count=int(target), aggressiveness=aggr, preserve_border=preserve_border, verbose=0)
    v, f, _ = s.getMesh()
    return np.asarray(v, np.float64), np.asarray(f, np.int64)

def clean_unused(V, F, attrs=None):
    used = np.unique(F)
    remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
    out = {k: a[used] for k, a in (attrs or {}).items()}
    return V[used], remap[F], out

# ---------------------------------------------------------------- level-set cut
class SurfMesh:
    """Triangle mesh with per-vertex attributes (interpolated through cuts) and per-face labels."""
    def __init__(self, V, F, N, label=0):
        self.V = V.copy(); self.F = F.copy(); self.N = N.copy()
        self.attr = {}
        self.lab = np.full(len(F), label, np.int64)

    def set_attr(self, name, vals):
        self.attr[name] = np.asarray(vals, float).copy()

    def cut(self, g, name=None):
        """Split triangles exactly along g=0 (g per vertex). Stores g as attribute `name`."""
        V, F, N = self.V, self.F, self.N
        g = np.asarray(g, float).copy()
        tiny = 1e-9
        g[np.abs(g) < tiny] = tiny
        nV = len(V)
        pos = g > 0
        fp = pos[F]; cnt = fp.sum(1)
        cross = (cnt == 1) | (cnt == 2)
        if not cross.any():
            if name: self.attr[name] = g
            return
        Fk = F[~cross]; Lk = self.lab[~cross]
        Fc = F[cross]; pc = fp[cross]; cc = cnt[cross]; Lc = self.lab[cross]
        lonely = np.where((cc == 1)[:, None], pc, ~pc)
        k = np.argmax(lonely, 1)
        r = np.arange(len(Fc))
        a = Fc[r, k]; b = Fc[r, (k + 1) % 3]; c = Fc[r, (k + 2) % 3]
        E = np.concatenate([np.sort(np.stack([a, b], 1), 1), np.sort(np.stack([a, c], 1), 1)])
        key = E[:, 0] * nV + E[:, 1]
        ukey, inv = np.unique(key, return_inverse=True)
        e0 = ukey // nV; e1 = ukey % nV
        t = g[e0] / (g[e0] - g[e1])
        newV = V[e0] + t[:, None] * (V[e1] - V[e0])
        newN = normalize(N[e0] + t[:, None] * (N[e1] - N[e0]))
        ids = nV + np.arange(len(ukey))
        p = ids[inv[:len(Fc)]]; q = ids[inv[len(Fc):]]
        T = np.concatenate([np.stack([a, p, q], 1), np.stack([p, b, c], 1), np.stack([p, c, q], 1)])
        self.V = np.concatenate([V, newV]); self.N = np.concatenate([N, newN])
        for kname, arr in self.attr.items():
            nv = arr[e0] + t * (arr[e1] - arr[e0]) if arr.ndim == 1 else arr[e0] + t[:, None] * (arr[e1] - arr[e0])
            self.attr[kname] = np.concatenate([arr, nv])
        gn = np.concatenate([g, np.zeros(len(ukey))])
        self.F = np.concatenate([Fk, T]); self.lab = np.concatenate([Lk, Lc, Lc, Lc])
        if name: self.attr[name] = gn
        return gn

    def face_mean(self, name):
        return self.attr[name][self.F].mean(1)

    def subdivide(self, mask, max_edge, iters=4):
        """Midpoint-subdivide faces in mask until edges < max_edge (only fully-masked faces)."""
        for _ in range(iters):
            F = self.F
            L = np.max(np.stack([np.linalg.norm(self.V[F[:, i]] - self.V[F[:, (i + 1) % 3]], axis=1) for i in range(3)], 1), 1)
            sel = mask & (L > max_edge)
            if not sel.any(): break
            # split the longest edge of selected faces via a cut-like approach: use 1->4 split with shared midpoints;
            # neighbours of split faces get T-junction fixed by splitting them too (1->2 per split edge).
            nV = len(self.V)
            Fs = F[sel]
            E = np.concatenate([np.sort(Fs[:, [0, 1]], 1), np.sort(Fs[:, [1, 2]], 1), np.sort(Fs[:, [2, 0]], 1)])
            key = E[:, 0] * nV + E[:, 1]
            ukey = np.unique(key)
            e0 = ukey // nV; e1 = ukey % nV
            mid = 0.5 * (self.V[e0] + self.V[e1])
            midN = normalize(self.N[e0] + self.N[e1])
            ids = nV + np.arange(len(ukey))
            lookup = dict(zip(ukey.tolist(), ids.tolist()))
            newF = []; newL = []
            for fi, (f, l) in enumerate(zip(F.tolist(), self.lab.tolist())):
                m = []
                for i in range(3):
                    u, v = f[i], f[(i + 1) % 3]
                    kk = min(u, v) * nV + max(u, v)
                    m.append(lookup.get(kk, -1))
                nm = sum(1 for x in m if x >= 0)
                if nm == 0:
                    newF.append(f); newL.append(l)
                elif nm == 3:
                    a, b, c = f; ab, bc, ca = m
                    newF += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]; newL += [l] * 4
                else:
                    # fan from midpoints: rotate so that first split edge index known
                    a, b, c = f
                    verts = [a, m[0], b, m[1], c, m[2]]
                    poly = [x for x in verts if x >= 0]
                    # triangulate polygon as a fan from a corner opposite a midpoint
                    for j in range(1, len(poly) - 1):
                        newF.append([poly[0], poly[j], poly[j + 1]]); newL.append(l)
            self.V = np.concatenate([self.V, mid]); self.N = np.concatenate([self.N, midN])
            for kname, arr in self.attr.items():
                self.attr[kname] = np.concatenate([arr, 0.5 * (arr[e0] + arr[e1])])
            self.F = np.asarray(newF, np.int64); self.lab = np.asarray(newL, np.int64)
            mask = np.ones(len(self.F), bool) if mask.all() else self._remask(sel_prev=None)
        return

    def _remask(self, sel_prev):
        return np.ones(len(self.F), bool)

def boundary_edges(F):
    """Directed boundary edges (u->v as in faces) of a face set."""
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    key_d = E[:, 0].astype(np.int64) * (1 << 31) + E[:, 1]
    key_r = E[:, 1].astype(np.int64) * (1 << 31) + E[:, 0]
    has_rev = np.isin(key_d, key_r)
    return E[~has_rev]

def extract(V, F, N, mask, extra=None):
    """Sub-mesh of faces in mask with compact vertex indices."""
    Fm = F[mask]
    used = np.unique(Fm)
    remap = -np.ones(len(V), np.int64); remap[used] = np.arange(len(used))
    ex = {k: v[used] for k, v in (extra or {}).items()}
    return V[used].copy(), remap[Fm], N[used].copy(), ex

def wall_strip(Vtop, Vbot, edges):
    """Quads between boundary edges (u->v) of a patch at Vtop and the same indices in Vbot (offset copy).
    Faces point toward the patch interior. Returns V, F."""
    u = edges[:, 0]; v = edges[:, 1]
    n = len(edges)
    Vw = np.concatenate([Vtop[u], Vtop[v], Vbot[v], Vbot[u]])
    i = np.arange(n)
    a, b, c, d = i, i + n, i + 2 * n, i + 3 * n
    Fw = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    return Vw, Fw

# ---------------------------------------------------------------- primitives (numpy meshes)
def revolve(profile, n_seg, axis_pts=None, closed_profile=False, uv=True):
    """Revolve a 2D profile [(x_axial, r)] around the x axis. Returns V (x,y,z), F, UV."""
    P = np.asarray(profile, float); m = len(P)
    th = np.linspace(0, 2 * np.pi, n_seg + 1)
    X = np.repeat(P[:, 0][None, :], n_seg + 1, 0)
    R = np.repeat(P[:, 1][None, :], n_seg + 1, 0)
    Y = R * np.cos(th)[:, None]; Z = R * np.sin(th)[:, None]
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    # profile arc-length for v
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    U = np.repeat((th / (2 * np.pi))[:, None], m, 1); W = np.repeat((seg / max(seg[-1], 1e-9))[None, :], n_seg + 1, 0)
    UV = np.stack([U, W], -1).reshape(-1, 2)
    idx = np.arange((n_seg + 1) * m).reshape(n_seg + 1, m)
    mm = m if closed_profile else m - 1
    F = []
    for j in range(mm):
        j2 = (j + 1) % m
        a = idx[:-1, j]; b = idx[1:, j]; c = idx[1:, j2]; d = idx[:-1, j2]
        F.append(np.stack([a, b, c], 1)); F.append(np.stack([a, c, d], 1))
    F = np.concatenate(F)
    return V, F, UV

def tube(path, radius, n_seg=10, closed=False, caps=True):
    """Tube mesh along a polyline path (k,3)."""
    P = np.asarray(path, float); k = len(P)
    T = np.gradient(P, axis=0); T = normalize(T)
    ref = np.array([0, 0, 1.0])
    Nn = np.cross(T, ref)
    bad = np.linalg.norm(Nn, axis=1) < 1e-3
    Nn[bad] = np.cross(T[bad], [1.0, 0, 0])
    Nn = normalize(Nn); B = np.cross(T, Nn)
    th = np.linspace(0, 2 * np.pi, n_seg, endpoint=False)
    rad = np.broadcast_to(np.asarray(radius, float), (k,))
    ring = (np.cos(th)[None, :, None] * Nn[:, None, :] + np.sin(th)[None, :, None] * B[:, None, :])
    V = (P[:, None, :] + ring * rad[:, None, None]).reshape(-1, 3)
    Nv = ring.reshape(-1, 3)
    idx = np.arange(k * n_seg).reshape(k, n_seg)
    F = []
    rows = k if closed else k - 1
    for i in range(rows):
        i2 = (i + 1) % k
        for j in range(n_seg):
            j2 = (j + 1) % n_seg
            a, b, c, d = idx[i, j], idx[i2, j], idx[i2, j2], idx[i, j2]
            F += [[a, d, c], [a, c, b]]
    F = np.asarray(F, np.int64)
    if caps and not closed:
        c0 = len(V); c1 = c0 + 1
        V = np.concatenate([V, P[:1], P[-1:]]); Nv = np.concatenate([Nv, -T[:1], T[-1:]])
        cap = []
        for j in range(n_seg):
            j2 = (j + 1) % n_seg
            cap.append([c0, idx[0, j2], idx[0, j]]); cap.append([c1, idx[-1, j], idx[-1, j2]])
        F = np.concatenate([F, np.asarray(cap)])
    return V, F

def box(c, half, rot=None):
    c = np.asarray(c, float); h = np.asarray(half, float)
    s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * h
    if rot is not None: s = s @ np.asarray(rot).T
    V = s + c
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    # ensure outward winding
    fn = face_normals(V, F); cen = V[F].mean(1) - c
    flip = np.einsum('ij,ij->i', fn, cen) < 0
    F[flip] = F[flip][:, ::-1]
    return V, F

def rot_x(a):
    c, s = np.cos(a), np.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def rot_y(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rot_z(a):
    c, s = np.cos(a), np.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def mc_part(field, lo, hi, res, target=None, smooth_normals=True):
    """Implicit field(X,S,Z) -> decimated mesh with analytic normals."""
    V, F = mc_mesh(field, lo, hi, res)
    if target and len(F) > target:
        V, F = decimate(V, F, target, preserve_border=False)
    N = field_normals(lambda x, s, z: field(x, s, z), V)
    F = fix_winding(V, F, N)
    return V, F, N

class Parts:
    """Collects mesh pieces: node -> list of dict(V,F,N,mat,UV,COL)."""
    def __init__(self):
        self.nodes = {}
    def add(self, node, V, F, mat, N=None, UV=None, COL=None, flat=False):
        if len(F) == 0: return
        V = np.asarray(V, float); F = np.asarray(F, np.int64)
        if N is None:
            N = vertex_normals(V, F)
        self.nodes.setdefault(node, []).append(dict(V=V, F=F, N=np.asarray(N, float), mat=mat, UV=UV, COL=COL, flat=flat))
    def tris(self, node=None):
        return sum(len(p['F']) for n, L in self.nodes.items() if node in (None, n) for p in L)

def project_to_surface(field, V, iters=4, h=0.0015):
    """Newton-project vertices onto field == 0."""
    V = V.copy()
    for _ in range(iters):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]
        f0 = field(x, s, z)
        g = np.stack([field(x + h, s, z) - field(x - h, s, z), field(x, s + h, z) - field(x, s - h, z),
                      field(x, s, z + h) - field(x, s, z - h)], 1) / (2 * h)
        g2 = np.maximum((g * g).sum(1), 1e-6)
        step = (f0 / g2)[:, None] * g
        sl = np.linalg.norm(step, axis=1, keepdims=True)
        step = step * np.minimum(1, 0.02 / np.maximum(sl, 1e-12))
        V -= step
    return V

def smooth_normals(V, F, N, iters=4, lam=0.6):
    """Average normals over the 1-ring (area weighted by shared faces) to iron out small wrinkles."""
    from scipy import sparse
    n = len(V)
    i = np.concatenate([F[:, 0], F[:, 1], F[:, 2], F[:, 1], F[:, 2], F[:, 0]])
    j = np.concatenate([F[:, 1], F[:, 2], F[:, 0], F[:, 0], F[:, 1], F[:, 2]])
    A = sparse.csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    deg = np.asarray(A.sum(1)).ravel(); deg[deg == 0] = 1
    for _ in range(iters):
        avg = (A @ N) / deg[:, None]
        N = normalize((1 - lam) * N + lam * avg)
    return N
