'use strict';
// =====================================================================
//  Рендер, небо, свет, день и ночь, снег, постобработка, звук
// =====================================================================
let renderer, scene, camera, post = null;
const QUALITY = [
  { pr: 0.7, shadow: false, sun: false, post: false, ao: false, tex: 1, lamps: 2, map: 512 },
  { pr: 1.0, shadow: true, sun: true, post: true, ao: false, tex: 1, lamps: 4, map: 1024 },
  { pr: 1.4, shadow: true, sun: true, post: true, ao: true, tex: 2, lamps: 6, map: 2048 },
];
let quality = 1;
try { const q = localStorage.getItem('wendigo_q'); if (q !== null) quality = clamp(+q, 0, 2); } catch (e) {}

function initRenderer() {
  renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  $('view').appendChild(renderer.domElement);
  maxAniso = renderer.capabilities.getMaxAnisotropy();
  scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x000000, 0.012);
  camera = new THREE.PerspectiveCamera(72, 1, 0.05, 600); camera.rotation.order = 'YXZ'; scene.add(camera);
  addEventListener('resize', resize);
}
function resize() {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, QUALITY[quality].pr));
  renderer.setSize(innerWidth, innerHeight, false);
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  if (post) { const v = renderer.getDrawingBufferSize(new THREE.Vector2()); post.rt.setSize(v.x, v.y); post.mat.uniforms.res.value.copy(v); }
}

