#!/usr/bin/env python3
"""Keeps a mesh's OLD atlas UVs (and triangle order) in a freshly exported GLB, so its baked texture stays valid.
Usage: python3 tools/glbkeep.py old.glb new.glb mesh [mesh ...]

Why: Blender does not pack an atlas the same way on every assemble (the `shelves` atlas in particular), so after a
re-export a part nobody touched can come out with its islands a few pixels away from where its texture was baked.
For a mesh whose geometry is unchanged this copies the UV and index data across from the old file, byte for byte;
it refuses (and changes nothing for that mesh) if the vertex positions are not identical."""
import sys, json, struct
import numpy as np

def read(path):
    b = bytearray(open(path, 'rb').read())
    n = struct.unpack('<I', b[12:16])[0]
    return b, json.loads(bytes(b[20:20 + n])), 20 + n + 8

def span(js, i):
    a = js['accessors'][i]; bv = js['bufferViews'][a['bufferView']]
    size = {5126: 4, 5123: 2, 5125: 4, 5121: 1}[a['componentType']] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[a['type']]
    assert not bv.get('byteStride'), 'interleaved buffers are not handled'
    return bv.get('byteOffset', 0) + a.get('byteOffset', 0), a['count'] * size, (a['componentType'], a['type'], a['count'])

def prim(js, name):
    for nd in js['nodes']:
        if nd.get('name') == name and 'mesh' in nd: return js['meshes'][nd['mesh']]['primitives'][0]
    return None

old, new = sys.argv[1], sys.argv[2]
bo, jo, oo = read(old); bn, jn, on = read(new)
changed = 0
for name in sys.argv[3:]:
    po, pn = prim(jo, name), prim(jn, name)
    if not po or not pn: print('%-16s missing in one of the files, left alone' % name); continue
    ok = True; jobs = []
    for key, io, i_n in (('POSITION', po['attributes']['POSITION'], pn['attributes']['POSITION']),
                         ('TEXCOORD_0', po['attributes']['TEXCOORD_0'], pn['attributes']['TEXCOORD_0']), ('indices', po['indices'], pn['indices'])):
        (so, lo, ko), (sn, ln, kn) = span(jo, io), span(jn, i_n)
        if ko != kn: ok = False; break
        if key == 'POSITION':
            if bo[oo + so:oo + so + lo] != bn[on + sn:on + sn + ln]:
                a = np.frombuffer(bytes(bo[oo + so:oo + so + lo]), np.float32); c = np.frombuffer(bytes(bn[on + sn:on + sn + ln]), np.float32)
                if np.abs(a - c).max() > 1e-6: ok = False; break
        else: jobs.append((so, lo, sn))
    if not ok: print('%-16s geometry differs, left alone (bake its atlas again)' % name); continue
    for so, lo, sn in jobs: bn[on + sn:on + sn + lo] = bo[oo + so:oo + so + lo]
    changed += 1; print('%-16s old UVs and triangle order kept' % name)
if changed: open(new, 'wb').write(bn)
