"""Saab 9000 Aero "Super Aero" 16" alloy (1994-98), generic: plain centre cap, no logo.
Measured from the director's close-up (reference 01, unwrapped to polar coordinates about the hub):
- a mostly solid, smooth, slightly dished face: three very broad spokes;
- three curved teardrop slots, 120 deg apart, all sweeping the same way round the wheel: a round head (~72 mm across)
  tapering along the arc over ~78 deg to a thin tail that drifts out toward the rim; each slot sits in a shallow dished
  flank (~18 mm) that catches the light;
- a flat ring r 0.163-0.186 under the slots, a thin bright polished lip r 0.188-0.219;
- a large flat round cap r = 0.075 m, flush with the face, with a fine seam; a valve stem on the ring under one slot.
Local wheel frame as wheels90: a = axial (outboard +), (y, z) radial, metres. Used via wheel type 'custom'.
The face is an implicit field (marching cubes); lip and barrel are lathe-turned.
"""
import numpy as np
from carlib import mc_mesh, decimate, field_normals, fix_winding, project_to_surface, revolve, vertex_normals, smin, smax

ST = dict(
    a_face=0.074,      # outboard face of the polished lip
    r_lip=0.219,       # lip outer edge
    r_lip_in=0.187,    # lip inner edge (step down onto the face ring)
    r_cap=0.075,       # flat centre cap
    # slots (v2.1): curved teardrops, all sweeping the same way round the wheel. The outer edge follows the circle
    # r = 0.164 (as measured on the reference); the inner edge arches in to r ~0.102 near the round head and closes in
    # toward a rounded tail ~66 deg further round.
    slot_span=np.deg2rad(66.0), slot_r_out=0.164, slot_hw=0.031, slot_tail=0.009,
    flank=0.018, flank_depth=0.010,
    dish=0.011,        # face dips this much between cap and ring
    phase=np.deg2rad(150.0),   # head angle of slot 0 (tail runs clockwise from it, as on the reference close-up)
)

def _slot_discs(st=ST, n=44):
    """Disc chain (angle offset, centre radius, radius) whose union is one slot: head at t=0, tail at t=1.
    Discs stay tangent to the outer circle r = slot_r_out, so the outer edge is concentric. Full depth (r_out -> ~0.104)
    over most of the arc, as measured on the reference (58 deg wide at r 0.14), closing only over the last third to a
    rounded tail: a fat teardrop rather than a lens."""
    t = np.linspace(0, 1, n)
    ang = -st['slot_span'] * t
    h0, h1 = st['slot_hw'], st['slot_tail']
    head = h0 * np.sqrt(np.clip(1 - ((0.16 - t) / 0.20) ** 2, 0.25, 1))
    tail = h1 + (h0 - h1) * np.clip((1 - t) / 0.42, 0, 1) ** 0.8
    w = np.where(t < 0.16, head, np.minimum(h0, tail))
    rc = st['slot_r_out'] - w
    return ang, rc, w

def slot_sd(y, z, st=ST):
    """Signed distance (m) to the three teardrop slots in the face plane (union of discs)."""
    ang, rc, w = _slot_discs(st)
    r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
    d = np.full(np.shape(y), 1.0)
    for k in range(3):
        a0 = st['phase'] + k * 2 * np.pi / 3
        cy = rc * np.cos(a0 + ang); cz = rc * np.sin(a0 + ang)
        for i in range(len(rc)):
            if w[i] <= 0: continue
            d = np.minimum(d, np.sqrt((y - cy[i]) ** 2 + (z - cz[i]) ** 2) - w[i])
    return d

def face_field(st=ST):
    af = st['a_face']
    def field(a, y, z):
        r = np.sqrt(y * y + z * z)
        t = np.clip((r - st['r_cap']) / (st['r_lip_in'] - st['r_cap']), 0, 1)
        a_top = af - 0.007 - st['dish'] * np.sin(np.pi * t) ** 1.2
        ds = slot_sd(y, z, st)
        fl = np.clip(1 - ds / st['flank'], 0, 1)
        a_top = a_top - st['flank_depth'] * fl ** 2
        d_face = smax(a - a_top, (a_top - 0.016) - a, 0.003)
        d_face = smax(d_face, r - (st['r_lip_in'] - 0.004), 0.002)
        d_face = smax(d_face, -ds, 0.004)
        # flat cap, flush with the face around it, fine seam groove at its edge
        a_cap = af - 0.006
        d_cap = smax(r - (st['r_cap'] - 0.0025), smax(a - a_cap, (a_cap - 0.03) - a, 0.002), 0.003)
        seam = smax(np.abs(r - st['r_cap']) - 0.0018, a - (a_cap - 0.003), 0.001)
        return smax(smin(d_face, d_cap, 0.0015), -seam, 0.001)
    return field

