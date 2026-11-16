#!/usr/bin/env python3
"""Compares two GLBs mesh by mesh (positions, atlas UVs, indices). Usage: python3 tools/glbdiff.py old.glb new.glb [-v]
After a re-export, any mesh whose UVs moved needs its atlas baked again; meshes that only differ in index order are fine."""
import sys, json, struct, hashlib, numpy as np
def load(path):
    b = open(path, 'rb').read()
    n = struct.unpack('<I', b[12:16])[0]; js = json.loads(b[20:20 + n]); bin_ = b[20 + n + 8:]
    out = {}
    CT = {5126: np.float32, 5123: np.uint16, 5125: np.uint32, 5121: np.uint8}
    NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
    def acc(i):
        a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.frombuffer(bin_, CT[a['componentType']], a['count'] * NC[a['type']], off).reshape(a['count'], NC[a['type']])
    for nd in js['nodes']:
        if 'mesh' not in nd: continue
        m = js['meshes'][nd['mesh']]; pr = m['primitives'][0]
        pos = acc(pr['attributes']['POSITION']); uv = acc(pr['attributes']['TEXCOORD_0']); idx = acc(pr['indices'])
        mat = js['materials'][pr['material']]['name']
        out[nd['name']] = dict(mat=mat, pos=pos, uv=uv, idx=idx, t=nd.get('translation'))
    return out
A = load(sys.argv[1]); B = load(sys.argv[2])
print('only in A:', sorted(set(A) - set(B)), ' only in B:', sorted(set(B) - set(A)))
for k in sorted(set(A) & set(B)):
    a, b = A[k], B[k]
    same_shape = a['pos'].shape == b['pos'].shape and a['idx'].shape == b['idx'].shape
    if same_shape:
        dp = float(np.abs(a['pos'] - b['pos']).max()); du = float(np.abs(a['uv'] - b['uv']).max()); di = int((a['idx'] != b['idx']).sum())
        st = 'IDENTICAL' if dp < 1e-6 and du < 1e-6 and di == 0 else 'DIFF pos %.2g uv %.2g idx %d' % (dp, du, di)
    else: st = 'DIFF shape %s -> %s' % (a['pos'].shape, b['pos'].shape)
    if st != 'IDENTICAL' or '-v' in sys.argv: print('%-16s %-10s %s' % (k, a['mat'], st))
print('compared', len(set(A) & set(B)), 'meshes')
