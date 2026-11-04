/* =====================================================================
   Letter A — 3D Garden (the "7D" page) for the Playgroup games site.
   Real Blender models (built on Kaggle) loaded as glTF:
     garden.glb · letterA.glb [Wiggle] · ant.glb [Walk, Wave]
     apple.glb [Bounce] · axe.glb [NoNo]
   Touch an object and it performs + sings the owner's own recorded
   line in the decided female-teacher voice (audio3d/*-female.mp3).
   Dimensions: 3D scene · orbit drag/zoom · gyro "Move Phone" camera ·
   gentle vibration on tap · background music (WebAudio, ducks under
   the lines) · a real WebXR AR attempt with a kind fallback note.
   ===================================================================== */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

window.__page3dBooted = true;
clearTimeout(window.__page3dWatchdog);

/* ---------------- Toast ---------------- */
const toastEl = document.getElementById('toast');
let toastTimer = null;
function toast(msg, ms = 3400){
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
}

/* ---------------- Music + jingles (WebAudio, same recipe as the games) --- */
const Music = {
  ctx: null, master: null, sfxGain: null, on: true, timer: null, step: 0,
  NOTES: [329.6, 392.0, 440.0, 392.0, 329.6, 293.7, 261.6, 293.7], // E G A G E D C D
  ensure(){
    if (this.ctx){ if (this.ctx.state === 'suspended') this.ctx.resume(); return; }
    try {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
      this.master = this.ctx.createGain(); this.master.gain.value = 0.0;
      this.master.connect(this.ctx.destination);
      this.sfxGain = this.ctx.createGain(); this.sfxGain.gain.value = 0.16;
      this.sfxGain.connect(this.ctx.destination);
      this.master.gain.linearRampToValueAtTime(this.on ? 0.05 : 0.0, this.ctx.currentTime + 1.2);
      this.timer = setInterval(() => this.tick(), 460);
    } catch(e){ /* music is a bonus, never a blocker */ }
  },
  tick(){
    if (!this.ctx || !this.on) return;
    const t = this.ctx.currentTime;
    const f = this.NOTES[this.step % this.NOTES.length];
    this.tone(f, t, 0.42, 'triangle', 0.5, this.master);
    if (this.step % 4 === 0) this.tone(130.8, t, 0.9, 'sine', 0.35, this.master); // soft C bass pad
    this.step++;
  },
  tone(freq, t, dur, type, vol, dest){
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + 0.04);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(dest); o.start(t); o.stop(t + dur + 0.05);
  },
  duck(on){
    if (!this.ctx || !this.master) return;
    const target = this.on ? (on ? 0.015 : 0.05) : 0.0;
    this.master.gain.cancelScheduledValues(this.ctx.currentTime);
    this.master.gain.linearRampToValueAtTime(target, this.ctx.currentTime + 0.25);
  },
  setOn(on){
    this.on = on;
    if (this.ctx && this.master){
      this.master.gain.cancelScheduledValues(this.ctx.currentTime);
      this.master.gain.linearRampToValueAtTime(on ? 0.05 : 0.0, this.ctx.currentTime + 0.3);
    }
  },
  jingle(){ /* the letter A's happy little song */
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    [523.3, 659.3, 783.0, 1046.5].forEach((f, i) => this.tone(f, t + i * 0.11, 0.34, 'triangle', 0.5, this.sfxGain));
  }
};
window.addEventListener('pointerdown', () => Music.ensure());
const tglMusic = document.getElementById('tglMusic');
tglMusic.addEventListener('click', () => {
  Music.ensure();
  Music.setOn(!Music.on);
  tglMusic.textContent = Music.on ? '🎵' : '🔇';
  tglMusic.classList.toggle('off', !Music.on);
});

