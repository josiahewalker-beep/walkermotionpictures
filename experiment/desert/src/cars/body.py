"""Parametric car body as an implicit field (model frame x lateral, s forward, z up).

Lower body  = smooth intersection of: side wall |x| < W(s, z), top z < Ztop(x, s), bottom z > Zbot(s),
              nose s < Sf(x, z), tail s > Sr(x, z)
Greenhouse  = |x| < Wg(s, z), z < Zroof(x, s), windshield plane, backlight plane, z > belt
Body        = smooth union, minus wheel wells.
"""
import numpy as np
from scipy.interpolate import PchipInterpolator
from carlib import smin, smax, sstep, gauss

class Curve:
    def __init__(self, pts):
        P = np.asarray(pts, float)
        o = np.argsort(P[:, 0]); P = P[o]
        self.lo, self.hi = P[0, 0], P[-1, 0]
        self.f = PchipInterpolator(P[:, 0], P[:, 1], extrapolate=True)
        self.y0, self.y1 = P[0, 1], P[-1, 1]
    def __call__(self, x):
        x = np.asarray(x, float)
        y = self.f(np.clip(x, self.lo, self.hi))
        return y

def softplus(x, k):
    return k * np.logaddexp(0, x / k)

class Body:
    def __init__(self, P):
        self.P = P
        self.c = {k: Curve(v) for k, v in P['curves'].items()}

    # ---------------- components
    def wall(self, ax, s, z):
        P, c = self.P, self.c
        W = c['W'](s)
        # cross-section: tuck under toward the bottom, crease + tumblehome above the character line
        W = W - P['tuck'] * (1 - sstep(P['tuck_z0'], P['tuck_z1'], z)) ** 2
        zc = c['crease_z'](s)
        W = W - P['crease_k'] * softplus(z - zc, P['crease_sharp']) - P['shoulder_k'] * np.maximum(z - zc, 0) ** 2
        if 'crease2_z' in c:   # lower sculpt line (concave above, convex below)
            z2 = c['crease2_z'](s)
            W = W - P['crease2_k'] * softplus(z2 - z, P['crease_sharp']) * sstep(-0.02, 0.06, z - P['tuck_z1'])
        if 'scallop' in P:
            sc = P['scallop']
            W = W - sc['depth'] * gauss(z, sc['z'], sc['w']) * sstep(sc['s0'], sc['s0'] + 0.3, s) * (1 - sstep(sc['s1'] - 0.3, sc['s1'], s))
        # arch flares
        for (sa, za, R, fl, wfl) in P['flares']:
            r = np.sqrt((s - sa) ** 2 + (z - za) ** 2)
            W = W + fl * np.exp(-((r - R) / wfl) ** 2) * sstep(za - 0.30, za + 0.10, z)
        for (sa, ws, zz, wz, amt) in P.get('haunches', []):
            W = W + amt * gauss(s, sa, ws) * gauss(z, zz, wz)
        return ax - W

    def top(self, ax, s, z):
        P, c = self.P, self.c
        Zt = c['Ztop'](s)
        if 'fender' in c:
            Zt = Zt + c['fender'](s) * sstep(P['fender_x0'], P['fender_x1'], ax)
        Zt = Zt - P.get('hood_crown', 0.0) * (ax / 0.9) ** 2
        return z - Zt

    def bottom(self, ax, s, z):
        return self.c['Zbot'](s) - z

    def nose(self, ax, s, z):
        P, c = self.P, self.c
        Lf = c['Lf'](z)
        return s - (Lf - P['nose_corner'] * (ax / P['half_w']) ** P['nose_pow'])

    def tail(self, ax, s, z):
        P, c = self.P, self.c
        Lr = c['Lr'](z)
        return (Lr + P['tail_corner'] * (ax / P['half_w']) ** P['tail_pow']) - s

    def lower(self, ax, s, z):
        P = self.P
        d = smax(self.wall(ax, s, z), self.top(ax, s, z), P['k_shoulder'])
        d = smax(d, self.nose(ax, s, z), P['k_nose'])
        d = smax(d, self.tail(ax, s, z), P['k_tail'])
        d = smax(d, self.bottom(ax, s, z), P['k_bottom'])
        return d

    def gh_width(self, s, z):
        P, c = self.P, self.c
        return c['Wg'](s) - P['tumble'] * (z - P['belt']) - P['tumble2'] * np.maximum(z - P['belt'], 0) ** 2

    def ws_dist(self, ax, s, z):
        P = self.P
        (s0, z0), (s1, z1) = P['ws_line']
        ds, dz = s1 - s0, z1 - z0
        n = np.array([-dz, ds]); n = n / np.linalg.norm(n)
        if n[0] < 0: n = -n
        wrap = P['ws_wrap'] * (ax / 0.75) ** 2
        return n[0] * (s - s0 + wrap) + n[1] * (z - z0) - P.get('ws_bulge', 0.0) * (1 - (ax / 0.75) ** 2)

    def bl_dist(self, ax, s, z):
        P = self.P
        if 'bl_line' not in P:
            return -np.ones_like(s * z)
        (s0, z0), (s1, z1) = P['bl_line']
        ds, dz = s1 - s0, z1 - z0
        n = np.array([-dz, ds]); n = n / np.linalg.norm(n)
        if n[0] > 0: n = -n
        wrap = P.get('bl_wrap', 0.0) * (ax / 0.75) ** 2
        return n[0] * (s - s0 - wrap) + n[1] * (z - z0)

    def roof(self, ax, s, z):
        P, c = self.P, self.c
        return z - (c['Zroof'](s) - P['roof_crown'] * (ax / 0.7) ** 2)

    def greenhouse(self, ax, s, z):
        P = self.P
        d = smax(ax - self.gh_width(s, z), self.roof(ax, s, z), P['k_roof'])
        d = smax(d, self.ws_dist(ax, s, z), P['k_ws'])
        d = smax(d, self.bl_dist(ax, s, z), P['k_bl'])
        d = smax(d, (P['belt'] - 0.12) - z, 0.0)
        return d

    def wells(self, ax, s, z):
        d = None
        for (sa, za, R, xin) in self.P['wells']:
            dc = np.sqrt((s - sa) ** 2 + (z - za) ** 2) - R
            dw = smax(dc, xin - ax, 0.02)
            d = dw if d is None else np.minimum(d, dw)
        return d

    def outer(self, x, s, z):
        ax = np.abs(x)
        return smin(self.lower(ax, s, z), self.greenhouse(ax, s, z), self.P['k_belt'])

    def well_dist(self, x, s, z):
        return self.wells(np.abs(x), s, z)

    def field(self, x, s, z):
        ax = np.abs(x)
        d = smin(self.lower(ax, s, z), self.greenhouse(ax, s, z), self.P['k_belt'])
        d = smax(d, -self.wells(ax, s, z), self.P['k_well'])
        return d
