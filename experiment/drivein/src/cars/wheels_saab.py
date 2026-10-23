"""Saab 9000 Aero "Super Aero" style 16" alloy (generic, no centre-cap logo): three broad, slightly swept
propeller spokes leaving three curved-triangle windows, a flat polished outer lip, a big plain centre cap.
Local wheel frame as wheels90: a = axial (outboard +), (y, z) radial, metres.  Used via wheel type 'custom'.
"""
import numpy as np
from carlib import mc_mesh, decimate, field_normals, fix_winding, project_to_surface, smin, smax, sstep

ST = dict(
    a_face=0.074,     # outboard face of the polished lip
    r_lip=0.212,      # outer edge of the lip (sits over the tyre bead)
    r_lip_in=0.180,   # inner edge of the lip, step down into the spoke face
    r_cap=0.072,      # plain centre cap
    win_r0=0.090, win_r1=0.170,               # radial span of the windows
    win_w0=np.deg2rad(5.0), win_w1=np.deg2rad(31.0),   # angular half width of a window at r0 / r1
    swirl=np.deg2rad(24.0),                    # windows sweep this far around between r0 and r1
    phase=np.deg2rad(90.0),
)

def super_aero_field(st=ST):
    af = st['a_face']
    def field(a, y, z):
        r = np.sqrt(y * y + z * z); th = np.arctan2(z, y)
        t = np.clip((r - st['r_cap']) / (st['r_lip_in'] - st['r_cap']), 0, 1)
        # spoke face: hub proud, falling gently toward the lip (slightly convex propeller face)
        a_sp = af - 0.010 - 0.020 * t ** 1.3
        d_face = smax(a - a_sp, (a_sp - 0.014) - a, 0.003)
        d_face = smax(d_face, r - (st['r_lip_in'] + 0.008), 0.004)
        # windows: curved triangles, narrow at the hub, wide at the rim, swept around
        tw = np.clip((r - st['win_r0']) / (st['win_r1'] - st['win_r0']), 0, 1)
        sector = 2 * np.pi / 3
        phc = st['phase'] + st['swirl'] * tw ** 1.4
        loc = (th - phc + sector / 2) % sector - sector / 2
        hw = st['win_w0'] + (st['win_w1'] - st['win_w0']) * tw ** 0.85
        # asymmetric: leading edge nearly straight, trailing edge bowed (scimitar look)
        bow = 0.10 * np.sin(np.pi * tw)
        d_ang = (np.abs(loc + bow * np.sign(loc) * (loc > 0)) - hw) * np.maximum(r, 0.03)
        d_rad = np.maximum(st['win_r0'] - r, r - st['win_r1'])
        d_win = smax(d_ang, d_rad, 0.016)
        d_face = smax(d_face, -d_win, 0.005)
        # polished outer lip: flat ring with rounded edges, a step proud of the spoke face
        d_lip = np.sqrt(np.maximum(np.abs(a - (af - 0.010)) - 0.007, 0) ** 2
                        + np.maximum(np.abs(r - 0.5 * (st['r_lip'] + st['r_lip_in'])) - 0.5 * (st['r_lip'] - st['r_lip_in']) + 0.003, 0) ** 2) - 0.003
        # barrel behind the lip
        d_bar = np.maximum(np.abs(r - 0.196) - 0.005, np.abs(a - (af - 0.085)) - 0.075)
        # centre cap: plain, slightly domed disc proud of the spokes, with a thin step ring
        a_cap = af - 0.002 - 0.006 * (r / st['r_cap']) ** 2
        d_cap = smax(r - st['r_cap'], smax(a - a_cap, (a_cap - 0.03) - a, 0.003), 0.004)
        d = smin(d_face, d_lip, 0.004)
        d = smin(d, d_cap, 0.003)
        d = np.minimum(d, d_bar)
        return d
    return field

def super_aero_mesh(target=9000, res=0.0018, st=ST):
    f = super_aero_field(st)
    R = st['r_lip'] + 0.008
    V, F = mc_mesh(f, (st['a_face'] - 0.165, -R, -R), (st['a_face'] + 0.012, R, R), res, slab=16)
    V, F = decimate(V, F, target)
    V = project_to_surface(f, V, iters=3, h=0.0008)
    N = field_normals(f, V, h=0.0010)
    F = fix_winding(V, F, N)
    return V, F, N

if __name__ == '__main__':
    # quick face-on check of the window shape (no Blender needed)
    import sys
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    f = super_aero_field()
    g = np.linspace(-0.22, 0.22, 400); Y, Z = np.meshgrid(g, g)
    hit = np.full(Y.shape, np.nan)
    for a in np.linspace(ST['a_face'] + 0.01, ST['a_face'] - 0.06, 120):
        d = f(np.full(Y.shape, a), Y, Z)
        m = (d < 0) & np.isnan(hit); hit[m] = a
    plt.figure(figsize=(5, 5)); plt.imshow(hit, origin='lower', cmap='gray', extent=[-0.22, 0.22, -0.22, 0.22])
    plt.savefig(sys.argv[1] if len(sys.argv) > 1 else 'wheel_face.png', dpi=90)
