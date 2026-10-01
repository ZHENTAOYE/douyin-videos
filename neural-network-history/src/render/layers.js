// 全局图层：背景神经网络、顶部年代轴、雪、冷色调、年份卡、字幕、暗角
'use strict';
const E_ = require('./engine');
const { W, H, TAU, P, rgba, mix, clamp, lerp, ramp, eo, eio, smooth, fade, rng, hash, TL, S, E, K, glow, dot, line, runs, createCanvas, cached } = E_;

// ---------------------------------------------------------------- moods → background state
const MOODS = {
  mystery: { act: 0.95, warm: 1, energy: 1.0, alpha: 0.30 },
  title:   { act: 0.40, warm: 1, energy: 0.5, alpha: 0.45 },
  memory:  { act: 0.10, warm: 0.9, energy: 0.25, alpha: 0.38 },
  hope:    { act: 0.28, warm: 1, energy: 0.55, alpha: 0.38 },
  tension: { act: 0.22, warm: 0.55, energy: 0.3, alpha: 0.32 },
  winter:  { act: 0.05, warm: 0, energy: 0.04, alpha: 0.34 },
  thaw:    { act: 0.12, warm: 0.65, energy: 0.2, alpha: 0.34 },
  revival: { act: 0.38, warm: 1, energy: 0.55, alpha: 0.34 },
  tender:  { act: 0.10, warm: 0.75, energy: 0.12, alpha: 0.32 },
  build:   { act: 0.58, warm: 1, energy: 0.75, alpha: 0.32 },
  triumph: { act: 0.78, warm: 1, energy: 0.95, alpha: 0.32 },
  drive:   { act: 1.0, warm: 1, energy: 1.5, alpha: 0.40 },
  warm:    { act: 0.85, warm: 1, energy: 0.6, alpha: 0.32 },
  coda:    { act: 1.0, warm: 1, energy: 0.7, alpha: 0.40 },
};
function sceneAt(t) {
  const sc = TL.scenes; let i = 0;
  while (i + 1 < sc.length && t >= sc[i + 1].t0) i++;
  return i;
}
function bgState(t) {
  const sc = TL.scenes, i = sceneAt(t);
  const cur = MOODS[sc[i].mood];
  const prev = i > 0 ? MOODS[sc[i - 1].mood] : cur;
  const k = smooth(ramp(t, sc[i].t0, sc[i].t0 + 1.6));
  const o = {};
  for (const key of Object.keys(cur)) o[key] = lerp(prev[key], cur[key], k);
  return o;
}

// ---------------------------------------------------------------- background network
const BG = (() => {
  const r = rng(1943); const nodes = [];
  const cols = 7, rows = 13;
  for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
    nodes.push({ x: (i + 0.5 + (r() - 0.5) * 0.8) * (W / cols), y: (j + 0.5 + (r() - 0.5) * 0.8) * (H / rows),
      birth: r(), phase: r() * TAU, rate: 0.6 + r() * 1.6, size: 3 + r() * 4 });
  }
  // nodes near the centre are born later so early chapters keep the stage clean
  for (const n of nodes) { const d = Math.hypot(n.x - W / 2, n.y - 820) / 900; n.birth = clamp(n.birth * 0.7 + (1 - d) * 0.35); }
  const edges = [];
  nodes.forEach((a, ia) => {
    const near = nodes.map((b, ib) => [Math.hypot(a.x - b.x, a.y - b.y), ib]).filter((d) => d[1] !== ia).sort((p, q) => p[0] - q[0]).slice(0, 3);
    for (const [, ib] of near) if (ia < ib || !edges.some((e) => e.a === ib && e.b === ia)) edges.push({ a: ia, b: ib, ph: r(), sp: 0.25 + r() * 0.5, on: r() });
  });
  return { nodes, edges };
})();

function drawBackground(ctx, t, override) {
  // base
  const g = cached('bgGrad', W, H, (c) => {
    const gr = c.createRadialGradient(W / 2, H * 0.42, 50, W / 2, H * 0.45, H * 0.75);
    gr.addColorStop(0, rgba(P.bg2)); gr.addColorStop(1, rgba(P.bg));
    c.fillStyle = gr; c.fillRect(0, 0, W, H);
  });
  ctx.drawImage(g, 0, 0);
  const st = Object.assign(bgState(t), override || {});
  const col = mix(P.ice, P.amber, st.warm);
  const { nodes, edges } = BG;
  ctx.save(); ctx.globalAlpha = st.alpha;
  ctx.lineWidth = 1.5;
  for (const e of edges) {
    const a = nodes[e.a], b = nodes[e.b];
    const vis = clamp((st.act - Math.max(a.birth, b.birth)) * 6);
    if (vis <= 0) continue;
    ctx.strokeStyle = rgba(col, 0.22 * vis);
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    if (e.on < st.energy * 0.55) {
      const p = (t * e.sp * (0.6 + st.energy) + e.ph) % 1;
      const x = lerp(a.x, b.x, p), y = lerp(a.y, b.y, p);
      glow(ctx, x, y, 14, col, 0.55 * vis); dot(ctx, x, y, 2.2, col, 0.9 * vis);
    }
  }
  for (const n of nodes) {
    const vis = clamp((st.act - n.birth) * 6);
    if (vis <= 0) continue;
    const fire = Math.pow(Math.max(0, Math.sin(t * n.rate * (0.5 + st.energy) + n.phase)), 10) * clamp(st.energy * 1.5);
    glow(ctx, n.x, n.y, n.size * (4 + fire * 6), col, (0.25 + 0.6 * fire) * vis);
    dot(ctx, n.x, n.y, n.size * 0.6, mix(col, P.paper, 0.4), 0.8 * vis);
  }
  ctx.restore();
}

