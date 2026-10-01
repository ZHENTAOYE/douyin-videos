// 渲染引擎：画布、字体、调色板、缓动、通用图形组件（档案卡、印章、神经元、字幕……）
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
    SerifL: 'SourceHanSerifSC-Light.otf',
    SansH: 'SourceHanSansSC-Heavy.otf', SansB: 'SourceHanSansSC-Bold.otf',
    SansM: 'SourceHanSansSC-Medium.otf', SansR: 'SourceHanSansSC-Regular.otf',
    SansL: 'SourceHanSansSC-Light.otf',
  };
  for (const [alias, f] of Object.entries(files)) {
    const p = path.join(sc, f);
    if (!fs.existsSync(p)) throw new Error('missing font ' + p + ' (run src/fetch_assets.sh)');
    GlobalFonts.registerFromPath(p, alias);
  }
  GlobalFonts.registerFromPath(path.join(FONT_DIR, 'LXGWWenKai-Regular.ttf'), 'Kai');
}

// ---------------------------------------------------------------- palette
const P = {
  bg: [11, 12, 16], bg2: [22, 20, 17],
  paper: [241, 233, 216], amber: [255, 181, 71], amberDeep: [214, 120, 38],
  red: [226, 62, 66], ice: [150, 196, 238], iceDeep: [84, 132, 176],
  ink: [34, 30, 25], card: [236, 227, 207], cardEdge: [201, 187, 156],
  grey: [128, 126, 118], gold: [222, 178, 92], green: [126, 206, 150],
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
// in over [a, a+fi], out over [b-fo, b]
const fade = (t, a, b, fi = 0.35, fo = 0.35) => Math.min(ramp(t, a, a + fi), 1 - ramp(t, b - fo, b));
const ap = (t, t0, d = 0.5) => eo(ramp(t, t0, t0 + d));

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
// time at which character `n` (0-based, of the plain text) is roughly spoken
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
// draw text with manual letter spacing (centered by default)
function spaced(ctx, s, x, y, font, color, sp, align = 'center') {
  ctx.font = font; ctx.fillStyle = color; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  const chars = [...s];
  const widths = chars.map((c) => ctx.measureText(c).width);
  const total = widths.reduce((a, b) => a + b, 0) + sp * (chars.length - 1);
  let cx = align === 'center' ? x - total / 2 : align === 'right' ? x - total : x;
  chars.forEach((c, i) => { ctx.fillText(c, cx, y); cx += widths[i] + sp; });
  return total;
}
// wrap text to width; returns lines
function wrap(ctx, s, maxW, font) {
  ctx.font = font;
  const lines = []; let cur = '';
  for (const ch of [...s]) {
    if (ch === '\n') { lines.push(cur); cur = ''; continue; }
    if (ctx.measureText(cur + ch).width > maxW && cur) {
      // keep closing punctuation on the line
      if ('，。、：；！？）》”'.includes(ch)) { cur += ch; lines.push(cur); cur = ''; continue; }
      lines.push(cur); cur = ch;
    } else cur += ch;
  }
  if (cur) lines.push(cur);
  return lines;
}
function para(ctx, s, x, y, maxW, font, color, lh, align = 'left') {
  const lines = wrap(ctx, s, maxW, font);
  ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'alphabetic';
  lines.forEach((l, i) => ctx.fillText(l, x, y + i * lh));
  return lines.length;
}

function glow(ctx, x, y, r, c, a = 1) {
  if (a <= 0.002 || r <= 0) return;
  const g = ctx.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, rgba(c, a)); g.addColorStop(0.35, rgba(c, a * 0.35)); g.addColorStop(1, rgba(c, 0));
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
// partial line from p0 to p (0..1)
function lineP(ctx, x1, y1, x2, y2, p, c, a = 1, lw = 2) {
  if (p <= 0) return; line(ctx, x1, y1, x1 + (x2 - x1) * p, y1 + (y2 - y1) * p, c, a, lw);
}
function arrow(ctx, x1, y1, x2, y2, c, a = 1, lw = 4, head = 18) {
  line(ctx, x1, y1, x2, y2, c, a, lw);
  const ang = Math.atan2(y2 - y1, x2 - x1);
  ctx.fillStyle = rgba(c, a); ctx.beginPath();
  ctx.moveTo(x2 + Math.cos(ang) * 4, y2 + Math.sin(ang) * 4);
  ctx.lineTo(x2 - Math.cos(ang - 0.45) * head, y2 - Math.sin(ang - 0.45) * head);
  ctx.lineTo(x2 - Math.cos(ang + 0.45) * head, y2 - Math.sin(ang + 0.45) * head);
  ctx.closePath(); ctx.fill();
}
// glowing neuron: level 0..1 (0 = dormant outline, 1 = firing)
function neuron(ctx, x, y, r, level, c = P.amber, alpha = 1, core = true) {
  const off = mix(P.grey, P.paper, 0.15);
  if (level > 0.02) glow(ctx, x, y, r * (2.6 + level * 1.6), c, 0.55 * level * alpha);
  dot(ctx, x, y, r, mix(P.bg, c, 0.18 + 0.5 * level), alpha);
  ctx.strokeStyle = rgba(mix(off, c, level), alpha * (0.55 + 0.45 * level)); ctx.lineWidth = Math.max(2, r * 0.12);
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.stroke();
  if (core && level > 0.02) dot(ctx, x, y, r * 0.45 * level, mix(c, [255, 255, 255], 0.35), alpha * level);
}
function pulse(ctx, x1, y1, x2, y2, p, c = P.amber, a = 1, r = 9) {
  if (p < 0 || p > 1) return;
  const x = lerp(x1, x2, p), y = lerp(y1, y2, p);
  glow(ctx, x, y, r * 3.2, c, 0.7 * a); dot(ctx, x, y, r * 0.55, mix(c, [255, 255, 255], 0.5), a);
}

// paper grain pattern (static)
let _grain = null;
function grainPattern(ctx) {
  if (!_grain) {
    _grain = createCanvas(256, 256);
    const g = _grain.getContext('2d'); const r = rng(7);
    for (let i = 0; i < 2600; i++) {
      g.fillStyle = `rgba(80,60,30,${0.02 + r() * 0.06})`;
      g.fillRect(r() * 256, r() * 256, 1 + r() * 2, 1 + r() * 2);
    }
    for (let i = 0; i < 40; i++) {
      g.strokeStyle = `rgba(120,90,50,${0.03 + r() * 0.03})`; g.lineWidth = 1;
      g.beginPath(); const x = r() * 256, y = r() * 256; g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 60, y + (r() - 0.5) * 8); g.stroke();
    }
  }
  return ctx.createPattern(_grain, 'repeat');
}
function paperRect(ctx, x, y, w, h, r = 8, col = P.card, shadow = true) {
  if (shadow) { ctx.fillStyle = 'rgba(0,0,0,0.5)'; roundRect(ctx, x + 8, y + 14, w, h, r); ctx.fill(); }
  ctx.fillStyle = rgba(col); roundRect(ctx, x, y, w, h, r); ctx.fill();
  ctx.save(); roundRect(ctx, x, y, w, h, r); ctx.clip();
  ctx.fillStyle = grainPattern(ctx); ctx.fillRect(x, y, w, h);
  const g = ctx.createLinearGradient(x, y, x, y + h); g.addColorStop(0, 'rgba(255,255,255,0.08)'); g.addColorStop(1, 'rgba(90,60,20,0.10)');
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
  ctx.restore();
}

