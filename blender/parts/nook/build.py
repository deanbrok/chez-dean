"""NOOK — the little kitchen behind the bar, and the kitchen table where the owner writes after closing.
Furnishing only (the shell agent builds floor / walls / ceiling / window / opening frame).
Textures are painted by tex.py into tex/ (build() only reads them).
"""
import math, os
import bmesh
from mathutils import Vector, Matrix
from barkit import kit, mats, layout
from barkit.kit import T, Rx, Ry, Rz

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = HERE + '/tex/paper.png'
PRINT = HERE + '/tex/print.png'
S = 2048.0
REG = dict(   # mirrors tex.py REG (pixels, top-left origin)
    ms_top=(0, 0, 1040, 1440), ms_done=(1040, 0, 2048, 1396), can=(0, 1440, 900, 1830), ink=(900, 1440, 1100, 1600),
    dict_cover=(1100, 1440, 1400, 1878), dict_spine=(1400, 1440, 1540, 1878), dict_edge=(1540, 1440, 1700, 1878),
    eraser=(1700, 1440, 1900, 1540),
    noren=(0, 0, 1600, 716), calendar=(1600, 0, 2048, 640), radio=(0, 720, 800, 1220),
    tin_tea=(800, 720, 1400, 920), tin_coffee=(800, 920, 1400, 1120), tin_biscuit=(1400, 720, 2048, 920),
    jar_a=(1400, 920, 1700, 1120), jar_b=(1700, 920, 2000, 1120), soy=(0, 1230, 300, 1530), oil=(300, 1230, 600, 1530),
    badge=(600, 1230, 900, 1330),
)
AX = kit.AX
M = {}

def R(reg, u, v):
    """(u, v) in 0..1 of a painted region (v=0 bottom) -> image uv"""
    x0, y0, x1, y1 = REG[reg]
    return ((x0 + u * (x1 - x0)) / S, 1.0 - (y1 - v * (y1 - y0)) / S)

def Rrect(reg):
    (u0, v0), (u1, v1) = R(reg, 0, 0), R(reg, 1, 1)
    return (u0, v0, u1, v1)

def SC(x, y, z): return Matrix.Diagonal((x, y, z, 1.0))

# ------------------------------------------------------------------------------------------------ mesh helpers
def tbox(name, x0, x1, y0, y1, z0, z1, mat, img=None, faces=None, bevel=0.0, segs=2, skip=()):
    """kit.box with painted faces: faces = {'-y': (region, rot_degrees)} -> material index 1 (img) + uv_tex"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    bm.normal_update()
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=segs, affect='EDGES', profile=0.5); bm.normal_update()
    uvl = bm.loops.layers.uv.new('uv_tex')
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    proj = {'-y': lambda c: ((c.x - x0) / dx, (c.z - z0) / dz), '+y': lambda c: ((x1 - c.x) / dx, (c.z - z0) / dz),
            '-x': lambda c: ((y1 - c.y) / dy, (c.z - z0) / dz), '+x': lambda c: ((c.y - y0) / dy, (c.z - z0) / dz),
            '+z': lambda c: ((c.x - x0) / dx, (c.y - y0) / dy)}
    for f in bm.faces:
        for k, spec in (faces or {}).items():
            if f.normal.dot(AX[k]) > 0.999:
                reg, rot = spec if isinstance(spec, tuple) else (spec, 0)
                f.material_index = 1
                for l in f.loops:
                    u, v = proj[k](l.vert.co)
                    for _ in range(int(rot) // 90 % 4): u, v = v, 1 - u
                    l[uvl].uv = R(reg, min(1, max(0, u)), min(1, max(0, v)))
    if isinstance(skip, str): skip = skip.split()
    if skip:
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(f.normal.dot(AX[k]) > 0.999 for k in skip)], context='FACES')
    return kit.finish(name, bm, [mat, img] if img else [mat])

def grid(name, nx, ny, fn, mat, reg=None, uvfn=None, smooth=True, rot=0):
    """parametric sheet: fn(u, v) -> (x, y, z); faces wind so that the normal = d/du x d/dv"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('uv_tex')
    vs = [[bm.verts.new(fn(i / nx, j / ny)) for i in range(nx + 1)] for j in range(ny + 1)]
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                u, v = a / nx, b / ny
                for _ in range(rot // 90 % 4): u, v = v, 1 - u
                if uvfn: l[uvl].uv = uvfn(u, v)
                elif reg: l[uvl].uv = R(reg, u, v)
                else: l[uvl].uv = (u, v)
    return kit.finish(name, bm, mat, smooth=smooth)

def rrect(w, d, r, n=5):
    """rounded rectangle outline (CCW), centred at the origin"""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def slab(name, outline, layers, mats_, top_mi=0, side_mi=None, cap_top=True):
    """extrude a CCW outline through layers [(inset, z), ...] (bottom->top). side band i gets material side_mi[i]."""
    bm = bmesh.new(); rings = []
    cx = sum(p[0] for p in outline) / len(outline); cy = sum(p[1] for p in outline) / len(outline)
    for ins, z in layers:
        ring = []
        for (x, y) in outline:
            dx, dy = x - cx, y - cy; L = math.hypot(dx, dy) or 1
            ring.append(bm.verts.new((x - dx / L * ins, y - dy / L * ins, z)))
        rings.append(ring)
    n = len(outline)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        for j in range(n):
            f = bm.faces.new((A[j], A[(j + 1) % n], B[(j + 1) % n], B[j]))
            if side_mi: f.material_index = side_mi[i]
    if cap_top:
        f = bm.faces.new(rings[-1]); f.material_index = top_mi
    return kit.finish(name, bm, mats_, smooth=True, sharp=40)

def basin(name, x0, x1, y0, y1, z0, z1, mat, bevel=0.012):
    """open box seen from inside (sink)"""
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector(((x0 + x1) / 2 + v.co.x * (x1 - x0), (y0 + y1) / 2 + v.co.y * (y1 - y0), (z0 + z1) / 2 + v.co.z * (z1 - z0)))
    bm.normal_update()
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if not all(v.co.z > z1 - 1e-6 for v in e.verts)], offset=bevel, segments=2, affect='EDGES', profile=0.5)
    bm.normal_update()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z > 0.999 and f.calc_center_median().z > z1 - 1e-6], context='FACES')
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return kit.finish(name, bm, mat, smooth=True, sharp=50)

def helix(p0, p1, r, turns, phase, n):
    p0, p1 = Vector(p0), Vector(p1)
    return [tuple(p0 + (p1 - p0) * (i / (n - 1)) + Vector((r * math.cos(phase + 2 * math.pi * turns * i / (n - 1)), r * math.sin(phase + 2 * math.pi * turns * i / (n - 1)), 0))) for i in range(n)]