// ---------------------------------------------------------------------
//  Небо
// ---------------------------------------------------------------------
const SKY = {};
function buildSky() {
  const mat = new THREE.ShaderMaterial({
    uniforms: { sunDir: { value: new THREE.Vector3(0, 1, 0) }, moonDir: { value: new THREE.Vector3(0, 1, 0) }, dayK: { value: 1 }, duskK: { value: 0 }, time: { value: 0 } },
    vertexShader: 'varying vec3 vD; void main(){ vD = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p.xyww; }',
    fragmentShader: `uniform vec3 sunDir; uniform vec3 moonDir; uniform float dayK; uniform float duskK; uniform float time; varying vec3 vD;
      float h3(vec3 p){ return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
      float vn(vec3 p){ vec3 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
        return mix(mix(mix(h3(i), h3(i + vec3(1,0,0)), f.x), mix(h3(i + vec3(0,1,0)), h3(i + vec3(1,1,0)), f.x), f.y),
                   mix(mix(h3(i + vec3(0,0,1)), h3(i + vec3(1,0,1)), f.x), mix(h3(i + vec3(0,1,1)), h3(i + vec3(1,1,1)), f.x), f.y), f.z); }
      float fbm(vec3 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * vn(p); p = p * 2.03 + 7.1; a *= 0.5; } return s; }
      void main(){
        vec3 d = normalize(vD); float h = d.y; float nk = 1.0 - dayK;
        vec3 day = mix(vec3(0.62, 0.68, 0.74), vec3(0.28, 0.42, 0.62), clamp(h * 1.6, 0.0, 1.0));
        vec3 nig = mix(vec3(0.03, 0.04, 0.062), vec3(0.004, 0.008, 0.02), clamp(h * 1.8, 0.0, 1.0));
        float md = max(dot(d, moonDir), 0.0);
        nig += vec3(0.05, 0.07, 0.12) * pow(md, 8.0) + vec3(0.02, 0.03, 0.05) * pow(md, 2.0); // лунное зарево
        vec3 col = mix(nig, day, dayK);
        float hz = pow(1.0 - abs(h), 5.0);
        col += vec3(0.9, 0.38, 0.12) * hz * duskK * 0.7 * max(0.0, dot(normalize(vec3(d.x, 0.0, d.z)), normalize(vec3(sunDir.x, 0.0, sunDir.z))) * 0.5 + 0.5);
        col += vec3(0.04, 0.05, 0.07) * hz * nk * 0.8; // холодная дымка у горизонта
        float sd = max(dot(d, sunDir), 0.0);
        col += vec3(1.0, 0.9, 0.7) * pow(sd, 900.0) * 30.0 * dayK + vec3(1.0, 0.6, 0.3) * pow(sd, 10.0) * 0.25 * (dayK + duskK);
        // облака (дрейфуют, ночью подсвечены луной)
        vec3 cp = vec3(d.x / (h + 0.28) * 2.4 + time * 0.012, d.z / (h + 0.28) * 2.4, time * 0.004);
        float cl = smoothstep(0.46, 0.78, fbm(cp)) * clamp(h * 3.5, 0.0, 1.0);
        // звёзды: два слоя, разной яркости и мерцание
        float stars = 0.0;
        vec3 c1 = floor(d * 380.0); float s1 = h3(c1); stars += step(0.9982, s1) * (0.5 + 0.9 * h3(c1 + 1.0)) * (0.75 + 0.25 * sin(time * (2.0 + 4.0 * s1) + s1 * 90.0));
        vec3 c2 = floor(d * 900.0); stars += step(0.9992, h3(c2)) * 0.35;
        float mw = exp(-pow(dot(d, normalize(vec3(0.35, 0.25, 1.0))) * 3.2, 2.0)) * (0.5 + 0.8 * fbm(d * 18.0)) * 0.05;
        col += (vec3(0.8, 0.85, 1.0) * stars * 1.4 + vec3(0.55, 0.6, 0.9) * mw) * nk * clamp(h * 5.0, 0.0, 1.0) * (1.0 - cl * 0.9);
        // луна: диск с «морями» и ореолом
        float disc = smoothstep(0.99953, 0.99968, md);
        float maria = 0.65 + 0.35 * fbm(d * 160.0);
        col += vec3(0.9, 0.93, 1.0) * disc * maria * 3.6 * nk * (1.0 - cl * 0.75) + vec3(0.25, 0.3, 0.45) * pow(md, 40.0) * 0.5 * nk;
        vec3 ccol = mix(vec3(0.02, 0.028, 0.045) + vec3(0.14, 0.16, 0.24) * pow(md, 5.0), vec3(0.78, 0.8, 0.84), dayK);
        col = mix(col, ccol, cl * mix(0.8, 0.45, dayK));
        gl_FragColor = vec4(col, 1.0);
      }`,
    side: THREE.BackSide, depthWrite: false, fog: false,
  });
  SKY.mesh = new THREE.Mesh(new THREE.SphereGeometry(450, 32, 16), mat); SKY.mesh.renderOrder = -1; SKY.mesh.frustumCulled = false; scene.add(SKY.mesh);
  SKY.mat = mat;
  SKY.sun = new THREE.DirectionalLight(0xfff0dc, 2); SKY.sun.castShadow = QUALITY[quality].sun;
  const sc = SKY.sun.shadow.camera; sc.left = -45; sc.right = 45; sc.top = 45; sc.bottom = -45; sc.near = 1; sc.far = 260;
  SKY.sun.shadow.mapSize.set(QUALITY[quality].map, QUALITY[quality].map); SKY.sun.shadow.bias = -0.0005; SKY.sun.shadow.normalBias = 0.04;
  scene.add(SKY.sun); scene.add(SKY.sun.target);
  SKY.moon = new THREE.DirectionalLight(0x8fa6d8, 0.2); scene.add(SKY.moon); scene.add(SKY.moon.target);
  SKY.hemi = new THREE.HemisphereLight(0x9ab0c8, 0x2a2618, 0.5); scene.add(SKY.hemi);
  SKY.lampLights = [];
  for (let i = 0; i < QUALITY[quality].lamps; i++) { const l = new THREE.PointLight(0xffc684, 0, 17, 2); l.position.set(0, -50, 0); scene.add(l); SKY.lampLights.push(l); }
}
// clock — минуты от полуночи
function dayFactor(clock) {
  const a = (clock - 360) / 840 * Math.PI; // 06:00 → 20:00
  return clamp(Math.sin(a) * 3 + 0.15, 0, 1);
}
const _fogDay = new THREE.Color(0.6, 0.65, 0.7), _fogNight = new THREE.Color(0.024, 0.032, 0.05), _fogDusk = new THREE.Color(0.45, 0.28, 0.2);
function updateSky(clock, px, pz) {
  const a = (clock - 360) / 840 * Math.PI;
  const sun = new THREE.Vector3(Math.cos(a) * 0.8, Math.sin(a), 0.45).normalize();
  const ma = (clock - 1260 + (clock < 600 ? 1440 : 0)) / 600 * Math.PI;
  const moon = new THREE.Vector3(-Math.cos(ma) * 0.7, Math.max(0.25, Math.sin(ma)), -0.5).normalize();
  const dk = dayFactor(clock), dusk = clamp(1 - Math.abs(sun.y) * 5, 0, 1) * (sun.y > -0.15 ? 1 : 0);
  SKY.dk = dk; const u = SKY.mat.uniforms; u.time.value = performance.now() / 1000; u.sunDir.value.copy(sun); u.moonDir.value.copy(moon); u.dayK.value = dk; u.duskK.value = dusk;
  SKY.mesh.position.copy(camera.position);
  SKY.sun.intensity = 2.4 * dk; SKY.sun.color.setRGB(1, 0.85 + 0.15 * dk, 0.7 + 0.28 * dk);
  SKY.sun.position.set(px + sun.x * 120, sun.y * 120, pz + sun.z * 120); SKY.sun.target.position.set(px, 0, pz);
  SKY.sun.visible = dk > 0.02;
  SKY.moon.intensity = 0.26 * (1 - dk); SKY.moon.position.set(px + moon.x * 100, moon.y * 100, pz + moon.z * 100); SKY.moon.target.position.set(px, 0, pz);
  SKY.hemi.intensity = 0.085 + 0.55 * dk;
  SKY.hemi.color.setRGB(0.25 + 0.4 * dk, 0.3 + 0.4 * dk, 0.45 + 0.35 * dk);
  const tt = performance.now() / 1000; SKY.fogK = 1 + 0.2 * Math.sin(tt * 0.045) + 0.1 * Math.sin(tt * 0.13 + 1.3) + (clock > 240 && clock < 380 ? 0.35 : 0); // предрассветный туман гуще
  scene.fog.density = lerp(0.038, 0.0085, dk) * SKY.fogK;
  scene.fog.color.copy(_fogNight).lerp(_fogDay, dk).lerp(_fogDusk, dusk * 0.35);
  MT.winLit.emissiveIntensity = (1 - dk) * 1.7;
  return dk;
}


