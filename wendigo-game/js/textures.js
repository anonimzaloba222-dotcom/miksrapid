'use strict';
// =====================================================================
//  Процедурные текстуры и материалы
// =====================================================================
THREE.ColorManagement.legacyMode = false;
let TEXS = 1, maxAniso = 4;
const TX = {}, TXN = {}, MT = {};
function mkTex(w, h, draw, srgb = true, scale = TEXS) {
  const c = document.createElement('canvas'); c.width = w * scale; c.height = h * scale;
  const g = c.getContext('2d', { willReadFrequently: true }); g.scale(scale, scale); draw(g, w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  if (srgb) t.encoding = THREE.sRGBEncoding;
  t.anisotropy = Math.min(8, maxAniso);
  return t;
}
function addNoise(g, w, h, amt) {
  const im = g.getImageData(0, 0, g.canvas.width, g.canvas.height), d = im.data;
  for (let i = 0; i < d.length; i += 4) {
    const n = (Math.random() - 0.5) * amt;
    d[i] = clamp(d[i] + n, 0, 255); d[i + 1] = clamp(d[i + 1] + n, 0, 255); d[i + 2] = clamp(d[i + 2] + n, 0, 255);
  }
  g.putImageData(im, 0, 0);
}
function blotches(g, w, h, n, rgb, amin, amax, rmin, rmax) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * w, y = Math.random() * h, r = rand(rmin, rmax), a = rand(amin, amax);
    for (const [ox, oy] of [[0, 0], [w, 0], [-w, 0], [0, h], [0, -h]]) {
      const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
      gr.addColorStop(0, `rgba(${rgb},${a})`); gr.addColorStop(1, `rgba(${rgb},0)`);
      g.fillStyle = gr; g.fillRect(x + ox - r, y + oy - r, 2 * r, 2 * r);
    }
  }
}
function cracks(g, w, h, n, col) {
  g.strokeStyle = col;
  for (let i = 0; i < n; i++) {
    let x = Math.random() * w, y = Math.random() * h, a = rand(0, 6.3);
    g.lineWidth = rand(0.6, 1.6); g.beginPath(); g.moveTo(x, y);
    for (let k = 0; k < 16; k++) { a += rand(-0.7, 0.7); x += Math.cos(a) * 8; y += Math.sin(a) * 8; g.lineTo(x, y); }
    g.stroke();
  }
}
function grainLines(g, x, y, w, len, r, gg, b, vertical, count) {
  for (let k = 0; k < count; k++) {
    g.strokeStyle = `rgba(${r * 0.45 | 0},${gg * 0.4 | 0},${b * 0.35 | 0},${rand(0.1, 0.35)})`;
    g.lineWidth = rand(0.6, 2); g.beginPath();
    const off = rand(2, w - 2), ph = rand(0, 6), amp = rand(1, 3);
    for (let t = 0; t <= len; t += 10) {
      const px = vertical ? x + off + Math.sin(t * 0.015 + ph) * amp : x + t;
      const py = vertical ? y + t : y + off + Math.sin(t * 0.015 + ph) * amp;
      t === 0 ? g.moveTo(px, py) : g.lineTo(px, py);
    }
    g.stroke();
  }
}
function normalTex(src, strength) {
  const w = src.width, h = src.height, sd = src.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, w, h).data;
  const L = new Float32Array(w * h);
  for (let i = 0; i < w * h; i++) L[i] = (sd[i * 4] * 0.3 + sd[i * 4 + 1] * 0.59 + sd[i * 4 + 2] * 0.11) / 255;
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'), out = g.createImageData(w, h), o = out.data;
  for (let y = 0; y < h; y++) {
    const yu = ((y - 1 + h) % h) * w, yd = ((y + 1) % h) * w, yr = y * w;
    for (let x = 0; x < w; x++) {
      const xl = (x - 1 + w) % w, xr = (x + 1) % w;
      const dx = (L[yr + xr] - L[yr + xl]) * strength, dy = (L[yd + x] - L[yu + x]) * strength;
      const l = Math.hypot(dx, dy, 1), k = (yr + x) * 4;
      o[k] = (-dx / l * 0.5 + 0.5) * 255; o[k + 1] = (dy / l * 0.5 + 0.5) * 255; o[k + 2] = (1 / l * 0.5 + 0.5) * 255; o[k + 3] = 255;
    }
  }
  g.putImageData(out, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = Math.min(8, maxAniso);
  return t;
}

