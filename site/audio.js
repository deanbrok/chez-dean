// All sound is synthesised here with WebAudio; nothing is downloaded. Everything is OFF until the visitor asks.
// music: vinyl crackle + a slow, quiet piano-trio-ish loop (soft chords, a walking sine bass, brushed noise)
// radio: very quiet rain and, now and then, a distant train
// one-shots: a piano chord, the telephone bell

const A = { ctx: null, master: null, music: null, radio: null, fx: null, musicOn: false, radioOn: false, timer: 0, next: 0, beat: 0, trainAt: 0, noise: null };

function ctx() {
  if (A.ctx) return A.ctx;
  const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return null;
  const c = new AC(); A.ctx = c;
  A.master = c.createGain(); A.master.gain.value = 0.8;
  const comp = c.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 3;
  A.master.connect(comp); comp.connect(c.destination);
  // a small room: two short feedback delays, darkened
  const verbIn = c.createGain(); verbIn.gain.value = 0.22;
  const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2400;
  for (const [t, fb] of [[0.043, 0.42], [0.071, 0.38], [0.113, 0.3]]) {
    const d = c.createDelay(0.5); d.delayTime.value = t; const g = c.createGain(); g.gain.value = fb;
    verbIn.connect(d); d.connect(g); g.connect(d); g.connect(lp);
  }
  lp.connect(A.master); A.verb = verbIn;
  A.music = c.createGain(); A.music.gain.value = 0; A.music.connect(A.master); A.music.connect(verbIn);
  A.radio = c.createGain(); A.radio.gain.value = 0; A.radio.connect(A.master);
  A.fx = c.createGain(); A.fx.gain.value = 0.9; A.fx.connect(A.master); A.fx.connect(verbIn);
  // shared noise buffer
  const len = c.sampleRate * 4, nb = c.createBuffer(1, len, c.sampleRate), d = nb.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  A.noise = nb;
  buildCrackle(); buildRain();
  A.timer = setInterval(tick, 120);
  return c;
}

function noiseSrc(loop = true) { const s = A.ctx.createBufferSource(); s.buffer = A.noise; s.loop = loop; s.loopStart = 0; return s; }

function buildCrackle() {
  const c = A.ctx, sr = c.sampleRate, len = sr * 6, buf = c.createBuffer(1, len, sr), d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * 0.01;
  for (let n = 0; n < 170; n++) {        // ticks and pops
    const at = Math.floor(Math.random() * (len - 600)), amp = Math.pow(Math.random(), 3) * 0.7 + 0.03, dec = 12 + Math.random() * 90;
    for (let i = 0; i < 400; i++) d[at + i] += (Math.random() * 2 - 1) * amp * Math.exp(-i / dec);
  }
  const s = c.createBufferSource(); s.buffer = buf; s.loop = true;
  const hp = c.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 700;
  const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 7000;
  const g = c.createGain(); g.gain.value = 0.28;
  s.connect(hp); hp.connect(lp); lp.connect(g); g.connect(A.music); s.start();
  // the rumble of a turntable, very low
  const r = noiseSrc(); const rl = c.createBiquadFilter(); rl.type = 'lowpass'; rl.frequency.value = 70;
  const rg = c.createGain(); rg.gain.value = 0.05; r.connect(rl); rl.connect(rg); rg.connect(A.music); r.start();
}

function buildRain() {
  const c = A.ctx;
  const s = noiseSrc(); const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1400; bp.Q.value = 0.4;
  const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3200;
  const g = c.createGain(); g.gain.value = 0.10;
  const lfo = c.createOscillator(); lfo.frequency.value = 0.07; const lg = c.createGain(); lg.gain.value = 0.03; lfo.connect(lg); lg.connect(g.gain); lfo.start();
  s.connect(bp); bp.connect(lp); lp.connect(g); g.connect(A.radio); s.start();
  // drips on the window sill
  const sr = c.sampleRate, len = sr * 5, buf = c.createBuffer(1, len, sr), d = buf.getChannelData(0);
  for (let n = 0; n < 60; n++) {
    const at = Math.floor(Math.random() * (len - 2000)), f = 1800 + Math.random() * 2400, amp = 0.04 + Math.random() * 0.08;
    for (let i = 0; i < 1500; i++) d[at + i] += Math.sin(i / sr * f * 6.283 * (1 - i / 6000)) * amp * Math.exp(-i / 220);
  }
  const ds = c.createBufferSource(); ds.buffer = buf; ds.loop = true;
  const dg = c.createGain(); dg.gain.value = 0.5; ds.connect(dg); dg.connect(A.radio); ds.start();
  A.trainAt = c.currentTime + 12 + Math.random() * 20;
}

