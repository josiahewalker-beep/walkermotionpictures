"""Shared helpers for the SET thread's procedural textures (numpy / scipy / PIL only).
All fields are periodic (wrap) unless stated, so every output tiles seamlessly.
Colour work is done in linear RGB and converted to sRGB on save."""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from PIL import Image

def rng(seed):
    return np.random.default_rng(seed)

def norm01(a):
    a = a - a.min()
    return a / max(a.max(), 1e-9)

def gblur(a, s, axis_sig=None):
    return ndi.gaussian_filter(a, s if axis_sig is None else axis_sig, mode='wrap')

def spectral(shape, r, beta=2.0, lo=1.0, hi=None, aniso=(1.0, 1.0)):
    """Periodic 1/f^beta noise in [-1,1]-ish (std 1). lo/hi: band limits in cycles per tile.
    aniso=(sy, sx) stretches frequencies: (1, 4) gives features elongated along rows (y)."""
    H, W = shape
    fy = np.fft.fftfreq(H)[:, None] * H * aniso[0]
    fx = np.fft.fftfreq(W)[None, :] * W * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    amp = np.where(f >= lo, 1.0 / np.maximum(f, 1e-6) ** (beta / 2), 0.0)
    if hi is not None:
        amp *= np.exp(-(f / hi) ** 2)
    ph = np.fft.fft2(r.standard_normal(shape))
    out = np.real(np.fft.ifft2(ph * amp))
    return (out - out.mean()) / (out.std() + 1e-9)

def worley(shape, cell, r, jitter=1.0, aspect=(1.0, 1.0), drop=0.0):
    """Periodic cellular noise. Returns F1, F2 (px), cell id (int), points (N,2 in px, y,x).
    cell: average spacing in px. aspect scales the grid (y, x)."""
    H, W = shape
    ny, nx = max(2, int(round(H / (cell * aspect[0])))), max(2, int(round(W / (cell * aspect[1]))))
    gy, gx = np.meshgrid(np.arange(ny), np.arange(nx), indexing='ij')
    py = (gy + 0.5 + (r.random(gy.shape) - 0.5) * jitter) * H / ny
    px = (gx + 0.5 + (r.random(gx.shape) - 0.5) * jitter) * W / nx
    pts = np.stack([py.ravel() % H, px.ravel() % W], 1)
    tree = cKDTree(pts, boxsize=[H, W])
    yy, xx = np.mgrid[0:H, 0:W]
    q = np.stack([yy.ravel() + 0.5, xx.ravel() + 0.5], 1) % [H, W]
    d, i = tree.query(q, k=2, workers=-1)
    return (d[:, 0].reshape(shape), d[:, 1].reshape(shape), i[:, 0].reshape(shape), pts)

