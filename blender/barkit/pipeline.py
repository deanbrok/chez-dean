"""Build / unwrap / light / preview / bake / export pipeline shared by every part agent and by the final assembly."""
import bpy, bmesh, sys, os, math, json, time, importlib.util
import numpy as np
from mathutils import Vector
from . import kit, mats, layout, tm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # .../blender
OUT = os.path.join(ROOT, 'out'); SITE = os.path.join(os.path.dirname(ROOT), 'site')   # repo/site is the deployed folder
THREADS = int(os.environ.get('BAR_THREADS', '1'))
sc = None
PACK_KW = {}
EXTRA_LIGHTS = []

def new_scene():
    global sc
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    kit.OBJS.clear(); kit.PARTS.clear(); kit._PID[0] = 0; mats._M.clear(); EXTRA_LIGHTS.clear()
    props_ = bpy.ops.uv.pack_islands.get_rna_type().properties.keys()
    if 'shape_method' in props_: PACK_KW['shape_method'] = 'AABB'
    if 'margin_method' in props_: PACK_KW['margin_method'] = 'FRACTION'
    return sc

def cycles_setup(samples=16):
    sc.render.engine = 'CYCLES'; c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
    c.use_adaptive_sampling = True; c.adaptive_threshold = 0.01
    c.max_bounces = 8; c.diffuse_bounces = 4; c.glossy_bounces = 4; c.transmission_bounces = 8; c.transparent_max_bounces = 8
    c.caustics_reflective = False; c.caustics_refractive = False
    c.sample_clamp_indirect = 8.0; c.blur_glossy = 0.4
    sc.render.threads_mode = 'FIXED'; sc.render.threads = THREADS
    sc.view_settings.view_transform = 'Standard'

# ------------------------------------------------------------------ parts
def load_part(name):
    """imports parts/<name>/build.py and runs its build() with kit.props(atlas=<name>)"""
    path = os.path.join(ROOT, 'parts', name, 'build.py')
    spec = importlib.util.spec_from_file_location('part_' + name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules['part_' + name] = mod
    sys.path.insert(0, os.path.dirname(path))
    try:
        spec.loader.exec_module(mod)
        n0 = len(kit.OBJS)
        with kit.props(atlas=name, td=1.0, part=0):
            mod.build()
    finally:
        sys.path.remove(os.path.dirname(path))
        # a part's helper modules (e.g. its own tex.py) must not shadow another part's module of the same name
        d = os.path.dirname(path) + os.sep
        for k in [k for k, m in sys.modules.items() if k != 'part_' + name and (getattr(m, '__file__', None) or '').startswith(d)]:
            del sys.modules[k]
    for o in kit.OBJS[n0:]:
        a = o['atlas']
        assert a == name or a.startswith(name + '_'), 'atlas %r of %s must be %r or start with %r' % (a, o.name, name, name + '_')
        if name == 'cat': o.visible_shadow = False       # only one cat is shown at a time: no baked cat shadows
    EXTRA_LIGHTS.extend(getattr(mod, 'LIGHTS', []))
    print('PART %s: %d objects' % (name, len(kit.OBJS) - n0), flush=True)

def blockout(names):
    g = mats.plain('_blockout_grey', (0.22, 0.2, 0.18), rough=0.8)
    with kit.props(atlas='_blockout'):
        for n in names:
            for i, (x0, x1, y0, y1, z0, z1) in enumerate(layout.BLOCKS[n]):
                kit.box('_blk_%s_%d' % (n, i), x0, x1, y0, y1, z0, z1, g)

# ------------------------------------------------------------------ lights / modes / cameras
def light(name, kind, loc, energy, col, extra):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = col
    extra = dict(extra); aim = extra.pop('aim', None); r = extra.pop('radius', None)
    if r is not None: ld.shadow_soft_size = r
    for k, v in extra.items(): setattr(ld, k, v)
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob); ob.location = loc
    if aim is not None: ob.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return ob

def add_lights():
    for (name, kind, loc, energy, col, extra) in list(layout.LIGHTS) + EXTRA_LIGHTS:
        assert name[:2] in ('N_', 'B_'), 'light name must start with N_ (room lamps) or B_ (always on): ' + name
        light('L' + name, kind, loc, energy, col, extra)
    sc.world = bpy.data.worlds.new('w')
    try: sc.world.use_nodes = True
    except Exception: pass

