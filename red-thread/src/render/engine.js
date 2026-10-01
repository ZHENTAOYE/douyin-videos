// 渲染引擎：画布、字体、调色板、缓动、通用图形（红线、印章、气泡、纸张……）
'use strict';
const fs = require('fs');
const path = require('path');
const { createCanvas, GlobalFonts } = require('@napi-rs/canvas');

const W = 1080, H = 1920, TAU = Math.PI * 2;
const ROOT = path.join(__dirname, '..', '..');
const BUILD = path.join(ROOT, 'build');
const FONT_DIR = process.env.FONT_DIR || path.join(ROOT, 'assets', 'fonts');

// ---------------------------------------------------------------- fonts
function registerFonts() {
  const sc = path.join(FONT_DIR, 'OTF', 'SimplifiedChinese');
  const files = {
    SerifH: 'SourceHanSerifSC-Heavy.otf', SerifB: 'SourceHanSerifSC-Bold.otf',
    SerifM: 'SourceHanSerifSC-Medium.otf', SerifR: 'SourceHanSerifSC-Regular.otf',
    SansH: 'SourceHanSansSC-Heavy.otf', SansB: 'SourceHanSansSC-Bold.otf',
    SansM: 'SourceHanSansSC-Medium.otf', SansR: 'SourceHanSansSC-Regular.otf',
  };
  for (const [alias, f] of Object.entries(files)) {
    const p = path.join(sc, f);
    if (!fs.existsSync(p)) throw new Error('missing font ' + p + ' (run src/fetch_assets.sh)');
    GlobalFonts.registerFromPath(p, alias);
  }
  GlobalFonts.registerFromPath(path.join(FONT_DIR, 'LXGWWenKai-Regular.ttf'), 'Kai');
}

