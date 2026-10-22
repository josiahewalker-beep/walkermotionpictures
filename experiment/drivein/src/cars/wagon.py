"""Forest-green 1990s full-size station wagon (long, low, upright tailgate, roof rack; generic, no badges).
python3 wagon.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_wagon.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.011
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 26000

S_FA, S_RA, RT = 1.55, -1.39, 0.34
BELT = 0.93
P = dict(
    half_w=0.97,
    curves=dict(
        W=[(2.65, 0.75), (2.55, 0.88), (2.3, 0.94), (1.8, 0.96), (0.0, 0.97), (-2.0, 0.965), (-2.5, 0.945), (-2.65, 0.88)],
        Ztop=[(2.65, 0.66), (2.55, 0.74), (2.3, 0.79), (1.8, 0.83), (1.3, 0.87), (1.0, 0.89), (0.0, 0.93), (-2.65, 0.95)],
        fender=[(2.65, 0.0), (2.2, 0.012), (1.2, 0.0), (-2.65, 0.0)],
        Zbot=[(2.65, 0.34), (2.5, 0.22), (2.2, 0.18), (0.0, 0.17), (-2.2, 0.19), (-2.5, 0.25), (-2.65, 0.35)],
        Lf=[(0.20, 2.52), (0.28, 2.62), (0.40, 2.65), (0.55, 2.655), (0.65, 2.645), (0.72, 2.60), (0.80, 2.40)],
        Lr=[(0.25, -2.52), (0.33, -2.62), (0.45, -2.65), (1.0, -2.655), (1.30, -2.625), (1.42, -2.58), (1.50, -2.45)],
        crease_z=[(2.6, 0.80), (0.0, 0.84), (-2.6, 0.87)],
        crease2_z=[(2.6, 0.45), (-2.6, 0.46)],
        Wg=[(1.3, 0.80), (0.8, 0.86), (0.0, 0.875), (-2.0, 0.875), (-2.5, 0.86), (-2.65, 0.84)],
        Zroof=[(1.1, 1.05), (0.75, 1.33), (0.45, 1.44), (0.0, 1.475), (-1.0, 1.48), (-2.0, 1.475), (-2.4, 1.46), (-2.65, 1.44)],
    ),
    tuck=0.05, tuck_z0=0.2, tuck_z1=0.48,
    crease_k=0.12, crease_sharp=0.010, shoulder_k=0.30, crease2_k=0.03,
    flares=[(S_FA, RT, 0.42, 0.006, 0.10), (S_RA, RT, 0.42, 0.006, 0.10)],
    haunches=[], fender_x0=0.40, fender_x1=0.80, hood_crown=0.025,
    nose_corner=0.30, nose_pow=3.0, tail_corner=0.10, tail_pow=3.5,
    k_shoulder=0.06, k_nose=0.06, k_tail=0.05, k_bottom=0.05, normal_blur=0.03,
    belt=BELT, tumble=0.18, tumble2=0.25,
    ws_line=((1.25, 0.90), (0.40, 1.43)), ws_wrap=0.14, ws_bulge=0.01,
    roof_crown=0.04, k_roof=0.06, k_ws=0.05, k_bl=0.05, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.01, 0.40, 0.50), (S_RA, RT + 0.01, 0.40, 0.50)],
)
HL = (0.40, 0.84, 0.575, 0.68)
C = dict(
    name='car_wagon', P=P, BOUNDS=((-1.02, -2.68, 0.14), (1.02, 2.68, 1.51)), res=RES, body_target=TARGET,
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.225, X_W=0.81,
    paint=car90.lin((34, 64, 46)), paint_metal=0.4, paint_rough=0.36, interior_color=(0.05, 0.047, 0.04),
    dlo_rear=lambda Z, c_s: np.full_like(Z, -2.44), top_off=0.055, a_off=0.075,
    pillars=[(-0.05, 0.035, -0.06), (-1.18, 0.05, 0.0)], b_s=-0.05, b_slant=-0.06, fd0=1.10,
    rd1=lambda Z, c_s: np.full_like(Z, -1.16), sill=0.29,
    ws_dom=0.35, bl_dom=-2.45, bl_zlo=1.0, bl_ztop=1.40, bl_side=0.11,
    hood=(1.31, 0.76, HL[3] + 0.012), lid=(-2.47, 0.80, 0.52),
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.66,
    grille=(0.38, 0.565, 0.69), grille_bars=3, grille_vbars=9, grille_sur_mat='chrome', lower_intake=(0.50, 0.26, 0.38),
    tail=(0.66, 0.55, 0.95), tail_panel=False, reverse=(0.68, 0.79, 0.565, 0.625), rplate=0.72,
    handles=[0.07, -1.04], markers=((S_FA + 0.85, 0.60), (S_RA - 0.95, 0.64)), fuel=(S_RA - 0.55, BELT - 0.14),
    rub=(lambda s: np.full_like(s, 0.53), 0.026), rub_raise=0.008,
    roof_rails=(0.62, 0.35, -2.35, 0.05), cross_bars=[-0.6, -1.7], rear_wiper=1.07,
    interior=dict(seat_s=0.15, seat_x=0.40, floor=0.32, dash_s=0.98, dash_z=0.88, dash_w=0.78, wheel_s=0.62, hip_z=0.52,
                  seat_h=0.62, rear_seats=True, rear_s=-0.75, cabin_bounds=((-0.85, -2.45, 0.32), (0.85, 1.15, 1.44)),
                  glass_band=(BELT + 0.02, 1.40), shell_target=1600),
    wheel=dict(type='cover', r_cover=0.198, a_face=0.075, dome=0.010, roll=0.028, ring_r=0.10, ring_h=0.004, cap_h=0.014,
               cap_r=0.055, holes=14, hole_r=0.15, hole_len=0.075, hole_w=0.014),
    wheel_target=1800, tyre_seg=36, rim_color=(0.6, 0.61, 0.63), rim_rough=0.35,
)

if __name__ == '__main__':
    car90.build(C, OUT)
