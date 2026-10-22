"""Mojave desert pavement ground: 6 m x 6 m tile at 2048^2 (2.93 mm/px) + 300 m macro map.
Outputs: sand_albedo.jpg, sand_normal.jpg, sand_rough.jpg, sand_macro.jpg"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from texlib import *

OUT = os.path.join(os.path.dirname(__file__), '../../tex')
N = 2048
PX = 6000.0 / N
r = rng(51)
shp = (N, N)

# ---------------- base: fine tan sand, wind ripples, crust ----------------
t_lo = spectral(shp, r, 2.8, lo=1, hi=40)
t_mid = spectral(shp, r, 2.2, lo=6, hi=250)
grain = gblur(r.standard_normal(shp), 0.55)
grain2 = gblur(r.standard_normal(shp), 1.4)
sand_a = np.array([0.46, 0.355, 0.255])      # light tan
sand_b = np.array([0.36, 0.265, 0.185])      # darker, slightly redder
mixk = norm01(t_lo * 0.7 + t_mid * 0.3)
col = sand_a * (1 - mixk[..., None]) + sand_b * mixk[..., None]
col *= (1 + 0.07 * grain + 0.05 * grain2)[..., None]
# coloured grains (dark mafic, white quartz, rust)
gr = r.random(shp)
col = np.where((gr < 0.035)[..., None], col * 0.45, col)
col = np.where((gr > 0.975)[..., None], np.minimum(col * 1.35, 0.75), col)
col = np.where(((gr > 0.5) & (gr < 0.52))[..., None], col * np.array([1.08, 0.82, 0.66]), col)
col = gblur(col, (0.5, 0.5, 0))

# wind ripples: ~8-12 cm wavelength, crests perpendicular to wind (wind along +x), only in sandy patches
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
wv = spectral(shp, rng(52), 2.6, lo=2, hi=60) * 22         # warp
lam = 34.0                                                     # px  (~10 cm)
k = 2 * np.pi * np.round(N / lam) / N                          # periodic frequency
phase = k * (xx + wv) + 0.6 * spectral(shp, rng(53), 2.4, lo=3, hi=100)
rip = np.sin(phase)
rip = np.sign(rip) * np.abs(rip) ** 0.7                        # sharper crests
rip_asym = rip - 0.35 * np.cos(phase)                          # lee/stoss asymmetry
sandy = smoothstep(-0.2, 0.9, t_lo * 0.8 + 0.5 * spectral(shp, rng(54), 2.4, lo=2, hi=80))   # where loose sand pools
h = 1.6 * rip_asym * sandy + 2.0 * t_mid + 0.25 * grain2
col *= (1 + 0.04 * rip * sandy)[..., None]                     # crests a touch lighter (coarser grains)

# ---------------- desert pavement: gravel and pebbles ----------------
pave = np.clip(1 - sandy * 0.7 + 0.15 * t_mid, 0.15, 1)                                        # pebble density mask
peb_pal = [[0.30, 0.20, 0.13],    # varnished brown (desert varnish)
           [0.16, 0.11, 0.08],    # dark varnish
           [0.40, 0.32, 0.24],    # tan granite
           [0.47, 0.43, 0.38],    # pale quartz/granite
           [0.12, 0.11, 0.10],    # basalt
           [0.38, 0.20, 0.12],    # red jasper/volcanic
           [0.26, 0.24, 0.21]]    # grey
peb_w = [0.24, 0.16, 0.18, 0.08, 0.14, 0.08, 0.12]
hp = h.copy()
cov_g = splat_pebbles(hp, col, rng(59), 110000, 1.0, 2.2, peb_pal, peb_w, power=1.5, height_k=0.5, flat=(0.5, 1.0), mask=pave)
cov_s = splat_pebbles(hp, col, rng(55), 70000, 1.8, 5.5, peb_pal, peb_w, power=2.2, height_k=0.55, flat=(0.5, 1.0), mask=pave)
cov_l = splat_pebbles(hp, col, rng(56), 5000, 5, 18, peb_pal, peb_w, power=2.8, height_k=0.5, flat=(0.45, 0.9), mask=pave * 0.9)
cov = np.maximum(np.maximum(cov_s, cov_l), cov_g)
h = hp
col *= (1 + cov * (0.10 * grain + 0.10 * grain2))[..., None]     # mottled stone surfaces
# sand drift banked against pebbles (leeward, +x) and a dusting over them
lee = np.clip(gblur(np.roll(cov, 3, 1), 2.5) - cov, 0, 1)
col = col * (1 - 0.45 * lee[..., None]) + sand_a * 0.95 * 0.45 * lee[..., None]
dust_on = cov * np.clip(0.15 + 0.25 * t_mid, 0, 0.5)
col = col * (1 - dust_on[..., None]) + sand_a * dust_on[..., None]
# contact shadow is lighting, but a thin ring of darker damp-ish fines does occur; keep tiny
ring = np.clip(gblur(cov, 1.2) - cov, 0, 1) * 0.15
col *= (1 - ring)[..., None]

# ---------------- organic bits: twigs, creosote leaf litter, dark crust ----------------
org = np.zeros(shp, np.float32)
for i in range(260):                                           # small twigs
    y0, x0 = r.random() * N, r.random() * N
    p = crack_path(r, (y0, x0), r.uniform(0, 2 * np.pi), r.uniform(8, 45), step=1.0, wander=0.25, persist=0.5)
    stamp_line(org, p, r.uniform(0.6, 1.0))
org = np.clip(gblur(org, 0.6) * 1.6, 0, 1)
litter = (gblur(r.random(shp).astype(np.float32), 0.8) > 0.5 + 0.09) * smoothstep(0.6, 1.4, spectral(shp, rng(57), 2.6, lo=3, hi=80))
litter = gblur(litter.astype(np.float32), 0.6)
twig_col = np.array([0.20, 0.15, 0.10])
lit_col = np.array([0.14, 0.12, 0.07])
col = col * (1 - org[..., None]) + twig_col * org[..., None]
col = col * (1 - 0.7 * litter[..., None]) + lit_col * 0.7 * litter[..., None]
h += org * 1.2 + litter * 0.4
# cryptobiotic crust patches (dark, slightly lumpy)
crust = 0.5 * smoothstep(1.6, 2.4, spectral(shp, rng(58), 2.4, lo=4, hi=150)) * (1 - cov)
col = col * (1 - 0.35 * crust[..., None]) + np.array([0.13, 0.11, 0.085]) * 0.35 * crust[..., None]
h += crust * 1.0 * norm01(grain2)

col = np.clip(col, 0.03, 0.85)
print('sand albedo mean', col.reshape(-1, 3).mean(0))
save_srgb(col, f'{OUT}/sand_albedo.jpg', 92)
save_normal(normal_from_height(gblur(h, 0.6), 1.0, PX), f'{OUT}/sand_normal.jpg', 94)
rough = 0.93 - 0.18 * cov * (1 - dust_on) - 0.05 * org + 0.03 * grain
save_gray(np.clip(rough, 0.5, 1), f'{OUT}/sand_rough.jpg', 90)

# ---------------- macro: 300 m x 300 m, 1024^2, multiplicative tint around 0.5 ----------------
M = 1024
rm = rng(61)
a = spectral((M, M), rm, 2.6, lo=1, hi=300)
b = spectral((M, M), rm, 2.0, lo=8, hi=400)
# drainage washes: lighter sinuous bands; darker gravel bars
wash_f = spectral((M, M), rm, 3.0, lo=1, hi=30, aniso=(1, 0.35))
wash = smoothstep(0.15, 0.0, np.abs(wash_f + 0.3 * b * 0.2) / 3.0)
lum = 1 + 0.10 * a + 0.04 * b + 0.10 * wash - 0.08 * smoothstep(0.8, 1.8, spectral((M, M), rm, 2.4, lo=3, hi=200))
hue = 0.03 * spectral((M, M), rm, 2.6, lo=1, hi=200)          # red vs yellow shift
tint = np.stack([lum * (1 + hue), lum, lum * (1 - hue)], -1)
print('macro', tint.min(), tint.max())
save_gray(np.clip(tint * 0.5, 0, 1), f'{OUT}/sand_macro.jpg', 92)