function buildTextures() {
  // асфальт (1 текстура = 4 м)
  TX.asphalt = mkTex(512, 512, (g, w, h) => {
    g.fillStyle = '#2b2b2c'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 4000; i++) { const v = rand(25, 70) | 0; g.fillStyle = `rgb(${v},${v},${v + 2})`; g.fillRect(rand(0, w), rand(0, h), rand(1, 3), rand(1, 3)); }
    blotches(g, w, h, 10, '15,15,15', 0.3, 0.6, 20, 80);
    blotches(g, w, h, 6, '70,70,68', 0.1, 0.25, 30, 90);
    g.fillStyle = 'rgba(20,20,20,0.6)'; g.fillRect(rand(50, 300), rand(50, 300), rand(60, 140), rand(40, 100)); // заплатка
    cracks(g, w, h, 12, 'rgba(8,8,8,0.8)');
    addNoise(g, w, h, 26);
  });
  // тротуарная плитка (1 = 2 м)
  TX.concrete = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#6e6c66'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      const v = rand(95, 125) | 0; g.fillStyle = `rgb(${v},${v - 2},${v - 6})`; g.fillRect(i * 64 + 2, j * 64 + 2, 60, 60);
    }
    blotches(g, w, h, 8, '40,38,30', 0.2, 0.4, 10, 40); cracks(g, w, h, 5, 'rgba(30,30,30,0.7)');
    addNoise(g, w, h, 22);
  });
  // трава с инеем (1 = 6 м)
  TX.grass = mkTex(512, 512, (g, w, h) => {
    g.fillStyle = '#3b4a2b'; g.fillRect(0, 0, w, h);
    blotches(g, w, h, 30, '70,80,45', 0.2, 0.45, 20, 80);
    blotches(g, w, h, 20, '40,35,22', 0.2, 0.4, 20, 60);
    for (let i = 0; i < 9000; i++) {
      const x = rand(0, w), y = rand(0, h), l = rand(3, 9), v = rand(0.6, 1.2);
      g.strokeStyle = Math.random() < 0.15 ? `rgba(200,205,210,${rand(0.15, 0.4)})` : `rgba(${60 * v | 0},${85 * v | 0},${40 * v | 0},0.7)`;
      g.lineWidth = 1; g.beginPath(); g.moveTo(x, y); g.lineTo(x + rand(-2, 2), y - l); g.stroke();
    }
    blotches(g, w, h, 12, '190,195,200', 0.08, 0.2, 15, 50);
    addNoise(g, w, h, 18);
  });
  // обшивка домов (нейтральная — цвет задаётся вершинами)
  TX.siding = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#d8d8d4'; g.fillRect(0, 0, w, h);
    for (let y = 0; y < h; y += 32) {
      const gr = g.createLinearGradient(0, y, 0, y + 32); gr.addColorStop(0, '#f0f0ec'); gr.addColorStop(0.85, '#c8c8c2'); gr.addColorStop(1, '#6a6a66');
      g.fillStyle = gr; g.fillRect(0, y, w, 32);
      grainLines(g, 0, y, 30, w, 200, 200, 196, false, 4);
    }
    blotches(g, w, h, 10, '60,55,45', 0.15, 0.35, 10, 50);
    for (let i = 0; i < 6; i++) { const x = rand(0, w); const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(50,40,30,0)'); gr.addColorStop(1, 'rgba(50,40,30,0.35)'); g.fillStyle = gr; g.fillRect(x, 0, rand(3, 10), h); }
    addNoise(g, w, h, 18);
  });
  TX.shingle = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#5a5a5a'; g.fillRect(0, 0, w, h);
    for (let r = 0; r < 8; r++) for (let c = -1; c < 9; c++) {
      const v = rand(140, 210) | 0, x = c * 32 + (r % 2 ? 16 : 0);
      g.fillStyle = `rgb(${v},${v},${v})`; g.fillRect(x + 1, r * 32 + 1, 30, 30);
      g.fillStyle = 'rgba(0,0,0,0.45)'; g.fillRect(x, r * 32 + 28, 32, 4);
    }
    blotches(g, w, h, 12, '40,50,30', 0.2, 0.45, 10, 40);
    addNoise(g, w, h, 20);
  });
  TX.brick = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#6b6158'; g.fillRect(0, 0, w, h);
    for (let r = 0; r < 16; r++) for (let c = -1; c < 5; c++) {
      const x = c * 64 + (r % 2 ? 32 : 0), v = rand(0.75, 1.1);
      g.fillStyle = `rgb(${125 * v | 0},${58 * v | 0},${42 * v | 0})`; g.fillRect(x + 2, r * 16 + 2, 60, 12);
    }
    blotches(g, w, h, 10, '20,15,10', 0.2, 0.4, 10, 40); addNoise(g, w, h, 22);
  });
  TX.bark = mkTex(128, 256, (g, w, h) => {
    g.fillStyle = '#3d2c20'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 40; i++) { g.strokeStyle = `rgba(${rand(10, 30) | 0},${rand(8, 20) | 0},5,0.7)`; g.lineWidth = rand(1, 4); const x = rand(0, w); g.beginPath(); g.moveTo(x, 0); for (let y = 0; y < h; y += 16) g.lineTo(x + rand(-4, 4), y); g.stroke(); }
    addNoise(g, w, h, 30);
  });
  TX.pine = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#1c2a1c'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 5000; i++) { const x = rand(0, w), y = rand(0, h), v = rand(0.5, 1.3); g.strokeStyle = `rgba(${30 * v | 0},${60 * v | 0},${34 * v | 0},0.8)`; g.lineWidth = 1; g.beginPath(); g.moveTo(x, y); g.lineTo(x + rand(-5, 5), y + rand(2, 7)); g.stroke(); }
    blotches(g, w, h, 10, '200,205,210', 0.1, 0.25, 8, 24);
    addNoise(g, w, h, 20);
  });
  // интерьер
  TX.wall = mkTex(256, 512, (g, w, h) => {
    g.fillStyle = '#7a735c'; g.fillRect(0, 0, w, h);
    for (let x = 0; x < w; x += 48) { g.fillStyle = 'rgba(40,35,20,0.3)'; g.fillRect(x, 0, 3, h); }
    g.fillStyle = 'rgba(50,45,28,0.35)';
    for (let r = 0; r < 12; r++) for (let c = 0; c < 6; c++) { g.beginPath(); g.ellipse(c * 48 + (r % 2 ? 24 : 0), r * 44 + 22, 6, 12, 0, 0, 7); g.fill(); }
    blotches(g, w, h, 10, '70,50,20', 0.15, 0.4, 20, 70);
    addNoise(g, w, h, 22);
    const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, 'rgba(0,0,0,0.5)'); gr.addColorStop(0.08, 'rgba(0,0,0,0)'); gr.addColorStop(0.8, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(15,8,0,0.6)');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
  });
  TX.wood = mkTex(512, 512, (g, w, h) => {
    g.fillStyle = '#1c1209'; g.fillRect(0, 0, w, h);
    const n = 5, pw = w / n;
    for (let i = 0; i < n; i++) {
      let y = -rand(0, h);
      while (y < h) {
        const len = rand(h * 0.45, h * 1.1), r = rand(70, 105), gg = r * 0.66, b = r * 0.42;
        for (const oy of [0, h, -h]) { g.fillStyle = `rgb(${r | 0},${gg | 0},${b | 0})`; g.fillRect(i * pw + 1.5, y + oy + 1.5, pw - 3, len - 3); grainLines(g, i * pw, y + oy, pw, len, r, gg, b, true, 14); }
        y += len;
      }
    }
    blotches(g, w, h, 8, '12,6,2', 0.25, 0.5, 20, 70); addNoise(g, w, h, 16);
  });
  TX.dwood = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#3a2516'; g.fillRect(0, 0, w, h); grainLines(g, 0, 0, h, w, 90, 58, 36, false, 40);
    blotches(g, w, h, 6, '10,5,2', 0.2, 0.4, 15, 50); addNoise(g, w, h, 14);
  });
  TX.door = mkTex(256, 512, (g, w, h) => {
    g.fillStyle = '#4b301b'; g.fillRect(0, 0, w, h); grainLines(g, 0, 0, w, h, 100, 66, 40, true, 30);
    for (const [x, y, pw, ph] of [[30, 30, 84, 190], [142, 30, 84, 190], [30, 260, 84, 220], [142, 260, 84, 220]]) {
      g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(x, y, pw, ph); g.fillStyle = 'rgba(255,220,180,0.08)'; g.fillRect(x + 6, y + 6, pw - 12, ph - 12);
    }
    blotches(g, w, h, 5, '10,5,2', 0.3, 0.5, 15, 40); addNoise(g, w, h, 16);
  });
  TX.ceil = mkTex(256, 256, (g, w, h) => { g.fillStyle = '#8a857a'; g.fillRect(0, 0, w, h); blotches(g, w, h, 10, '95,70,30', 0.2, 0.4, 15, 70); cracks(g, w, h, 5, 'rgba(30,25,20,0.6)'); addNoise(g, w, h, 20); });
  TX.fabric = mkTex(128, 128, (g, w, h) => {
    g.fillStyle = '#8a8070'; g.fillRect(0, 0, w, h); g.strokeStyle = 'rgba(0,0,0,0.1)';
    for (let i = 0; i < w; i += 3) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, h); g.stroke(); g.beginPath(); g.moveTo(0, i); g.lineTo(w, i); g.stroke(); }
    blotches(g, w, h, 6, '40,30,15', 0.2, 0.4, 8, 30); addNoise(g, w, h, 26);
  });
  // окно: тёмное стекло с рамой; светящаяся версия — тёплый свет за шторой
  const windowTex = lit => mkTex(128, 160, (g, w, h) => {
    if (lit) { const gr = g.createRadialGradient(w / 2, h / 2, 5, w / 2, h / 2, 90); gr.addColorStop(0, '#ffd89a'); gr.addColorStop(1, '#a8642a'); g.fillStyle = gr; }
    else { const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#1c2430'); gr.addColorStop(0.5, '#0a0d12'); gr.addColorStop(1, '#161c24'); g.fillStyle = gr; }
    g.fillRect(0, 0, w, h);
    if (lit) { g.fillStyle = 'rgba(120,50,20,0.55)'; g.fillRect(8, 8, 30, h - 16); g.fillRect(w - 38, 8, 30, h - 16); }
    else { g.fillStyle = 'rgba(200,210,230,0.08)'; g.beginPath(); g.moveTo(20, 10); g.lineTo(60, 10); g.lineTo(20, 90); g.fill(); }
    g.fillStyle = '#e4e0d6'; g.fillRect(0, 0, w, 8); g.fillRect(0, h - 8, w, 8); g.fillRect(0, 0, 8, h); g.fillRect(w - 8, 0, 8, h); g.fillRect(w / 2 - 4, 0, 8, h); g.fillRect(0, h / 2 - 4, w, 8);
    addNoise(g, w, h, 14);
  }, true, 1);
  TX.winDark = windowTex(false); TX.winLit = windowTex(true);
  // вывеска магазина
  TX.sign = mkTex(512, 96, (g, w, h) => {
    g.fillStyle = '#120808'; g.fillRect(0, 0, w, h);
    g.font = 'bold 56px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.shadowColor = '#ff3020'; g.shadowBlur = 18; g.fillStyle = '#ff6a50'; g.fillText('ПРОДУКТЫ', w / 2, h / 2 + 3);
  }, true, 1);
  // кожа вендиго с рёбрами, кость черепа
  TX.skin = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#6b6258'; g.fillRect(0, 0, w, h);
    for (let y = 30; y < 200; y += 18) { const gr = g.createLinearGradient(0, y, 0, y + 18); gr.addColorStop(0, 'rgba(0,0,0,0.5)'); gr.addColorStop(0.5, 'rgba(255,240,220,0.18)'); gr.addColorStop(1, 'rgba(0,0,0,0.4)'); g.fillStyle = gr; g.fillRect(0, y, w, 18); }
    blotches(g, w, h, 20, '30,20,18', 0.2, 0.45, 8, 35); blotches(g, w, h, 8, '90,30,25', 0.2, 0.4, 6, 20);
    g.strokeStyle = 'rgba(40,30,50,0.4)'; for (let i = 0; i < 30; i++) { let x = rand(0, w), y = rand(0, h); g.beginPath(); g.moveTo(x, y); for (let k = 0; k < 6; k++) { x += rand(-8, 8); y += rand(-8, 8); g.lineTo(x, y); } g.stroke(); }
    addNoise(g, w, h, 26);
  });
  TX.bone = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#d8ceb4'; g.fillRect(0, 0, w, h);
    blotches(g, w, h, 18, '120,100,70', 0.2, 0.45, 8, 40); blotches(g, w, h, 6, '70,20,15', 0.25, 0.5, 5, 18);
    cracks(g, w, h, 14, 'rgba(60,45,30,0.7)'); addNoise(g, w, h, 20);
  });
  TX.cookie = mkTex(256, 256, (g, w, h) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, w, h);
    const gr = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
    gr.addColorStop(0, '#fff'); gr.addColorStop(0.14, '#fbf6ea'); gr.addColorStop(0.2, '#a9a397'); gr.addColorStop(0.26, '#d8d1c2');
    gr.addColorStop(0.31, '#8a857b'); gr.addColorStop(0.45, '#6a665e'); gr.addColorStop(0.75, '#2c2a27'); gr.addColorStop(1, '#000');
    g.fillStyle = gr; g.fillRect(0, 0, w, h); blotches(g, w, h, 14, '0,0,0', 0.1, 0.25, 4, 14);
  }, true, 1);
  TX.cookie.wrapS = TX.cookie.wrapT = THREE.ClampToEdgeWrapping;
  TX.dot = mkTex(32, 32, (g) => { const gr = g.createRadialGradient(16, 16, 0, 16, 16, 16); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 32, 32); }, true, 1);
  TX.pool = mkTex(128, 128, (g) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,0.9)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); }, true, 1);
  TX.pool.wrapS = TX.pool.wrapT = THREE.ClampToEdgeWrapping;

  TXN.asphalt = normalTex(TX.asphalt.image, 3); TXN.concrete = normalTex(TX.concrete.image, 4);
  TXN.grass = normalTex(TX.grass.image, 3); TXN.siding = normalTex(TX.siding.image, 4);
  TXN.shingle = normalTex(TX.shingle.image, 5); TXN.brick = normalTex(TX.brick.image, 5);
  TXN.bark = normalTex(TX.bark.image, 4); TXN.wall = normalTex(TX.wall.image, 2.5);
  TXN.wood = normalTex(TX.wood.image, 4); TXN.door = normalTex(TX.door.image, 5);
  TXN.skin = normalTex(TX.skin.image, 5); TXN.bone = normalTex(TX.bone.image, 4); TXN.fabric = normalTex(TX.fabric.image, 4);
}

