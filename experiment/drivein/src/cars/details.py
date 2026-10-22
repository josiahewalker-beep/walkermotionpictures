"""Helpers shared by both cars: projected 2D feature functions, ray-surface queries, small parts
(mirrors, wipers, plates, grille mesh, LED strips, interior pieces), material table, vertex AO."""
import numpy as np
from carlib import (SDF2D, mirror_half, catmull_closed, smin, smax, sstep, normalize, mc_mesh, decimate,
                    field_normals, fix_winding, project_to_surface, tube, box, revolve, vertex_normals, rot_x, rot_z)

BIG = 1.0

def proj_fn(outline, plane, domain=None, res=0.002, mirror=True, n_per=24, side=None):
    """outline: closed list of 2D points in the projection plane. plane: 'side' (s,z), 'top' (ax,s), 'front'/'rear' (ax,z).
    If mirror, outline is in |x|. side=+1/-1 restricts to x>0/x<0. Returns fn(V,N)."""
    sd = SDF2D(outline, res=res, n_per=n_per)
    def fn(V, N):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]
        ax = np.abs(x) if mirror else x
        if plane == 'side':
            d = sd(s, z)
        elif plane == 'top':
            d = sd(ax, s)
        else:
            d = sd(ax, z)
        if domain is not None:
            d = np.where(domain(V), d, BIG)
        if side is not None:
            d = np.where(side * x > 0, d, BIG)
        return d
    fn.sd = sd
    return fn

def ray_hit(field, origin, direction, tmax=3.0, steps=300):
    """First zero crossing of field along a ray (bisection refined). origin, direction (3,)."""
    o = np.asarray(origin, float); d = normalize(np.asarray(direction, float))
    ts = np.linspace(0, tmax, steps)
    P = o + ts[:, None] * d
    f = field(P[:, 0], P[:, 1], P[:, 2])
    idx = np.where((f[:-1] > 0) & (f[1:] <= 0))[0]
    if len(idx) == 0:
        return None
    i = idx[0]; a, b = ts[i], ts[i + 1]
    for _ in range(40):
        m = 0.5 * (a + b); pm = o + m * d
        if field(pm[0:1], pm[1:2], pm[2:3])[0] > 0: a = m
        else: b = m
    return o + 0.5 * (a + b) * d

def grad(field, P, h=0.001):
    P = np.atleast_2d(P); x, s, z = P[:, 0], P[:, 1], P[:, 2]
    g = np.stack([field(x + h, s, z) - field(x - h, s, z), field(x, s + h, z) - field(x, s - h, z),
                  field(x, s, z + h) - field(x, s, z - h)], 1)
    return normalize(g)

def surface_curve(field, pts2d, plane, side_sign=1, offset=0.0):
    """Project 2D points onto the body along the plane's view direction. Returns (k,3) points (+offset along normal)."""
    out = []
    for p in pts2d:
        if plane == 'front':
            o = (side_sign * p[0], 3.0, p[1]); d = (0, -1, 0)
        elif plane == 'rear':
            o = (side_sign * p[0], -3.0, p[1]); d = (0, 1, 0)
        elif plane == 'side':
            o = (side_sign * 1.6, p[0], p[1]); d = (-side_sign, 0, 0)
        else:
            o = (side_sign * p[0], p[1], 2.5); d = (0, 0, -1)
        h = ray_hit(field, o, d, tmax=6)
        if h is None:
            continue
        n = grad(field, h)[0]
        out.append(h + n * offset)
    return np.array(out)

# ------------------------------------------------------------------ small parts
def mc_small(field, lo, hi, res, target):
    V, F = mc_mesh(field, lo, hi, res, slab=16)
    if target and len(F) > target:
        V, F = decimate(V, F, target)
    V = project_to_surface(field, V, iters=3)
    N = field_normals(field, V, h=0.001)
    F = fix_winding(V, F, N)
    return V, F, N

def mirror_parts(parts, field_body, base, side, scale=1.0, mats=('paint', 'trim_black', 'chrome'), lod=1.0):
    """Side mirror: rounded housing on a stalk. base = (x, s, z) at the door/sail surface (x>0 version)."""
    bx, bs, bz = base
    L = 0.24 * scale; Hh = 0.13 * scale; Dd = 0.095 * scale
    cx, cs, cz = bx + 0.10 * scale, bs - 0.06 * scale, bz + 0.07 * scale
    def housing(x, s, z):
        px = (x - cx) / (L / 2); pz = (z - cz) / (Hh / 2)
        # superellipse outline in (x, z), slab in s that is deeper at the outer end
        d2 = ((np.abs(px) ** 3 + np.abs(pz) ** 3) ** (1 / 3) - 1.0) * (Hh / 2)
        front = Dd * (0.65 + 0.35 * np.clip((px + 1) / 2, 0, 1))
        d_s = np.maximum(s - (cs + front), cs - s)
        return smax(d2, d_s, 0.025)
    def stalk(x, s, z):
        from carlib import sd_capsule
        P = np.stack([x, s, z], -1)
        return sd_capsule(P, (bx - 0.02, bs + 0.01, bz), (cx - L * 0.3, cs + 0.005, cz - 0.01), 0.018 * scale)
    lo = (bx - 0.05, cs - 0.06, cz - Hh / 2 - 0.05); hi = (cx + L / 2 + 0.03, cs + Dd + 0.03, cz + Hh / 2 + 0.03)
    Vh, Fh, Nh = mc_small(housing, (cx - L / 2 - 0.02, cs - 0.04, cz - Hh / 2 - 0.02), (cx + L / 2 + 0.02, cs + Dd + 0.03, cz + Hh / 2 + 0.02), 0.004, int(1800 * lod))
    # mirror glass = rear face (normal toward -s)
    rear = Nh[Fh].mean(1)[:, 1] < -0.85
    Vs, Fs, Ns = mc_small(stalk, (bx - 0.06, bs - 0.1, bz - 0.05), (cx + 0.02, bs + 0.06, cz + 0.05), 0.004, int(500 * lod))
    out = []
    for (V, F, N, m) in [(Vh, Fh[~rear], Nh, mats[0]), (Vh, Fh[rear], Nh, mats[2]), (Vs, Fs, Ns, mats[1])]:
        Vv = V.copy(); Nn = N.copy(); Ff = F.copy()
        if side < 0:
            Vv[:, 0] *= -1; Nn[:, 0] *= -1; Ff = Ff[:, ::-1]
        parts.add('body', Vv, Ff, m, N=Nn)