/* ---------------- The recorded lines (female-teacher voice) ---------------- */
const LINES = {
  ant:   new Audio('audio3d/line-ant-female.mp3'),
  apple: new Audio('audio3d/line-apple-female.mp3'),
  axe:   new Audio('audio3d/line-axe-female.mp3')
};
for (const k in LINES){ LINES[k].preload = 'auto'; }
let linePlaying = null;          /* name of the line currently singing, or null */
let lastLine = null;             /* {name, src, at} — for verification */
let lineWatchdog = null;
function endLine(){
  linePlaying = null;
  clearTimeout(lineWatchdog);
  Music.duck(false);
}
function playLine(name){
  const a = LINES[name];
  if (!a || linePlaying) return false;
  linePlaying = name;
  lastLine = { name, src: a.getAttribute('src') || a.src, at: Date.now() };
  Music.ensure();
  Music.duck(true);
  try { a.currentTime = 0; } catch(e){}
  a.addEventListener('ended', endLine, { once: true });
  const p = a.play();
  if (p && p.catch) p.catch(() => endLine());
  /* safety: never stay locked if 'ended' is missed */
  const dur = (isFinite(a.duration) && a.duration > 0) ? a.duration : 8;
  lineWatchdog = setTimeout(endLine, (dur + 1.5) * 1000);
  return true;
}

/* ---------------- Renderer / scene ---------------- */
const canvas = document.getElementById('scene');
let renderer = null;
try { renderer = new THREE.WebGLRenderer({ canvas, antialias: true }); } catch(e){ renderer = null; }
if (!renderer){
  document.getElementById('nogl').style.display = 'flex';
  document.getElementById('loading').classList.add('gone');
  throw new Error('WebGL unavailable');
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.06;
renderer.xr.enabled = true;    /* the Magic Camera attempt is real */

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xAEE0F2);
scene.fog = new THREE.Fog(0xAEE0F2, 26, 52);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 140);
const CAM_HOME = new THREE.Vector3(7.4, 5.6, 10.6);
const TGT_HOME = new THREE.Vector3(0, 0.5, 0);
/* portrait phones see a narrower slice — pull the home view back a bit */
function homePos(){
  const a = window.innerWidth / Math.max(1, window.innerHeight);
  const s = a < 0.75 ? 1.5 : a < 1.1 ? 1.22 : 1;
  return CAM_HOME.clone().multiplyScalar(s);
}
camera.position.copy(homePos());

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(TGT_HOME);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.minDistance = 3.5;
controls.maxDistance = 24;
controls.maxPolarAngle = 1.38;
controls.minPolarAngle = 0.15;
controls.enablePan = false;

