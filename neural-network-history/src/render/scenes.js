// 20 个场景的画面。所有动画都锚定在旁白的时间点上（S/E/K/CH/charT）。
'use strict';
const E_ = require('./engine');
const L = require('./layers');
const {
  W, H, TAU, P, rgba, mix, clamp, lerp, ramp, eo, ei, eio, eback, smooth, fade, ap, rng, hash,
  S, E, K, CH, charT, roundRect, cached, text, spaced, wrap, para, glow, dot, ring, line, lineP, arrow,
  neuron, pulse, paperRect, card, stamp, createCanvas,
} = E_;

const CUES = [];        // sound-effect cues, consumed by music.py
const SHAKES = [];      // camera shake events
const FLASHES = [];     // full-screen flashes
const cue = (t, type, gain = 1) => CUES.push({ t: +t.toFixed(3), type, gain });

// ------------------------------------------------------------------ shared diagram helpers
function layerNodes(xs, counts, yc, gap) {
  return xs.map((x, l) => Array.from({ length: counts[l] }, (_, i) => ({ x, y: yc + (i - (counts[l] - 1) / 2) * gap })));
}
function drawEdges(ctx, layers, colFn, a = 1) {
  for (let l = 0; l + 1 < layers.length; l++)
    for (const [i, n] of layers[l].entries())
      for (const [j, m] of layers[l + 1].entries()) {
        const [c, al, lw] = colFn(l, i, j);
        line(ctx, n.x, n.y, m.x, m.y, c, al * a, lw);
      }
}
function chip(ctx, s, x, y, font, fg, bg, padX = 18, h = 52, a = 1) {
  ctx.font = font; const w = ctx.measureText(s).width + padX * 2;
  ctx.save(); ctx.globalAlpha *= a;
  ctx.fillStyle = bg; roundRect(ctx, x - w / 2, y - h / 2, w, h, h / 2); ctx.fill();
  text(ctx, s, x, y + 1, font, fg, 'center', 'middle');
  ctx.restore();
  return w;
}
function check(ctx, x, y, s, c, a = 1, lw = 8) {
  ctx.strokeStyle = rgba(c, a); ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(x - s * 0.5, y); ctx.lineTo(x - s * 0.12, y + s * 0.38); ctx.lineTo(x + s * 0.55, y - s * 0.42); ctx.stroke();
}
function cross(ctx, x, y, s, c, a = 1, lw = 8) {
  line(ctx, x - s / 2, y - s / 2, x + s / 2, y + s / 2, c, a, lw); line(ctx, x + s / 2, y - s / 2, x - s / 2, y + s / 2, c, a, lw);
}
function withAlpha(ctx, a, fn) { if (a <= 0.003) return; ctx.save(); ctx.globalAlpha *= a; fn(); ctx.restore(); }
function withXform(ctx, x, y, s, rot, fn) { ctx.save(); ctx.translate(x, y); ctx.rotate(rot || 0); ctx.scale(s, s); fn(); ctx.restore(); }
const sig = (x) => 1 / (1 + Math.exp(-x));

// ================================================================== HOOK
const HOOK = (() => {
  const xs = [300, 460, 620, 780, 900], counts = [6, 7, 7, 5, 1];
  return { layers: layerNodes(xs, counts, 740, 82), inputs: ['点赞', '停留', '关注', '评论', '搜索', '时段'] };
})();
function hook(ctx, t) {
  const frz = ramp(t, S('H2'), S('H2') + 0.9);
  const live = 1 - frz;
  const L_ = HOOK.layers;
  // header
  withAlpha(ctx, fade(t, 0, 99, 0.15), () => {
    const label = frz < 0.5 ? '推荐系统 · 正在为你计算' : '这个系统的祖先，曾被判过……';
    text(ctx, label, W / 2, 470, '36px SansM', rgba(P.paper, 0.72));
    if (Math.floor(t * 2.5) % 2 === 0) { ctx.font = '36px SansM'; const w = ctx.measureText(label).width; ctx.fillStyle = rgba(P.amber, 0.9); ctx.fillRect(W / 2 + w / 2 + 8, 442, 4, 34); }
  });
  // edges
  const col = (l) => mix(P.grey, P.amber, live);
  drawEdges(ctx, L_, (l, i, j) => [col(l), 0.12 + 0.14 * live * (0.5 + 0.5 * Math.sin(t * 2 + i + j * 1.7 + l)), 2]);
  // flowing pulses
  if (live > 0.01) {
    for (let l = 0; l + 1 < L_.length; l++) L_[l].forEach((n, i) => L_[l + 1].forEach((m, j) => {
      const h = hash(l * 100 + i * 10 + j);
      if (h > 0.55) return;
      const p = (t * (0.7 + h) + h * 7) % 1;
      pulse(ctx, n.x, n.y, m.x, m.y, p, P.amber, 0.85 * live, 7);
    }));
  }
  // nodes
  L_.forEach((layer, l) => layer.forEach((n, i) => {
    const lv = live * (0.35 + 0.65 * Math.pow(0.5 + 0.5 * Math.sin(t * 3.1 + i * 1.3 + l * 2.1), 3));
    neuron(ctx, n.x, n.y, l === 4 ? 30 : 17, l === 4 ? live : lv, P.amber);
  }));
  // input chips
  HOOK.inputs.forEach((s, i) => {
    const n = L_[0][i];
    text(ctx, s, n.x - 40, n.y + 10, '28px SansM', rgba(P.paper, 0.75 * (0.4 + 0.6 * live)), 'right');
  });
  // output → "this video" card
  const out = L_[4][0];
  text(ctx, '猜你喜欢', out.x, out.y + 72, '28px SansB', rgba(mix(P.grey, P.amber, live)), 'center');
  const kC = ap(t, 0.6, 0.6);
  withAlpha(ctx, kC, () => {
    const x = 210, y = 1110, w = 660, h = 150;
    line(ctx, out.x, out.y + 90, out.x, y - 10, mix(P.grey, P.amber, live), 0.5, 2, [6, 8]);
    ctx.fillStyle = rgba([24, 23, 21], 0.95); roundRect(ctx, x, y, w, h, 18); ctx.fill();
    ctx.strokeStyle = rgba(mix(P.grey, P.amber, live), 0.6); ctx.lineWidth = 2; roundRect(ctx, x, y, w, h, 18); ctx.stroke();
    // thumbnail
    ctx.fillStyle = rgba(P.bg); roundRect(ctx, x + 18, y + 18, 84, 114, 10); ctx.fill();
    neuron(ctx, x + 60, y + 58, 12, live, P.amber); text(ctx, '往事', x + 60, y + 112, '22px SerifB', rgba(P.paper, 0.8));
    text(ctx, '这条视频：《神经网络往事》', x + 128, y + 58, '32px SansB', rgba(P.paper, 0.92), 'left');
    const m = clamp((t - 1.2) / 3.0) * 0.97;
    const mm = live > 0.5 ? m : 0.97;
    ctx.fillStyle = rgba(P.paper, 0.12); roundRect(ctx, x + 128, y + 86, 310, 16, 8); ctx.fill();
    ctx.fillStyle = rgba(mix(P.grey, P.amber, live)); roundRect(ctx, x + 128, y + 86, 310 * eo(mm / 0.97) * 0.97, 16, 8); ctx.fill();
    text(ctx, `匹配度 ${Math.round(mm * 100)}%`, x + w - 22, y + 104, '28px SansB', rgba(mix(P.grey, P.amber, live)), 'right');
  });
  // two death sentences
  const k0 = K('H2');
  stamp(ctx, '死刑', 400, 690, 128, t - k0, -0.2, P.red, '1969');
  stamp(ctx, '死刑', 690, 900, 128, t - (k0 + 0.42), 0.13, P.red, '1990s');
}
function hookCues() {
  cue(K('H1') - 0.05, 'fire', 0.5);
  cue(K('H2'), 'stamp'); cue(K('H2') + 0.42, 'stamp');
  SHAKES.push({ t: K('H2'), amp: 16 }, { t: K('H2') + 0.42, amp: 18 });
  FLASHES.push({ t: K('H2'), c: P.red, a: 0.22 }, { t: K('H2') + 0.42, c: P.red, a: 0.22 });
  cue(S('H2'), 'freeze');
}

// ================================================================== TITLE
function title(ctx, t) {
  const t0 = S('H3') - 0.2;
  const k = ap(t, t0, 0.9);
  const cx = 540, cy = 620;
  glow(ctx, cx, cy, 300, P.amber, 0.16 * k);
  for (let i = 0; i < 3; i++) { const p = (((t - t0) * 0.45 + i / 3) % 1 + 1) % 1; ring(ctx, cx, cy, 34 + p * 260, P.amber, (1 - p) * 0.35 * k, 2); }
  neuron(ctx, cx, cy, 28, 0.65 + 0.35 * Math.sin(t * 4), P.amber, k);
  // dendrite strokes
  withAlpha(ctx, k * 0.5, () => {
    for (let i = 0; i < 7; i++) { const a = -Math.PI / 2 + (i - 3) * 0.42; const r1 = 46, r2 = 120 + 30 * hash(i);
      lineP(ctx, cx + Math.cos(a) * r1, cy + Math.sin(a) * r1, cx + Math.cos(a) * r2, cy + Math.sin(a) * r2, ap(t, t0 + 0.1 * i, 0.6), P.amber, 0.7, 3); }
  });
  const s = '神经网络往事';
  ctx.font = '150px SerifH';
  const ws = [...s].map((c) => ctx.measureText(c).width); const total = ws.reduce((a, b) => a + b, 0) + 8 * 5;
  let x = W / 2 - total / 2;
  [...s].forEach((c, i) => {
    const kk = ap(t, t0 + 0.15 + i * 0.09, 0.55);
    withAlpha(ctx, kk, () => text(ctx, c, x + ws[i] / 2, 920 + (1 - kk) * 40, '150px SerifH', rgba(P.paper), 'center'));
    x += ws[i] + 8;
  });
  withAlpha(ctx, ap(t, t0 + 0.9, 0.6), () => {
    text(ctx, '一个被判过两次死刑的想法', W / 2, 1020, '44px SansM', rgba(P.paper, 0.82));
    const y = 1100; line(ctx, 330, y - 14, 420, y - 14, P.amber, 0.6, 2); line(ctx, 660, y - 14, 750, y - 14, P.amber, 0.6, 2);
    text(ctx, '1943 — 2024', W / 2, y, '40px SerifB', rgba(P.amber));
  });
}
function titleCues() { cue(S('H3') - 0.2, 'boom', 0.9); cue(S('H3') - 0.1, 'fire', 0.8); }

// ================================================================== 1943 · PITTS
const PITTS = { no: 1, zh: '沃尔特·皮茨', en: 'Walter Pitts', role: '天才少年 · 1923 – 1969', note: '几乎全靠自学，一生没有拿过任何学位。', w: 760, h: 400 };
const MCC = { no: 2, zh: '沃伦·麦卡洛克', en: 'Warren McCulloch', role: '神经科学家 · 1898 – 1969', note: '把这个无处可去的少年，接到了自己家里住。', w: 760, h: 400 };
function book(ctx, x, y, w, h, col, label, glowK) {
  ctx.fillStyle = rgba(col); ctx.fillRect(x, y, w, h);
  ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.fillRect(x + w - 10, y, 10, h);
  ctx.fillStyle = rgba(P.gold, 0.85); ctx.fillRect(x + 8, y + 30, w - 16, 4); ctx.fillRect(x + 8, y + h - 34, w - 16, 4);
  withXform(ctx, x + w / 2, y + h / 2, 1, -Math.PI / 2, () => {
    text(ctx, label, 0, 9, '26px SerifB', rgba(P.gold, 0.95), 'center');
  });
  if (glowK > 0) glow(ctx, x + w / 2, y + h / 2, h * 0.8, P.amber, 0.25 * glowK);
}
function brain(ctx, cx, cy, t, a) {
  const pts = [];
  const N = 180;
  for (let i = 0; i <= N; i++) {
    const th = (i / N) * TAU;
    const r = 1 + 0.045 * Math.sin(7 * th + 1) + 0.025 * Math.sin(15 * th) - 0.12 * Math.max(0, Math.sin(th)) ** 3;
    pts.push([cx + Math.cos(th) * 320 * r, cy + Math.sin(th) * 230 * r]);
  }
  withAlpha(ctx, a, () => {
    ctx.strokeStyle = rgba(P.paper, 0.45); ctx.lineWidth = 3; ctx.beginPath();
    pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.stroke();
    // cerebellum + stem
    ctx.beginPath(); ctx.ellipse(cx + 190, cy + 200, 105, 62, 0.15, 0, TAU); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + 70, cy + 215); ctx.quadraticCurveTo(cx + 95, cy + 300, cx + 80, cy + 360); ctx.moveTo(cx + 140, cy + 250); ctx.quadraticCurveTo(cx + 150, cy + 310, cx + 140, cy + 360); ctx.stroke();
    // inner network
    const r = rng(77); const ns = [];
    while (ns.length < 46) { const x = (r() - 0.5) * 560, y = (r() - 0.5) * 380; if ((x / 290) ** 2 + (y / 200) ** 2 < 1) ns.push([cx + x, cy + y, r()]); }
    ns.forEach((p, i) => ns.forEach((q, j) => {
      if (j <= i) return; const d = Math.hypot(p[0] - q[0], p[1] - q[1]); if (d > 120) return;
      line(ctx, p[0], p[1], q[0], q[1], P.amber, 0.12 + 0.25 * Math.max(0, Math.sin(t * 2 + i * 0.7 + j)), 1.5);
    }));
    ns.forEach((p, i) => neuron(ctx, p[0], p[1], 7, Math.pow(Math.max(0, Math.sin(t * 2.4 + p[2] * 20)), 6), P.amber));
  });
}
function pitts(ctx, t) {
  const tCard = K('A2') - 0.15, tUp = S('A3'), tLeft = K('A4') - 0.3, tOut = S('A5');
  // Pitts card motion
  const up = eio(ramp(t, tUp, tUp + 0.7)), left = eio(ramp(t, tLeft, tLeft + 0.7)), out = eio(ramp(t, tOut, tOut + 0.6));
  let x = 540, y = 760, s = 1, r = -0.02;
  x = lerp(x, 540, up); y = lerp(y, 520, up); s = lerp(s, 0.72, up);
  x = lerp(x, 360, left); y = lerp(y, 560, left); s = lerp(s, 0.66, left); r = lerp(r, -0.05, left);
  withAlpha(ctx, 1 - out, () => card(ctx, PITTS, x, y - out * 80, ramp(t, tCard, tCard + 0.6), r, s));
  // library: books, days, letter
  const libA = fade(t, CH('A3', 1) - 0.3, S('A4') + 0.6, 0.4, 0.5);
  withAlpha(ctx, libA, () => {
    const by = 760, bh = 330;
    const gk = ap(t, CH('A3', 2), 0.6) * (1 - ap(t, CH('A3', 3) + 0.4, 0.8));
    book(ctx, 330, by, 110, bh, [118, 34, 30], 'PRINCIPIA MATHEMATICA · I', gk);
    book(ctx, 445, by + 12, 110, bh - 12, [118, 34, 30], 'PRINCIPIA MATHEMATICA · II', gk);
    book(ctx, 560, by + 24, 110, bh - 24, [118, 34, 30], 'PRINCIPIA MATHEMATICA · III', gk);
    line(ctx, 280, by + bh + 2, 720, by + bh + 2, P.paper, 0.4, 3);
    // day counter + sun/moon arc
    const d = clamp((t - CH('A3', 1)) / (CH('A3', 2) - CH('A3', 1)));
    const day = Math.min(3, 1 + Math.floor(d * 3));
    const ph = (d * 3) % 1; const ang = Math.PI + ph * Math.PI;
    const sx = 500 + Math.cos(ang) * 300, sy = by - 20 + Math.sin(ang) * 120;
    if (Math.floor(d * 6) % 2 === 0) glow(ctx, sx, sy, 50, P.amber, 0.7); else { dot(ctx, sx, sy, 16, P.paper, 0.85); dot(ctx, sx + 7, sy - 4, 14, P.bg, 1); }
    text(ctx, `第 ${day} 天`, 810, by + 120, '48px SerifB', rgba(P.paper, 0.9), 'center');
    text(ctx, '躲在图书馆', 810, by + 170, '28px Kai', rgba(P.paper, 0.6), 'center');
    withAlpha(ctx, ap(t, CH('A3', 2), 0.5) * (1 - ap(t, CH('A3', 3) - 0.2, 0.3)), () => text(ctx, '《数学原理》 罗素 & 怀特海', 500, by + bh + 52, '30px SansM', rgba(P.amber, 0.9), 'center'));
  });
  // letter
  const letA = fade(t, CH('A3', 3) - 0.1, S('A4') + 0.9, 0.4, 0.5);
  withAlpha(ctx, letA, () => {
    const k = ap(t, CH('A3', 3) - 0.1, 0.6);
    withXform(ctx, 600 + (1 - k) * 300, 990, 1, 0.06, () => {
      paperRect(ctx, -260, -170, 520, 340, 6, [240, 234, 220]);
      const lines = ['罗素先生：', '您的《数学原理》第一卷，', '似乎有几处问题……', '—— 沃尔特·皮茨（12岁）'];
      lines.forEach((l, i) => text(ctx, l, -220 + (i === 3 ? 140 : 0), -95 + i * 64, i === 3 ? '28px Kai' : '36px Kai', rgba(P.ink, 0.85), 'left'));
      lineP(ctx, -220, -10, 60, -6, ap(t, CH('A3', 3) + 0.5, 0.5), P.red, 0.8, 4);
    });
  });
  withAlpha(ctx, letA, () => text(ctx, '* 出自后人的回忆与报道，细节或有出入', 540, 1250, '24px SansR', rgba(P.paper, 0.45)));
  // run away → meets McCulloch
  const runA = fade(t, S('A4'), S('A5') + 0.4, 0.3, 0.5);
  withAlpha(ctx, runA, () => {
    const k = ap(t, S('A4'), 0.6);
    chip(ctx, '15 岁 · 离家出走', 360, 760, '32px SansB', rgba(P.bg), rgba(P.amber), 22, 58, k);
    // dotted road
    ctx.setLineDash([4, 14]); ctx.strokeStyle = rgba(P.paper, 0.4 * k); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(360, 800);
    ctx.bezierCurveTo(360, 900, 620, 840, 600, 960 * 1); ctx.stroke(); ctx.setLineDash([]);
  });
  withAlpha(ctx, 1 - out, () => card(ctx, MCC, 620, 1000 - out * 80, ramp(t, tLeft, tLeft + 0.6), 0.035, 0.66));
  withAlpha(ctx, ap(t, tLeft + 0.7, 0.5) * (1 - out), () => text(ctx, '相差 25 岁', 860, 760, '34px Kai', rgba(P.amber), 'center'));
  // the question
  const qA = ap(t, tOut + 0.1, 0.8);
  if (qA > 0) {
    brain(ctx, 540, 820, t, qA);
    const qk = ap(t, CH('A5', 1), 0.5);
    withAlpha(ctx, qk, () => { glow(ctx, 540, 800, 180, P.amber, 0.25); text(ctx, '?', 540, 870 + (1 - qk) * 30, '200px SerifH', rgba(P.amber), 'center'); });
  }
  L.yearCard(ctx, t, S('A1') - 0.1, 1943, '一个少年，和一个问题', 2.0);
}
function pittsCues() {
  cue(S('A1') - 0.1, 'whoosh', 0.7); cue(K('A2') - 0.1, 'paper'); cue(CH('A3', 1) - 0.2, 'paper', 0.6); cue(CH('A3', 3) - 0.05, 'paper');
  cue(S('A4'), 'pop', 0.6); cue(K('A4') - 0.3, 'paper'); cue(CH('A5', 1), 'fire', 0.6);
}