// ---------------------------------------------------------------- archive card (档案卡)
// o: { no, zh, en, role, note, w, h }
function cardImage(o) {
  const w = o.w || 760, h = o.h || 380;
  return cached('card:' + JSON.stringify(o), w + 30, h + 40, (g) => {
    paperRect(g, 6, 6, w, h, 10);
    const ink = rgba(P.ink), inkDim = rgba(P.ink, 0.55);
    // header
    g.font = '24px SansM'; g.fillStyle = inkDim; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillText(`档案  No.${String(o.no).padStart(2, '0')}`, 40, 52);
    if (w >= 600) { g.textAlign = 'right'; g.font = '20px SansR'; g.fillText('NEURAL NETWORK · ARCHIVE', w - 28, 52); }
    line(g, 36, 70, w - 24, 70, P.ink, 0.35, 2);
    // tab marker
    g.fillStyle = rgba(P.amberDeep, 0.9); g.fillRect(w - 22, 90, 16, 64);
    let y = 70 + (o.compact ? 70 : 90);
    const zhSize = o.zhSize || (o.compact ? 52 : 64);
    g.textAlign = 'left'; g.font = `${zhSize}px SerifH`; g.fillStyle = ink;
    g.fillText(o.zh, 40, y);
    y += o.compact ? 42 : 50;
    if (o.en) { g.font = `${o.compact ? 24 : 28}px SansR`; g.fillStyle = inkDim; g.fillText(o.en, 42, y); y += o.compact ? 44 : 54; }
    if (o.role) { g.font = `${o.compact ? 26 : 30}px SansB`; g.fillStyle = rgba(P.amberDeep); g.fillText(o.role, 42, y); y += o.compact ? 46 : 56; }
    if (o.note) {
      g.font = `${o.compact ? 28 : 32}px Kai`; g.fillStyle = rgba(P.ink, 0.78);
      const lines = wrap(g, o.note, w - 90, g.font);
      lines.forEach((l, i) => g.fillText(l, 44, y + i * (o.compact ? 38 : 42)));
    }
    // paperclip
    g.strokeStyle = 'rgba(150,150,150,0.9)'; g.lineWidth = 4; g.lineCap = 'round';
    const px = w >= 600 ? Math.round(w * 0.56) : w - 80; g.beginPath(); g.moveTo(px, 2); g.lineTo(px, 34); g.arc(px + 10, 34, 10, Math.PI, 0, true); g.lineTo(px + 20, -6); g.stroke();
  });
}
// draw card centered at (x,y); k = appear progress; rot in radians
function card(ctx, o, x, y, k = 1, rot = 0, scale = 1) {
  if (k <= 0) return;
  const img = cardImage(o);
  const e = eo(k);
  ctx.save();
  ctx.globalAlpha *= clamp(k * 2.5);
  ctx.translate(x, y + (1 - e) * 70); ctx.rotate(rot + (1 - e) * 0.06); ctx.scale(scale, scale);
  ctx.drawImage(img, -img.width / 2, -img.height / 2);
  ctx.restore();
}