function train(t0) {
  const c = A.ctx, dur = 18;
  const s = noiseSrc(); const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 110;
  const g = c.createGain(); g.gain.setValueAtTime(0, t0); g.gain.linearRampToValueAtTime(0.5, t0 + 7); g.gain.linearRampToValueAtTime(0, t0 + dur);
  s.connect(lp); lp.connect(g); g.connect(A.radio); s.start(t0); s.stop(t0 + dur + 0.1);
  // wheels over rail joints: pairs of soft knocks, far away
  for (let t = t0 + 3; t < t0 + dur - 3; t += 0.95) {
    for (const dt of [0, 0.16]) {
      const k = noiseSrc(false); const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 260; bp.Q.value = 2;
      const kg = c.createGain(); const env = Math.sin(Math.PI * (t - t0) / dur) * 0.22;
      kg.gain.setValueAtTime(0, t + dt); kg.gain.linearRampToValueAtTime(env, t + dt + 0.01); kg.gain.exponentialRampToValueAtTime(0.0001, t + dt + 0.12);
      k.connect(bp); bp.connect(kg); kg.connect(A.radio); k.start(t + dt, Math.random() * 3); k.stop(t + dt + 0.15);
    }
  }
}

// ---- the trio: 66 bpm, swung; Dm9 G13 Cmaj9 A7b13, then Fmaj9 E7#9 Am9 D9 (all soft)
const BPM = 66, BEAT = 60 / BPM;
const CHORDS = [
  { n: [53, 57, 60, 64], b: [38, 41, 45, 43] }, { n: [53, 59, 64, 69], b: [43, 47, 50, 49] },
  { n: [52, 55, 59, 62], b: [48, 47, 45, 43] }, { n: [55, 61, 65, 69], b: [45, 44, 43, 40] },
  { n: [52, 57, 60, 67], b: [41, 45, 48, 47] }, { n: [56, 62, 67, 68], b: [40, 44, 47, 45] },
  { n: [55, 60, 64, 71], b: [45, 43, 41, 40] }, { n: [54, 60, 64, 66], b: [38, 42, 45, 44] },
];
const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);

function padChord(t, notes, dur) {
  const c = A.ctx;
  const bus = c.createGain(); bus.gain.value = 1; const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 1500;
  bus.connect(lp); lp.connect(A.music);
  notes.forEach((m, i) => {
    const at = t + i * 0.035 + Math.random() * 0.02;
    for (const [type, mul, amp] of [['triangle', 1, 0.028], ['sine', 2, 0.008]]) {
      const o = c.createOscillator(); o.type = type; o.frequency.value = hz(m) * mul; o.detune.value = (Math.random() - 0.5) * 8;
      const g = c.createGain();
      g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(amp, at + 0.02); g.gain.exponentialRampToValueAtTime(amp * 0.35, at + 0.9);
      g.gain.setTargetAtTime(0, at + dur * 0.8, 0.5);
      o.connect(g); g.connect(bus); o.start(at); o.stop(at + dur + 2.5);
    }
  });
}
function bass(t, m) {
  const c = A.ctx, o = c.createOscillator(); o.type = 'sine'; o.frequency.value = hz(m);
  const g = c.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.09, t + 0.02); g.gain.exponentialRampToValueAtTime(0.02, t + BEAT * 0.9);
  g.gain.linearRampToValueAtTime(0, t + BEAT * 0.98);
  o.connect(g); g.connect(A.music); o.start(t); o.stop(t + BEAT + 0.05);
}
function brush(t, len, amp) {
  const c = A.ctx, s = noiseSrc(false);
  const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 4200; bp.Q.value = 0.6;
  const g = c.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(amp, t + len * 0.45); g.gain.linearRampToValueAtTime(0, t + len);
  s.connect(bp); bp.connect(g); g.connect(A.music); s.start(t, Math.random() * 3); s.stop(t + len + 0.02);
}

function tick() {
  const c = A.ctx; if (!c) return;
  const now = c.currentTime;
  if (A.musicOn) {
    if (A.next < now) { A.next = now + 0.1; A.beat = 0; }
    while (A.next < now + 0.6) {
      const t = A.next, bar = Math.floor(A.beat / 4), b = A.beat % 4, ch = CHORDS[bar % CHORDS.length];
      if (b === 0) padChord(t, ch.n, BEAT * 3.6);
      if (b === 2 && Math.random() < 0.35) padChord(t + BEAT * 0.66, ch.n.slice(1), BEAT * 1.2);   // a soft comp on the and-of-three
      bass(t, ch.b[b]);
      brush(t, BEAT * 0.62, b % 2 ? 0.035 : 0.022);                       // sweep
      if (b % 2) brush(t + BEAT * 0.66, 0.07, 0.03);                       // swung tap
      A.next += BEAT; A.beat++;
    }
  }
  if (A.radioOn && now > A.trainAt) { train(now + 0.1); A.trainAt = now + 50 + Math.random() * 40; }
}

