"""Creatures for the drive-in sequence: moth, field mouse, great horned owl. All face +Z (glTF), metres, no rigging:
moving parts are separate nodes with their pivot at the hinge. Textures are procedural (numpy) and embedded.
flock .../heavy.lock python3 src/set/creatures.py [moth] [mouse] [owl]"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clib
from clib import Mesh, nrm, loft, sphere, blade
import texlib as TL
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import CubicSpline

SCR = os.environ.get('SET_SCRATCH', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/drivein_set')
TEXD = f'{SCR}/creature_tex'
os.makedirs(TEXD, exist_ok=True)


def spline_sections(rows, n):
    """rows: (z, y, rx, ry[, x]) control sections -> n interpolated (path, rx, ry)."""
    R = np.asarray(rows, float)
    t = np.r_[0, np.cumsum(np.abs(np.diff(R[:, 0])) + 1e-9)]
    ts = np.linspace(0, t[-1], n)
    cs = [CubicSpline(t, R[:, k]) for k in range(R.shape[1])]
    S = np.stack([c(ts) for c in cs], 1)
    x = S[:, 4] if R.shape[1] > 4 else np.zeros(n)
    path = np.stack([x, S[:, 1], S[:, 0]], 1)
    return path, np.maximum(S[:, 2], 1e-5), np.maximum(S[:, 3], 1e-5)


def remap_uv(m, u0, v0, u1, v1):
    m.UV = [np.c_[u0 + (u1 - u0) * uv[:, 0], v0 + (v1 - v0) * uv[:, 1]] for uv in m.UV]
    return m


def to_obj(pipe, name, mesh, parent=None, origin=None, smooth=70, recalc=False):
    V, F, _ = mesh.arrays()
    return pipe.make_mesh(name, V, F, uvs=mesh.loop_uvs(), smooth_angle=smooth, recalc=recalc, parent=parent, origin=origin)


# ====================================================================== MOTH
MOTH_ROOT_X = 0.0024


def moth_wing_outline(fore=True):
    """Outline in wing-local (x outward from the root, z forward), metres."""
    if fore:
        ctrl = np.array([[0.0, 0.0030], [0.006, 0.0042], [0.013, 0.0030], [0.019, 0.0005], [0.0225, -0.0030],
                         [0.0215, -0.0065], [0.0185, -0.0105], [0.0150, -0.0130], [0.0100, -0.0125], [0.005, -0.0095], [0.001, -0.0055]])
    else:
        ctrl = np.array([[0.0, -0.0020], [0.006, -0.0030], [0.0115, -0.0060], [0.0135, -0.0100], [0.0120, -0.0145],
                         [0.0085, -0.0170], [0.0045, -0.0160], [0.0015, -0.0115], [0.0, -0.0070]])
    # resample with a soft scalloped fringe on the outer margin
    t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))]
    ts = np.linspace(0, t[-1], 48 if fore else 36)
    P = np.stack([np.interp(ts, t, ctrl[:, 0]), np.interp(ts, t, ctrl[:, 1])], 1)
    P = ndi.gaussian_filter1d(P, 1.2, axis=0, mode='nearest')
    c = P.mean(0)
    d = P - c
    outer = np.clip(P[:, 0] / P[:, 0].max(), 0, 1) ** 2
    P = P + d * (0.03 * np.sin(np.arange(len(P)) * 2.0) * outer)[:, None]
    return P


def moth_wing(side):
    """side +1 = left wing (+X), -1 = right. Mesh in moth coords (pivot added by caller)."""
    m = Mesh()
    for fore, (v0, v1), yoff in ((True, (0.42, 1.0), 0.00025), (False, (0.0, 0.40), 0.0)):
        P = moth_wing_outline(fore)
        xmax = 0.0225 if fore else 0.0135
        zmin, zmax = (-0.0135, 0.0045) if fore else (-0.0175, -0.0015)
        def uv(p):
            return (p[0] / 0.0225, v0 + (v1 - v0) * (p[2] - zmin) / (zmax - zmin))
        c = np.array([P[:, 0].mean() * 0.6, P[:, 1].mean()])
        pts3 = np.c_[P[:, 0], np.zeros(len(P)), P[:, 1]]
        # slight dihedral + droop of the outer edge, angled back a little
        pts3[:, 1] = yoff + 0.08 * pts3[:, 0] - 1.5 * pts3[:, 0] ** 2
        cen = np.array([c[0], yoff + 0.08 * c[0], c[1]])
        w = clib.fan_polygon(pts3, cen, uv)
        if side < 0:
            w.transform(lambda v: v * np.array([-1, 1, 1]))
            w.F = [f[::-1] for f in w.F]
        m.merge(w)
    return m


def moth_body():
    path, rx, ry = spline_sections([(-0.0125, 0.0002, 0.0005, 0.0005), (-0.0105, 0.0004, 0.0016, 0.0015), (-0.006, 0.0006, 0.0022, 0.0021),
                                    (-0.001, 0.0008, 0.0026, 0.0025), (0.003, 0.0009, 0.0031, 0.0029), (0.0062, 0.0008, 0.0022, 0.0022),
                                    (0.0085, 0.0006, 0.0021, 0.0021), (0.0105, 0.0004, 0.0008, 0.0008)], 12)
    b = remap_uv(loft(path, rx, ry, m=10), 0, 0, 1, 1)
    for s in (1, -1):    # antennae: thin tapered, curving forward/out/up
        pts = np.array([[s * 0.0008, 0.0016, 0.0095], [s * 0.003, 0.0035, 0.0125], [s * 0.0055, 0.0045, 0.0155], [s * 0.0075, 0.0048, 0.018]])
        a = loft(pts, np.array([0.00025, 0.0002, 0.00015, 0.0001]), np.array([0.00025, 0.0002, 0.00015, 0.0001]), m=4)
        b.merge(remap_uv(a, 0, 0, 0.1, 0.1))
        for z0, dz in ((0.004, 0.003), (0.0015, -0.0005), (-0.001, -0.004)):    # six legs, tucked
            pts = np.array([[s * 0.0015, -0.0012, z0], [s * 0.0035, -0.0028, z0 + dz * 0.5], [s * 0.0045, -0.0040, z0 + dz]])
            l = loft(pts, np.array([0.0003, 0.00025, 0.00015]), np.array([0.0003, 0.00025, 0.00015]), m=4)
            b.merge(remap_uv(l, 0, 0, 0.1, 0.1))
    eyes = Mesh()
    for s in (1, -1):
        eyes.merge(sphere((s * 0.0016, 0.0009, 0.0092), 0.0009, m=8, n=5))
    return b, eyes


def tex_moth():
    n = 512
    r = TL.rng(71)
    yy, xx = np.mgrid[0:n, 0:n] / n
    u = xx; v = 1 - yy
    base = np.array([0.50, 0.45, 0.37])
    dust = TL.spectral((n, n), r, 2.2, lo=2, hi=200)
    fine = TL.spectral((n, n), r, 1.2, lo=60, hi=None)
    c = base * (1 + 0.08 * dust + 0.05 * fine)[..., None]
    fore = v > 0.41
    fv = (v - 0.42) / 0.58
    # forewing: wavy antemedial + postmedial lines, discal spot, darker subterminal shading
    am = np.exp(-((u - 0.30 - 0.05 * np.sin(fv * 12)) / 0.018) ** 2)
    pm = np.exp(-((u - 0.62 - 0.06 * np.sin(fv * 9 + 1)) / 0.02) ** 2)
    disc = np.exp(-(((u - 0.47) / 0.04) ** 2 + ((fv - 0.62) / 0.06) ** 2))
    sub = TL.smoothstep(0.70, 0.95, u)
    band = TL.smoothstep(0.32, 0.6, u) * (1 - TL.smoothstep(0.6, 0.66, u)) * 0.25
    dk = np.array([0.22, 0.18, 0.14])
    f = np.clip(0.55 * am + 0.6 * pm + 0.7 * disc + 0.3 * sub + band, 0, 0.85) * fore
    # hindwing: paler, plain with a faint margin
    hv = v / 0.40
    hw = (~fore) * (0.15 * TL.smoothstep(0.55, 0.9, u))
    c = c * (1 + 0.12 * (~fore))[..., None]
    c = c * (1 - (f + hw)[..., None]) + dk * (f + hw)[..., None]
    # veins (faint, radial from the root)
    ang = np.arctan2(v - (0.7 * fore + 0.2 * (~fore)), u + 0.05)
    vein = np.clip(np.cos(ang * 22) ** 40, 0, 1) * 0.12
    c = c * (1 - vein[..., None])
    TL.save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/moth_wing.jpg', 92)
    # body: fuzzy pale grey-brown
    b = np.array([0.40, 0.35, 0.28]) * (1 + 0.15 * TL.spectral((128, 128), r, 1.2, lo=8, hi=None))[..., None]
    TL.save_srgb(np.clip(b, 0.03, 0.85), f'{TEXD}/moth_body.jpg', 92)


def build_moth(pipe):
    from pipe import ROOT
    tex_moth()
    pipe.reset()
    root = pipe.empty('moth')
    body, eyes = moth_body()
    ob = to_obj(pipe, 'body', body, parent=root)
    T = TEXD
    pipe.assign(ob, pipe.material('fur', f'{T}/moth_body.jpg', rough=0.9))
    oe = to_obj(pipe, 'eyes', eyes, parent=ob)
    pipe.assign(oe, pipe.material('eye', base=(0.02, 0.018, 0.015), rough=0.15))
    wmat = pipe.material('wing', f'{T}/moth_wing.jpg', rough=0.85, double=True)
    tris = body.tris() + eyes.tris()
    for nm, s in (('wing_L', 1), ('wing_R', -1)):
        w = moth_wing(s)
        piv = np.array([s * MOTH_ROOT_X, 0.0016, 0.0035])
        w.transform(lambda v, piv=piv: v + piv)
        o = to_obj(pipe, nm, w, parent=ob, origin=piv, smooth=180)
        pipe.assign(o, wmat)
        tris += w.tris()
    print('moth tris', tris)
    pipe.export(f'{ROOT}/assets/moth.glb')


# ====================================================================== MOUSE
def mouse_parts():
    belly = lambda i, a: 0.82 if np.sin(a) < -0.2 else 1.0
    body_rows = [(-0.042, 0.018, 0.003, 0.003), (-0.039, 0.019, 0.013, 0.012), (-0.031, 0.021, 0.020, 0.018), (-0.019, 0.022, 0.0215, 0.0195),
                 (-0.006, 0.0215, 0.019, 0.018), (0.007, 0.021, 0.0155, 0.0155), (0.017, 0.0215, 0.0128, 0.0132), (0.026, 0.0225, 0.0112, 0.0118),
                 (0.031, 0.023, 0.0105, 0.0112)]
    path, rx, ry = spline_sections(body_rows, 18)
    body = remap_uv(loft(path, rx, ry, m=22, cap1=False, shape=lambda i, a: 0.85 if np.sin(a) < -0.3 else 1.0), 0, 0, 1, 0.5)
    head_rows = [(0.022, 0.0225, 0.0115, 0.0120), (0.031, 0.0250, 0.0127, 0.0125), (0.039, 0.0238, 0.0107, 0.0103),
                 (0.046, 0.0210, 0.0070, 0.0068), (0.0515, 0.0186, 0.0040, 0.0041), (0.0548, 0.0174, 0.0017, 0.0019), (0.0562, 0.0170, 0.0004, 0.0004)]
    path, rx, ry = spline_sections(head_rows, 14)
    head = remap_uv(loft(path, rx, ry, m=20, cap0=True), 0, 0.5, 1, 1.0)
    skin = Mesh()
    skin.merge(sphere((0, 0.0172, 0.0554), 0.0018, m=8, n=6))               # nose
    for s in (1, -1):                                                        # ears: rounded, cupped, thin
        root = np.array([s * 0.0070, 0.0330, 0.0310])
        d = nrm([s * 0.55, 0.85, -0.30]); side = nrm(np.cross(d, [0, 0, 1]) * s)
        e = blade(root, d, side, 0.0155, lambda t: 0.0076 * np.sin(np.pi * (0.12 + 0.88 * t)) ** 0.55 + 0.0006, nl=6, nw=4,
                  thick=0.0006, bend=lambda t, q, d=d: nrm(np.cross(d, side)) * 0.0018 * q * q * s)
        skin.merge(remap_uv(e, 0.6, 0.0, 0.9, 0.3))
    eyes = Mesh()
    for s in (1, -1):
        eyes.merge(sphere((s * 0.0081, 0.0283, 0.0405), 0.0031, m=10, n=7))
    # tail (pivot at the base)
    tz = np.linspace(0, 1, 18)
    tpath = np.stack([0.012 * np.sin(tz * 3.2) * tz, 0.018 - 0.016 * TL.smoothstep(0, 0.35, tz) + 0.001, -0.040 - 0.092 * tz], 1)
    trad = 0.0034 * (1 - tz) + 0.0007
    tail = remap_uv(loft(tpath, trad, trad, m=8), 0.0, 0.12, 1.0, 0.16)          # fur texture strip: brown top, white below
    # legs (pivot at the hips/shoulders): thigh/arm tube down to the foot, foot pointing forward
    legs = {}
    for nm, (hx, hy, hz), (fx, fz), flen, rad in (('leg_FL', (0.008, 0.013, 0.017), (0.010, 0.021), 0.008, 0.0028),
                                                  ('leg_FR', (-0.008, 0.013, 0.017), (-0.010, 0.021), 0.008, 0.0028),
                                                  ('leg_HL', (0.013, 0.016, -0.023), (0.016, -0.019), 0.017, 0.0045),
                                                  ('leg_HR', (-0.013, 0.016, -0.023), (-0.016, -0.019), 0.017, 0.0045)):
        hip = np.array([hx, hy, hz])
        ankle = np.array([fx, 0.0028, fz - flen * 0.35])
        knee = (hip + ankle) / 2 + np.array([0, 0, 0.004 if 'H' in nm else -0.002])
        m = loft(np.array([hip, knee, ankle]), np.array([rad, rad * 0.6, rad * 0.35]), np.array([rad, rad * 0.6, rad * 0.35]), m=8)
        foot = loft(np.array([ankle + (0, -0.001, 0), ankle + (np.sign(fx) * 0.0005, -0.0018, flen * 0.5), ankle + (np.sign(fx) * 0.001, -0.0022, flen)]),
                    np.array([0.0016, 0.0018, 0.0012]) * (1.25 if 'H' in nm else 1.0), np.array([0.0009, 0.0007, 0.0004]), m=6)
        leg = remap_uv(m, 0.70, 0.10, 0.80, 0.30)                                   # pale belly fur (white-footed)
        leg.merge(remap_uv(foot, 0.72, 0.10, 0.78, 0.20))
        legs[nm] = (leg, hip)
    # paws: two little hands under the chin (for holding a kernel), pivot at the chest
    paws = Mesh()
    for s in (1, -1):
        a = np.array([s * 0.006, 0.016, 0.026]); b = np.array([s * 0.0035, 0.0145, 0.038])
        paws.merge(remap_uv(loft(np.array([a, (a + b) / 2, b]), np.array([0.0022, 0.0018, 0.0012]), np.array([0.0022, 0.0018, 0.0012]), m=6), 0.70, 0.1, 0.8, 0.3))
        paws.merge(remap_uv(sphere(b + (0, 0, 0.0012), 0.0016, m=6, n=4, squash=(1, 0.7, 1.2)), 0.72, 0.1, 0.78, 0.2))
    return body, head, skin, eyes, tail, legs, paws


def tex_mouse():
    n = 1024
    r = TL.rng(81)
    yy, xx = np.mgrid[0:n, 0:n] / n
    u = xx; v = 1 - yy
    # loft u: a = 2*pi*u, a=0 side (+X), pi/2 back, -pi/2 (u .75) belly
    s = np.sin(2 * np.pi * u)
    back = TL.smoothstep(-0.45, -0.15, s)
    agouti = np.array([0.13, 0.085, 0.05]); belly = np.array([0.52, 0.49, 0.44]); dark = np.array([0.06, 0.045, 0.032])
    c = belly * (1 - back[..., None]) + agouti * back[..., None]
    c = c * (1 - 0.35 * TL.smoothstep(0.75, 1.0, s)[..., None]) + dark * 0.35 * TL.smoothstep(0.75, 1.0, s)[..., None]
    streak = TL.spectral((n, n), r, 1.6, lo=20, hi=None, aniso=(0.12, 1.0))
    tick = TL.smoothstep(1.0, 2.0, TL.spectral((n, n), r, 1.0, lo=100, hi=None, aniso=(0.25, 1.0)))
    c = c * (1 + 0.18 * streak)[..., None]
    c = c * (1 - tick[..., None] * 0.4) + np.array([0.30, 0.22, 0.13]) * 0.4 * tick[..., None] * back[..., None]
    # head half (v > .5): lighter cheeks, darker muzzle tip
    hv = (v - 0.5) * 2
    head = v > 0.5
    c[head] = c[head] * (1 - 0.25 * TL.smoothstep(0.75, 1.0, hv[head]))[..., None]
    TL.save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/mouse_fur_albedo.jpg', 92)
    h = 0.6 * streak + 0.3 * TL.spectral((n, n), r, 1.0, lo=150, hi=None, aniso=(0.2, 1.0))
    TL.save_normal(TL.normal_from_height(h, 1.0, 0.35), f'{TEXD}/mouse_fur_normal.jpg')
    # skin: pinkish grey (ears, nose, tail scales, feet)
    m = 256
    sk = np.array([0.30, 0.20, 0.17]) * (1 + 0.1 * TL.spectral((m, m), r, 2.0, lo=2, hi=60))[..., None]
    ring = (np.sin(np.arange(m) / m * 2 * np.pi * 40) > 0.6)[:, None] * np.ones((1, m))
    sk = sk * (1 - 0.15 * ring[..., None])
    TL.save_srgb(np.clip(sk, 0.03, 0.85), f'{TEXD}/mouse_skin.jpg', 92)


def build_mouse(pipe):
    from pipe import ROOT
    tex_mouse()
    pipe.reset()
    body, head, skin, eyes, tail, legs, paws = mouse_parts()
    T = TEXD
    fur = pipe.material('fur', f'{T}/mouse_fur_albedo.jpg', None, f'{T}/mouse_fur_normal.jpg', rough=0.75, nstr=0.6)
    skm = pipe.material('skin', f'{T}/mouse_skin.jpg', rough=0.55)
    eye = pipe.material('eye', base=(0.012, 0.01, 0.01), rough=0.06)
    root = pipe.empty('mouse')
    ob = to_obj(pipe, 'body', body, parent=root, origin=(0, 0.02, 0)); pipe.assign(ob, fur)
    neck = np.array([0, 0.023, 0.025])
    oh = to_obj(pipe, 'head', head, parent=ob, origin=neck); pipe.assign(oh, fur)
    os_ = to_obj(pipe, 'head_skin', skin, parent=oh, origin=neck); pipe.assign(os_, skm)
    oe = to_obj(pipe, 'eyes', eyes, parent=oh, origin=neck); pipe.assign(oe, eye)
    ot = to_obj(pipe, 'tail', tail, parent=ob, origin=(0, 0.019, -0.040)); pipe.assign(ot, fur)
    tris = body.tris() + head.tris() + skin.tris() + eyes.tris() + tail.tris() + paws.tris()
    for nm, (leg, hip) in legs.items():
        o = to_obj(pipe, nm, leg, parent=ob, origin=hip); pipe.assign(o, fur if True else skm)
        tris += leg.tris()
    chest = np.array([0, 0.016, 0.025])
    op = to_obj(pipe, 'paws', paws, parent=ob, origin=chest); pipe.assign(op, fur)
    pipe.empty('kernel_socket', (0, 0.0135, 0.0405), parent=op)
    print('mouse tris', tris)
    pipe.export(f'{ROOT}/assets/mouse.glb')


# ====================================================================== OWL
SPAN_ROOT = 0.062


def owl_wing(side):
    """Wing in owl coords (pivot at the shoulder added by caller). Arm/inner hand as a thick cambered grid,
    then six slotted primaries fanned at the tip and a scalloped trailing edge (secondaries)."""
    m = Mesh()
    L = 0.30                       # arm + inner hand span from the shoulder
    ns, nc = 16, 7
    V, UV = [], []
    def le(s):
        return 0.040 + 0.055 * TL.smoothstep(0.0, 0.62, s) - 0.035 * TL.smoothstep(0.62, 1.0, s)
    def te(s):
        sc = 0.007 * np.abs(np.sin(s * np.pi * 7))            # secondary feather tips
        return -0.215 + 0.045 * s ** 1.6 - sc
    def thick(s, c):
        return (0.022 * (1 - s) + 0.005) * np.sin(np.pi * np.clip(c, 0, 1) ** 0.6)
    for surf in (0, 1):
        for i in range(ns + 1):
            s = i / ns
            x = L * s
            for j in range(nc + 1):
                c = j / nc
                z = le(s) + (te(s) - le(s)) * c
                y = 0.012 * np.sin(np.pi * c) * (1 - 0.5 * s) + 0.06 * s * x * 0      # camber
                y += np.tan(np.radians(4)) * x - 0.10 * TL.smoothstep(0.55, 1.0, s) * x * 0.5
                y += thick(s, c) * (0.6 if surf == 0 else -0.4)
                V.append((x, y, z)); UV.append((x / 0.56, 0.5 + (z + 0.22) / 0.30 * 0.5))
    F = []
    W = nc + 1
    off = (ns + 1) * W
    for i in range(ns):
        for j in range(nc):
            q = [i * W + j, (i + 1) * W + j, (i + 1) * W + j + 1, i * W + j + 1]
            F.append(q)
            F.append([off + k for k in q[::-1]])
    for i in range(ns):                    # leading / trailing edges closing top and bottom
        for j in (0, nc):
            a, b = i * W + j, (i + 1) * W + j
            q = [a, off + a, off + b, b]
            F.append(q if j == 0 else q[::-1])
    V = np.array(V)
    grid = Mesh().add(V, F, np.array(UV))
    # make normals point up on the top surface: check one face
    p = V[F[0]]
    if np.cross(p[1] - p[0], p[2] - p[0])[1] < 0:
        grid.F = [f[::-1] for f in grid.F]
    m.merge(grid)
    # primaries: six slotted 'fingers' from the wing tip, fanned
    ytip = np.tan(np.radians(4)) * L - 0.05 * L
    tip_le, tip_te = np.array([L, ytip, le(1.0)]), np.array([L, ytip, te(1.0) + 0.01])
    angs = np.radians([28, 14, 2, -10, -22, -34])
    lens = [0.19, 0.225, 0.235, 0.225, 0.20, 0.17]
    for k, (a, ln) in enumerate(zip(angs, lens)):
        root = tip_le + (tip_te - tip_le) * (k + 0.5) / 6 + np.array([-0.035, 0, 0])
        d = nrm([np.cos(a), 0.03 + 0.01 * k, np.sin(a)])
        sd = nrm(np.cross([0, 1, 0], d))
        wf = lambda t: 0.017 * (1 - 0.45 * TL.smoothstep(0.35, 0.6, t)) * np.sqrt(np.clip(1 - t ** 4, 0, 1)) + 0.0015
        bend = lambda t, q: np.array([0, 0.018 * t * t - 0.01 * t, 0]) + np.array([0, 0.002 * q, 0])
        f = blade(root, d, sd, ln, wf, nl=7, nw=2, thick=0.0025, bend=bend, uv_rect=(0.62 + 0.06 * k, 0.5, 0.66 + 0.06 * k, 1.0))
        m.merge(f)
    if side < 0:
        m.transform(lambda v: v * np.array([-1, 1, 1]))
        m.F = [f[::-1] for f in m.F]
    return m


def owl_body():
    rows = [(-0.205, 0.000, 0.022, 0.016), (-0.16, 0.003, 0.052, 0.045), (-0.09, 0.006, 0.072, 0.066), (-0.01, 0.010, 0.077, 0.072),
            (0.06, 0.016, 0.068, 0.066), (0.095, 0.024, 0.062, 0.061), (0.13, 0.032, 0.074, 0.070), (0.175, 0.036, 0.076, 0.071),
            (0.205, 0.033, 0.064, 0.061), (0.222, 0.028, 0.036, 0.040), (0.228, 0.025, 0.004, 0.004)]
    path, rx, ry = spline_sections(rows, 16)
    flat = lambda i, a: 1.0
    b = remap_uv(loft(path, rx, ry, m=20), 0.0, 0.0, 0.5, 0.5)
    # ear tufts (the silhouette cue): stiff blades angled up/out/back
    for s in (1, -1):
        root = np.array([s * 0.042, 0.092, 0.180])
        d = nrm([s * 0.35, 0.85, -0.38]); side = nrm(np.cross(d, [0, 0, 1]))
        t1 = blade(root, d, side, 0.070, lambda t: 0.016 * (1 - t) ** 0.8 + 0.001, nl=5, nw=2, thick=0.004,
                   bend=lambda t, q: np.array([0, 0, -0.012 * t * t]))
        b.merge(remap_uv(t1, 0.5, 0.0, 0.6, 0.3))
    # tail fan: scalloped
    for k in range(9):
        a = np.radians(-28 + 7 * k)
        d = nrm([np.sin(a), -0.05, -np.cos(a)])
        side = nrm(np.cross([0, 1, 0], d))
        f = blade((0, 0.0, -0.17), d, side, 0.215, lambda t: 0.012 + 0.013 * t - 0.012 * t ** 6, nl=5, nw=2, thick=0.003)
        b.merge(remap_uv(f, 0.6 + 0.04 * k, 0.0, 0.64 + 0.04 * k, 0.45))
    # beak and tucked feet
    beak = loft(np.array([[0, 0.024, 0.220], [0, 0.014, 0.234], [0, 0.004, 0.237]]), np.array([0.009, 0.006, 0.001]), np.array([0.008, 0.005, 0.001]), m=6)
    feet = Mesh()
    for s in (1, -1):
        feet.merge(sphere((s * 0.028, -0.058, -0.07), 0.02, m=8, n=6, squash=(0.9, 0.7, 1.6)))
    b.merge(remap_uv(feet, 0.0, 0.0, 0.5, 0.5))
    eyes = Mesh()
    for s in (1, -1):
        eyes.merge(sphere((s * 0.030, 0.046, 0.208), 0.012, m=10, n=6, squash=(1, 1, 0.6)))
    return b, beak, eyes


def tex_owl():
    n = 1024
    r = TL.rng(91)
    yy, xx = np.mgrid[0:n, 0:n] / n
    u = xx; v = 1 - yy
    base = np.array([0.15, 0.105, 0.065]); pale = np.array([0.36, 0.29, 0.20]); dark = np.array([0.05, 0.035, 0.025])
    mott = TL.spectral((n, n), r, 1.8, lo=6, hi=None)
    c = base * (1 + 0.25 * mott)[..., None]
    # bars across feathers
    bars = (np.sin(v * 2 * np.pi * 26 + 0.6 * mott) > 0.35).astype(float)
    bars = ndi.gaussian_filter(bars, 1.2)
    wing = v > 0.5
    c = c * (1 - 0.45 * bars[..., None] * wing[..., None]) + dark * 0.45 * bars[..., None] * wing[..., None]
    # body region (u<.5, v<.5): pale barred belly on the lower half of the loft (u ~ .75 of the loft = belly)
    s = np.sin(2 * np.pi * (u / 0.5))
    bel = (~wing) & (u < 0.5)
    pb = TL.smoothstep(0.1, -0.6, s)
    cb = c * (1 - pb[..., None]) + pale * pb[..., None]
    fine_bars = ndi.gaussian_filter((np.sin(v * 2 * np.pi * 60 + mott) > 0.5).astype(float), 0.8)
    cb = cb * (1 - 0.35 * fine_bars[..., None])
    c[bel] = cb[bel]
    # feathers (primaries, tail, tufts): longitudinal dark bands
    fb = ndi.gaussian_filter((np.sin(v * 2 * np.pi * 12 + 0.4 * mott) > 0.2).astype(float), 1.5)
    fe = (u > 0.6)
    c[fe] = (c * (1 - 0.5 * fb[..., None]) + dark * 0.5 * fb[..., None])[fe]
    TL.save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/owl_feather_albedo.jpg', 92)
    h = 0.4 * mott + 0.5 * bars
    TL.save_normal(TL.normal_from_height(h, 1.0, 1.0), f'{TEXD}/owl_feather_normal.jpg')


def build_owl(pipe):
    from pipe import ROOT
    tex_owl()
    pipe.reset()
    T = TEXD
    fe = pipe.material('feather', f'{T}/owl_feather_albedo.jpg', None, f'{T}/owl_feather_normal.jpg', rough=0.85, nstr=0.5, double=True)
    root = pipe.empty('owl')
    body, beak, eyes = owl_body()
    ob = to_obj(pipe, 'body', body, parent=root); pipe.assign(ob, fe)
    obk = to_obj(pipe, 'beak', beak, parent=ob); pipe.assign(obk, pipe.material('beak', base=(0.05, 0.045, 0.04), rough=0.4))
    oey = to_obj(pipe, 'eyes', eyes, parent=ob); pipe.assign(oey, pipe.material('eye', base=(0.55, 0.32, 0.04), rough=0.08))
    tris = body.tris() + beak.tris() + eyes.tris()
    for nm, s in (('wing_L', 1), ('wing_R', -1)):
        piv = np.array([s * SPAN_ROOT, 0.035, 0.05])
        w = owl_wing(s)
        w.transform(lambda v, piv=piv: v + piv)
        o = to_obj(pipe, nm, w, parent=ob, origin=piv, smooth=60)
        pipe.assign(o, fe)
        tris += w.tris()
    print('owl tris', tris)
    pipe.export(f'{ROOT}/assets/owl.glb')


if __name__ == '__main__':
    import pipe
    which = sys.argv[1:] or ['moth', 'mouse', 'owl']
    if 'moth' in which:
        build_moth(pipe)
    if 'mouse' in which:
        build_mouse(pipe)
    if 'owl' in which:
        build_owl(pipe)
