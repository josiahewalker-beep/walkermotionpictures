"""Hero Saab 9000 Aero (1994-98 CS) rear end, kept separate so it can be redone on its own.
Read from the director's year-correct set (02 tail-lamp close-up, 10 straight rear, 03/05/06/11 rear 3/4s), lights OFF:

- full-width lamp band at z 0.818-1.000 across hatch and quarters: outer lamps |x| 0.567-0.84, wedge-shaped, wrapping
  the corner with a sweeping outboard edge (side view: from s -2.108 at the top back to -2.242 at the bottom), split
  into an upper smoked section (amber behind the smoke) and a lower red section at z 0.915;
- centre panel on the hatch between them: upper half smoked black, lower half red, a clear-ish reverse lens right of
  centre (passenger side, x 0.32-0.46);
- body-colour plate recess below the band, plate centred at z 0.72 (blank plate);
- black Aero spoiler blade across the hatch at the top edge of the lower panel (z ~1.07-1.10), short mounts, body-colour
  end caps, rear edge kicked up;
- third brake light: a separate black pod with a red lens at the top of the rear window, on the roof edge.
Model frame: x lateral (x < 0 driver), s forward, z up, metres.
"""
import numpy as np
from carlib import sd_round_box, smin, smax
import details as D

LAMP_X0, LAMP_X1 = 0.567, 0.845          # outer lamp inner edge / outer extent (|x|)
LAMP_Z0, LAMP_Z1 = 0.815, 1.000          # band bottom / top
SPLIT_Z = 0.915                          # smoked above, red below
PANEL_Z0, PANEL_Z1 = 0.822, 0.995        # centre panel
REV = (0.32, 0.46, 0.838, 0.902)         # reverse lens (x signed: passenger side +), z
# Corner wrap seen from the side (04 / 08): the lens runs round the corner onto the quarter panel; its bottom edge stays level
# at LAMP_Z0 and its front edge sweeps down from the top-rear corner to a pointed tip at the bottom (a teardrop / wedge in side
# view). Measured on 04 against the rim (977 px/m): ~0.145 m long on the flat quarter at its level bottom edge, ~0.16 m
# tall at the corner. Front edge as (z, s offset forward of the centre-line tail profile Lr(z)); the plan corner takes ~0.10.
WRAP_EDGE = ((0.815, 0.250), (0.835, 0.240), (0.870, 0.222), (0.910, 0.196), (0.945, 0.162), (0.975, 0.118), (1.000, 0.072))
TAIL_PROFILE = None                      # Lr(z): set by the car config (centre-line tail face s at height z)
RECESS = (0.53, 0.625, 0.812)            # plate recess half width, z0, z1
PLATE_Z = 0.718

def lamp_fns(plane_fn, MaskSDF):
    """-> (fn_tail, fn_tpanel, fn_rev) for car90's rear_lamp_fns hook."""
    we = np.array(WRAP_EDGE)
    def s_edge(z):
        return TAIL_PROFILE(z) + np.interp(z, we[:, 0], we[:, 1])
    rear = lambda V, N: (V[:, 1] < -1.95) & (N[:, 1] < 0.45) & (V[:, 2] > 0.6) & (V[:, 2] < 1.12)
    base = plane_fn(lambda X, Z: (X > LAMP_X0) & (Z > LAMP_Z0) & (Z < LAMP_Z1 - 0.012 * np.clip((X - LAMP_X0) / 0.27, 0, 1)), rear, rnd=0.012)
    def fn_tail(V, N):
        d = base(V, N)
        return np.where(d < 0.9, np.maximum(d, V[:, 1] - s_edge(V[:, 2])), d)
    rear_face = lambda V, N: (V[:, 1] < -2.0) & (N[:, 1] < -0.3)
    fn_tpanel = plane_fn(lambda X, Z: (X < LAMP_X0 - 0.014) & (Z > PANEL_Z0) & (Z < PANEL_Z1), rear_face, rnd=0.008)
    fn_rev = plane_fn(lambda X, Z: (X > REV[0]) & (X < REV[1]) & (Z > REV[2]) & (Z < REV[3]), rear_face, rnd=0.006, mirror=False)
    return fn_tail, fn_tpanel, fn_rev

def fn_split(V, N):
    return np.where(V[:, 1] < -1.95, V[:, 2] - SPLIT_Z, 1.0)

def recess_fn(plane_fn, MaskSDF):
    rear_face = lambda V, N: (V[:, 1] < -2.0) & (N[:, 1] < -0.3)
    return plane_fn(lambda X, Z: (X < RECESS[0]) & (Z > RECESS[1]) & (Z < RECESS[2]), rear_face, rnd=0.02)

