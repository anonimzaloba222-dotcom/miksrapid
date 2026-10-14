'use strict';
// =====================================================================
//  Вендиго: модель и поведение
// =====================================================================
const WD = { x: 0, z: -200, yaw: 0, state: 'away', speed: 0, path: [], repath: 0, target: -1, lastSeen: null, searchT: 0,
             waitT: 0, cool: 0, retreatT: 0, attackT: 0, phase: 0, stalkT: 0, bash: null, bashT: 0, howlT: 20, senseT: 0, anim: 'walk',
             lastTarget: -1 };
const WM = { root: null, p: {} };

// ---------------------------------------------------------------------
//  Модель
// ---------------------------------------------------------------------
function buildWendigoModel() {
  const root = new THREE.Group(); scene.add(root); WM.root = root;
  const add = (geo, mat, x, y, z, parent) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = true; parent.add(m); return m; };
  const grp = (x, y, z, parent) => { const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g); return g; };
  const bone = MT.bone, skin = MT.skin, dark = new THREE.MeshStandardMaterial({ color: 0x2a2420, roughness: 0.8, map: TX.skin });
  const pelvis = grp(0, 1.42, 0, root); WM.p.pelvis = pelvis;
  add(new THREE.SphereGeometry(0.17, 16, 12), skin, 0, 0, 0, pelvis).scale.set(1.2, 0.7, 0.9);
  // ноги с обратным коленом
  WM.p.legs = [];
  for (const sx of [-1, 1]) {
    const hip = grp(sx * 0.15, 0, 0, pelvis);
    add(new THREE.CapsuleGeometry(0.075, 0.55, 6, 10), skin, 0, -0.3, 0, hip);
    const knee = grp(0, -0.62, 0, hip);
    add(new THREE.CapsuleGeometry(0.05, 0.5, 6, 10), skin, 0, -0.27, 0, knee);
    const ankle = grp(0, -0.56, 0, knee);
    add(new THREE.CapsuleGeometry(0.04, 0.32, 6, 8), dark, 0, -0.17, 0, ankle);
    const foot = add(new THREE.ConeGeometry(0.06, 0.18, 8), MT.claw, 0, -0.36, 0.05, ankle); foot.rotation.x = Math.PI / 2;
    hip.rotation.x = -0.45; knee.rotation.x = 1.0; ankle.rotation.x = -0.6;
    WM.p.legs.push({ hip, knee, ankle });
  }
  // истощённое тело с рёбрами
  const spine = grp(0, 0.05, 0, pelvis); spine.rotation.x = 0.45; WM.p.spine = spine;
  const prof = [[0.001, 0], [0.13, 0.03], [0.15, 0.22], [0.115, 0.42], [0.18, 0.66], [0.225, 0.86], [0.215, 1.0], [0.14, 1.1], [0.001, 1.13]];
  const torso = add(new THREE.LatheGeometry(prof.map(([r, y]) => new THREE.Vector2(r, y)), 28), skin, 0, 0, 0, spine); torso.scale.set(1, 1, 0.68);
  for (let i = 0; i < 9; i++) add(new THREE.SphereGeometry(0.03, 8, 6), bone, 0, 0.15 + i * 0.1, -0.13 + Math.sin(i * 0.4) * 0.01, spine);
  for (let i = 0; i < 5; i++) { const r = add(new THREE.TorusGeometry(0.17 - Math.abs(i - 2) * 0.012, 0.009, 4, 18, Math.PI * 1.15), bone, 0, 0.62 + i * 0.075, 0.0, spine); r.rotation.set(Math.PI / 2, 0, -0.95 * Math.PI / 2 + 0.25); r.scale.set(1, 0.68, 1); }
  // руки до колен с когтями
  WM.p.arms = [];
  for (const sx of [-1, 1]) {
    const sh = grp(sx * 0.24, 1.02, 0, spine);
    add(new THREE.SphereGeometry(0.07, 10, 8), skin, 0, 0, 0, sh);
    add(new THREE.CapsuleGeometry(0.05, 0.62, 6, 10), skin, 0, -0.35, 0, sh);
    const el = grp(0, -0.72, 0, sh);
    add(new THREE.CapsuleGeometry(0.04, 0.62, 6, 10), dark, 0, -0.34, 0, el);
    const hand = grp(0, -0.72, 0, el);
    add(new THREE.SphereGeometry(0.05, 10, 8), dark, 0, 0, 0, hand).scale.set(1, 1.3, 0.6);
    for (let k = 0; k < 4; k++) {
      const f = grp(-0.04 + k * 0.027, -0.04, 0.01, hand); f.rotation.x = 0.25;
      add(new THREE.CapsuleGeometry(0.01, 0.13, 3, 6), dark, 0, -0.08, 0, f);
      const cl = add(new THREE.ConeGeometry(0.012, 0.16, 6), MT.claw, 0, -0.24, 0.02, f); cl.rotation.x = Math.PI + 0.35;
    }
    sh.rotation.z = sx * 0.12; el.rotation.x = -0.35;
    WM.p.arms.push({ sh, el, hand });
  }
  // шея и олений череп
  const neck = grp(0, 1.1, 0.02, spine); neck.rotation.x = -0.25; WM.p.neck = neck;
  add(new THREE.CapsuleGeometry(0.045, 0.3, 6, 10), skin, 0, 0.18, 0, neck);
  const head = grp(0, 0.4, 0.02, neck); WM.p.head = head;
  const skull = add(new THREE.SphereGeometry(0.13, 24, 18), bone, 0, 0.02, 0, head); skull.scale.set(0.95, 0.9, 1.1);
  const snout = add(new THREE.CylinderGeometry(0.045, 0.1, 0.34, 14), bone, 0, -0.04, 0.2, head); snout.rotation.x = Math.PI / 2 + 0.25;
  for (const sx of [-1, 1]) {
    const so = add(new THREE.SphereGeometry(0.045, 12, 10), MT.claw, sx * 0.062, 0.03, 0.085, head); so.scale.set(1, 1.15, 0.6);
    add(new THREE.SphereGeometry(0.012, 8, 6), MT.eye, sx * 0.062, 0.03, 0.11, head).castShadow = false;
    // рога: ветвящиеся отростки
    antler(head, sx, 0, 0.11, -0.02, 0.34, 0.025, 4);
  }
  const jaw = grp(0, -0.09, 0.06, head); WM.p.jaw = jaw;
  const jm = add(new THREE.CylinderGeometry(0.035, 0.07, 0.28, 12), bone, 0, -0.01, 0.13, jaw); jm.rotation.x = Math.PI / 2 + 0.35; jm.scale.set(1, 1, 0.6);
  for (let k = 0; k < 7; k++) { const t = add(new THREE.ConeGeometry(0.008, 0.04, 5), bone, -0.03 + k * 0.01, 0.0, 0.2 - Math.abs(k - 3) * 0.012, jaw); t.rotation.x = Math.PI; }
  root.scale.setScalar(1.08);
  root.position.set(0, 0, -300);
}
function antler(parent, sx, x, y, z, len, r, depth) {
  const g = new THREE.Group(); g.position.set(x, y, z); parent.add(g);
  g.rotation.z = -sx * (depth === 4 ? 0.7 : rand(0.2, 0.6)); g.rotation.x = depth === 4 ? -0.3 : rand(-0.6, 0.4);
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.7, r, len, 6), MT.bone); m.position.y = len / 2; m.castShadow = true; g.add(m);
  if (depth <= 0) return;
  antler(g, sx, 0, len, 0, len * 0.72, r * 0.72, depth - 1);
  if (depth > 1) antler(g, -sx, 0, len * rand(0.4, 0.8), 0, len * 0.55, r * 0.6, depth - 2);
}