// ---------------------------------------------------------------- stamp (印章)
function stampImage(txt, size, col, sub) {
  return cached(`stamp:${txt}:${size}:${col}:${sub}`, size * (txt.length * 1.0 + 1.2) + 40, size * 2.4, (g, w, h) => {
    g.translate(w / 2, h / 2);
    g.font = `${size}px SerifH`;
    const tw = g.measureText(txt).width;
    const bw = tw + size * 0.8, bh = size * 1.55;
    g.strokeStyle = rgba(col); g.lineWidth = size * 0.085; g.strokeRect(-bw / 2, -bh / 2, bw, bh);
    g.lineWidth = size * 0.03; g.strokeRect(-bw / 2 + size * 0.13, -bh / 2 + size * 0.13, bw - size * 0.26, bh - size * 0.26);
    g.fillStyle = rgba(col); g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(txt, 0, size * 0.05);
    if (sub) { g.font = `${size * 0.26}px SansB`; g.fillStyle = rgba(P.bg); const sw = g.measureText(sub).width + size * 0.3;
      g.fillStyle = rgba(col); g.fillRect(-sw / 2, -bh / 2 - size * 0.18, sw, size * 0.36);
      g.fillStyle = 'rgba(15,12,10,1)'; g.fillText(sub, 0, -bh / 2); }
    // wear: punch random holes
    g.globalCompositeOperation = 'destination-out';
    const r = rng(txt.length * 31 + size);
    for (let i = 0; i < 520; i++) { g.fillStyle = `rgba(0,0,0,${0.3 + r() * 0.7})`; g.beginPath(); g.arc((r() - 0.5) * w, (r() - 0.5) * h, r() * size * 0.035 + 0.5, 0, TAU); g.fill(); }
    g.globalCompositeOperation = 'source-over';
  });
}
function stamp(ctx, txt, x, y, size, since, rot = -0.16, col = P.red, sub = '') {
  if (since < 0) return;
  const img = stampImage(txt, size, col, sub);
  const k = clamp(since / 0.13);
  const s = lerp(2.3, 1, eo(k)) * (1 + 0.04 * Math.exp(-since * 9) * Math.sin(since * 60));
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot); ctx.scale(s, s);
  ctx.globalAlpha *= clamp(since / 0.06) * 0.95;
  ctx.drawImage(img, -img.width / 2, -img.height / 2);
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
  W, H, TAU, ROOT, BUILD, P, rgba, mix, clamp, lerp, ramp, eo, ei, eio, eback, smooth, fade, ap, rng, hash,
  TL, SEG, S, E, K, CH, charT, roundRect, cached, text, spaced, wrap, para, glow, dot, ring, line, lineP, arrow,
  neuron, pulse, paperRect, grainPattern, card, cardImage, stamp, runs, registerFonts, createCanvas,
};
