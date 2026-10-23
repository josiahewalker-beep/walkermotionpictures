"""Hero: silver 1994-98 Saab 9000 Aero, 5-door hatchback (CS/CSE body) with the Aero kit and 3-spoke "Super Aero"
16" alloys. Generic: no badges, no lettering, blank plate.
Real car: L 4761, W 1778, H 1415, wb 2672, track 1534/1504 mm, 205/55 R16.
Driver's front window rolled down (deep ledge with felt strips); empties `bucket_anchor` and `ledge_drop`.
python3 saab9000.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90
import details as D
from carlib import sd_round_box, smin, normalize, tube, box
from wheels_saab import super_aero_mesh

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_hero.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0072
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 27000

L2 = 2.38                                # half length
S_FA, RT = 1.455, 0.316                  # front overhang 0.925
S_RA = S_FA - 2.672                      # rear overhang 1.164
BELT = 0.92
P = dict(
    half_w=0.889,
    curves=dict(
        # plan: blunt, rounded nose and tail; slab sides
        W=[(2.38, 0.70), (2.32, 0.80), (2.20, 0.856), (1.9, 0.880), (1.2, 0.889), (0.0, 0.889), (-1.4, 0.889), (-2.0, 0.880),
           (-2.24, 0.858), (-2.33, 0.82), (-2.38, 0.74)],
        # top of the lower body: low hood falling to a short nose, level belt, rear deck up at the hatch
        Ztop=[(2.38, 0.635), (2.32, 0.685), (2.22, 0.722), (2.0, 0.762), (1.7, 0.808), (1.4, 0.855), (1.15, 0.88), (0.9, 0.90),
              (0.4, 0.915), (0.0, 0.92), (-0.8, 0.93), (-1.3, 0.95), (-1.7, 0.99), (-2.0, 1.025), (-2.2, 1.035),
              (-2.32, 1.02), (-2.38, 0.98)],
        fender=[(2.38, 0.0), (2.0, 0.006), (1.3, 0.008), (0.9, 0.0), (-2.38, 0.0)],
        # Aero kit: deep front spoiler, low skirts, deep rear valance
        Zbot=[(2.38, 0.24), (2.32, 0.19), (2.15, 0.175), (0.0, 0.178), (-2.0, 0.185), (-2.25, 0.22), (-2.38, 0.27)],
        # front profile s(z): spoiler lip, bumper face, raked lamp/grille band tucked under the hood edge
        Lf=[(0.17, 2.29), (0.22, 2.345), (0.30, 2.37), (0.45, 2.38), (0.54, 2.375), (0.58, 2.355), (0.63, 2.33),
            (0.68, 2.29), (0.715, 2.22), (0.75, 2.05)],
        # rear profile s(z): valance, bumper, near-vertical tail panel, deck edge
        Lr=[(0.22, -2.30), (0.30, -2.365), (0.45, -2.385), (0.56, -2.38), (0.60, -2.345), (0.75, -2.335), (0.92, -2.325),
            (1.00, -2.31), (1.04, -2.26), (1.07, -2.10)],
        crease_z=[(2.4, 0.84), (0.0, 0.875), (-2.4, 0.90)],
        crease2_z=[(2.4, 0.45), (-2.4, 0.45)],
        Wg=[(1.25, 0.70), (0.9, 0.79), (0.4, 0.815), (-0.6, 0.815), (-1.3, 0.80), (-1.8, 0.76), (-2.2, 0.68)],
        Zroof=[(1.05, 1.0), (0.7, 1.24), (0.40, 1.355), (0.15, 1.40), (-0.2, 1.415), (-0.6, 1.41), (-1.0, 1.395), (-1.25, 1.37),
               (-1.6, 1.25), (-2.1, 1.06)],
    ),
    tuck=0.02, tuck_z0=0.18, tuck_z1=0.40,
    crease_k=0.025, crease_sharp=0.012, shoulder_k=0.20, crease2_k=0.02,
    flares=[(S_FA, RT, 0.37, 0.003, 0.08), (S_RA, RT, 0.37, 0.003, 0.08)],
    # Aero side skirt: a soft bulge under the doors between the arches
    haunches=[(0.0, 0.62, 0.235, 0.045, 0.012)],
    fender_x0=0.45, fender_x1=0.78, hood_crown=0.03,
    nose_corner=0.30, nose_pow=2.4, tail_corner=0.14, tail_pow=2.8,
    k_shoulder=0.07, k_nose=0.06, k_tail=0.05, k_bottom=0.04, normal_blur=0.022,
    belt=BELT, tumble=0.20, tumble2=0.30,
    ws_line=((1.12, 0.905), (0.24, 1.39)), ws_wrap=0.15, ws_bulge=0.01,
    bl_line=((-2.10, 1.045), (-1.24, 1.375)), bl_wrap=0.12,
    roof_crown=0.035, k_roof=0.07, k_ws=0.05, k_bl=0.05, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.012, 0.365, 0.48), (S_RA, RT + 0.012, 0.365, 0.48)],
)
HL = (0.30, 0.79, 0.588, 0.680)          # headlamps: long, low, under the hood edge
B_S = -0.17                              # B-pillar at the belt

# ---------------------------------------------------------------- Aero fog lamps in the front spoiler (extra cut)
_fog_sdf = car90.MaskSDF(lambda X, Z: (X > 0.50) & (X < 0.70) & (Z > 0.285) & (Z < 0.345), (0.0, 0.0), (1.2, 1.6), res=0.002, rnd=0.012)
def fn_fog(V, N):
    dom = (V[:, 1] > S_FA + 0.55) & (N[:, 1] > -0.1)
    return np.where(dom, _fog_sdf(np.abs(V[:, 0]), V[:, 2]), 1.0)

# ---------------------------------------------------------------- side view of the wraparound hatch glass (extra cut)
# On the 9000 CS the hatch glass is visible from the side: a long dark band from a slim body-colour C-pillar back to the
# spoiler, above a near-level line at ~1.06 m.  Glass + black frit on the side faces of the rear greenhouse.
from body import Body as _Body
_B = _Body(P)
_QZ0 = 1.065
_qg_sdf = car90.MaskSDF(lambda S, Z: (S < -1.20 + 0.25 * (Z - _QZ0)) & (S > -2.40) & (Z > _QZ0) & (Z < _B.c['Zroof'](S) - 0.05),
                        (-3.0, 0.0), (3.0, 2.2), rnd=0.03)
def fn_qg(V, N):
    dom = (np.abs(V[:, 0]) > 0.45) & (np.abs(N[:, 0]) > 0.25) & (V[:, 2] > 1.0) & (V[:, 1] < -1.0)
    return np.where(dom, _qg_sdf(V[:, 1], V[:, 2]), 1.0)

# ---------------------------------------------------------------- extras
def ledge_felt(parts, B, f, L):
    """Felt/rubber window strips on the rolled-down driver's door: one along the outer lip, one along the inner lip."""
    C, zb, s_b, a_s, a_off = L['C'], L['zb'], L['s_b'], L['a_s'], L['a_off']
    s0 = s_b(zb) + 0.03; s1 = a_s(zb + 0.01) - a_off - 0.03
    outer, inner = [], []
    for s in np.linspace(s0, s1, 14):
        h = D.ray_hit(f, (-1.6, s, zb - 0.006), (1, 0, 0), tmax=1.6)
        if h is None: continue
        outer.append((h[0] + 0.002, s, zb + 0.004))
        inner.append((h[0] + C['ledge'] - 0.004, s, zb + 0.006))
    for pts, r in ((outer, 0.0055), (inner, 0.0065)):
        if len(pts) > 1:
            D.strip_along(parts, np.array(pts), r, 'trim_black', n_seg=8, col=(0.55, 0.55, 0.55))

