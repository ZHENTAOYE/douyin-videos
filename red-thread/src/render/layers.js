// 全局图层：宣纸底、月亮、水墨远山、洒金、祥云、字幕、暗角
'use strict';
const E_ = require('./engine');
const { W, H, TAU, P, rgba, mix, clamp, lerp, ramp, eo, smooth, fade, rng, TL, glow, dot, line, runs, cached, fiberPattern } = E_;

function sceneAt(t) {
  const sc = TL.scenes; let i = 0;
  while (i + 1 < sc.length && t >= sc[i + 1].t0) i++;
  return i;
}

// ---------------------------------------------------------------- background
// night amount: the legend / paper chapter dims the paper into dusk
const NIGHT = { night: 1, title: 0.35, tender: 0.45 };
function nightAt(t) {
  const sc = TL.scenes, i = sceneAt(t);
  const cur = NIGHT[sc[i].mood] || 0, prev = i > 0 ? (NIGHT[sc[i - 1].mood] || 0) : cur;
  return lerp(prev, cur, smooth(ramp(t, sc[i].t0 - 0.2, sc[i].t0 + 1.4)));
}

const FLECKS = (() => { const r = rng(2012); return Array.from({ length: 70 }, () => ({ x: r() * W, y: r() * H, s: 1.5 + r() * 4, a: r(), rot: r() * TAU, ph: r() * TAU })); })();

function mountains() {
  return cached('mountains', W, 520, (g, w, h) => {
    const r = rng(7);
    const layers = [[0.10, 210, 0.9], [0.16, 300, 0.7], [0.24, 390, 0.5]];
    for (const [a, base, amp] of layers) {
      const grd = g.createLinearGradient(0, base - 160, 0, h);
      grd.addColorStop(0, `rgba(60,58,62,${a})`); grd.addColorStop(1, `rgba(60,58,62,${a * 0.2})`);
      g.fillStyle = grd; g.beginPath(); g.moveTo(0, h);
      let y = base;
      for (let x = 0; x <= w; x += 12) {
        y = base - amp * (70 * Math.sin(x / 170 + base) + 40 * Math.sin(x / 63 + base * 2) + 18 * Math.sin(x / 23)) - r() * 4;
        g.lineTo(x, y);
      }
      g.lineTo(w, h); g.closePath(); g.fill();
    }
  });
}

function paperBase() {
  return cached('paperBase', W, H, (g) => {
    const gr = g.createRadialGradient(W / 2, H * 0.42, 100, W / 2, H * 0.45, H * 0.8);
    gr.addColorStop(0, rgba(P.paperHi)); gr.addColorStop(0.6, rgba(P.paper)); gr.addColorStop(1, rgba(P.paperLo));
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
    g.fillStyle = fiberPattern(g); g.fillRect(0, 0, W, H);
  });
}
function nightBase() {
  return cached('nightBase', W, H, (g) => {
    const gr = g.createLinearGradient(0, 0, 0, H);
    gr.addColorStop(0, 'rgb(34,38,58)'); gr.addColorStop(0.55, 'rgb(58,56,78)'); gr.addColorStop(1, 'rgb(96,80,86)');
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
    g.globalAlpha = 0.5; g.fillStyle = fiberPattern(g); g.fillRect(0, 0, W, H); g.globalAlpha = 1;
    const r = rng(99);
    for (let i = 0; i < 160; i++) { g.fillStyle = `rgba(255,248,225,${0.2 + r() * 0.6})`; g.beginPath(); g.arc(r() * W, r() * H * 0.7, 0.6 + r() * 1.8, 0, TAU); g.fill(); }
  });
}

function drawBackground(ctx, t) {
  ctx.drawImage(paperBase(), 0, 0);
  const n = nightAt(t);
  if (n > 0.003) { ctx.save(); ctx.globalAlpha = n; ctx.drawImage(nightBase(), 0, 0); ctx.restore(); }
  // moon (top right) — pale on paper, glowing at night
  const mx = 860, my = 250 + Math.sin(t * 0.2) * 4;
  glow(ctx, mx, my, 220, n > 0.5 ? P.moon : P.goldHi, 0.18 + 0.3 * n);
  E_.dot(ctx, mx, my, 74, mix([246, 236, 212], P.moon, n), 1);
  ctx.save(); ctx.globalAlpha = 0.18 * (1 - n * 0.5);
  for (const [x, y, r] of [[-20, -18, 14], [22, 10, 10], [-6, 26, 7], [28, -26, 6]]) E_.dot(ctx, mx + x, my + y, r, [200, 180, 140]);
  ctx.restore();
  E_.ring(ctx, mx, my, 74, P.ink, 0.12 * (1 - n), 2);
  // drifting clouds (祥云)
  ctx.save();
  for (let i = 0; i < 3; i++) {
    const x = ((t * (6 + i * 3) + i * 420) % (W + 400)) - 200, y = 170 + i * 120;
    cloud(ctx, x, y, 0.9 + i * 0.2, mix(P.paperLo, [200, 200, 220], n), 0.32 + 0.1 * n);
  }
  ctx.restore();
  // ink mountains
  ctx.save(); ctx.globalAlpha = 0.9 - 0.3 * n; ctx.drawImage(mountains(), 0, H - 520); ctx.restore();
  // gold flecks (洒金)
  for (const f of FLECKS) {
    const tw = 0.5 + 0.5 * Math.sin(t * 0.8 + f.ph);
    ctx.save(); ctx.translate(f.x, f.y); ctx.rotate(f.rot);
    ctx.fillStyle = rgba(P.goldHi, (0.18 + 0.25 * f.a) * (0.6 + 0.4 * tw));
    ctx.fillRect(-f.s / 2, -f.s / 3, f.s, f.s * 0.66);
    ctx.restore();
  }
}
function cloud(ctx, x, y, s, col, a) {
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s);
  ctx.strokeStyle = rgba(col, a); ctx.lineWidth = 3; ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.arc(0, 0, 22, Math.PI, Math.PI * 2.2);
  ctx.moveTo(40, 4); ctx.arc(52, 0, 16, Math.PI * 1.1, Math.PI * 2.4);
  ctx.moveTo(-26, 4); ctx.quadraticCurveTo(10, 18, 80, 8);
  ctx.stroke();
  ctx.restore();
}

