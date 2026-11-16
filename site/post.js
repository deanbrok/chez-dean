// THE LENS: everything between the baked room and your screen.
// The room is rendered into an off-screen (half-float, multisampled) buffer, then:
//   1. autofocus      a 1x1 buffer that eases toward the depth under a point on screen (or a distance we set), like a lens hunting
//   2. depth of field half resolution, scatter-as-gather on a golden-angle disc, circle of confusion from real distances
//   3. bloom          a mip chain (down 13 taps, up 9 taps) from the brightest parts: lamp shades, bulbs, valves
//   4. the print      bloom with a warm halation, a little chromatic aberration at the edges, optical vignette,
//                     a gentle film curve and split tone, then grain and dither in display space
// Nothing here knows about the bar. Quality steps down on small or slow devices (setQuality).
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

const DOF_FRAG = /* glsl */`
  ${DEPTH}
  ${COC}
  uniform sampler2D tColor; uniform vec2 uTexel; uniform int uTaps;
  varying vec2 vUv;
  const float GA = 2.39996323;
  void main(){
    float z0 = dist(vUv); float c0 = coc(z0); float r0 = abs(c0);
    vec3 acc = texture2D(tColor, vUv).rgb; float wsum = 1.0;
    float R = uMaxCoc;
    for (int i = 1; i < 48; i++){
      if (i >= uTaps) break;
      float fi = float(i), rad = sqrt(fi / float(uTaps)) * R;
      vec2 o = vec2(cos(fi * GA), sin(fi * GA)) * rad;
      vec2 uv = vUv + o * uTexel;
      float z = dist(uv); float c = abs(coc(z));
      // a sample behind us cannot blur over us further than our own circle
      if (z > z0) c = min(c, r0);
      float w = smoothstep(rad - 1.5, rad + 0.5, c);
      acc += texture2D(tColor, uv).rgb * w; wsum += w;
    }
    gl_FragColor = vec4(acc / wsum, r0 / uMaxCoc);
  }`;

const PREFILTER_FRAG = /* glsl */`
  uniform sampler2D tColor; uniform vec2 uTexel; uniform float uThreshold, uKnee;
  varying vec2 vUv;
  vec3 s(vec2 o){ return texture2D(tColor, vUv + o * uTexel).rgb; }
  vec3 bright(vec3 c){
    // the room arrives tone-mapped (0..1): stretch the top back out so a lamp shade outshines a cream label
    float m = max(c.r, max(c.g, c.b));
    float hdr = 1.0 / max(1.0 - 0.8 * m * m, 0.2);
    float soft = clamp(m - uThreshold + uKnee, 0.0, 2.0 * uKnee); soft = soft * soft / (4.0 * uKnee + 1e-4);
    float w = max(soft, m - uThreshold) / max(m, 1e-4);
    return c * w * hdr;
  }
  void main(){
    vec3 a = bright(s(vec2(-1.0, -1.0))), b = bright(s(vec2(1.0, -1.0))), c = bright(s(vec2(-1.0, 1.0))), d = bright(s(vec2(1.0, 1.0)));
    vec3 e = bright(s(vec2(0.0)));
    gl_FragColor = vec4((a + b + c + d) * 0.125 + e * 0.5, 1.0);
  }`;

