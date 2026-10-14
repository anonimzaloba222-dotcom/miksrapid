'use strict';
// =====================================================================
//  Ход игры: время суток, события, магазин, смерть, рассвет, цикл
// =====================================================================
const G = { state: 'loading', seed: 0, clock: 7 * 60, day: 1, night: 0, time: 0, danger: 0, hb: 1, msgT: 0, ambT: 6, netClock: null,
            built: false, flick: 1, flickT: 0, wStepAcc: 0, wSndT: 0, shake: 0, lastNight: false, nightsSurvived: 0 };
const DAYS_TO_WIN = 5;
const isNight = () => G.clock >= 21 * 60 || G.clock < 5 * 60;
const shopOpen = () => G.clock >= 7 * 60 && G.clock < 21 * 60;
function vibrate(p) { try { navigator.vibrate && navigator.vibrate(p); } catch (e) {} }
function showMsg(t, dur = 3) { const m = $('msg'); m.textContent = t; m.style.opacity = 1; G.msgT = dur; }
function showScreen(id) { for (const s of ['menu', 'lobby', 'join', 'over', 'win', 'loading']) $(s).classList.toggle('hidden', s !== id); }
function setControls(v) {
  for (const id of ['hud', 'quick', 'cross']) $(id).classList.toggle('hidden', !v);
  for (const id of ['bRun', 'bLight']) $(id).classList.toggle('hidden', !v || !isTouch);
  if (!v) { $('bAct').classList.add('hidden'); $('hint').textContent = ''; hintText = null; $('joy').style.display = 'none'; joyId = lookId = null; joyV = { x: 0, y: 0 }; if (document.pointerLockElement) document.exitPointerLock(); }
}

// ---------------------------------------------------------------------
//  Время: день ≈ 5.5 мин, ночь ≈ 4 мин
// ---------------------------------------------------------------------
function advanceClock(dt) {
  const rate = isNight() ? 2.0 : 2.9;
  const prev = G.clock;
  G.clock += dt * rate; if (G.clock >= 1440) G.clock -= 1440;
  if (NET.mode === 'client') return;
  const night = isNight();
  if (night && !G.lastNight) onNightStart();
  if (!night && G.lastNight && prev < 5 * 60 + 1) { const nd = G.day + 1; onDawn(nd); netSend(0, { k: 'dawn', day: nd }); }
  G.lastNight = night;
}
function onNightStart() {
  G.night = G.day;
  // каждой ночью часть фонарей перестаёт работать
  for (const l of Town.lamps) if (!l.broken && RNG() < 0.06 * G.night) { l.broken = true; netSend(0, { k: 'lamp', i: l.i }); }
  showMsg(`Ночь ${G.night}. Из леса доносится вой… Держись у фонарей или в домах.`, 5);
}
function onDawn(day) {
  G.day = day; G.nightsSurvived = day - 1;
  if (day > DAYS_TO_WIN) { if (NET.mode !== 'client') netSend(0, { k: 'win' }); winGame(); return; }
  if (Town.shop) Town.shop.stock = { canned: 6, bread: 6, water: 8, soda: 8, bandage: 3, battery: 4 };
  if (!P.alive) respawn();
  showMsg(`Рассвет. День ${day}. Вендиго ушёл в лес — до заката нужно запастись едой и водой.`, 5);
}
function respawn() {
  P.alive = true; P.hp = 50; P.food = Math.max(P.food, 40); P.water = Math.max(P.water, 40); P.stam = 100;
  P.x = Town.spawn.x + (P.id % 4) * 1.2; P.z = Town.spawn.z; P.yaw = Math.PI;
  G.state = 'play'; setControls(true); $('deadOv').classList.add('hidden'); updatePlayerList();
}