/* Lights — soft daylight, ONE shadow-casting sun */
scene.add(new THREE.HemisphereLight(0xD8F1FF, 0x79B364, 0.95));
const sun = new THREE.DirectionalLight(0xFFF1D6, 1.9);
sun.position.set(8, 12, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -9; sun.shadow.camera.right = 9;
sun.shadow.camera.top = 9; sun.shadow.camera.bottom = -9;
sun.shadow.camera.far = 34;
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.02;
scene.add(sun);

/* Everything 3D lives in `world` so AR can shrink it onto a table */
const world = new THREE.Group();
scene.add(world);

/* ---------------- Loading the Blender models ---------------- */
const barEl = document.getElementById('bar');
const pctEl = document.getElementById('pct');
const manager = new THREE.LoadingManager();
manager.onProgress = (url, done, total) => {
  const pc = Math.round((done / total) * 100);
  barEl.style.width = pc + '%';
  pctEl.textContent = pc + '%';
};
const loader = new GLTFLoader(manager);
const MODELS = {};              /* name -> {root, inner, mixer, actions, restoreAt, restoreClip} */
let loaded = false;
let lastAnim = null;

function prepShadows(root, cast, receive){
  root.traverse(o => { if (o.isMesh){ o.castShadow = cast; o.receiveShadow = receive; } });
}
function registerModel(name, gltf, opts = {}){
  const root = new THREE.Group();
  root.name = name + 'Root';
  root.add(gltf.scene);
  if (opts.scale) root.scale.setScalar(opts.scale);
  if (opts.pos) root.position.set(...opts.pos);
  if (opts.rotY) root.rotation.y = opts.rotY;
  world.add(root);
  const entry = { root, inner: gltf.scene, mixer: null, actions: {}, restoreAt: 0, restoreClip: null };
  if (gltf.animations && gltf.animations.length){
    entry.mixer = new THREE.AnimationMixer(gltf.scene);
    for (const clip of gltf.animations){
      entry.actions[clip.name] = entry.mixer.clipAction(clip);
    }
  }
  MODELS[name] = entry;
  return entry;
}
/* Play a one-shot clip, then return the model to its rest pose. */
function playOnce(entry, clipName){
  const a = entry.actions[clipName];
  if (!a) return false;
  a.stop();
  a.reset();
  a.setLoop(THREE.LoopOnce, 1);
  a.clampWhenFinished = true;
  a.enabled = true;
  a.setEffectiveWeight(1);
  a.play();
  entry.restoreAt = performance.now() / 1000 + (a.getClip().duration || 1);
  entry.restoreClip = clipName;
  lastAnim = { model: entry.root.name, clip: clipName, at: Date.now() };
  return true;
}

/* ---------------- Signboards — book-card style ---------------- */
function makeSign(aa, word, accent){
  const g = new THREE.Group();
  const postMat = new THREE.MeshStandardMaterial({ color: 0x7A4A26, roughness: 1 });
  const postGeo = new THREE.CylinderGeometry(0.05, 0.06, 1.2, 8);
  [-0.68, 0.68].forEach(x => {
    const p = new THREE.Mesh(postGeo, postMat);
    p.position.set(x, 0.6, 0); p.castShadow = true; g.add(p);
  });
  const cv = document.createElement('canvas');
  cv.width = 512; cv.height = 320;
  const c = cv.getContext('2d');
  const rr = (x, y, w, h, r) => { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); };
  rr(6, 6, 500, 308, 42); c.fillStyle = '#FBF7EC'; c.fill();
  c.lineWidth = 15; c.strokeStyle = '#0B5D43'; c.stroke();
  rr(30, 30, 452, 260, 30); c.lineWidth = 5; c.strokeStyle = '#C9A227'; c.stroke();
  c.textAlign = 'center'; c.textBaseline = 'middle';
  c.fillStyle = accent;
  c.font = '900 118px "Baloo 2","Comic Sans MS",sans-serif';
  c.fillText(aa, 256, 108);
  c.fillStyle = '#22332B';
  c.font = '800 88px "Baloo 2","Comic Sans MS",sans-serif';
  c.fillText(word, 256, 232);
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  const woodMat = new THREE.MeshStandardMaterial({ color: 0x7A4A26, roughness: 1 });
  const board = new THREE.Mesh(
    new THREE.BoxGeometry(2.0, 1.25, 0.07),
    [ woodMat, woodMat, woodMat, woodMat,
      new THREE.MeshStandardMaterial({ map: tex, roughness: 0.65 }),
      new THREE.MeshStandardMaterial({ color: 0xFBF7EC, roughness: 0.8 }) ]
  );
  board.position.y = 1.32;
  board.rotation.x = -0.05;
  board.castShadow = true;
  g.add(board);
  return g;
}

/* ---------------- Ant locomotion ----------------
   The Blender ant faces +X, feet on y=0. A wrapper root walks it
   along a gentle closed loop. Walk and Wave are blended by hand
   (managed weights — no fade-API surprises): Walk loops while it
   walks, its timeScale freezes at pauses (a tiny page-side breathing
   sway keeps it alive), and Wave takes over on tap.              */
const ANT_PATH = [
  [3.6, 2.2], [1.4, 4.0], [-1.6, 3.6], [-4.0, 1.6], [-4.4, -1.2],
  [-2.2, -3.1], [0.6, -3.4], [3.4, -2.2], [4.4, 0.2]
].map(([x, z]) => new THREE.Vector3(x, 0, z));
const antCurve = new THREE.CatmullRomCurve3(ANT_PATH, true, 'catmullrom', 0.55);
const antLen = antCurve.getLength();
const ANT_SPEED = 1.15;
let antU = 0.06, antMode = 'walk', antModeT = 5.5, antWaveT = 0, antHeading = 0;
let walkWeight = 0, waveWeight = 0;
const _ap = new THREE.Vector3(), _at = new THREE.Vector3();

