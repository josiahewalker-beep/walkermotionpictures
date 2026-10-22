"""Wooden utility pole (~5.2 m) with a single enamel barn-light shade on a gooseneck arm, photocell, conduit,
step pegs. Origin on the ground at the pole foot; the arm reaches toward +X. node `bulb` at the bulb.
flock .../heavy.lock python3 src/set/lamp_pole.py"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo
from geo import box, cyl, sweep, hexbolt, p_rect, p_circle, nrm, CUR, SOURCES, PERCH
import clib

H = 5.25
ARM_Y = 4.75
BULB = np.array([0.95, 4.38, 0.0])
W, ST = 'wood_old', 'steel_weathered'


def add_mesh(bname, m, axis=(0, 1, 0)):
    V, F, _ = m.arrays()
    geo.bucket(bname).add(V, F, axis=axis)


def build(seed=4):
    rs = np.random.default_rng(seed)
    geo.B.clear(); SOURCES.clear(); PERCH.clear()
    lean = np.array([-0.035, 0, 0.02])
    def pole_at(y):
        return np.array([0, y, 0]) + lean * y / H
    CUR['k'] = 0.55
    path = [pole_at(y) for y in np.linspace(-0.05, H, 9)]
    rr = np.linspace(0.135, 0.095, 9)
    sweep(W, p_circle(1.0, 14), path, up=(1, 0, 0), scale=list(rr))
    # pole top bevel cap (weathered end grain)
    cyl(W, pole_at(H), pole_at(H + 0.03), 0.095, 0.06, n=14)
    PERCH.append((pole_at(H + 0.03), 0.12, 1.0))
    CUR['k'] = 0.0
    # gooseneck arm: steel pipe out from a pole bracket, curving down to the shade
    CUR['k'] = 1.0
    base = pole_at(ARM_Y) + np.array([0.10, 0, 0])
    box(ST, base + (0.0, 0, 0), (0.02, 0.32, 0.12))
    for dy in (-0.11, 0.11):
        hexbolt(ST, base + (0.012, dy, 0), (1, 0, 0), r=0.010, head=0.012, src=1.0)
    t = np.linspace(0, 1, 12)
    arm = [base + np.array([0.02 + 0.80 * s, 0.10 * np.sin(np.pi * s * 0.9) - 0.0, 0]) for s in t[:8]]
    end = arm[-1]
    c = end + np.array([0.0, -0.13, 0])
    for a in np.linspace(np.pi / 2, -0.05, 6)[1:]:
        arm.append(c + np.array([0.13 * np.cos(a) * 1.0 + 0.0, 0.13 * np.sin(a), 0]) + np.array([0.0, 0, 0]))
    arm.append(np.array([BULB[0], BULB[1] + 0.20, 0]))
    arm = np.array(arm)
    sweep(ST, p_circle(0.021, 8), arm, up=(0, 0, 1))
    # support strap under the arm
    sweep(ST, p_rect(0.006, 0.03), [base + (0.01, -0.45, 0), base + (0.55, 0.04, 0)], up=(0, 0, 1))
    hexbolt(ST, base + (0.012, -0.45, 0), (1, 0, 0), r=0.009, head=0.01, src=1.0)
    # shade: enamel RLM dome (outside: green enamel, chipped; inside: white reflector)
    sh = np.array([BULB[0], BULB[1] - 0.02, 0])
    prof = [(0.028, 0.23), (0.032, 0.20), (0.05, 0.16), (0.10, 0.12), (0.16, 0.075), (0.205, 0.035), (0.235, 0.008), (0.245, 0.0)]
    outer = clib.lathe([(r, y) for r, y in prof], m=24, c=sh)
    add_mesh(ST, outer)
    inner = clib.flip(clib.lathe([(r - 0.004, y - 0.004) for r, y in prof[1:]], m=24, c=sh))
    V, F, UV = inner.arrays()
    geo.bucket('reflector').add(V, F)
    rim = clib.lathe([(0.245, 0.0), (0.249, -0.004), (0.241, -0.008), (0.236, -0.004)], m=24, c=sh)
    add_mesh(ST, rim)
    # socket + bulb
    cyl(ST, sh + (0, 0.17, 0), sh + (0, 0.11, 0), 0.03, 0.028, n=10)
    bulb = clib.sphere(BULB, 0.042, m=12, n=8, squash=(1, 1.2, 1)).merge(clib.lathe([(0.02, 0.05), (0.028, 0.08)], m=12, c=BULB))
    V, F, _ = bulb.arrays()
    geo.bucket('light_bulb').add(V, F)
    # photocell on the arm bracket
    pc = base + np.array([0.15, 0.10, 0])
    cyl(ST, pc, pc + (0, 0.06, 0), 0.03, 0.03, n=10)
    cyl(ST, pc + (0, 0.06, 0), pc + (0, 0.085, 0), 0.03, 0.02, n=10)
    # conduit down the pole (back side, -Z), weatherhead, junction box, straps
    zoff = np.array([0, 0, -0.125])
    for y0, y1 in ((0.0, ARM_Y + 0.25),):
        cyl(ST, pole_at(y0) + zoff, pole_at(y1) + zoff * 0.95, 0.017, n=6)
    cyl(ST, pole_at(ARM_Y + 0.25) + zoff * 0.95, pole_at(ARM_Y + 0.25) + zoff * 0.95 + (0.06, 0.06, 0), 0.03, 0.04, n=8)
    box(ST, pole_at(ARM_Y - 0.25) + (0.04, 0, -0.10), (0.12, 0.16, 0.08))
    box(ST, pole_at(1.3) + (0, 0, -0.16), (0.14, 0.2, 0.08))           # old disconnect box
    for y in np.arange(0.6, ARM_Y, 0.8):
        p = pole_at(y) + zoff
        box(ST, p, (0.07, 0.022, 0.012))
        SOURCES.append((p + (0, -0.012, 0), 0.8, 0.02, 0.35))
    # step pegs (lineman's steps) alternating sides from 2.4 m up
    for i, y in enumerate(np.arange(2.4, ARM_Y - 0.2, 0.42)):
        s = 1 if i % 2 else -1
        d = np.array([0.0, 0, s])
        p0 = pole_at(y) + d * 0.09
        cyl(ST, p0, p0 + d * 0.18 + (0, 0.025, 0), 0.010, n=6)
        cyl(ST, p0 + d * 0.18 + (0, 0.025, 0), p0 + d * 0.18 + (0, 0.06, 0), 0.010, n=6)
        SOURCES.append((p0, 0.9, 0.02, 0.4))
    # tag plate and nails (old pole number)
    box(ST, pole_at(1.75) + (0.0, 0, 0.125), (0.09, 0.05, 0.004))
    CUR['k'] = 0.0
    for k in range(10):                                            # old staples / nail heads from flyers
        y = rs.uniform(1.2, 2.2); a = rs.uniform(-1.2, 1.2)
        r = 0.135 - 0.04 * y / H
        p = pole_at(y) + np.array([np.sin(a) * r, 0, np.cos(a) * r])
        SOURCES.append((p, 0.6, 0.012, 0.25))
    return geo.B


if __name__ == '__main__':
    import pipe, setbuild
    from pipe import ROOT
    pipe.reset()
    Bk = build()
    for k, b in Bk.items():
        V, F, _ = b.arrays(); print(k, sum(len(f) - 2 for f in F))

    def extra(objs, root):
        pipe.empty('bulb', BULB, parent=root)

    setbuild.build(
        Bk,
        atlas={'wood_old': (512, 'wood', {'seed': 5}),
               'steel_weathered': (512, 'metal', {'seed': 25, 'paint_lo': (0.025, 0.06, 0.04), 'paint_hi': (0.05, 0.10, 0.065)})},
        tex_name='pole_tex', out_glb=f'{ROOT}/assets/lamp_pole.glb', sources=geo.SOURCES, perch=geo.PERCH, root_name='lamp_pole',
        plain={'reflector': (1.0, lambda: pipe.material('reflector', base=(0.72, 0.71, 0.66), rough=0.35, double=True)),
               'light_bulb': (1.0, lambda: pipe.material('light_bulb', base=(0.9, 0.8, 0.6), rough=0.2, emissive=(1.0, 0.62, 0.30), emissive_strength=4.0))},
        ground=0.0, ao_dist=0.5, ao_ground=(0, 0, 0, 10), extra=extra)
