"""Saab 9000 Aero "Super Aero" style 16" alloy (generic, no centre-cap logo): three broad, slightly swept
propeller spokes leaving three curved-triangle windows, a flat polished outer lip, a big plain centre cap.
Local wheel frame as wheels90: a = axial (outboard +), (y, z) radial, metres.  Used via wheel type 'custom'.
The spoke face + cap is an implicit field (marching cubes); the lip and barrel are lathe-turned (smooth, cheap).
"""
import numpy as np
from carlib import mc_mesh, decimate, field_normals, fix_winding, project_to_surface, revolve, vertex_normals, smin, smax

ST = dict(
    a_face=0.074,     # outboard face of the polished lip
    r_lip=0.213,      # outer edge of the lip (sits over the tyre bead)
    r_lip_in=0.180,   # inner edge of the lip, step down into the spoke face
    r_cap=0.070,      # plain centre cap
    win_r0=0.088, win_r1=0.171,               # radial span of the windows
    win_w0=np.deg2rad(7.0), win_w1=np.deg2rad(36.0),   # angular half width of a window at r0 / r1
    swirl=np.deg2rad(12.0),                    # windows sweep this far around between r0 and r1
    bow=0.05,                                  # trailing edge bowed a little (scimitar look)
    phase=np.deg2rad(90.0),
)

def face_field(st=ST):
    af = st['a_face']
    def field(a, y, z):
        r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
        t = np.clip((r - st['r_cap']) / (st['r_lip_in'] - st['r_cap']), 0, 1)
        # spoke face: hub proud, falling gently toward the lip
        a_sp = af - 0.008 - 0.022 * t
        d_face = smax(a - a_sp, (a_sp - 0.014) - a, 0.003)
        d_face = smax(d_face, r - (st['r_lip_in'] + 0.007), 0.003)
        # windows: rounded triangles, narrow at the hub, wide at the rim, slightly swept
        tw = np.clip((r - st['win_r0']) / (st['win_r1'] - st['win_r0']), 0, 1)
        sector = 2 * np.pi / 3
        phc = st['phase'] + st['swirl'] * tw
        loc = (th - phc + sector / 2) % sector - sector / 2
        hw = st['win_w0'] + (st['win_w1'] - st['win_w0']) * tw ** 0.9
        bow = st['bow'] * np.sin(np.pi * tw)
        d_ang = (np.abs(loc + bow * (loc > 0)) - hw) * np.maximum(r, 0.03)
        d_rad = np.maximum(st['win_r0'] - r, r - st['win_r1'])
        d_win = smax(d_ang, d_rad, 0.012)
        d_face = smax(d_face, -d_win, 0.004)
        # centre cap: plain, nearly flat disc proud of the spokes
        a_cap = af - 0.001 - 0.003 * (r / st['r_cap']) ** 2
        d_cap = smax(r - st['r_cap'], smax(a - a_cap, (a_cap - 0.03) - a, 0.003), 0.004)
        return smin(d_face, d_cap, 0.002)
    return field

def _lathe(prof, n_seg, outward_a=True):
    V, F, _ = revolve(prof, n_seg)
    N = vertex_normals(V, F)
    return V, F, N

def super_aero_mesh(target=5200, res=0.0016, st=ST, n_seg=96):
    f = face_field(st)
    R = st['r_lip_in'] + 0.012
    V, F = mc_mesh(f, (st['a_face'] - 0.045, -R, -R), (st['a_face'] + 0.006, R, R), res, slab=16)
    V, F = decimate(V, F, target)
    V = project_to_surface(f, V, iters=3, h=0.0008)
    N = field_normals(f, V, h=0.0010)
    F = fix_winding(V, F, N)
    af = st['a_face']; ri, ro = st['r_lip_in'], st['r_lip']
    # polished lip (a, r), from the inner step outward and back round to the tyre bead
    lip = [(af - 0.034, ri - 0.004), (af - 0.010, ri - 0.002), (af - 0.003, ri + 0.002), (af, ri + 0.008),
           (af + 0.0005, 0.5 * (ri + ro)), (af, ro - 0.006), (af - 0.004, ro - 0.001), (af - 0.012, ro), (af - 0.022, ro - 0.006)]
    Vl, Fl, Nl = _lathe(lip, n_seg)
    # orient so the lip's front face points outboard (+a)
    front = Vl[:, 0] > af - 0.002
    if np.mean(Nl[front, 0]) < 0:
        Fl = Fl[:, ::-1].copy(); Nl = -Nl
    # barrel seen through the windows (faces the axis)
    bar = [(af - 0.022, ro - 0.012), (af - 0.06, 0.197), (af - 0.17, 0.197)]
    Vb, Fb, Nb = _lathe(bar, n_seg // 2)
    rr = np.linalg.norm(Vb[:, 1:], axis=1)
    if np.mean(np.einsum('ij,ij->i', Nb[:, 1:], Vb[:, 1:] / rr[:, None])) > 0:
        Fb = Fb[:, ::-1].copy(); Nb = -Nb
    Vs = np.concatenate([V, Vl, Vb]); Ns = np.concatenate([N, Nl, Nb])
    Fs = np.concatenate([F, Fl + len(V), Fb + len(V) + len(Vl)])
    return Vs, Fs, Ns

if __name__ == '__main__':
    # quick face-on check of the window shape (no Blender needed)
    import sys
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    f = face_field()
    g = np.linspace(-0.22, 0.22, 400); Y, Z = np.meshgrid(g, g)
    hit = np.full(Y.shape, np.nan)
    for a in np.linspace(ST['a_face'] + 0.01, ST['a_face'] - 0.06, 120):
        d = f(np.full(Y.shape, a), Y, Z)
        m = (d < 0) & np.isnan(hit); hit[m] = a
    plt.figure(figsize=(5, 5)); plt.imshow(hit, origin='lower', cmap='gray', extent=[-0.22, 0.22, -0.22, 0.22])
    plt.gca().add_patch(plt.Circle((0, 0), ST['r_lip'], fill=False)); plt.gca().add_patch(plt.Circle((0, 0), ST['r_lip_in'], fill=False))
    plt.savefig(sys.argv[1] if len(sys.argv) > 1 else 'wheel_face.png', dpi=90)
