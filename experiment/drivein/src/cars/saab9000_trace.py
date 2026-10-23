"""Side-profile trace of the hero Saab 9000 Aero (CS body) from a straight driver-side photo (reference 08, 2048x1472,
director's year-correct set; red 1995 Aero, hatch open). Pixel points were read off zoomed, gridded crops.

Camera: rims are near-circular (axis ratio 0.99), hub to hub 1170 px = 2.672 m -> 437.9 px/m at the near wheel-face
plane. A level pinhole camera ~9.4 m from that plane, principal point (1240, 797) px, estimated from the far-side
tyres seen under the car; a 0.36 deg roll (hub line) is removed. Each curve carries `delta`, how far beyond the
wheel-face plane the traced edge lies (roof silhouette ~0.35 m inboard, glass ~0.12 m, door skin ~0), which corrects
its perspective scale. Model frame: s forward, z up, metres; the real car is 4761 mm long, so the traced overhangs
(0.995 / 1.043 m) are stretched 2.5 % to 1.020 / 1.069 m. Axles: S_FA = 1.3605, S_RA = -1.3115 (nose at +2.3805).
"""
import numpy as np
K = 437.9
HUB_F = (388.2, 900.4); HUB_R = (1558.2, 907.7)
ROLL = np.arctan2(HUB_R[1] - HUB_F[1], HUB_R[0] - HUB_F[0])
D = 9.4
XVP, YH = 1240.0, 797.0
WB = 2.672
OVH = 1.0251                      # overhang stretch to the real 4761 mm length
S_FA = 2.3805 - 0.995 * OVH       # 1.3605
S_RA = S_FA - WB
CAM = dict(K=K, D=D, XVP=XVP, YH=YH, HUB_F=HUB_F, ROLL=ROLL)

def derot(x, y):
    c, s = np.cos(-ROLL), np.sin(-ROLL)
    dx, dy = np.asarray(x, float) - HUB_F[0], np.asarray(y, float) - HUB_F[1]
    return HUB_F[0] + c * dx - s * dy, HUB_F[1] + s * dx + c * dy

def rel(x, y, delta=0.0, z_hub=0.316):
    """px -> (s relative to the front axle, z) for a point lying delta m beyond the wheel-face plane."""
    x, y = derot(x, y)
    xv, yh = derot(XVP, YH)
    f = 1 + delta / D
    s_vp = -(xv - HUB_F[0]) / K
    z_h = z_hub - (yh - HUB_F[1]) / K
    return s_vp - (x - xv) * f / K, z_h - (y - yh) * f / K

def absolute(s_rel):
    s_rel = np.asarray(s_rel, float)
    s = np.where(s_rel > 0, s_rel * OVH, np.where(s_rel < -WB, -WB + (s_rel + WB) * OVH, s_rel))
    return S_FA + s

T = dict(
    hood=([(80, 735), (100, 722), (150, 700), (200, 687), (250, 677), (300, 670), (350, 662), (400, 655), (450, 647), (500, 638), (560, 624), (610, 619)], 0.15),
    ascreen=([(630, 606), (650, 590), (700, 560), (750, 527), (800, 495), (850, 462), (880, 455)], 0.25),
    roof=([(880, 455), (1000, 450), (1100, 447), (1200, 446), (1300, 445), (1380, 445), (1460, 450)], 0.35),
    hatch=([(1480, 465), (1500, 475), (1600, 527), (1700, 570), (1730, 580), (1750, 587), (1850, 594), (1920, 597)], 0.25),
    tail=([(1925, 600), (1932, 680), (1937, 780), (1980, 790), (1980, 830), (1970, 890), (1960, 907), (1900, 925), (1700, 925)], 0.45),
    nose=([(78, 735), (62, 750), (58, 795), (12, 805), (12, 835), (25, 870), (35, 890), (55, 930), (100, 942), (240, 946)], 0.45),
    sill=([(612, 942), (1000, 945), (1390, 945)], 0.0),
    dlo_f=([(665, 640), (850, 470), (1095, 460), (1052, 630)], 0.12),
    dlo_r=([(1110, 627), (1135, 460), (1350, 462), (1485, 612), (1480, 620)], 0.12),
    quarter_div=([(1345, 462), (1345, 620)], 0.12),
    shut_f=([(620, 625), (612, 900)], 0.0),
    shut_b=([(1075, 630), (1065, 895)], 0.0),
    shut_r=([(1380, 445), (1515, 605), (1515, 620), (1490, 715), (1415, 770), (1390, 820), (1385, 895)], 0.0),
    rub_door_f=([(612, 800), (612, 820)], 0.0), rub_door_r=([(1385, 792), (1385, 815)], 0.0),
    rub_fb=([(12, 802), (12, 835), (245, 802), (245, 835)], 0.0),
    rub_rb=([(1695, 790), (1695, 815), (1980, 790), (1980, 815)], 0.0),
    handle_f=([(960, 660), (1030, 680)], 0.0), handle_r=([(1395, 651), (1500, 669)], 0.0),
    marker=([(550, 772), (578, 784)], 0.0),
    taillamp_side=([(1880, 620), (1935, 692)], 0.3),
    lamp_side=([(60, 745), (118, 792)], 0.2),
    mirror=([(690, 582), (735, 625)], 0.0),
)

def traced():
    """name -> (n,2) array of absolute (s, z) metres."""
    out = {}
    for k, (pts, d) in T.items():
        P = np.array([rel(x, y, d) for x, y in pts])
        out[k] = np.c_[absolute(P[:, 0]), P[:, 1]]
    return out

if __name__ == '__main__':
    for k, v in traced().items():
        print(k, np.round(v, 3).tolist())
