"""Weathering texture synthesis for the billboard (pure numpy; no Blender).
Works on baked per-texel world position (Blender coords, Z up) / normal / AO / edge maps."""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texlib import smoothstep, srgb2lin

_G = {}


def grid(seed, n=96, sig=1.6):
    if (seed, n) not in _G:
        g = np.random.default_rng(seed).standard_normal((n, n, n)).astype(np.float32)
        g = ndi.gaussian_filter(g, sig, mode='wrap')
        _G[(seed, n)] = g / g.std()
    return _G[(seed, n)]


def n3(P, scale, seed=0, stretch=(1, 1, 1)):
    """Smooth 3D noise (std ~1) at positions P (..., 3) metres; scale = feature size in m."""
    g = grid(seed)
    n = g.shape[0]
    R = np.random.default_rng(seed + 999).standard_normal((3, 3))
    Q, _ = np.linalg.qr(R)
    if stretch != (1, 1, 1):
        Q = np.eye(3)                       # keep axes for anisotropic (gravity) noise
    p = (P.reshape(-1, 3) @ Q.T) / np.array(stretch) / scale * (1.0 / 1.6) * 1.0
    c = [(p[:, k] * 1.0) % n for k in range(3)]
    v = ndi.map_coordinates(g, c, order=1, mode='grid-wrap')
    return v.reshape(P.shape[:-1])


def fbm(P, scale, seed, oct=4, gain=0.5, lac=2.03, stretch=(1, 1, 1)):
    s, a, tot, out = scale, 1.0, 0.0, 0.0
    for o in range(oct):
        out = out + a * n3(P, s, seed + o * 17, stretch)
        tot += a * a
        s /= lac
        a *= gain
    return out / np.sqrt(tot)


def streaks(P, N, used, sources, gain=1.0, seed=5):
    """Gravity streaks under point sources. sources: rows (x,y,z [Blender], strength, width, length)."""
    S = np.zeros(P.shape[:2], np.float32)
    idx = np.argwhere(used)
    pts = P[used]
    nz = N[used][:, 2]
    tree = cKDTree(pts)
    acc = np.zeros(len(pts), np.float32)
    for s in sources:
        c, st, w, L = s[:3], s[3], s[4], s[5]
        if st <= 0:
            continue
        ii = tree.query_ball_point(c, L + 0.1)
        if not ii:
            continue
        ii = np.array(ii)
        q = pts[ii]
        dz = c[2] - q[:, 2]
        lat = np.hypot(q[:, 0] - c[0], q[:, 1] - c[1])
        ww = w * (1 + 1.2 * np.clip(dz, 0, None) / max(L, 1e-3))
        v = st * np.exp(-(lat / ww) ** 2) * np.where(dz > -w * 0.6, np.exp(-np.clip(dz, 0, None) / (L * 0.55)), 0)
        v *= (1 - 0.75 * np.clip(nz[ii], 0, 1))          # less on top faces (washes off flat tops slowly)
        acc[ii] = np.maximum(acc[ii], v)
    # break streaks into rivulets with vertical-stretched noise
    rv = fbm(pts, 0.02, seed, oct=3, stretch=(1, 1, 8))
    acc *= np.clip(0.55 + 0.45 * rv, 0, 1.2)
    S[idx[:, 0], idx[:, 1]] = acc
    return np.clip(S * gain, 0, 1)


def droppings(P, N, used, perch, seed=9):
    out = np.zeros(P.shape[:2], np.float32)
    idx = np.argwhere(used)
    pts = P[used]
    nz = N[used][:, 2]
    tree = cKDTree(pts)
    acc = np.zeros(len(pts), np.float32)
    rng = np.random.default_rng(seed)
    for row in perch:
        c, r, d = row[:3], row[3], row[4]
        ii = tree.query_ball_point(c, r + 0.6)
        if not ii:
            continue
        ii = np.array(ii)
        q = pts[ii]
        dist = np.linalg.norm(q - c, axis=1)
        dz = c[2] - q[:, 2]
        near_top = (dist < r) * smoothstep(0.2, 0.7, nz[ii])
        drip = (dz > 0) * (dz < 0.5) * np.exp(-(np.hypot(q[:, 0] - c[0], q[:, 1] - c[1]) / (r * 0.8)) ** 2) * (1 - nz[ii].clip(0, 1)) * 0.6
        acc[ii] = np.maximum(acc[ii], d * np.maximum(near_top, drip))
    splat = fbm(pts, 0.012, seed, oct=2)
    blob = smoothstep(1.0, 1.6, splat + 1.2 * acc - 0.6)
    acc = np.clip(blob * np.clip(acc * 1.5, 0, 1), 0, 1)
    out[idx[:, 0], idx[:, 1]] = acc
    return out


def height_to_normal(h, texel_mm, strength=1.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * texel_mm) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * texel_mm) * strength
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def texel_size(P, used):
    d = np.linalg.norm(P[:, 1:] - P[:, :-1], axis=-1)
    m = used[:, 1:] & used[:, :-1]
    d = d[m]
    d = d[d < np.percentile(d, 90)]
    return float(np.median(d)) * 1000.0      # mm


