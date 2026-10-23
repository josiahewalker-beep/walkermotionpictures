"""Shrink a GLB in place: COLOR_0 float → normalized UNSIGNED_BYTE (core glTF) and NORMAL float → normalized BYTE
(KHR_mesh_quantization, natively supported by three.js GLTFLoader). Positions / UVs / indices untouched.
usage: python3 quantize.py file.glb [...]
"""
import sys, json, struct
import numpy as np

CT = {5126: (np.float32, 4), 5121: (np.uint8, 1), 5123: (np.uint16, 2), 5125: (np.uint32, 4), 5120: (np.int8, 1)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}


def quantize(path):
    d = open(path, 'rb').read()
    jl = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + jl])
    bin_off = 20 + jl + 8
    bl = struct.unpack('<I', d[20 + jl:24 + jl])[0]
    binb = d[bin_off:bin_off + bl]

    def read(ai):
        a = j['accessors'][ai]
        bv = j['bufferViews'][a['bufferView']]
        dt, sz = CT[a['componentType']]
        n = NC[a['type']]
        start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', sz * n)
        raw = np.frombuffer(binb, np.uint8, count=stride * (a['count'] - 1) + sz * n, offset=start)
        if stride == sz * n:
            return np.frombuffer(raw.tobytes(), dt).reshape(a['count'], n)
        rows = np.lib.stride_tricks.as_strided(raw, (a['count'], sz * n), (stride, 1))
        return np.frombuffer(rows.tobytes(), dt).reshape(a['count'], n)

    # gather every accessor as an array, rewrite selected ones, then rebuild one tightly packed buffer
    arrays = {}
    for ai, a in enumerate(j['accessors']):
        arrays[ai] = read(ai)
    changed = set()
    for m in j['meshes']:
        for p in m['primitives']:
            at = p['attributes']
            for key in [k for k in at if k.startswith('COLOR_')]:
                ai = at[key]
                if j['accessors'][ai]['componentType'] == 5126:
                    v = arrays[ai]
                    if v.shape[1] == 4 and np.allclose(v[:, 3], 1.0):
                        v = v[:, :3]
                        j['accessors'][ai]['type'] = 'VEC3'
                    arrays[ai] = np.round(np.clip(v, 0, 1) * 255).astype(np.uint8)
                    j['accessors'][ai]['componentType'] = 5121
                    j['accessors'][ai]['normalized'] = True
                    changed.add(ai)
            if 'NORMAL' in at:
                ai = at['NORMAL']
                if j['accessors'][ai]['componentType'] == 5126:
                    v = arrays[ai]
                    v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
                    arrays[ai] = np.round(np.clip(v, -1, 1) * 127).astype(np.int8)
                    j['accessors'][ai]['componentType'] = 5120
                    j['accessors'][ai]['normalized'] = True
                    changed.add(ai)
    if not changed:
        return
    # rebuild buffer: one bufferView per accessor (4-byte aligned element stride for vertex attributes), images kept
    out = bytearray()
    new_views = []
    vertex_attr = set()
    for m in j['meshes']:
        for p in m['primitives']:
            vertex_attr.update(p['attributes'].values())
    view_of_acc = {}
    for ai, a in enumerate(j['accessors']):
        arr = arrays[ai]
        if ai in vertex_attr:
            elem = arr.dtype.itemsize * arr.shape[1]
            stride = (elem + 3) // 4 * 4
            buf = np.zeros((len(arr), stride), np.uint8)
            buf[:, :elem] = np.frombuffer(np.ascontiguousarray(arr).tobytes(), np.uint8).reshape(len(arr), elem)
            data = buf.tobytes()
            bv = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data), 'target': 34962}
            if stride != elem:
                bv['byteStride'] = stride
        else:
            data = np.ascontiguousarray(arr).tobytes()
            bv = {'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data)}
            if j['bufferViews'][a['bufferView']].get('target') == 34963:
                bv['target'] = 34963
        out += data
        out += b'\0' * ((4 - len(out) % 4) % 4)
        a['bufferView'] = len(new_views)
        a.pop('byteOffset', None)
        new_views.append(bv)
    for im in j.get('images', []):
        if 'bufferView' in im:
            ov = j['bufferViews'][im['bufferView']]
            data = binb[ov.get('byteOffset', 0):ov.get('byteOffset', 0) + ov['byteLength']]
            im['bufferView'] = len(new_views)
            new_views.append({'buffer': 0, 'byteOffset': len(out), 'byteLength': len(data)})
            out += data
            out += b'\0' * ((4 - len(out) % 4) % 4)
    j['bufferViews'] = new_views
    j['buffers'] = [{'byteLength': len(out)}]
    ext = set(j.get('extensionsUsed', [])) | {'KHR_mesh_quantization'}
    j['extensionsUsed'] = sorted(ext)
    j['extensionsRequired'] = sorted(set(j.get('extensionsRequired', [])) | {'KHR_mesh_quantization'})
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(out)
    res = struct.pack('<III', 0x46546C67, 2, total) + struct.pack('<II', len(js), 0x4E4F534A) + js + \
        struct.pack('<II', len(out), 0x004E4942) + bytes(out)
    open(path, 'wb').write(res)
    return len(d), len(res)


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(p, quantize(p))