// ---------------------------------------------------------------------
//  Действия, которые согласует хост
// ---------------------------------------------------------------------
function requestDoor(d) {
  if (d.broken) { showMsg('Дверь выбита — её не закрыть', 1.5); return; }
  if (d.owner === -1 && !shopOpen() && !P.inShop) { showMsg('Магазин закрыт до 7:00', 2); return; }
  if (NET.mode === 'client') netSend(1, { k: 'door', d: d.id }); else toggleDoor(d, false);
}
function doorPair(d) { return d.owner === -1 ? [Town.shop.door, Town.shop.door2] : [d]; }
function toggleDoor(d, fromNet) {
  if (d.broken) return;
  const open = !d.open;
  if (!open) {
    // не закрываем дверь на стоящем в проёме
    const bodies = [P.alive ? P : null, ...[...REMOTES.values()].filter(r => r.alive)].filter(Boolean);
    for (const dd of doorPair(d)) for (const b of bodies) if (Math.hypot(b.x - dd.x, b.z - dd.z) < 0.75) return;
    if (WD.state !== 'away' && doorPair(d).some(dd => Math.hypot(WD.x - dd.x, WD.z - dd.z) < 0.9)) return;
  }
  for (const dd of doorPair(d)) { applyDoor(dd, open, false); netSend(0, { k: 'door', d: dd.id, o: open ? 1 : 0, b: 0 }); }
  if (d.owner === -1 && open && shopOpen()) SFX.bell();
}
function applyDoor(d, open, broken) {
  if (!d) return;
  const changed = d.open !== open;
  d.open = open; if (broken) { d.broken = true; d.open = true; }
  applyDoorCollision(d);
  if (changed) { const s = spatial(d.x, d.z, 22); SFX.door(s.vol, s.pan, s.muffle); }
}
function updateDoors(dt) {
  for (const d of Town.doors) {
    d.ang = lerp(d.ang, d.open ? (d.broken ? 1.25 : 1) : 0, Math.min(1, dt * 5));
    d.pivot.rotation.y = d.base + d.dir * Math.PI * 0.5 * d.ang;
  }
}
function requestLoot(ct) {
  if (NET.mode === 'client') { netSend(1, { k: 'loot', c: ct.id }); return; }
  if (ct.looted) return;
  ct.looted = true; addItems(ct.items, ct.money);
  netSend(0, { k: 'looted', c: ct.id, by: P.id });
}
// события вендиго (у хоста или в одиночной игре)
function aiEvent(t, d) {
  if (t === 'hit') { if (d.id === P.id) takeHit(d.dmg); else netSend(d.id, { k: 'hit', id: d.id, dmg: d.dmg }); return; }
  if (t === 'lamp') { netSend(0, { k: 'lamp', i: d.i }); return; }
  if (t === 'bash') {
    const door = Town.doors[d.d];
    if (d.broken) { applyDoor(door, true, true); netSend(0, { k: 'door', d: door.id, o: 1, b: 1 }); }
    d = { x: door.x, z: door.z, broken: d.broken };
  }
  worldFx(t, d); netSend(0, { k: 'fx', t, d });
}
function worldFx(t, d) {
  if (t === 'howl') { const s = spatial(d.x, d.z, 260); SFX.howl(Math.max(0.12, s.vol), s.pan, s.d > 40 ? 900 : 0); }
  else if (t === 'spot') { if (d.id === P.id) { SFX.screech(0.8, 0); vibrate([80, 60, 160]); showMsg('ОН ТЕБЯ ЗАМЕТИЛ — БЕГИ К СВЕТУ!', 2.5); } }
  else if (t === 'bash') { const s = spatial(d.x, d.z, 40); SFX.bash(Math.max(0.2, s.vol), s.pan, s.muffle); if (d.broken) showMsgNear(d, 'Он выбил дверь!'); }
}
function showMsgNear(d, text) { if (Math.hypot(d.x - P.x, d.z - P.z) < 25) showMsg(text, 2); }
function takeHit(dmg) {
  if (!P.alive) return;
  P.hp -= dmg; P.hurt = 1; G.shake = 0.6; SFX.hit(); vibrate([200, 50, 200]);
  showMsg(P.hp > 0 ? 'Вендиго ранил тебя! Используй бинт ✚' : '', 2);
  if (P.hp <= 0) { P.hp = 0; onLocalDeath(); }
}
function onLocalDeath() {
  if (!P.alive) return;
  P.alive = false; P.light = false; G.state = 'dead'; setControls(false); updatePlayerList();
  if (NET.mode === 'solo') { setTimeout(() => gameOver(G.day - 1), 2500); }
  else $('deadOv').classList.remove('hidden');
}
function alivePlayers() {
  const out = [];
  if (P.alive) out.push({ id: P.id, x: P.x, z: P.z, light: P.light, lamp: P.lamp, running: P.running, house: P.inShop ? 99 : P.house, hiddenDoor: P.hiddenDoor });
  for (const r of REMOTES.values()) if (r.alive) out.push({ id: r.id, x: r.x, z: r.z, light: r.light, lamp: r.lamp || !!lampLitAt(r.x, r.z), running: r.running, house: r.house, hiddenDoor: r.hiddenDoor });
  return out;
}
function gameOver(n) {
  if (G.state === 'over') return;
  G.state = 'over'; setControls(false); $('deadOv').classList.add('hidden');
  $('overTxt').textContent = `Ночей пережито: ${n} из ${DAYS_TO_WIN}.`;
  showScreen('over');
}
function winGame() {
  if (G.state === 'won') return;
  G.state = 'won'; setControls(false); $('deadOv').classList.add('hidden');
  showScreen('win');
}

