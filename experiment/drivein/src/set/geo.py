"""Mesh primitives in glTF coordinates (metres, +Y up), accumulated per material bucket as numpy arrays.
Adapted from the desert billboard generator (desert/src/set/bb_geo.py). Pure numpy."""
import numpy as np



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
        self.attr = []       # per polygon (ax, ay, az, k): grain axis (abs, glTF) + free scalar k (e.g. paint)

    def add(self, V, F, tag=0, axis=None):
        V = np.asarray(V, float)
        self.V.append(V)
        self.F.extend([[i + self.n for i in f] for f in F])
        self.tags.extend([tag] * len(F))
        ax = np.abs(nrm(axis)) if axis is not None else np.abs(nrm(CUR['axis']))
        self.attr.extend([[ax[0], ax[1], ax[2], CUR['k']]] * len(F))
        self.n += len(V)

    def arrays(self):
        return (np.concatenate(self.V) if self.V else np.zeros((0, 3))), self.F, np.array(self.tags, int)


CUR = {'axis': (0, 1, 0), 'k': 0.0}


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
    bucket(bname).add(V, F, tag, axis=path[-1] - path[0] if np.linalg.norm(path[-1] - path[0]) > 1e-6 else None)
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
    k = int(np.argmax([sx, sy, sz]))
    bucket(bname).add(V, F, tag, axis=rot(rotX, rotY, rotZ)[:, k])
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


