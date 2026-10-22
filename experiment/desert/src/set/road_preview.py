"""Reference composite of the road textures (and a preview GLB for the harness). Not shipped in assets/.
Shows exactly how the tiles, the macro, the line strips and the shoulder are meant to combine.
Layout (metres, x across the road, z along it): paved 10.2 m centred on x = 0; double yellow centres at ±0.11; white fog
lines at ±3.8; shoulder strips from |x| = 4.67 to 6.17 (ragged edge ≈ |x| 5.1); desert sand beyond.
Writes src/set/preview/road.glb (+ composite PNGs)."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from texlib import srgb2lin, lin2srgb, smoothstep

T = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../tex'))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview')
os.makedirs(OUT, exist_ok=True)
MPX = 0.007
WX, LZ = 14.0, 40.0
NX, NZ = int(WX / MPX), int(LZ / MPX)
xs = (np.arange(NX) + 0.5) * MPX - WX / 2
zs = (np.arange(NZ) + 0.5) * MPX


def load(name, mode='RGB'):
    return Image.open(f'{T}/{name}').convert(mode)


def tile_sample(img, tile_w_m, tile_h_m, x, z, lin=True, mode='RGB'):
    """Sample a tiling image (u across = x, v along = z) at metres; prefiltered to MPX by resizing."""
    pw, ph = max(2, int(round(tile_w_m / MPX))), max(2, int(round(tile_h_m / MPX)))
    a = np.asarray(img.resize((pw, ph), Image.LANCZOS), np.float32) / 255
    ix = (np.floor(x / tile_w_m * pw).astype(int)) % pw
    iz = (np.floor(z / tile_h_m * ph).astype(int)) % ph
    s = a[iz[:, None], ix[None, :]]
    return srgb2lin(s) if lin else s


X = xs[None, :]; Z = zs[:, None]
# --- asphalt ---
alb = tile_sample(load('asphalt_albedo.jpg'), 4, 4, xs, zs)
nrm = tile_sample(load('asphalt_normal.jpg'), 4, 4, xs, zs, lin=False)
rough = tile_sample(load('asphalt_rough.jpg', 'L'), 4, 4, xs, zs, lin=False)
mac = np.asarray(Image.open(f'{T}/asphalt_macro.png').convert('RGB'), np.float32) / 255
mu = np.clip(((xs + 5.1) / 10.2 * mac.shape[1]).astype(int), 0, mac.shape[1] - 1)
mv = (zs / 80.0 * mac.shape[0]).astype(int) % mac.shape[0]
M = mac[mv[:, None], mu[None, :]]
alb = alb * (2 * M[..., :1])
seal = M[..., 1]
alb = alb * (1 - seal[..., None]) + np.array([0.035, 0.034, 0.033]) * seal[..., None]
rough = rough * (1 - seal) + 0.42 * seal
paved = np.abs(X) < 5.1
# --- lines ---
la = np.asarray(load('lines_alpha.png', 'L'), np.float32) / 255
for cx, name, voff in ((-0.11, 'yellow', 0.0), (0.11, 'yellow', 3.1), (-3.8, 'white', 1.7), (3.8, 'white', 5.3)):
    col = srgb2lin(np.asarray(load(f'lines_{name}_albedo.png'), np.float32) / 255)
    ln = np.asarray(load('lines_normal.png'), np.float32) / 255
    sel = np.where(np.abs(xs - cx) < 0.075)[0]
    u = ((xs[sel] - cx + 0.075) / 0.15 * 256).astype(int).clip(0, 255)
    v = (((zs + voff) % 8.0) / 8.0 * 4096).astype(int) % 4096
    a = la[v[:, None], u[None, :]][..., None]
    alb[:, sel] = alb[:, sel] * (1 - a) + col[v[:, None], u[None, :]] * a
    nrm[:, sel] = nrm[:, sel] * (1 - a) + ln[v[:, None], u[None, :]] * a
    rough[:, sel] = rough[:, sel] * (1 - a[..., 0]) + 0.72 * a[..., 0]
# --- sand outside, shoulder strips over the edge ---
salb = tile_sample(load('sand_albedo.jpg'), 6, 6, xs, zs)
snrm = tile_sample(load('sand_normal.jpg'), 6, 6, xs, zs, lin=False)
srough = tile_sample(load('sand_rough.jpg', 'L'), 6, 6, xs, zs, lin=False)
smac = np.asarray(load('sand_macro.jpg'), np.float32) / 255
zi = (zs / 300 * 1024).astype(int) % 1024; xi = ((xs + 150) / 300 * 1024).astype(int) % 1024
salb = salb * 2 * smac[zi[:, None], xi[None, :]]
pv = paved[..., None]
alb = np.where(pv, alb, salb); nrm = np.where(pv, nrm, snrm); rough = np.where(paved, rough, srough)
shA = srgb2lin(np.asarray(load('shoulder_albedo.jpg'), np.float32) / 255)
shN = np.asarray(load('shoulder_normal.jpg'), np.float32) / 255
shM = np.asarray(load('shoulder_mask.png', 'L'), np.float32) / 255
for side in (-1, 1):
    sel = np.where((np.abs(xs) >= 4.67) & (np.abs(xs) < 6.17) & (np.sign(xs) == side))[0]
    u = ((np.abs(xs[sel]) - 4.67) / 1.5 * 1024).astype(int).clip(0, 1023)
    v = ((zs % 3.0) / 3.0 * 2048).astype(int) % 2048
    A = shA[v[:, None], u[None, :]]; Nn = shN[v[:, None], u[None, :]]
    if side < 0:
        Nn = Nn.copy(); Nn[..., 0] = 1 - Nn[..., 0]           # mirrored u flips the tangent x
    m = shM[v[:, None], u[None, :]]
    # blend: inside the paved mask keep the road (with its macro); in the gravel part use the shoulder texture; fade the
    # outer 0.3 m of the strip into the sand
    fade = smoothstep(1.2, 1.5, np.abs(xs[sel]) - 4.67)[None, :]
    w = (1 - m) * (1 - fade)
    ex = alb[:, sel]
    road_side = np.abs(xs[sel])[None, :] < 5.1
    base = np.where(road_side[..., None], ex, salb[:, sel])
    alb[:, sel] = np.where(m[..., None] > 0.5, np.where(road_side[..., None], ex, A), base * (1 - w[..., None]) + A * w[..., None])
    nrm[:, sel] = np.where(m[..., None] > 0.5, Nn, nrm[:, sel] * (1 - w[..., None]) + Nn * w[..., None])
    rough[:, sel] = np.where(m > 0.5, rough[:, sel], rough[:, sel] * (1 - w) + 0.92 * w)
    # paved mask also cuts the asphalt that lies beyond the ragged edge
    cut = (m < 0.5) & road_side
    alb[:, sel] = np.where(cut[..., None], A, alb[:, sel])
Image.fromarray((lin2srgb(np.clip(alb, 0, 1)) * 255 + .5).astype(np.uint8)).save(f'{OUT}/road_albedo.jpg', quality=90)
Image.fromarray((np.clip(nrm, 0, 1) * 255 + .5).astype(np.uint8)).save(f'{OUT}/road_normal.jpg', quality=90)
orm = np.stack([np.ones_like(rough), rough, np.zeros_like(rough)], -1)
Image.fromarray((orm * 255 + .5).astype(np.uint8)).save(f'{OUT}/road_orm.jpg', quality=90)
print('composite', alb.shape)

if '--glb' in sys.argv:
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def plane(name, w, l, cx, cz, y, uvs):
        me = bpy.data.meshes.new(name)
        V = [(cx - w / 2, -(cz - l / 2) * 0 - (cz - l / 2), y), ]
        # Blender coords: x, -z(gltf), y(gltf)
        V = [(cx - w / 2, -(cz - l / 2), y), (cx + w / 2, -(cz - l / 2), y), (cx + w / 2, -(cz + l / 2), y), (cx - w / 2, -(cz + l / 2), y)]
        me.from_pydata(V, [], [[0, 1, 2, 3]])
        uv = me.uv_layers.new(name='UVMap')
        uv.data.foreach_set('uv', np.array(uvs, np.float32).ravel())
        ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
        return ob
    def mat(name, a, n, o, rep=None):
        m = bpy.data.materials.new(name); nt = m.node_tree; b = nt.nodes['Principled BSDF']
        ta = nt.nodes.new('ShaderNodeTexImage'); ta.image = bpy.data.images.load(a); nt.links.new(ta.outputs[0], b.inputs['Base Color'])
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = bpy.data.images.load(n); tn.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(tn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], b.inputs['Normal'])
        to = nt.nodes.new('ShaderNodeTexImage'); to.image = bpy.data.images.load(o); to.image.colorspace_settings.name = 'Non-Color'
        sp = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(to.outputs[0], sp.inputs[0]); nt.links.new(sp.outputs['Green'], b.inputs['Roughness'])
        b.inputs['Metallic'].default_value = 0
        return m
    r = plane('road', WX, LZ, 0, LZ / 2 - 6, 0.004, [(0, 0), (1, 0), (1, 1), (0, 1)])
    r.data.materials.append(mat('road', f'{OUT}/road_albedo.jpg', f'{OUT}/road_normal.jpg', f'{OUT}/road_orm.jpg'))
    s = plane('sand', 120, 120, 0, 10, 0.0, [(0, 0), (20, 0), (20, 20), (0, 20)])
    s.data.materials.append(mat('sand', f'{T}/sand_albedo.jpg', f'{T}/sand_normal.jpg', f'{T}/sand_rough.jpg'))
    bpy.ops.export_scene.gltf(filepath=f'{OUT}/road.glb', export_format='GLB', export_yup=True, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=90)