def _lathe(prof, n_seg):
    V, F, _ = revolve(prof, n_seg)
    return V, F, vertex_normals(V, F)

def super_aero_mesh(target=5200, res=0.0015, st=ST, n_seg=96):
    f = face_field(st)
    R = st['r_lip_in'] + 0.012
    V, F = mc_mesh(f, (st['a_face'] - 0.05, -R, -R), (st['a_face'] + 0.004, R, R), res, slab=16)
    # drop the hidden back of the face slab (never seen) so the decimation budget goes to the visible face
    Nf = field_normals(f, V[F].mean(1), h=0.0010)
    F = F[Nf[:, 0] > -0.35]
    from carlib import clean_unused
    V, F = clean_unused(V, F)[:2]
    V, F = decimate(V, F, target)
    V = project_to_surface(f, V, iters=3, h=0.0008)
    N = field_normals(f, V, h=0.0010)
    F = fix_winding(V, F, N)
    af = st['a_face']; ri, ro = st['r_lip_in'], st['r_lip']
    lip = [(af - 0.030, ri - 0.013), (af - 0.011, ri - 0.011), (af - 0.0045, ri - 0.0065), (af - 0.0015, ri - 0.002), (af - 0.0002, ri + 0.004),
           (af, 0.5 * (ri + ro)), (af - 0.0005, ro - 0.004), (af - 0.004, ro - 0.0005), (af - 0.012, ro), (af - 0.022, ro - 0.007)]
    Vl, Fl, Nl = _lathe(lip, n_seg)
    front = Vl[:, 0] > af - 0.002
    if np.mean(Nl[front, 0]) < 0:
        Fl = Fl[:, ::-1].copy(); Nl = -Nl
    bar = [(af - 0.022, ro - 0.014), (af - 0.06, 0.197), (af - 0.17, 0.197)]
    Vb, Fb, Nb = _lathe(bar, n_seg // 2)
    rr = np.linalg.norm(Vb[:, 1:], axis=1)
    if np.mean(np.einsum('ij,ij->i', Nb[:, 1:], Vb[:, 1:] / rr[:, None])) > 0:
        Fb = Fb[:, ::-1].copy(); Nb = -Nb
    # valve stem: short rubber-capped post on the face ring under one slot
    phi = st['phase'] + np.deg2rad(22.0)
    rs = 0.173
    prof = [(af - 0.012, 0.0), (af - 0.012, 0.0045), (af + 0.006, 0.0045), (af + 0.010, 0.0035), (af + 0.011, 0.0)]
    Vs, Fs, Ns = _lathe(prof, 10)
    Vs = Vs + np.array([0.0, rs * np.cos(phi), rs * np.sin(phi)])
    if np.mean(Ns[:, 0]) < 0: Fs = Fs[:, ::-1].copy(); Ns = -Ns
    parts = [(V, F, N), (Vl, Fl, Nl), (Vb, Fb, Nb), (Vs, Fs, Ns)]
    Vo, Fo, No, off = [], [], [], 0
    for v, fa, n in parts:
        Vo.append(v); Fo.append(fa + off); No.append(n); off += len(v)
    return np.concatenate(Vo), np.concatenate(Fo), np.concatenate(No)

if __name__ == '__main__':
    # face-on depth map check (no Blender needed)
    import sys
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    f = face_field()
    g = np.linspace(-0.225, 0.225, 500); Y, Z = np.meshgrid(g, g)
    hit = np.full(Y.shape, np.nan)
    for a in np.linspace(ST['a_face'] + 0.005, ST['a_face'] - 0.05, 160):
        d = f(np.full(Y.shape, a), Y, Z)
        m = (d < 0) & np.isnan(hit); hit[m] = a
    plt.figure(figsize=(6, 6)); plt.imshow(hit, origin='lower', cmap='gray', extent=[-0.225, 0.225, -0.225, 0.225])
    for r in (ST['r_lip'], ST['r_lip_in']): plt.gca().add_patch(plt.Circle((0, 0), r, fill=False, color='y'))
    plt.savefig(sys.argv[1] if len(sys.argv) > 1 else 'wheel_face.png', dpi=90)
