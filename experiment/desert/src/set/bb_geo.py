"""Billboard geometry in glTF coordinates (metres, +Y up, face plane z = 0 facing +Z, origin on the ground below
the face centre). Parts are accumulated per material bucket as numpy vertex arrays + polygon index lists, and
converted to Blender (x, -z, y) only when the meshes are created.
Everything here is pure numpy so it can be unit-checked without Blender."""
import numpy as np

FACE_W, FACE_H, FACE_Y0 = 10.93, 4.28, 2.80
FX = FACE_W / 2
FY1 = FACE_Y0 + FACE_H
BORDER = 0.13
DECK_Y = 2.25            # top of catwalk grating
CW_Z1 = 0.90             # catwalk front edge
POLE_Z = -0.65
POLE_TOP = 3.35
PIER_TOP = 0.30
PLATE_T = 0.045


def nrm(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


class Bucket:
    def __init__(self, name):
        self.name = name
        self.V = []          # list of (n,3) arrays
        self.F = []          # list of lists of polygons (global indices assigned at merge)
        self.n = 0
        self.tags = []       # per polygon int tag (part id)

    def add(self, V, F, tag=0):
        V = np.asarray(V, float)
        self.V.append(V)
        self.F.extend([[i + self.n for i in f] for f in F])
        self.tags.extend([tag] * len(F))
        self.n += len(V)

    def arrays(self):
        return (np.concatenate(self.V) if self.V else np.zeros((0, 3))), self.F, np.array(self.tags, int)


B = {}
SOURCES = []          # rust-streak sources: (pos(3), strength, width m, length m)
PERCH = []            # bird perch points for droppings: (pos(3), radius m, density)


def bucket(name):
    if name not in B:
        B[name] = Bucket(name)
    return B[name]


# ---------------------------------------------------------------- profiles (a = side, b = up), closed CCW
def p_rect(w, h, ca=0.0, cb=0.0):
    return [(ca - w / 2, cb - h / 2), (ca + w / 2, cb - h / 2), (ca + w / 2, cb + h / 2), (ca - w / 2, cb + h / 2)]

def p_circle(r, n=12, phase=0.0):
    return [(r * np.cos(phase + 2 * np.pi * i / n), r * np.sin(phase + 2 * np.pi * i / n)) for i in range(n)]

def p_channel(d, w, t):
    """C channel: web along b (depth d), flanges of width w toward +a. Origin at the web centre."""
    h = d / 2
    return [(0, -h), (w, -h), (w, -h + t), (t, -h + t), (t, h - t), (w, h - t), (w, h), (0, h)]

def p_angle(l1, l2, t):
    """L angle: legs along +a (l1) and +b (l2), heel at origin."""
    return [(0, 0), (l1, 0), (l1, t), (t, t), (t, l2), (0, l2)]

def p_ibeam(d, bf, tw, tf):
    h, f, w = d / 2, bf / 2, tw / 2
    return [(-f, -h), (f, -h), (f, -h + tf), (w, -h + tf), (w, h - tf), (f, h - tf), (f, h), (-f, h), (-f, h - tf),
            (-w, h - tf), (-w, -h + tf), (-f, -h + tf)]


# ---------------------------------------------------------------- sweep
def frames(path, up):
    path = np.asarray(path, float)
    n = len(path)
    seg = nrm(np.diff(path, axis=0))
    T = np.zeros((n, 3))
    T[0], T[-1] = seg[0], seg[-1]
    for i in range(1, n - 1):
        T[i] = nrm(seg[i - 1] + seg[i])
    up = nrm(up)
    N = np.zeros((n, 3))
    u = up - np.dot(up, seg[0]) * seg[0]
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(seg[0], [1, 0, 0]) if abs(seg[0][0]) < 0.9 else np.cross(seg[0], [0, 0, 1])
    N[0] = nrm(u)
    for i in range(1, n):          # parallel transport along segments
        t0, t1 = seg[max(i - 1, 0)], seg[min(i, n - 2)]
        v = N[i - 1]
        ax = np.cross(t0, t1)
        s = np.linalg.norm(ax)
        if s > 1e-8:
            ax /= s
            ang = np.arctan2(s, np.dot(t0, t1))
            v = v * np.cos(ang) + np.cross(ax, v) * np.sin(ang) + ax * np.dot(ax, v) * (1 - np.cos(ang))
        N[i] = nrm(v - np.dot(v, seg[min(i, n - 2)]) * seg[min(i, n - 2)])
    return seg, N


def sweep(bname, profile, path, up=(0, 1, 0), caps=True, closed=False, tag=0, scale=None, twist=0.0):
    """Extrude a closed 2D profile along a polyline with mitred joints. scale: optional per-point scale list."""
    path = np.asarray(path, float)
    prof = np.asarray(profile, float)
    m, n = len(prof), len(path)
    if closed:
        path = np.vstack([path, path[:1]])
        n += 1
    seg, N = frames(path, up)
    rings = []
    for i in range(n):
        if closed and i == n - 1:
            break
        s = 1.0 if scale is None else scale[i]
        d_in = seg[i - 1] if i > 0 else (seg[-1] if closed else seg[0])
        d_out = seg[i] if i < len(seg) else (seg[0] if closed else seg[-1])
        Ni = N[i] if i < len(N) else N[0]
        ti = seg[min(i, len(seg) - 1)]
        Bv = nrm(np.cross(ti, Ni))
        Nv = nrm(np.cross(Bv, ti)) if True else Ni
        # build ring in the incoming segment frame then project onto the mitre plane
        Bin = nrm(np.cross(d_in, Ni)); Nin = nrm(np.cross(Bin, d_in))
        ca, sa = np.cos(twist * i), np.sin(twist * i)
        pa = prof[:, 0] * ca - prof[:, 1] * sa
        pb = prof[:, 0] * sa + prof[:, 1] * ca
        q = path[i] + s * (pa[:, None] * Bin + pb[:, None] * Nin)
        pn = nrm(d_in + d_out)
        denom = np.dot(d_in, pn)
        q = q + d_in[None, :] * (((path[i] - q) @ pn) / denom)[:, None]
        rings.append(q)
    V = np.concatenate(rings)
    F = []
    nr = len(rings)
    for i in range(nr - 1 + (1 if closed else 0)):
        a, b = i % nr, (i + 1) % nr
        for j in range(m):
            k = (j + 1) % m
            F.append([a * m + j, a * m + k, b * m + k, b * m + j])
    if caps and not closed:
        F.append(list(range(m))[::-1])
        F.append([(nr - 1) * m + j for j in range(m)])
    bucket(bname).add(V, F, tag)
    return V


def member(bname, profile, p0, p1, up=(0, 1, 0), tag=0):
    return sweep(bname, profile, [p0, p1], up, tag=tag)


def box(bname, c, size, tag=0, rotY=0.0, rotX=0.0, rotZ=0.0):
    """Axis-aligned box (optionally rotated about its centre: Z, then X, then Y)."""
    c = np.asarray(c, float); sx, sy, sz = np.asarray(size, float) / 2
    V = np.array([[-sx, -sy, -sz], [sx, -sy, -sz], [sx, sy, -sz], [-sx, sy, -sz],
                  [-sx, -sy, sz], [sx, -sy, sz], [sx, sy, sz], [-sx, sy, sz]])
    V = V @ rot(rotX, rotY, rotZ).T + c
    F = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
    bucket(bname).add(V, F, tag)
    return V


def rot(rx=0.0, ry=0.0, rz=0.0):
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


def cyl(bname, p0, p1, r0, r1=None, n=12, tag=0, caps=True, up=None):
    r1 = r0 if r1 is None else r1
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = nrm(p1 - p0)
    if up is None:
        up = (1, 0, 0) if abs(d[1]) > 0.9 else (0, 1, 0)
    return sweep(bname, p_circle(1.0, n), [p0, p1], up, caps=caps, tag=tag, scale=[r0, r1])


def hexbolt(bname, p, d, r=0.012, head=0.010, shank=0.0, tag=0, src=1.0):
    """Hex head (or nut) at p, axis d (pointing out of the surface)."""
    p, d = np.asarray(p, float), nrm(d)
    cyl(bname, p, p + d * head, r * 1.7, r * 1.6, n=6, tag=tag)
    if shank > 0:
        cyl(bname, p + d * head, p + d * (head + shank), r, r, n=6, tag=tag)
    if src:
        SOURCES.append((p, src, 0.012 + 0.01 * src, 0.15 + 0.35 * src))


# ---------------------------------------------------------------- the structure
def build(seed=3):
    rs = np.random.default_rng(seed)
    B.clear(); SOURCES.clear(); PERCH.clear()
    P = 'paint_peeling'; PR = 'steel_weathered_rear'; G = 'steel_weathered'; R = 'rust'

    # ---- face panels (behind z = 0, hidden by the slide from the front) ----
    zf0, zf1 = -0.012, -0.034
    npan = 9
    for i in range(npan):
        x0 = -FX + i * FACE_W / npan; x1 = x0 + FACE_W / npan
        box(PR, ((x0 + x1) / 2, FACE_Y0 + FACE_H / 2, (zf0 + zf1) / 2), (x1 - x0 - 0.004, FACE_H, zf0 - zf1), tag=1)
        # panel ribs on the back (hat sections)
        for xr in (x0 + 0.3, x1 - 0.3):
            member(PR, p_rect(0.05, 0.03), (xr, FACE_Y0, zf1 - 0.015), (xr, FY1, zf1 - 0.015), up=(0, 0, 1), tag=1)

    # ---- face frame (trim molding): channel opening inward, front lip on the border, outer wall, back lip ----
    zfr = -0.004
    prof = [(0.0, 0.0), (BORDER, 0.0), (BORDER, -0.20), (BORDER - 0.05, -0.20), (BORDER - 0.05, -0.194),
            (BORDER - 0.006, -0.194), (BORDER - 0.006, -0.006), (0.0, -0.006)]
    # a = outward from the face edge, b = z. Build the 4 sides as mitred closed sweep with profile in (outward, z).
    corners = [(-FX, FACE_Y0), (FX, FACE_Y0), (FX, FY1), (-FX, FY1)]
    # sweep a closed rectangle path; the profile's 'a' axis must point outward: use up=(0,0,1) and order CCW seen from +z
    path = [(x, y, zfr) for x, y in corners]
    prof_sw = [(-a, b) for a, b in prof]      # B = T x N points inward for CCW path → negate a for outward
    sweep(G, prof_sw[::-1], path, up=(0, 0, 1), closed=True, caps=False, tag=2)
    # staples / small bolts along the frame front lip (only on the border, outside the face rectangle)
    for k in range(70):
        side = rs.integers(4)
        t = rs.random()
        if side == 0: p = (-FX + t * FACE_W, FACE_Y0 - BORDER * rs.uniform(0.25, 0.75), zfr + 0.001)
        elif side == 1: p = (-FX + t * FACE_W, FY1 + BORDER * rs.uniform(0.25, 0.75), zfr + 0.001)
        elif side == 2: p = (-FX - BORDER * rs.uniform(0.25, 0.75), FACE_Y0 + t * FACE_H, zfr + 0.001)
        else: p = (FX + BORDER * rs.uniform(0.25, 0.75), FACE_Y0 + t * FACE_H, zfr + 0.001)
        SOURCES.append((np.array(p), 0.35, 0.006, 0.12))
    for x in np.linspace(-FX + 0.3, FX - 0.3, 12):
        hexbolt(R, (x, FACE_Y0 - BORDER * 0.5, zfr), (0, 0, 1), r=0.007, head=0.006, tag=3, src=0.8)
        hexbolt(R, (x, FY1 + BORDER * 0.5, zfr), (0, 0, 1), r=0.007, head=0.006, tag=3, src=0.8)
    for y in np.linspace(FACE_Y0 + 0.3, FY1 - 0.3, 5):
        for sx in (-1, 1):
            hexbolt(R, (sx * (FX + BORDER * 0.5), y, zfr), (0, 0, 1), r=0.007, head=0.006, tag=3, src=0.8)

    # ---- rear framing: vertical channels (extend below the face to carry the catwalk brackets) ----
    zv0 = zf1 - 0.03
    nv = 8
    VX = [-FX + 0.25 + i * (FACE_W - 0.5) / (nv - 1) for i in range(nv)]
    for x in VX:
        # channel web along z (depth 0.15), flanges along +x (0.05)
        sweep(PR, p_channel(0.15, 0.05, 0.007), [(x - 0.025, DECK_Y - 0.75, zv0 - 0.075), (x - 0.025, FY1 + 0.05, zv0 - 0.075)],
              up=(0, 0, 1), tag=4)
        # clip angles to the stringers
    # stringers (two horizontal channels behind the verticals)
    zs = zv0 - 0.15
    for ys in (FACE_Y0 + 0.95, FY1 - 0.75):
        sweep(PR, p_channel(0.20, 0.07, 0.008), [(-FX - 0.05, ys, zs - 0.035), (FX + 0.05, ys, zs - 0.035)], up=(0, 1, 0), tag=5)
        for x in VX:
            hexbolt(R, (x, ys + 0.05, zv0 - 0.15), (0, 0, 1), r=0.009, head=0.008, tag=3, src=0.5)
            hexbolt(R, (x, ys - 0.05, zv0 - 0.15), (0, 0, 1), r=0.009, head=0.008, tag=3, src=0.5)
    # kicker angles at the ends (top corners), visible from the side
    for sx in (-1, 1):
        sweep(PR, p_angle(0.065, 0.065, 0.007), [(sx * (FX - 0.2), FY1 - 0.75, zs - 0.07), (sx * (FX - 1.6), FACE_Y0 + 0.95, zs - 0.07)], up=(0, 0, 1), tag=6)

    # ---- head frame: I-beam saddle on the pole top, posts up to the lower stringer, diagonal angle braces ----
    hy = POLE_TOP + 0.04 + 0.155
    sweep(P, p_ibeam(0.31, 0.165, 0.009, 0.014), [(-3.6, hy, POLE_Z), (3.6, hy, POLE_Z)], up=(0, 1, 0), tag=7)
    for x in (-3.4, -1.15, 1.15, 3.4):     # web stiffeners
        box(P, (x, hy, POLE_Z + 0.042), (0.012, 0.28, 0.07), tag=7); box(P, (x, hy, POLE_Z - 0.042), (0.012, 0.28, 0.07), tag=7)
    box(P, (0, POLE_TOP + 0.02, POLE_Z), (0.95, 0.04, 0.95), tag=7)        # cap / saddle plate
    for sx in (-1, 1):                    # saddle side plates
        box(P, (sx * 0.30, POLE_TOP - 0.18, POLE_Z), (0.016, 0.36, 0.95), tag=7)
    ys_lo = FACE_Y0 + 0.95
    for x in (-3.4, -1.15, 1.15, 3.4):     # posts from head frame up to the lower stringer
        sweep(P, p_rect(0.10, 0.10), [(x, hy + 0.155, POLE_Z), (x, ys_lo, POLE_Z)], up=(0, 0, 1), tag=8)
        sweep(P, p_rect(0.10, 0.10), [(x, ys_lo - 0.05, POLE_Z), (x, ys_lo - 0.05, zs - 0.07)], up=(0, 1, 0), tag=8)
    for sx in (-1, 1):                    # long diagonal braces to the upper stringer
        sweep(PR, p_angle(0.075, 0.075, 0.008), [(sx * 3.4, hy + 0.16, POLE_Z + 0.05), (sx * 5.0, FY1 - 0.75, zs - 0.07)], up=(0, 0, 1), tag=6)
        sweep(PR, p_angle(0.075, 0.075, 0.008), [(sx * 1.15, hy + 0.16, POLE_Z + 0.05), (sx * 2.6, FY1 - 0.75, zs - 0.07)], up=(0, 0, 1), tag=6)
    for x in (-3.4, -1.15, 1.15, 3.4):
        for dz in (-0.05, 0.05):
            hexbolt(R, (x + 0.06, hy + 0.12, POLE_Z + dz), (1, 0, 0), r=0.010, head=0.009, tag=3, src=0.7)

    # ---- monopole: two tapered flanged sections on the base plate ----
    y0p = PIER_TOP + PLATE_T
    yfl = 1.85
    rb, rt = 0.47, 0.40
    rad = lambda y: rb + (rt - rb) * (y - y0p) / (POLE_TOP - y0p)
    cyl(P, (0, y0p, POLE_Z), (0, yfl - 0.03, POLE_Z), rad(y0p), rad(yfl), n=40, tag=10)
    cyl(P, (0, yfl + 0.03, POLE_Z), (0, POLE_TOP, POLE_Z), rad(yfl), rt, n=40, tag=10)
    for y0, y1 in ((yfl - 0.03, yfl), (yfl, yfl + 0.03)):
        cyl(P, (0, y0, POLE_Z), (0, y1, POLE_Z), rad(yfl) + 0.085, n=40, tag=11)
    for k in range(16):
        a = 2 * np.pi * (k + 0.5) / 16
        rr = rad(yfl) + 0.05
        p = np.array([np.cos(a) * rr, yfl + 0.03, POLE_Z + np.sin(a) * rr])
        hexbolt(R, p, (0, 1, 0), r=0.011, head=0.012, shank=0.012, tag=3, src=1.0)
        hexbolt(R, p - [0, 0.06, 0], (0, -1, 0), r=0.011, head=0.012, tag=3, src=0.0)
    # base gussets between the anchor bolts
    for k in range(8):
        a = 2 * np.pi * k / 8
        c, s = np.cos(a), np.sin(a)
        r0 = rb - 0.005
        V = []
        prof = [(r0, 0), (r0 + 0.17, 0), (r0, 0.30)]
        for off in (-0.008, 0.008):
            for (rr_, yy_) in prof:
                V.append([c * rr_ - s * off, y0p + yy_, POLE_Z + s * rr_ + c * off])
        bucket(P).add(V, [[0, 1, 2], [5, 4, 3], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], 12)
    # base plate, leveling grout gap, anchor bolts with nuts and washers
    cyl(R, (0, PIER_TOP + 0.012, POLE_Z), (0, y0p, POLE_Z), 0.70, n=48, tag=13)
    cyl('concrete', (0, PIER_TOP - 0.002, POLE_Z), (0, PIER_TOP + 0.012, POLE_Z), 0.66, 0.64, n=40, tag=14)     # grout pad
    for k in range(8):
        a = 2 * np.pi * (k + 0.5) / 8
        p = np.array([np.cos(a) * 0.60, y0p, POLE_Z + np.sin(a) * 0.60])
        cyl(R, p - [0, 0.02, 0], p + [0, 0.13, 0], 0.019, n=8, tag=15)                      # threaded rod
        cyl(R, p, p + [0, 0.006, 0], 0.045, n=12, tag=15)                                     # washer
        hexbolt(R, p + [0, 0.006, 0], (0, 1, 0), r=0.022, head=0.035, tag=15, src=1.6)        # nut
        hexbolt(R, p + [0, 0.065, 0], (0, 1, 0), r=0.022, head=0.030, tag=15, src=0.0)        # jam nut
    # concrete pier with a chamfered top edge
    sweep('concrete', [(0.0, -0.40), (0.80, -0.40), (0.80, PIER_TOP - 0.04), (0.76, PIER_TOP), (0.0, PIER_TOP)],
          [(0, 0, POLE_Z)], caps=False) if False else None
    n = 48
    rings = [(0.80, -0.35), (0.80, PIER_TOP - 0.035), (0.765, PIER_TOP)]
    V = []
    for rr_, yy_ in rings:
        for k in range(n):
            a = 2 * np.pi * k / n
            jit = 1 + 0.004 * np.sin(5 * a + 1) + 0.003 * np.sin(11 * a)
            V.append([np.cos(a) * rr_ * jit, yy_, POLE_Z + np.sin(a) * rr_ * jit])
    V.append([0, PIER_TOP, POLE_Z])
    F = []
    for j in range(len(rings) - 1):
        for k in range(n):
            a_, b_ = j * n + k, j * n + (k + 1) % n
            F.append([a_, b_, b_ + n, a_ + n][::-1])
    c_ = len(V) - 1
    for k in range(n):
        a_, b_ = (len(rings) - 1) * n + k, (len(rings) - 1) * n + (k + 1) % n
        F.append([a_, c_, b_])
    bucket('concrete').add(V, F, 16)

    # ---- catwalk ----
    BX = [-5.35, -3.55, -1.75, 0.0, 1.75, 3.55, 5.35]
    bent = 1                                # index of the bent bracket
    for i, x in enumerate(BX):
        xv = min(VX, key=lambda v: abs(v - x))
        x = xv if abs(xv - x) < 0.3 else x
        tip_drop = 0.07 if i == bent else 0.0
        # cantilever arm (channel, web vertical), from the rear vertical to the front channel
        sweep(P, p_channel(0.10, 0.04, 0.006), [(x + 0.03, DECK_Y - 0.08, zv0 - 0.15), (x + 0.03, DECK_Y - 0.08 - tip_drop, CW_Z1 + 0.02)],
              up=(-1, 0, 0) if False else (0, 1, 0), tag=20)
        # diagonal strut (angle), the bent one kinks outward
        p0 = np.array([x + 0.03, DECK_Y - 0.72, zv0 - 0.10])
        p1 = np.array([x + 0.03, DECK_Y - 0.14 - tip_drop * 0.8, CW_Z1 - 0.12])
        if i == bent:
            mid = (p0 + p1) / 2 + [0.09, -0.05, 0.02]
            sweep(P, p_angle(0.05, 0.05, 0.006), [p0, mid, p1], up=(1, 0, 0), tag=21)
        else:
            sweep(P, p_angle(0.05, 0.05, 0.006), [p0, p1], up=(1, 0, 0), tag=21)
        hexbolt(R, p0 + [0.06, 0, 0], (1, 0, 0), r=0.009, head=0.008, tag=3, src=0.9)
        hexbolt(R, (x + 0.09, DECK_Y - 0.08, zv0 - 0.10), (1, 0, 0), r=0.009, head=0.008, tag=3, src=0.9)
    # front channel (carries the lamps) and toe plate; back angle under the face edge
    sweep(P, p_channel(0.12, 0.045, 0.006)[::-1], [(-FX - 0.12, DECK_Y - 0.09, CW_Z1 + 0.02), (FX + 0.12, DECK_Y - 0.09, CW_Z1 + 0.02)],
          up=(0, 1, 0), tag=22)
    box(P, (0, DECK_Y + 0.055, CW_Z1 + 0.05), (FACE_W + 0.24, 0.20, 0.006), tag=23)          # toe plate
    sweep(P, p_angle(0.05, 0.05, 0.006), [(-FX - 0.12, DECK_Y - 0.035, 0.03), (FX + 0.12, DECK_Y - 0.035, 0.03)], up=(0, 0, 1), tag=24)
    for sx in (-1, 1):   # end plates
        box(P, (sx * (FX + 0.12), DECK_Y + 0.04, CW_Z1 / 2 + 0.02), (0.006, 0.17, CW_Z1 + 0.02), tag=23)
    for x in np.linspace(-FX, FX, 13):
        hexbolt(R, (x, DECK_Y + 0.07, CW_Z1 + 0.054), (0, 0, 1), r=0.007, head=0.006, tag=3, src=0.9)
        PERCH.append((np.array([x, DECK_Y + 0.155, CW_Z1 + 0.05]), 0.25, 1.0))
    # grating (bar grating, bearing bars across the walkway, cross rods along it)
    gx0, gx1 = -FX - 0.1, FX + 0.1
    nb = int((gx1 - gx0) / 0.032)
    for k in range(nb):
        x = gx0 + (k + 0.5) * (gx1 - gx0) / nb
        box('grating', (x, DECK_Y - 0.0155, CW_Z1 / 2 + 0.035), (0.005, 0.031, CW_Z1 - 0.02), tag=30)
    for z in np.arange(0.07, CW_Z1, 0.10):
        box('grating', (0, DECK_Y - 0.004, z), (gx1 - gx0, 0.008, 0.008), tag=31)
    # rear landing at the ladder top, around the pole
    lz0, lz1 = -1.75, 0.0
    for k in range(int(1.7 / 0.032)):
        x = -0.85 + (k + 0.5) * 0.032
        box('grating', (x, DECK_Y - 0.0155, (lz0 + lz1) / 2), (0.005, 0.031, lz1 - lz0), tag=32)
    for z in np.arange(lz0 + 0.05, lz1, 0.10):
        box('grating', (0, DECK_Y - 0.004, z), (1.70, 0.008, 0.008), tag=32)
    for sx in (-1, 1):
        sweep(G, p_angle(0.05, 0.05, 0.006), [(sx * 0.86, DECK_Y - 0.05, lz0), (sx * 0.86, DECK_Y - 0.05, 0.0)], up=(0, 1, 0), tag=40)
    sweep(G, p_angle(0.05, 0.05, 0.006), [(-0.86, DECK_Y - 0.05, lz0), (0.86, DECK_Y - 0.05, lz0)], up=(0, 1, 0), tag=40)
    for sx in (-1, 1):   # landing hangers from the head frame
        cyl(G, (sx * 0.84, DECK_Y - 0.05, lz0 + 0.02), (sx * 0.5, POLE_TOP - 0.1, POLE_Z - 0.3), 0.018, n=8, tag=40)
    # rear landing guard rail (behind the face plane, allowed)
    for sx in (-1, 1):
        cyl(G, (sx * 0.86, DECK_Y, lz0), (sx * 0.86, DECK_Y + 1.05, lz0), 0.021, n=10, tag=41)
    cyl(G, (-0.86, DECK_Y + 1.05, lz0), (0.86, DECK_Y + 1.05, lz0), 0.021, n=10, tag=41)
    cyl(G, (-0.86, DECK_Y + 0.55, lz0), (0.86, DECK_Y + 0.55, lz0), 0.017, n=8, tag=41)

    # ---- ladder with safety cage up the back of the pole ----
    lzc = POLE_Z - 0.62           # rail plane z
    ly0, ly1 = 0.95, DECK_Y + 1.05
    for sx in (-1, 1):
        member(G, p_rect(0.010, 0.060), (sx * 0.21, ly0, lzc), (sx * 0.21, ly1, lzc), up=(0, 0, 1), tag=42)
    for y in np.arange(ly0 + 0.15, DECK_Y, 0.30):
        cyl(G, (-0.21, y, lzc), (0.21, y, lzc), 0.0125, n=8, tag=43)
    for y in np.arange(ly0 + 0.3, DECK_Y, 0.9):   # stand-offs to the pole
        for sx in (-1, 1):
            member(G, p_rect(0.008, 0.05), (sx * 0.21, y, lzc + 0.03), (sx * 0.16, y, POLE_Z - rad(y) + 0.01), up=(0, 1, 0), tag=44)
    # cage hoops: open toward the ladder, centre behind the rails
    czc = lzc - 0.36
    hoops = list(np.arange(1.95, DECK_Y + 1.0, 0.62))
    for y in hoops:
        pts = [(0.36 * np.cos(a) * 1.0, y, czc + 0.36 * np.sin(a)) for a in np.linspace(np.deg2rad(55), np.deg2rad(55) - 2 * np.pi + np.deg2rad(110), 0)]
        arc = np.linspace(np.deg2rad(60), np.deg2rad(60 + 300), 22)
        pts = [(0.36 * np.cos(a), y, czc - 0.36 * np.sin(a) * -1) for a in arc]
        pts = [(px, py, pz) for (px, py, pz) in pts]
        # attach ends to the rails
        path = [(0.21, y, lzc)] + [(0.40 * np.cos(a), y, czc + 0.36 * np.sin(a) * -1) for a in arc][0:0] + []
        arc_pts = [(0.37 * np.cos(a), y, czc + 0.37 * np.sin(-a)) for a in np.linspace(np.deg2rad(-58), np.deg2rad(238), 24)]
        path = [(0.21, y, lzc)] + arc_pts + [(-0.21, y, lzc)]
        sweep(G, p_rect(0.008, 0.05), path, up=(0, 1, 0), tag=45)
    for a in np.deg2rad([-20, 30, 90, 150, 200]):
        p0 = (0.37 * np.cos(a) + 0.0, hoops[0], czc + 0.37 * np.sin(-a))
        p1 = (0.37 * np.cos(a), hoops[-1], czc + 0.37 * np.sin(-a))
        member(G, p_rect(0.045, 0.008), np.array(p0) * [1.025, 1, 1] + [0, 0, 0], np.array(p1) * [1.025, 1, 1], up=(np.cos(a), 0, -np.sin(a)), tag=46)

    # ---- flood lights on gooseneck arms ----
    LX = [-4.4, -2.2, 0.0, 2.2, 4.4]
    broken = 3
    for i_lamp, x in enumerate(LX):
        x = x + rs.uniform(-0.05, 0.05)
        a0 = np.array([x, DECK_Y - 0.12, CW_Z1 + 0.05])
        # mounting plate + U-bolts on the front channel
        box(P, a0 + [0, 0, 0.012], (0.16, 0.14, 0.012), tag=50)
        for dy in (-0.045, 0.045):
            hexbolt(R, a0 + [0.05, dy, 0.02], (0, 0, 1), r=0.007, head=0.008, tag=3, src=0.8)
            hexbolt(R, a0 + [-0.05, dy, 0.02], (0, 0, 1), r=0.007, head=0.008, tag=3, src=0.8)
        # gooseneck: out and down, then sweeping up toward the face
        t = np.linspace(0, 1, 16)
        zc = CW_Z1 + 0.07 + 0.95 * t
        yc = DECK_Y - 0.12 - 0.20 * np.sin(np.pi * t * 0.9) + 0.32 * t ** 2.2
        path = np.stack([np.full_like(t, x), yc, zc], 1)
        sweep(P, p_circle(0.027, 10), path, up=(1, 0, 0), tag=51)
        tip = path[-1]
        # fixture: aim from tip toward the face centre-ish
        aim = nrm(np.array([0, 4.9, -0.2]) + [x * 0.0, 0, 0] - tip)
        yaw = 0.0
        pitch = np.arctan2(aim[1], -aim[2])            # angle up from -z
        # housing local frame: lens normal = aim; box dims (w x, h, d along aim)
        Rm = rot(rx=pitch - np.pi / 2 + np.pi / 2, ry=0)  # rotate so local -z → aim
        c_aim = nrm(aim)
        upv = nrm(np.cross([1, 0, 0], c_aim))           # perpendicular in the y-z plane
        if upv[1] < 0: upv = -upv
        upv = -upv if np.dot(upv, [0, 0, 1]) < -2 else upv
        side = np.array([1.0, 0, 0])
        ctr = tip + c_aim * 0.12 + upv * 0.02
        def L(a, b, c):   # local (side, up, along aim) → world
            return ctr + a * side + b * upv + c * c_aim
        w, h, d = 0.46, 0.30, 0.20
        def hbox(bn, ca, cb, cc, sa, sb, sc, tag):
            V = []
            for (a, b, c) in [(-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]:
                V.append(L(ca + a * sa / 2, cb + b * sb / 2, cc + c * sc / 2))
            bucket(bn).add(V, [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]], tag)
            return V
        hbox(G, 0, 0, -0.02, w, h, d * 0.85, 52)                 # body
        hbox(G, 0, 0, -0.12, w * 0.78, h * 0.72, 0.06, 52)        # rear ballast box
        hbox(G, 0, h / 2 + 0.004, 0.035, w + 0.02, 0.008, d * 0.45, 52)   # rain lip / visor top
        for sa in (-1, 1):                                         # yoke
            hbox(G, sa * (w / 2 + 0.012), 0, -0.02, 0.008, 0.08, 0.10, 53)
        # yoke pivot onto arm tip
        cyl(G, tip, L(0, 0, -0.15), 0.018, n=8, tag=53)
        # lens frame and lens
        fz = d * 0.85 / 2 - 0.02 + 0.004
        hbox(G, 0, h / 2 - 0.012, fz, w, 0.024, 0.012, 54); hbox(G, 0, -h / 2 + 0.012, fz, w, 0.024, 0.012, 54)
        hbox(G, w / 2 - 0.012, 0, fz, 0.024, h, 0.012, 54); hbox(G, -w / 2 + 0.012, 0, fz, 0.024, h, 0.012, 54)
        # reflector inside (visible through the lens)
        lw, lh = w - 0.048, h - 0.048
        Vr = [L(-lw / 2, -lh / 2, fz - 0.002), L(lw / 2, -lh / 2, fz - 0.002), L(lw / 2, lh / 2, fz - 0.002), L(-lw / 2, lh / 2, fz - 0.002),
              L(-lw / 4, -lh / 4, fz - 0.09), L(lw / 4, -lh / 4, fz - 0.09), L(lw / 4, lh / 4, fz - 0.09), L(-lw / 4, lh / 4, fz - 0.09)]
        bucket('reflector').add(Vr, [[0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7], [4, 5, 6, 7]], 55)
        cyl('reflector', L(0, 0, fz - 0.09), L(0, 0, fz - 0.03), 0.025, n=8, tag=55)    # lamp
        # lens: 8 x 6 grid; the broken one loses a jagged region
        gx, gy = 8, 6
        Vl = [L(-lw / 2 + lw * i / gx, -lh / 2 + lh * j / gy, fz + 0.002) for j in range(gy + 1) for i in range(gx + 1)]
        Fl = []
        for j in range(gy):
            for i in range(gx):
                if i_lamp == broken and hole(i, j):
                    continue
                a_ = j * (gx + 1) + i
                Fl.append([a_, a_ + 1, a_ + gx + 2, a_ + gx + 1])
        bucket('glass').add(Vl, Fl, 56)
        if i_lamp == broken:
            # a few shards still in the frame, tilted
            for (i, j) in [(1, 1), (2, 4)]:
                p = L(-lw / 2 + lw * (i + 0.5) / gx, -lh / 2 + lh * (j + 0.5) / gy, fz + 0.006)
                sv = [p + L(0.03, -0.02, 0) - ctr, p + L(-0.025, 0.03, 0.004) - ctr, p + L(0.02, 0.035, -0.003) - ctr]
                bucket('glass').add(sv, [[0, 1, 2], [2, 1, 0]], 56)
        PERCH.append((L(0, h / 2 + 0.01, 0.0), 0.3, 1.6))
        # conduit drop into the fixture
        cyl(G, a0 + [0.10, -0.02, 0.0], a0 + [0.10, -0.02, -0.1], 0.011, n=8, tag=57)

    # ---- electrical: meter + junction box on the pole front, conduit down to the pier and up to the catwalk ----
    pz_front = POLE_Z + rad(1.3)
    jb_c = np.array([-0.16, 1.32, pz_front + 0.10])
    # unistrut backing
    for yy in (1.05, 1.62):
        member(G, p_rect(0.041, 0.041), (-0.45, yy, pz_front + 0.0), (0.18, yy, pz_front + 0.0), up=(0, 1, 0), tag=60)
    box(G, jb_c, (0.36, 0.46, 0.16), tag=61)                              # junction / disconnect box
    box(G, jb_c + [0, 0.235, 0.01], (0.39, 0.012, 0.19), tag=61)            # rain hood
    box(G, jb_c + [0.10, -0.05, 0.085], (0.04, 0.10, 0.02), tag=61)         # handle
    hexbolt(R, jb_c + [-0.15, 0.2, 0.08], (0, 0, 1), r=0.006, head=0.006, tag=3, src=1.0)
    hexbolt(R, jb_c + [0.15, 0.2, 0.08], (0, 0, 1), r=0.006, head=0.006, tag=3, src=1.0)
    hexbolt(R, jb_c + [0.0, -0.2, 0.08], (0, 0, 1), r=0.006, head=0.006, tag=3, src=0.6)
    mb_c = np.array([0.08, 1.40, pz_front + 0.10])
    box(G, mb_c, (0.22, 0.34, 0.12), tag=62)                               # meter socket
    cyl(G, mb_c + [0, 0.0, 0.06], mb_c + [0, 0.0, 0.085], 0.095, n=20, tag=62)   # meter ring
    cyl('glass', mb_c + [0, 0.0, 0.085], mb_c + [0, 0.0, 0.16], 0.085, 0.08, n=20, tag=63)   # meter glass dome
    PERCH.append((jb_c + [0, 0.245, 0], 0.15, 0.5))
    # conduit runs (rigid steel, 1")
    cr = 0.017
    sweep(G, p_circle(cr, 8), [jb_c + [-0.08, -0.23, 0], jb_c + [-0.08, -0.6, 0], jb_c + [-0.08, -0.85, -0.02],
                                (jb_c[0] - 0.08, PIER_TOP + 0.02, jb_c[2] - 0.05), (jb_c[0] - 0.08, PIER_TOP - 0.02, jb_c[2] - 0.05)], up=(1, 0, 0), tag=64)
    sweep(G, p_circle(cr, 8), [mb_c + [0, -0.17, 0], mb_c + [0, -0.45, 0], (mb_c[0], PIER_TOP + 0.01, mb_c[2] - 0.04)], up=(1, 0, 0), tag=64)
    # up the pole (following the taper) to the catwalk, then along under the deck to each lamp
    up_path = [jb_c + [0.08, 0.23, 0]]
    for y in np.linspace(1.62, DECK_Y - 0.25, 6):
        up_path.append((jb_c[0] + 0.08, y, POLE_Z + rad(y) + 0.03))
    up_path.append((jb_c[0] + 0.08, DECK_Y - 0.17, 0.20))
    up_path.append((jb_c[0] + 0.08, DECK_Y - 0.17, CW_Z1 - 0.08))
    sweep(G, p_circle(cr, 8), up_path, up=(1, 0, 0), tag=64)
    sweep(G, p_circle(cr, 8), [(LX[0] + 0.10, DECK_Y - 0.17, CW_Z1 - 0.08), (LX[-1] + 0.10, DECK_Y - 0.17, CW_Z1 - 0.08)], up=(0, 1, 0), tag=64)
    for x in LX:
        sweep(G, p_circle(0.011, 8), [(x + 0.10, DECK_Y - 0.17, CW_Z1 - 0.08), (x + 0.10, DECK_Y - 0.17, CW_Z1 + 0.04)], up=(0, 1, 0), tag=64)
        cyl(G, (x + 0.10, DECK_Y - 0.17, CW_Z1 - 0.08), (x + 0.10, DECK_Y - 0.17 - 0.06, CW_Z1 - 0.08), 0.03, n=8, tag=64)   # pull box
    for y in np.linspace(1.75, DECK_Y - 0.35, 3):        # pipe straps
        cyl(G, (jb_c[0] + 0.08 - 0.03, y, POLE_Z + rad(y) + 0.03), (jb_c[0] + 0.08 + 0.03, y, POLE_Z + rad(y) + 0.03), cr + 0.005, n=8, tag=64)

    # ---- owner's plate on the toe plate ----
    pc = np.array([1.12, DECK_Y + 0.055, CW_Z1 + 0.0535])
    bucket('plate').add([pc + [-0.21, -0.06, 0], pc + [0.21, -0.06, 0], pc + [0.21, 0.06, 0], pc + [-0.21, 0.06, 0]], [[0, 1, 2, 3]], 70)
    for dx in (-0.19, 0.19):
        hexbolt(R, pc + [dx, 0, 0.001], (0, 0, 1), r=0.005, head=0.004, tag=3, src=1.2)

    # ---- old vinyl remnants ----
    vinyl(rs)
    return B


def hole(i, j):
    # jagged hole in the broken lens (grid 8 x 6): upper-right region
    return (i >= 3 and j >= 2 and (i - 3) + (j - 2) * 1.3 < 5.5) or (i == 2 and j == 4)


def vinyl(rs):
    """Torn vinyl remnants: bands trapped under the frame lip on the border (outside the face rectangle)
    and shreds hanging below the bottom frame edge / beside the side edges. Double-sided material."""
    V = 'vinyl_old'
    z = -0.0035 + 0.0
    zlip = 0.0015
    # border bands: a jagged strip on the border front, (from the outer edge inward up to the face edge)
    def band(x0, x1, y_edge, sgn, seed):
        r = np.random.default_rng(seed)
        n = max(4, int((x1 - x0) / 0.04))
        xs = np.linspace(x0, x1, n)
        inner = y_edge + sgn * np.clip(r.normal(0.004, 0.010, n), 0.0, 0.04)
        outer = y_edge + sgn * (BORDER + 0.0)
        top = [(x, yi, zlip) for x, yi in zip(xs, inner)]
        bot = [(x, outer, zlip) for x in xs]
        Vv = top + bot
        F = [[i, i + 1, n + i + 1, n + i] if sgn < 0 else [n + i, n + i + 1, i + 1, i] for i in range(n - 1)]
        bucket(V).add(Vv, F, 80)
    band(-FX + 0.4, -FX + 3.1, FACE_Y0, -1, 1)
    band(1.2, 4.3, FACE_Y0, -1, 2)
    band(-2.5, 0.6, FY1, 1, 3)
    band(3.0, FX - 0.1, FY1, 1, 4)
    # side bands (vertical): swap axes
    def vband(y0, y1, sx, seed):
        r = np.random.default_rng(seed)
        n = max(4, int((y1 - y0) / 0.04))
        ys = np.linspace(y0, y1, n)
        inner = sx * FX + sx * np.clip(r.normal(0.004, 0.01, n), 0.0, 0.04)
        outer = sx * (FX + BORDER)
        Vv = [(xi, y, zlip) for xi, y in zip(inner, ys)] + [(outer, y, zlip) for y in ys]
        F = [[i, n + i, n + i + 1, i + 1] if sx > 0 else [i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
        bucket(V).add(Vv, F, 81)
    vband(FACE_Y0 + 0.2, FACE_Y0 + 2.6, -1, 5)
    vband(FACE_Y0 + 1.1, FY1 - 0.4, 1, 6)
    # hanging shreds below the bottom edge: wrap over the bottom frame lip and hang down, curling forward a little
    for k in range(9):
        r = np.random.default_rng(100 + k)
        x = r.uniform(-FX + 0.2, FX - 0.2)
        w = r.uniform(0.05, 0.22)
        Lh = r.uniform(0.15, 0.75)
        ny = max(3, int(Lh / 0.05))
        pts = []
        for j in range(ny + 1):
            t = j / ny
            y = FACE_Y0 - BORDER - t * Lh
            zz = zlip + 0.002 + 0.10 * t ** 2 * r.uniform(0.2, 1.0)
            dx = 0.03 * np.sin(t * 3 + k) * t
            pts.append((y, zz, dx))
        Vv, F = [], []
        for j, (y, zz, dx) in enumerate(pts):
            taper = 1 - 0.6 * (j / ny) ** 1.5 * r.uniform(0.5, 1)
            jag = r.uniform(-0.02, 0.02) if j == ny else 0
            Vv.append((x + dx - w / 2 * taper, y + jag, zz)); Vv.append((x + dx + w / 2 * taper, y - jag, zz + 0.004 * np.sin(j)))
        # part over the lip (on the border)
        Vv = [(x - w / 2, FACE_Y0 - 0.01, zlip), (x + w / 2, FACE_Y0 - 0.01, zlip)] + Vv
        for j in range(ny + 1):
            a = 2 * j
            F.append([a, a + 2, a + 3, a + 1][::-1])
        bucket(V).add(Vv, F, 82)
    # side shreds hanging off the outer frame wall at the far left and right, beside the face (x outside ±(FX+BORDER))
    for k, (sx, y0) in enumerate([(-1, 5.6), (-1, 3.9), (1, 4.4), (1, 6.6)]):
        r = np.random.default_rng(200 + k)
        w = r.uniform(0.08, 0.2); Lh = r.uniform(0.25, 0.8)
        ny = max(3, int(Lh / 0.05))
        Vv, F = [], []
        for j in range(ny + 1):
            t = j / ny
            xo = sx * (FX + BORDER + 0.002 + 0.06 * t ** 1.5)
            y = y0 - t * Lh
            zz = -0.02 - 0.04 * t + r.uniform(-0.01, 0.01)
            Vv.append((xo, y, zz + w / 2 * (1 - 0.5 * t))); Vv.append((xo, y, zz - w / 2 * (1 - 0.5 * t) - 0.05))
        for j in range(ny):
            a = 2 * j
            F.append([a, a + 2, a + 3, a + 1])
        bucket(V).add(Vv, F, 83)


def check_front_clear(Bk):
    """Assert nothing crosses in front of the face rectangle."""
    bad = []
    for name, b in Bk.items():
        V, F, _ = b.arrays()
        if len(V) == 0:
            continue
        m = (V[:, 0] > -FX) & (V[:, 0] < FX) & (V[:, 1] > FACE_Y0 + 1e-3) & (V[:, 1] < FY1) & (V[:, 2] > 1e-4)
        if m.any():
            bad.append((name, int(m.sum()), V[m][:3]))
    return bad


if __name__ == '__main__':
    Bk = build()
    tot = 0
    for k, b in Bk.items():
        V, F, _ = b.arrays()
        t = sum(len(f) - 2 for f in F)
        tot += t
        print(f'{k:22s} verts {len(V):7d} tris {t:7d}')
    print('total tris', tot, 'sources', len(SOURCES), 'perch', len(PERCH))
    print('front-clear violations:', check_front_clear(Bk))
