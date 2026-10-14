'use strict';
// =====================================================================
//  Сетевая игра по Wi-Fi (одна локальная сеть)
//  Android: мост AndroidNet (TCP-сервер + UDP-маяк, см. android/java).
//  Браузер: ?lan=bc — проверка в соседних вкладках через BroadcastChannel.
// =====================================================================
const NET = { mode: 'solo', myId: 1, hostIp: '', found: new Map(), started: false, lobby: [], sendT: 0, lastSnap: 0 };
const REMOTES = new Map(); // id → { name, x, z, yaw, pitch, hp, light, alive, house, running, lamp, hiddenDoor, avatar }

// ---------------------------------------------------------------------
//  Транспорт
// ---------------------------------------------------------------------
function makeTransport() {
  if (window.AndroidNet) return {
    native: true,
    host: name => AndroidNet.host(name), scan: () => AndroidNet.scan(), join: ip => AndroidNet.join(ip),
    send: (to, line) => AndroidNet.send(to, line), stop: () => AndroidNet.stop(), ip: () => AndroidNet.localIp(),
  };
  if (/[?&]lan=bc/.test(location.search) && window.BroadcastChannel) {
    const ch = new BroadcastChannel('wendigo-lan'), me = Math.random().toString(36).slice(2);
    let role = null, myId = 0, nextId = 1, beacon = null; const peers = new Map();
    const emit = (t, d) => window.__net([[t, d]]);
    ch.onmessage = ({ data: m }) => {
      if (role === 'host') {
        if (m.t === 'hello') { const id = ++nextId; peers.set(m.from, id); ch.postMessage({ t: 'welcome', to: m.from, id }); emit('join', String(id)); }
        if (m.t === 'up' && peers.has(m.from)) emit('msg', peers.get(m.from) + '|' + m.line);
        if (m.t === 'bye' && peers.has(m.from)) { emit('leave', String(peers.get(m.from))); peers.delete(m.from); }
      } else if (role === 'scan' && m.t === 'beacon') emit('found', 'local|' + m.name);
      else if (role === 'client') {
        if (m.t === 'welcome' && m.to === me) { myId = m.id; emit('connected', 'local'); }
        if (m.t === 'down' && (m.to === 0 || m.to === myId)) emit('msg', '1|' + m.line);
        if (m.t === 'hostgone') emit('disconnected', '1');
      }
    };
    addEventListener('beforeunload', () => ch.postMessage(role === 'host' ? { t: 'hostgone' } : { t: 'bye', from: me }));
    return {
      native: false,
      host: name => { role = 'host'; beacon = setInterval(() => ch.postMessage({ t: 'beacon', name }), 800); setTimeout(() => emit('hosting', 'local'), 10); },
      scan: () => { if (role !== 'client') role = 'scan'; },
      join: () => { role = 'client'; ch.postMessage({ t: 'hello', from: me }); },
      send: (to, line) => {
        if (role === 'host') { if (to === 0) ch.postMessage({ t: 'down', to: 0, line }); else ch.postMessage({ t: 'down', to, line }); }
        else ch.postMessage({ t: 'up', from: me, line });
      },
      stop: () => { clearInterval(beacon); role = null; }, ip: () => 'local',
    };
  }
  return null;
}
const TR = makeTransport();
function netAvailable() { return !!TR; }
function netSend(to, obj) { if (TR && NET.mode !== 'solo') TR.send(to, JSON.stringify(obj)); }
const isHostOrSolo = () => NET.mode !== 'client';