# ------------------------------------------------------------------------------------------------ materials
def materials():
    m = M
    m['paper'] = mats.image('nook_paper', PAPER, rough=0.78)
    m['print'] = mats.image('nook_print', PRINT, rough=0.62)
    m['label'] = mats.image('nook_label', PRINT, rough=0.45, coat=0.25)
    m['dict'] = mats.image('nook_dictcloth', PAPER, rough=0.7)
    m['can'] = mats.image('nook_canprint', PAPER, rough=0.28, coat=0.4)
    # noren: painted cloth with light coming through from the nook
    nm, nt, b, out = mats.base('nook_noren')
    uv = mats.N(nt, 'ShaderNodeUVMap'); uv.uv_map = 'uv_tex'
    t = mats.N(nt, 'ShaderNodeTexImage'); t.image = mats.bpy.data.images.load(PRINT, check_existing=True); t.name = 'SRC'
    mats.L(nt, uv.outputs[0], t.inputs[0]); mats.L(nt, t.outputs[0], b.inputs['Base Color'])
    mats.setp(b, rough=0.85, sheen=0.4)
    tr = mats.N(nt, 'ShaderNodeBsdfTranslucent'); mats.L(nt, t.outputs[0], tr.inputs[0])
    mx = mats.N(nt, 'ShaderNodeMixShader'); mx.inputs[0].default_value = 0.3
    mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2]); mats.L(nt, mx.outputs[0], out.inputs[0])
    m['noren'] = nm
    m['laminate'] = mats.noisy('nook_laminate', (0.66, 0.60, 0.45), (0.74, 0.69, 0.55), rough=0.3, scale=90, rvar=0.12, bmp=0.02)
    mats.setp(m['laminate'].node_tree.nodes['Principled BSDF'], coat=0.25, coat_rough=0.2)
    # ribbed aluminium edge strip
    am, nt, b, _ = mats.base('nook_edgestrip')
    mats.setp(b, col=(0.70, 0.69, 0.66), metal=1.0, rough=0.32)
    wv = mats.N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); wv.inputs['Scale'].default_value = 140
    mats.L(nt, mats.coords(nt), wv.inputs['Vector']); mats.bump(nt, b, wv.outputs[1], 0.35, 0.0008)
    m['edge'] = am
    m['chrome'] = mats.metal('nook_chrome', (0.86, 0.86, 0.85), rough=0.12, rvar=0.1, patina=0.18)
    m['alu'] = mats.metal('nook_alu', (0.78, 0.77, 0.74), rough=0.34, patina=0.3)
    m['steel'] = mats.metal('nook_steel', (0.62, 0.61, 0.59), rough=0.3, rvar=0.2, patina=0.35, scale=6)
    m['sinksteel'] = mats.metal('nook_sinksteel', (0.42, 0.41, 0.39), rough=0.42, rvar=0.25, patina=0.5, scale=10)
    m['enamel_dark'] = mats.noisy('nook_hobenamel', (0.03, 0.028, 0.026), (0.06, 0.05, 0.045), rough=0.3, scale=20)
    m['iron'] = mats.noisy('nook_castiron', (0.018, 0.016, 0.015), (0.05, 0.045, 0.04), rough=0.55, scale=40, bmp=0.2)
    m['vinyl'] = mats.leather('nook_vinyl', (0.30, 0.085, 0.03))
    m['rubber'] = mats.plain('nook_rubber', (0.02, 0.018, 0.016), rough=0.6)
    m['cabinet'] = mats.noisy('nook_cabinetpaint', (0.27, 0.26, 0.14), (0.33, 0.31, 0.18), rough=0.45, scale=6, bmp=0.05)
    m['fridge'] = mats.noisy('nook_fridge', (0.60, 0.52, 0.36), (0.66, 0.58, 0.42), rough=0.25, scale=4)
    mats.setp(m['fridge'].node_tree.nodes['Principled BSDF'], coat=0.5, coat_rough=0.15)
    m['pine'] = mats.wood('nook_pine', axis='X', cols=((0.20, 0.11, 0.05), (0.36, 0.22, 0.11), (0.48, 0.32, 0.17)), rough=0.5)
    m['spoonwood'] = mats.wood('nook_spoonwood', axis='Z', cols=((0.30, 0.18, 0.09), (0.45, 0.30, 0.16), (0.56, 0.40, 0.23)), rough=0.6, scale=3)
    m['bamboo'] = mats.noisy('nook_bamboo', (0.42, 0.30, 0.14), (0.56, 0.43, 0.22), rough=0.4, scale=8, sc3=(0.4, 6, 6))
    m['ceramic'] = mats.plain('nook_ceramic', (0.80, 0.77, 0.70), rough=0.18, coat=0.6)
    m['mugglaze'] = mats.noisy('nook_mugglaze', (0.70, 0.63, 0.50), (0.78, 0.72, 0.60), rough=0.15, scale=30)
    m['mugband'] = mats.plain('nook_mugband', (0.22, 0.10, 0.04), rough=0.2)
    m['coffee'] = mats.plain('nook_coffeedregs', (0.05, 0.025, 0.012), rough=0.1)
    m['cord'] = mats.noisy('nook_cord', (0.06, 0.035, 0.02), (0.14, 0.09, 0.05), rough=0.8, scale=900, sc3=(1, 1, 1))
    m['brass'] = mats.metal('nook_brass', (0.78, 0.56, 0.24), rough=0.3)
    m['gold'] = mats.metal('nook_gold', (0.95, 0.72, 0.36), rough=0.18, patina=0.15)
    m['glass'] = mats.glass('nook_glass', (0.95, 0.95, 0.92), shadow_amt=0.8)
    m['filament'] = mats.emissive('nook_filament', (1.0, 0.62, 0.28), 60.0, night_only=True)
    gm = mats.emissive('nook_bulbenv', (1.0, 0.72, 0.42), 1.4, night_only=True)     # EMN_: glows at night, off by day
    nt = gm.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
    mats.setp(b, col=(1.0, 0.97, 0.92), trans=1.0, rough=0.04, ior=1.5)
    tr = mats.N(nt, 'ShaderNodeBsdfTransparent'); lp = mats.N(nt, 'ShaderNodeLightPath'); mx = mats.N(nt, 'ShaderNodeMixShader')
    mats.L(nt, lp.outputs['Is Shadow Ray'], mx.inputs[0]); mats.L(nt, b.outputs[0], mx.inputs[1]); mats.L(nt, tr.outputs[0], mx.inputs[2])
    mats.L(nt, mx.outputs[0], out.inputs[0])
    m['bulbglass'] = gm
    m['beer'] = mats.glass('nook_beer', (0.85, 0.48, 0.10), shadow=(0.9, 0.55, 0.2), shadow_amt=0.6)
    m['foam'] = mats.noisy('nook_foam', (0.80, 0.74, 0.60), (0.92, 0.88, 0.78), rough=0.6, scale=300)
    m['resin'] = mats.plain('nook_penresin', (0.012, 0.010, 0.010), rough=0.12, coat=0.8)
    m['ink'] = mats.plain('nook_inkbottle', (0.02, 0.025, 0.06), rough=0.05, coat=1.0)
    m['bakelite'] = mats.plain('nook_bakelite', (0.02, 0.015, 0.012), rough=0.3)
    m['pencil'] = mats.plain('nook_pencilpaint', (0.10, 0.22, 0.09), rough=0.35, coat=0.4)
    m['pencilwood'] = mats.noisy('nook_pencilwood', (0.55, 0.38, 0.22), (0.66, 0.50, 0.32), rough=0.7, scale=60)
    m['graphite'] = mats.plain('nook_graphite', (0.05, 0.05, 0.05), rough=0.3, metal_=0.5)
    m['eraser'] = mats.plain('nook_eraser', (0.82, 0.80, 0.74), rough=0.7)
    m['pages'] = mats.noisy('nook_pages', (0.70, 0.66, 0.56), (0.80, 0.76, 0.66), rough=0.8, scale=200, sc3=(1, 1, 30))
    pm, nt, b, _ = mats.base('nook_paperedge')          # side of a stack of paper: fine horizontal lines
    wv = mats.N(nt, 'ShaderNodeTexWave', wave_type='BANDS', bands_direction='Z'); wv.inputs['Scale'].default_value = 900
    wv.inputs['Distortion'].default_value = 3; mats.L(nt, mats.coords(nt), wv.inputs['Vector'])
    mats.L(nt, mats.ramp(nt, wv.outputs[1], [(0.0, (0.62, 0.58, 0.49)), (1.0, (0.80, 0.77, 0.68))]), b.inputs['Base Color'])
    mats.setp(b, rough=0.85)
    m['paperedge'] = pm
    m['paperplain'] = mats.noisy('nook_paperplain', (0.76, 0.72, 0.62), (0.82, 0.78, 0.69), rough=0.85, scale=40)
    m['crumple'] = mats.noisy('nook_crumple', (0.62, 0.58, 0.48), (0.84, 0.80, 0.70), rough=0.85, scale=60, bmp=0.3)
    m['slip_red'] = mats.plain('nook_slipred', (0.45, 0.07, 0.05), rough=0.7)
    m['slip_white'] = mats.plain('nook_slipwhite', (0.80, 0.77, 0.68), rough=0.7)
    m['cig'] = mats.plain('nook_cigpaper', (0.82, 0.80, 0.74), rough=0.8)
    m['filter'] = mats.noisy('nook_cigfilter', (0.55, 0.36, 0.16), (0.70, 0.50, 0.26), rough=0.7, scale=400)
    m['ash'] = mats.noisy('nook_ash', (0.18, 0.17, 0.16), (0.45, 0.43, 0.40), rough=0.95, scale=120, bmp=0.3)
    m['water'] = mats.plain('nook_potwater', (0.42, 0.40, 0.33), rough=0.12)
    m['pasta'] = mats.plain('nook_spaghetti', (0.80, 0.62, 0.30), rough=0.4)
    m['kettle'] = mats.noisy('nook_kettleenamel', (0.30, 0.05, 0.03), (0.38, 0.08, 0.04), rough=0.18, scale=10)
    mats.setp(m['kettle'].node_tree.nodes['Principled BSDF'], coat=0.6, coat_rough=0.1)
    m['plate'] = mats.plain('nook_plate', (0.80, 0.78, 0.72), rough=0.12, coat=0.5)
    m['jarred'] = mats.noisy('nook_umeboshi', (0.30, 0.03, 0.03), (0.45, 0.08, 0.05), rough=0.3, scale=60)
    m['sugar'] = mats.noisy('nook_sugar', (0.78, 0.76, 0.72), (0.88, 0.86, 0.82), rough=0.8, scale=200)
    m['soy'] = mats.plain('nook_soyglass', (0.04, 0.015, 0.008), rough=0.08, coat=1.0)
    m['oil'] = mats.glass('nook_oil', (0.85, 0.70, 0.25), shadow=(0.9, 0.8, 0.4), shadow_amt=0.6)
    m['redcap'] = mats.plain('nook_redcap', (0.45, 0.06, 0.04), rough=0.35)
    m['lid'] = mats.metal('nook_lidmetal', (0.70, 0.62, 0.45), rough=0.35)
    m['apron'] = mats.noisy('nook_apron', (0.36, 0.16, 0.07), (0.48, 0.24, 0.11), rough=0.85, scale=30, bmp=0.15, sheen=0.4)
    tm_, nt, b, _ = mats.base('nook_teatowel')          # cream towel with a red check
    ch = mats.N(nt, 'ShaderNodeTexChecker'); ch.inputs['Scale'].default_value = 26
    ch.inputs['Color1'].default_value = (0.72, 0.66, 0.54, 1); ch.inputs['Color2'].default_value = (0.42, 0.10, 0.06, 1)
    mats.L(nt, mats.coords(nt), ch.inputs['Vector']); mats.L(nt, ch.outputs[0], b.inputs['Base Color'])
    mats.setp(b, rough=0.9, sheen=0.5)
    m['towel'] = tm_
    m['radiobody'] = mats.leather('nook_radiocase', (0.30, 0.17, 0.08))
    m['wallplug'] = mats.plain('nook_fittingwhite', (0.72, 0.70, 0.64), rough=0.35)
    return m

