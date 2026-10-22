"""Projection booth on tall timber legs (glTF coords, origin on the ground under the cabin centre, port faces +Z).
Board-and-batten cabin, tin shed roof with a lamphouse vent, one projection port (node `lens` at the port centre,
8.5 m above the origin), a door on the -X side opening onto a railed landing, and a wooden ladder down to the ground."""
import numpy as np
import geo
from geo import box, cyl, sweep, hexbolt, p_rect, nrm, CUR, SOURCES, PERCH

FL = 7.45                       # cabin floor (top of deck)
PORT = np.array([0.0, 8.5, 1.10])
CX, CZ = 1.2, 1.1               # cabin half sizes (outer sheathing planes)
YF, YB = 9.95, 9.62             # wall tops front / back
W, PW, ST, CO = 'wood_old', 'wood_painted', 'steel_weathered', 'concrete'


def top_at(z):
    return YB + (YF - YB) * (z + CZ) / (2 * CZ)


def prism(bname, poly, a0, a1, axis):
    """Extrude a 2D polygon (CCW) along axis 'x' (poly in z,y) or 'z' (poly in x,y) from a0 to a1."""
    poly = np.asarray(poly, float)
    m = len(poly)
    def P(u, v, a):
        return (a, v, u) if axis == 'x' else (u, v, a)
    V = [P(u, v, a0) for u, v in poly] + [P(u, v, a1) for u, v in poly]
    F = [list(range(m))[::-1], [m + j for j in range(m)]]
    for j in range(m):
        k = (j + 1) % m
        F.append([j, k, m + k, m + j])
    geo.bucket(bname).add(np.array(V), F, axis=(0, 1, 0))


def corrugated(bname, x0, x1, p_back, p_front, period=0.076, amp=0.009, t=0.004, dent=None):
    """Corrugated sheet spanning x0..x1, straight ribs running from p_back to p_front (both (y, z))."""
    n = int((x1 - x0) / period * 6) + 1
    xs = np.linspace(x0, x1, n)
    off = amp * np.sin((xs - x0) / period * 2 * np.pi)
    rows = 5
    V = []
    for side in (0, 1):
        for r in range(rows):
            s = r / (rows - 1)
            y = p_back[0] + (p_front[0] - p_back[0]) * s
            z = p_back[1] + (p_front[1] - p_back[1]) * s
            sag = -0.012 * np.sin(np.pi * s) * (1 + 0.5 * np.sin(xs * 3.1))
            if dent is not None:
                sag = sag - dent[2] * np.exp(-((xs - dent[0]) / 0.25) ** 2 - ((s - dent[1]) / 0.15) ** 2)
            V.append(np.c_[xs, y + off + sag - side * t, np.full(n, z)])
    V = np.concatenate(V)
    F = []
    for side in (0, 1):
        base = side * rows * n
        for r in range(rows - 1):
            for i in range(n - 1):
                a = base + r * n + i
                q = [a, a + 1, a + n + 1, a + n]
                F.append(q[::-1] if side == 0 else q)
    b2 = rows * n
    for r in range(rows - 1):           # side edges
        for i in (0, n - 1):
            a = r * n + i
            F.append([a, a + n, b2 + a + n, b2 + a])
    for r in (0, rows - 1):
        for i in range(n - 1):
            a = r * n + i
            F.append([a, a + 1, b2 + a + 1, b2 + a])
    geo.bucket(bname).add(V, F, axis=(p_front[1] - p_back[1]) * np.array([0, 0, 1.0]) + np.array([0, p_front[0] - p_back[0], 0]))


