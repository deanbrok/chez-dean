#!/usr/bin/env python3
"""Bundle a PoC site folder into ONE self-contained html file (JS bundled with esbuild, CSS inlined).
Usage: bundle.py <site_dir> <out_dir> <out_name.html>   (assets fetched by relative path are NOT handled here)"""
import sys, re, subprocess, pathlib
site, out, name = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), sys.argv[3]
out.mkdir(parents=True, exist_ok=True)
html = (site / 'index.html').read_text()
# stylesheets
def css(m):
    href = m.group(1)
    if href.startswith('http'): return m.group(0)
    return '<style>\n' + (site / href).read_text() + '\n</style>'
html = re.sub(r'<link[^>]+rel="stylesheet"[^>]+href="([^"]+)"[^>]*>', css, html)
html = re.sub(r'<link[^>]+href="([^"]+)"[^>]+rel="stylesheet"[^>]*>', css, html)
# local url(...) references in inlined CSS and <link rel="icon"> -> data URIs
import base64 as _b64, mimetypes as _mt
def _data(rel):
    f = site / rel.lstrip('./')
    if not f.is_file(): return None
    return 'data:%s;base64,%s' % (_mt.guess_type(f.name)[0] or 'application/octet-stream', _b64.b64encode(f.read_bytes()).decode())
def _cssurl(m):
    d = _data(m.group(1)); return 'url(%s)' % d if d else m.group(0)
html = re.sub(r'url\(["\']?(\.?/?[\w./-]+\.(?:png|jpg|jpeg|svg|webp))["\']?\)', _cssurl, html)
def _icon(m):
    d = _data(m.group(1)); return m.group(0).replace(m.group(1), d) if d else m.group(0)
html = re.sub(r'<link rel="icon" href="([^"]+)">', _icon, html)
# module entry
m = re.search(r'<script type="module" src="([^"]+)"></script>', html)
assert m, 'no external module entry found'
entry = site / m.group(1)
js = subprocess.run(['npx', '--yes', 'esbuild', str(entry), '--bundle', '--format=esm', '--minify',
    '--alias:three=' + str(site / 'vendor/three/build/three.module.js'),
    '--alias:three/addons=' + str(site / 'vendor/three/addons'), '--log-level=warning'],
    capture_output=True, text=True, check=True).stdout
js = js.replace('</script', '<\\/script')
html = html.replace(m.group(0), '<script type="module">\n' + js + '\n</script>')
html = re.sub(r'<script type="importmap">.*?</script>', '', html, flags=re.S)
# inline every non-code asset as base64 and serve it to fetch / <img> / XHR via blob URLs
import base64, json, mimetypes
assets = {}
for f in sorted(site.rglob('*')):
    rel = f.relative_to(site).as_posix()
    if not f.is_file() or rel.startswith('vendor/') or f.suffix in ('.html', '.js', '.css', '.map'): continue
    mime = {'.glb': 'model/gltf-binary', '.json': 'application/json'}.get(f.suffix) or mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
    assets[rel] = [mime, base64.b64encode(f.read_bytes()).decode()]
if assets:
    prelude = '''<script>
(() => {
  const A = ''' + json.dumps(assets) + ''';
  const base = new URL('.', location.href).href, urls = {};
  for (const k in A) { const b = atob(A[k][1]), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
    urls[k] = URL.createObjectURL(new Blob([u], { type: A[k][0] })); A[k] = null; }
  const map = u => { try { const abs = new URL(u, location.href).href.split(/[?#]/)[0];
    if (abs.startsWith(base)) { const k = decodeURIComponent(abs.slice(base.length)); if (urls[k]) return urls[k]; } } catch (e) {} return u; };
  const f = window.fetch.bind(window);
  window.fetch = (r, o) => typeof r === 'string' || r instanceof URL ? f(map(String(r)), o) : (map(r.url) !== r.url ? f(map(r.url), o) : f(r, o));
  const d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
  Object.defineProperty(HTMLImageElement.prototype, 'src', { get() { return d.get.call(this); }, set(v) { d.set.call(this, map(v)); }, configurable: true });
  const xo = XMLHttpRequest.prototype.open; XMLHttpRequest.prototype.open = function (m, u, ...a) { return xo.call(this, m, map(u), ...a); };
})();
</script>'''
    html = html.replace('<script type="module">', prelude + '\n<script type="module">', 1)
    print('inlined', len(assets), 'assets')
(out / 'index.html').write_text(html)
(out / name).write_text(html)
print('wrote', out / name, round(len(html) / 1e6, 2), 'MB')
