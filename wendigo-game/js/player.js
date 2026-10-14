'use strict';
// =====================================================================
//  Игрок: управление, движение, потребности, инвентарь, действия
// =====================================================================
const P = { id: 1, name: 'Игрок', x: 9, z: -4.5, yaw: Math.PI, pitch: 0, hp: 100, food: 85, water: 80, stam: 100, tired: false,
            battery: 100, light: false, money: 100, inv: { canned: 1, bread: 1, water: 1, soda: 0, bandage: 1, battery: 0 },
            alive: true, house: -1, inShop: false, hiddenDoor: false, running: false, moving: false, bob: 0, stepIdx: 0, hurt: 0, lamp: false };
const keys = {};
const inp = { lookX: 0, lookY: 0, act: false, light: false };
let joyId = null, joyO = { x: 0, y: 0 }, joyV = { x: 0, y: 0 }, lookId = null, lookLast = { x: 0, y: 0 }, runTouch = false;

function setupInput() {
  addEventListener('keydown', e => {
    keys[e.code] = true;
    if (G.state !== 'play') return;
    if (e.code === 'KeyE' || e.code === 'Space') inp.act = true;
    if (e.code === 'KeyF') inp.light = true;
    const q = { Digit1: 'food', Digit2: 'water', Digit3: 'bandage', Digit4: 'battery' }[e.code]; if (q) useItem(q);
  });
  addEventListener('keyup', e => { keys[e.code] = false; });
  const touchEl = $('touch');
  touchEl.addEventListener('pointerdown', e => {
    if (G.state !== 'play') return;
    if (e.pointerType === 'mouse') {
      if (document.pointerLockElement !== touchEl) { try { touchEl.requestPointerLock(); } catch (er) {} } else inp.act = true;
      return;
    }
    if (e.clientX < innerWidth * 0.42 && joyId === null) {
      joyId = e.pointerId; joyO = { x: e.clientX, y: e.clientY }; joyV = { x: 0, y: 0 };
      const j = $('joy'); j.style.display = 'block'; j.style.left = e.clientX + 'px'; j.style.top = e.clientY + 'px'; $('knob').style.transform = '';
    } else if (lookId === null) { lookId = e.pointerId; lookLast = { x: e.clientX, y: e.clientY }; }
  });
  addEventListener('pointermove', e => {
    if (e.pointerId === joyId) {
      let dx = e.clientX - joyO.x, dy = e.clientY - joyO.y; const l = Math.hypot(dx, dy), R = 55;
      if (l > R) { dx *= R / l; dy *= R / l; }
      joyV = { x: dx / R, y: dy / R }; $('knob').style.transform = `translate(${dx}px,${dy}px)`;
    } else if (e.pointerId === lookId) { inp.lookX += e.clientX - lookLast.x; inp.lookY += e.clientY - lookLast.y; lookLast = { x: e.clientX, y: e.clientY }; }
  });
  const endPtr = e => {
    if (e.pointerId === joyId) { joyId = null; joyV = { x: 0, y: 0 }; $('joy').style.display = 'none'; }
    if (e.pointerId === lookId) lookId = null;
  };
  addEventListener('pointerup', endPtr); addEventListener('pointercancel', endPtr);
  document.addEventListener('mousemove', e => { if (document.pointerLockElement === touchEl && G.state === 'play') { inp.lookX += e.movementX * 0.55; inp.lookY += e.movementY * 0.55; } });
  const bRun = $('bRun');
  bRun.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); runTouch = true; bRun.classList.add('on'); });
  for (const ev of ['pointerup', 'pointercancel', 'pointerleave']) bRun.addEventListener(ev, () => { runTouch = false; bRun.classList.remove('on'); });
  $('bAct').addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); inp.act = true; });
  $('bLight').addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); inp.light = true; });
  document.querySelectorAll('[data-use]').forEach(b => b.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); useItem(b.dataset.use); }));
  document.addEventListener('contextmenu', e => e.preventDefault());
}