// ---------------------------------------------------------------------
//  Приземный туман: билборды-клочья вокруг игрока + ореолы фонарей
// ---------------------------------------------------------------------
function buildMist() {
  const n = [34, 60, 96][quality], geo = new THREE.InstancedBufferGeometry(); geo.copy(new THREE.PlaneGeometry(1, 1));
  const off = new Float32Array(n * 3), sc = new Float32Array(n), ph = new Float32Array(n);
  for (let i = 0; i < n; i++) { off[i * 3] = rand(-58, 58); off[i * 3 + 1] = rand(1.0, 2.6); off[i * 3 + 2] = rand(-58, 58); sc[i] = rand(8, 17); ph[i] = rand(0.3, 1.2); }
  geo.setAttribute('off', new THREE.InstancedBufferAttribute(off, 3)); geo.setAttribute('sc', new THREE.InstancedBufferAttribute(sc, 1));
  geo.instanceCount = n;
  const mat = new THREE.ShaderMaterial({
    uniforms: { tMap: { value: TX.mist }, color: { value: new THREE.Color(0.1, 0.12, 0.16) }, opacity: { value: 0.2 } },
    vertexShader: 'attribute vec3 off; attribute float sc; varying vec2 vUv; varying float vZ; void main(){ vUv = uv; vec4 mv = modelViewMatrix * vec4(off, 1.0); mv.xy += position.xy * sc; vZ = -mv.z; gl_Position = projectionMatrix * mv; }',
    fragmentShader: 'uniform sampler2D tMap; uniform vec3 color; uniform float opacity; varying vec2 vUv; varying float vZ; void main(){ float a = texture2D(tMap, vUv).a * opacity * smoothstep(2.0, 9.0, vZ) * (1.0 - smoothstep(45.0, 70.0, vZ)); gl_FragColor = vec4(color, a); }',
    transparent: true, depthWrite: false, fog: false,
  });
  const m = new THREE.Mesh(geo, mat); m.frustumCulled = false; m.renderOrder = 5; scene.add(m);
  SKY.mist = { m, mat, off, ph, n, geo };
}
function updateMist(dt, dk, px, pz) {
  const M = SKY.mist; if (!M) return;
  const nk = 1 - dk, fk = SKY.fogK || 1, o = M.off;
  M.mat.uniforms.opacity.value = (0.07 + 0.2 * nk) * fk;
  M.mat.uniforms.color.value.setRGB(lerp(0.06, 0.72, dk), lerp(0.075, 0.76, dk), lerp(0.11, 0.8, dk));
  const wx = 0.6, wz = 0.25;
  for (let i = 0; i < M.n; i++) {
    o[i * 3] += wx * M.ph[i] * dt; o[i * 3 + 2] += wz * M.ph[i] * dt;
    if (o[i * 3] - px > 60) o[i * 3] -= 120; else if (o[i * 3] - px < -60) o[i * 3] += 120;
    if (o[i * 3 + 2] - pz > 60) o[i * 3 + 2] -= 120; else if (o[i * 3 + 2] - pz < -60) o[i * 3 + 2] += 120;
  }
  M.geo.attributes.off.needsUpdate = true;
}
function updateHalos(dk) {
  if (!SKY.halos && Town.lamps.length) {
    SKY.halos = Town.lamps.map(l => {
      const mk = (size, op, col) => { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: TX.dot, color: col, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, fog: false, opacity: 0 })); sp.scale.set(size, size, 1); sp.position.set(l.x, 5.4, l.z); scene.add(sp); return sp; };
      return { l, a: mk(1.4, 1, 0xffd9a0), b: mk(9, 0.3, 0xff9a4a) };
    });
  }
  if (!SKY.halos) return;
  const fk = SKY.fogK || 1;
  for (const h of SKY.halos) { const v = h.l.level; h.a.material.opacity = v; h.b.material.opacity = v * 0.22 * fk; h.a.visible = h.b.visible = v > 0.01; }
}

