// Cheap atmosphere: lamp glows, smoke, steam, the night sky behind the window, the cat's contact shadow.
import * as THREE from 'three';

const V = (a) => new THREE.Vector3(a[0], a[1], a[2]);

export function radialTexture(stops) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'); const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  for (const [o, a] of stops) gr.addColorStop(o, `rgba(255,255,255,${a})`);
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
export const glowTex = radialTexture([[0, 1], [0.1, 0.6], [0.3, 0.2], [0.6, 0.05], [1, 0]]);
const softTex = radialTexture([[0, 1], [0.35, 0.55], [0.7, 0.15], [1, 0]]);

export function sprite(color, size, opacity, tex = glowTex) {
  const m = new THREE.SpriteMaterial({ map: tex, color, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity });
  const s = new THREE.Sprite(m); s.scale.setScalar(size); s.renderOrder = 5; return s;
}

// ---------------------------------------------------------------- wisps (smoke from the ashtray, steam from the pot)
const wispFrag = /* glsl */`
  uniform float uTime, uAlpha, uWidth, uCurl; uniform vec3 uColor; varying vec2 vUv;
  float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
  float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++){ s += a*n(p); p *= 2.07; a *= 0.5; } return s; }
  void main(){
    // clamp: at the quad's edges a multisampled vUv.y can land a hair below 0, and pow(negative, 1.1) is NaN.
    // One NaN pixel in the half-float buffer is enough for the lens's bloom chain to spread it into a black box.
    float y = clamp(vUv.y, 0.0, 1.0), t = uTime;
    float sway = (sin(y*5.0 - t*0.7)*0.07 + sin(y*11.0 - t*1.3 + 1.7)*0.03) * smoothstep(0.0, 0.5, y) * uCurl
               + (fbm(vec2(y*1.4 - t*0.09, t*0.04)) - 0.5) * 0.7 * y * uCurl;
    float cx = 0.5 + sway;
    float w = mix(0.012, 0.22, pow(y, 1.1)) * uWidth;
    float d = (vUv.x - cx) / w;
    float strand = exp(-d*d*1.5);
    float br = fbm(vec2((vUv.x - cx)*5.0 + y*1.5, y*3.5 - t*0.28));
    float a = strand * mix(1.0, smoothstep(0.32, 0.78, br)*1.8, smoothstep(0.1, 0.55, y));
    a *= smoothstep(0.0, 0.05, y) * (1.0 - smoothstep(0.35, 0.95, y)) * smoothstep(0.0, 0.12, vUv.x) * smoothstep(1.0, 0.88, vUv.x);
    gl_FragColor = vec4(uColor, a * uAlpha);
    #include <colorspace_fragment>
  }`;
export function wisp(pos, w, h, color, width = 1, curl = 1) {
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    uniforms: { uTime: { value: 0 }, uAlpha: { value: 0.3 }, uWidth: { value: width }, uCurl: { value: curl }, uColor: { value: new THREE.Color(color) } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: wispFrag,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h).translate(0, h / 2, 0), m);
  mesh.position.copy(pos); mesh.renderOrder = 6; mesh.frustumCulled = false;
  return mesh;
}