window.__net = function (evs) { for (const [t, d] of evs) try { onNetEvent(t, d); } catch (e) { console.error(e); } };
function onNetEvent(t, d) {
  if (t === 'hosting') { NET.hostIp = d; renderLobby(); }
  else if (t === 'join') { /* имя придёт в hi */ }
  else if (t === 'leave') { const id = +d; dropRemote(id); NET.lobby = NET.lobby.filter(p => p.id !== id); netSend(0, { k: 'left', id }); renderLobby(); }
  else if (t === 'connected') { netSend(1, { k: 'hi', name: P.name }); $('joinStatus').textContent = 'Подключено. Ждём хоста…'; }
  else if (t === 'disconnected') { if (NET.mode === 'client') { showMsg('Связь с хостом потеряна', 4); setTimeout(() => location.reload(), 2500); } }
  else if (t === 'found') { const [ip, ...rest] = d.split('|'); NET.found.set(ip, rest.join('|')); renderFound(); }
  else if (t === 'error') { $('joinStatus').textContent = 'Ошибка сети: ' + d; }
  else if (t === 'msg') {
    const i = d.indexOf('|'), from = +d.slice(0, i); let m;
    try { m = JSON.parse(d.slice(i + 1)); } catch (e) { return; }
    if (m && typeof m.k === 'string') NET.mode === 'host' ? hostMsg(from, m) : clientMsg(m);
  }
}
const cleanName = s => String(s || 'Игрок').replace(/[<>]/g, '').slice(0, 16) || 'Игрок';

// ---------------------------------------------------------------------
//  Хост
// ---------------------------------------------------------------------
function hostGame() {
  NET.mode = 'host'; NET.myId = 1; P.id = 1;
  NET.lobby = [{ id: 1, name: P.name }];
  TR.host(P.name);
  showScreen('lobby'); renderLobby();
}
function hostMsg(from, m) {
  if (m.k === 'hi') {
    const name = cleanName(m.name);
    if (!NET.lobby.some(p => p.id === from)) NET.lobby.push({ id: from, name });
    if (NET.lobby.length > 4) { netSend(from, { k: 'full' }); return; }
    netSend(from, { k: 'welcome', id: from, seed: G.seed, started: NET.started, world: NET.started ? worldState() : null });
    netSend(0, { k: 'lobby', players: NET.lobby });
    if (NET.started) { ensureRemote(from, name); showMsg(`${name} присоединился`, 2.5); }
    renderLobby();
  } else if (m.k === 'st') {
    const r = REMOTES.get(from); if (!r) return;
    const s = m.s || {};
    const num = v => typeof v === 'number' && isFinite(v);
    if (num(s.x) && num(s.z)) { r.tx = clamp(s.x, WORLD.minX, WORLD.maxX); r.tz = clamp(s.z, WORLD.minZ, WORLD.maxZ); }
    if (num(s.yaw)) r.tyaw = s.yaw; if (num(s.pitch)) r.pitch = s.pitch; if (num(s.hp)) r.hp = s.hp;
    r.light = !!s.light; r.alive = !!s.alive; r.running = !!s.running; r.lamp = !!s.lamp; r.house = s.house | 0; r.hiddenDoor = !!s.hd;
  } else if (m.k === 'door') { const d = Town.doors[m.d | 0]; if (d) toggleDoor(d, true); }
  else if (m.k === 'lock') { const d = Town.doors[m.d | 0]; if (d && d.owner >= 0) { if (m.l) setLockHost(d, true); else if (d.locked) { applyLock(d, false); netSend(0, { k: 'lock', d: d.id, l: 0 }); makeNoise(d.x, d.z, 12); } } }
  else if (m.k === 'curt') toggleCurtain(Town.windows[m.w | 0]);
  else if (m.k === 'loot') {
    const ct = Town.containers[m.c | 0]; if (!ct || ct.looted) return;
    ct.looted = true; netSend(0, { k: 'looted', c: ct.id, by: from });
  } else if (m.k === 'buy') {
    const it = String(m.it); if (!(it in Town.shop.stock)) return;
    if (Town.shop.stock[it] > 0 && shopOpen()) { Town.shop.stock[it]--; netSend(from, { k: 'bought', it }); netSend(0, { k: 'stock', stock: Town.shop.stock }); }
    else netSend(from, { k: 'nostock', it });
  }
}
function worldState() {
  return { clock: G.clock, day: G.day, night: G.night, doors: Town.doors.map(d => (d.open ? 1 : 0) + (d.broken ? 2 : 0) + (d.locked ? 4 : 0)), curt: Town.windows.map(w => (w.has ? 1 : 0) + (w.closed ? 2 : 0)),
           looted: Town.containers.filter(c => c.looted).map(c => c.id), lamps: Town.lamps.filter(l => l.broken).map(l => l.i),
           stock: Town.shop.stock, players: NET.lobby };
}
function hostTick(dt) {
  NET.sendT -= dt; if (NET.sendT > 0) return; NET.sendT = 0.09;
  const ps = [[P.id, P.name, +P.x.toFixed(2), +P.z.toFixed(2), +P.yaw.toFixed(2), +P.pitch.toFixed(2), Math.round(P.hp), P.light ? 1 : 0, P.alive ? 1 : 0, P.running ? 1 : 0]];
  for (const [id, r] of REMOTES) ps.push([id, r.name, +r.x.toFixed(2), +r.z.toFixed(2), +r.yaw.toFixed(2), +r.pitch.toFixed(2), Math.round(r.hp), r.light ? 1 : 0, r.alive ? 1 : 0, r.running ? 1 : 0]);
  netSend(0, { k: 'snap', c: +G.clock.toFixed(1), d: G.day, n: G.night, w: [+WD.x.toFixed(2), +WD.z.toFixed(2), +WD.yaw.toFixed(2), WD.state, WD.anim, +WD.speed.toFixed(1), WD.attackT > 0 ? +WD.attackT.toFixed(2) : 0], ps });
}

