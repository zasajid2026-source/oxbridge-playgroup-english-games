/* =====================================================================
   The 3D Ant Garden — a standalone Three.js sample for the Playgroup
   games site. The ant is fully procedural (no external model): glossy
   banded gaster, waist nodes, thorax, head with elbowed antennae and
   six jointed legs driven by a tripod gait locked to distance walked.
   ===================================================================== */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

window.__ant3dBooted = true;
clearTimeout(window.__ant3dWatchdog);

/* ---------------- Voice — same style as the main games page ----------------
   Female Pakistani / Indian English picker, rate 0.82, pitch 1.05.     */
const Voice = {
  enabled: true, rate: 0.82, pitch: 1.05, voice: null,
  FEMALE: /female|heera|neerja|veena|swara|asha|ananya|kavya|priya|meera|zira|samantha|anita|sunita/i,
  score(v){
    const name = v.name || '', lang = (v.lang || '').toLowerCase().replace('_','-');
    const fem = this.FEMALE.test(name);
    if (lang.indexOf('en-pk') === 0 && fem) return 100;
    if (lang.indexOf('en-in') === 0 && fem) return 90;
    if (lang.indexOf('en-in') === 0) return 80;
    if (lang.indexOf('en-gb') === 0 && fem) return 70;
    if (lang.indexOf('en-us') === 0 && fem) return 65;
    if (lang.indexOf('en-pk') === 0) return 60;
    if (lang.indexOf('en-gb') === 0) return 50;
    if (lang.indexOf('en-us') === 0) return 45;
    if (lang.indexOf('en') === 0) return 30;
    return -1;
  },
  pick(){
    if (!('speechSynthesis' in window)) return;
    const vs = speechSynthesis.getVoices();
    let best = null, bs = -1;
    for (const v of vs){ const s = this.score(v); if (s > bs){ bs = s; best = v; } }
    this.voice = best;
  },
  say(text){
    if (!this.enabled || !('speechSynthesis' in window)) return;
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      if (this.voice) u.voice = this.voice;
      u.rate = this.rate; u.pitch = this.pitch;
      speechSynthesis.speak(u);
    } catch(e){ /* speech is a bonus, never a blocker */ }
  },
  setEnabled(on){
    this.enabled = on;
    if (!on){ try{ speechSynthesis.cancel(); }catch(e){} }
  }
};
if ('speechSynthesis' in window){
  Voice.pick();
  speechSynthesis.onvoiceschanged = () => Voice.pick();
}
const tglVoice = document.getElementById('tglVoice');
tglVoice.addEventListener('click', () => {
  Voice.setEnabled(!Voice.enabled);
  tglVoice.textContent = Voice.enabled ? '🔊' : '🔇';
  tglVoice.classList.toggle('off', !Voice.enabled);
});

/* ---------------- Renderer / scene ---------------- */
const canvas = document.getElementById('scene');
let renderer = null;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
} catch(e){ renderer = null; }
if (!renderer){
  document.getElementById('nogl').style.display = 'flex';
  throw new Error('WebGL unavailable');
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xAEE0F2);
scene.fog = new THREE.Fog(0xAEE0F2, 22, 46);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 120);
camera.position.set(8.5, 6.5, 11.5);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0.5, 0);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.minDistance = 4;
controls.maxDistance = 20;
controls.maxPolarAngle = 1.38;   /* never under the ground */
controls.minPolarAngle = 0.15;
controls.enablePan = false;

/* Lights — warm sun + soft sky fill; one small shadow map for mobile */
scene.add(new THREE.HemisphereLight(0xD8F1FF, 0x79B364, 0.95));
const sun = new THREE.DirectionalLight(0xFFF1D6, 1.9);
sun.position.set(8, 12, 6);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -12; sun.shadow.camera.right = 12;
sun.shadow.camera.top = 12; sun.shadow.camera.bottom = -12;
sun.shadow.camera.far = 32;
sun.shadow.bias = -0.0006;
scene.add(sun);

/* ---------------- The garden ---------------- */
const std = (color, opts = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.9, metalness: 0, ...opts });