// ---------------------------------------------------------------------
//  Магазин
// ---------------------------------------------------------------------
function openShop() { G.state = 'shop'; renderShop(); $('shop').classList.remove('hidden'); setControls(false); SFX.bell(); }
function closeShop() { $('shop').classList.add('hidden'); if (G.state === 'shop') { G.state = 'play'; setControls(true); } }
function renderShop() {
  const box = $('shopList'); if (!box || !Town.shop) return; box.textContent = '';
  for (const k of Object.keys(ITEMS)) {
    const it = ITEMS[k], st = Town.shop.stock[k] || 0;
    const row = document.createElement('div'); row.className = 'srow';
    const l = document.createElement('span'); l.textContent = `${it.icon} ${it.name} — ${it.price} ₽ (осталось ${st})`;
    const b = document.createElement('button'); b.textContent = 'Купить'; b.disabled = st <= 0 || P.money < it.price;
    b.onclick = () => buy(k);
    row.append(l, b); box.appendChild(row);
  }
  $('shopMoney').textContent = 'У тебя: ' + P.money + ' ₽';
}
function buy(k) {
  const it = ITEMS[k];
  if (P.money < it.price) { showMsg('Не хватает денег', 1.5); return; }
  if (NET.mode === 'client') { netSend(1, { k: 'buy', it: k }); return; }
  if ((Town.shop.stock[k] || 0) <= 0) return;
  Town.shop.stock[k]--; shopBought(k); netSend(0, { k: 'stock', stock: Town.shop.stock });
}
function shopBought(k) { P.money -= ITEMS[k].price; P.inv[k] = (P.inv[k] || 0) + 1; SFX.coin(); renderShop(); updateHud(true); }

// ---------------------------------------------------------------------
//  Запуск игры
// ---------------------------------------------------------------------
function startGameWorld(seed, world) {
  G.seed = seed | 0;
  showScreen('loading');
  setTimeout(() => {
    if (!G.built) {
      buildWorld(G.seed); buildWendigoModel(); buildSnow();
      G.built = true;
    }
    if (world) applyWorldState(world);
    else { G.clock = 7 * 60; G.day = 1; }
    P.x = Town.spawn.x + (P.id % 4) * 1.2; P.z = Town.spawn.z; P.yaw = Math.PI * 0.95;
    G.lastNight = isNight();
    renderer.compile(scene, camera);
    showScreen(null); G.state = 'play'; setControls(true); updateHud(true); updatePlayerList();
    showMsg(NET.mode === 'solo' ? 'Обыщи дома, купи припасы в магазине «Продукты». К 21:00 найди укрытие.' : 'Вы вместе. Держитесь рядом — ночью он охотится на отставших.', 6);
  }, 60);
}
function applyWorldState(w) {
  G.clock = w.clock; G.day = w.day; G.night = w.night;
  w.doors.forEach((v, i) => { const d = Town.doors[i]; if (d) { d.open = !!(v & 1); d.broken = !!(v & 2); d.ang = d.open ? 1 : 0; applyDoorCollision(d); } });
  for (const c of w.looted) if (Town.containers[c]) Town.containers[c].looted = true;
  for (const i of w.lamps) if (Town.lamps[i]) Town.lamps[i].broken = true;
  Town.shop.stock = w.stock;
  for (const p of w.players || []) if (p.id !== NET.myId) ensureRemote(p.id, p.name);
}
function startSolo() { NET.mode = 'solo'; P.id = 1; G.seed = (Math.random() * 1e9) | 0; startGameWorld(G.seed); }
function hostStart() {
  NET.started = true;
  for (const p of NET.lobby) if (p.id !== 1) { /* аватары после постройки мира */ }
  startGameWorld(G.seed);
  setTimeout(() => {
    for (const p of NET.lobby) if (p.id !== 1) ensureRemote(p.id, p.name);
    netSend(0, { k: 'start', seed: G.seed, world: worldState() });
  }, 120);
}

