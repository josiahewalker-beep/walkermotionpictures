"""Build assets/screen.glb (geometry, UVs, Cycles bakes, weathering, export) in one Blender run.
flock .../heavy.lock python3 src/set/screen_build.py      (~3-5 min on 2 cores)
Refuses to export if anything crosses in front of the face (screen_geo.check_front_clear / check_sightline)."""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipe
from pipe import log, SCR, ROOT
import screen_geo as SG
import weather2 as W2
import texlib as TL
from PIL import Image
import bpy

TEXD = f'{SCR}/screen_tex'
os.makedirs(TEXD, exist_ok=True)
OUT = f'{ROOT}/assets/screen.glb'
ATLAS = {'wood_old': 2048, 'wood_old_rear': 1024, 'wood_painted': 1024, 'steel_weathered': 1024, 'steel_weathered_rear': 512, 'concrete': 512}


def panel_tex():
    n = 1024; r = TL.rng(41)
    a = TL.spectral((n, n), r, 2.4, lo=1, hi=200); b = TL.spectral((n, n), r, 1.6, lo=30, hi=None)
    st = TL.spectral((n, n), r, 2.0, lo=2, hi=150, aniso=(0.15, 1.0))           # vertical runs
    c = np.array([0.052, 0.056, 0.052]) * (1 + 0.12 * a + 0.05 * b)[..., None]
    chalk = TL.smoothstep(0.6, 1.8, st + 0.4 * a) * 0.5
    c = c * (1 - chalk[..., None]) + np.array([0.11, 0.11, 0.10]) * chalk[..., None]
    rust = TL.smoothstep(1.6, 2.4, TL.spectral((n, n), r, 1.8, lo=20, hi=None) + 0.5 * a)
    c = c * (1 - rust[..., None]) + np.array([0.13, 0.06, 0.03]) * rust[..., None]
    TL.save_srgb(np.clip(c, 0.03, 0.85), f'{TEXD}/panel_albedo.png')
    orm = np.stack([np.ones((n, n)), np.clip(0.72 + 0.1 * chalk + 0.15 * rust + 0.04 * b, 0, 1), np.zeros((n, n))], -1)
    Image.fromarray((orm * 255).astype(np.uint8)).save(f'{TEXD}/panel_orm.png')
    TL.save_normal(TL.normal_from_height(0.3 * b + 0.6 * rust, 1.0, 2.0), f'{TEXD}/panel_normal.png')


def main():
    pipe.reset()
    Bk = SG.build()
    SG.split_visible(Bk, 'wood_old', 'wood_old_rear', SG.visible_from_camera)
    SG.split_visible(Bk, 'steel_weathered', 'steel_weathered_rear', SG.visible_from_camera)
    bad = SG.check_front_clear(Bk); bad2 = SG.check_sightline(Bk)
    if bad or bad2:
        raise SystemExit(f'REFUSING TO EXPORT: geometry in front of the face: {bad} {bad2}')
    root = pipe.empty('screen')
    objs = {}
    for name, b in Bk.items():
        V, F, tags = b.arrays()
        if name in ATLAS:
            ob = pipe.make_mesh(name, V, F, attr=b.attr, parent=root)
        else:
            ob = pipe.make_mesh(name, V, F, uvs=pipe.box_uv(V, F, 3.0), smooth_angle=60, parent=root)
        objs[name] = ob
        log(name, len(V), 'verts', len(F), 'faces')
    for name, res in ATLAS.items():
        pipe.smart_uv(objs[name], 0.003 if res >= 2048 else 0.005)
        log('uv', name)
    bpy.ops.mesh.primitive_plane_add(size=80, location=(0, -4, SG.GY))
    bpy.context.active_object.name = 'AO_ground'
    pipe.setup_cycles(ao_dist=1.2)
    src = np.array([np.r_[pipe.to_blender(p), s, w, l] for p, s, w, l in SG.SOURCES])
    per = np.array([np.r_[pipe.to_blender(p), r, d] for p, r, d in SG.PERCH])
    files = {}
    for name, res in ATLAS.items():
        d = pipe.extend(pipe.bake_maps(objs[name], res, ao_samples=16))
        P, N, AO, AX, K, used = d['pos'], d['nrm'], d['ao'], d['ax'], d['k'], d['used']
        import bb_weather as BW
        tm = BW.texel_size(P, used)
        E = pipe.edge_map(used, tm)
        log(name, 'texel mm', round(tm, 2))
        if name.startswith('wood_old'):
            out = W2.weather_wood(P, N, AO, E, AX, K, used, src, per, seed=1, ground=SG.GY)
        elif name == 'wood_painted':
            out = W2.weather_paintwood(P, N, AO, E, AX, K, used, src, per, seed=11, ground=SG.GY, top=18.6)
        elif name.startswith('steel_weathered'):
            out = W2.weather_metal(P, N, AO, E, AX, K, used, src, per, seed=21, ground=SG.GY)
        else:
            out = W2.weather_concrete(P, N, AO, E, AX, K, used, seed=31, ground=SG.GY)
        files[name] = pipe.save_set(TEXD, name, *out, tm, used)
        log('weathered', name)
    panel_tex()
    for name, ob in objs.items():
        if name in files:
            al, orm, nm = files[name]
            pipe.assign(ob, pipe.material(name, al, orm, nm))
        else:
            pipe.assign(ob, pipe.material('screen_panel', f'{TEXD}/panel_albedo.png', f'{TEXD}/panel_orm.png', f'{TEXD}/panel_normal.png'))
        ob.data.name = name
    pipe.export(OUT)


main()
