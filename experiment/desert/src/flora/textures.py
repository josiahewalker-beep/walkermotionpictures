"""Procedural textures for the flora assets (all original, generated with numpy/PIL).

bark   : corky, fissured, small squarish plates of old Joshua-tree trunks (albedo + normal), tileable.
thatch : dense skirt of dead, downward-pointing leaves (albedo), tileable — the core under the fur blades.
leaf   : a single living Yucca leaf strip (u across, v base→tip): pale serrated margin, striations, brown spine.
"""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from common import tile_noise, height_to_normal, save_img, smoothstep, TEXCACHE
import os


def worley(h, w, ncell_x, ncell_y, seed, stretch_y=1.0, warp=None):
    """Periodic Worley F1/F2 on an h×w grid. Points jittered on an ncell grid. stretch_y>1 → cells taller."""
    rng = np.random.default_rng(seed)
    gx, gy = np.meshgrid(np.arange(ncell_x), np.arange(ncell_y))
    px = (gx + rng.random(gx.shape)) / ncell_x
    py = (gy + rng.random(gy.shape)) / ncell_y
    pts = np.stack([px.ravel(), py.ravel() / stretch_y], -1)
    tree = cKDTree(pts, boxsize=[1.0, 1.0 / stretch_y])
    yy, xx = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij')
    if warp is not None:
        xx = (xx + warp[0]) % 1.0
        yy = (yy + warp[1]) % 1.0
    q = np.stack([xx.ravel(), (yy.ravel() / stretch_y) % (1.0 / stretch_y)], -1)
    d, i = tree.query(q, k=2)
    return d[:, 0].reshape(h, w), d[:, 1].reshape(h, w), i[:, 0].reshape(h, w)


def bark(size=1024, seed=3):
    """Joshua-tree trunk bark: corky, checkered into small oblong plates arranged in vertical columns,
    separated by deep fissures; fibrous plate tops, weathered grey with brown-grey flanks. Tileable."""
    h = w = size
    rng = np.random.default_rng(seed)
    yy, xx = np.meshgrid((np.arange(h) + 0.5) / h, (np.arange(w) + 0.5) / w, indexing='ij')
    warp = tile_noise(h, w, beta=3.2, ax=0.5, ay=2.0, seed=seed + 1) * 0.018
    xw = (xx + warp) % 1.0
    ncol = 22
    cx = xw * ncol
    col = np.floor(cx).astype(int) % ncol
    fx = cx - np.floor(cx)                                   # 0..1 across a column
    # irregular column widths: shift the furrow position per row band
    # horizontal breaks: per column, random phase and plate length
    plen = rng.uniform(0.045, 0.085, ncol)                   # plate length as a fraction of the tile
    nrows = np.maximum(1, np.round(1.0 / plen)).astype(int)
    phase = rng.random(ncol)
    ywarp = tile_noise(h, w, beta=3.0, seed=seed + 2) * 0.01
    cy = ((yy + ywarp + phase[col]) % 1.0) * nrows[col]
    row = np.floor(cy).astype(int)
    fy = cy - np.floor(cy)
    pid = col * 64 + row
    prand = np.random.default_rng(seed + 7).random(ncol * 64 + 64)
    # distance to plate edge (columns: deep fissures; rows: shallower cross-checks)
    ex = np.minimum(fx, 1 - fx)
    ey = np.minimum(fy, 1 - fy) / np.maximum(ncol / nrows[col], 1e-3) * 1.0
    deep = smoothstep(0.02, 0.30, ex + 0.06 * tile_noise(h, w, beta=2.0, seed=seed + 3))
    cross = smoothstep(0.02, 0.22, ey * 1.2 + 0.05 * tile_noise(h, w, beta=2.0, seed=seed + 4))
    plate = deep * (0.15 + 0.85 * cross)
    fib = tile_noise(h, w, beta=2.0, ax=0.3, ay=6.0, seed=seed + 5)
    fine = tile_noise(h, w, beta=1.5, seed=seed + 6)
    big = tile_noise(h, w, beta=3.2, seed=seed + 8)
    hgt = plate * (0.6 + 0.4 * prand[pid]) + 0.08 * fib * plate + 0.03 * fine + 0.05 * big
    hgt = ndimage.gaussian_filter(hgt, 0.8, mode='wrap')
    nmap = height_to_normal(hgt * 18.0)
    t = np.clip(hgt / np.percentile(hgt, 99), 0, 1)[..., None]
    top = np.array([0.36, 0.33, 0.29])
    side = np.array([0.26, 0.22, 0.18])
    furrow = np.array([0.075, 0.062, 0.05])
    c = furrow + (side - furrow) * smoothstep(0.05, 0.4, t) + (top - side) * smoothstep(0.55, 0.95, t)
    tint = (prand[pid] - 0.5)[..., None] * np.array([0.05, 0.045, 0.04])
    c = c + tint * t
    c = c * (1 + 0.10 * fine[..., None] + 0.12 * fib[..., None] + 0.08 * big[..., None])
    lich = smoothstep(1.5, 2.3, tile_noise(h, w, beta=2.6, seed=seed + 9)) * smoothstep(0.6, 0.9, t[..., 0])
    c = c * (1 - lich[..., None] * 0.4) + lich[..., None] * 0.4 * np.array([0.34, 0.33, 0.24])
    a = save_img(np.clip(c, 0.03, 0.9), 'bark_albedo.jpg')
    n = save_img(nmap, 'bark_normal.jpg', linear_to_srgb=False)
    return a, n