// ---------------------------------------------------------------- top banner (第几次 · 谁先开口 · 第几轮)
// o: { label, dir (1 men→women, -1 women→men), round (1-based, 0 = hide), total, a }
function banner(ctx, o) {
  const a = o.a == null ? 1 : o.a;
  if (a <= 0.003) return;
  ctx.save(); ctx.globalAlpha *= a;
  const y = 330;
  ctx.font = '40px SerifB';
  const lw = ctx.measureText(o.label).width + 120;
  ctx.fillStyle = rgba(P.paperHi, 0.92); E_.roundRect(ctx, W / 2 - lw / 2, y - 38, lw, 76, 38); ctx.fill();
  ctx.strokeStyle = rgba(P.red, 0.8); ctx.lineWidth = 3; ctx.stroke();
  E_.text(ctx, o.label, W / 2 + (o.dir > 0 ? -18 : 18), y + 14, '40px SerifB', rgba(P.ink));
  const ax = o.dir > 0 ? W / 2 + lw / 2 - 46 : W / 2 - lw / 2 + 46;
  E_.arrow(ctx, ax - 16 * o.dir, y, ax + 16 * o.dir, y, P.red, 1, 4, 13);
  if (o.round) {
    const ry = y + 70;
    const label = `第 ${o.round} 轮`;
    E_.text(ctx, label, W / 2 - 40, ry + 12, '32px SerifB', rgba(P.red));
    for (let i = 0; i < (o.total || 4); i++) E_.dot(ctx, W / 2 + 46 + i * 22, ry + 1, 6.5, i < o.round ? P.red : P.inkFaint, i < o.round ? 1 : 0.5);
  }
  ctx.restore();
}

// ---------------------------------------------------------------- subtitles
function subtitleChunk(t) {
  const all = [];
  for (const s of TL.segments) for (const c of s.chunks) all.push(c);
  for (let i = 0; i < all.length; i++) {
    const c = all[i], next = all[i + 1];
    const end = next ? Math.min(next.t0, c.t1 + 0.45) : c.t1 + 0.6;
    if (t >= c.t0 - 0.04 && t < end) return { c, end };
  }
  return null;
}
function cleanSub(s) {
  return s.replace(/[，。；：、]+$/g, '').replace(/[，；]/g, '  ').replace(/[“”]/g, (m) => (m === '“' ? '「' : '」'));
}
function drawSubtitle(ctx, t) {
  const hit = subtitleChunk(t);
  if (!hit) return;
  const { c, end } = hit;
  const k = eo(ramp(t, c.t0 - 0.04, c.t0 + 0.12));
  const a = k * (1 - ramp(t, end - 0.1, end));
  const rs = runs(cleanSub(c.text));
  let size = 58;
  const measure = (sz) => { ctx.font = `${sz}px SansB`; return rs.reduce((w, r) => w + ctx.measureText(r.t).width, 0); };
  while (measure(size) > 900 && size > 42) size -= 2;
  const tw = measure(size);
  const y = 1468 + (1 - k) * 10;
  ctx.save(); ctx.globalAlpha = a;
  // soft ink-wash band behind the line
  const bandW = tw + 150;
  const g = ctx.createLinearGradient(W / 2 - bandW / 2, 0, W / 2 + bandW / 2, 0);
  g.addColorStop(0, 'rgba(44,37,33,0)'); g.addColorStop(0.15, 'rgba(44,37,33,0.80)'); g.addColorStop(0.85, 'rgba(44,37,33,0.80)'); g.addColorStop(1, 'rgba(44,37,33,0)');
  ctx.fillStyle = g; ctx.fillRect(W / 2 - bandW / 2, y - size - 14, bandW, size + 40);
  ctx.font = `${size}px SansB`; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left';
  let x = W / 2 - tw / 2;
  for (const r of rs) {
    ctx.fillStyle = r.hl ? 'rgb(255,128,108)' : rgba(P.paperHi);
    ctx.fillText(r.t, x, y);
    x += ctx.measureText(r.t).width;
  }
  ctx.restore();
}

function drawVignette(ctx) {
  const v = cached('vignette', W, H, (c) => {
    const g = c.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.75);
    g.addColorStop(0, 'rgba(60,40,20,0)'); g.addColorStop(1, 'rgba(60,40,20,0.28)');
    c.fillStyle = g; c.fillRect(0, 0, W, H);
  });
  ctx.drawImage(v, 0, 0);
}

module.exports = { drawBackground, banner, drawSubtitle, drawVignette, sceneAt, nightAt, cloud };