def warp(a, dy, dx, order=1):
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    c = [yy + dy, xx + dx]
    if a.ndim == 2:
        return ndi.map_coordinates(a, c, order=order, mode='grid-wrap')
    return np.stack([ndi.map_coordinates(a[..., k], c, order=order, mode='grid-wrap') for k in range(a.shape[2])], -1)

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def normal_from_height(h, strength, px_mm=1.0):
    """h in millimetres; px_mm = millimetres per pixel. glTF / OpenGL convention (+Y = up in image).
    strength multiplies the slope (1 = physically correct)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * px_mm) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * px_mm) * strength   # +row = down in image
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n

def save_normal(n, path, quality=95):
    img = np.clip((n * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)
    _save(img, path, quality)

def lin2srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)

def srgb2lin(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def save_srgb(lin, path, quality=93):
    img = np.clip(lin2srgb(lin) * 255 + 0.5, 0, 255).astype(np.uint8)
    _save(img, path, quality)

def save_gray(a, path, quality=93):
    img = np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)
    _save(img, path, quality)

def _save(img, path, quality):
    im = Image.fromarray(img)
    if path.endswith('.jpg'):
        im.save(path, quality=quality, subsampling=0 if quality >= 95 else 2, optimize=True)
    else:
        im.save(path, optimize=True)

def stamp_line(mask, pts, val=1.0):
    """Accumulate a polyline (list of (y,x) px, may exceed bounds: wraps) into mask, max-combined."""
    H, W = mask.shape
    pts = np.asarray(pts, float)
    for a, b in zip(pts[:-1], pts[1:]):
        n = int(np.ceil(np.hypot(*(b - a)) * 2)) + 1
        t = np.linspace(0, 1, n)[:, None]
        p = a + (b - a) * t
        iy, ix = np.round(p[:, 0]).astype(int) % H, np.round(p[:, 1]).astype(int) % W
        mask[iy, ix] = np.maximum(mask[iy, ix], val)
    return mask

def crack_path(r, start, heading, length, step=2.0, wander=0.35, persist=0.85):
    """Random-walk crack polyline (px). heading in radians (0 = +x)."""
    pts = [np.array(start, float)]
    h, dh = heading, 0.0
    for _ in range(int(length / step)):
        dh = dh * persist + r.normal(0, wander) * (1 - persist) * 3
        h2 = h + dh
        pts.append(pts[-1] + step * np.array([np.sin(h2), np.cos(h2)]))
        h = heading + (h - heading) * 0.97 + dh * 0.1
    return pts

def tile3(path, out, scale=None):
    im = Image.open(path)
    if scale:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    w, h = im.size
    t = Image.new(im.mode, (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            t.paste(im, (i * w, j * h))
    t.save(out)

def splat_pebbles(h, col, r, n, rmin, rmax, palette, weights, power=2.5, height_k=0.6, flat=(0.45, 1.0),
                  mask=None, varnish=None, idmap=None):
    """Splat n elliptical domed pebbles (sizes in px, power-law between rmin..rmax) into height h (max-composite)
    and linear colour col (H,W,3). Wraps. mask: optional (H,W) density mask in [0,1] used for rejection.
    Returns coverage map. Pebbles are drawn smallest-last so big ones never bury small ones entirely."""
    H, W = h.shape
    cov = np.zeros_like(h)
    sizes = rmin + (rmax - rmin) * r.random(n) ** power
    order = np.argsort(-sizes)
    pal = np.asarray(palette); pw = np.asarray(weights, float); pw /= pw.sum()
    picks = r.choice(len(pal), n, p=pw)
    for k in order:
        s = sizes[k]
        cy, cx = r.random() * H, r.random() * W
        if mask is not None and r.random() > mask[int(cy) % H, int(cx) % W]:
            continue
        ar = r.uniform(*flat)                      # aspect
        th = r.random() * np.pi
        R = int(np.ceil(s)) + 2
        oy, ox = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
        fy, fx = oy - (cy % 1), ox - (cx % 1)
        c, si = np.cos(th), np.sin(th)
        a = (c * fx + si * fy) / s
        b = (-si * fx + c * fy) / (s * ar)
        # irregular outline: perturb radius by low-order angular harmonics
        ang = np.arctan2(b, a)
        rr = 1 + 0.12 * np.sin(2 * ang + r.random() * 6) + 0.08 * np.sin(3 * ang + r.random() * 6)
        d2 = (a * a + b * b) / (rr * rr)
        inside = d2 < 1
        if not inside.any():
            continue
        dome = np.sqrt(np.clip(1 - d2, 0, 1))
        ph = s * ar * height_k * dome * (0.6 + 0.4 * r.random())
        iy = (int(cy) + oy.astype(int)) % H
        ix = (int(cx) + ox.astype(int)) % W
        cur = h[iy, ix]
        win = inside & (ph + 0.0 > cur)
        if not win.any():
            continue
        base = pal[picks[k]] * (0.78 + 0.44 * r.random())
        shade = (0.86 + 0.14 * dome)[..., None]          # slightly darker at the rim (contact dirt), not lighting
        aa = smoothstep(1.0, 0.75, d2)[..., None] * win[..., None]
        sub = col[iy, ix]
        col[iy, ix] = sub * (1 - aa) + base * shade * aa
        h[iy, ix] = np.where(win, np.maximum(cur, ph), cur)
        cov[iy, ix] = np.maximum(cov[iy, ix], aa[..., 0])
        if idmap is not None:
            idmap[iy, ix] = np.where(win, k, idmap[iy, ix])
    return cov

def chipseal(N, mm_px, seed, shape=None):
    """Chip-seal asphalt surface. Returns dict(col (lin RGB), h (mm), stone, top, h_stone, dust_amt, dust_field).
    Stone spacing ~12 mm regardless of resolution. shape overrides (N,N)."""
    r = rng(seed)
    shp = shape or (N, N)
    Hh, Ww = shp
    k = 1.953 / mm_px                              # scale relative to the 4 m / 2048 master
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
    wy = gblur(r.standard_normal(shp), 2.0 * k) * 3.0 * k; wx = gblur(r.standard_normal(shp), 2.0 * k) * 3.0 * k
    F1, F2, cid, pts = worley(shp, 6.2 * k, r, jitter=0.95)
    F1 = warp(F1, wy, wx); F2 = warp(F2, wy, wx); cid = warp(cid.astype(np.float32), wy, wx, order=0).astype(int)
    ncell = len(pts)
    size_k = np.clip(r.normal(1.0, 0.22, ncell), 0.5, 1.5)
    loss = r.random(ncell) < 0.12
    rad = 3.05 * k * size_k[cid]
    inside = np.minimum(rad - F1, (F2 - F1) * 0.9 - 0.35 * k)
    stone = smoothstep(-0.2 * k, 1.1 * k, inside) * (~loss[cid])
    dome = np.sqrt(np.clip(inside / (rad * 0.8), 0, 1))
    tilt = (r.random((ncell, 2)) - 0.5) * 0.5 / k
    dyc = ((yy + 0.5 - pts[cid, 0] + Hh / 2) % Hh - Hh / 2)
    dxc = ((xx + 0.5 - pts[cid, 1] + Ww / 2) % Ww - Ww / 2)
    flat = r.random(ncell) < 0.45
    top = np.where(flat[cid], np.minimum(dome, 0.55) / 0.55, dome)
    h_stone = stone * (1.6 + 1.5 * size_k[cid]) * (top * 0.85 + 0.15) + stone * (tilt[cid, 0] * dyc + tilt[cid, 1] * dxc) * 0.3
    h_stone = np.maximum(h_stone, 0)
    del dyc, dxc
    G1, G2, gid, gpts = worley(shp, 2.4 * k, rng(seed + 20), jitter=1.0)
    grit = smoothstep(0.2 * k, 0.9 * k, G2 - G1) * (rng(seed + 21).random(len(gpts)) < 0.55)[gid]
    gcol = (0.10 + 0.12 * rng(seed + 22).random(len(gpts)))[gid]
    pal = np.array([[0.205, 0.200, 0.192], [0.140, 0.138, 0.134], [0.068, 0.067, 0.066],
                    [0.165, 0.118, 0.095], [0.215, 0.190, 0.155], [0.110, 0.106, 0.100]])
    pw = np.array([0.26, 0.32, 0.15, 0.06, 0.09, 0.12])
    pick = r.choice(len(pal), ncell, p=pw)
    scol = pal[pick] * (0.80 + 0.40 * r.random((ncell, 1)))
    speck = gblur(r.standard_normal(shp), 0.6 * k)
    stone_col = scol[cid] * (1 + 0.10 * speck[..., None])
    stone_col = stone_col * (0.88 + 0.12 * top[..., None])
    binder = np.array([0.050, 0.049, 0.047])
    dust = np.array([0.255, 0.215, 0.170])
    bcol = binder * (1 - grit[..., None]) + (gcol[..., None] * np.array([1.0, 0.96, 0.9])) * grit[..., None] * 0.8
    dust_field = norm01(spectral(shp, r, 2.4, lo=2, hi=400))
    dust_amt = np.clip((1 - stone) * (0.15 + 0.6 * dust_field ** 1.5), 0, 1) * 0.65
    col = stone_col * stone[..., None] + bcol * (1 - stone[..., None])
    col = col * (1 - dust_amt[..., None]) + dust * dust_amt[..., None]
    h = h_stone + grit * 0.6 - dust_amt * 0.3
    return dict(col=col, h=h, stone=stone, top=top, h_stone=h_stone, dust_amt=dust_amt, dust_field=dust_field, dust=dust)