// ---------------------------------------------------------------- winter (snow + cold grade)
function winterAmount(t) {
  const a1 = ramp(t, K('C6') - 0.2, K('C6') + 1.2) * (1 - ramp(t, S('D2'), S('D4') - 1));
  const a2 = Math.max(0.45 * ramp(t, S('E2'), S('E2') + 2), ramp(t, K('E5') - 0.2, K('E5') + 1.2)) * (1 - ramp(t, K('E8') - 2.5, K('E8') + 1.0));
  // the three lights scene keeps lighter snow
  const lights = (t > S('E6') - 0.3 && t < K('E8')) ? 0.65 : 1;
  return clamp(Math.max(a1, a2 * (t > S('E6') - 0.3 ? lights : 1)));
}
// cold grade: strong on the background, gentle on top so red stamps stay red
function drawGrade(ctx, t, layer) {
  const w = winterAmount(t);
  if (w <= 0.01) return;
  ctx.save();
  if (layer === 'bg') {
    ctx.globalCompositeOperation = 'saturation'; ctx.globalAlpha = 0.8 * w; ctx.fillStyle = 'rgb(128,128,128)'; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 0.22 * w; ctx.fillStyle = rgba(P.iceDeep); ctx.fillRect(0, 0, W, H);
  } else {
    ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = 0.3 * w; ctx.fillStyle = rgba(P.iceDeep); ctx.fillRect(0, 0, W, H);
  }
  ctx.restore();
}
const FLAKES = (() => { const r = rng(1969); return Array.from({ length: 260 }, () => ({ x: r() * W, y: r() * H, s: 1 + r() * 3.6, v: 50 + r() * 110, ph: r() * TAU, sw: 10 + r() * 30, k: r() })); })();
function drawSnow(ctx, t) {
  const w = winterAmount(t);
  if (w <= 0.01) return;
  ctx.save();
  for (const f of FLAKES) {
    if (f.k > w) continue;
    const y = (f.y + t * f.v) % (H + 40) - 20;
    const x = (f.x + Math.sin(t * 0.7 + f.ph) * f.sw + t * 18) % (W + 40) - 20;
    dot(ctx, x, y, f.s, P.paper, (0.25 + 0.5 * (f.s / 4.6)) * clamp((w - f.k) * 4));
  }
  ctx.restore();
}

// ---------------------------------------------------------------- HUD year axis
const Y0 = 1943, Y1 = 2024;
let YEAR_KEYS = null;
function yearKeys() {
  if (!YEAR_KEYS) YEAR_KEYS = [
    [S('A1'), 1943], [S('B2'), 1958], [S('C1'), 1969], [S('C7'), 1971], [S('D2'), 1982], [S('D4'), 1986],
    [S('D8'), 1989], [S('E1'), 1995], [S('E7'), 2004], [S('E8'), 2006], [S('F1'), 2012],
    [S('G2'), 2016], [S('G3'), 2017], [S('G4'), 2018], [S('G5'), 2022], [S('I1'), 2024],
  ];
  return YEAR_KEYS;
}
function yearAt(t) {
  const ks = yearKeys();
  if (t <= ks[0][0]) return ks[0][1];
  for (let i = ks.length - 1; i >= 0; i--) {
    if (t >= ks[i][0]) {
      const prev = i > 0 ? ks[i - 1][1] : ks[i][1];
      const dur = Math.min(1.2, 0.35 + Math.abs(ks[i][1] - prev) * 0.05);
      return lerp(prev, ks[i][1], eio(ramp(t, ks[i][0], ks[i][0] + dur)));
    }
  }
  return ks[0][1];
}
const WINTERS = [[1969, 1982], [1995, 2006]];
function drawHUD(ctx, t) {
  const a = fade(t, S('A1') - 0.6, S('J1') - 0.2, 0.8, 0.8);
  if (a <= 0) return;
  const x0 = 110, x1 = 970, y = 330;
  const X = (yr) => lerp(x0, x1, (yr - Y0) / (Y1 - Y0));
  const yr = yearAt(t);
  ctx.save(); ctx.globalAlpha = a;
  line(ctx, x0, y, x1, y, P.paper, 0.22, 2);
  // winters
  for (const [w0, w1] of WINTERS) {
    if (yr < w0) continue;
    const xe = X(Math.min(yr, w1));
    ctx.fillStyle = rgba(P.ice, 0.55); ctx.fillRect(X(w0), y - 3, xe - X(w0), 6);
  }
  // progress
  line(ctx, x0, y, X(yr), y, P.amber, 0.9, 3);
  for (const d of [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]) line(ctx, X(d), y - 6, X(d), y + 6, P.paper, 0.3, 2);
  E_.text(ctx, '1943', x0, y + 40, '24px SansM', rgba(P.paper, 0.45), 'left');
  E_.text(ctx, '2024', x1, y + 40, '24px SansM', rgba(P.paper, 0.45), 'right');
  const mx = X(yr);
  glow(ctx, mx, y, 26, P.amber, 0.8); dot(ctx, mx, y, 7, P.paper, 1);
  E_.text(ctx, String(Math.round(yr)), clamp(mx, x0 + 40, x1 - 40), y - 22, '34px SerifB', rgba(P.paper, 0.95), 'center');
  ctx.restore();
}

