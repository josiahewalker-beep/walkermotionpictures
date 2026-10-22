"""Weathering for the drive-in set: 30-40 years of mountain weather on timber, paint, steel and concrete.
Pure numpy on baked per-texel maps (Blender coords, Z up): P position, N normal, AO, E edge, AX grain axis (abs), K scalar.
Noise/streak/droppings helpers come from the desert billboard's bb_weather.py."""
import numpy as np
from scipy import ndimage as ndi
from bb_weather import fbm, streaks, droppings, lerp
from texlib import smoothstep


def grain_noise(P, AX, scale, seed, oct=3, stretch=10.0):
    """Noise stretched along each texel's member axis (x, y or z, whichever dominates)."""
    k = np.argmax(AX, axis=-1)
    out = np.zeros(P.shape[:2], np.float32)
    for a in range(3):
        m = k == a
        if not m.any():
            continue
        st = [1.0, 1.0, 1.0]; st[a] = stretch
        out[m] = fbm(P[m][:, None, :], scale, seed + a * 7, oct=oct, stretch=tuple(st))[:, 0]
    return out


def weather_wood(P, N, AO, E, AX, K, used, sources, perch, seed=1, ground=2.7):
    """Bare weathered timber (K ~ 0) / creosoted posts (K ~ 0.5). Returns col (linear), rough, metal, height."""
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    kk = K[..., 0]
    gz = P[..., 2] - ground
    lo = fbm(P, 0.6, seed, oct=4)
    mid = fbm(P, 0.06, seed + 30, oct=3)
    g1 = grain_noise(P, AX, 0.035, seed + 60, oct=3, stretch=12)
    g2 = grain_noise(P, AX, 0.006, seed + 90, oct=2, stretch=25)
    # each board its own tone: low-frequency noise plus position hash
    exposed = np.clip(0.35 + 0.45 * ao + 0.25 * np.clip(up, 0, 1), 0, 1)
    silver = np.array([0.205, 0.195, 0.175]); brown = np.array([0.15, 0.10, 0.065]); dark = np.array([0.075, 0.06, 0.05])
    col = lerp(brown, silver, smoothstep(0.35, 0.95, exposed + 0.06 * lo))
    col = col * (1 + 0.05 * lo + 0.16 * g1 + 0.10 * g2)[..., None]
    # creosote / old dark preservative on posts, heavier toward the ground, sun-bleached on top
    creo = np.clip(kk * 2, 0, 1) * np.clip(0.55 + 0.3 * lo + 0.4 * smoothstep(4.0, 0.0, gz), 0, 1)
    col = lerp(col, dark * (1 + 0.15 * g1)[..., None], creo * 0.85)
    # checks: dark cracks along the grain
    chk = smoothstep(1.55, 2.0, g1 + 0.35 * mid) * (0.6 + 0.4 * (1 - ao))
    col = lerp(col, col * 0.35, chk)
    # rot and moisture at the foot of verticals; moss/lichen
    foot = smoothstep(0.9, 0.0, gz) * (AX[..., 2] > 0.6)
    col = lerp(col, np.array([0.06, 0.05, 0.035]), foot * 0.6)
    moss = smoothstep(1.0, 1.6, mid + 0.7 * lo + 0.9 * (1 - ao) + 0.8 * foot + 0.4 * np.clip(up, 0, 1)) * (0.4 + 0.6 * smoothstep(3.5, 0, gz))
    col = lerp(col, np.array([0.065, 0.078, 0.038]) * (1 + 0.2 * mid)[..., None], moss * 0.8)
    lich = smoothstep(2.3, 2.7, fbm(P, 0.008, seed + 140, oct=2) + 0.3 * lo + 0.5 * ao)
    col = lerp(col, np.array([0.27, 0.28, 0.23]), lich * 0.45)
    # rust runs below nails/bolts, dirt streaks below horizontal members
    S = streaks(P, N, used, sources, 1.0, seed + 3) if len(sources) else np.zeros_like(up)
    col = lerp(col, np.array([0.12, 0.055, 0.025]), np.clip(S * 0.8, 0, 0.8))
    wst = smoothstep(0.6, 1.6, fbm(P, 0.25, seed + 200, oct=4, stretch=(1, 1, 8))) * (1 - np.abs(up)) * (0.3 + 0.7 * (1 - ao))
    col = lerp(col, np.array([0.07, 0.06, 0.05]), wst * 0.45)
    # pine needle duff and dust on horizontal tops
    duff = smoothstep(0.6, 0.9, up) * np.clip(0.5 + 0.5 * lo + 0.3 * (1 - ao), 0, 1) * smoothstep(-0.4, 0.6, mid + 0.4)
    duffc = lerp(np.array([0.13, 0.075, 0.04]), np.array([0.22, 0.17, 0.12]), smoothstep(-0.5, 0.8, g2))
    col = lerp(col, duffc, np.clip(duff, 0, 0.85))
    D = droppings(P, N, used, perch, seed + 7) if len(perch) else np.zeros_like(up)
    col = lerp(col, np.array([0.62, 0.60, 0.55]), D * 0.9)
    col = col * (0.5 + 0.5 * ao ** 0.8)[..., None]
    col = np.clip(col, 0.03, 0.85)
    rough = np.clip(0.80 + 0.08 * g2 + 0.08 * duff - 0.08 * creo - 0.05 * D, 0.55, 1.0)
    h = 0.25 * g2 + 0.15 * g1 - 1.0 * chk + 0.15 * moss + 0.1 * duff + 0.08 * D
    return col, rough, np.zeros_like(rough), h