def lerp(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) == 2 else t
    return a * (1 - t) + np.asarray(b) * t


def weather_painted(P, N, AO, E, used, sources, perch, paint_lo, paint_hi, seed=1, peel_amt=0.0,
                    frame_mask=None, galv_mask=None):
    """Returns base colour (linear), roughness, metallic, height (mm)."""
    H, W = used.shape
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    edge = np.clip((1 - E[..., 0]) * 6, 0, 1)
    convex = edge * smoothstep(0.55, 0.85, ao)
    lo = fbm(P, 0.35, seed, oct=5)
    mid = fbm(P, 0.06, seed + 50, oct=4)
    hi = fbm(P, 0.012, seed + 90, oct=3)
    # --- paint: sun-chalked grey-green ---
    chalk = np.clip(0.45 + 0.35 * up + 0.18 * lo + 0.08 * mid, 0, 1)
    col = lerp(np.asarray(paint_lo), np.asarray(paint_hi), chalk)
    col = col * (1 + 0.05 * hi)[..., None]
    # --- peel mask ---
    pv = 0.55 * lo + 0.35 * mid + 0.12 * hi + 1.6 * convex + 0.45 * np.clip(up, 0, 1) + 0.5 * (1 - ao) + peel_amt
    peel = smoothstep(1.05, 1.15, pv)
    ring = smoothstep(0.92, 1.05, pv) * (1 - peel)
    # --- rust ---
    r_t = np.clip(0.5 + 0.35 * mid + 0.25 * hi, 0, 1)
    rust_dark = np.array([0.075, 0.035, 0.018]); rust_or = np.array([0.30, 0.115, 0.035]); rust_mid = np.array([0.17, 0.07, 0.03])
    rcol = lerp(lerp(rust_dark, rust_mid, smoothstep(0.2, 0.6, r_t)), rust_or, smoothstep(0.6, 0.95, r_t))
    pits = smoothstep(1.2, 1.9, fbm(P, 0.004, seed + 140, oct=2))
    rcol = rcol * (1 - 0.5 * pits)[..., None]
    # rust blooms through intact paint (blisters)
    bloom = smoothstep(1.4, 2.0, mid + 0.6 * lo + 0.6 * (1 - ao)) * (1 - peel)
    col = lerp(col, lerp(col, rust_mid, 0.75), bloom * 0.8)
    col = lerp(col, col * 1.18 + 0.02, ring * 0.7)          # lifted, chalkier flake edge
    col = lerp(col, rcol, peel)
    # --- streaks ---
    S = streaks(P, N, used, sources, 1.0, seed + 3)
    gr = fbm(P, 0.15, seed + 200, oct=4, stretch=(1, 1, 9))
    grime = np.clip(smoothstep(0.4, 1.6, gr) * (1 - np.abs(up)) * (0.35 + 0.65 * (1 - ao)), 0, 1)
    stain = np.array([0.22, 0.085, 0.03])
    col = lerp(col, stain, np.clip(S * 0.85, 0, 0.85))
    col = lerp(col, np.array([0.12, 0.075, 0.045]), grime * 0.35)
    # --- dust/sand on horizontal surfaces and in corners ---
    dust_col = np.array([0.40, 0.31, 0.22])
    dst = smoothstep(0.55, 0.9, up) * np.clip(0.55 + 0.45 * lo + 0.3 * (1 - ao), 0, 1) + 0.35 * (1 - ao) * smoothstep(0.0, 0.5, up)
    dst = np.clip(dst * smoothstep(-0.6, 0.6, mid + 0.5), 0, 0.92)
    col = lerp(col, dust_col * (1 + 0.1 * hi)[..., None], dst)
    # --- bird droppings ---
    D = droppings(P, N, used, perch, seed + 7)
    col = lerp(col, np.array([0.70, 0.68, 0.62]) * (1 - 0.15 * smoothstep(0, 1, hi))[..., None], D * 0.9)
    # --- AO baked mildly into albedo ---
    col = col * (0.55 + 0.45 * ao ** 0.8)[..., None]
    col = np.clip(col, 0.03, 0.85)
    rough = 0.78 + 0.08 * chalk + 0.10 * peel + 0.08 * dst - 0.05 * D
    metal = np.zeros_like(rough)
    h = 0.12 * (1 - peel) + 0.05 * ring - 0.06 * pits * peel + 0.04 * dst * hi + 0.08 * D + 0.03 * bloom
    return col, np.clip(rough, 0.4, 1.0), metal, h