// ---------------------------------------------------------------- the sky behind the window
// A plane a little outside the wall, facing into the room. Coordinates in the shader are metres on the plane (u along the
// wall, v up), relative to the window's lower-left corner, so everything scales with whatever window the model has.
const skyFrag = /* glsl */`
  uniform float uTime, uMoon2; uniform vec2 uSize, uMoon, uMoonB; uniform float uHorizon, uMoonR;
  varying vec2 vP;
  float h(vec2 p){ return fract(sin(dot(p, vec2(41.3, 289.1))) * 15731.743); }
  float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
  vec3 moon(vec2 p, vec2 c, float r, vec3 col, float phase){
    float d = length(p - c);
    float disc = 1.0 - smoothstep(r * 0.94, r, d);
    // a little shading and a few maria so it reads as a moon, not a lamp
    float m = n((p - c) / r * 2.2 + phase) * 0.5 + n((p - c) / r * 5.0 + phase * 2.0) * 0.25;
    float lit = mix(0.82, 1.0, smoothstep(0.35, 0.65, m));
    float halo = exp(-max(d - r, 0.0) / (r * 1.6)) * 0.35 + exp(-max(d - r, 0.0) / (r * 6.0)) * 0.12;
    return col * (disc * lit + halo * (1.0 - disc));
  }
  void main(){
    vec2 p = vP;                                // metres: x along the wall, y up from the window sill
    float v = p.y / uSize.y;
    float hz = uHorizon;
    float wallMask = 1.0 - smoothstep(hz - 0.015, hz + 0.015, p.y);
    // windows of the building opposite, very soft
    vec2 g = fract(vec2(p.x * 1.6, p.y * 2.2 - 0.2)); float win = smoothstep(0.25, 0.3, g.x) * (1.0 - smoothstep(0.7, 0.75, g.x)) * smoothstep(0.3, 0.36, g.y) * (1.0 - smoothstep(0.8, 0.86, g.y));
    float pave = 1.0 - smoothstep(0.06, 0.09, p.y);                       // pavement at the bottom of the frame
    // deep blue, a few stars, the moon; the wall opposite is a dark silhouette with the odd lit window
    vec3 skyN = mix(vec3(0.035, 0.06, 0.13), vec3(0.012, 0.022, 0.06), smoothstep(0.0, 1.6, v));
    vec2 sc = p * 14.0; vec2 si = floor(sc); vec2 sf = fract(sc) - 0.5;
    float s = h(si); float star = step(0.965, s) * smoothstep(0.08, 0.0, length(sf + (vec2(h(si + 3.1), h(si + 7.7)) - 0.5) * 0.6));
    star *= 0.55 + 0.45 * sin(uTime * (0.6 + s * 2.0) + s * 40.0);
    skyN += vec3(0.85, 0.88, 1.0) * star * 0.9;
    skyN += moon(p, uMoon, uMoonR, vec3(0.93, 0.92, 0.85), 0.0);
    skyN += moon(p, uMoonB, uMoonR * 0.62, vec3(0.74, 0.90, 0.72), 3.7) * uMoon2;
    vec3 wallN = vec3(0.018, 0.022, 0.035) + (n(p * vec2(3.0, 9.0)) - 0.5) * 0.008;
    float lit = step(0.5, h(floor(vec2(p.x * 1.6, p.y * 2.2 - 0.2)) + 11.0)) * step(0.75, h(floor(vec2(p.x * 1.6, p.y * 2.2 - 0.2)) + 2.0));
    wallN = mix(wallN, vec3(0.30, 0.20, 0.09), win * lit * 0.5 * smoothstep(0.0, 0.3, hz - p.y));
    wallN = mix(wallN, vec3(0.03, 0.03, 0.04), pave);
    vec3 night = mix(skyN, wallN, wallMask);
    gl_FragColor = vec4(pow(max(night, 0.0), vec3(2.2)), 1.0);     // authored as display values -> linear
    #include <colorspace_fragment>
  }`;