def hatch_spoiler(parts, B, f, L):
    """Aero hatch-lid spoiler: a dark blade across the tail, standing just proud of the deck, rear edge kicked up."""
    sc = -2.20
    h = D.ray_hit(f, (0.0, sc, 2.0), (0, 0, -1), tmax=1.5)
    zd = h[2] if h is not None else 1.03
    ang = np.deg2rad(7.0)
    zc = zd + 0.026
    def fld(x, s, z):
        ds = s - sc; dz = z - zc
        u = ds * np.cos(ang) + dz * np.sin(ang); w = -ds * np.sin(ang) + dz * np.cos(ang)
        # chord tapers toward the tips
        P_ = np.stack([x, u, w], -1)
        blade = sd_round_box(P_, (0, -0.01, 0), (0.64, 0.12, 0.019), 0.016)
        # two pedestals onto the deck
        legs = None
        for xl in (-0.42, 0.42):
            dl = sd_round_box(np.stack([x, s, z], -1), (xl, sc + 0.02, zd - 0.005), (0.05, 0.06, 0.03), 0.012)
            legs = dl if legs is None else np.minimum(legs, dl)
        return smin(blade, legs, 0.01)
    V, F, N = D.mc_small(fld, (-0.70, sc - 0.20, zd - 0.05), (0.70, sc + 0.18, zd + 0.11), 0.006, 3500)
    parts.add('body', V, F, 'trim_black', N=N, COL=np.c_[np.full((len(V), 3), 0.85), np.ones(len(V))])