def set_mode(mode='night'):
    """the bar only exists at night now: every light on, the world colour set. (Kept as a function so old calls work.)"""
    assert mode == 'night', 'there is no day bake any more'
    for o in sc.objects:
        if o.type == 'LIGHT': o.hide_render = False; o.hide_viewport = False
    bg = sc.world.node_tree.nodes.get('Background')
    if bg: bg.inputs[0].default_value = (*layout.WORLD[mode], 1); bg.inputs[1].default_value = 1.0

def camera(name, p, t, fov):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'VERTICAL'; cd.angle = math.radians(fov); cd.clip_start = 0.05
    ob = bpy.data.objects.new(name, cd); sc.collection.objects.link(ob)
    ob.location = p; ob.rotation_euler = (Vector(t) - Vector(p)).to_track_quat('-Z', 'Y').to_euler()
    return ob

def cameras():
    for k, (p, t, fov) in layout.STOPS.items(): camera('cam_' + k, p, t, fov)
    sc.camera = bpy.data.objects['cam_bar']

def render(path, cam='cam_bar', mode='night', w=640, h=360, samples=16):
    cycles_setup(samples); set_mode(mode)
    sc.camera = bpy.data.objects[cam]
    sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '16'
    exr = path + '.tmp.exr'; sc.render.filepath = exr
    t0 = time.time(); bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(exr); a = np.array(img.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img); os.remove(exr)
    print('render %s %s %.1fs' % (cam, mode, time.time() - t0), end='  ')
    tm.save(a, path)

# ------------------------------------------------------------------ UV atlases
def select_only(obs):
    for o in bpy.context.view_layer.objects: o.select_set(False)
    for o in obs: o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]

def keep_only(ob, pid):
    bm = bmesh.new(); bm.from_mesh(ob.data); lp = bm.faces.layers.int['part']
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f[lp] != pid], context='FACES')
    bm.to_mesh(ob.data); bm.free()

def atlases():
    return sorted({o['atlas'] for o in kit.OBJS if o['atlas'] != '_blockout'})

def unwrap_all():
    """unwraps every atlas; returns the atlas names"""
    groups = {}
    for o in kit.OBJS:
        if o['atlas'] != '_blockout': groups.setdefault(o['atlas'], []).append(o)
    kit.OBJS.clear()                       # joined objects are gone after this
    for a in sorted(groups): unwrap(a, groups[a])
    return sorted(groups)

def unwrap(atlas, obs):
    """joins every object of the atlas, unwraps + packs into one 0..1 square (island size x face 'td'), splits interactive parts off"""
    from bpy_extras import bmesh_utils
    select_only(obs)
    if len(obs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = atlas + '_static'; me = ob.data; me.name = ob.name
    me.uv_layers.active = me.uv_layers['uv_atlas']; me.uv_layers['uv_atlas'].active_render = True
    sc.tool_settings.use_uv_select_sync = True
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bm = bmesh.from_edit_mesh(me); uvl = bm.loops.layers.uv['uv_atlas']; ltd = bm.faces.layers.float['td']
    islands = bmesh_utils.bmesh_linked_uv_islands(bm, uvl)
    for isl in islands:
        k = max(f[ltd] for f in isl)
        c = Vector((0, 0)); n = 0
        for f in isl:
            for l in f.loops: c += l[uvl].uv; n += 1
        c /= n
        for f in isl:
            for l in f.loops: l[uvl].uv = c + (l[uvl].uv - c) * k
    bmesh.update_edit_mesh(me)
    nfaces = len(bm.faces)
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.0028, scale=True, **PACK_KW)
    bpy.ops.object.mode_set(mode='OBJECT')
    a = np.zeros(len(me.polygons), np.int32); me.attributes['part'].data.foreach_get('value', a); ids = set(a.tolist()) - {0}
    out = [ob]; names = []
    for pid in sorted(ids):
        o2 = ob.copy(); o2.data = me.copy(); sc.collection.objects.link(o2)
        keep_only(o2, pid)
        info = kit.PARTS[pid]; o2.name = info['name']; o2.data.name = info['name']
        assert o2.name == info['name'], 'duplicate object name ' + info['name']
        o2.data.transform(info['matrix'].inverted()); o2.matrix_world = info['matrix']
        o2['atlas'] = atlas; out.append(o2); names.append(info['name'])
    if ids: keep_only(ob, 0)
    if atlas == 'cat' or atlas.startswith('cat_'):
        for o in out: o.visible_shadow = False
    me.calc_loop_triangles()
    tris = sum(len(o.data.loop_triangles) if not o.data.calc_loop_triangles() else 0 for o in out)
    print('ATLAS %s: %d islands, %d faces, %d tris, interactive: %s' % (atlas, len(islands), nfaces, tris, names), flush=True)
    return out

