"""Fast proportion check: body field only (coarse) + wheels -> GLB. Usage: python3 quick_body.py sports|minivan out.glb [res]"""
import sys, time, importlib
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from carlib import mc_mesh, decimate, field_normals, fix_winding, Parts
from body import Body
import wheels

name = sys.argv[1]; out = sys.argv[2]; res = float(sys.argv[3]) if len(sys.argv) > 3 else 0.012
M = importlib.import_module(name + '_params')
B = Body(M.P)
t = time.time()
V, F = mc_mesh(B.field, *M.BOUNDS, res)
print('mc', len(F), time.time() - t)
V, F = decimate(V, F, 60000)
N = field_normals(B.field, V)
F = fix_winding(V, F, N)
parts = Parts()
parts.add('body', V, F, 'paint', N=N)
M2 = M
axles = [('FL', M.S_FA, M.X_WF, 0.255), ('FR', M.S_FA, M.X_WF, 0.255), ('RL', M.S_RA, M.X_WR, 0.285), ('RR', M.S_RA, M.X_WR, 0.285)]
style = dict(r_lip=0.262, r_barrel=0.232, width=0.24, spokes=10, split=0.0, a_face=0.100, dish=0.035, spoke_depth=0.03, spoke_w0=0.016, spoke_w1=0.011)
cent = wheels.add_wheels(parts, axles, None, M.R_TYRE, 0.254, 0.255, style, 0.19)
import blendout
mats = dict(paint=dict(color=M.PAINT if hasattr(M, 'PAINT') else (0.45, 0.02, 0.02), metallic=0.3, roughness=0.3),
            rubber=dict(color=(0.035, 0.035, 0.035), roughness=0.85), rim=dict(color=(0.08, 0.08, 0.085), metallic=1, roughness=0.35),
            brake=dict(color=(0.4, 0.4, 0.4), metallic=1, roughness=0.5), chrome=dict(color=(0.8, 0.8, 0.8), metallic=1, roughness=0.1),
            caliper=dict(color=(0.5, 0.02, 0.02), roughness=0.4))
print('tris', blendout.build(parts, mats, out, node_origins=cent))
