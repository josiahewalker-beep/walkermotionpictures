"""Shared helpers for the FLORA generators (Joshua trees, shrubs, rocks).

Everything is built in numpy, then pushed into Blender (bpy as a Python module) in one go and exported as GLB.
Blender coordinates are Z-up; the glTF exporter converts to +Y up. Units: metres.
"""
import os, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DESERT = os.path.abspath(os.path.join(HERE, '..', '..'))
ASSETS = os.path.join(DESERT, 'assets')
TEXCACHE = os.path.join(HERE, '_tex')          # generated texture images (rebuildable)
os.makedirs(TEXCACHE, exist_ok=True)


# ----------------------------------------------------------------------------------------------------------- maths
def nrm(v, axis=-1):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def rodrigues(v, k, ang):
    """Rotate vectors v (N,3) about unit axes k (N,3) by angles ang (N,)."""
    ang = np.asarray(ang)[..., None]
    c, s = np.cos(ang), np.sin(ang)
    return v * c + np.cross(k, v) * s + k * (np.sum(k * v, -1, keepdims=True)) * (1 - c)


def perp(d):
    """Some unit vector perpendicular to each d (N,3)."""
    d = np.atleast_2d(d)
    a = np.where(np.abs(d[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
    return nrm(np.cross(d, a))


def srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ----------------------------------------------------------------------------------------------------------- noise
def tile_noise(h, w, beta=2.0, ax=1.0, ay=1.0, seed=0, fmin=1.0):
    """Tileable fractal noise via FFT filtering. ax/ay > 1 squash frequency along that axis
    (ay > 1 → features elongated along x...). Returns zero-mean, unit-std float32 (h, w)."""
    rng = np.random.default_rng(seed)
    wn = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h) * h
    fx = np.fft.fftfreq(w) * w
    FX, FY = np.meshgrid(fx, fy)
    f = np.sqrt((FX * ax) ** 2 + (FY * ay) ** 2)
    f[0, 0] = 1
    filt = 1.0 / np.maximum(f, fmin) ** (beta / 2)
    filt[0, 0] = 0
    out = np.real(np.fft.ifft2(np.fft.fft2(wn) * filt))
    out = (out - out.mean()) / (out.std() + 1e-9)
    return out.astype(np.float32)


def height_to_normal(hgt, strength=1.0):
    """Tileable tangent-space normal map (OpenGL convention, +Y up in texture = +V) from a height field."""
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5 * strength
    dy = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5 * strength
    # image row 0 is the top (v=1) when saved; PIL rows go down, so +v is -row
    n = np.stack([-dx, dy, np.ones_like(hgt)], -1)
    n = nrm(n)
    return (n * 0.5 + 0.5).astype(np.float32)


def save_img(arr, name, quality=92, linear_to_srgb=True):
    """arr float (h,w,3|4) in [0,1]; row 0 = top of image (v = 1)."""
    from PIL import Image
    a = np.asarray(arr, dtype=np.float64)
    if linear_to_srgb:
        a = a.copy()
        a[..., :3] = srgb(a[..., :3])
    a8 = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    path = os.path.join(TEXCACHE, name)
    if path.endswith('.png'):
        Image.fromarray(a8).save(path, optimize=True)
    else:
        Image.fromarray(a8[..., :3]).save(path, quality=quality, subsampling=0)
    return path


# ----------------------------------------------------------------------------------------------------------- mesh
class Part:
    """Accumulates triangles for one material."""

    def __init__(self):
        self.v, self.n, self.c, self.uv, self.t = [], [], [], [], []
        self.count = 0

    def add(self, v, t, n=None, c=None, uv=None):
        v = np.asarray(v, np.float64).reshape(-1, 3)
        t = np.asarray(t, np.int64).reshape(-1, 3)
        k = len(v)
        self.v.append(v)
        self.t.append(t + self.count)
        self.n.append(np.zeros((k, 3)) if n is None else np.asarray(n, np.float64).reshape(-1, 3))
        cc = np.ones((k, 4))
        if c is not None:
            c = np.asarray(c, np.float64).reshape(k, -1)
            cc[:, :c.shape[1]] = c
        self.c.append(cc)
        self.uv.append(np.zeros((k, 2)) if uv is None else np.asarray(uv, np.float64).reshape(-1, 2))
        self.count += k

    def arrays(self):
        if not self.v:
            return None
        return (np.concatenate(self.v), np.concatenate(self.t), np.concatenate(self.n),
                np.concatenate(self.c), np.concatenate(self.uv))

    @property
    def ntris(self):
        return sum(len(t) for t in self.t)


def bpy_reset():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy


def build_object(name, parts, materials):
    """parts: dict matname -> Part ; materials: dict matname -> bpy material. Returns bpy object.
    Normals: if a part's normals are all zero, Blender computes smooth ones; else custom normals are used."""
    import bpy
    V, T, N, C, UV, M = [], [], [], [], [], []
    off = 0
    names = [k for k in parts if parts[k].arrays() is not None]
    for mi, k in enumerate(names):
        v, t, n, c, uv = parts[k].arrays()
        V.append(v); T.append(t + off); N.append(n); C.append(c); UV.append(uv)
        M.append(np.full(len(t), mi))
        off += len(v)
    V = np.concatenate(V); T = np.concatenate(T); N = np.concatenate(N); C = np.concatenate(C)
    UV = np.concatenate(UV); M = np.concatenate(M)
    C[:, 3] = 1.0          # three.js multiplies vertex alpha into the fragment alpha: keep it opaque
    # fill missing normals from face normals (area-weighted)
    zero = np.linalg.norm(N, axis=1) < 1e-9
    if zero.any():
        fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
        acc = np.zeros_like(V)
        for j in range(3):
            np.add.at(acc, T[:, j], fn)
        N[zero] = acc[zero]
    N = nrm(N)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(len(T) * 3)
    me.loops.foreach_set('vertex_index', T.astype(np.int32).ravel())
    me.polygons.add(len(T))
    me.polygons.foreach_set('loop_start', (np.arange(len(T)) * 3).astype(np.int32))
    me.polygons.foreach_set('material_index', M.astype(np.int32))
    me.update(calc_edges=True)
    ca = me.color_attributes.new('Color', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', C.astype(np.float32).ravel())
    uvl = me.uv_layers.new(name='UVMap')
    uvl.data.foreach_set('uv', UV[T.ravel()].astype(np.float32).ravel())
    me.shade_smooth()
    me.normals_split_custom_set_from_vertices(N.astype(np.float32).tolist())
    for k in names:
        me.materials.append(materials[k])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def load_image(path, noncolor=False):
    import bpy
    im = bpy.data.images.load(path)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    im.pack()
    return im


def make_material(name, base=None, normal=None, normal_strength=1.0, rough=0.8, double=False, vcol=True,
                  alpha_clip=None, color=(1, 1, 1), rough_tex=None):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = not double
    nt = mat.node_tree
    bs = nt.nodes['Principled BSDF']
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = 0.0
    bs.inputs['Base Color'].default_value = (*color, 1)
    col_out = None
    if base is not None:
        tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = load_image(base)
        col_out = tx.outputs['Color']
        if alpha_clip is not None:
            nt.links.new(tx.outputs['Alpha'], bs.inputs['Alpha'])
    if vcol:
        vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Color'
        if col_out is not None:
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
            mx.inputs[0].default_value = 1.0
            nt.links.new(col_out, mx.inputs[6]); nt.links.new(vc.outputs['Color'], mx.inputs[7])
            col_out = mx.outputs[2]
        else:
            col_out = vc.outputs['Color']
    if col_out is not None:
        nt.links.new(col_out, bs.inputs['Base Color'])
    if normal is not None:
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = load_image(normal, noncolor=True)
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal_strength
        nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    if alpha_clip is not None:
        try:
            mat.blend_method = 'CLIP'
        except Exception:
            pass
        try:
            mat.surface_render_method = 'DITHERED'
        except Exception:
            pass
        # exporter reads alpha cutoff from a Math(<) node chain in newer versions; fall back on custom prop
        mat['gltf_alpha_cutoff'] = alpha_clip
    return mat


def export_glb(path, image_format='JPEG'):
    import bpy
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_yup=True, export_apply=True,
                              export_image_format=image_format, export_image_quality=88,
                              export_vertex_color='MATERIAL', export_all_vertex_colors=False, export_normals=True,
                              export_tangents=False, export_materials='EXPORT')
    return path


def glb_info(path):
    import json, struct
    d = open(path, 'rb').read()
    l = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + l])
    tris = 0
    for m in j['meshes']:
        for p in m['primitives']:
            tris += j['accessors'][p['indices']]['count'] // 3
    return dict(bytes=len(d), tris=tris, materials=[m['name'] for m in j.get('materials', [])],
                nodes=[n.get('name') for n in j['nodes']])