/* Ground — one big soft green disc */
const ground = new THREE.Mesh(new THREE.CircleGeometry(16, 56), std(0x69B85C));
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

/* Subtle colour patches on the grass */
{
  const patchCols = [0x77C268, 0x5DA852, 0x83CC72, 0x64AF57];
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 12; i++){
    const r = 1.4 + rnd() * 2.4;
    const p = new THREE.Mesh(new THREE.CircleGeometry(r, 24), std(patchCols[i % patchCols.length]));
    p.rotation.x = -Math.PI / 2;
    const a = rnd() * Math.PI * 2, d = 3 + rnd() * 11;
    p.position.set(Math.cos(a) * d, 0.006 + i * 0.0004, Math.sin(a) * d);
    p.receiveShadow = true;
    scene.add(p);
  }
}

/* The ant's wandering route — also drawn as the light dirt path */
const PATH_POINTS = [
  [ 4.2,  3.0], [ 1.6,  5.6], [-2.8,  4.6], [-5.2,  1.2],
  [-3.6, -3.0], [ 0.4, -4.6], [ 4.4, -2.6], [ 5.6,  0.8]
].map(([x, z]) => new THREE.Vector3(x, 0, z));
const pathCurve = new THREE.CatmullRomCurve3(PATH_POINTS, true, 'catmullrom', 0.6);
const pathLen = pathCurve.getLength();
{
  const sandCols = [0xDFBE8A, 0xD9B380, 0xE5C893];
  const disc = new THREE.CircleGeometry(1.0, 18);
  const steps = Math.floor(pathLen / 0.55);
  for (let i = 0; i < steps; i++){
    const pt = pathCurve.getPointAt(i / steps);
    const m = new THREE.Mesh(disc, std(sandCols[i % sandCols.length]));
    m.rotation.x = -Math.PI / 2;
    m.position.set(pt.x, 0.012 + (i % 3) * 0.0006, pt.z);
    m.scale.setScalar(0.85 + ((i * 37) % 10) / 40);
    m.receiveShadow = true;
    scene.add(m);
  }
}

/* Flowers */
function makeFlower(petalColor, x, z, s = 1){
  const g = new THREE.Group();
  const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.045, 0.72, 6), std(0x3E8E4F));
  stem.position.y = 0.36; stem.castShadow = true; g.add(stem);
  const head = new THREE.Group(); head.position.y = 0.74;
  const centre = new THREE.Mesh(new THREE.SphereGeometry(0.095, 12, 10), std(0xF6C90E, { roughness: 0.6 }));
  centre.castShadow = true; head.add(centre);
  const petalGeo = new THREE.SphereGeometry(0.088, 10, 8);
  const petalMat = std(petalColor, { roughness: 0.55 });
  for (let i = 0; i < 6; i++){
    const a = (i / 6) * Math.PI * 2;
    const p = new THREE.Mesh(petalGeo, petalMat);
    p.position.set(Math.cos(a) * 0.155, 0, Math.sin(a) * 0.155);
    p.scale.set(1, 0.45, 1);
    head.add(p);
  }
  g.add(head);
  g.position.set(x, 0, z);
  g.scale.setScalar(s);
  g.rotation.y = x * 1.7 + z;
  scene.add(g);
}
makeFlower(0xF78FB3,  3.2,  5.4, 1.1); makeFlower(0xFFFFFF, -4.6,  5.6, 1.0);
makeFlower(0xB388E8,  6.4, -0.6, 1.15); makeFlower(0xF78FB3, -6.8, -1.8, 0.95);
makeFlower(0xFFD166,  1.8, -6.2, 1.05); makeFlower(0xFFFFFF,  7.4,  3.6, 0.9);
makeFlower(0xB388E8, -1.8,  6.8, 1.0);  makeFlower(0xFFD166, -7.6,  2.8, 1.1);

