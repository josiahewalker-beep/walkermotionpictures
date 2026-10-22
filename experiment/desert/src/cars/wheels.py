"""Wheels: tyre (revolved, tread grooves + normal-mapped sipes/sidewall), alloy rim (implicit, marching cubes),
brake disc + hat, caliper. Local wheel frame: a = axial (outboard +), (y, z) radial; returned in model frame via place().
"""
import numpy as np
from carlib import (revolve, mc_mesh, decimate, field_normals, fix_winding, normalize, smin, smax, sstep,
                    vertex_normals)

def tyre_profile(r_out, r_bead, width, grooves=4, sidewall_bulge=0.012):
    hw = width / 2
    side_h = r_out - r_bead
    pts = []
    # inner bead -> inner sidewall -> tread -> outer sidewall -> outer bead (a from -hw to +hw)
    def side(sign):
        sp = []
        for t in np.linspace(0, 1, 9):
            r = r_bead + t * (side_h - 0.012)
            bul = sidewall_bulge * np.sin(np.pi * np.clip(t * 1.05, 0, 1)) ** 0.8
            a = sign * (hw - 0.012 + bul - 0.008 * t)
            sp.append((a, r))
        return sp
    inner = side(-1)
    pts += inner
    # shoulder round
    for ang in np.linspace(np.pi, np.pi / 2, 6)[1:]:
        pts.append((-hw + 0.022 + 0.026 * np.cos(ang) * 0.75, r_out - 0.016 + 0.016 * np.sin(ang)))
    # tread with grooves
    ta = -hw + 0.022
    tb = hw - 0.022
    gpos = np.linspace(ta, tb, grooves + 2)[1:-1]
    gw = 0.009; gd = 0.007
    xs = [ta]
    for g in gpos:
        xs += [g - gw / 2 - 0.001, g - gw / 2, g + gw / 2, g + gw / 2 + 0.001]
    xs.append(tb)
    for i, x in enumerate(xs):
        r = r_out
        if i > 0 and i < len(xs) - 1 and (i - 1) % 4 in (1, 2):
            r = r_out - gd
        pts.append((x, r))
    for ang in np.linspace(np.pi / 2, 0, 6)[:-1]:
        pts.append((hw - 0.022 + 0.026 * np.cos(ang) * 0.75, r_out - 0.016 + 0.016 * np.sin(ang)))
    pts += side(1)[::-1]
    # close inside (hidden)
    pts.append((hw - 0.02, r_bead - 0.004))
    pts.append((-hw + 0.02, r_bead - 0.004))
    return np.array(pts)

def tyre_mesh(r_out, r_bead, width, n_seg=72):
    P = tyre_profile(r_out, r_bead, width)
    # revolve: profile (a, r); revolve gives V (a, r cos, r sin)
    V, F, UV = revolve(P, n_seg, closed_profile=True)
    N = vertex_normals(V, F)
    # make sure normals point outward (away from the axis on tread)
    tread = np.abs(V[:, 0]) < width * 0.3
    rad = V[:, 1:] / np.maximum(np.linalg.norm(V[:, 1:], axis=1, keepdims=True), 1e-9)
    if np.mean(np.einsum('ij,ij->i', N[tread][:, 1:], rad[tread])) < 0:
        F = F[:, ::-1].copy(); N = -N
    # UVs: u around (repeat 24x for tread texture), v across the profile
    UV = UV.copy(); UV[:, 0] *= 24
    # vertex colour: slight dust toward tread, darker in grooves
    r = np.linalg.norm(V[:, 1:], axis=1)
    col = np.ones((len(V), 3))
    col = col * (0.85 + 0.15 * sstep(r_out - 0.03, r_out, r))[:, None]
    col[r < r_out - 0.004] *= 1.0
    return V, F, N, UV, np.clip(col, 0, 1)

