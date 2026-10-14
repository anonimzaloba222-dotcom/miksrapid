'use strict';
// =====================================================================
//  Деревня Кедровая: 31 дом, магазин, улицы, фонари, лес
// =====================================================================
const STREETS_Z = [-36, 0, 36], STREETS_X = [-48, 0, 48];
const LOT_X = [-74, -64, -31, -17, 17, 31, 64, 74];
const Town = { seed: 0, houses: [], shop: null, lamps: [], doors: [], containers: [], inter: [], spawn: { x: 9, z: -5 }, trees: [] };
const C = h => new THREE.Color(h);

// ---------------------------------------------------------------------
//  Сборщик геометрии: много коробок → одна сетка на материал
// ---------------------------------------------------------------------
class Geo {
  constructor() { this.p = []; this.n = []; this.u = []; this.c = []; }
  quad(a, b, c, d, n, uw, vh, col, u0 = 0, v0 = 0) {
    for (const v of [a, b, c, a, c, d]) this.p.push(v[0], v[1], v[2]);
    for (let i = 0; i < 6; i++) { this.n.push(n[0], n[1], n[2]); this.c.push(col.r, col.g, col.b); }
    for (const t of [[0, 0], [uw, 0], [uw, vh], [0, 0], [uw, vh], [0, vh]]) this.u.push(u0 + t[0], v0 + t[1]);
  }
  tri(a, b, c, n, uv, col) {
    for (const v of [a, b, c]) this.p.push(v[0], v[1], v[2]);
    for (let i = 0; i < 3; i++) { this.n.push(n[0], n[1], n[2]); this.c.push(col.r, col.g, col.b); }
    for (const t of uv) this.u.push(t[0], t[1]);
  }
  box(x0, y0, z0, x1, y1, z1, col, s = 1, f = 'px nx py ny pz nz') {
    if (x0 > x1) [x0, x1] = [x1, x0]; if (z0 > z1) [z0, z1] = [z1, z0];
    const w = x1 - x0, h = y1 - y0, d = z1 - z0;
    if (f.includes('pz')) this.quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1], [0, 0, 1], w * s, h * s, col);
    if (f.includes('nz')) this.quad([x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [0, 0, -1], w * s, h * s, col);
    if (f.includes('px')) this.quad([x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [1, 0, 0], d * s, h * s, col);
    if (f.includes('nx')) this.quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0], [-1, 0, 0], d * s, h * s, col);
    if (f.includes('py')) this.quad([x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0], [0, 1, 0], w * s, d * s, col);
    if (f.includes('ny')) this.quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [0, -1, 0], w * s, d * s, col);
  }
  mesh(mat, shadow = true) {
    if (!this.p.length) return null;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.u, 2));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.c, 3));
    g.computeBoundingSphere();
    const m = new THREE.Mesh(g, mat); m.castShadow = shadow; m.receiveShadow = true; scene.add(m); return m;
  }
}
// локальная система дома: фасад при lz=0, улица при lz<0; rot=0 или π
function Frame(cx, cz, rot) {
  const k = rot ? -1 : 1;
  return {
    k, cx, cz,
    x: lx => cx + lx * k, z: lz => cz + lz * k,
    pt: (lx, y, lz) => [cx + lx * k, y, cz + lz * k],
    n: (nx, ny, nz) => [nx * k, ny, nz * k],
    faces: f => k > 0 ? f : f.replace(/px/g, 'TMP').replace(/nx/g, 'px').replace(/TMP/g, 'nx').replace(/pz/g, 'TMP').replace(/nz/g, 'pz').replace(/TMP/g, 'nz'),
  };
}
function fbox(G, F, lx0, y0, lz0, lx1, y1, lz1, col, s, faces) { G.box(F.x(lx0), y0, F.z(lz0), F.x(lx1), y1, F.z(lz1), col, s, F.faces(faces || 'px nx py ny pz nz')); }
function fquad(G, F, a, b, c, d, n, uw, vh, col) { G.quad(F.pt(...a), F.pt(...b), F.pt(...c), F.pt(...d), F.n(...n), uw, vh, col); }
function fsolid(F, lx0, lz0, lx1, lz1, flags) { return markRect(F.x(lx0), F.z(lz0), F.x(lx1), F.z(lz1), flags); }

// ---------------------------------------------------------------------
//  Добыча в шкафах и холодильниках
// ---------------------------------------------------------------------
const ITEMS = {
  canned: { name: 'Консервы', icon: '🥫', food: 35, water: 0, price: 40 },
  bread: { name: 'Хлеб', icon: '🍞', food: 20, water: 0, price: 20 },
  water: { name: 'Вода', icon: '💧', food: 0, water: 40, price: 25 },
  soda: { name: 'Газировка', icon: '🥤', food: 5, water: 22, price: 15 },
  bandage: { name: 'Бинт', icon: '✚', heal: 30, price: 50 },
  battery: { name: 'Батарейки', icon: '🔋', price: 35 },
};
function rollLoot(kind) {
  const table = kind === 'fridge' ? ['water', 'water', 'soda', 'soda', 'canned', 'bread'] : ['canned', 'canned', 'bread', 'bandage', 'battery', 'water', 'soda'];
  const items = []; const n = RNG() < 0.25 ? 0 : RNG() < 0.65 ? 1 : 2;
  for (let i = 0; i < n; i++) items.push(spick(table));
  return { items, money: RNG() < 0.5 ? (5 + RNG() * 50 | 0) : 0 };
}
function addInter(type, x, y, z, w, h, d, ref) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), MT.hit); m.position.set(x, y, z); scene.add(m);
  const it = { type, mesh: m, pos: m.position, ref }; m.userData.inter = it; Town.inter.push(it); return it;
}

