"""Hero: rust-red 1990s mid-size sedan (soft aero shape of the Taurus/Accord era, generic, no badges).
Driver's front window rolled down; empties `bucket_anchor` (door inner ledge, mid-window) and `ledge_drop` (ground).
python3 hero.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_hero.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0075
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 60000

S_FA, S_RA, RT = 1.42, -1.32, 0.316
BELT = 0.92
P = dict(
    half_w=0.90,
    curves=dict(
        W=[(2.44, 0.66), (2.35, 0.80), (2.15, 0.86), (1.8, 0.885), (1.2, 0.895), (0.0, 0.90), (-1.2, 0.898), (-1.9, 0.88),
           (-2.25, 0.84), (-2.44, 0.72)],
        Ztop=[(2.44, 0.62), (2.38, 0.69), (2.25, 0.735), (2.0, 0.765), (1.6, 0.805), (1.2, 0.845), (0.95, 0.87), (0.6, 0.895),
              (0.0, 0.92), (-1.0, 0.93), (-1.6, 0.945), (-2.0, 0.955), (-2.3, 0.955), (-2.44, 0.92)],
        fender=[(2.44, 0.0), (2.0, 0.012), (1.4, 0.015), (0.9, 0.0), (-2.44, 0.0)],
        Zbot=[(2.44, 0.33), (2.35, 0.22), (2.1, 0.18), (0.0, 0.17), (-2.0, 0.19), (-2.3, 0.26), (-2.44, 0.36)],
        Lf=[(0.20, 2.30), (0.26, 2.40), (0.34, 2.44), (0.48, 2.45), (0.58, 2.44), (0.65, 2.42), (0.72, 2.36), (0.80, 2.15)],
        Lr=[(0.28, -2.30), (0.36, -2.40), (0.48, -2.44), (0.75, -2.45), (0.90, -2.44), (0.97, -2.40), (1.03, -2.25)],
        crease_z=[(2.4, 0.74), (1.0, 0.79), (0.0, 0.82), (-2.4, 0.85)],
        crease2_z=[(2.4, 0.42), (-2.4, 0.44)],
        Wg=[(1.2, 0.72), (0.8, 0.765), (0.3, 0.785), (-0.6, 0.785), (-1.3, 0.77), (-1.9, 0.72), (-2.2, 0.66)],
        Zroof=[(1.0, 1.0), (0.6, 1.24), (0.3, 1.345), (0.0, 1.385), (-0.5, 1.40), (-0.9, 1.385), (-1.3, 1.32), (-1.7, 1.15), (-2.0, 1.02)],
    ),
    tuck=0.045, tuck_z0=0.2, tuck_z1=0.48,
    crease_k=0.06, crease_sharp=0.012, shoulder_k=0.25, crease2_k=0.03,
    flares=[(S_FA, RT, 0.39, 0.008, 0.10), (S_RA, RT, 0.39, 0.008, 0.10)],
    haunches=[], fender_x0=0.40, fender_x1=0.75, hood_crown=0.03,
    nose_corner=0.40, nose_pow=2.2, tail_corner=0.16, tail_pow=2.6,
    k_shoulder=0.07, k_nose=0.07, k_tail=0.06, k_bottom=0.05, normal_blur=0.025,
    belt=BELT, tumble=0.22, tumble2=0.35,
    ws_line=((1.12, 0.89), (0.18, 1.375)), ws_wrap=0.16, ws_bulge=0.01,
    bl_line=((-2.02, 0.95), (-1.12, 1.39)), bl_wrap=0.10,
    roof_crown=0.04, k_roof=0.07, k_ws=0.05, k_bl=0.05, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.01, 0.375, 0.48), (S_RA, RT + 0.01, 0.375, 0.48)],
)
HL = (0.36, 0.80, 0.545, 0.648)
C = dict(
    name='car_hero', P=P, BOUNDS=((-0.95, -2.47, 0.14), (0.95, 2.47, 1.43)), res=RES, body_target=TARGET,
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.205, X_W=0.765,
    paint=car90.lin((118, 30, 22)), paint_metal=0.3, paint_rough=0.36,
    interior_color=(0.055, 0.05, 0.045),
    dlo_rear=lambda Z, c_s: c_s(Z) + 0.12, top_off=0.055, a_off=0.075,
    pillars=[(-0.12, 0.035, -0.08), (-1.165, 0.02, 0.0)], b_s=-0.12, b_slant=-0.08, fd0=0.98,
    rd1=lambda Z, c_s: np.full_like(Z, -1.165), sill=0.29,
    ws_dom=0.3, bl_dom=-1.0, bl_zlo=0.985, bl_ztop=1.33,
    hood=(1.18, 0.70, HL[3] + 0.012), lid=(-1.99, 0.70, 0.872),
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.62,
    grille=(0.33, 0.552, 0.630), grille_bars=2, lower_intake=(0.46, 0.25, 0.37),
    tail=(0.30, 0.70, 0.858), rplate=0.585,
    handles=[0.0, -1.05], markers=((S_FA + 0.80, 0.58), (S_RA - 0.80, 0.63)), fuel=(S_RA - 0.42, BELT - 0.13),
    rub=(lambda s: np.interp(s, [-2.5, 2.5], [0.465, 0.45]), 0.02),
    open_window=True, ledge=0.065,
    interior=dict(seat_s=0.05, seat_x=0.37, floor=0.30, dash_s=0.85, dash_z=0.86, dash_w=0.72, wheel_s=0.50, hip_z=0.50,
                  seat_h=0.62, rear_seats=True, rear_s=-0.85, cabin_bounds=((-0.80, -1.7, 0.30), (0.80, 1.05, 1.36)),
                  glass_band=(BELT + 0.02, 1.30)),
    wheel=dict(type='cover', r_cover=0.198, a_face=0.07, dome=0.012, roll=0.03, ring_r=0.125, ring_h=0.005, cap_h=0.012,
               cap_r=0.05, holes=10, hole_r=0.155, hole_len=0.05, hole_w=0.022),
    wheel_target=4000, tyre_seg=56, rim_color=(0.62, 0.63, 0.65), rim_rough=0.32,
)

if __name__ == '__main__':
    car90.build(C, OUT)
