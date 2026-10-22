"""Red sports coupe -> assets/car_sports.glb.   python3 sports.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from carlib import Parts, normalize, sstep, smax, smin, mirror_half, tube, box, revolve, vertex_normals, catmull_closed, mc_mesh
from body import Body
from surfops import build_labelled
import carbuild as CB
import details as D
import wheels as W
import interior as IN
import sports_params as M

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '../../assets/car_sports.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0065
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 50000

B = Body(M.P)
P = M.P
f = B.field

# ------------------------------------------------------------------ feature functions
def dlo_outline():
    """Side window daylight opening in (s, z), derived from the greenhouse."""
    belt = P['belt']
    zb = lambda s: belt + 0.045 + 0.02 * sstep(-0.6, -1.5, s)
    # A-pillar line: windshield side edge moved back by the pillar width
    zs = np.linspace(zb(0.5) + 0.0, 1.16, 12)
    front = []
    for z in zs:
        # find s where windshield plane meets the side of the greenhouse at height z
        ss = np.linspace(-0.4, 0.8, 600)
        wg = B.gh_width(ss, z)
        d = B.ws_dist(wg, ss, np.full_like(ss, z))
        i = np.argmin(np.abs(d))
        front.append((ss[i] - 0.075, z))
    front = np.array(front)
    # top edge: below the roof/side turn
    st = np.linspace(front[-1, 0] - 0.05, -1.62, 18)
    top = []
    for s_ in st:
        zr = B.c['Zroof'](s_) - P['roof_crown'] * (B.gh_width(s_, B.c['Zroof'](s_)) / 0.7) ** 2
        top.append((s_, zr - 0.075))
    top = np.array(top)
    # keep only while above belt line
    ok = top[:, 1] > zb(top[:, 0]) + 0.03
    top = top[ok]
    tail = top[-1]
    bottom = [(s_, zb(s_)) for s_ in np.linspace(tail[0] + 0.12, front[0, 0] + 0.02, 10)]
    pts = list(front[::-1][::-1])  # bottom->top along A pillar
    pts = list(front) + list(top[1:]) + [(tail[0] - 0.04, zb(tail[0]) + 0.012)] + bottom
    return np.array(pts)

DLO = dlo_outline()
side_dom = lambda V: (np.abs(V[:, 0]) > 0.45) & (V[:, 2] > P['belt'] - 0.06)
fn_dlo = D.proj_fn(DLO, 'side', domain=side_dom, n_per=8)
B_PILLAR_S = -0.78
def fn_bp(V, N):
    # B-pillar band (black) splitting door glass and quarter glass
    sb = B_PILLAR_S - 0.10 * (V[:, 2] - 0.93)
    return np.where(side_dom(V), np.abs(V[:, 1] - sb) - 0.014, 1.0)

def fn_ws(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    g1 = ax - (B.gh_width(s, z) - 0.085)
    g2 = z - 1.165
    g3 = (P['belt'] + 0.03) - z
    d = smax(smax(g1, g2, 0.05), g3, 0.04)
    return np.where(s > -0.35, d, 1.0)

def fn_bl(V, N):
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    g1 = ax - (B.gh_width(s, z) - 0.11)
    d = smax(smax(g1, s + 0.82, 0.06), -(s + 1.70), 0.05)
    return np.where(z > P['belt'] + 0.02, d, 1.0)

# panel gaps
door = mirror_half([])  if False else None
DOOR = [(0.735, 0.215), (0.72, 0.42), (0.69, 0.66), (0.64, 0.84), (0.60, 1.0), (-0.88, 1.0), (-0.86, 0.80),
        (-0.83, 0.55), (-0.82, 0.30), (-0.80, 0.215)]
side_dom2 = lambda V: (np.abs(V[:, 0]) > 0.55)
fn_door = D.proj_fn(DOOR, 'side', domain=side_dom2, n_per=6)
HOOD = [(0.0, 2.14), (0.35, 2.12), (0.52, 2.08), (0.60, 2.0), (0.615, 1.5), (0.60, 0.72), (0.0, 0.72)]
HOOD = np.concatenate([np.array(HOOD), np.array(HOOD)[::-1][1:-1] * [-1, 1]])
fn_hood = D.proj_fn(HOOD, 'top', domain=lambda V: (V[:, 2] > 0.55) & (V[:, 1] > 0.4), n_per=8, mirror=False)
DECK = [(0.0, -1.78), (0.60, -1.80), (0.64, -1.95), (0.62, -2.21), (0.0, -2.22)]
DECK = np.concatenate([np.array(DECK), np.array(DECK)[::-1][1:-1] * [-1, 1]])
fn_deck = D.proj_fn(DECK, 'top', domain=lambda V: (V[:, 2] > 0.86) & (V[:, 1] < -1.6), n_per=8, mirror=False)
FUEL = [(-1.40, 0.73), (-1.40, 0.83), (-1.55, 0.83), (-1.55, 0.73)]
fn_fuel = D.proj_fn(catmull_closed(np.array([(-1.40, 0.735), (-1.40, 0.825), (-1.405, 0.83), (-1.545, 0.83), (-1.55, 0.825), (-1.55, 0.735), (-1.545, 0.73), (-1.405, 0.73)]), 4),
                    'side', domain=lambda V: V[:, 0] > 0.5, n_per=3, mirror=False)
# front fascia split line (bumper to fender) from the arch up to the lamp
FASCIA = [(1.86, 0.50), (1.84, 0.56), (1.83, 0.64), (1.90, 0.64), (1.95, 0.50)]

# lights / openings (front & rear projections, |x|)
HEAD = [(0.34, 0.592), (0.50, 0.604), (0.66, 0.626), (0.80, 0.652), (0.875, 0.668), (0.91, 0.660), (0.91, 0.628),
        (0.87, 0.600), (0.76, 0.566), (0.62, 0.536), (0.46, 0.522), (0.36, 0.530), (0.33, 0.55)]
front_dom = lambda V: V[:, 1] > 1.6
fn_head = D.proj_fn(HEAD, 'front', domain=front_dom, n_per=8)
GRILLE = [(0.0, 0.500), (0.33, 0.500), (0.46, 0.468), (0.52, 0.40), (0.50, 0.285), (0.44, 0.215), (0.0, 0.215)]
fn_grille = D.proj_fn(mirror_half(GRILLE), 'front', domain=front_dom, n_per=8, mirror=False)
INTAKE = [(0.62, 0.43), (0.78, 0.455), (0.86, 0.43), (0.87, 0.30), (0.80, 0.215), (0.64, 0.215), (0.585, 0.30)]
fn_intake = D.proj_fn(INTAKE, 'front', domain=front_dom, n_per=8)
rear_dom = lambda V: V[:, 1] < -1.95
TAIL = [(0.0, 0.873), (0.50, 0.876), (0.74, 0.888), (0.88, 0.905), (0.935, 0.90), (0.945, 0.865), (0.92, 0.832),
        (0.86, 0.818), (0.72, 0.838), (0.50, 0.856), (0.0, 0.859)]
TAIL = np.concatenate([np.array(TAIL), np.array(TAIL)[::-1][1:-1] * [-1, 1]])
fn_tail = D.proj_fn(TAIL, 'rear', domain=rear_dom, n_per=8, mirror=False)
RPLATE = [(0.0, 0.705), (0.17, 0.705), (0.185, 0.69), (0.185, 0.525), (0.17, 0.51), (0.0, 0.51)]
fn_rplate = D.proj_fn(mirror_half(RPLATE), 'rear', domain=rear_dom, n_per=4, mirror=False)
HANDLE = [(-0.48, 0.795), (-0.48, 0.815), (-0.50, 0.825), (-0.66, 0.825), (-0.68, 0.815), (-0.68, 0.795), (-0.66, 0.785), (-0.50, 0.785)]
fn_handle = D.proj_fn(HANDLE, 'side', domain=side_dom2, n_per=4)
MARKER_F = [(1.93, 0.47), (1.93, 0.50), (2.03, 0.50), (2.03, 0.47)]
fn_mark_f = D.proj_fn(catmull_closed(np.array(MARKER_F), 2), 'side', domain=lambda V: (np.abs(V[:, 0]) > 0.6) & (V[:, 1] > 1.7), n_per=3)
MARKER_R = [(-2.03, 0.80), (-2.03, 0.83), (-2.13, 0.83), (-2.13, 0.80)]
fn_mark_r = D.proj_fn(catmull_closed(np.array(MARKER_R), 2), 'side', domain=lambda V: (np.abs(V[:, 0]) > 0.6) & (V[:, 1] < -1.9), n_per=3)

zl_curve = np.array([(2.4, 0.185), (2.0, 0.17), (1.6, 0.215), (0.95, 0.215), (0.7, 0.215), (-0.9, 0.215), (-1.0, 0.215),
                     (-1.75, 0.215), (-1.95, 0.30), (-2.4, 0.345)])
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

GAP = 0.0022
cuts = [
    ('dlo', fn_dlo, [0.0, 0.020]),
    ('bp', fn_bp, [0.0]),
    ('ws', fn_ws, [0.0, -0.035]),
    ('bl', fn_bl, [0.0, -0.03]),
    ('door', fn_door, [-GAP, GAP]),
    ('hood', fn_hood, [-GAP, GAP]),
    ('deck', fn_deck, [-GAP, GAP]),
    ('fuel', fn_fuel, [-GAP, GAP]),
    ('head', fn_head, [0.0, 0.006]),
    ('grille', fn_grille, [0.0, 0.010]),
    ('intake', fn_intake, [0.0, 0.006]),
    ('tail', fn_tail, [0.0, -0.005]),
    ('rplate', fn_rplate, [0.0]),
    ('handle', fn_handle, [0.0]),
    ('mark_f', fn_mark_f, [0.0]),
    ('mark_r', fn_mark_r, [0.0]),
    ('lower', fn_lower, [0.0]),
    ('well', fn_well, [0.004]),
]

labels = {
    'paint': dict(mat='paint'),
    'gap': dict(mat='trim_black', depth=0.0045, wall='paint', wall_col=0.25, col=0.5),
    'glass': dict(mat='glass', depth=0.007, wall='trim_black', wall_col=0.6),
    'frit': dict(mat='trim_black', depth=0.007, wall='trim_black', col=0.8),
    'dlo_trim': dict(mat='trim_black', depth=0.0, col=1.0),
    'lamp': dict(mat='trim_black', depth=0.03, wall='chrome', wall_col=0.6, col=0.7),
    'lamp_bezel': dict(mat='trim_black', depth=0.0, col=1.0),
    'grille': dict(mat='trim_black', depth=0.055, wall='trim_black', wall_col=0.35, col=0.25),
    'grille_sur': dict(mat='trim_black', depth=0.0, col=1.0),
    'intake': dict(mat='trim_black', depth=0.05, wall='trim_black', wall_col=0.35, col=0.25),
    'intake_sur': dict(mat='trim_black', depth=0.0, col=1.0),
    'tail': dict(mat='light_rear', depth=0.006, wall='trim_black', wall_col=0.5),
    'tail_bez': dict(mat='trim_black', depth=0.0, col=0.9),
    'rplate': dict(mat='trim_black', depth=0.014, wall='paint', wall_col=0.5, col=0.6),
    'handle': dict(mat='chrome', depth=0.0035, wall='trim_black', wall_col=0.3),
    'marker_f': dict(mat='light_front', depth=0.002, col=(1.0, 0.45, 0.05)),
    'marker_r': dict(mat='light_rear', depth=0.002),
    'lower': dict(mat='trim_black', depth=0.0, col=0.75),
    'well': dict(mat='trim_black', depth=0.0, col=0.25),
    'under': dict(mat='trim_black', depth=0.0, col=0.3),
}

def F_(name):
    return lambda fm: fm[name]

rules = [
    ('well', lambda fm: fm['well'] < 0.004),
    ('under', lambda fm: (fm['n'][:, 2] < -0.55) & (fm['c'][:, 2] < 0.3)),
    ('glass', lambda fm: (fm['ws'] < -0.035) | ((fm['bl'] < -0.03)) | ((fm['dlo'] < 0) & (fm['bp'] > 0))),
    ('frit', lambda fm: (fm['ws'] < 0) | (fm['bl'] < 0) | ((fm['dlo'] < 0) & (fm['bp'] <= 0))),
    ('dlo_trim', lambda fm: fm['dlo'] < 0.020),
    ('lamp', lambda fm: fm['head'] < 0),
    ('lamp_bezel', lambda fm: fm['head'] < 0.006),
    ('grille', lambda fm: fm['grille'] < 0),
    ('grille_sur', lambda fm: fm['grille'] < 0.010),
    ('intake', lambda fm: fm['intake'] < 0),
    ('intake_sur', lambda fm: fm['intake'] < 0.006),
    ('tail', lambda fm: fm['tail'] < -0.005),
    ('tail_bez', lambda fm: fm['tail'] < 0),
    ('rplate', lambda fm: fm['rplate'] < 0),
    ('handle', lambda fm: fm['handle'] < 0),
    ('marker_f', lambda fm: fm['mark_f'] < 0),
    ('marker_r', lambda fm: fm['mark_r'] < 0),
    ('lower', lambda fm: fm['lower'] < 0),
    ('gap', lambda fm: (np.abs(fm['door']) < GAP) | (np.abs(fm['hood']) < GAP) | (np.abs(fm['deck']) < GAP) | (np.abs(fm['fuel']) < GAP)),
]

def ao_col(V, N):
    """Cheap baked occlusion for the body: darker low and inside/near the wheel arches, lighter on top."""
    z = V[:, 2]; s = V[:, 1]
    a = 0.62 + 0.38 * sstep(0.12, 0.55, z)
    for (sa, za, R, xin) in P['wells']:
        r = np.sqrt((s - sa) ** 2 + (z - za) ** 2)
        a *= 1 - 0.3 * np.exp(-((r - R) / 0.05) ** 2) * (np.abs(V[:, 0]) > 0.5)
    a *= 0.85 + 0.15 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
    return np.repeat(a[:, None], 3, 1)

def build():
    CB.log('sports: body field')
    V, F, N = CB.body_surface(B, M.BOUNDS, RES, TARGET)
    cs = CB.run_cuts(B, V, F, N, cuts)
    parts = Parts()
    parts, lab = build_labelled(cs, labels, rules, 'paint', col_fn=ao_col, parts=parts, node='body')
    names = list(labels.keys())
    # lamp cover glass at the surface over the headlamp recesses
    m = (lab == names.index('lamp'))
    Fm = cs.F[m]; used = np.unique(Fm); remap = -np.ones(len(cs.V), np.int64); remap[used] = np.arange(len(used))
    parts.add('body', cs.V[used] + cs.N[used] * 0.0005, remap[Fm], 'light_cover', N=cs.N[used])
    CB.log('body labelled', parts.tris('body'))
    add_lamp_internals(parts)
    add_rear_details(parts)
    add_front_details(parts)
    for sgn in (1, -1):
        D.mirror_parts(parts, f, (sgn * 0.0 + 0.0, 0.0, 0.0), sgn) if False else None
    add_mirrors(parts)
    add_wipers(parts)
    IN.add_interior(parts, B, dict(seat_s=-0.45, seat_x=0.36, floor=0.24, dash_s=0.38, dash_z=0.86, wheel_s=0.05, hip_z=0.36,
                                    seat_h=0.62, rear_seats=False, cabin_bounds=((-0.8, -1.5, 0.2), (0.8, 0.6, 1.24))))
    CB.log('details done', parts.tris('body'))
    axles = [('FL', M.S_FA, M.X_WF, 0.255), ('FR', M.S_FA, M.X_WF, 0.255), ('RL', M.S_RA, M.X_WR, 0.285), ('RR', M.S_RA, M.X_WR, 0.285)]
    style = dict(r_lip=0.262, r_barrel=0.232, width=0.24, spokes=5, split=0.030, a_face=0.102, dish=0.032,
                 spoke_depth=0.03, spoke_w0=0.016, spoke_w1=0.013)
    cent = W.add_wheels(parts, axles, None, M.R_TYRE, 0.254, 0.255, style, 0.19)
    mats = CB.base_materials((0.45, 0.02, 0.02), (0.22, 0.22, 0.23), rim_rough=0.3)
    mats['plate']['tex_arr'] = D.plate_texture('7ABC123')
    mats['brake']['tex_arr'] = W.disc_texture(0.19)
    CB.export(parts, mats, OUT, cent)

def add_lamp_internals(parts):
    # DRL strip just inside the upper edge of each headlamp, and two projector lenses
    for sgn in (1, -1):
        pts2 = [(0.37, 0.578), (0.52, 0.590), (0.66, 0.610), (0.80, 0.636), (0.885, 0.652)]
        c = D.surface_curve(f, pts2, 'front', sgn, offset=-0.012)
        if len(c) > 1:
            D.strip_along(parts, D.smooth_path(c, 40), 0.0042, 'light_front', n_seg=8)
        for (px, pz, r) in [(0.56, 0.556, 0.024), (0.71, 0.578, 0.024)]:
            h = D.surface_curve(f, [(px, pz)], 'front', sgn, offset=-0.026)
            if len(h) == 0: continue
            n = D.grad(f, h[0])[0]
            ax_ = normalize(np.array([0, 1.0, 0.25]))
            # lens: short cylinder (chrome ring) + dome (glass-dark)
            prof = [(-0.012, r * 1.05), (0.0, r * 1.05), (0.0, r * 0.82), (0.004, r * 0.80), (0.010, r * 0.55), (0.013, 0.0)]
            Vl, Fl, _ = revolve(prof, 24)
            # local x is axial: map to ax_
            u = ax_; v = normalize(np.cross(u, [1.0, 0, 0])); w = np.cross(u, v)
            Vw = h[0] + Vl[:, 0:1] * u + Vl[:, 1:2] * v + Vl[:, 2:3] * w
            Nn = vertex_normals(Vw, Fl)
            if np.mean(np.einsum('ij,j->i', Nn, u)) < 0: Fl = Fl[:, ::-1]
            parts.add('body', Vw, Fl, 'chrome')

def rear_point(x, z, off=0.0):
    h = D.surface_curve(f, [(abs(x), z)], 'rear', np.sign(x) or 1, offset=off)
    return h[0] if len(h) else None

def add_rear_details(parts):
    # LED light bars inside the tail lamp band
    for sgn in (1, -1):
        pts = [(0.02, 0.866), (0.30, 0.867), (0.55, 0.869), (0.72, 0.878), (0.86, 0.888), (0.92, 0.882)]
        c = D.surface_curve(f, pts, 'rear', sgn, offset=-0.004)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 50), 0.0032, 'light_rear_led', n_seg=6)
        pts = [(0.74, 0.850), (0.86, 0.842), (0.925, 0.858)]
        c = D.surface_curve(f, pts, 'rear', sgn, offset=-0.004)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 20), 0.0028, 'light_rear_led', n_seg=6)
    # quad exhaust tips
    for sgn in (1, -1):
        for x in (0.50, 0.63):
            p = rear_point(sgn * x, 0.255, 0.0)
            if p is None: continue
            s0 = p[1] - 0.03
            prof = [(0.0, 0.030), (0.0, 0.040), (0.004, 0.044), (0.05, 0.044), (0.055, 0.041), (0.055, 0.036), (0.0, 0.036)]
            Vt, Ft, _ = revolve(prof, 28, closed_profile=True)
            # axis along -s
            Vw = np.stack([p[0] + Vt[:, 1], s0 - Vt[:, 0] + 0.0, p[2] + Vt[:, 2]], 1)
            Nn = vertex_normals(Vw, Ft)
            r = np.linalg.norm(Vt[:, 1:], axis=1)
            if np.mean(np.einsum('ij,ij->i', Nn[r > 0.042][:, [0, 2]], (Vw[r > 0.042][:, [0, 2]] - p[[0, 2]]))) < 0: Ft = Ft[:, ::-1]
            parts.add('body', Vw, Ft, 'chrome')
            # dark inner pipe
            Vi, Fi = tube(np.array([[p[0], s0 - 0.04, p[2]], [p[0], s0 + 0.25, p[2]]]), 0.031, n_seg=20, caps=False)
            parts.add('body', Vi, Fi[:, ::-1], 'trim_black', COL=np.c_[np.full((len(Vi), 3), 0.25), np.ones(len(Vi))])
    # rear plate
    p = rear_point(0.0, 0.607, 0.0)
    n = D.grad(f, p)[0]
    D.plate_mesh(parts, p - n * 0.012, n, (0, 0, 1.0))
    # diffuser fins
    for x in (-0.30, -0.12, 0.12, 0.30):
        p0 = rear_point(x, 0.20, 0.0)
        if p0 is None: continue
        bv, bf = D.box((x, p0[1] + 0.12, 0.175), (0.004, 0.16, 0.05))
        parts.add('body', bv, bf, 'trim_black', flat=True, COL=np.c_[np.full((8, 3), 0.6), np.ones(8)])

def add_front_details(parts):
    def depth_s(x, z):
        h = D.surface_curve(f, [(abs(x), z)], 'front', 1, offset=0.0)
        return (h[0][1] - 0.022) if len(h) else 2.1
    D.lattice_grille(parts, f, fn_grille.sd, (-0.52, 0.52), (0.215, 0.50), depth_s, pitch=0.025, bar=0.0038)
    for sgn in (1, -1):
        def depth_si(x, z):
            h = D.surface_curve(f, [(abs(x), z)], 'front', 1, offset=0.0)
            return (h[0][1] - 0.02) if len(h) else 2.0
        sdm = lambda ax, z: fn_intake.sd(ax, z)
        D.lattice_grille(parts, f, sdm, (0.58, 0.88) if sgn > 0 else (-0.88, -0.58), (0.215, 0.46), depth_si, pitch=0.025, bar=0.0038)
    # front plate on the grille
    h = []  # no front plate (rear only)
    if len(h):
        p = h[0].copy(); p[1] -= 0.035
        D.plate_mesh(parts, p, (0, 1.0, 0.05), (0, 0, 1.0))
    # front splitter lip
    pts = [(0.0, 0.135), (0.4, 0.14), (0.7, 0.15), (0.86, 0.17)]
    for sgn in (1, -1):
        c = D.surface_curve(f, pts, 'front', sgn, offset=0.004)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 30), 0.008, 'trim_black', n_seg=6)

def add_mirrors(parts):
    for sgn in (1, -1):
        h = D.surface_curve(f, [(0.50, 0.965)], 'side', sgn, offset=-0.005)
        if len(h) == 0: continue
        base = h[0].copy(); base[0] = abs(base[0])
        D.mirror_parts(parts, f, tuple(base), sgn, scale=0.95)

def add_wipers(parts):
    (s0, z0), (s1, z1) = P['ws_line']
    for (xa, xb) in [(-0.60, 0.02), (0.06, 0.64)]:
        pts = []
        for x in np.linspace(xa, xb, 10):
            t = (x - xa) / (xb - xa)
            sw = s0 - 0.07 - 0.05 * t
            h = D.ray_hit(f, (x, sw, 1.6), (0, 0, -1), tmax=1.2)
            if h is not None:
                n = D.grad(f, h)[0]
                pts.append(h + n * 0.012)
        if len(pts) > 1:
            D.strip_along(parts, np.array(pts), 0.0055, 'trim_black', n_seg=6, col=(0.5, 0.5, 0.5))

if __name__ == '__main__':
    build()