function buildMaterials() {
  const STD = o => new THREE.MeshStandardMaterial(o), nv = s => new THREE.Vector2(s, s);
  MT.asphalt = STD({ map: TX.asphalt, normalMap: TXN.asphalt, normalScale: nv(0.8), roughness: 0.85 });
  MT.concrete = STD({ map: TX.concrete, normalMap: TXN.concrete, normalScale: nv(0.8), roughness: 0.9 });
  MT.grass = STD({ map: TX.grass, normalMap: TXN.grass, normalScale: nv(0.7), roughness: 1 });
  MT.siding = STD({ map: TX.siding, normalMap: TXN.siding, normalScale: nv(1), roughness: 0.8, vertexColors: true });
  MT.shingle = STD({ map: TX.shingle, normalMap: TXN.shingle, normalScale: nv(1), roughness: 0.9, vertexColors: true });
  MT.brick = STD({ map: TX.brick, normalMap: TXN.brick, normalScale: nv(1), roughness: 0.9 });
  MT.bark = STD({ map: TX.bark, normalMap: TXN.bark, normalScale: nv(1), roughness: 1 });
  MT.pine = STD({ map: TX.pine, roughness: 1, vertexColors: true });
  MT.wall = STD({ map: TX.wall, normalMap: TXN.wall, normalScale: nv(0.8), roughness: 0.93 });
  MT.floor = STD({ map: TX.wood, normalMap: TXN.wood, normalScale: nv(0.9), roughness: 0.45 });
  MT.ceil = STD({ map: TX.ceil, roughness: 1 });
  MT.dwood = STD({ map: TX.dwood, roughness: 0.55, vertexColors: true });
  MT.door = STD({ map: TX.door, normalMap: TXN.door, normalScale: nv(1), roughness: 0.55 });
  MT.fabric = STD({ map: TX.fabric, normalMap: TXN.fabric, normalScale: nv(0.7), roughness: 1, vertexColors: true });
  MT.paint = STD({ roughness: 0.45, metalness: 0.4, vertexColors: true });
  MT.plain = STD({ roughness: 0.8, vertexColors: true });
  MT.metal = STD({ color: 0x55585a, roughness: 0.45, metalness: 0.85 });
  MT.glass = STD({ color: 0x0b0f14, roughness: 0.05, metalness: 0.6 });
  MT.doorGlass = STD({ color: 0x8aa0b0, roughness: 0.05, metalness: 0.3, transparent: true, opacity: 0.35 });
  MT.winDark = STD({ map: TX.winDark, roughness: 0.15, metalness: 0.3 });
  MT.winLit = STD({ map: TX.winLit, emissiveMap: TX.winLit, emissive: 0xffffff, emissiveIntensity: 0, roughness: 0.3 });
  MT.sign = new THREE.MeshBasicMaterial({ map: TX.sign, color: new THREE.Color(2.2, 2.2, 2.2) });
  MT.lampOn = new THREE.MeshBasicMaterial({ color: 0xffffff });
  MT.pool = new THREE.MeshBasicMaterial({ map: TX.pool, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: 0xffffff, polygonOffset: true, polygonOffsetFactor: -4 });
  MT.skin = STD({ map: TX.skin, normalMap: TXN.skin, normalScale: nv(1.2), roughness: 0.75 });
  MT.bone = STD({ map: TX.bone, normalMap: TXN.bone, normalScale: nv(1), roughness: 0.6 });
  MT.claw = STD({ color: 0x1a1612, roughness: 0.35 });
  MT.eye = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 5, 2.2), fog: false });
  MT.hit = new THREE.MeshBasicMaterial({ visible: false });
  MT.flame = new THREE.MeshBasicMaterial({ color: new THREE.Color(6, 2.6, 0.7) });
  MT.fluor = new THREE.MeshBasicMaterial({ color: new THREE.Color(3, 3.2, 3.4) });
}