def wall_boards(bname, axis, plane, span, holes, top_fn, y0=FL - 0.05, out=1):
    """Board-and-batten wall: sheathing (in pieces around holes) + battens every 0.3 m.
    axis 'z': wall in x-y at z=plane (outer face), 'x': wall in z-y at x=plane."""
    a0, a1 = span
    th = 0.025
    pl0, pl1 = (plane - th * out, plane) if out > 0 else (plane, plane + th)
    # sheathing: vertical strips split at hole edges
    cuts = sorted(set([a0, a1] + [h[0] for h in holes] + [h[1] for h in holes]))
    for c0, c1 in zip(cuts[:-1], cuts[1:]):
        ym = (c0 + c1) / 2
        top0, top1 = top_fn(c0), top_fn(c1)
        segs = [(y0, None)]
        hs = [h for h in holes if h[0] <= c0 + 1e-6 and h[1] >= c1 - 1e-6]
        ys = [y0]
        for h in sorted(hs, key=lambda h: h[2]):
            ys += [h[2], h[3]]
        ys += [None]
        for k in range(0, len(ys), 2):
            yb, yt = ys[k], ys[k + 1]
            if yt is None:
                poly = [(c0, yb), (c1, yb), (c1, top1), (c0, top0)]
            else:
                poly = [(c0, yb), (c1, yb), (c1, yt), (c0, yt)]
            prism(bname, poly, pl0, pl1, 'z' if axis == 'z' else 'x')
    # battens
    bo0, bo1 = (plane, plane + 0.02 * out) if out > 0 else (plane - 0.02, plane)
    for a in np.arange(a0 + 0.15, a1 - 0.05, 0.30):
        lo_, hi_ = a - 0.03, a + 0.03
        hs = [h for h in holes if h[0] - 0.03 < a < h[1] + 0.03]
        ys = [y0]
        for h in sorted(hs, key=lambda h: h[2]):
            ys += [h[2] - 0.0, h[3] + 0.0]
        ys += [None]
        for k in range(0, len(ys), 2):
            yb, yt = ys[k], ys[k + 1]
            t0, t1 = top_fn(lo_) - 0.02, top_fn(hi_) - 0.02
            poly = [(lo_, yb), (hi_, yb), (hi_, yt if yt is not None else t1), (lo_, yt if yt is not None else t0)]
            prism(bname, poly, min(bo0, bo1), max(bo0, bo1), 'z' if axis == 'z' else 'x')