// ---------------------------------------------------------------- palette (宣纸 · 墨 · 朱砂)
const P = {
  paper: [240, 230, 210], paperLo: [226, 210, 180], paperHi: [248, 242, 228],
  ink: [44, 37, 33], inkSoft: [104, 92, 82], inkFaint: [160, 146, 128],
  red: [198, 46, 40], redDeep: [146, 28, 26], redSoft: [226, 120, 110],
  gold: [182, 134, 52], goldHi: [222, 182, 96],
  skin: [250, 226, 204], blush: [240, 150, 140], white: [255, 252, 245],
  moon: [252, 244, 220], sky: [58, 70, 98], tear: [110, 160, 210], green: [70, 140, 92],
};
const rgba = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`;
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

// ---------------------------------------------------------------- math / easing
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, t) => a + (b - a) * t;
const ramp = (t, a, b) => clamp((t - a) / (b - a));
const eo = (t) => 1 - Math.pow(1 - clamp(t), 3);
const ei = (t) => Math.pow(clamp(t), 3);
const eio = (t) => { t = clamp(t); return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
const eback = (t) => { t = clamp(t); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); };
const smooth = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
const fade = (t, a, b, fi = 0.35, fo = 0.35) => Math.min(ramp(t, a, a + fi), 1 - ramp(t, b - fo, b));
const ap = (t, t0, d = 0.5) => eo(ramp(t, t0, t0 + d));
const pop = (t, t0, d = 0.45) => eback(ramp(t, t0, t0 + d));

function rng(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const hash = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };

// ---------------------------------------------------------------- timeline
const TL = JSON.parse(fs.readFileSync(path.join(BUILD, 'timeline.json'), 'utf8'));
const SEG = Object.fromEntries(TL.segments.map((s) => [s.id, s]));
const S = (id) => SEG[id].t0;
const E = (id) => SEG[id].t1;
const K = (id, i = 0) => (SEG[id].keywords[i] || { t: SEG[id].t0 }).t;
const CH = (id, i = 0) => { const c = SEG[id].chunks; return c[Math.min(i, c.length - 1)].t0; };
// time at which `needle` is roughly spoken inside line `id`
function charT(id, needle) {
  const s = SEG[id];
  for (const c of s.chunks) {
    const body = c.text.replace(/[【】]/g, '');
    const k = body.indexOf(needle);
    if (k >= 0) return c.t0 + (k / Math.max(1, body.length)) * (c.t1 - c.t0);
  }
  if (!charT.warned) charT.warned = new Set();
  if (!charT.warned.has(id + needle)) { charT.warned.add(id + needle); console.error(`charT: "${needle}" not found in ${id}`); }
  return s.t0;
}

// ---------------------------------------------------------------- canvas helpers
function roundRect(ctx, x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
}
const _cache = new Map();
function cached(key, w, h, draw) {
  let c = _cache.get(key);
  if (!c) { c = createCanvas(Math.ceil(w), Math.ceil(h)); draw(c.getContext('2d'), w, h); _cache.set(key, c); }
  return c;
}
function text(ctx, s, x, y, font, color, align = 'center', baseline = 'alphabetic') {
  ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = baseline;
  ctx.fillText(s, x, y);
}
function spaced(ctx, s, x, y, font, color, sp, align = 'center') {
  ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  const chars = [...s];
  const widths = chars.map((c) => ctx.measureText(c).width);
  const total = widths.reduce((a, b) => a + b, 0) + sp * (chars.length - 1);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  chars.forEach((c, i) => { ctx.fillText(c, cx, y); cx += widths[i] + sp; });
  return total;
}
function glow(ctx, x, y, r, c, a = 1) {
  if (a <= 0.002 || r <= 0) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(c, a)); g.addColorStop(0.4, rgba(c, a * 0.35)); g.addColorStop(1, rgba(c, 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
}
function dot(ctx, x, y, r, c, a = 1) { ctx.fillStyle = rgba(c, a); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill(); }
function ring(ctx, x, y, r, c, a = 1, lw = 2) { ctx.strokeStyle = rgba(c, a); ctx.lineWidth = lw; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke(); }
function line(ctx, x1, y1, x2, y2, c, a = 1, lw = 2, dash) {
  ctx.strokeStyle = rgba(c, a); ctx.lineWidth = lw; ctx.lineCap = 'round';
  if (dash) ctx.setLineDash(dash);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  if (dash) ctx.setLineDash([]);
}
function arrow(ctx, x1, y1, x2, y2, c, a = 1, lw = 4, head = 16) {
  line(ctx, x1, y1, x2, y2, c, a, lw);
  const ang = Math.atan2(y2 - y1, x2 - x1);
  ctx.fillStyle = rgba(c, a); ctx.beginPath();
  ctx.moveTo(x2 + Math.cos(ang) * 4, y2 + Math.sin(ang) * 4);
  ctx.lineTo(x2 - Math.cos(ang - 0.45) * head, y2 - Math.sin(ang - 0.45) * head);
  ctx.lineTo(x2 - Math.cos(ang + 0.45) * head, y2 - Math.sin(ang + 0.45) * head);
  ctx.closePath(); ctx.fill();
}
function withAlpha(ctx, a, fn) { if (a <= 0.003) return; ctx.save(); ctx.globalAlpha *= a; fn(); ctx.restore(); }
function withXform(ctx, x, y, s, rot, fn) { ctx.save(); ctx.translate(x, y); ctx.rotate(rot || 0); ctx.scale(s, s); fn(); ctx.restore(); }

// ---------------------------------------------------------------- paper texture
let _fiber = null;
function fiberPattern(ctx) {
  if (!_fiber) {
    _fiber = createCanvas(384, 384);
    const g = _fiber.getContext('2d'); const r = rng(1962);
    for (let i = 0; i < 3200; i++) {
      g.fillStyle = `rgba(120,95,60,${0.015 + r() * 0.04})`;
      g.fillRect(r() * 384, r() * 384, 1 + r() * 2, 1 + r() * 2);
    }
    // long soft fibres (宣纸纤维)
    for (let i = 0; i < 110; i++) {
      g.strokeStyle = `rgba(140,110,70,${0.025 + r() * 0.035})`; g.lineWidth = 0.6 + r();
      const x = r() * 384, y = r() * 384, a = r() * TAU, l = 20 + r() * 70;
      g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a + 0.5) * l * 0.5, y + Math.sin(a + 0.5) * l * 0.5, x + Math.cos(a) * l, y + Math.sin(a) * l); g.stroke();
    }
  }
  return ctx.createPattern(_fiber, 'repeat');
}
function paperRect(ctx, x, y, w, h, r = 10, col = P.paperHi, shadow = true) {
  if (shadow) { ctx.fillStyle = 'rgba(70,50,30,0.18)'; roundRect(ctx, x + 6, y + 10, w, h, r); ctx.fill(); }
  ctx.fillStyle = rgba(col); roundRect(ctx, x, y, w, h, r); ctx.fill();
  ctx.save(); roundRect(ctx, x, y, w, h, r); ctx.clip();
  ctx.fillStyle = fiberPattern(ctx); ctx.fillRect(x, y, w, h);
  ctx.restore();
}

// ---------------------------------------------------------------- red thread (红线)
// quadratic curve that sags a little, like a real thread
function threadCtrl(x1, y1, x2, y2, sag) {
  const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
  const d = Math.hypot(x2 - x1, y2 - y1);
  return [mx, my + (sag == null ? Math.min(70, d * 0.12) : sag)];
}
function qpt(x1, y1, cx, cy, x2, y2, u) {
  const a = (1 - u) * (1 - u), b = 2 * u * (1 - u), c = u * u;
  return [a * x1 + b * cx + c * x2, a * y1 + b * cy + c * y2];
}
// o: { p (0..1 drawn), dash, a, lw, sag, col, wob (wiggle amplitude), t }
function thread(ctx, x1, y1, x2, y2, o = {}) {
  const p = o.p == null ? 1 : o.p;
  if (p <= 0.001) return;
  const [cx, cy] = threadCtrl(x1, y1, x2, y2, o.sag);
  const col = o.col || P.red, a = o.a == null ? 1 : o.a, lw = o.lw || 5;
  const n = 48, wob = o.wob || 0, t = o.t || 0;
  ctx.save();
  ctx.strokeStyle = rgba(col, a); ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  if (o.dash) ctx.setLineDash(o.dash);
  ctx.beginPath();
  for (let i = 0; i <= n * p; i++) {
    const u = Math.min(p, i / n);
    let [x, y] = qpt(x1, y1, cx, cy, x2, y2, u);
    if (wob) y += Math.sin(u * Math.PI) * Math.sin(t * 6 + u * 9) * wob;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.restore();
  // a soft highlight on solid threads
  if (!o.dash && lw >= 4) {
    ctx.save(); ctx.strokeStyle = `rgba(255,220,200,${0.35 * a})`; ctx.lineWidth = lw * 0.3; ctx.beginPath();
    for (let i = 0; i <= n * p; i++) { const u = Math.min(p, i / n); const [x, y] = qpt(x1, y1, cx, cy, x2, y2, u); if (i === 0) ctx.moveTo(x, y - lw * 0.18); else ctx.lineTo(x, y - lw * 0.18); }
    ctx.stroke(); ctx.restore();
  }
  // the moving tip while drawing
  if (p < 1) { const [x, y] = qpt(x1, y1, cx, cy, x2, y2, p); glow(ctx, x, y, 22, P.red, 0.5 * a); dot(ctx, x, y, lw * 0.9, P.red, a); }
}
function threadMid(x1, y1, x2, y2, sag, u = 0.5) {
  const [cx, cy] = threadCtrl(x1, y1, x2, y2, sag);
  return qpt(x1, y1, cx, cy, x2, y2, u);
}
// a thread snapping in the middle: k 0..1 after the snap
function threadSnap(ctx, x1, y1, x2, y2, k, o = {}) {
  if (k >= 1) return;
  const a = (o.a == null ? 1 : o.a) * (1 - smooth(ramp(k, 0.45, 1)));
  const [cx, cy] = threadCtrl(x1, y1, x2, y2, o.sag);
  const n = 24, lw = o.lw || 5;
  const draw = (from, to, side) => {
    ctx.save(); ctx.strokeStyle = rgba(o.col || P.red, a); ctx.lineWidth = lw; ctx.lineCap = 'round';
    if (o.dash) ctx.setLineDash(o.dash);
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const u = lerp(from, to, i / n);
      let [x, y] = qpt(x1, y1, cx, cy, x2, y2, u);
      const d = side === 0 ? (u / 0.5) : ((1 - u) / 0.5);      // 0 at anchor → 1 at the cut
      const retract = eo(k) * 0.55;
      const ax = side === 0 ? x1 : x2, ay = side === 0 ? y1 : y2;
      x = lerp(x, ax, retract * d); y = lerp(y, ay, retract * d) + eo(k) * 90 * d * d;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke(); ctx.restore();
  };
  draw(0, 0.47, 0); draw(1, 0.53, 1);
  // spark at the cut
  if (k < 0.35) {
    const [mx, my] = qpt(x1, y1, cx, cy, x2, y2, 0.5);
    for (let i = 0; i < 7; i++) {
      const ang = i / 7 * TAU + 0.4, d = 10 + 46 * eo(k / 0.35);
      line(ctx, mx + Math.cos(ang) * d * 0.5, my + Math.sin(ang) * d * 0.5, mx + Math.cos(ang) * d, my + Math.sin(ang) * d, P.red, (1 - k / 0.35) * 0.9, 3);
    }
  }
}

// ---------------------------------------------------------------- stamp (印章)
function stampImage(txt, size, col, sub) {
  return cached(`stamp:${txt}:${size}:${col}:${sub}`, size * (txt.length * 1.0 + 1.2) + 40, size * 2.4, (g, w, h) => {
    g.translate(w / 2, h / 2);
    g.font = `${size}px SerifH`;
    const tw = g.measureText(txt).width;
    const bw = tw + size * 0.7, bh = size * 1.45;
    g.strokeStyle = rgba(col); g.lineWidth = size * 0.09; roundRect(g, -bw / 2, -bh / 2, bw, bh, size * 0.12); g.stroke();
    g.fillStyle = rgba(col); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, 0, size * 0.05);
    if (sub) { g.font = `${size * 0.26}px SansB`; const sw = g.measureText(sub).width + size * 0.3;
      g.fillRect(-sw / 2, -bh / 2 - size * 0.18, sw, size * 0.36);
      g.fillStyle = rgba(P.paperHi); g.fillText(sub, 0, -bh / 2); }
    g.globalCompositeOperation = 'destination-out';
    const r = rng(txt.length * 31 + size);
    for (let i = 0; i < 420; i++) { g.fillStyle = `rgba(0,0,0,${0.25 + r() * 0.6})`; g.beginPath(); g.arc((r() - 0.5) * w, (r() - 0.5) * h, r() * size * 0.03 + 0.5, 0, TAU); g.fill(); }
    g.globalCompositeOperation = 'source-over';
  });
}
function stamp(ctx, txt, x, y, size, since, rot = -0.16, col = P.red, sub = '') {
  if (since < 0) return;
  const img = stampImage(txt, size, col, sub);
  const k = clamp(since / 0.13);
  const s = lerp(2.2, 1, eo(k)) * (1 + 0.04 * Math.exp(-since * 9) * Math.sin(since * 60));
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  ctx.globalAlpha *= clamp(since / 0.06) * 0.92;
  ctx.drawImage(img, -img.width / 2, -img.height / 2);
  ctx.restore();
}
// filled square seal with one character (名章)
function seal(ctx, ch, x, y, size, col, rot = 0, a = 1) {
  if (a <= 0.003) return;
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.globalAlpha *= a;
  ctx.fillStyle = rgba(col); roundRect(ctx, -size / 2, -size / 2, size, size, size * 0.16); ctx.fill();
  ctx.strokeStyle = rgba(P.white, 0.75); ctx.lineWidth = Math.max(1.5, size * 0.04);
  roundRect(ctx, -size / 2 + size * 0.09, -size / 2 + size * 0.09, size * 0.82, size * 0.82, size * 0.1); ctx.stroke();
  text(ctx, ch, 0, size * 0.04, `${Math.round(size * 0.62)}px SerifH`, rgba(P.white), 'center', 'middle');
  ctx.restore();
}

// ---------------------------------------------------------------- heart
function heartPath(ctx, x, y, s) {
  ctx.beginPath(); ctx.moveTo(x, y + s * 0.35);
  ctx.bezierCurveTo(x - s * 1.0, y - s * 0.25, x - s * 0.55, y - s * 0.95, x, y - s * 0.45);
  ctx.bezierCurveTo(x + s * 0.55, y - s * 0.95, x + s * 1.0, y - s * 0.25, x, y + s * 0.35);
  ctx.closePath();
}
function heart(ctx, x, y, s, c = P.red, a = 1) {
  if (a <= 0.003 || s <= 0) return;
  ctx.save(); ctx.globalAlpha *= a; heartPath(ctx, x, y, s); ctx.fillStyle = rgba(c); ctx.fill(); ctx.restore();
}
// speech bubble with content drawn by fn(ctx) centred at the bubble
function bubble(ctx, x, y, w, h, k, tailDx = 0, fn) {
  if (k <= 0.003) return;
  const s = eback(k);
  ctx.save(); ctx.translate(x, y + h / 2 + 14); ctx.scale(s, s); ctx.translate(0, -h / 2 - 14);
  ctx.globalAlpha *= clamp(k * 3);
  ctx.fillStyle = 'rgba(70,50,30,0.14)'; roundRect(ctx, -w / 2 + 3, -h / 2 + 5, w, h, h / 2); ctx.fill();
  ctx.fillStyle = rgba(P.white); roundRect(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(tailDx - 10, h / 2 - 2); ctx.lineTo(tailDx + 4, h / 2 + 16); ctx.lineTo(tailDx + 12, h / 2 - 2); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = rgba(P.ink, 0.25); ctx.lineWidth = 2; roundRect(ctx, -w / 2, -h / 2, w, h, h / 2); ctx.stroke();
  if (fn) fn(ctx);
  ctx.restore();
}

// ---------------------------------------------------------------- rich text (【高亮】)
function runs(s) {
  const out = []; const re = /【(.+?)】/g; let last = 0, m;
  while ((m = re.exec(s))) { if (m.index > last) out.push({ t: s.slice(last, m.index), hl: false }); out.push({ t: m[1], hl: true }); last = m.index + m[0].length; }
  if (last < s.length) out.push({ t: s.slice(last), hl: false });
  return out;
}

module.exports = {
  W, H, TAU, ROOT, BUILD, P, rgba, mix, clamp, lerp, ramp, eo, ei, eio, eback, smooth, fade, ap, pop, rng, hash,
  TL, SEG, S, E, K, CH, charT, roundRect, cached, text, spaced, glow, dot, ring, line, arrow, withAlpha, withXform,
  fiberPattern, paperRect, thread, threadMid, threadSnap, stamp, seal, heart, heartPath, bubble, runs, registerFonts, createCanvas,
};
