"""Tiling ground textures for the drive-in (4 m × 4 m, 2048 px, seamless):

lot_*    : compacted decomposed-granite dirt and fine gravel; tyre-packed smoother darker patches with faint tread
           prints running along v; scattered fallen ponderosa needles (singles and 3-needle fascicles) and a few cones.
forest_* : forest floor under the pines: deep needle duff, fresh rust-orange needles over older grey-brown ones,
           dark humus in the gaps, bark flakes, twigs and a few cones.

Outputs drivein/tex/{lot,forest}_{albedo,normal,rough}.jpg. Albedo sRGB; normal (OpenGL, +Y = +v) and rough linear.
Run: python3 ground.py [lot|forest]   (numpy + PIL only; ~1 min each)
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw, ImageFile
ImageFile.MAXBLOCK = 2 ** 26
from common import tile_noise, height_to_normal, smoothstep, srgb, TEX

S = 2048          # output px
SS = 2            # supersample for the drawn layers
M = 4.0           # metres per tile
PX = S / M        # px per metre (512)
os.makedirs(TEX, exist_ok=True)


def save(arr, name, to_srgb=True, q=90):
    a = np.clip(arr, 0, 1)
    if to_srgb:
        a = srgb(a)
    a8 = (a * 255 + 0.5).astype(np.uint8)
    if a8.ndim == 2:
        a8 = np.repeat(a8[..., None], 3, -1)
    Image.fromarray(a8).save(os.path.join(TEX, name), quality=q, subsampling=0, optimize=True)
    print('wrote', name, 'mean', np.round(arr.reshape(-1, arr.shape[-1] if arr.ndim == 3 else 1).mean(0), 3))


class Layer:
    """Supersampled painter's canvas: linear colour (float), height (float), roughness, coverage. Wraps at the edges."""

    def __init__(self):
        n = S * SS
        self.n = n
        self.col = [Image.new('F', (n, n), 0.0) for _ in range(3)]
        self.hgt = Image.new('F', (n, n), 0.0)
        self.rough = Image.new('F', (n, n), 0.0)
        self.cov = Image.new('F', (n, n), 0.0)
        self.d = [ImageDraw.Draw(im) for im in self.col + [self.hgt, self.rough, self.cov]]

    def _wrapped(self, pts, r):
        n = self.n
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        offs = []
        for ox in (-n, 0, n):
            if min(xs) + ox > n + r or max(xs) + ox < -r:
                continue
            for oy in (-n, 0, n):
                if min(ys) + oy > n + r or max(ys) + oy < -r:
                    continue
                offs.append((ox, oy))
        return offs

    def line(self, pts, width, col, h, rough):
        """pts in px of the output resolution; width in output px."""
        pts = [(x * SS, y * SS) for x, y in pts]
        w = max(1, int(round(width * SS)))
        vals = list(col) + [h, rough, 1.0]
        for ox, oy in self._wrapped(pts, w):
            q = [(x + ox, y + oy) for x, y in pts]
            for d, v in zip(self.d, vals):
                d.line(q, fill=float(v), width=w, joint='curve')

    def poly(self, pts, col, h, rough):
        pts = [(x * SS, y * SS) for x, y in pts]
        vals = list(col) + [h, rough, 1.0]
        for ox, oy in self._wrapped(pts, 2):
            q = [(x + ox, y + oy) for x, y in pts]
            for d, v in zip(self.d, vals):
                d.polygon(q, fill=float(v))

    def ellipse(self, cx, cy, rx, ry, ang, col, h, rough, n=14):
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        c, s = math.cos(ang), math.sin(ang)
        x = rx * np.cos(t); y = ry * np.sin(t)
        self.poly(list(zip(cx + x * c - y * s, cy + x * s + y * c)), col, h, rough)

    def arrays(self):
        def down(im):
            a = np.asarray(im, dtype=np.float32)
            return a.reshape(S, SS, S, SS).mean((1, 3))
        cov = down(self.cov)
        safe = np.maximum(cov, 1e-6)
        col = np.stack([down(c) for c in self.col], -1) / safe[..., None]
        return col, down(self.hgt) / safe, down(self.rough) / safe, cov


