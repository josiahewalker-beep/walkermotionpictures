"""Crumbling asphalt edge into gravel/sand: 1024 x 2048 covering 1.5 m across (u) x 3 m along (v). Tiles along v only.
u = 0 is the road side (solid asphalt), the ragged edge sits around u ~ 0.45 m, then broken chunks, gravel, sand.
Outputs: shoulder_albedo.jpg, shoulder_normal.jpg, shoulder_mask.png (1 = paved, 0 = ground; soft ragged edge)"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from texlib import *

OUT = os.path.join(os.path.dirname(__file__), '../../tex')
H, W = 2048, 1024
PX = 1.4648                       # mm/px (both axes: 1500/1024, 3000/2048)
r = rng(71)
shp = (H, W)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
um = (xx + 0.5) * PX              # mm across

def fld(beta, lo, hi, seed, an=(1, 1)):
    # periodic along v, along u it's also periodic but we never see the wrap (u spans one edge only)
    return spectral(shp, rng(seed), beta, lo=lo, hi=hi, aniso=an)

# ---- asphalt (same recipe as the road tile, rescaled to this px size) ----
cs = chipseal(None, PX, 72, shape=shp)
acol, ah = cs['col'], cs['h']
dust = cs['dust']
t_lo = fld(2.6, 1, 60, 73)
acol *= (1 + 0.08 * t_lo)[..., None]
film = np.clip(0.16 + 0.10 * t_lo, 0, 0.35)
acol = acol * (1 - film[..., None]) + dust * film[..., None]

# ---- edge line: base position + ragged chunks ----
edge0 = 430 + 45 * fld(2.4, 1, 40, 74)[:, :1] + 14 * fld(1.8, 6, 200, 75)[:, :1]     # mm, varies along v
F1, F2, cid, pts = worley(shp, 55, rng(76), jitter=1.0)
ncell = len(pts)
cx_mm = pts[cid, 1] * PX
# cells near the edge break away with probability rising with distance from the road (decided per cell, at its centre)
cy_i = (pts[:, 0].astype(int)) % H
e_cell = edge0[cy_i, 0]
rel = (pts[:, 1] * PX - e_cell) / 160.0
keep = rng(77).random(ncell) < np.clip(0.45 - rel, 0, 1)
paved_cell = keep[cid] | (um < edge0 - 160)
jag = fld(1.6, 10, 600, 78) * 6
paved = (paved_cell & ((um + jag) < edge0 + 260)).astype(np.float32)
# the cell borders inside the kept area near the edge are cracks (chunks partly separated)
near = smoothstep(edge0 - 380, edge0 - 120, um) * paved
crackline = smoothstep(2.2, 0.4, warp(F2 - F1, fld(2, 4, 200, 85) * 4, fld(2, 4, 200, 86) * 4)) * near
crackline *= (rng(87).random(ncell)[cid] < 0.6)
dwy = fld(1.9, 6, 500, 88) * 9 + fld(1.5, 40, None, 89) * 2.5
dwx = fld(1.9, 6, 500, 90) * 9 + fld(1.5, 40, None, 91) * 2.5
paved = warp(paved, dwy, dwx)
crackline = warp(crackline, dwy, dwx)
paved = gblur(paved, 0.8)
paved = smoothstep(0.35, 0.65, paved)
# chunks that remain beyond the edge sit lower / settled
settle = np.clip((um - edge0 + 160) / 300, 0, 1) * paved
gaps = np.clip(crackline * 1.2, 0, 1)

# ---- ground: gravel shoulder then desert sand ----
gcol = np.zeros((H, W, 3)) + np.array([0.33, 0.255, 0.185])
gr = gblur(r.standard_normal(shp), 0.6)
gcol *= (1 + 0.08 * gr + 0.06 * fld(2.2, 4, 200, 79))[..., None]
gh = 0.8 * fld(2.2, 4, 300, 80)
dens = np.clip(1.0 - (um - edge0) / 1100.0, 0.25, 1.0)          # gravel thins with distance from the road
peb_pal = [[0.21, 0.20, 0.19], [0.14, 0.135, 0.13], [0.30, 0.22, 0.15], [0.40, 0.36, 0.31], [0.10, 0.095, 0.09], [0.30, 0.17, 0.11]]
peb_w = [0.24, 0.22, 0.2, 0.1, 0.12, 0.12]
c1 = splat_pebbles(gh, gcol, rng(81), 26000, 1.2, 3.0, peb_pal, peb_w, power=1.6, height_k=0.55, mask=dens)
c2 = splat_pebbles(gh, gcol, rng(82), 7000, 2.5, 6.5, peb_pal, peb_w, power=2.2, height_k=0.5, mask=dens)
# loose asphalt crumbs (dark chunks) just outside the edge
crumb_mask = smoothstep(edge0 + 450, edge0 + 50, um) * smoothstep(edge0 - 100, edge0 + 50, um)
c3 = splat_pebbles(gh, gcol, rng(83), 1600, 3, 14, [[0.085, 0.082, 0.078], [0.13, 0.12, 0.11], [0.17, 0.16, 0.15]], [0.4, 0.35, 0.25], power=2.4, height_k=0.45, flat=(0.5, 0.95), mask=crumb_mask * 0.7)
cov = np.maximum(np.maximum(c1, c2), c3)
dust_on = cov * 0.18
gcol = gcol * (1 - dust_on[..., None]) + np.array([0.40, 0.31, 0.22]) * dust_on[..., None]
gcol = np.clip(gcol, 0.03, 0.85)

# ---- compose ----
# asphalt edge darker where it is old and broken, sand blown onto the edge zone
sand_on = smoothstep(edge0 - 300, edge0 + 60, um) * np.clip(0.2 + 0.2 * fld(2.0, 6, 300, 84), 0, 0.5) * paved * (1 - cs['stone'] * 0.6)
acol = acol * (1 - sand_on[..., None]) + np.array([0.36, 0.28, 0.20]) * sand_on[..., None]
acol = acol * (1 - 0.5 * gaps[..., None]) + np.array([0.30, 0.235, 0.17]) * 0.5 * gaps[..., None]
col = acol * paved[..., None] + gcol * (1 - paved[..., None])
# height in mm: asphalt layer ~35 mm above the ground, dropping at the edge
h = (ah + 30 - 18 * settle - 6 * gaps) * paved + gh * (1 - paved)
col = np.clip(col, 0.03, 0.85)
save_srgb(col, f'{OUT}/shoulder_albedo.jpg', 92)
n = normal_from_height(gblur(h, 0.7), 0.6, PX)     # damp the 30 mm step so it doesn't alias
save_normal(n, f'{OUT}/shoulder_normal.jpg', 94)
mask = smoothstep(0.1, 0.9, gblur(paved, 1.0))
save_gray(mask, f'{OUT}/shoulder_mask.png')
print('albedo mean', col.reshape(-1, 3).mean(0), 'paved frac', paved.mean())