// ---------------------------------------------------------------------
//  Двери
// ---------------------------------------------------------------------
function makeDoor(F, lx, lz, width, h, mat, owner, glass, mirror) {
  const pivot = new THREE.Group(); const hx = mirror ? lx + width : lx, p = F.pt(hx, 0, lz); pivot.position.set(p[0], 0, p[2]);
  const base = (F.k > 0 ? 0 : Math.PI) + (mirror ? Math.PI : 0); pivot.rotation.y = base; scene.add(pivot);
  const panel = new THREE.Mesh(new THREE.BoxGeometry(width, h, 0.05), mat); panel.position.set(width / 2, h / 2, 0);
  panel.castShadow = true; panel.receiveShadow = true; pivot.add(panel);
  if (!glass) { const kn = new THREE.Mesh(new THREE.SphereGeometry(0.035, 10, 8), MT.metal); kn.position.set(width - 0.1, 1.0, 0.05); pivot.add(kn); }
  const d = { id: Town.doors.length, pivot, base, dir: mirror ? 1 : -1, open: false, ang: 0, broken: false, hp: 3, owner, cells: [], x: 0, z: 0 };
  d.cells = fsolid(F, lx, lz - 0.1, lx + width, lz + 0.12, DOORF);
  const c = F.pt(lx + width / 2, 0, lz); d.x = c[0]; d.z = c[2];
  addInter('door', c[0], 1.1, c[2], 1.0, 2.0, 0.4, d);
  Town.doors.push(d); applyDoorCollision(d);
  return d;
}
function applyDoorCollision(d) {
  for (const i of d.cells) { if (d.open) COL[i] &= ~(SOLID | OPAQUE); else COL[i] |= SOLID | OPAQUE; }
}

