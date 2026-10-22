"""Old sun-bleached desert two-lane: chip-seal asphalt tile (4 m x 4 m, 2048^2, ~1.95 mm/px) + road macro map.
Image axes: columns (u) run ACROSS the road, rows (v) run ALONG the road.
Outputs (desert/tex/): asphalt_albedo.jpg, asphalt_normal.jpg, asphalt_rough.jpg, asphalt_macro.jpg
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from texlib import *
from PIL import Image

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
bleach = 1 + 0.035 * t_lo + 0.05 * t_mid
col *= bleach[..., None]
# warm dust film over everything (more where t_lo is high), stays honest
film = np.clip(0.10 + 0.03 * t_lo, 0, 0.3)
col = col * (1 - film[..., None]) + dust * film[..., None]

# ---------------- fine transverse cracks (run across the road = along columns) ----------------
crack = np.zeros((N, N), np.float32)
for k in range(5):
    y0 = r.random() * N; x0 = r.random() * N
    L = r.uniform(150, 600)
    hd = (0 if r.random() < 0.5 else np.pi) + r.normal(0, 0.12)
    stamp_line(crack, crack_path(r, (y0, x0), hd, L, step=2.0, wander=0.22, persist=0.6), 1.0)
# a few short block / branch cracks
for k in range(8):
    y0 = r.random() * N; x0 = r.random() * N
    stamp_line(crack, crack_path(r, (y0, x0), r.uniform(0, 2 * np.pi), r.uniform(60, 260), step=2, wander=0.35, persist=0.6), 0.8)
crack_w = gblur(crack, 0.7)
crack_m = np.clip(crack_w * 1.4, 0, 0.8)
h -= crack_m * 3.0
col = col * (1 - 0.65 * crack_m[..., None])
# dust caught in the crack lips
lip = np.clip(gblur(crack, 2.5) * 4 - crack_m, 0, 1) * 0.25
col = col * (1 - lip[..., None]) + dust * lip[..., None]

# ---------------- outputs ----------------
col = np.clip(col, 0.02, 0.9)
lum = (col @ [0.2126, 0.7152, 0.0722])
print('albedo mean linear', col.reshape(-1, 3).mean(0), 'lum', lum.mean())
save_srgb(col, f'{OUT}/asphalt_albedo.jpg', 92)
n = normal_from_height(gblur(h, 0.5), 1.0, PX)
save_normal(n, f'{OUT}/asphalt_normal.jpg', 95)
rough = 0.86 + 0.06 * stone - 0.10 * (h_stone > 3.5) + 0.06 * dust_amt
rough += 0.03 * t_mid
save_gray(np.clip(rough, 0.3, 1.0), f'{OUT}/asphalt_rough.jpg', 92)

# ---------------- macro: full paved width x 80 m, RGB ----------------
# 1024 x 8192 px (~10 mm/px). u across the paved width 10.2 m (centre line at u = 0.5), v along 80 m (tiles along v).
# R: albedo multiplier (0.5 = x1). G: crack-sealant mask (1 = tar: albedo ~0.035, roughness ~0.4, raised 2 mm).
# B: patch mask (newer patch: finer, darker; R already includes the darkening).
MW, MH = 1024, 8192
WID, LEN = 10.2, 80.0
PXM = LEN / MH                                    # m per px along; across: WID / MW
rm = rng(21)
u = (np.arange(MW) + 0.5) / MW * WID - WID / 2    # m from the centre line
vv = np.arange(MH)
mm = 1 + 0.09 * spectral((MH, MW), rm, 2.8, lo=1, hi=120, aniso=(1, 8)) + 0.04 * spectral((MH, MW), rm, 2.0, lo=6, hi=600, aniso=(1, 8))
wp = np.zeros(MW)
for c in (-2.65, -1.05, 1.05, 2.65):
    wp += np.exp(-((u - c) / 0.33) ** 2)
oil = np.exp(-((np.abs(u) - 1.85) / 0.22) ** 2)
var = 1 + 0.35 * spectral((MH, MW), rm, 2.5, lo=2, hi=200, aniso=(1, 8))
mm *= 1 - 0.12 * wp[None, :] * var - 0.15 * oil[None, :] * np.clip(var, 0.2, 2)
mm *= 1 + 0.04 * np.exp(-(u / 0.5) ** 2)[None, :] + 0.10 * smoothstep(3.9, 5.1, np.abs(u))[None, :]
seal = np.zeros((MH, MW), np.float32)
openc = np.zeros((MH, MW), np.float32)
patch = np.zeros((MH, MW), np.float32)
yy2, xx2 = np.mgrid[0:MH, 0:MW].astype(np.float32)
def px_u(m): return (m + WID / 2) / WID * MW
def path_px(r_, y0, x0, hd, L, wander, step=1.5):
    # crack_path in px with anisotropic px (across 10 mm, along 9.8 mm ~ isotropic)
    return crack_path(r_, (y0, x0), hd, L, step=step, wander=wander, persist=0.7)
# transverse thermal cracks, every 5-14 m, most sealed
y = 0.0
while True:
    y += rm.uniform(5, 14) / PXM
    if y > MH - 200: break
    x_start = px_u(rm.uniform(-5.1, -3.0)) if rm.random() < 0.7 else px_u(rm.uniform(-3, 0))
    L = (px_u(rm.uniform(3.0, 5.1)) if rm.random() < 0.75 else px_u(rm.uniform(0, 3))) - x_start
    p = path_px(rm, y, x_start, rm.normal(0, 0.06), L, 0.18)
    tgt = seal if rm.random() < 0.75 else openc
    stamp_line(tgt, p, 1.0)
    if rm.random() < 0.4:          # a branch
        q = p[rm.integers(len(p))]
        stamp_line(openc, path_px(rm, q[0], q[1], rm.choice([-1, 1]) * rm.uniform(0.6, 1.2), rm.uniform(30, 120), 0.4), 0.8)
# longitudinal centre joint, sealed in long stretches, wandering a little
for k in range(4):
    y0 = rm.uniform(0, MH); L = rm.uniform(8, 30) / PXM
    stamp_line(seal, path_px(rm, y0, px_u(rm.normal(0, 0.05)), np.pi / 2, L, 0.05, step=3), 1.0)
# meandering tar snakes in the lanes
for k in range(10):
    y0 = rm.uniform(0, MH); x0 = px_u(rm.uniform(-4.2, 4.2))
    stamp_line(seal, path_px(rm, y0, x0, np.pi / 2 + rm.normal(0, 0.3), rm.uniform(1.5, 6) / PXM, 0.35, step=2), 1.0)
# open longitudinal cracks near the edges (edge cracking)
for k in range(14):
    y0 = rm.uniform(0, MH); side = rm.choice([-1, 1]); x0 = px_u(side * rm.uniform(4.3, 4.9))
    stamp_line(openc, path_px(rm, y0, x0, np.pi / 2 + rm.normal(0, 0.2), rm.uniform(1, 5) / PXM, 0.4, step=2), 0.9)
# sealant band: distance to stamped path, wobbly width 2.5-5 cm (2.5-5 px), overbanding
pad = 64
sp = np.pad(seal, pad, mode='wrap')
sd = ndi.distance_transform_edt(sp < 0.5)[pad:-pad, pad:-pad]
wob = spectral((MH, MW), rm, 2.2, lo=20, hi=2000)
hw = 2.6 + 1.0 * wob
sealm = smoothstep(hw + 0.8, hw - 0.8, sd)
# patches
for k in range(6):
    cy = rm.uniform(0, MH); cx = px_u(rm.uniform(-3.5, 3.5))
    hh = rm.uniform(0.5, 2.5) / PXM / 2; ww = rm.uniform(0.6, 2.4) / (WID / MW) / 2
    e = spectral((MH, MW), rng(100 + k), 2.2, lo=40, hi=3000) * 1.5
    dy = np.abs((yy2 - cy + MH / 2) % MH - MH / 2); dx = np.abs(xx2 - cx)
    d = np.maximum(dy - hh, dx - ww) + e
    pm_ = smoothstep(1.0, -1.0, d)
    patch = np.maximum(patch, pm_)
    sealm = np.maximum(sealm, smoothstep(3.5, 1.0, np.abs(d)) * 0.9)
openm = np.clip(gblur(openc, 0.6) * 1.6, 0, 1)
mm *= 1 - 0.30 * patch * (1 + 0.1 * spectral((MH, MW), rm, 2.0, lo=50, hi=3000))
mm *= 1 - 0.55 * openm
mm = mm * (1 - sealm) + (0.035 / 0.125) * (1 + 0.15 * wob) * sealm     # tar ~0.035 linear vs 0.125 mean tile
print('macro range', mm.min(), mm.max(), mm.mean(), 'seal frac', sealm.mean(), 'patch', patch.mean())
rgb = np.stack([np.clip(mm * 0.5, 0, 1), np.clip(sealm, 0, 1), np.clip(patch, 0, 1)], -1)
Image.fromarray((rgb * 255 + 0.5).astype(np.uint8)).save(f'{OUT}/asphalt_macro.png', optimize=True)
# grey-only copy (R channel) for simple multiply wiring, same mapping as the PNG
save_gray(np.clip(mm * 0.5, 0, 1), f'{OUT}/asphalt_macro.jpg', 92)
