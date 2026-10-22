"""Desert shrubs: creosote bush (Larrea tridentata) ×2 and white bursage (Ambrosia dumosa) ×1.

Creosote: an open vase of many thin, dark grey, slightly zig-zag stems rising from a root crown, forking a few
times; small olive/yellow-green leaf clusters (paired leaflets) toward the tips — alpha-tested cards.
Bursage: low dense hemispherical mound of fine pale grey stems with tiny grey-green leaves — cards on a mound.
Materials: bark (stems, vertex-coloured), leaf (alphaTest cards, double-sided). ≤ 8k tris each.
"""
import sys, os, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import nrm, rodrigues, perp, smoothstep, Part, bpy_reset, build_object, make_material, export_glb, \
    glb_info, voxel_ao, save_img, TEXCACHE, ASSETS

UP = np.array([0, 0, 1.0])

SHRUBS = {
    'creosote_a': dict(kind='creosote', seed=3, height=1.6, spread=1.0, stems=26, budget=7800),
    'creosote_b': dict(kind='creosote', seed=8, height=1.15, spread=0.8, stems=20, budget=7800),
    'bursage_a': dict(kind='bursage', seed=5, height=0.42, spread=0.42, stems=70, budget=7800),
}


# ------------------------------------------------------------------------------------------------ textures
def leaf_card_texture(kind, size=512, seed=1):
    """RGBA card: a sprig with many small leaves. Colour is a multiplier (vertex colour sets the hue)."""
    from PIL import Image, ImageDraw
    rng = np.random.default_rng(seed)
    S = size * 2
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    def leaflet(cx, cy, ang, L, W, shade):
        c, s = math.cos(ang), math.sin(ang)
        pts = []
        for t in np.linspace(0, 1, 9):
            w = W * math.sin(math.pi * t) ** 0.8
            pts.append((t * L, w))
        pts += [(t, -w) for t, w in reversed(pts)]
        pts = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]
        g = int(np.clip(shade, 0, 1) * 255)
        dr.polygon(pts, fill=(g, g, g, 255))
    if kind == 'creosote':
        # 3 twigs with zig-zag nodes; at each node a pair of fused leaflets (creosote leaves are bifoliate)
        for twig in range(6):
            x, y = S * (0.5 + rng.normal(0, 0.05)), S * 0.99
            ang = -math.pi / 2 + (twig - 2.5) * 0.17 + rng.normal(0, 0.08)
            pts = [(x, y)]
            for node in range(12):
                seg = S * 0.075 * (1 - node * 0.035)
                ang += (0.25 if node % 2 else -0.25) + rng.normal(0, 0.08)
                x += math.cos(ang) * seg; y += math.sin(ang) * seg
                pts.append((x, y))
                for side in (-1, 1):
                    la = ang + side * rng.uniform(0.7, 1.1)
                    L = S * rng.uniform(0.04, 0.06) * (0.6 + 0.4 * (node / 12))
                    shade = rng.uniform(0.62, 0.95)
                    leaflet(x, y, la, L, L * 0.33, shade)
                    leaflet(x, y, la + side * 0.35, L * 0.9, L * 0.30, shade * 0.9)
            dr.line(pts, fill=(70, 66, 60, 255), width=max(2, S // 220))
    else:
        # bursage: dense, tiny, lobed grey leaves on fine stems
        for twig in range(7):
            x, y = S * (0.5 + rng.normal(0, 0.15)), S * 0.98
            ang = -math.pi / 2 + rng.normal(0, 0.45)
            pts = [(x, y)]
            for node in range(12):
                seg = S * 0.06
                ang += rng.normal(0, 0.18)
                x += math.cos(ang) * seg; y += math.sin(ang) * seg
                pts.append((x, y))
                for side in (-1, 1):
                    if rng.random() < 0.8:
                        la = ang + side * rng.uniform(0.6, 1.3)
                        L = S * rng.uniform(0.025, 0.045)
                        leaflet(x, y, la, L, L * 0.45, rng.uniform(0.7, 1.0))
            dr.line(pts, fill=(150, 145, 135, 255), width=max(2, S // 300))
    img = img.resize((size, size), Image.LANCZOS)
    a = np.asarray(img).astype(np.float64) / 255
    # bleed colour into transparent texels (avoid dark fringes with mipmapping)
    from scipy import ndimage
    m = a[..., 3] > 0.05
    col = a[..., :3].copy()
    if m.any():
        idx = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
        col = col[idx[0], idx[1]]
    out = np.concatenate([col, a[..., 3:4]], -1)
    # colour channel is a multiplier → keep linear (save with sRGB transform for consistency)
    return save_img(out, f'{kind}_card.png')


# ------------------------------------------------------------------------------------------------ geometry
def stem_tube(part, pts, r0, r1, sides, col):
    T = nrm(np.gradient(pts, axis=0))
    N = np.zeros_like(T); N[0] = perp(T[:1])[0]
    for i in range(1, len(T)):
        v = N[i - 1] - T[i] * np.dot(N[i - 1], T[i]); N[i] = v / (np.linalg.norm(v) + 1e-12)
    B = np.cross(T, N)
    r = np.linspace(r0, r1, len(pts))
    a = np.linspace(0, 2 * math.pi, sides, endpoint=False)
    nor = np.cos(a)[None, :, None] * N[:, None] + np.sin(a)[None, :, None] * B[:, None]
    pos = pts[:, None] + nor * r[:, None, None]
    W = sides
    i = np.arange(len(pts) - 1)[:, None] * W + np.arange(W)[None]
    j = np.arange(len(pts) - 1)[:, None] * W + (np.arange(W)[None] + 1) % W
    tris = np.concatenate([np.stack([i, j, i + W], -1).reshape(-1, 3), np.stack([j, j + W, i + W], -1).reshape(-1, 3)])
    uv = np.c_[np.tile(np.linspace(0, 1, W), len(pts)), np.repeat(np.linspace(0, 4, len(pts)), W)]
    part.add(pos.reshape(-1, 3), tris, n=nor.reshape(-1, 3), c=np.c_[np.tile(col, (len(pos) * W, 1)), np.ones(len(pos) * W)],
             uv=uv)


def card(part, center, normal, up, w, h, col, base_at_bottom=True):
    """Single quad (2 tris), alpha card. up is the twig direction."""
    up = nrm(up - normal * np.dot(up, normal))
    rt = np.cross(up, normal)
    o = center - up * (h * 0.5 if not base_at_bottom else 0)
    v = np.array([o - rt * w / 2, o + rt * w / 2, o + rt * w / 2 + up * h, o - rt * w / 2 + up * h])
    uv = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], float)
    part.add(v, [[0, 1, 2], [0, 2, 3]], n=np.tile(normal, (4, 1)), c=np.c_[np.tile(col, (4, 1)), np.ones(4)], uv=uv)


def creosote(S, rng):
    stems, leaves = Part(), Part()
    tips = []
    H, R = S['height'], S['spread']
    n = S['stems']
    for k in range(n):
        az = rng.uniform(0, 2 * math.pi)
        lean = rng.uniform(0.15, 0.55)          # vase: stems lean outward
        d = nrm(np.array([math.cos(az) * lean, math.sin(az) * lean, 1.0]))
        p = np.array([rng.normal(0, 0.05), rng.normal(0, 0.05), -0.02])
        L = H * rng.uniform(0.6, 1.0)
        def grow(p, d, L, r, depth):
            pts = [p.copy()]
            segs = max(3, int(L / 0.14))
            for i in range(segs):
                d = nrm(d + rng.normal(0, 0.12, 3) + np.array([0, 0, 0.05]))
                p = p + d * (L / segs)
                pts.append(p.copy())
            pts = np.array(pts)
            col = np.array([0.16, 0.15, 0.135]) * rng.uniform(0.8, 1.2)
            stem_tube(stems, pts, r, r * 0.5, 4 if depth == 0 else 3, col) if depth < 2 else stem_tube(stems, pts[::2], r, r * 0.5, 3, col)
            # forks
            if depth < 2:
                for j in range(rng.integers(1, 3)):
                    t = rng.uniform(0.45, 0.85)
                    q = pts[int(t * (len(pts) - 1))]
                    cd = nrm(d + perp(d[None])[0] * rng.normal(0, 0.6) + np.cross(d, perp(d[None])[0]) * rng.normal(0, 0.6))
                    grow(q, cd, L * rng.uniform(0.35, 0.55), r * 0.55, depth + 1)
            tips.append((pts, depth))
        grow(p, d, L, rng.uniform(0.008, 0.014), 0)
    return stems, leaves, tips


def foliage_creosote(S, rng, leaves, tips, budget_cards):
    # leaf cards along the outer ~45% of each stem, biased to tips
    cand = []
    for pts, depth in tips:
        m = len(pts)
        for i in range(int(m * 0.55), m):
            cand.append((pts[i], pts[min(i + 1, m - 1)] - pts[max(i - 1, 0)], i / m))
    rng.shuffle(cand)
    w = np.array([c[2] ** 2 for c in cand]); w /= w.sum()
    pick = rng.choice(len(cand), size=min(budget_cards, len(cand) * 3), p=w)
    for i in pick:
        p, t, f = cand[i]
        t = nrm(t)
        nrmv = nrm(perp(t[None])[0] * 1.0 + np.cross(t, perp(t[None])[0]) * rng.normal(0, 1.2) + rng.normal(0, 0.4, 3))
        up = nrm(t + rng.normal(0, 0.5, 3) + np.array([0, 0, 0.4]))
        sz = rng.uniform(0.10, 0.18) * (S['height'] / 1.5) ** 0.5
        hue = rng.random()
        col = np.array([0.17, 0.18, 0.06]) * (1 - hue) + np.array([0.25, 0.24, 0.07]) * hue
        col *= rng.uniform(0.85, 1.15)
        card(leaves, p + rng.normal(0, 0.03, 3), nrmv, up, sz, sz, col)


def bursage(S, rng):
    stems, leaves = Part(), Part()
    H, R = S['height'], S['spread']
    tips = []
    for k in range(S['stems']):
        az = rng.uniform(0, 2 * math.pi); el = rng.uniform(0.2, 1.4)
        d = nrm(np.array([math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el) + 0.3]))
        pts = [np.array([0, 0, 0.0])]
        p = pts[0].copy()
        L = rng.uniform(0.6, 1.0) * math.hypot(R, H)
        for i in range(5):
            d = nrm(d + rng.normal(0, 0.18, 3))
            p = p + d * L / 5
            rad = math.hypot(p[0], p[1])
            if rad > R * 0.98:
                p[:2] *= R * 0.98 / rad
            p[2] = max(p[2], 0.0)
            p[2] = min(p[2], H * math.sqrt(max(0.0, 1 - (p[0] ** 2 + p[1] ** 2) / R ** 2)) + 0.02)
            pts.append(p.copy())
        pts = np.array(pts)
        stem_tube(stems, pts, 0.005, 0.0025, 3, np.array([0.42, 0.40, 0.36]))
        tips.append(pts)
    return stems, leaves, tips


def foliage_bursage(S, rng, leaves, n_cards):
    H, R = S['height'], S['spread']
    for k in range(n_cards):
        # points over a squashed hemisphere shell (outer 30%)
        az = rng.uniform(0, 2 * math.pi); u = rng.random() ** 0.6
        el = math.asin(u)
        rr = rng.uniform(0.55, 0.92)
        p = np.array([R * rr * math.cos(el) * math.cos(az), R * rr * math.cos(el) * math.sin(az), H * rr * math.sin(el)])
        out = nrm(np.array([p[0] / R ** 2, p[1] / R ** 2, p[2] / H ** 2]))
        nv = nrm(out + rng.normal(0, 0.7, 3))
        up = nrm(out + np.array([0, 0, 0.6]) + rng.normal(0, 0.4, 3))
        sz = rng.uniform(0.09, 0.15)
        col = np.array([0.33, 0.33, 0.27]) * rng.uniform(0.85, 1.12)
        card(leaves, p - up * sz * 0.4, nv, up, sz, sz, col)


def bake_ao(parts, cell=0.05):
    pts, w = [], []
    for k, part in parts.items():
        a = part.arrays()
        if a is None: continue
        pts.append(a[0]); w.append(np.full(len(a[0]), 0.35 if k == 'leaf' else 0.5))
    P = np.concatenate(pts); W = np.concatenate(w)
    for k, part in parts.items():
        a = part.arrays()
        if a is None: continue
        v, t, n, c, uv = a
        vis = voxel_ao(v, P, W, cell=cell, sigma=1.0, steps=30)
        c = c.copy(); c[:, :3] *= (0.35 + 0.65 * vis)[:, None]
        part.v, part.t, part.n, part.c, part.uv = [v], [t], [n], [c], [uv]; part.count = len(v)


def build(name):
    S = SHRUBS[name]
    rng = np.random.default_rng(S['seed'])
    if S['kind'] == 'creosote':
        stems, leaves, tips = creosote(S, rng)
        n_cards = min((S['budget'] - stems.ntris) // 2, int(S['stems'] * 34))
        foliage_creosote(S, rng, leaves, tips, n_cards)
    else:
        stems, leaves, tips = bursage(S, rng)
        n_cards = min((S['budget'] - stems.ntris) // 2, 1400)
        foliage_bursage(S, rng, leaves, n_cards)
    parts = {'bark': stems, 'leaf': leaves}
    bake_ao(parts, cell=0.04 if S['kind'] == 'bursage' else 0.06)
    tex = leaf_card_texture(S['kind'], seed=S['seed'])
    bpy_reset()
    mats = {'bark': make_material('bark', rough=0.9),
            'leaf': make_material('leaf', base=tex, rough=0.65, double=True, alpha_clip=0.5)}
    build_object(name, parts, mats)
    path = os.path.join(ASSETS, name + '.glb')
    export_glb(path, image_format='AUTO')
    fix_alpha_mode(path, 'leaf', 0.5)
    info = glb_info(path)
    print(f'{name}: tris={info["tris"]} ({stems.ntris} stem) {info["bytes"]/1e6:.2f}MB', flush=True)


def fix_alpha_mode(path, matname, cutoff):
    """Ensure the material is alphaMode MASK with alphaCutoff (patch the GLB JSON chunk in place)."""
    import json, struct
    d = bytearray(open(path, 'rb').read())
    l = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + l])
    for m in j.get('materials', []):
        if m['name'] == matname:
            m['alphaMode'] = 'MASK'; m['alphaCutoff'] = cutoff; m['doubleSided'] = True
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    rest = d[20 + l:]
    out = bytearray(d[:12]) + struct.pack('<I', len(js)) + d[16:20] + js + rest
    out[8:12] = struct.pack('<I', len(out))
    open(path, 'wb').write(out)


if __name__ == '__main__':
    for k in (sys.argv[1:] or list(SHRUBS)):
        build(k)
