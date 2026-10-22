"""Drive-in screen structure (pure numpy, glTF coords, metres, world placement: origin at lot zero below the face
centre, face plane z = 0 facing +Z). The HTML slide IS the screen face: 22.00 x 12.67 m, r 0.43, centre y 12.34.
Everything here lives behind z = -0.15 inside the face rectangle (check_front_clear) and nothing in front of z = 0
projects into the face from the fixed camera (check_sightline)."""
import numpy as np
import geo
from geo import box, cyl, sweep, hexbolt, p_rect, p_circle, nrm, CUR, SOURCES, PERCH

FW, FH, FR, FCY = 22.00, 12.67, 0.43, 12.34
FX = FW / 2
FY0, FY1 = FCY - FH / 2, FCY + FH / 2          # 6.005, 18.675
GY = 2.7                                       # lot height at the screen
PZ = -0.20                                     # panel front
CAM = np.array([-12.54, 2.16, 40.45])
PX = [-10.8, -7.2, -3.6, 0.0, 3.6, 7.2, 10.8]
ZF, ZB = -0.55, -2.15                          # front / back post rows (centres)
FOOT = GY + 0.30                               # top of the concrete footings
W, PW, ST, CO = 'wood_old', 'wood_painted', 'steel_weathered', 'concrete'


def rrect(w, h, r, n=8, inset=0.0):
    w, h, r = w / 2 - inset, h / 2 - inset, max(r - inset, 0.01)
    pts = []
    for cx, cy, a0 in ((w - r, -h + r, -np.pi / 2), (w - r, h - r, 0), (-w + r, h - r, np.pi / 2), (-w + r, -h + r, np.pi)):
        for i in range(n + 1):
            a = a0 + np.pi / 2 * i / n
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    return np.array(pts)


def in_face(x, y, pad=0.0):
    """Inside the rounded face rectangle (vectorised)."""
    w, h, r = FX + pad, FH / 2 + pad, FR + pad
    dx = np.abs(x) - (w - r); dy = np.abs(y - FCY) - (h - r)
    inside_box = (np.abs(x) <= w) & (np.abs(y - FCY) <= h)
    corner = (dx > 0) & (dy > 0)
    return inside_box & (~corner | (dx * dx + dy * dy <= r * r))


def panel():
    """Dark weathered face panel, exactly the slide's shape, front at z = -0.20 with a rounded/chamfered rim."""
    CUR['axis'] = (1, 0, 0); CUR['k'] = 0
    rings = [(0.030, PZ), (0.008, PZ - 0.006), (0.0, PZ - 0.022), (0.0, PZ - 0.060), (0.020, PZ - 0.080)]
    R = []
    for inset, z in rings:
        o = rrect(FW, FH, FR, 8, inset)
        R.append(np.c_[o[:, 0], o[:, 1] + FCY, np.full(len(o), z)])
    m = len(R[0])
    V = np.concatenate(R)
    F = []
    for i in range(len(R) - 1):
        for j in range(m):
            k = (j + 1) % m
            F.append([i * m + j, (i + 1) * m + j, (i + 1) * m + k, i * m + k])
    F.append(list(range(m)))                                   # front (CCW seen from +Z)
    F.append([(len(R) - 1) * m + j for j in range(m)][::-1])   # back
    geo.bucket('screen_panel').add(V, F)