// ================================================================== 1943 · MP NEURON
const BIO = (() => {
  // procedural biological neuron, drawn once
  return cached('bioNeuron', 900, 420, (g) => {
    const r = rng(11);
    const sx = 230, sy = 210;
    g.strokeStyle = rgba(P.paper, 0.85); g.lineCap = 'round';
    function branch(x, y, ang, len, w, depth) {
      const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
      g.lineWidth = w; g.beginPath(); g.moveTo(x, y);
      g.quadraticCurveTo((x + x2) / 2 + (r() - 0.5) * 20, (y + y2) / 2 + (r() - 0.5) * 20, x2, y2); g.stroke();
      if (depth > 0) { branch(x2, y2, ang - 0.35 - r() * 0.3, len * 0.68, w * 0.62, depth - 1); branch(x2, y2, ang + 0.35 + r() * 0.3, len * 0.68, w * 0.62, depth - 1); }
    }
    for (let i = 0; i < 6; i++) branch(sx, sy, Math.PI + (i - 2.5) * 0.42, 70, 7, 3);
    // axon
    g.lineWidth = 7; g.beginPath(); g.moveTo(sx + 40, sy); g.bezierCurveTo(400, sy - 30, 560, sy + 30, 760, sy); g.stroke();
    for (let i = 0; i < 4; i++) { const x = 330 + i * 100; g.fillStyle = rgba(P.paper, 0.9); roundRect(g, x, sy - 13 + Math.sin(i) * 6, 70, 26, 13); g.fill(); }
    for (let i = 0; i < 5; i++) { const a = (i - 2) * 0.35; g.lineWidth = 3; g.beginPath(); g.moveTo(760, sy); g.lineTo(760 + Math.cos(a) * 80, sy + Math.sin(a) * 80); g.stroke(); g.fillStyle = rgba(P.amber); g.beginPath(); g.arc(760 + Math.cos(a) * 86, sy + Math.sin(a) * 86, 8, 0, TAU); g.fill(); }
    g.fillStyle = rgba(P.amber, 0.9); g.beginPath(); g.ellipse(sx, sy, 50, 42, 0.2, 0, TAU); g.fill();
    g.fillStyle = rgba(P.bg, 0.6); g.beginPath(); g.arc(sx + 6, sy - 4, 15, 0, TAU); g.fill();
  });
})();
function mpUnit(ctx, t, cx, cy, sc, inputs, thr, tIn, label = true, a = 1) {
  // inputs: values; tIn: time inputs start travelling (null = idle)
  const ins = inputs.map((_, i) => ({ x: cx - 400 * sc, y: cy + (i - (inputs.length - 1) / 2) * 170 * sc }));
  const R = 76 * sc;
  const p = tIn == null ? -1 : clamp((t - tIn) / 0.8);
  const sum = inputs.reduce((s, v, i) => s + (p >= 1 - i * 0.05 ? v : 0), 0);
  const fired = tIn != null && p >= 1 && sum >= thr;
  const fireK = fired ? clamp((t - tIn - 0.85) / 0.6) : 0;
  withAlpha(ctx, a, () => {
    ins.forEach((n, i) => {
      line(ctx, n.x, n.y, cx - R * 0.95, cy + (n.y - cy) * 0.25, P.paper, 0.45, 3);
      const v = inputs[i];
      chip(ctx, String(v), n.x - 34 * sc, n.y, `${Math.round(34 * sc)}px SansB`, rgba(v ? P.bg : P.paper), rgba(v ? P.amber : P.grey, v ? 1 : 0.5), 16 * sc, 54 * sc);
      if (v && p >= 0 && p < 1) pulse(ctx, n.x, n.y, cx - R, cy + (n.y - cy) * 0.25, p, P.amber, 1, 10 * sc);
    });
    line(ctx, cx + R, cy, cx + 360 * sc, cy, P.paper, 0.45, 3);
    if (fired) pulse(ctx, cx + R, cy, cx + 360 * sc, cy, clamp(fireK * 1.3), P.amber, 1, 12 * sc);
    neuron(ctx, cx, cy, R, tIn == null ? 0.15 : 0.15 + 0.85 * (fired ? 1 : 0.25 * p), fired ? P.amber : P.paper, 1, false);
    text(ctx, tIn == null ? 'Σ' : String(sum), cx, cy + 18 * sc, `${Math.round(54 * sc)}px SerifB`, rgba(P.paper), 'center');
    if (label) text(ctx, `门槛 ${thr}`, cx, cy + R + 46 * sc, `${Math.round(30 * sc)}px SansM`, rgba(P.paper, 0.65), 'center');
    // output lamp
    const lx = cx + 360 * sc;
    const on = fired ? eo(clamp((fireK - 0.5) * 3)) : 0;
    if (on > 0) glow(ctx, lx, cy, 90 * sc, P.amber, 0.6 * on);
    dot(ctx, lx, cy, 30 * sc, on > 0 ? P.amber : P.grey, on > 0 ? 1 : 0.5);
    text(ctx, tIn == null ? '' : (fired && on > 0.2 ? '1' : (p >= 1 ? '0' : '')), lx, cy + 13 * sc, `${Math.round(36 * sc)}px SansB`, rgba(P.bg), 'center');
  });
  return { fired, p, sum };
}
function mpneuron(ctx, t) {
  const tMorph = CH('A6', 1) - 0.1;
  // biological neuron, revealed left → right, then fades as the switch appears
  const bioA = ap(t, S('A6') - 0.2, 0.4) * (1 - ap(t, tMorph + 0.4, 0.6));
  withAlpha(ctx, bioA, () => {
    const rev = ap(t, S('A6') - 0.2, 1.3);
    ctx.save(); ctx.beginPath(); ctx.rect(90, 0, 900 * rev, H); ctx.clip();
    ctx.drawImage(BIO, 90, 560); ctx.restore();
    text(ctx, '树突 · 接收', 240, 1030, '28px SansM', rgba(P.paper, 0.6)); text(ctx, '胞体', 320, 700 - 28, '28px SansM', rgba(P.amber, 0.9));
    text(ctx, '轴突 · 输出', 700, 1030, '28px SansM', rgba(P.paper, 0.6));
  });
  // abstract unit
  const unitA = ap(t, tMorph, 0.6) * (1 - ap(t, S('A8') - 0.1, 0.5));
  const phase2 = CH('A7', 1);
  if (unitA > 0) {
    let res;
    if (t < S('A7')) res = mpUnit(ctx, t, 540, 800, 1, [1, 0, 1], 2, null, true, unitA);
    else if (t < phase2) res = mpUnit(ctx, t, 540, 800, 1, [1, 0, 1], 2, S('A7') + 0.1, true, unitA);
    else res = mpUnit(ctx, t, 540, 800, 1, [1, 0, 0], 2, phase2 + 0.05, true, unitA);
    withAlpha(ctx, unitA * ap(t, K('A6'), 0.4), () => {
      text(ctx, '神经元 = 小开关', 540, 520, '54px SerifH', rgba(P.paper), 'center');
      text(ctx, '输入相加，超过门槛就“放电”', 540, 580, '30px SansM', rgba(P.paper, 0.6), 'center');
    });
    if (t >= S('A7')) {
      const fired = t < phase2;
      const tag = fired ? '≥ 门槛 → 放电' : '< 门槛 → 沉默';
      withAlpha(ctx, unitA * ap(t, (fired ? S('A7') : phase2) + 0.8, 0.3), () =>
        chip(ctx, tag, 540, 1110, '36px SansB', rgba(fired ? P.bg : P.paper), rgba(fired ? P.amber : P.grey, fired ? 1 : 0.6), 26, 64));
    }
  }
  // logic gates
  const gA = fade(t, S('A8') - 0.1, S('A9') + 0.3, 0.5, 0.4);
  withAlpha(ctx, gA, () => {
    text(ctx, '改一改门槛，就是不同的逻辑门', 540, 520, '40px SerifB', rgba(P.paper), 'center');
    const gates = [{ name: '与 AND', thr: 2, x: 300 }, { name: '或 OR', thr: 1, x: 780 }];
    gates.forEach((gt, gi) => {
      const cyc = ((Math.floor((t - S('A8')) / 0.75 + gi) % 4) + 4) % 4;
      const a = [[0, 0], [0, 1], [1, 0], [1, 1]][cyc];
      const ty = 760;
      const sumv = a[0] + a[1]; const on = sumv >= gt.thr;
      line(ctx, gt.x - 150, ty - 60, gt.x - 50, ty - 15, P.paper, 0.45, 3); line(ctx, gt.x - 150, ty + 60, gt.x - 50, ty + 15, P.paper, 0.45, 3);
      chip(ctx, String(a[0]), gt.x - 175, ty - 62, '30px SansB', rgba(a[0] ? P.bg : P.paper), rgba(a[0] ? P.amber : P.grey, a[0] ? 1 : 0.5), 14, 48);
      chip(ctx, String(a[1]), gt.x - 175, ty + 62, '30px SansB', rgba(a[1] ? P.bg : P.paper), rgba(a[1] ? P.amber : P.grey, a[1] ? 1 : 0.5), 14, 48);
      neuron(ctx, gt.x, ty, 56, on ? 1 : 0.15, on ? P.amber : P.paper, 1, false);
      text(ctx, String(gt.thr), gt.x, ty + 14, '40px SerifB', rgba(P.paper), 'center');
      line(ctx, gt.x + 56, ty, gt.x + 140, ty, P.paper, 0.45, 3);
      dot(ctx, gt.x + 150, ty, 18, on ? P.amber : P.grey, on ? 1 : 0.5);
      text(ctx, gt.name, gt.x, ty + 120, '36px SansB', rgba(P.amber), 'center');
      text(ctx, `门槛 ${gt.thr}`, gt.x, ty + 164, '28px SansM', rgba(P.paper, 0.6), 'center');
    });
    // wiring into a bigger net
    const k = ap(t, CH('A8', 1), 0.8);
    withAlpha(ctx, k, () => {
      const net = layerNodes([260, 440, 640, 820], [3, 4, 4, 2], 1080, 54);
      drawEdges(ctx, net, () => [P.amber, 0.18, 1.5]);
      net.forEach((ly, l) => ly.forEach((n, i) => neuron(ctx, n.x, n.y, 12, Math.pow(Math.max(0, Math.sin(t * 4 + l * 1.4 + i)), 4), P.amber)));
      text(ctx, '连起来 → 逻辑运算', 540, 1230, '32px SansM', rgba(P.paper, 0.7), 'center');
    });
  });
  // the paper
  const pA = ap(t, S('A9') - 0.1, 0.6);
  withAlpha(ctx, pA, () => withXform(ctx, 540, 790 + (1 - pA) * 60, 1, -0.015, () => {
    paperRect(ctx, -410, -230, 820, 460, 8);
    text(ctx, 'BULLETIN OF MATHEMATICAL BIOPHYSICS · 1943', 0, -170, '22px SansM', rgba(P.ink, 0.55), 'center');
    line(ctx, -360, -150, 360, -150, P.ink, 0.3, 2);
    text(ctx, 'A Logical Calculus of the Ideas', 0, -80, '44px SerifB', rgba(P.ink), 'center');
    text(ctx, 'Immanent in Nervous Activity', 0, -24, '44px SerifB', rgba(P.ink), 'center');
    text(ctx, 'W. S. McCulloch  &  W. Pitts', 0, 40, '30px SansM', rgba(P.ink, 0.7), 'center');
    text(ctx, '《神经活动中内在思想的逻辑演算》', 0, 96, '30px SerifM', rgba(P.ink, 0.75), 'center');
    const kk = ap(t, K('A9') - 0.1, 0.4);
    withAlpha(ctx, kk, () => chip(ctx, '人类第一个人工神经元模型', 0, 172, '34px SansB', rgba(P.bg), rgba(P.amberDeep), 28, 64));
  }));
}
function mpneuronCues() {
  cue(S('A6') - 0.2, 'whoosh', 0.5); cue(CH('A6', 1) - 0.1, 'click', 0.8);
  cue(S('A7') + 0.95, 'fire', 1); cue(CH('A7', 1) + 0.9, 'dud', 0.7);
  cue(S('A8') - 0.1, 'whoosh', 0.4); cue(S('A9') - 0.1, 'paper'); cue(K('A9'), 'ding', 0.6);
}