// ---------------------------------------------------------------------
//  Гость
// ---------------------------------------------------------------------
function joinGame(ip) {
  NET.mode = 'client';
  $('joinStatus').textContent = 'Подключение к ' + ip + '…';
  TR.join(ip);
}
function clientMsg(m) {
  if (m.k === 'welcome') {
    NET.myId = m.id; P.id = m.id; G.seed = m.seed | 0;
    if (m.started) startGameWorld(m.seed, m.world);
    else $('joinStatus').textContent = 'Ты в лобби. Ждём, пока хост начнёт игру…';
  } else if (m.k === 'full') { $('joinStatus').textContent = 'Комната заполнена (максимум 4 игрока)'; }
  else if (m.k === 'lobby') { NET.lobby = m.players || []; renderLobby(); $('joinStatus').textContent = 'В лобби: ' + NET.lobby.map(p => cleanName(p.name)).join(', '); }
  else if (m.k === 'start') { if (G.state !== 'play') startGameWorld(m.seed, m.world); }
  if (G.state !== 'play' && G.state !== 'dead') return;
  if (m.k === 'snap') {
    G.netClock = m.c; G.day = m.d; G.night = m.n;
    const w = m.w; WD.tx = w[0]; WD.tz = w[1]; WD.tyaw = w[2];
    if (WD.state !== w[3]) onWendigoState(WD.state, w[3]);
    if (WD.state === 'away' && w[3] !== 'away') { WD.x = w[0]; WD.z = w[1]; }
    WD.state = w[3]; WD.anim = w[4]; WD.speed = w[5]; WD.attackT = w[6];
    const seen = new Set();
    for (const p of m.ps) {
      const [id, name, x, z, yaw, pitch, hp, light, alive, running] = p; seen.add(id);
      if (id === NET.myId) continue;
      const r = ensureRemote(id, name);
      r.tx = x; r.tz = z; r.tyaw = yaw; r.pitch = pitch; r.hp = hp; r.light = !!light; r.alive = !!alive; r.running = !!running;
    }
    for (const id of [...REMOTES.keys()]) if (!seen.has(id)) dropRemote(id);
  } else if (m.k === 'door') applyDoor(Town.doors[m.d | 0], !!m.o, !!m.b);
  else if (m.k === 'lock') applyLock(Town.doors[m.d | 0], !!m.l);
  else if (m.k === 'curt') applyCurtain(Town.windows[m.w | 0], !!m.c);
  else if (m.k === 'looted') { const ct = Town.containers[m.c | 0]; if (ct) { const was = ct.looted; ct.looted = true; if (m.by === NET.myId && !was) addItems(ct.items, ct.money); } }
  else if (m.k === 'stock') { Town.shop.stock = m.stock; renderShop(); }
  else if (m.k === 'bought') shopBought(String(m.it));
  else if (m.k === 'nostock') showMsg('Этот товар закончился', 2);
  else if (m.k === 'hit') { if (m.id === NET.myId) takeHit(m.dmg); }
  else if (m.k === 'fx') worldFx(m.t, m.d);
  else if (m.k === 'lamp') { const l = Town.lamps[m.i | 0]; if (l) l.dying = 1.6; }
  else if (m.k === 'dawn') onDawn(m.day);
  else if (m.k === 'over') gameOver(m.nights);
  else if (m.k === 'win') winGame();
  else if (m.k === 'left') dropRemote(m.id);
}
function clientTick(dt) {
  NET.sendT -= dt; if (NET.sendT > 0) return; NET.sendT = 0.09;
  netSend(1, { k: 'st', s: { x: +P.x.toFixed(2), z: +P.z.toFixed(2), yaw: +P.yaw.toFixed(2), pitch: +P.pitch.toFixed(2), hp: Math.round(P.hp),
    light: P.light, alive: P.alive, running: P.running, lamp: P.lamp, house: P.inShop ? 99 : P.house, hd: P.hiddenDoor } });
}

