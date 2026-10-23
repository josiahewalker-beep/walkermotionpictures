"""Hero badges and blanks (director's brief): the invented make "SOB" as one chrome wordmark on the hatch, upper left above
the lamp band (where the real car carries its maker's wordmark), in plain bold block capitals rasterised from DejaVu
Sans Bold at normal width (licence: see drivein/CREDITS.md). Raised chrome letters with a dark edge.
Everything else stays blank: a plain round cap on the bonnet nose, a plain blank plate on the front spoiler.
Model frame: x lateral (x < 0 = driver side), s forward, z up, metres.
"""
import os
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFont
from carlib import smax, sd_round_box, revolve, vertex_normals, normalize
import details as D

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
if not os.path.exists(FONT):
    import matplotlib
    FONT = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data/fonts/ttf/DejaVuSans-Bold.ttf')
TEXT = 'SOB'
CAP_H = 0.028            # cap height (m)
RAISE = 0.0035           # letter thickness off the panel
WM_X, WM_Z = -0.625, 1.024   # centre of the wordmark (driver side of the hatch, between lamp band and spoiler)
PX = 0.0004              # raster resolution (m/px)

def _text_sdf():
    size = 400
    font = ImageFont.truetype(FONT, size)
    bb = font.getbbox(TEXT)
    W, H = bb[2] - bb[0] + 40, bb[3] - bb[1] + 40
    im = Image.new('L', (W, H), 0)
    ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), TEXT, font=font, fill=255)
    cap = font.getbbox('S')[3] - font.getbbox('S')[1]
    m = np.asarray(im) > 127
    scale = CAP_H / cap                   # m per font px
    k = max(1, int(round(PX / scale)))
    m = m[::k, ::k]; px = scale * k
    d = (ndimage.distance_transform_edt(~m) - ndimage.distance_transform_edt(m)) * px
    d = ndimage.gaussian_filter(d, 0.6)
    h, w = d.shape
    def sdf(u, v):
        # u right (m), v up (m), centred
        j = np.clip((u / px + w / 2), 0, w - 1.001); i = np.clip((-v / px + h / 2), 0, h - 1.001)
        return ndimage.map_coordinates(d, [i, j], order=1, mode='nearest')
    return sdf, w * px, h * px

def hatch_wordmark(parts, B, f, L):
    h = D.ray_hit(f, (WM_X, -3.0, WM_Z), (0, 1, 0), tmax=1.5)
    if h is None: return
    n = D.grad(f, h)[0]
    # local frame: w = outward normal, u = right as seen from behind (= -x), v = up
    w_ = normalize(n); u_ = normalize(np.cross(np.array([0, 0, 1.0]), w_)); v_ = np.cross(w_, u_)
    sdf, tw, th = _text_sdf()
    o = h - w_ * 0.0015
    def fld(x, s, z):
        P = np.stack([x, s, z], -1) - o
        uu, vv, ww = P @ u_, P @ v_, P @ w_
        d2 = sdf(uu.ravel(), vv.ravel()).reshape(uu.shape)
        return smax(d2, np.abs(ww - (RAISE + 0.0015) / 2) - (RAISE + 0.0015) / 2, 0.0008)
    ext = np.array([tw / 2 + 0.01, 0.03, th / 2 + 0.01])
    lo = h - ext; hi = h + ext
    V, F, N = D.mc_small(fld, lo, hi, 0.0006, 3200)
    fn = N[F].mean(1)
    face = (fn @ w_) > 0.8
    parts.add('body', V, F[face], 'chrome', N=N)
    parts.add('body', V, F[~face], 'trim_black', N=N, COL=np.c_[np.full((len(V), 3), 0.5), np.ones(len(V))])

def front_blanks(parts, B, f, L):
    """Plain round cap on the bonnet nose (no emblem) and a blank plate on the front spoiler."""
    hz = L['C']['head'][3] + 0.03
    h = D.ray_hit(f, (0.0, 2.6, hz), (0, -1, 0), tmax=1.0)
    hh = D.ray_hit(f, (0.0, 2.6, 2.0) if h is None else (0.0, h[1] - 0.035, 2.0), (0, 0, -1), tmax=1.5)
    if hh is not None:
        n = D.grad(f, hh)[0]
        prof = [(0.0, 0.0), (0.0, 0.021), (0.002, 0.020), (0.0035, 0.015), (0.004, 0.0)]
        Vc, Fc, _ = revolve(prof, 28)
        # revolve axis is local x -> map to the surface normal
        a = normalize(n); b = normalize(np.cross(a, [1.0, 0, 0])); c = np.cross(a, b)
        Vw = hh - a * 0.0015 + Vc[:, 0:1] * a + Vc[:, 1:2] * b + Vc[:, 2:3] * c
        Nw = vertex_normals(Vw, Fc)
        if np.mean(Nw @ a) < 0: Fc = Fc[:, ::-1]
        parts.add('body', Vw, Fc, 'chrome')
    p = D.surface_curve(f, [(0.0, 0.398)], 'front', 1, 0.0)
    if len(p):
        n = D.grad(f, p[0])[0]; n[2] = 0; n = normalize(n)
        D.plate_mesh(parts, p[0] + n * 0.004, n, (0, 0, 1.0), wpl=0.30, hpl=0.105)
