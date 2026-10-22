"""Joshua tree (Yucca brevifolia) generator — 4 variants + LOD1, exported as GLB.

usage: python3 joshua.py [a b c d] [--lod-only] [--seed N]

Anatomy modelled
- Skeleton: sympodial Y-forks, stout crooked limbs that turn upward; pipe-model radii; root flare on old trunks.
- Every branch carries one continuous phyllotaxis spiral of leaves, classified by distance s from its tip:
    s < LIVE      living rosette: stiff keeled dagger leaves, blue-green/olive, radiating like a sea urchin
    LIVE..DEAD    transition band: yellowing leaves folding downward
    DEAD..FUR     the skirt: grey-straw dead leaves pressed downward, overlapping like thatch
    beyond FUR    shed: corky, furrowed grey bark, a few straggling dead leaves at the ragged skirt edge
- Under the blades a thatch "core" tube (texture of packed dead leaves) gives the skirt its density.
- Ambient occlusion: voxel sky-visibility over the whole tree + per-blade base darkening, baked to COLOR_0.
Materials: bark (bark texture + normal), fur (thatch core + dead blades, double-sided), leaf (double-sided).
Blender Z-up during build; exported +Y up. Origin at the trunk base.
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import (nrm, rodrigues, perp, smoothstep, Part, bpy_reset, build_object, make_material, export_glb,
                    glb_info, voxel_ao, TEXCACHE, ASSETS)

UP = np.array([0, 0, 1.0])

VARIANTS = {
    # young: single trunk ~3 m, one or two terminal rosettes, fur nearly to the ground
    'a': dict(seed=11, height=3.0, trunk_len=2.1, trunk_lean=0.06, levels=1, nfork=(2, 2), p_branch=1.0,
              seg_len=(0.45, 0.75), tilt=(28, 40), up_pull=1.2, kink=0.10, r_tip=0.07, r_exp=0.42, flare=0.15, r_trunk=0.14, fur_z=0.5,
              fur_len=2.6, budget=60000, live_n=520),
    # ~5 m, forks into 2–4 branches
    'b': dict(seed=4, height=5.0, trunk_len=2.5, trunk_lean=0.08, levels=2, nfork=(2, 3), p_branch=0.6,
              seg_len=(1.0, 1.5), tilt=(38, 60), up_pull=0.9, kink=0.16, r_tip=0.07, r_exp=0.55, flare=0.2, r_trunk=0.18, fur_z=1.0,
              fur_len=2.6, budget=68000, live_n=480),
    # mature ~7 m, many branches, classic silhouette
    'c': dict(seed=21, height=7.0, trunk_len=2.5, trunk_lean=0.07, levels=4, nfork=(2, 3), p_branch=0.8,
              seg_len=(0.9, 1.4), tilt=(48, 75), up_pull=0.55, kink=0.18, r_tip=0.065, r_exp=0.52, flare=0.25, r_trunk=0.25, fur_z=1.2,
              fur_len=2.3, budget=69000, live_n=300),
    # old ~9 m, broad crown, thick trunk
    'd': dict(seed=37, height=9.0, trunk_len=2.6, trunk_lean=0.05, levels=4, nfork=(2, 3), p_branch=0.85,
              seg_len=(0.9, 1.3), tilt=(42, 66), up_pull=0.6, kink=0.2, r_tip=0.07, r_exp=0.56, flare=0.3, r_trunk=0.38, fur_z=1.5,
              fur_len=2.5, budget=69500, live_n=220),
}

LIVE = 0.30      # living rosette length along the stem (m)
DEAD = 0.44      # end of the yellowing transition band


# =================================================================================================== skeleton
class Branch:
    def __init__(self, pts, parent, depth):
        self.pts = np.array(pts)
        self.parent = parent
        self.depth = depth
        self.children = []
        self.ntips = 0


def grow_skeleton(P, rng):
    branches = []
    step = 0.07

    def grow(p0, d0, length, depth, parent):
        pts = [p0.copy()]
        p, d = p0.copy(), nrm(d0)
        n = max(3, int(length / step))
        kink_dir = perp(d[None])[0]
        for i in range(n):
            # crooked growth: occasional kinks, steady upward turning
            if rng.random() < step / 0.35:
                kink_dir = nrm(rodrigues(perp(d[None]), d[None], [rng.uniform(0, 2 * math.pi)]))[0]
            pull = P['up_pull'] if depth > 0 else 1.6
            d = nrm(d + UP * pull * step * (1 - d[2]) * 1.2 + kink_dir * P['kink'] * step * 2.0
                    + rng.normal(0, 0.02, 3))
            p = p + d * step
            pts.append(p.copy())
        b = Branch(pts, parent, depth)
        branches.append(b)
        if parent is not None:
            parent.children.append(b)
        top_ok = p[2] < P['height'] - 0.55
        if depth < P['levels'] and top_ok and rng.random() < (P['p_branch'] if depth > 0 else 1.0):
            lo, hi = P['nfork']
            k = rng.integers(lo, hi + 1)
            if depth == 0 and P['levels'] >= 3:
                k = max(k, 3)
            phi0 = rng.uniform(0, 2 * math.pi)
            # outward bias: lean children away from the trunk axis to open the crown
            out = np.array([p[0], p[1], 0.0])
            out = out / (np.linalg.norm(out) + 1e-9) if np.linalg.norm(out) > 0.15 else np.zeros(3)
            e1 = perp(d[None])[0]; e2 = np.cross(d, e1)
            for j in range(k):
                phi = phi0 + 2 * math.pi * j / k + rng.normal(0, 0.35)
                tilt = math.radians(rng.uniform(*P['tilt']))
                cd = d * math.cos(tilt) + (e1 * math.cos(phi) + e2 * math.sin(phi)) * math.sin(tilt)
                cd = nrm(cd + out * 0.35)
                L = rng.uniform(*P['seg_len']) * (0.85 ** max(0, depth - 1))
                # remaining height limits length
                grow(p - d * 0.05, cd, L, depth + 1, b)
        return b

    lean = nrm(UP + np.r_[rng.normal(0, P['trunk_lean'], 2), 0])
    root = grow(np.zeros(3), lean, P['trunk_len'], 0, None)
    if P['levels'] == 1:   # young: maybe one short side shoot near the top (counted as level 1 child)
        pass
    return branches, root


def finish_skeleton(branches, root, P):
    # scale so the crown top (rosettes reach ~0.25 m above the tip) lands on the target height
    top = max(b.pts[:, 2].max() for b in branches) + 0.25
    k = P['height'] / top
    for b in branches:
        b.pts = b.pts * np.array([k ** 0.6, k ** 0.6, k])
    # tips and pipe-model radii
    def count(b):
        b.ntips = 1 if not b.children else sum(count(c) for c in b.children)
        return b.ntips
    count(root)

    # cumulative arclength, distance-from-tip s
    for b in branches:
        seg = np.linalg.norm(np.diff(b.pts, axis=0), axis=1)
        b.arc = np.r_[0, np.cumsum(seg)]
        b.length = b.arc[-1]

    def s_assign(b):
        if not b.children:
            s_end = 0.0
        else:
            s_end = max(s_assign(c) for c in b.children)
        b.s = s_end + (b.length - b.arc)
        return b.s[0]
    s_assign(root)

    for b in branches:
        r_start = P['r_tip'] * (b.ntips ** P['r_exp']) * (1.08 if b.children else 1.2)
        if b.children:
            r_end = 1.08 * max(P['r_tip'] * (c.ntips ** P['r_exp']) * (1.08 if c.children else 1.2) for c in b.children)
        else:
            r_end = P['r_tip']
        t = b.arc / max(b.length, 1e-6)
        r = r_start + (r_end - r_start) * t
        if b.parent is None:
            z = b.pts[:, 2]
            r = r * (1 + P['flare'] * np.exp(-z / 0.35))
        b.r = r
    # pipe-model radii overshoot for yuccas (wood is fibrous, not secondary-thickened like an oak):
    # compress so the trunk base radius (before flare) equals r_trunk, tips stay at r_tip
    r0 = root.r[root.pts[:, 2] > 0.5].max() if (root.pts[:, 2] > 0.5).any() else root.r.max()
    g = math.log(P['r_trunk'] / P['r_tip']) / max(math.log(r0 / P['r_tip']), 1e-6)
    for b in branches:
        z = b.pts[:, 2]
        fl = (1 + P['flare'] * np.exp(-z / 0.35)) if b.parent is None else 1.0
        base = b.r / fl
        b.r = P['r_tip'] * np.maximum(base / P['r_tip'], 1e-3) ** g * fl
    return branches


# =================================================================================================== frames
def frames(pts):
    T = np.gradient(pts, axis=0)
    T = nrm(T)
    N = np.zeros_like(T)
    N[0] = perp(T[:1])[0]
    for i in range(1, len(T)):
        v = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        N[i] = v / (np.linalg.norm(v) + 1e-12)
    B = np.cross(T, N)
    return T, N, B


def sample_curve(b, s_vals):
    """Points, tangents, frame N, radius at given distances-from-tip s along branch b."""
    arc = b.length - (s_vals - b.s[-1])
    arc = np.clip(arc, 0, b.length)
    idx = np.clip(np.searchsorted(b.arc, arc) - 1, 0, len(b.arc) - 2)
    f = ((arc - b.arc[idx]) / np.maximum(b.arc[idx + 1] - b.arc[idx], 1e-9))[:, None]
    p = b.pts[idx] * (1 - f) + b.pts[idx + 1] * f
    T = nrm(b.T[idx] * (1 - f) + b.T[idx + 1] * f)
    N = b.N[idx] * (1 - f) + b.N[idx + 1] * f
    N = nrm(N - T * np.sum(N * T, 1, keepdims=True))
    r = b.r[idx] * (1 - f[:, 0]) + b.r[idx + 1] * f[:, 0]
    return p, T, N, r, arc


# =================================================================================================== tubes
def tube(part_bark, part_core, b, P, rng, lod=False):
    """Trunk/branch surface. Rings every ~0.09 m. Each quad is bark or thatch-core: the boundary is ragged
    (s + angular noise), the thatch core swells smoothly out of the bark above the skirt edge."""
    n_r = max(4, int(b.length / (0.16 if lod else 0.09)))
    arc = np.linspace(0, b.length, n_r + 1)
    s = b.length - arc + b.s[-1]
    p, T, N, r, _ = sample_curve(b, s)
    Bv = np.cross(T, N)
    rmax = b.r.max()
    sides = 6 if lod else int(np.clip(round(rmax * 55), 9, 22))
    ang = np.linspace(0, 2 * math.pi, sides + 1)
    A = ang[None, :]
    fur_len = P['fur_len']
    # ragged skirt edge: boundary s varies around the stem by ±0.25 m
    ph = rng.uniform(0, 6.28, 3)
    edge = fur_len + 0.12 + 0.13 * np.sin(A * 2 + ph[0]) + 0.08 * np.sin(A * 3 + ph[1]) + 0.05 * np.sin(A * 5 + ph[2])
    zfur = P['fur_z'] + (edge - fur_len - 0.12) * 1.2                     # ragged lower edge of the trunk skirt
    furness = smoothstep(edge + 0.02, edge - 0.40, s[:, None])        # 0 bark → 1 full thatch (per vertex)
    if b.depth <= 1:
        furness = np.maximum(furness, smoothstep(zfur - 0.05, zfur + 0.4, p[:, 2:3]))
    core_extra = (0.075 if lod else 0.05) * furness
    rad = r[:, None] + core_extra
    if not b.children:          # apex: the stem narrows into the terminal bud inside the rosette
        rad = rad * (0.25 + 0.75 * smoothstep(0.0, 0.16, s))[:, None]
    phase = rng.uniform(0, 6.28)
    bark_mod = 1 + (1 - furness) * (0.05 * np.sin(A * 7 + phase + 0.8 * np.sin(arc[:, None] * 3))
                                    + 0.035 * np.sin(A * 13 + 2 * phase + arc[:, None] * 1.7))
    R = rad * bark_mod
    radial = np.cos(A)[..., None] * N[:, None, :] + np.sin(A)[..., None] * Bv[:, None, :]
    pos = p[:, None, :] + radial * R[..., None]
    nor = radial
    circ = 2 * math.pi * r.mean()
    W = sides + 1
    v_all = pos.reshape(-1, 3); n_all = nor.reshape(-1, 3)
    sv = np.repeat(s, W)
    i = np.arange(n_r)[:, None] * W + np.arange(sides)[None, :]
    quad_fur = (furness[:-1, :-1] + furness[1:, :-1] + furness[:-1, 1:] + furness[1:, 1:]) * 0.25 > 0.35
    for fur in (False, True):
        q = i[quad_fur == fur]
        if len(q) == 0:
            continue
        tris = np.concatenate([np.stack([q, q + 1, q + W], -1), np.stack([q + 1, q + W + 1, q + W], -1)])
        tile = 0.32 if fur else 0.55
        nu = max(1, round(circ / tile))
        U = np.tile(ang / (2 * math.pi) * nu, n_r + 1)
        V = np.repeat(arc / tile, W)
        tone = np.ones((len(v_all), 3))
        if fur:
            tone *= np.array([0.50, 0.47, 0.43]) * (0.55 + 0.45 * furness.ravel())[:, None]   # darker where thin
            g = smoothstep(DEAD, 0.0, sv)[:, None]
            tone = tone * (1 - g) + g * np.array([0.30, 0.34, 0.22])
        else:
            tone *= rng.uniform(0.92, 1.08)
        used = np.unique(tris)
        remap = -np.ones(len(v_all), int); remap[used] = np.arange(len(used))
        (part_core if fur else part_bark).add(v_all[used], remap[tris], n=n_all[used],
                                              c=np.c_[tone[used], sv[used]], uv=np.c_[U, V][used])
    # cap the tip (hidden under the rosette)
    if not b.children:
        c0 = p[-1] + T[-1] * 0.01
        ring = pos[-1]
        k = len(ring)
        v = np.vstack([ring, c0[None]])
        tris = np.stack([np.arange(k - 1), np.full(k - 1, k), np.arange(1, k)], 1)
        part_core.add(v, tris, n=np.tile(T[-1], (k + 1, 1)), c=np.c_[np.tile([0.3, 0.34, 0.22], (k + 1, 1)), np.zeros(k + 1)],
                      uv=np.zeros((k + 1, 2)))


# =================================================================================================== blades
def blade_geometry(base, d, w_dir, out_dir, L, W, bend, keel, rows, droop=None):
    """Vectorised blade strips. base,d,w_dir,out_dir (n,3); L,W,bend,keel (n,). rows: list of (t, width_frac).
    Each row has 3 verts (left, mid, right) if keel else 2; final tip is a single vertex.
    bend: curvature toward out_dir (positive bends the blade outward along its length).
    Returns verts (n, nv, 3), uv (nv, 2), tris (nt, 3) template, t-param per vert (nv,)."""
    n = len(base)
    vs, uvs, ts = [], [], []
    cols = 3 if keel is not None else 2
    for (t, wf) in rows:
        # centreline with bend (quadratic) and optional droop vector
        c = base + d * (L * t)[:, None] + out_dir * (bend * L * t * t)[:, None]
        if droop is not None:
            c = c + droop * (L * t * t * t)[:, None]
        hw = (W * wf * 0.5)[:, None]
        if cols == 3:
            vs += [c - w_dir * hw, c + out_dir * (keel * W * wf)[:, None], c + w_dir * hw]
            uvs += [(0, t), (0.5, t), (1, t)]
            ts += [t, t, t]
        else:
            vs += [c - w_dir * hw, c + w_dir * hw]
            uvs += [(0, t), (1, t)]
            ts += [t, t]
    tip = base + d * L[:, None] + out_dir * (bend * L)[:, None]
    if droop is not None:
        tip = tip + droop * L[:, None]
    vs.append(tip); uvs.append((0.5, 1.0)); ts.append(1.0)
    V = np.stack(vs, 1)
    tris = []
    nr = len(rows)
    for r in range(nr - 1):
        a = r * cols
        bb = (r + 1) * cols
        for c in range(cols - 1):
            tris += [(a + c, a + c + 1, bb + c), (a + c + 1, bb + c + 1, bb + c)]
    tipi = nr * cols
    a = (nr - 1) * cols
    for c in range(cols - 1):
        tris.append((a + c, a + c + 1, tipi))
    return V, np.array(uvs, float), np.array(tris), np.array(ts)


def add_blades(part, V, uv_t, tris_t, t_t, normals_hint, colors, svals, uv_off=None, uv_scale=(1.0, 1.0)):
    """Append n blades. Winding is fixed so the geometric normal agrees with normals_hint (n,3)."""
    n, nv, _ = V.shape
    # winding check on the first triangle of each blade
    a, b_, c = tris_t[0]
    fn = np.cross(V[:, b_] - V[:, a], V[:, c] - V[:, a])
    flip = np.sum(fn * normals_hint, 1) < 0
    base_idx = (np.arange(n) * nv)[:, None, None]
    T = tris_t[None, :, :] + base_idx
    T = np.where(flip[:, None, None], T[:, :, ::-1], T)
    # per-vertex shading normal: blade face normal bent toward the hint (softer, foliage-like)
    fnn = nrm(fn) * np.where(flip, -1, 1)[:, None]
    sn = nrm(fnn * 0.55 + normals_hint)
    Nn = np.repeat(sn[:, None, :], nv, 1)
    C = colors.reshape(n, nv, 3) if colors.ndim == 3 else np.repeat(colors[:, None, :], nv, 1)
    S = np.repeat(svals[:, None], nv, 1)
    UV = np.repeat((uv_t * np.array(uv_scale))[None], n, 0)
    if uv_off is not None:
        UV = UV + uv_off[:, None, :]
    part.add(V.reshape(-1, 3), T.reshape(-1, 3), n=Nn.reshape(-1, 3),
             c=np.concatenate([C.reshape(-1, 3), S.reshape(-1, 1)], 1), uv=UV.reshape(-1, 2))


def fur_weight(b, s, P):
    """0..1 amount of dead-leaf skirt at distances-from-tip s on branch b: young wood (s < fur_len) always,
    plus the upper trunk and first limbs above fur_z (the classic shaggy skirt from ~1 m up)."""
    w = smoothstep(P['fur_len'] + 0.35, P['fur_len'] - 0.1, s)
    if b.depth <= 1:
        z = sample_curve(b, s)[0][:, 2]
        w = np.maximum(w, smoothstep(P['fur_z'] - 0.15, P['fur_z'] + 0.45, z))
    return w


def leaves_for_branch(b, P, rng, parts, dens_live, dens_fur, lod=False):
    """Phyllotaxis spiral of leaves along branch b, classified by distance from tip."""
    s0 = b.s[-1]                      # s at this branch's tip end (0 for terminal branches)
    s1 = b.s[0]
    fur_len = P['fur_len']
    straggle = 0.35
    s_hi = s1
    if s_hi <= s0:
        return
    # sample s by integrating density (dead blades per m² of skirt surface → per metre ∝ circumference)
    grid = np.linspace(s0, s_hi, 400)
    rr = sample_curve(b, grid)[3]
    circ = (rr + 0.05) / 0.12
    dens = np.where(grid < LIVE, dens_live, np.where(grid < DEAD, dens_live * 0.6, dens_fur * circ * fur_weight(b, grid, P)))
    if not b.children:
        pass
    else:
        dens = np.where(grid < DEAD, 0, dens)              # no rosette at a fork
    cum = np.r_[0, np.cumsum((dens[1:] + dens[:-1]) * 0.5 * np.diff(grid))]
    total = cum[-1]
    n = int(rng.poisson(total)) if total > 0 else 0
    if n == 0:
        return
    u = np.sort(rng.random(n)) * total
    s = np.interp(u, cum, grid)
    p, T, N, r, _ = sample_curve(b, s)
    Bv = np.cross(T, N)
    phi = np.arange(n) * 2.39996323 + rng.uniform(0, 6.28) + rng.normal(0, 0.12, n)
    Nr = np.cos(phi)[:, None] * N + np.sin(phi)[:, None] * Bv          # radial direction around the stem
    Wd = nrm(np.cross(T, Nr))                                          # circumferential

    live = s < LIVE
    trans = (s >= LIVE) & (s < DEAD)
    dead = s >= DEAD
    # ------------------------------------------------------------------ living leaves (+ transition)
    idx = np.flatnonzero(live | trans)
    if len(idx):
        ss = s[idx]
        q = ss / LIVE
        theta = np.where(ss < LIVE, np.radians(4 + 106 * q ** 0.8),
                         np.radians(110 + 45 * (ss - LIVE) / (DEAD - LIVE)))
        theta = theta + np.radians(rng.normal(0, 9, len(idx)))
        d = np.cos(theta)[:, None] * T[idx] + np.sin(theta)[:, None] * Nr[idx]
        # stiff, straight, slight random splay sideways
        d = nrm(d + Wd[idx] * rng.normal(0, 0.10, len(idx))[:, None])
        # adaxial (upper, channelled) side of the leaf: perpendicular to d in the (T, Nr) plane
        out_dir = nrm(-np.sin(theta)[:, None] * T[idx] + np.cos(theta)[:, None] * Nr[idx])
        wdir = nrm(np.cross(d, out_dir))
        L = rng.uniform(0.18, 0.34, len(idx)) * (0.55 + 0.45 * smoothstep(0.0, 0.06, ss))
        if lod:
            L *= 1.05
        W = rng.uniform(0.010, 0.014, len(idx)) * (1 + 0.15 * (L > 0.28))
        # leaves droop a little at the transition; living ones dead straight with tiny bend
        bend = np.where(ss < LIVE, rng.normal(0.0, 0.02, len(idx)), rng.uniform(0.02, 0.10, len(idx)))
        taper = (0.25 + 0.75 * smoothstep(0.0, 0.16, ss)) if not b.children else np.ones(len(ss))
        base = p[idx] + Nr[idx] * ((r[idx] + 0.05) * taper * 0.85)[:, None]
        if lod:
            V, uvt, trt, tt = blade_geometry(base, d, wdir, out_dir, L, W * 1.8, bend, None, [(0.0, 1.0)])
        else:
            V, uvt, trt, tt = blade_geometry(base, d, wdir, out_dir, L, W, bend, np.full(len(idx), -0.25),
                                             [(0.0, 1.0)])
        # colour per leaf: blue-green ↔ olive, with transition → yellow → straw
        k = rng.random(len(idx))
        green = np.array([0.105, 0.165, 0.085]) * (1 - k)[:, None] + np.array([0.145, 0.195, 0.085]) * k[:, None]
        green *= rng.uniform(0.85, 1.15, len(idx))[:, None]
        green[:, 2] *= rng.uniform(0.9, 1.25, len(idx))           # some bluer
        yel = np.array([0.36, 0.27, 0.09]) * rng.uniform(0.85, 1.1, len(idx))[:, None]
        straw = np.array([0.40, 0.36, 0.28]) * rng.uniform(0.85, 1.1, len(idx))[:, None]
        tt_ = np.clip((ss - LIVE) / (DEAD - LIVE), 0, 1)[:, None]
        # a few leaves in the living zone already browning at the tip (natural)
        col = np.where(tt_ < 0.5, green + (yel - green) * (tt_ * 2), yel + (straw - yel) * (tt_ * 2 - 1))
        col = col / 0.86 * 0.9
        nv = V.shape[1]
        # per-vertex: darker toward the leaf base (inside the rosette)
        ao_t = 0.42 + 0.58 * smoothstep(0.0, 0.8, tt)
        C = col[:, None, :] * ao_t[None, :, None]
        # tip spine browns: handled by the texture
        center = p[idx] - T[idx] * 0.08
        hint = nrm(V[:, -1] - center)                       # radial from rosette centre
        add_blades(parts['leaf'], V, uvt, trt, tt, nrm(hint + out_dir * 0.3), C, ss)
    # ------------------------------------------------------------------ dead fur blades
    idx = np.flatnonzero(dead)
    if len(idx):
        ss = s[idx]
        m = len(idx)
        flare = np.radians(np.where(rng.random(m) < 0.10, rng.uniform(22, 45, m), rng.uniform(4, 16, m)))
        # pointing back down the branch, flared out from the stem
        d = -np.cos(flare)[:, None] * T[idx] + np.sin(flare)[:, None] * Nr[idx]
        d = nrm(d + np.array([0, 0, -0.35]) * (1 - np.abs(T[idx][:, 2:3])) + Wd[idx] * rng.normal(0, 0.15, m)[:, None])
        out_dir = nrm(Nr[idx] - d * np.sum(Nr[idx] * d, 1, keepdims=True))
        wdir = nrm(np.cross(d, out_dir))
        L = rng.uniform(0.16, 0.30, m)
        W = rng.uniform(0.012, 0.022, m) * (1.6 if lod else 1.0)
        bend = rng.uniform(-0.02, 0.10, m)          # most tips curl outward a little
        lift = (r[idx] + 0.035)
        base = p[idx] + Nr[idx] * lift[:, None] + T[idx] * (L * 0.15)[:, None]
        droop = np.tile([0, 0, -1.0], (m, 1)) * rng.uniform(0.0, 0.06, m)[:, None]
        if lod:
            groups = [(np.arange(m), [(0.0, 1.0)])]
        else:
            thin = rng.random(m) < 0.6
            W = np.where(thin, W * 0.55, W * 1.1)
            L = np.where(thin, L * 1.1, L)
            groups = [(np.flatnonzero(thin), [(0.0, 1.0)]), (np.flatnonzero(~thin), [(0.0, 1.0), (0.6, 0.75)])]
        for gi, rows in groups:
            if len(gi) == 0:
                continue
            Vg, uvt, trt, tt = blade_geometry(base[gi], d[gi], wdir[gi], out_dir[gi], L[gi], W[gi], bend[gi], None,
                                              rows, droop=droop[gi])
            fur_emit(parts['fur'], Vg, uvt, trt, tt, gi, flare, out_dir, Nr[idx], ss, rng, m)


def fur_emit(part, V, uvt, trt, tt, gi, flare, out_dir, Nr, ss, rng, m):
    n = len(gi)
    tone = rng.uniform(0.82, 1.12, n)
    dark = rng.random(n) < 0.15
    tone[dark] *= 0.6
    warm = rng.normal(0, 0.025, n)
    col = np.array([0.43, 0.395, 0.335])[None, :] * tone[:, None]
    col[:, 0] += warm; col[:, 2] -= warm * 0.7
    under = 0.75 + 0.25 * smoothstep(0.08, 0.5, flare[gi])      # flatter blades are under-layers: darker
    col *= under[:, None]
    col = col / 0.85
    ao_t = 0.55 + 0.45 * smoothstep(0.0, 0.7, tt)
    C = col[:, None, :] * ao_t[None, :, None]
    uvo = np.c_[rng.random(n), rng.random(n)]          # each blade samples a narrow strip of the thatch texture
    add_blades(part, V, 1 - uvt, trt, tt, nrm(out_dir[gi] * 1.0 + Nr[gi] * 0.5), C, ss[gi],
               uv_off=uvo, uv_scale=(0.02, 0.25))


# =================================================================================================== AO
def bake_ao(parts, strength=1.0, cell=0.09):
    pts, w = [], []
    for k, part in parts.items():
        arr = part.arrays()
        if arr is None:
            continue
        v, t, n, c, uv = arr
        pts.append(v)
        w.append(np.full(len(v), {'leaf': 0.10, 'fur': 0.16, 'bark': 0.5}[k]))
    P = np.concatenate(pts); W = np.concatenate(w)
    for k, part in parts.items():
        arr = part.arrays()
        if arr is None:
            continue
        v, t, n, c, uv = arr
        vis = voxel_ao(v + n * 0.04, P, W, cell=cell, sigma=strength)
        ao = 0.30 + 0.70 * np.clip(vis, 0, 1) ** 0.9
        c = c.copy()
        c[:, :3] *= ao[:, None]
        # rebuild the part as one chunk
        part.v, part.t, part.n, part.c, part.uv = [v], [t], [n], [c], [uv]
        part.count = len(v)


# =================================================================================================== build
def build_tree(name, P, lod=False, seed_override=None):
    rng = np.random.default_rng(P['seed'] if seed_override is None else seed_override)
    branches, root = grow_skeleton(P, rng)
    finish_skeleton(branches, root, P)
    for b in branches:
        b.T, b.N, b.B = frames(b.pts)
    tips = [b for b in branches if not b.children]
    parts = {'bark': Part(), 'fur': Part(), 'leaf': Part()}
    for b in branches:
        tube(parts['bark'], parts['fur'], b, P, rng, lod=lod)
    tube_tris = parts['bark'].ntris + parts['fur'].ntris
    # density from budget
    fur_length = 0.0
    for b in branches:
        g = np.linspace(max(b.s[-1], DEAD), max(b.s[0], DEAD), 200)
        if g[-1] > g[0]:
            rr = sample_curve(b, g)[3]
            w = fur_weight(b, g, P) * (rr + 0.05) / 0.12
            fur_length += float(np.sum((w[1:] + w[:-1]) * 0.5 * np.diff(g)))
    if lod:
        live_n, leaf_tris, blade_tris, budget = int(min(70, 2600 / len(tips))), 1, 1, 7600
    else:
        live_n, leaf_tris, blade_tris, budget = P['live_n'], 2, 1.8, P['budget']
    dens_live = live_n / LIVE
    live_tris = len(tips) * (live_n + live_n * 0.6 * (DEAD - LIVE) / LIVE * 0 + 0.6 * dens_live * (DEAD - LIVE)) * leaf_tris
    remain = budget - tube_tris - live_tris
    dens_fur = max(2.0, remain / blade_tris / max(fur_length, 0.1))
    for b in branches:
        leaves_for_branch(b, P, rng, parts, dens_live, dens_fur, lod=lod)
    if not lod:
        bake_ao(parts, strength=1.0, cell=0.09)
    else:
        bake_ao(parts, strength=0.8, cell=0.15)
    stats = {k: v.ntris for k, v in parts.items()}
    build_tree.tips = [[float(b.pts[-1][0]), float(b.pts[-1][2]), float(-b.pts[-1][1])] for b in tips]
    return parts, stats, len(tips), dens_fur


def materials(lod=False):
    bark = make_material('bark', base=os.path.join(TEXCACHE, 'bark_albedo.jpg'),
                         normal=os.path.join(TEXCACHE, 'bark_normal.jpg'), normal_strength=1.0, rough=0.92)
    fur = make_material('fur', base=os.path.join(TEXCACHE, 'thatch_albedo.jpg'),
                        normal=None if lod else os.path.join(TEXCACHE, 'thatch_normal.jpg'),
                        rough=0.9, double=True)
    leaf = make_material('leaf', base=os.path.join(TEXCACHE, 'leaf_albedo.png'), rough=0.72, double=True)
    return dict(bark=bark, fur=fur, leaf=leaf)


def export_tree(key, lod=False):
    P = VARIANTS[key]
    t0 = time.time()
    parts, stats, ntips, df = build_tree(key, P, lod=lod)
    # the fur blades and the thatch core share 'fur' (core uses the thatch texture; blades use the same texture
    # via u∈[0,1], v∈[0,1] – one blade spans one leaf-length of the thatch, which reads as fibres)
    bpy = bpy_reset()
    mats = materials(lod)
    name = f'joshua_{key}' + ('_lod1' if lod else '')
    build_object(name, parts, mats)
    path = os.path.join(ASSETS, name + '.glb')
    export_glb(path)
    info = glb_info(path)
    if not lod:
        import json
        json.dump(build_tree.tips, open(os.path.join(os.path.dirname(__file__), '_tex', name + '_tips.json'), 'w'))
    print(f'{name}: tips={ntips} fur_density={df:.0f}/m parts={stats} total={info["tris"]} '
          f'size={info["bytes"]/1e6:.2f}MB  {time.time()-t0:.1f}s', flush=True)
    return info


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    keys = args or ['a', 'b', 'c', 'd']
    for k in keys:
        if '--lod-only' not in sys.argv:
            export_tree(k)
        if '--no-lod' not in sys.argv:
            export_tree(k, lod=True)