def group(atlas):
    return [o for o in sc.objects if o.type == 'MESH' and o.get('atlas') == atlas]

# ------------------------------------------------------------------ baking
def _bake(obs, name, res, kind, samples, margin, outdir):
    c = sc.cycles
    img = bpy.data.images.new(name, res, res, alpha=True, float_buffer=True)
    for o in sc.objects: o.select_set(False)
    for o in obs:
        o.select_set(True)
        o.data.uv_layers.active = o.data.uv_layers['uv_atlas']; o.data.uv_layers['uv_atlas'].active_render = True
        for m in o.data.materials:
            nt = m.node_tree
            n = nt.nodes.get('BAKE') or nt.nodes.new('ShaderNodeTexImage'); n.name = 'BAKE'
            n.image = img
            for x in nt.nodes: x.select = False
            n.select = True; nt.nodes.active = n
    bpy.context.view_layer.objects.active = obs[0]
    c.samples = samples
    kw = dict(margin=margin, use_clear=True, target='IMAGE_TEXTURES', save_mode='INTERNAL')
    if 'margin_type' in bpy.ops.object.bake.get_rna_type().properties.keys(): kw['margin_type'] = 'EXTEND'
    if kind == 'combined': kw.update(type='COMBINED', pass_filter={'EMIT', 'DIRECT', 'INDIRECT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION'})
    elif kind == 'normal': kw.update(type='NORMAL', normal_space='OBJECT')
    else: kw.update(type='DIFFUSE', pass_filter={'COLOR'})
    t0 = time.time()
    bpy.ops.object.bake(**kw)
    a = np.array(img.pixels[:], np.float32).reshape(res, res, 4)[::-1]
    np.save(os.path.join(outdir, name + '.npy'), a.astype(np.float16))
    print('BAKED %s %s res=%d spp=%d  %.1fs  mean=%.4f  fill=%.2f' % (name, kind, res, samples, time.time() - t0, a[..., :3].mean(), (a[..., 3] > 0).mean()), flush=True)
    bpy.data.images.remove(img)

# full-resolution light at 64 samples (adaptive), then OpenImageDenoise with albedo + normal guides (see denoise()).
# Raise SPP / RES on a machine with more cores (or a GPU) for an even cleaner result.
RES = int(os.environ.get('BAR_RES', '2048')); SPP = int(os.environ.get('BAR_SPP', '64'))
ATLAS_RES = {'counter_b': 0.5}       # atlases that hold only a few small things: a fraction of RES is plenty

def bake(atlas, modes=('night',), test=False, outdir=None, albedo=True):
    """COMBINED (seen from the hero camera) + DIFFUSE colour + normals, all at full res -> <outdir>/*.npy"""
    outdir = outdir or os.path.join(OUT, 'bake'); os.makedirs(outdir, exist_ok=True)
    cycles_setup(); sc.camera = bpy.data.objects['cam_bar']
    bk = sc.render.bake; bk.view_from = 'ACTIVE_CAMERA'; bk.margin_type = 'EXTEND'; bk.target = 'IMAGE_TEXTURES'; bk.use_clear = True
    res = max(256, int(RES * ATLAS_RES.get(atlas, 1)))
    lo, hi, spp = (512, 512, 8) if test else (res, res, SPP)
    obs = group(atlas)
    assert obs, 'no objects in atlas ' + atlas
    if len(obs) > 1:           # one joined object => one bake (this scene is not saved afterwards)
        obs.sort(key=lambda o: not o.name.endswith('_static'))
        select_only(obs); bpy.ops.object.join(); obs = [bpy.context.view_layer.objects.active]
    set_mode('night')
    if albedo:
        _bake(obs, 'alb_' + atlas, hi, 'albedo', 4, 2 if test else 8, outdir)
        _bake(obs, 'nrm_' + atlas, hi, 'normal', 1, 2 if test else 8, outdir)
    for mode in modes:
        _bake(obs, 'cmb_%s_%s' % (atlas, mode), lo, 'combined', spp, 2 if test else 8, outdir)