// ================================================================== 1958 · PERCEPTRON
const ROSEN = { no: 3, zh: '弗兰克·罗森布拉特', en: 'Frank Rosenblatt', role: '心理学家 · 1928 – 1971', note: '康奈尔航空实验室。他想造一台会自己学习的机器。', w: 760, h: 380 };
// a real (tiny) perceptron run, so the weight map on screen is honest
const PERC = (() => {
  const r = rng(58), N = 10;
  const trials = [];
  let w = Array.from({ length: N * N }, () => (r() - 0.5) * 0.2), b = 0;
  for (let k = 0; k < 50; k++) {
    const left = k === 0 ? true : r() < 0.5;
    const s = 2 + Math.floor(r() * 2);
    const cx = left ? Math.floor(r() * (4 - s + 1)) : 6 + Math.floor(r() * (4 - s + 1));
    const cy = Math.floor(r() * (N - s + 1));
    const x = new Array(N * N).fill(0);
    for (let i = 0; i < s; i++) for (let j = 0; j < s; j++) x[(cy + i) * N + cx + j] = 1;
    const target = left ? 1 : -1;
    let act = b; for (let i = 0; i < x.length; i++) act += w[i] * x[i];
    let guess = act >= 0 ? 1 : -1;
    if (k === 0) guess = -1;        // first demo trial is a miss, as narrated
    const before = w.slice();
    if (guess !== target) { for (let i = 0; i < x.length; i++) w[i] += 0.25 * target * x[i]; b += 0.05 * target; }
    trials.push({ x, target, guess, ok: guess === target, before, after: w.slice() });
  }
  return { trials, N };
})();
function trialTimes() {
  const t0 = S('B5') + 0.2, t1 = E('B5') - 0.7;
  const ts = [S('B3') + 0.1];
  for (let i = 1; i < 50; i++) ts.push(t0 + (t1 - t0) * Math.pow((i - 1) / 48, 1.7));
  return ts;
}
let _TT = null;
function perceptron(ctx, t) {
  // B1: hand-wired logic, no learning
  const b1A = fade(t, S('B1') - 0.2, S('B2') + 0.4, 0.4, 0.5);
  withAlpha(ctx, b1A, () => {
    const net = layerNodes([300, 540, 780], [3, 2, 1], 800, 150);
    drawEdges(ctx, net, () => [P.paper, 0.35, 3]);
    for (let l = 0; l < 2; l++) net[l].forEach((n) => net[l + 1].forEach((m) => {
      const x = (n.x + m.x) / 2, y = (n.y + m.y) / 2;
      ctx.fillStyle = rgba(P.grey, 0.95); roundRect(ctx, x - 13, y - 6, 26, 22, 4); ctx.fill();
      ctx.strokeStyle = rgba(P.grey); ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(x, y - 6, 8, Math.PI, 0); ctx.stroke();
    }));
    net.forEach((ly) => ly.forEach((n) => neuron(ctx, n.x, n.y, 30, 0.2, P.paper)));
    text(ctx, '接法：全靠人来设计', 540, 560, '44px SerifB', rgba(P.paper), 'center');
    withAlpha(ctx, ap(t, S('B1') + 0.6, 0.4), () => chip(ctx, '✕  不会学习', 540, 1080, '36px SansB', rgba(P.paper), rgba(P.red, 0.85), 26, 64));
  });
  // B2: Rosenblatt + perceptron title
  const b2A = fade(t, S('B2') + 1.6, S('B3') + 0.2, 0.5, 0.5);
  withAlpha(ctx, b2A, () => {
    card(ctx, ROSEN, 540, 600, ramp(t, S('B2') + 1.6, S('B2') + 2.2), -0.02, 0.86);
    const k = ap(t, K('B2') - 0.1, 0.5);
    withAlpha(ctx, k, () => {
      glow(ctx, 540, 930, 260, P.amber, 0.18);
      text(ctx, '感知机', 540, 980 + (1 - k) * 30, '120px SerifH', rgba(P.amber), 'center');
      text(ctx, 'Perceptron', 540, 1040, '40px SansR', rgba(P.paper, 0.7), 'center');
    });
    // see → guess → fix loop
    const k2 = ap(t, CH('B2', 2), 0.5);
    withAlpha(ctx, k2, () => {
      const items = ['看', '猜', '改'];
      items.forEach((s, i) => {
        const a = -Math.PI / 2 + i * TAU / 3 + t * 0.6; const x = 540 + Math.cos(a) * 0, y = 1170;
        chip(ctx, s, 380 + i * 160, y, '36px SansB', rgba(P.bg), rgba(i === 2 ? P.amber : P.paper, 0.95), 24, 60);
        if (i < 2) arrow(ctx, 420 + i * 160, y, 498 + i * 160, y, P.paper, 0.6, 3, 12);
      });
      ctx.strokeStyle = rgba(P.paper, 0.5); ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(700, 1200); ctx.quadraticCurveTo(540, 1270, 380, 1200); ctx.stroke();
      arrow(ctx, 400, 1212, 380, 1200, P.paper, 0.5, 3, 12);
    });
  });
  // B3–B5: the learning demo
  const dA = ap(t, S('B3') - 0.1, 0.5);
  if (dA <= 0) return L.yearCard(ctx, t, S('B2') - 0.05, 1958, '会学习的机器', 1.7);
  if (!_TT) _TT = trialTimes();
  const TT = _TT;
  let k = 0; while (k + 1 < TT.length && t >= TT[k + 1]) k++;
  const tr = PERC.trials[k];
  const lt = t - TT[k];
  const span = (k + 1 < TT.length ? TT[k + 1] : TT[k] + 1.2) - TT[k];
  // phases within a trial (first trial is narrated slowly)
  const first = k === 0;
  const tSee = first ? charT('B3', '看卡片') : TT[k];
  const tGuess = first ? charT('B3', '猜答案') : TT[k] + span * 0.35;
  const tJudge = first ? charT('B3', '猜错了') : TT[k] + span * 0.55;
  const tFix = first ? CH('B3', 1) : TT[k] + span * 0.65;
  const fixK = first ? ap(t, tFix + 0.2, 1.6) : ap(t, tFix, Math.max(0.05, span * 0.3));
  withAlpha(ctx, dA, () => {
    // counter
    text(ctx, `第 ${k + 1} 次`, 120, 560, '44px SerifB', rgba(P.paper), 'left');
    text(ctx, '感知机 · 学习中', 960, 560, '30px SansM', rgba(P.paper, 0.55), 'right');
    // card with a mark
    const N = PERC.N;
    withXform(ctx, 205, 790, 1, -0.03, () => {
      paperRect(ctx, -95, -125, 190, 250, 6, [240, 234, 220], false);
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) if (tr.x[i * N + j]) { ctx.fillStyle = rgba(P.ink); ctx.fillRect(-80 + j * 16, -80 + i * 16, 16, 16); }
      line(ctx, 0, -110, 0, 110, P.ink, 0.15, 2, [6, 6]);
    });
    arrow(ctx, 318, 790, 372, 790, P.paper, 0.5 * ap(t, tSee, 0.3), 4, 14);
    // weight map
    const gx = 392, gy = 640, cs = 30;
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
      const idx = i * N + j;
      const wv = lerp(tr.before[idx], tr.after[idx], fixK);
      const m = clamp(Math.abs(wv) / 0.6);
      const c = wv >= 0 ? P.amber : P.ice;
      ctx.fillStyle = rgba(mix(P.bg2, c, 0.15 + 0.75 * m)); ctx.fillRect(gx + j * cs + 1, gy + i * cs + 1, cs - 2, cs - 2);
      if (tr.x[idx] && t >= tSee) { ctx.strokeStyle = rgba(P.paper, 0.95); ctx.lineWidth = 3; ctx.strokeRect(gx + j * cs + 2.5, gy + i * cs + 2.5, cs - 5, cs - 5); }
    }
    text(ctx, '连线强弱（权重）', gx + 150, gy - 22, '28px SansM', rgba(P.paper, 0.65), 'center');
    text(ctx, '偏“左”', gx + 40, gy + 340, '24px SansM', rgba(P.amber, 0.9), 'center');
    text(ctx, '偏“右”', gx + 260, gy + 340, '24px SansM', rgba(P.ice, 0.9), 'center');
    arrow(ctx, 702, 790, 744, 790, P.paper, 0.5, 4, 14);
    // output
    const showG = t >= tGuess;
    const g = tr.guess > 0 ? '左' : '右';
    neuron(ctx, 820, 790, 62, showG ? 0.8 : 0.2, tr.guess > 0 ? P.amber : P.ice, 1, false);
    text(ctx, showG ? g : '?', 820, 810, '56px SerifH', rgba(P.paper), 'center');
    text(ctx, `答案：${tr.target > 0 ? '左' : '右'}`, 820, 900, '28px SansM', rgba(P.paper, 0.6), 'center');
    if (t >= tJudge) {
      const jk = ap(t, tJudge, 0.15);
      if (tr.ok) check(ctx, 820, 700, 56 * jk, P.amber, 1, 9); else cross(ctx, 820, 700, 52 * jk, P.red, 1, 9);
    }
    if (first) withAlpha(ctx, ap(t, K('B3') - 0.1, 0.3) * (1 - ap(t, S('B5') + 0.3, 0.3)), () =>
      chip(ctx, '猜错了 → 调一调', 540, 1040, '36px SansB', rgba(P.bg), rgba(P.amber), 26, 64));
    // accuracy curve (rolling over last 8 trials)
    const cx0 = 140, cx1 = 940, cy0 = 1240, cy1 = 1090;
    withAlpha(ctx, ap(t, S('B5'), 0.5), () => {
      line(ctx, cx0, cy0, cx1, cy0, P.paper, 0.3, 2); line(ctx, cx0, cy0, cx0, cy1 - 10, P.paper, 0.3, 2);
      text(ctx, '正确率', cx0 + 10, cy1 - 18, '24px SansM', rgba(P.paper, 0.6), 'left');
      text(ctx, '50 次', cx1, cy0 + 32, '22px SansM', rgba(P.paper, 0.5), 'right');
      ctx.strokeStyle = rgba(P.amber); ctx.lineWidth = 4; ctx.beginPath();
      for (let i = 0; i <= k; i++) {
        const win = PERC.trials.slice(Math.max(0, i - 7), i + 1); const acc = win.filter((q) => q.ok).length / win.length;
        const x = lerp(cx0, cx1, i / 49), y = lerp(cy0, cy1, acc);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.stroke();
    });
    const done = ap(t, E('B5') - 0.6, 0.4);
    withAlpha(ctx, done, () => chip(ctx, '✓  学会了：分得清左右', 540, 1040, '36px SansB', rgba(P.bg), rgba(P.amber), 26, 64));
  });
  withAlpha(ctx, ap(t, S('B5') + 1, 0.6), () =>
    para(ctx, '注：1958 年的公开演示在 IBM 704 计算机上运行；1960 年造出的 Mark I 硬件，用 20×20 = 400 个光电管当“眼睛”。', 120, 1296, 840, '23px SansR', rgba(P.paper, 0.45), 32));
}
function perceptronCues() {
  cue(S('B1') - 0.2, 'whoosh', 0.4); cue(S('B1') + 0.6, 'error', 0.5);
  cue(S('B2') - 0.05, 'whoosh', 0.7); cue(S('B2') + 1.6, 'paper'); cue(K('B2') - 0.1, 'fire', 0.7);
  if (!_TT) _TT = trialTimes();
  cue(charT('B3', '猜错了'), 'error', 0.8);
  _TT.forEach((tt, i) => { if (i === 0) return; const span = (_TT[i + 1] || tt + 0.6) - tt; cue(tt + span * 0.55, PERC.trials[i].ok ? 'tick' : 'error', PERC.trials[i].ok ? 0.35 : 0.3); });
  cue(E('B5') - 0.6, 'ding', 0.8);
}

// ================================================================== 1958 · NYT
function hypeCurve(ctx, t, x0, y0, x1, y1, prog, crashProg, alpha) {
  // years 1943..1975 on x; expectation on y
  const Y = (yr) => lerp(x0, x1, (yr - 1943) / (1975 - 1943));
  const f = (yr) => {
    if (yr < 1958) return 0.08 + 0.12 * (yr - 1943) / 15;
    if (yr < 1962) return 0.2 + 0.75 * eo((yr - 1958) / 4);
    if (yr < 1969) return 0.95 - 0.08 * (yr - 1962) / 7;
    return Math.max(0.03, 0.87 - 0.84 * eo((yr - 1969) / 3.5));
  };
  withAlpha(ctx, alpha, () => {
    line(ctx, x0, y0, x1, y0, P.paper, 0.3, 2); line(ctx, x0, y0, x0, y1 - 10, P.paper, 0.3, 2);
    for (const yr of [1943, 1958, 1969]) { line(ctx, Y(yr), y0, Y(yr), y0 + 10, P.paper, 0.4, 2); text(ctx, String(yr), Y(yr), y0 + 40, '24px SansM', rgba(P.paper, 0.55)); }
    const end = lerp(1943, 1969, prog) + (crashProg > 0 ? 6 * crashProg : 0);
    ctx.lineWidth = 6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.strokeStyle = rgba(P.amber); ctx.beginPath();
    let yr = 1943; ctx.moveTo(Y(yr), lerp(y0, y1, f(yr)));
    for (yr = 1943; yr <= Math.min(end, 1969); yr += 0.25) ctx.lineTo(Y(yr), lerp(y0, y1, f(yr)));
    ctx.stroke();
    if (end > 1969) {
      ctx.strokeStyle = rgba(P.red); ctx.beginPath(); ctx.moveTo(Y(1969), lerp(y0, y1, f(1969)));
      for (yr = 1969; yr <= end; yr += 0.2) ctx.lineTo(Y(yr), lerp(y0, y1, f(yr)));
      ctx.stroke();
    }
    const hx = Y(end), hy = lerp(y0, y1, f(end));
    glow(ctx, hx, hy, 40, end > 1969 ? P.red : P.amber, 0.8);
  });
}
function nyt(ctx, t) {
  const k = ap(t, S('B6') - 0.15, 0.7);
  const shrink = eio(ramp(t, S('B7') - 0.1, S('B7') + 0.6));
  const body = '海军今天展示了一台电子计算机的雏形。人们期待它将来能走路、说话、看东西、写字、自我复制，并意识到自己的存在。';
  const hl = '意识到自己的存在';
  withAlpha(ctx, k, () => withXform(ctx, lerp(540, 540, shrink), lerp(800, 600, shrink) + (1 - k) * 120, lerp(1, 0.62, shrink), -0.025, () => {
    paperRect(ctx, -430, -350, 860, 700, 4, [233, 226, 208]);
    text(ctx, '1958 年 7 月 8 日', -380, -292, '26px SansM', rgba(P.ink, 0.6), 'left');
    text(ctx, '《纽约时报》', 380, -292, '26px SansM', rgba(P.ink, 0.6), 'right');
    line(ctx, -390, -270, 390, -270, P.ink, 0.6, 3); line(ctx, -390, -262, 390, -262, P.ink, 0.4, 1);
    text(ctx, 'NEW NAVY DEVICE', 0, -190, '62px SerifH', rgba(P.ink), 'center');
    text(ctx, 'LEARNS BY DOING', 0, -122, '62px SerifH', rgba(P.ink), 'center');
    text(ctx, '海军新装置：边做边学', 0, -58, '40px SerifB', rgba(P.ink, 0.8), 'center');
    line(ctx, -390, -26, 390, -26, P.ink, 0.35, 2);
    // typewriter body + highlighter
    const n = Math.floor(body.length * clamp((t - S('B6') - 0.2) / Math.max(0.5, (K('B6') - S('B6') - 0.2))));
    const shown = body.slice(0, n);
    const font = '36px SerifR';
    const lines = wrap(ctx, body, 760, font);
    let idx = 0; const hs = body.indexOf(hl), he = hs + hl.length;
    const hk = ap(t, K('B6'), 0.6);
    lines.forEach((ln, li) => {
      const y = 40 + li * 58; let x = -380;
      ctx.font = font;
      for (const ch of [...ln]) {
        const w = ctx.measureText(ch).width;
        if (idx >= hs && idx < he && hk > 0) { const kk = clamp(hk * hl.length - (idx - hs)); ctx.fillStyle = rgba(P.amber, 0.75); ctx.fillRect(x, y - 34, w * kk, 46); }
        if (idx < shown.length) text(ctx, ch, x, y, font, rgba(P.ink, 0.88), 'left');
        x += w; idx++;
      }
    });
  }));
  // hype curve
  const hA = ap(t, S('B7'), 0.5);
  if (hA > 0) {
    hypeCurve(ctx, t, 150, 1230, 930, 900, ap(t, S('B7'), 2.6) * 0.62, 0, hA);
    withAlpha(ctx, ap(t, CH('B7', 1) - 0.2, 0.5), () => text(ctx, '会思考的机器，就要来了？', 640, 870, '34px Kai', rgba(P.amber), 'center'));
    text(ctx, '期待', 160, 885, '26px SansM', rgba(P.paper, 0.6 * hA), 'left');
  }
}
function nytCues() { cue(S('B6') - 0.15, 'paper'); cue(S('B6') + 0.2, 'type', 1); cue(K('B6'), 'marker', 0.6); cue(S('B7'), 'riser', 0.6); }