export function makeSky(win, stops) {
  // win: {x, y0, y1, z0, z1} (three.js). The wall is the plane x = win.x; the room is on the +x side when x < 0.
  const zA = Math.min(win.z0, win.z1), zB = Math.max(win.z0, win.z1), yA = Math.min(win.y0, win.y1), yB = Math.max(win.y0, win.y1);
  const side = win.x < 0 ? -1 : 1;                       // outward direction along x
  const depth = 0.45, margin = 1.6;
  const W = zB - zA, H = yB - yA;
  const px = win.x + side * depth;
  const geo = new THREE.PlaneGeometry(W + margin * 2, H + margin * 2);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 }, uMoon2: { value: 0 }, uSize: { value: new THREE.Vector2(W, H) },
      uMoon: { value: new THREE.Vector2(W * 0.35, H * 0.8) }, uMoonB: { value: new THREE.Vector2(W * 0.5, H * 0.95) },
      uHorizon: { value: H * 0.3 }, uMoonR: { value: Math.min(W, H) * 0.075 },
    },
    vertexShader: /* glsl */`
      uniform vec2 uSize; varying vec2 vP;
      void main(){ vP = position.xy + uSize * 0.5; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: skyFrag,
  });
  const mesh = new THREE.Mesh(geo, mat);
  // plane local x runs along the wall, local y up, facing the room
  mesh.position.set(px, (yA + yB) / 2, (zA + zB) / 2);
  mesh.rotation.y = side < 0 ? Math.PI / 2 : -Math.PI / 2;
  mesh.updateMatrixWorld();
  // local x direction in world: for rotation.y = +90deg local +x -> world -z
  const ux = new THREE.Vector3(1, 0, 0).applyQuaternion(mesh.quaternion);
  const toPlane = (pt) => {      // world point on the plane -> shader coords (metres from lower-left of the window footprint)
    const d = pt.clone().sub(mesh.position);
    return new THREE.Vector2(d.dot(ux) + W / 2, d.y + H / 2);
  };
  const hitFrom = (cam, wp) => {  // ray from cam through world point wp, intersect plane x = px
    const dir = wp.clone().sub(cam); const t = (px - cam.x) / dir.x; return cam.clone().addScaledVector(dir, t);
  };
  // the moon, the horizon of the wall opposite: placed as seen from the window stop, so they sit inside the frame there
  const st = stops.window || stops.bar;
  if (st) {
    const cam = V(st.p);
    const zAt = (f) => { // f=0 at the window end nearest the camera's look direction... just use the far-from-camera side
      const near = Math.abs(cam.z - zA) < Math.abs(cam.z - zB) ? zA : zB, far = near === zA ? zB : zA;
      return near + (far - near) * f;
    };
    const m1 = hitFrom(cam, new THREE.Vector3(win.x, yA + H * 0.66, zAt(0.64)));
    const m2 = hitFrom(cam, new THREE.Vector3(win.x, yA + H * 0.73, zAt(0.47)));
    const hz = hitFrom(cam, new THREE.Vector3(win.x, yA + H * 0.3, zAt(0.5)));
    mat.uniforms.uMoon.value.copy(toPlane(m1));
    mat.uniforms.uMoonB.value.copy(toPlane(m2));
    mat.uniforms.uHorizon.value = toPlane(hz).y;
  }
  mesh.renderOrder = -1;
  return mesh;
}

// ---------------------------------------------------------------- dust hanging in the lamplight
// a few hundred specks that drift and turn; each is only visible near one of the lights (pools: [{p, r, color}])
export function makeDust(pools, count = 360) {
  const pos = new Float32Array(count * 3), seed = new Float32Array(count), pool = new Float32Array(count * 4), col = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    const k = pools[i % pools.length], c = V(k.p);
    // uniform in a sphere of radius r around the light, a little more below it than above (light falls down and out)
    let x, y, z; do { x = Math.random() * 2 - 1; y = Math.random() * 2 - 1; z = Math.random() * 2 - 1; } while (x * x + y * y + z * z > 1);
    pos.set([c.x + x * k.r, c.y + y * k.r * 0.9 - k.r * 0.15, c.z + z * k.r], i * 3);
    pool.set([c.x, c.y, c.z, k.r], i * 4); col.set(k.color, i * 3); seed[i] = Math.random() * 100;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('seed', new THREE.BufferAttribute(seed, 1));
  g.setAttribute('pool', new THREE.BufferAttribute(pool, 4)); g.setAttribute('tint', new THREE.BufferAttribute(col, 3));
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uAlpha: { value: 1 }, uScale: { value: 720 } },
    vertexShader: /* glsl */`
      attribute float seed; attribute vec4 pool; attribute vec3 tint; uniform float uTime, uScale; varying float vA; varying vec3 vC;
      void main(){
        float t = uTime;
        vec3 p = position + vec3(sin(t * 0.071 + seed) * 0.06 + sin(t * 0.23 + seed * 3.1) * 0.012,
                                 sin(t * 0.053 + seed * 1.7) * 0.05 - mod(t * 0.0025 + seed * 0.01, 0.06),
                                 cos(t * 0.067 + seed * 0.6) * 0.06 + cos(t * 0.19 + seed * 2.3) * 0.012);
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        float d = length(p - pool.xyz) / pool.w;
        float lit = exp(-d * d * 3.2);                        // only near the light
        float glint = pow(0.5 + 0.5 * sin(t * (0.4 + fract(seed) * 0.9) + seed * 7.0), 6.0);   // a speck turning to catch it
        vA = lit * (0.3 + 1.4 * glint); vC = tint;
        gl_PointSize = max(1.0, uScale * 0.0034 / -mv.z);
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: /* glsl */`
      uniform float uAlpha; varying float vA; varying vec3 vC;
      void main(){ float d = length(gl_PointCoord - 0.5); float a = smoothstep(0.5, 0.1, d) * vA * uAlpha;
        gl_FragColor = vec4(vC * a, a);
        #include <colorspace_fragment>
      }`,
  });
  const pts = new THREE.Points(g, m); pts.frustumCulled = false; pts.renderOrder = 7;
  return pts;
}

