"""HIFI — the sound system of DEAN'S.
Belt-drive turntable on the counter (HAYASE BD-3), valve power amp on a slim preamp/tuner (OKABE LABORATORY),
upright reel-to-reel deck threaded and ready (SHIRANE TR-7), now-playing easel with the sleeve of the record on
the platter ("After Hours" by The House Trio, LOW LAMP records), two big studio monitors (HAZAMA M-15),
headphones with a coiled cord. All makers, names and designs are invented.
Textures: tex.py -> tex/close.png (sleeve + label), tex/sheet.png (panels, dials, badges), tex/regions.json."""
import math, os, json
import bpy, bmesh
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
CRED_Z = layout.CREDENZA['top_z']
Y_FWD = 1.0

# ============================================================================================ small helpers
def front(x, y, z):
    """local frame whose +Z points toward the room (-Y), local X = world X, local Y = world Z"""
    return T(x, y, z) @ Rx(90)

def frame(origin, d):
    """local frame at origin whose +Z runs along direction d"""
    q = Vector((0, 0, 1)).rotation_difference(Vector(d).normalized())
    return Matrix.Translation(Vector(origin)) @ q.to_matrix().to_4x4()

def fquad(name, x0, x1, z0, z1, y, mat, rect):
    """quad in the plane y, facing -Y, uv rect (u0, v0, u1, v1)"""
    u0, v0, u1, v1 = rect
    return kit.quad(name, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], mat, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))

def sub_rect(rect, fu0, fv0, fu1, fv1):
    u0, v0, u1, v1 = rect
    return (u0 + (u1 - u0) * fu0, v0 + (v1 - v0) * fv0, u0 + (u1 - u0) * fu1, v0 + (v1 - v0) * fv1)

def disc(name, mat, rect, r, z=0.0, r0=0.0, segs=32, rot=0.0, uvr=None):
    """flat (annular) disc in the local XY plane at height z facing +Z; the circle of radius uvr (default r) fills rect"""
    uvr = uvr or r
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('uv_tex')
    u0, v0, u1, v1 = rect; cu, cv, hu, hv = (u0 + u1) / 2, (v0 + v1) / 2, (u1 - u0) / 2, (v1 - v0) / 2
    def ring(rr): return [bm.verts.new((rr * math.cos(2 * math.pi * j / segs), rr * math.sin(2 * math.pi * j / segs), z)) for j in range(segs)]
    def uv(co):
        a = math.radians(rot); x = co.x * math.cos(a) - co.y * math.sin(a); y = co.x * math.sin(a) + co.y * math.cos(a)
        return (cu + hu * x / uvr, cv + hv * y / uvr)
    O = ring(r)
    if r0 > 0:
        I = ring(r0)
        for j in range(segs):
            j2 = (j + 1) % segs; f = bm.faces.new((I[j], O[j], O[j2], I[j2]))
            for l in f.loops: l[uvl].uv = uv(l.vert.co)
    else:
        c = bm.verts.new((0, 0, z))
        for j in range(segs):
            f = bm.faces.new((c, O[j], O[(j + 1) % segs]))
            for l in f.loops: l[uvl].uv = uv(l.vert.co)
    return kit.finish(name, bm, mat)

def flange(name, mat, radii, segs, windows, z=0.0):
    """reel flange: annular disc (local XY, facing +Z) with window cut-outs in ring 2; windows: list of (seg0, seg1)"""
    bm = bmesh.new()
    rings = [[bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), z)) for j in range(segs)] for r in radii]
    for k in range(len(radii) - 1):
        A, B = rings[k], rings[k + 1]
        for j in range(segs):
            if k == 2 and any(s0 <= j < s1 for s0, s1 in windows): continue
            j2 = (j + 1) % segs; bm.faces.new((A[j], B[j], B[j2], A[j2]))
    return kit.finish(name, bm, mat)

