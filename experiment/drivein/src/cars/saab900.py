"""Cherry-red 1987 classic Saab 900 Turbo SPG three-door hatchback (the car of Hamaguchi's "Drive My Car", 2021).
Wraparound windscreen, tall upright glasshouse with thin pillars, long front overhang, clamshell bonnet (side shut line at
headlamp-top height), long fastback hatch with lip spoiler, black bumpers + rubbing strips, body-colour SPG kit (deep air dam,
sculpted skirts, rear valance), sunroof, three-spoke alloys. Generic procedural geometry: no badges or lettering, blank plates.
python3 saab900.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90
import details as D
import wheels_saab900 as WS
from carlib import sstep, gauss, smax

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_saab900.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.011
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

# 900 three-door: L 4.69, W 1.69, H 1.42, wheelbase 2.517, 195/60 R15
HALF_L = 2.345
S_FA, S_RA, RT = 1.27, -1.247, 0.3075
BELT = 0.87
WELL_R = 0.365
ZA = RT + 0.01
BUMP = (0.405, 0.555)          # black bumper band (z)

def field_mod(d, x, s, z):
    """Bumpers proud of the body, SPG skirt bulge, hatch lip spoiler."""
    ax = np.abs(x)
    band = sstep(BUMP[0] - 0.012, BUMP[0] + 0.004, z) * (1 - sstep(BUMP[1] - 0.004, BUMP[1] + 0.012, z))
    ends = sstep(S_FA + 0.38, S_FA + 0.50, s) + sstep(-(S_RA - 0.44), -(S_RA - 0.56), -s)
    near_well = np.minimum(np.sqrt((s - S_FA) ** 2 + (z - ZA) ** 2), np.sqrt((s - S_RA) ** 2 + (z - ZA) ** 2))
    keep = sstep(WELL_R + 0.01, WELL_R + 0.05, near_well)
    d = d - band * (0.012 + 0.026 * ends) * keep
    # skirts: soft outward bulge low between the arches
    skirt = gauss(z, 0.27, 0.07) * sstep(S_RA + 0.30, S_RA + 0.45, s) * (1 - sstep(S_FA - 0.45, S_FA - 0.30, s))
    d = d - 0.014 * skirt * (ax > 0.5)
    # rear lip spoiler across the hatch at the base of the glass
    sp = np.sqrt(((s + 2.215) / 0.05) ** 2 + ((z - 1.005) / 0.022) ** 2) - 1.0
    sp = smax(sp * 0.03, ax - 0.66, 0.02)
    return np.minimum(d, sp)

P = dict(
    half_w=0.845,
    curves=dict(
        W=[(HALF_L, 0.70), (2.28, 0.80), (2.10, 0.835), (1.6, 0.845), (0.0, 0.845), (-1.8, 0.845), (-2.20, 0.83), (-HALF_L, 0.79)],
        Ztop=[(HALF_L, 0.69), (2.25, 0.725), (2.0, 0.76), (1.5, 0.80), (1.0, 0.84), (0.6, 0.865), (0.0, 0.88), (-1.0, 0.90),
              (-1.8, 0.94), (-2.2, 0.98), (-HALF_L, 0.97)],
        fender=[(HALF_L, 0.0), (2.0, 0.006), (1.0, 0.006), (0.6, 0.0), (-HALF_L, 0.0)],
        Zbot=[(HALF_L, 0.25), (2.27, 0.165), (1.9, 0.16), (0.0, 0.175), (-1.9, 0.18), (-2.25, 0.20), (-HALF_L, 0.27)],
        Lf=[(0.14, 2.25), (0.20, 2.31), (0.32, 2.335), (0.46, 2.345), (0.56, 2.305), (0.64, 2.285), (0.70, 2.25), (0.74, 2.16), (0.78, 1.95)],
        Lr=[(0.18, -2.27), (0.24, -2.32), (0.36, -2.34), (0.50, -2.345), (0.60, -2.31), (0.85, -2.30), (0.98, -2.27), (1.03, -2.18), (1.08, -1.95)],
        crease_z=[(2.3, 0.70), (1.0, 0.77), (0.0, 0.79), (-2.3, 0.82)],
        crease2_z=[(2.3, 0.37), (-2.3, 0.37)],
        Wg=[(1.0, 0.66), (0.6, 0.73), (0.2, 0.755), (-0.8, 0.755), (-1.6, 0.74), (-2.1, 0.69), (-2.3, 0.62)],
        Zroof=[(1.0, 0.92), (0.5, 1.25), (0.2, 1.375), (0.0, 1.405), (-0.5, 1.42), (-0.9, 1.415), (-1.2, 1.37), (-2.0, 1.05), (-2.3, 0.98)],
    ),
    tuck=0.035, tuck_z0=0.17, tuck_z1=0.38,
    crease_k=0.05, crease_sharp=0.010, shoulder_k=0.22, crease2_k=0.03,
    flares=[(S_FA, RT, WELL_R + 0.02, 0.006, 0.08), (S_RA, RT, WELL_R + 0.02, 0.006, 0.08)],
    haunches=[], fender_x0=0.45, fender_x1=0.78, hood_crown=0.03,
    nose_corner=0.24, nose_pow=2.8, tail_corner=0.12, tail_pow=3.0,
    k_shoulder=0.06, k_nose=0.05, k_tail=0.05, k_bottom=0.05, normal_blur=0.025,
    belt=BELT, tumble=0.13, tumble2=0.18,
    ws_line=((0.70, 0.87), (0.06, 1.39)), ws_wrap=0.24, ws_bulge=0.015,
    bl_line=((-2.19, 0.99), (-1.08, 1.41)), bl_wrap=0.06,
    roof_crown=0.035, k_roof=0.06, k_ws=0.045, k_bl=0.05, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, ZA, WELL_R, 0.48), (S_RA, ZA, WELL_R, 0.48)],
)

def sunroof(parts, B, f, L):
    """Steel tilt/slide sunroof: thin dark shut line on the roof (front-centre)."""
    s0, s1, xh = -0.42, 0.12, 0.39
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

HL = (0.37, 0.735, 0.565, 0.685)
C = dict(
    lod=0.4, name='car_saab900', P=P, BOUNDS=((-0.90, -2.40, 0.12), (0.90, 2.40, 1.46)), res=RES, body_target=TARGET,
    field_mod=field_mod, doors=2, fd1=lambda Z: np.full_like(Z, -0.47),
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.195, X_W=0.715,
    paint=car90.lin((156, 18, 30)), paint_metal=0.0, paint_rough=0.30, interior_color=(0.05, 0.047, 0.045),
    dlo_rear=lambda Z, c_s: -1.40 + 0.72 * (Z - BELT), top_off=0.05, a_off=0.06,
    pillars=[(-0.50, 0.028, -0.03)], b_s=-0.47, b_slant=-0.03, fd0=0.64, sill=0.39,
    ws_dom=0.15, ws_ztop=1.345, ws_side=0.075, bl_dom=-0.95, bl_zlo=1.02, bl_ztop=1.355, bl_side=0.10, dlo_bot=0.03,
    hood=(0.66, 1.3, 0.695), lid=(-1.02, 0.64, 0.60), rear_dom=0.62,
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.70, head_rnd=0.012,
    grille=(0.33, 0.57, 0.678), grille_bars=3, grille_sur_mat='trim_black', bar_mat='trim_black', lower_intake=(0.44, 0.24, 0.355),
    tail=(0.30, 0.625, 0.80), tail_s=-2.22, tail_panel=False, reverse=(0.31, 0.42, 0.635, 0.69), rplate=0.712,
    handles=[-0.33], handle_z=BELT - 0.06, markers=((S_FA - 0.52, 0.66), (-9.0, 0.0)), fuel=(S_RA - 0.50, 0.78),
    rub=(lambda s: np.full_like(s, 0.5 * (BUMP[0] + BUMP[1])),
         0.5 * (BUMP[1] - BUMP[0])), rub_raise=0.0,
    antenna=False, rear_wiper=1.06, mirror_scale=0.85, mirror_dz=0.06,
    exhaust=(0.42, S_RA - 0.9, 0.22),
    extras=[sunroof],
    interior=dict(seat_s=-0.12, seat_x=0.36, floor=0.30, dash_s=0.62, dash_z=0.84, dash_w=0.70, wheel_s=0.33, hip_z=0.48,
                  seat_h=0.60, rear_seats=True, rear_s=-1.0, cabin_bounds=((-0.76, -1.95, 0.30), (0.76, 0.70, 1.38)),
                  glass_band=(BELT + 0.02, 1.33)),
    wheel=dict(type='saab3', rim=dict(r_lip=0.200, r_barrel=0.180, width=0.16, a_face=0.050, dish=0.018, thick=0.010,
                                      open_r0=0.072, open_r1=0.163, spoke_w0=0.020, spoke_w1=0.034, sweep=2.4, cap_r=0.052)),
    wheel_target=1100, tyre_seg=26, rim_color=(0.66, 0.67, 0.69), rim_rough=0.32,
)

if __name__ == '__main__':
    car90.W9 = WS          # this car's three-spoke rims (wheels_saab900.add_wheels has the wheels90 signature)
    car90.build(C, OUT)