// ---------------------------------------------------------------------
//  Дом
// ---------------------------------------------------------------------
const SIDING_OLD = ['#9aa7a8', '#b7a98e', '#8f6f5a', '#a9b49a', '#c9c3b2', '#7d8a99', '#b08f7a', '#9c8f9e', '#d0c7a8', '#6f7a6a'].map(C);
const SIDING = ['#c9a06a', '#b08550', '#9a7448', '#d4b07a', '#5f86a8', '#6f9a62', '#c8a84e', '#a8584a', '#8a6a44', '#7aa0b0'].map(C); // сруб и крашеные доски
const ROOFS = ['#9a9a96', '#82827e', '#6a6e6a', '#6f8a6a', '#8a5a44', '#7a7a78'].map(C); // шифер и крашеная жесть
const TRIMS = ['#f2efe6', '#f2efe6', '#3f7ab0', '#e8d8a0', '#58a068'].map(C); // наличники
function buildHouse(GB, h) {
  const F = Frame(h.x, h.zf, h.rot), col = h.col, white = C('#d8d4c8'), wood = C('#f2dcc0'), fab = h.fab;
  const ext = GB.siding, int = GB.wall;
  const W = 4, D = 8, T = 0.2, HH = 3;
  // стены: снаружи обшивка, внутри обои
  fbox(ext, F, -W, 0, 0, -0.55, HH, T, col, 1, 'nz py nx px'); fbox(int, F, -W + T, 0, T, -0.55, HH, T + 0.001, white, 1, 'pz');
  fbox(ext, F, 0.55, 0, 0, W, HH, T, col, 1, 'nz py px nx'); fbox(int, F, 0.55, 0, T, W - T, HH, T + 0.001, white, 1, 'pz');
  fbox(ext, F, -0.55, 2.2, 0, 0.55, HH, T, col, 1, 'nz py ny'); fbox(int, F, -0.55, 2.2, T, 0.55, HH, T + 0.001, white, 1, 'pz');
  fbox(ext, F, -W, 0, D - T, W, HH, D, col, 1, 'pz py px nx'); fbox(int, F, -W + T, 0, D - T - 0.001, W - T, HH, D - T, white, 1, 'nz');
  fbox(ext, F, -W, 0, T, -W + T, HH, D - T, col, 1, 'nx py'); fbox(int, F, -W + T, 0, T, -W + T + 0.001, HH, D - T, white, 1, 'px');
  fbox(ext, F, W - T, 0, T, W, HH, D - T, col, 1, 'px py'); fbox(int, F, W - T - 0.001, 0, T, W - T, HH, D - T, white, 1, 'nx');
  for (const [a, b, c, d] of [[-W, 0, -0.55, T], [0.55, 0, W, T], [-W, D - T, W, D], [-W, T, -W + T, D - T], [W - T, T, W, D - T]]) fsolid(F, a, b, c, d, SOLID | OPAQUE);
  // фронтоны и крыша
  for (const sx of [-1, 1]) {
    const x = sx * W, a = F.pt(x, HH, 0), b = F.pt(x, HH, D), c = F.pt(x, 5.05, D / 2), n = F.n(sx, 0, 0);
    if (sx < 0) ext.tri(a, b, c, n, [[0, 0], [8, 0], [4, 2]], col); else ext.tri(b, a, c, n, [[0, 0], [8, 0], [4, 2]], col);
  }
  const rl = Math.hypot(2.15, 4.5);
  fquad(GB.roof, F, [W + 0.4, 2.9, -0.5], [-W - 0.4, 2.9, -0.5], [-W - 0.4, 5.05, D / 2], [W + 0.4, 5.05, D / 2], [0, 4.5 / rl, -2.15 / rl], 8.8, rl, h.roofCol);
  fquad(GB.roof, F, [-W - 0.4, 2.9, D + 0.5], [W + 0.4, 2.9, D + 0.5], [W + 0.4, 5.05, D / 2], [-W - 0.4, 5.05, D / 2], [0, 4.5 / rl, 2.15 / rl], 8.8, rl, h.roofCol);
  fquad(GB.plain, F, [-W - 0.4, 2.9, -0.5], [W + 0.4, 2.9, -0.5], [W + 0.4, 5.03, D / 2], [-W - 0.4, 5.03, D / 2], [0, -4.5 / rl, 2.15 / rl], 1, 1, C('#2a2622'));
  fquad(GB.plain, F, [W + 0.4, 2.9, D + 0.5], [-W - 0.4, 2.9, D + 0.5], [-W - 0.4, 5.03, D / 2], [W + 0.4, 5.03, D / 2], [0, -4.5 / rl, -2.15 / rl], 1, 1, C('#2a2622'));
  fbox(GB.brick, F, 2.2, 3.4, 5.2, 2.9, 6.0, 5.9, white, 1);
  // пол, потолок, крыльцо, дорожка
  fquad(GB.floor, F, [-W + T, 0.02, D - T], [W - T, 0.02, D - T], [W - T, 0.02, T], [-W + T, 0.02, T], [0, 1, 0], 7.6 / 2, 7.6 / 2, white);
  fquad(GB.floor, F, [-0.55, 0.02, T], [0.55, 0.02, T], [0.55, 0.02, 0], [-0.55, 0.02, 0], [0, 1, 0], 0.5, 0.1, white);
  fquad(GB.ceil, F, [-W + T, 2.95, T], [W - T, 2.95, T], [W - T, 2.95, D - T], [-W + T, 2.95, D - T], [0, -1, 0], 2, 2, white);
  fbox(GB.concrete, F, -1.1, 0, -1.1, 1.1, 0.14, 0, white, 0.5, 'py pz nz px nx');
  fquad(GB.concrete, F, [-0.6, 0.035, -1.1], [0.6, 0.035, -1.1], [0.6, 0.035, -2.5], [-0.6, 0.035, -2.5], [0, 1, 0], 0.6, 0.7, white);
  // окна (снаружи могут светиться ночью)
  const wins = [[-2.4, 0, -1], [2.4, 0, -1]], winB = h.lit ? GB.winL : GB.win;
  for (const [lx] of wins) {
    fquad(winB, F, [lx + 0.55, 1.0, -0.006], [lx - 0.55, 1.0, -0.006], [lx - 0.55, 2.3, -0.006], [lx + 0.55, 2.3, -0.006], [0, 0, -1], 1, 1, white);
    fquad(GB.win, F, [lx - 0.55, 1.0, T + 0.004], [lx + 0.55, 1.0, T + 0.004], [lx + 0.55, 2.3, T + 0.004], [lx - 0.55, 2.3, T + 0.004], [0, 0, 1], 1, 1, white);
    fbox(GB.plain, F, lx - 0.65, 0.92, -0.12, lx + 0.65, 1.0, 0, C('#cfcabc'), 1, 'py nz px nx');
  }
  for (const sx of [-1, 1]) {
    const x = sx * (W + 0.006), xi = sx * (W - T - 0.004);
    const a = [x, 1.0, 3.4], b = [x, 1.0, 4.6], c = [x, 2.3, 4.6], d = [x, 2.3, 3.4];
    if (sx > 0) fquad(winB, F, b, a, d, c, [1, 0, 0], 1, 1, white); else fquad(winB, F, a, b, c, d, [-1, 0, 0], 1, 1, white);
    if (sx > 0) fquad(GB.win, F, [xi, 1.0, 3.4], [xi, 1.0, 4.6], [xi, 2.3, 4.6], [xi, 2.3, 3.4], [-1, 0, 0], 1, 1, white);
    else fquad(GB.win, F, [xi, 1.0, 4.6], [xi, 1.0, 3.4], [xi, 2.3, 3.4], [xi, 2.3, 4.6], [1, 0, 0], 1, 1, white);
  }
  // штакетник с воротцами
  const fc = h.fence, FX = 4.9;
  for (let lx = -FX; lx <= FX; lx += 0.3) if (Math.abs(lx) > 0.95) fbox(GB.plain, F, lx - 0.04, 0, -2.45, lx + 0.04, 1.0 + ((lx * 10 | 0) % 2 ? 0.04 : 0), -2.39, fc, 1, 'px nx py pz nz');
  for (const y of [0.3, 0.75]) { fbox(GB.plain, F, -FX - 0.05, y, -2.39, -0.95, y + 0.07, -2.34, fc, 1, 'py pz nz ny'); fbox(GB.plain, F, 0.95, y, -2.39, FX + 0.05, y + 0.07, -2.34, fc, 1, 'py pz nz ny'); }
  fsolid(F, -FX, -2.5, -0.95, -2.34, SOLID); fsolid(F, 0.95, -2.5, FX, -2.34, SOLID);
  for (const px of [-0.95, 0.95]) fbox(GB.dwood, F, px - 0.1, 0, -2.5, px + 0.1, 1.45, -2.3, h.trim, 1);
  // тропинка от калитки к крыльцу (утоптанная земля)
  GB.asphalt.quad(...[F.pt(-0.7, 0.03, -1.1), F.pt(0.7, 0.03, -1.1), F.pt(0.7, 0.03, -5.4), F.pt(-0.7, 0.03, -5.4)], [0, 1, 0], 0.35, 1.1, C('#fff'), h.x * 0.1, h.zf * 0.1);
  // навес над крыльцом на столбах
  for (const px of [-1.0, 1.0]) fbox(GB.dwood, F, px - 0.07, 0, -1.05, px + 0.07, 2.5, -0.91, h.trim, 1);
  fbox(GB.dwood, F, -1.3, 2.5, -1.2, 1.3, 2.62, 0, h.roofCol, 1);
  // наличники и ставни на окнах
  const T2 = h.trim, nal = (lx, side) => {
    const w = 0.55, y0 = 1.0, y1 = 2.3;
    if (!side) {
      fbox(GB.dwood, F, lx - w - 0.16, y0 - 0.12, -0.1, lx - w, y1 + 0.1, -0.02, T2, 1); fbox(GB.dwood, F, lx + w, y0 - 0.12, -0.1, lx + w + 0.16, y1 + 0.1, -0.02, T2, 1);
      fbox(GB.dwood, F, lx - w - 0.2, y1, -0.1, lx + w + 0.2, y1 + 0.2, -0.02, T2, 1); fbox(GB.dwood, F, lx - w - 0.1, y0 - 0.2, -0.12, lx + w + 0.1, y0 - 0.1, -0.02, T2, 1);
      fbox(GB.dwood, F, lx - 0.03, y0, -0.06, lx + 0.03, y1, -0.01, T2, 1);
      if (h.shut) for (const sx of [-1, 1]) fbox(GB.dwood, F, sx > 0 ? lx + w + 0.16 : lx - w - 0.16 - 0.5, y0 - 0.1, -0.08, sx > 0 ? lx + w + 0.16 + 0.5 : lx - w - 0.16, y1 + 0.1, -0.02, h.shutCol, 1);
    }
  };
  nal(-2.4); nal(2.4);
  for (const sx of [-1, 1]) { const x = sx * (W + 0.01), xo = sx * (W + 0.08); fbox(GB.dwood, F, Math.min(x, xo), 0.88, 3.2, Math.max(x, xo), 1.0, 4.8, T2, 1); fbox(GB.dwood, F, Math.min(x, xo), 2.3, 3.2, Math.max(x, xo), 2.5, 4.8, T2, 1); fbox(GB.dwood, F, Math.min(x, xo), 1.0, 3.2, Math.max(x, xo), 2.3, 3.4, T2, 1); fbox(GB.dwood, F, Math.min(x, xo), 1.0, 4.6, Math.max(x, xo), 2.3, 4.8, T2, 1); }
  // дровница и колодец во дворе
  if (h.wood) {
    for (let r = 0; r < 4; r++) for (let c = 0; c < 6 - (r >> 1); c++) fbox(GB.siding, F, 2.6 + c * 0.2 + (r >> 1) * 0.1, r * 0.2, -2.1, 2.78 + c * 0.2 + (r >> 1) * 0.1, r * 0.2 + 0.19, -1.25, SIDING[(r * 7 + c * 3 + h.id) % 4], 1);
    fsolid(F, 2.5, -2.1, 3.9, -1.25, SOLID);
  }
  if (h.well) {
    const wx = -3.4, wz = -1.9;
    fbox(GB.siding, F, wx - 0.5, 0, wz - 0.5, wx + 0.5, 0.85, wz + 0.5, C('#8a6a44'), 1, 'px nx pz nz py'); fbox(GB.plain, F, wx - 0.3, 0.84, wz - 0.3, wx + 0.3, 0.86, wz + 0.3, C('#0c1014'), 1, 'py');
    for (const sx of [-1, 1]) fbox(GB.dwood, F, wx + sx * 0.52 - 0.05, 0.85, wz - 0.05, wx + sx * 0.52 + 0.05, 2.1, wz + 0.05, C('#6a4a2c'), 1);
    fbox(GB.dwood, F, wx - 0.6, 1.7, wz - 0.03, wx + 0.6, 1.76, wz + 0.03, C('#6a4a2c'), 1);
    fquad(GB.roof, F, [wx - 0.8, 1.95, wz - 0.7], [wx - 0.8, 1.95, wz + 0.7], [wx, 2.45, wz + 0.7], [wx, 2.45, wz - 0.7], [-0.53, 0.85, 0], 1.4, 1, h.roofCol);
    fquad(GB.roof, F, [wx + 0.8, 1.95, wz + 0.7], [wx + 0.8, 1.95, wz - 0.7], [wx, 2.45, wz - 0.7], [wx, 2.45, wz + 0.7], [0.53, 0.85, 0], 1.4, 1, h.roofCol);
    fsolid(F, wx - 0.5, wz - 0.5, wx + 0.5, wz + 0.5, SOLID);
  }
  // мебель
  fbox(GB.wood, F, -3.7, 0, 5.6, -2.1, 0.42, 7.75, wood, 1); fbox(GB.fabric, F, -3.65, 0.42, 5.65, -2.15, 0.62, 7.7, fab, 1);
  fbox(GB.fabric, F, -3.6, 0.62, 7.2, -2.2, 0.74, 7.6, C('#c8c2b0'), 1); fbox(GB.wood, F, -3.75, 0, 7.72, -2.05, 1.1, 7.8, wood, 1);
  fsolid(F, -3.7, 5.6, -2.1, 7.8, SOLID);
  fbox(GB.wood, F, 0.6, 0.74, 4.1, 1.8, 0.79, 4.9, wood, 1);
  for (const [a, b] of [[0.65, 4.15], [1.7, 4.15], [0.65, 4.8], [1.7, 4.8]]) fbox(GB.wood, F, a, 0, b, a + 0.06, 0.74, b + 0.06, wood, 1);
  for (const lz of [3.6, 5.3]) { fbox(GB.wood, F, 0.95, 0.44, lz - 0.2, 1.4, 0.48, lz + 0.2, wood, 1); fbox(GB.wood, F, 0.95, 0.48, lz > 4.5 ? lz + 0.16 : lz - 0.2, 1.4, 0.95, lz > 4.5 ? lz + 0.2 : lz - 0.16, wood, 1); }
  fsolid(F, 0.6, 4.1, 1.8, 4.9, SOLID);
  fquad(GB.fabric, F, [-1.6, 0.025, 5.2], [0.4, 0.025, 5.2], [0.4, 0.025, 2.4], [-1.6, 0.025, 2.4], [0, 1, 0], 1, 1.4, h.rug);
  fbox(GB.wood, F, 0.8, 0, 7.2, 3.0, 0.9, 7.8, wood, 1); fbox(GB.plain, F, 0.78, 0.9, 7.15, 3.02, 0.95, 7.8, C('#b9b3a4'), 1);
  fsolid(F, 0.8, 7.2, 3.0, 7.8, SOLID);
  fbox(GB.wood, F, 3.4, 0, 1.0, 3.78, 1.8, 2.4, wood, 1); fsolid(F, 3.4, 1.0, 3.8, 2.4, SOLID);
  // шкаф и холодильник — в них припасы
  fbox(GB.wood, F, -3.78, 0, 1.2, -3.18, 2.0, 2.3, wood, 1); fsolid(F, -3.8, 1.2, -3.18, 2.3, SOLID);
  fbox(GB.plain, F, 3.15, 0, 6.5, 3.78, 1.8, 7.15, C('#d6d2c4'), 1); fsolid(F, 3.15, 6.5, 3.8, 7.15, SOLID);
  for (const [kind, lx, lz] of [['cupboard', -3.3, 1.75], ['fridge', 3.3, 6.82]]) {
    const p = F.pt(lx, 1.0, lz), loot = rollLoot(kind);
    const ct = { id: Town.containers.length, kind, looted: false, items: loot.items, money: loot.money, house: h.id };
    Town.containers.push(ct); addInter('loot', p[0], 1.0, p[2], 0.9, 1.8, 0.9, ct);
  }
  h.door = makeDoor(F, -0.55, 0.1, 1.1, 2.2, MT.door, h.id);
  h.door.open = RNG() < 0.35; h.door.ang = h.door.open ? 1 : 0; applyDoorCollision(h.door);
  const a = F.pt(-W, 0, 0), b = F.pt(W, 0, D);
  h.bounds = { x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), z0: Math.min(a[2], b[2]), z1: Math.max(a[2], b[2]) };
}