// ================================================================== 1969 · XOR
const XP = { x0: 300, y0: 560, s: 480 };
const XPT = [[0, 0, 0], [1, 0, 1], [0, 1, 1], [1, 1, 0]];
const xpPos = (a, b, P_ = XP) => [P_.x0 + 60 + a * (P_.s - 120), P_.y0 + P_.s - 60 - b * (P_.s - 120)];
function xorPlot(ctx, t, a, P_ = XP, heat = null) {
  withAlpha(ctx, a, () => {
    ctx.strokeStyle = rgba(P.paper, 0.3); ctx.lineWidth = 2; ctx.strokeRect(P_.x0, P_.y0, P_.s, P_.s);
    if (heat) {
      const n = 36, cs = P_.s / n;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
        const u = (j + 0.5) / n, v = 1 - (i + 0.5) / n;
        const uu = (u * P_.s - 60) / (P_.s - 120), vv = (v * P_.s - 60) / (P_.s - 120);
        const o = heat(uu, vv);
        ctx.fillStyle = rgba(mix(P.ice, P.amber, o), 0.32); ctx.fillRect(P_.x0 + j * cs, P_.y0 + i * cs, cs + 0.5, cs + 0.5);
      }
    }
    text(ctx, 'A', P_.x0 + P_.s / 2, P_.y0 + P_.s + 44, '28px SansM', rgba(P.paper, 0.6));
    text(ctx, 'B', P_.x0 - 30, P_.y0 + P_.s / 2, '28px SansM', rgba(P.paper, 0.6));
    for (const [pa, pb, o] of XPT) {
      const [x, y] = xpPos(pa, pb, P_);
      const c = o ? P.amber : P.ice;
      glow(ctx, x, y, 60, c, 0.35); dot(ctx, x, y, 30, c); text(ctx, String(o), x, y + 12, '34px SansB', rgba(P.bg), 'center');
      text(ctx, `(${pa},${pb})`, x, y + (pb ? -48 : 70), '22px SansM', rgba(P.paper, 0.5), 'center');
    }
  });
}
function xor(ctx, t) {
  // C2: the book
  const bookOut = eio(ramp(t, S('C3') - 0.1, S('C3') + 0.5));
  const bA = ap(t, S('C2') - 0.2, 0.6) * (1 - ap(t, S('C4') - 0.2, 0.4));
  withAlpha(ctx, bA, () => withXform(ctx, lerp(540, 200, bookOut), lerp(780, 520, bookOut), lerp(1, 0.36, bookOut), -0.04 * (1 - bookOut), () => {
    ctx.fillStyle = 'rgba(0,0,0,0.5)'; ctx.fillRect(-180, -250, 380, 520);
    ctx.fillStyle = rgba([238, 232, 216]); ctx.fillRect(170, -244, 20, 504);
    ctx.fillStyle = rgba([30, 44, 78]); ctx.fillRect(-190, -260, 370, 520);
    ctx.fillStyle = 'rgba(0,0,0,0.35)'; ctx.fillRect(-190, -260, 26, 520);
    spaced(ctx, 'PERCEPTRONS', 0, -120, '50px SerifB', rgba(P.paper), 4);
    text(ctx, 'an introduction to', 0, -60, '24px SansR', rgba(P.paper, 0.7)); text(ctx, 'computational geometry', 0, -30, '24px SansR', rgba(P.paper, 0.7));
    line(ctx, -110, 20, 110, 20, P.amber, 0.8, 3);
    text(ctx, 'Marvin Minsky', 0, 110, '30px SansM', rgba(P.paper, 0.9)); text(ctx, 'Seymour Papert', 0, 152, '30px SansM', rgba(P.paper, 0.9));
    text(ctx, 'MIT · 1969', 0, 226, '24px SansR', rgba(P.paper, 0.6));
  }));
  withAlpha(ctx, ap(t, charT('C2', '就叫'), 0.4) * (1 - bookOut), () => text(ctx, '《感知机》', 540, 1110, '48px SerifB', rgba(P.amber)));
  withAlpha(ctx, fade(t, S('C2') + 1.2, S('C3') + 0.2, 0.5, 0.4), () => {
    text(ctx, '冷知识', 540, 1190, '26px SansB', rgba(P.amber, 0.8));
    text(ctx, '明斯基和罗森布拉特，是同一所高中（布朗克斯科学高中）的校友', 540, 1236, '27px Kai', rgba(P.paper, 0.7));
  });
  // C3: truth table
  const tA = ap(t, S('C3') + 0.2, 0.5) * (1 - ap(t, S('C4') - 0.1, 0.4));
  withAlpha(ctx, tA, () => {
    withAlpha(ctx, ap(t, K('C3') - 0.2, 0.4), () => {
      text(ctx, '异或 XOR', 540, 640, '72px SerifH', rgba(P.paper));
      text(ctx, '两个输入不一样，才输出 1', 540, 700, '32px Kai', rgba(P.paper, 0.65));
    });
    const cols = [360, 540, 720]; const hdr = ['输入 A', '输入 B', '输出'];
    hdr.forEach((h, i) => text(ctx, h, cols[i], 790, '30px SansB', rgba(P.paper, 0.6)));
    line(ctx, 280, 810, 800, 810, P.paper, 0.3, 2);
    XPT.forEach(([a, b, o], r) => {
      const kk = ap(t, S('C3') + 0.5 + r * 0.25, 0.3); const y = 875 + r * 78;
      withAlpha(ctx, kk, () => {
        text(ctx, String(a), cols[0], y, '44px SerifB', rgba(P.paper)); text(ctx, String(b), cols[1], y, '44px SerifB', rgba(P.paper));
        chip(ctx, String(o), cols[2], y - 14, '38px SansB', rgba(P.bg), rgba(o ? P.amber : P.ice), 22, 56);
      });
    });
  });
  // C4: plot + failing lines
  const pA = ap(t, S('C4') - 0.1, 0.5) * (1 - ap(t, S('C5') + 0.1, 0.5));
  if (pA > 0) {
    xorPlot(ctx, t, pA);
    withAlpha(ctx, pA * ap(t, charT('C4', '对角'), 0.5), () => {
      const [ax, ay] = xpPos(0, 0), [bx, by] = xpPos(1, 1), [cx, cy] = xpPos(0, 1), [dx, dy] = xpPos(1, 0);
      line(ctx, ax, ay, bx, by, P.ice, 0.7, 3, [10, 10]); line(ctx, cx, cy, dx, dy, P.amber, 0.7, 3, [10, 10]);
    });
    const tA0 = CH('C4', 1), tA1 = E('C4') + 0.2; const n = 5;
    if (t > tA0) {
      const i = Math.min(n - 1, Math.floor((t - tA0) / ((tA1 - tA0) / n)));
      const lp = ((t - tA0) / ((tA1 - tA0) / n)) - i;
      const angs = [0.15, 1.2, -0.7, 0.62, 2.3], offs = [0, 40, -30, 70, -10];
      const ang = angs[i], off = offs[i];
      const cx = XP.x0 + XP.s / 2 + Math.cos(ang + Math.PI / 2) * off, cy = XP.y0 + XP.s / 2 + Math.sin(ang + Math.PI / 2) * off;
      const L2 = 420 * eo(clamp(lp * 3));
      withAlpha(ctx, pA, () => {
        ctx.save(); ctx.beginPath(); ctx.rect(XP.x0, XP.y0, XP.s, XP.s); ctx.clip();
        line(ctx, cx - Math.cos(ang) * L2, cy - Math.sin(ang) * L2, cx + Math.cos(ang) * L2, cy + Math.sin(ang) * L2, P.paper, 0.95, 5);
        ctx.restore();
        // which point is on the wrong side → red ring
        const wrong = XPT.filter(([a, b, o], j) => (j + i) % 3 === 0)[0] || XPT[i % 4];
        if (lp > 0.35) { const [x, y] = xpPos(wrong[0], wrong[1]); ring(ctx, x, y, 44, P.red, 0.95, 5); cross(ctx, XP.x0 + XP.s - 10, XP.y0 - 30, 30, P.red, 1, 7); }
        text(ctx, `第 ${i + 1} 次尝试`, XP.x0, XP.y0 - 22, '30px SansB', rgba(P.paper, 0.8), 'left');
      });
    }
    withAlpha(ctx, pA * ap(t, charT('C4', '都分不开'), 0.4), () => text(ctx, '一条直线，永远分不开', 540, 1150, '40px Kai', rgba(P.red)));
  }
  // C5: multi-layer net with question marks
  const nA = ap(t, S('C5') + 0.1, 0.5);
  withAlpha(ctx, nA, () => {
    text(ctx, '多层网络', 540, 600, '56px SerifH', rgba(P.paper));
    const net = layerNodes([320, 540, 760], [2, 3, 1], 820, 150);
    drawEdges(ctx, net, () => [P.paper, 0.35, 3]);
    net.forEach((ly, l) => ly.forEach((n) => { neuron(ctx, n.x, n.y, 36, 0.15, P.paper, 1, false); if (l === 1) text(ctx, '?', n.x, n.y + 16, '44px SerifH', rgba(P.amber), 'center'); }));
    withAlpha(ctx, ap(t, charT('C5', '没人知道'), 0.4), () => chip(ctx, '怎么训练？没人知道', 540, 1120, '38px SansB', rgba(P.paper), rgba(P.red, 0.85), 28, 66));
  });
  L.yearCard(ctx, t, S('C1') - 0.1, 1969, '寒冬将至', 1.8);
}
function xorCues() {
  cue(S('C1') - 0.1, 'whoosh', 0.7); cue(S('C2') - 0.2, 'paper'); cue(K('C3') - 0.2, 'pop', 0.6);
  const tA0 = CH('C4', 1), tA1 = E('C4') + 0.2; for (let i = 0; i < 5; i++) cue(tA0 + (i + 0.35) * (tA1 - tA0) / 5, 'error', 0.45);
  cue(charT('C5', '没人知道'), 'dud', 0.6);
}

// ================================================================== WINTER 1
function winter1(ctx, t) {
  const cA = ap(t, S('C6') - 0.2, 0.5) * (1 - ap(t, S('C7') - 0.2, 0.6));
  if (cA > 0) {
    hypeCurve(ctx, t, 150, 1180, 930, 800, 1, ap(t, S('C6') + 0.2, 1.8), cA);
    withAlpha(ctx, cA, () => text(ctx, '研究经费', 160, 785, '28px SansM', rgba(P.paper, 0.6), 'left'));
    withAlpha(ctx, cA * ap(t, S('C6') + 1.5, 0.4), () => text(ctx, '迅速枯竭', 840, 1120, '36px Kai', rgba(P.red), 'center'));
  }
  withAlpha(ctx, 1 - ap(t, S('C7') - 0.2, 0.8), () => stamp(ctx, '死刑', 540, 760, 180, t - K('C6'), -0.12, P.red, '第一次 · 1969'));
  // memorial
  const mA = ap(t, S('C7') + 0.1, 0.9);
  withAlpha(ctx, mA, () => {
    const dim = 1 - 0.75 * ramp(t, E('C7') - 0.5, E('C7') + 1.3);
    const fl = 0.85 + 0.15 * Math.sin(t * 13) * Math.sin(t * 7.3);
    glow(ctx, 540, 700, 160 * dim, P.amber, 0.5 * fl * dim);
    dot(ctx, 540, 700, 9, mix(P.amber, P.paper, 0.5), dim);
    text(ctx, '弗兰克·罗森布拉特', 540, 880, '64px SerifM', rgba(P.paper));
    text(ctx, '1928 — 1971', 540, 950, '44px SerifL', rgba(P.paper, 0.7));
    withAlpha(ctx, ap(t, charT('C7', '43岁'), 0.6), () => text(ctx, '43 岁生日那天', 540, 1030, '36px Kai', rgba(P.amber, 0.85)));
    withAlpha(ctx, ap(t, E('C7') - 0.3, 0.8), () => text(ctx, '他没能看到，这个想法后来改变了世界', 540, 1150, '30px Kai', rgba(P.paper, 0.55)));
  });
}
function winter1Cues() {
  cue(S('C6') + 0.2, 'fall', 0.8); cue(K('C6'), 'stamp', 1.2);
  SHAKES.push({ t: K('C6'), amp: 24 }); FLASHES.push({ t: K('C6'), c: P.red, a: 0.28 });
  cue(S('C7') + 0.1, 'bell', 0.5);
}

// ================================================================== 1982 · HOPFIELD
const HOPF = { no: 5, zh: '约翰·霍普菲尔德', en: 'John Hopfield', role: '物理学家 · 1933 –', note: '把神经网络看成一个会“下山”的物理系统。', w: 760, h: 360, compact: true };
const energy = (x) => 960 + 150 * Math.exp(-(((x - 330) / 95) ** 2)) + 110 * Math.exp(-(((x - 720) / 80) ** 2)) + 12 * Math.sin(x / 45) + 0.06 * (x - 540);
function energyCurve(ctx, x0, x1, a, sc = 1, ox = 0, oy = 0) {
  withAlpha(ctx, a, () => {
    ctx.beginPath();
    for (let x = x0; x <= x1; x += 6) { const y = energy(x); const X = ox + (x - 540) * sc + 540, Y = oy + (y - 1000) * sc + 1000; x === x0 ? ctx.moveTo(X, Y) : ctx.lineTo(X, Y); }
    ctx.strokeStyle = rgba(P.amber, 0.9); ctx.lineWidth = 5 * sc; ctx.stroke();
  });
}
function hopfield(ctx, t) {
  // D1: one warm light in the snow
  const d1 = ap(t, S('D1') - 0.1, 1.0) * (1 - ap(t, S('D2') + 1.4, 0.5));
  withAlpha(ctx, d1, () => {
    const fl = 0.9 + 0.1 * Math.sin(t * 9);
    glow(ctx, 540, 800, 200, P.amber, 0.45 * fl); neuron(ctx, 540, 800, 22, 0.9, P.amber);
    const r = rng(5);
    for (let i = 0; i < 6; i++) {
      const a = r() * TAU, d = 160 + r() * 140; const x = 540 + Math.cos(a) * d, y = 800 + Math.sin(a) * d;
      const k = ap(t, S('D1') + 0.4 + i * 0.25, 0.6);
      lineP(ctx, 540, 800, x, y, k, P.amber, 0.35, 2); neuron(ctx, x, y, 9, 0.4 * k, P.amber, k);
    }
  });
  const cA = ap(t, S('D2') + 1.55, 0.6);
  withAlpha(ctx, cA, () => card(ctx, HOPF, 540, 560, cA, -0.02, 0.86));
  // energy landscape + rolling ball
  const eA = ap(t, S('D2') + 1.8, 0.6);
  if (eA > 0) {
    energyCurve(ctx, 130, 950, eA);
    withAlpha(ctx, eA, () => {
      text(ctx, '能量', 120, 860, '28px SansM', rgba(P.paper, 0.6), 'left');
      arrow(ctx, 110, 1180, 110, 880, P.paper, 0.3, 2, 10);
      const tb = charT('D2', '能量') + 0.4;
      const u = clamp((t - tb) / 2.4);
      // damped roll from x=150 into valley at 330
      const x = 330 - 180 * Math.exp(-u * 3.2) * Math.cos(u * 9);
      const y = energy(x) - 22;
      glow(ctx, x, y, 50, P.paper, 0.4); dot(ctx, x, y, 20, P.paper);
      withAlpha(ctx, ap(t, tb + 2.0, 0.5), () => { text(ctx, '一段“记忆”', 330, 1175, '32px Kai', rgba(P.amber), 'center'); });
      text(ctx, '网络会自己滚进“能量最低”的山谷', 540, 1255, '28px SansM', rgba(P.paper, 0.55), 'center');
    });
  }
  withAlpha(ctx, ap(t, E('D2') + 0.1, 0.4), () => withXform(ctx, 760, 400, 1, -0.05, () => chip(ctx, '记住这个名字 · 42 年后见', 0, 0, '32px Kai', rgba(P.bg), rgba(P.amber), 22, 58)));
  L.yearCard(ctx, t, S('D2') - 0.1, 1982, '冬天里的一盏灯', 1.65);
}
function hopfieldCues() { cue(S('D1') - 0.1, 'fire', 0.5); cue(S('D2') - 0.1, 'whoosh', 0.6); cue(S('D2') + 1.55, 'paper'); cue(charT('D2', '能量') + 0.4, 'roll', 0.6); cue(E('D2') + 0.1, 'pop', 0.7); }