def weather_paintwood(P, N, AO, E, AX, K, used, sources, perch, seed=11, ground=2.7, top=18.6,
                      paints=((0.38, 0.37, 0.34), (0.33, 0.34, 0.31), (0.41, 0.40, 0.36), (0.30, 0.31, 0.28))):
    """Plywood painted over several times (old sign blocks rolled out in slightly different whites), 30+ years of
    weather: chalking, peel along sheet edges and the bottom, dirt runs from the top edge, mildew low down."""
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    gx, gy, gz = P[..., 0], -P[..., 1], P[..., 2]
    lo = fbm(P, 0.8, seed, oct=4); mid = fbm(P, 0.07, seed + 30, oct=3); hi = fbm(P, 0.012, seed + 60, oct=2)
    grain = grain_noise(P, AX, 0.03, seed + 90, oct=3, stretch=14)
    # painted-over blocks: a coarse grid of rectangles (world x / height) each with its own paint coat
    bx = np.floor((gx + 40) / 3.7 + 0.3 * np.floor(gz / 2.9)).astype(int); by = np.floor((gz + 1.3) / 2.9).astype(int)
    hsh = (bx * 73856093 ^ by * 19349663) % 997 / 997.0
    pal = np.asarray(paints)
    pc = pal[(hsh * len(pal)).astype(int) % len(pal)]
    coat = smoothstep(0.25, 0.6, hsh)              # newer coat (cleaner) vs older
    col = pc * (1 + 0.06 * lo + 0.03 * mid)[..., None]
    chalk = np.clip(0.4 + 0.3 * up + 0.2 * lo, 0, 1)
    col = lerp(col, col * 1.06 + 0.02, chalk * 0.4)
    # peel: sheet edges (E), lower third, random blisters; bare wood is grey and grainy
    pv = 0.30 * lo + 0.35 * mid + 0.20 * hi + 1.1 * E + 0.6 * (1 - ao) ** 1.5 + 0.55 * smoothstep(4.5, ground + 0.5, gz) - 0.25 * coat
    peel = smoothstep(1.05, 1.12, pv)
    ring = smoothstep(0.98, 1.05, pv) * (1 - peel)
    wood = np.array([0.20, 0.185, 0.16]) * (1 + 0.12 * grain + 0.06 * hi)[..., None]
    col = lerp(col, col * 0.82, ring * 0.6)
    col = lerp(col, wood, peel)
    # dirt runs from the top edge and below every horizontal batten / sheet joint
    run = fbm(P, 0.12, seed + 120, oct=4, stretch=(1, 1, 10))
    fromtop = smoothstep(top - 4.5, top - 0.2, gz)
    dirt = np.clip(smoothstep(0.2, 1.4, run) * (0.25 + 0.75 * fromtop), 0, 1)
    col = lerp(col, np.array([0.13, 0.11, 0.085]), dirt * 0.55)
    S = streaks(P, N, used, sources, 1.0, seed + 3) if len(sources) else np.zeros_like(up)
    col = lerp(col, np.array([0.16, 0.08, 0.04]), np.clip(S * 0.8, 0, 0.8))
    mil = smoothstep(0.8, 1.6, fbm(P, 0.15, seed + 160, oct=4) + 1.2 * smoothstep(5.5, ground, gz) + 0.6 * (1 - ao))
    col = lerp(col, np.array([0.12, 0.13, 0.10]), mil * 0.35)
    D = droppings(P, N, used, perch, seed + 7) if len(perch) else np.zeros_like(up)
    col = lerp(col, np.array([0.62, 0.60, 0.55]), D * 0.9)
    col = col * (0.55 + 0.45 * ao ** 0.8)[..., None]
    col = np.clip(col, 0.03, 0.85)
    rough = np.clip(0.78 + 0.1 * chalk + 0.1 * peel + 0.05 * dirt, 0.5, 1)
    h = 0.12 * (1 - peel) + 0.06 * ring + 0.12 * grain * peel + 0.04 * hi + 0.05 * D
    return col, rough, np.zeros_like(rough), h