// ---------------------------------------------------------------------
//  Магазин
// ---------------------------------------------------------------------
function buildShop(GB, s) {
  const F = Frame(s.x, s.zf, s.rot), white = C('#d8d4c8');
  const W = 9, D = 10, HH = 4, T = 0.3;
  fbox(GB.brick, F, -W, 0, 0, -1.1, 0.8, T, white, 1); fbox(GB.brick, F, 1.1, 0, 0, W, 0.8, T, white, 1);
  fbox(GB.brick, F, -W, 3.0, 0, W, HH + 0.6, T, white, 1);
  fbox(GB.brick, F, -W, 0.8, 0, -8.2, 3.0, T, white, 1); fbox(GB.brick, F, 8.2, 0.8, 0, W, 3.0, T, white, 1);
  fbox(GB.brick, F, -W, 0, D - T, W, HH + 0.6, D, white, 1);
  fbox(GB.brick, F, -W, 0, T, -W + T, HH + 0.6, D - T, white, 1); fbox(GB.brick, F, W - T, 0, T, W, HH + 0.6, D - T, white, 1);
  for (const [a, b, c, d] of [[-W, 0, -1.1, T], [1.1, 0, W, T], [-W, D - T, W, D], [-W, T, -W + T, D - T], [W - T, T, W, D - T]]) fsolid(F, a, b, c, d, SOLID | OPAQUE);
  // большие витрины
  for (const [a, b] of [[-8.2, -1.6], [1.6, 8.2]]) {
    fquad(GB.glassShop, F, [a, 0.8, 0.15], [b, 0.8, 0.15], [b, 3.0, 0.15], [a, 3.0, 0.15], [0, 0, -1], 1, 1, white);
    fbox(GB.plain, F, a, 0.8, 0.1, b, 0.86, 0.3, C('#ddd'), 1); fbox(GB.plain, F, b - 0.05, 0.8, 0.1, b + 0.05, 3.0, 0.3, C('#ddd'), 1);
  }
  for (const [a, b] of [[-5.6, -4.4], [4.4, 5.6], [-3.4, -3.0], [3.0, 3.4]]) fbox(GB.brick, F, a, 0.8, -0.02, b, 3.0, T, white, 1, 'px nx pz nz');
  fbox(GB.plain, F, -1.6, 0.8, 0.1, -1.1, 3.0, 0.3, C('#ddd'), 1); fbox(GB.plain, F, 1.1, 0.8, 0.1, 1.6, 3.0, 0.3, C('#ddd'), 1);
  fbox(GB.plain, F, -W - 0.2, HH + 0.6, -0.2, W + 0.2, HH + 0.8, D + 0.2, C('#3a3836'), 1);
  // интерьер
  fquad(GB.concrete, F, [-W + T, 0.02, D - T], [W - T, 0.02, D - T], [W - T, 0.02, T], [-W + T, 0.02, T], [0, 1, 0], 8, 5, white);
  fquad(GB.concrete, F, [-1.1, 0.02, T], [1.1, 0.02, T], [1.1, 0.02, 0], [-1.1, 0.02, 0], [0, 1, 0], 1, 0.15, white);
  fquad(GB.ceil, F, [-W + T, HH - 0.05, T], [W - T, HH - 0.05, T], [W - T, HH - 0.05, D - T], [-W + T, HH - 0.05, D - T], [0, -1, 0], 6, 4, white);
  fbox(GB.wall, F, -W + T, 0, D - T - 0.002, W - T, HH, D - T, white, 1, 'nz');
  fbox(GB.wall, F, -W + T, 0, T, -W + T + 0.002, HH, D - T, white, 1, 'px'); fbox(GB.wall, F, W - T - 0.002, 0, T, W - T, HH, D - T, white, 1, 'nx');
  // стеллажи с товарами
  const prodC = ['#a83a2a', '#d8b03a', '#3a6aa8', '#e8e0c8', '#4a8a3a', '#8a3a6a', '#c86a2a'].map(C);
  for (const lx0 of [-6.5, -2.5, 1.5]) {
    fbox(GB.metal, F, lx0, 0, 4.0, lx0 + 2.8, 1.9, 4.6, C('#8a8a88'), 1); fsolid(F, lx0, 4.0, lx0 + 2.8, 4.6, SOLID);
    for (let y = 0.25; y < 1.8; y += 0.45) for (let x = lx0 + 0.1; x < lx0 + 2.7; x += srand(0.14, 0.24)) {
      const w = srand(0.1, 0.18), hh = srand(0.15, 0.32);
      for (const sz of [3.95, 4.65]) fbox(GB.paint, F, x, y, sz - 0.12, x + w, y + hh, sz + 0.12, spick(prodC), 1);
    }
  }
  // холодильник с напитками вдоль задней стены
  fbox(GB.metal, F, -6, 0, D - 1.2, 2, 2.2, D - T, C('#cfcfcf'), 1); fsolid(F, -6, D - 1.2, 2, D - T, SOLID);
  fquad(GB.fridgeGlow, F, [2, 0.2, D - 1.21], [-6, 0.2, D - 1.21], [-6, 2.0, D - 1.21], [2, 2.0, D - 1.21], [0, 0, -1], 1, 1, white);
  // прилавок и касса
  fbox(GB.wood, F, 3.2, 0, 1.6, 7.5, 1.0, 2.3, C('#8a6a4a'), 1); fbox(GB.plain, F, 3.15, 1.0, 1.55, 7.55, 1.05, 2.35, C('#2a2a2a'), 1);
  fbox(GB.paint, F, 4.0, 1.05, 1.7, 4.5, 1.35, 2.1, C('#333'), 1); fsolid(F, 3.2, 1.6, 7.5, 2.3, SOLID);
  // лампы дневного света
  for (const lx of [-5, 0, 5]) fbox(GB.fluor, F, lx - 1.2, HH - 0.12, 4.9, lx + 1.2, HH - 0.06, 5.1, white, 1, 'ny');
  // вывеска
  const sg = new THREE.Mesh(new THREE.PlaneGeometry(7, 1.2), MT.sign);
  const sp = F.pt(0, 3.75, -0.02); sg.position.set(sp[0], sp[1], sp[2]); sg.rotation.y = F.k > 0 ? Math.PI : 0; scene.add(sg); s.signMesh = sg;
  // двери (стеклянные), продавец, касса
  s.door = makeDoor(F, -1.1, 0.15, 1.1, 2.6, MT.doorGlass, -1, true);
  s.door2 = makeDoor(F, 0, 0.15, 1.1, 2.6, MT.doorGlass, -1, true, true);
  const kp = F.pt(5.4, 0, 3.0); s.keeperPos = { x: kp[0], z: kp[2] };
  const cp = F.pt(5.4, 1.2, 1.95); s.counter = addInter('shop', cp[0], 1.2, cp[2], 4.3, 1.0, 1.0, s);
  const lp = [F.pt(-4, HH - 0.5, 5), F.pt(4, HH - 0.5, 5)];
  s.lights = lp.map(p => { const l = new THREE.PointLight(0xe8f0ff, 0, 14, 2); l.position.set(p[0], p[1], p[2]); scene.add(l); return l; });
  const a = F.pt(-W, 0, 0), b = F.pt(W, 0, D);
  s.bounds = { x0: Math.min(a[0], b[0]), x1: Math.max(a[0], b[0]), z0: Math.min(a[2], b[2]), z1: Math.max(a[2], b[2]) };
  s.stock = { canned: 6, bread: 6, water: 8, soda: 8, bandage: 3, battery: 4 };
}
function makeKeeper() {
  const g = new THREE.Group(); scene.add(g);
  const std = c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8 });
  const add = (geo, m, x, y, z) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); o.castShadow = true; g.add(o); return o; };
  add(new THREE.CapsuleGeometry(0.22, 0.6, 4, 10), std(0x5a5048), 0, 1.15, 0);
  add(new THREE.SphereGeometry(0.13, 16, 12), std(0xc8a890), 0, 1.72, 0);
  add(new THREE.CapsuleGeometry(0.1, 0.7, 4, 8), std(0x2a2a30), -0.1, 0.45, 0); add(new THREE.CapsuleGeometry(0.1, 0.7, 4, 8), std(0x2a2a30), 0.1, 0.45, 0);
  add(new THREE.SphereGeometry(0.135, 14, 10, 0, 6.3, 0, 1.3), std(0xdddddd), 0, 1.75, -0.01);
  add(new THREE.BoxGeometry(0.46, 0.5, 0.05), std(0x3a6a8a), 0, 1.15, 0.2);
  return g;
}

