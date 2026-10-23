"""Regenerate the PINES section of drivein/ASSETS.md (between the PINES markers; other sections untouched)."""
import os, re, json, struct
import numpy as np
from common import ASSETS, TEX, DRIVEIN

FILES = ['pine_a', 'pine_a_lod1', 'pine_b', 'pine_b_lod1', 'pine_c', 'pine_c_lod1', 'rock_a', 'rock_b', 'pinecone',
         'needle_clump']


def info(path):
    d = open(path, 'rb').read()
    l = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + l])
    tris = sum(j['accessors'][p['indices']]['count'] // 3 for m in j['meshes'] for p in m['primitives'])
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for m in j['meshes']:
        for p in m['primitives']:
            a = j['accessors'][p['attributes']['POSITION']]
            lo = np.minimum(lo, a['min']); hi = np.maximum(hi, a['max'])
    return tris, hi - lo, len(d), [m['name'] for m in j.get('materials', [])], [n.get('name') for n in j['nodes']]


def table():
    rows = ['| file | size x × y(up) × z, m | tris | GLB | materials |', '|---|---|---|---|---|']
    for f in FILES:
        p = os.path.join(ASSETS, f + '.glb')
        if not os.path.exists(p):
            continue
        t, s, b, mats, nodes = info(p)
        rows.append(f'| `{f}.glb` | {s[0]:.2f} × {s[1]:.2f} × {s[2]:.2f} | {t:,} | {b/1e6:.1f} MB | {", ".join(mats)} |')
    return '\n'.join(rows)


BODY = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DOC.md')).read()

if __name__ == '__main__':
    path = os.path.join(DRIVEIN, 'ASSETS.md')
    s = open(path).read()
    sec = '<!-- PINES:BEGIN -->\n' + BODY.replace('{{TABLE}}', table()).strip() + '\n<!-- PINES:END -->'
    if '<!-- PINES:BEGIN -->' in s:
        s = re.sub(r'<!-- PINES:BEGIN -->.*?<!-- PINES:END -->', lambda m: sec, s, flags=re.S)
    else:
        s = s.rstrip('\n') + '\n\n' + sec + '\n'
    open(path, 'w').write(s)
    print('updated PINES section')
