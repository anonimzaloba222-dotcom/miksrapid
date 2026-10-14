'use strict';
// =====================================================================
//  Общие утилиты, генератор случайных чисел, сетка столкновений
// =====================================================================
const $ = id => document.getElementById(id);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const lerp = (a, b, t) => a + (b - a) * t;
const rand = (a, b) => a + Math.random() * (b - a);
const pick = a => a[Math.random() * a.length | 0];
const angWrap = a => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };
const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

// детерминированный генератор: у хоста и гостей одинаковый город
function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
let RNG = mulberry32(1);
const srand = (a, b) => a + RNG() * (b - a);
const spick = a => a[RNG() * a.length | 0];
function sshuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = RNG() * (i + 1) | 0; [a[i], a[j]] = [a[j], a[i]]; } return a; }

// ---------------------------------------------------------------------
//  Сетка 0.5 м: 1 — нельзя пройти, 2 — не видно сквозь, 4 — дверь
// ---------------------------------------------------------------------
const WORLD = { minX: -112, maxX: 112, minZ: -86, maxZ: 86, cs: 0.5 };
WORLD.gw = Math.round((WORLD.maxX - WORLD.minX) / WORLD.cs);
WORLD.gh = Math.round((WORLD.maxZ - WORLD.minZ) / WORLD.cs);
const COL = new Uint8Array(WORLD.gw * WORLD.gh);
const SOLID = 1, OPAQUE = 2, DOORF = 4;
const gxOf = x => Math.floor((x - WORLD.minX) / WORLD.cs);
const gzOf = z => Math.floor((z - WORLD.minZ) / WORLD.cs);
function markRect(x0, z0, x1, z1, flags) {
  if (x0 > x1) [x0, x1] = [x1, x0]; if (z0 > z1) [z0, z1] = [z1, z0];
  const a = clamp(gxOf(x0 + 0.001), 0, WORLD.gw - 1), b = clamp(gxOf(x1 - 0.001), 0, WORLD.gw - 1);
  const c = clamp(gzOf(z0 + 0.001), 0, WORLD.gh - 1), d = clamp(gzOf(z1 - 0.001), 0, WORLD.gh - 1);
  const cells = [];
  for (let j = c; j <= d; j++) for (let i = a; i <= b; i++) { COL[j * WORLD.gw + i] |= flags; cells.push(j * WORLD.gw + i); }
  return cells;
}
function colAt(x, z) {
  const i = gxOf(x), j = gzOf(z);
  if (i < 0 || j < 0 || i >= WORLD.gw || j >= WORLD.gh) return SOLID | OPAQUE;
  return COL[j * WORLD.gw + i];
}
function circleFree(x, z, r) {
  const a = gxOf(x - r), b = gxOf(x + r), c = gzOf(z - r), d = gzOf(z + r);
  for (let j = c; j <= d; j++) for (let i = a; i <= b; i++) {
    if (i < 0 || j < 0 || i >= WORLD.gw || j >= WORLD.gh) return false;
    if (COL[j * WORLD.gw + i] & SOLID) return false;
  }
  return true;
}
// видно ли от точки к точке (стены, деревья, закрытые двери)
function sightClear(x1, z1, x2, z2) {
  const dx = x2 - x1, dz = z2 - z1, d = Math.hypot(dx, dz), n = Math.ceil(d / 0.35);
  for (let k = 1; k < n; k++) if (colAt(x1 + dx * k / n, z1 + dz * k / n) & OPAQUE) return false;
  return true;
}
// движение кругом с скольжением вдоль стен
function moveCircle(e, dx, dz, r) {
  const steps = Math.max(1, Math.ceil(Math.hypot(dx, dz) / 0.15));
  const sx = dx / steps, sz = dz / steps;
  let moved = false;
  for (let k = 0; k < steps; k++) {
    if (circleFree(e.x + sx, e.z + sz, r)) { e.x += sx; e.z += sz; moved = true; }
    else if (circleFree(e.x + sx, e.z, r)) { e.x += sx; moved = true; }
    else if (circleFree(e.x, e.z + sz, r)) { e.z += sz; moved = true; }
  }
  return moved;
}

// ---------------------------------------------------------------------
//  Навигация вендиго: клетки 1 м, поиск в ширину
// ---------------------------------------------------------------------
const NAV = { w: Math.round((WORLD.maxX - WORLD.minX)), h: Math.round((WORLD.maxZ - WORLD.minZ)), block: null, avoid: null };
function buildNav() {
  NAV.block = new Uint8Array(NAV.w * NAV.h); NAV.avoid = new Uint8Array(NAV.w * NAV.h);
  for (let j = 0; j < NAV.h; j++) for (let i = 0; i < NAV.w; i++) {
    let b = 0;
    for (let dj = 0; dj < 2; dj++) for (let di = 0; di < 2; di++) {
      const c = COL[(j * 2 + dj) * WORLD.gw + i * 2 + di];
      if ((c & SOLID) && !(c & DOORF)) b = 1;
    }
    NAV.block[j * NAV.w + i] = b;
  }
}
const navIdx = (x, z) => clamp(Math.floor(z - WORLD.minZ), 0, NAV.h - 1) * NAV.w + clamp(Math.floor(x - WORLD.minX), 0, NAV.w - 1);
const navX = i => (i % NAV.w) + WORLD.minX + 0.5, navZ = i => Math.floor(i / NAV.w) + WORLD.minZ + 0.5;
let _prev = null, _queue = null;
function navPath(fx, fz, tx, tz, ignoreAvoid) {
  const N = NAV.w * NAV.h; if (!_prev) { _prev = new Int32Array(N); _queue = new Int32Array(N); }
  const s = navIdx(fx, fz); let t = navIdx(tx, tz);
  if (NAV.block[t]) { // цель в стене — ищем соседнюю свободную клетку
    let best = -1;
    for (let r = 1; r < 4 && best < 0; r++) for (let dj = -r; dj <= r; dj++) for (let di = -r; di <= r; di++) {
      const k = t + dj * NAV.w + di; if (k >= 0 && k < N && !NAV.block[k]) { best = k; break; }
    }
    if (best < 0) return []; t = best;
  }
  _prev.fill(-1); _prev[s] = s; let h = 0, q = 0; _queue[q++] = s;
  const W = NAV.w;
  while (h < q) {
    const c = _queue[h++]; if (c === t) break;
    const cx = c % W;
    const ns = [cx > 0 ? c - 1 : -1, cx < W - 1 ? c + 1 : -1, c - W, c + W];
    for (const n of ns) {
      if (n < 0 || n >= N || _prev[n] !== -1 || NAV.block[n]) continue;
      if (!ignoreAvoid && NAV.avoid[n] && n !== t) continue;
      _prev[n] = c; _queue[q++] = n;
    }
  }
  if (_prev[t] === -1) return [];
  const path = []; for (let c = t; c !== s; c = _prev[c]) path.push(c);
  return path.reverse();
}