// ---------------------------------------------------------------------
//  Атмосфера
// ---------------------------------------------------------------------
function updateAtmosphere(dt, dk) {
  const near = WD.state !== 'away';
  const dW = near ? Math.hypot(WD.x - P.x, WD.z - P.z) : 999;
  let danger = clamp(1 - dW / 26, 0, 1);
  if (near && (WD.state === 'chase' || WD.state === 'attack') && dW < 30) danger = Math.max(danger, 0.7);
  G.danger = lerp(G.danger, P.alive ? danger : 0, dt * 3);
  G.hb -= dt;
  if (G.hb <= 0) { G.hb = 1.3 - 0.9 * G.danger; if (G.danger > 0.2) { SFX.heart(0.15 + 0.5 * G.danger); if (G.danger > 0.7) vibrate(25); } }
  if (AU.chase) AU.chase.gain.setTargetAtTime(G.danger > 0.65 ? 0.03 : 0, anow(), 0.6);
  if (AU.windG) AU.windG.gain.setTargetAtTime(0.03 + 0.06 * (1 - dk), anow(), 1);
  G.flickT -= dt;
  if (G.flickT <= 0) {
    G.flickT = rand(0.04, 0.2);
    G.flick = (G.danger > 0.5 && Math.random() < G.danger * 0.35) || (P.battery < 15 && Math.random() < 0.3) ? rand(0.1, 0.5) : 1;
  }
  // шаги и звуки вендиго
  if (near) {
    G.wStepAcc += dt * WD.speed;
    if (G.wStepAcc > 1.3) { G.wStepAcc = 0; const s = spatial(WD.x, WD.z, 34); SFX.step(s.vol * 1.2, 'road', s.pan, s.muffle, true); if (s.vol > 0.5) G.shake = Math.max(G.shake, 0.08); }
    G.wSndT -= dt;
    if (G.wSndT <= 0) {
      G.wSndT = rand(2.5, 6);
      const s = spatial(WD.x, WD.z, 30);
      if (WD.anim === 'stalk') SFX.growl(Math.max(0.15, s.vol), s.pan, s.muffle); else if (s.vol > 0.05) SFX.clicks(s.vol * 0.6, s.pan, s.muffle);
    }
  }
  G.ambT -= dt;
  if (G.ambT <= 0) {
    G.ambT = rand(5, 12);
    if (dk > 0.5) SFX.bird(rand(-1, 1)); else if (Math.random() < 0.5) SFX.owl(rand(-1, 1));
  }
  // магазин
  const sh = Town.shop, open = shopOpen();
  for (const l of sh.lights) l.intensity = open ? 1.5 * (Math.random() < 0.02 ? 0.3 : 1) : 0;
  MT.fluor.color.setScalar(open ? 3.2 : 0.05); MT.fridgeGlow.color.setRGB(open ? 1.6 : 0.05, open ? 1.9 : 0.06, open ? 2.2 : 0.08);
  MT.sign.color.setScalar(open || Math.random() < 0.5 ? 2.2 : 0.3);
  Town.keeper.visible = open;
  if (G.msgT > 0) { G.msgT -= dt; if (G.msgT <= 0) $('msg').style.opacity = 0; }
  if (G.shake > 0) { G.shake -= dt; camera.position.x += rand(-1, 1) * G.shake * 0.08; camera.position.y += rand(-1, 1) * G.shake * 0.08; }
}
function spectate(dt) {
  const alive = [...REMOTES.values()].filter(r => r.alive);
  const r = alive[0];
  if (!r) return;
  const a = G.time * 0.2;
  camera.position.set(r.x + Math.sin(a) * 6, 4, r.z + Math.cos(a) * 6);
  camera.lookAt(r.x, 1.5, r.z);
}
function wendigoClient(dt) {
  if (WD.tx === undefined) return;
  if (Math.hypot(WD.tx - WD.x, WD.tz - WD.z) > 8) { WD.x = WD.tx; WD.z = WD.tz; }
  WD.x = lerp(WD.x, WD.tx, Math.min(1, dt * 9)); WD.z = lerp(WD.z, WD.tz, Math.min(1, dt * 9));
  WD.yaw += angWrap(WD.tyaw - WD.yaw) * Math.min(1, dt * 9);
  if (G.netClock !== null) { if (Math.abs(G.netClock - G.clock) > 3) G.clock = G.netClock; G.netClock = null; }
}
function onWendigoState() {}

