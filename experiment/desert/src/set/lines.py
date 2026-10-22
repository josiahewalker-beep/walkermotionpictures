"""Worn lane paint strip: 256 x 4096 px covering 0.15 m (across, u) x 8 m (along, v).
Outputs: lines_yellow_albedo.png, lines_white_albedo.png, lines_alpha.png, lines_normal.png
Worked internally on an isotropic grid (1.953 mm/px: 77 x 4096) then resampled across to 256."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from texlib import *
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), '../../tex')
H, W = 4096, 154                 # 0.15 m at 0.974 mm/px across, rows at 1.953 mm/px → compensate below
MMX, MMY = 150.0 / W, 8000.0 / H
r = rng(41)
shp = (H, W)

# underlying chip seal height (paint follows the aggregate). Generate isotropic then squash.
cs = chipseal(None, MMY, 41, shape=(H, W // 2 + 1))
def widen(a):
    a2 = np.repeat(a, 2, axis=1)[:, :W]
    return gblur(a2, (0, 0.6))
h_ag = widen(cs['h']); stone = widen(cs['stone']); top = widen(cs['top'])

# low-frequency fields along the strip (anisotropic: long along v)
def field(beta, lo, hi, seed, an=(1, 1)):
    # physical isotropy: the tile is 8 m along (rows) x 0.15 m across (cols); lo/hi are cycles per 8 m
    return spectral(shp, rng(seed), beta, lo=lo, hi=hi, aniso=(an[0], an[1] * 8000.0 / 150.0))

v = (np.arange(H) + 0.5) / H                         # 0..1 along 8 m
u = (np.arange(W) + 0.5) / W * 150 - 75              # mm from strip centre

# ragged paint edges: paint is 110 mm wide nominal, edges wander +-6 mm with fine overspray speckle
eL = -55 + 2.5 * spectral((H, 1), rng(2), 2.2, lo=2, hi=500)[:, 0] + 1.0 * spectral((H, 1), rng(3), 1.2, lo=30)[:, 0]
eR = 55 + 2.5 * spectral((H, 1), rng(4), 2.2, lo=2, hi=500)[:, 0] + 1.0 * spectral((H, 1), rng(5), 1.2, lo=30)[:, 0]
inside = smoothstep(-0.8, 0.8, u[None, :] - eL[:, None]) * smoothstep(0.8, -0.8, u[None, :] - eR[:, None])
overspray = (r.random(shp) < 0.05) * smoothstep(12, 0, np.minimum(np.abs(u[None, :] - eL[:, None]), np.abs(u[None, :] - eR[:, None]))) * (1 - inside)
overspray = gblur(overspray.astype(np.float32), 0.6) * 1.5

# wear: large flaked gaps (aggregate shows through), worn stone tops, a few chipped-out bites from the edges
wear_lo = field(2.4, 6, 1200, 6, (1, 0.7))           # blotches elongated along the line
wear_hi = field(2.0, 60, 2000, 7)
wear = 0.5 * wear_lo + 0.18 * wear_hi
# section-level wear: some 1-2 m stretches are much worse (old repaint seams, plough scrapes)
sect = np.interp(v, np.linspace(0, 1, 9), np.r_[rng(8).random(8), 0])  # periodic-ish
sect = gblur(np.r_[sect, sect, sect], 40)[H:2 * H] if False else np.convolve(np.r_[sect, sect, sect], np.ones(200) / 200, 'same')[H:2 * H]
wear += 0.9 * (sect[:, None] - 0.5)
# stone tops lose paint first (traffic polishing), valleys keep it
wear += 0.45 * stone * top ** 2
# edge bites
F1, F2, cid, pts = worley(shp, 26, rng(9), jitter=1.0)
bite = (rng(10).random(len(pts)) < 0.18)[cid] & (F1 < 14 + 8 * rng(11).random(len(pts))[cid])
edge_d = np.minimum(np.abs(u[None, :] - eL[:, None]), np.abs(u[None, :] - eR[:, None]))
bite = bite & (edge_d < 22)
paint = inside * smoothstep(0.75, 0.45, wear) * (~bite)
# partly worn: thin paint film over the stones (lets the grey through)
thin = inside * smoothstep(0.95, 0.55, wear) * (~bite)
alpha = np.clip(np.maximum(paint, thin * 0.55) + overspray * 0.6, 0, 1)
# tiny pinholes / chips everywhere
pin = (gblur(r.standard_normal(shp), 0.7) > 1.45) * 0.85
alpha = alpha * (1 - pin * inside)

# colour (linear). Paint sun-faded, dust-filmed, stained by binder bleed-through in valleys
dirt = np.array([0.20, 0.165, 0.125])
tyre = np.array([0.045, 0.043, 0.042])
tone = 1 + 0.08 * field(2.2, 2, 400, 12) + 0.05 * field(1.8, 30, 3000, 13)
valley = (1 - stone) * 0.25 + (1 - top) * stone * 0.1
dust_k = np.clip(0.18 + 0.15 * field(2.2, 2, 1500, 14) + 0.3 * valley, 0, 0.7)
# tyre scuffs: dark smears in sections, streaky along v
scuff_sec = np.clip(np.convolve(np.r_[rng(15).random(6), ] .repeat(H // 6 + 1)[:H], np.ones(120) / 120, 'same') - 0.55, 0, 1) * 2.2
scuff = np.clip(scuff_sec[:, None] * (0.6 + 0.6 * field(2.0, 4, 600, 16, (1, 0.4))), 0, 0.85)
scuff *= smoothstep(-0.3, 0.6, field(2.0, 3, 400, 17, (1, 0.2)))
oil = np.clip(field(2.6, 2, 150, 18) - 1.2, 0, 1) * 0.5

def paint_col(base):
    c = np.asarray(base)[None, None, :] * tone[..., None]
    c = c * (1 - dust_k[..., None]) + dirt * dust_k[..., None]
    c = c * (1 - 0.6 * (thin - paint)[..., None].clip(0, 1)) + 0.12 * (thin - paint)[..., None].clip(0, 1) * dirt
    c = c * (1 - scuff[..., None]) + tyre * scuff[..., None]
    c = c * (1 - oil[..., None])
    return np.clip(c, 0.03, 0.9)

yel = paint_col([0.56, 0.36, 0.065])      # faded traffic yellow
wht = paint_col([0.62, 0.60, 0.555])      # faded white, slightly warm

def to_out(a, isotropic_rows=True):
    # resample across: W=154 -> 256 columns
    if a.ndim == 2:
        return np.asarray(Image.fromarray(a.astype(np.float32), 'F').resize((256, H), Image.BICUBIC))
    return np.stack([to_out(a[..., k]) for k in range(a.shape[2])], -1)

save_srgb(to_out(yel), f'{OUT}/lines_yellow_albedo.png')
save_srgb(to_out(wht), f'{OUT}/lines_white_albedo.png')
save_gray(np.clip(to_out(alpha), 0, 1), f'{OUT}/lines_alpha.png')
# normal: aggregate + paint thickness (0.4 mm, with chip edges)
hp = h_ag * (1 - 0.25 * paint) + 0.4 * gblur(paint, 0.8) + 0.2 * thin
n_iso = normal_from_height(hp, 1.0, MMY)      # rows at MMY; columns at MMX → correct x slope
dx = (np.roll(hp, -1, 1) - np.roll(hp, 1, 1)) / (2 * MMX)
dy = (np.roll(hp, -1, 0) - np.roll(hp, 1, 0)) / (2 * MMY)
n = np.stack([-dx, dy, np.ones_like(hp)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
save_normal(to_out(n), f'{OUT}/lines_normal.png')
print('yellow mean', yel[alpha > 0.5].mean(0), 'white mean', wht[alpha > 0.5].mean(0), 'alpha mean', alpha.mean())