def cuts_labels_rules(plane_fn, MaskSDF):
    """Extra cuts / labels / rules (rules take priority over car90's own)."""
    fn_rec = recess_fn(plane_fn, MaskSDF)
    cuts = [('tsplit', fn_split, [0.0]), ('recess', fn_rec, [0.0])]
    labels = {
        'tail_smoke': dict(mat='light_marker', depth=0.006, wall='trim_black', wall_col=0.4, col=0.22),
        'panel_smoke': dict(mat='light_rear', depth=0.004, wall='trim_black', wall_col=0.4, col=0.10),
        'panel_red': dict(mat='light_rear', depth=0.004, wall='trim_black', wall_col=0.5, col=0.85),
        'recess': dict(mat='paint', depth=0.016, wall='paint', wall_col=0.55, col=0.92),
    }
    rules = [
        ('tail_smoke', lambda fm: (fm['tail'] < -0.006) & (fm['tsplit'] > 0)),
        ('panel_smoke', lambda fm: (fm['tpanel'] < 0) & (fm['tsplit'] > 0) & (fm['rev'] > 0)),
        ('panel_red', lambda fm: (fm['tpanel'] < 0) & (fm['rev'] > 0)),
        ('recess', lambda fm: (fm['recess'] < 0) & (fm['rplate'] > 0)),
    ]
    return cuts, labels, rules

# ------------------------------------------------------------------------------------------------ add-on parts
def aero_spoiler(parts, B, f, L):
    """Black Aero blade sitting on the hatch at the base of the glass: a wedge section (thin leading edge on the hatch,
    thick trailing edge just past the tail face, upper surface rising rearward), ~0.055 m tall seen from behind, full
    width with the ends dropping into body-colour end caps."""
    h = D.ray_hit(f, (0.0, -2.10, 2.0), (0, 0, -1), tmax=1.5)
    zd = h[2] if h is not None else 1.045
    s_le, s_te = -2.020, -2.262          # leading / trailing edge
    half = 0.725
    def fld(x, s, z):
        ax = np.abs(x)
        drop = 0.030 * np.clip((ax - 0.62) / (half - 0.62), 0, 1) ** 2
        zz = z + drop
        t = np.clip((s_le - s) / (s_le - s_te), 0, 1)           # 0 at the leading edge -> 1 at the trailing edge
        z_bot = zd - 0.010 + 0.006 * t
        z_top = zd + 0.006 + 0.036 * t ** 0.8                   # upper surface rises rearward
        d_v = np.maximum(z_bot - zz, zz - z_top)
        d_s = np.maximum(s - s_le, s_te - s)
        d = smax(d_v, d_s, 0.008)
        return smax(d, ax - half, 0.02)
    V, F, N = D.mc_small(fld, (-0.80, s_te - 0.04, zd - 0.06), (0.80, s_le + 0.04, zd + 0.09), 0.0045, 3600)
    fc = V[F].mean(1)
    cap = np.abs(fc[:, 0]) > half - 0.05
    parts.add('body', V, F[~cap], 'trim_black', N=N, COL=np.c_[np.full((len(V), 3), 0.7), np.ones(len(V))])
    parts.add('body', V, F[cap], 'paint', N=N, COL=np.c_[np.full((len(V), 3), 0.85), np.ones(len(V))])

def brake_pod(parts, B, f, L):
    """Third brake light: black pod with a red lens on the roof edge at the top of the rear window (lights off)."""
    hh = None
    for s0 in np.linspace(-0.98, -1.20, 23):       # last roof point before the glass falls away
        h = D.ray_hit(f, (0.0, s0, 2.0), (0, 0, -1), tmax=1.5)
        if h is not None and (hh is None or h[2] > hh[2] - 0.012): hh = h
    if hh is None: return
    c = np.array([0.0, hh[1] - 0.01, hh[2] + 0.014])
    def fld(x, s, z):
        P = np.stack([x, s, z], -1)
        body = sd_round_box(P, c, (0.165, 0.045, 0.020), 0.016)
        return body
    V, F, N = D.mc_small(fld, c - (0.20, 0.08, 0.05), c + (0.20, 0.08, 0.05), 0.0035, 1600)
    fc = V[F].mean(1); fn = N[F].mean(1)
    lens = (fn[:, 1] < -0.55) & (np.abs(fc[:, 0]) < 0.13) & (fc[:, 2] > c[2] - 0.012)
    parts.add('body', V, F[lens], 'light_rear', N=N)
    parts.add('body', V, F[~lens], 'trim_black', N=N, COL=np.c_[np.full((len(V), 3), 0.7), np.ones(len(V))])