def needle_path(rng, x, y, L, ang, bend):
    k = 7
    t = np.linspace(0, 1, k)
    a = ang + bend * (t - 0.5)
    dx = np.cumsum(np.cos(a)) * L / (k - 1); dy = np.cumsum(np.sin(a)) * L / (k - 1)
    return list(zip(x + dx - dx[0], y + dy - dy[0]))


def needle_colour(rng, age):
    """Fallen ponderosa needles: fresh rust-orange → tan-brown → old grey-brown. Linear albedo."""
    fresh = np.array([0.36, 0.15, 0.045])
    tan = np.array([0.30, 0.17, 0.08])
    old = np.array([0.15, 0.11, 0.08])
    if age < 0.5:
        c = fresh + (tan - fresh) * (age / 0.5)
    else:
        c = tan + (old - tan) * ((age - 0.5) / 0.5)
    return c * rng.uniform(0.8, 1.15) * np.array([1, rng.uniform(0.9, 1.1), rng.uniform(0.85, 1.15)])


def draw_needles(L, rng, n, h0, age_range, fascicle_p=0.35, len_cm=(12, 22), width_px=1.0):
    for i in range(n):
        x, y = rng.uniform(0, S, 2)
        ang = rng.uniform(0, 2 * np.pi)
        age = rng.uniform(*age_range)
        col = needle_colour(rng, age)
        ln = rng.uniform(*len_cm) / 100 * PX
        cnt = 3 if rng.random() < fascicle_p else 1
        for j in range(cnt):
            a = ang + (rng.normal(0, 0.09) if cnt > 1 else 0)
            b = rng.normal(0, 0.25)
            pts = needle_path(rng, x + rng.normal(0, 0.6), y + rng.normal(0, 0.6), ln * rng.uniform(0.92, 1.0), a, b)
            L.line(pts, width_px * rng.uniform(0.8, 1.2), col * rng.uniform(0.92, 1.05), h0 + rng.uniform(0, 0.4), 0.62)


def draw_cone(L, rng, cx, cy, h0, size_cm=None, old=False):
    """Ponderosa cone lying on its side: ovoid, rows of woody scales with prickle-tipped dark apophyses."""
    lc = (size_cm or rng.uniform(7, 11)) / 100 * PX
    wc = lc * rng.uniform(0.62, 0.75)
    ang = rng.uniform(0, 2 * np.pi)
    ca, sa = math.cos(ang), math.sin(ang)
    base = np.array([0.20, 0.10, 0.045]) if not old else np.array([0.13, 0.095, 0.07])
    # body shadow first (dark), then scales from the tip toward the base so base scales overlap
    L.ellipse(cx, cy, lc / 2, wc / 2, ang, base * 0.35, h0, 0.85)
    nrow = 9
    for r in range(nrow):
        t = (r + 0.5) / nrow                        # 0 tip … 1 base
        along = (0.5 - t) * lc * 0.92
        half = wc / 2 * math.sin(math.pi * (0.12 + 0.8 * t)) ** 0.7
        ns = max(2, int(round(half * 2 / (wc * 0.2))))
        for k in range(ns):
            off = (-half + (k + 0.5) * 2 * half / ns) * 0.95 + (r % 2) * half / ns * 0.5
            if abs(off) > half:
                continue
            px = cx + along * ca - off * sa
            py = cy + along * sa + off * ca
            sw = wc * 0.11; sl = lc * 0.075
            sh = 1 - (abs(off) / max(half, 1e-3)) ** 2          # brighter on the rounded top
            c = base * (0.55 + 0.6 * sh) * rng.uniform(0.85, 1.15)
            L.ellipse(px, py, sl, sw, ang, c, h0 + 1.6 * sh + 0.4, 0.8, n=8)
            L.ellipse(px - 0.3 * sl * ca, py - 0.3 * sl * sa, sl * 0.35, sw * 0.4, ang,
                      c * 0.55, h0 + 1.7 * sh + 0.5, 0.75, n=6)


