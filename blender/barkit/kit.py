"""Small modelling kit on top of bmesh: boxes, lathes, tubes, quads; transform + property stacks."""
import bpy, bmesh, math
from mathutils import Vector, Matrix
from contextlib import contextmanager

XF = [Matrix.Identity(4)]
P = dict(atlas=None, td=1.0, part=0)
OBJS = []
PARTS = {}   # part id -> dict(name=..., matrix=Matrix)  (interactive pieces split off after UV packing)

@contextmanager
def xform(m):
    XF.append(XF[-1] @ m)
    try: yield
    finally: XF.pop()

@contextmanager
def props(**kw):
    old = dict(P); P.update(kw)
    try: yield
    finally:
        P.clear(); P.update(old)

def T(x, y, z): return Matrix.Translation((x, y, z))
def Rx(d): return Matrix.Rotation(math.radians(d), 4, 'X')
def Ry(d): return Matrix.Rotation(math.radians(d), 4, 'Y')
def Rz(d): return Matrix.Rotation(math.radians(d), 4, 'Z')

_PID = [0]
def new_part(name, origin=(0, 0, 0)):
    """register an interactive piece; returns its part id. origin is in the CURRENT xform's local coords and becomes the
    object's origin/pivot in the exported GLB (object axes stay world-aligned)."""
    _PID[0] += 1
    PARTS[_PID[0]] = dict(name=name, matrix=Matrix.Translation((XF[-1] @ Vector(origin).to_4d()).to_3d()), atlas=P['atlas'])
    return _PID[0]

@contextmanager
def interactive(name, origin=(0, 0, 0), td=None):
    """everything built inside becomes ONE separate named mesh in the GLB (clickable / animatable), pivot at origin."""
    pid = new_part(name, origin)
    kw = dict(part=pid)
    if td is not None: kw['td'] = td
    with props(**kw):
        yield pid

def adopt(ob, smooth=None):
    """register a mesh object you made WITHOUT the kit helpers (bpy.ops primitives, modifiers, metaballs, curves...).
    Converts to mesh, applies modifiers + transforms, tags it with the current props (atlas / td / part)."""
    import bpy as _b
    for o in _b.context.view_layer.objects: o.select_set(False)
    ob.select_set(True); _b.context.view_layer.objects.active = ob
    if ob.type != 'MESH' or ob.modifiers: _b.ops.object.convert(target='MESH')
    ob = _b.context.view_layer.objects.active
    _b.ops.object.transform_apply(location=True, rotation=True, scale=True)
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me)
    bm.transform(XF[-1])
    bm.loops.layers.uv.get('uv_tex') or bm.loops.layers.uv.new('uv_tex')
    bm.loops.layers.uv.get('uv_atlas') or bm.loops.layers.uv.new('uv_atlas')
    ltd = bm.faces.layers.float.get('td') or bm.faces.layers.float.new('td')
    lpart = bm.faces.layers.int.get('part') or bm.faces.layers.int.new('part')
    for f in bm.faces:
        f[ltd] = P['td']; f[lpart] = P['part']
        if smooth is not None: f.smooth = smooth
    bm.normal_update(); bm.to_mesh(me); bm.free()
    assert P['atlas'], 'kit.props(atlas=...) not set'
    ob['atlas'] = P['atlas']
    OBJS.append(ob)
    return ob

def finish(name, bm, mats, smooth=False, sharp=35):
    if not isinstance(mats, (list, tuple)): mats = [mats]
    bm.transform(XF[-1])
    bm.loops.layers.uv.get('uv_tex') or bm.loops.layers.uv.new('uv_tex')
    bm.loops.layers.uv.get('uv_atlas') or bm.loops.layers.uv.new('uv_atlas')
    ltd = bm.faces.layers.float.new('td'); lpart = bm.faces.layers.int.new('part')
    for f in bm.faces:
        f[ltd] = P['td']; f[lpart] = P['part']
        if smooth: f.smooth = True
    bm.normal_update()
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    if smooth and hasattr(me, 'set_sharp_from_angle'):
        me.set_sharp_from_angle(angle=math.radians(sharp))
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    assert P['atlas'], 'kit.props(atlas=...) not set'
    ob['atlas'] = P['atlas']
    OBJS.append(ob)
    return ob