// ---------------------------------------------------------------------
//  Фонари: включаются в темноте, мигают, ломаются; ближайшие дают свет
// ---------------------------------------------------------------------
let lampAssignT = 0;
function updateLamps(dt, dk, px, pz) {
  const head = Town.lampMeshes.head, pool = Town.lampMeshes.pool, hc = head.instanceColor.array, pc = pool.instanceColor.array;
  const wantOn = dk < 0.35;
  for (const l of Town.lamps) {
    let lv = wantOn && !l.broken ? 1 : 0;
    if (lv && l.flicker) { l.flickT -= dt; if (l.flickT <= 0) { l.flickT = rand(0.04, 0.4); l.fl = Math.random() < 0.3 ? rand(0, 0.3) : 1; } lv *= l.fl ?? 1; }
    if (l.dying > 0) { l.dying -= dt; lv *= Math.random() < 0.5 ? 0 : rand(0.3, 1); if (l.dying <= 0) { l.broken = true; lv = 0; } }
    l.level = lv;
    const k = lv * 5;
    hc[l.i * 3] = 0.06 + k; hc[l.i * 3 + 1] = 0.06 + k * 0.78; hc[l.i * 3 + 2] = 0.05 + k * 0.5;
    const pk = lv * 0.32; pc[l.i * 3] = pk; pc[l.i * 3 + 1] = pk * 0.8; pc[l.i * 3 + 2] = pk * 0.55;
  }
  head.instanceColor.needsUpdate = true; pool.instanceColor.needsUpdate = true;
  lampAssignT -= dt;
  if (lampAssignT <= 0) {
    lampAssignT = 0.4;
    const near = Town.lamps.filter(l => !l.broken && wantOn).sort((a, b) => Math.hypot(a.x - px, a.z - pz) - Math.hypot(b.x - px, b.z - pz));
    SKY.lampLights.forEach((L, i) => { const l = near[i]; L.userData.lamp = l || null; if (l) L.position.set(l.x, 5.2, l.z); });
  }
  for (const L of SKY.lampLights) L.intensity = L.userData.lamp ? 1.5 * L.userData.lamp.level : 0;
  updateHalos(dk); if (!SKY.mist) buildMist(); updateMist(dt, dk, px, pz);
}

