// THE LENS: everything between the baked room and your screen.
// The room is rendered into an off-screen (half-float, multisampled) buffer, then:
//   1. autofocus      a 1x1 buffer that eases toward the depth under a point on screen (or a distance we set), like a lens hunting
//   2. the half       the picture at half resolution with each pixel's circle of confusion beside it (from real distances)
//   3. depth of field half resolution, scatter-as-gather on a golden-angle disc, one fetch per tap from the half
//   4. bloom          a mip chain from quarter resolution down (13 taps down, 9 up) of the brightest parts: lamp shades,
//                     bulbs, valves; the sharpest level is not a buffer at all, the print works it out from the half
//   5. the print      bloom with a warm halation, a little chromatic aberration at the edges, optical vignette,
//                     a gentle film curve and split tone, then grain and dither in display space
// Nothing here knows about the bar. Quality steps down on small or slow devices (setQuality).
//
// What it costs (measured on an M1 Pro at 3456x2000, see README "Performance"): the full-resolution work is the room
// itself and the print; everything in between runs on a quarter of the pixels or fewer, and no pass reads the
// full-resolution depth or colour more than once per pixel. Keep it that way: a pass that gathers many taps from a
// full-resolution texture is what made this lens take 14 ms a frame.
import * as THREE from 'three';

