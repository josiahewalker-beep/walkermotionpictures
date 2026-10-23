"""Build assets/booth.glb.  flock .../heavy.lock python3 src/set/booth_build.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipe, setbuild
from pipe import ROOT
import booth_geo as BG
import geo

RED = ((0.20, 0.075, 0.05), (0.17, 0.065, 0.045), (0.22, 0.09, 0.06), (0.16, 0.07, 0.05))


def extra(objs, root):
    pipe.empty('lens', BG.PORT, parent=root)


pipe.reset()
Bk = BG.build()
setbuild.build(
    Bk,
    atlas={'wood_old': (1024, 'wood', {'seed': 3}),
           'wood_painted': (1024, 'paintwood', {'seed': 13, 'top': BG.YF, 'paints': RED}),
           'steel_weathered': (1024, 'metal', {'seed': 23}),
           'concrete': (256, 'concrete', {'seed': 33})},
    tex_name='booth_tex', out_glb=f'{ROOT}/assets/booth.glb', sources=geo.SOURCES, perch=geo.PERCH, root_name='booth',
    plain={'glass': (1.0, lambda: pipe.material('glass', base=(0.22, 0.22, 0.21), rough=0.25, alpha=0.6, double=True)),
           'interior': (1.0, lambda: pipe.material('interior', base=(0.035, 0.03, 0.025), rough=0.9))},
    ground=0.0, ao_dist=0.8, ao_ground=(0, 0, 0, 20), extra=extra)
