#!/usr/bin/env python3
"""Command line for the bar pipeline.  Always run as:  python3 blender/barkit/run.py <command> ...

  preview <part> [--cam bar|records|hifi|table|window|stairs] [--res 640x360] [--spp 16]
                 [--at x,y,z --look x,y,z [--fov 40]]      custom close-up camera instead of --cam
                 [--with part,part]                        also build these other parts for real (if their build.py exists)
                 [--solo]                                  no blockout of the rest of the room
                 [--out name]                              file name suffix
      Builds grey blockout of the other zones + your part + the room lights, renders to parts/<part>/shots/.

  baketest <part>
      Builds your part (+ blockout), unwraps + packs its atlas(es), runs a LOW-RES test bake,
      writes parts/<part>/shots/<atlas>_<mode>.jpg and parts/<part>/shots/<part>.glb. Proves the part survives
      the real pipeline; look at the atlas images: nothing black / pink / missing, important things get enough texels.

  assemble                  (assembler only) all parts for real -> out/bar.blend
  bake <atlas> [--test]     (assembler only)
  post [atlas]              (assembler only)
  export                    (assembler only) -> site/bar.glb + site/scene.json
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
from barkit import kit, mats, layout, pipeline as P

def opt(name, default=None):
    a = sys.argv
    return a[a.index(name) + 1] if name in a else default

def vec(s): return tuple(float(v) for v in s.split(','))

def build(real, block):
    P.new_scene()
    P.blockout(block)
    for n in real: P.load_part(n)
    P.add_lights(); P.cameras()

def have(n): return os.path.exists(os.path.join(P.ROOT, 'parts', n, 'build.py'))

cmd = sys.argv[1] if len(sys.argv) > 1 else ''
if cmd == 'preview':
    part = sys.argv[2]
    real = [part] + [n for n in (opt('--with') or '').split(',') if n and n != part and have(n)]
    block = [] if '--solo' in sys.argv else [n for n in layout.PARTS if n not in real]
    build(real, block)
    cam = 'cam_' + (opt('--cam') or 'bar')
    if opt('--at'):
        P.camera('cam_custom', vec(opt('--at')), vec(opt('--look')), float(opt('--fov', '40'))); cam = 'cam_custom'
    w, h = (int(v) for v in (opt('--res') or '640x360').split('x'))
    mode = 'night'
    d = os.path.join(P.ROOT, 'parts', part, 'shots'); os.makedirs(d, exist_ok=True)
    out = os.path.join(d, 'preview_%s_%s%s.png' % (cam[4:], mode, ('_' + opt('--out')) if opt('--out') else ''))
    P.render(out, cam, mode, w, h, int(opt('--spp') or 16))
    print('WROTE', out)
elif cmd == 'baketest':
    part = sys.argv[2]
    build([part], [n for n in layout.PARTS if n != part])
    d = os.path.join(P.ROOT, 'parts', part, 'shots'); os.makedirs(d, exist_ok=True)
    ats = P.unwrap_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(d, '_baketest.blend'))
    for a in ats:
        bpy.ops.wm.open_mainfile(filepath=os.path.join(d, '_baketest.blend')); P.sc = bpy.context.scene
        P.bake(a, test=True, outdir=os.path.join(d, '_bake'))
        P.post(a, bakedir=os.path.join(d, '_bake'), outdir=d, quality=85)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(d, '_baketest.blend')); P.sc = bpy.context.scene
    P.export_glb(os.path.join(d, part + '.glb'), only=ats)
    os.remove(os.path.join(d, '_baketest.blend'))
    print('BAKETEST OK', ats)
elif cmd == 'standin':
    # contract-true stand-in assets for the web agent: blockout as real atlases + a box for every interactive name
    P.new_scene()
    cols = dict(shell=(0.25, 0.2, 0.16), counter=(0.3, 0.14, 0.08), shelves=(0.28, 0.2, 0.1), hifi=(0.12, 0.12, 0.13), nook=(0.3, 0.28, 0.2), lounge=(0.2, 0.12, 0.1), cat=(0.05, 0.05, 0.05))
    for n in layout.PARTS:
        g = mats.plain('standin_' + n, cols[n], rough=0.7); h = mats.plain('standin_hot_' + n, (0.75, 0.45, 0.12), rough=0.5)
        with kit.props(atlas=n):
            for i, (x0, x1, y0, y1, z0, z1) in enumerate(layout.BLOCKS[n]): kit.box('blk_%s_%d' % (n, i), x0, x1, y0, y1, z0, z1, g)
            for name, (part, o, (sx, sy, sz)) in layout.INTERACTIVE.items():
                if part != n: continue
                with kit.interactive(name, origin=o, td=2.0):
                    kit.box(name, o[0] - sx / 2, o[0] + sx / 2, o[1] - sy / 2, o[1] + sy / 2, o[2], o[2] + sz, h)
    P.add_lights(); P.cameras()
    P.unwrap_all()
    os.makedirs(P.OUT, exist_ok=True); f = os.path.join(P.OUT, '_standin.blend'); bpy.ops.wm.save_as_mainfile(filepath=f)
    for a in layout.PARTS:
        bpy.ops.wm.open_mainfile(filepath=f); P.sc = bpy.context.scene
        P.bake(a, test=True, outdir=os.path.join(P.OUT, '_standin_bake')); P.post(a, bakedir=os.path.join(P.OUT, '_standin_bake'))
    bpy.ops.wm.open_mainfile(filepath=f); P.sc = bpy.context.scene
    names = P.export_glb(os.path.join(P.SITE, 'bar.glb'))
    json.dump(P.scene_meta(names), open(os.path.join(P.SITE, 'scene.json'), 'w'), indent=1)
    P.stamp()
    print('STANDIN OK')
elif cmd == 'assemble':
    skip = (opt('--skip') or '').split(',')
    real = [n for n in layout.PARTS if have(n) and n not in skip]
    build(real, [n for n in layout.PARTS if n not in real])
    ats = P.unwrap_all()
    os.makedirs(P.OUT, exist_ok=True)
    json.dump(dict(atlases=ats, extra_lights=[[*l[:5], {k: (list(v) if isinstance(v, tuple) else v) for k, v in l[5].items()}] for l in P.EXTRA_LIGHTS]),
              open(os.path.join(P.OUT, 'assemble.json'), 'w'))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(P.OUT, 'bar.blend'))
    print('ASSEMBLED', real, 'atlases', ats)
elif cmd in ('bake', 'render'):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(P.OUT, 'bar.blend')); P.sc = bpy.context.scene
    if cmd == 'bake':
        P.bake(sys.argv[2], test='--test' in sys.argv, albedo='--noalbedo' not in sys.argv)
    else:
        cam = 'cam_' + (opt('--cam') or 'bar')
        if opt('--at'):
            P.camera('cam_custom', vec(opt('--at')), vec(opt('--look')), float(opt('--fov', '40'))); cam = 'cam_custom'
        w, h = (int(v) for v in (opt('--res') or '960x540').split('x'))
        mode = 'night'
        P.render(os.path.join(P.OUT, 'render_%s_%s.png' % (cam[4:], mode)), cam, mode, w, h, int(opt('--spp') or 24))
elif cmd == 'post':
    meta = json.load(open(os.path.join(P.OUT, 'assemble.json')))
    for a in ([sys.argv[2]] if len(sys.argv) > 2 else meta['atlases']): P.post(a)
    P.stamp()
elif cmd == 'export':
    bpy.ops.wm.open_mainfile(filepath=os.path.join(P.OUT, 'bar.blend')); P.sc = bpy.context.scene
    meta = json.load(open(os.path.join(P.OUT, 'assemble.json')))
    P.EXTRA_LIGHTS.extend([tuple(l) for l in meta['extra_lights']])
    names = P.export_glb(os.path.join(P.SITE, 'bar.glb'))
    json.dump(P.scene_meta(names), open(os.path.join(P.SITE, 'scene.json'), 'w'), indent=1)
    P.stamp()
    print('EXPORTED')
else:
    print(__doc__)
