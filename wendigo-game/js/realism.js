'use strict';
// =====================================================================
//  Реализм: руки с фонариком, ветер в листве и траве, пар изо рта,
//  пылинки в луче фонаря, тёплый свет в жилых домах
// =====================================================================
const RL = { t: 0 };
const WIND_U = { value: 0 };

// ---- ветер: смещение вершин крон и травы в шейдере (инстансы) ----
function addWind(mat, h0, amp) {
  if (!mat || mat.userData.wind) return; mat.userData.wind = true;
  mat.onBeforeCompile = sh => {
    sh.uniforms.uWind = WIND_U;
    sh.vertexShader = 'uniform float uWind;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      #ifdef USE_INSTANCING
        vec2 ip = vec2(instanceMatrix[3].x, instanceMatrix[3].z);
      #else
        vec2 ip = vec2(0.0);
      #endif
      float hw = max(0.0, position.y - ${h0.toFixed(2)}) * ${amp.toFixed(4)};
      float gust = 0.6 + 0.4 * sin(uWind * 0.23 + ip.x * 0.05);
      transformed.x += sin(uWind * 1.15 + ip.x * 0.35 + ip.y * 0.21 + position.y * 0.3) * hw * gust;
      transformed.z += cos(uWind * 0.93 + ip.x * 0.27 + ip.y * 0.33 + position.x * 0.4) * hw * 0.7 * gust;`);
  };
  mat.needsUpdate = true;
}
function setupWind() {
  addWind(MT.pine, 1.5, 0.012);
  addWind(MT.birchLeaf, 2.5, 0.016);
  addWind(MT.tuft, 0.0, 0.16);
}

// ---- руки игрока с фонариком (видны от первого лица) ----
function buildViewmodel() {
  const g = new THREE.Group(); camera.add(g); RL.vm = g;
  const M = (c, r = 0.8, m = 0) => new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: m });
  const sleeve = M(0x3a4a3a, 0.95), skin = M(0x2e2a26, 0.85), metal = M(0x2a2c30, 0.35, 0.8), rubber = M(0x151515, 0.9);
  const add = (geo, mat, x, y, z, rx = 0, ry = 0, rz = 0) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.rotation.set(rx, ry, rz); g.add(m); return m; };
  // рукав и манжета
  add(new THREE.CapsuleGeometry(0.048, 0.3, 6, 12), sleeve, 0.035, -0.055, 0.2, Math.PI / 2 - 0.15, 0, 0);
  add(new THREE.CylinderGeometry(0.06, 0.062, 0.05, 14), M(0x2a362a, 0.95), 0.02, -0.035, 0.03, Math.PI / 2 - 0.15, 0, 0);
  // кисть
  const hand = add(new THREE.SphereGeometry(0.05, 14, 10), skin, 0.0, -0.02, -0.02); hand.scale.set(0.95, 0.8, 1.25);
  for (let i = 0; i < 4; i++) { const f = add(new THREE.CapsuleGeometry(0.0125, 0.045, 4, 8), skin, -0.03 + i * 0.018, -0.005 + Math.abs(i - 1.5) * 0.004, -0.075, 0.2, 0, Math.PI / 2); f.scale.set(1, 1, 1); }
  add(new THREE.CapsuleGeometry(0.014, 0.04, 4, 8), skin, 0.045, 0.02, -0.05, 0.6, 0, -0.5); // большой палец
  // фонарик: корпус, рифление, голова, линза
  add(new THREE.CylinderGeometry(0.02, 0.02, 0.2, 16), metal, -0.005, 0.012, -0.09, Math.PI / 2, 0, 0);
  for (let i = 0; i < 5; i++) add(new THREE.TorusGeometry(0.0205, 0.0025, 6, 16), rubber, -0.005, 0.012, -0.02 - i * 0.02, 0, 0, 0);
  add(new THREE.CylinderGeometry(0.032, 0.022, 0.05, 18), metal, -0.005, 0.012, -0.21, Math.PI / 2, 0, 0);
  RL.lens = new THREE.MeshBasicMaterial({ color: 0x222222 });
  add(new THREE.CircleGeometry(0.028, 18), RL.lens, -0.005, 0.012, -0.236, 0, 0, 0);
  add(new THREE.BoxGeometry(0.012, 0.008, 0.02), M(0xa82a20, 0.5), -0.005, 0.034, -0.1); // кнопка
  g.traverse(o => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; } });
  RL.base = new THREE.Vector3(0.24, -0.25, -0.42); g.position.copy(RL.base);
  RL.lag = { yaw: 0, pitch: 0, py: 0, pp: 0, low: 0 };
}
function updateViewmodel(dt) {
  const g = RL.vm; if (!g) return;
  g.visible = P.alive && G.state === 'play';
  if (!g.visible) return;
  const L = RL.lag;
  const dy = angWrap(P.yaw - L.py), dp = P.pitch - L.pp; L.py = P.yaw; L.pp = P.pitch;
  L.yaw = lerp(L.yaw, clamp(dy / Math.max(dt, 0.001) * 0.012, -0.08, 0.08), Math.min(1, dt * 8));
  L.pitch = lerp(L.pitch, clamp(dp / Math.max(dt, 0.001) * 0.012, -0.06, 0.06), Math.min(1, dt * 8));
  L.low = lerp(L.low, (P.light ? 0 : 0.07) + (P.running ? 0.05 : 0), Math.min(1, dt * 6));
  const bx = Math.cos(P.bob) * (P.running ? 0.022 : 0.01), by = Math.abs(Math.sin(P.bob)) * (P.running ? 0.026 : 0.012);
  const breathe = Math.sin(G.time * 1.7) * 0.003;
  g.position.set(RL.base.x + bx + L.yaw * 0.5, RL.base.y - by - L.low + breathe - L.pitch * 0.4, RL.base.z + L.low * 0.4);
  g.rotation.set(-L.low * 1.2 + L.pitch, L.yaw * 2, (P.running ? Math.sin(P.bob) * 0.06 : 0) - L.yaw);
  const on = P.light && G.flick > 0.2;
  RL.lens.color.setRGB(on ? 3 : 0.12, on ? 2.8 : 0.12, on ? 2.4 : 0.12);
}

// ---- пар изо рта в холодную ночь ----
function buildBreath() {
  RL.breath = [];
  for (let i = 0; i < 6; i++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: TX.mist, color: 0xd8dde4, transparent: true, depthWrite: false, opacity: 0 }));
    s.visible = false; scene.add(s); RL.breath.push({ s, t: 9, vx: 0, vy: 0, vz: 0 });
  }
  RL.breathT = 1;
}
function updateBreath(dt, dk) {
  if (!RL.breath) return;
  const cold = dk < 0.45 && P.alive && G.state === 'play';
  RL.breathT -= dt;
  if (cold && RL.breathT <= 0) {
    RL.breathT = P.running ? rand(1.0, 1.5) : rand(2.6, 3.6);
    const b = RL.breath.find(x => x.t > 1.6);
    if (b) {
      const fx = -Math.sin(P.yaw), fz = -Math.cos(P.yaw);
      b.t = 0; b.s.visible = true;
      b.s.position.set(camera.position.x + fx * 0.32, camera.position.y - 0.12, camera.position.z + fz * 0.32);
      b.vx = fx * 0.35 + rand(-0.05, 0.05); b.vy = 0.08; b.vz = fz * 0.35 + rand(-0.05, 0.05);
    }
  }
  for (const b of RL.breath) {
    if (b.t > 1.6) { b.s.visible = false; continue; }
    b.t += dt; b.s.position.x += b.vx * dt; b.s.position.y += b.vy * dt; b.s.position.z += b.vz * dt;
    const k = b.t / 1.6, sz = 0.12 + k * 0.5; b.s.scale.set(sz, sz, 1);
    b.s.material.opacity = Math.sin(Math.min(1, k * 3) * Math.PI / 2) * (1 - k) * 0.32;
  }
}

// ---- пылинки и снежинки, видимые только в луче фонаря ----
function buildDust() {
  const n = [80, 160, 260][quality], pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { pos[i * 3] = rand(-5, 5); pos[i * 3 + 1] = rand(0.2, 3); pos[i * 3 + 2] = rand(-5, 5); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.ShaderMaterial({
    uniforms: { cp: { value: new THREE.Vector3() }, dir: { value: new THREE.Vector3(0, 0, -1) }, on: { value: 0 } },
    vertexShader: `uniform vec3 cp; uniform vec3 dir; uniform float on; varying float a;
      void main(){ vec4 mv = modelViewMatrix * vec4(position, 1.0); vec3 d = position - cp; float l = length(d);
        float c = dot(d / max(l, 0.001), dir);
        a = on * smoothstep(0.935, 0.99, c) * smoothstep(0.5, 1.3, l) * (1.0 - smoothstep(4.0, 5.5, l));
        gl_PointSize = clamp(26.0 / -mv.z, 1.0, 5.0); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying float a; void main(){ vec2 q = gl_PointCoord - 0.5; float r = 1.0 - smoothstep(0.2, 0.5, length(q)); gl_FragColor = vec4(vec3(1.0, 0.95, 0.85) * a * r * 0.8, 1.0); }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; scene.add(pts);
  RL.dust = { pts, mat, pos, n };
}
function updateDust(dt, dk) {
  const D = RL.dust; if (!D) return;
  const c = camera.position, p = D.pos;
  for (let i = 0; i < D.n; i++) {
    p[i * 3] += Math.sin(RL.t * 0.7 + i) * 0.05 * dt + 0.08 * dt; p[i * 3 + 1] += (Math.cos(RL.t * 0.5 + i * 1.7) * 0.05 - 0.04) * dt; p[i * 3 + 2] += Math.cos(RL.t * 0.6 + i * 0.3) * 0.05 * dt;
    for (let k = 0; k < 3; k += 2) { const d = p[i * 3 + k] - (k ? c.z : c.x); if (d > 5) p[i * 3 + k] -= 10; else if (d < -5) p[i * 3 + k] += 10; }
    if (p[i * 3 + 1] < 0.1) p[i * 3 + 1] += 3; else if (p[i * 3 + 1] > 3.2) p[i * 3 + 1] -= 3;
  }
  D.pts.geometry.attributes.position.needsUpdate = true;
  D.mat.uniforms.cp.value.copy(FL.spot.position); D.mat.uniforms.dir.value.copy(FL.dir);
  D.mat.uniforms.on.value = P.light && P.alive ? (1 - dk) * (G.flick || 1) : 0;
}

// ---- тёплый свет в жилых (светящихся) домах рядом с игроком ----
function buildHouseLights() {
  RL.hl = [0, 1].map(() => { const l = new THREE.PointLight(0xffb060, 0, 9, 1.6); l.position.set(0, -50, 0); scene.add(l); return l; });
  RL.hlT = 0;
}
function updateHouseLights(dt, dk) {
  if (!RL.hl) return;
  RL.hlT -= dt;
  if (RL.hlT <= 0) {
    RL.hlT = 0.5;
    const near = Town.houses.filter(h => h.lit).map(h => ({ h, d: Math.hypot((h.bounds.x0 + h.bounds.x1) / 2 - P.x, (h.bounds.z0 + h.bounds.z1) / 2 - P.z) })).sort((a, b) => a.d - b.d);
    RL.hl.forEach((l, i) => { const e = near[i]; l.userData.h = e && e.d < 30 ? e.h : null; if (l.userData.h) { const b = l.userData.h.bounds; l.position.set((b.x0 + b.x1) / 2, 2.4, (b.z0 + b.z1) / 2); } });
  }
  const on = clamp((0.5 - dk) * 3, 0, 1);
  for (const l of RL.hl) l.intensity = l.userData.h ? 1.3 * on * (0.95 + 0.05 * Math.sin(RL.t * 9 + l.position.x)) : 0;
}

function buildRealism() { setupWind(); buildViewmodel(); buildBreath(); buildDust(); buildHouseLights(); }
function updateRealism(dt, dk) {
  RL.t += dt; WIND_U.value = RL.t;
  updateViewmodel(dt); updateBreath(dt, dk); updateDust(dt, dk); updateHouseLights(dt, dk);
}