def denoise(rgb, alb=None, nrm=None):
    """OpenImageDenoise through Blender's compositor (float RGB arrays, top row first) -> denoised float RGB"""
    H, W = rgb.shape[:2]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s2 = bpy.context.scene
    s2.render.engine = 'BLENDER_WORKBENCH'; s2.render.use_compositing = True
    s2.render.resolution_x = W; s2.render.resolution_y = H; s2.render.resolution_percentage = 100
    def mk(name, a):
        im = bpy.data.images.new(name, W, H, alpha=True, float_buffer=True)
        b = np.ones((H, W, 4), np.float32); b[..., :3] = a; im.pixels.foreach_set(b[::-1].ravel()); return im   # float = linear
    nt = bpy.data.node_groups.new('dn', 'CompositorNodeTree'); s2.compositing_node_group = nt
    nt.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    out = nt.nodes.new('NodeGroupOutput'); dn = nt.nodes.new('CompositorNodeDenoise')
    i1 = nt.nodes.new('CompositorNodeImage'); i1.image = mk('src', rgb); nt.links.new(i1.outputs[0], dn.inputs['Image'])
    for key, a in (('Albedo', alb), ('Normal', nrm)):
        if a is None: continue
        i = nt.nodes.new('CompositorNodeImage'); i.image = mk(key, a); nt.links.new(i.outputs[0], dn.inputs[key])
    nt.links.new(dn.outputs[0], out.inputs[0])
    s2.render.image_settings.file_format = 'OPEN_EXR'; s2.render.image_settings.color_depth = '32'
    f = os.path.join(OUT, '_dn.exr'); s2.render.filepath = f
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(f); a = np.array(im.pixels[:], np.float32).reshape(H, W, 4)[::-1, :, :3]
    bpy.data.images.remove(im); os.remove(f)
    return a

def _rs(a, size, f):
    from PIL import Image
    return np.stack([np.asarray(Image.fromarray(a[..., i].astype(np.float32), 'F').resize((size, size), f)) for i in range(3)], -1)

