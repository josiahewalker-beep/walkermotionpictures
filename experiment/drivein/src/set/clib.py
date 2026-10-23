"""Small-mesh helpers for props and creatures (pure numpy, glTF coords, metres). Each builder returns
(V, F, UV-per-vertex) so meshes can be merged and handed to pipe.make_mesh (per-loop UVs derived from per-vertex)."""
import numpy as np


def nrm(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


class Mesh:
    def __init__(self):
        self.V, self.F, self.UV = [], [], []
        self.n = 0

    def add(self, V, F, UV=None):
        V = np.asarray(V, float)
        self.V.append(V)
        self.F.extend([[i + self.n for i in f] for f in F])
        self.UV.append(np.zeros((len(V), 2)) if UV is None else np.asarray(UV, float))
        self.n += len(V)
        return self

    def merge(self, other):
        V, F, UV = other.arrays()
        return self.add(V, F, UV)

    def arrays(self):
        if not self.V:
            return np.zeros((0, 3)), [], np.zeros((0, 2))
        return np.concatenate(self.V), self.F, np.concatenate(self.UV)

    def loop_uvs(self):
        V, F, UV = self.arrays()
        return [UV[f] for f in F]

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    def transform(self, fn):
        self.V = [fn(v) for v in self.V]
        return self


def frames(path, up=(0, 1, 0)):
    path = np.asarray(path, float)
    n = len(path)
    T = np.zeros((n, 3))
    for i in range(n):
        a, b = path[max(i - 1, 0)], path[min(i + 1, n - 1)]
        T[i] = nrm(b - a)
    S = np.zeros((n, 3)); U = np.zeros((n, 3))
    up = np.asarray(up, float)
    for i in range(n):
        s = np.cross(up, T[i])
        if np.linalg.norm(s) < 1e-6:
            s = np.cross((0, 0, 1), T[i])
        S[i] = nrm(s)
        U[i] = nrm(np.cross(T[i], S[i]))
    return T, S, U


def loft(path, rx, ry, m=16, cap0=True, cap1=True, up=(0, 1, 0), offs=None, phase=0.0, shape=None):
    """Tube through path with elliptical sections (rx along the side vector, ry along up).
    offs: optional per-ring (n,m) radial multipliers. shape(i, a) -> multiplier. UV: u around, v along."""
    path = np.asarray(path, float)
    n = len(path)
    T, S, U = frames(path, up)
    rx = np.broadcast_to(np.asarray(rx, float), (n,)); ry = np.broadcast_to(np.asarray(ry, float), (n,))
    V, UV = [], []
    for i in range(n):
        for j in range(m + 1):
            a = phase + 2 * np.pi * j / m
            k = 1.0
            if offs is not None:
                k *= offs[i, j % m]
            if shape is not None:
                k *= shape(i, a)
            V.append(path[i] + k * (rx[i] * np.cos(a) * S[i] + ry[i] * np.sin(a) * U[i]))
            UV.append((j / m, i / (n - 1)))
    F = []
    W = m + 1
    for i in range(n - 1):
        for j in range(m):
            F.append([i * W + j, (i + 1) * W + j, (i + 1) * W + j + 1, i * W + j + 1])
    V = list(V)
    if cap0:
        c = len(V); V.append(path[0] - T[0] * 0.0); UV.append((0.5, 0.0))
        for j in range(m):
            F.append([c, j + 1, j])
    if cap1:
        c = len(V); V.append(path[-1]); UV.append((0.5, 1.0))
        b = (n - 1) * W
        for j in range(m):
            F.append([c, b + j, b + j + 1])
    V = np.array(V)
    F = orient(V, F)
    return Mesh().add(V, F, np.array(UV))


def orient(V, F):
    """Flip all faces if the (closed-ish) mesh has negative signed volume."""
    vol = 0.0
    for f in F:
        for k in range(1, len(f) - 1):
            vol += np.dot(V[f[0]], np.cross(V[f[k]], V[f[k + 1]]))
    return [list(f)[::-1] for f in F] if vol < 0 else [list(f) for f in F]


def sphere(c, r, m=12, n=8, squash=(1, 1, 1)):
    c = np.asarray(c, float)
    V, UV, F = [], [], []
    for i in range(n + 1):
        th = np.pi * i / n
        for j in range(m + 1):
            ph = 2 * np.pi * j / m
            p = np.array([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)]) * r * np.asarray(squash)
            V.append(c + p); UV.append((j / m, 1 - i / n))
    W = m + 1
    for i in range(n):
        for j in range(m):
            q = [i * W + j, i * W + j + 1, (i + 1) * W + j + 1, (i + 1) * W + j]
            if i == 0:
                F.append([q[0], q[2], q[3]])
            elif i == n - 1:
                F.append([q[0], q[1], q[2]])
            else:
                F.append(q)
    V = np.array(V)
    return Mesh().add(V, orient(V - c, F), np.array(UV))