// ---------------------------------------------------------------- a mouthful of smoke, let out slowly
// A few dozen soft billboards. Each one's whole life is worked out in the vertex shader from the moment it was born:
// it leaves the mouth fast, the air stops it, then it hangs, swells, curls and thins. Nothing is simulated per frame.
// Quads, not GL points: near the eye a puff covers a good part of the screen, far beyond the largest point a GPU will draw.
const puffVert = /* glsl */`
  attribute vec4 aStart; attribute vec4 aVel;          // xyz + time of birth ; velocity xyz + a random number per puff
  uniform float uTime, uLife; uniform vec3 uLamp; uniform float uLampR;
  varying vec2 vUv; varying float vA, vSeed, vAge, vLit;
  void main(){
    float age = uTime - aStart.w, rnd = aVel.w;
    float life = uLife * (0.75 + 0.5 * fract(rnd * 7.31));
    float k = clamp(age / life, 0.0, 1.0);
    float a = max(age, 0.0);
    float travel = (1.0 - exp(-a * 2.1)) / 2.1;                         // drag: quick out of the mouth, then it hangs
    vec3 p = aStart.xyz + aVel.xyz * travel;
    p.y += 0.016 * a + 0.0035 * a * a;                                  // warm smoke rises, slowly
    float s = rnd * 6.2831853;
    p += vec3(sin(a * 0.9 + s), sin(a * 0.7 + s * 1.7) * 0.6, cos(a * 0.8 + s * 2.3)) * (0.006 + 0.016 * fract(rnd * 11.3)) * a;   // each goes its own way
    float size = mix(0.014, 0.17, 1.0 - exp(-a * 0.75)) * (0.6 + 0.8 * fract(rnd * 3.7));
    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    float ang = s + a * 0.14 * (fract(rnd * 5.3) - 0.5);
    float c = cos(ang), sn = sin(ang);
    mv.xy += vec2(position.x * c - position.y * sn, position.x * sn + position.y * c) * size;
    vUv = position.xy; vSeed = rnd; vAge = a;
    vA = smoothstep(0.0, 0.035, k) * (1.0 - smoothstep(0.22, 1.0, k));
    vA *= smoothstep(0.05, 0.24, -mv.z);                                // never fog the lens itself
    vec3 dl = p - uLamp; vLit = 0.30 + 0.70 * exp(-dot(dl, dl) / (uLampR * uLampR));   // it brightens as it drifts into the lamplight
    gl_Position = projectionMatrix * mv;
    if (age < 0.0 || k >= 1.0) gl_Position = vec4(2.0, 2.0, 2.0, 1.0); // not born yet, or gone: off screen
  }`;
