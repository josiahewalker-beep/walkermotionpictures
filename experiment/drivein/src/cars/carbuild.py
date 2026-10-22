"""Shared build pipeline: body field -> MC -> decimate -> project -> cuts -> labels/insets -> parts -> GLB."""
import time
import numpy as np
from carlib import smooth_normals, blurred_normals, mc_mesh, decimate, field_normals, fix_winding, project_to_surface, Parts, normalize, sstep
from surfops import CutSurface, build_labelled
import wheels as W
import blendout

SMOOTH_ITERS = 4
NORMAL_BLUR = 0.018

def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)

def body_normals(B, V):
    n_out = blurred_normals(B.outer, V, radius=B.P.get('normal_blur', NORMAL_BLUR))
    n_full = field_normals(B.field, V, h=0.0015)
    dw = B.well_dist(V[:, 0], V[:, 1], V[:, 2])
    w = np.clip((-dw - 0.001) / 0.004, 0, 1)[:, None]   # inside the well cut -> well normals
    return normalize(n_out * (1 - w) + n_full * w)

def split_edges(V, F, flag):
    """Split the flagged edges (bool per unique edge, edges as returned by unique_edges) with bmesh."""
    import bmesh
    bm = bmesh.new()
    for v in V: bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    for f in F:
        try: bm.faces.new([bm.verts[i] for i in f])
        except ValueError: pass
    bm.verts.index_update()
    want = set(map(tuple, flag.tolist()))
    sel = [e for e in bm.edges if tuple(sorted((e.verts[0].index, e.verts[1].index))) in want]
    if sel:
        bmesh.ops.subdivide_edges(bm, edges=sel, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts], float)
    F = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64)
    bm.free()
    return V, F, len(sel)

def refine_for_cuts(B, V, F, N, cuts, iters=4):
    """Edges that a thin feature (band, glass inset, strip) passes through without changing sign at the two end
    vertices would be skipped by the level-set cut: find them by sampling each cut function inside the edge, split
    them, re-project. Keeps the decimated mesh coarse everywhere else."""
    for it in range(iters):
        E = np.unique(np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1), axis=0)
        bad = np.zeros(len(E), bool)
        a, b = E[:, 0], E[:, 1]
        for name, fn, offs in cuts:
            if not offs: continue
            ga = fn(V[a], N[a]); gb = fn(V[b], N[b])
            for t in (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875):
                P = V[a] + t * (V[b] - V[a]); Nt = normalize(N[a] + t * (N[b] - N[a]))
                gt = fn(P, Nt)
                for o in offs:
                    sa, sb, st = np.sign(ga - o), np.sign(gb - o), np.sign(gt - o)
                    bad |= (sa == sb) & (st != sa) & (np.abs(gt) < 0.9)
        if not bad.any(): break
        V, F, n = split_edges(V, F, E[bad])
        V = project_to_surface(B.field, V)
        N = body_normals(B, V)
        F = fix_winding(V, F, N)
        log('refine', it, n, len(F))
    return V, F, N

def split_long(V, F, L, zmin=-1.0, iters=5):
    """Split edges longer than L (bmesh) so thin bands and inset features can't be skipped by long decimated slivers.
    Edges whose midpoint lies below zmin (underside) are left alone."""
    import bmesh
    bm = bmesh.new()
    for v in V: bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    for f in F:
        try: bm.faces.new([bm.verts[i] for i in f])
        except ValueError: pass
    for _ in range(iters):
        long = [e for e in bm.edges if e.calc_length() > L and 0.5 * (e.verts[0].co.z + e.verts[1].co.z) > zmin]
        if not long: break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    bm.verts.index_update()
    V = np.array([v.co[:] for v in bm.verts], float)
    F = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64)
    bm.free()
    return V, F

def body_surface(B, bounds, res, target, max_edge=None, zmin=-1.0):
    t = time.time()
    V, F = mc_mesh(B.field, *bounds, res)
    log('mc', len(F), round(time.time() - t, 1))
    V, F = decimate(V, F, target)
    if max_edge:
        V, F = split_long(V, F, max_edge, zmin)
        log('split', len(F))
    V = project_to_surface(B.field, V)
    N = body_normals(B, V)
    F = fix_winding(V, F, N)
    log('decimated', len(F))
    return V, F, N

def run_cuts(B, V, F, N, cuts):
    """cuts: list of (name, fn, offsets)"""
    V, F, N = refine_for_cuts(B, V, F, N, cuts)
    cs = CutSurface(V, F, N, normal_fn=lambda P: body_normals(B, P))
    for name, fn, offs in cuts:
        cs.add_fn(name, fn)
    for name, fn, offs in cuts:
        for o in offs:
            cs.cut(name, o)
    log('cut faces', len(cs.F))
    return cs

def tri_count(parts):
    return {n: sum(len(p['F']) for p in L) for n, L in parts.nodes.items()}

def export(parts, mats, out, origins, empties=None, root='car'):
    total = blendout.build(parts, mats, out, node_origins=origins, empties=empties, root_name=root)
    log('exported', out, total, tri_count(parts))
    return total

def base_materials(paint, rim_color, rim_rough=0.3, caliper=(0.42, 0.02, 0.02)):
    nrm, rough = W.tyre_textures(1024)
    return {
        'paint': dict(color=paint, metallic=0.55, roughness=0.28, vcol=True),
        'glass': dict(color=(0.03, 0.035, 0.04), metallic=0.0, roughness=0.03, alpha=0.82, ior=1.5),
        'chrome': dict(color=(0.85, 0.85, 0.86), metallic=1.0, roughness=0.08),
        'trim_black': dict(color=(0.035, 0.036, 0.038), metallic=0.0, roughness=0.42, vcol=True),
        'rubber': dict(color=(0.04, 0.04, 0.042), metallic=0.0, roughness=0.88, vcol=True, normal_arr=nrm, rough_arr=rough),
        'rim': dict(color=rim_color, metallic=1.0, roughness=rim_rough, vcol=True),
        'brake': dict(color=(0.30, 0.30, 0.31), metallic=0.8, roughness=0.62),
        'light_marker': dict(color=(0.55, 0.22, 0.02), metallic=0.0, roughness=0.15, emission=(1.0, 0.45, 0.05), emission_strength=0.1),
        'caliper': dict(color=caliper, metallic=0.0, roughness=0.35),
        'light_front': dict(color=(0.85, 0.86, 0.88), metallic=0.0, roughness=0.15, vcol=True, emission=(0.9, 0.95, 1.0), emission_strength=0.6),
        'light_rear': dict(color=(0.32, 0.01, 0.012), metallic=0.0, roughness=0.12, vcol=True, emission=(0.6, 0.02, 0.02), emission_strength=0.25),
        'light_rear_led': dict(color=(0.6, 0.05, 0.04), metallic=0.0, roughness=0.3, emission=(1.0, 0.06, 0.04), emission_strength=2.0),
        'light_cover': dict(color=(0.6, 0.62, 0.64), metallic=0.0, roughness=0.02, alpha=0.18, ior=1.5),
        'interior': dict(color=(0.045, 0.043, 0.042), metallic=0.0, roughness=0.65, vcol=True),
        'plate': dict(color=(1, 1, 1), metallic=0.0, roughness=0.45),
    }