def lathe(profile, m=24, c=(0, 0, 0), close_bottom=False, close_top=False):
    """profile: list of (r, y). Revolve around +Y. UV: u around, v = arc length fraction."""
    pr = np.asarray(profile, float)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pr, axis=0), axis=1))]
    L = L / L[-1]
    V, UV, F = [], [], []
    for i, (r, y) in enumerate(pr):
        for j in range(m + 1):
            a = 2 * np.pi * j / m
            V.append((c[0] + r * np.cos(a), c[1] + y, c[2] + r * np.sin(a))); UV.append((j / m, L[i]))
    W = m + 1
    for i in range(len(pr) - 1):
        for j in range(m):
            F.append([i * W + j, i * W + j + 1, (i + 1) * W + j + 1, (i + 1) * W + j])
    if close_bottom:
        k = len(V); V.append((c[0], c[1] + pr[0][1], c[2])); UV.append((0.5, 0))
        for j in range(m):
            F.append([k, j + 1, j][::-1])
    if close_top:
        k = len(V); V.append((c[0], c[1] + pr[-1][1], c[2])); UV.append((0.5, 1))
        b = (len(pr) - 1) * W
        for j in range(m):
            F.append([k, b + j, b + j + 1][::-1])
    return Mesh().add(np.array(V), F, np.array(UV))


def flip(mesh):
    mesh.F = [f[::-1] for f in mesh.F]
    return mesh


def blade(root, d, side, length, width_fn, nl=8, nw=3, thick=0.0, bend=None, uv_rect=(0, 0, 1, 1)):
    """Flat feather/leaf blade from root along d, width along side. width_fn(t) half-width at t in [0,1].
    bend(t) -> offset vector added. Two-sided via a thin thickness if thick > 0, else single surface (double-sided material)."""
    root, d, side = np.asarray(root, float), nrm(d), nrm(side)
    nrmv = nrm(np.cross(side, d))
    V, UV = [], []
    u0, v0, u1, v1 = uv_rect
    for i in range(nl + 1):
        t = i / nl
        w = width_fn(t)
        for j in range(nw + 1):
            s = -1 + 2 * j / nw
            p = root + d * length * t + side * w * s
            if bend is not None:
                p = p + bend(t, s)
            V.append(p); UV.append((u0 + (u1 - u0) * (s * 0.5 + 0.5), v0 + (v1 - v0) * t))
    F = []
    W = nw + 1
    for i in range(nl):
        for j in range(nw):
            F.append([i * W + j, i * W + j + 1, (i + 1) * W + j + 1, (i + 1) * W + j])
    V = np.array(V)
    m = Mesh().add(V, F, np.array(UV))
    if thick > 0:
        b = Mesh().add(V - nrmv * thick, [f[::-1] for f in F], np.array(UV))
        m.merge(b)
    return m


def fan_polygon(pts, center, uvfn):
    """Planar polygon star-shaped around center -> triangle fan. uvfn(p) -> uv."""
    pts = np.asarray(pts, float)
    V = np.vstack([center, pts])
    F = [[0, i + 1, (i + 1) % len(pts) + 1] for i in range(len(pts))]
    return Mesh().add(V, F, np.array([uvfn(p) for p in V]))