// ---------------------------------------------------------------------
//  Меню
// ---------------------------------------------------------------------
function setupMenu() {
  try { const n = localStorage.getItem('wendigo_name'); if (n) $('nameIn').value = n; } catch (e) {}
  const getName = () => { P.name = cleanName($('nameIn').value.trim()); try { localStorage.setItem('wendigo_name', P.name); } catch (e) {} };
  $('bSolo').onclick = () => { getName(); initAudio(); goFull(); startSolo(); };
  $('bHost').onclick = () => {
    getName(); initAudio();
    if (!netAvailable()) { $('netNote').textContent = 'Сетевая игра работает в Android-приложении (Wendigo.apk).'; return; }
    G.seed = (Math.random() * 1e9) | 0; goFull(); hostGame();
  };
  $('bJoin').onclick = () => {
    getName(); initAudio();
    if (!netAvailable()) { $('netNote').textContent = 'Сетевая игра работает в Android-приложении (Wendigo.apk).'; return; }
    goFull(); NET.found.clear(); renderFound(); showScreen('join'); TR.scan();
    if (!TR.native) setTimeout(() => { if (!NET.found.size) $('foundList').textContent = 'Никто не создал игру'; }, 2500);
  };
  $('bConnect').onclick = () => { const ip = $('ipIn').value.trim(); if (/^[\d.]{7,15}$/.test(ip) || ip === 'local') joinGame(ip); else $('joinStatus').textContent = 'Введи адрес вида 192.168.1.5'; };
  $('bRescan').onclick = () => { NET.found.clear(); renderFound(); TR.scan(); };
  $('lobbyStart').onclick = () => hostStart();
  for (const id of ['joinBack', 'lobbyBack']) $(id).onclick = () => location.reload();
  document.querySelectorAll('[data-restart]').forEach(b => b.onclick = () => location.reload());
  $('shopClose').onclick = closeShop;
  document.querySelectorAll('[data-q]').forEach(b => {
    b.classList.toggle('sel', +b.dataset.q === quality);
    b.onclick = () => { if (+b.dataset.q === quality) return; try { localStorage.setItem('wendigo_q', b.dataset.q); } catch (e) {} location.reload(); };
  });
  document.addEventListener('visibilitychange', () => { if (AU.ctx) document.hidden ? AU.ctx.suspend() : AU.ctx.resume(); });
}
function goFull() {
  try {
    if (!/; wv\)/.test(navigator.userAgent) && isTouch && document.documentElement.requestFullscreen && !document.fullscreenElement)
      document.documentElement.requestFullscreen().then(() => { try { screen.orientation.lock('landscape').catch(() => {}); } catch (e) {} }).catch(() => {});
  } catch (e) {}
}

// ---------------------------------------------------------------------
//  Главный цикл
// ---------------------------------------------------------------------
let last = performance.now();
function loop(t) {
  requestAnimationFrame(loop);
  const dt = Math.min(0.05, (t - last) / 1000 || 0); last = t;
  if (!G.built || document.hidden) return;
  if (!['play', 'dead', 'shop'].includes(G.state)) { if (G.state === 'over' || G.state === 'won') renderFrame(0, 0); return; }
  G.time += dt;
  advanceClock(dt);
  if (G.state === 'play') updatePlayer(dt); else if (G.state === 'dead') spectate(dt);
  if (isHostOrSolo()) wendigoAI(dt, isNight()); else wendigoClient(dt);
  animateWendigo(dt, G.time);
  updateRemotes(dt); updateDoors(dt);
  const dk = updateSky(G.clock, camera.position.x, camera.position.z);
  updateLamps(dt, dk, camera.position.x, camera.position.z);
  updateFlashlight(dt, P.light && P.alive && G.state !== 'dead', G.flick, dk);
  const hb = P.house >= 0 ? Town.houses[P.house].bounds : P.inShop ? null : null;
  if (hb) { FL.room.position.set((hb.x0 + hb.x1) / 2, 2.4, (hb.z0 + hb.z1) / 2); FL.room.intensity = 0.9 * dk; } else FL.room.intensity = 0;
  updateSnow(dt, G.time, camera.position.x, camera.position.z);
  updateAtmosphere(dt, dk);
  if (NET.mode === 'host') {
    hostTick(dt);
    if (NET.started && !P.alive && [...REMOTES.values()].every(r => !r.alive)) { netSend(0, { k: 'over', nights: G.day - 1 }); gameOver(G.day - 1); }
  } else if (NET.mode === 'client') clientTick(dt);
  updateHud();
  renderFrame(G.danger, P.hurt);
}

// ---------------------------------------------------------------------
function boot() {
  initRenderer();
  setupInput(); setupMenu();
  showScreen('menu'); $('bSolo').disabled = true; $('bSolo').textContent = 'ЗАГРУЗКА…';
  setTimeout(() => {
    TEXS = QUALITY[quality].tex;
    buildTextures(); buildMaterials(); buildSky(); buildFlashlight(); setupPost(); resize();
    $('bSolo').disabled = false; $('bSolo').textContent = 'ОДИНОЧНАЯ ИГРА';
    G.state = 'menu';
    requestAnimationFrame(loop);
  }, 50);
}
boot();
