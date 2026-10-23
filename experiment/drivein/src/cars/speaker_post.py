"""Classic drive-in speaker post: steel pipe (~1.1 m) on a small concrete footing, junction head with two hooks, two boxy
aluminium window speakers (grille face, volume knob, window hook) hanging either side, coiled cords into the pipe.
Origin at the base centre, +Y up. Speakers face model +-x (glTF -+X).  python3 speaker_post.py [out.glb]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from carlib import Parts, tube, box, revolve, vertex_normals, sstep
import carbuild as CB
import car90

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(car90.ASSETS, 'speaker_post.glb')

def col(V, base=1.0, lo=0.0, hi=1.2, dark=0.55):
    a = base * (dark + (1 - dark) * sstep(lo, hi, V[:, 2]))
    return np.c_[np.repeat(a[:, None], 3, 1), np.ones(len(V))]

def cyl(z0, z1, r, n=12, cap=True, c=(0, 0)):
    prof = ([(z0, 0.0)] if cap else []) + [(z0, r), (z1, r)] + ([(z1, 0.0)] if cap else [])
    V, F, _ = revolve(prof, n)
    # revolve is about x: (axial, r cos, r sin) -> put axial on z
    V = np.stack([V[:, 1] + c[0], V[:, 2] + c[1], V[:, 0]], 1)
    N = vertex_normals(V, F)
    cen = np.array([c[0], c[1], 0.5 * (z0 + z1)])
    out = np.einsum('ij,ij->i', N, V - cen)
    if np.mean(out) < 0: F = F[:, ::-1].copy()
    return V, F

def build():
    parts = Parts()
    n = 'speaker_post'
    # footing + pipe + cap
    V, F = cyl(0.0, 0.07, 0.10, n=10)
    parts.add(n, V, F, 'concrete', COL=col(V, 1.0, 0.0, 0.07, 0.6), flat=False)
    V, F = cyl(0.05, 1.02, 0.030, n=12)
    parts.add(n, V, F, 'steel_weathered', COL=col(V, 1.0, 0.05, 0.6, 0.55))
    V, F = cyl(1.02, 1.035, 0.036, n=12)
    parts.add(n, V, F, 'steel_weathered', COL=col(V, 0.9, 0.0, 1.0, 1.0))
    # junction head
    V, F = box((0, 0, 1.08), (0.055, 0.045, 0.05))
    parts.add(n, V, F, 'steel_weathered', flat=True, COL=col(V, 1.0, 1.0, 1.13, 0.7))
    V, F = box((0, 0, 1.135), (0.065, 0.055, 0.008))
    parts.add(n, V, F, 'steel_weathered', flat=True)
    for sg in (1, -1):
        # hook arm out of the head
        hook = np.array([(sg * 0.05, 0, 1.10), (sg * 0.085, 0, 1.10), (sg * 0.095, 0, 1.115), (sg * 0.09, 0, 1.13)])
        V, F = tube(hook, 0.006, n_seg=6)
        parts.add(n, V, F, 'steel_weathered')
        # speaker hanging from the hook: box 0.075 deep (x), 0.17 wide (s), 0.12 tall
        cx = sg * 0.135; cz = 1.03
        V, F = box((cx, 0, cz), (0.036, 0.085, 0.062))
        parts.add(n, V, F, 'aluminium', flat=True, COL=col(V, 1.0, 0.95, 1.1, 0.75))
        # bevelled front rim + grille face (dark perforated look)
        V, F = box((cx + sg * 0.037, 0, cz), (0.003, 0.077, 0.054))
        parts.add(n, V, F, 'aluminium', flat=True)
        V, F = box((cx + sg * 0.039, 0, cz + 0.004), (0.002, 0.068, 0.040))
        parts.add(n, V, F, 'trim_black', flat=True, COL=col(V, 1.0, 0, 1, 1.0))
        # horizontal grille louvres
        for zz in np.linspace(cz - 0.028, cz + 0.034, 6):
            V, F = box((cx + sg * 0.0415, 0, zz), (0.0015, 0.066, 0.0025))
            parts.add(n, V, F, 'aluminium', flat=True)
        # volume knob below the grille
        Vk, Fk = cyl(0.0, 0.012, 0.011, n=10)
        Vk = np.stack([cx + sg * (0.04 + Vk[:, 2]), Vk[:, 0] + 0.045, Vk[:, 1] + cz - 0.045], 1)
        Fk = Fk if sg > 0 else Fk[:, ::-1]
        if sg > 0: Fk = Fk[:, ::-1]
        parts.add(n, Vk, Fk, 'trim_black')
        # window hook on the back (the lip that hangs over the car's glass)
        V, F = box((cx - sg * 0.04, 0, cz + 0.055), (0.006, 0.05, 0.012))
        parts.add(n, V, F, 'aluminium', flat=True)
        # coiled cord: from under the speaker down and into the pipe
        t = np.linspace(0, 1, 34)
        p0 = np.array([cx, 0.03, cz - 0.062]); p1 = np.array([sg * 0.032, 0.0, 0.62])
        mid = p0 + (p1 - p0) * t[:, None]
        sag = -0.10 * np.sin(np.pi * t)
        coil = np.stack([0.018 * np.cos(t * 2 * np.pi * 5), 0.018 * np.sin(t * 2 * np.pi * 5), np.zeros_like(t)], 1)
        coil *= sstep(0.0, 0.15, t)[:, None] * (1 - sstep(0.85, 1.0, t))[:, None]
        path = mid + coil + np.stack([sg * 0.06 * np.sin(np.pi * t), np.zeros_like(t), sag], 1)
        V, F = tube(path, 0.0045, n_seg=4)
        parts.add(n, V, F, 'rubber', COL=col(V, 1.0, 0, 1, 1.0))
    mats = {
        'steel_weathered': dict(color=(0.22, 0.21, 0.19), metallic=0.75, roughness=0.62, vcol=True),
        'aluminium': dict(color=(0.62, 0.62, 0.60), metallic=1.0, roughness=0.42, vcol=True),
        'trim_black': dict(color=(0.03, 0.03, 0.03), metallic=0.0, roughness=0.5, vcol=True),
        'rubber': dict(color=(0.03, 0.03, 0.032), metallic=0.0, roughness=0.75, vcol=True),
        'concrete': dict(color=(0.36, 0.34, 0.31), metallic=0.0, roughness=0.92, vcol=True),
    }
    raw = OUT[:-4] + '_raw.glb'
    tris = CB.export(parts, mats, raw, {}, root='speaker_post_root')
    car90.pack(raw, OUT)
    return tris

if __name__ == '__main__':
    build()