// ---------------------------------------------------------------------
//  Инвентарь
// ---------------------------------------------------------------------
function useItem(kind) {
  if (!P.alive) return;
  const inv = P.inv;
  let it = null;
  if (kind === 'food') it = inv.canned > 0 ? 'canned' : inv.bread > 0 ? 'bread' : null;
  else if (kind === 'water') it = inv.water > 0 ? 'water' : inv.soda > 0 ? 'soda' : null;
  else if (kind === 'bandage') it = inv.bandage > 0 ? 'bandage' : null;
  else if (kind === 'battery') it = inv.battery > 0 ? 'battery' : null;
  if (!it) { showMsg('Нет: ' + { food: 'еды', water: 'воды', bandage: 'бинтов', battery: 'батареек' }[kind], 1.5); return; }
  const d = ITEMS[it]; inv[it]--;
  if (d.food) P.food = Math.min(100, P.food + d.food);
  if (d.water) P.water = Math.min(100, P.water + d.water);
  if (d.heal) P.hp = Math.min(100, P.hp + d.heal);
  if (it === 'battery') P.battery = 100;
  if (kind === 'food') SFX.eat(); else if (kind === 'water') SFX.drink(); else SFX.pickup();
  showMsg(`${d.icon} ${d.name}`, 1.2);
  updateHud(true);
}
function addItems(items, money) {
  for (const k of items) P.inv[k] = (P.inv[k] || 0) + 1;
  P.money += money || 0;
  if (items.length || money) {
    SFX.pickup(); if (money) SFX.coin();
    showMsg('Найдено: ' + [...items.map(k => ITEMS[k].icon + ' ' + ITEMS[k].name), money ? `₽ ${money}` : ''].filter(Boolean).join(', '), 2.5);
  } else showMsg('Пусто…', 1.5);
  updateHud(true);
}