// ---------------------------------------------------------------------
//  Деревья (инстансы), машины, остановка
// ---------------------------------------------------------------------
function pineGeometry() {
  const parts = [];
  const add = (r, h, y, shade) => {
    const g = new THREE.ConeGeometry(r, h, 9, 1).toNonIndexed(); g.translate(0, y, 0);
    const n = g.attributes.position.count, col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { const yy = g.attributes.position.getY(i); const k = shade * (0.75 + 0.35 * clamp((yy - y + h / 2) / h, 0, 1)); col[i * 3] = 0.5 * k; col[i * 3 + 1] = 0.75 * k; col[i * 3 + 2] = 0.55 * k; }
    g.setAttribute('color', new THREE.BufferAttribute(col, 3)); parts.push(g);
  };
  add(2.0, 3.2, 2.6, 0.75); add(1.65, 2.8, 4.1, 0.85); add(1.25, 2.4, 5.5, 0.95); add(0.8, 2.0, 6.8, 1.05);
  const pos = [], nor = [], uv = [], colA = [];
  for (const g of parts) { pos.push(...g.attributes.position.array); nor.push(...g.attributes.normal.array); uv.push(...g.attributes.uv.array); colA.push(...g.attributes.color.array); }
  const m = new THREE.BufferGeometry();
  m.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); m.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  m.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); m.setAttribute('color', new THREE.Float32BufferAttribute(colA, 3));
  return m;
}
function birchCrown() {
  const pos = [], nor = [], uv = [], col = [];
  const blobs = [[0, 5.2, 0, 1.3, 1], [0.7, 4.2, 0.3, 1.0, 0.85], [-0.6, 4.4, -0.4, 1.0, 0.9], [0.1, 6.2, 0.1, 0.8, 1.1]];
  for (const [x, y, z, r, k] of blobs) {
    const g = new THREE.IcosahedronGeometry(r, 1).toNonIndexed(); g.translate(x, y, z);
    for (let i = 0; i < g.attributes.position.count; i++) { const n = 0.8 + 0.4 * ((Math.sin(i * 12.9 + x * 7 + y) + 1) / 2); col.push(0.5 * k * n, 0.55 * k * n, 0.18 * k * n); }
    pos.push(...g.attributes.position.array); nor.push(...g.attributes.normal.array); uv.push(...g.attributes.uv.array);
  }
  const m = new THREE.BufferGeometry();
  m.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); m.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  m.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); m.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  return m;
}
function buildTrees(list) {
  const dummy = new THREE.Object3D(), pines = list.filter(t => !t.b), birches = list.filter(t => t.b);
  const parts = [
    [pines, new THREE.CylinderGeometry(0.16, 0.3, 3.0, 8).translate(0, 1.5, 0), MT.bark, pineGeometry(), MT.pine],
    [birches, new THREE.CylinderGeometry(0.1, 0.17, 5.4, 8).translate(0, 2.7, 0), MT.birch, birchCrown(), MT.birchLeaf],
  ];
  for (const [arr, tg, tm, cg, cm] of parts) {
    if (!arr.length) continue;
    const trunk = new THREE.InstancedMesh(tg, tm, arr.length), crown = new THREE.InstancedMesh(cg, cm, arr.length);
    arr.forEach((t, i) => {
      dummy.position.set(t.x, 0, t.z); dummy.rotation.set(0, t.r, 0); dummy.scale.set(t.s, t.s * t.h, t.s); dummy.updateMatrix();
      trunk.setMatrixAt(i, dummy.matrix); crown.setMatrixAt(i, dummy.matrix);
      markRect(t.x - 0.3 * t.s, t.z - 0.3 * t.s, t.x + 0.3 * t.s, t.z + 0.3 * t.s, SOLID | OPAQUE);
    });
    for (const m of [trunk, crown]) { m.castShadow = true; m.receiveShadow = true; scene.add(m); }
  }
}
function buildCar(GB, x, z, alongX, col) {
  const L = 4.3, Wd = 1.8, b = (a0, y0, b0, a1, y1, b1, G, c) => alongX ? G.box(x + a0, y0, z + b0, x + a1, y1, z + b1, c, 1) : G.box(x + b0, y0, z + a0, x + b1, y1, z + a1, c, 1);
  b(-L / 2, 0.35, -Wd / 2, L / 2, 1.0, Wd / 2, GB.paint, col);
  b(-1.1, 1.0, -Wd / 2 + 0.12, 0.9, 1.55, Wd / 2 - 0.12, GB.glassCar, C('#fff'));
  b(-1.05, 1.55, -Wd / 2 + 0.15, 0.85, 1.6, Wd / 2 - 0.15, GB.paint, col);
  for (const [a, c] of [[-1.35, -0.92], [1.35, -0.92], [-1.35, 0.92], [1.35, 0.92]]) b(a - 0.33, 0, c - 0.12, a + 0.33, 0.66, c + 0.12, GB.plain, C('#151515'));
  if (alongX) markRect(x - L / 2, z - Wd / 2, x + L / 2, z + Wd / 2, SOLID | OPAQUE); else markRect(x - Wd / 2, z - L / 2, x + Wd / 2, z + L / 2, SOLID | OPAQUE);
}

