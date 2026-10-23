"""Three-spoke 15" alloy in the manner of the classic Saab 900 SPG/Aero wheel (broad, slightly swept spokes, three large
rounded-triangle openings, flat outer ring, plain domed centre cap; no logo). Generic geometry, built from scratch.
add_wheels() mirrors wheels90.add_wheels (same node / material contract) but uses this rim.
Local wheel frame: a = axial (outboard +), (y, z) radial.  Node origin = hub centre."""
import numpy as np
from carlib import mc_mesh, decimate, field_normals, fix_winding, project_to_surface, revolve, vertex_normals, smin, smax, sstep
import wheels as W

def rim_field(st):
    R_lip, R_in, aw = st['r_lip'], st['r_barrel'], st['width'] / 2
    a_face, dish, t = st['a_face'], st['dish'], st.get('thick', 0.011)
    r0, r1 = st['open_r0'], st['open_r1']
    sweep = st.get('sweep', 2.2)
    def field(a, y, z):
        r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
        d_barrel = np.maximum(np.abs(r - (R_in + 0.006)) - 0.006, np.abs(a + 0.01) - (aw - 0.01))
        d_lip = np.sqrt(np.maximum(np.abs(a - (aw - 0.014)) - 0.008, 0) ** 2 + np.maximum(np.abs(r - (R_lip - 0.016)) - 0.014, 0) ** 2) - 0.004
        # face: shallow dish toward the hub, gentle roll into the lip
        u = np.clip(r / R_in, 0, 1)
        af = a_face - dish * (1 - u) ** 2 - 0.006 * sstep(0.9, 1.0, u)
        d_face = smax(np.abs(a - af) - t, r - (R_in + 0.010), 0.004)
        # three openings between swept spokes
        sector = 2 * np.pi / 3
        loc = (th - sweep * (r - r0) + sector / 2) % sector - sector / 2      # angle from the opening centre
        half_open = sector / 2 * r - (st['spoke_w0'] + (st['spoke_w1'] - st['spoke_w0']) * np.clip((r - r0) / (r1 - r0), 0, 1))
        o = np.abs(loc) * r - half_open
        o = smax(smax(o, r - r1, 0.018), r0 - r, 0.014)
        d = smax(d_face, -o, 0.004)
        # spoke edge bevel: faces near the openings sit a little inboard (soft chamfer read)
        d = d + 0.003 * np.exp(-(o / 0.006) ** 2) * (a > af - 0.002)
        # centre cap (plain dome)
        d_cap = smax(r - st['cap_r'], np.maximum(a - (a_face - dish + 0.010 + 0.006 * (1 - (r / st['cap_r']) ** 2)), (a_face - dish - 0.02) - a), 0.004)
        d = smin(d, d_cap, 0.005)
        d = smin(d, d_barrel, 0.006)
        d = smin(d, d_lip, 0.004)
        return d
    return field

def rim_mesh(st, res=0.0022, target=1200):
    R = st['r_lip'] + 0.01; aw = st['width'] / 2 + 0.012
    f = rim_field(st)
    V, F = mc_mesh(f, (-aw, -R, -R), (aw, R, R), res, slab=16)
    V, F = decimate(V, F, target)
    V = project_to_surface(f, V, iters=4, h=0.0008)
    N = field_normals(f, V, h=0.0012)
    F = fix_winding(V, F, N)
    return V, F, N

def back_plate(st, n_seg=36):
    a = st['a_face'] - st['dish'] - 0.05; R = st['r_barrel']
    V, F, _ = revolve([(a, 0.0), (a, R), (a - 0.07, R)], n_seg)
    N = vertex_normals(V, F)
    if np.mean(N[:, 0]) < 0:
        F = F[:, ::-1].copy(); N = -N
    return V, F, N

def add_wheels(parts, axles, r_out, r_bead, width, st, tyre_seg=48, target=3000):
    """Same signature as wheels90.add_wheels; st = dict(type='saab3', rim=dict(...))."""
    rs = st['rim']
    rim = rim_mesh(rs, target=target)
    back = back_plate(rs)
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
        ca = np.ones((len(Vr), 3)) * (0.18 + 0.82 * sstep(rs['a_face'] - rs['dish'] - 0.04, rs['a_face'] - rs['dish'] + 0.004, Vr[:, 0]))[:, None]
        dust = st.get('dust', 0.12) * sstep(0.6 * r_bead, r_bead, rr)
        ca = ca * (1 - dust[:, None]) + dust[:, None] * np.array([0.45, 0.37, 0.28])
        Vm, Nm = W.to_model(Vr, Nr, centre, side)
        parts.add(node, Vm, Fr if side > 0 else Fr[:, ::-1], 'rim', N=Nm, COL=np.c_[ca, np.ones(len(ca))])
        Vb, Fb, Nb = back
        Vm, Nm = W.to_model(Vb, Nb, centre, side)
        parts.add(node, Vm, Fb if side > 0 else Fb[:, ::-1], 'trim_black', N=Nm, COL=np.c_[np.full((len(Vb), 3), 0.3), np.ones(len(Vb))])
        out[node] = centre
    return out