def build(seed=5):
    rs = np.random.default_rng(seed)
    geo.B.clear(); SOURCES.clear(); PERCH.clear()
    # ---------------- legs, footings, bracing
    legs = [((-1.45, -1.30), (-1.10, -1.00)), ((1.45, -1.30), (1.10, -1.00)), ((-1.45, 1.30), (-1.10, 1.00)), ((1.45, 1.30), (1.10, 1.00)),
            ((-2.15, -1.05), (-2.10, -1.00)), ((-2.15, 1.05), (-2.10, 1.00))]
    tops = []
    for (bx, bz), (tx, tz) in legs:
        CUR['k'] = 0.35
        a = np.array([bx, 0.30, bz]); b = np.array([tx, FL - 0.25, tz])
        sweep(W, p_rect(0.20, 0.20), [a, b], up=(1, 0, 0))
        tops.append(b)
        CUR['k'] = 0
        box(CO, (bx, 0.05, bz), (0.50, 0.50, 0.50))
        CUR['k'] = 1.0
        for sx in (-1, 1):
            box(ST, (bx + sx * 0.108, 0.48, bz), (0.012, 0.36, 0.20))
            hexbolt(ST, (bx + sx * 0.114, 0.48, bz), (sx, 0, 0), r=0.010, head=0.01, src=0.8)
        CUR['k'] = 0
    def legpos(i, y):
        (bx, bz), (tx, tz) = legs[i]
        t = (y - 0.3) / (FL - 0.25 - 0.3)
        return np.array([bx + (tx - bx) * t, y, bz + (tz - bz) * t])
    faces = [(0, 1), (2, 3), (0, 2), (1, 3), (4, 5), (4, 0), (5, 2)]
    for (i, j) in faces:
        for y in (2.4, 4.85):
            a, b = legpos(i, y), legpos(j, y)
            d = nrm(b - a); n_out = np.cross(d, (0, 1, 0));
            sweep(W, p_rect(0.05, 0.19), [a - d * 0.12, b + d * 0.12], up=(0, 1, 0))
            hexbolt(W, a + np.array([0, 0, 0]) + (0, 0.0, 0), (0, 0, 1) if abs(d[0]) > 0.5 else (1, 0, 0), r=0.012, src=0.9)
        for (y0, y1) in ((0.5, 2.4), (2.4, 4.85), (4.85, FL - 0.35)):
            if (i, j) in ((4, 0), (5, 2)) and y0 < 1:
                continue
            a, b = legpos(i, y0), legpos(j, y1)
            sweep(W, p_rect(0.045, 0.14), [a, b], up=(0, 1, 0))
            a, b = legpos(j, y0), legpos(i, y1)
            if (i + j + int(y0)) % 2 == 0:
                sweep(W, p_rect(0.045, 0.14), [a, b], up=(0, 1, 0))
    # ---------------- floor framing and deck (cabin + landing on -X)
    for z in (-1.0, 1.0):
        box(W, (-0.45, FL - 0.18, z), (3.6, 0.24, 0.16))
    for x in np.arange(-2.15, 1.3, 0.4):
        box(W, (x, FL - 0.14, 0), (0.06, 0.16, 2.3))
    for i, z in enumerate(np.arange(-1.22, 1.24, 0.145)):
        L0, L1 = -2.28, 1.33
        if i == 6:
            L0 = -2.0
        box(W, ((L0 + L1) / 2, FL - 0.025 + rs.normal(0, 0.002), z + 0.07), (L1 - L0 - rs.uniform(0, 0.05), 0.04, 0.135), rotX=rs.normal(0, 0.006))
    # landing railing (gap for the ladder at z -0.3..0.3)
    for (x, z) in ((-2.22, -1.18), (-2.22, -0.32), (-2.22, 0.32), (-2.22, 1.18), (-1.3, -1.18), (-1.3, 1.18)):
        box(W, (x, FL + 0.52, z), (0.07, 1.05, 0.07))
    for hy in (0.5, 1.0):
        box(W, (-2.22, FL + hy, -0.75), (0.045, 0.09, 0.86))
        box(W, (-2.22, FL + hy, 0.75), (0.045, 0.09, 0.86))
        box(W, (-1.76, FL + hy, -1.18), (0.92, 0.09, 0.045))
        box(W, (-1.76, FL + hy, 1.18), (0.92, 0.09, 0.045))
    PERCH.append((np.array([-2.22, FL + 1.05, -0.75]), 0.4, 0.8))
    # ---------------- ladder (timber rails, rungs) leaning on the landing
    base = np.array([-3.25, 0.0, 0]); topp = np.array([-2.32, FL + 0.95, 0])
    for z in (-0.24, 0.24):
        sweep(W, p_rect(0.045, 0.10), [base + (0, 0, z), topp + (0, 0, z)], up=(1, 0, 0))
    d = topp - base
    for t in np.arange(0.3, FL, 0.3) / d[1]:
        p = base + d * t
        if p[1] > FL + 0.5:
            break
        box(W, (p[0] + 0.03, p[1], 0), (0.05, 0.035, 0.46))
    # ---------------- cabin walls (painted board and batten)
    CUR['k'] = 1.0
    port_hole = (-0.27, 0.27, PORT[1] - 0.20, PORT[1] + 0.20)
    wall_boards(PW, 'z', CZ, (-CX, CX), [port_hole], lambda a: YF)                 # front (+Z)
    wall_boards(PW, 'z', -CZ, (-CX, CX), [], lambda a: YB, out=-1)                 # back
    door = (-0.60, 0.25, FL, FL + 1.95)
    wall_boards(PW, 'x', -CX, (-CZ, CZ), [door], top_at, out=-1)                    # door side (-X)
    side_win = (-0.45, 0.25, FL + 1.05, FL + 1.55)
    wall_boards(PW, 'x', CX, (-CZ, CZ), [side_win], top_at)                         # +X with a small window
    # corner boards and trims
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(PW, (sx * (CX + 0.012), (FL + top_at(sz * CZ)) / 2, sz * (CZ + 0.012)), (0.11, top_at(sz * CZ) - FL + 0.05, 0.11))
    # port frame and sill
    px0, px1, py0, py1 = port_hole
    for (c, s) in (((0, py1 + 0.045, CZ + 0.03), (0.66, 0.09, 0.05)), ((0, py0 - 0.05, CZ + 0.05), (0.70, 0.06, 0.12)),
                   ((px0 - 0.045, PORT[1], CZ + 0.03), (0.09, 0.50, 0.05)), ((px1 + 0.045, PORT[1], CZ + 0.03), (0.09, 0.50, 0.05))):
        box(PW, c, s)
    # side window frame
    for (c, s) in (((CX + 0.03, side_win[3] + 0.04, -0.1), (0.05, 0.08, 0.84)), ((CX + 0.05, side_win[2] - 0.04, -0.1), (0.10, 0.06, 0.86)),
                   ((CX + 0.03, (side_win[2] + side_win[3]) / 2, side_win[0] - 0.04), (0.05, 0.58, 0.08)),
                   ((CX + 0.03, (side_win[2] + side_win[3]) / 2, side_win[1] + 0.04), (0.05, 0.58, 0.08))):
        box(PW, c, s)
    # door: boards + Z brace
    dz0, dz1, dy0, dy1 = door
    for zz in np.arange(dz0 + 0.07, dz1, 0.14):
        box(PW, (-CX - 0.03, (dy0 + dy1) / 2 + 0.01, zz), (0.03, dy1 - dy0 - 0.03, 0.135))
    for yy in (dy0 + 0.25, dy1 - 0.25):
        box(PW, (-CX - 0.06, yy, (dz0 + dz1) / 2), (0.025, 0.12, dz1 - dz0 - 0.06))
    sweep(PW, p_rect(0.025, 0.11), [(-CX - 0.06, dy0 + 0.3, dz0 + 0.06), (-CX - 0.06, dy1 - 0.3, dz1 - 0.06)], up=(1, 0, 0))
    CUR['k'] = 1.0
    for yy in (dy0 + 0.25, dy1 - 0.25):
        box(ST, (-CX - 0.08, yy, dz1 - 0.2), (0.008, 0.05, 0.42))
        hexbolt(ST, (-CX - 0.084, yy, dz1 - 0.1), (-1, 0, 0), r=0.008, head=0.006, src=1.0)
    cyl(ST, (-CX - 0.09, FL + 1.0, dz0 + 0.1), (-CX - 0.16, FL + 1.0, dz0 + 0.1), 0.012, n=6)
    box(ST, (-CX - 0.075, FL + 1.0, dz0 + 0.1), (0.01, 0.12, 0.06))
    # ---------------- rafters, roof, fascia, vent stack
    CUR['k'] = 0
    for x in (-1.25, -0.62, 0.0, 0.62, 1.25):
        sweep(W, p_rect(0.05, 0.14), [(x, YB + 0.07, -CZ - 0.32), (x, YF + 0.07, CZ + 0.30)], up=(0, 1, 0))
    CUR['k'] = 1.0
    sl = (YF - YB) / (2 * CZ)
    yb_r = YB + 0.14 - 0.30 * sl; yf_r = YF + 0.15 + 0.28 * sl
    for (x0, x1) in ((-1.42, 0.06), (-0.02, 1.42)):
        corrugated(ST, x0, x1, (yb_r, -CZ - 0.34), (yf_r, CZ + 0.32), dent=(0.5, 0.6, 0.02) if x0 > 0 else None)
    box(PW, (0, yf_r - 0.08, CZ + 0.33), (2.9, 0.16, 0.025))            # fascia
    vx, vz = 0.55, -0.35
    vy = YB + (YF - YB) * (vz + CZ) / (2 * CZ) + 0.18
    cyl(ST, (vx, vy - 0.1, vz), (vx, vy + 0.95, vz), 0.09, n=12)
    cyl(ST, (vx, vy + 0.95, vz), (vx, vy + 1.08, vz), 0.20, 0.03, n=12)
    cyl(ST, (vx, vy - 0.02, vz), (vx, vy + 0.05, vz), 0.16, 0.10, n=12)
    PERCH.append((np.array([vx, vy + 1.08, vz]), 0.3, 0.6))
    # conduit down the front-right leg + weatherhead
    a = legpos(3, 0.2); b = legpos(3, FL - 0.3)
    cyl(ST, a + (0.13, 0, 0.0), b + (0.13, 0, 0.0), 0.016, n=6)
    cyl(ST, b + (0.13, 0, 0), np.array([CX + 0.04, FL + 0.6, 0.8]), 0.016, n=6)
    box(ST, (CX + 0.06, FL + 0.75, 0.8), (0.08, 0.24, 0.18))
    # ---------------- projector inside (dark enamel), lens barrel to the port
    box(ST, (0, FL + 0.35, 0.25), (0.30, 0.70, 0.30))
    box(ST, (0, PORT[1] - 0.02, 0.35), (0.34, 0.40, 0.55))
    box(ST, (0, PORT[1] + 0.05, -0.15), (0.40, 0.55, 0.50))            # lamphouse
    cyl(ST, (0, PORT[1], 0.62), (0, PORT[1], 0.98), 0.055, n=12)
    for yy, zz in ((PORT[1] + 0.55, 0.45), (PORT[1] + 0.45, -0.05)):
        cyl(ST, (-0.03, yy, zz), (0.03, yy, zz), 0.30, n=16)
    CUR['k'] = 0
    # glass panes (port, side window)
    geo.bucket('glass').add(np.array([[px0, py0, CZ - 0.012], [px1, py0, CZ - 0.012], [px1, py1, CZ - 0.012], [px0, py1, CZ - 0.012]]), [[0, 1, 2, 3]])
    z0, z1, y0, y1 = side_win
    geo.bucket('glass').add(np.array([[CX - 0.012, y0, z1], [CX - 0.012, y0, z0], [CX - 0.012, y1, z0], [CX - 0.012, y1, z1]]), [[0, 1, 2, 3]])
    # dark interior box (so the port and window read as a dim room, not see-through)
    geo.bucket('interior').add(*_inner_box())
    return geo.B


def _inner_box():
    x, z = CX - 0.03, CZ - 0.03
    y0, y1 = FL + 0.002, YB - 0.05
    V = np.array([[-x, y0, -z], [x, y0, -z], [x, y0, z], [-x, y0, z], [-x, y1, -z], [x, y1, -z], [x, y1, z], [-x, y1, z]])
    F = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]   # facing inward
    return V, F


if __name__ == '__main__':
    Bk = build()
    tot = 0
    for k, b in Bk.items():
        V, F, _ = b.arrays()
        t = sum(len(f) - 2 for f in F)
        tot += t
        print(f'{k:16s} verts {len(V):7d} tris {t:7d}  bbox {V.min(0).round(2)} {V.max(0).round(2)}')
    print('total tris', tot)