# ------------------------------------------------------------------------------------------------ table + chairs
def table():
    t = layout.NOOK_TABLE; z = t['top_z']
    cx, cy = (t['x0'] + t['x1']) / 2, (t['y0'] + t['y1']) / 2
    w, d = t['x1'] - t['x0'], t['y1'] - t['y0']
    with kit.xform(T(cx, cy, 0)):
        with kit.props(td=1.0):
            slab('table_top', rrect(w, d, 0.04, 5),
                 [(0.0015, z - 0.029), (0.0, z - 0.027), (0.0, z - 0.002), (0.0018, z)], [M['laminate'], M['edge']],
                 top_mi=0, side_mi=[1, 1, 1])
        with kit.props(td=0.5):
            kit.box('table_apron', -w / 2 + 0.06, w / 2 - 0.06, -d / 2 + 0.06, d / 2 - 0.06, z - 0.09, z - 0.029, M['alu'], skip='+z -z', bevel=0.003)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    x, y = sx * (w / 2 - 0.075), sy * (d / 2 - 0.075)
                    kit.cyl('table_leg', x, y, 0.022, z - 0.06, 0.0125, M['chrome'], segs=12, cap='')
                    kit.cyl('table_foot', x, y, 0.0, 0.022, 0.0135, M['rubber'], segs=12, r1=0.0125, cap='t')

def chair(name, x, y, rot):
    """1970s kitchen chair: chrome tube frame, oxblood-orange vinyl seat and back pad. local front = +Y"""
    with kit.xform(T(x, y, 0) @ Rz(rot)), kit.props(td=0.45):
        hw, r = 0.19, 0.0105
        for s in (-1, 1):
            X = s * hw
            kit.tube(name + '_side', [(X, 0.17, 0.0), (X, 0.175, 0.30), (X, 0.17, 0.425), (X, 0.12, 0.435), (X, -0.12, 0.435),
                                      (X, -0.165, 0.45), (X, -0.185, 0.62), (X, -0.205, 0.84)], r, M['chrome'], segs=8)
            kit.tube(name + '_back', [(X, -0.20, 0.0), (X, -0.19, 0.20), (X, -0.17, 0.415)], r, M['chrome'], segs=8)
            kit.cyl(name + '_foot', X, 0.17, -0.0, 0.012, r * 1.15, M['rubber'], segs=8, cap='t')
            kit.cyl(name + '_foot', X, -0.20, -0.0, 0.012, r * 1.15, M['rubber'], segs=8, cap='t')
        kit.tube(name + '_rung', [(-hw, -0.18, 0.13), (hw, -0.18, 0.13)], 0.0075, M['chrome'], segs=6)
        kit.tube(name + '_rung', [(-hw, 0.172, 0.13), (hw, 0.172, 0.13)], 0.0075, M['chrome'], segs=6)
        kit.tube(name + '_rail', [(-hw, -0.12, 0.435), (hw, -0.12, 0.435)], 0.008, M['chrome'], segs=6)
        kit.tube(name + '_rail', [(-hw, 0.12, 0.435), (hw, 0.12, 0.435)], 0.008, M['chrome'], segs=6)
        with kit.props(td=0.7):
            slab(name + '_seat', rrect(0.40, 0.39, 0.06, 4), [(0.0, 0.445), (0.0, 0.47), (0.012, 0.488), (0.035, 0.493)], [M['vinyl']], side_mi=[0, 0, 0])
            with kit.xform(T(0, -0.185, 0.64) @ Rx(-5)):
                kit.box(name + '_backpad', -0.196, 0.196, 0.0, 0.026, 0.0, 0.165, M['vinyl'], bevel=0.009, segs=2)

# ------------------------------------------------------------------------------------------------ the writing table still life
def manuscript():
    ox, oy, oz = layout.INTERACTIVE['manuscript'][1]
    W, H = 0.26, 0.36
    with kit.interactive('manuscript', origin=(ox, oy, oz), td=3.2):
        with kit.xform(T(ox, oy, oz + 0.0012) @ Rz(-4)):
            with kit.props(td=1.0):
                tbox('ms_block', -W / 2, W / 2, -H / 2, H / 2, 0.0, 0.007, M['paperedge'], skip='-z +z')
                with kit.xform(Rz(1.3) @ T(0.002, -0.003, 0)):
                    tbox('ms_block2', -W / 2, W / 2, -H / 2, H / 2, 0.007, 0.0125, M['paperedge'], skip='-z +z')
            with kit.props(td=1.4):
                with kit.xform(Rz(-1.6) @ T(-0.003, 0.002, 0)):
                    grid('ms_loose', 1, 1, lambda u, v: ((u - 0.5) * W, (v - 0.5) * H, 0.0128), M['paper'], 'ms_done')
            def top(u, v):
                x, y = (u - 0.5) * W, (v - 0.5) * H
                lift = 0.006 * max(0, (u - 0.72) / 0.28) ** 2 * max(0, (0.30 - v) / 0.30) ** 2
                return (x, y, 0.0134 + lift + 0.0004 * math.sin(v * 3.0))
            grid('ms_top', 8, 10, top, M['paper'], 'ms_top')
            # the fountain pen, uncapped, lying across the sheet; nib just below where the writing stops
            nib = Vector((-0.012, -0.028, 0)); dr = Vector((-0.7071, 0.7071, 0)); L = 0.136
            back = nib - dr * L
            with kit.xform(T(back.x, back.y, 0.0134 + 0.0064) @ Rz(135) @ Ry(90)), kit.props(td=2.0):
                kit.lathe('pen_body', [(0, 0), (0.0035, 0.0006), (0.0058, 0.003), (0.0064, 0.008), (0.0064, 0.082), (0.0061, 0.085)],
                          M['resin'], segs=16)
                kit.lathe('pen_ring', [(0.0061, 0.085), (0.0063, 0.0855), (0.0063, 0.0885), (0.0058, 0.089)], M['gold'], segs=16)
                kit.lathe('pen_grip', [(0.0058, 0.089), (0.0056, 0.096), (0.0048, 0.110), (0.0050, 0.1115), (0.0035, 0.1125)], M['resin'], segs=16)
                with kit.xform(SC(1.0, 0.32, 1.0)):
                    kit.lathe('pen_nib', [(0, 0.104), (0.0044, 0.1045), (0.0042, 0.116), (0.0026, 0.127), (0.0006, 0.136), (0, 0.1362)],
                              M['gold'], segs=10)