function antPlace(){
  const m = MODELS.ant;
  if (!m) return;
  antCurve.getPointAt(antU, _ap);
  m.root.position.set(_ap.x, 0, _ap.z);
  m.root.rotation.y = antHeading;
}
function antHeadingAt(u){
  antCurve.getTangentAt(u, _at);
  /* model forward is +X: rotation.y = atan2(-dz, dx) */
  return Math.atan2(-_at.z, _at.x);
}
function dampAngle(a, b, lambda, dt){
  let d = ((b - a + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
  return a + d * (1 - Math.exp(-lambda * dt));
}
function antStartClips(){
  const m = MODELS.ant;
  if (!m) return;
  const wk = m.actions.Walk, wv = m.actions.Wave;
  if (wk){ wk.setLoop(THREE.LoopRepeat); wk.enabled = true; wk.setEffectiveWeight(0); wk.play(); }
  if (wv){ wv.setLoop(THREE.LoopOnce, 1); wv.clampWhenFinished = true; wv.enabled = true; wv.setEffectiveWeight(0); wv.play(); }
}
function antWave(){
  const m = MODELS.ant;
  if (!m || !m.actions.Wave) return false;
  m.actions.Wave.reset();
  antWaveT = m.actions.Wave.getClip().duration || 1.2;
  lastAnim = { model: 'antRoot', clip: 'Wave', at: Date.now() };
  return true;
}
function updateAnt(dt, t){
  const m = MODELS.ant;
  if (!m) return;
  const waving = antWaveT > 0;
  if (waving){
    antWaveT -= dt;
  } else if (antMode === 'walk'){
    antU = (antU + (ANT_SPEED * dt) / antLen) % 1;
    antHeading = dampAngle(antHeading, antHeadingAt(antU), 5, dt);
    antModeT -= dt;
    if (antModeT <= 0){ antMode = 'pause'; antModeT = 1.4 + Math.random() * 1.3; }
  } else { /* pause */
    antModeT -= dt;
    if (antModeT <= 0){ antMode = 'walk'; antModeT = 4.5 + Math.random() * 3; }
  }
  antPlace();
  /* managed blend weights */
  const wk = m.actions.Walk, wv = m.actions.Wave;
  if (wk){
    const target = waving ? 0 : 1;
    walkWeight += (target - walkWeight) * Math.min(1, dt * 7);
    wk.setEffectiveWeight(walkWeight);
    const tsTarget = (!waving && antMode === 'walk') ? 1 : 0;
    wk.timeScale = THREE.MathUtils.damp(wk.timeScale || 0, tsTarget, 6, dt);
  }
  if (wv){
    const target = waving ? 1 : 0;
    waveWeight += (target - waveWeight) * Math.min(1, dt * 7);
    wv.setEffectiveWeight(waveWeight);
  }
  /* gentle breathing sway from the page side, strongest at pauses */
  const swayAmp = antMode === 'pause' && !waving ? 1 : 0.25;
  m.inner.position.y = Math.sin(t * 2.2) * 0.012 * swayAmp;
  m.inner.rotation.z = Math.sin(t * 1.7) * 0.010 * swayAmp;
}

/* ---------------- Load everything ---------------- */
const loadJobs = [
  ['garden',  'models3d/garden.glb',  {}],
  ['letterA', 'models3d/letterA.glb', { scale: 2.3, pos: [0, 0, -4.4], rotY: -Math.PI / 2 }],
  ['apple',   'models3d/apple.glb',   { scale: 1.7, pos: [-3.2, 0, 2.5], rotY: 0.4 }],
  ['axe',     'models3d/axe.glb',     { scale: 1.35, pos: [2.95, 0, 2.95], rotY: -0.30 }],
  ['ant',     'models3d/ant.glb',     { scale: 1.15 }]
];
Promise.all(loadJobs.map(([name, url, opts]) =>
  loader.loadAsync(url).then(gltf => ({ name, gltf, opts })).catch(err => ({ name, err }))
)).then(results => {
  const failed = results.filter(r => r.err);
  for (const r of results){
    if (r.err) continue;
    const entry = registerModel(r.name, r.gltf, r.opts);
    if (r.name === 'garden'){
      entry.root.traverse(o => {
        if (o.isMesh){
          o.receiveShadow = true;
          const bb = new THREE.Box3().setFromObject(o);
          o.castShadow = (bb.max.y - bb.min.y) > 1.0;   /* tree + bushes cast, ground doesn't */
        }
      });
    } else {
      prepShadows(entry.root, true, false);
    }
  }
  if (failed.length){
    document.getElementById('loadnote').style.display = 'flex';
    return;
  }
  /* signboards beside their objects */
  const signAnt = makeSign('Aa', 'Ant', '#C0392B');
  signAnt.position.set(0.6, 0, 4.7); signAnt.rotation.y = 0.10; world.add(signAnt);
  const signApple = makeSign('Aa', 'Apple', '#C0392B');
  signApple.position.set(-3.7, 0, 3.9); signApple.rotation.y = 0.35; world.add(signApple);
  const signAxe = makeSign('Aa', 'Axe', '#C0392B');
  signAxe.position.set(4.3, 0, 3.0); signAxe.rotation.y = -0.55; world.add(signAxe);

  if (MODELS.ant){
    antHeading = antHeadingAt(antU);
    antStartClips();
    antPlace();
  }
  loaded = true;
  barEl.style.width = '100%'; pctEl.textContent = '100%';
  setTimeout(() => document.getElementById('loading').classList.add('gone'), 350);
  setTimeout(() => toast('Tap the ant 🐜, apple 🍎 and axe 🪓 — they sing!', 4200), 700);
});

/* ---------------- Touch = perform + sing ---------------- */
function buzz(pattern){
  try { if (navigator.vibrate) navigator.vibrate(pattern); } catch(e){}
}
const HIT = [
  { key: 'ant',     model: 'ant',     clip: 'Wave',   line: 'ant'   },
  { key: 'apple',   model: 'apple',   clip: 'Bounce', line: 'apple' },
  { key: 'axe',     model: 'axe',     clip: 'NoNo',   line: 'axe'   },
  { key: 'letterA', model: 'letterA', clip: 'Wiggle', line: null    }
];
function performTap(hit){
  if (linePlaying) return;                    /* one song at a time */
  const entry = MODELS[hit.model];
  if (!entry) return;
  if (hit.key === 'ant'){ if (!antWave()) return; }
  else if (!playOnce(entry, hit.clip)) return;
  buzz(hit.key === 'letterA' ? [25] : [40, 40, 40]);
  if (hit.line) playLine(hit.line);
  else { Music.ensure(); Music.jingle(); }
}
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let downPos = null;
renderer.domElement.addEventListener('pointerdown', e => { downPos = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!downPos) return;
  const moved = Math.hypot(e.clientX - downPos[0], e.clientY - downPos[1]);
  downPos = null;
  if (moved > 8 || !loaded || arActive) return;      /* drags are for the camera */
  pointer.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  /* the FRONT-most tappable object wins — the ant may stroll behind one */
  const hits = [];
  for (const hit of HIT){
    const entry = MODELS[hit.model];
    if (!entry) continue;
    const xs = raycaster.intersectObject(entry.root, true);
    if (xs.length) hits.push({ hit, d: xs[0].distance });
  }
  if (hits.length){
    hits.sort((a, b) => a.d - b.d);
    performTap(hits[0].hit);
  }
});

/* ---------------- 📱 Move Phone — gyro camera ---------------- */
const btnGyro = document.getElementById('btnGyro');
let gyroOn = false, gyroSeen = false, baseAz = 0, basePol = 1.0, tgtAz = 0, tgtPol = 1.0;
function onGyro(e){
  if (e.beta == null && e.gamma == null) return;
  gyroSeen = true;
  const gamma = THREE.MathUtils.degToRad(e.gamma || 0);
  const beta = THREE.MathUtils.degToRad((e.beta == null ? 45 : e.beta) - 45);
  tgtAz = THREE.MathUtils.clamp(baseAz - gamma * 1.15, baseAz - 1.15, baseAz + 1.15);
  tgtPol = THREE.MathUtils.clamp(basePol + beta * 0.55, 0.32, 1.35);
}
function gyroOff(silent){
  gyroOn = false;
  window.removeEventListener('deviceorientation', onGyro);
  if (!arActive) controls.enabled = true;
  btnGyro.classList.remove('on');
  if (!silent) toast('Drag to look around 👀');
}
btnGyro.addEventListener('click', async () => {
  if (gyroOn){ gyroOff(false); return; }
  if (!('DeviceOrientationEvent' in window)){
    toast('This phone has no tilt sensor — drag still works! 👀');
    return;
  }
  if (typeof DeviceOrientationEvent.requestPermission === 'function'){
    try {
      const res = await DeviceOrientationEvent.requestPermission();
      if (res !== 'granted'){ toast('No problem — drag to look around! 👀'); return; }
    } catch(e){ toast('No problem — drag to look around! 👀'); return; }
  }
  const off = camera.position.clone().sub(controls.target);
  baseAz = Math.atan2(off.x, off.z);
  basePol = Math.acos(THREE.MathUtils.clamp(off.y / off.length(), -1, 1));
  tgtAz = baseAz; tgtPol = basePol;
  gyroSeen = false;
  gyroOn = true;
  controls.enabled = false;
  btnGyro.classList.add('on');
  window.addEventListener('deviceorientation', onGyro);
  toast('Move your phone to look around! 📱', 2600);
  setTimeout(() => {
    if (gyroOn && !gyroSeen){ gyroOff(true); toast('This phone has no tilt sensor — drag still works! 👀'); }
  }, 1800);
});
function updateGyroCam(dt){
  const off = camera.position.clone().sub(controls.target);
  const radius = off.length();
  const az = Math.atan2(off.x, off.z);
  const pol = Math.acos(THREE.MathUtils.clamp(off.y / radius, -1, 1));
  const k = 1 - Math.exp(-6 * dt);
  const naz = az + (tgtAz - az) * k;
  const npol = pol + (tgtPol - pol) * k;
  camera.position.set(
    controls.target.x + radius * Math.sin(npol) * Math.sin(naz),
    controls.target.y + radius * Math.cos(npol),
    controls.target.z + radius * Math.sin(npol) * Math.cos(naz)
  );
  camera.lookAt(controls.target);
}

/* ---------------- 📷 Magic Camera — real WebXR AR attempt ---------------- */
const btnAR = document.getElementById('btnAR');
let arActive = false;
const MAGIC_NO = 'Magic camera is not on this phone — enjoy the 3D garden! 🌈';
btnAR.addEventListener('click', async () => {
  if (!('xr' in navigator)){ toast(MAGIC_NO); return; }
  let ok = false;
  try { ok = await navigator.xr.isSessionSupported('immersive-ar'); } catch(e){ ok = false; }
  if (!ok){ toast(MAGIC_NO); return; }
  try {
    const session = await navigator.xr.requestSession('immersive-ar', { optionalFeatures: ['local-floor', 'hit-test'] });
    session.addEventListener('end', () => {
      arActive = false;
      world.scale.setScalar(1);
      world.position.set(0, 0, 0);
      if (!gyroOn) controls.enabled = true;
      toast('Welcome back to the 3D garden! 🌈');
    });
    await renderer.xr.setSession(session);
    /* shrink the garden onto the table in front of the child */
    arActive = true;
    controls.enabled = false;
    world.scale.setScalar(0.09);
    world.position.set(0, -1.0, -1.1);
    toast('Magic! The garden is in your room! 📷', 3000);
  } catch(e){ toast(MAGIC_NO); }
});

/* ---------------- Loop + resize ---------------- */
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;
  if (loaded){
    updateAnt(dt, t);
    const nowS = performance.now() / 1000;
    for (const k in MODELS){
      const e = MODELS[k];
      if (e.restoreAt && nowS > e.restoreAt){ e.actions[e.restoreClip].stop(); e.restoreAt = 0; e.restoreClip = null; }
      if (e.mixer) e.mixer.update(dt);
    }
  }
  if (gyroOn && !arActive) updateGyroCam(dt);
  else if (!arActive) controls.update();
  renderer.render(scene, camera);
});
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

/* ---------------- Verification handle ---------------- */
function focusOn(name){
  if (name === 'home'){
    camera.position.copy(homePos());
    controls.target.copy(TGT_HOME);
    return true;
  }
  const entry = MODELS[name];
  if (!entry) return false;
  const p = entry.root.position;
  controls.target.set(p.x, 0.45, p.z);
  camera.position.set(p.x + 2.4, 1.7, p.z + 3.0);
  return true;
}
window.PAGE3D = {
  THREE, scene, camera, renderer, controls, world, models: MODELS,
  state(){
    const running = {};
    for (const k in MODELS){
      running[k] = Object.keys(MODELS[k].actions).filter(n => {
        const a = MODELS[k].actions[n];
        return a.isRunning() && a.getEffectiveWeight() > 0.05;
      });
    }
    return { loaded, antMode, antU, antWaveT, linePlaying, lastLine, lastAnim, gyroOn, arActive, musicOn: Music.on, running };
  },
  focusOn,
  tapObject(key){
    const hit = HIT.find(h => h.key === key);
    if (hit) performTap(hit);
  }
};
