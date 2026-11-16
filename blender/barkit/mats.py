"""Procedural Cycles materials (all get baked)."""
import bpy, os, math

_M = {}

def N(nt, typ, **kw):
    n = nt.nodes.new(typ)
    for k, v in kw.items(): setattr(n, k, v)
    return n
def L(nt, a, b): nt.links.new(a, b)

def base(name):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree; nt.nodes.clear()
    out = N(nt, 'ShaderNodeOutputMaterial'); b = N(nt, 'ShaderNodeBsdfPrincipled')
    L(nt, b.outputs[0], out.inputs[0])
    _M[name] = m
    return m, nt, b, out

def setp(b, **kw):
    names = {'col': 'Base Color', 'rough': 'Roughness', 'metal': 'Metallic', 'ior': 'IOR', 'trans': 'Transmission Weight',
             'coat': 'Coat Weight', 'coat_rough': 'Coat Roughness', 'emit': 'Emission Color', 'emit_s': 'Emission Strength',
             'sheen': 'Sheen Weight', 'aniso': 'Anisotropic', 'spec': 'Specular IOR Level'}
    for k, v in kw.items():
        s = b.inputs[names[k]]
        if k in ('col', 'emit') and len(v) == 3: v = (*v, 1)
        s.default_value = v

def mixc(nt, a, bb, fac=1.0, blend='MULTIPLY'):
    n = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend)
    for sock, val in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], bb)):
        if hasattr(val, 'links'): L(nt, val, sock)
        else: sock.default_value = val if not isinstance(val, tuple) else (*val, 1)[:4]
    return n.outputs[2]

def math_(nt, op, a, b=None, clamp=False):
    n = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    for sock, val in ((n.inputs[0], a), (n.inputs[1], b)):
        if val is None: continue
        if hasattr(val, 'links'): L(nt, val, sock)
        else: sock.default_value = val
    return n.outputs[0]

def ramp(nt, fac, stops, interp='LINEAR'):
    n = N(nt, 'ShaderNodeValToRGB')
    cr = n.color_ramp; cr.interpolation = interp
    while len(cr.elements) < len(stops): cr.elements.new(0.5)
    for e, (p, c) in zip(cr.elements, stops):
        e.position = p; e.color = (*c, 1) if len(c) == 3 else c
    L(nt, fac, n.inputs[0])
    return n.outputs[0]

def coords(nt, scale=(1, 1, 1), rot=(0, 0, 0)):
    tc = N(nt, 'ShaderNodeTexCoord'); mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Scale'].default_value = scale; mp.inputs['Rotation'].default_value = rot
    L(nt, tc.outputs['Object'], mp.inputs[0])
    return mp.outputs[0]

def noise(nt, vec, scale=5, detail=4, rough=0.55, dist=0.0):
    n = N(nt, 'ShaderNodeTexNoise')
    n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = dist
    L(nt, vec, n.inputs['Vector'])
    return n.outputs[0]

def bump(nt, b, height, strength=0.2, dist=0.002):
    n = N(nt, 'ShaderNodeBump')
    n.inputs['Strength'].default_value = strength; n.inputs['Distance'].default_value = dist
    L(nt, height, n.inputs['Height']); L(nt, n.outputs[0], b.inputs['Normal'])

def wood(name, axis='X', cols=((0.04, 0.018, 0.009), (0.15, 0.065, 0.028), (0.26, 0.12, 0.05)), rough=0.3, rvar=0.12,
         scale=1.0, bmp=0.12, coat=0.0):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    lo, cr = 0.7 * scale, 16 * scale
    sc = {'X': (lo, cr, cr), 'Y': (cr, lo, cr), 'Z': (cr, cr, lo)}[axis]
    v = coords(nt, sc)
    v2 = coords(nt, tuple(s * 0.22 for s in sc))
    streak = noise(nt, v, 2.2, 7, 0.62, 1.4)
    broad = noise(nt, v2, 1.6, 3, 0.5, 0.6)
    f = math_(nt, 'ADD', math_(nt, 'MULTIPLY', streak, 0.62), math_(nt, 'MULTIPLY', broad, 0.38))
    col = ramp(nt, f, [(0.30, cols[0]), (0.52, cols[1]), (0.72, cols[2])])
    L(nt, col, b.inputs['Base Color'])
    r = math_(nt, 'ADD', rough - rvar * 0.5, math_(nt, 'MULTIPLY', broad, rvar), clamp=True)
    L(nt, r, b.inputs['Roughness'])
    bump(nt, b, streak, bmp, 0.0015)
    setp(b, coat=coat, coat_rough=0.08)
    return m

def metal(name, col, rough=0.3, rvar=0.15, patina=0.35, scale=18):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    v = coords(nt)
    n1 = noise(nt, v, scale, 5, 0.6)
    n2 = noise(nt, v, scale * 6, 3, 0.5)
    k = ramp(nt, n1, [(0.35, (1 - patina,) * 3), (0.65, (1, 1, 1))])
    L(nt, mixc(nt, col, k, 1.0), b.inputs['Base Color'])
    r = math_(nt, 'ADD', rough - rvar * 0.5, math_(nt, 'MULTIPLY', n1, rvar), clamp=True)
    L(nt, r, b.inputs['Roughness'])
    setp(b, metal=1.0)
    bump(nt, b, n2, 0.03, 0.0005)
    return m