def tyre_textures(size=1024):
    """Normal map for the tyre: tread sipes/blocks on the crown, ribs + faint lettering-free bands on sidewalls.
    UV v runs across the profile (0..1), u around (tiled 24x)."""
    h = w = size
    v = np.linspace(0, 1, h)[:, None]
    u = np.linspace(0, 1, w)[None, :]
    height = np.zeros((h, w))
    # find tread band by v (profile index fraction): crown roughly in the middle 34%..66%
    crown = sstep(0.30, 0.34, v) * (1 - sstep(0.66, 0.70, v))
    # diagonal sipes
    sipe = np.abs(((u * 6 + (v - 0.5) * 1.6) % 1.0) - 0.5)
    height -= crown * (sipe < 0.035) * 0.9
    # block edges near shoulders
    shoulder = (sstep(0.30, 0.33, v) * (1 - sstep(0.36, 0.38, v))) + (sstep(0.62, 0.64, v) * (1 - sstep(0.67, 0.70, v)))
    slot = np.abs(((u * 3) % 1.0) - 0.5) < 0.06
    height -= shoulder * slot * 1.2
    # sidewall: fine concentric ribs near the rim, a raised band (rim protector)
    sw = (1 - sstep(0.26, 0.30, v)) + sstep(0.70, 0.74, v)
    ribs = 0.15 * np.sin(v * 900) * (sw > 0.5)
    band = 0.6 * (np.exp(-((v - 0.07) / 0.012) ** 2) + np.exp(-((v - 0.93) / 0.012) ** 2))
    height += ribs + band
    from scipy import ndimage
    height = ndimage.gaussian_filter(height, 1.0)
    gy, gx = np.gradient(height)
    s = 3.0
    n = normalize(np.stack([-gx * s, gy * s, np.ones_like(height)], -1))
    nrm = n * 0.5 + 0.5
    rough = np.ones((h, w, 3)) * 0.85
    rough[..., 1] = 0.82 + 0.1 * (crown > 0.5)
    return nrm, rough

def rim_field(style):
    """Returns field(a, y, z) for the alloy rim, in local wheel coords (a outboard)."""
    R_lip = style['r_lip']; R_in = style['r_barrel']; aw = style['width'] / 2
    n_sp = style['spokes']; split = style.get('split', 0.0)
    a_face = style['a_face']; dish = style['dish']
    def field(a, y, z):
        r = np.sqrt(y * y + z * z)
        th = np.arctan2(z, y)
        # barrel (thin wall cylinder) from inboard to just behind the lip
        d_barrel = np.maximum(np.abs(r - (R_in + 0.006)) - 0.006, np.abs(a + 0.01) - (aw - 0.01))
        # outboard lip ring, rounded
        lip_c = np.array([aw - 0.012, R_lip - 0.012])
        d_lip = np.sqrt(np.maximum(np.abs(a - (aw - 0.014)) - 0.008, 0) ** 2 + np.maximum(np.abs(r - (R_lip - 0.016)) - 0.014, 0) ** 2) - 0.004
        # spoke face height: concave dish, hub sits outboard
        tt = np.clip((r - 0.075) / (R_in - 0.075), 0, 1)
        af = a_face - dish * (1 - tt) ** 1.5
        ab = af - style['spoke_depth'] * (0.7 + 0.3 * tt)
        sector = 2 * np.pi / n_sp
        local = (th + sector / 2) % sector - sector / 2
        if split > 0:
            # twin spokes: two thin bars per sector, joining near the hub
            off = split * sstep(0.09, 0.16, r)
            ang_d = np.minimum(np.abs(local - off / np.maximum(r, 0.05)), np.abs(local + off / np.maximum(r, 0.05))) * r
        else:
            ang_d = np.abs(local) * r
        hw = style['spoke_w0'] + (style['spoke_w1'] - style['spoke_w0']) * tt
        d_sp_ang = ang_d - hw
        d_sp_a = np.maximum(a - af, ab - a)
        d_sp_r = np.maximum(r - (R_in + 0.008), 0.07 - r)
        d_spoke = smax(smax(d_sp_ang, d_sp_a, 0.004), d_sp_r, 0.004)
        # hub
        a_hub = a_face - dish + 0.006
        d_hub = smax(r - 0.095, np.maximum(a - a_hub, (a_hub - 0.06) - a), 0.006)
        # lug holes (5) and centre bore
        lug = None
        for k in range(5):
            ang = 2 * np.pi * k / 5 + np.pi / 10
            cy, cz = 0.057 * np.cos(ang), 0.057 * np.sin(ang)
            dl = np.sqrt((y - cy) ** 2 + (z - cz) ** 2) - 0.011
            lug = dl if lug is None else np.minimum(lug, dl)
        d_hub = smax(d_hub, -np.maximum(lug, -(a - (a_hub - 0.012))), 0.002)
        d_hub = smax(d_hub, -(0.034 - r), 0.002)
        # back plate between spokes near hub (mounting face)
        d = smin(d_spoke, d_hub, 0.010)
        d = smin(d, d_barrel, 0.006)
        d = smin(d, d_lip, 0.004)
        # spoke-lip join
        return d
    return field