def table_things():
    z = layout.NOOK_TABLE['top_z']
    # --- finished sheets fanned out to the left/back, under the stack's corner
    for i, (x, y, a, rot) in enumerate(((2.56, 2.605, 4, 0), (2.545, 2.645, 11, 180), (2.535, 2.675, 18, 0))):
        with kit.xform(T(x, y, z + 0.0003 * (i + 1)) @ Rz(a)), kit.props(td=(1.3, 1.5, 2.0)[i]):
            if True:
                def fn(u, v, i=i):
                    return ((u - 0.5) * 0.26, (v - 0.5) * 0.36, 0.0003 * math.sin(u * 3.1 + i) + 0.0004 * (1 - v))
                grid('ms_fan%d' % i, 3, 4, fn, M['paper'], 'ms_done', rot=rot)
    # --- pen cap, rolled a little away
    with kit.xform(T(2.905, 2.265, z + 0.0072) @ Rz(62) @ Ry(90)), kit.props(td=2.0):
        kit.lathe('pen_cap', [(0, 0), (0.0045, 0.0005), (0.0068, 0.003), (0.0072, 0.008), (0.0072, 0.056), (0.0074, 0.0565),
                              (0.0074, 0.061), (0.0062, 0.061), (0.0062, 0.010), (0, 0.010)], M['resin'], segs=16,
)
    # cap gets a gold ring at its mouth (mi above uses one material list; add gold band as separate lathe)
    with kit.xform(T(2.905, 2.265, z + 0.0072) @ Rz(62) @ Ry(90)), kit.props(td=2.0):
        kit.lathe('pen_capband', [(0.0073, 0.0555), (0.0076, 0.056), (0.0076, 0.0605), (0.0073, 0.061)], M['gold'], segs=16)
        kit.box('pen_clip', -0.0094, -0.0072, -0.0012, 0.0012, 0.012, 0.050, M['gold'], bevel=0.0005)
    # --- dictionary, closed, spine toward the writer
    with kit.xform(T(2.445, 2.325, z) @ Rz(-7)), kit.props(td=2.0):
        bw, bd, bh = 0.19, 0.135, 0.058
        tbox('dict_pages', -bw / 2 + 0.004, bw / 2 - 0.004, -bd / 2 + 0.004, bd / 2 - 0.003, 0.004, bh - 0.004, M['pages'], M['dict'],
             faces={'+y': ('dict_edge', 90)}, skip='-z')
        tbox('dict_board_t', -bw / 2, bw / 2, -bd / 2, bd / 2, bh - 0.004, bh, M['slip_red'], M['dict'], faces={'+z': ('dict_cover', 90)}, bevel=0.0012)
        tbox('dict_board_b', -bw / 2, bw / 2, -bd / 2, bd / 2, 0.0, 0.004, M['slip_red'], skip='-z', bevel=0.0012)
        tbox('dict_spine', -bw / 2, bw / 2, -bd / 2 - 0.004, -bd / 2 + 0.006, 0.0, bh, M['slip_red'], M['dict'],
             faces={'-y': ('dict_spine', 90)}, bevel=0.003, skip='-z')
        for k, (x, mat, ln) in enumerate(((-0.04, M['slip_red'], 0.035), (0.025, M['slip_white'], 0.028), (0.06, M['slip_white'], 0.022))):
            kit.quad('dict_slip', [(x, bd / 2 - 0.01, bh - 0.008 - k * 0.012), (x + 0.012, bd / 2 - 0.01, bh - 0.008 - k * 0.012),
                                   (x + 0.014, bd / 2 + ln, bh - 0.006 - k * 0.012), (x + 0.002, bd / 2 + ln, bh - 0.006 - k * 0.012)], mat)
        # pencil on the dictionary
        with kit.xform(T(-0.075, -0.02, bh + 0.0036) @ Rz(16) @ Ry(90)):
            kit.lathe('pencil', [(0, 0), (0.0036, 0.0), (0.0036, 0.128)], M['pencil'], segs=6, smooth=False)
            kit.lathe('pencil_tip', [(0.0036, 0.128), (0.0012, 0.146), (0, 0.149)], M['pencilwood'], segs=6, smooth=False)
            kit.lathe('pencil_lead', [(0.0012, 0.1455), (0.0004, 0.150), (0, 0.1505)], M['graphite'], segs=6)
    # --- eraser
    with kit.xform(T(2.585, 2.245, z) @ Rz(24)), kit.props(td=2.0):
        tbox('eraser', -0.022, 0.022, -0.011, 0.011, 0.0, 0.010, M['eraser'], bevel=0.0015, skip='-z')
        tbox('eraser_sleeve', -0.012, 0.012, -0.0115, 0.0115, -0.0003, 0.0104, M['eraser'], M['paper'],
             faces={'+z': 'eraser', '-y': 'eraser', '+y': 'eraser'}, skip='-z -x +x')
    # --- ink bottle
    with kit.xform(T(2.915, 2.415, z) @ Rz(9)), kit.props(td=2.0):
        tbox('ink_bottle', -0.026, 0.026, -0.026, 0.026, 0.0, 0.046, M['ink'], bevel=0.006, segs=2, skip='-z')
        kit.quad('ink_label', [(-0.02, -0.0262, 0.008), (0.02, -0.0262, 0.008), (0.02, -0.0262, 0.040), (-0.02, -0.0262, 0.040)], M['paper'],
                 uv=(R('ink', 0, 0), R('ink', 1, 0), R('ink', 1, 1), R('ink', 0, 1)))
        kit.cyl('ink_neck', 0, 0, 0.046, 0.052, 0.011, M['ink'], segs=16, cap='')
        kit.lathe('ink_cap', [(0.0135, 0.050), (0.0135, 0.068), (0.012, 0.0695), (0, 0.0695)], M['bakelite'], segs=16)
    # --- ashtray with a few butts
    with kit.xform(T(3.045, 2.305, z)), kit.props(td=1.6):
        kit.lathe('ashtray', [(0, 0.0), (0.050, 0.0), (0.060, 0.004), (0.064, 0.020), (0.066, 0.022), (0.062, 0.022), (0.056, 0.008),
                              (0.044, 0.004), (0, 0.004)], M['alu'], segs=24)
        kit.lathe('ash_heap', [(0, 0.004), (0.03, 0.004), (0.018, 0.008), (0, 0.009)], M['ash'], segs=10)
        for k, (a, x, y) in enumerate(((20, -0.01, 0.0), (150, 0.012, 0.01), (-70, 0.0, -0.012))):
            with kit.xform(T(x, y, 0.0085) @ Rz(a) @ Ry(84)):
                kit.cyl('butt_filter', 0, 0, 0.0, 0.020, 0.0038, M['filter'], segs=8)
                kit.cyl('butt_paper', 0, 0, 0.020, 0.028 + 0.012 * (k == 0), 0.0038, M['cig'], segs=8, cap='')
                kit.cyl('butt_ash', 0, 0, 0.028 + 0.012 * (k == 0), 0.031 + 0.03 * (k == 0), 0.0036, M['ash'], segs=8, r1=0.0031)
    # --- beer can, opened
    with kit.xform(T(3.075, 2.69, z) @ Rz(-20)), kit.props(td=2.0):
        rc, hc = 0.033, 0.122
        kit.lathe('can_base', [(0, 0.002), (0.024, 0.0), (0.031, 0.002), (rc, 0.009), (rc, 0.012)], M['alu'], segs=24)
        kit.cyl_patch('can_label', 0, 0, 0.012, 0.106, rc, -180, 180, M['can'], uvrect=Rrect('can'), segs=24)
        kit.lathe('can_top', [(rc, 0.106), (rc, 0.110), (0.029, 0.118), (0.0295, 0.122), (0.027, 0.121), (0.026, 0.117), (0, 0.117)], M['alu'], segs=24)
        kit.box('can_tab', -0.004, 0.004, -0.004, 0.012, 0.117, 0.119, M['alu'], bevel=0.001)
        with kit.xform(T(0.0, 0.012, 0.117) @ Rx(-50)):
            kit.box('can_ring', -0.005, 0.005, 0.0, 0.016, 0.0, 0.0012, M['alu'])
        kit.box('can_hole', -0.006, 0.006, -0.018, -0.006, 0.1172, 0.1174, M['rubber'])
    # --- small glass, a little beer and foam left
    with kit.xform(T(2.95, 2.615, z)), kit.props(td=1.8):
        kit.lathe('glass', [(0, 0), (0.028, 0.0), (0.030, 0.003), (0.034, 0.092), (0.0325, 0.092), (0.0285, 0.009), (0, 0.009)], M['glass'], segs=24)
        kit.lathe('glass_beer', [(0, 0.009), (0.0285, 0.009), (0.0291, 0.024), (0, 0.024)], M['beer'], segs=24)
        kit.lathe('glass_foam', [(0.0291, 0.024), (0.0293, 0.0262), (0.026, 0.0268), (0.019, 0.0252), (0.015, 0.0240)], M['foam'], segs=24)
        kit.cyl_patch('glass_lace', 0, 0, 0.040, 0.046, 0.0318, 30, 150, M['foam'], segs=8)
    # --- mug, empty, dregs
    with kit.xform(T(2.795, 2.80, z) @ Rz(30)), kit.props(td=1.6):
        rm = 0.039
        kit.lathe('mug', [(0, 0.0), (rm - 0.003, 0.0), (rm, 0.004), (rm, 0.088), (rm - 0.004, 0.090), (rm - 0.004, 0.012), (0, 0.010)],
                  [M['mugglaze']], segs=24)
        kit.cyl_patch('mug_band', 0, 0, 0.060, 0.072, rm + 0.0003, 0, 360, M['mugband'], segs=24)
        kit.lathe('mug_dregs', [(0, 0.0105), (rm - 0.0042, 0.0125), (0, 0.0128)], M['coffee'], segs=16)
        kit.tube('mug_handle', [(rm - 0.002, 0, 0.074), (rm + 0.018, 0, 0.072), (rm + 0.026, 0, 0.052), (rm + 0.018, 0, 0.030),
                                (rm - 0.002, 0, 0.026)], 0.0055, M['mugglaze'], segs=8)
    # --- one crumpled ball of paper
    with kit.props(td=1.4):
        import bpy
        me = bpy.data.meshes.new('crumple'); bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.032)
        import random
        rnd = random.Random(7)
        for v in bm.verts:
            n = v.co.normalized()
            k = (1.0 + 0.18 * math.sin(n.x * 9.1 + 1.3) * math.sin(n.y * 7.7 + 0.4) + 0.12 * math.sin(n.z * 11.3)
                 + 0.07 * abs(math.sin(n.x * 23 + n.y * 17)) + rnd.uniform(-0.09, 0.09))
            v.co = n * 0.032 * k * Vector((1.0, 0.92, 0.82))
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new('crumple', me); bpy.context.scene.collection.objects.link(ob)
        ob.location = (2.385, 2.47, z + 0.0255); ob.rotation_euler = (0.3, 0.5, 0.2)
        me.materials.append(M['crumple'])
        for p in me.polygons: p.use_smooth = False
        kit.adopt(ob)