def build(seed=7):
    rs = np.random.default_rng(seed)
    geo.B.clear(); SOURCES.clear(); PERCH.clear()
    panel()
    # ---------------- posts (creosoted 8x12 timbers) on concrete footings with steel saddles
    for x in PX:
        for z in (ZF, ZB):
            CUR['k'] = 0.35
            top = 18.55 if z == ZF else 18.58
            for (ya, yb) in ((FOOT, 6.45), (6.45, top)):         # split so the seen part gets the dense atlas
                box(W, (x, (ya + yb) / 2, z), (0.24, yb - ya, 0.30))
            CUR['k'] = 0
            box(CO, (x, GY + 0.05, z), (0.62, 0.50, 0.66))
            box(CO, (x, GY + 0.27, z), (0.56, 0.06, 0.60))
            CUR['k'] = 1.0
            for sx in (-1, 1):
                box(ST, (x + sx * 0.128, FOOT + 0.22, z), (0.012, 0.44, 0.26))
                for yy in (FOOT + 0.12, FOOT + 0.34):
                    hexbolt(ST, (x + sx * 0.134, yy, z), (sx, 0, 0), r=0.011, head=0.012, src=0.8)
            box(ST, (x, FOOT + 0.006, z), (0.30, 0.012, 0.36))
        # raked buttress strut behind the back row, on its own footing
        CUR['k'] = 0.35
        a = np.array([x, 15.6, ZB - 0.16]); b = np.array([x, FOOT, -8.0])
        mid = b + (a - b) * (6.45 - FOOT) / (a[1] - FOOT)
        sweep(W, p_rect(0.22, 0.26), [b, mid], up=(1, 0, 0))
        sweep(W, p_rect(0.22, 0.26), [mid, a], up=(1, 0, 0))
        CUR['k'] = 0
        box(CO, (x, GY + 0.05, -8.0), (0.60, 0.50, 0.70))
        box(CO, (x, GY + 0.27, -8.0), (0.54, 0.06, 0.64))
        CUR['k'] = 1.0
        for sx in (-1, 1):
            box(ST, (x + sx * 0.118, FOOT + 0.2, -8.0 + 0.05), (0.012, 0.40, 0.30))
            hexbolt(ST, (x + sx * 0.124, FOOT + 0.2, -8.0 + 0.05), (sx, 0, 0), r=0.011, head=0.012, src=0.8)
        CUR['k'] = 0
        # horizontal ties strut <-> back post and an X in between
        for yy in (6.3, 10.2):
            t = (yy - FOOT) / (15.6 - FOOT)
            zz = -8.0 + t * (ZB - 0.16 + 8.0)
            box(W, (x + 0.135, yy, (ZB - 0.15 + zz) / 2), (0.05, 0.24, abs(zz - ZB) + 0.2))
            hexbolt(W, (x + 0.16, yy, ZB), (1, 0, 0), r=0.013, head=0.012, src=1.0)
        # side-plane ties front <-> back post (catwalk beams and top) and diagonal braces
        for yy in (5.30, 12.05, 18.35):
            box(W, (x + 0.145, yy, (ZF + ZB) / 2), (0.05, 0.25, ZF - ZB + 0.30))
            box(W, (x - 0.145, yy, (ZF + ZB) / 2), (0.05, 0.25, ZF - ZB + 0.30))
            for z in (ZF, ZB):
                hexbolt(W, (x + 0.17, yy, z), (1, 0, 0), r=0.013, head=0.012, src=1.0)
                hexbolt(W, (x - 0.17, yy, z), (-1, 0, 0), r=0.013, head=0.012, src=1.0)
        for (y0, y1, flip) in ((FOOT + 0.2, 5.15, 0), (5.45, 11.9, 1), (12.2, 18.2, 0)):
            za, zb = (ZF, ZB) if flip else (ZB, ZF)
            sweep(W, p_rect(0.05, 0.19), [(x + 0.145, y0, za), (x + 0.145, y1, zb)], up=(1, 0, 0))
    # ---------------- nailers behind the panel and girts for the back skin
    CUR['k'] = 0
    for yy in np.arange(6.25, 18.5, 1.22):
        box(W, (0, yy, -0.345), (21.9, 0.19, 0.10))
    for yy in np.arange(6.4, 18.5, 1.22):
        box(W, (0, yy, ZB - 0.20), (21.9, 0.19, 0.10))
    box(W, (0, 5.78, -0.42), (21.9, 0.30, 0.15))                       # sill under the face
    # ---------------- painted plywood back skin (board-and-batten seams), 30-40 years of weather
    CUR['k'] = 1.0
    zs = ZB - 0.255
    cols = 18
    for c in range(cols):
        x0 = -10.98 + c * 1.22
        yb = 5.95
        while yb < 18.6:
            hgt = min(2.44, 18.62 - yb)
            if c == 15 and 8.0 < yb < 11:
                hgt2 = hgt - 0.9              # a short replacement sheet with a gap strip above it
                box(PW, (x0 + 0.61, yb + hgt2 / 2, zs), (1.215, hgt2, 0.019), rotZ=0.004)
                box(PW, (x0 + 0.61, yb + hgt2 + 0.48, zs - 0.004), (1.215, 0.82, 0.019))
            else:
                warp = rs.normal(0, 0.003)
                box(PW, (x0 + 0.61, yb + hgt / 2, zs + rs.normal(0, 0.002)), (1.215, hgt - 0.006, 0.019), rotX=warp)
            yb += 2.44
        if c > 0:
            box(PW, (x0, 12.28, zs - 0.022), (0.075, 12.62, 0.022))       # batten over the seam
    for yy in (5.95 + 2.44 * i for i in range(1, 6)):
        box(PW, (0, yy, zs - 0.040), (21.96, 0.075, 0.018))
    box(PW, (0, 18.56, zs - 0.03), (22.0, 0.14, 0.035))                  # top trim board
    CUR['k'] = 0
    # ---------------- sheet-metal cap along the top and the side
    CUR['k'] = 1.0
    box(ST, (0, 18.615, (PZ - 0.09 + zs - 0.05) / 2), (22.06, 0.012, abs(zs - 0.05 - PZ + 0.09)))
    for xs in (-1, 1):
        box(ST, (xs * 11.0, 18.58, (PZ - 0.09 + zs) / 2), (0.012, 0.08, abs(zs - PZ + 0.09)))
    CUR['k'] = 0
    # ---------------- catwalks (decks between the post rows) with pipe railings on the rear side
    for yd, rail in ((5.55, True), (12.30, True)):
        nb = 9
        z0, z1 = ZF - 0.17, ZB + 0.17
        bw = (z0 - z1) / nb
        for i in range(nb):
            zc = z0 - bw * (i + 0.5)
            for s in range(len(PX) - 1):
                if yd < 6 and i == 4 and s == 2:
                    continue                                           # missing board
                xa, xb = PX[s] - 0.10, PX[s + 1] + 0.10
                if s == 0:
                    xa = -10.95
                if s == len(PX) - 2:
                    xb = 10.95
                box(W, ((xa + xb) / 2, yd - 0.02 + rs.normal(0, 0.003), zc), (xb - xa, 0.04, bw - 0.012), rotX=rs.normal(0, 0.01))
        CUR['k'] = 1.0
        for s in range(len(PX)):
            cyl(ST, (PX[s] + 0.0, yd, ZB + 0.25), (PX[s], yd + 1.05, ZB + 0.25), 0.024, n=8)
            hexbolt(ST, (PX[s], yd + 0.5, ZB + 0.15), (0, 0, -1), r=0.01, head=0.01, src=0.6)
        for hy in (0.55, 1.05):
            cyl(ST, (-10.95, yd + hy, ZB + 0.25), (10.95, yd + hy, ZB + 0.25), 0.024, n=8)
        box(ST, (0, yd + 0.08, ZB + 0.25), (21.9, 0.14, 0.006))                # toe plate
        CUR['k'] = 0
        for px in (-10.95, -6.0, 1.0, 9.0):
            PERCH.append((np.array([px, yd + 1.08, ZB + 0.25]), 0.35, 0.9))
    # ---------------- steel rod X-bracing (with turnbuckles) under the face and between the back posts
    CUR['k'] = 0.0
    for zr in (ZF + 0.165, ZB - 0.165):
        for s in range(len(PX) - 1):
            xa, xb = PX[s] + 0.12, PX[s + 1] - 0.12
            for (pa, pb) in (((xa, FOOT + 0.25), (xb, 5.05)), ((xa, 5.05), (xb, FOOT + 0.25))):
                a = np.array([pa[0], pa[1], zr]); b = np.array([pb[0], pb[1], zr])
                cyl(ST, a, b, 0.011, n=6)
                m = (a + b) / 2; d = nrm(b - a)
                cyl(ST, m - d * 0.12, m + d * 0.12, 0.022, n=6)
                for p in (a, b):
                    box(ST, p, (0.012, 0.16, 0.10))
    # ---------------- ladder with cage on the left flank (outside the face, x < -11)
    CUR['k'] = 0.0
    lx = -11.32
    zl0, zl1 = -1.10, -1.60
    for zz in (zl0, zl1):
        cyl(ST, (lx, GY, zz), (lx, 13.4, zz), 0.022, n=8)
    for yy in np.arange(GY + 0.30, 13.3, 0.30):
        cyl(ST, (lx, yy, zl0), (lx, yy, zl1), 0.012, n=6)
    for yy in (4.0, 7.0, 10.0, 13.0):
        for zz in (zl0, zl1):
            box(ST, (lx + 0.24, yy, zz), (0.42, 0.05, 0.012))
    zc = (zl0 + zl1) / 2
    cx = lambda a: lx - 0.06 - 0.70 * np.cos(a)
    cz = lambda a: zc + 0.40 * np.sin(a)
    for yy in np.arange(5.0, 13.4, 0.9):
        arc = [np.array([cx(a), yy, cz(a)]) for a in np.linspace(-np.pi / 2, np.pi / 2, 11)]
        sweep(ST, p_rect(0.008, 0.05), arc, up=(0, 1, 0), caps=True)
    for ang in (-1.0, -0.33, 0.33, 1.0):
        box(ST, (cx(ang), 9.2, cz(ang)), (0.05, 8.4, 0.008), rotY=-ang)
    PERCH.append((np.array([lx - 0.5, 13.0, -1.35]), 0.4, 0.7))
    # ---------------- light at the top left (old flood for the screen tower, dead)
    return geo.B