def plain(name, col, rough=0.5, metal_=0.0, **kw):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    setp(b, col=col, rough=rough, metal=metal_, **kw)
    return m

def noisy(name, c0, c1, rough=0.6, scale=12, bmp=0.0, rvar=0.0, detail=4, sc3=(1, 1, 1), metal_=0.0, sheen=0.0):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    v = coords(nt, sc3)
    n1 = noise(nt, v, scale, detail, 0.6)
    L(nt, ramp(nt, n1, [(0.3, c0), (0.7, c1)]), b.inputs['Base Color'])
    if rvar:
        L(nt, math_(nt, 'ADD', rough - rvar / 2, math_(nt, 'MULTIPLY', n1, rvar), clamp=True), b.inputs['Roughness'])
    else: setp(b, rough=rough)
    setp(b, metal=metal_, sheen=sheen)
    if bmp: bump(nt, b, noise(nt, v, scale * 8, 3, 0.6), bmp, 0.001)
    return m

def leather(name, col=(0.085, 0.02, 0.015)):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    v = coords(nt)
    vor = N(nt, 'ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 260
    L(nt, v, vor.inputs['Vector'])
    n1 = noise(nt, v, 9, 5, 0.65)
    worn = ramp(nt, n1, [(0.35, tuple(c * 0.55 for c in col)), (0.75, tuple(min(1, c * 1.9) for c in col))])
    L(nt, worn, b.inputs['Base Color'])
    L(nt, math_(nt, 'ADD', 0.32, math_(nt, 'MULTIPLY', n1, 0.25)), b.inputs['Roughness'])
    h = math_(nt, 'ADD', vor.outputs[0], math_(nt, 'MULTIPLY', n1, 0.6))
    bump(nt, b, h, 0.25, 0.0008)
    return m

def tiles(name, col=(0.012, 0.05, 0.035)):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    tc = N(nt, 'ShaderNodeTexCoord'); mp = N(nt, 'ShaderNodeMapping')
    mp.inputs['Rotation'].default_value = (math.radians(90), 0, 0)
    L(nt, tc.outputs['Object'], mp.inputs[0])
    br = N(nt, 'ShaderNodeTexBrick'); br.offset = 0.5
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Mortar Size'].default_value = 0.004; br.inputs['Brick Width'].default_value = 0.15
    br.inputs['Row Height'].default_value = 0.075; br.inputs['Bias'].default_value = 0.0
    br.inputs['Color1'].default_value = (*col, 1); br.inputs['Color2'].default_value = (*[c * 0.7 for c in col], 1)
    br.inputs['Mortar'].default_value = (0.05, 0.045, 0.04, 1)
    L(nt, mp.outputs[0], br.inputs['Vector'])
    L(nt, br.outputs['Color'], b.inputs['Base Color'])
    L(nt, math_(nt, 'ADD', 0.08, math_(nt, 'MULTIPLY', br.outputs['Fac'] if 'Fac' in br.outputs else br.outputs[1], 0.6)), b.inputs['Roughness'])
    bump(nt, b, br.outputs[1], -0.4, 0.002)
    setp(b, coat=0.6, coat_rough=0.05)
    return m

def planks(name, axis='X', cols=((0.012, 0.007, 0.004), (0.035, 0.018, 0.009), (0.06, 0.03, 0.014)), width=0.12, rough=0.55):
    """wood with plank seams (walls / ceiling / floor)"""
    if name in _M: return _M[name]
    m = wood(name, axis, cols, rough=rough, bmp=0.1)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = N(nt, 'ShaderNodeTexCoord'); sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Object'], sep.inputs[0])
    cross = {'X': 'Y', 'Y': 'X', 'Z': 'X'}[axis]
    if name.endswith('_wallx'): cross = 'Y'
    if name.endswith('_wally'): cross = 'X'
    u = math_(nt, 'DIVIDE', sep.outputs[cross], width)
    fr = math_(nt, 'FRACT', u)
    seam = math_(nt, 'LESS_THAN', fr, 0.035)
    plank_id = math_(nt, 'FLOOR', u)
    wn = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D'); L(nt, plank_id, wn.inputs['W'])
    tint = math_(nt, 'ADD', 0.7, math_(nt, 'MULTIPLY', wn.outputs[0], 0.6))
    old = b.inputs['Base Color'].links[0].from_socket
    c1 = mixc(nt, old, tint, 1.0)   # multiply by a grey (float socket -> colour is fine)
    c2 = mixc(nt, c1, (0.15, 0.15, 0.15), seam)
    L(nt, c2, b.inputs['Base Color'])
    return m

def emissive(name, col, strength, night_only=True):
    """light-emitting surface (bulb, lamp-shade interior, valve, indicator, VU meter...).
    night_only=True  -> name gets the prefix EMN_ : switched OFF in the daytime bake (room lamps)
    night_only=False -> name gets the prefix EMA_ : on in both bakes (hi-fi pilot lights, the stairwell glow...)"""
    name = ('EMN_' if night_only else 'EMA_') + name
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    setp(b, col=(0, 0, 0), emit=col, emit_s=strength, rough=0.5)
    return m

def image(name, file, rough=0.6, uvmap='uv_tex', coat=0.0, tint=None):
    """material from a painted image (absolute path), mapped with the mesh's uv_tex layer (kit.quad / kit.cyl_patch / disc write it)."""
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    uv = N(nt, 'ShaderNodeUVMap'); uv.uv_map = uvmap
    t = N(nt, 'ShaderNodeTexImage'); t.image = bpy.data.images.load(file, check_existing=True)   # file: ABSOLUTE path
    t.name = 'SRC'
    L(nt, uv.outputs[0], t.inputs[0])
    if tint: L(nt, mixc(nt, t.outputs[0], tint, 1.0), b.inputs['Base Color'])
    else: L(nt, t.outputs[0], b.inputs['Base Color'])
    setp(b, rough=rough, coat=coat, coat_rough=0.1)
    return m

def glass(name, col=(1, 1, 1), rough=0.0, shadow=(1, 1, 1), shadow_amt=0.85, ior=1.5):
    """glass that lets (tinted) light through on shadow rays -> cheap fake caustic glow"""
    if name in _M: return _M[name]
    m, nt, b, out = base(name)
    setp(b, col=col, rough=rough, trans=1.0, ior=ior)
    tr = N(nt, 'ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (*shadow, 1)
    lp = N(nt, 'ShaderNodeLightPath'); mx = N(nt, 'ShaderNodeMixShader')
    L(nt, math_(nt, 'MULTIPLY', lp.outputs['Is Shadow Ray'], shadow_amt), mx.inputs[0])
    L(nt, b.outputs[0], mx.inputs[1]); L(nt, tr.outputs[0], mx.inputs[2]); L(nt, mx.outputs[0], out.inputs[0])
    return m

def shade_paper(name, col=(0.9, 0.62, 0.32)):
    if name in _M: return _M[name]
    m, nt, b, out = base(name)
    nt.nodes.remove(b)
    d = N(nt, 'ShaderNodeBsdfDiffuse'); t = N(nt, 'ShaderNodeBsdfTranslucent'); mx = N(nt, 'ShaderNodeMixShader')
    d.inputs[0].default_value = (*col, 1); t.inputs[0].default_value = (*col, 1)
    mx.inputs[0].default_value = 0.55
    L(nt, d.outputs[0], mx.inputs[1]); L(nt, t.outputs[0], mx.inputs[2]); L(nt, mx.outputs[0], out.inputs[0])
    return m

def vinyl(name, center=(0, 0, 0)):
    """black vinyl with a radial anisotropic highlight; tangent computed from world position so it survives joins"""
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    setp(b, col=(0.006, 0.006, 0.007), rough=0.3, aniso=0.92)
    geo = N(nt, 'ShaderNodeNewGeometry')
    sub = N(nt, 'ShaderNodeVectorMath', operation='SUBTRACT'); L(nt, geo.outputs['Position'], sub.inputs[0]); sub.inputs[1].default_value = center
    cr = N(nt, 'ShaderNodeVectorMath', operation='CROSS_PRODUCT'); cr.inputs[0].default_value = (0, 0, 1); L(nt, sub.outputs[0], cr.inputs[1])
    nm = N(nt, 'ShaderNodeVectorMath', operation='NORMALIZE'); L(nt, cr.outputs[0], nm.inputs[0])
    L(nt, nm.outputs[0], b.inputs['Tangent'])
    ln = N(nt, 'ShaderNodeVectorMath', operation='LENGTH'); L(nt, sub.outputs[0], ln.inputs[0])
    wn = N(nt, 'ShaderNodeTexWhiteNoise', noise_dimensions='1D')
    L(nt, math_(nt, 'FLOOR', math_(nt, 'MULTIPLY', ln.outputs['Value'], 45)), wn.inputs['W'])
    L(nt, math_(nt, 'ADD', 0.22, math_(nt, 'MULTIPLY', wn.outputs[0], 0.16)), b.inputs['Roughness'])
    return m

def globe(name):
    if name in _M: return _M[name]
    m, nt, b, _ = base(name)
    v = coords(nt)
    n1 = noise(nt, v, 9, 6, 0.6, 0.3)
    col = ramp(nt, n1, [(0.47, (0.16, 0.17, 0.10)), (0.5, (0.07, 0.04, 0.02)), (0.53, (0.36, 0.24, 0.10)), (0.8, (0.28, 0.16, 0.07))])
    L(nt, col, b.inputs['Base Color'])
    setp(b, rough=0.3, coat=0.3)
    return m
