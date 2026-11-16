#!/usr/bin/env python3
"""Headless screenshot of a static page folder with WebGL (software GL).
Usage: python3 shot.py <site_dir> <out.png> [--wait MS] [--js "code run before the shot"] [--size 1280x720] [--hash name]
       --js may be given several times; each runs then waits --wait ms; a shot is saved per step as out-1.png, out-2.png ...
Prints console errors / page errors / failed requests, and the measured FPS over 2s.
"""
import os, sys, argparse, threading, http.server, socketserver, functools, time
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser()
ap.add_argument('site'); ap.add_argument('out')
ap.add_argument('--wait', type=int, default=4000)
ap.add_argument('--js', action='append', default=[])
ap.add_argument('--size', default='1280x720')
ap.add_argument('--hash', default='')
a = ap.parse_args()
w, h = map(int, a.size.split('x'))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *x): pass
Handler = functools.partial(Q, directory=a.site)
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get('CHROME', '/usr/bin/google-chrome'), headless=True, args=[
        '--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist', '--enable-webgl', '--autoplay-policy=no-user-gesture-required'])
    pg = b.new_page(viewport={'width': w, 'height': h})
    pg.on('console', lambda m: print('[console.%s] %s' % (m.type, m.text)) if m.type in ('error', 'warning') else None)
    pg.on('pageerror', lambda e: print('[pageerror]', e))
    pg.on('requestfailed', lambda r: print('[requestfailed]', r.url))
    pg.on('response', lambda r: print('[http %d] %s' % (r.status, r.url)) if r.status >= 400 else None)
    url = 'http://127.0.0.1:%d/index.html' % port + (('#' + a.hash) if a.hash else '')
    pg.goto(url, wait_until='load')
    pg.wait_for_timeout(a.wait)
    if not a.js:
        pg.screenshot(path=a.out)
    else:
        base = a.out[:-4]
        pg.screenshot(path=base + '-0.png')
        for i, code in enumerate(a.js, 1):
            pg.evaluate(code)
            pg.wait_for_timeout(a.wait)
            pg.screenshot(path='%s-%d.png' % (base, i))
    fps = pg.evaluate("""() => new Promise(r => { let n = 0; const t0 = performance.now();
        const f = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2); };
        requestAnimationFrame(f); })""")
    print('fps (software GL, only a rough relative signal):', fps)
    b.close()
srv.shutdown()