def _fill(a, alpha, it=6):
    a = a.copy(); m = alpha > 0
    for _ in range(it):
        acc = np.zeros_like(a); cnt = np.zeros(m.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            sm = np.roll(m, (dy, dx), (0, 1)); sa = np.roll(a, (dy, dx), (0, 1))
            acc += sa * sm[..., None]; cnt += sm
        new = (~m) & (cnt > 0)
        a[new] = acc[new] / cnt[new][..., None]; m = m | new
    return a, m

def post(atlas, modes=('night',), bakedir=None, outdir=None, quality=88, size=None):
    """denoise (albedo + normal guided), tone-map, JPEG -> <outdir>/<atlas>.jpg"""
    from PIL import Image
    bakedir = bakedir or os.path.join(OUT, 'bake'); outdir = outdir or os.path.join(SITE, 'tex'); os.makedirs(outdir, exist_ok=True)
    alb = np.load(os.path.join(bakedir, 'alb_%s.npy' % atlas)).astype(np.float32); H = alb.shape[0]
    a, _ = _fill(alb[..., :3], alb[..., 3], 16)
    pn = os.path.join(bakedir, 'nrm_%s.npy' % atlas)
    nrm = None
    if os.path.exists(pn):
        n = np.load(pn).astype(np.float32); nrm, _ = _fill(n[..., :3] * 2 - 1, n[..., 3], 16)
    for mode in modes:
        p = os.path.join(bakedir, 'cmb_%s_%s.npy' % (atlas, mode))
        if not os.path.exists(p): continue
        cmb = np.load(p).astype(np.float32)
        c, _ = _fill(cmb[..., :3], cmb[..., 3], 8)
        if c.shape[0] != H: c = _rs(c, H, Image.BILINEAR)
        if os.environ.get('BAR_NODENOISE') != '1': c = np.maximum(denoise(c, a, nrm), 0)
        img = (tm.tonemap(c) * 255 + 0.5).astype(np.uint8)
        im = Image.fromarray(img)
        if size and size != H: im = im.resize((size, size), Image.LANCZOS)
        f = os.path.join(outdir, '%s.jpg' % atlas)
        im.save(f, quality=quality, subsampling=0)
        print('POST %s  fill %.2f  mean %.1f  %d KB' % (f, (alb[..., 3] > 0).mean(), img.mean(), os.path.getsize(f) // 1024), flush=True)

# ------------------------------------------------------------------ the bake's version stamp
def stamp():
    """writes scene.json's "v": a short hash of bar.glb + every tex/*.jpg. The page appends it to those URLs (?v=...),
    so a browser can never pair one bake's model with another bake's textures out of its cache. Run after post / export."""
    import hashlib, glob, json
    f = os.path.join(SITE, 'scene.json')
    if not os.path.exists(f): return None
    h = hashlib.sha1()
    for p in [os.path.join(SITE, 'bar.glb')] + sorted(glob.glob(os.path.join(SITE, 'tex', '*.jpg'))):
        if os.path.exists(p): h.update(os.path.basename(p).encode()); h.update(open(p, 'rb').read())
    meta = json.load(open(f)); meta['v'] = h.hexdigest()[:10]
    json.dump(meta, open(f, 'w'), indent=1)
    print('STAMP', meta['v'], flush=True)
    return meta['v']

# ------------------------------------------------------------------ export
def export_glb(path, only=None):
    """strips to geometry + uv_atlas, one material per atlas (named like the atlas), writes a plain GLB"""
    simple = {}; tris = 0; names = {}
    for o in list(sc.objects):
        a = o.get('atlas') if o.type == 'MESH' else None
        if not a or a == '_blockout' or (only and a not in only):
            bpy.data.objects.remove(o, do_unlink=True); continue
        me = o.data
        for l in [l for l in me.uv_layers if l.name != 'uv_atlas']: me.uv_layers.remove(l)
        if a not in simple: simple[a] = bpy.data.materials.new(a)
        me.materials.clear(); me.materials.append(simple[a])
        for at in [at for at in me.attributes if at.name in ('td', 'part')]: me.attributes.remove(at)
        me.calc_loop_triangles(); tris += len(me.loop_triangles); names[o.name] = a
        o.select_set(True)
    kw = dict(filepath=path, export_format='GLB', export_apply=True, export_yup=True, use_selection=True,
              export_normals=False, export_materials='EXPORT', export_cameras=False, export_lights=False, export_animations=False)
    props_ = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props_})
    print('GLB %s  %d KB  %d tris  %d meshes' % (path, os.path.getsize(path) // 1024, tris, len(names)), flush=True)
    return names

def scene_meta(names):
    """the contract the web page reads (three.js coordinates: x, y up, z toward the viewer)"""
    t = layout.three
    L = list(layout.LIGHTS) + EXTRA_LIGHTS
    return dict(
        atlases=sorted(set(names.values())),
        meshes=names,                                   # mesh/node name -> atlas (= material name; texture tex/<atlas>.jpg)
        stops={k: dict(p=t(p), t=t(tg), fov=fov) for k, (p, tg, fov) in layout.STOPS.items()},
        glows=[dict(name=n, p=t(loc), color=[round(c, 3) for c in col], when=n[0]) for (n, kind, loc, e, col, ex) in L if kind == 'POINT'],
        window=dict(x=layout.WINDOW['x'], y0=layout.WINDOW['z0'], y1=layout.WINDOW['z1'], z0=-layout.WINDOW['y0'], z1=-layout.WINDOW['y1']),
        cats={k: dict(p=t(p), rot=r) for k, (p, r) in layout.CAT_SPOTS.items()},
        eye=t(layout.EYE),
        points={k: t(v) for k, v in layout.POINTS.items()},
    )