# ------------------------------------------------------------------------------------------------ bulb
def bulb():
    x, y, zb = layout.NOOK_BULB
    top = layout.ROOM['z1']
    with kit.xform(T(x, y, 0)), kit.props(td=1.0):
        kit.lathe('bulb_glass', [(0, zb - 0.034), (0.012, zb - 0.031), (0.024, zb - 0.021), (0.030, zb - 0.004), (0.030, zb + 0.008),
                                 (0.026, zb + 0.024), (0.017, zb + 0.040), (0.0135, zb + 0.052)], M['bulbglass'], segs=20)
        kit.tube('bulb_stem', [(0, 0, zb + 0.045), (0, 0, zb + 0.012)], 0.003, M['bulbglass'], segs=6)
        kit.tube('bulb_filament', [(-0.009, 0, zb + 0.004), (-0.006, 0.002, zb + 0.0), (-0.003, -0.002, zb + 0.003), (0.0, 0.002, zb + 0.0),
                                   (0.003, -0.002, zb + 0.003), (0.006, 0.002, zb + 0.0), (0.009, 0, zb + 0.004)], 0.0011, M['filament'], segs=5)
        for s in (-1, 1):
            kit.tube('bulb_wire', [(s * 0.009, 0, zb + 0.004), (s * 0.004, 0, zb + 0.014), (s * 0.002, 0, zb + 0.026)], 0.0004, M['alu'], segs=4, caps=False)
        kit.lathe('bulb_screw', [(0.0138, zb + 0.050), (0.0142, zb + 0.056), (0.0136, zb + 0.060), (0.0142, zb + 0.064), (0.0136, zb + 0.068),
                                 (0.0142, zb + 0.072), (0.0138, zb + 0.076)], M['alu'], segs=16)
        kit.lathe('bulb_holder', [(0.0175, zb + 0.072), (0.020, zb + 0.074), (0.0205, zb + 0.098), (0.0195, zb + 0.102), (0.0185, zb + 0.104),
                                  (0.0195, zb + 0.108), (0.0195, zb + 0.124), (0.012, zb + 0.132), (0.006, zb + 0.136), (0, zb + 0.137)],
                  M['ceramic'], segs=20)
        c0 = zb + 0.136
        for ph in (0, math.pi):
            kit.tube('bulb_cord', helix((0, 0, c0), (0, 0, top - 0.02), 0.0028, (top - c0) / 0.018, ph, 48), 0.0029, M['cord'], segs=5)
        kit.lathe('ceiling_rose', [(0, top - 0.026), (0.008, top - 0.026), (0.03, top - 0.018), (0.036, top - 0.006), (0.036, top)], M['ceramic'], segs=20)

# ------------------------------------------------------------------------------------------------ noren
def noren():
    o = layout.NOOK_OPENING
    x0, x1 = o['x0'], o['x1']; z0, z1 = 1.55, 2.02
    yr = o['y'] + 0.042                              # rod sits in the wall opening, a little in from the bar face
    with kit.props(td=0.6):
        kit.tube('noren_rod', [(x0 - 0.01, yr, z1 + 0.003), (x1 + 0.01, yr, z1 + 0.003)], 0.0105, M['bamboo'], segs=10)
        for x in (x0 + 0.21, x0 + 0.52, x1 - 0.2):
            kit.tube('noren_node', [(x - 0.004, yr, z1 + 0.003), (x + 0.004, yr, z1 + 0.003)], 0.0118, M['bamboo'], segs=10)
    n, gap = 4, 0.006
    pw = (x1 - x0 - gap * (n - 1)) / n
    part = {0: (0.0, -0.06), 1: (0.040, 0.0), 2: (0.0, 0.0), 3: (0.0, 0.0)}    # (left edge, right edge) bottom swing: parted between 0 and 1
    with kit.props(td=0.7):
        for k in range(n):
            a = x0 + k * (pw + gap); b = a + pw
            ua, ub = (a - x0) / (x1 - x0), (b - x0) / (x1 - x0)
            def fn(u, v, k=k, a=a, b=b):
                t = (1 - v)                                     # 0 at the top, 1 at the hem
                sw = part[k][0] * (1 - u) + part[k][1] * u
                x = a + (b - a) * u + sw * t ** 1.6
                fold = (0.0035 + 0.007 * t) * math.sin(2 * math.pi * (u * 2.6 + 0.3 * k) + 0.7 * t) * min(1.0, t * 7)
                y = yr - 0.0135 + fold - 0.012 * t * (k == 1) * (1 - u)
                z = z0 + (z1 + 0.003 - z0) * v
                return (x, y, z)
            def uvf(u, v, ua=ua, ub=ub):
                return R('noren', ua + (ub - ua) * u, min(1.0, v * 1.0))
            grid('noren_panel%d' % k, 10, 7, fn, M['noren'], uvfn=uvf)
            # sleeve over the rod: a short strip wrapping its top
            def sl(u, v, a=a, b=b):
                th = -math.pi / 2 + math.pi * v                 # front -> over the top -> back
                return (a + (b - a) * u, yr + 0.0135 * math.sin(th), z1 + 0.003 + 0.0135 * math.cos(th))
            grid('noren_sleeve%d' % k, 4, 3, sl, M['noren'], uvfn=lambda u, v, ua=ua, ub=ub: R('noren', ua + (ub - ua) * u, 0.985))

