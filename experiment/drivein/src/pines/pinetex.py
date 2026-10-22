"""Textures for the pines: tileable bark (albedo + normal) per species and RGBA needle-card atlases.

Bark
  ponderosa : big jigsaw plates (cinnamon / orange-brown), separated by deep near-black furrows; plates are made of
              thin flaking scales.
  lodgepole : thin bark, small grey-brown flaky scales, no deep furrows.
  fir       : Douglas fir: thick, dark grey-brown, deeply furrowed vertical ridges with cross-breaks.
Needle atlases (1024², 2×2 cells, 4 variants each; colour = real albedo, alpha = needles)
  ponderosa : long-needle bottlebrush tufts (needles 15-25 cm in threes) at the end of a stout twig.
  lodgepole : short (5 cm) paired needles crowding stout twigs: a small branchlet with 2-3 twiglets.
  fir       : flat sprays: a twig with alternate side twigs, short needles all round, feathery outline.
"""
import os, math
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw
from common import tile_noise, height_to_normal, save_img, smoothstep, srgb, TEXCACHE


def worley(h, w, ncx, ncy, seed, warp=None):
    rng = np.random.default_rng(seed)
    gx, gy = np.meshgrid(np.arange(ncx), np.arange(ncy))
    px = (gx + rng.uniform(0.15, 0.85, gx.shape)) / ncx
    py = (gy + rng.uniform(0.15, 0.85, gy.shape)) / ncy
    # metric: cells are taller than wide → compare in a space scaled by cell aspect
    sx, sy = ncx, ncy
    pts = np.stack([px.ravel() * sx, py.ravel() * sy], -1)
    tree = cKDTree(pts, boxsize=[sx, sy])
    yy, xx = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij')
    if warp is not None:
        xx = (xx + warp[0]) % 1.0; yy = (yy + warp[1]) % 1.0
    q = np.stack([(xx * sx).ravel() % sx, (yy * sy).ravel() % sy], -1)
    d, i = tree.query(q, k=2)
    return d[:, 0].reshape(h, w), d[:, 1].reshape(h, w), i[:, 0].reshape(h, w)


