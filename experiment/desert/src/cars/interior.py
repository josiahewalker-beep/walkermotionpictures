"""Cabin interior seen through the glass: inner shell (headliner, door cards, floor), seats, dashboard, wheel, console."""
import numpy as np
from carlib import smin, smax, sd_round_box, sd_capsule, normalize, tube, vertex_normals, rot_x
import details as D

def add_interior(parts, B, C):
    lo, hi = C['cabin_bounds']
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    cen = (lo + hi) / 2; half = (hi - lo) / 2
    def shell(x, s, z):
        P = np.stack([x, s, z], -1)
        return smax(B.field(x, s, z) + 0.035, sd_round_box(P, cen, half, 0.05), 0.03)
    V, F, N = D.mc_small(shell, lo - 0.02, hi + 0.02, 0.02, 5000)
    col = 0.55 + 0.45 * np.clip((V[:, 2] - C['floor']) / 0.8, 0, 1)
    parts.add('body', V, F[:, ::-1], 'interior', N=-N, COL=np.c_[np.repeat(col[:, None], 3, 1), np.ones(len(V))])

    sx, ss, hz, sh = C['seat_x'], C['seat_s'], C['hip_z'], C['seat_h']
    def seat_field(x, s, z, xs, s0):
        ax = x - xs
        P = np.stack([ax, s - s0, z], -1)
        cushion = sd_round_box(P, (0, 0.06, hz - 0.02), (0.25, 0.26, 0.06), 0.05)
        # bolsters
        bol = sd_round_box(np.stack([np.abs(ax), s - s0, z], -1), (0.22, 0.06, hz + 0.03), (0.04, 0.24, 0.05), 0.035)
        # backrest tilted ~20 deg back
        a = np.deg2rad(18)
        sb = (s - s0 + 0.20); zb = z - (hz + 0.02)
        u = sb * np.cos(a) - zb * np.sin(a); w = sb * np.sin(a) + zb * np.cos(a)
        back = sd_round_box(np.stack([ax, u, w], -1), (0, 0.0, sh / 2), (0.25, 0.055, sh / 2), 0.05)
        bolb = sd_round_box(np.stack([np.abs(ax), u, w], -1), (0.21, 0.035, sh / 2 - 0.05), (0.05, 0.06, sh / 2 - 0.12), 0.04)
        head = sd_round_box(np.stack([ax, u, w], -1), (0, -0.01, sh + 0.10), (0.13, 0.05, 0.09), 0.04)
        d = smin(cushion, bol, 0.02)
        d = smin(d, back, 0.03)
        d = smin(d, bolb, 0.02)
        d = smin(d, head, 0.02)
        return d
    for xs in (-sx, sx):
        fld = lambda x, s, z, xs=xs: seat_field(x, s, z, xs, ss)
        V, F, N = D.mc_small(fld, (xs - 0.32, ss - 0.65, hz - 0.12), (xs + 0.32, ss + 0.40, hz + sh + 0.25), 0.014, 1600)
        col = 0.8 + 0.2 * np.clip((V[:, 2] - hz) / sh, 0, 1)
        parts.add('body', V, F, 'interior', N=N, COL=np.c_[np.repeat(col[:, None], 3, 1), np.ones(len(V))])
    if C.get('rear_seats'):
        rs = C['rear_s']
        for xs in (-sx, sx):
            fld = lambda x, s, z, xs=xs: seat_field(x, s, z, xs, rs)
            V, F, N = D.mc_small(fld, (xs - 0.32, rs - 0.65, hz - 0.12), (xs + 0.32, rs + 0.40, hz + sh + 0.25), 0.016, 1200)
            parts.add('body', V, F, 'interior', N=N, COL=np.c_[np.full((len(V), 3), 0.85), np.ones(len(V))])
    # dashboard + instrument hood + console
    ds, dz = C['dash_s'], C['dash_z']
    w = C.get('dash_w', 0.70)
    def dash(x, s, z):
        P = np.stack([x, s, z], -1)
        d = sd_round_box(P, (0, ds + 0.10, dz - 0.12), (w, 0.22, 0.12), 0.06)
        hood = sd_round_box(P, (-sx, ds - 0.06, dz + 0.0), (0.17, 0.07, 0.05), 0.03)
        cons = sd_round_box(P, (0, ds - 0.25, C['floor'] + 0.17), (0.11, 0.42, 0.17), 0.04)
        stack = sd_round_box(P, (0, ds - 0.02, dz - 0.25), (0.13, 0.08, 0.2), 0.04)
        return smin(smin(smin(d, hood, 0.03), cons, 0.04), stack, 0.04)
    V, F, N = D.mc_small(dash, (-w - 0.1, ds - 0.75, C['floor'] - 0.05), (w + 0.1, ds + 0.4, dz + 0.1), 0.016, 2200)
    parts.add('body', V, F, 'interior', N=N, COL=np.c_[np.full((len(V), 3), 0.9), np.ones(len(V))])
    # steering wheel (driver on model x<0 = car's left, glTF +X)
    ws_ = C['wheel_s']; wz = dz - 0.03
    c = np.array([-sx, ws_ + 0.0, wz])
    tilt = np.deg2rad(25)
    th = np.linspace(0, 2 * np.pi, 33)
    ring = np.stack([0.185 * np.cos(th), -0.185 * np.sin(th) * np.sin(tilt), 0.185 * np.sin(th) * np.cos(tilt)], 1) + c
    Vt, Ft = tube(ring, 0.017, n_seg=10, closed=False, caps=False)
    parts.add('body', Vt, Ft, 'interior', COL=np.c_[np.full((len(Vt), 3), 0.7), np.ones(len(Vt))])
    for ang in (0, np.pi, 1.5 * np.pi):
        p = np.array([0.185 * np.cos(ang), -0.185 * np.sin(ang) * np.sin(tilt), 0.185 * np.sin(ang) * np.cos(tilt)]) + c
        Vt, Ft = tube(np.array([c, p]), 0.012, n_seg=6)
        parts.add('body', Vt, Ft, 'interior')
    Vt, Ft = tube(np.array([c, c + np.array([0, 0.30, 0.10])]), 0.03, n_seg=8)
    parts.add('body', Vt, Ft, 'interior')
