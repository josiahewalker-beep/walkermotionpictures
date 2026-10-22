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
    n_out = blurred_normals(B.outer, V, radius=NORMAL_BLUR)
    n_full = field_normals(B.field, V, h=0.0015)
    dw = B.well_dist(V[:, 0], V[:, 1], V[:, 2])
    w = np.clip((-dw - 0.001) / 0.004, 0, 1)[:, None]   # inside the well cut -> well normals
    return normalize(n_out * (1 - w) + n_full * w)

def body_surface(B, bounds, res, target):
    t = time.time()
    V, F = mc_mesh(B.field, *bounds, res)
    log('mc', len(F), round(time.time() - t, 1))
    V, F = decimate(V, F, target)
    V = project_to_surface(B.field, V)
    N = body_normals(B, V)
    F = fix_winding(V, F, N)
    log('decimated', len(F))
    return V, F, N

def run_cuts(B, V, F, N, cuts):
    """cuts: list of (name, fn, offsets)"""
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

def export(parts, mats, out, origins):
    total = blendout.build(parts, mats, out, node_origins=origins)
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
