// DEAN'S: a basement jazz bar, a few minutes after closing.
// The room arrives as a baked GLB (bar.glb) + one baked texture per atlas (tex/<atlas>.jpg) + scene.json.
// This file only displays the bake (unlit), runs it through a lens (post.js), moves a camera between fixed stops,
// animates a handful of named meshes and opens DOM panels. Nothing about the room's geometry is hard-coded here:
// positions, stops, lamps, the window and the animation pivots are read from the assets at run time.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as C from './content.js';
import { panelFor, SLUGS, slugFor, COUNTS, esc } from './panels.js';
import * as FX from './fx.js';
import * as AU from './audio.js';
import { buildGrid } from './occlude.js';
import { Lens } from './post.js';

const $ = (s) => document.querySelector(s);
const canvas = $('#gl'), tip = $('#tip'), panel = $('#panel'), panelBody = $('#panel-body'), sheet = $('#panel .sheet');
const TOUCH = matchMedia('(hover: none), (pointer: coarse)').matches;
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
const SS = (() => { try { sessionStorage.setItem('_t', '1'); return sessionStorage; } catch { return null; } })();
const UP = new THREE.Vector3(0, 1, 0);
const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);
const clamp = THREE.MathUtils.clamp, lerp = THREE.MathUtils.lerp;
const smooth = (x) => { x = clamp(x, 0, 1); return x * x * x * (x * (x * 6 - 15) + 10); };     // smootherstep: unhurried at both ends
const sstep = (a, b, x) => smooth((x - a) / (b - a));