const TRI = new THREE.BufferGeometry();
TRI.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
TRI.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 2, 0, 0, 2], 2));
const ORTHO = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const VERT = /* glsl */`varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

const DEPTH = /* glsl */`
  uniform sampler2D tDepth; uniform float uNear, uFar;
  float dist(vec2 uv){ float d = texture2D(tDepth, uv).x; return uNear * uFar / (uFar - d * (uFar - uNear)); }`;

const AF_FRAG = /* glsl */`
  ${DEPTH}
  uniform sampler2D tPrev; uniform vec2 uPoint; uniform float uLerp, uFixed, uAspect;
  varying vec2 vUv;
  void main(){
    float target;
    if (uFixed > 0.0) target = 1.0 / uFixed;
    else {
      // a small cross-shaped metering area; average in 1/distance (what the lens actually moves in)
      float s = 0.0; vec2 r = vec2(0.012 / uAspect, 0.012);
      s += 1.0 / dist(uPoint);
      s += 1.0 / dist(uPoint + vec2(r.x, 0.0)); s += 1.0 / dist(uPoint - vec2(r.x, 0.0));
      s += 1.0 / dist(uPoint + vec2(0.0, r.y)); s += 1.0 / dist(uPoint - vec2(0.0, r.y));
      target = s / 5.0;
    }
    float prev = texture2D(tPrev, vec2(0.5)).x;
    if (!(prev > 0.0 && prev < 1000.0)) prev = target;      // never let a bad value stick (NaN fails every comparison)
    gl_FragColor = vec4(mix(prev, target, uLerp), 0.0, 0.0, 1.0);
  }`;

// circle of confusion in pixels of the full-resolution image
const COC = /* glsl */`
  uniform sampler2D tFocus; uniform float uAperture, uMaxCoc, uHeight;
  float coc(float z){ float f = texture2D(tFocus, vec2(0.5)).x; return clamp(uAperture * uHeight * (1.0 / z - f), -uMaxCoc, uMaxCoc); }`;

// the half: colour (the four pixels under it, averaged) and the signed circle of confusion (+ nearer than focus, - farther)
const HALF_FRAG = /* glsl */`
  ${DEPTH}
  ${COC}
  uniform sampler2D tColor; uniform vec2 uTexel;
  varying vec2 vUv;
  void main(){
    // min(max(c, 0), 64): a NaN compares false both ways, so this also turns a bad pixel into a finite one
    // before the blur or the bloom chain can spread it across the picture
    vec3 c = min(max(texture2D(tColor, vUv).rgb, vec3(0.0)), vec3(64.0));
    gl_FragColor = vec4(c, coc(dist(vUv - 0.5 * uTexel)));
  }`;

// TAPS and the disc (uK: offset x, y in units of the largest circle, and the radius as a fraction of it) come from outside,
// so the loop is a fixed length and nothing in it but one fetch and a little arithmetic
const DOF_FRAG = /* glsl */`
  uniform sampler2D tHalf; uniform vec2 uTexel; uniform float uMaxCoc; uniform vec3 uK[TAPS];
  varying vec2 vUv;
  void main(){
    vec4 h0 = texture2D(tHalf, vUv); float c0 = h0.a, r0 = abs(c0);
    vec3 acc = h0.rgb; float wsum = 1.0;
    for (int i = 1; i < TAPS; i++){
      vec3 k = uK[i]; float rad = k.z * uMaxCoc;
      vec4 s = texture2D(tHalf, vUv + k.xy * uMaxCoc * uTexel);
      float c = abs(s.a);
      // a sample behind us cannot blur over us further than our own circle
      if (s.a < c0) c = min(c, r0);
      float w = smoothstep(rad - 1.5, rad + 0.5, c);
      acc += s.rgb * w; wsum += w;
    }
    gl_FragColor = vec4(acc / wsum, r0 / uMaxCoc);
  }`;

const BRIGHT = /* glsl */`
  uniform float uThreshold, uKnee;
  vec3 bright(vec3 c){
    // the room arrives tone-mapped (0..1): stretch the top back out so a lamp shade outshines a cream label
    float m = max(c.r, max(c.g, c.b));
    float hdr = 1.0 / max(1.0 - 0.8 * m * m, 0.2);
    float soft = clamp(m - uThreshold + uKnee, 0.0, 2.0 * uKnee); soft = soft * soft / (4.0 * uKnee + 1e-4);
    float w = max(soft, m - uThreshold) / max(m, 1e-4);
    return c * w * hdr;
  }`;

// FIRST: the top of the chain reads the half and keeps only what is bright; the rest just halve
const DOWN_FRAG = /* glsl */`
  uniform sampler2D tColor; uniform vec2 uTexel; varying vec2 vUv;
  #ifdef FIRST
  ${BRIGHT}
  vec3 s(float x, float y){ return bright(texture2D(tColor, vUv + vec2(x, y) * uTexel).rgb); }
  #else
  vec3 s(float x, float y){ return texture2D(tColor, vUv + vec2(x, y) * uTexel).rgb; }
  #endif
  void main(){
    vec3 c = s(0.0, 0.0) * 0.125;
    c += (s(-1.0, -1.0) + s(1.0, -1.0) + s(-1.0, 1.0) + s(1.0, 1.0)) * 0.125;
    c += (s(-2.0, -2.0) + s(2.0, -2.0) + s(-2.0, 2.0) + s(2.0, 2.0)) * 0.03125;
    c += (s(0.0, -2.0) + s(0.0, 2.0) + s(-2.0, 0.0) + s(2.0, 0.0)) * 0.0625;
    gl_FragColor = vec4(c, 1.0);
  }`;

const UP_FRAG = /* glsl */`
  uniform sampler2D tColor; uniform vec2 uTexel; uniform float uWeight; varying vec2 vUv;
  vec3 s(float x, float y){ return texture2D(tColor, vUv + vec2(x, y) * uTexel).rgb; }
  void main(){
    vec3 c = s(0.0, 0.0) * 4.0 + (s(-1.0, 0.0) + s(1.0, 0.0) + s(0.0, -1.0) + s(0.0, 1.0)) * 2.0
           + s(-1.0, -1.0) + s(1.0, -1.0) + s(-1.0, 1.0) + s(1.0, 1.0);
    gl_FragColor = vec4(c / 16.0 * uWeight, 1.0);
  }`;

const PRINT_FRAG = /* glsl */`
  uniform sampler2D tColor, tHalf, tDof, tBloom; uniform vec2 uRes; uniform float uTime, uBloom, uBloomTail, uCA, uVig, uGrain, uExposure, uDof, uMaxCoc, uLift;
  uniform vec3 uShadowTint, uHighTint;
  varying vec2 vUv;
  ${BRIGHT}
  float hash(vec2 p){ p = fract(p * vec2(443.897, 441.423)); p += dot(p, p.yx + 19.19); return fract((p.x + p.y) * p.x); }
  vec3 toSRGB(vec3 c){ return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c)); }
  vec3 shoulder(vec3 x){ // linear up to k, then a soft roll-off to 1: room for the bloom without clipping to flat white
    float k = 0.86; vec3 over = max(x - k, 0.0);
    return min(x, vec3(k)) + (1.0 - k) * (1.0 - exp(-over / (1.0 - k)));
  }
  vec3 lensSample(sampler2D t, vec2 uv, vec2 d){
    return vec3(texture2D(t, uv + d).r, texture2D(t, uv).g, texture2D(t, uv - d).b);
  }
  void main(){
    vec2 uv = vUv, q = uv - 0.5; float r2 = dot(q * vec2(uRes.x / uRes.y, 1.0), q * vec2(uRes.x / uRes.y, 1.0));
    // lateral chromatic aberration grows toward the corners; measured against the corner (r2c = 1 there) so a wide
    // window gets the same small fringe as a square one instead of doubled lettering at the sides
    float r2c = dot(q, q) * 2.0;
    vec2 ca = q * uCA * r2c;
    vec3 c = lensSample(tColor, uv, ca);
    if (uDof > 0.5){
      vec4 d = texture2D(tDof, uv);
      float k = smoothstep(0.6, 2.2, d.a * uMaxCoc);
      // where the picture is sharp (most of it, most of the time) the blurred one is not looked at again
      if (k > 0.0) c = mix(c, vec3(texture2D(tDof, uv + ca * 1.5).r, d.g, texture2D(tDof, uv - ca * 1.5).b), k);
    }
    // bloom, with the long tail tinted warm the way film halates around a bulb. Its sharpest level is the bright part
    // of the half-resolution picture, worked out here; the wide levels come up the chain in tBloom
    vec3 b = bright(texture2D(tHalf, uv).rgb) + max(texture2D(tBloom, uv).rgb, 0.0) * uBloomTail;
    c += b * uBloom * vec3(1.0, 0.80, 0.62);
    // exposure, a whisper of black lift (no print is truly black), optical vignette (cos^4-ish)
    c *= uExposure;
    float vig = mix(1.0, pow(max(0.0, 1.0 - r2 * 0.62), 2.2), uVig);
    c *= vig;
    c = c + uLift * (1.0 - c);
    // split tone: cool, slightly green shadows; warm highlights. luminance-preserving-ish
    float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c *= mix(uShadowTint, uHighTint, smoothstep(0.0, 0.35, l));
    // a little less saturation in the deep shadows
    l = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(l), c, mix(0.82, 1.0, smoothstep(0.0, 0.08, l)));
    c = shoulder(max(c, 0.0));
    vec3 s = toSRGB(clamp(c, 0.0, 1.0));
    // grain: luminance noise, two sizes, strongest in the mid-tones; then dither away the banding
    vec2 px = gl_FragCoord.xy;
    float t = floor(uTime * 24.0);
    float g = hash(px + t * 17.0) + hash(floor(px / 2.0) + t * 31.0) - 1.0;
    float L = dot(s, vec3(0.299, 0.587, 0.114));
    s += g * uGrain * (0.35 + 2.2 * L * (1.0 - L));
    s += (hash(px * 1.37 + t) - 0.5) / 255.0;
    gl_FragColor = vec4(s, 1.0);
  }`;

function rt(w, h, type, opts = {}) {
  const t = new THREE.WebGLRenderTarget(Math.max(1, w), Math.max(1, h), {
    type, format: THREE.RGBAFormat, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: false, ...opts,
  });
  t.texture.generateMipmaps = false;
  return t;
}
function pass(frag, uniforms, extra = {}) {
  const m = new THREE.ShaderMaterial({ vertexShader: VERT, fragmentShader: frag, uniforms, depthTest: false, depthWrite: false, ...extra });
  const mesh = new THREE.Mesh(TRI, m); mesh.frustumCulled = false;
  return { m, mesh, u: m.uniforms };
}
// the blur disc: a golden-angle spiral, tap i at radius sqrt(i / n) of the largest circle
const GA = 2.39996323;
function disc(n) {
  const k = [];
  for (let i = 0; i < n; i++) { const r = Math.sqrt(i / n); k.push(new THREE.Vector3(Math.cos(i * GA) * r, Math.sin(i * GA) * r, r)); }
  return k;
}
const TAPS = { 2: 32, 1: 16 };              // depth-of-field taps at each quality
// can this GPU draw into a 4-sample buffer of this format? Make a tiny one and see
function canMultisample(gl, format) {
  try {
    const fb = gl.createFramebuffer(), rb = gl.createRenderbuffer();
    while (gl.getError()) { /* clear */ }
    gl.bindRenderbuffer(gl.RENDERBUFFER, rb); gl.renderbufferStorageMultisample(gl.RENDERBUFFER, 4, format, 4, 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb); gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.RENDERBUFFER, rb);
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE
      && gl.getRenderbufferParameter(gl.RENDERBUFFER, gl.RENDERBUFFER_SAMPLES) >= 2 && gl.getError() === gl.NO_ERROR;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.bindRenderbuffer(gl.RENDERBUFFER, null);
    gl.deleteFramebuffer(fb); gl.deleteRenderbuffer(rb);
    return ok;
  } catch { return false; }
}

export class Lens {
  constructor(renderer, { small = false } = {}) {
    this.r = renderer;
    const gl = renderer.getContext();
    const isGL2 = typeof WebGL2RenderingContext !== 'undefined' && gl instanceof WebGL2RenderingContext;
    const ext = renderer.extensions;
    const half = isGL2 && (ext.has('EXT_color_buffer_float') || ext.has('EXT_color_buffer_half_float'));
    this.ok = !!half;
    if (!this.ok) return;
    this.type = THREE.HalfFloatType;
    // The room's own buffer is the one big thing here, and multisampled it is several times bigger still: storing and
    // resolving it was a third of the old frame. Packed 11/11/10-bit floats (no alpha, which nothing reads) are half
    // the bytes of RGBA16F and keep values above 1 for the bloom; their steps are finer than the 8-bit textures the
    // room is made of. Needs EXT_color_buffer_float; without it, half floats as before.
    // Not every GPU can multisample a float buffer, and what a browser reports about it is not reliable, so try
    // (canMultisample). If the packed format can only be drawn single-sampled here and half floats can be
    // multisampled, antialiasing wins and the half floats stay.
    const canPack = ext.has('EXT_color_buffer_float');
    const msPacked = canPack && canMultisample(gl, gl.R11F_G11F_B10F), msHalf = !msPacked && canMultisample(gl, gl.RGBA16F);
    renderer.resetState();                // the test bound a framebuffer behind three's back
    const packed = canPack && (msPacked || !msHalf);
    this.roomFmt = packed ? { type: THREE.UnsignedInt101111Type, format: THREE.RGBFormat } : {};
    this.msaa = msPacked || msHalf;
    this.small = small;
    this.q = small ? 1 : 2;               // 2: everything; 1: fewer taps, no MSAA; 0: no depth of field, smaller bloom
    this.levels = 5;                      // bloom levels, from quarter resolution down
    this.focus = { uv: new THREE.Vector2(0.5, 0.5), dist: 0, speed: 2.2 };
    this.params = {
      aperture: 0.0016,    // circle of confusion (fraction of image height) per dioptre of defocus: a fast lens, stopped down a little
      maxCoc: 9,           // px at full resolution, before the image-height scaling below
      bloom: 0.16, threshold: 0.74, knee: 0.18,
      ca: 0.0022, vig: 0.6, grain: 0.026, exposure: 1.1, lift: 0.0035,
      shadowTint: new THREE.Vector3(0.97, 1.0, 1.04), highTint: new THREE.Vector3(1.035, 1.0, 0.95),
    };
    this.scene = new THREE.Scene();
    this.afPing = [0, 1].map(() => rt(1, 1, this.type, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter }));
    this.afI = 0; this.afPrimed = false;
    const depthU = () => ({ tDepth: { value: null }, uNear: { value: 0.03 }, uFar: { value: 40 } });
    const brightU = () => ({ uThreshold: { value: 0.6 }, uKnee: { value: 0.2 } });
    this.af = pass(AF_FRAG, { ...depthU(), tPrev: { value: null }, uPoint: { value: new THREE.Vector2(0.5, 0.5) }, uLerp: { value: 1 }, uFixed: { value: 0 }, uAspect: { value: 1 } });
    this.halve = pass(HALF_FRAG, { ...depthU(), tFocus: { value: null }, uAperture: { value: 0 }, uMaxCoc: { value: 1 }, uHeight: { value: 1 },
      tColor: { value: null }, uTexel: { value: new THREE.Vector2() } });
    this.dofs = {};                       // one blur per tap count, compiled the first time it is wanted
    this.down0 = pass(DOWN_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() }, ...brightU() }, { defines: { FIRST: 1 } });
    this.down = pass(DOWN_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() } });
    this.up = pass(UP_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() }, uWeight: { value: 1 } },
      { blending: THREE.AdditiveBlending, transparent: true });
    this.print = pass(PRINT_FRAG, {
      tColor: { value: null }, tHalf: { value: null }, tDof: { value: null }, tBloom: { value: null }, uRes: { value: new THREE.Vector2() }, uTime: { value: 0 },
      uBloom: { value: 0 }, uBloomTail: { value: 0.9 }, ...brightU(), uCA: { value: 0 }, uVig: { value: 0 }, uGrain: { value: 0 }, uExposure: { value: 1 }, uDof: { value: 1 },
      uMaxCoc: { value: 1 }, uLift: { value: 0 }, uShadowTint: { value: new THREE.Vector3(1, 1, 1) }, uHighTint: { value: new THREE.Vector3(1, 1, 1) },
    });
    this.print.m.toneMapped = false;
    this.w = this.h = 0;
  }

  _dof(taps) {
    return this.dofs[taps] || (this.dofs[taps] = pass(DOF_FRAG, { tHalf: { value: null }, uTexel: { value: new THREE.Vector2() }, uMaxCoc: { value: 1 }, uK: { value: disc(taps) } },
      { defines: { TAPS: taps } }));
  }

  setSize(w, h, pr) {
    if (!this.ok) return;
    const W = Math.max(2, Math.round(w * pr)), H = Math.max(2, Math.round(h * pr));
    if (W === this.w && H === this.h && this.builtQ === this.q) return;
    this.w = W; this.h = H; this.builtQ = this.q;
    this.dispose(true);
    // on a dense screen every CSS pixel is already four of ours: two samples each there, four on an ordinary one
    const samples = this.q >= 2 && this.msaa ? (pr >= 1.5 ? 2 : 4) : 0;
    this.main = rt(W, H, this.type, { depthBuffer: true, samples, ...this.roomFmt });
    this.main.depthTexture = new THREE.DepthTexture(W, H); this.main.depthTexture.type = THREE.UnsignedIntType;
    const hw = W >> 1, hh = H >> 1;
    this.half = rt(hw, hh, this.type);                             // colour + circle of confusion
    this.blur = this.q > 0 ? rt(hw, hh, this.type) : null;         // the half, out of focus
    this.mips = [];
    let mw = hw >> 1, mh = hh >> 1;
    const levels = this.q === 0 ? 3 : this.levels;
    for (let i = 0; i < levels && mw >= 2 && mh >= 2; i++) { this.mips.push(rt(mw, mh, this.type)); mw >>= 1; mh >>= 1; }
  }

  dispose(keepAF) {
    for (const t of [this.main, this.half, this.blur, ...(this.mips || [])]) if (t) { if (t.depthTexture) t.depthTexture.dispose(); t.dispose(); }
    this.main = this.half = this.blur = null; this.mips = [];
    if (!keepAF) for (const t of this.afPing) t.dispose();
  }

  setQuality(q) { if (!this.ok || q === this.q) return; this.q = q; this.w = 0; }

  // where to focus: a point on screen (0..1, y up) for the autofocus to meter, or a distance in metres
  focusOn(uv) { this.focus.dist = 0; this.focus.uv.set(uv[0], uv[1]); }
  focusAt(d) { this.focus.dist = d; }

  _draw(p, target) { this.r.setRenderTarget(target); this.r.render(p.mesh, ORTHO); }

  render(scene, camera, dt, time) {
    const r = this.r, P = this.params;
    if (!this.main) { const s = r.getSize(new THREE.Vector2()); this.setSize(s.x, s.y, r.getPixelRatio()); }
    // a canvas a few pixels across (a hidden pane, a tab still laying out) has no room for the bloom chain: draw the bare room
    if (!this.mips.length) { r.setRenderTarget(null); r.render(scene, camera); return; }
    const W = this.w, H = this.h;
    const auto = r.autoClear; r.autoClear = true;
    // 1. the room
    r.setRenderTarget(this.main); r.clear(); r.render(scene, camera);
    const depth = this.main.depthTexture, near = camera.near, far = camera.far;
    // 2. autofocus: ~0.4 s to settle; snaps on the first frame
    {
      const u = this.af.u, src = this.afPing[this.afI], dst = this.afPing[1 - this.afI];
      u.tDepth.value = depth; u.uNear.value = near; u.uFar.value = far; u.tPrev.value = src.texture;
      u.uPoint.value.copy(this.focus.uv); u.uFixed.value = this.focus.dist; u.uAspect.value = W / H;
      u.uLerp.value = this.afPrimed ? 1 - Math.exp(-dt * this.focus.speed * 2.5) : 1;
      this._draw(this.af, dst); this.afI = 1 - this.afI; this.afPrimed = true;
    }
    const focusTex = this.afPing[this.afI].texture;
    const scaleH = H / 1080;                       // keep the look the same at any resolution
    const maxCoc = Math.max(2, P.maxCoc * Math.max(scaleH, 0.5));
    // 3. the half: the only pass besides the print that reads the full-resolution picture, and the only one that reads its depth
    {
      const u = this.halve.u;
      u.tDepth.value = depth; u.uNear.value = near; u.uFar.value = far; u.tFocus.value = focusTex;
      u.uAperture.value = P.aperture; u.uHeight.value = H; u.uMaxCoc.value = maxCoc;
      u.tColor.value = this.main.texture; u.uTexel.value.set(1 / W, 1 / H);
      this._draw(this.halve, this.half);
    }
    // 4. depth of field, at half resolution
    const useDof = this.q > 0;
    if (useDof) {
      const dof = this._dof(TAPS[this.q] || TAPS[1]), u = dof.u;
      u.tHalf.value = this.half.texture; u.uTexel.value.set(1 / W, 1 / H); u.uMaxCoc.value = maxCoc;
      this._draw(dof, this.blur);
    }
    // 5. bloom: bright parts of the half, down the chain and back up to quarter resolution
    {
      const n = this.mips.length;
      for (let i = 0; i < n; i++) {
        const p = i === 0 ? this.down0 : this.down, s = i === 0 ? this.half : this.mips[i - 1];
        p.u.tColor.value = s.texture; p.u.uTexel.value.set(1 / s.width, 1 / s.height);
        if (i === 0) { p.u.uThreshold.value = P.threshold; p.u.uKnee.value = P.knee; }
        this._draw(p, this.mips[i]);
      }
      r.autoClear = false;
      for (let i = n - 1; i > 0; i--) {
        const s = this.mips[i], u2 = this.up.u; u2.tColor.value = s.texture; u2.uTexel.value.set(1 / s.width, 1 / s.height);
        u2.uWeight.value = i === n - 1 ? 1.0 : 0.9;
        this._draw(this.up, this.mips[i - 1]);
      }
      r.autoClear = true;
    }
    // 6. the print, to the screen
    {
      const u = this.print.u;
      u.tColor.value = this.main.texture; u.tHalf.value = this.half.texture; u.tDof.value = useDof ? this.blur.texture : null; u.tBloom.value = this.mips[0].texture;
      u.uRes.value.set(W, H); u.uTime.value = time; u.uBloom.value = P.bloom; u.uBloomTail.value = this.mips.length > 1 ? 0.9 : 1.0;
      u.uThreshold.value = P.threshold; u.uKnee.value = P.knee;
      u.uCA.value = P.ca; u.uVig.value = P.vig; u.uGrain.value = P.grain; u.uExposure.value = P.exposure; u.uLift.value = P.lift;
      u.uDof.value = useDof ? 1 : 0; u.uMaxCoc.value = maxCoc;
      u.uShadowTint.value.copy(P.shadowTint); u.uHighTint.value.copy(P.highTint);
      this._draw(this.print, null);
    }
    r.autoClear = auto;
  }

  info() { return { ok: this.ok, q: this.q, w: this.w, h: this.h, samples: this.main ? this.main.samples : 0, packed: !!this.roomFmt.format, focus: this.focus.dist || [+this.focus.uv.x.toFixed(2), +this.focus.uv.y.toFixed(2)] }; }
}
