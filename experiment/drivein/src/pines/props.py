"""Small scatter props for the lot near the camera:

pinecone.glb     : a ponderosa cone lying on its side, ~9.5 cm long, open scales, ≤ 500 tris. Material `bark`
                   (512 px albedo + normal: phyllotactic scale pattern, dark prickled umbo on each scale).
needle_clump.glb : a few fallen-needle cards lying flat on the dirt (fresh rust-orange to grey-brown 3-needle
                   fascicles), ≤ 300 tris, material `needles` (alpha MASK, double-sided).
Origins on the ground; +Y up in the GLB.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw
from common import nrm, smoothstep, srgb, Part, bpy_reset, build_object, make_material, export_glb, glb_info, \
    save_img, height_to_normal, TEXCACHE, ASSETS
from pines import fix_alpha_mode

GOLD = (math.sqrt(5) - 1) / 2


def cone_texture(size=512, nscale=110):
    """u around (0..1, wraps), v along (0 = stalk end, 1 = tip). Scale centres on a phyllotactic spiral."""
    k = np.arange(nscale)
    vs = (k + 0.5) / nscale
    us = (k * GOLD) % 1.0
    aspect = 2.2                                  # cone length / circumference ratio in metric terms
    pts = np.stack([us, vs * aspect], -1)
    pts = np.concatenate([pts + [o, 0] for o in (-1, 0, 1)])
    tree = cKDTree(pts)
    yy, xx = np.meshgrid((np.arange(size) + 0.5) / size, (np.arange(size) + 0.5) / size, indexing='ij')
    v = 1 - yy                                    # row 0 = top = v 1
    q = np.stack([xx.ravel(), v.ravel() * aspect], -1)
    d, i = tree.query(q, k=2)
    f1 = d[:, 0].reshape(size, size); f2 = d[:, 1].reshape(size, size)
    idx = (i[:, 0] % nscale).reshape(size, size)
    cen = pts[i[:, 0]].reshape(size, size, 2)
    # each scale is a woody plate whose exposed end (apophysis) faces outward; the umbo (prickle) at its centre
    edge = smoothstep(0.0, 0.035, f2 - f1)
    rel = (v * aspect - cen[..., 1])              # + toward tip
    dome = edge * (1 - smoothstep(0.0, 0.07, f1)) ** 0.6
    hgt = dome + 0.25 * edge * smoothstep(0.03, -0.04, rel)
    umbo = 1 - smoothstep(0.004, 0.012, f1)
    rnd = np.random.default_rng(3).random(nscale)[idx]
    base = np.array([0.20, 0.105, 0.05]) * (0.8 + 0.4 * rnd[..., None])
    col = base * (0.25 + 0.75 * edge[..., None]) * (0.75 + 0.35 * dome[..., None])
    col = col * (1 - 0.7 * umbo[..., None]) + np.array([0.06, 0.04, 0.03]) * 0.7 * umbo[..., None]
    # the stalk end is greyer and weathered, the tip scales smaller and darker
    col *= (0.85 + 0.15 * smoothstep(0.0, 0.3, v))[..., None]
    a = save_img(np.clip(col, 0.02, 0.9), 'cone_albedo.jpg')
    n = save_img(height_to_normal(ndimage.gaussian_filter(hgt + 0.6 * umbo, 0.7) * 6), 'cone_normal.jpg',
                 linear_to_srgb=False)
    return a, n


def pinecone():
    L = 0.095; R = 0.033
    nu, nv = 16, 15
    part = Part()
    u = np.linspace(0, 1, nu + 1)
    v = np.linspace(0, 1, nv + 1)
    U, V = np.meshgrid(u, v)
    # ovoid profile, widest ~40% from the stalk, open scales give a lumpy outline
    prof = np.sin(np.pi * np.clip(V * 0.97 + 0.02, 0, 1)) ** 0.75 * (1 - 0.25 * V)
    bump = 1 + 0.10 * np.cos(2 * np.pi * (8 * U + 5 * V * 2.2))
    r = R * prof * bump + 0.002
    th = U * 2 * np.pi
    x = (V - 0.45) * L
    P = np.stack([x, r * np.cos(th), r * np.sin(th)], -1)          # axis along X, Blender Z up
    # lying on its side, slightly tilted; lift so the lowest point touches z = 0
    tilt = math.radians(8)
    ct, st = math.cos(tilt), math.sin(tilt)
    P = P @ np.array([[ct, 0, st], [0, 1, 0], [-st, 0, ct]]).T
    P[..., 2] -= P[..., 2].min() + 0.003
    W = nu + 1
    tris = []
    for j in range(nv):
        for i in range(nu):
            a = j * W + i; b = a + 1; c = a + W; d = c + 1
            tris += [[a, b, d], [a, d, c]]
    part.add(P.reshape(-1, 3), tris, uv=np.stack([U.ravel(), V.ravel()], -1),
             c=np.c_[np.tile([1, 1, 1], (W * (nv + 1), 1)), np.ones(W * (nv + 1))])
    # stalk stub
    print('pinecone tris', part.ntris)
    a, n = cone_texture()
    bpy_reset()
    mat = make_material('bark', base=a, normal=n, rough=0.85, vcol=False)
    build_object('pinecone', {'bark': part}, {'bark': mat})
    path = os.path.join(ASSETS, 'pinecone.glb')
    export_glb(path)
    print(glb_info(path))


def fallen_atlas(size=512, seed=4):
    rng = np.random.default_rng(seed)
    S = size * 2
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for cell in range(4):
        ox, oy = (cell % 2) * S / 2, (cell // 2) * S / 2
        for k in range(rng.integers(9, 15)):
            cx, cy = ox + rng.uniform(0.15, 0.85) * S / 2, oy + rng.uniform(0.15, 0.85) * S / 2
            ang = rng.uniform(0, 2 * np.pi)
            ln = rng.uniform(0.28, 0.42) * S / 2           # cell = 0.5 m → 14-21 cm needles
            age = rng.random()
            c = np.array([0.36, 0.15, 0.045]) * (1 - age) + np.array([0.17, 0.12, 0.085]) * age
            for j in range(3 if rng.random() < 0.6 else 1):
                a = ang + rng.normal(0, 0.06)
                bend = rng.normal(0, 0.25)
                t = np.linspace(0, 1, 6)
                aa = a + bend * t
                x = cx + np.concatenate([[0], np.cumsum(np.cos(aa[:-1]))]) * ln / 5 - math.cos(a) * ln / 2
                y = cy + np.concatenate([[0], np.cumsum(np.sin(aa[:-1]))]) * ln / 5 - math.sin(a) * ln / 2
                x = np.clip(x, ox + 2, ox + S / 2 - 2); y = np.clip(y, oy + 2, oy + S / 2 - 2)
                cc = srgb(np.clip(c * rng.uniform(0.85, 1.1), 0, 1))
                dr.line(list(zip(x, y)), fill=tuple(int(q * 255) for q in cc) + (255,), width=3, joint='curve')
            # dark papery sheath at the fascicle base
            dr.ellipse([x[0] - 3, y[0] - 3, x[0] + 3, y[0] + 3], fill=(40, 28, 20, 255))
    img = img.resize((size, size), Image.LANCZOS)
    a = np.asarray(img).astype(np.float64) / 255
    alpha = np.clip(a[..., 3] * 1.5, 0, 1)
    m = alpha > 0.05
    idx = ndimage.distance_transform_edt(~m, return_distances=False, return_indices=True)
    col = a[..., :3][idx[0], idx[1]]
    path = os.path.join(TEXCACHE, 'needles_fallen.png')
    Image.fromarray((np.c_[col.reshape(-1, 3), alpha.reshape(-1, 1)].reshape(size, size, 4) * 255 + 0.5)
                    .astype(np.uint8)).save(path, optimize=True)
    return path


def needle_clump(ncards=48, seed=9):
    rng = np.random.default_rng(seed)
    part = Part()
    for k in range(ncards):
        rr = 0.35 * math.sqrt(rng.random()); a = rng.uniform(0, 2 * np.pi)
        c = np.array([rr * math.cos(a), rr * math.sin(a), 0.0])
        s = rng.uniform(0.18, 0.30)
        rot = rng.uniform(0, 2 * np.pi)
        ex = np.array([math.cos(rot), math.sin(rot), 0]) * s / 2
        ey = np.array([-math.sin(rot), math.cos(rot), 0]) * s / 2
        # slight tilt so the needles lie on each other, a few mm off the ground
        tilt = rng.normal(0, 0.06, 2)
        z0 = 0.003 + 0.004 * k / ncards
        v = np.array([c - ex - ey, c + ex - ey, c + ex + ey, c - ex + ey])
        v[:, 2] = z0 + (v[:, 0] - c[0]) * tilt[0] + (v[:, 1] - c[1]) * tilt[1]
        v[:, 2] = np.maximum(v[:, 2], 0.001)
        cell = rng.integers(4)
        cu, cv = (cell % 2) * 0.5, 1 - (cell // 2 + 1) * 0.5
        uv = np.array([[cu, cv], [cu + 0.5, cv], [cu + 0.5, cv + 0.5], [cu, cv + 0.5]])
        shade = rng.uniform(0.75, 1.0)
        part.add(v, [[0, 1, 2], [0, 2, 3]], n=np.tile([0, 0, 1.0], (4, 1)), uv=uv,
                 c=np.c_[np.full((4, 3), shade), np.ones(4)])
    tex = fallen_atlas()
    bpy_reset()
    mat = make_material('needles', base=tex, rough=0.6, double=True, alpha_clip=0.4)
    build_object('needle_clump', {'needles': part}, {'needles': mat})
    path = os.path.join(ASSETS, 'needle_clump.glb')
    export_glb(path, image_format='AUTO')
    fix_alpha_mode(path, 'needles', 0.4)
    print(glb_info(path))


if __name__ == '__main__':
    pinecone(); needle_clump()