# ------------------------------------------------------------------------------------------------ kitchenette
def kitchenette():
    K = layout.KITCHENETTE; zt = K['top_z']
    xa, xb = K['x0'], 2.975                          # cabinet + worktop; fridge from 2.985 to the right wall
    yb = K['y1']; yf = K['y0']
    with kit.props(td=0.35):
        kit.box('cab_body', xa, xb, yf + 0.03, yb, 0.08, zt - 0.03, M['cabinet'], skip='-x +y -z -y +z')
    with kit.props(td=0.1):
        kit.box('cab_shadowgap', xa, xb, yf + 0.031, yf + 0.034, 0.08, zt - 0.03, M['rubber'], only='-y')
    with kit.props(td=0.35):
        kit.box('cab_plinth', xa, xb, yf + 0.07, yb, 0.0, 0.08, M['rubber'], skip='-x +y -z +z')
        for (d0, d1) in ((xa + 0.004, 2.55), (2.555, xb - 0.004)):
            kit.box('cab_door', d0, d1, yf + 0.022, yf + 0.032, 0.095, zt - 0.045, M['cabinet'], bevel=0.003, skip='+y')
    with kit.props(td=0.7):
        kit.box('cab_handle', 2.53, 2.542, yf + 0.008, yf + 0.022, 0.62, 0.70, M['chrome'], bevel=0.003, skip='+y')
        kit.box('cab_handle', 2.568, 2.580, yf + 0.008, yf + 0.022, 0.62, 0.70, M['chrome'], bevel=0.003, skip='+y')
        # stainless worktop with the sink cut-out: four pieces around the basin
        sx0, sx1, sy0, sy1 = 2.655, 2.945, yf + 0.075, yb - 0.075
        kit.box('worktop', xa, sx0, yf, yb, zt - 0.03, zt, M['steel'], bevel=0.004, skip='-x +y -z')
        kit.box('worktop', sx1, xb, yf, yb, zt - 0.03, zt, M['steel'], bevel=0.004, skip='+y -z')
        kit.box('worktop', sx0, sx1, yf, sy0, zt - 0.03, zt, M['steel'], bevel=0.004, skip='-x +x -z')
        kit.box('worktop', sx0, sx1, sy1, yb, zt - 0.03, zt, M['steel'], skip='-x +x +y -z')
        basin('sink', sx0, sx1, sy0, sy1, zt - 0.17, zt, M['sinksteel'])
        kit.lathe('sink_drain', [(0.024, zt - 0.168), (0.022, zt - 0.169), (0, zt - 0.169)], M['alu'], segs=12,
                  center=((sx0 + sx1) / 2, (sy0 + sy1) / 2 + 0.05, 0))
        # single wall tap over the sink
        tx = (sx0 + sx1) / 2
        kit.tube('tap', [(tx, yb, 1.02), (tx, yb - 0.05, 1.02), (tx, yb - 0.12, 1.015), (tx, yb - 0.145, 0.995), (tx, yb - 0.15, 0.965)],
                 0.0085, M['chrome'], segs=10)
        with kit.xform(T(tx, yb, 1.02) @ Rx(90)):
            kit.lathe('tap_flange', [(0, -0.0), (0.02, 0.0), (0.018, 0.008), (0.011, 0.012)], M['chrome'], segs=12)
        kit.lathe('tap_head', [(0.0085, 1.028), (0.011, 1.03), (0.011, 1.05), (0, 1.052)], M['chrome'], segs=10, center=(tx, yb - 0.05, 0))
        for a in (0, 90):
            with kit.xform(T(tx, yb - 0.05, 1.047) @ Rz(a + 45)):
                kit.box('tap_cross', -0.022, 0.022, -0.004, 0.004, 0.0, 0.007, M['chrome'], bevel=0.002)
    # --- built-in two-ring gas hob
    hx0, hx1 = 2.09, 2.62
    with kit.props(td=0.8):
        kit.box('hob_plate', hx0, hx1, yf + 0.05, yb - 0.045, zt, zt + 0.006, M['enamel_dark'], bevel=0.003, skip='-z')
        for bx in (2.20, layout.POINTS['hob'][0]):
            by = layout.POINTS['hob'][1]
            kit.lathe('hob_burner', [(0.050, zt + 0.006), (0.050, zt + 0.012), (0.042, zt + 0.016), (0.040, zt + 0.020), (0.030, zt + 0.021),
                                     (0.030, zt + 0.016), (0, zt + 0.016)], M['iron'], segs=20, center=(bx, by, 0))
            kit.lathe('hob_cap', [(0.028, zt + 0.017), (0.028, zt + 0.022), (0.02, zt + 0.025), (0, zt + 0.026)], M['iron'], segs=16, center=(bx, by, 0))
            for a in range(4):
                with kit.xform(T(bx, by, 0) @ Rz(45 + 90 * a)):
                    kit.box('hob_support', 0.048, 0.092, -0.004, 0.004, zt + 0.006, zt + 0.032, M['iron'], bevel=0.0015)
            with kit.xform(T(bx, yf + 0.03, 0.74) @ Rx(90)):
                kit.lathe('hob_knob', [(0, 0.0), (0.018, 0.0), (0.018, 0.012), (0.015, 0.016), (0, 0.016)], M['bakelite'], segs=14)
                kit.box('hob_knob_grip', -0.004, 0.004, -0.014, 0.014, 0.016, 0.026, M['bakelite'], bevel=0.002)
    pot()
    kettle()
    rack_and_shelf()

def pot():
    px, py, _ = layout.POINTS['hob']; zb = layout.KITCHENETTE['top_z'] + 0.032
    with kit.xform(T(px, py, zb)), kit.props(td=1.4):
        r, h = 0.088, 0.098
        kit.lathe('pot', [(0, 0.0), (r - 0.006, 0.0), (r, 0.006), (r, h - 0.004), (r + 0.003, h - 0.002), (r + 0.003, h), (r - 0.0025, h),
                          (r - 0.0025, 0.006), (0, 0.004)], M['alu'], segs=28)
        kit.lathe('pot_water', [(0, 0.062), (r - 0.0026, 0.062), (0, 0.0625)], M['water'], segs=20)
        for s in (-1, 1):
            kit.tube('pot_handle', [(s * (r - 0.002), -0.025, h - 0.022), (s * (r + 0.022), -0.022, h - 0.016), (s * (r + 0.026), 0.0, h - 0.014),
                                    (s * (r + 0.022), 0.022, h - 0.016), (s * (r - 0.002), 0.025, h - 0.022)], 0.0045, M['alu'], segs=6)
        # spaghetti ends poking out of the water, leaning on the rim
        import random
        rnd = random.Random(11)
        for i in range(10):
            a = math.radians(-128 + 7.5 * i + rnd.uniform(-3, 3)); rr = rnd.uniform(0.01, 0.05)
            p0 = (rr * math.cos(a + 2.6), rr * math.sin(a + 2.6), 0.060)
            c, s_ = math.cos(a), math.sin(a)
            if i % 3 == 0:                                   # stiff end still leaning on the inside of the rim
                pts = [p0, ((r - 0.004) * c, (r - 0.004) * s_, h + 0.004)]
            else:                                            # softened ends draped over the rim
                d = rnd.uniform(0.008, 0.02)
                pts = [p0, ((p0[0] + r * c) / 2, (p0[1] + r * s_) / 2, 0.085), ((r + 0.0035) * c, (r + 0.0035) * s_, h + 0.0035),
                       ((r + 0.008) * c, (r + 0.008) * s_, h - 0.002), ((r + 0.0095) * c, (r + 0.0095) * s_, h - 0.006 - d)]
            kit.tube('spaghetti', pts, 0.0011, M['pasta'], segs=4)
        # wooden spoon across the front rim, bowl in the water
        sp = [(0.02, 0.035, 0.064), (0.012, -0.02, 0.08), (0.004, -r - 0.003, h + 0.0075), (-0.004, -r - 0.07, h + 0.03), (-0.012, -r - 0.15, h + 0.052)]
        kit.tube('spoon_handle', sp[1:], 0.0055, M['spoonwood'], segs=8, radii=[0.004, 0.0055, 0.006, 0.0065])
        with kit.xform(T(0.02, 0.035, 0.064) @ Rx(-20) @ SC(1.0, 1.6, 0.35)):
            kit.lathe('spoon_bowl', [(0, -0.006), (0.016, -0.004), (0.02, 0.003), (0.016, 0.006), (0, 0.0065)], M['spoonwood'], segs=12)
    # lid, tilted: back edge resting on the rim, front edge propped on the spoon handle
    with kit.xform(T(px, py + 0.088, zb + 0.098) @ Rx(-5) @ T(0, -0.091, 0)), kit.props(td=1.4):
        kit.lathe('pot_lid', [(0, 0.020), (0.02, 0.019), (0.06, 0.010), (0.086, -0.001), (0.094, -0.003), (0.094, 0.0), (0.088, 0.003),
                              (0.06, 0.014), (0.02, 0.023), (0, 0.024)], M['alu'], segs=28)
        kit.lathe('pot_lid_knob', [(0.006, 0.023), (0.007, 0.03), (0.016, 0.033), (0.016, 0.040), (0, 0.042)], M['bakelite'], segs=12)

def kettle():
    kx, ky = 2.20, layout.POINTS['hob'][1]; zb = layout.KITCHENETTE['top_z'] + 0.032
    with kit.xform(T(kx, ky, zb)), kit.props(td=0.9):
        kit.lathe('kettle', [(0, 0.0), (0.078, 0.0), (0.086, 0.008), (0.088, 0.05), (0.080, 0.075), (0.055, 0.098), (0.040, 0.104),
                             (0.036, 0.104), (0, 0.104)], M['kettle'], segs=24)
        kit.lathe('kettle_lid', [(0.040, 0.104), (0.040, 0.108), (0.03, 0.113), (0.012, 0.116), (0.006, 0.117), (0.008, 0.126), (0, 0.128)],
                  M['kettle'], segs=16)
        with kit.xform(Rz(-150)):
            kit.tube('kettle_spout', [(0.070, 0, 0.025), (0.098, 0, 0.055), (0.118, 0, 0.088), (0.128, 0, 0.098)], 0.011, M['kettle'], segs=8,
                     radii=[0.016, 0.012, 0.0085, 0.0075])
        kit.tube('kettle_handle', [(0, -0.05, 0.088), (0, -0.045, 0.14), (0, 0.0, 0.165), (0, 0.045, 0.14), (0, 0.05, 0.088)], 0.0035, M['chrome'], segs=6)
        kit.tube('kettle_grip', [(0, -0.026, 0.158), (0, 0.0, 0.166), (0, 0.026, 0.158)], 0.008, M['bakelite'], segs=8)