def split_visible(Bk, src, dst, vis_fn):
    """Move polygons of bucket src whose centroid fails vis_fn(c) into a new bucket dst (own, cheaper atlas)."""
    b = Bk[src]
    V, F, tags = b.arrays()
    A = np.asarray(b.attr)
    keep = [vis_fn(V[f].mean(0)) for f in F]
    for name, sel in ((src, True), (dst, False)):
        nb = geo.Bucket(name)
        idx = [i for i, k in enumerate(keep) if k == sel]
        used = sorted({v for i in idx for v in F[i]})
        remap = {v: j for j, v in enumerate(used)}
        nb.V = [V[used]]; nb.n = len(used)
        nb.F = [[remap[v] for v in F[i]] for i in idx]
        nb.tags = [int(tags[i]) for i in idx]
        nb.attr = [list(A[i]) for i in idx]
        Bk[name] = nb
    return Bk


def visible_from_camera(c):
    """Rough visibility class for atlas density: under the face, the left flank, or the outer rim of the structure."""
    return c[1] < 6.5 or c[0] < -10.3 or c[1] > 18.3


def check_front_clear(Bk, zlim=-0.15):
    """Violations: geometry at z > zlim inside the face rectangle (vertices and triangle samples)."""
    bad = []
    for name, b in Bk.items():
        V, F, _ = b.arrays()
        if not len(V):
            continue
        m = (V[:, 2] > zlim) & in_face(V[:, 0], V[:, 1], 0.0)
        # also sample along polygon edges / centroids (large polygons can cross without a vertex inside)
        S = []
        for f in F:
            P = V[f]
            if P[:, 2].max() <= zlim:
                continue
            c = P.mean(0)
            S.append(c)
            for i in range(len(f)):
                for t in (0.25, 0.5, 0.75):
                    S.append(P[i] * (1 - t) + P[(i + 1) % len(f)] * t)
        S = np.array(S) if S else np.zeros((0, 3))
        ms = (S[:, 2] > zlim) & in_face(S[:, 0], S[:, 1], 0.0) if len(S) else np.zeros(0, bool)
        if m.any() or ms.any():
            bad.append((name, int(m.sum() + ms.sum())))
    return bad


def check_sightline(Bk):
    """Anything in front of the slide plane (z > 0) must not project into the face from the camera."""
    bad = []
    for name, b in Bk.items():
        V, F, _ = b.arrays()
        if not len(V):
            continue
        Q = V[V[:, 2] > 0]
        if not len(Q):
            continue
        t = CAM[2] / (CAM[2] - Q[:, 2])
        pr = CAM + (Q - CAM) * t[:, None]
        m = in_face(pr[:, 0], pr[:, 1], 0.02)
        if m.any():
            bad.append((name, int(m.sum())))
    return bad


if __name__ == '__main__':
    Bk = build()
    tot = 0
    for k, b in Bk.items():
        V, F, _ = b.arrays()
        t = sum(len(f) - 2 for f in F)
        tot += t
        print(f'{k:16s} verts {len(V):7d} tris {t:7d}  bbox {V.min(0).round(2)} {V.max(0).round(2)}')
    print('total tris', tot, 'sources', len(SOURCES), 'perch', len(PERCH))
    print('front violations', check_front_clear(Bk), 'sightline', check_sightline(Bk))