// ================================================================== 1986 · BACKPROP
const RHW = { no: 6, zh: '鲁梅尔哈特 · 辛顿 · 威廉姆斯', zhSize: 44, en: 'D. Rumelhart · G. Hinton · R. Williams', role: '《自然》 · 1986', note: '《通过反向传播误差来学习表征》', w: 800, h: 360, compact: true };
const BPN = layerNodes([200, 420, 640, 860], [2, 3, 3, 1], 820, 150);
const BPW = (() => { const r = rng(86); const w = {}; for (let l = 0; l < 3; l++) BPN[l].forEach((_, i) => BPN[l + 1].forEach((_, j) => { w[`${l}${i}${j}`] = [r() * 2 - 1, r() * 2 - 1]; })); return w; })();
function backprop(ctx, t) {
  // D4: paper card + term
  const d4 = fade(t, S('D4') + 1.6, S('D5') + 0.2, 0.5, 0.5);
  withAlpha(ctx, d4, () => {
    card(ctx, RHW, 540, 600, ramp(t, S('D4') + 1.6, S('D4') + 2.2), -0.015, 0.92);
    const k = ap(t, K('D4') - 0.1, 0.5);
    withAlpha(ctx, k, () => {
      glow(ctx, 540, 920, 260, P.amber, 0.16);
      text(ctx, '反向传播', 540, 960 + (1 - k) * 30, '100px SerifH', rgba(P.amber), 'center');
      text(ctx, 'Backpropagation', 540, 1020, '36px SansR', rgba(P.paper, 0.7), 'center');
    });
    para(ctx, '注：类似的方法更早已由 Linnainmaa（1970）、Werbos（1974）等人提出，这篇论文让它真正流行起来。', 120, 1180, 840, '24px SansR', rgba(P.paper, 0.5), 34);
  });
  // D5/D6: forward then backward
  const nA = ap(t, S('D5') - 0.1, 0.5) * (1 - ap(t, S('D7') - 0.1, 0.5));
  if (nA > 0) {
    const tF = S('D5') + 0.3, tB = charT('D5', '误差'), tU = S('D6');
    const fP = clamp((t - tF) / Math.max(0.8, tB - tF - 0.2));   // forward progress 0..1 over 3 layers
    const bP = clamp((t - tB) / Math.max(0.8, (E('D5') + 0.2) - tB)); // backward progress
    const uP = clamp((t - tU) / (E('D6') - tU));
    withAlpha(ctx, nA, () => {
      for (let l = 0; l < 3; l++) BPN[l].forEach((n, i) => BPN[l + 1].forEach((m, j) => {
        const [w0, w1] = BPW[`${l}${i}${j}`];
        const wv = lerp(w0, w0 + w1 * 0.6, eio(uP));
        const lw = 1.5 + Math.abs(wv) * 6;
        const backHit = bP * 3 > (2 - l) && bP < 1.02 && t > tB;
        line(ctx, n.x, n.y, m.x, m.y, backHit && t < tU ? P.red : (wv >= 0 ? P.amber : P.ice), 0.35 + 0.2 * Math.abs(wv), lw);
        const fl = fP * 3 - l; if (fl > 0 && fl < 1 && t < tB) pulse(ctx, n.x, n.y, m.x, m.y, fl, P.amber, 1, 8);
        const bl = bP * 3 - (2 - l); if (bl > 0 && bl < 1 && t < tU) pulse(ctx, m.x, m.y, n.x, n.y, bl, P.red, 1, 8);
        if (t > tU && hash(l * 31 + i * 7 + j) < 0.45) {
          const mk = ap(t, tU + hash(l + i + j) * 1.5, 0.3) * (1 - ap(t, E('D6') - 0.2, 0.3));
          withAlpha(ctx, mk, () => text(ctx, w1 > 0 ? '+' : '−', (n.x + m.x) / 2, (n.y + m.y) / 2 - 8, '30px SansB', rgba(w1 > 0 ? P.amber : P.ice), 'center'));
        }
      }));
      BPN.forEach((ly, l) => ly.forEach((n) => {
        const fwd = t < tB ? clamp(fP * 3 - l + 1) : 0.4;
        const back = t > tB && t < tU ? clamp(bP * 3 - (3 - l) + 1) * (1 - clamp(bP * 3 - (3 - l))) : 0;
        neuron(ctx, n.x, n.y, 32, Math.max(fwd * 0.8, back), back > 0.1 ? P.red : P.amber);
      }));
      text(ctx, 'A = 1', 110, 760, '28px SansM', rgba(P.paper, 0.7), 'center'); text(ctx, 'B = 0', 110, 910, '28px SansM', rgba(P.paper, 0.7), 'center');
      // readout
      const outs = [0.21, 0.47, 0.78, 0.96];
      const o = t < tU ? 0.21 : outs[Math.min(3, Math.floor(uP * 4))];
      const showO = fP >= 1 || t > tB;
      withAlpha(ctx, showO ? 1 : 0, () => {
        text(ctx, `输出 ${o.toFixed(2)}`, 860, 690, '32px SansB', rgba(P.paper), 'center');
        text(ctx, '目标 1', 860, 650, '26px SansM', rgba(P.paper, 0.55), 'center');
        const err = 1 - o;
        withAlpha(ctx, t > tB - 0.3 ? 1 : 0, () => chip(ctx, `误差 ${err.toFixed(2)}`, 860, 960, '30px SansB', rgba(P.paper), rgba(err > 0.1 ? P.red : P.green, 0.85), 18, 52));
      });
      const ph = t < tB ? ['信号：从前往后', P.amber] : t < tU ? ['误差：从后往前，层层追责', P.red] : ['每根连线，改一点点', P.paper];
      text(ctx, ph[0], 540, 580, '44px SerifB', rgba(ph[1]), 'center');
      if (t > tB && t < tU) [0, 1, 2].forEach((l) => withAlpha(ctx, clamp(bP * 3 - (2 - l)), () => text(ctx, '追责', BPN[l + 1][0].x, BPN[l + 1][0].y - 60, '26px Kai', rgba(P.red), 'center')));
    });
  }
  // D7: XOR solved
  const xA = ap(t, S('D7') - 0.1, 0.6);
  if (xA > 0) {
    const kk = lerp(1, 14, ap(t, S('D7'), 2.6));
    const heat = (u, v) => { const h1 = sig(kk * (u + v - 0.5)), h2 = sig(kk * (u + v - 1.5)); return sig(kk * (h1 - h2 - 0.5)); };
    xorPlot(ctx, t, xA, XP, heat);
    withAlpha(ctx, ap(t, charT('D7', '迎刃'), 0.4), () => { check(ctx, 860, 600, 70, P.amber, 1, 10); text(ctx, '迎刃而解', 540, 1150, '48px SerifH', rgba(P.amber)); });
  }
  L.yearCard(ctx, t, S('D4') - 0.1, 1986, '误差，从后往前传', 1.7);
}
function backpropCues() {
  cue(S('D4') - 0.1, 'whoosh', 0.6); cue(S('D4') + 1.6, 'paper'); cue(K('D4') - 0.1, 'fire', 0.7);
  cue(S('D5') + 0.3, 'sweepUp', 0.6); cue(charT('D5', '误差'), 'sweepDown', 0.7); cue(S('D6'), 'tick', 0.4); cue(S('D6') + 0.8, 'tick', 0.4); cue(S('D6') + 1.6, 'tick', 0.4);
  cue(charT('D7', '迎刃'), 'ding', 0.9);
}

// ================================================================== 1989 · LECUN
const LECUN = { no: 7, zh: '杨立昆', en: 'Yann LeCun', role: '贝尔实验室 · 1960 –', note: '用卷积神经网络，教机器认手写数字。', w: 760, h: 340, compact: true };
const DIGIT = (() => {
  const c = createCanvas(140, 140), g = c.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, 140, 140);
  g.fillStyle = '#fff'; g.font = '150px Kai'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('7', 70, 78);
  const d = g.getImageData(0, 0, 140, 140).data; const N = 14; const px = [];
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { let s = 0; for (let a = 0; a < 10; a++) for (let b = 0; b < 10; b++) s += d[((i * 10 + a) * 140 + j * 10 + b) * 4]; px.push(s / 25500); }
  const fm = []; const k = [[-1, -1, -1], [2, 2, 2], [-1, -1, -1]];
  for (let i = 0; i < 12; i++) for (let j = 0; j < 12; j++) { let s = 0; for (let a = 0; a < 3; a++) for (let b = 0; b < 3; b++) s += k[a][b] * px[(i + a) * N + j + b]; fm.push(clamp(s / 2.5)); }
  return { px, fm, N };
});
let _DIG = null;
function lecun(ctx, t) {
  if (!_DIG) _DIG = DIGIT();
  const cA = ap(t, S('D8') + 1.55, 0.6) * (1 - ap(t, S('D9') - 0.1, 0.5));
  withAlpha(ctx, cA, () => {
    card(ctx, LECUN, 540, 540, cA, -0.02, 0.8);
    const { px, fm, N } = _DIG;
    const gx = 110, gy = 760, cs = 22;
    for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) { ctx.fillStyle = rgba(mix(P.bg2, P.paper, px[i * N + j] * 0.95)); ctx.fillRect(gx + j * cs, gy + i * cs, cs - 1, cs - 1); }
    text(ctx, '手写数字', gx + 154, gy - 18, '26px SansM', rgba(P.paper, 0.6));
    const p = clamp((t - (S('D8') + 2.3)) / (E('D8') - S('D8') - 2.4));
    const pos = Math.min(143, Math.floor(p * 144));
    const ki = Math.floor(pos / 12), kj = pos % 12;
    ctx.strokeStyle = rgba(P.amber); ctx.lineWidth = 4; ctx.strokeRect(gx + kj * cs - 2, gy + ki * cs - 2, cs * 3 + 3, cs * 3 + 3);
    const fx = 520, fy = 800, fs = 18;
    arrow(ctx, 432, 914, 500, 914, P.paper, 0.5, 3, 12);
    for (let q = 0; q < 144; q++) { const i = Math.floor(q / 12), j = q % 12; const on = q <= pos; ctx.fillStyle = rgba(on ? mix(P.bg2, P.amber, fm[q]) : P.bg2, on ? 1 : 0.6); ctx.fillRect(fx + j * fs, fy + i * fs, fs - 1, fs - 1); }
    text(ctx, '卷积：提取笔画', fx + 108, gy - 18, '26px SansM', rgba(P.paper, 0.6));
    line(ctx, gx + kj * cs + cs * 1.5, gy + ki * cs + cs * 1.5, fx + kj * fs + fs / 2, fy + ki * fs + fs / 2, P.amber, 0.35, 2);
    // outputs
    arrow(ctx, 748, 914, 790, 914, P.paper, 0.5, 3, 12);
    for (let d = 0; d < 10; d++) {
      const y = 762 + d * 31; const win = d === 7; const conf = win ? p : 0.05 + 0.1 * hash(d) * p;
      text(ctx, String(d), 815, y + 10, '24px SansB', rgba(win && p > 0.9 ? P.amber : P.paper, 0.85), 'center');
      ctx.fillStyle = rgba(win ? P.amber : P.grey, win ? 1 : 0.5); ctx.fillRect(835, y - 8, 110 * conf, 20);
    }
  });
  // D9: the cheque
  const qA = ap(t, S('D9') - 0.1, 0.6);
  withAlpha(ctx, qA, () => {
    withXform(ctx, 540, 820 + (1 - qA) * 60, 1, -0.02, () => {
      paperRect(ctx, -420, -200, 840, 400, 8, [214, 228, 212]);
      text(ctx, 'PAY TO THE ORDER OF', -380, -110, '22px SansM', rgba(P.ink, 0.6), 'left'); line(ctx, -140, -108, 380, -108, P.ink, 0.5, 2);
      text(ctx, 'Bell Bakery', -100, -120, '40px Kai', rgba([30, 50, 110]), 'left');
      ctx.strokeStyle = rgba(P.ink, 0.6); ctx.lineWidth = 2; ctx.strokeRect(80, -50, 300, 80);
      text(ctx, '$', 100, 6, '40px SerifB', rgba(P.ink, 0.7), 'left');
      const digits = '1250.00';
      let x = 140;
      [...digits].forEach((d, i) => {
        ctx.font = '54px Kai'; const w = ctx.measureText(d).width; text(ctx, d, x, 12, '54px Kai', rgba([30, 50, 110]), 'left');
        const kk = ap(t, S('D9') + 0.6 + i * 0.28, 0.2);
        if (d !== '.' && kk > 0) { ctx.strokeStyle = rgba(P.amberDeep, kk); ctx.lineWidth = 3; ctx.strokeRect(x - 3, -36, w + 6, 58); text(ctx, d, x + w / 2, -44, '20px SansB', rgba(P.amberDeep, kk), 'center'); }
        x += w + 2;
      });
      text(ctx, 'one thousand two hundred fifty', -380, 100, '34px Kai', rgba([30, 50, 110]), 'left'); line(ctx, -380, 110, 380, 110, P.ink, 0.4, 2);
      text(ctx, '⑆ 0210 0002 1 ⑆  4417 0042', -380, 170, '24px SansR', rgba(P.ink, 0.5), 'left');
    });
    const sk = ap(t, charT('D9', '一成'), 0.6);
    withAlpha(ctx, sk, () => {
      const bx = 160, by = 1110, bw = 760;
      ctx.fillStyle = rgba(P.paper, 0.12); roundRect(ctx, bx, by, bw, 26, 13); ctx.fill();
      ctx.fillStyle = rgba(P.amber); roundRect(ctx, bx, by, bw * 0.12 * sk, 26, 13); ctx.fill();
      text(ctx, '90 年代末：美国 10% 以上的支票，由它来读', 540, 1190, '32px SansB', rgba(P.paper, 0.9));
    });
  });
  L.yearCard(ctx, t, S('D8') - 0.1, 1989, '机器认字', 1.6);
}
function lecunCues() { cue(S('D8') - 0.1, 'whoosh', 0.6); cue(S('D8') + 1.55, 'paper'); cue(S('D8') + 2.3, 'scan', 0.6); cue(S('D9') - 0.1, 'paper'); for (let i = 0; i < 6; i++) cue(S('D9') + 0.6 + i * 0.28, 'tick', 0.35); cue(charT('D9', '一成'), 'ding', 0.6); }

// ================================================================== WINTER 2
function winter2(ctx, t) {
  // E2: vanishing error through a deep chain
  const eA = ap(t, S('E2') - 0.1, 0.5) * (1 - ap(t, S('E3') - 0.1, 0.5));
  withAlpha(ctx, eA, () => {
    const xs = Array.from({ length: 8 }, (_, i) => 140 + i * 114);
    const net = layerNodes(xs, [3, 3, 3, 3, 3, 3, 3, 3], 720, 100);
    drawEdges(ctx, net, () => [P.paper, 0.18, 2]);
    const tb = charT('E2', '误差');
    const pos = 7 - clamp((t - tb) / 2.0) * 7;     // wave front layer index
    net.forEach((ly, l) => ly.forEach((n) => {
      const amp = Math.exp(-(7 - l) * 0.6);
      const hit = t > tb && pos <= l ? amp * Math.exp(-(l - pos) * 1.5) : 0;
      neuron(ctx, n.x, n.y, 20, clamp(hit * 1.3), P.red);
    }));
    text(ctx, '网络一深……', 540, 560, '44px SerifB', rgba(P.paper), 'center');
    withAlpha(ctx, ap(t, charT('E2', '就没了'), 0.4), () => {
      chip(ctx, '误差传到前面，几乎为零：梯度消失', 540, 900, '30px SansB', rgba(P.paper), rgba(P.iceDeep, 0.9), 24, 58);
    });
    // data / compute badges
    const b1 = ap(t, charT('E2', '数据'), 0.4), b2 = ap(t, charT('E2', '电脑'), 0.4);
    withAlpha(ctx, b1, () => {
      ctx.fillStyle = rgba(P.paper, 0.06); roundRect(ctx, 120, 1000, 400, 210, 16); ctx.fill();
      for (let i = 0; i < 5; i++) { ctx.fillStyle = rgba(mix(P.iceDeep, P.paper, hash(i) * 0.5), 0.9); ctx.fillRect(170 + i * 22, 1040 - i * 6, 90, 70); ctx.strokeStyle = rgba(P.bg); ctx.strokeRect(170 + i * 22, 1040 - i * 6, 90, 70); }
      text(ctx, '数据太少', 320, 1180, '40px SansB', rgba(P.paper), 'center');
    });
    withAlpha(ctx, b2, () => {
      ctx.fillStyle = rgba(P.paper, 0.06); roundRect(ctx, 560, 1000, 400, 210, 16); ctx.fill();
      ctx.fillStyle = rgba(P.paper, 0.15); roundRect(ctx, 610, 1060, 300, 24, 12); ctx.fill();
      const pr = 0.02 + 0.02 * ramp(t, charT('E2', '电脑'), E('E2') + 1);
      ctx.fillStyle = rgba(P.ice); roundRect(ctx, 610, 1060, 300 * pr, 24, 12); ctx.fill();
      text(ctx, `训练中… ${Math.round(pr * 100)}%`, 760, 1120, '26px SansM', rgba(P.paper, 0.6), 'center');
      text(ctx, '电脑太慢', 760, 1180, '40px SansB', rgba(P.paper), 'center');
    });
  });
  // E3: SVM + migration
  const sA = ap(t, S('E3') - 0.1, 0.5) * (1 - ap(t, S('E4') - 0.1, 0.5));
  withAlpha(ctx, sA, () => {
    const r = rng(95);
    const ox = 540, oy = 720;
    const ang = -0.6; const nx = Math.cos(ang + Math.PI / 2), ny = Math.sin(ang + Math.PI / 2);
    for (let i = 0; i < 26; i++) {
      const side = i % 2 ? 1 : -1; const along = (r() - 0.5) * 440, off = side * (60 + r() * 120);
      const x = ox + Math.cos(ang) * along + nx * off, y = oy + Math.sin(ang) * along + ny * off;
      dot(ctx, x, y, 11, side > 0 ? P.amber : P.ice, 0.95);
      if (i < 4) ring(ctx, ox + Math.cos(ang) * (i * 120 - 180) + nx * side * 60, oy + Math.sin(ang) * (i * 120 - 180) + ny * side * 60, 18, P.paper, 0.8, 3);
    }
    const Lx = Math.cos(ang) * 330, Ly = Math.sin(ang) * 330;
    line(ctx, ox - Lx, oy - Ly, ox + Lx, oy + Ly, P.paper, 0.95, 5);
    line(ctx, ox - Lx + nx * 60, oy - Ly + ny * 60, ox + Lx + nx * 60, oy + Ly + ny * 60, P.paper, 0.4, 3, [10, 10]);
    line(ctx, ox - Lx - nx * 60, oy - Ly - ny * 60, ox + Lx - nx * 60, oy + Ly - ny * 60, P.paper, 0.4, 3, [10, 10]);
    withAlpha(ctx, ap(t, K('E3') - 0.2, 0.4), () => { text(ctx, '支持向量机 SVM', 540, 990, '60px SerifH', rgba(P.paper)); text(ctx, '数学漂亮 · 结果稳定 · 不用调玄学参数', 540, 1040, '28px SansM', rgba(P.paper, 0.6)); });
    // migration of researchers
    const mk = ramp(t, charT('E3', '学术界'), E('E3') + 0.3);
    withAlpha(ctx, ap(t, charT('E3', '学术界') - 0.3, 0.3), () => {
      text(ctx, '神经网络', 270, 1240, '30px SansB', rgba(P.paper, 0.7 - 0.4 * mk), 'center');
      text(ctx, 'SVM', 810, 1240, '30px SansB', rgba(P.paper, 0.9), 'center');
      const rr = rng(3);
      for (let i = 0; i < 34; i++) {
        const x0 = 170 + rr() * 200, y0 = 1120 + rr() * 80, x1 = 710 + rr() * 200, y1 = 1120 + rr() * 80;
        const m = eio(clamp(mk * 1.6 - (i / 34) * 0.6));
        dot(ctx, lerp(x0, x1, m), lerp(y0, y1, m) - Math.sin(m * Math.PI) * 50, 7, i < 3 ? P.amber : P.paper, 0.85);
      }
    });
  });
  // E4: rejection letter
  const rA = ap(t, S('E4') - 0.1, 0.5);
  withAlpha(ctx, rA * (1 - 0.6 * ap(t, S('E5'), 0.4)), () => withXform(ctx, 540, 800 + (1 - rA) * 60, 1, 0.02, () => {
    paperRect(ctx, -390, -280, 780, 560, 6, [236, 231, 220]);
    text(ctx, '审稿意见', -340, -200, '44px SerifB', rgba(P.ink), 'left');
    text(ctx, 'REVIEWER COMMENTS', 340, -200, '22px SansM', rgba(P.ink, 0.5), 'right');
    line(ctx, -340, -175, 340, -175, P.ink, 0.4, 2);
    const r = rng(4);
    for (let i = 0; i < 7; i++) { const y = -130 + i * 50; if (i === 2) continue; ctx.fillStyle = rgba(P.ink, 0.18); roundRect(ctx, -340, y - 14, 600 + r() * 80, 16, 8); ctx.fill(); }
    const hk = ap(t, charT('E4', '神经网络'), 0.5);
    ctx.fillStyle = rgba(P.amber, 0.7 * hk); ctx.fillRect(-344, -52, 360 * hk, 42);
    text(ctx, '……本文使用了“神经网络”……', -340, -20, '32px Kai', rgba(P.ink, 0.85), 'left');
    stamp(ctx, '拒稿', 170, 160, 100, t - charT('E4', '被拒'), -0.14, P.red, 'REJECT');
  }));
  withAlpha(ctx, ap(t, S('E4') + 0.3, 0.5) * (1 - ap(t, S('E5'), 0.3)), () => text(ctx, '* 据研究者回忆，那些年这类论文很难发表', 540, 1240, '24px SansR', rgba(P.paper, 0.45)));
  stamp(ctx, '死刑', 540, 820, 180, t - K('E5'), 0.1, P.red, '第二次 · 1990s');
  L.yearCard(ctx, t, S('E1') - 0.1, '1990s', '好景不长', 1.55);
}
function winter2Cues() {
  cue(S('E1') - 0.1, 'whoosh', 0.6); cue(charT('E2', '误差'), 'sweepDown', 0.5); cue(charT('E2', '数据'), 'pop', 0.5); cue(charT('E2', '电脑'), 'pop', 0.5);
  cue(S('E3') - 0.1, 'whoosh', 0.4); cue(charT('E3', '学术界'), 'flock', 0.5);
  cue(S('E4') - 0.1, 'paper'); cue(charT('E4', '被拒'), 'stamp', 0.6);
  cue(K('E5'), 'stamp', 1.2); SHAKES.push({ t: K('E5'), amp: 24 }); FLASHES.push({ t: K('E5'), c: P.red, a: 0.28 });
}