// ---------------------------------------------------------------------
//  Обновление
// ---------------------------------------------------------------------
const ray = new THREE.Raycaster(), CENTER = new THREE.Vector2(0, 0);
let target = null;
function interLabel(t) {
  if (!t) return '';
  if (t.type === 'door') return t.ref.broken ? 'Дверь выбита' : t.ref.open ? 'Закрыть дверь' : 'Открыть дверь';
  if (t.type === 'loot') return t.ref.looted ? 'Пусто' : t.ref.kind === 'fridge' ? 'Обыскать холодильник' : 'Обыскать шкаф';
  if (t.type === 'shop') return shopOpen() ? 'Купить' : 'Продавца нет';
  return '';
}
function updatePlayer(dt) {
  const sens = 0.0042;
  if (!P.alive) { inp.lookX = inp.lookY = 0; return; }
  if (inp.light) { inp.light = false; if (P.battery > 0) { P.light = !P.light; SFX.click(); } else showMsg('Батарейка села. Найди 🔋', 2); }
  P.yaw -= inp.lookX * sens; P.pitch = clamp(P.pitch - inp.lookY * sens, -1.35, 1.35); inp.lookX = inp.lookY = 0;

  let mx = joyV.x, mz = -joyV.y;
  if (keys.KeyW || keys.ArrowUp) mz += 1; if (keys.KeyS || keys.ArrowDown) mz -= 1;
  if (keys.KeyA || keys.ArrowLeft) mx -= 1; if (keys.KeyD || keys.ArrowRight) mx += 1;
  let mag = Math.hypot(mx, mz); if (mag > 1) { mx /= mag; mz /= mag; mag = 1; }
  P.running = (runTouch || keys.ShiftLeft || keys.ShiftRight) && mag > 0.25 && !P.tired && mz > -0.2;
  P.moving = mag > 0.08;
  if (P.running) { mx /= mag; mz /= mag; }
  const sp = P.running ? 5.4 : 2.6;
  const fx = -Math.sin(P.yaw), fz = -Math.cos(P.yaw), rx = Math.cos(P.yaw), rz = -Math.sin(P.yaw);
  if (!circleFree(P.x, P.z, 0.3)) { const sp = freeSpot(P.x, P.z, 0.3); P.x = sp.x; P.z = sp.z; } // выталкиваем из стены/дерева
  if (P.moving) moveCircle(P, (rx * mx + fx * mz) * sp * dt, (rz * mx + fz * mz) * sp * dt, 0.3);

  // выносливость и потребности
  if (P.running) { P.stam -= 11 * dt; if (P.stam <= 0) { P.stam = 0; P.tired = true; SFX.breath(0.25); } }
  else { P.stam = Math.min(100, P.stam + (P.moving ? 8 : 15) * dt); if (P.tired && P.stam > 35) P.tired = false; }
  P.food = Math.max(0, P.food - dt * 100 / 420);
  P.water = Math.max(0, P.water - dt * 100 / 330 * (P.running ? 1.7 : 1));
  if (P.food <= 0 || P.water <= 0) { P.hp -= dt * 0.8; if (Math.random() < dt * 0.3) showMsg(P.food <= 0 ? 'Ты умираешь от голода' : 'Ты умираешь от жажды', 2); }
  else if (P.food > 40 && P.water > 40 && P.hp < 100) P.hp = Math.min(100, P.hp + dt * 0.25);
  if (P.light) { P.battery = Math.max(0, P.battery - dt * 100 / 330); if (P.battery <= 0) { P.light = false; showMsg('Фонарик погас', 2); } }
  P.hurt = Math.max(0, P.hurt - dt * 1.5);
  if (P.hp <= 0) { P.hp = 0; onLocalDeath(); return; }

  // где игрок
  P.house = -1; P.inShop = false;
  for (const h of Town.houses) { const b = h.bounds; if (P.x > b.x0 && P.x < b.x1 && P.z > b.z0 && P.z < b.z1) { P.house = h.id; break; } }
  const sb = Town.shop.bounds; if (P.x > sb.x0 && P.x < sb.x1 && P.z > sb.z0 && P.z < sb.z1) P.inShop = true;
  P.hiddenDoor = P.house >= 0 ? !Town.houses[P.house].door.open : P.inShop ? !(Town.shop.door.open || Town.shop.door2.open) : false;
  P.lamp = !!lampLitAt(P.x, P.z);

  // покачивание и шаги
  const amp = P.running ? 0.06 : 0.032;
  if (P.moving) P.bob += dt * (P.running ? 11 : 7) * Math.max(0.5, mag);
  const idx = Math.floor(P.bob / Math.PI);
  if (idx !== P.stepIdx) {
    P.stepIdx = idx;
    if (P.moving) SFX.step(P.running ? 0.32 : 0.15, P.house >= 0 ? 'wood' : onRoad(P.x, P.z) ? 'road' : 'grass');
  }
  const bobY = Math.abs(Math.sin(P.bob)) * amp, bobX = Math.cos(P.bob) * amp * 0.5;
  camera.position.set(P.x + rx * bobX, 1.66 + bobY - amp * 0.5, P.z + rz * bobX);
  camera.rotation.set(P.pitch, P.yaw, Math.cos(P.bob) * (P.running ? 0.01 : 0.004));
  camera.fov = lerp(camera.fov, P.running ? 78 : 72, dt * 4); camera.updateProjectionMatrix();

  // под прицелом
  const near = Town.inter.filter(it => Math.abs(it.pos.x - P.x) < 3 && Math.abs(it.pos.z - P.z) < 3).map(it => it.mesh);
  target = null;
  if (near.length) {
    ray.setFromCamera(CENTER, camera); ray.far = 2.6;
    const h = ray.intersectObjects(near, false)[0];
    if (h) { const it = h.object.userData.inter; if (it.type === 'door' || sightClear(P.x, P.z, it.pos.x, it.pos.z)) target = it; }
  }
  setHint(interLabel(target));
  if (inp.act) { inp.act = false; if (target) doAction(target); }
}
function onRoad(x, z) { return STREETS_Z.some(s => Math.abs(z - s) < 6) || STREETS_X.some(s => Math.abs(x - s) < 6); }
function doAction(t) {
  if (t.type === 'door') requestDoor(t.ref);
  else if (t.type === 'loot') { if (t.ref.looted) showMsg('Здесь уже пусто', 1.5); else requestLoot(t.ref); }
  else if (t.type === 'shop') { if (shopOpen()) openShop(); else showMsg('Продавец ушёл. Магазин работает с 7:00 до 21:00', 2.5); }
}
let hintText = null;
function setHint(t) {
  if (t === hintText) return; hintText = t;
  $('hint').textContent = t; $('cross').classList.toggle('on', !!t);
  const b = $('bAct'); b.classList.toggle('hidden', !t || !isTouch);
  b.textContent = t.startsWith('Обыскать') ? 'ОБЫСКАТЬ' : t.includes('Открыть') ? 'ОТКРЫТЬ' : t.includes('Закрыть') ? 'ЗАКРЫТЬ' : t === 'Купить' ? 'КУПИТЬ' : '…';
}

// ---------------------------------------------------------------------
//  Интерфейс
// ---------------------------------------------------------------------
let hudT = 0;
function updateHud(force) {
  hudT -= 0.016; if (!force && hudT > 0) return; hudT = 0.1;
  const bar = (id, v, low) => { const e = $(id); e.style.width = v + '%'; e.classList.toggle('low', v < low); };
  bar('bHp', P.hp, 30); bar('bFood', P.food, 20); bar('bWater', P.water, 20); bar('bStam', P.stam, 20);
  $('money').textContent = '₽ ' + P.money;
  $('battery').textContent = '🔦 ' + Math.round(P.battery) + '%';
  $('qFood').textContent = P.inv.canned + P.inv.bread; $('qWater').textContent = P.inv.water + P.inv.soda;
  $('qBand').textContent = P.inv.bandage; $('qBat').textContent = P.inv.battery;
  const hh = Math.floor(G.clock / 60), mm = Math.floor(G.clock % 60);
  $('clock').textContent = `День ${G.day} · ${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}` + (isNight() ? ' 🌙' : ' ☀');
}
