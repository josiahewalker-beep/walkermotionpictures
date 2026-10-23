"""Generic 1990s American car generator (sedan / wagon / SUV / compact pickup) for the drive-in.

Each car script (hero.py, wagon.py, ...) passes a config dict C to build(C, out_path).
Model frame: x lateral (x < 0 = car's LEFT / driver side = glTF +X), s forward, z up, metres.
Pipeline (from ../desert/src/cars): implicit body field -> marching cubes -> Blender decimate -> analytic (blurred)
normals -> exact level-set cuts -> labelled insets with walls -> details -> GLB via blendout.py.

Side/front/rear features are defined as inequality masks rasterised to signed-distance fields (MaskSDF), or as
3D rounded boxes (hood, trunk lid, liftgate), so every shut line is an exact cut through the mesh.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from carlib import Parts, normalize, sstep, smax, smin, tube, box, revolve, vertex_normals, SDF2D
from body import Body
from surfops import build_labelled
import carbuild as CB
import details as D
import interior as IN
import wheels90 as W9

ASSETS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../assets'))
BIG = 1.0

def lin(srgb):
    return tuple(((c / 255 + 0.055) / 1.055) ** 2.4 for c in srgb)

class MaskSDF:
    """Signed distance (negative inside) of a 2D region given as a boolean function on a grid; convex corners
    rounded by radius rnd (erode + dilate)."""
    def __init__(self, inside_fn, lo, hi, res=0.0025, rnd=0.0):
        lo = np.asarray(lo, float); hi = np.asarray(hi, float)
        nu = int(np.ceil((hi[0] - lo[0]) / res)) + 1; nv = int(np.ceil((hi[1] - lo[1]) / res)) + 1
        u = lo[0] + np.arange(nu) * res; v = lo[1] + np.arange(nv) * res
        UU, VV = np.meshgrid(u, v, indexing='ij')
        m = inside_fn(UU, VV)
        d = self._sd(m, res)
        if rnd > 0:
            d = self._sd(d < -rnd, res) - rnd
            m2 = d < 0
            # also round concave corners (dilate then erode)
            d2 = self._sd(~m2, res)       # distance inside the complement
            d = -(self._sd(d2 < -rnd, res) - rnd)
        self.d = ndimage.gaussian_filter(d, 0.8).astype(np.float32); self.lo = lo; self.res = res; self.shape = d.shape
    @staticmethod
    def _sd(m, res):
        din = ndimage.distance_transform_edt(m); dout = ndimage.distance_transform_edt(~m)
        return (dout - din) * res + np.where(m, 0.5 * res, -0.5 * res)
    __call__ = SDF2D.__call__

def rbox3(V, lo, hi, k=0.02):
    """Rounded 3D box distance (approx) in model frame; lo/hi may contain None for open sides."""
    x, s, z = np.abs(V[:, 0]), V[:, 1], V[:, 2]
    P = [x, s, z]
    d = None
    for i in range(3):
        for (lim, sg) in ((lo[i], -1), (hi[i], 1)):
            if lim is None: continue
            di = sg * (P[i] - lim)
            d = di if d is None else smax(d, di, k)
    return d

def build(C, out):
    P = C['P']
    B = Body(P)
    if 'field_mod' in C:
        fo, ff, fm_ = B.outer, B.field, C['field_mod']
        B.outer = lambda x, s, z: fm_(fo(x, s, z), x, s, z)
        B.field = lambda x, s, z: fm_(ff(x, s, z), x, s, z)
    f = B.field
    BELT = P['belt']
    S_FA, S_RA, RT = C['S_FA'], C['S_RA'], C['R_TYRE']
    wells = P['wells']
    Rw = wells[0][2]; za = wells[0][1]
    gw = lambda s, z: B.gh_width(s, z)

    # ------------------------------------------------ greenhouse edges in side view
    zgrid = np.linspace(0.0, 2.2, 441)
    ss = np.linspace(-3.0, 3.0, 2401)
    Sg, Zg = np.meshgrid(ss, zgrid)
    dws = B.ws_dist(gw(Sg, Zg), Sg, Zg)
    a_edge = np.full(len(zgrid), 9.0)
    for i in range(len(zgrid)):
        j = np.where(dws[i] > 0)[0]
        j = j[ss[j] > -0.5] if len(j) else j
        if len(j): a_edge[i] = ss[j[0]]
    if 'bl_line' in P:
        dbl = B.bl_dist(gw(Sg, Zg), Sg, Zg)
        c_edge = np.full(len(zgrid), -9.0)
        for i in range(len(zgrid)):
            j = np.where((dbl[i] > 0) & (ss < 0.5))[0]
            if len(j): c_edge[i] = ss[j[-1]]
    else:
        c_edge = np.full(len(zgrid), -9.0)
    a_s = lambda z: np.interp(z, zgrid, a_edge)
    c_s = lambda z: np.interp(z, zgrid, c_edge)
    roof_z = lambda s: B.c['Zroof'](s) - P['roof_crown'] * (gw(s, B.c['Zroof'](s)) / 0.7) ** 2

    zb = BELT + C.get('dlo_bot', 0.035)
    a_off, top_off = C.get('a_off', 0.075), C.get('top_off', 0.075)
    dlo_rear = C['dlo_rear']          # fn(z) -> rear edge s of the side glass
    def dlo_in(S, Z):
        return (Z > zb) & (S < a_s(Z) - a_off) & (S > dlo_rear(Z, c_s)) & (Z < roof_z(S) - top_off)
    SIDE_LO, SIDE_HI = (-3.0, 0.0), (3.0, 2.2)
    dlo_sdf = MaskSDF(dlo_in, SIDE_LO, SIDE_HI, rnd=C.get('dlo_round', 0.035))
    side_dom = lambda V, N: (np.abs(V[:, 0]) > 0.45) & (np.abs(N[:, 0]) > 0.3)
    def side_fn(sdf, side=None, dom=None):
        def fn(V, N):
            d = sdf(V[:, 1], V[:, 2])
            ok = side_dom(V, N) if dom is None else dom(V, N)
            if side is not None: ok = ok & (side * V[:, 0] > 0)
            return np.where(ok, d, BIG)
        fn.sdf = sdf
        return fn
    fn_dlo = side_fn(dlo_sdf, dom=lambda V, N: (np.abs(V[:, 0]) > 0.45) & (V[:, 2] > BELT - 0.08) & (np.abs(N[:, 0]) > 0.25))
    pillars = C['pillars']            # list of (s at belt, half width, slant ds/dz)
    def fn_bp(V, N):
        s, z = V[:, 1], V[:, 2]
        d = np.full(len(V), 1.0)
        for (sp, hw, sl) in pillars:
            d = np.minimum(d, np.abs(s - (sp + sl * (z - BELT))) - hw)
        return np.where(np.abs(V[:, 0]) > 0.45, d, 1.0)
    # windscreen / backlight glass (inset inside the frit)
    def fn_ws(V, N):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
        wtop = C['ws_ztop'] if 'ws_ztop' in C else roof_z(s) - C.get('ws_top', 0.06)
        d = smax(smax(ax - (gw(s, z) - C.get('ws_side', 0.09)), z - wtop, 0.05),
                 (BELT + 0.03) - z, 0.04)
        return np.where((s > C['ws_dom']) & (N[:, 2] > -0.2), d, 1.0)
    def fn_bl(V, N):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
        ztop = C['bl_ztop'] if 'bl_ztop' in C else roof_z(s) - C.get('bl_top', 0.06)
        d = smax(smax(ax - (gw(s, z) - C.get('bl_side', 0.10)), z - ztop, 0.05),
                 C['bl_zlo'] - z, 0.04)
        return np.where((s < C['bl_dom']) & (z > BELT - 0.05), d, 1.0)

    GAP = 0.0024
    sill = C.get('sill', 0.30)
    s_b = lambda z: C['b_s'] + C.get('b_slant', -0.08) * (z - BELT)
    fd0 = C['fd0']
    dtop = lambda S: roof_z(S) - top_off + 0.035
    def fdoor_in(S, Z):
        front = np.where(Z < BELT - 0.03, fd0, np.minimum(fd0, a_s(Z) - a_off + 0.035))
        rear = s_b(Z) if C.get('doors', 4) == 4 else C['fd1'](Z)
        if C.get('doors', 4) != 4:
            rear = np.where(Z > BELT - 0.03, np.maximum(rear, dlo_rear(Z, c_s) - 0.035), rear)
        return (Z > sill) & (Z < dtop(S)) & (S < front) & (S > rear)
    side2 = lambda V, N: (np.abs(V[:, 0]) > 0.5) & (np.abs(N[:, 0]) > 0.25) & (V[:, 2] < 1.9)
    fn_fdoor = side_fn(MaskSDF(fdoor_in, SIDE_LO, SIDE_HI, rnd=0.03), dom=side2)
    fns_extra = []
    if C.get('doors', 4) == 4:
        rd1 = C['rd1']                # fn(Z, c_s) rear edge of the rear door
        def rdoor_in(S, Z):
            out_arch = ((S - S_RA) ** 2 + (Z - za) ** 2) > (Rw + 0.045) ** 2
            return (Z > sill) & (Z < dtop(S)) & (S < s_b(Z)) & (S > rd1(Z, c_s)) & out_arch
        fn_rdoor = side_fn(MaskSDF(rdoor_in, SIDE_LO, SIDE_HI, rnd=0.03), dom=side2)
    else:
        fn_rdoor = lambda V, N: np.full(len(V), BIG)
    # hood / deck lid / liftgate as rounded 3D boxes
    hb = C['hood']        # (s_rear, half_w, z_front_edge)
    fn_hood = lambda V, N: np.where((V[:, 1] > hb[0] - 0.3) & (V[:, 2] > hb[2] - 0.15), rbox3(V, (None, hb[0], hb[2]), (hb[1], None, None), 0.03), BIG)
    tb = C['lid']         # (s_front, half_w, z_bottom)  lid = s < s_front, |x| < w, z > z_bottom
    fn_lid = lambda V, N: np.where((V[:, 1] < tb[0] + 0.3) & (V[:, 2] > tb[2] - 0.15), rbox3(V, (None, None, tb[2]), (tb[1], tb[0], None), 0.03), BIG)
    fz = C.get('fuel', (S_RA - 0.42, BELT - 0.12))
    fn_fuel = side_fn(MaskSDF(lambda S, Z: (np.abs(S - fz[0]) < 0.085) & (np.abs(Z - fz[1]) < 0.075), SIDE_LO, SIDE_HI, rnd=0.02), side=1)

    FRONT_LO, FRONT_HI = (0.0, 0.0), (1.2, 1.6)
    front_dom = lambda V, N: (V[:, 1] > S_FA + C.get('front_dom', 0.55)) & (N[:, 1] > -0.1)
    rear_dom = lambda V, N: (V[:, 1] < S_RA - C.get('rear_dom', 0.6)) & (N[:, 1] < 0.1)
    def plane_fn(inside, dom, plane='front', rnd=0.012, mirror=True):
        sdf = MaskSDF(inside, FRONT_LO if mirror else (-1.2, 0.0), FRONT_HI, res=0.002, rnd=rnd)
        def fn(V, N):
            u = np.abs(V[:, 0]) if mirror else V[:, 0]
            return np.where(dom(V, N), sdf(u, V[:, 2]), BIG)
        fn.sdf = sdf
        return fn
    hl = C['head']        # (x0, x1, z0, z1)
    fn_head = plane_fn(lambda X, Z: (X > hl[0]) & (X < hl[1]) & (Z > hl[2]) & (Z < hl[3]), front_dom, rnd=C.get('head_rnd', 0.02))
    cl = C.get('corner', (hl[1] + 0.012, 2.0, hl[2], hl[3]))
    corner_dom = lambda V, N: (V[:, 1] > S_FA + C.get('corner_s', 0.62)) & (np.abs(V[:, 0]) > 0.3)
    fn_corner = plane_fn(lambda X, Z: (X > cl[0]) & (X < cl[1]) & (Z > cl[2]) & (Z < cl[3]), corner_dom, rnd=0.012)
    gr = C['grille']      # (half_w, z0, z1)
    fn_grille = plane_fn(lambda X, Z: (X < gr[0]) & (Z > gr[1]) & (Z < gr[2]), front_dom, rnd=C.get('grille_rnd', 0.015))
    li = C['lower_intake']
    fn_lowg = plane_fn(lambda X, Z: (X < li[0]) & (Z > li[1]) & (Z < li[2]), front_dom, rnd=0.02)
    tl = C['tail']        # (x0, z0, z1) tail lamp outboard of x0, wraps the corner
    tail_dom = lambda V, N: (V[:, 1] < C.get('tail_s', S_RA - C.get('rear_dom', 0.6))) & (N[:, 1] < 0.35)
    fn_tail = plane_fn(lambda X, Z: (X > tl[0]) & (Z > tl[1]) & (Z < tl[2]), tail_dom, rnd=0.015)
    fn_tpanel = plane_fn(lambda X, Z: (X < tl[0] - 0.012) & (Z > tl[1]) & (Z < tl[2]), rear_dom, rnd=0.01) if C.get('tail_panel', True) else (lambda V, N: np.full(len(V), BIG))
    rv = C.get('reverse', (tl[0] + 0.02, tl[0] + 0.13, tl[1] + 0.012, tl[1] + 0.06))
    fn_rev = plane_fn(lambda X, Z: (X > rv[0]) & (X < rv[1]) & (Z > rv[2]) & (Z < rv[3]), rear_dom, rnd=0.008)
    rp = C['rplate']      # (z centre)
    fn_rplate = plane_fn(lambda X, Z: (X < 0.175) & (np.abs(Z - rp) < 0.092), rear_dom, rnd=0.015)
    # door handles (pull-up flaps) and side markers
    hz = C.get('handle_z', BELT - 0.075)
    hs = C['handles']     # list of s centres
    fn_handle = side_fn(MaskSDF(lambda S, Z: (np.min([np.abs(S - h) for h in hs], 0) < 0.075) & (np.abs(Z - hz) < 0.021), SIDE_LO, SIDE_HI, rnd=0.012))
    mk = C.get('markers', ((S_FA + 0.78, 0.60), (S_RA - 0.80, 0.62)))
    fn_mark_f = side_fn(MaskSDF(lambda S, Z: (np.abs(S - mk[0][0]) < 0.06) & (np.abs(Z - mk[0][1]) < 0.022), SIDE_LO, SIDE_HI, rnd=0.008))
    fn_mark_r = side_fn(MaskSDF(lambda S, Z: (np.abs(S - mk[1][0]) < 0.06) & (np.abs(Z - mk[1][1]) < 0.022), SIDE_LO, SIDE_HI, rnd=0.008))
    rz = C['rub']         # (z centre fn(s), half height)
    def fn_rub(V, N):
        d = np.abs(V[:, 2] - rz[0](V[:, 1])) - rz[1]
        return np.where((N[:, 2] > -0.5) & (N[:, 2] < 0.6), d, BIG)
    zl = C.get('clad')    # None or z top of lower cladding (two-tone)
    fn_lower = (lambda V, N: V[:, 2] - zl(V[:, 1])) if zl else (lambda V, N: np.full(len(V), BIG))
    def fn_well(V, N):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]
        d = None
        for (sa, za_, R, xin) in wells:
            dc = np.sqrt((s - sa) ** 2 + (z - za_) ** 2) - R
            d = dc if d is None else np.minimum(d, dc)
        return np.where(np.abs(x) > 0.40, d, 1.0)
    def fn_clad(V, N):
        x, s, z = V[:, 0], V[:, 1], V[:, 2]
        d = None
        for (sa, za_, R, xin) in wells:
            dc = np.sqrt((s - sa) ** 2 + (z - za_) ** 2) - (R + C.get('arch_lip', 0.0))
            d = dc if d is None else np.minimum(d, dc)
        return np.where(np.abs(x) > 0.55, d, 1.0)
    open_win = C.get('open_window')     # hero: driver's front window rolled down
    def fn_open(V, N):
        return np.where((V[:, 0] < -0.4) & (V[:, 1] > s_b(V[:, 2]) + 0.01), 1.0, 0.0) - 0.5

    cuts = [
        ('dlo', fn_dlo, [0.0, 0.018]), ('bp', fn_bp, [0.0]), ('ws', fn_ws, [0.0, -0.04]), ('bl', fn_bl, [0.0, -0.035]),
        ('fdoor', fn_fdoor, [-GAP, GAP]), ('rdoor', fn_rdoor, [-GAP, GAP]),
        ('hood', fn_hood, [-GAP, GAP]), ('lid', fn_lid, [-GAP, GAP]), ('fuel', fn_fuel, [-GAP, GAP]),
        ('head', fn_head, [0.0, 0.008]), ('corner', fn_corner, [0.0]), ('grille', fn_grille, [0.0, 0.012]), ('lowg', fn_lowg, [0.0]),
        ('tail', fn_tail, [0.0, -0.006]), ('tpanel', fn_tpanel, [0.0]), ('rev', fn_rev, [0.0]), ('rplate', fn_rplate, [0.0]),
        ('handle', fn_handle, [0.0]), ('mark_f', fn_mark_f, [0.0]), ('mark_r', fn_mark_r, [0.0]),
        ('rub', fn_rub, [0.0]), ('lower', fn_lower, [0.0]), ('well', fn_well, [0.004]), ('clad', fn_clad, [0.0] if C.get('clad_cut', True) else []),
    ]
    cuts += list(C.get('extra_cuts', []))     # (name, fn(V, N), offsets): config-specific features (fog lamps, ...)
    if open_win:
        cuts.append(('open', fn_open, []))
    hmat = C.get('handle_mat', 'trim_black')
    labels = {
        'paint': dict(mat='paint'),
        'open': dict(mat='trim_black', depth=C.get('ledge', 0.065), wall='trim_black', wall_col=0.55, skip=True),
        'gap': dict(mat='trim_black', depth=0.005, wall='paint', wall_col=0.25, col=0.5),
        'glass': dict(mat='glass', depth=0.007, wall='trim_black', wall_col=0.15),
        'frit': dict(mat='trim_black', depth=0.008, wall='trim_black', col=0.8),
        'dlo_trim': dict(mat=C.get('dlo_mat', 'trim_black'), depth=0.0, col=1.0),
        'lamp': dict(mat='light_front', depth=0.03, wall='chrome', wall_col=0.6, col=0.8),
        'lamp_bezel': dict(mat='trim_black', depth=0.0, col=1.0),
        'corner': dict(mat='light_marker', depth=0.004, wall='trim_black', wall_col=0.5),
        'grille': dict(mat='trim_black', depth=0.04, wall='trim_black', wall_col=0.35, col=0.25),
        'grille_sur': dict(mat=C.get('grille_sur_mat', 'trim_black'), depth=0.0),
        'lowg': dict(mat='trim_black', depth=0.035, wall='trim_black', wall_col=0.35, col=0.25),
        'tail': dict(mat='light_rear', depth=0.006, wall='trim_black', wall_col=0.5),
        'tail_bez': dict(mat='trim_black', depth=0.0, col=0.9),
        'rev': dict(mat='light_front', depth=0.004, wall='trim_black', wall_col=0.5, col=0.7),
        'tpanel': dict(mat='light_rear', depth=0.004, wall='trim_black', wall_col=0.5, col=0.45),
        'rplate': dict(mat='trim_black', depth=0.014, wall='paint', wall_col=0.5, col=0.6),
        'handle': dict(mat=hmat, depth=0.005, wall='trim_black', wall_col=0.3, col=0.8),
        'marker_f': dict(mat='light_marker', depth=0.002),
        'marker_r': dict(mat='light_rear', depth=0.002),
        'rub': dict(mat=C.get('rub_mat', 'trim_black'), depth=-C.get('rub_raise', 0.006), wall='trim_black', wall_col=0.6, col=0.9),
        'lower': dict(mat='trim_black', depth=-0.002, col=0.75, wall='trim_black'),
        'clad': dict(mat='trim_black', depth=0.0, col=0.75),
        'well': dict(mat='trim_black', depth=0.0, col=0.25, dec=C.get('dec_hidden', 0.15)),
        'under': dict(mat='trim_black', depth=0.0, col=0.3, dec=C.get('dec_hidden', 0.15)),
    }
    labels.update(C.get('extra_labels', {}))
    rules = list(C.get('extra_rules', [])) + [
        ('well', lambda fm: fm['well'] < 0.004),
        ('under', lambda fm: (fm['n'][:, 2] < -0.55) & (fm['c'][:, 2] < 0.40)),
    ]
    if open_win:
        rules.append(('open', lambda fm: (fm['open'] > 0) & (fm['dlo'] < 0) & (fm['bp'] > 0)))
    rules += [
        ('glass', lambda fm: (fm['ws'] < -0.04) | (fm['bl'] < -0.035) | ((fm['dlo'] < 0) & (fm['bp'] > 0))),
        ('frit', lambda fm: (fm['ws'] < 0) | (fm['bl'] < 0)),
        ('dlo_trim', lambda fm: fm['dlo'] < 0.018),
        ('lamp', lambda fm: fm['head'] < 0),
        ('lamp_bezel', lambda fm: fm['head'] < 0.008),
        ('corner', lambda fm: fm['corner'] < 0),
        ('grille', lambda fm: fm['grille'] < 0),
        ('grille_sur', lambda fm: fm['grille'] < 0.012),
        ('lowg', lambda fm: fm['lowg'] < 0),
        ('rev', lambda fm: fm['rev'] < 0),
        ('tail', lambda fm: fm['tail'] < -0.006),
        ('tail_bez', lambda fm: fm['tail'] < 0),
        ('tpanel', lambda fm: fm['tpanel'] < 0),
        ('rplate', lambda fm: fm['rplate'] < 0),
        ('handle', lambda fm: fm['handle'] < 0),
        ('marker_f', lambda fm: fm['mark_f'] < 0),
        ('marker_r', lambda fm: fm['mark_r'] < 0),
        ('gap', lambda fm: (np.abs(fm['fdoor']) < GAP) | (np.abs(fm['rdoor']) < GAP) | (np.abs(fm['hood']) < GAP)
                           | (np.abs(fm['lid']) < GAP) | (np.abs(fm['fuel']) < GAP)),
        ('rub', lambda fm: (fm['rub'] < 0) & (fm['clad'] > 0)),
        ('clad', lambda fm: (fm['clad'] < 0) & (fm['c'][:, 2] < 0.95)),
        ('lower', lambda fm: fm['lower'] < 0),
    ]

    def ao_col(V, N):
        z = V[:, 2]; s = V[:, 1]
        a = 0.60 + 0.40 * sstep(0.15, 0.62, z)
        for (sa, za_, R, xin) in wells:
            r = np.sqrt((s - sa) ** 2 + (z - za_) ** 2)
            a *= 1 - 0.32 * np.exp(-((r - R) / 0.05) ** 2) * (np.abs(V[:, 0]) > 0.5)
        a *= 0.85 + 0.15 * np.clip(N[:, 2] * 0.5 + 0.5, 0, 1)
        # cowl / base of the windscreen and backlight collect shadow
        a *= 1 - 0.25 * np.exp(-((B.ws_dist(np.abs(V[:, 0]), s, z)) / 0.05) ** 2) * (z < BELT + 0.1)
        return np.repeat(a[:, None], 3, 1)

    CB.log(C['name'], 'body field')
    V, F, N = CB.body_surface(B, C['BOUNDS'], C['res'], C['body_target'], C.get('max_edge', None), C.get('split_zmin', 0.3))
    cs = CB.run_cuts(B, V, F, N, cuts)
    parts = Parts()
    parts, lab = build_labelled(cs, labels, rules, 'paint', col_fn=ao_col, parts=parts, node='body')
    names = list(labels.keys())
    m = (lab == names.index('lamp'))
    Fm = cs.F[m]; used = np.unique(Fm); remap = -np.ones(len(cs.V), np.int64); remap[used] = np.arange(len(used))
    parts.add('body', cs.V[used] + cs.N[used] * 0.0005, remap[Fm], 'light_cover', N=cs.N[used])
    CB.log('body labelled', parts.tris('body'))
    surf = lambda pts, plane, sgn=1, off=0.0: D.surface_curve(f, pts, plane, sgn, offset=off)

    # headlamp internals: a horizontal reflector divider + bulb cup per lamp
    for sgn in (1, -1):
        zc = 0.5 * (hl[2] + hl[3])
        c = surf([(x, zc) for x in np.linspace(hl[0] + 0.03, hl[1] - 0.02, 6)], 'front', sgn, -0.022)
        if len(c) > 1: D.strip_along(parts, D.smooth_path(c, 20), 0.003, 'chrome', n_seg=6)
        for px in (hl[0] + 0.25 * (hl[1] - hl[0]), hl[0] + 0.7 * (hl[1] - hl[0])):
            h = surf([(px, zc)], 'front', sgn, -0.028)
            if len(h) == 0: continue
            Vl, Fl, _ = revolve([(-0.01, 0.022), (0.0, 0.022), (0.004, 0.016), (0.008, 0.008), (0.010, 0.0)], 16)
            u = np.array([0, 1.0, 0]); v = np.array([1.0, 0, 0]); w = np.array([0, 0, 1.0])
            Vw = h[0] + Vl[:, 0:1] * u + Vl[:, 1:2] * v + Vl[:, 2:3] * w
            Nn = vertex_normals(Vw, Fl)
            if np.mean(Nn @ u) < 0: Fl = Fl[:, ::-1]
            parts.add('body', Vw, Fl, 'chrome')
    # grille bars
    if C.get('grille_bars', 0):
        for z in np.linspace(gr[1] + 0.012, gr[2] - 0.012, C['grille_bars']):
            pts = []
            for x in np.linspace(-gr[0] + 0.02, gr[0] - 0.02, 9):
                h = surf([(abs(x), z)], 'front', np.sign(x) or 1, 0.0)
                if len(h): pts.append(h[0] - np.array([0, 0.018, 0]))
            if len(pts) > 1: D.strip_along(parts, np.array(pts), 0.0045, C.get('bar_mat', 'chrome'), n_seg=6)
    if C.get('grille_vbars', 0):
        for x in np.linspace(-gr[0] + 0.03, gr[0] - 0.03, C['grille_vbars']):
            pts = []
            for z in np.linspace(gr[1] + 0.006, gr[2] - 0.006, 4):
                h = surf([(abs(x), z)], 'front', np.sign(x) or 1, 0.0)
                if len(h): pts.append(h[0] - np.array([0, 0.02, 0]))
            if len(pts) > 1: D.strip_along(parts, np.array(pts), 0.004, C.get('bar_mat', 'chrome'), n_seg=6)
    # rear plate
    p = surf([(0.0, rp)], 'rear', 1, 0.0)
    if len(p):
        n = D.grad(f, p[0])[0]; n[2] = 0; n = normalize(n)
        D.plate_mesh(parts, p[0] - n * 0.012, n, (0, 0, 1.0))
    # mirrors
    mz = BELT + C.get('mirror_dz', 0.07)
    ms = a_s(mz) - a_off + C.get('mirror_ds', 0.02)
    for sgn in (1, -1):
        h = surf([(ms, mz)], 'side', sgn, -0.005)
        if len(h):
            b = h[0].copy(); b[0] = abs(b[0])
            D.mirror_parts(parts, f, tuple(b), sgn, scale=C.get('mirror_scale', 0.9), mats=C.get('mirror_mats', ('trim_black', 'trim_black', 'chrome')), lod=C.get('lod', 1.0))
    # wipers (parked on the cowl)
    (s0, z0), _ = P['ws_line']
    for (xa, xb) in [(-0.62, 0.0), (0.06, 0.58)]:
        pts = []
        for x in np.linspace(xa, xb, 9):
            t = (x - xa) / (xb - xa)
            hh = D.ray_hit(f, (x, s0 - 0.06 - 0.04 * t, 2.4), (0, 0, -1), tmax=2.0)
            if hh is not None: pts.append(hh + D.grad(f, hh)[0] * 0.012)
        if len(pts) > 1: D.strip_along(parts, np.array(pts), 0.005, 'trim_black', n_seg=6, col=(0.5, 0.5, 0.5))
    if C.get('rear_wiper'):
        pts = []
        for t in np.linspace(0, 1, 7):
            x = -0.05 + t * 0.45; z = C['rear_wiper'] + t * 0.02
            hh = surf([(abs(x), z)], 'rear', np.sign(x) or 1, 0.012)
            if len(hh): pts.append(hh[0])
        if len(pts) > 1: D.strip_along(parts, np.array(pts), 0.0055, 'trim_black', n_seg=6, col=(0.5, 0.5, 0.5))
    # antenna (fixed mast on the right front fender, period-typical)
    if C.get('antenna', True):
        ant_s = C.get('antenna_s', a_s(BELT) + 0.05)
        hh = D.ray_hit(f, (0.72, ant_s, 2.4), (0, 0, -1), tmax=2.5)
        if hh is not None:
            Vt, Ft = tube(np.array([hh - [0, 0, 0.01], hh + [0, -0.06, 0.72]]), 0.0025, n_seg=5)
            parts.add('body', Vt, Ft, 'chrome')
            Vt, Ft = tube(np.array([hh - [0, 0, 0.005], hh + [0, 0, 0.012]]), 0.009, n_seg=8)
            parts.add('body', Vt, Ft, 'trim_black')
    # exhaust tip
    ex = C.get('exhaust', (0.45, S_RA - 0.85, 0.24))
    if ex:
        hh = D.ray_hit(f, (ex[0], -3.5, ex[2] + 0.02), (0, 1, 0), tmax=3.0)
        se = (hh[1] + 0.02) if hh is not None else ex[1]
        Vt, Ft = tube(np.array([(ex[0], se + 0.25, ex[2]), (ex[0], se - 0.025, ex[2] - 0.008)]), 0.028, n_seg=12)
        parts.add('body', Vt, Ft, 'steel_exhaust' if False else 'trim_black', COL=np.c_[np.full((len(Vt), 3), 0.6), np.ones(len(Vt))])
    if C.get('roof_rails'):
        rx, r0, r1, rh = C['roof_rails']
        for sgn in (1, -1):
            rail = []
            for s_ in np.linspace(r0, r1, 22):
                hh = D.ray_hit(f, (sgn * rx, s_, 2.6), (0, 0, -1), tmax=1.5)
                if hh is not None: rail.append(hh + np.array([0, 0, rh]))
            rail = np.array(rail)
            if len(rail) > 1:
                Vr_, Fr_ = tube(rail, 0.013, n_seg=8)
                parts.add('body', Vr_, Fr_, 'trim_black', COL=np.c_[np.full((len(Vr_), 3), 0.9), np.ones(len(Vr_))])
                for k in (0, len(rail) // 2, len(rail) - 1):
                    bv, bf = box(rail[k] - np.array([0, 0, rh / 2]), (0.016, 0.045, rh / 2 + 0.004))
                    parts.add('body', bv, bf, 'trim_black', flat=True)
            if C.get('cross_bars') and sgn == 1:
                for s_ in C['cross_bars']:
                    hh = D.ray_hit(f, (0.0, s_, 2.6), (0, 0, -1), tmax=1.5)
                    if hh is None: continue
                    zc = hh[2] + rh + 0.012
                    Vr_, Fr_ = tube(np.array([(-rx, s_, zc), (rx, s_, zc)]), 0.011, n_seg=8)
                    parts.add('body', Vr_, Fr_, 'trim_black')
    for extra in C.get('extras', []):
        extra(parts, B, f, locals())
    # cabin
    IC = dict(C['interior'])
    if C.get('lod', 1.0) < 1.0:
        IC.setdefault('seat_target', 450); IC.setdefault('dash_target', 700); IC['shell_target'] = 900
    from collections import Counter
    _cnt = Counter()
    for _p in parts.nodes['body']: _cnt[_p['mat']] += len(_p['F'])
    CB.log('body tris by material before cabin', dict(_cnt))
    IN.add_interior(parts, B, IC)
    CB.log('details done', parts.tris('body'))
    xw = C['X_W']
    axles = [('FL', S_FA, xw), ('FR', S_FA, xw), ('RL', S_RA, xw), ('RR', S_RA, xw)]
    cent = W9.add_wheels(parts, axles, RT, C['R_BEAD'], C['TYRE_W'], C['wheel'], tyre_seg=C.get('tyre_seg', 48),
                         target=C.get('wheel_target', 3000))
    # materials
    mats = CB.base_materials(C['paint'], C.get('rim_color', (0.62, 0.63, 0.65)), rim_rough=C.get('rim_rough', 0.35))
    for k in ('brake', 'caliper', 'light_rear_led'):
        mats.pop(k, None)
    mats['paint'].update(metallic=C.get('paint_metal', 0.35), roughness=C.get('paint_rough', 0.34))
    mats['glass'].update(color=(0.018, 0.02, 0.022), roughness=0.03, alpha=0.84)
    mats['light_front'] = dict(color=(0.72, 0.73, 0.74), metallic=0.6, roughness=0.22, vcol=True)          # lights off
    mats['light_rear'] = dict(color=(0.30, 0.012, 0.010), metallic=0.0, roughness=0.10, vcol=True)
    mats['light_marker'] = dict(color=(0.55, 0.20, 0.02), metallic=0.0, roughness=0.12)
    mats['light_cover']['alpha'] = 0.16
    mats['interior'] = dict(color=C.get('interior_color', (0.05, 0.048, 0.045)), metallic=0.0, roughness=0.8, vcol=True)
    mats['plate']['tex_arr'] = blank_plate()
    used_mats = {p['mat'] for L in parts.nodes.values() for p in L}
    mats = {k: v for k, v in mats.items() if k in used_mats}
    emp = {}
    if open_win:
        emp = hero_anchors(B, f, C, zb, s_b, a_s, a_off)
    raw = out[:-4] + '_raw.glb' if C.get('pack', True) else out
    CB.export(parts, mats, raw, cent, empties=emp, root=C['name'])
    if C.get('pack', True):
        pack(raw, out)
    return parts

GLTFPACK = os.environ.get('GLTFPACK', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/npm/node_modules/.bin/gltfpack')

def pack(raw, out):
    """meshopt-compress like the desert assets (gltfpack -cc), keeping node + material names; raw file removed."""
    import subprocess, shutil
    exe = GLTFPACK if os.path.exists(GLTFPACK) else shutil.which('gltfpack')
    if not exe:
        os.replace(raw, out); CB.log('gltfpack not found, wrote uncompressed', out); return
    subprocess.run([exe, '-i', raw, '-o', out, '-cc', '-kn', '-km'], check=True, capture_output=True)
    os.remove(raw)
    CB.log('packed', out, os.path.getsize(out))

def hero_anchors(B, f, C, zb, s_b, a_s, a_off):
    """bucket_anchor: on top of the driver's door inner ledge, mid-window. ledge_drop: ground just outside the door."""
    s_front = a_s(zb + 0.01) - a_off
    s_mid = 0.5 * (s_front + s_b(zb))
    h = D.ray_hit(f, (-1.6, s_mid, zb - 0.004), (1, 0, 0), tmax=1.6)
    n = D.grad(f, h)[0]
    nh = normalize(np.array([n[0], n[1], 0.0]))
    top = h - nh * C.get('ledge', 0.065) * 0.5
    top[2] = zb + 0.002
    drop = np.array([h[0] - 0.32, s_mid - 0.05, 0.0])
    CB.log('bucket_anchor (model x,s,z)', np.round(top, 3), 'ledge_drop', np.round(drop, 3))
    return {'bucket_anchor': top, 'ledge_drop': drop}

def blank_plate(w=512, h=256):
    """Generic US-size plate with no characters: embossed border, mounting holes, a little grime."""
    y, x = np.mgrid[0:h, 0:w] / np.array([h, w])[:, None, None]
    a = np.ones((h, w, 3)) * np.array([0.86, 0.87, 0.88])
    border = ((x < 0.025) | (x > 0.975) | (y < 0.05) | (y > 0.95))
    a[border] = [0.18, 0.22, 0.36]
    band = (y > 0.08) & (y < 0.17) & (x > 0.2) & (x < 0.8)
    a[band] = [0.62, 0.30, 0.25]       # plain coloured header band (no text)
    for hx in (0.2, 0.8):
        for hy in (0.14, 0.86):
            m = ((x - hx) * 2) ** 2 + (y - hy) ** 2 < 0.0012
            a[m] = 0.45
    g = (y ** 3 * 0.25)[..., None]
    a = a * (1 - g) + g * np.array([0.5, 0.42, 0.32])
    return a
