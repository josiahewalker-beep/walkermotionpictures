"""90s wheels: tyre (from wheels.py, fewer segments for background cars) + one of
  'cover'  : full plastic/steel wheel cover with slots, raised ring and a centre dome (Taurus/Corsica era)
  'steel'  : painted steel wheel with round holes and a small chrome centre cap (work trucks, base models)
  'alloy'  : 5-spoke alloy from wheels.rim_field (Explorer/Cherokee era)
Local wheel frame: a = axial (outboard +), (y, z) radial.  Node origin = hub centre.
"""
import numpy as np
from carlib import (mc_mesh, decimate, field_normals, fix_winding, project_to_surface, revolve, vertex_normals,
                    smin, smax, sstep, gauss)
import wheels as W

def cover_field(st):
    Rc = st['r_cover']; af0 = st['a_face']; t = st.get('thick', 0.0035)
    def field(a, y, z):
        r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
        u = np.clip(r / Rc, 0, 1.2)
        af = af0 - st.get('dome', 0.012) * u ** 2 - st.get('roll', 0.03) * sstep(0.86, 1.0, u) ** 1.5
        af = af + st.get('ring_h', 0.006) * gauss(r, st.get('ring_r', 0.6 * Rc), 0.007)
        af = af + st.get('cap_h', 0.014) * (1 - sstep(st.get('cap_r', 0.05) - 0.006, st.get('cap_r', 0.05) + 0.004, r))
        d = smax(np.abs(a - af) - t, r - Rc, 0.004)
        n = st['holes']
        sector = 2 * np.pi / n
        loc = (th + sector / 2 + st.get('phase', 0.0)) % sector - sector / 2
        if st.get('hole_type', 'slot') == 'slot':
            dh = smax(np.abs(r - st['hole_r']) - st['hole_len'] / 2, np.abs(loc) * r - st['hole_w'] / 2, 0.006)
        else:
            cy = st['hole_r'] * np.cos(loc); cz = st['hole_r'] * np.sin(loc)
            dh = np.sqrt((r * np.cos(loc) - st['hole_r']) ** 2 + (r * np.sin(loc)) ** 2) - st['hole_w'] / 2
        d = smax(d, -dh, 0.003)
        return d
    return field

def cover_mesh(st, res=0.0024, target=3000):
    Rc = st['r_cover'] + 0.01
    f = cover_field(st)
    a0 = st['a_face'] - 0.06; a1 = st['a_face'] + 0.03
    V, F = mc_mesh(f, (a0, -Rc, -Rc), (a1, Rc, Rc), res, slab=16)
    V, F = decimate(V, F, target)
    V = project_to_surface(f, V, iters=3, h=0.0008)
    N = field_normals(f, V, h=0.0010)
    F = fix_winding(V, F, N)
    return V, F, N

def back_plate(st, n_seg=40):
    """Dark disc behind the cover/holes (the wheel's inner face and brake drum in shadow)."""
    a = st['a_face'] - 0.05; R = st['r_cover']
    prof = [(a, 0.0), (a, R), (a - 0.07, R)]
    V, F, _ = revolve(prof, n_seg)
    N = vertex_normals(V, F)
    if np.mean(N[:, 0]) < 0:
        F = F[:, ::-1].copy(); N = -N
    return V, F, N

def add_wheels(parts, axles, r_out, r_bead, width, st, tyre_seg=48, target=3000):
    """axles: list of (name, s, x_half). Returns node -> hub centre (model frame)."""
    if st['type'] == 'alloy':
        rim = W.rim_mesh(st['alloy'], target=target)
    else:
        rim = cover_mesh(st, target=target)
    back = back_plate(st)
    out = {}
    for (name, s, xh) in axles:
        side = 1 if name.endswith('R') else -1
        centre = (side * xh, s, r_out)
        node = 'wheel_' + name
        Vt, Ft, Nt, UVt, Ct = W.tyre_mesh(r_out, r_bead, width, n_seg=tyre_seg)
        Vm, Nm = W.to_model(Vt, Nt, centre, side)
        parts.add(node, Vm, Ft if side > 0 else Ft[:, ::-1], 'rubber', N=Nm, UV=UVt, COL=np.c_[Ct, np.ones(len(Ct))])
        Vr, Fr, Nr = rim
        rr = np.linalg.norm(Vr[:, 1:], axis=1)
        ca = np.ones((len(Vr), 3))
        if st['type'] == 'alloy':
            ca *= (0.12 + 0.88 * sstep(-0.08, 0.08, Vr[:, 0]))[:, None]
        else:
            ca *= (0.55 + 0.45 * sstep(st['a_face'] - 0.03, st['a_face'], Vr[:, 0]))[:, None]
        dust = st.get('dust', 0.15) * sstep(0.6 * r_bead, r_bead, rr)
        ca = ca * (1 - dust[:, None]) + dust[:, None] * np.array([0.45, 0.37, 0.28])
        Vm, Nm = W.to_model(Vr, Nr, centre, side)
        parts.add(node, Vm, Fr if side > 0 else Fr[:, ::-1], 'rim', N=Nm, COL=np.c_[ca, np.ones(len(ca))])
        Vb, Fb, Nb = back
        Vm, Nm = W.to_model(Vb, Nb, centre, side)
        parts.add(node, Vm, Fb if side > 0 else Fb[:, ::-1], 'trim_black', N=Nm,
                  COL=np.c_[np.full((len(Vb), 3), 0.35), np.ones(len(Vb))])
        if st['type'] == 'steel':
            # small chrome centre cap with lug nuts
            prof = [(0.0, 0.0), (0.0, 0.052), (0.010, 0.050), (0.018, 0.040), (0.022, 0.0)]
            a_c = st['a_face'] - st.get('dome', 0.012) * 0 - 0.004
            Vc, Fc, _ = revolve([(a_c + p[0], p[1]) for p in prof], 28)
            Nc = vertex_normals(Vc, Fc)
            if np.mean(Nc[:, 0]) < 0: Fc = Fc[:, ::-1].copy(); Nc = -Nc
            Vm, Nm = W.to_model(Vc, Nc, centre, side)
            parts.add(node, Vm, Fc if side > 0 else Fc[:, ::-1], 'chrome', N=Nm)
        if st['type'] == 'alloy':
            prof = [(0.0, 0.0), (0.0, 0.034), (0.004, 0.033), (0.007, 0.028), (0.008, 0.0)]
            a_hub = st['alloy']['a_face'] - st['alloy']['dish'] + 0.006
            Vc, Fc, _ = revolve([(a_hub - 0.003 + p[0], p[1]) for p in prof], 24)
            Nc = vertex_normals(Vc, Fc)
            if np.mean(Nc[:, 0]) < 0: Fc = Fc[:, ::-1].copy(); Nc = -Nc
            Vm, Nm = W.to_model(Vc, Nc, centre, side)
            parts.add(node, Vm, Fc if side > 0 else Fc[:, ::-1], 'chrome', N=Nm)
        out[node] = centre
    return out