def rim_mesh(style, res=0.0022, target=8000):
    R = style['r_lip'] + 0.01; aw = style['width'] / 2 + 0.012
    f = rim_field(style)
    fld = lambda X, Y, Z: f(X, Y, Z)
    V, F = mc_mesh(fld, (-aw, -R, -R), (aw, R, R), res, slab=16)
    V, F = decimate(V, F, target)
    N = field_normals(fld, V, h=0.0012)
    F = fix_winding(V, F, N)
    return V, F, N

def disc_mesh(r_disc, r_hat=0.085, a0=-0.055, thick=0.03, n_seg=72):
    # disc ring profile (closed) in (a, r)
    P = [(a0 - thick / 2, r_hat + 0.012), (a0 - thick / 2, r_disc), (a0 + thick / 2, r_disc), (a0 + thick / 2, r_hat + 0.015),
         (a0 + thick / 2 + 0.002, r_hat), (0.045, r_hat - 0.004), (0.045, 0.035), (0.040, 0.030), (a0 + thick / 2 - 0.006, r_hat - 0.010)]
    V, F, UV = revolve(P, n_seg, closed_profile=True)
    N = vertex_normals(V, F)
    # orient outward-ish: check rim face (r max) normals radial
    rr = np.linalg.norm(V[:, 1:], axis=1)
    m = rr > r_disc - 0.001
    if m.any() and np.mean(np.einsum('ij,ij->i', N[m][:, 1:], V[m][:, 1:] / rr[m][:, None])) < 0:
        F = F[:, ::-1].copy(); N = -N
    # planar UV on the disc face
    UV = np.stack([V[:, 1] / (2 * r_disc) + 0.5, V[:, 2] / (2 * r_disc) + 0.5], 1)
    return V, F, N, UV

def disc_texture(r_disc, size=512):
    h = w = size
    y, z = np.meshgrid(np.linspace(-r_disc, r_disc, w), np.linspace(-r_disc, r_disc, h))
    r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
    base = 0.42 + 0.04 * np.sin(r * 2200) * 0.3
    # cross-drilled holes in 3 rows, 12 around
    holes = np.zeros_like(r)
    for row, rr in enumerate([r_disc * 0.62, r_disc * 0.74, r_disc * 0.86]):
        for k in range(12):
            ang = 2 * np.pi * k / 12 + row * 0.18
            hy, hz = rr * np.cos(ang), rr * np.sin(ang)
            holes = np.maximum(holes, (np.sqrt((y - hy) ** 2 + (z - hz) ** 2) < 0.0045).astype(float))
    hub = r < 0.105
    col = np.where(holes > 0, 0.06, base)
    col = np.where(hub, 0.18, col)
    # rust/heat tint at the outer edge, dust
    rgb = np.stack([col * 1.05, col * 0.98, col * 0.92], -1)
    edge = sstep(r_disc * 0.93, r_disc, r)[..., None]
    rgb = rgb * (1 - 0.4 * edge) + edge * 0.4 * np.array([0.30, 0.17, 0.10])
    return np.clip(rgb, 0.03, 0.9)

def caliper_field(r_c0, r_c1, span, a_in, a_out, ang_c):
    def f(a, y, z):
        r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
        dth = (th - ang_c + np.pi) % (2 * np.pi) - np.pi
        d_ang = np.abs(dth) * r - span / 2 * r
        d_r = np.maximum(r - r_c1, r_c0 - r)
        d_a = np.maximum(a - a_out, a_in - a)
        d = smax(smax(d_ang, d_r, 0.012), d_a, 0.010)
        return d
    return f

def caliper_mesh(r_disc, a_disc, ang_c, target=1400):
    f = caliper_field(r_disc - 0.05, r_disc + 0.025, 0.95, a_disc - 0.045, a_disc + 0.04, ang_c)
    R = r_disc + 0.04
    V, F = mc_mesh(lambda X, Y, Z: f(X, Y, Z), (a_disc - 0.06, -R, -R), (a_disc + 0.06, R, R), 0.004, slab=16)
    V, F = decimate(V, F, target)
    N = field_normals(lambda x, y, z: f(x, y, z), V, h=0.002)
    F = fix_winding(V, F, N)
    return V, F, N

