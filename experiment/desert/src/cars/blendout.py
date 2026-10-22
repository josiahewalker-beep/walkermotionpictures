"""Write a Parts collection (carlib.Parts) to a GLB through Blender (bpy as a Python module).

Model frame (x lateral, s forward, z up) -> Blender (-x, -s, z): nose toward Blender -Y = glTF +Z.
Each node becomes one Blender object (one glTF node/mesh with one primitive per material).
"""
import numpy as np
import bpy

def _clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def make_image(name, arr, colorspace='sRGB'):
    """arr: HxWx3 or HxWx4 float 0..1 (row 0 = top)."""
    h, w = arr.shape[:2]
    if arr.shape[2] == 3:
        arr = np.concatenate([arr, np.ones((h, w, 1))], 2)
    img = bpy.data.images.new(name, w, h, alpha=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    img.file_format = 'JPEG' if name.endswith('jpg') else 'PNG'
    img.pack()
    return img

def make_material(name, spec):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    c = spec.get('color', (0.5, 0.5, 0.5))
    bsdf.inputs['Base Color'].default_value = (*c, 1.0)
    bsdf.inputs['Metallic'].default_value = spec.get('metallic', 0.0)
    bsdf.inputs['Roughness'].default_value = spec.get('roughness', 0.5)
    if 'emission' in spec:
        bsdf.inputs['Emission Color'].default_value = (*spec['emission'], 1.0)
        bsdf.inputs['Emission Strength'].default_value = spec.get('emission_strength', 1.0)
    if 'alpha' in spec:
        bsdf.inputs['Alpha'].default_value = spec['alpha']
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
    if 'ior' in spec:
        bsdf.inputs['IOR'].default_value = spec['ior']
    m.use_backface_culling = not spec.get('double', False)
    if spec.get('vcol'):
        # multiply base colour by COLOR_0 so the exporter keeps the attribute
        vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
        if 'tex' in spec:
            pass
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        mix.inputs[6].default_value = (*c, 1.0)
        nt.links.new(vc.outputs['Color'], mix.inputs[7])
        nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    if 'tex' in spec:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = spec['tex']
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    if 'normal_tex' in spec:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = spec['normal_tex']
        t.image.colorspace_settings.name = 'Non-Color'
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = spec.get('normal_strength', 1.0)
        nt.links.new(t.outputs['Color'], nm.inputs['Color'])
        nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    if 'rough_tex' in spec:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = spec['rough_tex']
        t.image.colorspace_settings.name = 'Non-Color'
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(t.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
    return m

def to_blender(V):
    V = np.asarray(V, float)
    return np.stack([-V[:, 0], -V[:, 1], V[:, 2]], 1)

def build(parts, matspecs, out_path, node_origins=None, root_name='car'):
    """parts: carlib.Parts; matspecs: name -> spec dict; node_origins: node -> (x,s,z) pivot in model frame."""
    _clear()
    scn = bpy.context.scene
    mats = {k: make_material(k, v) for k, v in matspecs.items()}
    root = bpy.data.objects.new(root_name, None)
    scn.collection.objects.link(root)
    node_origins = node_origins or {}
    total = 0
    for node, plist in parts.nodes.items():
        org = np.asarray(node_origins.get(node, (0, 0, 0)), float)
        Vs, Fs, Ns, Ms, UVs, Cs = [], [], [], [], [], []
        off = 0
        matnames = []
        for p in plist:
            V, F, N = p['V'], p['F'], p['N']
            if p.get('flat'):
                # unshare vertices so each face is flat-shaded
                fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
                fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
                V = V[F].reshape(-1, 3); N = np.repeat(fn, 3, 0)
                uv = p['UV'][F].reshape(-1, 2) if p['UV'] is not None else None
                col = p['COL'][F].reshape(-1, p['COL'].shape[1]) if p['COL'] is not None else None
                F = np.arange(len(V)).reshape(-1, 3)
            else:
                uv = p['UV']; col = p['COL']
            if p['mat'] not in matnames:
                matnames.append(p['mat'])
            Vs.append(V - org); Fs.append(F + off); Ns.append(N)
            Ms.append(np.full(len(F), matnames.index(p['mat'])))
            UVs.append(uv if uv is not None else np.zeros((len(V), 2)))
            Cs.append(col if col is not None else np.ones((len(V), 4)))
            off += len(V)
        V = to_blender(np.concatenate(Vs)); F = np.concatenate(Fs); N = to_blender(np.concatenate(Ns))
        M = np.concatenate(Ms); UV = np.concatenate(UVs); C = np.concatenate(Cs)
        if C.shape[1] == 3:
            C = np.concatenate([C, np.ones((len(C), 1))], 1)
        total += len(F)
        me = bpy.data.meshes.new(node)
        me.vertices.add(len(V)); me.vertices.foreach_set('co', V.astype(np.float32).ravel())
        me.loops.add(len(F) * 3); me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
        me.polygons.add(len(F))
        me.polygons.foreach_set('loop_start', (np.arange(len(F)) * 3).astype(np.int32))
        me.polygons.foreach_set('loop_total', np.full(len(F), 3, np.int32))
        me.polygons.foreach_set('material_index', M.astype(np.int32))
        me.update(calc_edges=True)
        me.validate(clean_customdata=False)
        for mn in matnames:
            me.materials.append(mats[mn])
        uvl = me.uv_layers.new(name='UVMap')
        lv = F.ravel()
        uvl.data.foreach_set('uv', UV[lv].astype(np.float32).ravel())
        ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set('color', np.clip(C, 0, 1).astype(np.float32).ravel())
        me.color_attributes.active_color = ca
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices(N.astype(np.float32))
        ob = bpy.data.objects.new(node, me)
        ob.location = tuple(to_blender(org[None])[0])
        ob.parent = root
        scn.collection.objects.link(ob)
    bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', export_yup=True, export_apply=True,
                              export_image_format='AUTO', export_vertex_color='ACTIVE',
                              export_all_vertex_colors=False, export_tangents=False)
    return total