def draw_stones(L, rng, n, rmin, rmax, h0, palette):
    for i in range(n):
        x, y = rng.uniform(0, S, 2)
        r = rmin * (rmax / rmin) ** (rng.random() ** 1.8)
        c = palette[rng.integers(len(palette))] * rng.uniform(0.75, 1.2)
        L.ellipse(x, y, r, r * rng.uniform(0.55, 0.95), rng.uniform(0, np.pi), c, h0 + r * 0.25, rng.uniform(0.62, 0.82),
                  n=max(6, int(r * 2)))


def finish(name, base_col, base_h, base_rough, layers, normal_strength):
    col = base_col.copy(); h = base_h.copy(); rough = base_rough.copy()
    for L, shade in layers:
        c, lh, lr, cov = L.arrays()
        # soft contact shadow under each layer (ambient occlusion from the layer's height)
        occl = ndimage.gaussian_filter(cov, 2.0, mode='wrap')
        col *= (1 - shade * occl)[..., None]
        col = col * (1 - cov[..., None]) + c * cov[..., None]
        h = h * (1 - cov) + np.maximum(lh, h) * cov
        rough = rough * (1 - cov) + lr * cov
    # cavity from height (low = darker)
    hb = ndimage.gaussian_filter(h, 6, mode='wrap')
    cav = np.clip((h - hb), -2, 2)
    col *= (1 + 0.10 * np.tanh(cav))[..., None]
    nmap = height_to_normal(ndimage.gaussian_filter(h, 0.7, mode='wrap'), normal_strength)
    save(np.clip(col, 0.02, 0.9), f'{name}_albedo.jpg')
    save(nmap, f'{name}_normal.jpg', to_srgb=False)
    save(np.clip(rough, 0.3, 1.0), f'{name}_rough.jpg', to_srgb=False)


def lot(seed=21):
    rng = np.random.default_rng(seed)
    big = tile_noise(S, S, beta=3.4, seed=seed)
    mid = tile_noise(S, S, beta=2.4, seed=seed + 1)
    fine = tile_noise(S, S, beta=1.2, seed=seed + 2)
    # tyre-packed patches: smoother, darker, fewer loose stones, faint tread prints along v
    packed = smoothstep(0.1, 0.9, tile_noise(S, S, beta=3.6, ax=2.2, ay=0.6, seed=seed + 3))
    yy, xx = np.meshgrid(np.arange(S), np.arange(S), indexing='ij')
    tread = 0.5 + 0.5 * np.sin(yy / (0.028 * PX) * 2 * np.pi + 2.0 * tile_noise(S, S, beta=3, seed=seed + 4))
    tread = smoothstep(0.55, 0.95, tread) * packed * smoothstep(-0.2, 0.6, tile_noise(S, S, beta=3, seed=seed + 5))
    dirt = np.array([0.215, 0.158, 0.108])            # decomposed granite dirt, warm grey-brown
    dark = np.array([0.150, 0.110, 0.076])
    col = dirt[None, None] * (1 + 0.10 * big[..., None] + 0.06 * mid[..., None] + 0.05 * fine[..., None])
    col = col * (1 - packed[..., None] * 0.35) + dark * packed[..., None] * 0.35
    col *= (1 - 0.05 * tread)[..., None]
    # grit: sand-sized mineral grains (quartz bright, biotite dark) as per-pixel speckle
    g = rng.random((S, S))
    col *= np.where(g > 0.985, 1.35, np.where(g < 0.02, 0.6, 1.0))[..., None]
    h = 0.8 * big + 0.5 * mid + 0.35 * fine - 0.6 * packed - 0.35 * tread
    h = h * (1 - 0.5 * packed)
    rough = 0.93 - 0.08 * packed + 0.02 * fine
    # stones (loose gravel sits mostly off the packed patches)
    pal = [np.array(c) for c in ([0.30, 0.28, 0.26], [0.36, 0.30, 0.25], [0.20, 0.18, 0.17], [0.42, 0.39, 0.35],
                                 [0.26, 0.17, 0.11], [0.12, 0.11, 0.10])]
    st = Layer()
    draw_stones(st, rng, 26000, 1.2, 4.5, 2.0, pal)        # 2–9 mm grit
    draw_stones(st, rng, 1800, 4.5, 10.0, 3.0, pal)        # 9–20 mm gravel
    draw_stones(st, rng, 60, 10, 18, 4.0, pal)             # a few pebbles
    c, sh, sr, cov = st.arrays()
    cov *= (1 - 0.75 * packed) * (0.6 + 0.4 * smoothstep(-1, 1, mid))
    # pressed-in stones on the packed patches: flush, duller
    st2 = (c, sh * (1 - 0.6 * packed), sr, cov)
    nd = Layer()
    draw_needles(nd, rng, 170, 5.0, (0.0, 1.0), fascicle_p=0.4)
    cones = Layer()
    for k in range(3):
        draw_cone(cones, rng, *rng.uniform(0, S, 2), 6.0, old=k == 2)
    # a few small twig bits
    for k in range(10):
        x, y = rng.uniform(0, S, 2)
        nd.line(needle_path(rng, x, y, rng.uniform(0.04, 0.12) * PX, rng.uniform(0, 6.3), rng.normal(0, 0.4)),
                rng.uniform(2, 4), np.array([0.13, 0.09, 0.06]) * rng.uniform(0.8, 1.2), 5.5, 0.85)

    class Pre:  # wrap precomputed arrays
        def __init__(s, a): s.a = a
        def arrays(s): return s.a
    finish('lot', col, h, rough, [(Pre(st2), 0.35), (nd, 0.35), (cones, 0.6)], normal_strength=3.0)