def weather_steel(P, N, AO, E, used, sources, perch, seed=21):
    """Dark weathered steel (face frame) + dull galvanized (ladder, cage, lamps, conduit, boxes)."""
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    gz = -P[..., 1]; gy = P[..., 2]
    frame = ((gz > -0.25) & (gz < 0.05) & (gy > 2.6)).astype(np.float32)
    frame = ndi.gaussian_filter(frame, 1.0)
    # dark painted steel version
    c1, r1, m1, h1 = weather_painted(P, N, AO, E, used, sources, perch, [0.045, 0.048, 0.045], [0.11, 0.11, 0.10], seed=seed, peel_amt=0.05)
    # galvanized: dull zinc grey, white-rust mottling, red rust spots, sand
    lo = fbm(P, 0.25, seed + 300, oct=4); mid = fbm(P, 0.04, seed + 340, oct=4); hi = fbm(P, 0.01, seed + 380, oct=2)
    g = np.array([0.30, 0.30, 0.29]) * (1 + 0.10 * lo + 0.06 * mid)[..., None]
    white = smoothstep(0.6, 1.4, mid + 0.3 * lo) * 0.5
    g = lerp(g, np.array([0.46, 0.45, 0.42]), white)
    rs = smoothstep(1.2, 1.8, mid + 0.5 * hi + 0.6 * (1 - ao) + 0.3 * lo)
    rc = lerp(np.array([0.09, 0.04, 0.02]), np.array([0.26, 0.10, 0.035]), np.clip(0.5 + 0.4 * hi, 0, 1))
    g = lerp(g, rc, rs)
    S = streaks(P, N, used, sources, 0.8, seed + 5)
    g = lerp(g, np.array([0.22, 0.09, 0.035]), np.clip(S * 0.8, 0, 0.8))
    dst = np.clip(smoothstep(0.55, 0.9, up) * (0.5 + 0.4 * lo) + 0.3 * (1 - ao) * smoothstep(0.0, 0.5, up), 0, 0.9)
    g = lerp(g, np.array([0.40, 0.31, 0.22]), dst)
    D = droppings(P, N, used, perch, seed + 8)
    g = lerp(g, np.array([0.70, 0.68, 0.62]), D * 0.9)
    g = g * (0.55 + 0.45 * ao ** 0.8)[..., None]
    rg = 0.62 + 0.15 * white + 0.25 * rs + 0.25 * dst + 0.05 * lo
    mg = np.clip(0.55 * (1 - rs) * (1 - dst) * (1 - white * 0.6) * (1 - D), 0, 1)
    hg = 0.05 * rs * hi + 0.04 * dst + 0.08 * D
    f = frame[..., None]
    col = np.clip(c1 * f + g * (1 - f), 0.03, 0.85)
    return col, np.clip(r1 * frame + rg * (1 - frame), 0.35, 1), m1 * frame + mg * (1 - frame), h1 * frame + hg * (1 - frame)


def weather_concrete(P, N, AO, E, used, seed=31):
    up = N[..., 2]
    ao = np.clip(AO[..., 0], 0, 1)
    edge = np.clip((1 - E[..., 0]) * 6, 0, 1)
    lo = fbm(P, 0.3, seed, oct=5); mid = fbm(P, 0.05, seed + 40, oct=4); hi = fbm(P, 0.006, seed + 80, oct=2)
    col = np.array([0.38, 0.35, 0.31]) * (1 + 0.08 * lo + 0.05 * mid + 0.07 * hi)[..., None]
    agg = smoothstep(1.0, 1.6, fbm(P, 0.008, seed + 120, oct=2))
    col = lerp(col, np.array([0.30, 0.28, 0.25]), agg * 0.5)
    # rust stain from the base plate: ring on the top around r~0.7, running down the side under the anchors
    gx, gz, gy = P[..., 0], -P[..., 1], P[..., 2]
    rr = np.hypot(gx, gz + 0.65)
    ring = np.exp(-((rr - 0.72) / 0.07) ** 2) * smoothstep(0.5, 0.9, up)
    ang = np.arctan2(gz + 0.65, gx)
    anch = np.cos((ang - np.pi / 8) * 8) * 0.5 + 0.5
    side = (1 - smoothstep(0.3, 0.7, np.abs(up))) * np.exp(-np.clip(0.30 - gy, 0, None) / 0.25) * anch ** 3
    st = np.clip((ring + side) * (0.6 + 0.4 * fbm(P, 0.02, seed + 9, oct=3, stretch=(1, 1, 6))), 0, 1)
    col = lerp(col, np.array([0.25, 0.12, 0.05]), st * 0.7)
    # damp/dirt band near ground, chips on the edge
    band = smoothstep(0.08, -0.02, gy)
    col = lerp(col, np.array([0.30, 0.24, 0.18]), band * 0.7)
    chip = smoothstep(0.9, 1.4, mid + 0.8 * edge) * edge
    col = lerp(col, np.array([0.30, 0.28, 0.25]), chip * 0.6)
    dst = smoothstep(0.6, 0.9, up) * np.clip(0.4 + 0.4 * lo, 0, 1)
    col = lerp(col, np.array([0.42, 0.33, 0.24]), dst * 0.6)
    col = col * (0.6 + 0.4 * ao)[..., None]
    rough = 0.9 + 0.05 * dst
    h = 0.15 * hi + 0.4 * agg - 1.2 * chip
    return np.clip(col, 0.03, 0.85), np.clip(rough, 0.5, 1) * np.ones_like(up), np.zeros_like(up), h
