"""Mustard/gold 1990s compact sedan (boxier notchback of the Corsica/Corolla era, bottle-cap wheel covers; generic).
python3 sedan_a.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_sedan_a.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.010
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

S_FA, S_RA, RT = 1.33, -1.29, 0.30
BELT = 0.90
P = dict(
    half_w=0.86,
    curves=dict(
        W=[(2.27, 0.62), (2.19, 0.76), (2.0, 0.82), (1.67, 0.845), (1.1, 0.855), (0.0, 0.86), (-1.1, 0.858), (-1.77, 0.84),
           (-2.10, 0.80), (-2.27, 0.70)],
        Ztop=[(2.27, 0.62), (2.21, 0.69), (2.1, 0.725), (1.85, 0.75), (1.5, 0.785), (1.1, 0.82), (0.88, 0.84), (0.55, 0.87),
              (0.0, 0.90), (-1.0, 0.91), (-1.5, 0.925), (-1.9, 0.94), (-2.15, 0.94), (-2.27, 0.905)],
        fender=[(2.27, 0.0), (1.9, 0.01), (1.3, 0.012), (0.8, 0.0), (-2.27, 0.0)],
        Zbot=[(2.27, 0.32), (2.18, 0.21), (1.95, 0.17), (0.0, 0.16), (-1.85, 0.18), (-2.14, 0.25), (-2.27, 0.35)],
        Lf=[(0.20, 2.15), (0.26, 2.23), (0.34, 2.265), (0.48, 2.275), (0.58, 2.268), (0.65, 2.25), (0.72, 2.20), (0.80, 2.0)],
        Lr=[(0.28, -2.14), (0.36, -2.23), (0.48, -2.265), (0.75, -2.275), (0.88, -2.268), (0.95, -2.23), (1.0, -2.10)],
        crease_z=[(2.2, 0.73), (0.0, 0.80), (-2.2, 0.83)],
        crease2_z=[(2.2, 0.42), (-2.2, 0.43)],
        Wg=[(1.1, 0.69), (0.75, 0.73), (0.3, 0.745), (-0.6, 0.745), (-1.2, 0.735), (-1.75, 0.69), (-2.0, 0.64)],
        Zroof=[(0.95, 0.98), (0.55, 1.22), (0.3, 1.315), (0.0, 1.355), (-0.5, 1.37), (-0.9, 1.355), (-1.25, 1.29), (-1.6, 1.12), (-1.85, 1.0)],
    ),
    tuck=0.04, tuck_z0=0.2, tuck_z1=0.46,
    crease_k=0.10, crease_sharp=0.010, shoulder_k=0.28, crease2_k=0.03,
    flares=[(S_FA, RT, 0.37, 0.006, 0.10), (S_RA, RT, 0.37, 0.006, 0.10)],
    haunches=[], fender_x0=0.38, fender_x1=0.72, hood_crown=0.025,
    nose_corner=0.30, nose_pow=2.6, tail_corner=0.12, tail_pow=3.0,
    k_shoulder=0.06, k_nose=0.06, k_tail=0.05, k_bottom=0.05, normal_blur=0.025,
    belt=BELT, tumble=0.22, tumble2=0.35,
    ws_line=((1.04, 0.87), (0.17, 1.345)), ws_wrap=0.14, ws_bulge=0.01,
    bl_line=((-1.84, 0.93), (-1.16, 1.35)), bl_wrap=0.08,
    roof_crown=0.04, k_roof=0.06, k_ws=0.05, k_bl=0.04, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.01, 0.355, 0.46), (S_RA, RT + 0.01, 0.355, 0.46)],
)
HL = (0.33, 0.74, 0.55, 0.64)
C = dict(
    lod=0.4, name='car_sedan_a', P=P, BOUNDS=((-0.91, -2.30, 0.13), (0.91, 2.30, 1.40)), res=RES, body_target=TARGET,
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.178, TYRE_W=0.185, X_W=0.725,
    paint=car90.lin((178, 138, 48)), paint_metal=0.5, paint_rough=0.33, interior_color=(0.06, 0.05, 0.04),
    dlo_rear=lambda Z, c_s: c_s(Z) + 0.10, top_off=0.055, a_off=0.075,
    pillars=[(-0.10, 0.035, -0.08), (-1.10, 0.02, 0.0)], b_s=-0.10, b_slant=-0.08, fd0=0.92,
    rd1=lambda Z, c_s: np.full_like(Z, -1.10), sill=0.28,
    ws_dom=0.3, bl_dom=-1.0, bl_zlo=0.965, bl_ztop=1.31,
    hood=(1.10, 0.66, HL[3] + 0.012), lid=(-1.82, 0.66, 0.812),
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.60,
    grille=(0.30, 0.555, 0.625), grille_bars=2, bar_mat='trim_black', lower_intake=(0.42, 0.24, 0.35),
    tail=(0.28, 0.66, 0.80), rplate=0.56,
    handles=[0.02, -0.98], markers=((S_FA + 0.75, 0.57), (S_RA - 0.78, 0.62)), fuel=(S_RA - 0.40, BELT - 0.13),
    rub=(lambda s: np.full_like(s, 0.45), 0.018), rub_mat='chrome', rub_raise=0.004,
    interior=dict(seat_s=0.02, seat_x=0.36, floor=0.29, dash_s=0.80, dash_z=0.84, dash_w=0.70, wheel_s=0.46, hip_z=0.48,
                  seat_h=0.60, rear_seats=True, rear_s=-0.82, cabin_bounds=((-0.78, -1.6, 0.29), (0.78, 0.98, 1.33)),
                  glass_band=(BELT + 0.02, 1.28), shell_target=1600),
    wheel=dict(type='cover', hole_type='round', r_cover=0.188, a_face=0.065, dome=0.016, roll=0.03, ring_r=0.09, ring_h=0.0,
               cap_h=0.010, cap_r=0.045, holes=6, hole_r=0.122, hole_w=0.05),
    wheel_target=1000, tyre_seg=26, rim_color=(0.62, 0.63, 0.65), rim_rough=0.35,
)

if __name__ == '__main__':
    car90.build(C, OUT)