def weather_metal(P, N, AO, E, AX, K, used, sources, perch, seed=21, ground=2.7,
                  paint_lo=(0.035, 0.045, 0.038), paint_hi=(0.08, 0.09, 0.075)):
    """K ~ 0: dull galvanized (ladder, rods, rails); K ~ 1: dark green enamel paint over steel (brackets, boxes)."""
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    kk = np.clip(K[..., 0], 0, 1)
    lo = fbm(P, 0.3, seed, oct=4); mid = fbm(P, 0.04, seed + 40, oct=3); hi = fbm(P, 0.01, seed + 80, oct=2)
    g = np.array([0.17, 0.165, 0.155]) * (1 + 0.06 * lo + 0.04 * mid)[..., None]
    white = smoothstep(0.8, 1.6, mid + 0.3 * lo) * 0.25
    g = lerp(g, np.array([0.24, 0.235, 0.22]), white)
    pc = lerp(np.asarray(paint_lo), np.asarray(paint_hi), np.clip(0.5 + 0.3 * up + 0.2 * lo, 0, 1))
    col = lerp(g, pc, kk)
    rs = smoothstep(1.2, 1.55, 0.45 * mid + 0.35 * hi + 1.0 * (1 - ao) ** 1.5 + 1.0 * E + 0.3 * lo + 0.5 * smoothstep(ground + 1, ground, P[..., 2]))
    rc = lerp(np.array([0.08, 0.035, 0.018]), np.array([0.26, 0.10, 0.035]), np.clip(0.5 + 0.4 * hi, 0, 1))
    col = lerp(col, rc, rs)
    S = streaks(P, N, used, sources, 0.8, seed + 5) if len(sources) else np.zeros_like(up)
    col = lerp(col, np.array([0.20, 0.085, 0.035]), np.clip(S * 0.8, 0, 0.8))
    dst = np.clip(smoothstep(0.55, 0.9, up) * (0.5 + 0.4 * lo), 0, 0.85)
    col = lerp(col, np.array([0.15, 0.10, 0.065]), dst * 0.7)
    D = droppings(P, N, used, perch, seed + 8) if len(perch) else np.zeros_like(up)
    col = lerp(col, np.array([0.62, 0.60, 0.55]), D * 0.9)
    col = col * (0.55 + 0.45 * ao ** 0.8)[..., None]
    rough = np.clip(0.6 + 0.06 * white + 0.25 * rs + 0.15 * dst - 0.15 * kk * (1 - rs), 0.35, 1)
    metal = np.clip(0.3 * (1 - kk) * (1 - rs) * (1 - dst), 0, 1)
    h = 0.06 * rs * hi + 0.04 * dst + 0.08 * D + 0.03 * kk * (1 - rs)
    return np.clip(col, 0.03, 0.85), rough, metal, h


def weather_concrete(P, N, AO, E, AX, K, used, seed=31, ground=2.7):
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    lo = fbm(P, 0.3, seed, oct=4); mid = fbm(P, 0.05, seed + 40, oct=3); hi = fbm(P, 0.006, seed + 80, oct=2)
    col = np.array([0.27, 0.26, 0.24]) * (1 + 0.08 * lo + 0.05 * mid + 0.07 * hi)[..., None]
    band = smoothstep(ground + 0.12, ground - 0.02, P[..., 2])
    col = lerp(col, np.array([0.12, 0.09, 0.06]), band * 0.75)
    moss = smoothstep(0.9, 1.6, mid + 0.6 * lo + 0.8 * band + 0.5 * (1 - ao))
    col = lerp(col, np.array([0.07, 0.085, 0.045]), moss * 0.7)
    chip = smoothstep(0.9, 1.4, mid + 0.8 * E) * E
    col = lerp(col, np.array([0.32, 0.30, 0.27]), chip * 0.6)
    rs = smoothstep(0.5, 0.95, up) * smoothstep(1.0, 1.6, lo + mid)
    col = lerp(col, np.array([0.20, 0.10, 0.05]), rs * 0.5)
    col = col * (0.6 + 0.4 * ao)[..., None]
    rough = np.clip(0.88 + 0.06 * moss, 0.5, 1) * np.ones_like(up)
    h = 0.15 * hi - 1.0 * chip + 0.1 * moss
    return np.clip(col, 0.03, 0.85), rough, np.zeros_like(up), h
