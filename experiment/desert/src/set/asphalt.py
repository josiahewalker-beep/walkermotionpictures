"""Old sun-bleached desert two-lane: chip-seal asphalt tile (4 m x 4 m, 2048^2, ~1.95 mm/px) + road macro map.
Image axes: columns (u) run ACROSS the road, rows (v) run ALONG the road.
Outputs (desert/tex/): asphalt_albedo.jpg, asphalt_normal.jpg, asphalt_rough.jpg, asphalt_macro.jpg
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from texlib import *

OUT = os.path.join(os.path.dirname(__file__), '../../tex')
N = 2048
PX = 4000.0 / N            # mm per pixel
r = rng(11)

# ---------------- aggregate (chip seal, 3/8" stone set in oxidised binder, fines between) ----------------
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
cs = chipseal(N, PX, 11)
col, h, stone, h_stone, dust_amt, dust_field, dust = cs['col'], cs['h'], cs['stone'], cs['h_stone'], cs['dust_amt'], cs['dust_field'], cs['dust']

# ---------------- surface tonal variation ----------------
t_lo = spectral((N, N), r, 2.6, lo=1, hi=60)            # metre-scale mottling
t_mid = spectral((N, N), r, 2.0, lo=8, hi=300)
bleach = 1 + 0.10 * t_lo + 0.05 * t_mid
col *= bleach[..., None]
# warm dust film over everything (more where t_lo is high), stays honest
film = np.clip(0.10 + 0.08 * t_lo, 0, 0.3)
col = col * (1 - film[..., None]) + dust * film[..., None]

# ---------------- fine transverse cracks (run across the road = along columns) ----------------
crack = np.zeros((N, N), np.float32)
for k in range(9):
    y0 = r.random() * N; x0 = r.random() * N
    L = r.uniform(250, 1400)
    hd = (0 if r.random() < 0.5 else np.pi) + r.normal(0, 0.12)
    stamp_line(crack, crack_path(r, (y0, x0), hd, L, step=2.0, wander=0.22, persist=0.6), 1.0)
# a few short block / branch cracks
for k in range(14):
    y0 = r.random() * N; x0 = r.random() * N
    stamp_line(crack, crack_path(r, (y0, x0), r.uniform(0, 2 * np.pi), r.uniform(60, 260), step=2, wander=0.35, persist=0.6), 0.8)
crack_w = gblur(crack, 0.7)
crack_m = np.clip(crack_w * 2.2, 0, 1)
h -= crack_m * 3.0
col = col * (1 - 0.65 * crack_m[..., None])
# dust caught in the crack lips
lip = np.clip(gblur(crack, 2.5) * 4 - crack_m, 0, 1) * 0.25
col = col * (1 - lip[..., None]) + dust * lip[..., None]

# ---------------- tar snakes (crack sealant) ----------------
tar = np.zeros((N, N), np.float32)
for k in range(5):
    y0 = r.random() * N; x0 = r.random() * N
    if k < 3:   # longitudinal, meandering along the road
        p = crack_path(r, (y0, x0), np.pi / 2 + r.normal(0, 0.15), r.uniform(900, 2000), step=3, wander=0.16, persist=0.6)
    else:       # transverse
        p = crack_path(r, (y0, x0), r.normal(0, 0.1), r.uniform(500, 1300), step=3, wander=0.14, persist=0.6)
    stamp_line(tar, p, 1.0)
tw = spectral((N, N), r, 2.2, lo=4, hi=200)
tar_d = ndi.distance_transform_edt(tar < 0.5)
# periodic distance: compute on tiled copy is expensive; approximate via wrap padding
pad = 40
tp = np.pad(tar, pad, mode='wrap')
tar_d = ndi.distance_transform_edt(tp < 0.5)[pad:-pad, pad:-pad]
half_w = 5.5 + 2.0 * tw                       # 2.5–4.5 cm wide band, wobbly edges
tar_m = smoothstep(half_w + 1.2, half_w - 1.2, tar_d)
# sealant is smeared: thin, slightly dusty, sand-sprinkled at edges, aggregate tops poke through near its edge
tar_col = np.array([0.032, 0.031, 0.030]) * (1 + 0.25 * t_mid[..., None])
tar_dust = smoothstep(0.3, 0.9, norm01(spectral((N, N), r, 1.8, lo=16, hi=500))) * 0.35
tar_c = tar_col * (1 - tar_dust[..., None]) + dust * 0.7 * tar_dust[..., None]
poke = (h_stone > 3.6) & (tar_d > half_w * 0.55)
tar_eff = tar_m * np.where(poke, 0.25, 1.0)
col = col * (1 - tar_eff[..., None]) + tar_c * tar_eff[..., None]
h = h * (1 - tar_eff) + (1.2 + 0.4 * gblur(r.standard_normal((N, N)), 3)) * tar_eff

# ---------------- a patch (newer, darker, finer mix, slightly raised) ----------------
def patch_mask(cy, cx, hh, ww, rot, seed):
    rr = rng(seed)
    dy = ((yy - cy + N / 2) % N - N / 2); dx = ((xx - cx + N / 2) % N - N / 2)
    c, s = np.cos(rot), np.sin(rot)
    py, px = c * dy - s * dx, s * dy + c * dx
    e = spectral((N, N), rr, 2.2, lo=6, hi=300) * 2.5
    d = np.maximum(np.abs(py) - hh, np.abs(px) - ww) + e
    return smoothstep(2.0, -2.0, d), d

pm, pd = patch_mask(N * 0.73, N * 0.28, 150, 240, 0.03, 5)
pm *= 0.92
F1b, F2b, cidb, ptsb = worley((N, N), 3.2, rng(12), jitter=0.9)
fine_stone = smoothstep(0.5, 1.4, F2b - F1b)
fcol = np.array([0.068, 0.066, 0.063]) * (1 + 1.6 * fine_stone[..., None] * (rng(13).random(len(ptsb))[cidb][..., None] - 0.2))
fcol = fcol * (1 + 0.14 * t_lo[..., None] + 0.08 * t_mid[..., None])
ffilm = 0.16 + 0.08 * dust_field[..., None]
fcol = fcol * (1 - ffilm) + dust * ffilm
col = col * (1 - pm[..., None]) + fcol * pm[..., None]
h = h * (1 - pm) + (2.2 + fine_stone * 0.9) * pm
# sealed seam around the patch
seam = smoothstep(9, 2, np.abs(pd + 1)) * (1 - 0.6 * tar_dust)
col = col * (1 - seam[..., None]) + tar_col * seam[..., None]
h = h * (1 - seam) + 2.0 * seam
tar_all = np.maximum(tar_eff, seam)

# ---------------- outputs ----------------
col = np.clip(col, 0.02, 0.9)
lum = (col @ [0.2126, 0.7152, 0.0722])
print('albedo mean linear', col.reshape(-1, 3).mean(0), 'lum', lum.mean())
save_srgb(col, f'{OUT}/asphalt_albedo.jpg', 92)
n = normal_from_height(gblur(h, 0.5), 1.0, PX)
save_normal(n, f'{OUT}/asphalt_normal.jpg', 95)
rough = 0.86 + 0.06 * stone - 0.10 * (h_stone > 3.5) * (1 - pm) - 0.47 * tar_all + 0.06 * dust_amt - 0.10 * pm
rough += 0.03 * t_mid
save_gray(np.clip(rough, 0.3, 1.0), f'{OUT}/asphalt_rough.jpg', 92)

# ---------------- macro: whole road width x 256 m, multiplicative tone (0.5 grey = x1) ----------------
# 512 x 4096 px, u across the paved width (8.2 m: two 3.7 m lanes + 0.4 m each side), v along 256 m.
MW, MH = 512, 4096
rm = rng(21)
mm = 1 + 0.10 * spectral((MH, MW), rm, 2.8, lo=1, hi=80, aniso=(1, 3)) + 0.04 * spectral((MH, MW), rm, 2.0, lo=4, hi=300)
u = (np.arange(MW) + 0.5) / MW * 8.2 - 4.1           # metres from the centre line
wp = np.zeros(MW)
for c in (-2.85, -1.25, 1.25, 2.85):               # wheel paths, 1.6 m apart per lane
    wp += np.exp(-((u - c) / 0.32) ** 2)
oil = np.exp(-((np.abs(u) - 2.05) / 0.22) ** 2)     # drip stripe between the wheel paths
var = 1 + 0.35 * spectral((MH, MW), rm, 2.5, lo=2, hi=150, aniso=(1, 6))
mm *= 1 - 0.13 * wp[None, :] * var - 0.16 * oil[None, :] * np.clip(var, 0.2, 2)
# lighter, bleached crown and edges
mm *= 1 + 0.05 * np.exp(-(u / 0.6) ** 2)[None, :] + 0.08 * smoothstep(3.4, 4.1, np.abs(u))[None, :]
# large soft patches
for k in range(9):
    cy, cx = rm.random() * MH, rm.uniform(40, MW - 40)
    hh, ww = rm.uniform(20, 90), rm.uniform(25, 120)
    yy2, xx2 = np.mgrid[0:MH, 0:MW]
    d = np.maximum(np.abs(((yy2 - cy + MH / 2) % MH - MH / 2)) - hh, np.abs(xx2 - cx) - ww)
    mm *= 1 - 0.18 * smoothstep(3, -3, d) * rm.uniform(0.4, 1)
print('macro range', mm.min(), mm.max(), mm.mean())
save_gray(np.clip(mm * 0.5, 0, 1), f'{OUT}/asphalt_macro.jpg', 92)