// ---------------------------------------------------------------------
//  Город целиком
// ---------------------------------------------------------------------
function buildWorld(seed) {
  Town.seed = seed; RNG = mulberry32(seed);
  const GB = {};
  for (const k of ['siding', 'wall', 'roof', 'plain', 'brick', 'floor', 'ceil', 'concrete', 'win', 'winL', 'wood', 'fabric', 'paint', 'metal', 'glassShop', 'fridgeGlow', 'fluor', 'glassCar', 'asphalt', 'dwood', 'puddle', 'mark']) GB[k] = new Geo();

  // ---- земля и дороги ----
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(260, 200), MT.grass); ground.rotation.x = -Math.PI / 2;
  MT.grass.map.repeat.set(260 / 6, 200 / 6); MT.grass.normalMap.repeat.copy(MT.grass.map.repeat);
  ground.receiveShadow = true; scene.add(ground);
  const road = (x0, z0, x1, z1) => GB.asphalt.quad([x0, 0.02, z1], [x1, 0.02, z1], [x1, 0.02, z0], [x0, 0.02, z0], [0, 1, 0], (x1 - x0) / 4, (z1 - z0) / 4, C('#fff'), x0 / 4, -z1 / 4);
  // грунтовые дороги: узкая колея, обочины заросли травой, лужи
  const HW = 3.2;
  const rut = (x0, z0, x1, z1) => GB.mark.quad([x0, 0.026, z1], [x1, 0.026, z1], [x1, 0.026, z0], [x0, 0.026, z0], [0, 1, 0], 1, 1, C('#fff'));
  for (const zs of STREETS_Z) {
    road(-104, zs - HW, 104, zs + HW);
    for (const o of [-1.05, 1.05]) rut(-104, zs + o - 0.28, 104, zs + o + 0.28);
  }
  for (const xs of STREETS_X) {
    road(xs - HW, -66, xs + HW, -40); road(xs - HW, -32, xs + HW, -4); road(xs - HW, 4, xs + HW, 32); road(xs - HW, 40, xs + HW, 66);
    for (const o of [-1.05, 1.05]) for (const [a, b] of [[-66, -40], [-32, -4], [4, 32], [40, 66]]) rut(xs + o - 0.28, a, xs + o + 0.28, b);
  }
  for (let i = 0; i < 30; i++) { // лужи
    const zs = spick(STREETS_Z) + srand(-1.8, 1.8), x = srand(-100, 100), r = srand(0.6, 1.5);
    GB.puddle.quad([x - r, 0.03, zs + r * 0.6], [x + r, 0.03, zs + r * 0.6], [x + r, 0.03, zs - r * 0.6], [x - r, 0.03, zs - r * 0.6], [0, 1, 0], 1, 1, C('#fff'));
  }

  // ---- участки ----
  const lots = [];
  for (const zs of STREETS_Z) for (const sd of [-1, 1]) for (const x of LOT_X) lots.push({ x, zs, sd });
  const shopLots = lots.filter(l => l.zs === 0 && l.sd === -1 && (l.x === 17 || l.x === 31));
  const rest = sshuffle(lots.filter(l => !shopLots.includes(l)));
  const houseLots = rest.slice(0, 31), emptyLots = rest.slice(31);
  Town.shop = { x: 24, zf: -8.5, rot: 1 };
  buildShop(GB, Town.shop);
  houseLots.forEach((l, i) => {
    const h = { id: i, x: l.x, zf: l.zs + l.sd * 8.5, rot: l.sd < 0 ? 1 : 0, col: spick(SIDING), roofCol: spick(ROOFS), lit: RNG() < 0.3,
                fab: C(spick(['#6a3a34', '#3a4a6a', '#5a6a3a', '#7a6a4a'])), trim: spick(TRIMS), shut: RNG() < 0.55, shutCol: C(spick(['#3f6a9a', '#4a7a4a', '#8a3a30', '#2f5a6a'])), wood: RNG() < 0.5, well: RNG() < 0.3,
                rug: C(spick(['#5a2a24', '#2a3a4a', '#4a3a2a'])), fence: C(spick(['#8a6a44', '#5f86a8', '#6f9a62', '#c9b890', '#a8584a'])) };
    Town.houses.push(h); buildHouse(GB, h);
  });

  // ---- деревья: лес вокруг и во дворах ----
  const trees = [];
  const nearRoad = (x, z) => STREETS_Z.some(zs => Math.abs(z - zs) < 7 && Math.abs(x) < 106) || STREETS_X.some(xs => Math.abs(x - xs) < 7 && Math.abs(z) < 68);
  for (let i = 0; i < 2600 && trees.length < 950; i++) {
    const x = srand(-111, 111), z = srand(-85, 85);
    if (Math.abs(x) < 86 && Math.abs(z) < 58) continue;
    if (nearRoad(x, z)) continue;
    if (trees.some(t => Math.abs(t.x - x) < 2.6 && Math.abs(t.z - z) < 2.6)) continue;
    trees.push({ x, z, s: srand(0.8, 1.35), h: srand(0.85, 1.3), r: srand(0, 6.3), b: RNG() < 0.3 });
  }
  for (const l of emptyLots) {
    const zc = l.zs + l.sd * 12.5;
    for (let k = 0; k < 3; k++) { const x = l.x + srand(-4, 4), z = zc + srand(-3, 3); trees.push({ x, z, s: srand(0.6, 1.0), h: srand(0.8, 1.1), r: srand(0, 6.3), b: RNG() < 0.5 }); }
  }
  for (let i = 0; i < 40; i++) { // берёзы вдоль дорог
    const zs = spick(STREETS_Z), x = srand(-98, 98), z = zs + (RNG() < 0.5 ? -1 : 1) * srand(4.6, 5.6);
    if (STREETS_X.some(xs => Math.abs(x - xs) < 6) || houseLots.some(l => l.zs === zs && Math.abs(l.x - x) < 5.6 && Math.sign(z - zs) === l.sd)) continue;
    trees.push({ x, z, s: srand(0.7, 1.0), h: srand(0.9, 1.2), r: srand(0, 6.3), b: true });
  }
  Town.trees = trees; buildTrees(trees);

  // ---- фонари ----
  const lampSpots = [];
  for (const zs of STREETS_Z) for (let x = -92, k = 0; x <= 92; x += 17, k++) if (!STREETS_X.some(xs => Math.abs(x - xs) < 8)) lampSpots.push({ x, z: zs + (k % 2 ? 5.4 : -5.4), dx: 0, dz: k % 2 ? -1 : 1 });
  for (const xs of STREETS_X) for (const z of [-54, -20, 20, 54]) lampSpots.push({ x: xs + 5.4, z, dx: -1, dz: 0 });
  buildLamps(lampSpots);
  { // провода между столбами
    const pts = [];
    for (let i = 1; i < lampSpots.length; i++) {
      const a = lampSpots[i - 1], b = lampSpots[i];
      if (Math.hypot(a.x - b.x, a.z - b.z) > 20) continue;
      for (const dy of [0, 0.35]) for (let k = 0; k < 8; k++) {
        const t0 = k / 8, t1 = (k + 1) / 8, sag = t => -0.9 * 4 * t * (1 - t);
        pts.push(a.x + (b.x - a.x) * t0, 5.6 - dy + sag(t0), a.z + (b.z - a.z) * t0, a.x + (b.x - a.x) * t1, 5.6 - dy + sag(t1), a.z + (b.z - a.z) * t1);
      }
    }
    const wg = new THREE.BufferGeometry(); wg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const wires = new THREE.LineSegments(wg, new THREE.LineBasicMaterial({ color: 0x0e0e10 })); wires.frustumCulled = false; scene.add(wires);
  }

  // ---- машины, остановка ----
  const carC = ['#6a1a1a', '#1a3a5a', '#4a4a48', '#7a6a3a', '#2a4a2a', '#8a8a86', '#3a2a4a'].map(C);
  const carSpots = [[-80, -34.2, 1], [-22, 1.8, 1], [36, 37.8, 1], [70, -1.8, 1], [-46.2, 18, 0], [1.8, -50, 0], [49.8, 26, 0]];
  for (const [x, z, ax] of carSpots) buildCar(GB, x, z, !!ax, spick(carC));
  GB.metal.box(7.4, 0, -7.6, 7.5, 2.4, -6.4, C('#556'), 1); GB.metal.box(11.4, 0, -7.6, 11.5, 2.4, -6.4, C('#556'), 1);
  GB.metal.box(7.3, 2.4, -7.8, 11.6, 2.5, -6.2, C('#445'), 1); GB.glassShop.quad([7.5, 0.4, -7.55], [11.4, 0.4, -7.55], [11.4, 2.3, -7.55], [7.5, 2.3, -7.55], [0, 0, 1], 1, 1, C('#fff'));
  GB.wood.box(7.8, 0.45, -7.4, 11.1, 0.52, -7.0, C('#8a6a4a'), 1);
  markRect(7.3, -7.8, 11.6, -7.4, SOLID);

  // ---- сборка сеток ----
  MT.asphalt.map.repeat.set(1, 1);
  const meshes = {
    siding: GB.siding.mesh(MT.siding), wall: GB.wall.mesh(MT.wall), roof: GB.roof.mesh(MT.shingle), plain: GB.plain.mesh(MT.plain),
    brick: GB.brick.mesh(MT.brick), floor: GB.floor.mesh(MT.floor, false), ceil: GB.ceil.mesh(MT.ceil, false), concrete: GB.concrete.mesh(MT.concrete),
    win: GB.win.mesh(MT.winDark, false), winL: GB.winL.mesh(MT.winLit, false), wood: GB.wood.mesh(MT.dwood), fabric: GB.fabric.mesh(MT.fabric),
    paint: GB.paint.mesh(MT.paint), metal: GB.metal.mesh(MT.metal), glassShop: GB.glassShop.mesh(MT.shopGlass = new THREE.MeshStandardMaterial({ color: 0x9ab0c0, roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.28, depthWrite: false, side: THREE.DoubleSide }), false),
    fridge: GB.fridgeGlow.mesh(MT.fridgeGlow = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.6, 1.9, 2.2) }), false),
    fluor: GB.fluor.mesh(MT.fluor, false), glassCar: GB.glassCar.mesh(MT.glass), asphalt: GB.asphalt.mesh(MT.asphalt, false),
    dwood: GB.dwood.mesh(MT.dwood), puddle: GB.puddle.mesh(new THREE.MeshStandardMaterial({ color: 0x1c2228, map: TX.pool, roughness: 0.04, metalness: 0.5, transparent: true, opacity: 1, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3 }), false),
    mark: GB.mark.mesh(new THREE.MeshStandardMaterial({ color: 0x1e1812, roughness: 1, transparent: true, opacity: 0.45, polygonOffset: true, polygonOffsetFactor: -2 }), false),
  };
  Town.meshes = meshes;
  Town.keeper = makeKeeper(); Town.keeper.position.set(Town.shop.keeperPos.x, 0, Town.shop.keeperPos.z); Town.keeper.rotation.y = 0;
  // границы карты
  markRect(-112, -86, 112, -84.5, SOLID | OPAQUE); markRect(-112, 84.5, 112, 86, SOLID | OPAQUE);
  markRect(-112, -86, -110.5, 86, SOLID | OPAQUE); markRect(110.5, -86, 112, 86, SOLID | OPAQUE);
  buildNav();
}