def rack_and_shelf():
    yb = layout.KITCHENETTE['y1']
    # --- wire dish rack on the wall over the sink, three plates and two upturned glasses
    rx0, rx1, ry0, ry1, rz = 2.655, 2.955, yb - 0.17, yb - 0.008, 1.10
    w = 0.0019
    with kit.props(td=0.9):
        frame = [(rx0, ry1, rz), (rx0, ry0, rz), (rx1, ry0, rz), (rx1, ry1, rz)]
        kit.tube('rack_wire', frame + [(rx0, ry1, rz)], w, M['chrome'], segs=4, caps=False)
        kit.tube('rack_wire', [(rx0, ry0, rz + 0.07), (rx1, ry0, rz + 0.07)], w, M['chrome'], segs=4)
        for x in (rx0, rx1):
            kit.tube('rack_wire', [(x, ry0, rz), (x, ry0, rz + 0.07), (x, ry1, rz + 0.20)], w, M['chrome'], segs=4)
        for i in range(9):
            x = rx0 + 0.015 + i * 0.03
            kit.tube('rack_wire', [(x, ry1, rz), (x, ry0, rz)], w * 0.8, M['chrome'], segs=4)
        for i in range(5):
            x = rx0 + 0.03 + i * 0.024
            kit.tube('rack_wire', [(x, ry0, rz + 0.07), (x, ry0 + 0.02, rz + 0.005), (x, ry1 - 0.01, rz + 0.005), (x, ry1 - 0.01, rz + 0.11)],
                     w * 0.8, M['chrome'], segs=4, caps=False)
        for k in range(3):
            x = rx0 + 0.04 + k * 0.024
            with kit.xform(T(x, (ry0 + ry1) / 2 + 0.006, rz + 0.098) @ Rz(0) @ Ry(90 - 6)):
                kit.lathe('plate', [(0, -0.003), (0.05, -0.003), (0.062, 0.0), (0.095, 0.010), (0.099, 0.014), (0.096, 0.016), (0.090, 0.0125),
                                    (0.06, 0.004), (0, 0.003)], M['plate'], segs=22)
        for k in range(2):
            gx = rx1 - 0.10 + k * 0.065
            with kit.xform(T(gx, (ry0 + ry1) / 2, rz + 0.002 + 0.09) @ Rx(180)):
                kit.lathe('rack_glass', [(0, 0), (0.028, 0.0), (0.030, 0.003), (0.034, 0.09), (0.0325, 0.09), (0.0285, 0.008), (0, 0.008)],
                          M['glass'], segs=18)
    # --- wall shelf with tins, jars and bottles
    sx0, sx1, sz = 2.50, 3.27, 1.37
    with kit.props(td=0.6):
        kit.box('shelf_board', sx0, sx1, yb - 0.17, yb, sz - 0.02, sz, M['pine'], bevel=0.003, skip='+y')
        for x in (sx0 + 0.07, sx1 - 0.07):
            kit.tube('shelf_bracket', [(x, yb, sz - 0.13), (x, yb - 0.004, sz - 0.11), (x, yb - 0.12, sz - 0.024), (x, yb - 0.14, sz - 0.021),
                                       (x, yb, sz - 0.021)], 0.004, M['iron'], segs=5)
    with kit.props(td=1.0):
        y = yb - 0.08
        def bottle(name, x, r, h, glassmat, label, capmat, neck=0.05):
            kit.lathe(name, [(0, sz), (r, sz), (r, sz + h * 0.62), (r * 0.9, sz + h * 0.72), (r * 0.4, sz + h - neck * 0.5),
                             (r * 0.33, sz + h - 0.012), (r * 0.36, sz + h), (0, sz + h)], glassmat, segs=18, center=(x, y, 0))
            kit.cyl(name + '_cap', x, y, sz + h - 0.016, sz + h + 0.005, r * 0.40, capmat, segs=12)
            kit.cyl_patch(name + '_label', x, y, sz + h * 0.12, sz + h * 0.55, r + 0.0005, -150, -30, M['label'], uvrect=Rrect(label), segs=8)
        bottle('soy', 2.545, 0.036, 0.23, M['soy'], 'soy', M['redcap'])
        bottle('oil', 2.625, 0.032, 0.25, M['oil'], 'oil', M['redcap'])
        def tin(name, x, r, h, label, lidmat):
            kit.lathe(name, [(0, sz), (r, sz), (r, sz + h), (0, sz + h)], M['lid'], segs=20, center=(x, y, 0))
            kit.cyl_patch(name + '_label', x, y, sz + 0.008, sz + h - 0.012, r + 0.0006, -180, 180, M['label'], uvrect=Rrect(label), segs=20)
            kit.lathe(name + '_lid', [(r + 0.002, sz + h - 0.014), (r + 0.002, sz + h + 0.004), (r - 0.003, sz + h + 0.006), (0, sz + h + 0.006)],
                      lidmat, segs=20, center=(x, y, 0))
        tin('tin_tea', 2.725, 0.044, 0.13, 'tin_tea', M['lid'])
        tin('tin_coffee', 2.84, 0.05, 0.12, 'tin_coffee', M['lid'])
        tin('tin_biscuit', 2.965, 0.06, 0.08, 'tin_biscuit', M['redcap'])
        def jar(name, x, r, h, fillmat, label):
            kit.lathe(name + '_fill', [(0, sz + 0.004), (r - 0.003, sz + 0.004), (r - 0.003, sz + h * 0.72), (0, sz + h * 0.74)], fillmat, segs=16,
                      center=(x, y, 0))
            kit.lathe(name, [(0, sz), (r, sz), (r, sz + h * 0.85), (r * 0.82, sz + h * 0.9), (r * 0.8, sz + h), (r * 0.75, sz + h),
                             (r * 0.75, sz + h * 0.9), (r - 0.002, sz + h * 0.85), (r - 0.002, sz + 0.004), (0, sz + 0.004)], M['glass'],
                      segs=16, center=(x, y, 0))
            kit.cyl(name + '_lid', x, y, sz + h, sz + h + 0.014, r * 0.82, M['lid'], segs=16)
            kit.cyl_patch(name + '_label', x, y, sz + h * 0.25, sz + h * 0.62, r + 0.0006, -140, -40, M['label'], uvrect=Rrect(label), segs=6)
        jar('jar_ume', 3.09, 0.045, 0.11, M['jarred'], 'jar_a')
        jar('jar_sugar', 3.19, 0.042, 0.10, M['sugar'], 'jar_b')
    # --- rail with a frying pan and a ladle, left of the shelf
    rz2 = 1.345
    with kit.props(td=0.6):
        kit.tube('rail', [(2.075, yb - 0.035, rz2), (2.48, yb - 0.035, rz2)], 0.006, M['chrome'], segs=8)
        for x in (2.08, 2.475):
            kit.tube('rail_post', [(x, yb, rz2), (x, yb - 0.035, rz2)], 0.005, M['chrome'], segs=6)
        # frying pan hanging flat against the wall
        with kit.xform(T(2.24, yb - 0.006, rz2 - 0.215) @ Rx(90)):
            kit.lathe('fpan', [(0, 0.0), (0.085, 0.0), (0.105, 0.03), (0.107, 0.031), (0.106, 0.033), (0.101, 0.031), (0.082, 0.004), (0, 0.004)],
                      M['iron'], segs=24)
        kit.tube('fpan_handle', [(2.24, yb - 0.026, rz2 - 0.11), (2.24, yb - 0.014, rz2 - 0.02)], 0.009, M['bakelite'], segs=8,
                 radii=[0.008, 0.0065])
        kit.tube('hook', [(2.24, yb - 0.035, rz2), (2.24, yb - 0.04, rz2 - 0.012), (2.24, yb - 0.025, rz2 - 0.02), (2.24, yb - 0.012, rz2 - 0.012)],
                 0.0015, M['chrome'], segs=4)
        lx = 2.43
        kit.tube('ladle', [(lx, yb - 0.035, rz2 + 0.004), (lx, yb - 0.045, rz2 - 0.02), (lx, yb - 0.035, rz2 - 0.25)], 0.0035, M['chrome'], segs=6)
        with kit.xform(T(lx, yb - 0.07, rz2 - 0.262)):
            kit.lathe('ladle_bowl', [(0, -0.03), (0.022, -0.027), (0.035, -0.012), (0.038, 0.0), (0.035, 0.0), (0.032, -0.010), (0.02, -0.023), (0, -0.026)],
                      M['chrome'], segs=16)

