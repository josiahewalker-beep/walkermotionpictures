"""Blender side of the SET pipeline (shared by screen / booth / lamp pole):
geo buckets -> meshes -> UVs -> Cycles bakes (world position, normal, AO, grain axis, paint scalar) per atlas material
-> numpy weathering (weather2.py) -> PNG textures -> glTF materials -> GLB.
Approach follows the desert billboard (desert/src/set/bb_build.py + bb_finish.py)."""
import os, sys, math, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from scipy import ndimage as ndi
from PIL import Image

SCR = os.environ.get('SET_SCRATCH', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/drivein_set')
os.makedirs(SCR, exist_ok=True)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def to_blender(V):
    V = np.asarray(V, float)
    return np.stack([V[..., 0], -V[..., 2], V[..., 1]], -1)


def to_gltf(V):
    V = np.asarray(V, float)
    return np.stack([V[..., 0], V[..., 2], -V[..., 1]], -1)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box_uv(V, F, scale, top_only=False):
    uvs = []
    for f in F:
        P = V[f]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(f) > 3:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        ax = 1 if top_only else int(np.argmax(np.abs(n)))
        if ax == 0:
            uv = np.stack([-P[:, 2] * np.sign(n[0] or 1), P[:, 1]], 1)
        elif ax == 1:
            uv = np.stack([P[:, 0], -P[:, 2]], 1)
        else:
            uv = np.stack([P[:, 0] * np.sign(n[2] or 1), P[:, 1]], 1)
        uvs.append(uv / scale)
    return uvs


def make_mesh(name, V, F, attr=None, uvs=None, smooth_angle=35, recalc=True, parent=None, origin=None):
    """V in glTF coords. origin (glTF) becomes the object location (pivot); verts are stored relative to it."""
    me = bpy.data.meshes.new(name)
    Vb = to_blender(V)
    loc = np.zeros(3) if origin is None else to_blender(np.asarray(origin, float))
    me.from_pydata((Vb - loc).tolist(), [], [list(f) for f in F])
    me.validate(clean_customdata=False)
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc.tolist()
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        bpy.context.view_layer.update()
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', np.concatenate(uvs).astype(np.float32).ravel())
    if attr is not None:
        A = np.asarray(attr, np.float32)                  # per polygon (ax, ay, az, k), glTF axis
        Ab = np.stack([A[:, 0], A[:, 2], A[:, 1], A[:, 3]], 1)   # abs axis in Blender order
        npl = np.array([len(f) for f in F])
        per_loop = np.repeat(Ab, npl, axis=0)
        ca = me.color_attributes.new('gattr', 'FLOAT_COLOR', 'CORNER')
        c = np.concatenate([per_loop[:, :3], np.ones((len(per_loop), 1), np.float32)], 1)
        ca.data.foreach_set('color', c.ravel())
        cb = me.color_attributes.new('kattr', 'FLOAT_COLOR', 'CORNER')
        c2 = np.concatenate([np.repeat(per_loop[:, 3:4], 3, 1), np.ones((len(per_loop), 1), np.float32)], 1)
        cb.data.foreach_set('color', c2.ravel())
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    except Exception as e:
        log('sharp-from-angle failed', e)
    return ob


def empty(name, origin=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.location = to_blender(np.asarray(origin, float)).tolist()
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        bpy.context.view_layer.update()
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()
    return ob


def select_only(ob):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)


def smart_uv(ob, margin, angle=48):
    select_only(ob)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=margin, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    try:
        bpy.ops.uv.pack_islands(margin=margin, rotate=True, shape_method='CONCAVE')
    except TypeError:
        bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def setup_cycles(ao_dist=0.8):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 1
    sc.render.bake.margin = 8
    sc.render.bake.margin_type = 'EXTEND'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 2
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.light_settings.distance = ao_dist


def _bake_mat(kind):
    m = bpy.data.materials.new('bake_' + kind)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    if kind == 'pos':
        nt.links.new(geo.outputs['Position'], em.inputs['Color'])
    elif kind == 'nrm':
        nt.links.new(geo.outputs['Normal'], em.inputs['Color'])
    elif kind in ('ax', 'k'):
        at = nt.nodes.new('ShaderNodeAttribute'); at.attribute_name = 'gattr' if kind == 'ax' else 'kattr'
        nt.links.new(at.outputs['Color'], em.inputs['Color'])
    img_node = nt.nodes.new('ShaderNodeTexImage')
    nt.nodes.active = img_node
    return m, img_node


def bake_maps(ob, res, ao_samples=16, kinds=('pos', 'nrm', 'ax', 'k', 'ao')):
    sc = bpy.context.scene
    out = {}
    for kind in kinds:
        img = bpy.data.images.new(f'{ob.name}_{kind}', res, res, alpha=False, float_buffer=True)
        m, imn = _bake_mat(kind)
        imn.image = img
        ob.data.materials.clear(); ob.data.materials.append(m)
        select_only(ob)
        if kind == 'ao':
            sc.cycles.samples = ao_samples
            bpy.ops.object.bake(type='AO', margin=8)
        else:
            sc.cycles.samples = 1
            bpy.ops.object.bake(type='EMIT', margin=0 if kind == 'nrm' else 8)
        a = np.empty(res * res * 4, np.float32)
        img.pixels.foreach_get(a)
        out[kind] = a.reshape(res, res, 4)[::-1, :, :3].copy()
        bpy.data.images.remove(img)
        bpy.data.materials.remove(m)
        log('baked', ob.name, kind, res)
    out['used'] = np.linalg.norm(out['nrm'], axis=-1) > 0.5
    ob.data.materials.clear()
    return out


def extend(d):
    used = d['used']
    _, (iy, ix) = ndi.distance_transform_edt(~used, return_indices=True)
    for k in ('pos', 'nrm', 'ax', 'k', 'ao'):
        if k in d:
            d[k] = d[k][iy, ix]
    d['nrm'] = d['nrm'] / (np.linalg.norm(d['nrm'], axis=-1, keepdims=True) + 1e-9)
    return d


def edge_map(used, texel_mm, radius_mm=9.0):
    d = ndi.distance_transform_edt(used)
    return np.exp(-np.clip(d - 1, 0, None) * texel_mm / radius_mm) * used


# ---------------------------------------------------------------- materials
def load_img(path, noncolor=False):
    im = bpy.data.images.load(path)
    if noncolor:
        im.colorspace_settings.name = 'Non-Color'
    return im


def material(name, albedo=None, orm=None, normal=None, base=(0.5, 0.5, 0.5), rough=0.8, metal=0.0, alpha=1.0,
             double=False, nstr=1.0, emissive=None, emissive_strength=1.0, rough_img=None, alpha_img=False):
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
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(albedo)
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha_img:
            nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])
            try:
                m.surface_render_method = 'DITHERED'
            except Exception:
                m.blend_method = 'CLIP'
    if orm:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(orm, True)
        sp = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t.outputs['Color'], sp.inputs['Color'])
        nt.links.new(sp.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sp.outputs['Blue'], bsdf.inputs['Metallic'])
    if normal:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = load_img(normal, True)
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if emissive is not None:
        bsdf.inputs['Emission Color'].default_value = (*emissive, 1)
        bsdf.inputs['Emission Strength'].default_value = emissive_strength
    if alpha < 1:
        bsdf.inputs['Alpha'].default_value = alpha
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            m.blend_method = 'BLEND'
    m.use_backface_culling = not double
    return m


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