// ---------------------------------------------------------------------
//  Фонари: столбы инстансами, лампы светятся, ближайшие дают настоящий свет
// ---------------------------------------------------------------------
function buildLamps(spots) {
  const n = spots.length, dummy = new THREE.Object3D();
  const pole = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.09, 0.14, 5.8, 8).translate(0, 2.9, 0), MT.bark, n);
  const arm = new THREE.InstancedMesh(new THREE.BoxGeometry(0.1, 0.1, 1.4).translate(0, 0, 0.7), MT.bark, n);
  const head = new THREE.InstancedMesh(new THREE.BoxGeometry(0.42, 0.12, 0.26), MT.lampOn, n);
  const pool = new THREE.InstancedMesh(new THREE.PlaneGeometry(13, 13).rotateX(-Math.PI / 2), MT.pool, n);
  spots.forEach((s, i) => {
    const rot = Math.atan2(s.dx, s.dz);
    dummy.rotation.set(0, rot, 0); dummy.scale.set(1, 1, 1);
    dummy.position.set(s.x, 0, s.z); dummy.updateMatrix(); pole.setMatrixAt(i, dummy.matrix);
    dummy.position.set(s.x, 5.5, s.z); dummy.updateMatrix(); arm.setMatrixAt(i, dummy.matrix);
    const hx = s.x + s.dx * 1.35, hz = s.z + s.dz * 1.35;
    dummy.position.set(hx, 5.45, hz); dummy.updateMatrix(); head.setMatrixAt(i, dummy.matrix);
    dummy.position.set(hx, 0.12, hz); dummy.rotation.set(0, 0, 0); dummy.updateMatrix(); pool.setMatrixAt(i, dummy.matrix);
    markRect(s.x - 0.15, s.z - 0.15, s.x + 0.15, s.z + 0.15, SOLID);
    Town.lamps.push({ i, x: hx, z: hz, broken: RNG() < 0.12, on: false, level: 0, flickT: 0, flicker: RNG() < 0.15, dying: 0 });
  });
  head.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
  pool.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
  pole.castShadow = arm.castShadow = true;
  for (const m of [pole, arm, head, pool]) scene.add(m);
  pool.frustumCulled = false; head.frustumCulled = false;
  Town.lampMeshes = { head, pool };
}