def sweep(name, pts, side, w, t, mat, caps=False):
    """rectangular section (w along `side`, t across) swept along pts"""
    pts = [Vector(p) for p in pts]; side = Vector(side).normalized()
    bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        tg = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = side.cross(tg).normalized()
        rings.append([bm.verts.new(p + side * sx * w / 2 + n * sy * t / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    for i in range(len(pts) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(4):
            j2 = (j + 1) % 4; bm.faces.new((A[j], A[j2], B[j2], B[j]))
    if caps: bm.faces.new(rings[0]); bm.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return kit.finish(name, bm, mat)

def catmull(pts, n=8):
    pts = [Vector(p) for p in pts]; out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1]); return out

def resample(pts, step):
    pts = [Vector(p) for p in pts]; L = [0.0]
    for a, b in zip(pts, pts[1:]): L.append(L[-1] + (b - a).length)
    out = []; s = 0.0; i = 0
    while s <= L[-1]:
        while L[i + 1] < s: i += 1
        f = (s - L[i]) / max(L[i + 1] - L[i], 1e-9); out.append(pts[i].lerp(pts[i + 1], f)); s += step
    out.append(pts[-1]); return out

def coil(pts, rh, pitch, per_turn=6):
    """helix of radius rh wound around the polyline pts"""
    step = pitch / per_turn
    c = resample(pts, step); out = []; n = None
    for i, p in enumerate(c):
        tg = (c[min(i + 1, len(c) - 1)] - c[max(i - 1, 0)]).normalized()
        if n is None: n = tg.cross(Vector((0, 0, 1))).normalized()
        n = (n - tg * n.dot(tg)).normalized(); b = tg.cross(n)
        a = 2 * math.pi * i / per_turn
        out.append(p + (n * math.cos(a) + b * math.sin(a)) * rh)
    return out

def knob(name, x, y, z, r, h, mat, cap=None, skirt=0.0, segs=20, pointer=None):
    """round knob on a front panel (panel plane y, knob sticks out toward -Y)"""
    with kit.xform(front(x, y, z)):
        prof = []
        if skirt: prof += [(r + skirt, 0), (r + skirt, h * 0.22), (r, h * 0.3)]
        else: prof += [(r, 0)]
        prof += [(r, h * 0.88), (r * 0.9, h), (0, h)]
        kit.lathe(name, prof, mat, segs=segs, sharp=40)
        if cap: kit.cyl(name + '_cap', 0, 0, h, h + 0.0006, r * 0.62, cap, segs=segs, cap='t')
        if pointer: kit.box(name + '_ptr', -0.0006, 0.0006, r * 0.3, r * 0.85, h, h + 0.0008, pointer, skip='-z')

# ============================================================================================ materials
class _M: pass

def brushed(name, col, rough=0.3, axis='X', metal=1.0):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    sc = {'X': (4, 500, 500), 'Y': (500, 4, 500), 'Z': (500, 500, 4)}[axis]
    v = mats.coords(nt, sc)
    n = mats.noise(nt, v, 1.0, 4, 0.6)
    mats.L(nt, mats.ramp(nt, n, [(0.3, tuple(c * 0.82 for c in col)), (0.7, tuple(min(1, c * 1.1) for c in col))]), b.inputs['Base Color'])
    mats.L(nt, mats.math_(nt, 'ADD', rough - 0.06, mats.math_(nt, 'MULTIPLY', n, 0.12)), b.inputs['Roughness'])
    mats.setp(b, metal=metal)
    return m

def hammertone(name, col):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    v = mats.coords(nt)
    vor = mats.N(nt, 'ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 260; mats.L(nt, v, vor.inputs['Vector'])
    n1 = mats.noise(nt, v, 25, 4, 0.6)
    f = mats.math_(nt, 'ADD', mats.math_(nt, 'MULTIPLY', vor.outputs['Distance'], 0.7), mats.math_(nt, 'MULTIPLY', n1, 0.3))
    mats.L(nt, mats.ramp(nt, f, [(0.2, tuple(c * 1.35 for c in col)), (0.75, tuple(c * 0.7 for c in col))]), b.inputs['Base Color'])
    mats.L(nt, mats.math_(nt, 'ADD', 0.30, mats.math_(nt, 'MULTIPLY', vor.outputs['Distance'], 0.25)), b.inputs['Roughness'])
    mats.setp(b, metal=0.6)
    mats.bump(nt, b, vor.outputs['Distance'], 0.45, 0.0012)
    return m

def vinyl(name, c):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L, M = mats.N, mats.L, mats.math_
    mats.setp(b, rough=0.3, aniso=0.9)
    geo = N(nt, 'ShaderNodeNewGeometry')
    sub = N(nt, 'ShaderNodeVectorMath', operation='SUBTRACT'); L(nt, geo.outputs['Position'], sub.inputs[0]); sub.inputs[1].default_value = c
    cr = N(nt, 'ShaderNodeVectorMath', operation='CROSS_PRODUCT'); cr.inputs[0].default_value = (0, 0, 1); L(nt, sub.outputs[0], cr.inputs[1])
    nm = N(nt, 'ShaderNodeVectorMath', operation='NORMALIZE'); L(nt, cr.outputs[0], nm.inputs[0]); L(nt, nm.outputs[0], b.inputs['Tangent'])
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, sub.outputs[0], sep.inputs[0])
    r = M(nt, 'SQRT', M(nt, 'ADD', M(nt, 'MULTIPLY', sep.outputs[0], sep.outputs[0]), M(nt, 'MULTIPLY', sep.outputs[1], sep.outputs[1])))
    g = M(nt, 'MULTIPLY', M(nt, 'GREATER_THAN', r, 0.059), M(nt, 'LESS_THAN', r, 0.1462))
    for gc in (0.0885, 0.1065, 0.1255):                                   # track gaps
        g = M(nt, 'MULTIPLY', g, M(nt, 'GREATER_THAN', M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', r, gc)), 0.0009))
    wn = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D'); L(nt, M(nt, 'FLOOR', M(nt, 'MULTIPLY', r, 900)), wn.inputs['W'])
    L(nt, M(nt, 'ADD', 0.10, M(nt, 'MULTIPLY', g, M(nt, 'ADD', 0.16, M(nt, 'MULTIPLY', wn.outputs[0], 0.14)))), b.inputs['Roughness'])
    col = M(nt, 'ADD', 0.0045, M(nt, 'MULTIPLY', g, M(nt, 'ADD', 0.006, M(nt, 'MULTIPLY', wn.outputs[0], 0.005))))
    L(nt, col, b.inputs['Base Color'])
    return m

def tapepack(name, c, axis_y=True):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    N, L, M = mats.N, mats.L, mats.math_
    geo = N(nt, 'ShaderNodeNewGeometry')
    sub = N(nt, 'ShaderNodeVectorMath', operation='SUBTRACT'); L(nt, geo.outputs['Position'], sub.inputs[0]); sub.inputs[1].default_value = c
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, sub.outputs[0], sep.inputs[0])
    r = M(nt, 'SQRT', M(nt, 'ADD', M(nt, 'MULTIPLY', sep.outputs[0], sep.outputs[0]), M(nt, 'MULTIPLY', sep.outputs[2], sep.outputs[2])))
    wn = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D'); L(nt, M(nt, 'FLOOR', M(nt, 'MULTIPLY', r, 700)), wn.inputs['W'])
    L(nt, mats.ramp(nt, wn.outputs[0], [(0.0, (0.09, 0.045, 0.02)), (1.0, (0.19, 0.10, 0.05))]), b.inputs['Base Color'])
    L(nt, M(nt, 'ADD', 0.25, M(nt, 'MULTIPLY', wn.outputs[0], 0.2)), b.inputs['Roughness'])
    return m

def image_emit(name, file, strength):
    if name in mats._M: return mats._M[name]
    m, nt, b, _ = mats.base(name)
    uv = mats.N(nt, 'ShaderNodeUVMap'); uv.uv_map = 'uv_tex'
    t = mats.N(nt, 'ShaderNodeTexImage'); t.image = bpy.data.images.load(file, check_existing=True); t.name = 'SRC'
    mats.L(nt, uv.outputs[0], t.inputs[0]); mats.L(nt, t.outputs[0], b.inputs['Base Color']); mats.L(nt, t.outputs[0], b.inputs['Emission Color'])
    mats.setp(b, emit_s=strength, rough=0.25, coat=0.6, coat_rough=0.05)
    return m

def make_mats():
    m = _M()
    m.walnut = mats.wood('hifi_walnut', axis='X', rough=0.35, coat=0.35)
    m.walnut_v = mats.wood('hifi_walnut_v', axis='Z', rough=0.38, coat=0.3)
    m.oak = mats.wood('hifi_oak', axis='Z', cols=((0.16, 0.09, 0.04), (0.32, 0.19, 0.09), (0.45, 0.30, 0.15)), rough=0.5)
    m.alu = brushed('hifi_alu', (0.66, 0.66, 0.64), 0.36, metal=0.8)
    m.alu_dark = brushed('hifi_alu_dark', (0.30, 0.30, 0.29), 0.3)
    m.chrome = mats.plain('hifi_chrome', (0.85, 0.85, 0.83), rough=0.12, metal_=1.0)
    m.knob = brushed('hifi_knob', (0.70, 0.70, 0.68), 0.22, axis='Z')
    m.rubber = mats.plain('hifi_rubber', (0.016, 0.015, 0.014), rough=0.78)
    m.blackplastic = mats.plain('hifi_blackplastic', (0.018, 0.017, 0.016), rough=0.32)
    m.blackpaint = mats.noisy('hifi_blackpaint', (0.013, 0.012, 0.011), (0.03, 0.028, 0.026), rough=0.45, scale=40)
    m.crinkle = mats.noisy('hifi_crinkle', (0.010, 0.010, 0.010), (0.035, 0.034, 0.032), rough=0.55, scale=320, bmp=0.3)
    m.hammer = hammertone('hifi_hammertone', (0.085, 0.10, 0.088))
    m.close = mats.image('hifi_close', os.path.join(TEX, 'close.png'), rough=0.55)
    m.sheet = mats.image('hifi_sheet', os.path.join(TEX, 'sheet.png'), rough=0.38)
    m.dials = image_emit('EMA_hifi_dials', os.path.join(TEX, 'sheet.png'), 0.9)
    m.heater = mats.emissive('hifi_heater', (1.0, 0.40, 0.09), 26, night_only=False)
    m.heater_dim = mats.emissive('hifi_heater_dim', (1.0, 0.36, 0.08), 6, night_only=False)
    m.pilot = mats.emissive('hifi_pilot', (1.0, 0.22, 0.05), 14, night_only=False)
    m.amber = mats.emissive('hifi_amber', (1.0, 0.55, 0.16), 10, night_only=False)
    m.strobe = mats.emissive('hifi_strobe', (1.0, 0.32, 0.08), 12, night_only=False)
    m.glass = mats.glass('hifi_valveglass', (0.97, 0.95, 0.92), rough=0.02, shadow_amt=0.9)
    m.getter = mats.plain('hifi_getter', (0.30, 0.29, 0.28), rough=0.12, metal_=1.0)
    m.plate = mats.plain('hifi_valveplate', (0.035, 0.035, 0.038), rough=0.6, metal_=0.5)
    m.mica = mats.plain('hifi_mica', (0.50, 0.46, 0.38), rough=0.4)
    m.bakelite = mats.plain('hifi_bakelite', (0.075, 0.035, 0.016), rough=0.32)
    m.cone = mats.noisy('hifi_cone', (0.14, 0.115, 0.08), (0.22, 0.18, 0.125), rough=0.85, scale=70, bmp=0.25, detail=6)
    m.felt = mats.noisy('hifi_felt', (0.018, 0.016, 0.014), (0.04, 0.035, 0.03), rough=0.95, scale=220)
    m.baffle = mats.noisy('hifi_baffle', (0.020, 0.018, 0.016), (0.038, 0.034, 0.03), rough=0.75, scale=90, bmp=0.15)
    m.horn = mats.noisy('hifi_horn', (0.045, 0.045, 0.045), (0.085, 0.083, 0.08), rough=0.45, scale=160, bmp=0.25, metal_=0.6)
    m.tape = mats.plain('hifi_tape', (0.22, 0.11, 0.05), rough=0.35)
    m.cushion = mats.leather('hifi_cushion', (0.035, 0.024, 0.018))
    m.hpshell = mats.plain('hifi_hpshell', (0.055, 0.036, 0.024), rough=0.28, coat=0.4)
    m.card = mats.noisy('hifi_card', (0.42, 0.38, 0.30), (0.55, 0.50, 0.40), rough=0.85, scale=40)
    m.cable = mats.plain('hifi_cable', (0.018, 0.018, 0.018), rough=0.35)
    m.cable_ox = mats.plain('hifi_cable_ox', (0.16, 0.03, 0.022), rough=0.4)
    m.brass = mats.metal('hifi_brass', (0.78, 0.56, 0.24), rough=0.3, patina=0.3)
    sp = layout.INTERACTIVE['platter_record'][1]
    m.vinyl = vinyl('hifi_vinyl', sp)
    m.pack_l = tapepack('hifi_pack_l', layout.INTERACTIVE['reel_l'][1])
    m.pack_r = tapepack('hifi_pack_r', layout.INTERACTIVE['reel_r'][1])
    return m

# ============================================================================================ turntable
def turntable(m, R):
    tt = layout.TURNTABLE; z0 = tt['z']
    X0, X1, Y0, Y1 = tt['x0'], tt['x1'], tt['y0'], tt['y1']
    sp = layout.INTERACTIVE['platter_record'][1]; cx, cy = sp[0], sp[1]
    zf, zt = z0 + 0.010, z0 + 0.065            # feet top, plinth top
    zp = zt + 0.003                             # plate top
    with kit.props(td=1.6):
        for fx, fy in ((X0 + 0.05, Y0 + 0.045), (X1 - 0.05, Y0 + 0.045), (X0 + 0.05, Y1 - 0.045), (X1 - 0.05, Y1 - 0.045)):
            kit.lathe('tt_foot', [(0.024, z0), (0.024, zf - 0.002), (0.02, zf)], m.rubber, segs=16)
        kit.box('tt_plinth', X0, X1, Y0, Y1, zf, zt, m.walnut, skip='-z +z', bevel=0.005, segs=2)
        e, bv = 0.009, 0.005    # walnut border around the top plate (inside the bevelled edge)
        for (a0, a1, b0, b1) in ((X0 + bv, X1 - bv, Y0 + bv, Y0 + e), (X0 + bv, X1 - bv, Y1 - e, Y1 - bv), (X0 + bv, X0 + e, Y0 + e, Y1 - e), (X1 - e, X1 - bv, Y0 + e, Y1 - e)):
            kit.box('tt_rim', a0, a1, b0, b1, zt - 0.01, zt, m.walnut, only=('+z',))
        holed_box('tt_plate', m.alu, X0 + e, X1 - e, Y0 + e, Y1 - e, zt - 0.002, zp, [('c', cx, cy, 0.147)], axis='z', drop='-z')
        # nameplate print along the front of the plate
        b = R['tt_badge']; kit.quad('tt_badge', [(-0.815, -0.689, zp + 0.0002), (-0.715, -0.689, zp + 0.0002), (-0.715, -0.676, zp + 0.0002), (-0.815, -0.676, zp + 0.0002)],
                                    m.sheet, ((b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])))
        # speed selector (front-left corner)
        kx, ky = -0.846, -0.664
        kit.lathe('tt_speed', [(0.016, zp), (0.016, zp + 0.002), (0.0125, zp + 0.003), (0.0125, zp + 0.011), (0.0115, zp + 0.012)], m.knob, segs=24, center=(kx, ky, 0))
        with kit.xform(T(kx, ky, zp + 0.012) @ Rz(25)): disc('tt_speed_top', m.sheet, R['speed_top'], 0.0115, segs=24)
        # strobe lamp housing looking at the platter rim
        lx, ly = -0.862, -0.585
        kit.box('tt_strobe_box', lx - 0.009, lx + 0.008, ly - 0.011, ly + 0.011, zp, zp + 0.016, m.chrome, skip='-z', bevel=0.002, segs=1)
        kit.quad('tt_strobe_lens', [(lx + 0.0085, ly - 0.007, zp + 0.005), (lx + 0.0085, ly + 0.007, zp + 0.005), (lx + 0.0085, ly + 0.007, zp + 0.012), (lx + 0.0085, ly - 0.007, zp + 0.012)], m.strobe)
        # start / stop buttons + pilot jewel (front right)
        for i, bx in enumerate((-0.512, -0.488)):
            kit.box('tt_btn', bx - 0.009, bx + 0.009, -0.684, -0.672, zp, zp + 0.005, m.chrome if i else m.blackplastic, skip='-z', bevel=0.0012, segs=1)
        kit.lathe('tt_pilot_ring', [(0.0055, zp), (0.0055, zp + 0.002), (0.004, zp + 0.0025)], m.chrome, segs=16, center=(-0.463, -0.678, 0))
        kit.lathe('tt_pilot', [(0.004, zp + 0.0025), (0.003, zp + 0.0045), (0.0, zp + 0.0052)], m.pilot, segs=12, center=(-0.463, -0.678, 0))
        # 45 adapter in the rear-left corner
        kit.lathe('tt_45', [(0.019, zp), (0.019, zp + 0.007), (0.0175, zp + 0.0085), (0.0065, zp + 0.0085), (0.0065, zp + 0.013), (0.0055, zp + 0.014), (0, zp + 0.014)],
                  m.chrome, segs=24, center=(-0.848, -0.357, 0))
        # bearing collar under the platter
        kit.lathe('tt_bearing', [(0.03, zp), (0.03, 1.0905), (0.0, 1.0905)], m.alu_dark, segs=24, center=(cx, cy, 0))
    # ---- platter + mat + record (spins about Z, pivot at the spindle)
    with kit.interactive('platter_record', origin=sp, td=2.6):
        for k in range(4):
            kit.cyl_patch('tt_strobe_rim', cx, cy, 1.0905, 1.1075, 0.155, k * 90, (k + 1) * 90, m.sheet, uvrect=R['strobe'], segs=16)
        kit.lathe('tt_platter_top', [(0.155, 1.1075), (0.1538, 1.1088), (0.1488, 1.1088)], m.alu, segs=64, center=(cx, cy, 0))
        kit.lathe('tt_mat', [(0.1488, 1.1088), (0.1488, 1.1108), (0.147, 1.1112)], m.rubber, segs=48, center=(cx, cy, 0))
        with kit.props(td=3.2):
            kit.lathe('tt_record', [(0.1524, 1.1112), (0.1524, 1.1145), (0.1515, 1.1152), (0.147, 1.1150), (0.0505, 1.1150)], m.vinyl, segs=72, center=(cx, cy, 0))
            with kit.xform(T(cx, cy, 1.11505)):
                disc('tt_label', m.close, (0.5, 0.0, 1.0, 1.0), 0.0505, r0=0.0037, segs=40, rot=-30)
        kit.lathe('tt_spindle', [(0.0036, 1.1150), (0.0036, 1.1255), (0.0026, 1.128), (0.0, 1.1285)], m.chrome, segs=12, center=(cx, cy, 0))

def tonearm(m, R):
    P3 = Vector(layout.INTERACTIVE['tonearm'][1]); C3 = Vector(layout.INTERACTIVE['platter_record'][1])
    P = P3.xy; C = C3.xy
    zA = 1.134; Leff = 0.277; rp = 0.117          # tube height, effective length, playing radius (a third of the way in)
    zp = layout.TURNTABLE['z'] + 0.068
    d = C - P; D = d.length; u = d / D
    a = (Leff ** 2 - rp ** 2 + D * D) / (2 * D); h = math.sqrt(Leff ** 2 - a * a)
    S = P + u * a + Vector((-u.y, u.x)) * h       # stylus point
    rad = (S - C).normalized(); tg = Vector((-rad.y, rad.x)); line = (S - P).normalized()
    hs = tg if tg.dot(line) > 0 else -tg            # headshell axis = groove tangent
    Q = S - hs * 0.045                              # headshell collar
    lq = Q - P; Lq = lq.length; lqd = lq / Lq
    beta = math.atan2(lqd.x * hs.y - lqd.y * hs.x, lqd.dot(hs))
    cb, sb = math.cos(beta * 1.5), math.sin(beta * 1.5)
    t0 = Vector((lqd.x * cb - lqd.y * sb, lqd.x * sb + lqd.y * cb))
    B0 = P + t0 * 0.012; B1 = B0 + t0 * Lq * 0.38; B2 = Q - hs * Lq * 0.30; B3 = Q
    def bez(t): return B0 * (1 - t) ** 3 + B1 * 3 * (1 - t) ** 2 * t + B2 * 3 * (1 - t) * t * t + B3 * t ** 3
    curve = [bez(i / 18) for i in range(19)]
    v3 = lambda v, z: (v.x, v.y, z)
    # ---- static: base, pillar, anti-skate dial, cue lever, arm rest
    with kit.props(td=1.8):
        kit.lathe('ta_base', [(0.031, zp), (0.031, zp + 0.004), (0.027, zp + 0.006), (0.0105, zp + 0.006), (0.0095, zp + 0.008), (0.0095, 1.117), (0, 1.117)],
                  m.chrome, segs=28, center=(P.x, P.y, 0))
        ax, ay = P.x + 0.036, P.y - 0.040
        kit.lathe('ta_antiskate', [(0.0085, zp), (0.0085, zp + 0.008), (0.0075, zp + 0.009)], m.knob, segs=20, center=(ax, ay, 0))
        with kit.xform(T(ax, ay, zp + 0.009)): disc('ta_antiskate_top', m.sheet, R['dial_top'], 0.0075, segs=20, rot=90)
        cx_, cy_ = P.x + 0.044, P.y - 0.095
        kit.box('ta_cue_base', cx_ - 0.008, cx_ + 0.008, cy_ - 0.012, cy_ + 0.012, zp, zp + 0.011, m.chrome, skip='-z', bevel=0.002, segs=1)
        kit.tube('ta_cue_lever', [(cx_, cy_ - 0.004, zp + 0.010), (cx_, cy_ - 0.022, zp + 0.016), (cx_, cy_ - 0.030, zp + 0.019)], 0.0018, m.chrome, segs=8)
        kit.cyl('ta_cue_tip', cx_, cy_ - 0.034, zp + 0.016, zp + 0.024, 0.004, m.blackplastic, segs=12)
        # arm rest: where the tube would lie with the arm swung back to rest
        phi_play = math.atan2(line.y, line.x); dl = math.radians(-95) - phi_play
        cp = curve[12] - P; rp_ = P + Vector((cp.x * math.cos(dl) - cp.y * math.sin(dl), cp.x * math.sin(dl) + cp.y * math.cos(dl)))
        kit.cyl('ta_rest_post', rp_.x, rp_.y, zp, zA - 0.007, 0.0035, m.chrome, segs=10, cap='t')
        kit.box('ta_rest_cradle', rp_.x - 0.007, rp_.x + 0.007, rp_.y - 0.004, rp_.y + 0.004, zA - 0.009, zA - 0.004, m.rubber, bevel=0.0012, segs=1)
        kit.box('ta_rest_clip_a', rp_.x - 0.007, rp_.x - 0.005, rp_.y - 0.004, rp_.y + 0.004, zA - 0.004, zA + 0.003, m.rubber)
        kit.box('ta_rest_clip_b', rp_.x + 0.005, rp_.x + 0.007, rp_.y - 0.004, rp_.y + 0.004, zA - 0.004, zA + 0.003, m.rubber)
    # ---- the arm (swings about Z at the pivot)
    t03 = Vector((t0.x, t0.y, 0))
    with kit.interactive('tonearm', origin=tuple(P3), td=2.4):
        kit.lathe('ta_gimbal', [(0.011, 1.117), (0.011, 1.140), (0.009, 1.144), (0.0, 1.145)], m.chrome, segs=20, center=(P.x, P.y, 0))
        kit.box('ta_yoke', P.x - 0.013, P.x + 0.013, P.y - 0.003, P.y + 0.003, zA - 0.006, zA + 0.006, m.alu_dark, bevel=0.0015, segs=1)
        kit.tube('ta_tube', [v3(p, zA) for p in curve], 0.0042, m.chrome, segs=12)
        kit.tube('ta_stub', [v3(P + t0 * 0.004, zA), v3(P - t0 * 0.062, zA)], 0.0045, m.chrome, segs=10)
        cw0 = Vector(v3(P - t0 * 0.056, zA))
        with kit.xform(frame(cw0, t03)):
            kit.lathe('ta_cw', [(0.0045, 0), (0.012, 0), (0.0152, 0.003), (0.0152, 0.025), (0.0125, 0.028), (0.0045, 0.028)], m.chrome, segs=28)
            for k in range(4):
                kit.cyl_patch('ta_cw_scale', 0, 0, 0.0135, 0.0185, 0.01525, k * 90, (k + 1) * 90, m.sheet, uvrect=R['cw_scale'], segs=7)
            kit.lathe('ta_cw_ring', [(0.0153, 0.020), (0.0153, 0.025), (0.0125, 0.028)], m.blackplastic, segs=28)
        ang = math.degrees(math.atan2(hs.y, hs.x))
        with kit.xform(T(Q.x, Q.y, zA) @ Rz(ang)):
            kit.tube('ta_collar', [(-0.006, 0, 0), (0.008, 0, 0)], 0.0056, m.alu_dark, segs=12)
            kit.box('ta_shell', 0.006, 0.056, -0.0095, 0.0095, -0.0025, 0.0005, m.alu, bevel=0.0012, segs=1)
            kit.tube('ta_lift', [(0.050, 0.009, -0.001), (0.058, 0.019, 0.001), (0.063, 0.029, 0.006), (0.064, 0.033, 0.009)], 0.0012, m.chrome, segs=6)
            kit.box('ta_cart', 0.026, 0.048, -0.0082, 0.0082, -0.0155, -0.0025, m.blackplastic, bevel=0.0015, segs=1)
            kit.box('ta_cart_band', 0.0475, 0.0485, -0.0075, 0.0075, -0.012, -0.004, m.brass)
            kit.box('ta_stylus_guard', 0.040, 0.0505, -0.005, 0.005, -0.0168, -0.0145, m.cable_ox)
            kit.tube('ta_cantilever', [(0.042, 0, -0.0150), (0.0452, 0, -0.0186)], 0.0005, m.chrome, segs=5)
    return dict(S=S, rest=rp_, cw=cw0)

def turntable_cable(m):
    pts = [(-0.80, -0.333, 1.050), (-0.80, -0.315, 1.040), (-0.79, -0.285, 1.0245), (-0.78, -0.262, 1.0235), (-0.776, -0.247, 1.012), (-0.775, -0.244, 0.97), (-0.775, -0.246, 0.90)]
    kit.tube('tt_cable', catmull(pts, 4), 0.0028, m.cable, segs=8)

# ============================================================================================ valve amp + preamp
STACK = (0.40, 0.88)

def amp(m, R, meta):
    x0, x1 = STACK; z0 = CRED_Z
    # ---------- preamp / tuner (bottom of the stack)
    pz0, pz1 = z0 + 0.005, z0 + 0.075
    fx0, fx1, fy = x0 + 0.015, x1 - 0.015, 1.1715
    with kit.props(td=1.2):
        for fx in (x0 + 0.04, x1 - 0.04):
            for fy_ in (1.20, 1.43): kit.cyl('pre_foot', fx, fy_, z0, pz0, 0.013, m.rubber, segs=12, cap='t')
        kit.box('pre_body', fx0, fx1, 1.172, 1.47, pz0, pz1, m.crinkle, skip='-z +y -y', bevel=0.002, segs=1)
        for a, b_ in ((x0, fx0), (fx1, x1)):
            kit.box('pre_cheek', a, b_, 1.166, 1.465, pz0, pz1, m.walnut, skip='-z +y', bevel=0.003, segs=2)
    with kit.props(td=1.8):
        fz0, fz1 = pz0 + 0.002, pz1 - 0.002
        fquad('pre_face', fx0, fx1, fz0, fz1, fy, m.sheet, R['pre_front'])
        W, H = fx1 - fx0, fz1 - fz0
        U = lambda u: fx0 + u * W; V = lambda v: fz0 + v * H
        pre = meta['pre']
        for k, reg in (('vu1', 'vu_a'), ('vu2', 'vu_b')):
            u0, v0, u1, v1 = pre[k]
            fquad('pre_' + k, U(u0), U(u1), V(v0), V(v1), fy - 0.0008, m.dials, R[reg])
            for (a0, a1, b0, b1) in ((u0, u1, v1, v1), (u0, u1, v0, v0)):
                kit.box('pre_bezel', U(u0) - 0.002, U(u1) + 0.002, fy - 0.003, fy, (V(b0) - 0.002) if b0 == v0 else V(b0), V(b0) if b0 == v0 else V(b0) + 0.002, m.chrome, skip='+y')
        u0, v0, u1, v1 = pre['tuner']
        fquad('pre_tuner', U(u0), U(u1), V(v0), V(v1), fy - 0.0008, m.dials, R['tuner'])
        for u in pre['knobs']:
            knob('pre_knob', U(u), fy, V(pre['knob_v']), 0.0058, 0.010, m.knob, cap=m.alu_dark, segs=16)
        knob('pre_tune', U(pre['tune'][0]), fy, V(pre['tune'][1]), 0.0125, 0.016, m.knob, skirt=0.002, segs=24, pointer=m.blackplastic)
        jx, jz = U(pre['jack'][0]), V(pre['jack'][1])
        with kit.xform(front(jx, fy, jz)):
            kit.lathe('pre_jack', [(0.0055, 0), (0.0055, 0.002), (0.0035, 0.002), (0.0035, 0.001)], m.chrome, segs=12)
            kit.lathe('hp_plug', [(0.0034, 0.0), (0.0034, 0.004), (0.0048, 0.005), (0.0048, 0.026), (0.004, 0.030), (0.0022, 0.034)], m.chrome, segs=12)
    # ---------- power amplifier (top of the stack)
    az0, az1 = pz1 + 0.003, pz1 + 0.070          # chassis z
    ay0, ay1 = 1.18, 1.47
    with kit.props(td=1.3):
        for fx in (x0 + 0.03, x1 - 0.03):
            for fy_ in (1.21, 1.44): kit.cyl('amp_foot', fx, fy_, pz1, az0, 0.010, m.rubber, segs=10, cap='t')
        kit.box('amp_chassis', x0 + 0.008, x1 - 0.008, ay0, ay1, az0, az1, m.hammer, skip='-z +y -y', bevel=0.003, segs=2)
    with kit.props(td=1.8):
        px0, px1, py = x0 + 0.004, x1 - 0.004, 1.1745
        kit.box('amp_panel', px0, px1, py, ay0 + 0.001, az0 - 0.001, az1 + 0.002, m.alu, skip='-y +y -z', bevel=0.0015, segs=1)
        fquad('amp_face', px0 + 0.0012, px1 - 0.0012, az0 + 0.0003, az1 + 0.0007, py - 0.0001, m.sheet, R['amp_front'])
        W, H = px1 - px0, az1 - az0
        U = lambda u: px0 + u * W; V = lambda v: az0 + v * H
        am = meta['amp']
        for u in am['knobs']:
            knob('amp_knob', U(u), py, V(0.45), 0.0135, 0.020, m.knob, cap=m.blackplastic, skirt=0.0035, segs=20, pointer=m.chrome)
        tx, tz = U(am['toggle']), V(0.45)
        with kit.xform(front(tx, py, tz)):
            kit.lathe('amp_toggle_nut', [(0.0055, 0), (0.0055, 0.004), (0.0035, 0.005), (0.003, 0.005)], m.chrome, segs=6, smooth=False)
        kit.tube('amp_toggle', [(tx, py - 0.004, tz), (tx, py - 0.012, tz + 0.0055), (tx, py - 0.016, tz + 0.008)], 0.0017, m.chrome, segs=8, radii=[0.0018, 0.0016, 0.0022])
        lx, lz = U(am['pilot']), V(0.5)
        with kit.xform(front(lx, py, lz)):
            kit.lathe('amp_pilot_bezel', [(0.0085, 0), (0.0085, 0.003), (0.0065, 0.0045), (0.006, 0.0045)], m.chrome, segs=16)
            kit.lathe('amp_pilot', [(0.006, 0.0045), (0.0052, 0.008), (0.003, 0.0098), (0.0, 0.0103)], m.pilot, segs=14)
    # ---------- valves (centred on layout.POINTS['valves'])
    vx, vy, _ = layout.POINTS['valves']; zc = az1
    with kit.props(td=1.7):
        for i in range(4):
            x = vx + (i - 1.5) * 0.06
            power_valve(m, x, vy, zc)
        for i in range(3):
            small_valve(m, vx + (i - 1) * 0.07, 1.226, zc)
        # transformers + filter capacitors
        for i, (tx_, w, d, h) in enumerate(((0.50, 0.072, 0.062, 0.074), (0.625, 0.072, 0.062, 0.074), (0.775, 0.092, 0.074, 0.088))):
            ty = 1.418
            kit.box('amp_xfmr', tx_ - w / 2, tx_ + w / 2, ty - d / 2, ty + d / 2, zc, zc + h, m.crinkle, skip='-z', bevel=0.007, segs=3)
            kit.box('amp_xfmr_band', tx_ - w / 2 - 0.0015, tx_ + w / 2 + 0.0015, ty - 0.008, ty + 0.008, zc, zc + h * 0.55, m.alu_dark, skip='-z', bevel=0.001, segs=1)
        for cx_ in (0.785, 0.835):
            kit.lathe('amp_cap', [(0.017, zc), (0.017, zc + 0.058), (0.0155, zc + 0.062), (0.006, zc + 0.063), (0.0, zc + 0.064)], m.alu, segs=20, center=(cx_, 1.258, 0))
            kit.lathe('amp_cap_ring', [(0.0185, zc), (0.0185, zc + 0.006), (0.017, zc + 0.007)], m.alu_dark, segs=20, center=(cx_, 1.258, 0))

def power_valve(m, x, y, zc):
    kit.lathe('pv_socket', [(0.024, zc), (0.024, zc + 0.003), (0.021, zc + 0.004)], m.bakelite, segs=20, center=(x, y, 0))
    kit.lathe('pv_base', [(0.0165, zc + 0.003), (0.0165, zc + 0.020), (0.0155, zc + 0.022), (0.0, zc + 0.022)], m.bakelite, segs=20, center=(x, y, 0))
    prof = [(0.0158, zc + 0.022), (0.0175, zc + 0.030), (0.0215, zc + 0.046), (0.0225, zc + 0.062), (0.0215, zc + 0.080), (0.018, zc + 0.094),
            (0.012, zc + 0.104), (0.006, zc + 0.109), (0.0015, zc + 0.111), (0.0, zc + 0.111)]
    kit.lathe('pv_glass', prof, [m.glass, m.getter], segs=16, center=(x, y, 0), mi=[0, 0, 0, 0, 0, 0, 1, 1, 1])
    # electrodes: two plates either side of the glowing heater (gap faces the room), mica spacers
    for s in (-1, 1):
        kit.box('pv_plate', x + s * 0.0045, x + s * 0.0075, y - 0.0085, y + 0.0085, zc + 0.034, zc + 0.084, m.plate)
    kit.box('pv_plate_side', x - 0.0075, x + 0.0075, y + 0.0078, y + 0.0085, zc + 0.034, zc + 0.084, m.plate)
    kit.cyl('pv_heater', x, y, zc + 0.030, zc + 0.088, 0.0022, m.heater, segs=8)
    kit.cyl('pv_glow_base', x, y, zc + 0.022, zc + 0.024, 0.0125, m.heater_dim, segs=16, cap='t')
    for zz in (zc + 0.031, zc + 0.087):
        kit.box('pv_mica', x - 0.013, x + 0.013, y - 0.011, y + 0.011, zz, zz + 0.0012, m.mica)

def small_valve(m, x, y, zc):
    kit.lathe('sv_socket', [(0.0135, zc), (0.0135, zc + 0.004), (0.0115, zc + 0.005)], m.bakelite, segs=16, center=(x, y, 0))
    prof = [(0.0102, zc + 0.004), (0.0102, zc + 0.042), (0.0094, zc + 0.047), (0.006, zc + 0.050), (0.002, zc + 0.052), (0.0006, zc + 0.0545), (0.0, zc + 0.0545)]
    kit.lathe('sv_glass', prof, [m.glass, m.getter], segs=16, center=(x, y, 0), mi=[0, 1, 1, 1, 1, 1])
    for s in (-1, 1):
        kit.box('sv_plate', x + s * 0.0028, x + s * 0.0046, y - 0.005, y + 0.005, zc + 0.012, zc + 0.034, m.plate)
    kit.cyl('sv_heater', x, y, zc + 0.010, zc + 0.037, 0.0013, m.heater, segs=6)
    kit.box('sv_mica', x - 0.008, x + 0.008, y - 0.0065, y + 0.0065, zc + 0.0355, zc + 0.0365, m.mica)

# ============================================================================================ reel-to-reel
def tangent_pts(c1, r1, c2, r2, side):
    """external tangent between two circles in XZ, on the side where the normal's x has sign `side`"""
    d = c2 - c1; D = d.length; u = d / D
    cth = (r1 - r2) / D; sth = math.sqrt(max(0.0, 1 - cth * cth)); best = None
    for s in (1, -1):
        n = Vector((u.x * cth - s * u.y * sth, s * u.x * sth + u.y * cth))
        if best is None or n.x * side > best.x * side: best = n
    return c1 + best * r1, c2 + best * r2, best

def reel_deck(m, R, meta):
    X0, X1 = layout.CRED_REEL; z0 = CRED_Z; ztop = 1.35
    yf = 1.28                                    # front panel plane
    hl = Vector(layout.INTERACTIVE['reel_l'][1]); hr = Vector(layout.INTERACTIVE['reel_r'][1])
    yt = hl.y                                     # tape centre plane
    with kit.props(td=1.0):
        for fx in (X0 + 0.04, X1 - 0.04): kit.cyl('rr_foot', fx, 1.33, z0, z0 + 0.005, 0.014, m.rubber, segs=12, cap='t')
        kit.box('rr_body', X0 + 0.015, X1 - 0.015, yf + 0.004, 1.55, z0 + 0.005, ztop - 0.002, m.crinkle, skip='-z +y -y', bevel=0.002, segs=1)
        for a, b_ in ((X0, X0 + 0.015), (X1 - 0.015, X1)):
            kit.box('rr_cheek', a, b_, yf - 0.005, 1.55, z0 + 0.005, ztop, m.walnut_v, skip='-z +y', bevel=0.003, segs=2)
    with kit.props(td=1.5):
        px0, px1 = X0 + 0.015, X1 - 0.015
        kit.box('rr_upper', px0, px1, yf, yf + 0.006, 1.073, ztop - 0.003, m.alu, skip='+y', bevel=0.0015, segs=1)
        kit.box('rr_lower_back', px0, px1, yf, yf + 0.006, z0 + 0.005, 1.073, m.blackpaint, skip='+y -y')
        lz0, lz1 = z0 + 0.0175, 1.0705
        fquad('rr_lower', px0, px1, lz0, lz1, yf - 0.0002, m.sheet, R['reel_lower'])
        kit.box('rr_kick', px0, px1, yf - 0.001, yf + 0.006, z0 + 0.005, lz0, m.blackpaint, skip='+y -z')
        W, H = px1 - px0, lz1 - lz0
        U = lambda u: px0 + u * W; V = lambda v: lz0 + v * H
        rl = meta['reel']; fy = yf - 0.0003
        for k in ('vu1', 'vu2'):
            u0, v0, u1, v1 = rl[k]; fquad('rr_' + k, U(u0), U(u1), V(v0), V(v1), fy - 0.0006, m.dials, R['vu_rest'])
        u0, v0, u1, v1 = rl['counter']; fquad('rr_counter', U(u0), U(u1), V(v0), V(v1), fy - 0.0006, m.sheet, R['counter'])
        knob('rr_reset', U(rl['reset'][0]), fy, V(rl['reset'][1]), 0.003, 0.004, m.chrome, segs=10)
        for i, u in enumerate(rl['levers']):
            lx, lzz = U(u), V(rl['lever_v'])
            kit.tube('rr_lever', [(lx, fy, lzz), (lx, fy - 0.016, lzz - 0.003), (lx, fy - 0.026, lzz - 0.006)], 0.0022, m.chrome, segs=8)
            kit.box('rr_lever_tip', lx - 0.006, lx + 0.006, fy - 0.040, fy - 0.024, lzz - 0.011, lzz - 0.002, m.blackplastic if i < 2 else m.cable_ox, bevel=0.002, segs=1)
        for u in rl['knobs']:
            knob('rr_knob', U(u), fy, V(rl['knob_v']), 0.0065, 0.010, m.knob, cap=m.blackplastic, segs=16)
        knob('rr_speed', U(rl['speed'][0]), fy, V(rl['speed'][1]), 0.008, 0.010, m.blackplastic, segs=16, pointer=m.chrome)
        px_, pzz = U(rl['power'][0]), V(rl['power'][1])
        kit.box('rr_power', px_ - 0.011, px_ + 0.011, fy - 0.010, fy, pzz - 0.007, pzz + 0.007, m.blackplastic, skip='+y', bevel=0.002, segs=1)
        with kit.xform(front(U(rl['pilot'][0]), fy, V(rl['pilot'][1]))):
            kit.lathe('rr_pilot', [(0.0045, 0), (0.0045, 0.0015), (0.003, 0.004), (0, 0.0045)], m.amber, segs=12)
        # ---- tape path: supply pack -> guide -> under the heads, capstan -> guide -> take-up pack
        rL, rR = 0.072, 0.040
        gL, gR, gr = Vector((-1.205, 1.116)), Vector((-0.795, 1.116)), 0.009
        cL, cR = Vector((hl.x, hl.z)), Vector((hr.x, hr.z))
        a1, a2, nA = tangent_pts(cL, rL, gL, gr, -1)
        b1, b2, nB = tangent_pts(gR, gr, cR, rR, +1)
        path = [a1, a2]
        aa = math.atan2(nA.y, nA.x) % (2 * math.pi)
        for k in range(1, 7):
            t = aa + (1.5 * math.pi - aa) * k / 6; path.append(gL + Vector((math.cos(t), math.sin(t))) * gr)
        ab = math.atan2(nB.y, nB.x) % (2 * math.pi)
        if ab < 1.5 * math.pi: ab += 2 * math.pi
        for k in range(0, 7):
            t = 1.5 * math.pi + (ab - 1.5 * math.pi) * k / 6; path.append(gR + Vector((math.cos(t), math.sin(t))) * gr)
        path.append(b2)
        ztape = gL.y - gr
        sweep('rr_tape', [(p.x, yt, p.y) for p in path], (0, 1, 0), 0.0064, 0.0025, m.tape)
        # guide rollers + tension arms
        for g, sx in ((gL, -1), (gR, 1)):
            with kit.xform(front(g.x, yf, g.y)):
                kit.lathe('rr_guide', [(0.004, 0), (0.004, 0.012), (gr, 0.0125), (gr, 0.0265), (gr - 0.0015, 0.028), (0.0, 0.028)], m.chrome, segs=16)
            ax_ = g.x - sx * 0.012
            kit.tube('rr_tension_arm', [(ax_, yf - 0.004, g.y + 0.050), (g.x, yf - 0.004, g.y)], 0.0025, m.chrome, segs=8)
            with kit.xform(front(ax_, yf, g.y + 0.050)): kit.lathe('rr_arm_hub', [(0.007, 0), (0.007, 0.006), (0.0055, 0.0075), (0, 0.0075)], m.alu_dark, segs=14)
        # head block: cover above the tape, three heads touching it from above
        kit.box('rr_headcover', -1.052, -0.935, yt - 0.009, yf, ztape + 0.0075, ztape + 0.060, m.blackpaint, skip='+y', bevel=0.004, segs=2)
        kit.box('rr_headtrim', -1.050, -0.937, yt - 0.0095, yt - 0.007, ztape + 0.040, ztape + 0.046, m.chrome, skip='+y')
        for hx in (-1.030, -0.997, -0.964):
            kit.box('rr_head', hx - 0.0065, hx + 0.0065, yt - 0.0045, yt + 0.0045, ztape + 0.0009, ztape + 0.0085, m.chrome, bevel=0.0018, segs=2)
        cpx = -0.900
        with kit.xform(front(cpx, yf, ztape + 0.0034)):
            kit.lathe('rr_capstan_pin', [(0.0026, 0), (0.0026, 0.030), (0.0, 0.0305)], m.chrome, segs=10)
        with kit.xform(front(cpx, yf, ztape - 0.0118)):
            kit.lathe('rr_pinch', [(0.004, 0), (0.004, 0.012), (0.0115, 0.0135), (0.0115, 0.0265), (0.010, 0.028), (0.0, 0.028)], m.rubber, segs=18)
        kit.tube('rr_pinch_arm', [(cpx + 0.03, yf - 0.006, ztape - 0.03), (cpx, yf - 0.006, ztape - 0.0118)], 0.003, m.alu_dark, segs=8)
    # ---- the two reels (interactive, spin about Y)
    for name, hc, rpack, pm in (('reel_l', hl, rL, m.pack_l), ('reel_r', hr, rR, m.pack_r)):
        with kit.interactive(name, origin=tuple(hc), td=2.0):
            with kit.xform(front(hc.x, hc.y, hc.z)):
                win = [(1, 12), (17, 28), (33, 44)]
                flange(name + '_front', m.alu, [0.0075, 0.026, 0.034, 0.078, 0.0889], 48, win, z=0.0058)
                flange(name + '_back', m.alu_dark, [0.0075, 0.026, 0.034, 0.078, 0.0889], 48, win, z=-0.0058)
                kit.lathe(name + '_rim', [(0.0889, 0.0048), (0.0889, 0.0068), (0.0875, 0.0072)], m.alu, segs=48)
                kit.lathe(name + '_pack', [(rpack, -0.0032), (rpack, 0.0032), (0.026, 0.0032)], pm, segs=48)
                kit.lathe(name + '_hub', [(0.0075, 0.0058), (0.0075, 0.012), (0.006, 0.014), (0.0, 0.014)], m.chrome, segs=16)
                kit.cyl(name + '_cap', 0, 0, 0.014, 0.017, 0.012, m.blackplastic, segs=16)
                for k in range(3):
                    with kit.xform(Rz(k * 120 + 15)):
                        kit.box(name + '_prong', 0.010, 0.017, -0.002, 0.002, 0.014, 0.0165, m.blackplastic)
    return dict(path=path)

# ============================================================================================ now playing
def nowplaying(m, R):
    piv = Vector(layout.INTERACTIVE['nowplaying'][1]); sx = 0.315 / 2; lean = 12.0
    x0, x1 = layout.CRED_NOWPLAYING
    with kit.props(td=1.4):
        kit.box('np_ledge', x0 + 0.025, x1 - 0.025, 1.343, 1.405, CRED_Z, piv.z, m.oak, skip='-z', bevel=0.002, segs=1)
        kit.box('np_lip', x0 + 0.025, x1 - 0.025, 1.343, 1.356, piv.z, piv.z + 0.026, m.oak, skip='-z', bevel=0.002, segs=1)
        tl = math.tan(math.radians(lean))
        kit.tube('np_mast', [(piv.x, 1.397, piv.z - 0.003), (piv.x, 1.397 + 0.345 * tl, piv.z + 0.342)], 0.008, m.oak, segs=4)
        kit.tube('np_leg', [(piv.x, 1.397 + 0.29 * tl, piv.z + 0.29), (piv.x, 1.548, CRED_Z + 0.002)], 0.007, m.oak, segs=4)
        kit.box('np_plate', piv.x - 0.036, piv.x + 0.036, 1.3415, 1.343, piv.z + 0.0035, piv.z + 0.0225, m.brass, skip='+y', bevel=0.0005, segs=1)
    with kit.props(td=2.4):
        fquad('np_plate_face', piv.x - 0.0355, piv.x + 0.0355, piv.z + 0.004, piv.z + 0.022, 1.3413, m.sheet, R['np_plate'])
    with kit.interactive('nowplaying', origin=tuple(piv), td=2.6):
        with kit.xform(T(piv.x, piv.y, piv.z) @ Rx(-lean)):
            fquad('np_cover', -sx, sx, 0.0, 0.315, 0.0, m.close, (0.0, 0.0, 0.5, 1.0))
            with kit.props(td=0.6):
                kit.box('np_sleeve', -sx, sx, 0.0002, 0.0032, 0.0, 0.315, m.card, skip='-y -z', bevel=0.0006, segs=1)

# ============================================================================================ speakers
def speaker(m, R, meta, S, tag):
    x0, x1, y0, y1, z0, z1 = S['x0'], S['x1'], S['y0'], S['y1'], S['z0'], S['z1']
    xc = (x0 + x1) / 2; t = 0.022; outer = '-x' if xc < 0 else '+x'
    zb = z0 + 0.03                                   # cabinet bottom (on a recessed plinth)
    yb = y0 + 0.016                                  # baffle front (recessed)
    with kit.props(td=0.55):
        kit.box('spk_plinth', x0 + 0.03, x1 - 0.03, y0 + 0.03, y1, z0, zb, m.blackpaint, skip='-z +y ' + outer)
        kit.box('spk_top', x0, x1, y0, y1, z1 - t, z1, m.walnut_v, skip='+y', bevel=0.004, segs=2)
        kit.box('spk_bottom', x0, x1, y0, y1, zb, zb + t, m.walnut_v, skip='+y -z', bevel=0.004, segs=2)
        for a, b_, inner, out_ in ((x0, x0 + t, '+x', '-x'), (x1 - t, x1, '-x', '+x')):
            sk = '+y ' + inner + (' ' + out_ if out_ == outer else '')
            kit.box('spk_side', a, b_, y0, y1, zb + t - 0.002, z1 - t + 0.002, m.walnut_v, skip=sk, bevel=0.004, segs=2)
    # baffle with holes (boolean)
    wz, hz, pz = zb + 0.32, zb + 0.70, zb + 0.072
    with kit.props(td=0.7):
        holed_box('spk_baffle', m.baffle, x0 + t, x1 - t, yb, yb + 0.022, zb + t, z1 - t, axis='y', drop='+y',
               holes=[('c', xc, wz, 0.172), ('r', xc, hz, 0.150, 0.050), ('c', xc - 0.215, pz, 0.033), ('c', xc + 0.215, pz, 0.033)])
    with kit.props(td=1.0):
        # 15-inch woofer
        with kit.xform(front(xc, yb, wz)):
            kit.lathe('spk_frame', [(0.193, 0.0), (0.193, 0.004), (0.189, 0.0065), (0.173, 0.0065), (0.171, 0.004), (0.171, -0.012)], m.horn, segs=32)
            roll = [(0.1615 + 0.0085 * math.cos(math.radians(a)), -0.006 + 0.0085 * math.sin(math.radians(a))) for a in range(0, 181, 45)]
            kit.lathe('spk_surround', [(0.171, -0.006)] + roll, m.rubber, segs=32)
            cone = []
            for i in range(5):
                f = i / 4; cone.append((0.153 - (0.153 - 0.056) * f, -0.006 - 0.072 * (f ** 0.8)))
            kit.lathe('spk_cone', cone, m.cone, segs=32)
            cap = [(0.056 * math.cos(math.radians(a)), -0.078 + 0.030 * math.sin(math.radians(a))) for a in range(0, 91, 30)]
            kit.lathe('spk_dustcap', cap, m.felt, segs=24)
            for k in range(8):
                a = math.radians(22.5 + k * 45)
                kit.lathe('spk_bolt', [(0.0045, 0.0065), (0.004, 0.0085), (0.0, 0.0095)], m.chrome, segs=8, center=(0.182 * math.cos(a), 0.182 * math.sin(a), 0))
        # horn
        with kit.xform(front(xc, yb, hz)):
            horn(m, 0.150, 0.050, 0.13)
        # reflex ports
        for px in (xc - 0.215, xc + 0.215):
            with kit.xform(front(px, yb, pz)):
                kit.lathe('spk_port', [(0.039, 0.0), (0.039, 0.003), (0.035, 0.0045), (0.033, 0.003), (0.033, -0.16), (0.0, -0.16)], m.blackplastic, segs=16)
        # level control plate with badge
        pw, ph = 0.19, 0.0697; ptz = z1 - t - 0.085
        kit.box('spk_plate_back', xc - pw / 2, xc + pw / 2, yb - 0.002, yb, ptz - ph / 2, ptz + ph / 2, m.alu, skip='+y -y', bevel=0.0008, segs=1)
    with kit.props(td=1.6):
        fquad('spk_plate', xc - pw / 2, xc + pw / 2, ptz - ph / 2, ptz + ph / 2, yb - 0.002, m.sheet, R['spk_plate'])
        for u in meta['spk']['knobs']:
            knob('spk_knob', xc - pw / 2 + u * pw, yb - 0.002, ptz - ph / 2 + 0.45 * ph, 0.0085, 0.012, m.knob, cap=m.blackplastic, skirt=0.002, segs=14, pointer=m.chrome)

def holed_box(name, mat, x0, x1, y0, y1, z0, z1, holes, axis='y', drop='+y'):
    """box with through-holes (boolean). holes: ('c', u, w, r) circle or ('r', u, w, hu, hw) rectangle, where (u, w) are
    (x, z) for axis 'y' and (x, y) for axis 'z'. The face whose normal is `drop` is deleted (hidden side)."""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    cutters = []
    for h in holes:
        cb = bmesh.new()
        if h[0] == 'c':
            _, cu, cw, r = h
            bmesh.ops.create_cone(cb, cap_ends=True, segments=48 if r > 0.1 else 20, radius1=r, radius2=r, depth=0.2)
            if axis == 'y': cb.transform(Matrix.Translation((cu, (y0 + y1) / 2, cw)) @ Rx(90))
            else: cb.transform(Matrix.Translation((cu, cw, (z0 + z1) / 2)))
        else:
            _, cu, cw, hu, hw = h
            bmesh.ops.create_cube(cb, size=1.0)
            for v in cb.verts:
                if axis == 'y': v.co = Vector((cu + v.co.x * 2 * hu, (y0 + y1) / 2 + v.co.y * 0.2, cw + v.co.z * 2 * hw))
                else: v.co = Vector((cu + v.co.x * 2 * hu, cw + v.co.y * 2 * hw, (z0 + z1) / 2 + v.co.z * 0.2))
        cm = bpy.data.meshes.new(name + '_cut'); cb.to_mesh(cm); cb.free(); cm.materials.append(mat)
        co = bpy.data.objects.new(name + '_cut', cm); bpy.context.scene.collection.objects.link(co); co.hide_render = True
        md = ob.modifiers.new('cut', 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = co
        cutters.append(co)
    ob = kit.adopt(ob, smooth=False)
    dv = kit.AX[drop]; lim = {'+y': y1, '-y': y0, '+z': z1, '-z': z0}[drop]
    bm = bmesh.new(); bm.from_mesh(ob.data)
    dead = [f for f in bm.faces if f.normal.dot(dv) > 0.999 and abs(f.calc_center_median().dot(dv) - lim * (1 if drop[0] == '+' else -1)) < 1e-4]
    bmesh.ops.delete(bm, geom=dead, context='FACES'); bm.to_mesh(ob.data); bm.free()
    for co in cutters:
        me_ = co.data; bpy.data.objects.remove(co, do_unlink=True); bpy.data.meshes.remove(me_)
    return ob

def horn(m, hw, hh, depth):
    """rectangular flared horn in local coords (mouth at z=0 facing +z, throat at z=-depth) + vanes + flange"""
    rings = []
    for i in range(6):
        f = i / 5; k = (1 - f) ** 1.8
        w = 0.018 + (hw - 0.018) * k; h = 0.011 + (hh - 0.011) * k
        rings.append((w, h, -depth * f))
    bm = bmesh.new()
    V = [[bm.verts.new((sx * w, sy * h, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))] for (w, h, z) in rings]
    for i in range(len(V) - 1):
        A, B = V[i], V[i + 1]
        for j in range(4):
            j2 = (j + 1) % 4; bm.faces.new((A[j], B[j], B[j2], A[j2]))
    bm.faces.new(list(reversed(V[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces: f.normal_flip()      # look into the horn
    kit.finish('spk_horn', bm, m.horn)
    for fx in (-0.6, -0.2, 0.2, 0.6):
        pts = [(fx * w, -h, z) for (w, h, z) in rings[:4]]; top = [(fx * w, h, z) for (w, h, z) in rings[:4]]
        for s in (0, 1):
            for i in range(3):
                q = [pts[i], pts[i + 1], top[i + 1], top[i]]
                kit.quad('spk_vane', q if s else list(reversed(q)), m.horn)
    fw = 0.016
    for (a0, a1, b0, b1) in ((-hw - fw, hw + fw, hh, hh + fw), (-hw - fw, hw + fw, -hh - fw, -hh), (-hw - fw, -hw, -hh, hh), (hw, hw + fw, -hh, hh)):
        kit.box('spk_horn_flange', a0, a1, b0, b1, 0.0, 0.006, m.horn, skip='-z', bevel=0.0015, segs=1)

# ============================================================================================ headphones + cables
def headphones(m):
    hx = 0.322; cups = (1.195, 1.365); z0 = CRED_Z
    with kit.props(td=1.2):
        for cy in cups:
            kit.lathe('hp_cushion', [(0.030, z0 + 0.016), (0.030, z0 + 0.004), (0.036, z0 + 0.0), (0.048, z0 + 0.0005), (0.052, z0 + 0.008), (0.050, z0 + 0.016)][::-1],
                      m.cushion, segs=28, center=(hx, cy, 0))
            kit.lathe('hp_shell', [(0.052, z0 + 0.016), (0.053, z0 + 0.022), (0.051, z0 + 0.034), (0.044, z0 + 0.042), (0.025, z0 + 0.046), (0.0, z0 + 0.047)],
                      m.hpshell, segs=28, center=(hx, cy, 0))
            kit.lathe('hp_trim', [(0.0535, z0 + 0.0215), (0.0535, z0 + 0.0255), (0.0525, z0 + 0.026)], m.chrome, segs=28, center=(hx, cy, 0))
            kit.lathe('hp_badge', [(0.018, z0 + 0.0468), (0.018, z0 + 0.0478), (0.0, z0 + 0.048)], m.chrome, segs=20, center=(hx, cy, 0))
            # yoke: U-fork from the cup's pivots (on +-x) up over the cup
            yk = [(hx - 0.056, cy, z0 + 0.024), (hx - 0.058, cy, z0 + 0.048), (hx - 0.040, cy, z0 + 0.064), (hx, cy, z0 + 0.068),
                  (hx + 0.040, cy, z0 + 0.064), (hx + 0.058, cy, z0 + 0.048), (hx + 0.056, cy, z0 + 0.024)]
            kit.tube('hp_yoke', catmull(yk, 3), 0.0028, m.chrome, segs=8)
            for s in (-1, 1):
                kit.cyl('hp_pivot', hx + s * 0.056, cy, z0 + 0.019, z0 + 0.029, 0.005, m.chrome, segs=10)
        # headband: arc over the two cups (in the YZ plane)
        yc = (cups[0] + cups[1]) / 2; rr = (cups[1] - cups[0]) / 2; zb = z0 + 0.068
        arc = [(hx, yc - rr * math.cos(math.radians(a)), zb + 0.012 + rr * 1.05 * math.sin(math.radians(a))) for a in range(0, 181, 12)]
        arc = [(hx, cups[0], zb)] + arc + [(hx, cups[1], zb)]
        sweep('hp_band', arc, (1, 0, 0), 0.026, 0.004, m.chrome)
        pad = [(hx, yc - rr * 0.92 * math.cos(math.radians(a)), zb + 0.012 + rr * 1.05 * math.sin(math.radians(a)) - 0.008) for a in range(24, 157, 12)]
        sweep('hp_pad', pad, (1, 0, 0), 0.040, 0.012, m.cushion, caps=True)
    # coiled cord: from the front cup, over the credenza edge in a loose loop, up into the preamp's PHONES jack
    pre = dict(x0=STACK[0] + 0.015, w=STACK[1] - STACK[0] - 0.03)
    jx = pre['x0'] + 0.035 * pre['w']; jz = CRED_Z + 0.007 + 0.35 * 0.066
    with kit.props(td=0.8):
        kit.tube('hp_cord_a', [(hx + 0.030, cups[0] - 0.045, z0 + 0.012), (hx + 0.036, cups[0] - 0.060, z0 + 0.004), (hx + 0.038, 1.120, z0 + 0.003)], 0.0022, m.cable, segs=6)
        path = [(hx + 0.038, 1.120, z0 + 0.003), (hx + 0.040, 1.100, z0 - 0.012), (hx + 0.046, 1.094, z0 - 0.055), (hx + 0.065, 1.093, z0 - 0.080),
                (hx + 0.090, 1.094, z0 - 0.070), (jx + 0.004, 1.098, z0 - 0.035), (jx + 0.002, 1.110, z0 + 0.004), (jx, 1.128, jz - 0.004), (jx, 1.140, jz)]
        c = catmull(path, 6)
        kit.tube('hp_cord_coil', coil(c[1:-3], 0.0055, 0.0095, 5), 0.0018, m.cable, segs=4, caps=False)
        kit.tube('hp_cord_b', [tuple(c[-4]), tuple(c[-2]), (jx, 1.1365, jz)], 0.0022, m.cable, segs=6)

def cables(m):
    with kit.props(td=0.4):
        z = CRED_Z + 0.004
        # amp -> right speaker, along the wall behind the now-playing easel
        kit.tube('cab_spk_r', catmull([(0.86, 1.46, 0.95), (0.89, 1.52, z + 0.004), (0.95, 1.574, z), (1.30, 1.578, z), (1.345, 1.575, z + 0.02), (1.352, 1.57, 0.99)], 4),
                 0.0045, m.cable_ox, segs=8)
        # reel deck -> credenza back, behind the bottles
        kit.tube('cab_reel', catmull([(-0.77, 1.54, 1.02), (-0.745, 1.565, 0.96), (-0.72, 1.578, z), (-0.68, 1.584, z)], 4), 0.003, m.cable, segs=6)
        # left speaker cable disappearing behind the reel deck
        kit.tube('cab_spk_l', catmull([(-1.352, 1.57, 0.99), (-1.345, 1.575, z + 0.02), (-1.30, 1.578, z), (-1.24, 1.572, z)], 4), 0.0045, m.cable_ox, segs=8)
        # pre <-> amp interconnects at the back
        for i, col in enumerate((m.cable, m.cable_ox)):
            x = 0.62 + i * 0.03
            kit.tube('cab_ic', catmull([(x, 1.47, 0.95), (x + 0.01, 1.50, 0.975), (x + 0.02, 1.49, 1.0), (x + 0.02, 1.47, 1.01)], 4), 0.0028, col, segs=6)

# ============================================================================================ build
def build():
    meta = json.load(open(os.path.join(TEX, 'regions.json')))
    R = {k: tuple(v) for k, v in meta['regions'].items()}
    m = make_mats()
    with kit.props(atlas='hifi_b'):
        turntable(m, R)
        tonearm(m, R)
        turntable_cable(m)
        nowplaying(m, R)
    with kit.props(atlas='hifi'):
        amp(m, R, meta)
        reel_deck(m, R, meta)
        speaker(m, R, meta, layout.SPEAKER_L, 'l')
        speaker(m, R, meta, layout.SPEAKER_R, 'r')
        headphones(m)
        cables(m)

LIGHTS = []
