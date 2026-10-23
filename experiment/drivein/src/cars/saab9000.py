"""Hero: silver 1994-98 Saab 9000 Aero, 5-door hatchback (CS body) with the Aero kit and 3-spoke "Super Aero" 16" alloys.
Invented make "Sob": one chrome "Sob" wordmark on the hatch (upper left, above the lamp band); otherwise blank parts only
(plain bonnet cap, blank front plate on the spoiler, plain wheel caps, blank rear plate). Real car: L 4761, W 1778,
H 1415, wb 2672, track 1534/1504 mm, 205/55 R16.

v2 (2026-10-22): the side silhouette, beltline, side glass (DLO), pillars, shut lines, arches, rub strips and nose/tail
profiles are traced from the director's straight driver-side photo (see saab9000_trace.py for the camera and the
pixel data) and fed to the shared implicit-body generator (car90.py) as exact curves and masks. Rear lamps, spoiler and
brake pod: saab9000_rear.py; wheel: wheels_saab.py; badge + front blanks: saab9000_badges.py.
Driver's front window rolled down (deep ledge with felt strips); empties `bucket_anchor` and `ledge_drop`.
python3 saab9000.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from matplotlib.path import Path
import car90
import details as D
from body import Body
from carlib import sd_round_box, smin, smax
from wheels_saab import super_aero_mesh
import saab9000_trace as TR
import saab9000_rear as REAR
import saab9000_badges as BADGE

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_hero.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0068
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 26000

L2 = 2.3805
S_FA, S_RA, RT = TR.S_FA, TR.S_RA, 0.316
TRC = TR.traced()
BELT = 0.905
DLO_BOT = 0.028                       # BELT + DLO_BOT = 0.933: driver's window sill (ledge) at mid-window

def pts(name):
    return TRC[name]

# ------------------------------------------------------------------ traced side glass and door outlines (s, z)
DLO_F = pts('dlo_f'); DLO_R = pts('dlo_r')
_dlo_paths = [Path(DLO_F), Path(DLO_R)]
def dlo_mask(S, Z):
    P = np.c_[S.ravel(), Z.ravel()]
    m = np.zeros(len(P), bool)
    for p in _dlo_paths: m |= p.contains_points(P)
    return m.reshape(S.shape)
# front-door glass front edge (along the A-pillar) and top, as functions
_fe = DLO_F[[0, 1]]                      # (s, z) bottom-front -> top-front
def dlo_front_s(Z):
    return np.interp(Z, _fe[:, 1], _fe[:, 0])
_top = np.array([DLO_F[1], DLO_F[2], DLO_R[1], DLO_R[2]])
def dlo_top_z(S):
    o = np.argsort(_top[:, 0]); return np.interp(S, _top[o, 0], _top[o, 1])
# B line: shut below the belt, centre of the body-colour pillar above it
_b_lo = pts('shut_b')                    # (s, z) top, bottom
_b_hi = np.array([[0.5 * (DLO_F[3, 0] + DLO_R[0, 0]), 0.95], [0.5 * (DLO_F[2, 0] + DLO_R[1, 0]), 1.342]])
def b_line(Z):
    lo = np.interp(Z, _b_lo[::-1, 1], _b_lo[::-1, 0])
    hi = np.interp(Z, _b_hi[:, 1], _b_hi[:, 0])
    return np.where(Z < 0.945, lo, hi)
_sf = pts('shut_f')
_sr = pts('shut_r'); _sro = np.argsort(_sr[:, 1])
SILL = 0.322
def fdoor_mask(S, Z):
    front = np.where(Z < 0.93, np.interp(Z, _sf[::-1, 1], _sf[::-1, 0]), dlo_front_s(Z) + 0.035)
    return (Z > SILL) & (Z < dlo_top_z(S) + 0.034) & (S < front) & (S > b_line(Z))
def rdoor_mask(S, Z):
    rear = np.interp(Z, _sr[_sro, 1], _sr[_sro, 0])
    out_arch = ((S - S_RA) ** 2 + (Z - RT) ** 2) > (0.35 + 0.045) ** 2
    return (Z > SILL) & (Z < dlo_top_z(S) + 0.034) & (S < b_line(Z)) & (S > rear) & out_arch

# ------------------------------------------------------------------ body curves from the trace
def _hood_ztop():
    h = pts('hood')
    out = [(L2, 0.62), (2.31, 0.66), (2.235, 0.700)]
    for s, z in h[:-2]:
        out.append((s, z + 0.017))                  # traced at the fender edge; centre is crowned
    return out
ZTOP = _hood_ztop() + [(0.99, 0.952), (0.86, 0.935), (0.749, 0.911), (0.4, 0.918), (0.0, 0.928), (-0.146, 0.938),
                       (-0.28, 0.946), (-0.6, 0.955), (-0.9, 0.962), (-1.14, 0.968), (-1.4, 0.99), (-1.7, 1.025),
                       (-1.95, 1.042), (-2.15, 1.046), (-2.25, 1.040), (-2.3, 1.02), (-L2, 0.98)]
_roof = pts('roof')
ZROOF = [(0.55, 1.25), (0.40, 1.335)] + [(s, z + 0.017) for s, z in _roof] + [(-1.25, 1.36), (-1.6, 1.21), (-2.0, 1.07)]
_nose = pts('nose')
LF = [(0.17, 2.10), (0.20, 2.205), (0.228, 2.273), (0.324, 2.322), (0.371, 2.347), (0.42, 2.372), (0.455, 2.3805),
      (0.527, 2.3805), (0.540, 2.33), (0.551, 2.267), (0.659, 2.258), (0.695, 2.219), (0.73, 2.10)]
# rear (v2.1): bumper face below the rub strip shortened to match 10 (valance turns under from z ~0.34), hatch face leans
# forward ~5 cm from the bumper shelf to the deck
LR = [(0.27, -2.06), (0.300, -2.215), (0.330, -2.318), (0.352, -2.355), (0.40, -2.374), (0.47, -2.3805),
      (0.592, -2.3805), (0.603, -2.33), (0.615, -2.284), (0.82, -2.266), (1.0, -2.240), (1.046, -2.228), (1.08, -2.17)]
ZBOT = [(L2, 0.26), (2.30, 0.215), (2.16, 0.199), (1.82, 0.195), (1.55, 0.205), (0.85, 0.224), (-0.93, 0.228),
        (-1.62, 0.262), (-2.05, 0.272), (-2.20, 0.295), (-2.32, 0.335), (-L2, 0.36)]
WS_WRAP, BL_WRAP = 0.13, 0.10
_a = pts('ascreen')
_ws_dir = (_a[5] - _a[0]) / np.linalg.norm(_a[5] - _a[0])
_ws0 = _a[0] + np.array([WS_WRAP, 0]) + _ws_dir * (0.92 - _a[0][1]) / _ws_dir[1]
_ws1 = _a[0] + np.array([WS_WRAP, 0]) + _ws_dir * (1.40 - _a[0][1]) / _ws_dir[1]
_h = pts('hatch')
_bl_dir = (_h[0] - _h[5]) / np.linalg.norm(_h[0] - _h[5])
_bl0 = _h[5] - np.array([0.087, 0]) + _bl_dir * (1.05 - _h[5][1]) / _bl_dir[1]
_bl1 = _h[5] - np.array([0.087, 0]) + _bl_dir * (1.42 - _h[5][1]) / _bl_dir[1]

P = dict(
    half_w=0.889,
    curves=dict(
        W=[(2.3805, 0.70), (2.32, 0.80), (2.20, 0.858), (1.9, 0.880), (1.2, 0.889), (0.0, 0.889), (-1.4, 0.889), (-2.0, 0.882),
           (-2.24, 0.862), (-2.33, 0.83), (-2.3805, 0.76)],
        Ztop=ZTOP,
        fender=[(L2, 0.0), (-L2, 0.0)],
        Zbot=ZBOT, Lf=LF, Lr=LR,
        crease_z=[(2.4, 0.83), (0.0, 0.87), (-2.4, 0.93)],
        crease2_z=[(2.4, 0.45), (-2.4, 0.46)],
        Wg=[(1.25, 0.74), (0.85, 0.815), (0.4, 0.84), (-0.6, 0.84), (-1.2, 0.83), (-1.8, 0.79), (-2.25, 0.71)],
        Zroof=ZROOF,
    ),
    tuck=0.022, tuck_z0=0.20, tuck_z1=0.40,
    crease_k=0.018, crease_sharp=0.012, shoulder_k=0.16, crease2_k=0.016,
    flares=[(S_FA, RT, 0.375, 0.003, 0.07), (S_RA, RT, 0.36, 0.003, 0.07)],
    haunches=[(-0.05, 0.62, 0.25, 0.045, 0.012)],
    fender_x0=0.45, fender_x1=0.78, hood_crown=0.03,
    nose_corner=0.24, nose_pow=2.6, tail_corner=0.13, tail_pow=2.3,
    k_shoulder=0.06, k_nose=0.022, k_tail=0.03, k_bottom=0.035, normal_blur=0.02,
    belt=BELT, tumble=0.20, tumble2=0.30,
    ws_line=(tuple(_ws0), tuple(_ws1)), ws_wrap=WS_WRAP, ws_bulge=0.008,
    bl_line=(tuple(_bl0), tuple(_bl1)), bl_wrap=BL_WRAP,
    roof_crown=0.035, k_roof=0.06, k_ws=0.045, k_bl=0.045, k_belt=0.025, k_well=0.012,
    wells=[(S_FA, RT, 0.365, 0.48), (S_RA, RT, 0.350, 0.48)],
)
_B = Body(P)
REAR.TAIL_PROFILE = _B.c['Lr']

HL = (0.335, 0.665, 0.566, 0.664)      # slim rectangular headlamps under the bonnet edge
B_S = float(_b_hi[0, 0])

def fn_fog_mk():
    sdf = car90.MaskSDF(lambda X, Z: (X > 0.585) & (X < 0.715) & (Z > 0.282) & (Z < 0.338), (0.0, 0.0), (1.2, 1.6), res=0.002, rnd=0.024)
    def fn(V, N):
        dom = (V[:, 1] > S_FA + 0.6) & (N[:, 1] > -0.1)
        return np.where(dom, sdf(np.abs(V[:, 0]), V[:, 2]), 1.0)
    return fn
fn_fog = fn_fog_mk()

def lid_fn(V, N):
    """Hatch: from the roof's rear edge down the glass, then between the outer lamps to the bumper top."""
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    w = np.where(z < 1.035, REAR.LAMP_X0 - 0.004, np.maximum(_B.gh_width(s, z) - 0.022, REAR.LAMP_X0 - 0.004))
    d = smax(smax(ax - w, 0.608 - z, 0.015), s - (-1.075), 0.03)
    return np.where((s < -0.8) & (z > 0.45), d, 1.0)