def fridge():
    K = layout.KITCHENETTE; zt = K['top_z']
    fx0, fx1, fy0, fy1 = 2.985, 3.395, K['y0'] + 0.03, K['y1'] - 0.012
    with kit.props(td=0.35):
        kit.box('fridge_body', fx0, fx1, fy0, fy1, 0.03, zt, M['fridge'], bevel=0.035, segs=3, skip='+y -y')
        kit.box('fridge_door', fx0 + 0.006, fx1 - 0.006, fy0 - 0.022, fy0 + 0.01, 0.06, zt - 0.025, M['fridge'], bevel=0.02, segs=3, skip='+y')
        kit.box('fridge_gasket', fx0 + 0.012, fx1 - 0.012, fy0 - 0.002, fy0 + 0.002, 0.07, zt - 0.033, M['rubber'], skip='+y')
        for x in (fx0 + 0.04, fx1 - 0.04):
            kit.cyl('fridge_foot', x, fy0 + 0.04, 0.0, 0.03, 0.012, M['rubber'], segs=8, cap='t')
        kit.box('fridge_plinth', fx0 + 0.02, fx1 - 0.02, fy0 + 0.02, fy1 - 0.02, 0.0, 0.032, M['rubber'], skip='+y -z')
    with kit.props(td=0.8):
        hx = fx0 + 0.04
        kit.tube('fridge_handle', [(hx, fy0 - 0.022, 0.70), (hx, fy0 - 0.05, 0.69), (hx, fy0 - 0.055, 0.58), (hx, fy0 - 0.05, 0.47),
                                   (hx, fy0 - 0.022, 0.46)], 0.008, M['chrome'], segs=8)
        kit.quad('fridge_badge', [(fx1 - 0.15, fy0 - 0.0225, 0.75), (fx1 - 0.05, fy0 - 0.0225, 0.75), (fx1 - 0.05, fy0 - 0.0225, 0.783),
                                  (fx1 - 0.15, fy0 - 0.0225, 0.783)], M['label'], uv=(R('badge', 0, 0), R('badge', 1, 0), R('badge', 1, 1), R('badge', 0, 1)))
    # tea towel folded over a bar on the sink cabinet door
    yf = K['y0']
    with kit.props(td=0.6):
        kit.tube('towel_bar', [(2.62, yf + 0.022, 0.73), (2.62, yf - 0.012, 0.73), (2.94, yf - 0.012, 0.73), (2.94, yf + 0.022, 0.73)],
                 0.004, M['chrome'], segs=6)
        def towel(u, v):
            x = 2.66 + 0.21 * u
            zz = 0.735 - (1 - v) * 0.30
            y = yf - 0.012 - 0.006 - 0.004 * math.sin(u * 9.0 + v * 2) * (1 - v) - 0.003
            return (x, y, zz)
        grid('towel', 6, 6, towel, M['towel'])
        grid('towel_top', 3, 1, lambda u, v: (2.66 + 0.21 * u, yf - 0.012 - 0.006 + 0.012 * v, 0.738 + 0.004 * math.sin(math.pi * v)), M['towel'])

def radio():
    ox, oy, oz = layout.INTERACTIVE['radio'][1]
    sx, sy, sz = layout.INTERACTIVE['radio'][2]
    x0, x1, y0, y1, z0, z1 = ox - sx / 2, ox + sx / 2, oy - sy / 2, oy + sy / 2, oz, oz + sz
    with kit.interactive('radio', origin=(ox, oy, oz), td=2.0):
        with kit.props(td=1.3):
            tbox('radio_body', x0, x1, y0 + 0.004, y1, z0 + 0.004, z1, M['radiobody'], bevel=0.012, segs=3, skip='-z')
        tbox('radio_front', x0 + 0.006, x1 - 0.006, y0, y0 + 0.012, z0 + 0.006, z1 - 0.006, M['chrome'], M['print'], faces={'-y': 'radio'},
             bevel=0.004, segs=2)
        kit.cyl('radio_feet', x0 + 0.03, oy, z0, z0 + 0.004, 0.006, M['rubber'], segs=8, cap='')
        kit.cyl('radio_feet', x1 - 0.03, oy, z0, z0 + 0.004, 0.006, M['rubber'], segs=8, cap='')
        # knobs on top: tuning (big, knurled) and volume
        kit.lathe('radio_tune', [(0, z1), (0.016, z1), (0.016, z1 + 0.014), (0.014, z1 + 0.016), (0, z1 + 0.016)], M['bakelite'], segs=16,
                  center=(x1 - 0.045, oy, 0), smooth=False)
        kit.lathe('radio_tune_cap', [(0.0105, z1 + 0.0162), (0.0108, z1 + 0.0168), (0, z1 + 0.017)], M['chrome'], segs=16, center=(x1 - 0.045, oy, 0))
        kit.lathe('radio_vol', [(0, z1), (0.011, z1), (0.011, z1 + 0.012), (0.009, z1 + 0.014), (0, z1 + 0.014)], M['bakelite'], segs=12,
                  center=(x1 - 0.088, oy, 0))
        # carrying handle (folded down a little toward the back)
        hz = z1 - 0.025
        for s in (-1, 1):
            with kit.xform(T(ox + s * (sx / 2), oy + 0.01, hz) @ Ry(90 * s)):
                kit.lathe('radio_pivot', [(0, 0), (0.008, 0.0), (0.008, 0.004), (0, 0.0045)], M['chrome'], segs=10)
        hp = []
        for i in range(13):
            a = math.pi * i / 12
            hp.append((ox - (sx / 2 + 0.005) * math.cos(a), oy + 0.01 + 0.02 * math.sin(a), hz + 0.05 * math.sin(a) ** 0.6))
        kit.tube('radio_handle', hp, 0.0042, M['chrome'], segs=8)
        # telescopic aerial, pulled out, leaning left and back
        base = Vector((x1 - 0.012, y1 - 0.012, z1))
        d = Vector((-0.50, 0.04, 0.86)).normalized()
        kit.cyl('radio_aerial_base', base.x, base.y, z1 - 0.002, z1 + 0.008, 0.007, M['chrome'], segs=10)
        segs_ = [(0.0045, 0.10), (0.0036, 0.09), (0.0028, 0.09), (0.0021, 0.08)]
        p = base + d * 0.006
        for r, ln in segs_:
            q = p + d * ln
            kit.tube('radio_aerial', [tuple(p), tuple(q)], r, M['chrome'], segs=6)
            p = q - d * 0.006
        kit.lathe('radio_aerial_tip', [(0, -0.004), (0.004, -0.002), (0.004, 0.002), (0, 0.004)], M['chrome'], segs=8, center=tuple(p + d * 0.01))

# ------------------------------------------------------------------------------------------------ wall: calendar, apron
def wall_things():
    xw = layout.NOOK['x1'] - 0.002
    # calendar on the right wall (faces -X), a thin pad with a curl at the bottom
    y0, y1, z0, z1 = 2.13, 2.43, 1.075, 1.505
    with kit.props(td=1.3):
        def cal(u, v):
            curl = 0.010 * max(0, (0.12 - v) / 0.12) ** 2
            return (xw - 0.0035 - curl, y1 - (y1 - y0) * u, z0 + (z1 - z0) * v)
        grid('calendar', 3, 6, cal, M['print'], 'calendar')
        tbox('calendar_pad', xw - 0.0034, xw, y0 + 0.002, y1 - 0.002, z0 + 0.012, z1 - 0.002, M['paperedge'], skip='+x -x')
        with kit.xform(T(xw, (y0 + y1) / 2, z1 - 0.016) @ Ry(-90)):
            kit.lathe('calendar_nail', [(0, 0.0), (0.0016, 0.0), (0.0016, 0.007), (0.004, 0.007), (0.004, 0.0085), (0, 0.009)], M['iron'], segs=8)
    # two hooks and an apron hanging from them
    ya, yb_, zh = 2.66, 2.83, 1.47
    with kit.props(td=0.7):
        for y in (ya, yb_):
            with kit.xform(T(xw, y, zh) @ Ry(-90)):
                kit.lathe('hook_rose', [(0, 0), (0.012, 0.0), (0.011, 0.005), (0, 0.006)], M['brass'], segs=10)
            kit.tube('hook', [(xw - 0.004, y, zh), (xw - 0.035, y, zh - 0.004), (xw - 0.045, y, zh + 0.012)], 0.0035, M['brass'], segs=6)
        def apron(u, v):
            t = 1 - v
            y = yb_ + 0.03 - (yb_ - ya + 0.06) * u - (u - 0.5) * 0.06 * t
            z = 1.44 - 0.55 * t
            x = (xw - 0.010 - 0.008 * math.sin(u * math.pi) * (0.3 + 0.7 * t)
                 - 0.013 * (0.5 + 0.5 * math.sin(u * 2 * math.pi * 2.5 + t * 1.5)) * t ** 0.8)
            return (x, y, z)
        grid('apron', 12, 8, apron, M['apron'])
        for y in (ya, yb_):
            grid('apron_strap', 1, 3, lambda u, v, y=y: (xw - 0.035 - 0.006 * math.sin(v * math.pi), y + 0.009 - 0.018 * u, 1.43 + 0.05 * v), M['apron'])
        for k, y in enumerate((ya - 0.035, yb_ + 0.035)):
            grid('apron_tie', 1, 4, lambda u, v, y=y, k=k: (xw - 0.016 - 0.01 * math.sin(v * 2.0), y + 0.008 - 0.016 * u + 0.02 * (1 - v) * (k - 0.5),
                                                            1.20 - 0.38 * (1 - v)), M['apron'])

# ------------------------------------------------------------------------------------------------
def build():
    materials()
    table()
    chair('chair_a', 2.66, 1.92, -40)            # pulled out, turned: someone just stood up
    chair('chair_b', 3.175, 2.57, 90)             # tucked in at the end of the table, back to the wall
    manuscript()
    table_things()
    bulb()
    noren()
    kitchenette()
    fridge()
    radio()
    wall_things()

LIGHTS = []