def bark(kind, size=1024, seed=5):
    h = w = size
    rng = np.random.default_rng(seed)
    wx = tile_noise(h, w, beta=3.0, seed=seed + 1) * 0.02
    wy = tile_noise(h, w, beta=3.0, seed=seed + 2) * 0.03
    fine = tile_noise(h, w, beta=1.4, seed=seed + 3)
    fib = tile_noise(h, w, beta=1.8, ax=0.25, ay=5.0, seed=seed + 4)     # vertical fibres/flakes
    big = tile_noise(h, w, beta=3.2, seed=seed + 5)
    if kind == 'ponderosa':
        # tile = 1.2 m around × 1.6 m tall: ~5 plates across, ~4 down
        f1, f2, cid = worley(h, w, 5, 4, seed, warp=(wx, wy))
        edge = f2 - f1                                       # 0 at the furrow
        plate = smoothstep(0.03, 0.28, edge + 0.04 * fine)
        prand = np.random.default_rng(seed + 9).random(cid.max() + 1)[cid]
        # flaky scales within a plate: small worley, shallow steps
        g1, g2, gid = worley(h, w, 26, 30, seed + 11, warp=(wx * 2, wy * 2))
        scale_e = smoothstep(0.0, 0.12, g2 - g1)
        srand = np.random.default_rng(seed + 12).random(gid.max() + 1)[gid]
        hgt = plate * (0.75 + 0.25 * prand) + plate * (0.08 * scale_e + 0.06 * srand) + 0.02 * fine
        top = np.array([0.27, 0.13, 0.065])                 # cinnamon/orange plate faces
        top2 = np.array([0.22, 0.14, 0.095])                 # greyer, older faces
        side = np.array([0.12, 0.065, 0.038])
        furrow = np.array([0.028, 0.018, 0.013])
        t = plate[..., None]
        c = furrow + (side - furrow) * smoothstep(0.0, 0.35, t) + (top - side) * smoothstep(0.4, 0.9, t)
        mix = smoothstep(-0.3, 1.0, big + 0.6 * (prand - 0.5))[..., None]
        c = c * (1 - 0.45 * mix) + (top2 * t) * 0.45 * mix
        c *= (0.80 + 0.35 * srand[..., None]) * (1 - 0.35 * (1 - scale_e[..., None]) * t)
        c *= (1 + 0.08 * fine[..., None])
        nstr = 14.0
    elif kind == 'lodgepole':
        g1, g2, gid = worley(h, w, 20, 34, seed + 21, warp=(wx, wy))
        scale_e = smoothstep(0.0, 0.18, g2 - g1)
        srand = np.random.default_rng(seed + 22).random(gid.max() + 1)[gid]
        hgt = scale_e * (0.5 + 0.5 * srand) + 0.1 * fib + 0.05 * fine
        base = np.array([0.20, 0.155, 0.12])
        c = base * (0.55 + 0.45 * scale_e[..., None]) * (0.75 + 0.45 * srand[..., None])
        warm = smoothstep(0.6, 1.0, srand)[..., None] * np.array([0.06, 0.02, -0.01])
        c = c + warm * scale_e[..., None]
        c *= (1 + 0.10 * big[..., None] + 0.08 * fine[..., None])
        # grey lichen-ish weathering
        lich = smoothstep(1.2, 2.0, tile_noise(h, w, beta=2.4, seed=seed + 23))[..., None]
        c = c * (1 - 0.35 * lich) + np.array([0.26, 0.25, 0.22]) * 0.35 * lich
        nstr = 8.0
    else:  # fir
        # deep vertical furrows: worley with tall cells → ridges, then cross-breaks
        f1, f2, cid = worley(h, w, 7, 3, seed + 31, warp=(wx * 1.5, wy * 0.5))
        edge = f2 - f1
        ridge = smoothstep(0.02, 0.35, edge + 0.05 * fine)
        prand = np.random.default_rng(seed + 32).random(cid.max() + 1)[cid]
        cross = smoothstep(0.1, 0.5, np.abs(np.sin((np.arange(h)[:, None] / h * 9 + prand * 3) * np.pi))) * 0.25 + 0.75
        hgt = ridge * cross * (0.8 + 0.2 * prand) + 0.12 * fib * ridge + 0.03 * fine
        top = np.array([0.20, 0.135, 0.095])
        side = np.array([0.10, 0.065, 0.045])
        furrow = np.array([0.03, 0.02, 0.015])
        t = (ridge * cross)[..., None]
        c = furrow + (side - furrow) * smoothstep(0.0, 0.4, t) + (top - side) * smoothstep(0.5, 0.95, t)
        c *= (1 + 0.12 * fib[..., None] + 0.08 * big[..., None])
        nstr = 12.0
    hgt = ndimage.gaussian_filter(hgt, 0.8, mode='wrap')
    nmap = height_to_normal(hgt * nstr)
    a = save_img(np.clip(c, 0.025, 0.9), f'bark_{kind}_albedo.jpg')
    n = save_img(nmap, f'bark_{kind}_normal.jpg', linear_to_srgb=False)
    return a, n


# --------------------------------------------------------------------------------------------- needle atlases
def _c8(lin, a=255):
    s = srgb(np.clip(np.asarray(lin, float), 0, 1))
    return tuple(int(x * 255 + 0.5) for x in s) + (a,)


def needle_col(rng, kind, tip=0.0):
    """Linear albedo for one needle. Colours carry the full value; vertex colours only add AO and jitter."""
    if kind == 'ponderosa':     # yellow-green, warm
        base = np.array([0.048, 0.100, 0.040])
        hi = np.array([0.085, 0.145, 0.052])
    elif kind == 'lodgepole':   # yellow-green, a touch darker
        base = np.array([0.044, 0.092, 0.040])
        hi = np.array([0.078, 0.130, 0.050])
    else:                       # Douglas fir: deep green, slightly blue
        base = np.array([0.030, 0.072, 0.045])
        hi = np.array([0.055, 0.105, 0.062])
    c = base + (hi - base) * rng.uniform(0, 1) * 0.7
    if rng.random() < 0.05:     # a few dead/browning needles
        c = np.array([0.20, 0.10, 0.04]) * rng.uniform(0.6, 1.1)
    return c * rng.uniform(0.8, 1.15)


