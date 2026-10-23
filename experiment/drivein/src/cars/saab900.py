"""Cherry-red 1987 classic Saab 900 Turbo SPG three-door hatchback (the car of Hamaguchi's "Drive My Car", 2021).

v2 (2026-10-22): body built from exact curves and outlines (saab900_profile.py: published dimensions + the car's known
side-view geometry; no photos were available) fed to car90.py through the v2 hooks, the same method as the hero 9000:
  - deeply curved windscreen: a Body subclass gives the screen a plan wrap that shrinks with height, so the A-pillar
    stands ~30 deg from vertical in side view while the screen centre is raked (the 900's bubble screen);
  - tall glasshouse with a traced DLO (door glass, thin body-colour B-pillar, small quarter light, broad C-pillar);
  - clamshell bonnet: its own shut-line cut (side line rising from the lamp band to the A-pillar base, rear edge
    following the screen's wrap), dropping onto the slim slanted headlamp/grille band; long front overhang;
  - SPG kit: deep air dam with a wide lower intake, skirts with a sculpted line (cut groove + outward step), body-colour
    rear valance, lip spoiler at the base of the hatch glass (separate mesh), black bumpers + door rubbing strip as one
    exact band (deep at the ends, slim along the doors);
  - three-spoke 15" alloys (wheels_saab900.py, unchanged from v1).
No badges or lettering; blank plates. v1 is kept as assets/car_saab900_v1.glb.
python3 saab900.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from matplotlib.path import Path
import car90
import details as D
import wheels_saab900 as WS
from body import Body
from carlib import sstep, gauss, smax, sd_round_box
import saab900_profile as PR

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_saab900.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.011
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

L2, S_FA, S_RA, RT, BELT = PR.L2, PR.S_FA, PR.S_RA, PR.RT, PR.BELT
WELL_R = 0.370
ZA = RT + 0.008

class Saab900Body(Body):
    """Windscreen with a height-dependent plan wrap (the 900's deeply curved screen)."""
    def ws_dist(self, ax, s, z):
        (s0, z0), (s1, z1) = PR.WS_C0, PR.WS_C1
        k = (s1 - s0) / (z1 - z0)
        (za_, wa), (zb_, wb) = PR.WS_WRAP
        wrap = wa + (wb - wa) * np.clip((z - za_) / (zb_ - za_), -0.3, 1.3)
        s_surf = s0 + k * (z - z0) - wrap * (ax / 0.75) ** 2 + 0.015 * (1 - (ax / 0.75) ** 2)
        return (s - s_surf) / np.sqrt(1 + k * k)

def _ends(s):
    """1 on the bumpers (ahead of the front arch / behind the rear arch), 0 along the doors."""
    return np.clip(sstep(S_FA + 0.365, S_FA + 0.395, s) + sstep(-(S_RA - 0.365), -(S_RA - 0.395), -s), 0, 1)

def field_mod(d, x, s, z):
    """Bumpers proud of the body, SPG skirt step below the sculpted line."""
    ax = np.abs(x)
    b0, b1 = PR.BUMP
    band = sstep(b0 - 0.012, b0 + 0.004, z) * (1 - sstep(b1 - 0.004, b1 + 0.012, z))
    near_well = np.minimum(np.sqrt((s - S_FA) ** 2 + (z - ZA) ** 2), np.sqrt((s - S_RA) ** 2 + (z - ZA) ** 2))
    keep = sstep(WELL_R + 0.01, WELL_R + 0.05, near_well)
    sb = PR.STRIP[0]
    strip = sstep(sb - PR.STRIP[1] - 0.008, sb - PR.STRIP[1] + 0.002, z) * (1 - sstep(sb + PR.STRIP[1] - 0.002, sb + PR.STRIP[1] + 0.008, z))
    e = _ends(s)
    d = d - (band * 0.036 * e + strip * 0.007 * (1 - e)) * keep
    # skirts: the panel below the sculpted line stands ~1.6 cm proud, rolling under at the bottom
    sk = sstep(PR.SKIRT_Z + 0.006, PR.SKIRT_Z - 0.010, z) * sstep(0.17, 0.24, z)
    sk = sk * sstep(S_RA + 0.33, S_RA + 0.43, s) * (1 - sstep(S_FA - 0.43, S_FA - 0.33, s))
    return d - 0.016 * sk * (ax > 0.5)

P = dict(
    half_w=0.845,
    curves=dict(W=PR.W, Ztop=PR.ZTOP, fender=[(L2, 0.0), (2.0, 0.006), (1.0, 0.006), (0.6, 0.0), (-L2, 0.0)],
                Zbot=PR.ZBOT, Lf=PR.LF, Lr=PR.LR,
                crease_z=[(2.3, 0.70), (1.0, 0.76), (0.0, 0.79), (-2.3, 0.81)],
                crease2_z=[(2.3, 0.38), (-2.3, 0.38)],
                Wg=PR.WG, Zroof=PR.ZROOF),
    tuck=0.030, tuck_z0=0.17, tuck_z1=0.36,
    crease_k=0.035, crease_sharp=0.010, shoulder_k=0.20, crease2_k=0.012,
    flares=[(S_FA, RT, WELL_R + 0.02, 0.010, 0.07), (S_RA, RT, WELL_R + 0.02, 0.010, 0.07)],
    haunches=[], fender_x0=0.45, fender_x1=0.78, hood_crown=0.03,
    nose_corner=0.22, nose_pow=2.6, tail_corner=0.12, tail_pow=3.0,
    k_shoulder=0.055, k_nose=0.025, k_tail=0.035, k_bottom=0.04, normal_blur=0.02,
    belt=BELT, tumble=0.10, tumble2=0.12,
    ws_line=(PR.WS_C0, PR.WS_C1), ws_wrap=0.2, ws_bulge=0.015,
    bl_line=PR.BL_LINE, bl_wrap=PR.BL_WRAP,
    roof_crown=0.035, k_roof=0.055, k_ws=0.04, k_bl=0.045, k_belt=0.025, k_well=0.012,
    wells=[(S_FA, ZA, WELL_R, 0.48), (S_RA, ZA, WELL_R, 0.48)],
)
_B = Saab900Body(P)

# ------------------------------------------------------------------ side glass from the screen's actual side edge
def _a_side():
    zz = np.linspace(BELT, 1.40, 48); ss = np.linspace(-0.2, 1.2, 1401)
    out = []
    for z in zz:
        Sg = ss; d = _B.ws_dist(_B.gh_width(Sg, z), Sg, np.full_like(Sg, z))
        j = np.where(d > 0)[0]
        out.append(ss[j[0]] if len(j) else 1.2)
    return zz, np.array(out)
_AZ, _AS = _a_side()
A_OFF = 0.060                                      # thin A-pillar: glass edge 6 cm behind the screen's side edge
def dlo_front_s(Z):
    return np.interp(Z, _AZ, _AS) - A_OFF
_zg = np.linspace(BELT + 0.03, PR.DLO_TOP, 30)
DLO_F = np.r_[np.c_[dlo_front_s(_zg), _zg], [[PR.B_FRONT, PR.DLO_TOP], [PR.B_FRONT, BELT + 0.03]]]
_paths = [Path(DLO_F), Path(np.array(PR.QUARTER))]
def dlo_mask(S, Z):
    Pp = np.c_[S.ravel(), Z.ravel()]
    m = np.zeros(len(Pp), bool)
    for p in _paths: m |= p.contains_points(Pp)
    return m.reshape(S.shape)
def fdoor_mask(S, Z):
    front = np.where(Z < BELT - 0.02, PR.DOOR_FRONT, np.minimum(PR.DOOR_FRONT, dlo_front_s(Z) + 0.035))
    return (Z > PR.SILL) & (Z < PR.DLO_TOP + 0.034) & (S < front) & (S > PR.DOOR_REAR)

# ------------------------------------------------------------------ clamshell bonnet shut line
def hood_fn(V, N):
    """Bonnet = above a side line rising from the lamp band (z 0.69 at the nose) to the A-pillar base (z 0.80), and ahead
    of a rear edge that follows the screen's wrap (the clamshell takes the wing tops with it)."""
    x, s, z = V[:, 0], V[:, 1], V[:, 2]; ax = np.abs(x)
    zl = np.interp(s, [0.55, 2.30], [0.805, 0.688])
    sr = 0.745 - 0.235 * np.clip(ax / 0.80, 0, 1.1) ** 2
    d = smax(zl - z, sr - s, 0.03)
    return np.where((s > 0.25) & (z > 0.55), d, 1.0)

def skirt_fn(V, N):
    """The SPG skirt's sculpted line (a groove along its top edge) between the arches."""
    s, z = V[:, 1], V[:, 2]
    dom = (np.abs(V[:, 0]) > 0.5) & (np.abs(N[:, 0]) > 0.3) & (s > S_RA + 0.36) & (s < S_FA - 0.36)
    return np.where(dom, np.abs(z - PR.SKIRT_Z) - 0.004, 1.0)

# ------------------------------------------------------------------ extras
def lip_spoiler(parts, B, f, L):
    """SPG lip spoiler across the hatch at the base of the glass: a short, up-swept blade on the deck."""
    s_le = -2.035
    h = D.ray_hit(f, (0.0, s_le - 0.05, 2.4), (0, 0, -1), tmax=2.0)
    if h is None: return
    z0 = h[2]
    def fld(x, s, z):
        # chord from (s_le, z0) to (s_le - 0.13, z0 + 0.05), 2 cm thick, rounded; ends follow the deck's plan corners
        t = np.clip((s_le - s) / 0.13, 0, 1)
        zc = z0 + 0.012 + 0.038 * t ** 1.4
        d = np.maximum(np.abs(z - zc) - (0.011 - 0.004 * t), np.maximum(s - s_le, (s_le - 0.13) - s))
        return np.maximum(d, np.abs(x) - 0.60) - 0.002
    V, F, N = D.mc_small(fld, (-0.64, s_le - 0.16, z0 - 0.02), (0.64, s_le + 0.02, z0 + 0.08), 0.006, 900)
    parts.add('body', V, F, 'paint', N=N, COL=np.c_[np.full((len(V), 3), 0.9), np.ones(len(V))])

def sunroof(parts, B, f, L):
    """Steel tilt/slide sunroof (the film car has one): thin dark shut line on the roof."""
    s0, s1, xh = -0.40, 0.12, 0.38
    path = []
    for t in np.linspace(0, 1, 40):
        per = t * 4
        if per < 1: x, s = -xh + 2 * xh * per, s1
        elif per < 2: x, s = xh, s1 - (s1 - s0) * (per - 1)
        elif per < 3: x, s = xh - 2 * xh * (per - 2), s0
        else: x, s = -xh, s0 + (s1 - s0) * (per - 3)
        h = D.ray_hit(f, (x, s, 2.4), (0, 0, -1), tmax=1.5)
        if h is not None: path.append(h + np.array([0, 0, 0.001]))
    if len(path) > 4:
        D.strip_along(parts, np.array(path + [path[0]]), 0.004, 'trim_black', n_seg=4, col=(0.3, 0.3, 0.3))

HL = (0.345, 0.735, 0.566, 0.676)        # slim headlamps in the slanted band, under the bonnet edge
C = dict(
    lod=0.4, name='car_saab900', P=P, body_cls=Saab900Body, field_mod=field_mod,
    BOUNDS=((-0.90, -L2 - 0.03, 0.12), (0.90, L2 + 0.03, 1.45)), res=RES, body_target=TARGET, max_edge=0.14,
    doors=2, fd1=lambda Z: np.full_like(Z, PR.DOOR_REAR),
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.195, X_W=0.715,
    paint=car90.lin((186, 28, 40)), paint_metal=0.0, paint_rough=0.30, interior_color=(0.05, 0.047, 0.045),
    dlo_mask=dlo_mask, dlo_bot=0.03, dlo_round=0.03, top_off=0.05, a_off=A_OFF,
    dlo_rear=lambda Z, c_s: np.full_like(Z, -1.40),
    pillars=[], b_s=PR.DOOR_REAR, b_slant=0.0, fd0=PR.DOOR_FRONT, fdoor_mask=fdoor_mask, sill=PR.SILL,
    ws_dom=-0.40, ws_ztop=1.352, ws_side=0.065, bl_dom=-0.85, bl_zlo=1.05, bl_ztop=1.37, bl_side=0.10,
    hood=(9.0, 1.3, 9.0), lid=(-0.96, 0.62, 0.585), rear_dom=0.62,
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.72, head_rnd=0.010,
    grille=(0.322, 0.570, 0.672), grille_rnd=0.010, grille_bars=3, grille_sur_mat='trim_black', bar_mat='trim_black',
    lower_intake=(0.42, 0.215, 0.330),
    tail=(0.215, 0.592, 0.815), tail_s=-2.22, tail_panel=False, reverse=(0.225, 0.33, 0.605, 0.67), rplate=0.712,
    handles=[(-0.40, BELT - 0.065)], handle_size=(0.06, 0.016),
    markers=((S_FA - 0.56, 0.665), (-9.0, 0.0)), fuel=(S_RA - 0.30, 0.80),
    rub=(lambda s: PR.STRIP[0] + (0.5 * (PR.BUMP[0] + PR.BUMP[1]) - PR.STRIP[0]) * _ends(s),
         lambda s: PR.STRIP[1] + (0.5 * (PR.BUMP[1] - PR.BUMP[0]) - PR.STRIP[1]) * _ends(s)),
    rub_raise=0.0, rub_nz=1.01,
    antenna=False, rear_wiper=1.10, mirror_scale=0.85, mirror_at=(0.40, BELT + 0.07),
    exhaust=(0.42, S_RA - 0.9, 0.22),
    extra_cuts=[('hood2', hood_fn, [-0.0024, 0.0024]), ('skirt', skirt_fn, [0.0])],
    extra_labels={},
    extra_rules=[('gap', lambda fm: np.abs(fm['hood2']) < 0.0024), ('gap', lambda fm: fm['skirt'] < 0)],
    extras=[lip_spoiler, sunroof],
    interior=dict(seat_s=-0.10, seat_x=0.36, floor=0.30, dash_s=0.64, dash_z=0.84, dash_w=0.70, wheel_s=0.36, hip_z=0.48,
                  seat_h=0.62, rear_seats=True, rear_s=-1.0, cabin_bounds=((-0.76, -1.95, 0.30), (0.76, 0.72, 1.38)),
                  glass_band=(BELT + 0.02, 1.33)),
    wheel=dict(type='saab3', rim=dict(r_lip=0.200, r_barrel=0.180, width=0.16, a_face=0.050, dish=0.018, thick=0.010,
                                      open_r0=0.078, open_r1=0.160, spoke_w0=0.034, spoke_w1=0.072, sweep=2.0, cap_r=0.052)),
    wheel_target=1100, tyre_seg=26, rim_color=(0.66, 0.67, 0.69), rim_rough=0.32,
)

if __name__ == '__main__':
    car90.W9 = WS          # this car's three-spoke rims (wheels_saab900.add_wheels has the wheels90 signature)
    car90.build(C, OUT)