def save_set(texd, name, col, rough, metal, h, texel_mm, used, nstrength=1.0, ext='png'):
    from texlib import save_srgb, save_normal
    from bb_weather import height_to_normal
    _, (iy, ix) = ndi.distance_transform_edt(~used, return_indices=True)
    col, rough, metal, h = col[iy, ix], rough[iy, ix], metal[iy, ix], h[iy, ix]
    save_srgb(col, f'{texd}/{name}_albedo.png')
    orm = np.stack([np.ones_like(rough), rough, metal], -1)
    Image.fromarray(np.clip(orm * 255 + 0.5, 0, 255).astype(np.uint8)).save(f'{texd}/{name}_orm.png')
    n = height_to_normal(ndi.gaussian_filter(h, 0.6), texel_mm, nstrength)
    save_normal(n, f'{texd}/{name}_normal.png')
    return [f'{texd}/{name}_albedo.png', f'{texd}/{name}_orm.png', f'{texd}/{name}_normal.png']


def tri_count():
    t = 0
    for o in bpy.data.objects:
        if o.type == 'MESH':
            t += sum(len(p.vertices) - 2 for p in o.data.polygons)
    return t


def export(path, jpeg_quality=88, vcol=False):
    for o in list(bpy.data.objects):
        if o.type == 'MESH' and o.name.startswith('AO_'):
            bpy.data.objects.remove(o)
    kw = dict(filepath=path, export_format='GLB', export_yup=True, export_apply=True,
              export_image_format='JPEG', export_jpeg_quality=jpeg_quality, export_tangents=False,
              export_animations=False, export_cameras=False, export_lights=False)
    try:
        bpy.ops.export_scene.gltf(**kw, export_vertex_color='ACTIVE' if vcol else 'NONE')
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    log('exported', path, round(os.path.getsize(path) / 1e6, 2), 'MB', tri_count(), 'tris')