def lattice_grille(parts, field, outline_fn_sd, xs_range, zs_range, depth_s_fn, pitch=0.028, bar=0.0045, mat='trim_black'):
    """Diagonal mesh grille: bars at +-45 deg in the (x, z) front plane, clipped to the opening (sd<0)."""
    x0, x1 = xs_range; z0, z1 = zs_range
    V = []; F = []
    for sgn in (1, -1):
        c0 = (z0 - sgn * x1) if sgn > 0 else (z0 + x0)
        for c in np.arange(-3, 3, pitch):
            # line z = sgn*x + c
            t = np.linspace(x0, x1, 120)
            zz = sgn * t + c
            ok = (zz > z0) & (zz < z1)
            if ok.sum() < 2: continue
            t = t[ok]; zz = zz[ok]
            inside = outline_fn_sd(np.abs(t), zz) < -0.004
            if inside.sum() < 2: continue
            # split into contiguous runs
            idx = np.where(inside)[0]
            runs = np.split(idx, np.where(np.diff(idx) > 1)[0] + 1)
            for r in runs:
                if len(r) < 2: continue
                xa, za = t[r[0]], zz[r[0]]; xb, zb = t[r[-1]], zz[r[-1]]
                sa = depth_s_fn(xa, za); sb = depth_s_fn(xb, zb)
                pa = np.array([xa, sa, za]); pb = np.array([xb, sb, zb])
                d = pb - pa; Lr = np.linalg.norm(d)
                if Lr < 1e-3: continue
                u = d / Lr; n = np.array([0, 1.0, 0]); w = np.cross(u, n); w /= np.linalg.norm(w)
                # bar as a flat ribbon facing forward, slightly thick (box)
                cen = 0.5 * (pa + pb)
                R = np.stack([u, n, w], 1)
                bv, bf = box(cen, (Lr / 2, 0.008, bar / 2), rot=R)
                F.append(bf + sum(len(v) for v in V)); V.append(bv)
    if V:
        V = np.concatenate(V); F = np.concatenate(F)
        parts.add('body', V, F, mat, flat=True, COL=np.c_[np.full((len(V), 3), 0.55), np.ones(len(V))])

def plate_texture(text='7ABC123', w=1024, h=512):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new('RGB', (w, h), (222, 224, 226))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([6, 6, w - 7, h - 7], radius=34, outline=(40, 46, 70), width=10)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf', 250)
    except Exception:
        f = ImageFont.load_default(size=250)
    bb = dr.textbbox((0, 0), text, font=f)
    dr.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1] + 20), text, fill=(28, 40, 92), font=f)
    # four mounting holes
    for hx in (0.2, 0.8):
        for hy in (0.15, 0.85):
            dr.ellipse([hx * w - 10, hy * h - 10, hx * w + 10, hy * h + 10], fill=(150, 150, 150))
    a = np.asarray(im, float) / 255.0
    # light grime toward the bottom
    g = np.linspace(0, 1, h)[:, None, None] ** 3 * 0.18
    a = a * (1 - g) + g * np.array([0.55, 0.45, 0.33])
    return a

def plate_mesh(parts, centre, normal, up, wpl=0.305, hpl=0.152, mat='plate', node='body'):
    """Flat plate with a 6 mm thickness, face textured (UV 0..1)."""
    c = np.asarray(centre, float); n = normalize(np.asarray(normal, float)); u = normalize(np.asarray(up, float))
    r = np.cross(u, n); r /= np.linalg.norm(r)
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    Vf = np.array([c + n * 0.003 + r * a * wpl / 2 + u * b * hpl / 2 for a, b in corners])
    UV = np.array([[(a + 1) / 2, (b + 1) / 2] for a, b in corners])
    Ff = np.array([[0, 1, 2], [0, 2, 3]])
    if np.dot(np.cross(Vf[1] - Vf[0], Vf[2] - Vf[0]), n) < 0: Ff = Ff[:, ::-1]
    parts.add(node, Vf, Ff, mat, N=np.repeat(n[None], 4, 0), UV=UV)
    # back/edge box in trim
    bv, bf = box(c - n * 0.002, (wpl / 2 + 0.006, 0.004, hpl / 2 + 0.006), rot=np.stack([r, n, u], 1))
    parts.add(node, bv, bf, 'trim_black', flat=True)

def strip_along(parts, pts, radius, mat, n_seg=8, node='body', col=None):
    if len(pts) < 2: return
    V, F = tube(pts, radius, n_seg=n_seg)
    C = None if col is None else np.c_[np.tile(col, (len(V), 1)), np.ones(len(V))]
    parts.add(node, V, F, mat, COL=C)

def smooth_path(P, n=60):
    P = np.asarray(P)
    return catmull_closed(P, n_per=max(2, n // max(1, len(P) - 1)), closed=False)
