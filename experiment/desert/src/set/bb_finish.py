"""Stage 2: weathering textures from the stage-1 bake cache, small-part textures, materials, GLB export.
flock .../heavy.lock python3 bb_finish.py  [--tex-only]"""
import os, sys, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scipy import ndimage as ndi
from PIL import Image, ImageDraw, ImageFont
from texlib import *
import bb_weather as W
import bb_geo

SCR = os.environ.get('SET_SCRATCH', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/set')
TEXD = f'{SCR}/bbtex'
os.makedirs(TEXD, exist_ok=True)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT_GLB = f'{ROOT}/assets/billboard.glb'
t0 = time.time()


def log(*a):
    print(f'[{time.time() - t0:6.1f}s]', *a, flush=True)


def g2b(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


def save_set(name, col, rough, metal, h, texel_mm, used, nstrength=1.0):
    _, (iy, ix) = ndi.distance_transform_edt(~used, return_indices=True)
    col, rough, metal, h = col[iy, ix], rough[iy, ix], metal[iy, ix], h[iy, ix]
    save_srgb(col, f'{TEXD}/{name}_albedo.png')
    orm = np.stack([np.ones_like(rough), rough, metal], -1)
    Image.fromarray(np.clip(orm * 255 + 0.5, 0, 255).astype(np.uint8)).save(f'{TEXD}/{name}_orm.png')
    n = W.height_to_normal(ndi.gaussian_filter(h, 0.6), texel_mm, nstrength)
    save_normal(n, f'{TEXD}/{name}_normal.png')


def edge_map(used, texel_mm, radius_mm=9.0):
    d = ndi.distance_transform_edt(used)
    return np.exp(-np.clip(d - 1, 0, None) * texel_mm / radius_mm) * used


def make_atlas_textures():
    d = np.load(f'{SCR}/bb_bake.npz')
    bb_geo.build()                      # geometry is deterministic: regenerate streak sources / perches
    src = np.array([np.r_[p, s, w, l] for p, s, w, l in bb_geo.SOURCES]); src[:, :3] = g2b(src[:, :3])
    per = np.array([np.r_[p, r, d] for p, r, d in bb_geo.PERCH]); per[:, :3] = g2b(per[:, :3])
    for name in ('paint_peeling', 'steel_weathered_rear', 'steel_weathered', 'concrete'):
        P, N, AO, used = d[f'{name}_pos'], d[f'{name}_nrm'], d[f'{name}_ao'], d[f'{name}_used']
        _, (iy, ix) = ndi.distance_transform_edt(~used, return_indices=True)
        P, N, AO = P[iy, ix], N[iy, ix], AO[iy, ix]          # extend every map from the nearest covered texel
        N = N / (np.linalg.norm(N, axis=-1, keepdims=True) + 1e-9)
        tm = W.texel_size(P, used)
        E = edge_map(used, tm)
        log(name, 'texel mm', round(tm, 2))
        if name == 'paint_peeling':
            out = W.weather_painted(P, N, AO, E, used, src, per, [0.15, 0.148, 0.138], [0.235, 0.228, 0.212], seed=1)
        elif name == 'steel_weathered_rear':
            out = W.weather_painted(P, N, AO, E, used, src, per, [0.15, 0.148, 0.138], [0.225, 0.22, 0.205], seed=2, peel_amt=0.05)
        elif name == 'steel_weathered':
            out = W.weather_steel(P, N, AO, E, used, src, per, seed=21)
        else:
            out = W.weather_concrete(P, N, AO, E, used, seed=31)
        col, rough, metal, h = out
        save_set(name, col, rough, metal, h, tm, used)
        log('saved', name)


# ----------------------------------------------------------------- small-part textures
def tex_rust():
    """Tileable crusty rust, 1024^2 = 0.5 m."""
    n = 1024; r = rng(301)
    a = spectral((n, n), r, 2.2, lo=2, hi=300); b = spectral((n, n), r, 1.6, lo=20, hi=None)
    t = np.clip(0.5 + 0.3 * a + 0.2 * b, 0, 1)
    c = (np.array([0.07, 0.032, 0.016]) * (1 - t[..., None]) + np.array([0.29, 0.11, 0.035]) * t[..., None])
    scale = smoothstep(0.8, 1.6, spectral((n, n), r, 2.0, lo=8, hi=400))
    c = c * (1 - 0.3 * scale[..., None])
    dust = smoothstep(0.6, 1.5, spectral((n, n), r, 2.4, lo=2, hi=100)) * 0.4
    c = c * (1 - dust[..., None]) + np.array([0.38, 0.29, 0.20]) * dust[..., None]
    save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/rust_albedo.png')
    h = 0.4 * a + 0.25 * b + 0.3 * scale
    save_normal(normal_from_height(h, 1.0, 0.5), f'{TEXD}/rust_normal.png')
    orm = np.stack([np.ones((n, n)), np.clip(0.88 + 0.06 * b, 0, 1), np.zeros((n, n))], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(f'{TEXD}/rust_orm.png')


def tex_grating():
    """Unique (non-tiling) map for the whole deck: u = (x + 5.6)/11.2, v = (z + 1.8)/2.8 (glTF metres)."""
    Wd, Hd = 4096, 1024
    r = rng(311)
    yy, xx = np.mgrid[0:Hd, 0:Wd]
    X = xx / Wd * 11.2 - 5.6; Z = 1.0 - yy / Hd * 2.8           # image top = v 0 → z = 1.0 (front)
    lo = spectral((Hd, Wd), r, 2.4, lo=2, hi=200); mid = spectral((Hd, Wd), r, 1.8, lo=40, hi=1500)
    c = np.array([0.29, 0.29, 0.28]) * (1 + 0.08 * lo + 0.06 * mid)[..., None]
    white = smoothstep(0.5, 1.5, mid + 0.4 * lo) * 0.45
    c = c * (1 - white[..., None]) + np.array([0.45, 0.44, 0.41]) * white[..., None]
    rs = smoothstep(1.1, 1.8, spectral((Hd, Wd), r, 2.0, lo=30, hi=1500) + 0.5 * lo)
    c = c * (1 - rs[..., None]) + np.array([0.22, 0.09, 0.035]) * rs[..., None]
    # sand drifts against the toe plate (front) and in the corners
    sand = np.clip(smoothstep(0.75, 0.97, Z) * (0.6 + 0.4 * lo) + 0.4 * smoothstep(0.3, 1.2, lo), 0, 0.95)
    c = c * (1 - sand[..., None]) + np.array([0.40, 0.31, 0.22]) * (1 + 0.1 * mid)[..., None] * sand[..., None]
    # droppings: dense under the lamp arms & along the toe plate, scattered elsewhere
    dens = 0.25 + 0.75 * np.exp(-((Z - 0.85) / 0.15) ** 2)
    for lx in (-4.4, -2.2, 0.0, 2.2, 4.4):
        dens += 1.2 * np.exp(-((X - lx) / 0.35) ** 2 - ((Z - 0.8) / 0.25) ** 2)
    spots = spectral((Hd, Wd), rng(312), 1.2, lo=200, hi=None)
    D = smoothstep(2.3, 2.9, spots + 0.9 * dens)
    c = c * (1 - 0.9 * D[..., None]) + np.array([0.70, 0.68, 0.62]) * 0.9 * D[..., None]
    save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/grating_albedo.png')
    orm = np.stack([np.ones_like(lo), np.clip(0.62 + 0.25 * rs + 0.3 * sand + 0.1 * white, 0, 1), np.clip(0.5 * (1 - rs) * (1 - sand) * (1 - D), 0, 1)], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(f'{TEXD}/grating_orm.png')


def tex_vinyl():
    """Faded printed vinyl remnants: u = x/11.2 + 0.5, v = (y - 2.55)/4.8. Old sun-bleached print, dirty."""
    Wd, Hd = 2048, 1024
    r = rng(321)
    lo = spectral((Hd, Wd), r, 2.8, lo=1, hi=30); mid = spectral((Hd, Wd), r, 2.0, lo=10, hi=400)
    # ghosts of an old print: big colour fields (faded red, sky blue, warm yellow) with a dark band
    yy, xx = np.mgrid[0:Hd, 0:Wd] / np.array([Hd, Wd])[:, None, None]
    base = np.array([0.40, 0.37, 0.32])
    red = np.array([0.55, 0.20, 0.15]); blue = np.array([0.22, 0.33, 0.46]); yel = np.array([0.62, 0.50, 0.25])
    zone = (xx + 0.1 * lo * 0.2)
    c = np.where((zone < 0.38)[..., None], blue, np.where((zone < 0.71)[..., None], red, yel))
    c = c * (1 - 0.15 * (yy > 0.85)[..., None])
    fade = np.clip(0.55 + 0.15 * lo + 0.1 * mid, 0, 0.9)           # heavy UV bleaching toward the backing white
    c = c * (1 - fade[..., None]) + base * fade[..., None]
    grime = np.clip(0.25 + 0.4 * smoothstep(0.0, 1.5, spectral((Hd, Wd), r, 2.0, lo=4, hi=300, aniso=(0.3, 1.0))), 0, 0.7)
    c = c * (1 - grime[..., None]) + np.array([0.25, 0.20, 0.15]) * grime[..., None]
    save_srgb(np.clip(c, 0.05, 0.8), f'{TEXD}/vinyl_albedo.png')


def tex_plate():
    Wd, Hd = 512, 160
    r = rng(331)
    al = np.array([0.42, 0.42, 0.40]) * (1 + 0.08 * spectral((Hd, Wd), r, 2.0, lo=2, hi=100))[..., None]
    img = Image.new('L', (Wd, Hd), 0)
    dr = ImageDraw.Draw(img)
    try:
        f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
        f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
    except Exception:
        f1 = f2 = ImageFont.load_default()
    dr.rectangle((6, 6, Wd - 7, Hd - 7), outline=255, width=4)
    dr.text((Wd / 2, 52), 'HIGH DESERT OUTDOOR', font=f1, fill=255, anchor='mm')
    dr.text((Wd / 2, 108), 'STRUCTURE No. 1127   ·   EST. 1998', font=f2, fill=255, anchor='mm')
    t = np.asarray(img, float) / 255
    t = ndi.gaussian_filter(t, 0.8)
    paint = np.array([0.08, 0.10, 0.09])                            # old dark-green fill around raised letters
    c = al * t[..., None] + paint * (1 - t[..., None])
    rs = smoothstep(0.6, 1.5, spectral((Hd, Wd), r, 2.0, lo=4, hi=200) + 0.8 * (1 - t))
    c = c * (1 - 0.6 * rs[..., None]) + np.array([0.24, 0.10, 0.04]) * 0.6 * rs[..., None]
    dust = smoothstep(0.3, 1.0, spectral((Hd, Wd), r, 2.2, lo=2, hi=60)) * 0.45
    c = c * (1 - dust[..., None]) + np.array([0.40, 0.31, 0.22]) * dust[..., None]
    save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/plate_albedo.png')
    save_normal(normal_from_height(t * 0.6, 1.0, 0.8), f'{TEXD}/plate_normal.png')


# ----------------------------------------------------------------- Blender
def blender_export():
    import bpy
    bpy.ops.wm.open_mainfile(filepath=f'{SCR}/bb_stage1.blend')
    objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH'}

    def img(path, noncolor=False):
        im = bpy.data.images.load(path)
        if noncolor:
            im.colorspace_settings.name = 'Non-Color'
        return im

    def material(name, albedo=None, orm=None, normal=None, base=(0.5, 0.5, 0.5), rough=0.8, metal=0.0, alpha=1.0,
                 double=False, nstr=1.0, ior=None):
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        nt = m.node_tree
        bsdf = nt.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value = (*base, 1)
        bsdf.inputs['Roughness'].default_value = rough
        bsdf.inputs['Metallic'].default_value = metal
        if albedo:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(albedo)
            nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if orm:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(orm, True)
            sp = nt.nodes.new('ShaderNodeSeparateColor')
            nt.links.new(t.outputs['Color'], sp.inputs['Color'])
            nt.links.new(sp.outputs['Green'], bsdf.inputs['Roughness'])
            nt.links.new(sp.outputs['Blue'], bsdf.inputs['Metallic'])
        if normal:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(normal, True)
            nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
            nt.links.new(t.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
        if alpha < 1:
            bsdf.inputs['Alpha'].default_value = alpha
            try:
                m.surface_render_method = 'BLENDED'
            except Exception:
                m.blend_method = 'BLEND'
        m.use_backface_culling = not double
        return m

    T = lambda n: f'{TEXD}/{n}.png'
    mats = {}
    for n in ('paint_peeling', 'steel_weathered_rear', 'steel_weathered', 'concrete'):
        mats[n] = material(n, T(f'{n}_albedo'), T(f'{n}_orm'), T(f'{n}_normal'))
    mats['rust'] = material('rust', T('rust_albedo'), T('rust_orm'), T('rust_normal'))
    mats['grating'] = material('grating', T('grating_albedo'), T('grating_orm'), double=True)
    mats['vinyl_old'] = material('vinyl_old', T('vinyl_albedo'), rough=0.75, double=True)
    mats['plate'] = material('plate', T('plate_albedo'), normal=T('plate_normal'), rough=0.6, metal=0.4)
    mats['glass'] = material('glass', base=(0.30, 0.29, 0.27), rough=0.35, alpha=0.55, double=True)
    mats['reflector'] = material('reflector', base=(0.55, 0.54, 0.52), rough=0.45, metal=0.9, double=True)
    for n, o in objs.items():
        o.data.materials.clear()
        o.data.materials.append(mats[n])
    # grating UVs: unique deck mapping
    g = objs['grating'].data
    uvl = g.uv_layers[0] if g.uv_layers else g.uv_layers.new(name='UVMap')
    co = np.empty(len(g.vertices) * 3); g.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    li = np.empty(len(g.loops), int); g.loops.foreach_get('vertex_index', li)
    p = co[li]
    u = (p[:, 0] + 5.6) / 11.2
    v = 1 - (1.0 - (p[:, 1] * -1) * -1) / 2.8           # gltf z = -blender y ; v(img top = z 1.0) handled below
    gz = -p[:, 1]
    v = 1 - (1.0 - gz) / 2.8                             # blender v (bottom-up): z = 1.0 → v = 1 (image top)
    uvl.data.foreach_set('uv', np.stack([u, v], 1).astype(np.float32).ravel())
    # one object per material, named
    for n, o in objs.items():
        o.name = n
        o.data.name = n
    bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', export_yup=True, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=88, export_tangents=False,
                              export_vertex_color='NONE', export_animations=False, export_cameras=False, export_lights=False)
    log('exported', OUT_GLB, os.path.getsize(OUT_GLB) / 1e6, 'MB')


if __name__ == '__main__':
    if '--export-only' not in sys.argv:
        make_atlas_textures()
        tex_rust(); tex_grating(); tex_vinyl(); tex_plate()
        log('small textures')
    if '--tex-only' not in sys.argv:
        blender_export()