# ----------------------------------------------------------------------------------------------------------- AO
def voxel_ao(sample_pts, occ_pts, occ_w, cell=0.08, sigma=1.0, ground=True, steps=40, lo=None, hi=None):
    """Sky-visibility estimate. occ_pts/occ_w define an occlusion density field on a voxel grid; returns
    visibility in [0,1] for each sample point (cosine-weighted over the upper hemisphere + horizon)."""
    from scipy import ndimage
    pad = 0.6
    if lo is None:
        lo = np.minimum(occ_pts.min(0), sample_pts.min(0)) - pad
        hi = np.maximum(occ_pts.max(0), sample_pts.max(0)) + pad
    shape = np.ceil((hi - lo) / cell).astype(int) + 1
    idx = np.floor((occ_pts - lo) / cell).astype(int)
    idx = np.clip(idx, 0, shape - 1)
    dens = np.zeros(shape, np.float32)
    np.add.at(dens, (idx[:, 0], idx[:, 1], idx[:, 2]), occ_w.astype(np.float32))
    dens = ndimage.gaussian_filter(dens, 1.0)
    dens *= sigma
    # directions: zenith + rings at 60, 35, 12 degrees elevation
    dirs, wts = [], []
    for elev, n in ((90, 1), (60, 6), (35, 8), (12, 10)):
        for k in range(n):
            az = 2 * math.pi * (k + 0.5 * (elev == 35)) / n
            e = math.radians(elev)
            dirs.append((math.cos(e) * math.cos(az), math.cos(e) * math.sin(az), math.sin(e)))
            wts.append(math.sin(e) * (1.0 / n) * {90: 1.0, 60: 2.2, 35: 2.6, 12: 1.6}[elev] + 0.04)
    wts = np.array(wts) / sum(wts)
    vis_grid = np.zeros(shape, np.float32)
    P = int(steps) + 2
    padded = np.pad(dens, P, mode='constant')
    for d, w in zip(dirs, wts):
        tau = np.zeros(shape, np.float32)
        for s in range(1, steps + 1):
            o = np.round(np.array(d) * s * 1.0).astype(int)
            if s > 1 and np.all(o == np.round(np.array(d) * (s - 1)).astype(int)):
                continue
            sl = tuple(slice(P + o[a], P + o[a] + shape[a]) for a in range(3))
            tau += padded[sl]
        vis_grid += w * np.exp(-tau)
    coords = ((sample_pts - lo) / cell).T
    return ndimage.map_coordinates(vis_grid, coords, order=1, mode='nearest')
