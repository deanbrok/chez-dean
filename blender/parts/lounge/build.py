"""LOUNGE — the left side of DEAN'S: upright piano under the high window, floor lamp, pink pay phone on its shelf,
framed sea chart, gig posters, coat stand + hat, umbrella stand (one umbrella wet, a puddle), stopped wall clock
above the stair door, a café table with its chairs up, a rubber plant.
Textures are painted by tex.py into tex/ (sheet.png + map.jpg; regions in tex/regions.json)."""
import os, json, math, random
import bmesh
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
_REG = None

def R(k):
    """uv rect (u0, v0, u1, v1) of a painted region of sheet.png"""
    global _REG
    if _REG is None: _REG = json.load(open(os.path.join(TEX, 'regions.json')))
    S = _REG['size']; x, y, w, h = _REG['regions'][k]
    return (x / S, 1 - (y + h) / S, (x + w) / S, 1 - y / S)

# ================================================================== geometry helpers
def V3(*a): return Vector(a)

def basis(o, right, up):
    """matrix whose local X = right, Y = up, Z = right x up (the face normal), origin o"""
    r = Vector(right).normalized(); u = Vector(up).normalized(); n = r.cross(u).normalized(); u = n.cross(r)
    m = Matrix.Identity(4)
    for i in range(3):
        m[i][0], m[i][1], m[i][2], m[i][3] = r[i], u[i], n[i], o[i]
    return m

def prism(name, pts, axis, a0, a1, mat, bevel=0.0, segs=2, skip=(), smooth=False, sharp=35):
    """2D polygon pts extruded along axis ('y': pts are (x,z); 'x': (y,z); 'z': (x,y)) from a0 to a1"""
    bm = bmesh.new()
    def P(p, a):
        if axis == 'y': return (p[0], a, p[1])
        if axis == 'x': return (a, p[0], p[1])
        return (p[0], p[1], a)
    v0 = [bm.verts.new(P(p, a0)) for p in pts]; v1 = [bm.verts.new(P(p, a1)) for p in pts]
    bm.faces.new(v0); bm.faces.new(v1)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n; bm.faces.new((v0[i], v0[j], v1[j], v1[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=segs, affect='EDGES', profile=0.5)
    bm.normal_update()
    if skip:
        dead = [f for f in bm.faces if any(f.normal.dot(kit.AX[k]) > 0.999 for k in skip)]
        bmesh.ops.delete(bm, geom=dead, context='FACES')
    return kit.finish(name, bm, mat, smooth=smooth, sharp=sharp)

def disc(name, r, mat, uvr=(0, 0, 1, 1), segs=32, z=0.0):
    """flat textured disc in local XY at height z (normal +Z), uv rect mapped onto its bounding square"""
    bm = bmesh.new(); l = bm.loops.layers.uv.new('uv_tex')
    u0, v0, u1, v1 = uvr
    c = bm.verts.new((0, 0, z))
    ring = [bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z)) for j in range(segs)]
    for j in range(segs):
        f = bm.faces.new((c, ring[j], ring[(j + 1) % segs]))
        for loop in f.loops:
            p = loop.vert.co
            loop[l].uv = (u0 + (0.5 + 0.5 * p.x / r) * (u1 - u0), v0 + (0.5 + 0.5 * p.y / r) * (v1 - v0))
    return kit.finish(name, bm, mat)

def grid(name, o, U, V, nu, nv, mat, uvr=(0, 0, 1, 1), fn=None, smooth=True):
    """parametric sheet o + U s + V t (+ fn(s, t)); normal = U x V; uv rect spans the sheet"""
    o, U, V = Vector(o), Vector(U), Vector(V)
    bm = bmesh.new(); l = bm.loops.layers.uv.new('uv_tex')
    u0, v0, u1, v1 = uvr
    vs = {}
    for i in range(nu + 1):
        for j in range(nv + 1):
            s, t = i / nu, j / nv
            p = o + U * s + V * t
            if fn: p = p + Vector(fn(s, t))
            vs[i, j] = bm.verts.new(p)
    for i in range(nu):
        for j in range(nv):
            f = bm.faces.new((vs[i, j], vs[i + 1, j], vs[i + 1, j + 1], vs[i, j + 1]))
            for loop, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                loop[l].uv = (u0 + (u1 - u0) * a / nu, v0 + (v1 - v0) * b / nv)
    return kit.finish(name, bm, mat, smooth=smooth)

def rect_sweep(name, W, H, prof, mat):
    """picture-frame moulding in local XY (normal +Z): prof = [(inset, height), ...] from the outside edge inward"""
    bm = bmesh.new(); loops = []
    for (s, h) in prof:
        w2, h2 = W / 2 - s, H / 2 - s
        loops.append([bm.verts.new(p) for p in ((-w2, -h2, h), (w2, -h2, h), (w2, h2, h), (-w2, h2, h))])
    for A, B in zip(loops, loops[1:]):
        for j in range(4):
            j2 = (j + 1) % 4; bm.faces.new((A[j], A[j2], B[j2], B[j]))
    return kit.finish(name, bm, mat)