# ------------------------------------------------------------------ extras
def ledge_felt(parts, B, f, L):
    """Felt/rubber window strips on the rolled-down driver's door: one along the outer lip, one along the inner lip."""
    C, zb, s_b = L['C'], L['zb'], L['s_b']
    s0 = s_b(zb) + 0.03; s1 = dlo_front_s(zb + 0.01) - 0.03
    outer, inner = [], []
    for s in np.linspace(s0, s1, 14):
        h = D.ray_hit(f, (-1.6, s, zb - 0.006), (1, 0, 0), tmax=1.6)
        if h is None: continue
        outer.append((h[0] + 0.002, s, zb + 0.004))
        inner.append((h[0] + C['ledge'] - 0.004, s, zb + 0.006))
    for pts_, r in ((outer, 0.0055), (inner, 0.0065)):
        if len(pts_) > 1:
            D.strip_along(parts, np.array(pts_), r, 'trim_black', n_seg=8, col=(0.55, 0.55, 0.55))

def handle_bars(parts, B, f, L):
    """Horizontal pull bars set into the black handle recesses."""
    for (sc, zc) in HANDLES:
        for sgn in (-1, 1):
            h = D.ray_hit(f, (sgn * 1.6, sc, zc), (-sgn, 0, 0), tmax=1.6)
            if h is None: continue
            x0 = h[0] + sgn * 0.004
            def fld(x, s, z, x0=x0):
                return sd_round_box(np.stack([x, s, z], -1), (x0, sc, zc + 0.002), (0.012, 0.066, 0.011), 0.008)
            V, F, N = D.mc_small(fld, (x0 - 0.03, sc - 0.09, zc - 0.03), (x0 + 0.03, sc + 0.09, zc + 0.03), 0.003, 500)
            parts.add('body', V, F, 'trim_black', N=N, COL=np.c_[np.full((len(V), 3), 0.75), np.ones(len(V))])