def thatch(size=1024, seed=5, n_blades=2600):
    """Overlapping dead leaves pointing DOWN the image (toward larger row = toward v=0 = toward the trunk base)."""
    from PIL import Image, ImageDraw
    h = w = size
    rng = np.random.default_rng(seed)
    ida = Image.new('I', (w, h), 0)
    dr = ImageDraw.Draw(ida)
    ya = rng.random(n_blades) * h                     # attachment row
    xa = rng.random(n_blades) * w
    L = rng.uniform(0.16, 0.30, n_blades) * h
    Wd = rng.uniform(0.010, 0.020, n_blades) * w
    lean = rng.normal(0, 0.10, n_blades)              # sideways drift (fraction of L)
    order = np.argsort(-ya)                           # lowest attachments first, highest drawn last (on top)
    for rank, i in enumerate(order):
        x0, y0, l, wd, ln = xa[i], ya[i], L[i], Wd[i], lean[i]
        pts = [(x0 - wd / 2, y0), (x0 + wd / 2, y0), (x0 + ln * l + wd * 0.35, y0 + 0.6 * l),
               (x0 + ln * l * 1.6, y0 + l), (x0 + ln * l - wd * 0.35, y0 + 0.6 * l)]
        for ox in (-w, 0, w):
            for oy in (-h, 0, h):
                dr.polygon([(px + ox, py + oy) for px, py in pts], fill=int(i + 1))
    ids = np.array(ida, dtype=np.int64)
    bid = np.maximum(ids - 1, 0)
    rows = np.arange(h)[:, None].astype(np.float64)
    t = ((rows - ya[bid]) % h) / L[bid]                       # 0 at attachment, 1 at tip
    t = np.clip(t, 0, 1)
    # per-blade tone: grey-straw to grey-brown, a few dark ones
    tone = rng.uniform(0.82, 1.08, n_blades)
    dark = rng.random(n_blades) < 0.12
    tone[dark] *= 0.62
    warm = rng.uniform(-0.04, 0.05, n_blades)
    base = np.array([0.40, 0.365, 0.30])
    col = base[None, None, :] * tone[bid][..., None]
    col[..., 0] += warm[bid]; col[..., 2] -= warm[bid] * 0.6
    # fibres along each blade
    fib = tile_noise(h, w, beta=1.4, ax=0.25, ay=8.0, seed=seed + 1)
    col *= (1 + 0.12 * fib[..., None])
    # lighter toward the tip (more exposed), darker near the attachment (under the blade above)
    col *= (0.70 + 0.30 * smoothstep(0.0, 0.8, t))[..., None]
    # contact shadows: where the blade above ends (boundary to a different id just above / beside)
    edge = np.zeros((h, w), np.float32)
    for dy, dx in ((-2, 0), (-4, 0), (0, 2), (0, -2), (-3, 2), (-3, -2)):
        edge = np.maximum(edge, (np.roll(np.roll(ids, dy, 0), dx, 1) != ids).astype(np.float32))
    edge = ndimage.gaussian_filter(edge, 1.2, mode='wrap')
    col *= (1 - 0.45 * np.clip(edge, 0, 1))[..., None]
    col = col / col.mean((0, 1), keepdims=True) * 0.62           # neutral-grey multiplier (linear mean ≈ 0.48)
    a = save_img(np.clip(col, 0.03, 1.0), 'thatch_albedo.jpg')
    hgt = (0.5 * t + 0.25 * fib * 0.2) - 0.6 * edge
    nmap = height_to_normal(ndimage.gaussian_filter(hgt, 1.0, mode='wrap') * 6.0)
    n = save_img(nmap, 'thatch_normal.jpg', linear_to_srgb=False)
    return a, n