// ---------------------------------------------------------------- year title card (章节年份)
function yearCard(ctx, t, t0, year, label, dur = 1.9) {
  const a = fade(t, t0, t0 + dur, 0.25, 0.45);
  if (a <= 0) return;
  const k = eo(ramp(t, t0, t0 + 0.7));
  ctx.save();
  const base = ctx.globalAlpha;
  ctx.globalAlpha = base * a * 0.78; ctx.fillStyle = rgba(P.bg); ctx.fillRect(0, 300, W, 1000);
  ctx.globalAlpha = base * a;
  const y = 820 + (1 - k) * 30;
  glow(ctx, W / 2, y - 80, 360, P.amber, 0.12 * a);
  ctx.save(); ctx.translate(W / 2, y); const s = lerp(1.1, 1, k); ctx.scale(s, s);
  E_.spaced(ctx, String(year), 0, 0, '230px SerifH', rgba(P.paper), 6);
  ctx.restore();
  ctx.font = '44px SansM'; const lw = ctx.measureText(label).width;
  E_.text(ctx, label, W / 2, y + 100, '44px SansM', rgba(P.amber), 'center');
  line(ctx, W / 2 - lw / 2 - 130, y + 85, W / 2 - lw / 2 - 30, y + 85, P.amber, 0.7 * k, 2);
  line(ctx, W / 2 + lw / 2 + 30, y + 85, W / 2 + lw / 2 + 130, y + 85, P.amber, 0.7 * k, 2);
  ctx.restore();
}

// ---------------------------------------------------------------- subtitles
function subtitleChunk(t) {
  const segs = TL.segments;
  const all = [];
  for (const s of segs) for (const c of s.chunks) all.push(c);
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
  const out = ramp(t, end - 0.1, end);
  const a = k * (1 - out);
  const rs = runs(cleanSub(c.text));
  let size = 58;
  const measure = (sz) => { ctx.font = `${sz}px SansB`; return rs.reduce((w, r) => w + ctx.measureText(r.t).width, 0); };
  while (measure(size) > 860 && size > 44) size -= 2;
  const tw = measure(size);
  const y = 1408 + (1 - k) * 12;
  ctx.save(); ctx.globalAlpha = a;
  ctx.font = `${size}px SansB`; ctx.textBaseline = 'alphabetic'; ctx.textAlign = 'left'; ctx.lineJoin = 'round';
  let x = W / 2 - tw / 2;
  // soft backing for legibility
  const bg = ctx.createLinearGradient(0, y - 90, 0, y + 40);
  bg.addColorStop(0, 'rgba(0,0,0,0)'); bg.addColorStop(0.5, 'rgba(0,0,0,0.28)'); bg.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = bg; ctx.fillRect(W / 2 - tw / 2 - 80, y - 90, tw + 160, 130);
  for (const r of rs) {
    ctx.strokeStyle = 'rgba(8,8,10,0.92)'; ctx.lineWidth = 10; ctx.strokeText(r.t, x, y);
    ctx.fillStyle = r.hl ? rgba(P.amber) : rgba(P.paper);
    ctx.fillText(r.t, x, y);
    x += ctx.measureText(r.t).width;
  }
  ctx.restore();
}

// ---------------------------------------------------------------- vignette
function drawVignette(ctx) {
  const v = cached('vignette', W, H, (c) => {
    const g = c.createRadialGradient(W / 2, H / 2, H * 0.28, W / 2, H / 2, H * 0.72);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.55)');
    c.fillStyle = g; c.fillRect(0, 0, W, H);
  });
  ctx.drawImage(v, 0, 0);
}

module.exports = { drawBackground, drawGrade, drawSnow, drawHUD, yearCard, drawSubtitle, drawVignette, winterAmount, sceneAt, bgState, yearAt, BG };