const puffFrag = /* glsl */`
  uniform vec3 uColor; uniform float uAlpha; varying vec2 vUv; varying float vA, vSeed, vAge, vLit;
  float h(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  float n(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
    return mix(mix(h(i), h(i+vec2(1,0)), f.x), mix(h(i+vec2(0,1)), h(i+vec2(1,1)), f.x), f.y); }
  void main(){
    float fall = 1.0 - smoothstep(0.0, 1.0, length(vUv));              // 1 in the middle, 0 at the edge of the quad
    vec2 q = vUv * 1.3 + vSeed * 31.0;
    vec2 w = vec2(n(q * 1.7 + vAge * 0.13), n(q * 1.7 + 5.2 - vAge * 0.11));        // the noise is bent by slower noise: curls, not blots
    float nz = n(q * 2.2 + w * 1.6) * 0.55 + n(q * 4.6 - w * 2.1 + 3.3) * 0.30 + n(q * 9.0 + w) * 0.15;
    float a = fall * smoothstep(0.44 - 0.26 * fall, 0.80, nz);         // ragged, with holes, thinning to nothing at the edge
    gl_FragColor = vec4(uColor * vLit, clamp(a, 0.0, 1.0) * vA * uAlpha);
    #include <colorspace_fragment>
  }`;
export function makePuff(count = 34, color = 0xe6d8c2) {
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0]), 3));
  g.setIndex([0, 1, 2, 0, 2, 3]);
  const start = new Float32Array(count * 4), vel = new Float32Array(count * 4);
  for (let i = 0; i < count; i++) start[i * 4 + 3] = 1e9;               // nobody has breathed out yet
  const aS = new THREE.InstancedBufferAttribute(start, 4), aV = new THREE.InstancedBufferAttribute(vel, 4);
  aS.setUsage(THREE.DynamicDrawUsage); aV.setUsage(THREE.DynamicDrawUsage);
  g.setAttribute('aStart', aS); g.setAttribute('aVel', aV); g.instanceCount = count;
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: { uTime: { value: 0 }, uLife: { value: 7.0 }, uAlpha: { value: 0.30 }, uColor: { value: new THREE.Color(color) },
      uLamp: { value: new THREE.Vector3(0, 9, 0) }, uLampR: { value: 0.55 } },
    vertexShader: puffVert, fragmentShader: puffFrag,
  });
  const mesh = new THREE.Mesh(g, m); mesh.frustumCulled = false; mesh.renderOrder = 8;
  const d = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3();
  let until = -1;
  // breathe out from `origin` along `dir` (unit), starting at `time`, over `dur` seconds
  mesh.userData.emit = (origin, dir, time, { dur = 1.3, speed = 1.7, spread = 0.17 } = {}) => {
    a.set(0, 1, 0).cross(dir); if (a.lengthSq() < 1e-6) a.set(1, 0, 0); a.normalize(); b.crossVectors(dir, a);
    for (let i = 0; i < count; i++) {
      const u = i / count, an = Math.random() * Math.PI * 2, sp = Math.sqrt(Math.random()) * spread;
      d.copy(dir).addScaledVector(a, Math.cos(an) * sp).addScaledVector(b, Math.sin(an) * sp).normalize()
        .multiplyScalar(speed * (0.55 + 0.75 * Math.random()) * (1 - 0.35 * u));      // the end of a breath has less behind it
      start.set([origin.x + (Math.random() - 0.5) * 0.02, origin.y + (Math.random() - 0.5) * 0.012, origin.z + (Math.random() - 0.5) * 0.02,
        time + u * dur + Math.random() * 0.08], i * 4);
      vel.set([d.x, d.y, d.z, Math.random()], i * 4);
    }
    aS.needsUpdate = true; aV.needsUpdate = true; until = time + dur + m.uniforms.uLife.value * 1.3;
  };
  mesh.userData.active = (time) => time < until;
  mesh.visible = false;
  return mesh;
}

// ---------------------------------------------------------------- a soft contact shadow (for the cat, which is baked without shadows)
const blobTex = radialTexture([[0, 0.85], [0.45, 0.5], [0.8, 0.1], [1, 0]]);
export function blob(box) {
  const s = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const m = new THREE.MeshBasicMaterial({ map: blobTex, color: 0x000000, transparent: true, opacity: 0.55, depthWrite: false });
  // the texture is white; use it as alpha by tinting black and using its luminance as alpha
  m.alphaMap = blobTex; m.map = null;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), m);
  mesh.rotation.x = -Math.PI / 2; mesh.scale.set(s.x * 1.25 + 0.06, s.z * 1.25 + 0.06, 1);
  mesh.position.set(c.x, box.min.y + 0.004, c.z); mesh.renderOrder = 2;
  return mesh;
}
export { softTex };