// ================================================================== 2004 · THREE LIGHTS
const LIGHTS = [
  { city: '多伦多', zh: '辛顿', en: 'Geoffrey Hinton', x: 290, y: 760 },
  { city: '纽约', zh: '杨立昆', en: 'Yann LeCun', x: 560, y: 1010 },
  { city: '蒙特利尔', zh: '本吉奥', en: 'Yoshua Bengio', x: 800, y: 680 },
];
const SPROUT = (() => { const r = rng(2006); return Array.from({ length: 70 }, (_, i) => { const src = LIGHTS[i % 3]; const a = r() * TAU, d = 60 + r() * 330; return { x: src.x + Math.cos(a) * d, y: src.y + Math.sin(a) * d * 0.8, src: i % 3, d, ph: r() }; }).filter((n) => n.y > 450 && n.y < 1250 && n.x > 70 && n.x < 1010); })();
function lights(ctx, t) {
  const grow = ap(t, CH('E8', 1), 2.8);
  // sprouting deep network
  if (grow > 0) {
    SPROUT.forEach((n, i) => {
      const k = clamp(grow * 1.6 - n.d / 420);
      if (k <= 0) return;
      const s = LIGHTS[n.src];
      lineP(ctx, s.x, s.y, n.x, n.y, k, P.amber, 0.22, 1.5);
      const nb = SPROUT[(i + 3) % SPROUT.length]; if (k > 0.8) line(ctx, n.x, n.y, nb.x, nb.y, P.amber, 0.08 * k, 1);
      neuron(ctx, n.x, n.y, 8, k * Math.pow(Math.max(0, Math.sin(t * 3 + n.ph * 20)), 3), P.amber, k);
    });
  }
  // connecting lines
  const lk = ap(t, S('E7'), 1.2);
  for (let i = 0; i < 3; i++) { const a = LIGHTS[i], b = LIGHTS[(i + 1) % 3]; lineP(ctx, a.x, a.y, b.x, b.y, lk, P.amber, 0.35, 2); }
  LIGHTS.forEach((Lg, i) => {
    const k = ap(t, K('E6', i) - 0.1, 0.8);
    if (k <= 0) return;
    const fl = 0.85 + 0.15 * Math.sin(t * (7 + i) + i * 2) * Math.sin(t * 3.1 + i);
    glow(ctx, Lg.x, Lg.y, (130 + 60 * grow) * k, P.amber, 0.55 * fl * k);
    neuron(ctx, Lg.x, Lg.y, 18, k, P.amber);
    withAlpha(ctx, k, () => {
      text(ctx, Lg.city, Lg.x, Lg.y - 52, '28px SansM', rgba(P.paper, 0.6));
      text(ctx, Lg.zh, Lg.x, Lg.y + 82, '46px SerifB', rgba(P.paper));
      text(ctx, Lg.en, Lg.x, Lg.y + 118, '24px SansR', rgba(P.paper, 0.6));
    });
  });
  withAlpha(ctx, ap(t, S('E7') + 0.3, 0.6) * (1 - ap(t, K('E8') - 0.4, 0.4)), () => {
    text(ctx, 'CIFAR · 加拿大高等研究院', 540, 500, '32px SansM', rgba(P.amber, 0.85));
    text(ctx, '一笔不大的资助，一个很小的圈子', 540, 548, '28px Kai', rgba(P.paper, 0.6));
  });
  const dk = ap(t, K('E8') - 0.15, 0.6);
  withAlpha(ctx, dk, () => {
    glow(ctx, 540, 470, 300, P.amber, 0.22);
    text(ctx, '深度学习', 540, 520 + (1 - dk) * 30, '120px SerifH', rgba(P.amber), 'center');
    text(ctx, 'Deep Learning', 540, 580, '36px SansR', rgba(P.paper, 0.75), 'center');
  });
}
function lightsCues() { [0, 1, 2].forEach((i) => cue(K('E6', i) - 0.1, 'fire', 0.6)); cue(CH('E8', 1), 'swell', 0.7); cue(K('E8') - 0.15, 'boom', 0.6); }

// ================================================================== 2009 · IMAGENET
const LI = { no: 8, zh: '李飞飞', en: 'Fei-Fei Li', role: '计算机科学家 · ImageNet 发起人', note: '想让机器学会“看”，先得给它海量看得懂的图片。', w: 760, h: 340, compact: true };
const MOSAIC = (() => { const r = rng(2009); const cols = 34, rows = 18; const tiles = []; const pal = [[150, 120, 90], [90, 110, 130], [120, 140, 90], [170, 150, 120], [70, 80, 100], [180, 110, 80], [110, 100, 140], [200, 180, 150]];
  for (let i = 0; i < rows; i++) for (let j = 0; j < cols; j++) { const a = pal[Math.floor(r() * pal.length)], b = pal[Math.floor(r() * pal.length)]; tiles.push({ i, j, a, b, o: r(), sh: Math.floor(r() * 3) }); }
  return { cols, rows, tiles }; })();
function imagenet(ctx, t) {
  const cA = ap(t, S('F2') - 0.2, 0.6);
  withAlpha(ctx, cA, () => card(ctx, LI, 540, 520, cA, -0.02, 0.78));
  const mA = ap(t, S('F2') + 0.2, 0.5);
  if (mA > 0) {
    const fill = ramp(t, S('F2') + 0.3, K('F2'));
    const x0 = 100, y0 = 690, cs = 26;
    withAlpha(ctx, mA, () => {
      for (const tl of MOSAIC.tiles) {
        const k = clamp((fill - tl.o * 0.92) * 12);
        if (k <= 0) continue;
        const x = x0 + tl.j * cs, y = y0 + tl.i * cs;
        ctx.fillStyle = rgba(mix(tl.a, tl.b, 0.5), 0.9 * k); ctx.fillRect(x, y, cs - 2, cs - 2);
        ctx.fillStyle = rgba(tl.b, 0.8 * k);
        if (tl.sh === 0) { ctx.beginPath(); ctx.arc(x + cs / 2, y + cs / 2, 6, 0, TAU); ctx.fill(); }
        else if (tl.sh === 1) ctx.fillRect(x + 6, y + cs - 12, cs - 14, 8);
        else { ctx.beginPath(); ctx.moveTo(x + 4, y + cs - 5); ctx.lineTo(x + cs / 2, y + 6); ctx.lineTo(x + cs - 6, y + cs - 5); ctx.fill(); }
      }
    });
    const stats = [['167', '个国家', charT('F2', '167')], ['近 5 万', '人参与标注', charT('F2', '近5万')], ['1400 万+', '张图片', charT('F2', '1400')]];
    stats.forEach(([n, l, tt], i) => withAlpha(ctx, ap(t, tt - 0.1, 0.4), () => {
      const x = 220 + i * 320;
      text(ctx, n, x, 1225, '50px SerifH', rgba(P.amber)); text(ctx, l, x, 1268, '26px SansM', rgba(P.paper, 0.7));
    }));
    const nk = ap(t, K('F2') - 0.1, 0.5);
    withAlpha(ctx, nk, () => {
      ctx.fillStyle = rgba(P.bg, 0.82); roundRect(ctx, 280, 860, 520, 140, 16); ctx.fill();
      ctx.strokeStyle = rgba(P.amber, 0.8); ctx.lineWidth = 3; roundRect(ctx, 280, 860, 520, 140, 16); ctx.stroke();
      text(ctx, 'ImageNet', 540, 950, '84px SerifH', rgba(P.paper)); text(ctx, '2009', 540, 990, '24px SansM', rgba(P.amber));
    });
  }
  L.yearCard(ctx, t, S('F1') - 0.1, 2012, '转折', 1.9);
}
function imagenetCues() { cue(S('F1') - 0.1, 'whoosh', 0.8); cue(S('F2') - 0.2, 'paper'); cue(S('F2') + 0.3, 'shimmer', 0.6); cue(K('F2') - 0.1, 'boom', 0.5); }

// ================================================================== 2012 · ALEXNET
const ALEX = { no: 9, zh: '亚历克斯 · 伊利亚 · 辛顿', zhSize: 44, en: 'Alex Krizhevsky · Ilya Sutskever · Geoffrey Hinton', role: '多伦多大学 · 2012', note: '他们的网络后来被叫作 AlexNet。', w: 820, h: 340, compact: true };
function gpu(ctx, x, y, w, h, t, on) {
  ctx.fillStyle = rgba([40, 40, 44]); roundRect(ctx, x, y, w, h, 8); ctx.fill();
  ctx.strokeStyle = rgba(P.amber, 0.3 + 0.6 * on); ctx.lineWidth = 3; roundRect(ctx, x, y, w, h, 8); ctx.stroke();
  for (let f = 0; f < 2; f++) {
    const cx = x + w * (0.3 + f * 0.4), cy = y + h / 2, r = h * 0.36;
    ring(ctx, cx, cy, r, P.paper, 0.5, 2);
    for (let b = 0; b < 7; b++) { const a = t * 18 * on + b * TAU / 7; line(ctx, cx, cy, cx + Math.cos(a) * r * 0.9, cy + Math.sin(a) * r * 0.9, P.paper, 0.45, 3); }
  }
  ctx.fillStyle = rgba(P.amber, 0.25 + 0.7 * on); ctx.fillRect(x + 10, y + h - 8, w - 20, 4);
}
function alexnet(ctx, t) {
  // F3: team + architecture
  const aA = ap(t, S('F3') - 0.1, 0.5) * (1 - ap(t, S('F4') - 0.1, 0.5));
  withAlpha(ctx, aA, () => {
    card(ctx, ALEX, 540, 540, aA, -0.015, 0.84);
    const kb = ramp(t, charT('F3', '交出了') - 0.4, E('F3'));
    const blocks = [[150, 210, 26], [250, 170, 40], [345, 130, 56], [440, 130, 56], [535, 110, 50]];
    blocks.forEach(([x, h, d], i) => {
      const k = clamp(kb * 8 - i);
      if (k <= 0) return;
      withAlpha(ctx, k, () => {
        const y = 940 - h / 2; const w = 34;
        ctx.fillStyle = rgba(mix(P.bg2, P.amber, 0.35)); ctx.fillRect(x, y, w, h);
        ctx.fillStyle = rgba(mix(P.bg2, P.amber, 0.55)); ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + d, y - d * 0.6); ctx.lineTo(x + d + w, y - d * 0.6); ctx.lineTo(x + w, y); ctx.fill();
        ctx.fillStyle = rgba(mix(P.bg2, P.amber, 0.22)); ctx.beginPath(); ctx.moveTo(x + w, y); ctx.lineTo(x + w + d, y - d * 0.6); ctx.lineTo(x + w + d, y + h - d * 0.6); ctx.lineTo(x + w, y + h); ctx.fill();
      });
    });
    [650, 730, 810].forEach((x, i) => { const k = clamp(kb * 8 - 5 - i); withAlpha(ctx, k, () => { ctx.fillStyle = rgba(P.amber, 0.8); ctx.fillRect(x, 940 - (i === 2 ? 50 : 120), 26, i === 2 ? 100 : 240); }); });
    withAlpha(ctx, clamp(kb * 8 - 7), () => {
      text(ctx, '卷积 × 5', 330, 1090, '28px SansM', rgba(P.paper, 0.65)); text(ctx, '全连接 × 3', 740, 1090, '28px SansM', rgba(P.paper, 0.65));
      text(ctx, 'AlexNet · 8 层 · 约 6000 万个参数', 540, 1180, '36px SansB', rgba(P.paper));
    });
  });
  // F4: bedroom with two gaming GPUs
  const bA = ap(t, S('F4') - 0.1, 0.5) * (1 - ap(t, S('F5') - 0.1, 0.5));
  withAlpha(ctx, bA, () => {
    // window with moon
    ctx.strokeStyle = rgba(P.paper, 0.5); ctx.lineWidth = 4; ctx.strokeRect(150, 560, 260, 220); line(ctx, 280, 560, 280, 780, P.paper, 0.5, 4); line(ctx, 150, 670, 410, 670, P.paper, 0.5, 4);
    dot(ctx, 350, 610, 22, P.paper, 0.8); dot(ctx, 360, 602, 20, P.bg, 1);
    line(ctx, 110, 1090, 970, 1090, P.paper, 0.5, 5); line(ctx, 160, 1090, 160, 1250, P.paper, 0.4, 5); line(ctx, 920, 1090, 920, 1250, P.paper, 0.4, 5);
    // tower
    const on = ap(t, S('F4') + 0.3, 0.6);
    ctx.fillStyle = rgba([26, 26, 30]); roundRect(ctx, 520, 640, 340, 450, 14); ctx.fill();
    ctx.strokeStyle = rgba(P.paper, 0.45); ctx.lineWidth = 3; roundRect(ctx, 520, 640, 340, 450, 14); ctx.stroke();
    glow(ctx, 690, 880, 260, P.amber, 0.18 * on);
    gpu(ctx, 550, 790, 280, 86, t, on); gpu(ctx, 550, 910, 280, 86, t, on);
    for (let i = 0; i < 3; i++) { ctx.strokeStyle = rgba(P.amber, 0.25 * on); ctx.lineWidth = 3; ctx.beginPath(); for (let y = 0; y < 90; y += 4) { const x = 620 + i * 70 + Math.sin(y / 10 + t * 6 + i) * 8; y ? ctx.lineTo(x, 620 - y) : ctx.moveTo(x, 620 - y); } ctx.stroke(); }
    withAlpha(ctx, ap(t, K('F4') - 0.2, 0.4), () => chip(ctx, 'GTX 580 × 2 · 打游戏用的显卡', 540, 1160, '34px SansB', rgba(P.bg), rgba(P.amber), 24, 62));
    withAlpha(ctx, ap(t, charT('F4', '父母家'), 0.5), () => text(ctx, '据说：父母家的卧室', 280, 860, '34px Kai', rgba(P.paper, 0.75), 'center'));
  });
  // F5/F6: error-rate bars
  const cA = ap(t, S('F5') - 0.1, 0.5);
  if (cA > 0) withAlpha(ctx, cA, () => {
    text(ctx, 'ImageNet 图像识别错误率', 540, 560, '42px SerifB', rgba(P.paper));
    text(ctx, '（前 5 个猜测都不对才算错 · 越低越好）', 540, 604, '26px SansM', rgba(P.paper, 0.55));
    const base = 1180, sc = 17.5;
    line(ctx, 120, base, 960, base, P.paper, 0.4, 2);
    const bars = [
      ['2010 冠军', 28.2, P.grey, S('F5') - 0.1], ['2011 冠军', 25.8, P.grey, S('F5') + 0.1],
      ['2012 第二名', 26.2, P.ice, charT('F5', '26.2') - 0.4], ['2012 AlexNet', 15.3, P.amber, charT('F5', '他们')],
    ];
    bars.forEach(([lab, v, c, tt], i) => {
      const k = eo(ramp(t, tt, tt + 0.7));
      const x = 160 + i * 205, w = 140, h = v * sc * k;
      ctx.fillStyle = rgba(c, i === 3 ? 1 : 0.75); ctx.fillRect(x, base - h, w, h);
      if (i === 3) glow(ctx, x + w / 2, base - h, 120, P.amber, 0.35 * k);
      withAlpha(ctx, k, () => {
        text(ctx, `${v}%`, x + w / 2, base - h - 18, i === 3 ? '48px SerifH' : '38px SerifB', rgba(i === 3 ? P.amber : P.paper), 'center');
        text(ctx, lab, x + w / 2, base + 40, '26px SansM', rgba(P.paper, 0.7), 'center');
      });
    });
    const gk = ap(t, K('F6') - 0.2, 0.4);
    withAlpha(ctx, gk, () => {
      const x2 = 160 + 2 * 205 + 140, ya = base - 26.2 * sc, yb = base - 15.3 * sc;
      line(ctx, x2 + 10, ya, x2 + 60, ya, P.paper, 0.6, 2, [6, 6]); arrow(ctx, x2 + 35, ya, x2 + 35, yb - 6, P.amber, 1, 4, 14);
      text(ctx, '−10.9', x2 + 46, (ya + yb) / 2 + 10, '30px SansB', rgba(P.amber), 'left');
    });
  });
  const sk = t - K('F6');
  if (sk > 0) {
    const k = eo(clamp(sk / 0.18));
    withAlpha(ctx, clamp(sk / 0.08), () => withXform(ctx, 540, 860, lerp(2.2, 1, k), -0.05, () => {
      glow(ctx, 0, -60, 300, P.amber, 0.3);
      ctx.lineJoin = 'round'; ctx.font = '220px SerifH'; ctx.strokeStyle = rgba(P.bg, 0.9); ctx.lineWidth = 18; ctx.textAlign = 'center'; ctx.strokeText('碾压', 0, 0);
      text(ctx, '碾压', 0, 0, '220px SerifH', rgba(P.amber), 'center');
    }));
  }
}
function alexnetCues() {
  cue(S('F3') - 0.1, 'paper'); cue(charT('F3', '交出了') - 0.4, 'build', 0.6);
  cue(S('F4') - 0.1, 'whoosh', 0.4); cue(S('F4') + 0.3, 'fans', 0.7);
  cue(S('F5') - 0.1, 'whoosh', 0.4); cue(charT('F5', '26.2') - 0.4, 'rise', 0.5); cue(charT('F5', '他们'), 'drop', 0.8);
  cue(K('F6'), 'impact', 1.3); SHAKES.push({ t: K('F6'), amp: 20 }); FLASHES.push({ t: K('F6'), c: P.amber, a: 0.25 });
}

