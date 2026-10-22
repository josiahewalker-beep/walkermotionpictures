"""Popcorn bucket (striped red/white paper, heaped with popcorn) and one popped kernel for instancing.
flock .../heavy.lock python3 src/set/popcorn.py"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clib
from clib import Mesh, nrm
import texlib as TL
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

SCR = os.environ.get('SET_SCRATCH', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/drivein_set')
TEXD = f'{SCR}/popcorn_tex'
os.makedirs(TEXD, exist_ok=True)
H, R0, R1 = 0.22, 0.066, 0.090          # height, bottom radius, top radius


def kernel(rs, size=0.02, lumps=4, m=8, n=5, nub=True):
    """Popped kernel: a few overlapping squashed lumps (the 'wings' of a butterfly kernel) + the hull nub.
    UV covers the popcorn texture (lumps random sub-rects)."""
    out = Mesh()
    for k in range(lumps):
        d = nrm(rs.normal(size=3)) * size * rs.uniform(0.15, 0.32)
        r = size * rs.uniform(0.28, 0.40)
        sq = rs.uniform(0.7, 1.15, 3)
        s = clib.sphere(d, r, m=m, n=n, squash=sq)
        V, F, UV = s.arrays()
        # lumpy surface
        V = V + nrm(V - d) * (r * 0.12 * np.sin(V[:, 0] * 900 + k) * np.sin(V[:, 1] * 700 + 2 * k))[:, None]
        UV = UV * 0.45 + rs.uniform(0, 0.5, 2)
        out.add(V, F, UV)
    # hull nub: a small dark flake near the centre (bottom-right corner of the texture is hull brown)
    if not nub:
        return out
    s = clib.sphere(nrm(rs.normal(size=3)) * size * 0.18, size * 0.13, m=6, n=4, squash=(1, 0.5, 1))
    V, F, UV = s.arrays()
    out.add(V, F, UV * 0.06 + np.array([0.92, 0.02]))
    return out


def bucket_mesh():
    m = 32
    # outer wall: bottom up to the rim roll; UV v 0..0.92 (stripes texture), u around
    prof = [(R0 - 0.004, 0.0), (R0, 0.004)] + [(R0 + (R1 - R0) * t, 0.004 + (H - 0.012) * t) for t in np.linspace(0.08, 1.0, 6)]
    outer = clib.lathe(prof, m=m)
    V, F, UV = outer.arrays()
    UV[:, 1] = np.clip(V[:, 1] / H, 0, 1) * 0.92
    # slight crumple / unevenness (paper)
    a = np.arctan2(V[:, 2], V[:, 0])
    V[:, [0, 2]] *= (1 + 0.012 * np.sin(a * 7 + 1.3) * (V[:, 1] / H) + 0.006 * np.sin(a * 13))[:, None]
    bucket = Mesh().add(V, F, UV)
    # rim roll (rolled paper edge)
    t = np.linspace(-np.pi * 0.2, np.pi * 1.25, 4)
    rp = [(R1 + 0.0035 * np.cos(tt) - 0.0005, H - 0.006 + 0.0035 * np.sin(tt)) for tt in t]
    roll = clib.lathe(rp, m=m)
    V, F, UV = roll.arrays(); UV[:, 1] = 0.94 + 0.04 * UV[:, 1]
    bucket.add(V, F, UV)
    # inner wall (visible above the heap edge) and bottom
    inner = clib.flip(clib.lathe([(R1 - 0.0025, H - 0.006), (R0 - 0.0015, 0.004)][::-1], m=m))
    V, F, UV = inner.arrays(); UV[:, 1] = 0.94 + 0.05 * UV[:, 1]; UV[:, 0] = UV[:, 0] * 0.1 + 0.9
    bucket.add(V, F, UV)
    bot = clib.lathe([(0.0001, 0.0), (R0 - 0.004, 0.0)], m=m)
    V, F, UV = bot.arrays(); UV[:] = (0.95, 0.97)
    bucket.add(V, F, UV)
    return bucket


def heap_mesh(rs):
    """Dome of popcorn above the rim plus loose kernels on top."""
    m, n = 16, 4
    V, UV, F = [], [], []
    top = H + 0.05
    for i in range(n + 1):
        t = i / n
        r = (R1 - 0.003) * np.cos(t * np.pi / 2) ** 0.8
        y = H - 0.012 + (top - H + 0.012) * np.sin(t * np.pi / 2) ** 1.3
        for j in range(m + 1):
            a = 2 * np.pi * j / m
            bump = (0.006 * np.sin(a * 5 + i * 1.7) * np.sin(i * 2.1 + 0.3) + 0.004 * rs.normal()) * (i < n)
            rr = max(r + bump * 0.6, 0)
            V.append((rr * np.cos(a), y + bump * (0.5 + t), rr * np.sin(a)))
            UV.append((j / m * 2.0 % 1.0 if False else j / m, t))
    W = m + 1
    for i in range(n):
        for j in range(m):
            q = [i * W + j, i * W + j + 1, (i + 1) * W + j + 1, (i + 1) * W + j]
            F.append(q if i < n - 1 else [q[0], q[1], q[2]])
    V = np.array(V)
    F = [f[::-1] for f in F]
    heap = Mesh().add(V, clib.orient(V - (0, H, 0), F), np.array(UV) * 0.9)
    # loose kernels sitting on the dome
    for k in range(18):
        a = rs.uniform(0, 2 * np.pi) if k else 0.0
        rr = (R1 - 0.014) * (np.sqrt((k + 0.5) / 18)) if k else 0.0
        a = k * 2.39996
        t = np.arccos(np.clip(rr / R1, 0, 1)) / (np.pi / 2)
        y = H - 0.012 + (top - H + 0.012) * np.sin(t * np.pi / 2) ** 1.3 + 0.004
        kn = kernel(rs, size=rs.uniform(0.019, 0.025), lumps=3, m=6, n=4, nub=False)
        Rm = rot_rand(rs)
        kn.transform(lambda v, Rm=Rm, a=a, rr=rr, y=y: v @ Rm.T + np.array([rr * np.cos(a), y, rr * np.sin(a)]))
        heap.merge(kn)
    return heap


def rot_rand(rs):
    q = nrm(rs.normal(size=4))
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


# ------------------------------------------------------------------ textures
def tex_paper():
    Wd, Hd = 1024, 1024
    r = TL.rng(51)
    u = (np.arange(Wd) + 0.5) / Wd
    v = 1 - (np.arange(Hd) + 0.5) / Hd                  # image row 0 = v 1 (top)
    U, Vv = np.meshgrid(1 - u, v)          # lathe u runs clockwise seen from outside: mirror so text reads
    red = np.array([0.50, 0.018, 0.022]); white = np.array([0.74, 0.72, 0.67])
    stripes = (np.floor(U * 16) % 2 == 0)
    edge = np.abs((U * 16) % 1 - 0.5)
    stripe = ndi.gaussian_filter(stripes.astype(float), (0, 0.8))
    c = white * (1 - stripe[..., None]) + red * stripe[..., None]
    # white band with POPCORN lettering near the top of the wall (v 0.70..0.86)
    band = (Vv > 0.70) & (Vv < 0.86)
    c[band] = white
    img = Image.new('L', (Wd, Hd), 0)
    dr = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 88)
    except Exception:
        f = ImageFont.load_default()
    y_mid = int((1 - 0.78) * Hd)
    for x0 in (Wd * 0.25, Wd * 0.75):
        dr.text((x0, y_mid), 'POPCORN', font=f, fill=255, anchor='mm')
    t = ndi.gaussian_filter(np.asarray(img, float) / 255, 0.7)
    c = c * (1 - t[..., None]) + red * t[..., None]
    # thin red lines framing the band
    for vb in (0.70, 0.86):
        ln = np.exp(-((Vv - vb) / 0.004) ** 2)
        c = c * (1 - ln[..., None]) + red * ln[..., None]
    # grease spots, scuffs, slight yellowing, inner wall region (u > 0.9, v > 0.94) plain kraft-white
    lo = TL.spectral((Hd, Wd), r, 2.4, lo=1, hi=60)
    gr = TL.smoothstep(1.3, 2.2, TL.spectral((Hd, Wd), r, 1.8, lo=6, hi=200) + 0.4 * lo)
    c = c * (1 - 0.25 * gr[..., None]) + np.array([0.55, 0.42, 0.20]) * 0.25 * gr[..., None]
    c = c * (1 + 0.04 * lo)[..., None]
    c[Vv > 0.93] = np.array([0.70, 0.68, 0.62])
    TL.save_srgb(np.clip(c, 0.02, 0.85), f'{TEXD}/paper_albedo.jpg', 92)
    crump = TL.spectral((Hd, Wd), r, 2.0, lo=3, hi=120, aniso=(1.0, 0.4))
    TL.save_normal(TL.normal_from_height(0.12 * crump, 1.0, 0.4), f'{TEXD}/paper_normal.jpg')
    rough = np.clip(0.55 + 0.08 * lo - 0.25 * gr, 0.2, 1)
    orm = np.stack([np.ones_like(rough), rough, np.zeros_like(rough)], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(f'{TEXD}/paper_orm.png')


def tex_popcorn():
    n = 512
    r = TL.rng(61)
    a = TL.spectral((n, n), r, 2.0, lo=4, hi=None)
    b = TL.spectral((n, n), r, 1.4, lo=30, hi=None)
    F1, F2, _, _ = TL.worley((n, n), 28, r)
    cell = np.clip((F2 - F1) / 10, 0, 1)
    fluff = np.array([0.80, 0.74, 0.58]); butter = np.array([0.72, 0.52, 0.20])
    t = TL.smoothstep(-0.6, 1.2, a)
    c = fluff * (1 - t[..., None]) + butter * t[..., None]
    c = c * (0.85 + 0.15 * cell)[..., None] * (1 + 0.05 * b)[..., None]
    # hull brown in the bottom-right corner (used by the nub)
    yy, xx = np.mgrid[0:n, 0:n] / n
    hull = (xx > 0.9) & (yy > 0.9)
    c[hull] = np.array([0.20, 0.09, 0.03])
    TL.save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/popcorn_albedo.jpg', 92)
    h = 0.6 * cell + 0.2 * b
    TL.save_normal(TL.normal_from_height(h, 1.0, 0.25), f'{TEXD}/popcorn_normal.jpg')


def export_all():
    import bpy, pipe
    from pipe import ROOT
    rs = np.random.default_rng(12)
    tex_paper(); tex_popcorn()
    # ---- bucket
    pipe.reset()
    root = pipe.empty('popcorn_bucket')
    b = bucket_mesh(); h = heap_mesh(rs)
    V, F, _ = b.arrays()
    ob1 = pipe.make_mesh('bucket', V, F, uvs=b.loop_uvs(), smooth_angle=70, recalc=False, parent=root)
    V, F, _ = h.arrays()
    ob2 = pipe.make_mesh('popcorn', V, F, uvs=h.loop_uvs(), smooth_angle=80, recalc=False, parent=root)
    T = TEXD
    pipe.assign(ob1, pipe.material('paper', f'{T}/paper_albedo.jpg', f'{T}/paper_orm.png', f'{T}/paper_normal.jpg', double=True))
    pop = pipe.material('popcorn', f'{T}/popcorn_albedo.jpg', None, f'{T}/popcorn_normal.jpg', rough=0.7)
    pipe.assign(ob2, pop)
    print('bucket tris', b.tris() + h.tris())
    pipe.export(f'{ROOT}/assets/popcorn_bucket.glb')
    # ---- single kernel
    pipe.reset()
    k = kernel(np.random.default_rng(3), size=0.02, lumps=4, m=8, n=5)
    V, F, _ = k.arrays()
    V = V - np.array([0, V[:, 1].min(), 0])          # origin at the bottom
    ob = pipe.make_mesh('popcorn_kernel', V, F, uvs=k.loop_uvs(), smooth_angle=80, recalc=False)
    pipe.assign(ob, pipe.material('popcorn', f'{T}/popcorn_albedo.jpg', None, f'{T}/popcorn_normal.jpg', rough=0.7))
    print('kernel tris', k.tris())
    pipe.export(f'{ROOT}/assets/popcorn_kernel.glb')


if __name__ == '__main__':
    export_all()