/* Grass tufts */
{
  const tuftCols = [0x4E9B47, 0x5DA852, 0x43873E];
  const coneGeo = new THREE.ConeGeometry(0.07, 0.52, 5);
  let seed = 31;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 16; i++){
    const tuft = new THREE.Group();
    for (let b = 0; b < 5; b++){
      const blade = new THREE.Mesh(coneGeo, std(tuftCols[b % 3]));
      blade.position.set((rnd() - 0.5) * 0.3, 0.24, (rnd() - 0.5) * 0.3);
      blade.rotation.set((rnd() - 0.5) * 0.5, 0, (rnd() - 0.5) * 0.5);
      blade.castShadow = true;
      tuft.add(blade);
    }
    const a = rnd() * Math.PI * 2, d = 3.5 + rnd() * 11.5;
    tuft.position.set(Math.cos(a) * d, 0, Math.sin(a) * d);
    scene.add(tuft);
  }
}

/* Smooth stones */
{
  const stoneMat = std(0x9AA0A3, { roughness: 0.95 });
  [[2.6, 1.4, 0.34], [-3.4, -5.4, 0.42], [6.8, 5.6, 0.3], [-6.2, 4.2, 0.26], [0.8, 7.6, 0.38]].forEach(([x, z, r]) => {
    const s = new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), stoneMat);
    s.position.set(x, r * 0.32, z);
    s.scale.y = 0.55;
    s.rotation.y = x * 2.3;
    s.castShadow = true; s.receiveShadow = true;
    scene.add(s);
  });
}

/* The apple tree — trunk, leafy canopy, red apples */
{
  const tree = new THREE.Group();
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.55, 2.3, 10), std(0x7A4A26, { roughness: 1 }));
  trunk.position.y = 1.15; trunk.castShadow = true; tree.add(trunk);
  const leafCols = [0x3E8E4F, 0x4CA35C, 0x35804A];
  [[0, 3.3, 0, 1.75], [1.15, 2.75, 0.3, 1.15], [-1.05, 2.85, -0.25, 1.1], [0.25, 2.6, 0.95, 1.0], [-0.3, 2.65, -1.0, 0.95]]
    .forEach(([x, y, z, r], i) => {
      const c = new THREE.Mesh(new THREE.SphereGeometry(r, 20, 16), std(leafCols[i % 3], { roughness: 0.85 }));
      c.position.set(x, y, z); c.castShadow = true; tree.add(c);
    });
  const appleMat = std(0xE23B2E, { roughness: 0.35 });
  const appleGeo = new THREE.SphereGeometry(0.17, 12, 10);
  [[0.9, 2.2, 1.15], [-1.25, 2.3, 0.55], [0.3, 1.95, -1.35], [1.55, 2.6, -0.5],
   [-0.7, 2.0, 1.25], [0.05, 3.9, 0.9], [-1.5, 3.1, -0.8], [1.3, 3.3, 0.75]]
    .forEach(([x, y, z]) => {
      const a = new THREE.Mesh(appleGeo, appleMat);
      a.position.set(x, y, z); a.castShadow = true; tree.add(a);
    });
  tree.position.set(-6.4, 0, -5.4);
  scene.add(tree);
}

/* Two soft bushes at the edges */
[[8.6, -4.6, 1.5], [-9.2, 0.8, 1.25]].forEach(([x, z, r]) => {
  const b = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), std(0x4CA35C, { roughness: 0.9 }));
  b.position.set(x, r * 0.55, z); b.scale.y = 0.72; b.castShadow = true;
  scene.add(b);
});

/* ---------------- The ant — fully procedural ----------------
   Local space: head toward +Z. bodyGroup rides at BODY_Y so the feet
   just touch the ground; legs hang from the thorax with hip yaw
   (stride), hip splay (lift) and a knee joint.                     */
const BODY_Y = 0.88;
const bodyMat  = new THREE.MeshStandardMaterial({ color: 0x3A2317, roughness: 0.28, metalness: 0.08 });
const darkMat  = new THREE.MeshStandardMaterial({ color: 0x201207, roughness: 0.35, metalness: 0.05 });
const bandMat  = new THREE.MeshStandardMaterial({ color: 0x54341E, roughness: 0.22, metalness: 0.08 });
const eyeMat   = new THREE.MeshStandardMaterial({ color: 0x0A0603, roughness: 0.12, metalness: 0.2 });