// ---------------------------------------------------------------------
//  Фонарик игрока
// ---------------------------------------------------------------------
const FL = {};
function buildFlashlight() {
  FL.spot = new THREE.SpotLight(0xfff0d8, 0, 26, 0.5, 0.5, 1.5);
  FL.spot.castShadow = QUALITY[quality].shadow;
  if (FL.spot.castShadow) { FL.spot.map = TX.cookie; FL.spot.shadow.mapSize.set(1024, 1024); }
  FL.spot.shadow.bias = -0.0006; FL.spot.shadow.normalBias = 0.03; FL.spot.shadow.camera.near = 0.2; FL.spot.shadow.camera.far = 26;
  FL.target = new THREE.Object3D(); scene.add(FL.target); FL.spot.target = FL.target; scene.add(FL.spot);
  FL.fill = new THREE.PointLight(0xffe8c8, 0, 3.5, 2); scene.add(FL.fill);
  FL.room = new THREE.PointLight(0xdfe6f0, 0, 9, 1.5); scene.add(FL.room);
  const bg = new THREE.CylinderGeometry(0.025, 3.2, 9, 40, 1, true); bg.translate(0, -4.5, 0); bg.rotateX(-Math.PI / 2);
  FL.beam = new THREE.Mesh(bg, beamMaterial(9)); FL.beam.frustumCulled = false; scene.add(FL.beam);
  FL.dir = new THREE.Vector3(0, 0, -1);
}
function beamMaterial(len) {
  return new THREE.ShaderMaterial({
    uniforms: { k: { value: 0.04 }, col: { value: new THREE.Color(1, 0.94, 0.84) } },
    vertexShader: `varying float vL; varying vec3 vN; varying vec3 vV; void main(){ vL = position.z / ${len.toFixed(1)}; vec4 mv = modelViewMatrix * vec4(position, 1.0); vV = normalize(-mv.xyz); vN = normalize(normalMatrix * normal); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: 'uniform float k; uniform vec3 col; varying float vL; varying vec3 vN; varying vec3 vV; void main(){ float e = pow(abs(dot(vN, vV)), 2.5); float a = k * e * pow(1.0 - vL, 1.6) * smoothstep(0.0, 0.05, vL); gl_FragColor = vec4(col * a, 1.0); }',
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide,
  });
}
const _cd = new THREE.Vector3(), _r = new THREE.Vector3();
function updateFlashlight(dt, on, flick, dk) {
  camera.getWorldDirection(_cd);
  FL.dir.lerp(_cd, Math.min(1, dt * 12)).normalize();
  _r.set(Math.cos(camera.rotation.y), 0, -Math.sin(camera.rotation.y));
  FL.spot.position.copy(camera.position).addScaledVector(_r, 0.16).add(new THREE.Vector3(0, -0.2, 0)).addScaledVector(_cd, 0.1);
  FL.target.position.copy(FL.spot.position).addScaledVector(FL.dir, 6);
  FL.spot.intensity = on ? 3.4 * flick : 0;
  FL.fill.position.copy(camera.position); FL.fill.intensity = on ? 0.2 * flick : 0;
  FL.beam.visible = on && flick > 0.2 && dk < 0.6;
  FL.beam.position.copy(FL.spot.position); FL.beam.lookAt(FL.target.position);
  FL.beam.material.uniforms.k.value = 0.045 * flick * (1 - dk);
}

// ---------------------------------------------------------------------
//  Снег
// ---------------------------------------------------------------------
const SNOW = {};
function buildSnow() {
  const N = quality === 0 ? 700 : 1800, p = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { p[i * 3] = rand(-30, 30); p[i * 3 + 1] = rand(0, 22); p[i * 3 + 2] = rand(-30, 30); }
  SNOW.geo = new THREE.BufferGeometry(); SNOW.geo.setAttribute('position', new THREE.BufferAttribute(p, 3));
  SNOW.pts = new THREE.Points(SNOW.geo, new THREE.PointsMaterial({ size: 0.07, map: TX.dot, color: 0xe8eef8, transparent: true, opacity: 0.75, depthWrite: false }));
  SNOW.pts.frustumCulled = false; scene.add(SNOW.pts); SNOW.ox = 0; SNOW.oz = 0;
}
function updateSnow(dt, t, px, pz) {
  const p = SNOW.geo.attributes.position.array;
  for (let i = 0; i < p.length; i += 3) {
    p[i + 1] -= dt * (1.2 + (i % 7) * 0.12);
    p[i] += Math.sin(t * 0.7 + i) * dt * 0.4 + dt * 0.6;
    if (p[i + 1] < 0) { p[i + 1] = 22; p[i] = px + rand(-30, 30); p[i + 2] = pz + rand(-30, 30); }
    if (p[i] - px > 30) p[i] -= 60; else if (p[i] - px < -30) p[i] += 60;
    if (p[i + 2] - pz > 30) p[i + 2] -= 60; else if (p[i + 2] - pz < -30) p[i + 2] += 60;
  }
  SNOW.geo.attributes.position.needsUpdate = true;
}

// ---------------------------------------------------------------------
//  Постобработка
// ---------------------------------------------------------------------
const POST_FS = `
uniform sampler2D tColor; uniform sampler2D tDepth;
uniform vec2 res; uniform float time; uniform float near; uniform float far;
uniform float night; uniform float exposure; uniform float danger; uniform float aoOn; uniform float thr; uniform float hurt;
varying vec2 vUv;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float linD(vec2 uv) { float d = texture2D(tDepth, uv).x; return near * far / (far - d * (far - near)); }
vec3 wRRT(vec3 v) { vec3 a = v * (v + 0.0245786) - 0.000090537; vec3 b = v * (0.983729 * v + 0.4329510) + 0.238081; return a / b; }
vec3 wAces(vec3 c) {
  const mat3 I = mat3(vec3(0.59719, 0.07600, 0.02840), vec3(0.35458, 0.90834, 0.13383), vec3(0.04823, 0.01566, 0.83777));
  const mat3 O = mat3(vec3(1.60475, -0.10208, -0.00327), vec3(-0.53108, 1.10813, -0.07276), vec3(-0.07367, -0.00605, 1.07602));
  c *= exposure / 0.6; c = I * c; c = wRRT(c); c = O * c; return clamp(c, 0.0, 1.0);
}
void main() {
  vec2 uv = vUv, px = 1.0 / res, dc = uv - 0.5; float r2 = dot(dc, dc);
  vec2 ca = dc * (0.003 + 0.01 * danger);
  vec3 col = vec3(texture2D(tColor, uv - ca).r, texture2D(tColor, uv).g, texture2D(tColor, uv + ca).b);
  if (aoOn > 0.5) {
    float d = linD(uv);
    if (d < 60.0) {
      float occ = 0.0, rnd = hash(gl_FragCoord.xy) * 6.2831, rad = clamp(0.5 / d, 0.003, 0.06);
      for (int i = 0; i < 12; i++) {
        float fi = float(i), a = fi * 2.39996 + rnd, rr = (fi + 0.5) / 12.0;
        float diff = d - linD(uv + vec2(cos(a) * res.y / res.x, sin(a)) * rr * rad);
        occ += smoothstep(0.03, 0.2, diff) * (1.0 - smoothstep(0.4, 1.2, diff));
      }
      col *= 1.0 - 0.65 * occ / 12.0;
    }
  }
  vec3 bl = vec3(0.0); float bs = res.y / 720.0;
  for (int i = 0; i < 16; i++) { float fi = float(i), a = fi * 2.39996; bl += max(texture2D(tColor, uv + vec2(cos(a), sin(a)) * (3.0 + fi * 2.8) * bs * px).rgb - thr, 0.0); }
  col += bl / 16.0 * 1.1;
  col = wAces(col);
  float l = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(l), col, 0.82);
  col *= mix(vec3(0.86, 0.96, 1.1), vec3(1.05, 1.0, 0.92), smoothstep(0.0, 0.45, l));
  col = mix(col, vec3(dot(col, vec3(0.299, 0.587, 0.114))) * vec3(0.82, 0.95, 1.22), night * 0.4);
  col += vec3(0.0, 0.004, 0.014) * night;
  col = pow(col, vec3(1.0 / 2.2));
  col = (col - 0.5) * 1.06 + 0.5;
  col *= 1.0 - smoothstep(0.18, 0.85, r2 * 1.7) * (0.55 + 0.22 * night);
  col = mix(col, vec3(0.4, 0.0, 0.0), danger * smoothstep(0.08, 0.6, r2 * 1.7) * (0.75 + 0.25 * sin(time * (4.0 + 8.0 * danger))));
  col = mix(col, vec3(0.55, 0.0, 0.0), hurt * 0.6);
  col += (hash(uv * res + fract(time * 7.0) * 113.0) - 0.5) * (0.055 + 0.03 * night);
  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;
function setupPost() {
  const q = QUALITY[quality];
  if (!q.post || !renderer.capabilities.isWebGL2) return;
  const hdr = renderer.extensions.has('EXT_color_buffer_float') || renderer.extensions.has('EXT_color_buffer_half_float');
  const rt = new THREE.WebGLRenderTarget(4, 4, { type: hdr ? THREE.HalfFloatType : THREE.UnsignedByteType });
  rt.depthTexture = new THREE.DepthTexture(4, 4); rt.depthTexture.type = THREE.UnsignedIntType;
  const mat = new THREE.ShaderMaterial({
    uniforms: { tColor: { value: rt.texture }, tDepth: { value: rt.depthTexture }, res: { value: new THREE.Vector2(4, 4) }, time: { value: 0 },
                near: { value: camera.near }, far: { value: camera.far }, exposure: { value: 1.35 }, night: { value: 0 }, danger: { value: 0 }, hurt: { value: 0 },
                aoOn: { value: q.ao ? 1 : 0 }, thr: { value: hdr ? 1.0 : 0.88 } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: POST_FS, depthTest: false, depthWrite: false,
  });
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), mat); quad.frustumCulled = false;
  const ps = new THREE.Scene(); ps.add(quad);
  post = { rt, mat, ps, pc: new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1) };
  resize();
}
function renderFrame(danger, hurt) {
  if (!post) { renderer.render(scene, camera); return; }
  renderer.setRenderTarget(post.rt); renderer.render(scene, camera); renderer.setRenderTarget(null);
  const u = post.mat.uniforms; u.time.value = performance.now() / 1000; u.danger.value = danger; u.hurt.value = hurt; u.night.value = 1 - (SKY.dk ?? 1);
  renderer.render(post.ps, post.pc);
}

// ---------------------------------------------------------------------
//  Звук
// ---------------------------------------------------------------------
const AU = {};
function initAudio() {
  if (AU.ctx) { AU.ctx.resume(); return; }
  let ctx; try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { return; }
  AU.ctx = ctx;
  const comp = ctx.createDynamicsCompressor(); comp.connect(ctx.destination);
  AU.master = ctx.createGain(); AU.master.gain.value = 0.9; AU.master.connect(comp);
  const nb = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = nb.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  AU.noise = nb;
  const wind = ctx.createBufferSource(); wind.buffer = nb; wind.loop = true;
  AU.windF = ctx.createBiquadFilter(); AU.windF.type = 'bandpass'; AU.windF.frequency.value = 350; AU.windF.Q.value = 0.6;
  AU.windG = ctx.createGain(); AU.windG.gain.value = 0.05;
  const lfo = ctx.createOscillator(); lfo.frequency.value = 0.06; const lg = ctx.createGain(); lg.gain.value = 200; lfo.connect(lg); lg.connect(AU.windF.frequency); lfo.start();
  wind.connect(AU.windF); AU.windF.connect(AU.windG); AU.windG.connect(AU.master); wind.start();
  AU.chase = ctx.createGain(); AU.chase.gain.value = 0;
  const cf = ctx.createBiquadFilter(); cf.type = 'lowpass'; cf.frequency.value = 650;
  for (const fr of [49, 51.9, 73.4, 98.7]) { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = fr; o.connect(cf); o.start(); }
  cf.connect(AU.chase); AU.chase.connect(AU.master);
}
const anow = () => AU.ctx.currentTime;
function aout(pan, muffle) {
  let node = AU.master;
  if (AU.ctx.createStereoPanner) { const p = AU.ctx.createStereoPanner(); p.pan.value = clamp(pan, -1, 1); p.connect(node); node = p; }
  if (muffle) { const f = AU.ctx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = muffle; f.connect(node); node = f; }
  return node;
}
function noiseHit(vol, freq, dur, pan = 0, muffle = 0, type = 'lowpass') {
  if (!AU.ctx || vol < 0.003) return;
  const t = anow(), s = AU.ctx.createBufferSource(); s.buffer = AU.noise;
  const f = AU.ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq;
  const g = AU.ctx.createGain(); g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  s.connect(f); f.connect(g); g.connect(aout(pan, muffle)); s.start(t, Math.random() * 1.5); s.stop(t + dur + 0.05);
}
function tone(type, f0, f1, vol, dur, pan = 0, delay = 0, muffle = 0) {
  if (!AU.ctx || vol < 0.003) return;
  const t = anow() + delay, o = AU.ctx.createOscillator(), g = AU.ctx.createGain();
  o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(1, f1), t + dur);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(aout(pan, muffle)); o.start(t); o.stop(t + dur + 0.05);
}
function spatial(x, z, maxD) {
  const dx = x - camera.position.x, dz = z - camera.position.z, d = Math.hypot(dx, dz);
  const yaw = camera.rotation.y, rx = Math.cos(yaw), rz = -Math.sin(yaw);
  return { vol: Math.pow(clamp(1 - d / maxD, 0, 1), 1.5), pan: d > 0.1 ? (dx * rx + dz * rz) / d * 0.8 : 0, muffle: sightClear(camera.position.x, camera.position.z, x, z) ? 0 : 700, d };
}
const SFX = {
  step(vol, surf, pan = 0, muffle = 0, heavy) {
    const f = heavy ? 220 : surf === 'wood' ? 900 : surf === 'grass' ? 1800 : 1300;
    noiseHit(vol * (heavy ? 0.9 : 0.45), f, heavy ? 0.18 : 0.08, pan, muffle, surf === 'grass' && !heavy ? 'bandpass' : 'lowpass');
    if (heavy || surf === 'wood') tone('sine', heavy ? 60 : 120, 40, vol * (heavy ? 0.6 : 0.2), 0.12, pan, 0, muffle);
  },
  door(vol, pan, muffle) {
    if (!AU.ctx) return;
    const t = anow(), dur = rand(0.5, 0.9), o = AU.ctx.createOscillator(), g = AU.ctx.createGain(), f = AU.ctx.createBiquadFilter(), l = AU.ctx.createOscillator(), lg = AU.ctx.createGain();
    o.type = 'sawtooth'; o.frequency.setValueAtTime(rand(150, 220), t); o.frequency.linearRampToValueAtTime(rand(90, 150), t + dur);
    l.frequency.value = rand(18, 30); lg.gain.value = 25; l.connect(lg); lg.connect(o.frequency);
    f.type = 'bandpass'; f.frequency.value = 1100; f.Q.value = 3;
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vol * 0.45, t + 0.08); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(f); f.connect(g); g.connect(aout(pan, muffle)); o.start(t); l.start(t); o.stop(t + dur + 0.05); l.stop(t + dur + 0.05);
  },
  bash(vol, pan, muffle) { noiseHit(vol, 400, 0.35, pan, muffle); tone('sine', 80, 30, vol, 0.35, pan, 0, muffle); noiseHit(vol * 0.5, 2500, 0.15, pan, muffle, 'highpass'); },
  howl(vol, pan, muffle) {
    if (!AU.ctx || vol < 0.01) return;
    const t = anow(), o = AU.ctx.createOscillator(), vib = AU.ctx.createOscillator(), vg = AU.ctx.createGain(), g = AU.ctx.createGain();
    o.type = 'sawtooth'; o.frequency.setValueAtTime(170, t); o.frequency.linearRampToValueAtTime(430, t + 0.9); o.frequency.linearRampToValueAtTime(300, t + 2.4); o.frequency.linearRampToValueAtTime(140, t + 3.4);
    vib.frequency.value = 6.5; vg.gain.value = 14; vib.connect(vg); vg.connect(o.frequency);
    const out = aout(pan, muffle || 2400);
    for (const [fr, q] of [[700, 6], [1150, 7], [2600, 8]]) { const f = AU.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = fr; f.Q.value = q; o.connect(f); f.connect(g); }
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(vol * 1.6, t + 0.5); g.gain.linearRampToValueAtTime(vol * 1.2, t + 2.4); g.gain.exponentialRampToValueAtTime(0.0001, t + 3.6);
    g.connect(out); o.start(t); vib.start(t); o.stop(t + 3.7); vib.stop(t + 3.7);
    noiseHit(vol * 0.2, 1500, 3.0, pan, muffle, 'bandpass');
  },
  screech(vol, pan) {
    if (!AU.ctx) return; noiseHit(vol * 0.7, 3500, 0.9, pan);
    for (const f of [900, 1350]) { const t = anow(), o = AU.ctx.createOscillator(), g = AU.ctx.createGain(); o.type = 'sawtooth'; o.frequency.setValueAtTime(f, t); o.frequency.linearRampToValueAtTime(f * 2.4, t + 0.25); o.frequency.exponentialRampToValueAtTime(f * 0.5, t + 0.9);
      g.gain.setValueAtTime(vol * 0.25, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.95); o.connect(g); g.connect(aout(pan)); o.start(t); o.stop(t + 1); }
  },
  clicks(vol, pan, muffle) { for (let i = 0; i < 6; i++) setTimeout(() => noiseHit(vol * rand(0.5, 1), 3800, 0.025, pan, muffle, 'highpass'), i * rand(50, 110)); },
  growl(vol, pan, muffle) { tone('sawtooth', 70, 55, vol * 0.5, 1.4, pan, 0, muffle || 500); noiseHit(vol * 0.3, 300, 1.2, pan, muffle); },
  hit() { noiseHit(0.9, 1800, 0.25); tone('sine', 120, 40, 0.8, 0.3); tone('square', 300, 90, 0.2, 0.3); },
  heart(vol) { tone('sine', 65, 30, vol, 0.18); tone('sine', 60, 28, vol * 0.7, 0.18, 0, 0.17); },
  eat() { for (let i = 0; i < 4; i++) setTimeout(() => noiseHit(0.18, 1200, 0.07, 0, 0, 'bandpass'), i * 160); },
  drink() { for (let i = 0; i < 4; i++) setTimeout(() => tone('sine', rand(300, 420), 180, 0.12, 0.12), i * 220); },
  coin() { tone('triangle', 1800, 1800, 0.1, 0.25); tone('triangle', 2400, 2400, 0.08, 0.3, 0, 0.08); },
  pickup() { [660, 990].forEach((f, i) => tone('triangle', f, f, 0.1, 0.35, 0, i * 0.07)); },
  bell() { [1320, 1760].forEach((f, i) => tone('sine', f, f, 0.12, 1.2, 0, i * 0.12)); },
  click() { noiseHit(0.12, 4000, 0.03, 0, 0, 'highpass'); },
  bird(pan) { const b = rand(2200, 3400); for (let i = 0; i < 3; i++) tone('sine', b, b * rand(1.1, 1.4), 0.03, 0.12, pan, i * 0.15); },
  owl(pan) { tone('sine', 420, 380, 0.06, 0.35, pan, 0, 900); tone('sine', 400, 360, 0.06, 0.5, pan, 0.5, 900); },
  breath(vol) { noiseHit(vol, 1400, 0.45, 0, 0, 'bandpass'); },
};