// ---------------------------------------------------------------------
//  Другие игроки на экране
// ---------------------------------------------------------------------
const AV_COL = [0x8a2a2a, 0x2a5a8a, 0x3a7a3a, 0x8a6a2a];
function ensureRemote(id, name) {
  let r = REMOTES.get(id);
  if (r) { if (name) r.name = cleanName(name); return r; }
  r = { id, name: cleanName(name), x: Town.spawn.x, z: Town.spawn.z, tx: Town.spawn.x, tz: Town.spawn.z, yaw: 0, tyaw: 0, pitch: 0, hp: 100, light: false, alive: true, running: false, house: -1, lamp: false, hiddenDoor: false, phase: 0 };
  r.avatar = makeAvatar(AV_COL[id % 4], r.name); REMOTES.set(id, r);
  updatePlayerList(); return r;
}
function dropRemote(id) {
  const r = REMOTES.get(id); if (!r) return;
  scene.remove(r.avatar.g); if (r.avatar.spot) { scene.remove(r.avatar.spot); scene.remove(r.avatar.spot.target); }
  REMOTES.delete(id); updatePlayerList();
}
function makeAvatar(color, name) {
  const g = new THREE.Group(); scene.add(g);
  const std = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85 });
  const add = (geo, m, x, y, z, p = g) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; p.add(o); return o; };
  const legs = [], arms = [];
  for (const sx of [-1, 1]) { const hip = new THREE.Group(); hip.position.set(sx * 0.1, 0.9, 0); g.add(hip); add(new THREE.CapsuleGeometry(0.075, 0.75, 4, 8), std(0x22252a), 0, -0.45, 0, hip); legs.push(hip); }
  add(new THREE.CapsuleGeometry(0.21, 0.5, 4, 12), std(color), 0, 1.28, 0);
  add(new THREE.SphereGeometry(0.12, 16, 12), std(0xd2b49a), 0, 1.75, 0);
  add(new THREE.SphereGeometry(0.125, 14, 10, 0, 6.3, 0, 1.4), std(0x222222), 0, 1.78, -0.01);
  for (const sx of [-1, 1]) { const sh = new THREE.Group(); sh.position.set(sx * 0.27, 1.55, 0); g.add(sh); add(new THREE.CapsuleGeometry(0.06, 0.55, 4, 8), std(color), 0, -0.3, 0, sh); arms.push(sh); }
  // подпись с именем
  const c = document.createElement('canvas'); c.width = 256; c.height = 48; const x = c.getContext('2d');
  x.font = 'bold 28px Georgia'; x.textAlign = 'center'; x.fillStyle = 'rgba(0,0,0,0.5)'; x.fillRect(0, 4, 256, 40); x.fillStyle = '#fff'; x.fillText(name, 128, 34);
  const tag = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, transparent: true }));
  tag.scale.set(1.2, 0.22, 1); tag.position.y = 2.15; g.add(tag);
  const beam = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 2.2, 7, 24, 1, true).translate(0, -3.5, 0).rotateX(-Math.PI / 2), beamMaterial(7));
  beam.position.set(0.2, 1.45, 0.25); beam.frustumCulled = false; g.add(beam);
  let spot = null;
  if (quality >= 1) { spot = new THREE.SpotLight(0xfff0d8, 0, 20, 0.5, 0.5, 1.6); scene.add(spot); scene.add(spot.target); }
  return { g, legs, arms, beam, spot };
}
function updateRemotes(dt) {
  for (const r of REMOTES.values()) {
    r.x = lerp(r.x, r.tx, Math.min(1, dt * 10)); r.z = lerp(r.z, r.tz, Math.min(1, dt * 10)); r.yaw += angWrap(r.tyaw - r.yaw) * Math.min(1, dt * 10);
    const a = r.avatar, mv = Math.hypot(r.x - (r.px ?? r.x), r.z - (r.pz ?? r.z)) / Math.max(dt, 0.001); r.px = r.x; r.pz = r.z;
    r.phase += dt * mv * 2.2;
    const s = clamp(mv / 3, 0, 1);
    a.legs[0].rotation.x = Math.sin(r.phase) * 0.6 * s; a.legs[1].rotation.x = -Math.sin(r.phase) * 0.6 * s;
    a.arms[0].rotation.x = -Math.sin(r.phase) * 0.5 * s; a.arms[1].rotation.x = -0.9;
    a.g.position.set(r.x, 0, r.z); a.g.rotation.y = r.yaw + Math.PI;
    a.g.visible = r.alive; a.g.rotation.z = 0;
    a.beam.visible = r.alive && r.light && dayFactor(G.clock) < 0.6; a.beam.rotation.x = -r.pitch;
    if (a.spot) {
      a.spot.intensity = r.alive && r.light ? 2.4 : 0;
      a.spot.position.set(r.x, 1.5, r.z);
      a.spot.target.position.set(r.x - Math.sin(r.yaw) * 6, 1.5 + Math.sin(r.pitch) * 6, r.z - Math.cos(r.yaw) * 6);
    }
  }
}
function updatePlayerList() {
  const el = $('plist'); if (!el) return;
  el.textContent = NET.mode === 'solo' ? '' : '👥 ' + [P.name + (P.alive ? '' : ' ✝'), ...[...REMOTES.values()].map(r => r.name + (r.alive ? '' : ' ✝'))].join(', ');
}

// ---------------------------------------------------------------------
//  Лобби
// ---------------------------------------------------------------------
function renderLobby() {
  const box = $('lobbyPlayers'); if (!box) return;
  box.textContent = '';
  for (const p of NET.lobby) { const d = document.createElement('div'); d.textContent = '• ' + cleanName(p.name) + (p.id === 1 ? ' (хост)' : ''); box.appendChild(d); }
  $('lobbyIp').textContent = NET.mode === 'host' ? (NET.hostIp ? 'Твой адрес: ' + NET.hostIp : 'Запуск сервера…') : '';
  $('lobbyStart').classList.toggle('hidden', NET.mode !== 'host');
}
function renderFound() {
  const box = $('foundList'); box.textContent = '';
  if (!NET.found.size) { box.textContent = 'Поиск игр в сети…'; return; }
  for (const [ip, name] of NET.found) {
    const b = document.createElement('button'); b.className = 'room'; b.textContent = `${cleanName(name)} — ${ip}`;
    b.onclick = () => joinGame(ip); box.appendChild(b);
  }
}