// ---------------------------------------------------------------- the URL hash: deep links + test switches
// tokens separated by & , ; : "cat=sit", "post-first-pressing", "records", "fixedres", "nolens"
function parseHash(h) {
  const out = { flags: new Set(), kv: {}, slug: null, stop: null };
  for (const tok of decodeURIComponent((h || '').replace(/^#/, '')).split(/[&,;]/)) {
    if (!tok) continue;
    const [k, v] = tok.split('=');
    if (v !== undefined) out.kv[k] = v;
    else if (SLUGS[k]) out.slug = k;
    else out.flags.add(k);
  }
  return out;
}
const HASH = parseHash(location.hash);

// ---------------------------------------------------------------- the interactive names (the contract with the modellers)
const NAMES = ['door', 'note', 'cigarbox', 'matchbook', 'paperback', 'cigar', 'platter_record', 'tonearm', 'reel_l', 'reel_r', 'nowplaying',
  'manuscript', 'radio', 'phone', 'piano_keys', 'clock_hour', 'clock_min', 'clock_sec', 'mapframe',
  'rec_0', 'rec_1', 'rec_2', 'rec_3', 'rec_4', 'rec_5', 'book_0', 'book_1', 'book_2', 'book_3',
  'bottle_0', 'bottle_1', 'bottle_2', 'bottle_3', 'cat_sleep', 'cat_sit', 'cat_watch'];
// what each one does. pref = the stop it is meant to be opened from (verified against the real views at run time)
function specFor(name) {
  let m;
  if ((m = /^rec_(\d+)$/.exec(name))) return { group: 'rec', index: +m[1], pref: 'records', act: 'panel', motion: 'sleeve' };
  if ((m = /^book_(\d+)$/.exec(name))) return { group: 'book', index: +m[1], pref: 'records', act: 'panel', motion: 'tilt' };
  if ((m = /^bottle_(\d+)$/.exec(name))) return { group: 'bottle', index: +m[1], pref: 'records', act: 'panel', motion: 'lift' };
  if ((m = /^cat_(\w+)$/.exec(name))) return { group: 'cat', pose: m[1], pref: null, act: 'cat', motion: m[1] === 'sleep' ? 'breathe' : null };
  return ({
    nowplaying: { pref: 'records', act: 'panel', motion: 'lean' },
    manuscript: { pref: 'table', act: 'panel', motion: 'nudge' },
    radio: { pref: 'table', act: 'radio', motion: 'nudge' },
    note: { pref: 'bar', act: 'panel', motion: 'nudge' },
    matchbook: { pref: 'bar', act: 'panel', motion: 'slide' },
    cigarbox: { pref: 'bar', act: 'panel', motion: 'lid' },
    paperback: { pref: 'bar', act: 'panel', motion: 'lift' },
    cigar: { pref: 'bar', act: 'smoke', motion: 'cigar' },
    phone: { pref: 'window', act: 'panel', motion: null },
    mapframe: { pref: 'window', act: 'panel', motion: null },
    piano_keys: { pref: 'window', act: 'chord', motion: 'dip' },
    door: { pref: 'stairs', act: 'panel', motion: 'door' },
    platter_record: { pref: 'hifi', act: 'music', motion: 'spin' },
    tonearm: { pref: 'hifi', act: 'music', motion: 'bob' },
    reel_l: { pref: 'records', act: 'say', motion: null },
    reel_r: { pref: 'records', act: 'say', motion: null },
    clock_hour: { pref: null, act: null, motion: null },
    clock_min: { pref: null, act: null, motion: null },
    clock_sec: { pref: null, act: null, motion: 'twitch' },
  })[name] || { pref: null, act: null, motion: null };
}
function labelFor(it) {
  const g = it.group || it.name;
  switch (g) {
    case 'rec': return ['Liner notes · ' + C.POSTS[it.index % C.POSTS.length].cat, C.POSTS[it.index % C.POSTS.length].title];
    case 'book': return ['Reading list', C.SHELVES[it.index % C.SHELVES.length].title];
    case 'bottle': return ['Bottle keep', C.BOTTLES[it.index % C.BOTTLES.length].name];
    case 'cat': return ['', 'The cat'];
    case 'nowplaying': return ['Now playing', C.NOW.album + ' — this month'];
    case 'manuscript': return ['On the kitchen table', 'Writing'];
    case 'radio': return ['The radio', AU.state().radio ? 'Turn it off' : 'Rain, and a train somewhere'];
    case 'note': return ['A note on the counter', 'About'];
    case 'matchbook': return ['A matchbook', 'How this place was made'];
    case 'cigarbox': return ['The cigar box', 'Odds & ends'];
    case 'paperback': return ['Face down, left open', 'Currently reading'];
    case 'cigar': return ['In the ashtray, still lit', 'Take a puff'];
    case 'phone': return ['The telephone', 'Contact'];
    case 'mapframe': return ['An old map', 'Places'];
    case 'piano_keys': return ['The piano', AU.soundOn() ? 'One chord' : 'One chord (sound is off)'];
    case 'door': return ['The door is open', 'Downstairs'];
    case 'platter_record': case 'tonearm': return ['The turntable', AU.state().music ? 'Lift the needle' : 'Drop the needle (sound on)'];
    case 'reel_l': case 'reel_r': return ['The tape deck', C.REEL_LINE];
  }
  return null;
}

// ---------------------------------------------------------------- renderer
let renderer;
try {
  // with the lens on, the room is multisampled off-screen, so the canvas itself needs no antialiasing
  const lensLikely = !HASH.flags.has('nolens') && (() => { try { const g = document.createElement('canvas').getContext('webgl2');
    const ok = !!g && !!(g.getExtension('EXT_color_buffer_float') || g.getExtension('EXT_color_buffer_half_float'));
    g && g.getExtension('WEBGL_lose_context')?.loseContext(); return ok; } catch { return false; } })();
  renderer = new THREE.WebGLRenderer({ canvas, antialias: !lensLikely, powerPreference: 'high-performance' });
} catch (e) {
  $('#err').textContent = 'This room needs WebGL, and your browser would rather not. The door stays locked, for now.';
  throw e;
}
const MAXR = Math.min(devicePixelRatio || 1, 2);
const perf = { ratio: MAXR, acc: 0, n: 0, locked: HASH.flags.has('fixedres'), lowFrames: 0 };
renderer.setPixelRatio(perf.ratio);
renderer.setClearColor(0x050302, 1);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, innerWidth / innerHeight, 0.03, 40);

// ---------------------------------------------------------------- the lens (post.js): focus, bloom, grain. #nolens to see the bare bake
const SMALL_SCREEN = TOUCH && Math.min(screen.width, screen.height) < 820;
let lens = null;
if (!HASH.flags.has('nolens')) {
  try { lens = new Lens(renderer, { small: SMALL_SCREEN }); if (!lens.ok) lens = null; } catch (e) { console.warn('lens off:', e); lens = null; }
}
document.body.classList.toggle('lens', !!lens);
const GLOW_K = lens ? 0.5 : 1;          // the lens blooms the lamps itself, so the painted-on glows can be quieter

// ---------------------------------------------------------------- loading
const progress = { glb: 0, tex: 0, ntex: 1 };
function showProgress() { $('#bar').style.width = Math.round((progress.glb * 0.4 + (progress.tex / progress.ntex) * 0.6) * 100) + '%'; }
const aniso = Math.min(8, renderer.capabilities.getMaxAnisotropy());
const SMALL = SMALL_SCREEN;
const texLoader = new THREE.TextureLoader();
function prep(t) { t.flipY = false; t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = aniso; t.needsUpdate = true; return t; }
function loadTex(url) {
  return new Promise((resolve) => {
    const plain = () => texLoader.load(url, (t) => resolve(prep(t)), undefined, () => resolve(null));
    if (SMALL && 'createImageBitmap' in window) {         // phones: decode straight to 1024 px, a quarter of the memory
      fetch(url).then((r) => { if (!r.ok) throw new Error(r.status); return r.blob(); })
        .then((b) => createImageBitmap(b, { resizeWidth: 1024, resizeHeight: 1024, resizeQuality: 'high' }))
        .then((bm) => resolve(prep(new THREE.Texture(bm)))).catch(plain);
    } else plain();
  });
}
const grey = new THREE.DataTexture(new Uint8Array([90, 80, 70, 255]), 1, 1); grey.needsUpdate = true;

const META = await fetch('./scene.json').then((r) => r.json()).catch(() => null);
if (!META) { $('#err').textContent = 'The room could not be found (scene.json).'; throw new Error('scene.json'); }
const ATLASES = META.atlases || [...new Set(Object.values(META.meshes || {}))];
progress.ntex = ATLASES.length;

// ---------------------------------------------------------------- materials: one baked atlas each, unlit
const ATL = {};
for (const a of ATLASES) ATL[a] = { map: { value: grey } };
const VERT = /* glsl */`varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;
const FRAG = /* glsl */`
  uniform sampler2D map; uniform float uHover, uGlow; varying vec2 vUv;
  void main(){
    vec3 c = texture2D(map, vUv).rgb;
    c = c * (1.0 + 0.30 * uHover) + vec3(0.030, 0.022, 0.012) * uHover + vec3(0.30, 0.17, 0.06) * uGlow;
    gl_FragColor = vec4(c, 1.0);
    #include <colorspace_fragment>
  }`;
function roomMat(atlas) {
  const a = ATL[atlas];
  if (!a) return new THREE.MeshBasicMaterial({ color: 0x5a5046 });
  return new THREE.ShaderMaterial({ name: atlas, uniforms: { map: a.map, uHover: { value: 0 }, uGlow: { value: 0 } },
    vertexShader: VERT, fragmentShader: FRAG });
}
const sharedMats = {};

const firstTex = Promise.all(ATLASES.map((a) => loadTex(`./tex/${a}.jpg`).then((t) => {
  progress.tex++; showProgress();
  if (t) ATL[a].map.value = t;
})));
let gltf;
try {
  [gltf] = await Promise.all([
    new GLTFLoader().loadAsync('./bar.glb', (e) => { if (e.total) { progress.glb = e.loaded / e.total; showProgress(); } }),
    firstTex,
  ]);
} catch (e) {
  $('#err').textContent = 'The room could not be loaded. Try again in a moment.'; throw e;
}
progress.glb = 1; showProgress();

// ---------------------------------------------------------------- the room
const root = gltf.scene; scene.add(root);
root.updateMatrixWorld(true);
const atlasOf = (o) => {
  const m = ((o.material && o.material.name) || '').replace(/\.\d+$/, '');
  if (ATL[m]) return m;
  const n = (META.meshes || {})[o.name] || (META.meshes || {})[o.parent && o.parent.name];
  return ATL[n] ? n : null;
};
const staticMeshes = [];
const nameSet = new Set(NAMES);
{ // the cigar's ash is its own mesh (it grows, and gets knocked off) but it goes wherever the cigar goes
  const cg = root.getObjectByName('cigar'), ash = root.getObjectByName('cigar_ash');
  if (cg && ash) cg.attach(ash);
}
const isInteractive = (o) => { for (let p = o; p && p !== root; p = p.parent) if (nameSet.has(p.name)) return p.name; return null; };
root.traverse((o) => {
  if (!o.isMesh) return;
  const a = atlasOf(o);
  if (isInteractive(o)) { o.material = roomMat(a); }
  else { o.material = sharedMats[a] || (sharedMats[a] = roomMat(a)); o.matrixAutoUpdate = false; staticMeshes.push(o); }
});

// ---------------------------------------------------------------- camera stops
const ORDER = ['bar', 'records', 'hifi', 'table', 'window', 'stairs'].filter((k) => META.stops && META.stops[k]);
for (const k of Object.keys(META.stops || {})) if (!ORDER.includes(k)) ORDER.push(k);
const m4 = new THREE.Matrix4();
const lookQ = (p, t) => new THREE.Quaternion().setFromRotationMatrix(m4.lookAt(p, t, UP));
const STOPS = {};
for (const k of ORDER) {
  const s = META.stops[k], p = V(s.p), t = V(s.t);
  STOPS[k] = { p, t, fov: s.fov || 45, q: lookQ(p, t), d: p.distanceTo(t) };
}
const EYE = META.eye ? V(META.eye) : STOPS.bar.p.clone();

// visibility of a box from a stop, with a reference 16:9 frame: 0 if its centre is out of frame, else its size on screen
const refCam = new THREE.PerspectiveCamera(45, 16 / 9, 0.03, 40);
function seenFrom(box, k) {
  const s = STOPS[k]; if (!s) return 0;
  refCam.fov = s.fov; refCam.position.copy(s.p); refCam.quaternion.copy(s.q); refCam.updateProjectionMatrix(); refCam.updateMatrixWorld();
  const c = box.getCenter(new THREE.Vector3()).project(refCam);
  if (c.z > 1 || c.z < -1 || Math.abs(c.x) > 0.9 || Math.abs(c.y) > 0.88) return 0;
  const lo = new THREE.Vector2(9, 9), hi = new THREE.Vector2(-9, -9), v = new THREE.Vector3();
  for (let i = 0; i < 8; i++) {
    v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z).project(refCam);
    lo.min(v); hi.max(v);
  }
  return Math.max(hi.x - lo.x, hi.y - lo.y);
}

// ---------------------------------------------------------------- interactive items
const ITEMS = [], BY = {}, MISSING = [];
const tmpV = new THREE.Vector3(), tmpV2 = new THREE.Vector3(), tmpQ = new THREE.Quaternion(), tmpQ2 = new THREE.Quaternion();
const localAxes = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]].map(V);
for (const name of NAMES) {
  const obj = root.getObjectByName(name);
  if (!obj) { MISSING.push(name); continue; }
  scene.attach(obj);                       // world transform == local transform from now on
  obj.matrixAutoUpdate = true;
  const mats = []; obj.traverse((o) => { if (o.isMesh) mats.push(o.material); });
  const box = new THREE.Box3().setFromObject(obj);
  if (box.isEmpty()) box.setFromCenterAndSize(obj.position, new THREE.Vector3(0.05, 0.05, 0.05));
  // the object's own bounding box in local space (for presenting it to the camera)
  const lbox = new THREE.Box3(); obj.traverse((o) => { if (o.isMesh) { o.geometry.computeBoundingBox(); const b = o.geometry.boundingBox.clone(); if (o !== obj) b.applyMatrix4(o.matrix); lbox.union(b); } });
  const it = { name, obj, mats, box, lbox, ...specFor(name), home: { p: obj.position.clone(), q: obj.quaternion.clone(), s: obj.scale.clone() },
    t: 0, target: 0, h: 0, hover: 0, pulse: 0, center: box.getCenter(new THREE.Vector3()), size: box.getSize(new THREE.Vector3()) };
  // where it is opened from: its preferred stop if it is really in frame there, otherwise the stop that sees it best
  let best = null, bs = 0;
  for (const k of ORDER) { const s = seenFrom(box, k); if (s > bs) { bs = s; best = k; } }
  it.stop = it.pref && seenFrom(box, it.pref) > 0 ? it.pref : best || it.pref || 'bar';
  // "out": the object's local horizontal axis that points most toward the camera of its stop (= away from the wall/shelf)
  const viewer = STOPS[it.stop] ? STOPS[it.stop].p : EYE;
  const toView = viewer.clone().sub(it.center); toView.y = 0; toView.normalize();
  let bestAx = null, bd = -2;
  for (const a of localAxes) {
    const w = a.clone().applyQuaternion(obj.quaternion); if (Math.abs(w.y) > 0.7) continue;
    w.y = 0; w.normalize(); const d = w.dot(toView); if (d > bd) { bd = d; bestAx = w; }
  }
  it.out = bestAx || toView;
  it.side = new THREE.Vector3().crossVectors(UP, it.out).normalize();       // rotating +angle about this tips the top toward "out"
  const half = (v) => (Math.abs(it.size.x * v.x) + Math.abs(it.size.z * v.z)) / 2;
  it.front = it.center.clone().addScaledVector(it.out, half(it.out)); it.front.y = box.min.y;
  it.back = it.center.clone().addScaledVector(it.out, -half(it.out)); it.back.y = box.min.y;
  // the axis pointing out of the wall toward the viewer, in the object's own frame (for the clock hand)
  const dirView = viewer.clone().sub(obj.position).normalize(); let wa = null, wd = -2;
  for (const a of localAxes) { const w = a.clone().applyQuaternion(obj.quaternion); const d = w.dot(dirView); if (d > wd) { wd = d; wa = w; } }
  it.wallAxis = wa;
  // hit box: at least 5 cm in every direction, a little padding
  const hb = box.clone().expandByScalar(0.008), hs = hb.getSize(new THREE.Vector3()), hc = hb.getCenter(new THREE.Vector3());
  it.hit = new THREE.Box3().setFromCenterAndSize(hc, hs.max(new THREE.Vector3(0.05, 0.05, 0.05)));
  it.label = labelFor(it);
  it.clickable = !!it.act && it.act !== 'say';
  ITEMS.push(it); BY[name] = it;
}
const itemFor = (group, i) => ITEMS.find((x) => (x.group === group && x.index === i) || (x.name === group && i === undefined));

// door: which way is "further open"? toward the stairwell (the stairs glow lies down there)
if (BY.door) {
  const it = BY.door, c = it.center.clone().sub(it.home.p); c.y = 0;
  const down = META.points && META.points.stairs_glow ? V(META.points.stairs_glow).sub(it.home.p) : it.out.clone().negate();
  down.y = 0;
  it.swing = Math.sign(new THREE.Vector3().crossVectors(c, down).y) || 1;
}
// with Downstairs open, look past the door, down the stairs
if (BY.door && META.points && META.points.stairs_glow) { const g = V(META.points.stairs_glow); BY.door.lookAt = new THREE.Vector3(g.x, BY.door.center.y, g.z).lerp(BY.door.center, 0.35); }
// tonearm: tilt axis perpendicular to the arm
if (BY.tonearm) {
  const it = BY.tonearm, arm = it.center.clone().sub(it.home.p); arm.y = 0;
  it.bobAxis = arm.lengthSq() > 1e-6 ? new THREE.Vector3().crossVectors(UP, arm.normalize()) : new THREE.Vector3(1, 0, 0);
}

// regions: clicking near a stop's things takes you there
const REGIONS = [];
for (const k of ORDER) {
  const members = ITEMS.filter((x) => x.stop === k && x.clickable && x.group !== 'cat');
  const b = new THREE.Box3(); for (const m of members) b.union(m.box);
  if (k === 'window' && META.window) {
    const w = META.window; b.union(new THREE.Box3(new THREE.Vector3(w.x - 0.05, Math.min(w.y0, w.y1), Math.min(w.z0, w.z1)), new THREE.Vector3(w.x + 0.05, Math.max(w.y0, w.y1), Math.max(w.z0, w.z1))));
  }
  if (b.isEmpty()) continue;
  REGIONS.push({ stop: k, box: b.expandByScalar(k === 'table' ? 0.25 : 0.12) });
}

// ---------------------------------------------------------------- the cat of the day
const CAT_POSES = ITEMS.filter((x) => x.group === 'cat');
function catOfDay(d = new Date()) {
  const day = Math.floor((Date.UTC(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
  let h = (day * 2654435761) >>> 0; h ^= h >>> 15; h = Math.imul(h, 2246822519) >>> 0; h ^= h >>> 13;
  const names = CAT_POSES.map((x) => x.pose);
  if (names.includes('watch') && h % 5 === 0) return 'watch';
  const rest = names.filter((n) => n !== 'watch');
  return rest.length ? rest[(h >>> 3) % rest.length] : names[0];
}
let catPose = null; const catBlob = { mesh: null };
function setCat(pose) {
  if (!CAT_POSES.length) return;
  if (!CAT_POSES.some((x) => x.pose === pose)) pose = CAT_POSES[0].pose;
  catPose = pose;
  for (const c of CAT_POSES) { c.obj.visible = c.pose === pose; c.hidden = c.pose !== pose; }
  if (catBlob.mesh) { scene.remove(catBlob.mesh); catBlob.mesh = null; }
  const it = CAT_POSES.find((x) => x.pose === pose);
  catBlob.mesh = FX.blob(it.box); scene.add(catBlob.mesh);
}
setCat(HASH.kv.cat || catOfDay());

// ---------------------------------------------------------------- atmosphere
const P = META.points || {};
const glows = [];
for (const g of META.glows || []) {
  const nightOnly = g.when === 'N', p = V(g.p);     // N_ = a room lamp, B_ = always on (both are lit now)
  const nearValves = P.valves && p.distanceTo(V(P.valves)) < 0.2;
  const size = nearValves ? 0.24 : nightOnly ? 0.5 : 0.16;
  const s = FX.sprite(new THREE.Color(...g.color), size, nightOnly ? 0.42 : 0.5);
  scene.add(s); glows.push({ s, base: p, nightOnly, flicker: nearValves, op: s.material.opacity, seed: Math.random() * 50 });
}
let valve = null;
if (P.valves) { valve = FX.sprite(new THREE.Color(1, 0.42, 0.12), 0.2, 0.3); valve.position.copy(V(P.valves)); scene.add(valve); }
let stairsGlow = null;
if (P.stairs_glow) { stairsGlow = FX.sprite(new THREE.Color(0.30, 0.75, 0.80), 1.5, 0.16, FX.softTex); stairsGlow.position.copy(V(P.stairs_glow)); scene.add(stairsGlow); }
let phoneGlow = null;
if (P.phone) { phoneGlow = FX.sprite(new THREE.Color(1, 0.7, 0.45), 0.4, 0); phoneGlow.position.copy(V(P.phone)); scene.add(phoneGlow); }
let radioGlow = null;
if (BY.radio) { radioGlow = FX.sprite(new THREE.Color(1, 0.6, 0.25), 0.18, 0); radioGlow.position.copy(BY.radio.front).setY(BY.radio.center.y); scene.add(radioGlow); }
const smoke = P.smoke ? FX.wisp(V(P.smoke), 0.3, 0.5, 0xeadbc4, 1, 1) : null;
const steam = P.hob ? FX.wisp(V(P.hob), 0.4, 0.5, 0xf2efe8, 1.7, 0.55) : null;
if (smoke) scene.add(smoke); if (steam) scene.add(steam);
let sky = null;
if (META.window) { sky = FX.makeSky(META.window, STOPS); scene.add(sky); }
// dust in the light of the counter lamp, the two shelf washes and the pendants (only where a lamp would show it)
const dustPools = [];
for (const g of META.glows || []) {
  if (!/counter_lamp|pend|floor_lamp|nook_bulb|pianolamp/.test(g.name)) continue;
  dustPools.push({ p: g.p, r: /pend|nook/.test(g.name) ? 0.45 : 0.32, color: g.color.map((c) => c * 1.1) });
}
const dust = dustPools.length && !REDUCED ? FX.makeDust(dustPools, 90 * dustPools.length) : null;
if (dust) scene.add(dust);

// ---------------------------------------------------------------- camera state
let stop = ORDER.find((k) => HASH.flags.has(k)) || (STOPS.bar ? 'bar' : ORDER[0]);
const cam = { p: STOPS[stop].p.clone(), q: STOPS[stop].q.clone(), fov: STOPS[stop].fov };
let tween = null;
const view = { p: new THREE.Vector3(), q: new THREE.Quaternion(), fov: 45, f: new THREE.Vector3(), r: new THREE.Vector3(), u: new THREE.Vector3() };
const drift = { v: new THREE.Vector3(), k: 0 };
function goto(name, instant = false) {
  if (!STOPS[name]) return;
  if (name === stop && !tween && !instant) return;
  const to = STOPS[name], dist = cam.p.distanceTo(to.p), ang = cam.q.angleTo(to.q);
  stop = name; arrivedAt = null;
  updateDial(); hideTip(); document.body.classList.toggle('away', name !== 'bar');
  if (instant || REDUCED) { cam.p.copy(to.p); cam.q.copy(to.q); cam.fov = to.fov; tween = null; arrive(); return; }
  tween = { p0: cam.p.clone(), q0: cam.q.clone(), f0: cam.fov, to, t: 0, dur: clamp(1.9 + dist * 0.42 + ang * 0.5, 2.0, 3.8) };
}
let arrivedAt = 0, clockT = 0;
function arrive() { arrivedAt = clockT; refreshMarks(); }

const mouse = { x: 0, y: 0, sx: 0, sy: 0, last: -100 };
let pullS = 0; const tmpV3 = new THREE.Vector3(), tmpV4 = new THREE.Vector3();
const look = { x: 0, y: 0 }, ZERO2 = { x: 0, y: 0 }, lookOut = { x: 0, y: 0 };
function lookToward(p, fov, aspect) {      // yaw/pitch that bring p to the middle of the free part of the screen
  const free = panelFree(), d = tmpV2.copy(p).sub(view.p);
  const fz = d.dot(view.f); if (fz < 0.05) return ZERO2;
  const tv = Math.tan(THREE.MathUtils.degToRad(fov) / 2), th = tv * aspect;
  const nx = ((free.x0 + free.x1) / innerWidth) - 1, ny = 1 - ((free.y0 + free.y1) / innerHeight);
  const ox = Math.atan2(d.dot(view.r), fz), oy = Math.atan2(d.dot(view.u), fz);
  const mobile = innerWidth <= 720;
  lookOut.x = -clamp(ox - Math.atan(nx * th * 0.85), -0.55, 0.55) * (mobile ? 0.3 : 1);
  lookOut.y = mobile ? clamp(oy - Math.atan(ny * tv * 0.8), -0.3, 0.3) : clamp(oy, -0.08, 0.08) * 0.5;
  return lookOut;
}
const qTmp = new THREE.Quaternion(), eTmp = new THREE.Euler();
function updateCamera(dt, time) {
  if (tween) {
    tween.t = Math.min(1, tween.t + dt / tween.dur); const e = smooth(tween.t);
    cam.p.lerpVectors(tween.p0, tween.to.p, e); cam.q.slerpQuaternions(tween.q0, tween.to.q, e); cam.fov = lerp(tween.f0, tween.to.fov, e);
    cam.p.y += Math.sin(Math.PI * e) * 0.035;            // a slight lift: leaning across rather than sliding
    if (tween.t >= 1) { tween = null; arrive(); }
  }
  const aspect = innerWidth / innerHeight;
  let fov = cam.fov, pull = 0;
  if (aspect < 1.5) {          // narrow screens: keep some of the width, step back a little
    const h0 = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * 1.5);
    fov = Math.min(THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(h0 / 2) / aspect)), aspect < 0.8 ? 68 : 76);
    pull = clamp((1.5 - aspect) / 1.0, 0, 1) * (stop === 'bar' ? 0.38 : 0.26);
    // and if this stop's things still do not fit across the screen, step back a little further (at most 75 cm)
    const rg = REGIONS.find((r) => r.stop === stop);
    if (rg) {
      const hf = Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * aspect);
      const sz = rg.box.getSize(tmpV), c = rg.box.getCenter(tmpV2);
      const r = tmpV3.set(1, 0, 0).applyQuaternion(cam.q), f = tmpV4.set(0, 0, -1).applyQuaternion(cam.q);
      const half = (Math.abs(sz.x * r.x) + Math.abs(sz.z * r.z)) / 2 - 0.1, d0 = c.sub(cam.p).dot(f);
      pull = Math.max(pull, clamp((half * 1.05) / Math.tan(hf) - d0, 0, 0.75));
    }
  }
  pullS = pullS < 0 ? pull : pullS + (pull - pullS) * (1 - Math.exp(-dt * 1.5)); pull = pullS;
  view.f.set(0, 0, -1).applyQuaternion(cam.q); view.r.set(1, 0, 0).applyQuaternion(cam.q); view.u.set(0, 1, 0).applyQuaternion(cam.q);
  view.q.copy(cam.q); view.fov = fov;
  view.p.copy(cam.p).addScaledVector(view.f, -pull);
  drift.k += ((open && open.group === 'door' ? 1 : 0) - drift.k) * (1 - Math.exp(-dt * 0.9));
  if (drift.k > 0.001 && BY.door) { tmpV.copy(BY.door.center).sub(STOPS.stairs ? STOPS.stairs.p : cam.p); tmpV.y = 0; tmpV.setLength(0.38 * smooth(drift.k)); view.p.add(tmpV); }
  // with a panel open, turn the head a little so the object you picked up is not hidden behind the paper
  const lt = open && open.item && open.item.motion !== 'sleeve' ? lookToward(open.item.lookAt || open.item.center, fov, aspect) : ZERO2;
  const lk = 1 - Math.exp(-dt * 1.1);
  look.x += (lt.x - look.x) * lk; look.y += (lt.y - look.y) * lk;
  // parallax: a few degrees around the stop; on touch (or idle) a slow sway
  const idle = TOUCH || time - mouse.last > 8;
  const wide = aspect < 0.8 && !open ? 2.4 : 1;
  const sway = REDUCED ? 0 : 1;
  const ax = idle ? Math.sin(time * 0.19) * 0.55 * wide * sway : mouse.x, ay = idle ? Math.sin(time * 0.13 + 1.3) * 0.3 * sway : mouse.y;
  const k = 1 - Math.exp(-dt * 1.8);
  mouse.sx += (ax - mouse.sx) * k; mouse.sy += (ay - mouse.sy) * k;
  const amp = open ? 0.3 : 1;
  const yaw = -mouse.sx * 0.045 * amp + Math.sin(time * 0.11) * 0.004, pitch = -mouse.sy * 0.028 * amp + Math.sin(time * 0.083 + 2) * 0.003;
  camera.position.copy(view.p).addScaledVector(view.r, mouse.sx * 0.03 * amp).addScaledVector(view.u, -mouse.sy * 0.015 * amp);
  qTmp.setFromAxisAngle(UP, yaw + look.x); camera.quaternion.copy(view.q).premultiply(qTmp);
  tmpV.set(1, 0, 0).applyQuaternion(camera.quaternion);
  qTmp.setFromAxisAngle(tmpV, pitch + look.y); camera.quaternion.premultiply(qTmp);
  if (Math.abs(camera.fov - fov) > 0.01 || camera.aspect !== aspect) { camera.fov = fov; camera.aspect = aspect; camera.updateProjectionMatrix(); }
  camera.updateMatrixWorld();
}

// ---------------------------------------------------------------- panels
let open = null;      // {group, index, item, slug}
let rang = !!(SS && SS.getItem('rang'));
function openPanel(group, index, opts = {}) {
  const p = panelFor(group, index, { rang });
  if (!p) return;
  const it = itemFor(group, index);
  if (it && it.stop !== stop) goto(it.stop, !!opts.instant);
  if (open && open.item && open.item !== it) open.item.target = 0;
  panel.className = 'on ' + p.cls + (opts.instant ? ' instant' : '');
  panel.setAttribute('aria-hidden', 'false'); panel.setAttribute('aria-label', p.label);
  panelBody.innerHTML = p.html; sheet.scrollTop = 0;
  open = { group, index, item: it, slug: slugFor(group, index) };
  if (it) it.target = 1;
  document.body.classList.add('panel-open'); document.body.classList.toggle('downstairs', group === 'door');
  hideTip(); refreshMarks();
  if (open.slug) history.replaceState(null, '', '#' + open.slug);
  if (opts.instant) requestAnimationFrame(() => panel.classList.remove('instant'));
  setTimeout(() => $('#close').focus({ preventScroll: true }), 60);
}
function closePanel() {
  if (!open) return;
  if (open.item) open.item.target = 0;
  open = null;
  panel.classList.remove('on'); panel.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('panel-open', 'downstairs');
  history.replaceState(null, '', location.pathname + location.search);
  refreshMarks(); canvas.focus({ preventScroll: true });
}
$('#close').addEventListener('click', closePanel);
panel.addEventListener('click', (e) => {
  const go = e.target.closest('[data-go]');
  if (go) { const [g, i] = go.dataset.go.split(':'); openPanel(g, +i); return; }
  if (e.target === sheet || e.target === panel) closePanel();     // the dark margin around the paper counts as outside
});
addEventListener('hashchange', () => {
  const h = parseHash(location.hash);
  if (h.slug && (!open || open.slug !== h.slug)) { const [g, i] = SLUGS[h.slug]; openPanel(g, i); }
});

// ---------------------------------------------------------------- sound controls
const sndBtn = $('#snd');
function syncSound() {
  const s = AU.state();
  sndBtn.setAttribute('aria-pressed', String(s.music)); sndBtn.title = 'Sound: ' + (s.music ? 'on' : 'off');
}
function toggleMusic() { AU.setMusic(!AU.state().music); syncSound(); }
sndBtn.addEventListener('click', toggleMusic);

// ---------------------------------------------------------------- the line at the edge of the screen
const whisperEl = $('#whisper'); let whisperT = 0;
function whisper(text, ms = 4200) {
  whisperEl.textContent = text; whisperEl.classList.add('on');
  clearTimeout(whisperT); whisperT = setTimeout(() => whisperEl.classList.remove('on'), ms);
}
let catLine = Math.floor(Math.random() * C.CAT_LINES.length);

// ---------------------------------------------------------------- acting on things
function perform(it) {
  switch (it.act) {
    case 'panel': openPanel(it.group || it.name, it.index); break;
    case 'music': toggleMusic(); it.pulse = 1; break;
    case 'chord': AU.pianoChord(); it.pulse = 1; break;
    case 'radio': AU.setRadio(!AU.state().radio); it.pulse = 1; break;
    case 'say': whisper(C.REEL_LINE, 3200); break;
    case 'smoke': startPuff(); break;
    case 'cat': whisper(C.CAT_LINES[catLine++ % C.CAT_LINES.length], 3600); break;
  }
}
function act(hit) {
  if (open) { closePanel(); return; }
  if (!hit) { if (!TOUCH && stop !== 'bar') goto('bar'); return; }
  if (hit.region) { goto(hit.region.stop); return; }
  const it = hit.item;
  if (it.act === 'cat' || it.act === 'say') { perform(it); return; }
  if (!it.act) return;
  if (it.stop !== stop) { goto(it.stop); return; }
  perform(it);
}
function describe(hit) {
  if (!hit) return stop !== 'bar' && !TOUCH ? ['', 'Back to the stool', true, true] : null;
  if (hit.region) return ['Go over', C.STOP_NAMES[hit.region.stop] || hit.region.stop, true];
  const it = hit.item, l = labelFor(it);
  if (!l) return null;
  if (it.act === 'cat' || it.act === 'say') return [l[0], l[1], it.act === 'cat', true];
  if (it.stop !== stop) return ['Go over', C.STOP_NAMES[it.stop] || it.stop, true];
  return [l[0], l[1], true];
}

// ---------------------------------------------------------------- picking: boxes first, then an occlusion check against the room
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), hitP = new THREE.Vector3();
let grid = null;        // built shortly after the first frame; until then, plain raycasts
function occluded(origin, dir, dist, self) {
  const far = Math.max(0, dist - 0.02);
  const movers = BY.door && BY.door.obj !== self ? [BY.door.obj] : [];
  ray.set(origin, dir); ray.near = 0; ray.far = far;
  let hit = movers.length && ray.intersectObjects(movers, true).length > 0;
  if (!hit) hit = grid ? grid.blocked(origin, dir, far) : ray.intersectObjects(staticMeshes, false).length > 0;
  ray.far = Infinity;
  return hit;
}
const isChildOf = (o, p) => { for (; o; o = o.parent) if (o === p) return true; return false; };
function pick(cx, cy) {
  const r = canvas.getBoundingClientRect();
  ndc.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const o = ray.ray.origin.clone(), d = ray.ray.direction.clone();
  const cands = [];
  for (const it of ITEMS) {
    if (it.hidden || it.busy || !it.label) continue;
    if (ray.ray.intersectBox(it.hit, hitP)) cands.push({ item: it, dist: hitP.distanceTo(o) });
  }
  for (const rg of REGIONS) if (rg.stop !== stop && ray.ray.intersectBox(rg.box, hitP)) cands.push({ region: rg, dist: hitP.distanceTo(o) + 0.3 });
  cands.sort((a, b) => a.dist - b.dist);
  for (const c of cands) {
    if (!occluded(o, d, c.dist, c.item && c.item.obj)) return c;
  }
  return null;
}

let hovered = null, lastPick = 0, pendingMove = null;
function hideTip() { tip.classList.remove('on'); canvas.classList.remove('hot'); hovered = null; }
function hoverAt(x, y) {
  if (open || tween) { hideTip(); return; }
  const h = pick(x, y), d = describe(h);
  hovered = h && h.item ? h.item : null;
  canvas.classList.toggle('hot', !!(d && d[2]));
  if (d) {
    tip.innerHTML = (d[0] ? esc(d[0]) : '') + '<b>' + esc(d[1]) + '</b>'; tip.classList.toggle('quiet', !!d[3]); tip.classList.add('on');
    const tx = Math.min(x + 16, innerWidth - tip.offsetWidth - 8), ty = Math.min(y + 20, innerHeight - tip.offsetHeight - 8);
    tip.style.transform = `translate(${tx}px, ${ty}px)`;
  } else tip.classList.remove('on');
}
canvas.addEventListener('pointermove', (ev) => {
  if (ev.pointerType === 'touch') return;
  mouse.x = (ev.clientX / innerWidth) * 2 - 1; mouse.y = (ev.clientY / innerHeight) * 2 - 1; mouse.last = performance.now() / 1000;
  pendingMove = [ev.clientX, ev.clientY];
});
canvas.addEventListener('pointerleave', () => { pendingMove = null; hideTip(); });
let down = null;
canvas.addEventListener('pointerdown', (ev) => { down = { x: ev.clientX, y: ev.clientY, t: performance.now() }; });
canvas.addEventListener('pointerup', (ev) => {
  if (!down) return;
  const dx = ev.clientX - down.x, dy = ev.clientY - down.y, d0 = down; down = null;
  if (Math.hypot(dx, dy) > 45 && Math.abs(dx) > Math.abs(dy) * 1.4 && performance.now() - d0.t < 800) {
    if (!open) step(dx < 0 ? 1 : -1);
    return;
  }
  if (Math.hypot(dx, dy) < 12) act(open ? null : pick(ev.clientX, ev.clientY));
});
function step(n) { const i = ORDER.indexOf(stop); goto(ORDER[(i + n + ORDER.length) % ORDER.length]); }

// ---------------------------------------------------------------- brass rings over what opens at this stop
const marksEl = $('#marks');
for (const it of ITEMS) {
  if (!it.clickable || it.group === 'cat') continue;
  const b = document.createElement('button'); b.className = 'mark'; b.type = 'button'; b.innerHTML = '<i></i>';
  b.setAttribute('aria-label', (it.label || []).filter(Boolean).join(': '));
  b.addEventListener('click', (e) => { e.stopPropagation(); if (open) closePanel(); else act({ item: it }); });
  b.addEventListener('pointerenter', () => { if (TOUCH) return; hovered = it; const r = b.getBoundingClientRect(); hoverTip(it, r.right, r.top); });
  b.addEventListener('pointerleave', () => { hovered = null; hideTip(); });
  marksEl.appendChild(b);
  // ring sits on the top front edge of the object
  const p = it.front.clone(); p.y = it.box.max.y - Math.min(0.03, it.size.y * 0.25);
  if (it.size.y < 0.06) p.y = it.box.max.y + 0.015;
  it.mark = { el: b, p, on: false, vis: true };
}
function hoverTip(it, x, y) {
  const d = describe({ item: it }); if (!d) return;
  tip.innerHTML = (d[0] ? esc(d[0]) : '') + '<b>' + esc(d[1]) + '</b>'; tip.classList.remove('quiet'); tip.classList.add('on');
  tip.style.transform = `translate(${Math.min(x + 8, innerWidth - tip.offsetWidth - 8)}px, ${Math.max(8, y - tip.offsetHeight - 6)}px)`;
}
function refreshMarks() {        // which rings are not hidden behind something, from this stop's camera
  const s = STOPS[stop]; if (!s) return;
  for (const it of ITEMS) {
    if (!it.mark) continue;
    if (it.stop !== stop) { it.mark.vis = false; continue; }
    const d = it.mark.p.clone().sub(s.p), L = d.length();
    it.mark.vis = !occluded(s.p, d.normalize(), L - 0.02, it.obj);
  }
}
const pv = new THREE.Vector3();
function updateMarks(time) {
  const show = !open && !tween && !SM.on && arrivedAt !== null && clockT - arrivedAt > 0.6;
  const placed = [];
  for (const it of ITEMS) {
    const m = it.mark; if (!m) continue;
    const ringing = it.name === 'phone' && ring.on;
    let on = (show && m.vis && !it.busy) || (ringing && !open);
    if (on) {
      pv.copy(m.p).project(camera);
      const x = ((pv.x + 1) / 2) * innerWidth, y = ((1 - pv.y) / 2) * innerHeight;
      if (pv.z > 1 || x < 10 || y < 10 || x > innerWidth - 10 || y > innerHeight - 10) on = false;
      else if (!ringing && placed.some((q) => Math.hypot(q[0] - x, q[1] - y) < 20)) on = false;    // keep crowded spots tidy
      else { placed.push([x, y]); m.el.style.transform = `translate(${x}px, ${y}px)`; }
    }
    if (on !== m.on) { m.el.classList.toggle('on', on); m.on = on; }
    m.el.classList.toggle('ringing', ringing);
  }
}

// ---------------------------------------------------------------- the dial
const dial = $('#dial'), stations = dial.querySelector('.stations'), needle = dial.querySelector('.needle');
ORDER.forEach((k, i) => {
  const b = document.createElement('button'); b.type = 'button'; b.dataset.stop = k;
  b.innerHTML = `<b>${i + 1}</b>${esc(C.STOP_SHORT[k] || k)}`; b.title = (C.STOP_NAMES[k] || k) + ' (' + (i + 1) + ')';
  b.addEventListener('click', () => { closePanel(); goto(k); });
  stations.appendChild(b);
});
function updateDial() {
  let cur = null;
  stations.querySelectorAll('button').forEach((b) => { const on = b.dataset.stop === stop; b.setAttribute('aria-current', String(on)); if (on) cur = b; });
  if (cur) needle.style.transform = `translateX(${cur.offsetLeft + cur.offsetWidth / 2 - 1 + stations.offsetLeft}px)`;
  // if the keyboard moved us (arrows, 1-6, Esc) while a station button had focus, take the focus along:
  // otherwise the focus ring stays behind on the stop we just left
  const f = document.activeElement;
  if (cur && f && f !== cur && f.parentNode === stations) cur.focus({ preventScroll: true });
}

// ---------------------------------------------------------------- help, keys
const help = $('#help'), info = $('#info');
help.innerHTML = `<h2>${esc(C.HELP.title)}</h2><ul>${C.HELP.items.map((x) => `<li>${esc(x)}</li>`).join('')}</ul><small>${esc(C.HELP.small)}</small>`;
info.addEventListener('click', () => { const on = !help.classList.contains('on'); help.classList.toggle('on', on); info.setAttribute('aria-expanded', String(on)); });
addEventListener('keydown', (e) => {
  if (e.target && /input|textarea/i.test(e.target.tagName)) return;
  if (e.key === 'Escape') {
    if (help.classList.contains('on')) { help.classList.remove('on'); info.setAttribute('aria-expanded', 'false'); }
    else if (open) closePanel(); else goto('bar');
  } else if (!open && (e.key === 'ArrowRight' || e.key === 'ArrowLeft')) step(e.key === 'ArrowRight' ? 1 : -1);
  else if (!open && /^[1-9]$/.test(e.key) && ORDER[+e.key - 1]) goto(ORDER[+e.key - 1]);
});

// ---------------------------------------------------------------- the telephone that rings once
const ring = { on: false, t: 0, at: rang ? Infinity : 40 + Math.random() * 50 };
function startRing(hold) {
  if (ring.on) return;
  ring.on = true; ring.t = 0; ring.at = Infinity; rang = true; if (SS) SS.setItem('rang', '1');
  AU.phoneBell();
  whisper(C.PHONE_WHISPER, hold || 4800);
}
const burst = (t) => (t < 0.9 || (t > 1.35 && t < 2.25) ? 1 : 0);

// ---------------------------------------------------------------- the second moon
const moon = { dwell: 0, need: +(HASH.kv.moon || 12), on: !!(SS && SS.getItem('moon2')), a: SS && SS.getItem('moon2') ? 1 : 0 };

// ---------------------------------------------------------------- the cigar: pick it up, draw, let the smoke out, put it back
// The model gives three points on its centre line (scene.json: cigar_foot, cigar_ember, cigar_head). Everything else is posed
// from those: where it rests, where the hand holds it up to be looked at, and where it sits when it is in your mouth.
const CG_T = { lift: 1.15, look: 0.85, mouth: 0.75, draw: 1.7, back: 1.3, tap: 0.55 };
CG_T.t1 = CG_T.lift; CG_T.t2 = CG_T.t1 + CG_T.look; CG_T.t3 = CG_T.t2 + CG_T.mouth; CG_T.t4 = CG_T.t3 + CG_T.draw; CG_T.t5 = CG_T.t4 + CG_T.back;
const SM = { on: false, t: 0, hold: false, in: false, out: false, tap: false, tapped: false, puffs: 0, said: false, warm: 0, ash: 1, ashTo: 1, drawK: 0 };
const CIGAR = (() => {
  const it = BY.cigar; if (!it || !P.cigar_foot || !P.cigar_head || !P.cigar_ember) return null;
  const foot = V(P.cigar_foot), head = V(P.cigar_head), ember = V(P.cigar_ember);
  const a0 = head.clone().sub(foot).normalize();
  const n0 = UP.clone().addScaledVector(a0, -a0.y).normalize(), s0 = new THREE.Vector3().crossVectors(a0, n0);
  const rest = new THREE.Matrix4().makeBasis(a0, n0, s0).transpose();        // the resting frame, inverted (it is orthonormal)
  it.obj.updateMatrixWorld(true);
  // the ash hangs from a pivot on the burn line whose X axis is the cigar's own, so it can be made longer or shorter
  const ash = it.obj.getObjectByName('cigar_ash'); let pivot = null;
  if (ash) {
    pivot = new THREE.Group(); it.obj.add(pivot);
    pivot.position.copy(it.obj.worldToLocal(ember.clone()));
    pivot.quaternion.setFromUnitVectors(new THREE.Vector3(1, 0, 0), a0.clone().applyQuaternion(it.obj.quaternion.clone().invert()));
    pivot.updateMatrixWorld(true); pivot.attach(ash);
  }
  const glow = FX.sprite(new THREE.Color(1, 0.36, 0.07), 0.04, 0); glow.renderOrder = 9; scene.add(glow);
  const lamp = (META.glows || []).find((g) => /counter_lamp/.test(g.name));
  const puff = FX.makePuff(SMALL_SCREEN ? 20 : 34);
  if (lamp) puff.material.uniforms.uLamp.value.copy(V(lamp.p));
  scene.add(puff);
  return { it, foot, head, ember, a0, n0, rest, len: head.distanceTo(foot), pivot, glow, puff,
    footL: foot.clone().sub(it.home.p), emberL: ember.clone().sub(it.home.p), midL: foot.clone().lerp(head, 0.6).sub(it.home.p),
    emberW: ember.clone(), focus: new THREE.Vector3(), held: 0, wisp: 0.2, qd: new THREE.Quaternion() };
})();
function startPuff() {
  if (!CIGAR || SM.on) return;
  SM.on = true; SM.t = 0; SM.hold = false; SM.in = false; SM.out = false; SM.tapped = false; SM.puffs++;
  SM.tap = SM.ashTo >= 1.3;                    // by about the third draw the ash is long enough to knock off
  CIGAR.it.busy = true; hideTip();
  if (!SM.said) { SM.said = true; whisper(C.CIGAR_FIRST, 3800); }
}
function breatheOut(time) {
  SM.out = true;
  const c = CIGAR, p = c.puff;
  if (REDUCED) { p.userData.emit(tmpV.copy(c.emberW).setY(c.emberW.y + 0.03), tmpV2.set(0, 1, 0), time, { speed: 0.35, spread: 0.3 }); }
  else {
    const o = tmpV.copy(view.p).addScaledVector(view.f, 0.09).addScaledVector(view.u, -0.075);
    p.userData.emit(o, tmpV2.copy(view.f).addScaledVector(view.u, -0.10).normalize(), time);
  }
  p.visible = true; AU.breath('out');
}
// a point `d` metres in front of the eye, at (nx, ny) of the half-screen
const cgAt = (out, d, nx, ny, tanV, aspect) => out.copy(view.p).addScaledVector(view.f, d).addScaledVector(view.r, nx * d * tanV * Math.min(aspect, 1.9)).addScaledVector(view.u, ny * d * tanV);
const cgA = new THREE.Vector3(), cgN = new THREE.Vector3(), cgS = new THREE.Vector3(), cgM = new THREE.Matrix4();
const cgF1 = new THREE.Vector3(), cgF2 = new THREE.Vector3(), cgQ1 = new THREE.Quaternion(), cgQ2 = new THREE.Quaternion(), QI = new THREE.Quaternion();
function cgQuat(out, ax, top) {                // the turn that takes the resting cigar to: axis (foot -> head) = ax, band's face toward `top`
  cgA.copy(ax).normalize(); cgN.copy(top).addScaledVector(cgA, -top.dot(cgA)).normalize(); cgS.crossVectors(cgA, cgN);
  return out.setFromRotationMatrix(cgM.makeBasis(cgA, cgN, cgS).multiply(CIGAR.rest));
}
function poseCigar(it, dt, time) {
  const c = CIGAR, o = it.obj, T = CG_T;
  if (SM.on && !SM.hold) SM.t += dt;
  const t = SM.on ? SM.t : 0;
  let F = c.foot, q = QI, held = 0; SM.drawK = 0;
  if (SM.on && !REDUCED) {
    const tanV = Math.tan(THREE.MathUtils.degToRad(view.fov) / 2), aspect = innerWidth / innerHeight;
    // held up to be looked at: across the view, foot to the left and a little away, the band turned to the eye
    cgQuat(cgQ1, tmpV.copy(view.r).multiplyScalar(0.86).addScaledVector(view.u, -0.16).addScaledVector(view.f, -0.44), tmpV2.copy(view.f).negate().addScaledVector(view.u, 0.3));
    cgAt(cgF1, 0.31, 0.06, -0.15, tanV, aspect).addScaledVector(cgA, -c.len * 0.5);
    cgF1.y += Math.sin(time * 1.3) * 0.0012;
    // in the corner of the mouth: it comes up out of the bottom of the frame, a little from the right, lit end in view
    cgQuat(cgQ2, tmpV.copy(view.f).multiplyScalar(-0.80).addScaledVector(view.u, -0.42).addScaledVector(view.r, 0.40), view.u);
    cgAt(cgF2, 0.20, -0.10, -0.50, tanV, aspect);
    if (t < T.t1) { const e = smooth(t / T.t1); F = tmpV3.lerpVectors(c.foot, cgF1, e); F.y += Math.sin(Math.PI * e) * 0.03; q = tmpQ2.slerpQuaternions(QI, cgQ1, e); held = e; }
    else if (t < T.t2) { F = cgF1; q = cgQ1; held = 1; }
    else if (t < T.t3) { const e = smooth((t - T.t2) / T.mouth); F = tmpV3.lerpVectors(cgF1, cgF2, e); q = tmpQ2.slerpQuaternions(cgQ1, cgQ2, e); held = 1; }
    else if (t < T.t4) {
      const x = (t - T.t3) / T.draw; SM.drawK = Math.max(0, Math.sin(Math.PI * Math.min(1, x * 1.15))) ** 0.6;
      F = tmpV3.copy(cgF2).addScaledVector(view.f, -0.004 * SM.drawK); q = cgQ2; held = 1;
    } else if (t < T.t5) { const e = smooth((t - T.t4) / T.back); F = tmpV3.lerpVectors(cgF2, c.foot, e); F.y += Math.sin(Math.PI * e) * 0.035; q = tmpQ2.slerpQuaternions(cgQ2, QI, e); held = 1 - e; }
  } else if (SM.on) {                           // reduced motion: it stays where it is and simply glows
    if (t >= T.t3 && t < T.t4) SM.drawK = Math.max(0, Math.sin(Math.PI * Math.min(1, ((t - T.t3) / T.draw) * 1.15))) ** 0.6;
  }
  if (SM.on) {
    if (t >= T.t3 && !SM.in) { SM.in = true; AU.breath('in'); }
    if (t >= T.t4) SM.warm = 1;
    if (t >= T.t4 + 0.12 && !SM.out) breatheOut(time);
    if (t >= T.t5) {
      if (SM.tap) {                             // two small knocks on the rim; the ash lets go on the first
        const x = (t - T.t5) / T.tap;
        if (x < 1) rotAbout(o, it.home.p, it.side, Math.sin(x * Math.PI * 4) * 0.045 * (1 - x));
        if (x > 0.12 && !SM.tapped) { SM.tapped = true; SM.ashTo = 0.3; whisper(C.CIGAR_ASH, 3200); }
      }
      if (t >= T.t5 + (SM.tap ? T.tap : 0)) { SM.on = false; it.busy = false; if (!SM.tap) SM.ashTo += SM.ashTo < 1 ? 0.35 : 0.2; }
    }
  }
  c.held = held;
  if (q !== QI) {
    o.quaternion.copy(q).multiply(it.home.q);
    o.position.copy(F).sub(tmpV4.copy(c.footL).applyQuaternion(q));
  }
  c.qd.copy(q);
  // the ash: longer after every draw, short again once it has been knocked off (it falls faster than it grows)
  SM.ash += (SM.ashTo - SM.ash) * (1 - Math.exp(-dt * (SM.ashTo < SM.ash ? 14 : 1.2)));
  if (c.pivot) c.pivot.scale.set(SM.ash, 1, 1);
}
function updateCigarFx(dt, time) {
  const c = CIGAR, o = c.it.obj;
  c.emberW.copy(c.emberL).applyQuaternion(c.qd).add(o.position);
  c.focus.copy(c.midL).applyQuaternion(c.qd).add(o.position);
  SM.warm = Math.max(0, SM.warm - dt / 7);
  // the ember: a breath of red at rest, white-orange while you draw on it, then it settles
  const flick = 0.9 + 0.1 * (Math.sin(time * 9.1) * 0.6 + Math.sin(time * 23.7 + 1) * 0.4);
  const k = Math.max(SM.drawK * (0.85 + 0.15 * Math.sin(time * 31)), SM.warm * SM.warm * 0.35);
  tmpV.subVectors(camera.position, c.emberW).normalize();
  c.glow.position.copy(c.emberW).addScaledVector(tmpV, 0.011).addScaledVector(tmpV2.copy(c.a0).applyQuaternion(c.qd), -0.003);
  c.glow.scale.setScalar(lerp(0.035, 0.10, k));
  c.glow.material.opacity = (0.10 * flick + 0.85 * k) * (lens ? 0.8 : 1);
  c.glow.material.color.setRGB(1, lerp(0.30, 0.52, k), lerp(0.05, 0.16, k));
  // the wisp rises from wherever the lit end is: thin in the hand, nothing while air is being pulled through it,
  // and a good deal more for a while after it has been drawn on
  if (smoke) {
    smoke.position.copy(c.emberW); smoke.position.y += 0.006;
    const inMouth = SM.on && SM.t > CG_T.t2 + 0.3 && SM.t < CG_T.t4 + 0.4;
    const want = inMouth ? 0 : lerp(0.2 + 0.22 * SM.warm, 0.13, c.held);
    c.wisp += (want - c.wisp) * (1 - Math.exp(-dt * 3));
    smoke.scale.setScalar(lerp(1, 0.42, c.held));
    smoke.material.uniforms.uWidth.value = 1 + 0.7 * SM.warm * (1 - c.held);
  }
  const p = c.puff;
  if (p.visible) { p.material.uniforms.uTime.value = time; if (!p.userData.active(time)) p.visible = false; }
}

// ---------------------------------------------------------------- per-frame: objects
const sleeveQ = new THREE.Quaternion(), basis = new THREE.Matrix4(), bx = new THREE.Vector3(), bz = new THREE.Vector3();
let platterAngle = 0;
function rotAbout(obj, pivot, axis, angle) {
  tmpQ.setFromAxisAngle(axis, angle);
  obj.position.sub(pivot).applyQuaternion(tmpQ).add(pivot);
  obj.quaternion.premultiply(tmpQ);
}
function panelFree() {      // the part of the screen the open panel leaves free
  const mobile = innerWidth <= 720;
  if (mobile) return { x0: 0, x1: innerWidth, y0: 0, y1: innerHeight - panel.offsetHeight };
  return { x0: 0, x1: innerWidth - panel.offsetWidth, y0: 0, y1: innerHeight };
}
function updateItems(dt, time) {
  for (const it of ITEMS) {
    const speed = it.motion === 'sleeve' ? 0.8 : it.motion === 'door' ? 0.45 : 1.4;
    it.t = clamp(it.t + Math.sign(it.target - it.t) * dt * speed, 0, 1);
    const hov = hovered === it && !open && it.stop === stop ? 1 : hovered === it ? 0.6 : 0;
    it.h += (hov - it.h) * (1 - Math.exp(-dt * 9));
    it.pulse = Math.max(0, it.pulse - dt * 1.6);
    const e = smooth(it.t), o = it.obj;
    o.position.copy(it.home.p); o.quaternion.copy(it.home.q); o.scale.copy(it.home.s);
    const hn = it.h * (it.stop === stop ? 1 : 0);
    let hl = it.h * (1 - e);
    switch (it.motion) {
      case 'sleeve': poseSleeve(it, e, hn, time); hl = it.h * (1 - Math.min(1, e * 3)); break;
      case 'tilt': o.position.addScaledVector(it.out, e * 0.035 + hn * 0.006); o.position.y += e * 0.004; rotAbout(o, tmpV2.copy(it.front).addScaledVector(it.out, e * 0.035), it.side, e * 0.24 + hn * 0.03); break;
      case 'lift': o.position.y += e * 0.035 + hn * 0.006; o.position.addScaledVector(it.out, e * 0.02); break;
      case 'lean': rotAbout(o, it.front, it.side, e * 0.12 + hn * 0.03); o.position.y += e * 0.006; break;
      case 'nudge': o.position.y += e * 0.006 + hn * 0.003; rotAbout(o, it.center, UP, e * 0.06); break;
      case 'slide': o.position.addScaledVector(it.out, e * 0.025 + hn * 0.004); break;
      case 'cigar': if (CIGAR) { poseCigar(it, dt, time); if (it.busy) hl = 0; else o.position.y += hn * 0.004; } break;
      case 'lid': rotAbout(o, it.back, it.side, -(e * 0.07 + hn * 0.025)); break;
      case 'door': rotAbout(o, it.home.p, UP, it.swing * (e * 0.3 + hn * 0.03)); break;
      case 'dip': o.position.y -= Math.sin(Math.min(1, it.pulse) * Math.PI) * 0.004 + hn * 0.001; break;
      case 'spin': platterAngle -= dt * (33.333 / 60) * Math.PI * 2; tmpQ.setFromAxisAngle(UP, platterAngle); o.quaternion.multiply(tmpQ); break;
      case 'bob': rotAbout(o, it.home.p, it.bobAxis, Math.sin(platterAngle) * 0.0035); break;
      case 'twitch': {
        const ph = time % 1, a = ph < 0.05 ? ph / 0.05 : Math.exp(-(ph - 0.05) * 14);
        rotAbout(o, it.home.p, it.wallAxis, -THREE.MathUtils.degToRad(1) * a); break;
      }
      case 'breathe': { const b = Math.sin(time * 1.6) * 0.5 + 0.5; o.scale.set(it.home.s.x * (1 + b * 0.006), it.home.s.y * (1 + b * 0.014), it.home.s.z * (1 + b * 0.006)); break; }
    }
    if (it.name === 'phone' && ring.on) { const j = burst(ring.t) * Math.sin(time * 70) * 0.006; rotAbout(o, it.center, UP, j); }
    const glow = it.name === 'phone' && ring.on ? burst(ring.t) * (0.5 + 0.5 * Math.sin(ring.t * 20)) * 0.35 : 0;
    for (const m of it.mats) if (m.uniforms) { m.uniforms.uHover.value = hl; m.uniforms.uGlow.value = glow; }
  }
}
function poseSleeve(it, e, hn, time) {
  const o = it.obj;
  const a = smooth(e / 0.3), b = smooth((e - 0.24) / 0.76);
  const slide = Math.max(0.12, Math.min(0.24, it.size.x * Math.abs(it.out.x) + it.size.z * Math.abs(it.out.z)) * 0.75);
  o.position.addScaledVector(it.out, hn * 0.012 + a * slide);
  if (b <= 0) return;
  // fly to a spot in front of the camera, front cover (the local -X face) toward the viewer, upright
  const free = panelFree(), vw = innerWidth, vh = innerHeight;
  const tanV = Math.tan(THREE.MathUtils.degToRad(view.fov) / 2), aspect = vw / vh;
  const ls = it.lbox.getSize(tmpV).multiply(it.home.s), hW = ls.y, wW = ls.z;
  const fw = free.x1 - free.x0, fh = free.y1 - free.y0;
  const pxPerM = Math.min((fh * 0.56) / hW, (fw * 0.62) / wW);
  const d = Math.max(0.3, vh / (2 * tanV * pxPerM));
  const cx = (free.x0 + free.x1) / 2, cy = (free.y0 + free.y1) / 2;
  const nx = (cx / vw) * 2 - 1, ny = 1 - (cy / vh) * 2;
  const target = tmpV2.copy(view.p).addScaledVector(view.f, d).addScaledVector(view.r, nx * d * tanV * aspect).addScaledVector(view.u, ny * d * tanV);
  target.y += Math.sin(time * 0.7) * 0.003;
  bz.crossVectors(view.f, view.u);                  // local Z -> camera right
  basis.makeBasis(view.f, view.u, bz); sleeveQ.setFromRotationMatrix(basis);
  tmpQ.setFromAxisAngle(view.u, 0.16 + Math.sin(time * 0.45) * 0.025); sleeveQ.premultiply(tmpQ);   // a slight turn, held in the hand
  const lc = it.lbox.getCenter(new THREE.Vector3()).multiply(it.home.s).applyQuaternion(sleeveQ);
  target.sub(lc);
  o.position.lerp(target, b); o.quaternion.slerp(sleeveQ, b);
}

// ---------------------------------------------------------------- per-frame: atmosphere
function updateAtmos(dt, time) {
  for (const g of glows) {
    tmpV.subVectors(camera.position, g.base).normalize();
    g.s.position.copy(g.base).addScaledVector(tmpV, 0.12);
    let op = g.op * GLOW_K;
    if (g.flicker) op *= 1 + 0.02 * (Math.sin(time * 13 + g.seed) * 0.6 + Math.sin(time * 31.7 + g.seed * 2) * 0.4);
    g.s.material.opacity = op; g.s.visible = op > 0.003;
  }
  if (valve) { valve.material.opacity = 0.36 * GLOW_K * (1 + 0.02 * (Math.sin(time * 11.3) * 0.5 + Math.sin(time * 27.1 + 1) * 0.3 + Math.sin(time * 53.9) * 0.2)); }
  if (stairsGlow) {
    const at = stop === 'stairs' && !tween ? 1 : 0.55;
    stairsGlow.userData.k = lerp(stairsGlow.userData.k ?? at, at, 1 - Math.exp(-dt * 0.5));
    stairsGlow.material.opacity = (0.10 + 0.07 * (0.5 + 0.5 * Math.sin(time * 0.62))) * stairsGlow.userData.k * (1 + 0.6 * drift.k);
  }
  if (phoneGlow) phoneGlow.material.opacity = ring.on ? burst(ring.t) * (0.25 + 0.2 * Math.sin(ring.t * 22)) : 0;
  if (radioGlow) radioGlow.material.opacity += ((AU.state().radio ? 0.35 : 0) - radioGlow.material.opacity) * (1 - Math.exp(-dt * 2));
  for (const w of [smoke, steam]) {
    if (!w) continue;
    w.material.uniforms.uTime.value = time;
    w.rotation.y = Math.atan2(camera.position.x - w.position.x, camera.position.z - w.position.z);
  }
  if (smoke) smoke.material.uniforms.uAlpha.value = CIGAR ? CIGAR.wisp : 0.2;
  if (CIGAR) updateCigarFx(dt, time);
  if (steam) steam.material.uniforms.uAlpha.value = 0.08;
  if (sky) { const u = sky.material.uniforms; u.uTime.value = time; u.uMoon2.value = moon.a; }
  if (dust) { dust.material.uniforms.uTime.value = time; dust.material.uniforms.uScale.value = innerHeight * renderer.getPixelRatio(); }
}

let wallT = 0;
function updateStrange(dt, rdt) {
  // the telephone (timed in real seconds, counted only while the page is visible)
  wallT += rdt;
  if (!ring.on && wallT > ring.at) startRing();
  if (ring.on) { ring.t += dt; if (ring.t > 3.2) ring.on = false; }
  // the second moon: stay at the window, at night, for a while
  if (!moon.on) {
    if (stop === 'window' && !tween && !open) moon.dwell += rdt; else moon.dwell = 0;
    if (moon.dwell > moon.need) { moon.on = true; if (SS) SS.setItem('moon2', '1'); }
  }
  if (moon.on && moon.a < 1) moon.a = Math.min(1, moon.a + dt / 7);
}

// ---------------------------------------------------------------- frame loop, adaptive resolution
function resize() { renderer.setSize(innerWidth, innerHeight, false); if (lens) lens.setSize(innerWidth, innerHeight, renderer.getPixelRatio()); updateDial(); }
addEventListener('resize', resize); resize();
function adapt(dt) {
  if (perf.locked || frames < 40 || document.hidden) return;
  perf.acc += dt; perf.n++;
  if (perf.acc < 2) return;
  const avg = perf.acc / perf.n; perf.acc = 0; perf.n = 0;
  if (avg > 1 / 32) {
    // too slow: first the lens gives up its expensive parts, then the resolution comes down
    if (lens && lens.q > 1) { lens.setQuality(1); resize(); }
    else if (perf.ratio > 0.75) { perf.ratio = Math.max(0.75, +(perf.ratio * 0.8).toFixed(2)); renderer.setPixelRatio(perf.ratio); resize(); }
    else if (lens && lens.q > 0) { lens.setQuality(0); resize(); }
  }
}

// ---------------------------------------------------------------- where the lens focuses
// each stop meters a point on screen (what you would look at from there); with something picked up, it racks to that thing
const FOCUS_AT = { bar: [0.5, 0.5], records: [0.5, 0.52], hifi: [0.5, 0.5], table: [0.5, 0.5], window: [0.42, 0.5], stairs: [0.5, 0.62] };
const fwd = new THREE.Vector3();
function updateFocus() {
  if (CIGAR && CIGAR.held > 0.5 && !open) {            // in the hand: the lens follows the cigar, the room goes soft
    camera.getWorldDirection(fwd);
    lens.focusAt(Math.max(0.14, tmpV.copy(CIGAR.focus).sub(camera.position).dot(fwd)));
  } else if (open && open.item) {
    const it = open.item; it.obj.updateMatrixWorld();
    const c = it.lbox.getCenter(tmpV).applyMatrix4(it.obj.matrixWorld);
    camera.getWorldDirection(fwd);
    lens.focusAt(Math.max(0.2, c.sub(camera.position).dot(fwd)));
  } else lens.focusOn(FOCUS_AT[stop] || [0.5, 0.5]);
}

let frames = 0, last = performance.now();
function frame(now) {
  const rdt = Math.max(0, (now - last) / 1000); last = now;
  const dt = Math.min(rdt, 0.1);
  clockT += dt;
  const time = clockT;
  if (pendingMove && now - lastPick > 90) { lastPick = now; const [x, y] = pendingMove; pendingMove = null; hoverAt(x, y); }
  adapt(rdt);        // before drawing: a step down resizes the canvas, which clears it, and done after drawing that showed as one black frame
  updateCamera(dt, time); updateItems(dt, time); updateAtmos(dt, time); updateStrange(dt, Math.min(rdt, 0.5));
  if (lens) { updateFocus(dt); lens.render(scene, camera, dt, time); } else renderer.render(scene, camera);
  updateMarks(time);
  frames++;
  if (frames === 2) {
    $('#loading').classList.add('done'); document.body.dataset.ready = '1';
    const mk = () => { grid = buildGrid(staticMeshes); refreshMarks(); };
    if ('requestIdleCallback' in window) requestIdleCallback(mk, { timeout: 1500 }); else setTimeout(mk, 300);
  }
}

// ---------------------------------------------------------------- start
goto(stop, true); updateDial(); syncSound();
if (HASH.slug) { const [g, i] = SLUGS[HASH.slug]; openPanel(g, i, { instant: true }); }
renderer.setAnimationLoop(frame);
document.fonts && document.fonts.ready.then(updateDial);

// ---------------------------------------------------------------- testing hooks
function settle() {
  if (tween) { cam.p.copy(tween.to.p); cam.q.copy(tween.to.q); cam.fov = tween.to.fov; tween = null; arrive(); }
  for (const it of ITEMS) it.t = it.target;
  drift.k = open && open.group === 'door' ? 1 : 0;
  mouse.sx = mouse.x; mouse.sy = mouse.y; pullS = -1;
  if (open && open.item && open.item.motion !== 'sleeve') { const l = lookToward(open.item.lookAt || open.item.center, camera.fov, innerWidth / innerHeight); look.x = l.x; look.y = l.y; } else { look.x = look.y = 0; }
  if (moon.on) moon.a = 1;
  arrivedAt = clockT - 10;
  updateCamera(0, clockT); updateItems(0, clockT);
}
window.__poc = {
  goto: (s) => { closePanel(); goto(s); },
  open: (name, i) => {           // an interactive name ('rec_2', 'door'), a deep-link slug ('post-rain-on-b1'), or (group, index)
    if (SLUGS[name]) { const [g, j] = SLUGS[name]; openPanel(g, j); return; }
    const it = BY[name] || itemFor(name, i);
    if (it) { if (it.stop !== stop) goto(it.stop); if (it.act === 'panel') openPanel(it.group || it.name, it.index); else perform(it); }
    else if (COUNTS[name] !== undefined) openPanel(name, i || 0);
  },
  close: closePanel,
  cat: (name) => setCat(name),
  settle,
  smoke: (t, hold) => { startPuff(); if (CIGAR && t !== undefined) { SM.t = t; SM.hold = !!hold; } },   // jump to a moment of the puff (and stay there)
  skip: (sec) => { clockT += sec; if (SM.on && !SM.hold) SM.t += sec; },     // jump the room's clock forward (slow software-GL screenshots)
  ring: (holdMs) => startRing(holdMs),      // holdMs: keep the line up longer (slow software-GL screenshots)
  moon: (sec) => { moon.need = sec; },
  res: (r) => { perf.locked = true; perf.ratio = r; renderer.setPixelRatio(r); resize(); },
  mouse: (x, y) => { mouse.x = x; mouse.y = y; mouse.last = clockT; },
  hover: (name) => { const it = BY[name]; if (!it) return; pv.copy(it.center).project(camera); hoverAt(((pv.x + 1) / 2) * innerWidth, ((1 - pv.y) / 2) * innerHeight); },
  click: (x, y) => act(open ? null : pick(x, y)),
  info: () => ({
    stop, tween: !!tween, open: open && { group: open.group, index: open.index, slug: open.slug },
    lens: lens ? lens.info() : null, cat: catPose, frames, ratio: perf.ratio, calls: renderer.info.render.calls, tris: renderer.info.render.triangles,
    sound: AU.state(), rang, cigar: CIGAR ? { on: SM.on, t: +SM.t.toFixed(2), puffs: SM.puffs, ash: +SM.ash.toFixed(2), held: +CIGAR.held.toFixed(2) } : null, ringing: ring.on, ringAt: ring.at, moon2: moon.on, moonDwell: +moon.dwell.toFixed(1), missing: MISSING,
    homes: Object.fromEntries(ITEMS.map((x) => [x.name, x.stop])), regions: REGIONS.map((r) => r.stop),
  }),
  dbg: { scene, camera, renderer, ITEMS, STOPS, staticMeshes, grid: () => grid, THREE, lens: () => lens },
};
