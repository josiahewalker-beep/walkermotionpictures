"""Maroon/wood-brown 1990s full-size sedan (long, formal upright roofline, chrome waterfall grille, chrome side
moulding, fine-slot wheel covers; generic Crown Vic/Caprice-era, no badges).
python3 sedan_b.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_sedan_b.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.011
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 3800

S_FA, S_RA, RT = 1.50, -1.48, 0.33
BELT = 0.93
P = dict(
    half_w=0.95,
    curves=dict(
        W=[(2.60, 0.74), (2.52, 0.87), (2.3, 0.93), (1.8, 0.945), (0.0, 0.95), (-1.8, 0.948), (-2.35, 0.93), (-2.60, 0.84)],
        Ztop=[(2.60, 0.66), (2.54, 0.74), (2.4, 0.78), (2.0, 0.81), (1.5, 0.85), (1.1, 0.88), (0.6, 0.91), (0.0, 0.93),
              (-1.0, 0.94), (-1.8, 0.96), (-2.4, 0.97), (-2.60, 0.94)],
        fender=[(2.6, 0.0), (2.2, 0.012), (1.4, 0.01), (0.9, 0.0), (-2.6, 0.0)],
        Zbot=[(2.60, 0.33), (2.5, 0.22), (2.2, 0.18), (0.0, 0.17), (-2.2, 0.19), (-2.5, 0.26), (-2.60, 0.36)],
        Lf=[(0.20, 2.48), (0.26, 2.56), (0.34, 2.595), (0.48, 2.60), (0.62, 2.598), (0.70, 2.58), (0.76, 2.52), (0.84, 2.30)],
        Lr=[(0.28, -2.48), (0.36, -2.57), (0.48, -2.60), (0.75, -2.605), (0.92, -2.60), (0.98, -2.56), (1.04, -2.40)],
        crease_z=[(2.5, 0.78), (0.0, 0.82), (-2.5, 0.86)],
        crease2_z=[(2.5, 0.44), (-2.5, 0.45)],
        Wg=[(1.2, 0.76), (0.8, 0.80), (0.3, 0.82), (-0.8, 0.82), (-1.4, 0.81), (-1.8, 0.78), (-2.1, 0.72)],
        Zroof=[(1.0, 1.0), (0.6, 1.27), (0.3, 1.38), (0.0, 1.42), (-0.8, 1.43), (-1.3, 1.40), (-1.5, 1.30), (-1.8, 1.10), (-2.0, 1.0)],
    ),
    tuck=0.045, tuck_z0=0.2, tuck_z1=0.48,
    crease_k=0.12, crease_sharp=0.010, shoulder_k=0.30, crease2_k=0.03,
    flares=[(S_FA, RT, 0.40, 0.006, 0.10), (S_RA, RT, 0.40, 0.006, 0.10)],
    haunches=[], fender_x0=0.42, fender_x1=0.80, hood_crown=0.025,
    nose_corner=0.25, nose_pow=3.2, tail_corner=0.08, tail_pow=3.5,
    k_shoulder=0.06, k_nose=0.06, k_tail=0.05, k_bottom=0.05, normal_blur=0.03,
    belt=BELT, tumble=0.20, tumble2=0.30,
    ws_line=((1.20, 0.90), (0.25, 1.40)), ws_wrap=0.14, ws_bulge=0.01,
    bl_line=((-1.88, 0.98), (-1.36, 1.42)), bl_wrap=0.06,
    roof_crown=0.04, k_roof=0.06, k_ws=0.05, k_bl=0.04, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.01, 0.39, 0.50), (S_RA, RT + 0.01, 0.39, 0.50)],
)
HL = (0.44, 0.86, 0.57, 0.67)
C = dict(
    lod=0.4, name='car_sedan_b', P=P, BOUNDS=((-1.0, -2.63, 0.14), (1.0, 2.63, 1.45)), res=RES, body_target=TARGET,
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.215, X_W=0.80,
    paint=car90.lin((86, 32, 30)), paint_metal=0.35, paint_rough=0.36, interior_color=(0.07, 0.045, 0.04),
    dlo_rear=lambda Z, c_s: c_s(Z) + 0.20, top_off=0.055, a_off=0.075,
    pillars=[(-0.10, 0.035, -0.08), (-1.20, 0.02, 0.0)], b_s=-0.10, b_slant=-0.08, fd0=1.04,
    rd1=lambda Z, c_s: np.full_like(Z, -1.20), sill=0.29,
    ws_dom=0.3, bl_dom=-1.1, bl_zlo=0.995, bl_ztop=1.385, ws_ztop=1.36,
    hood=(1.26, 0.74, HL[3] + 0.012), lid=(-1.86, 0.74, 0.90),
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.66,
    grille=(0.40, 0.575, 0.675), grille_bars=1, grille_vbars=11, grille_sur_mat='chrome', lower_intake=(0.50, 0.27, 0.37),
    tail=(0.36, 0.68, 0.88), rplate=0.60,
    handles=[0.02, -1.08], markers=((S_FA + 0.85, 0.60), (S_RA - 0.85, 0.64)), fuel=(S_RA - 0.45, BELT - 0.13),
    rub=(lambda s: np.full_like(s, 0.50), 0.02), rub_mat='chrome', rub_raise=0.005,
    interior=dict(seat_s=0.05, seat_x=0.40, floor=0.30, dash_s=0.92, dash_z=0.88, dash_w=0.78, wheel_s=0.56, hip_z=0.50,
                  seat_h=0.62, rear_seats=True, rear_s=-0.95, cabin_bounds=((-0.85, -1.75, 0.30), (0.85, 1.1, 1.40)),
                  glass_band=(BELT + 0.02, 1.36)),
    wheel=dict(type='cover', r_cover=0.198, a_face=0.072, dome=0.014, roll=0.03, ring_r=0.09, ring_h=0.006, cap_h=0.016,
               cap_r=0.055, holes=24, hole_r=0.145, hole_len=0.075, hole_w=0.009),
    wheel_target=1000, tyre_seg=26, rim_color=(0.66, 0.67, 0.69), rim_rough=0.25,
)

if __name__ == '__main__':
    car90.build(C, OUT)