// ---------------------------------------------------------------------
//  Анимация (у всех игроков одинаковая, по состоянию из сети)
// ---------------------------------------------------------------------
function animateWendigo(dt, t) {
  const p = WM.p, st = WD.anim, sp = WD.speed;
  const run = st === 'run', stalk = st === 'stalk', s = clamp(sp / 3, 0, 1.6);
  WD.phase += dt * (1.5 + sp * 1.25);
  const ph = WD.phase;
  for (let i = 0; i < 2; i++) {
    const sgn = i ? 1 : -1, sw = Math.sin(ph + (i ? Math.PI : 0));
    p.legs[i].hip.rotation.x = -0.45 - sw * 0.5 * s - (stalk ? 0.4 : 0);
    p.legs[i].knee.rotation.x = 1.0 + Math.max(0, -sw) * 0.6 * s + (stalk ? 0.4 : 0);
    p.legs[i].ankle.rotation.x = -0.6 - Math.max(0, sw) * 0.3 * s;
    const a = p.arms[i];
    a.sh.rotation.x = (run ? -0.9 : -0.1) + Math.sin(ph + (i ? 0 : Math.PI)) * (run ? 0.8 : 0.35) * s;
    a.el.rotation.x = run ? -0.9 : -0.35 - Math.sin(t * 0.7 + i) * 0.05;
    a.sh.rotation.z = sgn * (0.12 + (run ? 0.25 : 0));
  }
  p.spine.rotation.x = run ? 0.95 : stalk ? 0.75 : 0.45 + Math.sin(t * 0.8) * 0.03;
  p.pelvis.position.y = (stalk ? 1.2 : run ? 1.32 : 1.42) + Math.abs(Math.sin(ph)) * 0.05 * s;
  p.neck.rotation.x = run ? -0.75 : stalk ? -0.55 : -0.25;
  p.head.rotation.z = stalk ? Math.sin(t * 2.3) * 0.35 : Math.sin(t * 0.9) * 0.08 + (Math.random() < 0.004 ? rand(-0.5, 0.5) : 0);
  p.jaw.rotation.x = st === 'howl' ? 0.6 + Math.sin(t * 30) * 0.05 : st === 'attack' ? 0.5 : run ? 0.15 + Math.sin(t * 9) * 0.1 : 0.04;
  if (st === 'attack') { const k = clamp(WD.attackT / 0.5, 0, 1); p.arms[1].sh.rotation.x = -2.6 + k * 1.8; p.arms[1].sh.rotation.z = 0.6 - k * 0.8; }
  if (st === 'howl') { p.neck.rotation.x = -1.2; p.spine.rotation.x = 0.25; }
  if (st === 'bash') { p.arms[0].sh.rotation.x = p.arms[1].sh.rotation.x = -1.8 + Math.abs(Math.sin(t * 4)) * 0.6; }
  WM.root.position.set(WD.x, 0, WD.z);
  WM.root.rotation.y = WD.yaw;
  WM.root.visible = WD.state !== 'away';
}