function ball(mat, r, sx = 1, sy = 1, sz = 1){
  const m = new THREE.Mesh(new THREE.SphereGeometry(r, 24, 18), mat);
  m.scale.set(sx, sy, sz);
  m.castShadow = true;
  return m;
}
function limb(mat, len, rTop, rBot){
  /* cylinder extending DOWN -Y from its group origin */
  const geo = new THREE.CylinderGeometry(rTop, rBot, len, 8);
  geo.translate(0, -len / 2, 0);
  const m = new THREE.Mesh(geo, mat);
  m.castShadow = true;
  return m;
}

const antGroup = new THREE.Group();   /* position on path + heading */
const bodyGroup = new THREE.Group();  /* bob + pitch */
bodyGroup.position.y = BODY_Y;
antGroup.add(bodyGroup);
scene.add(antGroup);

/* Gaster (abdomen) — banded: glossy segments stacked along Z */
const gaster = new THREE.Group();
gaster.position.set(0, 0.06, -1.02);
{
  const segs = [
    [0.30, -0.44], [0.47, -0.26], [0.565, -0.05], [0.56, 0.17], [0.44, 0.36], [0.26, 0.48]
  ];
  segs.forEach(([r, dz], i) => {
    const s = ball(i % 2 ? bandMat : bodyMat, r, 0.96, 0.9, 1.0);
    s.position.z = dz;
    gaster.add(s);
  });
}
bodyGroup.add(gaster);

/* Waist nodes (petiole + post-petiole) */
const waist1 = ball(darkMat, 0.135); waist1.position.set(0, 0.05, -0.40); bodyGroup.add(waist1);
const waist2 = ball(darkMat, 0.115); waist2.position.set(0, 0.04, -0.26); bodyGroup.add(waist2);

/* Thorax */
const thorax = ball(bodyMat, 0.37, 0.92, 0.88, 1.6);
thorax.position.set(0, 0.02, 0.12);
bodyGroup.add(thorax);

/* Head */
const headGroup = new THREE.Group();
headGroup.position.set(0, 0.08, 0.88);
bodyGroup.add(headGroup);
headGroup.add(ball(bodyMat, 0.41, 1.0, 0.95, 1.05));
[-1, 1].forEach(s => {
  const eye = ball(eyeMat, 0.078);
  eye.position.set(0.315 * s, 0.10, 0.14);
  headGroup.add(eye);
  const mand = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.22, 8), darkMat);
  mand.position.set(0.13 * s, -0.13, 0.40);
  mand.rotation.set(1.25, 0, -0.5 * s);
  mand.castShadow = true;
  headGroup.add(mand);
});

/* Antennae — elbowed: scape from the head, funicule bending forward.
   Each antenna: root group (sweep yaw) → scape → elbow group → funicule. */
function makeAntenna(side){
  const root = new THREE.Group();
  root.position.set(0.15 * side, 0.30, 0.26);
  const scape = limb(bodyMat, 0.42, 0.030, 0.036);
  const scapePivot = new THREE.Group();
  scapePivot.rotation.set(-0.55, 0, -0.55 * side); /* up, out, a little forward */
  scape.rotation.x = Math.PI; /* limb hangs -Y; flip so it rises +Y */
  scapePivot.add(scape);
  root.add(scapePivot);
  const elbow = new THREE.Group();
  elbow.position.set(0, 0.42, 0);
  /* position the elbow at the scape tip inside the pivot's frame */
  scapePivot.add(elbow);
  const fun = limb(bodyMat, 0.46, 0.024, 0.028);
  fun.rotation.x = Math.PI;
  const funPivot = new THREE.Group();
  funPivot.rotation.x = 1.85; /* bend forward + down, like a real ant feeling ahead */
  funPivot.add(fun);
  const tip = ball(darkMat, 0.045);
  tip.position.y = 0.46;
  funPivot.add(tip);
  elbow.add(funPivot);
  /* shift elbow to the true scape tip: scape was flipped, its tip is +Y 0.42 in pivot space */
  headGroup.add(root);
  return { root, scapePivot, funPivot };
}
const antennae = [makeAntenna(-1), makeAntenna(1)];

