"""Blue minivan -> assets/car_minivan.glb.   python3 minivan.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from carlib import Parts, normalize, sstep, smax, smin, mirror_half, tube, box, revolve, vertex_normals, catmull_closed
from body import Body
from surfops import build_labelled
import carbuild as CB
import details as D
import wheels as W
import interior as IN
import minivan_params as M

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '../../assets/car_minivan.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0075
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 50000

B = Body(M.P)
P = M.P
f = B.field
BELT = P['belt']

def dlo_outline():
    zb = lambda s: BELT + 0.04 + 0.03 * sstep(-0.5, -2.2, s)
    zs = np.linspace(zb(1.2), 1.62, 12)
    front = []
    for z in zs:
        ss = np.linspace(0.3, 1.7, 700)
        wg = B.gh_width(ss, z)
        d = B.ws_dist(wg, ss, np.full_like(ss, z))
        i = np.argmin(np.abs(d))
        front.append((ss[i] - 0.085, z))
    front = np.array(front)
    st = np.linspace(front[-1, 0] - 0.06, -2.30, 22)
    top = []
    for s_ in st:
        zr = B.c['Zroof'](s_) - P['roof_crown'] * (B.gh_width(s_, B.c['Zroof'](s_)) / 0.7) ** 2
        top.append((s_, zr - 0.085))
    top = np.array(top)
    rear = [(-2.33, top[-1, 1] - 0.04), (-2.36, 1.40), (-2.36, zb(-2.36) + 0.04)]
    bottom = [(s_, zb(s_)) for s_ in np.linspace(-2.32, front[0, 0] + 0.02, 14)]
    return np.array(list(front) + list(top[1:]) + rear + bottom)

DLO = dlo_outline()
side_dom = lambda V: (np.abs(V[:, 0]) > 0.5) & (V[:, 2] > BELT - 0.06)
fn_dlo = D.proj_fn(DLO, 'side', domain=side_dom, n_per=6)
def fn_bp(V, N):
    s, z = V[:, 1], V[:, 2]
    d1 = np.abs(s - (0.18 - 0.06 * (z - 1.1))) - 0.035     # B pillar (blacked out)
    d2 = np.abs(s - (-1.08 - 0.10 * (z - 1.1))) - 0.045    # C pillar
    return np.where(side_dom(V), np.minimum(d1, d2), 1.0)

def fn_ws(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    d = smax(smax(ax - (B.gh_width(s, z) - 0.095), z - 1.665, 0.05), (BELT + 0.03) - z, 0.04)
    return np.where(s > 0.4, d, 1.0)

def fn_bl(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    d = smax(smax(ax - (B.gh_width(s, z) - 0.115), z - 1.665, 0.05), 1.21 - z, 0.05)
    return np.where((s < -2.2) & (z > 1.0), d, 1.0)

GAP = 0.0024
sd2 = lambda V: np.abs(V[:, 0]) > 0.55
FDOOR = [(1.075, 0.33), (1.08, 0.80), (1.13, 1.0), (1.17, 1.25), (0.20, 1.25), (0.195, 0.80), (0.20, 0.33)]
SDOOR = [(0.135, 0.33), (0.14, 0.80), (0.135, 1.25), (-1.06, 1.25), (-1.035, 0.80), (-1.0, 0.33)]
fn_fdoor = D.proj_fn(FDOOR, 'side', domain=sd2, n_per=5)
fn_sdoor = D.proj_fn(SDOOR, 'side', domain=sd2, n_per=5)
TRACK = [(-1.07, 1.026), (-2.30, 1.034), (-2.30, 1.042), (-1.07, 1.034)]
fn_track = D.proj_fn(TRACK, 'side', domain=sd2, n_per=2)
HOOD = [(0.0, 2.43), (0.40, 2.41), (0.62, 2.33), (0.70, 2.2), (0.70, 1.64), (0.0, 1.64)]
HOOD = np.concatenate([np.array(HOOD), np.array(HOOD)[::-1][1:-1] * [-1, 1]])
fn_hood = D.proj_fn(HOOD, 'top', domain=lambda V: (V[:, 2] > 0.8) & (V[:, 1] > 1.4), n_per=8, mirror=False)
HATCH = [(0.0, 0.62), (0.62, 0.62), (0.70, 0.66), (0.73, 0.90), (0.74, 1.30), (0.73, 1.95), (0.0, 1.95)]
fn_hatch = D.proj_fn(mirror_half(HATCH), 'rear', domain=lambda V: V[:, 1] < -2.3, n_per=6, mirror=False)
fn_fuel = D.proj_fn(catmull_closed(np.array([(-1.78, 0.90), (-1.78, 1.0), (-1.785, 1.005), (-1.915, 1.005), (-1.92, 1.0), (-1.92, 0.90), (-1.915, 0.895), (-1.785, 0.895)]), 3),
                    'side', domain=lambda V: V[:, 0] > 0.5, n_per=3, mirror=False)

front_dom = lambda V: V[:, 1] > 1.95
HEAD = [(0.42, 0.87), (0.60, 0.885), (0.78, 0.925), (0.90, 0.965), (0.945, 0.958), (0.95, 0.90), (0.90, 0.845),
        (0.74, 0.815), (0.56, 0.80), (0.44, 0.805), (0.40, 0.835)]
fn_head = D.proj_fn(HEAD, 'front', domain=front_dom, n_per=8)
GRILLE = [(0.0, 0.80), (0.36, 0.80), (0.46, 0.765), (0.50, 0.62), (0.46, 0.50), (0.0, 0.50)]
fn_grille = D.proj_fn(mirror_half(GRILLE), 'front', domain=front_dom, n_per=8, mirror=False)
LOWER = [(0.0, 0.42), (0.46, 0.42), (0.54, 0.37), (0.50, 0.27), (0.0, 0.27)]
fn_lowg = D.proj_fn(mirror_half(LOWER), 'front', domain=front_dom, n_per=6, mirror=False)
FOG = [(0.66, 0.40), (0.80, 0.42), (0.86, 0.36), (0.80, 0.31), (0.66, 0.31), (0.62, 0.35)]
fn_fog = D.proj_fn(FOG, 'front', domain=front_dom, n_per=6)
rear_dom = lambda V: V[:, 1] < -2.25
TAIL = [(0.72, 1.30), (0.90, 1.31), (0.965, 1.27), (0.975, 1.10), (0.96, 0.98), (0.88, 0.96), (0.74, 0.99), (0.70, 1.10)]
fn_tail = D.proj_fn(TAIL, 'rear', domain=rear_dom, n_per=8)
TBAR = [(0.0, 1.135), (0.66, 1.135), (0.66, 1.155), (0.0, 1.155)]
fn_tbar = D.proj_fn(mirror_half(TBAR), 'rear', domain=rear_dom, n_per=3, mirror=False)
RPLATE = [(0.0, 0.97), (0.17, 0.97), (0.185, 0.955), (0.185, 0.79), (0.17, 0.775), (0.0, 0.775)]
fn_rplate = D.proj_fn(mirror_half(RPLATE), 'rear', domain=rear_dom, n_per=4, mirror=False)
H1 = [(0.42, 0.975), (0.42, 0.995), (0.40, 1.005), (0.25, 1.005), (0.23, 0.995), (0.23, 0.975), (0.25, 0.965), (0.40, 0.965)]
H2 = [(-0.04, 0.975), (-0.04, 0.995), (-0.06, 1.005), (-0.21, 1.005), (-0.23, 0.995), (-0.23, 0.975), (-0.21, 0.965), (-0.06, 0.965)]
fn_h1 = D.proj_fn(H1, 'side', domain=sd2, n_per=3)
fn_h2 = D.proj_fn(H2, 'side', domain=sd2, n_per=3)
fn_mark_f = D.proj_fn(catmull_closed(np.array([(2.18, 0.70), (2.18, 0.73), (2.30, 0.73), (2.30, 0.70)]), 2), 'side',
                      domain=lambda V: (np.abs(V[:, 0]) > 0.6) & (V[:, 1] > 1.9), n_per=3)

zl_curve = np.array([(2.7, 0.27), (2.3, 0.27), (2.0, 0.30), (1.0, 0.30), (-1.0, 0.30), (-2.0, 0.30), (-2.3, 0.41), (-2.7, 0.41)])
def fn_lower(V, N):
    zl = np.interp(V[:, 1], zl_curve[::-1, 0], zl_curve[::-1, 1])
    return V[:, 2] - zl

def fn_well(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]
    d = None
    for (sa, za, R, xin) in P['wells']:
        dc = np.sqrt((s - sa) ** 2 + (z - za) ** 2) - R
        d = dc if d is None else np.minimum(d, dc)
    return np.where(np.abs(x) > 0.45, d, 1.0)

# arch cladding: black band around the arches (crossover-style lip)
def fn_clad(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]
    d = None
    for (sa, za, R, xin) in P['wells']:
        dc = np.sqrt((s - sa) ** 2 + (z - za) ** 2) - (R + 0.035)
        d = dc if d is None else np.minimum(d, dc)
    return np.where(np.abs(x) > 0.6, d, 1.0)

cuts = [
    ('dlo', fn_dlo, [0.0, 0.018]), ('bp', fn_bp, [0.0]), ('ws', fn_ws, [0.0, -0.04]), ('bl', fn_bl, [0.0, -0.035]),
    ('fdoor', fn_fdoor, [-GAP, GAP]), ('sdoor', fn_sdoor, [-GAP, GAP]), ('track', fn_track, [0.0]),
    ('hood', fn_hood, [-GAP, GAP]), ('hatch', fn_hatch, [-GAP, GAP]), ('fuel', fn_fuel, [-GAP, GAP]),
    ('head', fn_head, [0.0, 0.007]), ('grille', fn_grille, [0.0, 0.012]), ('lowg', fn_lowg, [0.0]),
    ('fog', fn_fog, [0.0, 0.006]), ('tail', fn_tail, [0.0, -0.006]), ('tbar', fn_tbar, [0.0]), ('rplate', fn_rplate, [0.0]),
    ('h1', fn_h1, [0.0]), ('h2', fn_h2, [0.0]), ('mark_f', fn_mark_f, [0.0]), ('lower', fn_lower, [0.0]),
    ('well', fn_well, [0.004]), ('clad', fn_clad, [0.0]),
]

labels = {
    'paint': dict(mat='paint'),
    'gap': dict(mat='trim_black', depth=0.005, wall='paint', wall_col=0.25, col=0.5),
    'glass': dict(mat='glass', depth=0.008, wall='trim_black', wall_col=0.6),
    'frit': dict(mat='trim_black', depth=0.008, wall='trim_black', col=0.8),
    'dlo_trim': dict(mat='trim_black', depth=0.0, col=1.0),
    'lamp': dict(mat='trim_black', depth=0.035, wall='chrome', wall_col=0.6, col=0.7),
    'lamp_bezel': dict(mat='trim_black', depth=0.0, col=1.0),
    'grille': dict(mat='trim_black', depth=0.05, wall='trim_black', wall_col=0.35, col=0.25),
    'grille_sur': dict(mat='chrome', depth=0.0),
    'lowg': dict(mat='trim_black', depth=0.04, wall='trim_black', wall_col=0.35, col=0.25),
    'fog': dict(mat='trim_black', depth=0.02, wall='trim_black', col=0.4),
    'fog_sur': dict(mat='trim_black', depth=0.0),
    'tail': dict(mat='light_rear', depth=0.006, wall='trim_black', wall_col=0.5),
    'tail_bez': dict(mat='trim_black', depth=0.0, col=0.9),
    'tbar': dict(mat='chrome', depth=0.0),
    'rplate': dict(mat='trim_black', depth=0.014, wall='paint', wall_col=0.5, col=0.6),
    'handle': dict(mat='chrome', depth=0.004, wall='trim_black', wall_col=0.3),
    'marker_f': dict(mat='light_front', depth=0.002, col=(1.0, 0.45, 0.05)),
    'lower': dict(mat='trim_black', depth=0.0, col=0.7),
    'clad': dict(mat='trim_black', depth=0.0, col=0.75),
    'well': dict(mat='trim_black', depth=0.0, col=0.25),
    'under': dict(mat='trim_black', depth=0.0, col=0.3),
}
rules = [
    ('well', lambda fm: fm['well'] < 0.004),
    ('under', lambda fm: (fm['n'][:, 2] < -0.55) & (fm['c'][:, 2] < 0.35)),
    ('glass', lambda fm: (fm['ws'] < -0.04) | (fm['bl'] < -0.035) | ((fm['dlo'] < 0) & (fm['bp'] > 0))),
    ('frit', lambda fm: (fm['ws'] < 0) | (fm['bl'] < 0)),
    ('dlo_trim', lambda fm: fm['dlo'] < 0.018),
    ('lamp', lambda fm: fm['head'] < 0),
    ('lamp_bezel', lambda fm: fm['head'] < 0.007),
    ('grille', lambda fm: fm['grille'] < 0),
    ('grille_sur', lambda fm: fm['grille'] < 0.012),
    ('lowg', lambda fm: fm['lowg'] < 0),
    ('fog', lambda fm: fm['fog'] < 0),
    ('fog_sur', lambda fm: fm['fog'] < 0.006),
    ('tail', lambda fm: fm['tail'] < -0.006),
    ('tail_bez', lambda fm: fm['tail'] < 0),
    ('tbar', lambda fm: fm['tbar'] < 0),
    ('rplate', lambda fm: fm['rplate'] < 0),
    ('handle', lambda fm: (fm['h1'] < 0) | (fm['h2'] < 0)),
    ('marker_f', lambda fm: fm['mark_f'] < 0),
    ('clad', lambda fm: (fm['clad'] < 0) & (fm['c'][:, 2] < 0.95)),
    ('lower', lambda fm: fm['lower'] < 0),
    ('gap', lambda fm: (np.abs(fm['fdoor']) < GAP) | (np.abs(fm['sdoor']) < GAP) | (fm['track'] < 0) | (np.abs(fm['hood']) < GAP)
                       | (np.abs(fm['hatch']) < GAP) | (np.abs(fm['fuel']) < GAP)),
]

def ao_col(V, N):
    z = V[:, 2]; s = V[:, 1]
    a = 0.62 + 0.38 * sstep(0.17, 0.65, z)
    for (sa, za, R, xin) in P['wells']:
        r = np.sqrt((s - sa) ** 2 + (z - za) ** 2)
        a *= 1 - 0.3 * np.exp(-((r - R) / 0.05) ** 2) * (np.abs(V[:, 0]) > 0.5)
    a *= 0.85 + 0.15 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
    return np.repeat(a[:, None], 3, 1)

def surf(pt2, plane, sgn=1, off=0.0):
    h = D.surface_curve(f, pt2, plane, sgn, offset=off)
    return h

def build():
    CB.log('minivan: body field')
    V, F, N = CB.body_surface(B, M.BOUNDS, RES, TARGET)
    cs = CB.run_cuts(B, V, F, N, cuts)
    parts = Parts()
    parts, lab = build_labelled(cs, labels, rules, 'paint', col_fn=ao_col, parts=parts, node='body')
    names = list(labels.keys())
    m = (lab == names.index('lamp'))
    Fm = cs.F[m]; used = np.unique(Fm); remap = -np.ones(len(cs.V), np.int64); remap[used] = np.arange(len(used))
    parts.add('body', cs.V[used] + cs.N[used] * 0.0005, remap[Fm], 'light_cover', N=cs.N[used])
    CB.log('body labelled', parts.tris('body'))
    # headlamp internals: DRL strip + projector
    for sgn in (1, -1):
        c = surf([(0.44, 0.858), (0.60, 0.868), (0.78, 0.905), (0.90, 0.945), (0.935, 0.94)], 'front', sgn, -0.014)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 40), 0.0045, 'light_front')
        c = surf([(0.47, 0.82), (0.62, 0.818), (0.78, 0.835), (0.90, 0.865)], 'front', sgn, -0.02)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 30), 0.0035, 'chrome')
        for (px, pz) in [(0.62, 0.85), (0.76, 0.87)]:
            h = surf([(px, pz)], 'front', sgn, -0.03)
            if len(h) == 0: continue
            prof = [(-0.012, 0.027), (0.0, 0.027), (0.0, 0.021), (0.005, 0.02), (0.011, 0.013), (0.014, 0.0)]
            Vl, Fl, _ = revolve(prof, 24)
            u = normalize(np.array([0, 1.0, 0.1])); v = normalize(np.cross(u, [1.0, 0, 0])); w = np.cross(u, v)
            Vw = h[0] + Vl[:, 0:1] * u + Vl[:, 1:2] * v + Vl[:, 2:3] * w
            Nn = vertex_normals(Vw, Fl)
            if np.mean(Nn @ u) < 0: Fl = Fl[:, ::-1]
            parts.add('body', Vw, Fl, 'chrome')
        # fog lamp lens
        h = surf([(0.74, 0.365)], 'front', sgn, -0.015)
        if len(h):
            Vl, Fl, _ = revolve([(-0.005, 0.03), (0.0, 0.03), (0.006, 0.02), (0.008, 0.0)], 20)
            u = np.array([0, 1.0, 0]); v = np.array([1.0, 0, 0]); w = np.array([0, 0, 1.0])
            Vw = h[0] + Vl[:, 0:1] * u + Vl[:, 1:2] * v + Vl[:, 2:3] * w
            Nn = vertex_normals(Vw, Fl)
            if np.mean(Nn @ u) < 0: Fl = Fl[:, ::-1]
            parts.add('body', Vw, Fl, 'light_front')
        # tail LED bars (vertical C shape)
        c = surf([(0.76, 1.27), (0.90, 1.275), (0.945, 1.22), (0.95, 1.08), (0.93, 1.0), (0.82, 0.99)], 'rear', sgn, -0.004)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 40), 0.004, 'light_rear_led', n_seg=6)
    # grille slats (horizontal chrome-dark bars)
    for z in np.linspace(0.54, 0.76, 6):
        for sgn in (1, -1):
            pass
        pts = []
        xs = np.linspace(-0.46, 0.46, 9)
        for x in xs:
            if fn_grille.sd(np.array([abs(x)]), np.array([z]))[0] > -0.01: continue
            h = surf([(abs(x), z)], 'front', np.sign(x) or 1, 0.0)
            if len(h): pts.append(h[0] - np.array([0, 0.03, 0]))
        if len(pts) > 1:
            D.strip_along(parts, np.array(pts), 0.008, 'trim_black', n_seg=6, col=(0.9, 0.9, 0.9))
    def depth_s(x, z):
        h = surf([(abs(x), z)], 'front', 1, 0.0)
        return (h[0][1] - 0.02) if len(h) else 2.4
    D.lattice_grille(parts, f, lambda ax, z: fn_lowg.sd(ax, z), (-0.55, 0.55), (0.27, 0.42), depth_s, pitch=0.026, bar=0.004)
    # rear plate + wiper + roof rails
    p = surf([(0.0, 0.873)], 'rear', 1, 0.0)
    if len(p):
        n = D.grad(f, p[0])[0]
        D.plate_mesh(parts, p[0] - n * 0.012, n, (0, 0, 1.0))
    wp = []
    for t in np.linspace(0, 1, 8):
        x = -0.05 + t * 0.55; z = 1.24 + t * 0.28
        h = surf([(abs(x), z)], 'rear', np.sign(x) or 1, 0.012)
        if len(h): wp.append(h[0])
    if len(wp) > 1: D.strip_along(parts, np.array(wp), 0.006, 'trim_black', col=(0.5, 0.5, 0.5))
    for sgn in (1, -1):
        rail = []
        for s_ in np.linspace(0.45, -2.25, 28):
            h = D.ray_hit(f, (sgn * 0.58, s_, 2.3), (0, 0, -1), tmax=1.0)
            if h is not None: rail.append(h + np.array([0, 0, 0.055]))
        rail = np.array(rail)
        if len(rail) > 1:
            V_, F_ = tube(rail, 0.014, n_seg=10)
            parts.add('body', V_, F_, 'trim_black', COL=np.c_[np.full((len(V_), 3), 0.9), np.ones(len(V_))])
            for k in (0, len(rail) // 2, len(rail) - 1):
                bv, bf = box(rail[k] - np.array([0, 0, 0.03]), (0.018, 0.05, 0.03))
                parts.add('body', bv, bf, 'trim_black', flat=True)
    # mirrors (larger)
    for sgn in (1, -1):
        h = surf([(1.15, 1.13)], 'side', sgn, -0.005)
        if len(h):
            b = h[0].copy(); b[0] = abs(b[0])
            D.mirror_parts(parts, f, tuple(b), sgn, scale=1.15)
    # wipers
    (s0, z0), _ = P['ws_line']
    for (xa, xb) in [(-0.68, 0.02), (0.06, 0.62)]:
        pts = []
        for x in np.linspace(xa, xb, 10):
            t = (x - xa) / (xb - xa)
            h = D.ray_hit(f, (x, s0 - 0.08 - 0.05 * t, 2.2), (0, 0, -1), tmax=1.5)
            if h is not None: pts.append(h + D.grad(f, h)[0] * 0.012)
        if len(pts) > 1: D.strip_along(parts, np.array(pts), 0.0055, 'trim_black', col=(0.5, 0.5, 0.5))
    IN.add_interior(parts, B, dict(seat_s=0.45, seat_x=0.40, floor=0.36, dash_s=1.15, dash_z=1.06, dash_w=0.80, wheel_s=0.78,
                                    hip_z=0.62, seat_h=0.66, rear_seats=True, rear_s=-0.55,
                                    cabin_bounds=((-0.85, -2.35, 0.36), (0.85, 1.5, 1.72))))
    CB.log('details done', parts.tris('body'))
    axles = [('FL', M.S_FA, M.X_WF, 0.235), ('FR', M.S_FA, M.X_WF, 0.235), ('RL', M.S_RA, M.X_WR, 0.235), ('RR', M.S_RA, M.X_WR, 0.235)]
    style = dict(r_lip=0.236, r_barrel=0.208, width=0.20, spokes=6, split=0.0, a_face=0.084, dish=0.018,
                 spoke_depth=0.026, spoke_w0=0.024, spoke_w1=0.019)
    cent = W.add_wheels(parts, axles, None, M.R_TYRE, 0.229, 0.235, style, 0.165)
    mats = CB.base_materials(M.PAINT, (0.62, 0.63, 0.65), rim_rough=0.28, caliper=(0.12, 0.12, 0.13))
    mats['plate']['tex_arr'] = D.plate_texture('8MVN417')
    mats['brake']['tex_arr'] = W.disc_texture(0.165)
    mats['glass']['color'] = (0.025, 0.028, 0.03)
    CB.export(parts, mats, OUT, cent)

if __name__ == '__main__':
    build()