def loop_tube(name, pts, r, mat, segs=6, nrm=(0, 0, 1)):
    """closed tube along a closed polyline lying roughly in the plane with normal nrm"""
    pts = [Vector(p) for p in pts]; nrm = Vector(nrm).normalized(); n = len(pts)
    bm = bmesh.new(); rings = []
    for i in range(n):
        t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
        a = t.cross(nrm).normalized(); b = nrm
        rings.append([bm.verts.new(pts[i] + (a * math.cos(2 * math.pi * k / segs) + b * math.sin(2 * math.pi * k / segs)) * r) for k in range(segs)])
    for i in range(n):
        A, B = rings[i], rings[(i + 1) % n]
        for k in range(segs):
            k2 = (k + 1) % segs; bm.faces.new((A[k], A[k2], B[k2], B[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return kit.finish(name, bm, mat, smooth=True)

def rings_mesh(name, rings, mat, smooth=True, close_top=None, flip=False):
    """loft through rings of equal vertex count (lists of points); optional fan cap at the start"""
    bm = bmesh.new(); R_ = [[bm.verts.new(p) for p in ring] for ring in rings]; n = len(rings[0])
    for A, B in zip(R_, R_[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            f = (A[k], A[k2], B[k2], B[k]); bm.faces.new(f[::-1] if flip else f)
    if close_top is not None:
        c = bm.verts.new(close_top)
        for k in range(n):
            f = (c, R_[0][(k + 1) % n], R_[0][k]); bm.faces.new(f[::-1] if flip else f)
    return kit.finish(name, bm, mat, smooth=smooth)

def smooth_path(pts, n=6):
    """Catmull-Rom resample of a polyline"""
    P = [Vector(p) for p in pts]; out = []
    for i in range(len(P) - 1):
        p0 = P[i - 1] if i > 0 else P[i]; p1, p2 = P[i], P[i + 1]; p3 = P[i + 2] if i + 2 < len(P) else P[i + 1]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return out

# ================================================================== materials
def bsdf(m): return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

def gloss(m, coat=0.5, r=0.08):
    mats.setp(bsdf(m), coat=coat, coat_rough=r); return m

WAL = ((0.022, 0.010, 0.005), (0.060, 0.028, 0.012), (0.115, 0.055, 0.024))

def M():
    d = {}
    d['wal_v'] = mats.wood('lounge_walnut_v', 'Z', WAL, rough=0.32, coat=0.45, bmp=0.05)
    d['wal_y'] = mats.wood('lounge_walnut_y', 'Y', WAL, rough=0.30, coat=0.5, bmp=0.05)
    d['wal_x'] = mats.wood('lounge_walnut_x', 'X', WAL, rough=0.32, coat=0.45, bmp=0.05)
    d['oak'] = mats.wood('lounge_oak', 'Y', ((0.10, 0.055, 0.025), (0.22, 0.12, 0.055), (0.34, 0.20, 0.10)), rough=0.45, bmp=0.08)
    d['bent'] = mats.wood('lounge_bentwood', 'Z', ((0.05, 0.022, 0.010), (0.12, 0.055, 0.024), (0.20, 0.10, 0.045)), rough=0.38, coat=0.25)
    d['frame'] = mats.wood('lounge_framewood', 'X', ((0.018, 0.009, 0.005), (0.045, 0.022, 0.010), (0.08, 0.04, 0.018)), rough=0.35, coat=0.3)
    d['ivory'] = mats.noisy('lounge_ivory', (0.58, 0.50, 0.34), (0.68, 0.60, 0.43), rough=0.28, scale=30, rvar=0.1)
    d['ebony'] = gloss(mats.plain('lounge_ebony', (0.010, 0.009, 0.008), rough=0.3), 0.4, 0.15)
    d['brass'] = mats.metal('lounge_brass', (0.78, 0.54, 0.22), rough=0.28, patina=0.45)
    d['brass_d'] = mats.metal('lounge_brass_dull', (0.62, 0.42, 0.17), rough=0.42, patina=0.6)
    d['chrome'] = mats.metal('lounge_chrome', (0.72, 0.72, 0.72), rough=0.16, patina=0.2)
    d['steel'] = gloss(mats.plain('lounge_bluesteel', (0.015, 0.016, 0.022), rough=0.3, metal_=0.8), 0.3)
    d['felt'] = mats.noisy('lounge_felt', (0.16, 0.012, 0.012), (0.24, 0.025, 0.02), rough=0.95, scale=60)
    d['leather'] = mats.leather('lounge_leather', (0.11, 0.025, 0.018))
    d['shade'] = mats.shade_paper('lounge_shade', (0.80, 0.50, 0.22))
    d['fringe'] = mats.shade_paper('lounge_fringe', (0.55, 0.30, 0.10))
    d['pink'] = mats.noisy('lounge_phone_pink', (0.56, 0.20, 0.17), (0.64, 0.25, 0.21), rough=0.33, scale=9, rvar=0.12)
    d['black'] = mats.plain('lounge_blackplastic', (0.012, 0.011, 0.011), rough=0.35)
    d['dark'] = mats.plain('lounge_darkhole', (0.004, 0.003, 0.003), rough=0.8)
    d['paper'] = mats.noisy('lounge_paper', (0.62, 0.56, 0.42), (0.70, 0.64, 0.50), rough=0.85, scale=40)
    d['cream'] = mats.plain('lounge_mount', (0.70, 0.64, 0.50), rough=0.9)
    d['core'] = mats.plain('lounge_mountcore', (0.80, 0.77, 0.68), rough=0.9)
    d['sheet'] = mats.image('lounge_sheet', os.path.join(TEX, 'sheet.png'), rough=0.75)
    d['sheet_g'] = mats.image('lounge_sheet_gloss', os.path.join(TEX, 'sheet.png'), rough=0.3, coat=0.5)
    d['map'] = mats.image('lounge_map', os.path.join(TEX, 'map.jpg'), rough=0.5, coat=0.6)
    d['coat'] = mats.noisy('lounge_raincoat', (0.15, 0.10, 0.05), (0.24, 0.17, 0.085), rough=0.7, scale=6, bmp=0.15, sheen=0.3)
    d['felt_hat'] = mats.noisy('lounge_hatfelt', (0.035, 0.03, 0.026), (0.06, 0.05, 0.04), rough=0.85, scale=20, sheen=0.5)
    d['ribbon'] = mats.plain('lounge_hatband', (0.012, 0.010, 0.010), rough=0.45)
    d['wet'] = gloss(mats.noisy('lounge_umbrella_wet', (0.008, 0.008, 0.010), (0.016, 0.016, 0.02), rough=0.12, scale=80, bmp=0.35), 1.0, 0.02)
    d['umb2'] = mats.noisy('lounge_umbrella_dry', (0.025, 0.06, 0.04), (0.04, 0.085, 0.055), rough=0.75, scale=30, sheen=0.3)
    d['puddle'] = gloss(mats.plain('lounge_puddle', (0.010, 0.010, 0.011), rough=0.04), 1.0, 0.0)
    d['cane'] = mats.wood('lounge_cane', 'Z', ((0.20, 0.11, 0.04), (0.33, 0.19, 0.08), (0.45, 0.29, 0.13)), rough=0.35, coat=0.5)
    d['marble'] = gloss(mats.noisy('lounge_marble', (0.50, 0.47, 0.42), (0.66, 0.63, 0.57), rough=0.25, scale=5, detail=8), 0.5, 0.05)
    d['iron'] = mats.metal('lounge_iron', (0.07, 0.07, 0.07), rough=0.55, patina=0.3)
    d['glaze'] = gloss(mats.noisy('lounge_potglaze', (0.03, 0.075, 0.05), (0.05, 0.12, 0.08), rough=0.22, scale=7), 0.6, 0.05)
    d['soil'] = mats.noisy('lounge_soil', (0.02, 0.013, 0.008), (0.045, 0.03, 0.018), rough=0.95, scale=60, bmp=0.3)
    d['leaf'] = gloss(mats.noisy('lounge_leaf', (0.012, 0.04, 0.016), (0.025, 0.065, 0.028), rough=0.32, scale=25), 0.5, 0.1)
    d['leaf2'] = gloss(mats.noisy('lounge_leaf_new', (0.03, 0.08, 0.025), (0.05, 0.11, 0.035), rough=0.3, scale=25), 0.5, 0.1)
    d['sheath'] = mats.plain('lounge_sheath', (0.30, 0.05, 0.04), rough=0.4)
    d['stem'] = mats.noisy('lounge_stem', (0.05, 0.045, 0.03), (0.09, 0.08, 0.05), rough=0.6, scale=40)
    d['pencil'] = mats.plain('lounge_pencil', (0.42, 0.24, 0.04), rough=0.4)
    d['graphite'] = mats.plain('lounge_graphite', (0.03, 0.03, 0.03), rough=0.3, metal_=0.5)
    d['string'] = mats.plain('lounge_string', (0.55, 0.50, 0.40), rough=0.9)
    d['bookpages'] = mats.noisy('lounge_bookpages', (0.55, 0.49, 0.36), (0.66, 0.60, 0.46), rough=0.9, scale=200, sc3=(1, 1, 30))
    d['dirpages'] = mats.noisy('lounge_dirpages', (0.48, 0.42, 0.30), (0.60, 0.54, 0.40), rough=0.9, scale=300, sc3=(1, 1, 40))
    for i, c in enumerate([(0.034, 0.08, 0.042), (0.16, 0.022, 0.018), (0.52, 0.43, 0.27), (0.43, 0.20, 0.03)]):
        d['book%d' % i] = mats.noisy('lounge_bookcloth%d' % i, tuple(x * 0.8 for x in c), c, rough=0.8, scale=50)
    d['dircover'] = mats.plain('lounge_dircover', (0.60, 0.36, 0.05), rough=0.7)
    # gold leaf name on the walnut nameboard: walnut nodes + an image mask from the sheet
    m = mats.wood('lounge_namegold', 'Y', WAL, rough=0.32, coat=0.45, bmp=0.05)
    if 'patched' not in m:
        nt = m.node_tree; b = bsdf(m)
        uv = mats.N(nt, 'ShaderNodeUVMap'); uv.uv_map = 'uv_tex'
        t = mats.N(nt, 'ShaderNodeTexImage'); t.image = d['sheet'].node_tree.nodes['SRC'].image; mats.L(nt, uv.outputs[0], t.inputs[0])
        mask = mats.N(nt, 'ShaderNodeRGBToBW'); mats.L(nt, t.outputs[0], mask.inputs[0])
        old = b.inputs['Base Color'].links[0].from_socket
        mats.L(nt, mats.mixc(nt, old, (0.80, 0.56, 0.22), mask.outputs[0], 'MIX'), b.inputs['Base Color'])
        mats.L(nt, mask.outputs[0], b.inputs['Metallic'])
        m['patched'] = 1
    d['namegold'] = m
    # lamp bulb: night-only emitter that does not block the assembler's point light sitting inside it
    bm_ = mats.emissive('lounge_bulb', (1.0, 0.72, 0.42), 22, night_only=True)
    if 'patched' not in bm_:
        nt = bm_.node_tree; b = bsdf(bm_); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        tr = mats.N(nt, 'ShaderNodeBsdfTransparent'); lp = mats.N(nt, 'ShaderNodeLightPath'); mx = mats.N(nt, 'ShaderNodeMixShader')
        mats.L(nt, lp.outputs['Is Shadow Ray'], mx.inputs[0]); mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2])
        mats.L(nt, mx.outputs[0], out.inputs[0]); bm_['patched'] = 1
    d['bulb'] = bm_
    d['enamel'] = mats.plain('lounge_enamel', (0.70, 0.64, 0.50), rough=0.35)
    t_ = mats.emissive('lounge_pianolamp_tube', (1.0, 0.74, 0.46), 8, night_only=True)
    if 'patched' not in t_:
        nt = t_.node_tree; b = bsdf(t_); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        tr = mats.N(nt, 'ShaderNodeBsdfTransparent'); lp = mats.N(nt, 'ShaderNodeLightPath'); mx = mats.N(nt, 'ShaderNodeMixShader')
        mats.L(nt, lp.outputs['Is Shadow Ray'], mx.inputs[0]); mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2])
        mats.L(nt, mx.outputs[0], out.inputs[0]); t_['patched'] = 1
    d['bulb_s'] = t_
    return d

# ================================================================== the piano
def piano(m):
    P = layout.PIANO; X0, X1, Y0, Y1, TOP = P['x0'] + 0.002, P['x1'], P['y0'], P['y1'], P['top_z']
    kx, ky, kz = layout.INTERACTIVE['piano_keys'][1]
    KL = layout.INTERACTIVE['piano_keys'][2][1]                      # keyboard length (1.25)
    KY0, KY1 = ky - KL / 2, ky + KL / 2
    CT = 0.045                                                       # cheek thickness
    with kit.props(td=1.0):
        # cheeks with the key arms
        prof = [(X0, 0.075), (X1, 0.075), (X1, 0.62), (-2.625, 0.62), (-2.603, 0.64), (-2.603, 0.765), (-2.625, 0.79),
                (-2.78, 0.80), (X1, 0.83), (X1, TOP - 0.03), (X0, TOP - 0.03)]
        for i, (a, b) in enumerate(((Y0, Y0 + CT), (Y1 - CT, Y1))):
            with kit.props(td=0.75 if i == 0 else 0.6):
                prism('piano_cheek%d' % i, prof, 'y', a, b, m['wal_v'], bevel=0.004, segs=2, skip=['-x'])
        # lid + cornice
        kit.box('piano_lid', X0, -2.775, Y0 - 0.012, Y1 + 0.012, TOP - 0.03, TOP, m['wal_y'], bevel=0.008, segs=3, skip='-x -z')
        kit.box('piano_cornice', -2.86, -2.80, Y0 + CT, Y1 - CT, TOP - 0.065, TOP - 0.03, m['wal_y'], bevel=0.006, segs=2, skip='-x')
    with kit.props(td=0.4):
        kit.box('piano_plinth', X0, -2.795, Y0, Y1, 0.0, 0.075, m['wal_y'], bevel=0.004, skip='-x -z')
    with kit.props(td=0.8):
        # lower board + two raised fields
        kit.box('piano_lowerboard', -2.97, -2.815, Y0 + CT, Y1 - CT, 0.075, 0.655, m['wal_v'], skip='-x -z +z')
        for i, (a, b) in enumerate(((-1.40, -0.79), (-0.71, -0.10))):
            kit.box('piano_field%d' % i, -2.817, -2.806, a, b, 0.15, 0.56, m['wal_v'], bevel=0.005, segs=2, skip='-x')
            with kit.xform(basis((-2.8155, (a + b) / 2, 0.355), (0, 1, 0), (0, 0, 1))):
                rect_sweep('piano_fieldmould%d' % i, b - a + 0.05, 0.46, [(0, 0), (0, 0.006), (0.008, 0.01), (0.016, 0.006), (0.02, 0.0)], m['wal_v'])
        # turned legs + toe blocks
        for i, yc in enumerate((Y0 + CT / 2, Y1 - CT / 2)):
            kit.lathe('piano_leg%d' % i, [(0.0, 0.075), (0.026, 0.075), (0.028, 0.11), (0.02, 0.14), (0.026, 0.20), (0.034, 0.30), (0.028, 0.42),
                                          (0.02, 0.50), (0.026, 0.56), (0.03, 0.60), (0.03, 0.62), (0.0, 0.62)], m['wal_v'], segs=12, center=(-2.645, yc, 0))
            kit.box('piano_toe%d' % i, -2.80, -2.6, yc - 0.032, yc + 0.032, 0.0, 0.075, m['wal_v'], bevel=0.008, segs=2, skip='-z')
    with kit.props(td=1.2):
        # keybed, key blocks, key slip, nameboard, folded fallboard
        with kit.props(td=0.4):
            kit.box('piano_keybed', -2.84, -2.625, KY0 - 0.01, KY1 + 0.01, 0.655, 0.72, m['wal_x'], skip='-x +z')
        for i, (a, b) in enumerate(((Y0 + CT, KY0 - 0.002), (KY1 + 0.002, Y1 - CT))):
            kit.box('piano_keyblock%d' % i, -2.845, -2.615, a, b, 0.70, 0.79, m['wal_x'], bevel=0.008, segs=3, skip='-x -z')
        kit.box('piano_keyslip', -2.645, -2.622, KY0 - 0.004, KY1 + 0.004, 0.665, 0.733, m['wal_x'], bevel=0.003, segs=2, skip='-x -z')
        kit.box('piano_keyfelt', -2.815, -2.797, KY0, KY1, 0.72, 0.747, m['felt'], skip='-x -z')
        kit.box('piano_nameboard', -2.85, -2.815, KY0, KY1, 0.72, 0.825, m['wal_y'], skip='-x -z')
        kit.box('piano_fallboard', -2.88, -2.815, KY0 - 0.002, KY1 + 0.002, 0.825, 0.872, m['wal_y'], bevel=0.012, segs=3, skip='-x')
    with kit.props(td=3.0):
        nw = 0.60; nh = nw * 96 / 608
        kit.quad('piano_name', [(-2.8145, ky - nw / 2, 0.773 - nh / 2), (-2.8145, ky + nw / 2, 0.773 - nh / 2),
                                (-2.8145, ky + nw / 2, 0.773 + nh / 2), (-2.8145, ky - nw / 2, 0.773 + nh / 2)], m['namegold'], uv=_quv(R('name')))
    with kit.props(td=1.0):
        # upper front with a moulded panel each side, music desk ledge
        kit.box('piano_upper', -3.0, -2.835, Y0 + CT, Y1 - CT, 0.872, TOP - 0.065, m['wal_v'], skip='-x -z +z')
        for i, (a, b) in enumerate(((-1.42, -0.08),)):
            with kit.xform(basis((-2.835, (a + b) / 2, 1.04), (0, 1, 0), (0, 0, 1))):
                rect_sweep('piano_uppermould%d' % i, b - a, 0.25, [(0, 0), (0, 0.004), (0.006, 0.009), (0.014, 0.007), (0.018, 0.0)], m['wal_v'])
        kit.box('piano_desk', -2.84, -2.768, ky - 0.42, ky + 0.42, 0.885, 0.905, m['wal_x'], bevel=0.005, segs=2, skip='-x')
        kit.box('piano_desklip', -2.78, -2.766, ky - 0.42, ky + 0.42, 0.905, 0.918, m['wal_x'], bevel=0.003, segs=1, skip='-z')
    # hand-copied sheets leaning on the desk, slightly fanned and bowed
    with kit.props(td=2.0):
        for i, (yc, rot, reg) in enumerate(((ky - 0.235, 1.5, 'music0'), (ky, -0.5, 'music1'), (ky + 0.232, -2.0, 'music2'))):
            w, h = 0.228, 0.30
            lean = math.radians(9.5)
            o = Vector((-2.789 - 0.0005 * i, yc, 0.906))
            up = Vector((-math.sin(lean), 0, math.cos(lean)))
            right = Vector((0, 1, 0))
            with kit.xform(T(*o) @ Rx(rot) @ T(*(-o))):
                grid('piano_sheet%d' % i, o - right * w / 2, right * w, up * h, 6, 6, m['sheet'], R(reg),
                     fn=lambda s, t, i=i: (0.006 * math.sin(math.pi * s) * (0.4 + t) + 0.0012 * i, 0, 0))
    # candle sconces (brass swing arms with empty cups)
    with kit.props(td=1.2):
        for i, yc in enumerate((-1.32, -0.18)):
            with kit.xform(T(-2.835, yc, 1.04) @ Ry(90)):
                kit.lathe('sconce_plate%d' % i, [(0, 0.0), (0.026, 0.0), (0.024, 0.006), (0.012, 0.01), (0, 0.011)], m['brass'], segs=16)
            s = 1 if i == 0 else -1
            kit.tube('sconce_arm%d' % i, smooth_path([(-2.83, yc, 1.04), (-2.80, yc, 1.03), (-2.77, yc - 0.012 * s, 1.035), (-2.745, yc - 0.02 * s, 1.055)], 3),
                     0.005, m['brass'], segs=8)
            kit.lathe('sconce_cup%d' % i, [(0.0, -0.012), (0.01, -0.012), (0.034, -0.002), (0.036, 0.002), (0.012, 0.004), (0.011, 0.03),
                                           (0.015, 0.034), (0.009, 0.034), (0.008, 0.012), (0, 0.012)], m['brass'], segs=12,
                      center=(-2.745, yc - 0.02 * s, 1.067))
    # pedals
    with kit.props(td=1.5):
        kit.box('pedal_plate', -2.799, -2.792, ky - 0.11, ky + 0.11, 0.018, 0.064, m['brass_d'], bevel=0.002, segs=1, skip='-x')
        for i, dy in enumerate((-0.07, 0.0, 0.07)):
            with kit.xform(T(0, ky + dy, 0)):
                prism('pedal%d' % i, [(-2.80, -0.011), (-2.72, -0.012), (-2.69, -0.016), (-2.675, -0.012), (-2.672, 0.0), (-2.675, 0.012),
                                      (-2.69, 0.016), (-2.72, 0.012), (-2.80, 0.011)], 'z', 0.034, 0.045, m['brass'], bevel=0.002, segs=1)

def _quv(r):
    u0, v0, u1, v1 = r
    return ((u0, v0), (u1, v0), (u1, v1), (u0, v1))

def piano_keys(m):
    kx, ky, kz = layout.INTERACTIVE['piano_keys'][1]
    L = layout.INTERACTIVE['piano_keys'][2][1]
    n = 52; ww = L / n; y0 = ky - L / 2
    xf, xb = kx + 0.0775, kx - 0.0775                                 # front / back of the white keys
    names = 'ABCDEFG'
    with kit.interactive('piano_keys', origin=(kx, ky, kz), td=1.6):
        for i in range(n):
            a = y0 + i * ww + 0.0006; b = y0 + (i + 1) * ww - 0.0006
            c_, tz = 0.0013, kz + 0.022
            prism('wkey%d' % i, [(a, kz), (b, kz), (b, tz - c_), (b - c_, tz), (a + c_, tz), (a, tz - c_)], 'x', xb, xf, m['ivory'], skip=['-z', '-x'])
            if names[i % 7] in 'ACDFG' and i < n - 1:
                c = y0 + (i + 1) * ww
                prism('bkey%d' % i, [(c - 0.0068, kz + 0.012), (c + 0.0068, kz + 0.012), (c + 0.0068, kz + 0.029), (c + 0.0048, kz + 0.034),
                                     (c - 0.0048, kz + 0.034), (c - 0.0068, kz + 0.029)], 'x', xb, xb + 0.095, m['ebony'], skip=['-z', '-x'])

def piano_top(m):
    TOP = layout.PIANO['top_z']
    # stack of music books (cover cells of the 'books' strip)
    u0, v0, u1, v1 = R('books'); q = (u1 - u0) / 4
    z = TOP
    with kit.props(td=1.4):
        for i, (cx, cy, rot, w, l, th) in enumerate(((-3.12, -1.255, 3, 0.235, 0.31, 0.016), (-3.115, -1.26, -2, 0.225, 0.30, 0.012),
                                                     (-3.125, -1.25, 6, 0.23, 0.305, 0.02), (-3.11, -1.265, -4.5, 0.215, 0.29, 0.010))):
            k = (0, 2, 1, 3)[i]
            with kit.xform(T(cx, cy, z) @ Rz(rot)):
                l, w = w, l                                                       # long side along y: the cover reads landscape from the room
                kit.box('book_cover%d' % i, -l / 2, l / 2, -w / 2, w / 2, 0, th, m['book%d' % k], bevel=0.0015, segs=1, skip='-z')
                with kit.props(td=0.8):
                    kit.box('book_pages%d' % i, -l / 2 + 0.004, l / 2 - 0.006, -w / 2 + 0.003, w / 2 - 0.004, 0.0015, th - 0.0015, m['bookpages'], skip='-z +z')
                uv = ((u0 + k * q, v0), (u0 + (k + 1) * q, v0), (u0 + (k + 1) * q, v1), (u0 + k * q, v1))
                # cover image, read from the front of the piano (+x is down the page)
                kit.quad('book_face%d' % i, [(l / 2 - 0.004, -w / 2 + 0.003, th + 0.0004), (l / 2 - 0.004, w / 2 - 0.003, th + 0.0004),
                                             (-l / 2 + 0.004, w / 2 - 0.003, th + 0.0004), (-l / 2 + 0.004, -w / 2 + 0.003, th + 0.0004)], m['sheet'],
                         uv=uv)
            z += th
    # metronome, turned toward the room
    with kit.props(td=1.6), kit.xform(T(-2.955, -1.02, TOP) @ Rz(-22)):
        with kit.xform(Rz(45)):
            kit.lathe('metro_plinth', [(0.0, 0.0), (0.082, 0.0), (0.082, 0.016), (0.074, 0.02), (0.0, 0.02)], m['wal_v'], segs=4, smooth=False)
            kit.lathe('metro_body', [(0.068, 0.02), (0.024, 0.215), (0.012, 0.226), (0.0, 0.228)], m['wal_v'], segs=4, smooth=False)
        # front face: dark slot, scale strip, brass pendulum (stopped, upright)
        b0, b1 = Vector((0.048, 0, 0.02)), Vector((0.017, 0, 0.215))
        up = (b1 - b0).normalized()
        with kit.xform(basis(b0 + (b1 - b0) * 0.5 + Vector((0.0015, 0, 0)), (0, 1, 0), up)):
            Lf = (b1 - b0).length
            kit.box('metro_slot', -0.012, 0.012, -Lf * 0.42, Lf * 0.46, 0.0, 0.001, m['dark'])
            kit.box('metro_scale', -0.004, 0.004, -Lf * 0.2, Lf * 0.42, 0.001, 0.0018, m['paper'])
            kit.box('metro_rod', -0.0012, 0.0012, -Lf * 0.42, Lf * 0.52, 0.002, 0.0035, m['brass'])
            kit.box('metro_weight', -0.008, 0.008, Lf * 0.12, Lf * 0.12 + 0.016, 0.002, 0.009, m['brass'], bevel=0.0015, segs=1)
    # small framed photograph leaning against the wall
    with kit.props(td=2.0):
        o = Vector((-3.335, -1.40, TOP + 0.003))
        lean = math.radians(13)
        up = Vector((-math.sin(lean), 0.0, math.cos(lean))); right = Vector((math.sin(math.radians(8)), math.cos(math.radians(8)), 0))
        fw, fh = 0.135, 0.175
        with kit.xform(basis(o + up * fh / 2, right, up)):
            rect_sweep('photo_frame', fw, fh, [(0, -0.006), (0, 0.006), (0.004, 0.009), (0.010, 0.008), (0.014, 0.004)], m['brass'])
            with kit.props(td=0.3): kit.box('photo_back', -fw / 2, fw / 2, -fh / 2, fh / 2, -0.008, -0.006, m['frame'])
            pw, ph = fw - 0.028, fh - 0.028
            kit.quad('photo_print', [(-pw / 2, -ph / 2, 0.003), (pw / 2, -ph / 2, 0.003), (pw / 2, ph / 2, 0.003), (-pw / 2, ph / 2, 0.003)], m['sheet'], uv=_quv(R('photo')))

# ================================================================== brass piano lamp clipped over the music desk
PLAMP = (-2.712, -0.80, 1.318)            # axis centre of its trough shade = where its little light sits

def piano_lamp(m):
    TOP = layout.PIANO['top_z']
    lx, ly, lz = PLAMP
    bx, by = -3.30, -0.985
    with kit.props(td=1.4):
        with kit.xform(T(bx, by, TOP) @ Matrix.Diagonal((1.0, 1.45, 1.0, 1.0))):
            kit.lathe('plamp_base', [(0, 0), (0.05, 0), (0.05, 0.006), (0.042, 0.016), (0.02, 0.022), (0.012, 0.03), (0, 0.03)], m['brass'], segs=20)
        arm = smooth_path([(bx, by, TOP + 0.025), (bx, by + 0.005, TOP + 0.10), (bx + 0.03, by + 0.03, TOP + 0.15), (-3.10, -0.93, TOP + 0.163),
                           (-2.86, -0.84, TOP + 0.155), (-2.745, -0.805, TOP + 0.125), (lx - 0.004, ly, lz + 0.036)], 3)
        kit.tube('plamp_arm', arm, 0.0045, m['brass'], segs=6)
        kit.lathe('plamp_knuckle', [(0.0, -0.01), (0.009, -0.006), (0.009, 0.006), (0.0, 0.01)], m['brass'], segs=10, center=(lx - 0.004, ly, lz + 0.036))
        # trough shade: brass outside, cream enamel inside, open toward the music desk and keys
        r, L = 0.034, 0.30
        f0, f1 = math.radians(-55), math.radians(185)
        arc = lambda rr, s, t, a0=f0, a1=f1: (rr * math.cos(a0 + (a1 - a0) * t), 0.0, rr * math.sin(a0 + (a1 - a0) * t))
        grid('plamp_shade', (lx, ly - L / 2, lz), (0, L, 0), (0, 0, 0), 1, 14, m['brass'], fn=lambda s, t: arc(r, s, t))
        grid('plamp_shade_in', (lx, ly - L / 2, lz), (0, L, 0), (0, 0, 0), 1, 14, m['enamel'], fn=lambda s, t: arc(r - 0.0015, s, 1 - t))
        for i, (yy, sgn) in enumerate(((ly - L / 2, -1), (ly + L / 2, 1))):
            bm = bmesh.new(); vs = [bm.verts.new((lx, yy, lz))]
            vs += [bm.verts.new(Vector((lx, yy, lz)) + Vector(arc(r, 0, k / 10))) for k in range(11)]
            f = bm.faces.new(vs); bm.normal_update()
            if f.normal.y * sgn < 0: f.normal_flip()
            kit.finish('plamp_cap%d' % i, bm, m['brass'])
        with kit.xform(T(lx, ly, lz) @ Rx(90)):
            kit.cyl('plamp_tube', 0, 0, -L / 2 + 0.02, L / 2 - 0.02, 0.0075, m['bulb_s'], segs=10)

# ================================================================== piano stool
def stool(m):
    cx, cy = -2.50, layout.INTERACTIVE['piano_keys'][1][1]
    with kit.props(td=0.9):
        for k in range(4):
            a = math.radians(45 + 90 * k); d = Vector((math.cos(a), math.sin(a), 0))
            pts = [Vector((cx, cy, 0)) + d * r + Vector((0, 0, z)) for r, z in ((0.045, 0.34), (0.08, 0.27), (0.13, 0.14), (0.175, 0.03), (0.19, 0.0))]
            kit.tube('stool_leg%d' % k, smooth_path(pts, 2), 0.016, m['wal_v'], segs=6)
        kit.lathe('stool_hub', [(0, 0.27), (0.05, 0.27), (0.058, 0.29), (0.05, 0.33), (0.056, 0.36), (0.044, 0.385), (0.0, 0.385)], m['wal_v'], segs=16, center=(cx, cy, 0))
        prof = [(0, 0.385)]
        for i in range(5):
            prof += [(0.019, 0.385 + i * 0.014), (0.023, 0.385 + i * 0.014 + 0.007)]
        prof += [(0.019, 0.46), (0, 0.46)]
        kit.lathe('stool_screw', prof, m['brass_d'], segs=12, center=(cx, cy, 0))
        kit.lathe('stool_base', [(0, 0.452), (0.15, 0.452), (0.168, 0.46), (0.17, 0.472), (0.162, 0.48), (0.0, 0.48)], m['wal_v'], segs=32, center=(cx, cy, 0))
        kit.lathe('stool_cushion', [(0.158, 0.478), (0.165, 0.49), (0.162, 0.51), (0.145, 0.522), (0.10, 0.528), (0.0, 0.53)], m['leather'], segs=32, center=(cx, cy, 0))
        kit.lathe('stool_piping', [(0.163, 0.478), (0.168, 0.482), (0.166, 0.486), (0.160, 0.487)], m['brass_d'], segs=32, center=(cx, cy, 0))

# ================================================================== floor lamp
def floor_lamp(m):
    x, y = layout.FLOOR_LAMP
    with kit.props(td=1.0):
        kit.lathe('lamp_base', [(0, 0), (0.15, 0), (0.15, 0.012), (0.13, 0.03), (0.06, 0.045), (0.025, 0.06), (0.016, 0.08), (0, 0.08)], m['brass'], segs=24, center=(x, y, 0))
        kit.cyl('lamp_stem', x, y, 0.08, 1.33, 0.011, m['brass'], segs=12, cap='')
        kit.lathe('lamp_knuckle', [(0.011, 0.68), (0.017, 0.69), (0.017, 0.72), (0.011, 0.73)], m['brass'], segs=12, center=(x, y, 0))
        kit.lathe('lamp_socket', [(0.011, 1.33), (0.02, 1.335), (0.022, 1.36), (0.018, 1.41), (0.012, 1.415)], m['brass'], segs=16, center=(x, y, 0))
        # harp + finial
        kit.tube('lamp_harp', smooth_path([(x, y - 0.08, 1.36), (x, y - 0.11, 1.45), (x, y - 0.07, 1.58), (x, y, 1.61), (x, y + 0.07, 1.58), (x, y + 0.11, 1.45), (x, y + 0.08, 1.36)], 3),
                 0.004, m['brass'], segs=6)
        kit.lathe('lamp_finial', [(0, 1.60), (0.012, 1.605), (0.016, 1.625), (0.008, 1.645), (0, 1.65)], m['brass'], segs=12, center=(x, y, 0))
    with kit.props(td=1.2):
        out = [(0.24, 1.33), (0.236, 1.36), (0.216, 1.43), (0.188, 1.51), (0.162, 1.57), (0.15, 1.60)]
        kit.lathe('lamp_shade', out, m['shade'], segs=32, center=(x, y, 0))
        with kit.props(td=0.5): kit.lathe('lamp_shade_in', [(r - 0.004, z) for r, z in reversed(out)], m['shade'], segs=32, center=(x, y, 0))
        kit.lathe('lamp_trim_lo', [(0.242, 1.327), (0.244, 1.333), (0.242, 1.345), (0.238, 1.345)], m['fringe'], segs=32, center=(x, y, 0))
        kit.lathe('lamp_trim_hi', [(0.152, 1.592), (0.154, 1.60), (0.150, 1.606), (0.146, 1.606)], m['fringe'], segs=32, center=(x, y, 0))
        nf = 84
        for k in range(nf):
            a = 2 * math.pi * (k + 0.5) / nf; c, s = math.cos(a), math.sin(a)
            ln = 0.05 + 0.005 * math.sin(k * 2.3) + 0.003 * math.sin(k * 0.7)
            kit.tube('lamp_fringe%d' % k, [(x + 0.2415 * c, y + 0.2415 * s, 1.334), (x + 0.2445 * c, y + 0.2445 * s, 1.334 - ln)], 0.0017, m['fringe'], segs=3, caps=False, smooth=False)
        kit.lathe('lamp_bulb', [(0, 1.405), (0.012, 1.41), (0.03, 1.44), (0.031, 1.46), (0.02, 1.485), (0, 1.492)], m['bulb'], segs=16, center=(x, y, 0))

# ================================================================== pay phone, shelf, directory, memo
def phone_corner(m):
    px, py, pz = layout.INTERACTIVE['phone'][1]
    WX = -3.398
    with kit.props(td=1.0):
        kit.box('phone_shelf', WX, -3.12, py - 0.25, py + 0.25, pz - 0.032, pz, m['oak'], bevel=0.004, segs=2, skip='-x')
        for i, yb in enumerate((py - 0.19, py + 0.19)):
            prism('phone_bracket%d' % i, [(WX, pz - 0.032), (-3.15, pz - 0.032), (-3.17, pz - 0.05), (-3.24, pz - 0.09), (-3.32, pz - 0.15), (WX, pz - 0.17)],
                  'y', yb - 0.011, yb + 0.011, m['oak'], bevel=0.002, segs=1, skip=['-x'])
    # ---- the telephone itself (interactive)
    with kit.interactive('phone', origin=(px, py, pz), td=2.4):
        X = lambda dx: px + dx
        body = [(X(-0.117), pz), (X(0.096), pz), (X(0.106), pz + 0.012), (X(0.106), pz + 0.05), (X(0.064), pz + 0.163), (X(0.046), pz + 0.178), (X(-0.117), pz + 0.178)]
        prism('phone_body', body, 'y', py - 0.105, py + 0.105, m['pink'], bevel=0.009, segs=3, skip=['-x'], smooth=True, sharp=40)
        with kit.props(td=0.5):
            kit.box('phone_foot', X(-0.117), X(0.10), py - 0.1, py + 0.1, pz, pz + 0.006, m['black'], skip='-x -z +z')
        # cradle forks
        for i, s in enumerate((-1, 1)):
            yc = py + s * 0.068
            with kit.xform(T(0, yc, pz + 0.174)):
                prism('phone_fork%d' % i, [(-0.022, 0.0), (0.022, 0.0), (0.024, 0.028), (0.013, 0.028), (0.007, 0.018), (-0.007, 0.018), (-0.013, 0.028), (-0.024, 0.028)],
                      'x', X(-0.06), X(0.022), m['pink'], bevel=0.003, segs=1)
            kit.cyl('phone_hook%d' % i, X(-0.02), yc, pz + 0.17, pz + 0.19, 0.006, m['chrome'], segs=10)
        # handset on the cradle, lying along Y
        hz = pz + 0.212
        hx = X(-0.019)
        kit.tube('handset_grip', smooth_path([(hx, py - 0.08, hz + 0.004), (hx, py - 0.045, hz + 0.017), (hx, py, hz + 0.021), (hx, py + 0.045, hz + 0.017), (hx, py + 0.08, hz + 0.004)], 3),
                 0.017, m['pink'], segs=12, radii=None)
        for i, s in enumerate((-1, 1)):
            cup = [(0, -0.026), (0.024, -0.026), (0.032, -0.02), (0.034, -0.01), (0.029, 0.004), (0.016, 0.014), (0.0, 0.017)]
            kit.lathe('handset_cup%d' % i, cup, m['pink'], segs=16, center=(hx, py + s * 0.088, hz))
        # sloped front: dial + coin slot plate
        a0, a1 = Vector((X(0.106), py, pz + 0.05)), Vector((X(0.064), py, pz + 0.163))
        up = (a1 - a0).normalized()
        mid = a0 + (a1 - a0) * 0.47 + Vector((0.002, 0, 0))
        with kit.xform(basis(mid + Vector((0, -0.022, 0)), (0, 1, 0), up)):
            with kit.props(td=3.5):
                disc('phone_dial', 0.047, m['sheet_g'], R('dial'), segs=32, z=0.004)
            kit.lathe('phone_dialrim', [(0.045, 0.0), (0.05, 0.0), (0.051, 0.004), (0.049, 0.0065), (0.046, 0.0055)], m['chrome'], segs=32)
            kit.lathe('phone_dialcap', [(0.0, 0.0065), (0.009, 0.0062), (0.006, 0.0085), (0.0, 0.0092)], m['chrome'], segs=12)
            a = math.radians(122)
            kit.tube('phone_fingerstop', [(0.033 * math.sin(a), 0.033 * math.cos(a), 0.007), (0.052 * math.sin(a), 0.052 * math.cos(a), 0.007)], 0.0022, m['chrome'], segs=6)
        with kit.xform(basis(a0 + (a1 - a0) * 0.62 + Vector((0.002, 0.07, 0)), (0, 1, 0), up)):
            kit.box('phone_coinplate', -0.016, 0.016, -0.022, 0.022, 0.0, 0.004, m['chrome'], bevel=0.002, segs=1)
            kit.box('phone_coinslot', -0.0025, 0.0025, -0.014, 0.014, 0.003, 0.0045, m['dark'])
        # coin return cup + instruction card on the front
        fx = X(0.106)
        kit.box('phone_return', fx - 0.004, fx + 0.008, py + 0.042, py + 0.088, pz + 0.012, pz + 0.04, m['chrome'], bevel=0.003, segs=2)
        kit.box('phone_returnhole', fx + 0.0075, fx + 0.0086, py + 0.048, py + 0.082, pz + 0.022, pz + 0.036, m['dark'])
        lw, lh = 0.068, 0.034
        with kit.props(td=3.0):
            kit.quad('phone_label', [(fx + 0.0008, py - 0.088, pz + 0.012), (fx + 0.0008, py - 0.088 + lw, pz + 0.012),
                                     (fx + 0.0008, py - 0.088 + lw, pz + 0.012 + lh), (fx + 0.0008, py - 0.088, pz + 0.012 + lh)], m['sheet'], uv=_quv(R('label')))
        # coiled cord: from the mouthpiece end down beside the phone, a loop resting on the shelf, into the body side
        path = smooth_path([(hx + 0.01, py - 0.098, hz - 0.02), (X(0.02), py - 0.125, pz + 0.15), (X(0.06), py - 0.135, pz + 0.07), (X(0.07), py - 0.14, pz + 0.018),
                            (X(0.02), py - 0.155, pz + 0.014), (X(-0.03), py - 0.13, pz + 0.03), (X(-0.06), py - 0.106, pz + 0.05)], 6)
        pts = []
        pitch = 0.007
        acc = 0.0; nrm = None
        for i, p in enumerate(path):
            t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
            if nrm is None: nrm = t.cross(Vector((0, 0, 1))).normalized()
            nrm = (nrm - t * nrm.dot(t)).normalized(); b = t.cross(nrm)
            if i: acc += (path[i] - path[i - 1]).length
            if i == len(path) - 1: break
            seg = (path[i + 1] - p).length; k = max(1, int(seg / pitch * 6))
            for j in range(k):
                pp = p + (path[i + 1] - p) * (j / k)
                ang = 2 * math.pi * (acc + seg * j / k) / pitch
                pts.append(pp + (nrm * math.cos(ang) + b * math.sin(ang)) * 0.0065)
        kit.tube('phone_cord', pts, 0.0021, m['pink'], segs=3)
    # ---- directory hanging on a chain under the shelf
    with kit.props(td=1.4):
        bx0, bx1, by0, by1, bz0, bz1 = WX, -3.364, py - 0.11, py + 0.11, pz - 0.47, pz - 0.18
        with kit.props(td=0.5): kit.box('dir_block', bx0, bx1 - 0.002, by0 + 0.003, by1 - 0.003, bz0 + 0.002, bz1 - 0.002, m['dirpages'], skip='-x')
        kit.box('dir_coverback', bx0, bx0 + 0.003, by0, by1, bz0, bz1, m['dircover'], skip='-x')
        kit.box('dir_coverfront', bx1 - 0.003, bx1, by0, by1, bz0, bz1, m['dircover'], skip='-x')
        kit.box('dir_spine', bx0, bx1, by0 - 0.003, by0, bz0, bz1, m['dircover'], bevel=0.0015, segs=1)
        with kit.props(td=1.8):
            kit.quad('dir_face', [(bx1 + 0.0004, by0, bz0), (bx1 + 0.0004, by1, bz0), (bx1 + 0.0004, by1, bz1), (bx1 + 0.0004, by0, bz1)], m['sheet'], uv=_quv(R('directory')))
        # chain from a screw-eye under the shelf to the punched corner of the book
        top = Vector((-3.372, by0 + 0.03, pz - 0.034)); bot = Vector((-3.381, by0 + 0.022, bz1 - 0.012))
        nl = 7; d = (bot - top) / nl
        for k in range(nl):
            c = top + d * (k + 0.5); ax = d.normalized()
            side = Vector((1, 0, 0)) if k % 2 else Vector((0, 1, 0))
            side = (side - ax * side.dot(ax)).normalized()
            lp = [c + ax * (0.011 * math.cos(2 * math.pi * j / 6)) + side * (0.0055 * math.sin(2 * math.pi * j / 6)) for j in range(6)]
            loop_tube('dir_chain%d' % k, lp, 0.0013, m['brass_d'], segs=4, nrm=ax.cross(side))
        kit.cyl('dir_eye', top.x, top.y, top.z + 0.0, pz - 0.032, 0.004, m['brass_d'], segs=8)
    # ---- memo pad + a stub of pencil on a string, on the shelf
    with kit.props(td=2.2):
        mx0, mx1, my0, my1 = -3.372, -3.267, py - 0.235, py - 0.16
        kit.box('memo_block', mx0, mx1, my0, my1, pz, pz + 0.009, m['paper'], skip='-z')
        kit.quad('memo_face', [(mx1, my0, pz + 0.0094), (mx1, my1, pz + 0.0094), (mx0, my1, pz + 0.0094), (mx0, my0, pz + 0.0094)], m['sheet'],
                 uv=((R('memo')[0], R('memo')[1]), (R('memo')[2], R('memo')[1]), (R('memo')[2], R('memo')[3]), (R('memo')[0], R('memo')[3])))
    with kit.props(td=1.2):
        pc = Vector((-3.30, py - 0.195, pz + 0.0135))
        with kit.xform(T(*pc) @ Rz(62) @ Ry(90)):
            kit.cyl('pencil_body', 0, 0, -0.026, 0.02, 0.0042, m['pencil'], segs=6, smooth=False)
            kit.cyl('pencil_tip', 0, 0, 0.02, 0.032, 0.0042, m['cane'], segs=6, r1=0.0012, smooth=False)
            kit.cyl('pencil_lead', 0, 0, 0.0318, 0.0345, 0.0012, m['graphite'], segs=6, r1=0.0003, smooth=False)
        tail = pc + Vector((math.cos(math.radians(62)), math.sin(math.radians(62)), 0)) * -0.026
        kit.tube('pencil_string', smooth_path([tail, (-3.26, py - 0.235, pz + 0.002), (-3.18, py - 0.226, pz + 0.002), (-3.125, py - 0.222, pz - 0.004),
                                               (-3.118, py - 0.222, pz - 0.045), (-3.119, py - 0.232, pz - 0.016)], 4), 0.0009, m['string'], segs=4)
        kit.cyl('pencil_eye', -3.12, py - 0.232, pz - 0.022, pz - 0.012, 0.003, m['brass_d'], segs=8)

# ================================================================== framed chart above the phone
def mapframe(m):
    o = layout.INTERACTIVE['mapframe'][1]
    W, H = layout.INTERACTIVE['mapframe'][2][1], layout.INTERACTIVE['mapframe'][2][2]
    with kit.interactive('mapframe', origin=o, td=1.4):
        with kit.xform(basis((-3.399, o[1], o[2]), (0, 1, 0), (0, 0, 1))):
            rect_sweep('map_frame', W, H, [(0, 0), (0, 0.022), (0.004, 0.028), (0.012, 0.031), (0.022, 0.028), (0.03, 0.022), (0.034, 0.016), (0.036, 0.008)], m['frame'])
            rect_sweep('map_slip', W, H, [(0.036, 0.008), (0.038, 0.009), (0.040, 0.007)], m['brass_d'])
            rect_sweep('map_mount', W, H, [(0.040, 0.007), (0.068, 0.007)], m['cream'])
            rect_sweep('map_core', W, H, [(0.068, 0.007), (0.071, 0.004)], m['core'])
            mw, mh = W / 2 - 0.071, H / 2 - 0.071
            with kit.props(td=6.0):
                kit.quad('map_chart', [(-mw, -mh, 0.004), (mw, -mh, 0.004), (mw, mh, 0.004), (-mw, mh, 0.004)], m['map'])

# ================================================================== wall clock above the stair door (stopped at 3:07)
def clock(m):
    cx, cy, cz = layout.CLOCK
    wy = layout.DOOR['y'] - 0.001
    with kit.props(td=1.4), kit.xform(T(cx, wy, cz) @ Rx(90)):
        prof = [(0.150, 0.0), (0.155, 0.006), (0.157, 0.02), (0.153, 0.03), (0.150, 0.031), (0.150, 0.040), (0.146, 0.046), (0.140, 0.047),
                (0.136, 0.044), (0.135, 0.032), (0.134, 0.022)]
        kit.lathe('clock_case', prof, [m['wal_x'], m['brass']], segs=32, mi=[0, 0, 0, 0, 1, 1, 1, 1, 1, 1], sharp=50)
        with kit.props(td=3.2):
            disc('clock_face', 0.134, m['sheet_g'], R('clock'), segs=40, z=0.022)
    # hands: each its own interactive mesh, pivot at the centre, modelled pointing at 3:07:41
    h, mi, s = 3, 7, 41
    spec = [('clock_hour', (h % 12 + mi / 60) * 30, m['steel'],
             [(-0.0035, -0.02), (0.0035, -0.02), (0.004, 0.0), (0.0028, 0.044), (0.011, 0.051), (0.0045, 0.064), (0.0, 0.074),
              (-0.0045, 0.064), (-0.011, 0.051), (-0.0028, 0.044), (-0.004, 0.0)]),
            ('clock_min', mi * 6 + s / 10, m['steel'],
             [(-0.003, -0.024), (0.003, -0.024), (0.0034, 0.0), (0.0022, 0.088), (0.0062, 0.097), (0.0, 0.117), (-0.0062, 0.097), (-0.0022, 0.088), (-0.0034, 0.0)]),
            ('clock_sec', s * 6, m['brass'],
             [(-0.0009, -0.034), (0.0009, -0.034), (0.0009, 0.124), (0.0, 0.127), (-0.0009, 0.124)])]
    for name, ang, mat, pts in spec:
        o = layout.INTERACTIVE[name][1]
        with kit.interactive(name, origin=o, td=2.0), kit.xform(T(*o) @ Ry(ang)):
            prism(name + '_blade', pts, 'y', -0.0008, 0.0008, mat)
            if name == 'clock_sec':
                with kit.xform(Rx(90)):
                    kit.cyl('clock_sec_tail', 0, 0.024, -0.0008, 0.0008, 0.0045, mat, segs=12, smooth=False)
                    kit.lathe('clock_boss', [(0.0, 0.0008), (0.0045, 0.0008), (0.004, 0.003), (0.0, 0.0042)], m['brass'], segs=12)
            else:
                with kit.xform(Rx(90)):
                    kit.cyl(name + '_ring', 0, 0, -0.0008, 0.0008, 0.0062 if name == 'clock_hour' else 0.0052, mat, segs=14, smooth=False)

# ================================================================== posters
def posters(m):
    WX = -3.398
    for k, (reg, y0, y1, z0, z1, corner) in enumerate((('posterA', 0.055, 0.395, 1.70, 2.18, (1, 0)), ('posterB', -2.30, -1.946, 1.40, 1.90, (0, 1)))):
        cs, ct = corner
        def curl(s, t, cs=cs, ct=ct):
            q = max(0.0, (abs(s - (1 - cs)) + abs(t - (1 - ct)) - 1.62) / 0.38)
            # a corner that has let go of its tape by a centimetre and a half, not five: at 5 cm the wall lamps threw a
            # hard black shadow of the flap across a quarter of the poster, which read as a hole in the print
            lift = 0.016 * q ** 2.2
            pull = 0.007 * q ** 2
            return (lift + 0.0004, (-pull if cs else pull) * 0.7, (pull if not ct else -pull) * 0.7)
        with kit.props(td=1.7):
            grid('poster_%d' % k, (WX, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0), 6, 8, m['sheet'], R(reg), fn=curl, smooth=True)
            # No separate sheet for the paper's back. There used to be one 0.3 mm behind the print, but where the corner
            # curls the quads are warped, the two sheets triangulated differently, and the unlit back poked through the
            # front: whole grid cells of the poster baked black. With a 1.6 cm lift no camera stop can see the back anyway.
        # yellowed tape on the two top corners
        with kit.props(td=0.6):
            for j, (yy, ang) in enumerate(((y0 + 0.012, 35), (y1 - 0.012, -35))):
                with kit.xform(T(WX + 0.0012, yy, z1 - 0.008) @ Rx(ang)):
                    kit.quad('poster_tape%d_%d' % (k, j), [(0, -0.018, -0.008), (0, 0.018, -0.008), (0, 0.018, 0.008), (0, -0.018, 0.008)], m['paper'])

# ================================================================== coat stand, raincoat, hat
def coat_corner(m):
    cx, cy = -3.15, 1.25
    HOOK = -45                                                        # the raincoat hangs on the upper hook pointing at the room
    with kit.props(td=0.8):
        kit.lathe('coatstand_pole', [(0, 0.0), (0.032, 0.0), (0.032, 0.02), (0.027, 0.06), (0.025, 0.4), (0.021, 1.0), (0.019, 1.60), (0.024, 1.64),
                                     (0.026, 1.69), (0.019, 1.715), (0.03, 1.75), (0.022, 1.79), (0.006, 1.815), (0, 1.82)], m['bent'], segs=12, center=(cx, cy, 0))
        C = Vector((cx, cy, 0))
        for k in range(4):
            a = math.radians(65 + 90 * k); d = Vector((math.cos(a), math.sin(a), 0))
            pts = [C + d * r + Vector((0, 0, z)) for r, z in ((0.018, 0.40), (0.05, 0.32), (0.11, 0.18), (0.17, 0.07), (0.205, 0.018), (0.235, 0.012), (0.245, 0.03))]
            kit.tube('coatstand_leg%d' % k, smooth_path(pts, 2), 0.012, m['bent'], segs=6)
            for j, (z0, rr) in enumerate(((1.69, 1.0), (1.55, 0.75))):
                b = math.radians(HOOK + 90 * k + (0 if j == 0 else 45))
                e = Vector((math.cos(b), math.sin(b), 0))
                pts = [C + e * (r * rr) + Vector((0, 0, z0 + dz * rr)) for r, dz in ((0.015, 0.02), (0.06, 0.0), (0.11, -0.04), (0.15, -0.06), (0.17, -0.035), (0.165, 0.005))]
                kit.tube('coatstand_hook%d_%d' % (k, j), pts, 0.0085, m['bent'], segs=5)
                kit.lathe('coatstand_knob%d_%d' % (k, j), [(0, -0.008), (0.012, 0.0), (0, 0.009)], m['bent'], segs=8,
                          center=tuple(C + e * (0.165 * rr) + Vector((0, 0, z0 + 0.012 * rr))))
    # raincoat: built in a local frame (+x toward the pole = the coat's back, y = shoulders), front faces the room
    e = Vector((math.cos(math.radians(HOOK)), math.sin(math.radians(HOOK)), 0))
    tip = C + e * 0.155
    hz = 1.64
    rnd = random.Random(4)
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    with kit.props(td=1.0), kit.xform(T(tip.x, tip.y, 0) @ Rz(HOOK + 180)):
        rows = [(hz + 0.01, 0.025, 0.02), (hz - 0.03, 0.10, 0.05), (hz - 0.08, 0.175, 0.08), (hz - 0.16, 0.19, 0.09), (hz - 0.26, 0.185, 0.09),
                (hz - 0.36, 0.175, 0.088), (hz - 0.52, 0.17, 0.09), (hz - 0.62, 0.18, 0.095), (hz - 0.72, 0.19, 0.10), (hz - 0.82, 0.20, 0.10),
                (hz - 0.90, 0.21, 0.10), (hz - 0.98, 0.215, 0.10)]
        rings = []
        nv = 28
        for i, (z, w, d) in enumerate(rows):
            ring = []
            f = min(1.0, i / 3) * (0.3 + 0.7 * i / len(rows))
            for j in range(nv):
                a = 2 * math.pi * j / nv
                rr = 1 + f * (0.09 * math.sin(6 * a + ph[0] + z * 5) + 0.05 * math.sin(11 * a + ph[1] - z * 3) + 0.03 * math.sin(17 * a + ph[3]))
                yy = w * math.cos(a) * rr
                xx = d * math.sin(a) * rr * (0.75 if math.sin(a) > 0 else 1.0)
                ring.append(Vector((xx + 0.01 * f * math.sin(3 * a + ph[2]), yy, z)))
            rings.append(ring)
        rings.append([Vector((p.x * 0.9, p.y * 0.9, rows[-1][0] + 0.03)) for p in rings[-1]])   # hem turns inward (lining)
        rings_mesh('raincoat_body', rings, m['coat'], close_top=(0, 0, hz + 0.02))
        # front: the overlap edge, two rows of buttons, lapels; sleeves hanging slightly forward; belt with its loose end
        kit.tube('raincoat_edge', smooth_path([(-0.07, 0.045, hz - 0.06), (-0.093, 0.05, hz - 0.30), (-0.092, 0.035, hz - 0.62), (-0.1, 0.03, hz - 0.97)], 3),
                 0.006, m['coat'], segs=5)
        for r_ in range(3):
            for c_ in (-0.035, 0.065):
                z = hz - 0.30 - r_ * 0.12
                with kit.xform(T(-0.094, c_, z) @ Ry(-90)):
                    kit.cyl('raincoat_btn%d_%d' % (r_, int(c_ * 100)), 0, 0, 0.0, 0.006, 0.0095, m['frame'], segs=10, smooth=False)
        for i, s in enumerate((-1, 1)):
            kit.tube('raincoat_lapel%d' % i, smooth_path([(-0.03, s * 0.03, hz - 0.01), (-0.075, s * 0.08, hz - 0.10), (-0.088, s * 0.06, hz - 0.24)], 3),
                     0.011, m['coat'], segs=5)
            pts = [(-0.01, s * 0.155, hz - 0.08), (-0.04, s * 0.18, hz - 0.25), (-0.055, s * 0.175, hz - 0.5), (-0.05, s * 0.16, hz - 0.70)]
            kit.tube('raincoat_sleeve%d' % i, smooth_path(pts, 3), 0.045, m['coat'], segs=10)
        bz = hz - 0.40
        bl = [Vector((0.092 * math.sin(2 * math.pi * j / 22) * (0.75 if math.sin(2 * math.pi * j / 22) > 0 else 1.0) - 0.004,
                      0.183 * math.cos(2 * math.pi * j / 22), bz)) for j in range(22)]
        loop_tube('raincoat_belt', bl, 0.012, m['coat'], segs=4)
        kit.box('raincoat_buckle', -0.104, -0.096, -0.03, 0.0, bz - 0.022, bz + 0.022, m['brass_d'], bevel=0.002, segs=1)
        kit.tube('raincoat_beltend', smooth_path([(-0.1, 0.0, bz), (-0.104, 0.03, bz - 0.12), (-0.1, 0.025, bz - 0.26)], 3), 0.012, m['coat'], segs=4)
        kit.lathe('raincoat_collar', [(0.06, -0.06), (0.075, -0.03), (0.06, 0.0), (0.04, 0.02)], m['coat'], segs=16, center=(0, 0, hz - 0.02))
    # felt hat on the top of the pole, tipped a little
    with kit.props(td=0.9), kit.xform(T(cx, cy, 1.765) @ Rz(30) @ Rx(-9) @ Matrix.Diagonal((1.0, 1.16, 1.0, 1.0))):
        kit.lathe('hat_brim', [(0.15, 0.012), (0.152, 0.02), (0.14, 0.012), (0.10, 0.004), (0.082, 0.004), (0.082, 0.0), (0.10, -0.002), (0.14, 0.004), (0.15, 0.012)],
                  m['felt_hat'], segs=24)
        kit.lathe('hat_crown', [(0.083, 0.0), (0.084, 0.035), (0.080, 0.075), (0.070, 0.105), (0.05, 0.115), (0.03, 0.108), (0.0, 0.11)], m['felt_hat'], segs=24)
        kit.lathe('hat_band', [(0.0845, 0.004), (0.0855, 0.006), (0.0855, 0.03), (0.0845, 0.032)], m['ribbon'], segs=24)

# ================================================================== umbrella stand, two umbrellas (one wet), puddle
def umbrella(name, m, canopy, handle, wet):
    rings = []; nv = 12
    hs = [(0.10, 0.004), (0.13, 0.012), (0.20, 0.026), (0.32, 0.036), (0.46, 0.034), (0.58, 0.022), (0.66, 0.012), (0.69, 0.0065)]
    for z, r in hs:
        ring = []
        for j in range(nv):
            a = 2 * math.pi * j / nv
            rr = r * (1 + 0.22 * math.cos(6 * a) + 0.06 * math.sin(3 * a + z * 9))
            ring.append(Vector((rr * math.cos(a + z * 1.2), rr * math.sin(a + z * 1.2), z)))
        rings.append(ring)
    rings_mesh(name + '_canopy', rings, canopy, close_top=None)
    kit.cyl(name + '_ferrule', 0, 0, 0.0, 0.11, 0.0035, m['chrome'], segs=6, r1=0.004)
    kit.cyl(name + '_shaft', 0, 0, 0.68, 0.80, 0.0055, m['chrome'], segs=8)
    kit.lathe(name + '_strap', [(0.03, 0.40), (0.033, 0.405), (0.033, 0.425), (0.03, 0.43)], canopy, segs=16)
    kit.tube(name + '_handle', smooth_path([(0, 0, 0.79), (0, 0, 0.84), (0.012, 0, 0.875), (0.042, 0, 0.892), (0.07, 0, 0.875), (0.08, 0, 0.84), (0.072, 0, 0.815)], 3),
             0.0105, handle, segs=8)

def umbrellas(m):
    sx, sy = -3.305, 1.47
    with kit.props(td=0.9):
        kit.lathe('ustand_outer', [(0.0, 0.0), (0.083, 0.0), (0.086, 0.012), (0.082, 0.02), (0.080, 0.1), (0.084, 0.11), (0.080, 0.12), (0.078, 0.38),
                                   (0.082, 0.39), (0.078, 0.40), (0.080, 0.47), (0.088, 0.485), (0.089, 0.495), (0.084, 0.50), (0.076, 0.495), (0.075, 0.45), (0.075, 0.05), (0.0, 0.05)],
                  m['brass'], segs=20, center=(sx, sy, 0))
    with kit.props(td=0.8):
        with kit.xform(T(sx + 0.012, sy - 0.01, 0.05) @ Rz(100) @ Ry(6) @ Rz(-130)):
            umbrella('umbrella_wet', m, m['wet'], m['cane'], True)
        with kit.xform(T(sx - 0.02, sy + 0.025, 0.05) @ Rz(270) @ Ry(7) @ Rz(80)):
            umbrella('umbrella_dry', m, m['umb2'], m['frame'], False)
    # the small puddle, spreading out from under the stand toward the door
    rnd = random.Random(9)
    with kit.props(td=0.7):
        bm = bmesh.new(); n = 26
        c = Vector((sx + 0.09, sy + 0.02, 0.0012))
        ks = [rnd.uniform(0, 6.28) for _ in range(3)]
        ring = []
        for j in range(n):
            a = 2 * math.pi * j / n
            r = 0.105 + 0.022 * math.sin(3 * a + ks[0]) + 0.014 * math.sin(5 * a + ks[1]) + 0.008 * math.sin(9 * a + ks[2])
            ring.append(bm.verts.new(c + Vector((r * 1.25 * math.cos(a), r * 0.8 * math.sin(a), 0))))
        cv = bm.verts.new(c)
        for j in range(n): bm.faces.new((cv, ring[j], ring[(j + 1) % n]))
        kit.finish('puddle', bm, m['puddle'])
        # a few stray drops further out
        for j, (dx, dy, r) in enumerate(((0.26, -0.05, 0.012), (0.23, 0.07, 0.008), (0.31, 0.01, 0.006))):
            kit.cyl('puddle_drop%d' % j, sx + dx, sy + dy, 0.0, 0.0012, r, m['puddle'], segs=10, cap='t', smooth=False)

# ================================================================== café table with two bentwood chairs upside down
def chair(name, m):
    """bentwood café chair in its normal orientation (seat top z 0.475, back toward +y)"""
    kit.lathe(name + '_seat', [(0.0, 0.447), (0.19, 0.447), (0.2, 0.455), (0.2, 0.468), (0.19, 0.475), (0.0, 0.477)], m['bent'], segs=24)
    loop_tube(name + '_seatring', [(0.182 * math.cos(2 * math.pi * j / 18), 0.182 * math.sin(2 * math.pi * j / 18), 0.437) for j in range(18)], 0.011, m['bent'], segs=6)
    for i, s in enumerate((-1, 1)):
        kit.tube(name + '_fleg%d' % i, smooth_path([(s * 0.125, -0.11, 0.44), (s * 0.145, -0.135, 0.22), (s * 0.17, -0.17, 0.0)], 2), 0.0125, m['bent'], segs=6)
    back = [(-0.16, 0.19, 0.0), (-0.135, 0.13, 0.44), (-0.14, 0.165, 0.62), (-0.125, 0.205, 0.80), (-0.07, 0.228, 0.875), (0.0, 0.232, 0.888),
            (0.07, 0.228, 0.875), (0.125, 0.205, 0.80), (0.14, 0.165, 0.62), (0.135, 0.13, 0.44), (0.16, 0.19, 0.0)]
    kit.tube(name + '_back', smooth_path(back, 3), 0.013, m['bent'], segs=6)
    hoop = [(-0.095, 0.15, 0.475), (-0.10, 0.175, 0.62), (-0.075, 0.2, 0.74), (0.0, 0.212, 0.775), (0.075, 0.2, 0.74), (0.10, 0.175, 0.62), (0.095, 0.15, 0.475)]
    kit.tube(name + '_hoop', smooth_path(hoop, 2), 0.009, m['bent'], segs=6)
    loop_tube(name + '_legring', [(0.158 * math.cos(2 * math.pi * j / 16), 0.01 + 0.168 * math.sin(2 * math.pi * j / 16), 0.2) for j in range(16)], 0.008, m['bent'], segs=5)

def cafe(m):
    tx, ty = -2.71, -2.24
    TZ = 0.725
    with kit.props(td=0.9):
        kit.lathe('cafe_top', [(0.0, TZ - 0.025), (0.29, TZ - 0.025), (0.30, TZ - 0.018), (0.302, TZ - 0.008), (0.296, TZ), (0.0, TZ)], m['marble'], segs=32, center=(tx, ty, 0))
        kit.lathe('cafe_base', [(0.0, 0.0), (0.22, 0.0), (0.22, 0.012), (0.18, 0.03), (0.07, 0.06), (0.035, 0.09), (0.024, 0.12), (0.022, 0.62), (0.03, 0.65),
                                (0.10, 0.68), (0.10, TZ - 0.025), (0.0, TZ - 0.025)], m['iron'], segs=20, center=(tx, ty, 0))
    with kit.props(td=0.6):
        ax = 25
        with kit.xform(T(tx, ty, TZ) @ Rz(ax) @ T(0.0, -0.175, 0) @ Rx(180) @ T(0, 0, -0.477)):
            chair('chairA', m)
        with kit.xform(T(tx, ty, TZ + 0.028) @ Rz(ax + 180) @ T(0.0, -0.165, 0) @ Rx(180) @ Rx(-4) @ T(0, 0, -0.477)):
            chair('chairB', m)

# ================================================================== rubber plant by the piano
def plant(m):
    px, py = -3.11, -1.84
    rnd = random.Random(21)
    with kit.props(td=0.8):
        kit.lathe('plant_pot', [(0.0, 0.0), (0.115, 0.0), (0.12, 0.012), (0.135, 0.12), (0.155, 0.27), (0.168, 0.30), (0.17, 0.315), (0.162, 0.322),
                                (0.152, 0.315), (0.14, 0.28), (0.0, 0.28)], m['glaze'], segs=24, center=(px, py, 0))
        kit.lathe('plant_soil', [(0.0, 0.29), (0.147, 0.285)], m['soil'], segs=24, center=(px, py, 0))
        kit.lathe('plant_saucer', [(0.0, 0.0), (0.15, 0.0), (0.16, 0.02), (0.152, 0.022), (0.13, 0.008), (0.0, 0.008)], m['glaze'], segs=32, center=(px, py, -0.002))
    stems = [((px - 0.02, py + 0.01), 1.68, (0.07, 0.03)), ((px + 0.03, py - 0.03), 1.42, (0.14, -0.10)), ((px - 0.01, py - 0.04), 1.15, (0.10, 0.10)),
             ((px + 0.02, py + 0.03), 0.95, (0.16, 0.02))]
    with kit.props(td=0.8):
        for si, ((sx, sy), top, (lx, ly)) in enumerate(stems):
            pts = [Vector((sx, sy, 0.28)), Vector((sx + lx * 0.25, sy + ly * 0.25, 0.28 + (top - 0.28) * 0.35)), Vector((sx + lx * 0.7, sy + ly * 0.7, 0.28 + (top - 0.28) * 0.75)),
                   Vector((sx + lx, sy + ly, top))]
            path = smooth_path(pts, 4)
            kit.tube('plant_stem%d' % si, path, 0.011 - 0.002 * si, m['stem'], segs=5, radii=[0.014 - 0.007 * i / len(path) for i in range(len(path))])
            # reddish sheath at the growing tip
            tip = path[-1]; dirv = (path[-1] - path[-2]).normalized()
            kit.tube('plant_sheath%d' % si, [tip, tip + dirv * 0.07], 0.006, m['sheath'], segs=5, radii=[0.006, 0.001])
            # leaves from 40% of the height upward, spiralling, biased away from the wall (+x) and the piano (-y)
            nleaf = int((top - 0.40) / 0.045)
            for k in range(nleaf):
                t = 0.30 + 0.68 * (k / max(1, nleaf - 1)) ** 0.8
                idx = min(len(path) - 1, int(t * (len(path) - 1)))
                base = path[idx]
                az = 2 * math.pi * ((k * 0.382 + si * 0.31) % 1.0)
                az = math.atan2(math.sin(az), math.cos(az) + 0.55)          # lean away from the wall (+x)
                if math.sin(az) > 0.6 and base.z > 1.3: az -= 0.6         # keep clear of the piano end / window
                L = (0.22 + 0.08 * rnd.random()) * (0.75 if t > 0.88 else 1.0)
                Wd = L * 0.56
                pitch = math.radians(rnd.uniform(-8, 18) + (30 if t > 0.88 else 0))
                leaf('plant_leaf%d_%d' % (si, k), base, az, pitch, L, Wd, m['leaf2'] if t > 0.85 else m['leaf'], m['stem'], rnd)

def leaf(name, base, az, pitch, L, W, mat, petmat, rnd):
    """glossy oval rubber-plant leaf: short petiole, blade folded along the midrib, tip drooping"""
    d = Vector((math.cos(az), math.sin(az), 0)); side = Vector((-math.sin(az), math.cos(az), 0)); z = Vector((0, 0, 1))
    fwd = d * math.cos(pitch) + z * math.sin(pitch)
    pet = base + fwd * 0.035
    kit.tube(name + '_pet', [base, pet], 0.003, petmat, segs=4, caps=False)
    nrow = 7; droop = 0.05 + 0.05 * rnd.random(); fold = 0.09; twist = rnd.uniform(-0.2, 0.2)
    bm = bmesh.new(); rows = []
    up = fwd.cross(side).normalized()
    for i in range(nrow + 1):
        u = i / nrow
        w = W * 0.5 * (math.sin(math.pi * min(1, u * 1.04)) ** 0.6) * (1 - 0.15 * u)
        c = pet + fwd * (L * u) - z * (droop * u * u)
        sv = (side * math.cos(twist * u) + up * math.sin(twist * u))
        if i == nrow:
            rows.append([bm.verts.new(c)]); break
        rows.append([bm.verts.new(c + sv * -w - up * (fold * w)), bm.verts.new(c + up * 0.002), bm.verts.new(c + sv * w - up * (fold * w))])
    for i in range(nrow - 1):
        A, B = rows[i], rows[i + 1]
        bm.faces.new((A[0], A[1], B[1], B[0])); bm.faces.new((A[1], A[2], B[2], B[1]))
    A = rows[nrow - 1]; tipv = rows[nrow][0]
    bm.faces.new((A[0], A[1], tipv)); bm.faces.new((A[1], A[2], tipv))
    bm.normal_update()
    if sum(f.normal.dot(up) for f in bm.faces) < 0:
        for f in bm.faces: f.normal_flip()
    kit.finish(name, bm, mat, smooth=True)

# ================================================================== build
def build():
    m = M()
    piano(m)
    piano_keys(m)
    piano_top(m)
    piano_lamp(m)
    stool(m)
    floor_lamp(m)
    phone_corner(m)
    mapframe(m)
    clock(m)
    posters(m)
    coat_corner(m)
    umbrellas(m)
    cafe(m)
    plant(m)

# a small brass piano lamp over the music desk (night only): it is what lets the keys and the copied music be seen after closing
LIGHTS = [('N_lounge_pianolamp', 'POINT', PLAMP, 3.0, layout.WARM, dict(radius=0.015))]