/* Legs — hip yaw group → splay pivot (rotation.z) → femur → knee → tibia.
   Tripod gait: (R0,L1,R2) in phase, (L0,R1,L2) half a cycle later.   */
const legs = [];
{
  const hipZ = [0.40, 0.12, -0.16];
  [-1, 1].forEach(side => {
    for (let i = 0; i < 3; i++){
      const yaw = new THREE.Group();
      yaw.position.set(0.25 * side, -0.06, hipZ[i]);
      bodyGroup.add(yaw);
      const splay = new THREE.Group();
      yaw.add(splay);
      const femur = limb(bodyMat, 0.52, 0.045, 0.055);
      splay.add(femur);
      const knee = new THREE.Group();
      knee.position.y = -0.52;
      splay.add(knee);
      const tibia = limb(darkMat, 0.55, 0.032, 0.042);
      knee.add(tibia);
      const tripod = ((side > 0) === (i % 2 === 0)) ? 0 : Math.PI;
      legs.push({ side, i, yaw, splay, knee, tripod });
    }
  });
}
/* Pose constants solved so the feet rest on the ground at BODY_Y */
const SPLAY_BASE = 0.80, KNEE_BASE = 0.45;

/* A soft pulsing ring under the ant before the show starts */
const ring = new THREE.Mesh(
  new THREE.RingGeometry(1.05, 1.3, 40),
  new THREE.MeshBasicMaterial({ color: 0xC9A227, transparent: true, opacity: 0.85, side: THREE.DoubleSide })
);
ring.rotation.x = -Math.PI / 2;
ring.position.y = 0.03;
antGroup.add(ring);

/* ---------------- Movement choreography ----------------
   State machine: walk (ease in/out along the path) ↔ pause (antennae
   explore, tiny heading turns). Gait phase advances ONLY with distance
   travelled, so the legs freeze the moment the ant stops.            */
let u = 0.02;                       /* position along the path, 0..1 */
let heading = 0;
let started = false;
let gaitPhase = 0;
let gaitAmp = 0;                    /* 0 still … 1 full stride */
let mode = 'pause';
let modeT = 0;                      /* time left in this mode */
let walkFrom = u, walkTo = u, walkDist = 0, walkDone = 0;
let pauseTurn = 0;                  /* small heading drift while pausing */
let waveT = 0;                      /* antenna-wave timer after tapping the ant */
const MAX_SPEED = 1.55;             /* garden units per second */

function placeAnt(){
  const pt = pathCurve.getPointAt(u);
  antGroup.position.set(pt.x, 0, pt.z);
  antGroup.rotation.y = heading;
}
function tangentHeading(uu){
  const t = pathCurve.getTangentAt(uu);
  return Math.atan2(t.x, t.z);
}
function beginWalk(){
  const span = 0.09 + Math.random() * 0.10;         /* ~1/8 of the loop */
  walkFrom = u; walkTo = u + span; walkDone = 0;
  walkDist = span * pathLen;
  mode = 'walk';
}
function beginPause(long){
  mode = 'pause';
  modeT = long ? 1.6 + Math.random() * 1.4 : 0.9 + Math.random() * 0.9;
  pauseTurn = (Math.random() - 0.5) * 0.55;
}
placeAnt();
heading = tangentHeading(u);
placeAnt();