// ---------------------------------------------------------------------
//  Поведение (считает хост или одиночная игра)
// ---------------------------------------------------------------------
const FOREST_GATES = [[-104, -36], [-104, 0], [-104, 36], [104, -36], [104, 0], [104, 36], [-48, -66], [0, -66], [48, -66], [-48, 66], [0, 66], [48, 66]];
let avoidKey = '';
function lampLitAt(x, z, r = 4.6) {
  for (const l of Town.lamps) if (l.level > 0.5 && Math.abs(l.x - x) < r && Math.abs(l.z - z) < r && Math.hypot(l.x - x, l.z - z) < r) return l;
  return null;
}
function updateAvoid() {
  const key = Town.lamps.map(l => l.level > 0.5 ? 1 : 0).join('');
  if (key === avoidKey) return; avoidKey = key;
  NAV.avoid.fill(0);
  for (const l of Town.lamps) if (l.level > 0.5) {
    for (let dz = -5; dz <= 5; dz++) for (let dx = -5; dx <= 5; dx++) if (dx * dx + dz * dz <= 20) NAV.avoid[navIdx(l.x + dx, l.z + dz)] = 1;
  }
}
function wPathTo(x, z, ignoreAvoid) { WD.path = navPath(WD.x, WD.z, x, z, ignoreAvoid); }
function wdSpeed() {
  const n = G.night;
  return { roam: 2.0, investigate: 3.4, search: 2.6, chase: 5.0 + 0.25 * n, retreat: 4.6, leave: 3.6, emerge: 2.4, stalk: 0, bash: 0, attack: 1.0 }[WD.state] || 0;
}
function setWState(s) { if (WD.state !== s) { WD.state = s; WD.repath = 0; } }
function wendigoAI(dt, night) {
  WD.cool -= dt; WD.howlT -= dt;
  const ps = alivePlayers();
  // ---- рассвет: уходит в лес ----
  if (!night) {
    if (WD.state === 'away') return;
    if (WD.state !== 'leave') { setWState('leave'); const g = nearestGate(WD.x, WD.z); wPathTo(g[0], g[1], true); WD.target = -1; }
    if (!WD.path.length || Math.hypot(WD.x - nearestGate(WD.x, WD.z)[0], WD.z - nearestGate(WD.x, WD.z)[1]) < 3) { WD.state = 'away'; WD.x = 0; WD.z = -300; WD.speed = 0; return; }
    followPath(dt, wdSpeed(), true); WD.anim = 'walk'; return;
  }
  // ---- ночь: выходит из леса ----
  if (WD.state === 'away') {
    const g = spick(FOREST_GATES); WD.x = g[0] * 1.06; WD.z = g[1] * 1.06; WD.yaw = Math.atan2(-g[0], -g[1]);
    setWState('howl'); WD.waitT = 3.2; aiEvent('howl', { x: WD.x, z: WD.z }); return;
  }
  if (WD.state === 'howl') { WD.anim = 'howl'; WD.speed = 0; WD.waitT -= dt; if (WD.waitT <= 0) setWState('roam'); return; }
  updateAvoid();

  // ---- чувства ----
  WD.senseT -= dt;
  if (WD.senseT <= 0) {
    WD.senseT = 0.2;
    let best = null, bd = 1e9;
    for (const p of ps) {
      const d = Math.hypot(p.x - WD.x, p.z - WD.z);
      if (p.house >= 0 && p.hiddenDoor && WD.lastTarget !== p.id) continue;
      let range = 9 + (p.light ? 18 : 0) + (p.lamp ? 12 : 0) + (p.running ? 5 : 0);
      if (WD.state === 'chase' && WD.target === p.id) range += 10;
      if (d > range) continue;
      const fwd = Math.cos(Math.atan2(p.x - WD.x, p.z - WD.z) - WD.yaw);
      if (d > 5 && fwd < -0.2 && !(WD.state === 'chase' && WD.target === p.id)) continue;
      if (!sightClear(WD.x, WD.z, p.x, p.z)) continue;
      if (d < bd) { bd = d; best = p; }
    }
    if (best) {
      if (WD.state !== 'chase' && WD.state !== 'attack' && WD.state !== 'stalk' && WD.state !== 'retreat') aiEvent('spot', { id: best.id });
      if (WD.state !== 'attack' && WD.state !== 'retreat' && WD.state !== 'bash') setWState('chase');
      WD.target = best.id; WD.lastTarget = best.id; WD.lastSeen = { x: best.x, z: best.z, t: G.time };
    } else if (WD.state === 'roam' || WD.state === 'search') {
      // слух: бег и хлопки дверей
      for (const p of ps) if (p.running && Math.hypot(p.x - WD.x, p.z - WD.z) < 17) { setWState('investigate'); WD.lastSeen = { x: p.x, z: p.z, t: G.time }; break; }
    }
  }

  const tgt = ps.find(p => p.id === WD.target);
  switch (WD.state) {
    case 'roam': {
      WD.anim = 'walk';
      if (WD.waitT > 0) { WD.waitT -= dt; WD.speed = 0; if (WD.howlT < 0 && Math.random() < 0.01) { WD.howlT = rand(25, 50); setWState('howl'); WD.waitT = 3; aiEvent('howl', { x: WD.x, z: WD.z }); } break; }
      if (!WD.path.length) {
        // идёт к случайному дому или вдоль улицы, чаще — ближе к людям
        let gx, gz;
        if (ps.length && Math.random() < 0.55) { const p = pick(ps); gx = p.x + rand(-14, 14); gz = p.z + rand(-14, 14); }
        else if (Math.random() < 0.5) { const h = pick(Town.houses); gx = h.door.x; gz = h.door.z + (h.rot ? 3 : -3); }
        else { gx = rand(-90, 90); gz = pick(STREETS_Z) + rand(-3, 3); }
        wPathTo(gx, gz); if (!WD.path.length) { WD.waitT = 1; break; }
        WD.waitT = 0;
      }
      if (!followPath(dt, wdSpeed())) WD.waitT = rand(1.5, 4);
      break;
    }
    case 'investigate': case 'search': {
      WD.anim = 'walk';
      if (WD.state === 'search') { WD.searchT -= dt; if (WD.searchT <= 0) { setWState('roam'); WD.path = []; break; } }
      WD.repath -= dt;
      if (WD.repath <= 0) { WD.repath = 1.5; const ls = WD.lastSeen; wPathTo(ls.x + (WD.state === 'search' ? rand(-8, 8) : 0), ls.z + (WD.state === 'search' ? rand(-8, 8) : 0)); }
      if (!followPath(dt, wdSpeed())) { if (WD.state === 'investigate') { setWState('search'); WD.searchT = 10; } else WD.repath = 0; }
      break;
    }
    case 'chase': {
      WD.anim = 'run';
      if (!tgt) { setWState('search'); WD.searchT = 10; break; }
      const d = Math.hypot(tgt.x - WD.x, tgt.z - WD.z);
      if (G.time - WD.lastSeen.t > 3.5) { setWState('search'); WD.searchT = 12; break; }
      // жертва под фонарём — кружит рядом и выжидает
      if (lampLitAt(tgt.x, tgt.z) && d < 14) { setWState('stalk'); WD.stalkT = 0; break; }
      if (d < 1.9 && WD.cool <= 0) { setWState('attack'); WD.attackT = 0.5; break; }
      WD.repath -= dt;
      if (d < 4 && sightClear(WD.x, WD.z, tgt.x, tgt.z)) {
        moveToward(tgt.x, tgt.z, wdSpeed() * dt); WD.speed = wdSpeed();
      } else {
        if (WD.repath <= 0) { WD.repath = 0.4; wPathTo(WD.lastSeen.x, WD.lastSeen.z); }
        if (!followPath(dt, wdSpeed())) { setWState('search'); WD.searchT = 10; }
      }
      break;
    }
    case 'stalk': {
      WD.anim = 'stalk'; WD.speed = 0;
      if (!tgt) { setWState('search'); WD.searchT = 8; break; }
      WD.yaw += angWrap(Math.atan2(tgt.x - WD.x, tgt.z - WD.z) - WD.yaw) * Math.min(1, dt * 4);
      WD.stalkT += dt;
      const lamp = lampLitAt(tgt.x, tgt.z);
      if (!lamp) { setWState('chase'); break; }
      // держится на краю света, медленно обходит
      const d = Math.hypot(tgt.x - WD.x, tgt.z - WD.z);
      if (d > 9) { wPathTo(tgt.x, tgt.z); followPath(dt, 1.4); WD.speed = 1.4; }
      if (WD.stalkT > 5 && Math.random() < dt * 0.18) { lamp.dying = 1.6; WD.stalkT = 0; aiEvent('lamp', { i: lamp.i }); }
      if (WD.stalkT > 22) { setWState('roam'); WD.path = []; WD.waitT = 2; }
      break;
    }
    case 'attack': {
      WD.anim = 'attack'; WD.speed = 0; WD.attackT -= dt;
      if (tgt) WD.yaw += angWrap(Math.atan2(tgt.x - WD.x, tgt.z - WD.z) - WD.yaw) * Math.min(1, dt * 8);
      if (WD.attackT <= 0) {
        if (tgt && Math.hypot(tgt.x - WD.x, tgt.z - WD.z) < 2.5 && !(tgt.house >= 0 && tgt.hiddenDoor && false)) aiEvent('hit', { id: tgt.id, dmg: 28 + G.night * 3 });
        WD.cool = 1.4;
        if (Math.random() < 0.45) { setWState('retreat'); WD.retreatT = rand(2.5, 4); }
        else setWState('chase');
      }
      break;
    }
    case 'retreat': {
      WD.anim = 'run'; WD.retreatT -= dt;
      const ax = tgt ? WD.x - tgt.x : 1, az = tgt ? WD.z - tgt.z : 0, l = Math.hypot(ax, az) || 1;
      moveToward(WD.x + ax / l * 5, WD.z + az / l * 5, wdSpeed() * dt); WD.speed = wdSpeed();
      if (WD.retreatT <= 0) setWState(tgt ? 'chase' : 'search'), WD.searchT = 8;
      break;
    }
    case 'bash': {
      WD.anim = 'bash'; WD.speed = 0; WD.bashT -= dt;
      const d = WD.bash;
      if (!d || d.open) { setWState(WD.target >= 0 ? 'chase' : 'search'); WD.searchT = 8; break; }
      WD.yaw += angWrap(Math.atan2(d.x - WD.x, d.z - WD.z) - WD.yaw) * Math.min(1, dt * 6);
      if (WD.bashT <= 0) {
        WD.bashT = 1.2; d.hp--;
        aiEvent('bash', { d: d.id, broken: d.hp <= 0 });
        if (d.hp <= 0) setWState(WD.target >= 0 ? 'chase' : 'search');
      }
      break;
    }
  }
}
function nearestGate(x, z) { let b = FOREST_GATES[0], bd = 1e9; for (const g of FOREST_GATES) { const d = Math.hypot(g[0] - x, g[1] - z); if (d < bd) { bd = d; b = g; } } return b; }
function moveToward(tx, tz, step) {
  const dx = tx - WD.x, dz = tz - WD.z, l = Math.hypot(dx, dz); if (l < 0.01) return;
  const e = { x: WD.x, z: WD.z }; moveCircle(e, dx / l * Math.min(step, l), dz / l * Math.min(step, l), 0.35);
  if (!lampLitAt(e.x, e.z, 4.2) || WD.state === 'leave') { WD.x = e.x; WD.z = e.z; }
  WD.yaw += angWrap(Math.atan2(dx, dz) - WD.yaw) * Math.min(1, step * 3);
}
function segDist(px, pz, ax, az, bx, bz) {
  const vx = bx - ax, vz = bz - az, l2 = vx * vx + vz * vz || 1, t = clamp(((px - ax) * vx + (pz - az) * vz) / l2, 0, 1);
  return Math.hypot(px - ax - vx * t, pz - az - vz * t);
}
function lineNavFree(x1, z1, x2, z2) {
  const dx = x2 - x1, dz = z2 - z1, n = Math.ceil(Math.hypot(dx, dz) / 0.5);
  for (let k = 1; k <= n; k++) if (NAV.block[navIdx(x1 + dx * k / n, z1 + dz * k / n)]) return false;
  return true;
}
// идёт по пути; возвращает false, когда путь кончился
function followPath(dt, speed, ignoreAvoid) {
  if (!WD.path.length) { WD.speed = 0; return false; }
  // срезаем углы: ищем самую дальнюю видимую точку пути
  let k = 0;
  for (let i = Math.min(WD.path.length - 1, 7); i > 0; i--) if (lineNavFree(WD.x, WD.z, navX(WD.path[i]), navZ(WD.path[i]))) { k = i; break; }
  if (k > 0) WD.path.splice(0, k);
  const n = WD.path[0], tx = navX(n), tz = navZ(n);
  // закрытая дверь на пути — ломает
  for (const d of Town.doors) {
    if (d.open || Math.abs(d.x - WD.x) > 2 || Math.abs(d.z - WD.z) > 2) continue;
    if (segDist(d.x, d.z, WD.x, WD.z, tx, tz) < 0.75 && Math.hypot(d.x - WD.x, d.z - WD.z) < 1.6) { WD.bash = d; setWState('bash'); WD.bashT = 0.6; WD.speed = 0; return true; }
  }
  const dx = tx - WD.x, dz = tz - WD.z, l = Math.hypot(dx, dz);
  if (l < 0.3) { WD.path.shift(); return true; }
  const step = Math.min(l, speed * dt);
  WD.x += dx / l * step; WD.z += dz / l * step; WD.speed = speed;
  WD.yaw += angWrap(Math.atan2(dx, dz) - WD.yaw) * Math.min(1, dt * 7);
  return true;
}
