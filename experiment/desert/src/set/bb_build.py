"""Stage 1 (Blender, heavy): build the billboard meshes from bb_geo, UV them, bake world position / normal / AO / edge
maps for the atlas materials, save a .blend and an .npz cache.  Stage 2 is bb_finish.py.
Run under the shared lock:  flock .../heavy.lock python3 bb_build.py"""
import os, sys, math, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import bb_geo

SCR = os.environ.get('SET_SCRATCH', '/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/set')
os.makedirs(SCR, exist_ok=True)
BLEND = f'{SCR}/bb_stage1.blend'
CACHE = f'{SCR}/bb_bake'
ATLAS = {'paint_peeling': 2048, 'steel_weathered_rear': 1024, 'steel_weathered': 2048, 'concrete': 1024}
t0 = time.time()


def log(*a):
    print(f'[{time.time() - t0:6.1f}s]', *a, flush=True)


def to_blender(V):
    V = np.asarray(V, float)
    return np.stack([V[:, 0], -V[:, 2], V[:, 1]], 1)


def box_uv(V, F, scale, top_only=False):
    """Per-face box projection, glTF coords in metres → UV (per loop)."""
    uvs = []
    for f in F:
        P = V[f]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(f) > 3:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        ax = int(np.argmax(np.abs(n)))
        if top_only:
            ax = 1
        if ax == 0:
            uv = np.stack([P[:, 2] * np.sign(n[0] or 1) * -1, P[:, 1]], 1)
        elif ax == 1:
            uv = np.stack([P[:, 0], -P[:, 2]], 1)
        else:
            uv = np.stack([P[:, 0] * np.sign(n[2] or 1), P[:, 1]], 1)
        uvs.append(uv / scale)
    return uvs


def make_mesh(name, V, F, uvs=None, smooth_angle=35, recalc=True):
    me = bpy.data.meshes.new(name)
    Vb = to_blender(V)
    me.from_pydata(Vb.tolist(), [], [list(f) for f in F])
    me.validate(clean_customdata=False)
    if recalc:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if uvs is not None:
        uvl = me.uv_layers.new(name='UVMap')
        flat = np.concatenate(uvs)
        uvl.data.foreach_set('uv', flat.astype(np.float32).ravel())
    me.shade_smooth()
    try:
        me.set_sharp_from_angle(angle=math.radians(smooth_angle))
    except Exception as e:
        log('sharp-from-angle failed', e)
    return ob


def smart_uv(ob, margin):
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    if not ob.data.uv_layers:
        ob.data.uv_layers.new(name='UVMap')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(48), island_margin=margin, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    try:
        bpy.ops.uv.pack_islands(margin=margin, rotate=True, shape_method='CONCAVE')
    except TypeError:
        bpy.ops.uv.pack_islands(margin=margin, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    Bk = bb_geo.build()
    bad = bb_geo.check_front_clear(Bk)
    assert not bad, bad
    objs = {}
    for name, b in Bk.items():
        V, F, tags = b.arrays()
        if name in ATLAS:
            ob = make_mesh(name, V, F)
        elif name == 'grating':
            ob = make_mesh(name, V, F, box_uv(V, F, 1.0, top_only=True))     # 1 UV unit = 1 m, x / -z
        elif name == 'vinyl_old':
            ob = make_mesh(name, V, F, [np.stack([V[f, 0] / 11.2 + 0.5, (V[f, 1] - 2.55) / 4.8], 1) for f in F], smooth_angle=80, recalc=False)
        elif name == 'plate':
            ob = make_mesh(name, V, F, [np.array([[0, 0], [1, 0], [1, 1], [0, 1]])], recalc=False)
        else:
            ob = make_mesh(name, V, F, box_uv(V, F, 0.5), recalc=name not in ('glass', 'reflector'))   # rust, glass, reflector: 1 UV = 0.5 m
        objs[name] = ob
        log(name, len(V), 'verts', len(F), 'faces')
    for name in ATLAS:
        smart_uv(objs[name], 0.004 if ATLAS[name] >= 2048 else 0.006)
        log('uv', name)

    # ground for AO
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = 'AO_ground'

    # ---- bake setup ----
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 1
    sc.render.bake.margin = 8
    sc.render.bake.margin_type = 'EXTEND'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 2
    world = bpy.data.worlds.new('W'); sc.world = world
    world.light_settings.distance = 0.6

    def bake_mat(kind):
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
        elif kind == 'edge':
            bev = nt.nodes.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = 0.012; bev.samples = 8
            dot = nt.nodes.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
            nt.links.new(bev.outputs['Normal'], dot.inputs[0]); nt.links.new(geo.outputs['Normal'], dot.inputs[1])
            nt.links.new(dot.outputs['Value'], em.inputs['Color'])
        else:  # ao (shader irrelevant)
            pass
        img_node = nt.nodes.new('ShaderNodeTexImage')
        nt.nodes.active = img_node
        return m, img_node

    cache = {}
    for name, res in ATLAS.items():
        ob = objs[name]
        for kind in ('pos', 'nrm', 'edge', 'ao'):
            img = bpy.data.images.new(f'{name}_{kind}', res, res, alpha=False, float_buffer=True)
            m, imn = bake_mat(kind)
            imn.image = img
            ob.data.materials.clear(); ob.data.materials.append(m)
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True); bpy.context.view_layer.objects.active = ob
            if kind == 'ao':
                sc.cycles.samples = 24
                bpy.ops.object.bake(type='AO', margin=8)
            else:
                sc.cycles.samples = 8 if kind == 'edge' else 1
                bpy.ops.object.bake(type='EMIT', margin=8)
            a = np.empty(res * res * 4, np.float32)
            img.pixels.foreach_get(a)
            a = a.reshape(res, res, 4)[::-1, :, :3].copy()          # top row first (image convention)
            cache[f'{name}_{kind}'] = a
            log('baked', name, kind)
        # coverage mask: a texel is "used" if it has a normal
        cache[f'{name}_used'] = (np.linalg.norm(cache[f'{name}_nrm'], axis=-1) > 0.5)
        ob.data.materials.clear()
    np.savez_compressed(CACHE, **cache)
    log('saved cache')
    bpy.data.objects.remove(ground)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for im in list(bpy.data.images):
        bpy.data.images.remove(im)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    # also save the sources / perches the weathering needs
    np.savez(f'{SCR}/bb_meta', sources=np.array([np.r_[p, s, w, l] for p, s, w, l in bb_geo.SOURCES]),
             perch=np.array([np.r_[p, r, d] for p, r, d in bb_geo.PERCH]))
    log('done')


main()
