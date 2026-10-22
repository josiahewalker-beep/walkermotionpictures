"""Preview only (not shipped): a 24 × 24 m plane with a tiling ground texture (4 m repeat) plus scattered cones,
needle clumps and a rock, written to src/pines/preview/<name>_ground.glb for the harness (use ground=0)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from common import Part, bpy_reset, build_object, make_material, TEX
import bpy

name = sys.argv[1] if len(sys.argv) > 1 else 'lot'
n = 24
part = Part()
g = np.linspace(-12, 12, n + 1)
X, Y = np.meshgrid(g, g)
V = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], -1)
W = n + 1
T = []
for j in range(n):
    for i in range(n):
        a = j * W + i
        T += [[a, a + 1, a + W + 1], [a, a + W + 1, a + W]]
part.add(V, T, n=np.tile([0, 0, 1.0], (len(V), 1)), uv=V[:, :2] / 4.0)
bpy_reset()
mat = make_material('dirt', base=os.path.join(TEX, f'{name}_albedo.jpg'), normal=os.path.join(TEX, f'{name}_normal.jpg'),
                    rough=0.9, vcol=False)
build_object(f'{name}_ground', {'dirt': part}, {'dirt': mat})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'preview', f'{name}_ground.glb')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=True, export_apply=True, export_image_format='JPEG')
print(out)