def to_model(V, N, centre, side):
    """local (a, y, z) -> model (x, s, z). side=+1 for model x>0 (outboard +x), -1 for x<0.
    local y maps to model s (forward), z to up."""
    Vm = np.stack([side * V[:, 0], V[:, 1], V[:, 2]], 1) + np.asarray(centre)
    Nm = np.stack([side * N[:, 0], N[:, 1], N[:, 2]], 1)
    return Vm, Nm

def add_wheels(parts, axles, track_half, r_out, r_bead, width, rim_style, disc_r, caliper=True, tyre_w_rear=None,
               cache=None):
    """axles: dict name->(s, x_half). Adds nodes wheel_FL etc. Calipers go to node 'body'."""
    import copy
    rim = rim_mesh(rim_style)
    out = {}
    for (name, s, xh, w) in axles:
        side = 1 if name.endswith('R') else -1   # FR, RR on model +x (glTF -X, car's right)
        centre = (side * xh, s, r_out)
        node = 'wheel_' + name
        Vt, Ft, Nt, UVt, Ct = tyre_mesh(r_out, r_bead, w)
        Vm, Nm = to_model(Vt, Nt, centre, side)
        Fm = Ft if side > 0 else Ft[:, ::-1]
        parts.add(node, Vm, Fm, 'rubber', N=Nm, UV=UVt, COL=np.c_[Ct, np.ones(len(Ct))])
        Vr, Fr, Nr = rim
        sc = np.array([1, 1, 1.0]); Vr2 = Vr.copy(); Vr2[:, 0] = Vr[:, 0] * (w / rim_style['width'])
        Vm, Nm = to_model(Vr2, Nr, centre, side)
        rr = np.linalg.norm(Vr[:, 1:], axis=1)
        ca = np.ones((len(Vr), 3))
        # baked cavity darkening toward the inboard barrel, brake dust tint on the face
        ca *= (0.35 + 0.65 * sstep(-0.10, 0.06, Vr[:, 0]))[:, None]
        dust = 0.18 * sstep(0.15, 0.25, rr)
        ca = ca * (1 - dust[:, None]) + dust[:, None] * np.array([0.55, 0.45, 0.33])
        parts.add(node, Vm, Fr if side > 0 else Fr[:, ::-1], 'rim', N=Nm, COL=np.c_[ca, np.ones(len(ca))])
        Vd, Fd, Nd, UVd = disc_mesh(disc_r, a0=-0.05)
        Vm, Nm = to_model(Vd, Nd, centre, side)
        parts.add(node, Vm, Fd if side > 0 else Fd[:, ::-1], 'brake', N=Nm, UV=UVd)
        # centre cap
        cap_prof = [(0.0, 0.0), (0.0, 0.0335), (0.004, 0.033), (0.007, 0.028), (0.008, 0.0)]
        a_hub = rim_style['a_face'] - rim_style['dish'] + 0.006
        Vc, Fc, _ = revolve([(a_hub - 0.003 + p[0], p[1]) for p in cap_prof], 32)
        Nc = vertex_normals(Vc, Fc)
        if np.mean(Nc[:, 0]) < 0: Fc = Fc[:, ::-1].copy(); Nc = -Nc
        Vm, Nm = to_model(Vc, Nc, centre, side)
        parts.add(node, Vm, Fc if side > 0 else Fc[:, ::-1], 'chrome', N=Nm)
        if caliper:
            ang = np.deg2rad(165) if s > 0 else np.deg2rad(15)   # behind/above the axle toward the car centre
            ang = np.deg2rad(160) if s > 0 else np.deg2rad(20)
            key = ('cal', disc_r)
            Vc, Fc, Nc = caliper_mesh(disc_r, -0.05, 0.0)
            # rotate around the axle to the chosen angle (front: rear-upper; local y = forward)
            ang = np.deg2rad(150) if s > 0 else np.deg2rad(30)
            c, sn = np.cos(ang), np.sin(ang)
            Rm = np.array([[1, 0, 0], [0, c, -sn], [0, sn, c]])
            Vc2 = Vc @ Rm.T; Nc2 = Nc @ Rm.T
            Vm, Nm = to_model(Vc2, Nc2, centre, side)
            parts.add('body', Vm, Fc if side > 0 else Fc[:, ::-1], 'caliper', N=Nm)
        out[node] = centre
    return out