_hf, _hr = pts('handle_f'), pts('handle_r')
HANDLES = [(float(_hf[:, 0].mean()), float(_hf[:, 1].mean())), (float(_hr[:, 0].mean()), float(_hr[:, 1].mean()))]
_rf, _rd, _rr, _rb = pts('rub_fb'), pts('rub_door_f'), pts('rub_door_r'), pts('rub_rb')
# front bumper: the strip caps the bumper top (covers the shelf in front of the lamps, z up to 0.553)
RUB_S = [L2 + 0.1, 2.26, 2.12, 1.70, 1.45, 0.851, -0.915, -1.40, -1.63, -L2 - 0.1]
RUB_ZC = [0.5055, 0.5055, 0.4985, 0.501, 0.523, 0.5255, 0.5515, 0.558, 0.5605, 0.5625]
RUB_HW = [0.0485, 0.0485, 0.0375, 0.0375, 0.026, 0.0225, 0.0265, 0.028, 0.0285, 0.0285]
rub_zc = lambda s: np.interp(s, RUB_S[::-1], RUB_ZC[::-1])
rub_hw = lambda s: np.interp(s, RUB_S[::-1], RUB_HW[::-1])
_mk = pts('marker')

def liner_normals(V, N):
    """Arch liners shade as if facing outboard: seen edge-on they otherwise mirror the environment (Fresnel)."""
    n = np.zeros_like(N); n[:, 0] = np.where(V[:, 0] < 0, -1.0, 1.0)
    return n