const DOWN_FRAG = /* glsl */`
  uniform sampler2D tColor; uniform vec2 uTexel; varying vec2 vUv;
  vec3 s(float x, float y){ return texture2D(tColor, vUv + vec2(x, y) * uTexel).rgb; }
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
  uniform sampler2D tColor, tDof, tBloom; uniform vec2 uRes; uniform float uTime, uBloom, uCA, uVig, uGrain, uExposure, uDof, uMaxCoc, uLift;
  uniform vec3 uShadowTint, uHighTint;
  varying vec2 vUv;
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
    vec2 ca = q * uCA * r2;                                 // lateral chromatic aberration grows toward the corners
    vec3 c = lensSample(tColor, uv, ca);
    if (uDof > 0.5){
      vec4 d = texture2D(tDof, uv);
      float k = smoothstep(0.6, 2.2, d.a * uMaxCoc);
      c = mix(c, lensSample(tDof, uv, ca * 1.5).rgb, k);
    }
    // bloom, with the long tail tinted warm the way film halates around a bulb
    vec3 b = max(texture2D(tBloom, uv).rgb, 0.0);
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
    this.small = small;
    this.q = small ? 1 : 2;               // 2: everything; 1: fewer taps, no MSAA; 0: no depth of field, smaller bloom
    this.levels = 6;
    this.focus = { uv: new THREE.Vector2(0.5, 0.5), dist: 0, speed: 2.2 };
    this.params = {
      aperture: 0.0016,    // circle of confusion (fraction of image height) per dioptre of defocus: a fast lens, stopped down a little
      maxCoc: 9,           // px at full resolution, before the image-height scaling below
      bloom: 0.16, threshold: 0.74, knee: 0.18,
      ca: 0.0035, vig: 0.6, grain: 0.026, exposure: 1.1, lift: 0.0035,
      shadowTint: new THREE.Vector3(0.97, 1.0, 1.04), highTint: new THREE.Vector3(1.035, 1.0, 0.95),
    };
    this.scene = new THREE.Scene();
    this.afPing = [0, 1].map(() => rt(1, 1, this.type, { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter }));
    this.afI = 0; this.afPrimed = false;
    const depthU = () => ({ tDepth: { value: null }, uNear: { value: 0.03 }, uFar: { value: 40 } });
    this.af = pass(AF_FRAG, { ...depthU(), tPrev: { value: null }, uPoint: { value: new THREE.Vector2(0.5, 0.5) }, uLerp: { value: 1 }, uFixed: { value: 0 }, uAspect: { value: 1 } });
    this.dof = pass(DOF_FRAG, { ...depthU(), tFocus: { value: null }, uAperture: { value: 0 }, uMaxCoc: { value: 1 }, uHeight: { value: 1 },
      tColor: { value: null }, uTexel: { value: new THREE.Vector2() }, uTaps: { value: 32 } });
    this.pre = pass(PREFILTER_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() }, uThreshold: { value: 0.6 }, uKnee: { value: 0.2 } });
    this.down = pass(DOWN_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() } });
    this.up = pass(UP_FRAG, { tColor: { value: null }, uTexel: { value: new THREE.Vector2() }, uWeight: { value: 1 } },
      { blending: THREE.AdditiveBlending, transparent: true });
    this.print = pass(PRINT_FRAG, {
      tColor: { value: null }, tDof: { value: null }, tBloom: { value: null }, uRes: { value: new THREE.Vector2() }, uTime: { value: 0 },
      uBloom: { value: 0 }, uCA: { value: 0 }, uVig: { value: 0 }, uGrain: { value: 0 }, uExposure: { value: 1 }, uDof: { value: 1 },
      uMaxCoc: { value: 1 }, uLift: { value: 0 }, uShadowTint: { value: new THREE.Vector3(1, 1, 1) }, uHighTint: { value: new THREE.Vector3(1, 1, 1) },
    });
    this.print.m.toneMapped = false;
    this.w = this.h = 0;
  }

  setSize(w, h, pr) {
    if (!this.ok) return;
    const W = Math.max(2, Math.round(w * pr)), H = Math.max(2, Math.round(h * pr));
    if (W === this.w && H === this.h && this.builtQ === this.q) return;
    this.w = W; this.h = H; this.builtQ = this.q;
    this.dispose(true);
    const samples = this.q >= 2 ? 4 : 0;
    this.main = rt(W, H, this.type, { depthBuffer: true, samples });
    this.main.depthTexture = new THREE.DepthTexture(W, H); this.main.depthTexture.type = THREE.UnsignedIntType;
    this.half = rt(W >> 1, H >> 1, this.type);
    this.mips = [];
    let mw = W >> 1, mh = H >> 1;
    const levels = this.q === 0 ? 4 : this.levels;
    for (let i = 0; i < levels && mw >= 4 && mh >= 4; i++) { this.mips.push(rt(mw, mh, this.type)); mw >>= 1; mh >>= 1; }
  }

  dispose(keepAF) {
    for (const t of [this.main, this.half, ...(this.mips || [])]) if (t) { if (t.depthTexture) t.depthTexture.dispose(); t.dispose(); }
    this.main = this.half = null; this.mips = [];
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
    const W = this.w, H = this.h, hw = this.half.width, hh = this.half.height;
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
    // 3. depth of field at half resolution
    const useDof = this.q >= 1 || this.small;
    if (this.q > 0) {
      const u = this.dof.u;
      u.tDepth.value = depth; u.uNear.value = near; u.uFar.value = far; u.tFocus.value = focusTex;
      u.uAperture.value = P.aperture; u.uHeight.value = H; u.uMaxCoc.value = maxCoc;
      u.tColor.value = this.main.texture; u.uTexel.value.set(1 / W, 1 / H); u.uTaps.value = this.q >= 2 ? 40 : 20;
      this._draw(this.dof, this.half);
    }
    // 4. bloom
    {
      const u = this.pre.u; u.tColor.value = this.main.texture; u.uTexel.value.set(1 / W, 1 / H); u.uThreshold.value = P.threshold; u.uKnee.value = P.knee;
      this._draw(this.pre, this.mips[0]);
      for (let i = 1; i < this.mips.length; i++) {
        const d = this.down.u, s = this.mips[i - 1]; d.tColor.value = s.texture; d.uTexel.value.set(1 / s.width, 1 / s.height);
        this._draw(this.down, this.mips[i]);
      }
      r.autoClear = false;
      for (let i = this.mips.length - 1; i > 0; i--) {
        const s = this.mips[i], u2 = this.up.u; u2.tColor.value = s.texture; u2.uTexel.value.set(1 / s.width, 1 / s.height);
        u2.uWeight.value = i === this.mips.length - 1 ? 1.0 : 0.9;
        this._draw(this.up, this.mips[i - 1]);
      }
      r.autoClear = true;
    }
    // 5. the print, to the screen
    {
      const u = this.print.u;
      u.tColor.value = this.main.texture; u.tDof.value = this.half.texture; u.tBloom.value = this.mips[0].texture;
      u.uRes.value.set(W, H); u.uTime.value = time; u.uBloom.value = P.bloom;
      u.uCA.value = P.ca; u.uVig.value = P.vig; u.uGrain.value = P.grain; u.uExposure.value = P.exposure; u.uLift.value = P.lift;
      u.uDof.value = this.q > 0 && useDof ? 1 : 0; u.uMaxCoc.value = maxCoc;
      u.uShadowTint.value.copy(P.shadowTint); u.uHighTint.value.copy(P.highTint);
      this._draw(this.print, null);
    }
    r.autoClear = auto;
  }

  info() { return { ok: this.ok, q: this.q, w: this.w, h: this.h, focus: this.focus.dist || [+this.focus.uv.x.toFixed(2), +this.focus.uv.y.toFixed(2)] }; }
}