def leaf(w=64, h=1024, seed=7):
    """Albedo multiplier strip for a living leaf; vertex colours carry the hue. Mean ≈ 0.85."""
    rng = np.random.default_rng(seed)
    u = (np.arange(w) + 0.5) / w
    v = 1 - (np.arange(h) + 0.5) / h                 # row 0 = tip (v = 1)
    U, V = np.meshgrid(u, v)
    col = np.ones((h, w, 3)) * 0.86
    # fine parallel striations
    stri = 0.5 + 0.5 * np.sin(U * np.pi * 18 + 0.6 * np.sin(V * 40))
    col *= (0.93 + 0.07 * stri)[..., None]
    # slightly lighter midline, darker toward margins, then a pale yellow-white serrated margin
    col *= (0.92 + 0.08 * np.cos((U - 0.5) * np.pi))[..., None]
    teeth = 0.5 + 0.5 * np.sign(np.sin(V * 2 * np.pi * 160))
    m = np.minimum(U, 1 - U)
    margin = (m < 0.055 + 0.02 * teeth).astype(np.float64)
    margin = ndimage.gaussian_filter(margin, 0.6)
    pale = np.array([1.35, 1.30, 0.80])               # multiplier against a green vertex colour → pale straw edge
    col = col * (1 - margin[..., None]) + pale * margin[..., None] * 0.80
    # pale sheathing base, brown terminal spine
    base = smoothstep(0.08, 0.0, V)
    col = col * (1 - base[..., None]) + np.array([1.6, 1.5, 1.0]) * 0.55 * base[..., None]
    tip = smoothstep(0.90, 0.985, V)
    col = col * (1 - tip[..., None]) + np.array([1.7, 1.05, 0.65]) * 0.5 * tip[..., None]
    col = np.clip(col, 0.02, 1.0)
    return save_img(col, 'leaf_albedo.png')


def dead_leaf(w=64, h=512, seed=8):
    """Albedo for individual dead fur blades (fibrous, split, greyed). Mean ≈ 0.9 (vertex colour carries tone)."""
    u = (np.arange(w) + 0.5) / w
    v = 1 - (np.arange(h) + 0.5) / h
    U, V = np.meshgrid(u, v)
    fib = tile_noise(h, w, beta=1.2, ax=0.2, ay=10.0, seed=seed)
    col = np.ones((h, w, 3)) * (0.88 + 0.10 * fib[..., None])
    m = np.minimum(U, 1 - U)
    col *= (0.78 + 0.22 * smoothstep(0.0, 0.18, m))[..., None]
    return save_img(np.clip(col, 0.03, 1), 'deadleaf_albedo.jpg')


if __name__ == '__main__':
    print(bark()); print(thatch()); print(leaf()); print(dead_leaf())