def car90_plane_fn(inside, dom, rnd=0.012, mirror=True):
    """Same as car90's plane_fn (front/rear plane mask SDF over (|x| or x, z))."""
    sdf = car90.MaskSDF(inside, (0.0, 0.0) if mirror else (-1.2, 0.0), (1.2, 1.6), res=0.002, rnd=rnd)
    def fn(V, N):
        u = np.abs(V[:, 0]) if mirror else V[:, 0]
        return np.where(dom(V, N), sdf(u, V[:, 2]), car90.BIG)
    return fn

rear_cuts, rear_labels, rear_rules = REAR.cuts_labels_rules(
    lambda inside, dom, plane='front', rnd=0.012, mirror=True: car90_plane_fn(inside, dom, rnd, mirror), car90.MaskSDF)

C = dict(
    name='car_hero', P=P, BOUNDS=((-0.93, -L2 - 0.03, 0.15), (0.93, L2 + 0.03, 1.44)), res=RES, body_target=TARGET,
    clad_cut=False, max_edge=0.12, well_offsets=[0.004, 0.012], S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.2032, TYRE_W=0.205, X_W=0.767,
    paint=(0.462, 0.466, 0.472), paint_metal=0.75, paint_rough=0.25,
    interior_color=(0.045, 0.043, 0.041),
    dlo_mask=dlo_mask, dlo_bot=DLO_BOT, dlo_round=0.028, top_off=0.05, a_off=0.085,
    dlo_rear=lambda Z, c_s: np.full_like(Z, -1.2),
    pillars=[(float(pts('quarter_div')[:, 0].mean()), 0.010, 0.0)],      # thin black divider before the quarter light
    b_s=B_S, b_slant=float((_b_hi[1, 0] - _b_hi[0, 0]) / (_b_hi[1, 1] - _b_hi[0, 1])), fd0=0.84,
    rd1=lambda Z, c_s: np.full_like(Z, -1.2), sill=SILL,
    fdoor_mask=fdoor_mask, rdoor_mask=rdoor_mask,
    ws_dom=0.25, ws_ztop=1.36, ws_side=0.06,
    bl_dom=-1.0, bl_zlo=1.062, bl_ztop=1.36, bl_side=0.03,
    hood=(1.13, 0.80, HL[3] + 0.014), lid=(-1.075, 0.567, 0.608), lid_fn=lid_fn,
    head=HL, head_rnd=0.012, corner=(HL[1] + 0.012, 2.0, HL[2] + 0.002, HL[3] - 0.002), corner_s=0.70,
    grille=(0.322, 0.574, 0.657), grille_rnd=0.012, grille_bars=2, bar_mat='chrome', grille_sur_mat='chrome',
    lower_intake=(0.50, 0.255, 0.332),
    tail=(REAR.LAMP_X0, REAR.LAMP_Z0, REAR.LAMP_Z1), tail_s=-2.0, rplate=REAR.PLATE_Z,
    rear_lamp_fns=REAR.lamp_fns,
    handles=HANDLES, handle_size=(0.082, 0.024),
    markers=((float(_mk[:, 0].mean()), float(_mk[:, 1].mean())), (-2.31, 0.40)),
    fuel=(S_RA - 0.42, 0.86),                                       # passenger (-X glTF) rear quarter
    rub=(rub_zc, rub_hw), rub_raise=0.008, rub_nz=1.01,
    mirror_mats=('paint', 'trim_black', 'chrome'), mirror_at=(0.665, 0.945), mirror_scale=0.82,
    antenna=False, exhaust=(-0.70, S_RA - 0.9, 0.255),
    extra_cuts=[('fog', fn_fog, [0.0])] + rear_cuts,
    extra_labels=dict({'fog': dict(mat='light_front', depth=0.012, wall='trim_black', wall_col=0.4, col=0.75),
                       # arch liners: matte black (glossy trim_black caught the sky at grazing angles = pale crescents)
                       'well': dict(mat='interior', depth=0.0, col=0.35, dec=0.15, nfn=liner_normals)}, **rear_labels),
    extra_rules=rear_rules + [('fog', lambda fm: fm['fog'] < 0),
                              ('well', lambda fm: (fm['well'] < 0.012) & (fm['c'][:, 2] < 0.75))],
    extras=[ledge_felt, handle_bars, REAR.aero_spoiler, REAR.brake_pod, BADGE.hatch_wordmark, BADGE.front_blanks],
    open_window=True, ledge=0.078, ledge_z=BELT + DLO_BOT,
    interior=dict(seat_s=0.06, seat_x=0.37, floor=0.30, dash_s=0.84, dash_z=0.88, dash_w=0.72, wheel_s=0.50, hip_z=0.49,
                  seat_h=0.64, rear_seats=True, rear_s=-0.86, cabin_bounds=((-0.80, -1.95, 0.30), (0.80, 1.05, 1.38)),
                  glass_band=(BELT + 0.04, 1.33)),
    wheel=dict(type='custom', mesh_fn=lambda target: super_aero_mesh(target, n_seg=64), a_face=0.074, r_cover=0.196, dust=0.10),
    wheel_target=4600, tyre_seg=40, rim_color=(0.58, 0.59, 0.60), rim_rough=0.34, rim_metal=0.55,
)

if __name__ == '__main__':
    car90.build(C, OUT)