function fade(g, v, tc = 0.6) { const t = A.ctx.currentTime; g.gain.cancelScheduledValues(t); g.gain.setTargetAtTime(v, t, tc); }

export function setMusic(on) {
  if (on && !ctx()) return false;
  if (!A.ctx) return false;
  A.ctx.resume();
  A.musicOn = on; fade(A.music, on ? 0.55 : 0, on ? 0.8 : 0.3);
  if (on) A.next = 0;
  return on;
}
export function setRadio(on) {
  if (on && !ctx()) return false;
  if (!A.ctx) return false;
  A.ctx.resume();
  A.radioOn = on; fade(A.radio, on ? 0.35 : 0, on ? 1.5 : 0.4);
  return on;
}
export const soundOn = () => !!A.ctx && (A.musicOn || A.radioOn);
export const state = () => ({ music: A.musicOn, radio: A.radioOn, ctx: !!A.ctx });

// one soft chord that does not quite resolve
export function pianoChord() {
  if (!soundOn()) return;
  const c = A.ctx, t = c.currentTime + 0.03;
  const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 2600; lp.connect(A.fx);
  [50, 55, 60, 64, 69].forEach((m, i) => {
    const at = t + i * 0.028;
    for (const [mul, amp] of [[1, 0.06], [2.003, 0.022], [3.01, 0.008]]) {
      const o = c.createOscillator(); o.type = 'sine'; o.frequency.value = hz(m) * mul;
      const g = c.createGain(); g.gain.setValueAtTime(0, at); g.gain.linearRampToValueAtTime(amp, at + 0.006);
      g.gain.exponentialRampToValueAtTime(amp * 0.25, at + 0.7); g.gain.exponentialRampToValueAtTime(0.0001, at + 4.2);
      o.connect(g); g.connect(lp); o.start(at); o.stop(at + 4.3);
    }
  });
}

// the cigar: a draw (air through the leaf, the foot crackling) and the long breath out
export function breath(kind) {
  if (!soundOn()) return;
  const c = A.ctx, t = c.currentTime + 0.02, inn = kind === 'in', dur = inn ? 1.5 : 2.6, peak = inn ? 0.030 : 0.045;
  const s = noiseSrc(), f = c.createBiquadFilter(), g = c.createGain();
  f.type = 'bandpass'; f.Q.value = 0.8;
  f.frequency.setValueAtTime(inn ? 2400 : 950, t); f.frequency.linearRampToValueAtTime(inn ? 3300 : 520, t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(peak, t + dur * 0.25);
  g.gain.linearRampToValueAtTime(peak * 0.7, t + dur * 0.7); g.gain.linearRampToValueAtTime(0, t + dur);
  s.connect(f); f.connect(g); g.connect(A.fx); s.start(t, Math.random() * 2); s.stop(t + dur + 0.05);
  if (!inn) return;
  const hp = c.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 3500; hp.connect(A.fx);
  for (let i = 0; i < 9; i++) {                         // the leaf catching
    const at = t + 0.25 + Math.random() * 1.1, k = noiseSrc(false), kg = c.createGain();
    kg.gain.setValueAtTime(0.02 + Math.random() * 0.035, at); kg.gain.exponentialRampToValueAtTime(0.0001, at + 0.012);
    k.connect(kg); kg.connect(hp); k.start(at, Math.random() * 3, 0.02);
  }
}

// two short bursts of an old telephone bell
export function phoneBell() {
  if (!soundOn()) return;
  const c = A.ctx, t0 = c.currentTime + 0.05;
  const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3000;
  const out = c.createGain(); out.gain.value = 0.5; lp.connect(out); out.connect(A.fx);
  for (const start of [t0, t0 + 1.35]) {
    const dur = 0.85;
    const env = c.createGain(); env.gain.setValueAtTime(0, start); env.gain.linearRampToValueAtTime(1, start + 0.02);
    env.gain.setValueAtTime(1, start + dur - 0.06); env.gain.linearRampToValueAtTime(0, start + dur + 0.25);
    const trem = c.createGain(); trem.gain.value = 0.5;
    const lfo = c.createOscillator(); lfo.type = 'square'; lfo.frequency.value = 17; const lg = c.createGain(); lg.gain.value = 0.5;
    lfo.connect(lg); lg.connect(trem.gain);
    for (const [f, a] of [[1180, 0.05], [1475, 0.04], [2860, 0.012]]) {
      const o = c.createOscillator(); o.type = 'sine'; o.frequency.value = f;
      const g = c.createGain(); g.gain.value = a; o.connect(g); g.connect(trem); o.start(start); o.stop(start + dur + 0.4);
    }
    trem.connect(env); env.connect(lp); lfo.start(start); lfo.stop(start + dur + 0.4);
  }
}