// ================================================================== 2012 · THREE INGREDIENTS
function ingredients(ctx, t) {
  const items = [
    { zh: '算法', sub: '1986 · 反向传播', x: 310, y: 720, tt: charT('F7', '1986') },
    { zh: '数据', sub: '2009 · ImageNet', x: 770, y: 720, tt: charT('F7', '2009') },
    { zh: '算力', sub: '游戏显卡 GPU', x: 540, y: 1010, tt: charT('F7', '游戏显卡') },
  ];
  const tm = charT('F7', '三样东西') + 0.25;
  const m = eio(ramp(t, tm, tm + 0.9));
  items.forEach((it) => {
    const k = ap(t, it.tt - 0.1, 0.5);
    if (k <= 0) return;
    const x = lerp(it.x, 540, m * 0.72), y = lerp(it.y, 830, m * 0.72);
    withAlpha(ctx, k * (1 - 0.75 * ap(t, tm + 0.7, 0.5)), () => {
      glow(ctx, x, y, 220, P.amber, 0.25 + 0.25 * m);
      ctx.fillStyle = rgba(P.amber, 0.12); ctx.beginPath(); ctx.arc(x, y, 150, 0, TAU); ctx.fill();
      ring(ctx, x, y, 150, P.amber, 0.85, 4);
      withAlpha(ctx, 1 - m, () => { text(ctx, it.zh, x, y + 10, '72px SerifH', rgba(P.paper)); text(ctx, it.sub, x, y + 64, '26px SansM', rgba(P.paper, 0.7)); });
    });
  });
  const fk = ap(t, tm + 0.7, 0.5);
  withAlpha(ctx, fk, () => {
    glow(ctx, 540, 830, 380, P.amber, 0.4);
    text(ctx, '2012', 540, 880, '150px SerifH', rgba(P.paper));
    text(ctx, '三样东西，终于凑齐', 540, 1010, '36px SansB', rgba(P.paper, 0.9));
    text(ctx, '深度学习，爆发', 540, 1220, '48px SerifB', rgba(P.amber));
  });
}
function ingredientsCues() {
  ['1986', '2009', '游戏显卡'].forEach((w) => cue(charT('F7', w) - 0.1, 'pop', 0.7));
  const tm = charT('F7', '三样东西') + 0.25; cue(tm, 'swell', 0.6); cue(tm + 0.75, 'boom', 1.0);
  FLASHES.push({ t: tm + 0.75, c: P.amber, a: 0.3 }); SHAKES.push({ t: tm + 0.75, amp: 10 });
}

// ================================================================== 2012 · AUCTION
function auction(ctx, t) {
  const hA = ap(t, S('F8') - 0.1, 0.5);
  withAlpha(ctx, hA, () => {
    text(ctx, 'DNNresearch', 540, 560, '64px SerifH', rgba(P.paper));
    text(ctx, '辛顿和两个学生的公司 · 只有 3 名员工', 540, 610, '28px SansM', rgba(P.paper, 0.6));
    text(ctx, '2012 年 12 月 · 太浩湖畔的一家赌场酒店', 540, 660, '30px Kai', rgba(P.amber, 0.85));
  });
  const bidders = [['谷歌', '谷歌'], ['微软', '微软'], ['DeepMind', 'DeepMind'], ['百度', '百度']];
  const tFinal = K('F9');
  const tStart = charT('F8', '都来竞价') - 0.3;
  bidders.forEach(([name, key], i) => {
    const k = ap(t, charT('F8', key) - 0.1, 0.4);
    if (k <= 0) return;
    const y = 770 + i * 100;
    // who is bidding right now
    let active = -1;
    if (t > tStart && t < tFinal) { const step = Math.floor((t - tStart) / 0.32); const pool = (t - tStart) > (tFinal - tStart) * 0.55 ? [0, 3] : [0, 1, 2, 3]; active = pool[step % pool.length]; }
    const win = t >= tFinal && i === 0;
    const lose = t >= tFinal && i !== 0;
    withAlpha(ctx, k * (lose ? 0.35 : 1), () => {
      ctx.fillStyle = rgba(win ? P.amber : P.paper, win ? 0.18 : 0.05); roundRect(ctx, 150, y - 42, 780, 84, 14); ctx.fill();
      if (active === i || win) { ctx.strokeStyle = rgba(P.amber, 0.9); ctx.lineWidth = 3; roundRect(ctx, 150, y - 42, 780, 84, 14); ctx.stroke(); }
      // paddle
      const up = active === i ? -18 : 0;
      dot(ctx, 210, y - 8 + up, 22, active === i || win ? P.amber : P.grey); line(ctx, 210, y + 14 + up, 210, y + 40 + up, P.paper, 0.6, 5);
      text(ctx, name, 260, y + 14, '44px SansB', rgba(P.paper), 'left');
      if (win) text(ctx, '成交 ✓', 900, y + 14, '36px SansB', rgba(P.amber), 'right');
    });
  });
  // price ticker
  const pk = ap(t, tStart, 0.3);
  withAlpha(ctx, pk, () => {
    const u = ramp(t, tStart, tFinal);
    const price = t >= tFinal ? 44 : Math.floor(lerp(12, 44, eio(u)) * 2) / 2;
    const s = '$ ' + (price * 1e6).toLocaleString('en-US');
    const big = t >= tFinal ? eback(ramp(t, tFinal, tFinal + 0.4)) : 1;
    withXform(ctx, 540, 1215, lerp(1, 1.12, big - (t >= tFinal ? 0 : 1)), 0, () => text(ctx, s, 0, 0, '76px SerifH', rgba(t >= tFinal ? P.amber : P.paper), 'center'));
    text(ctx, '当前出价', 540, 1132, '26px SansM', rgba(P.paper, 0.5));
  });
}
function auctionCues() {
  cue(S('F8') - 0.1, 'whoosh', 0.5);
  ['谷歌', '微软', 'DeepMind', '百度'].forEach((w) => cue(charT('F8', w) - 0.1, 'pop', 0.45));
  const tStart = charT('F8', '都来竞价') - 0.3, tFinal = K('F9');
  for (let x = tStart; x < tFinal - 0.15; x += 0.32) cue(x, 'bid', 0.35);
  cue(tFinal, 'gavel', 1.0); SHAKES.push({ t: tFinal, amp: 8 });
}

// ================================================================== 2016–2022 · ACCELERATION
const GO = (() => { const r = rng(2016); const st = []; const used = new Set(); while (st.length < 120) { const i = Math.floor(r() * 19), j = Math.floor(r() * 19); const k = i * 19 + j; if (used.has(k)) continue; used.add(k); st.push([i, j, st.length % 2]); } return st; })();
function accel(ctx, t) {
  // G1: speed lines + "加速"
  const g1 = ap(t, S('G1') - 0.2, 0.4) * (1 - ap(t, S('G2') - 0.1, 0.3));
  withAlpha(ctx, g1, () => {
    for (let i = 0; i < 60; i++) {
      const a = hash(i) * TAU, sp = 0.6 + hash(i + 9);
      const p = ((((t - S('G1')) * sp * 1.4 + hash(i + 3)) % 1) + 1) % 1;
      const r0 = 80 + p * 900, r1 = r0 + 60 + p * 160;
      line(ctx, 540 + Math.cos(a) * r0, 820 + Math.sin(a) * r0, 540 + Math.cos(a) * r1, 820 + Math.sin(a) * r1, P.amber, 0.5 * (1 - p), 3);
    }
    for (let i = 3; i >= 0; i--) text(ctx, '加速', 540 - i * 18, 880, '200px SerifH', rgba(P.amber, i ? 0.12 : 1), 'center');
  });
  // G2: Go
  const g2 = ap(t, S('G2') - 0.1, 0.4) * (1 - ap(t, S('G3') - 0.1, 0.4));
  withAlpha(ctx, g2, () => {
    const x0 = 250, y0 = 640, s = 580, st = s / 18;
    ctx.fillStyle = rgba([196, 160, 102]); ctx.fillRect(x0 - 30, y0 - 30, s + 60, s + 60);
    for (let i = 0; i < 19; i++) { line(ctx, x0, y0 + i * st, x0 + s, y0 + i * st, P.ink, 0.7, 1.5); line(ctx, x0 + i * st, y0, x0 + i * st, y0 + s, P.ink, 0.7, 1.5); }
    const n = Math.floor(GO.length * clamp((t - S('G2')) / (E('G2') - S('G2'))));
    for (let q = 0; q < n; q++) { const [i, j, c] = GO[q]; dot(ctx, x0 + j * st, y0 + i * st, st * 0.46, c ? [240, 238, 230] : [20, 20, 22]); }
    if (n > 60) { const [i, j] = GO[37]; ring(ctx, x0 + j * st, y0 + i * st, st * 0.75, P.amber, 1, 4); text(ctx, '第 37 手', x0 + j * st + 30, y0 + i * st - 24, '26px Kai', rgba(P.amber), 'left'); }
    text(ctx, 'AlphaGo  4 : 1  李世石', 540, 560, '54px SerifH', rgba(P.paper));
    text(ctx, '2016 · 首尔', 540, 1290, '28px SansM', rgba(P.paper, 0.6));
  });
  // G3: attention arcs
  const g3 = ap(t, S('G3') - 0.1, 0.4) * (1 - ap(t, S('G4') - 0.1, 0.4));
  withAlpha(ctx, g3, () => {
    text(ctx, 'Transformer', 540, 580, '72px SerifH', rgba(P.paper));
    text(ctx, '2017 ·《Attention Is All You Need》', 540, 632, '28px SansM', rgba(P.paper, 0.6));
    const toks = ['小猫', '没', '跳', '上', '桌子', '，', '因为', '它', '太', '累', '了'];
    ctx.font = '40px SerifB'; const ws = toks.map((s) => ctx.measureText(s).width + 26);
    const tot = ws.reduce((a, b) => a + b, 0); let x = 540 - tot / 2; const xs = [];
    toks.forEach((s, i) => { xs.push(x + ws[i] / 2); x += ws[i]; });
    const y = 980, src = 7;
    const att = [0.82, 0.05, 0.08, 0.02, 0.35, 0.01, 0.06, 0, 0.04, 0.12, 0.03];
    const ak = ap(t, K('G3') - 0.4, 1.2);
    toks.forEach((s, i) => {
      if (i === src) return;
      const kk = clamp(ak * 1.5 - Math.abs(i - src) * 0.06);
      const h = 60 + Math.abs(i - src) * 34;
      ctx.strokeStyle = rgba(i === 0 ? P.amber : P.paper, (0.15 + 0.85 * att[i]) * kk); ctx.lineWidth = 1 + att[i] * 12;
      ctx.beginPath(); ctx.moveTo(xs[src], y - 50); ctx.quadraticCurveTo((xs[src] + xs[i]) / 2, y - 50 - h * 1.6, xs[i], y - 50); ctx.stroke();
    });
    toks.forEach((s, i) => text(ctx, s, xs[i], y, '40px SerifB', rgba(i === src || (i === 0 && ak > 0.7) ? P.amber : P.paper), 'center'));
    withAlpha(ctx, ap(t, K('G3') + 0.6, 0.5), () => text(ctx, '“它”是谁？注意力会去看句子里所有的词', 540, 1080, '30px Kai', rgba(P.paper, 0.75)));
    withAlpha(ctx, ap(t, charT('G3', '地基'), 0.5), () => chip(ctx, '今天几乎所有大模型的地基', 540, 1180, '34px SansB', rgba(P.bg), rgba(P.amber), 24, 62));
  });
  // G4: Turing award
  const g4 = ap(t, S('G4') - 0.1, 0.4) * (1 - ap(t, S('G5') - 0.1, 0.4));
  withAlpha(ctx, g4, () => {
    text(ctx, '2018 年度图灵奖', 540, 600, '64px SerifH', rgba(P.paper));
    text(ctx, '“计算机界的诺贝尔奖”', 540, 652, '28px SansM', rgba(P.paper, 0.6));
    LIGHTS.forEach((Lg, i) => {
      const x = 230 + i * 310, y = 860; const k = ap(t, S('G4') + 0.3 + i * 0.25, 0.4);
      withAlpha(ctx, k, () => { glow(ctx, x, y, 150, P.amber, 0.45); neuron(ctx, x, y, 20, 1, P.amber); text(ctx, Lg.zh, x, y + 100, '48px SerifB', rgba(P.paper)); text(ctx, Lg.en, x, y + 140, '22px SansR', rgba(P.paper, 0.6)); });
    });
    withAlpha(ctx, ap(t, CH('G4', 1), 0.4), () => text(ctx, '当年守灯的三个人', 540, 1150, '34px Kai', rgba(P.amber)));
  });
  // G5: chat
  const g5 = ap(t, S('G5') - 0.1, 0.4) * (1 - ap(t, S('G6') - 0.1, 0.4));
  withAlpha(ctx, g5, () => {
    ctx.fillStyle = rgba([24, 24, 27]); roundRect(ctx, 160, 520, 760, 700, 34); ctx.fill();
    ctx.strokeStyle = rgba(P.paper, 0.25); ctx.lineWidth = 2; roundRect(ctx, 160, 520, 760, 700, 34); ctx.stroke();
    text(ctx, 'ChatGPT · 2022.11.30', 540, 584, '30px SansB', rgba(P.paper, 0.8));
    line(ctx, 160, 612, 920, 612, P.paper, 0.15, 2);
    const q = '讲讲神经网络的往事？';
    ctx.font = '32px SansM'; const qw = ctx.measureText(q).width + 50;
    ctx.fillStyle = rgba(P.amber, 0.9); roundRect(ctx, 880 - qw, 650, qw, 70, 24); ctx.fill();
    text(ctx, q, 880 - qw / 2, 696, '32px SansM', rgba(P.bg));
    const ans = '1943 年，一个 15 岁就离家出走的少年，和一位神经科学家，想弄明白大脑是怎么思考的……';
    const n = Math.floor(ans.length * clamp((t - S('G5') - 0.4) / 2.6));
    ctx.fillStyle = rgba(P.paper, 0.08); roundRect(ctx, 200, 750, 620, 260, 24); ctx.fill();
    para(ctx, ans.slice(0, n) + (Math.floor(t * 3) % 2 ? '▍' : ''), 230, 805, 560, '32px SansR', rgba(P.paper, 0.9), 48);
    text(ctx, '上线约两个月，用户数估计破亿', 540, 1150, '28px Kai', rgba(P.paper, 0.6));
  });
  // G6: Ilya
  const g6 = ap(t, S('G6') - 0.1, 0.5);
  withAlpha(ctx, g6, () => {
    card(ctx, { no: 10, zh: '伊利亚·苏茨克维', en: 'Ilya Sutskever', role: 'OpenAI 联合创始人 · 前首席科学家', note: '2012 年，那个 8 层网络的作者之一。', w: 760, h: 340, compact: true }, 540, 720, g6, 0.015, 0.92);
    const k = ap(t, K('G6') - 0.1, 0.5);
    withAlpha(ctx, k, () => {
      chip(ctx, '2012 · AlexNet', 300, 1060, '30px SansB', rgba(P.paper), rgba(P.grey, 0.7), 20, 56);
      arrow(ctx, 400, 1060, 640, 1060, P.amber, 0.9, 4, 16);
      chip(ctx, '2022 · ChatGPT', 780, 1060, '30px SansB', rgba(P.bg), rgba(P.amber), 20, 56);
    });
  });
}
function accelCues() {
  cue(S('G1') - 0.2, 'riser', 0.8); cue(S('G2') - 0.1, 'whoosh', 0.6);
  for (let q = 0; q < 14; q++) cue(S('G2') + q * (E('G2') - S('G2')) / 14, 'stone', 0.35);
  cue(S('G3') - 0.1, 'whoosh', 0.6); cue(K('G3') - 0.4, 'shimmer', 0.6);
  cue(S('G4') - 0.1, 'whoosh', 0.6); [0, 1, 2].forEach((i) => cue(S('G4') + 0.3 + i * 0.25, 'fire', 0.5));
  cue(S('G5') - 0.1, 'whoosh', 0.6); cue(S('G5') + 0.4, 'type', 0.7);
  cue(S('G6') - 0.1, 'paper'); cue(K('G6') - 0.1, 'ding', 0.7);
}

