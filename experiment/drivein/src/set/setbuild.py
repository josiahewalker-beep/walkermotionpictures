"""Generic Blender build for a SET asset: buckets -> meshes -> atlas bakes -> weathering -> materials -> GLB."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipe
from pipe import log, SCR
import weather2 as W2
import bb_weather as BW
import bpy

WEATHER = {'wood': W2.weather_wood, 'paintwood': W2.weather_paintwood, 'metal': W2.weather_metal}


def build(Bk, atlas, tex_name, out_glb, sources, perch, root_name, plain=None, ground=0.0, ao_dist=0.8,
          ao_ground=(0, 0, 0, 30), parent_map=None, origin_map=None, extra=None):
    """atlas: {bucket: (res, kind, kwargs)} kind in wood|paintwood|metal|concrete.
    plain: {bucket: (uv_scale, material_factory)} for meshes with tiling / flat materials.
    extra(objs, root): callback before export (add nodes etc.)."""
    texd = f'{SCR}/{tex_name}'
    os.makedirs(texd, exist_ok=True)
    plain = plain or {}
    root = pipe.empty(root_name)
    objs = {}
    for name, b in Bk.items():
        V, F, tags = b.arrays()
        if not len(F):
            continue
        par = root if not parent_map or name not in parent_map else objs[parent_map[name]]
        org = None if not origin_map else origin_map.get(name)
        if name in atlas:
            ob = pipe.make_mesh(name, V, F, attr=b.attr, parent=par, origin=org)
        else:
            sc = plain.get(name, (1.0, None))[0]
            ob = pipe.make_mesh(name, V, F, uvs=pipe.box_uv(V, F, sc), smooth_angle=60, parent=par, origin=org)
        objs[name] = ob
        log(name, len(V), 'verts', len(F), 'faces')
    for name, (res, kind, kw) in atlas.items():
        if name in objs:
            pipe.smart_uv(objs[name], 0.003 if res >= 2048 else 0.005)
    x, y, z, s = ao_ground
    bpy.ops.mesh.primitive_plane_add(size=s, location=(x, y, z))
    bpy.context.active_object.name = 'AO_ground'
    pipe.setup_cycles(ao_dist=ao_dist)
    src = np.array([np.r_[pipe.to_blender(p), s_, w, l] for p, s_, w, l in sources]) if sources else np.zeros((0, 6))
    per = np.array([np.r_[pipe.to_blender(p), r, d] for p, r, d in perch]) if perch else np.zeros((0, 5))
    for name, (res, kind, kw) in atlas.items():
        if name not in objs:
            continue
        d = pipe.extend(pipe.bake_maps(objs[name], res, ao_samples=16))
        P, N, AO, AX, K, used = d['pos'], d['nrm'], d['ao'], d['ax'], d['k'], d['used']
        tm = BW.texel_size(P, used)
        E = pipe.edge_map(used, tm)
        if kind == 'concrete':
            out = W2.weather_concrete(P, N, AO, E, AX, K, used, ground=ground, **kw)
        else:
            out = WEATHER[kind](P, N, AO, E, AX, K, used, src, per, ground=ground, **kw)
        al, orm, nm = pipe.save_set(texd, name, *out, tm, used)
        mname = kw.get('_mat', name) if False else name
        pipe.assign(objs[name], pipe.material(name.split('.')[0], al, orm, nm))
        log('weathered', name, 'texel mm', round(tm, 1))
    for name, (sc, fac) in plain.items():
        if name in objs and fac is not None:
            pipe.assign(objs[name], fac())
    for name, ob in objs.items():
        ob.data.name = name
    if extra:
        extra(objs, root)
    pipe.export(out_glb)
    return objs