def stop_lamp(parts, B, f, L):
    """High-mounted stop lamp: a slim red pod on the roof's trailing edge over the hatch glass."""
    h = D.ray_hit(f, (0.0, -1.16, 2.0), (0, 0, -1), tmax=1.5)
    if h is None: return
    def fld(x, s, z):
        return sd_round_box(np.stack([x, s, z], -1), (0, h[1] - 0.005, h[2] + 0.004), (0.15, 0.03, 0.016), 0.01)
    V, F, N = D.mc_small(fld, (-0.18, h[1] - 0.06, h[2] - 0.03), (0.18, h[1] + 0.05, h[2] + 0.04), 0.004, 500)
    rear = N[F].mean(1)[:, 1] < -0.5
    parts.add('body', V, F[rear], 'light_rear', N=N)
    parts.add('body', V, F[~rear], 'trim_black', N=N)

C = dict(
    name='car_hero', P=P, BOUNDS=((-0.93, -L2 - 0.03, 0.13), (0.93, L2 + 0.03, 1.43)), res=RES, body_target=TARGET,
    clad_cut=False, max_edge=0.12, S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.2032, TYRE_W=0.205, X_W=0.767,
    paint=(0.462, 0.466, 0.472), paint_metal=0.75, paint_rough=0.25,      # Saab silver, warm-ish, linear ~0.5
    interior_color=(0.045, 0.043, 0.041),
    # side glass: front door + rear door only; body-colour C-pillar between the rear door glass and the hatch glass
    dlo_rear=lambda Z, c_s: -1.06 + 0.12 * (Z - BELT), top_off=0.05, a_off=0.07, dlo_round=0.03,
    pillars=[(B_S, 0.034, 0.03)], b_s=B_S, b_slant=0.03, fd0=0.955,
    rd1=lambda Z, c_s: np.where(Z > BELT - 0.03, -1.085 + 0.12 * (Z - BELT), -1.10), sill=0.285,
    ws_dom=0.2, ws_ztop=1.345, ws_side=0.06,
    bl_dom=-1.15, bl_zlo=1.075, bl_ztop=1.335, bl_side=0.035,
    hood=(1.13, 0.80, HL[3] + 0.012), lid=(-1.26, 0.69, 0.575),
    head=HL, head_rnd=0.03, corner=(HL[1] + 0.012, 2.0, HL[2] + 0.004, HL[3] - 0.004), corner_s=0.62,
    grille=(0.235, 0.598, 0.672), grille_rnd=0.02, grille_bars=2, bar_mat='trim_black', lower_intake=(0.47, 0.255, 0.385),
    tail=(0.40, 0.775, 0.925), tail_s=S_RA - 0.62, reverse=(0.42, 0.53, 0.785, 0.835), rplate=0.665,
    handles=[0.10, -0.90], handle_z=BELT - 0.095,
    markers=((S_FA - 0.42, 0.62), (S_RA - 0.93, 0.42)),             # amber repeater behind the front arch; red US-spec reflector low on the rear bumper
    fuel=(S_RA - 0.40, BELT - 0.14),                               # right rear quarter (passenger side)
    rub=(lambda s: np.full_like(s, 0.50), 0.019), rub_raise=0.007,
    mirror_mats=('paint', 'trim_black', 'chrome'), mirror_dz=0.065, mirror_ds=0.03, mirror_scale=0.80,
    antenna=False, exhaust=(-0.46, S_RA - 0.9, 0.24),
    extra_cuts=[('fog', fn_fog, [0.0]), ('qg', fn_qg, [0.0, 0.018])],
    extra_labels={'fog': dict(mat='light_front', depth=0.012, wall='trim_black', wall_col=0.4, col=0.75)},
    # fog lamps; and keep the whole upper wheel-well lining black (faces just past the well cut whose normals face into the arch)
    extra_rules=[('fog', lambda fm: fm['fog'] < 0),
                 ('glass', lambda fm: fm['qg'] < 0), ('dlo_trim', lambda fm: fm['qg'] < 0.018),
                 ('well', lambda fm: (fm['well'] < 0.03) & (np.abs(fm['n'][:, 0]) < 0.7) & (fm['c'][:, 2] < 0.75))],
    extras=[ledge_felt, hatch_spoiler, stop_lamp],
    open_window=True, ledge=0.078,
    interior=dict(seat_s=0.02, seat_x=0.37, floor=0.30, dash_s=0.86, dash_z=0.87, dash_w=0.72, wheel_s=0.50, hip_z=0.49,
                  seat_h=0.62, rear_seats=True, rear_s=-0.92, cabin_bounds=((-0.80, -1.95, 0.30), (0.80, 1.05, 1.37)),
                  glass_band=(BELT + 0.02, 1.32)),
    wheel=dict(type='custom', mesh_fn=lambda target: super_aero_mesh(target, n_seg=80), a_face=0.074, r_cover=0.196, dust=0.12),
    wheel_target=3900, tyre_seg=52, rim_color=(0.70, 0.71, 0.72), rim_rough=0.22,
)

if __name__ == '__main__':
    car90.build(C, OUT)