AX = {'+x': Vector((1, 0, 0)), '-x': Vector((-1, 0, 0)), '+y': Vector((0, 1, 0)), '-y': Vector((0, -1, 0)),
      '+z': Vector((0, 0, 1)), '-z': Vector((0, 0, -1))}

def box(name, x0, x1, y0, y1, z0, z1, mat, skip=(), bevel=0.0, segs=2, only=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    bm.normal_update()
    if only: skip = [k for k in AX if k not in only]
    if isinstance(skip, str): skip = skip.split()
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=segs, affect='EDGES', profile=0.5)
        bm.normal_update()
    if skip:
        dead = [f for f in bm.faces if any(f.normal.dot(AX[k]) > 0.999 for k in skip)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return finish(name, bm, mat)

def lathe(name, prof, mat, segs=24, smooth=True, center=(0, 0, 0), mi=None, sharp=35):
    """prof: list of (r, z). Outward normal is (dz, -dr): go UP on outside walls, INWARD on top faces."""
    cx, cy, cz = center
    bm = bmesh.new(); rings = []
    for (r, z) in prof:
        if r < 1e-7: rings.append([bm.verts.new((cx, cy, cz + z))])
        else:
            rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * j / segs), cy + r * math.sin(2 * math.pi * j / segs), cz + z)) for j in range(segs)])
    for i in range(len(prof) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1: continue
        for j in range(segs):
            j2 = (j + 1) % segs
            if len(A) == 1: f = bm.faces.new((A[0], B[j2], B[j]))
            elif len(B) == 1: f = bm.faces.new((A[j], A[j2], B[0]))
            else: f = bm.faces.new((A[j], A[j2], B[j2], B[j]))
            if mi: f.material_index = mi[i]
    return finish(name, bm, mat, smooth=smooth, sharp=sharp)

def cyl(name, cx, cy, z0, z1, r, mat, segs=24, r1=None, cap='tb', smooth=True):
    r1 = r if r1 is None else r1
    prof = []
    if 'b' in cap: prof.append((0, z0))
    prof += [(r, z0), (r1, z1)]
    if 't' in cap: prof.append((0, z1))
    return lathe(name, prof, mat, segs=segs, smooth=smooth, center=(cx, cy, 0))

def tube(name, pts, r, mat, segs=8, caps=True, smooth=True, radii=None):
    pts = [Vector(p) for p in pts]
    bm = bmesh.new(); rings = []
    n = None
    for i, p in enumerate(pts):
        if i == 0: t = (pts[1] - pts[0])
        elif i == len(pts) - 1: t = (pts[-1] - pts[-2])
        else: t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        t.normalize()
        if n is None:
            a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n = t.cross(a).normalized()
        else:
            n = (n - t * n.dot(t)).normalized()
        b = t.cross(n)
        rr = radii[i] if radii else r
        rings.append([bm.verts.new(p + (n * math.cos(2 * math.pi * j / segs) + b * math.sin(2 * math.pi * j / segs)) * rr) for j in range(segs)])
    for i in range(len(pts) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((A[j], A[j2], B[j2], B[j]))
    if caps:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return finish(name, bm, mat, smooth=smooth)

def quad(name, pts, mat, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(vs)
    l = bm.loops.layers.uv.new('uv_tex')
    for loop, u in zip(f.loops, uv): loop[l].uv = u
    return finish(name, bm, mat)

def cyl_patch(name, cx, cy, z0, z1, r, a0, a1, mat, uvrect=(0, 0, 1, 1), segs=10):
    """label wrapped on a cylinder between angles a0..a1 (degrees, CCW from +x); uv u runs with angle"""
    bm = bmesh.new(); l = bm.loops.layers.uv.new('uv_tex')
    u0, v0, u1, v1 = uvrect
    cols = []
    for j in range(segs + 1):
        a = math.radians(a0 + (a1 - a0) * j / segs)
        cols.append((bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z0)), bm.verts.new((cx + r * math.cos(a), cy + r * math.sin(a), z1))))
    for j in range(segs):
        f = bm.faces.new((cols[j][0], cols[j + 1][0], cols[j + 1][1], cols[j][1]))
        ua, ub = u0 + (u1 - u0) * j / segs, u0 + (u1 - u0) * (j + 1) / segs
        for loop, u in zip(f.loops, ((ua, v0), (ub, v0), (ub, v1), (ua, v1))): loop[l].uv = u
    return finish(name, bm, mat, smooth=True)