// ================================================================== 2024 · NOBEL
function medal(ctx, x, y, r, t) {
  for (let i = 0; i < 16; i++) { const a = i * TAU / 16 + t * 0.15; line(ctx, x + Math.cos(a) * r * 1.15, y + Math.sin(a) * r * 1.15, x + Math.cos(a) * r * 1.6, y + Math.sin(a) * r * 1.6, P.gold, 0.25, 3); }
  glow(ctx, x, y, r * 2, P.gold, 0.35);
  const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
  g.addColorStop(0, rgba([255, 230, 160])); g.addColorStop(0.6, rgba([214, 168, 82])); g.addColorStop(1, rgba([150, 108, 40]));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
  ring(ctx, x, y, r * 0.86, [120, 84, 30], 0.6, 3);
  text(ctx, '诺贝尔', x, y - r * 0.12, `${Math.round(r * 0.3)}px SerifH`, rgba([90, 60, 20]), 'center');
  text(ctx, '物理学奖', x, y + r * 0.22, `${Math.round(r * 0.2)}px SerifB`, rgba([90, 60, 20]), 'center');
  text(ctx, '2024', x, y + r * 0.52, `${Math.round(r * 0.17)}px SansB`, rgba([90, 60, 20]), 'center');
}
function nobel(ctx, t) {
  const mA = ap(t, S('I1') + 1.5, 0.6) * (1 - ap(t, S('I4') - 0.1, 0.5));
  const up = eio(ramp(t, S('I2') - 0.2, S('I2') + 0.4));
  withAlpha(ctx, mA, () => medal(ctx, 540, lerp(780, 600, up), lerp(190, 120, up), t));
  const cards = [
    [{ no: 5, zh: '霍普菲尔德', en: 'John Hopfield', role: '91 岁 · 物理学家', w: 440, h: 270, compact: true, zhSize: 46 }, 300, 980, K('I2', 0)],
    [{ no: 6, zh: '辛顿', en: 'Geoffrey Hinton', role: '76 岁 · 计算机科学家', w: 440, h: 270, compact: true, zhSize: 46 }, 780, 980, K('I2', 1)],
  ];
  const cOut = ap(t, S('I4') - 0.1, 0.5);
  cards.forEach(([o, x, y, tt], i) => withAlpha(ctx, 1 - cOut, () => card(ctx, o, x, y, ramp(t, tt - 0.15, tt + 0.45), i ? 0.02 : -0.02, 1)));
  // flashback to 1982
  const fk = ap(t, S('I3'), 0.5) * (1 - cOut);
  withAlpha(ctx, fk, () => {
    ctx.fillStyle = rgba(P.bg, 0.85); roundRect(ctx, 90, 1140, 420, 150, 14); ctx.fill();
    ctx.strokeStyle = rgba(P.amber, 0.6); ctx.lineWidth = 2; roundRect(ctx, 90, 1140, 420, 150, 14); ctx.stroke();
    energyCurve(ctx, 130, 950, 1, 0.4, -240, 220);
    text(ctx, '1982 · 能量', 300, 1278, '24px SansB', rgba(P.amber), 'center');
    text(ctx, '42 年后', 680, 1230, '40px Kai', rgba(P.amber), 'center');
    arrow(ctx, 530, 1215, 600, 1215, P.amber, 0.8, 3, 12);
  });
  // phone + quote
  const qA = ap(t, S('I4') - 0.1, 0.5) * (1 - ap(t, S('I5') - 0.1, 0.5));
  withAlpha(ctx, qA, () => {
    const ringK = Math.max(0, Math.sin((t - S('I4')) * 30)) * (t < charT('I4', '他说') ? 1 : 0);
    withXform(ctx, 540, 640, 1, ringK * 0.08, () => {
      ctx.fillStyle = rgba([30, 30, 34]); roundRect(ctx, -60, -110, 120, 220, 22); ctx.fill();
      ctx.strokeStyle = rgba(P.paper, 0.6); ctx.lineWidth = 4; roundRect(ctx, -60, -110, 120, 220, 22); ctx.stroke();
      ctx.fillStyle = rgba(P.amber, 0.25 + 0.5 * ringK); roundRect(ctx, -46, -86, 92, 160, 10); ctx.fill();
    });
    if (ringK > 0) for (let i = 0; i < 2; i++) { ctx.strokeStyle = rgba(P.amber, 0.6); ctx.lineWidth = 4; ctx.beginPath(); ctx.arc(540, 640, 150 + i * 30, -0.5, 0.5); ctx.stroke(); ctx.beginPath(); ctx.arc(540, 640, 150 + i * 30, Math.PI - 0.5, Math.PI + 0.5); ctx.stroke(); }
    withAlpha(ctx, ap(t, charT('I4', '加州'), 0.4), () => text(ctx, '加州 · 一家便宜的旅馆', 540, 810, '34px Kai', rgba(P.paper, 0.75)));
    const qk = ap(t, charT('I4', '他说'), 0.5);
    withAlpha(ctx, qk, () => withXform(ctx, 540, 1020 + (1 - qk) * 40, 1, -0.015, () => {
      paperRect(ctx, -390, -150, 780, 300, 8);
      text(ctx, '“I\'m flabbergasted.”', 0, -50, '58px SerifB', rgba(P.ink), 'center');
      text(ctx, '我完全惊呆了。', 0, 30, '46px SerifB', rgba(P.amberDeep), 'center');
      text(ctx, '—— 辛顿，接到获奖电话时', 0, 100, '26px SansR', rgba(P.ink, 0.6), 'center');
    }));
  });
  // warning
  const wA = ap(t, S('I5') - 0.1, 0.5);
  withAlpha(ctx, wA, () => {
    const x = 540, y = 680, s = 120;
    ctx.fillStyle = rgba(P.amber); ctx.beginPath(); ctx.moveTo(x, y - s); ctx.lineTo(x + s * 1.1, y + s * 0.8); ctx.lineTo(x - s * 1.1, y + s * 0.8); ctx.closePath(); ctx.fill();
    text(ctx, '!', x, y + s * 0.62, '150px SerifH', rgba(P.bg), 'center');
    withAlpha(ctx, ap(t, CH('I5', 2) - 0.1, 0.5), () => text(ctx, '认真对待 AI 的风险', 540, 960, '68px SerifH', rgba(P.paper)));
    text(ctx, '2023 年，他从谷歌离职，好更自由地谈论这件事', 540, 1040, '30px Kai', rgba(P.paper, 0.6));
  });
  L.yearCard(ctx, t, S('I1') - 0.1, 2024, '回响', 1.75);
}
function nobelCues() {
  cue(S('I1') - 0.1, 'whoosh', 0.8); cue(S('I1') + 1.5, 'chime', 0.9);
  cue(K('I2', 0) - 0.15, 'paper'); cue(K('I2', 1) - 0.15, 'paper'); cue(S('I3'), 'pop', 0.6);
  cue(S('I4') - 0.1, 'phone', 0.6); cue(charT('I4', '他说'), 'paper'); cue(S('I5') - 0.1, 'low', 0.7);
}

// ================================================================== ENDING
const TIMELINE = [
  ['1943', '第一个人工神经元'], ['1958', '感知机'], ['1969', '第一次死刑', 1], ['1982', '霍普菲尔德网络'], ['1986', '反向传播'],
  ['1989', '卷积网络读支票'], ['1990s', '第二次死刑', 1], ['2006', '深度学习'], ['2012', 'AlexNet'], ['2017', 'Transformer'], ['2022', 'ChatGPT'], ['2024', '诺贝尔奖'],
];
const NAMES = ['皮茨', '麦卡洛克', '罗森布拉特', '霍普菲尔德', '鲁梅尔哈特', '辛顿', '杨立昆', '本吉奥', '李飞飞', '亚历克斯', '伊利亚'];
const CONST = (() => {
  const r = rng(81); const named = []; const pos = [[220, 560], [470, 520], [780, 560], [300, 760], [600, 700], [860, 820], [190, 980], [470, 930], [740, 1040], [330, 1180], [640, 1200]];
  NAMES.forEach((n, i) => named.push({ x: pos[i][0], y: pos[i][1], name: n }));
  const others = Array.from({ length: 70 }, () => ({ x: 90 + r() * 900, y: 470 + r() * 800, ph: r() }));
  return { named, others };
})();
function ending(ctx, t) {
  // J1: vertical timeline
  const tlA = ap(t, S('J1') - 0.2, 0.5) * (1 - ap(t, S('J2') - 0.2, 0.6));
  withAlpha(ctx, tlA, () => {
    const x = 260, y0 = 470, y1 = 1230; const n = TIMELINE.length;
    const rev = ramp(t, S('J1'), charT('J1', '隔了'));
    line(ctx, x, y0, x, lerp(y0, y1, rev), P.paper, 0.4, 3);
    TIMELINE.forEach(([yr, lab, red], i) => {
      const y = lerp(y0, y1, i / (n - 1)); const k = clamp(rev * n - i + 0.5);
      withAlpha(ctx, k, () => {
        dot(ctx, x, y, red ? 11 : 8, red ? P.red : P.amber);
        text(ctx, yr, x - 26, y + 11, '32px SerifB', rgba(red ? P.red : P.paper, 0.9), 'right');
        text(ctx, lab, x + 30, y + 11, '30px SansM', rgba(red ? P.red : P.paper, 0.85), 'left');
      });
    });
    const sk = ap(t, charT('J1', '81年') - 0.1, 0.5);
    withAlpha(ctx, sk, () => { text(ctx, '81 年', 790, 760, '100px SerifH', rgba(P.amber)); });
    const dk = ap(t, charT('J1', '两次死刑') - 0.1, 0.5);
    withAlpha(ctx, dk, () => { text(ctx, '2 次死刑', 790, 900, '72px SerifH', rgba(P.red)); });
  });
  // J2: constellation — the many leave, a few stay
  const cA = ap(t, S('J2') - 0.2, 0.8) * (1 - 0.6 * ap(t, S('J3') - 0.2, 0.6)) * (1 - ap(t, E('J4') + 0.3, 0.6));
  if (cA > 0) withAlpha(ctx, cA, () => {
    const leave = ap(t, CH('J2', 3), 1.6);
    const stay = ap(t, CH('J2', 2), 0.8);
    const { named, others } = CONST;
    others.forEach((o, i) => {
      const a = 1 - leave * (0.3 + 0.7 * o.ph);
      const drift = leave * 160 * (o.ph - 0.5);
      if (a <= 0.02) return;
      const nb = others[(i + 7) % others.length];
      line(ctx, o.x + drift, o.y, nb.x + drift, nb.y, P.paper, 0.06 * a, 1);
      neuron(ctx, o.x + drift, o.y - leave * 60 * o.ph, 6, 0.3 * a * Math.pow(Math.max(0, Math.sin(t * 2 + o.ph * 30)), 2), P.paper, a);
    });
    named.forEach((n, i) => { const m = named[(i + 1) % named.length]; if (i < named.length - 1) line(ctx, n.x, n.y, m.x, m.y, P.amber, 0.12 + 0.25 * stay, 1.5); });
    named.forEach((n, i) => {
      const k = ap(t, S('J2') + i * 0.12, 0.5);
      neuron(ctx, n.x, n.y, 12, 0.3 + 0.7 * stay, P.amber, k);
      withAlpha(ctx, k * (0.35 + 0.65 * stay), () => text(ctx, n.name, n.x, n.y + 50, '30px SerifB', rgba(P.paper), 'center'));
    });
  });
  // J3/J4: heart
  const hA = ap(t, S('J3') - 0.1, 0.5) * (1 - ap(t, E('J4') + 0.5, 0.5));
  const fill = ap(t, charT('J4', '它猜') - 0.1, 0.35);
  withAlpha(ctx, hA, () => {
    const beat = 1 + 0.05 * Math.pow(Math.max(0, Math.sin(t * 5)), 8) + 0.15 * Math.exp(-Math.max(0, t - charT('J4', '它猜')) * 6) * (fill > 0 ? 1 : 0);
    withXform(ctx, 540, 840, beat * 1.9, 0, () => {
      if (fill > 0) glow(ctx, 0, -10, 220, P.amber, 0.5 * fill);
      ctx.beginPath(); ctx.moveTo(0, 70);
      ctx.bezierCurveTo(-150, -20, -95, -140, 0, -72); ctx.bezierCurveTo(95, -140, 150, -20, 0, 70); ctx.closePath();
      if (fill > 0) { ctx.fillStyle = rgba(P.amber, fill); ctx.fill(); }
      ctx.strokeStyle = rgba(P.amber); ctx.lineWidth = 5; ctx.stroke();
    });
    if (fill > 0) for (let i = 0; i < 18; i++) { const a = i * TAU / 18, d = 120 + 260 * eo(ramp(t, charT('J4', '它猜'), charT('J4', '它猜') + 1.2)); dot(ctx, 540 + Math.cos(a) * d, 800 + Math.sin(a) * d, 6, P.amber, 1 - ramp(t, charT('J4', '它猜') + 0.4, charT('J4', '它猜') + 1.4)); }
    withAlpha(ctx, ap(t, S('J3') + 0.4, 0.5) * (1 - fill), () => text(ctx, '让推荐算法知道', 540, 1120, '34px Kai', rgba(P.paper, 0.7)));
    withAlpha(ctx, fill, () => text(ctx, '它，猜得没错', 540, 1140, '64px SerifH', rgba(P.paper)));
  });
  // end card
  const eA = ap(t, E('J4') + 0.6, 0.8);
  withAlpha(ctx, eA, () => {
    text(ctx, '神经网络往事', 540, 860, '110px SerifH', rgba(P.paper));
    text(ctx, '1943 — 2024', 540, 950, '40px SerifB', rgba(P.amber));
    stamp(ctx, '完', 540, 1090, 64, t - (E('J4') + 1.0), -0.12, P.red);
  });
}
function endingCues() {
  cue(S('J1') - 0.2, 'whoosh', 0.5); cue(charT('J1', '81年') - 0.1, 'boom', 0.5); cue(charT('J1', '两次死刑') - 0.1, 'stamp', 0.5);
  cue(CH('J2', 2), 'swell', 0.5);
  cue(S('J3') - 0.1, 'pop', 0.5); cue(charT('J4', '它猜') - 0.1, 'heart', 1.0); FLASHES.push({ t: charT('J4', '它猜'), c: P.amber, a: 0.15 });
  cue(E('J4') + 1.0, 'stamp', 0.4);
}

const SCENES = { hook, title, pitts, mpneuron, perceptron, nyt, xor, winter1, hopfield, backprop, lecun, winter2, lights, imagenet, alexnet, ingredients, auction, accel, nobel, ending };
[hookCues, titleCues, pittsCues, mpneuronCues, perceptronCues, nytCues, xorCues, winter1Cues, hopfieldCues, backpropCues, lecunCues, winter2Cues, lightsCues, imagenetCues, alexnetCues, ingredientsCues, auctionCues, accelCues, nobelCues, endingCues].forEach((f) => f());
CUES.sort((a, b) => a.t - b.t);

module.exports = { SCENES, CUES, SHAKES, FLASHES };
