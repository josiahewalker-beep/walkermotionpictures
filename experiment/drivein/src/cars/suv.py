"""Cream/tan 1990s compact SUV (boxy four-door, tall greenhouse, two-tone lower, roof rack, 5-spoke alloys; generic).
python3 suv.py [out.glb] [res] [body_target]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'car_suv.glb')
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.011
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 6500

S_FA, S_RA, RT = 1.40, -1.44, 0.366
BELT = 1.13
P = dict(
    half_w=0.89,
    curves=dict(
        W=[(2.39, 0.72), (2.30, 0.84), (2.1, 0.875), (1.6, 0.885), (0.0, 0.89), (-2.1, 0.885), (-2.30, 0.86), (-2.39, 0.80)],
        Ztop=[(2.39, 0.95), (2.30, 1.02), (2.1, 1.055), (1.6, 1.08), (1.0, 1.10), (0.0, 1.12), (-2.39, 1.13)],
        fender=[(2.39, 0.0), (2.0, 0.01), (1.2, 0.0), (-2.39, 0.0)],
        Zbot=[(2.39, 0.48), (2.25, 0.38), (2.0, 0.35), (0.0, 0.34), (-2.0, 0.35), (-2.3, 0.41), (-2.39, 0.50)],
        Lf=[(0.40, 2.28), (0.48, 2.36), (0.60, 2.39), (0.80, 2.40), (0.95, 2.39), (1.02, 2.34), (1.10, 2.10)],
        Lr=[(0.45, -2.30), (0.55, -2.38), (0.70, -2.39), (1.30, -2.395), (1.62, -2.37), (1.72, -2.30), (1.78, -2.10)],
        crease_z=[(2.3, 1.02), (0.0, 1.04), (-2.3, 1.06)],
        crease2_z=[(2.3, 0.62), (-2.3, 0.62)],
        Wg=[(1.0, 0.78), (0.6, 0.82), (0.0, 0.83), (-2.0, 0.83), (-2.3, 0.80), (-2.39, 0.78)],
        Zroof=[(0.95, 1.28), (0.65, 1.65), (0.3, 1.74), (0.0, 1.76), (-1.5, 1.765), (-2.2, 1.75), (-2.39, 1.72)],
    ),
    tuck=0.04, tuck_z0=0.36, tuck_z1=0.60,
    crease_k=0.10, crease_sharp=0.010, shoulder_k=0.30, crease2_k=0.02,
    flares=[(S_FA, RT, 0.45, 0.012, 0.09), (S_RA, RT, 0.45, 0.012, 0.09)],
    haunches=[], fender_x0=0.40, fender_x1=0.75, hood_crown=0.02,
    nose_corner=0.25, nose_pow=3.5, tail_corner=0.08, tail_pow=4.0,
    k_shoulder=0.06, k_nose=0.06, k_tail=0.05, k_bottom=0.05, normal_blur=0.03,
    belt=BELT, tumble=0.12, tumble2=0.20,
    ws_line=((1.05, 1.10), (0.42, 1.71)), ws_wrap=0.12, ws_bulge=0.01,
    roof_crown=0.035, k_roof=0.06, k_ws=0.05, k_bl=0.05, k_belt=0.03, k_well=0.012,
    wells=[(S_FA, RT + 0.01, 0.43, 0.48), (S_RA, RT + 0.01, 0.43, 0.48)],
)
HL = (0.36, 0.80, 0.86, 0.975)
C = dict(
    lod=0.4, name='car_suv', P=P, BOUNDS=((-0.95, -2.42, 0.28), (0.95, 2.42, 1.80)), res=RES, body_target=TARGET,
    S_FA=S_FA, S_RA=S_RA, R_TYRE=RT, R_BEAD=0.19, TYRE_W=0.235, X_W=0.76,
    paint=car90.lin((190, 172, 134)), paint_metal=0.25, paint_rough=0.38, interior_color=(0.07, 0.06, 0.05),
    dlo_rear=lambda Z, c_s: np.full_like(Z, -2.18), top_off=0.055, a_off=0.075,
    pillars=[(0.05, 0.035, -0.05), (-1.05, 0.045, 0.0)], b_s=0.05, b_slant=-0.05, fd0=0.90,
    rd1=lambda Z, c_s: np.full_like(Z, -1.03), sill=0.45,
    ws_dom=0.35, bl_dom=-2.25, bl_zlo=1.20, bl_ztop=1.66, bl_side=0.11, dlo_bot=0.04,
    hood=(1.13, 0.72, HL[3] + 0.012), lid=(-2.27, 0.76, 0.62), rear_dom=0.55,
    head=HL, corner=(HL[1] + 0.012, 2.0, HL[2], HL[3]), corner_s=0.58,
    grille=(0.34, 0.865, 0.97), grille_bars=3, grille_sur_mat='chrome', lower_intake=(0.50, 0.44, 0.56),
    tail=(0.68, 0.82, 1.22), tail_s=-2.24, ws_ztop=1.655, tail_panel=False, reverse=(0.70, 0.80, 0.83, 0.90), rplate=0.98,
    handles=[0.17, -0.91], handle_z=BELT - 0.08, markers=((S_FA + 0.80, 0.86), (S_RA - 0.80, 0.90)), fuel=(S_RA - 0.45, BELT - 0.15),
    rub=(lambda s: np.full_like(s, 0.70), 0.022), clad=lambda s: np.full_like(s, 0.60), arch_lip=0.04,
    roof_rails=(0.60, 0.25, -2.15, 0.05), cross_bars=[-0.5, -1.6], rear_wiper=1.28, mirror_scale=1.1,
    exhaust=(0.45, S_RA - 0.85, 0.40),
    interior=dict(seat_s=0.15, seat_x=0.38, floor=0.48, dash_s=0.95, dash_z=1.08, dash_w=0.74, wheel_s=0.62, hip_z=0.72,
                  seat_h=0.64, rear_seats=True, rear_s=-0.75, cabin_bounds=((-0.82, -2.25, 0.48), (0.82, 1.05, 1.72)),
                  glass_band=(BELT + 0.02, 1.68), shell_target=1600),
    wheel=dict(type='alloy', r_cover=0.19, a_face=0.07,
               alloy=dict(r_lip=0.205, r_barrel=0.182, width=0.20, spokes=5, split=0.0, a_face=0.075, dish=0.022,
                          spoke_depth=0.026, spoke_w0=0.034, spoke_w1=0.026)),
    wheel_target=1500, tyre_seg=30, rim_color=(0.62, 0.63, 0.65), rim_rough=0.3,
)

if __name__ == '__main__':
    car90.build(C, OUT)