def curve(p0, d, L, bend, n=6):
    a0 = math.atan2(d[1], d[0])
    t = np.linspace(0, 1, n)
    a = a0 + bend * t
    seg = L / (n - 1)
    x = p0[0] + np.concatenate([[0], np.cumsum(np.cos(a[:-1]) * seg)])
    y = p0[1] + np.concatenate([[0], np.cumsum(np.sin(a[:-1]) * seg)])
    return list(zip(x, y))


def draw_ponderosa(dr, S, rng):
    # coordinates: x right, y down; twig from the bottom centre upward
    tw = [(S * 0.5 + rng.normal(0, S * 0.02), S * 1.0)]
    ang = -math.pi / 2 + rng.normal(0, 0.12)
    p = np.array(tw[0])
    for i in range(8):
        ang += rng.normal(0, 0.05)
        p = p + np.array([math.cos(ang), math.sin(ang)]) * S * 0.055
        tw.append(tuple(p))
    twig = np.array(tw)
    # needles: from the upper 70% of the twig, sweeping forward (up) and out, longest mid-twig
    nf = 70
    for k in range(nf):
        t = 0.3 + 0.7 * rng.random() ** 0.7
        i = t * (len(twig) - 1); i0 = int(min(i, len(twig) - 2)); f = i - i0
        q = twig[i0] * (1 - f) + twig[i0 + 1] * f
        side = rng.choice([-1, 1])
        spread = rng.uniform(0.15, 1.15) * (1.15 - 0.6 * t)
        a = ang + side * spread
        L = S * rng.uniform(0.34, 0.48) * (0.85 + 0.25 * math.sin(math.pi * t))
        bend = -side * rng.uniform(0.05, 0.35)            # needles curve back toward the twig axis (upward)
        col = needle_col(rng, 'ponderosa')
        for j in range(3):                                 # fascicle of three
            aj = a + rng.normal(0, 0.035)
            pts = curve(q, (math.cos(aj), math.sin(aj)), L * rng.uniform(0.93, 1.0), bend + rng.normal(0, 0.05))
            dr.line(pts, fill=_c8(col * rng.uniform(0.85, 1.1)), width=max(2, S // 230))
    # terminal brush and bud
    for k in range(18):
        a = ang + rng.normal(0, 0.35)
        col = needle_col(rng, 'ponderosa')
        pts = curve(twig[-1], (math.cos(a), math.sin(a)), S * rng.uniform(0.25, 0.4), rng.normal(0, 0.2))
        dr.line(pts, fill=_c8(col), width=max(2, S // 230))
    dr.line([tuple(x) for x in twig[:5]], fill=_c8([0.12, 0.07, 0.04]), width=max(3, S // 70))


def draw_lodgepole(dr, S, rng):
    def twig(p0, ang, L, w):
        pts = [np.array(p0)]
        a = ang
        for i in range(10):
            a += rng.normal(0, 0.05)
            pts.append(pts[-1] + np.array([math.cos(a), math.sin(a)]) * L / 10)
        pts = np.array(pts)
        # short paired needles all along, pointing forward, dense; denser and longer near the tip
        for k in range(int(L / S * 260)):
            t = rng.random() ** 0.8
            i = t * (len(pts) - 1); i0 = int(min(i, len(pts) - 2)); f = i - i0
            q = pts[i0] * (1 - f) + pts[i0 + 1] * f
            side = rng.choice([-1, 1])
            na = a + side * rng.uniform(0.25, 1.1)
            nl = S * rng.uniform(0.11, 0.17)
            col = needle_col(rng, 'lodgepole')
            for j in range(2):
                aj = na + rng.normal(0, 0.12)
                dr.line(curve(q, (math.cos(aj), math.sin(aj)), nl, -side * rng.uniform(0, 0.3), n=4),
                        fill=_c8(col * rng.uniform(0.9, 1.1)), width=max(2, S // 220))
        dr.line([tuple(x) for x in pts], fill=_c8([0.10, 0.07, 0.045]), width=w)
        return pts
    main = twig((S * 0.5, S * 1.0), -math.pi / 2 + rng.normal(0, 0.1), S * 0.82, max(3, S // 90))
    for k in range(rng.integers(2, 4)):
        t = rng.uniform(0.25, 0.65)
        q = main[int(t * (len(main) - 1))]
        twig(q, -math.pi / 2 + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9), S * rng.uniform(0.35, 0.5), max(2, S // 140))


def draw_fir(dr, S, rng):
    def spray(p0, ang, L, depth):
        pts = [np.array(p0)]
        a = ang
        for i in range(12):
            a += rng.normal(0, 0.03)
            pts.append(pts[-1] + np.array([math.cos(a), math.sin(a)]) * L / 12)
        pts = np.array(pts)
        # flat ranks of short needles on both sides (2–3 cm), plus a few on top
        nl0 = S * 0.055
        for i in range(len(pts) - 1):
            for k in range(9):
                f = rng.random()
                q = pts[i] * (1 - f) + pts[i + 1] * f
                tt = (i + f) / (len(pts) - 1)
                nl = nl0 * (1.0 - 0.35 * tt) * rng.uniform(0.8, 1.1)
                side = 1 if k % 2 else -1
                na = a + side * rng.uniform(0.7, 1.25)
                col = needle_col(rng, 'fir')
                dr.line(curve(q, (math.cos(na), math.sin(na)), nl, -side * 0.15, n=3), fill=_c8(col),
                        width=max(2, S // 200))
        dr.line([tuple(x) for x in pts], fill=_c8([0.09, 0.06, 0.04]), width=max(2, S // (120 + depth * 80)))
        if depth == 0:
            for j in range(1, 11):
                t = j / 11
                q = pts[int(t * (len(pts) - 1))]
                for side in (-1, 1):
                    if rng.random() < 0.85:
                        spray(q, a + side * rng.uniform(0.6, 0.9), L * (0.42 - 0.3 * t) * rng.uniform(0.8, 1.1), 1)
    spray((S * 0.5, S * 1.0), -math.pi / 2 + rng.normal(0, 0.05), S * 0.95, 0)


def atlas(kind, size=1024, seed=1):
    """2×2 atlas of four card variants. Cell (i, j): u in [i/2, (i+1)/2], v in [j/2, (j+1)/2]; twig base at the
    bottom centre of each cell (v low), growing toward +v."""
    rng = np.random.default_rng(seed)
    S2 = size                                   # cell size at 2× supersampling
    img = Image.new('RGBA', (size * 2, size * 2), (0, 0, 0, 0))
    for ci in range(4):
        cell = Image.new('RGBA', (S2, S2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(cell)
        {'ponderosa': draw_ponderosa, 'lodgepole': draw_lodgepole, 'fir': draw_fir}[kind](dr, S2, rng)
        img.paste(cell, ((ci % 2) * S2, (ci // 2) * S2))
    img = img.resize((size, size), Image.LANCZOS)
    a = np.asarray(img).astype(np.float64) / 255
    alpha = a[..., 3]
    # thicken alpha slightly so the mip chain keeps coverage at distance (alpha-test thinning)
    alpha = np.clip(alpha * 1.6, 0, 1)
    m = alpha > 0.05
    col = a[..., :3].copy()
    # un-premultiply-ish: colours of semi-transparent edge texels are fine (PIL resizes straight alpha)
    idx = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
    col = col[idx[0], idx[1]]
    out = np.concatenate([col, alpha[..., None]], -1)
    path = os.path.join(TEXCACHE, f'needles_{kind}.png')
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, optimize=True)
    # mean colour of covered texels (linear), for calibration
    lin = np.where(out[..., :3] <= 0.04045, out[..., :3] / 12.92, ((out[..., :3] + 0.055) / 1.055) ** 2.4)
    mc = lin[alpha > 0.5].mean(0)
    print(f'needles_{kind}: coverage {np.mean(alpha > 0.5):.2f}, mean linear {np.round(mc, 3)}')
    return path


if __name__ == '__main__':
    import sys
    for k in sys.argv[1:] or ['ponderosa', 'lodgepole', 'fir']:
        print(bark(k)); print(atlas(k))