function updateAnt(dt, t){
  let speed = 0;
  if (started){
    if (mode === 'walk'){
      const remain = walkDist - walkDone;
      const ramp = THREE.MathUtils.clamp(Math.min(walkDone, remain) / 0.55, 0, 1);
      speed = MAX_SPEED * (0.25 + 0.75 * ramp);
      const step = Math.min(speed * dt, remain);
      walkDone += step;
      u = (walkFrom + walkDone / pathLen) % 1;
      const target = tangentHeading(u);
      heading = dampAngle(heading, target, 6, dt);
      if (remain <= 0.001) beginPause(false);
    } else { /* pause */
      modeT -= dt;
      heading = dampAngle(heading, heading + pauseTurn * dt * 0.5, 2.5, dt);
      if (modeT <= 0) beginWalk();
    }
  }
  /* gait follows distance actually travelled */
  gaitPhase += speed * dt * 2.3;
  gaitAmp = THREE.MathUtils.damp(gaitAmp, speed > 0.05 ? 1 : 0, 5, dt);
  placeAnt();

  /* legs */
  for (const leg of legs){
    const p = gaitPhase + leg.tripod;
    const lift = Math.max(0, -Math.cos(p)) * gaitAmp;
    leg.yaw.rotation.y = Math.sin(p) * 0.42 * gaitAmp;
    leg.splay.rotation.z = leg.side * (SPLAY_BASE + lift * 0.38);
    leg.knee.rotation.z = -leg.side * (KNEE_BASE + lift * 0.55);
  }
  /* body bob + pitch, breathing when still */
  const bob = Math.sin(gaitPhase * 2) * 0.028 * gaitAmp + Math.sin(t * 2.1) * 0.008;
  bodyGroup.position.y = BODY_Y + bob;
  bodyGroup.rotation.x = Math.sin(gaitPhase * 2 + 0.6) * 0.045 * gaitAmp;
  bodyGroup.rotation.y = Math.sin(gaitPhase) * 0.05 * gaitAmp;

  /* antennae — always alive; faster + wider while pausing or waving */
  const exploring = (mode === 'pause' && started) || waveT > 0;
  const freq = exploring ? 9.5 : 5.2;
  const amp  = exploring ? 0.50 : 0.27;
  antennae.forEach((a, k) => {
    const ph = t * freq + k * 1.9;
    a.root.rotation.y = Math.sin(ph) * amp;
    a.root.rotation.x = Math.cos(ph * 0.83) * amp * 0.35;
    a.funPivot.rotation.x = 1.85 + Math.sin(ph * 1.27 + 0.8) * 0.22 * (amp / 0.27);
  });
  /* head turns a little while exploring */
  const headTarget = exploring ? Math.sin(t * 0.85) * 0.20 : 0;
  headGroup.rotation.y = THREE.MathUtils.damp(headGroup.rotation.y, headTarget, 4, dt);
  headGroup.rotation.x = waveT > 0 ? -0.18 : 0;
  if (waveT > 0) waveT -= dt;

  /* start ring pulse */
  ring.visible = !started;
  if (!started){
    const s = 1 + Math.sin(t * 2.6) * 0.09;
    ring.scale.setScalar(s);
    ring.material.opacity = 0.55 + Math.sin(t * 2.6) * 0.3;
  }
}
function dampAngle(a, b, lambda, dt){
  let d = ((b - a + Math.PI) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - Math.PI;
  return a + d * (1 - Math.exp(-lambda * dt));
}

/* ---------------- Start + tap-the-ant ---------------- */
const startWrap = document.getElementById('startWrap');
const hintBar = document.getElementById('hintBar');
function startPerformance(){
  if (started) return;
  started = true;
  startWrap.classList.add('gone');
  hintBar.classList.add('show');
  Voice.say('Look! The ant is walking! Ants have six little legs.');
  beginWalk();
}
document.getElementById('btnStart').addEventListener('click', startPerformance);

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let downPos = null;
renderer.domElement.addEventListener('pointerdown', e => { downPos = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!downPos) return;
  const moved = Math.hypot(e.clientX - downPos[0], e.clientY - downPos[1]);
  downPos = null;
  if (moved > 7) return;                       /* it was an orbit drag, not a tap */
  pointer.set((e.clientX / window.innerWidth) * 2 - 1, -(e.clientY / window.innerHeight) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  if (raycaster.intersectObject(antGroup, true).length){
    if (!started) startPerformance();
    else waveT = 1.2;                          /* a happy antenna wave */
  }
});

/* ---------------- Loop + resize ---------------- */
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.05);
  const t = clock.elapsedTime;
  updateAnt(dt, t);
  controls.update();
  renderer.render(scene, camera);
});
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

/* Handle for local verification */
window.ANT3D = { scene, camera, controls, ant: antGroup, start: startPerformance,
                 get started(){ return started; }, get u(){ return u; } };