def forest(seed=31):
    rng = np.random.default_rng(seed)
    big = tile_noise(S, S, beta=3.4, seed=seed)
    mid = tile_noise(S, S, beta=2.2, seed=seed + 1)
    fine = tile_noise(S, S, beta=1.2, seed=seed + 2)
    humus = np.array([0.075, 0.055, 0.040])
    col = humus[None, None] * (1 + 0.15 * big[..., None] + 0.1 * fine[..., None])
    h = 0.6 * big + 0.4 * mid + 0.3 * fine
    rough = 0.9 + 0.03 * fine
    layers = []
    # deep old duff (grey-brown, broken), then progressively fresher layers on top
    L1 = Layer(); draw_needles(L1, rng, 5200, 1.0, (0.65, 1.0), fascicle_p=0.15, len_cm=(5, 18))
    layers.append((L1, 0.25))
    # bark flakes (ponderosa jigsaw scales) and small twigs
    L2 = Layer()
    for k in range(70):
        x, y = rng.uniform(0, S, 2); r = rng.uniform(0.6, 2.2) / 100 * PX
        npt = 7
        t = np.sort(rng.uniform(0, 2 * np.pi, npt))
        rr = r * rng.uniform(0.6, 1.2, npt)
        c = np.array([0.30, 0.15, 0.07]) * rng.uniform(0.6, 1.2)
        L2.poly(list(zip(x + rr * np.cos(t), y + rr * np.sin(t) * 0.7)), c, 2.5, 0.85)
    for k in range(18):
        x, y = rng.uniform(0, S, 2)
        L2.line(needle_path(rng, x, y, rng.uniform(0.08, 0.3) * PX, rng.uniform(0, 6.3), rng.normal(0, 0.5)),
                rng.uniform(3, 6), np.array([0.11, 0.08, 0.06]) * rng.uniform(0.8, 1.3), 3.5, 0.85)
    draw_needles(L2, rng, 2600, 2.0, (0.35, 0.85), fascicle_p=0.3, len_cm=(10, 21))
    layers.append((L2, 0.3))
    L3 = Layer(); draw_needles(L3, rng, 1300, 3.5, (0.0, 0.45), fascicle_p=0.45, len_cm=(13, 23))
    for k in range(4):
        draw_cone(L3, rng, *rng.uniform(0, S, 2), 4.5, old=k >= 2)
    layers.append((L3, 0.35))
    finish('forest', col, h, rough, layers, normal_strength=2.6)


if __name__ == '__main__':
    for k in (sys.argv[1:] or ['lot', 'forest']):
        {'lot': lot, 'forest': forest}[k]()
