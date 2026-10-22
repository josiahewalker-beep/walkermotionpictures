"""Wood-brown/maroon 1990s compact pickup (regular cab, step-side-free fleetside bed, chrome bumpers, steel wheels;
generic, S-10/Ranger era). File name kept as car_sedan_b.glb per the scene contract.
python3 sedan_b.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90
from carlib import smax, sd_round_box, box

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_sedan_b.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.010
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 10000

S_FA, S_RA, RT = 1.42, -1.33, 0.34
BELT = 1.05
WELL_R = 0.42
ZA = RT + 0.01
BED = dict(xh=0.79, s0=-2.31, s1=-0.50, floor=0.56)
P = dict(
    half_w=0.86,
    curves=dict(
        W=[(2.37, 0.70), (2.28, 0.82), (2.05, 0.85), (1.5, 0.86), (0.0, 0.86), (-2.30, 0.86), (-2.375, 0.84)],
        Ztop=[(2.37, 0.86), (2.30, 0.92), (2.1, 0.95), (1.5, 0.99), (1.0, 1.02), (0.6, 1.04), (0.3, 1.05), (-2.375, 1.05)],
        fender=[(2.37, 0.0), (2.0, 0.008), (1.2, 0.0), (-2.37, 0.0)],
        Zbot=[(2.37, 0.45), (2.25, 0.36), (2.0, 0.33), (0.0, 0.32), (-2.0, 0.34), (-2.3, 0.40), (-2.375, 0.46)],
        Lf=[(0.36, 2.28), (0.44, 2.35), (0.56, 2.37), (0.80, 2.375), (0.92, 2.36), (0.98, 2.32), (1.04, 2.15)],
        Lr=[(0.40, -2.30), (0.48, -2.37), (0.60, -2.375), (1.0, -2.375), (1.05, -2.37), (1.10, -2.30)],
        crease_z=[(2.3, 0.98), (0.0, 1.0), (-2.3, 1.0)],
        crease2_z=[(2.3, 0.60), (-2.3, 0.60)],
        Wg=[(0.9, 0.76), (0.4, 0.79), (-0.5, 0.79)],
        Zroof=[(0.75, 1.30), (0.5, 1.53), (0.25, 1.585), (0.0, 1.60), (-0.44, 1.60)],
    ),
    tuck=0.035, tuck_z0=0.34, tuck_z1=0.58,
    crease_k=0.08, crease_sharp=0.010, shoulder_k=0.30, crease2_k=0.02,
    flares=[(S_FA, RT, 0.44, 0.008, 0.09), (S_RA, RT, 0.44, 0.008, 0.09)],
    haunches=[], fender_x0=0.40, fender_x1=0.75, hood_crown=0.02,
    nose_corner=0.22, nose_pow=3.5, tail_corner=0.05, tail_pow=5.0,
    k_shoulder=0.05, k_nose=0.06, k_tail=0.04, k_bottom=0.05, normal_blur=0.025,
    belt=BELT, tumble=0.15, tumble2=0.25,
    ws_line=((0.95, 1.03), (0.42, 1.56)), ws_wrap=0.12, ws_bulge=0.01,
    bl_line=((-0.44, 1.0), (-0.42, 1.62)), bl_wrap=0.03,
    roof_crown=0.035, k_roof=0.05, k_ws=0.05, k_bl=0.04, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, ZA, WELL_R, 0.50), (S_RA, ZA, WELL_R, 0.50)],
)

def field_mod(d, x, s, z):
    """Carve the cargo bed (with wheel tubs) and the cab-to-bed gap out of the one-piece body field."""
    ax = np.abs(x)
    Pb = np.stack([x, s, z], -1)
    sc = 0.5 * (BED['s0'] + BED['s1']); sh = 0.5 * (BED['s1'] - BED['s0'])
    bed = sd_round_box(Pb, (0.0, sc, BED['floor'] + 0.8), (BED['xh'], sh, 0.8), 0.02)
    tub = smax(np.sqrt((s - S_RA) ** 2 + (z - ZA) ** 2) - (WELL_R + 0.05), 0.52 - ax, 0.01)
    bed = smax(bed, -tub, 0.012)
    d = smax(d, -bed, 0.008)
    gap = np.maximum(np.abs(s + 0.455) - 0.014, 0.40 - z)
    return smax(d, -gap, 0.003)

def bumpers(parts, B, f, L):
    for (sc, zc, hs) in ((-2.41, 0.47, 0.07), (2.40, 0.50, 0.06)):
        V, F = box((0.0, sc, zc), (0.83, hs, 0.085))
        parts.add('body', V, F, 'chrome', flat=True)
        V, F = box((0.0, sc - np.sign(sc) * 0.02, zc - 0.07), (0.78, hs, 0.025))
        parts.add('body', V, F, 'trim_black', flat=True)

HL = (0.40, 0.80, 0.80, 0.90)
in_bed = lambda fm: ((np.abs(fm['c'][:, 0]) < BED['xh'] + 0.005) & (fm['c'][:, 1] > BED['s0'] - 0.005)
                     & (fm['c'][:, 1] < BED['s1'] + 0.005) & (fm['c'][:, 2] < BELT - 0.025) & (fm['c'][:, 2] > BED['floor'] - 0.02))
C = dict(
    name='car_sedan_b', P=P, BOUNDS=((-0.92, -2.40, 0.28), (0.92, 2.40, 1.64)), res=RES, body_target=TARGET,
    field_mod=field_mod, doors=2, fd1=lambda Z: np.full_like(Z, -0.30),
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.205, X_W=0.72,
    paint=car90.lin((96, 38, 30)), paint_metal=0.3, paint_rough=0.38, interior_color=(0.06, 0.05, 0.045),
    dlo_rear=lambda Z, c_s: np.full_like(Z, -0.33), top_off=0.055, a_off=0.075,
    pillars=[], b_s=-0.30, fd0=0.91, sill=0.42,
    ws_dom=0.3, bl_dom=-0.43, bl_zlo=1.14, bl_ztop=1.52, bl_side=0.12,
    hood=(1.05, 0.70, HL[3] + 0.012), lid=(-2.30, 0.80, 0.58),
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.62,
    grille=(0.38, 0.78, 0.92), grille_bars=2, grille_vbars=5, grille_sur_mat='chrome', lower_intake=(0.50, 0.40, 0.44),
    tail=(0.70, 0.62, 0.98), tail_panel=False, reverse=(0.72, 0.82, 0.63, 0.70), rplate=0.76,
    handles=[-0.18], markers=((S_FA + 0.78, 0.82), (S_RA - 0.85, 0.86)), fuel=(S_RA + 0.55, BELT - 0.13),
    rub=(lambda s: np.full_like(s, 0.70), 0.018),
    extra_labels={'bedliner': dict(mat='trim_black', depth=0.0, col=0.6)},
    extra_rules=[('bedliner', in_bed)],
    extras=[bumpers], exhaust=(0.45, S_RA - 0.85, 0.40),
    interior=dict(seat_s=-0.02, seat_x=0.36, floor=0.48, dash_s=0.70, dash_z=1.05, dash_w=0.72, wheel_s=0.38, hip_z=0.70,
                  seat_h=0.55, rear_seats=False, cabin_bounds=((-0.80, -0.42, 0.48), (0.80, 0.95, 1.56)),
                  glass_band=(BELT + 0.02, 1.53), shell_target=1400),
    wheel=dict(type='steel', hole_type='round', r_cover=0.19, a_face=0.06, dome=0.008, roll=0.035, ring_r=0.155, ring_h=0.006,
               cap_h=0.0, cap_r=0.05, holes=6, hole_r=0.125, hole_w=0.04),
    wheel_target=1300, tyre_seg=30, rim_color=(0.55, 0.56, 0.58), rim_rough=0.45,
)

if __name__ == '__main__':
    car90.build(C, OUT)
