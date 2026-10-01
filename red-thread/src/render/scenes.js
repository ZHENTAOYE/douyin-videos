// 14 个场景的画面。所有动画都锚定在旁白的时间点上（S/E/K/CH/charT）。
'use strict';
const E_ = require('./engine');
const L = require('./layers');
const F = require('./figures');
const M = require('./match');
const {
  W, H, TAU, P, rgba, mix, clamp, lerp, ramp, eo, ei, eio, eback, smooth, fade, ap, pop, hash,
  S, E, K, CH, charT, roundRect, text, spaced, glow, dot, ring, line, arrow, withAlpha, withXform,
  paperRect, thread, threadMid, threadSnap, stamp, seal, heart, bubble,
} = E_;
const { MEN, WOMEN, MPREF, WPREF, MENFIRST, WOMENFIRST, WM, rankOf } = M;

const CUES = [];        // sound-effect cues, consumed by music.py
const SHAKES = [];
const FLASHES = [];
const cue = (t, type, gain = 1) => CUES.push({ t: +t.toFixed(3), type, gain });

// ================================================================== board geometry
const ROWS = [600, 805, 1010, 1215];
const MX = 210, WX = 870;
const pos = (side, i) => ({ x: side === 'm' ? MX : WX, y: ROWS[i] });
const hand = (side, i) => (side === 'm' ? [MX + 56, ROWS[i] + 20] : [WX - 56, ROWS[i] + 20]);
const people = (side) => (side === 'm' ? MEN : WOMEN);
const prefs = (side) => (side === 'm' ? MPREF : WPREF);
const other = (side) => (side === 'm' ? 'f' : 'm');
function pairThread(ctx, side, i, j, o) {          // thread from side's i to the other side's j
  const [x1, y1] = hand(side, i), [x2, y2] = hand(other(side), j);
  thread(ctx, x1, y1, x2, y2, o);
}
function pairSnap(ctx, side, i, j, k, o) {
  const [x1, y1] = hand(side, i), [x2, y2] = hand(other(side), j);
  threadSnap(ctx, x1, y1, x2, y2, k, o);
}
function pairMid(side, i, j, u = 0.5) {
  const [x1, y1] = hand(side, i), [x2, y2] = hand(other(side), j);
  return threadMid(x1, y1, x2, y2, null, u);
}
function rankBadge(ctx, side, i, rank, k, opt = {}) {
  if (k <= 0.003) return;
  const { x, y } = pos(side, i);
  const bx = side === 'm' ? x + 84 : x - 84, by = y - 64;
  const best = rank === 1;
  const col = opt.col || (best ? P.gold : rank === 2 ? [150, 128, 100] : P.inkFaint);
  withXform(ctx, bx, by, eback(k), 0, () => {
    ctx.globalAlpha *= clamp(k * 3);
    ctx.fillStyle = rgba(col); roundRect(ctx, -44, -22, 88, 44, 22); ctx.fill();
    text(ctx, `第${rank}名`, 0, 1, '28px SerifH', rgba(P.white), 'center', 'middle');
  });
}

// ------------------------------------------------------------------ the people on the board
// o.mood(side,i) → mood, o.appear(side,i) → 0..1, o.chips(side,i) → chip options | null, o.dim(side,i)
function drawPeople(ctx, t, o) {
  for (const side of ['m', 'f']) for (let i = 0; i < 4; i++) {
    const k = o.appear ? o.appear(side, i) : 1;
    if (k <= 0.003) continue;
    const { x, y } = pos(side, i);
    const p = people(side)[i];
    const dim = o.dim ? o.dim(side, i) : 0;
    withAlpha(ctx, clamp(k * 2) * (1 - 0.6 * dim), () => {
      const s = eback(k);
      F.person(ctx, x, y + (1 - k) * 40, p, { s, mood: o.mood ? o.mood(side, i) : 'neutral', t, look: side === 'm' ? 0.6 : -0.6 });
      seal(ctx, p.ch, side === 'm' ? x - 108 : x + 108, y - 52, 46, p.col, side === 'm' ? -0.06 : 0.06, clamp(k * 2));
      const ch = o.chips && o.chips(side, i);
      if (ch) F.prefChips(ctx, x, y + 98, prefs(side)[i], people(other(side)), ch);
    });
  }
}

// ------------------------------------------------------------------ a full run of the algorithm, timed to narration
// times[r] = { prop: [t per proposal, in proposal order] | t, dur, decide }, final: t
function buildRun(res, side, times, final) {
  const threads = [];
  const live = {};                 // receiver -> thread currently held
  res.rounds.forEach((r, ri) => {
    const tm = times[ri];
    r.proposals.forEach((pr, k) => {
      const t0 = Array.isArray(tm.prop) ? tm.prop[k] : tm.prop + k * 0.18;
      const th = { p: pr.from, q: pr.to, t0, t1: t0 + (tm.dur || 0.9), snap: Infinity, round: ri };
      threads.push(th);
    });
    const byKey = (p, q) => threads.filter((th) => th.p === p && th.q === q && th.round === ri)[0];
    for (const rj of r.rejected) byKey(rj.from, rj.to).snap = tm.decide;
    for (const b of r.bumped) live[b.to].snap = tm.decide;
    for (const [w, m] of r.hold.entries()) if (m != null) {
      const th = threads.filter((x) => x.p === m && x.q === w && x.snap === Infinity).slice(-1)[0];
      if (th) live[w] = th;
    }
  });
  return { res, side, times, threads, final };
}
function runState(run, t) {
  const st = { mood: {}, crossed: {}, ptr: {}, hold: {} };
  const ps = run.side, rs = other(ps);
  for (let i = 0; i < 4; i++) { st.crossed[i] = new Set(); st.mood[ps + i] = 'neutral'; st.mood[rs + i] = 'neutral'; }
  for (const th of run.threads) {
    if (t < th.t0) continue;
    const k = prefs(ps)[th.p].indexOf(th.q);
    st.ptr[th.p] = k;
    if (t >= th.snap) {
      st.crossed[th.p].add(k);
      st.mood[ps + th.p] = t < th.snap + 2.2 ? 'sad' : 'neutral';
    } else if (t < th.t1 + 0.2) {
      st.mood[ps + th.p] = 'love';
    } else {
      st.mood[ps + th.p] = 'happy';
      st.hold[th.q] = th.p;
      st.mood[rs + th.q] = 'shy';
    }
  }
  for (const i of Object.keys(st.ptr)) if (st.crossed[i].has(st.ptr[i])) delete st.ptr[i];
  return st;
}
function drawRunThreads(ctx, t, run, a = 1) {
  const fin = run.final;
  for (const th of run.threads) {
    if (t < th.t0) continue;
    if (t >= th.snap) { pairSnap(ctx, run.side, th.p, th.q, ramp(t, th.snap, th.snap + 0.9), { a, dash: [16, 10] }); continue; }
    const p = eio(ramp(t, th.t0, th.t1));
    const solid = t >= fin;
    const tight = solid ? eo(ramp(t, fin, fin + 0.5)) : 0;
    pairThread(ctx, run.side, th.p, th.q, { p, a, dash: solid ? null : [16, 10], lw: solid ? 6 : 5, wob: 4 * (1 - tight), t });
    if (p >= 1) {
      const [mx, my] = pairMid(run.side, th.p, th.q);
      if (!solid) seal(ctx, '暂', mx, my, 36, P.red, -0.08, clamp((t - th.t1) * 4));
      else {
        const k = ramp(t, fin, fin + 0.6);
        glow(ctx, mx, my, 60, P.red, 0.35 * (1 - k) + 0.12);
        heart(ctx, mx, my + 6, 16 * eback(k), P.red, 1);
      }
    }
  }
}
function runCues(run) {
  for (const th of run.threads) {
    cue(th.t0, 'string', 0.6);
    cue(th.t1 - 0.05, 'pop', 0.45);
    if (th.snap < Infinity) cue(th.snap, 'snap', 0.9);
  }
}

// ================================================================== HOOK
const MOPT = MENFIRST.match;          // men → women
const WOPT = WM;                       // men → women (women-first)
function hook(ctx, t) {
  const tSwitch = K('H2') + 0.1;
  const switched = t >= tSwitch;
  // banner flip
  const flip = eio(ramp(t, tSwitch - 0.25, tSwitch + 0.25));
  const label = flip < 0.5 ? '男生先开口' : '女生先开口';
  withXform(ctx, W / 2, 330, 1, 0, () => {
    ctx.save(); ctx.scale(1, Math.abs(Math.cos(flip * Math.PI)) * 0.9 + 0.1); ctx.translate(-W / 2, -330);
    L.banner(ctx, { label, dir: flip < 0.5 ? 1 : -1, a: ap(t, 0.1, 0.4) });
    ctx.restore();
  });
  const appear = (side, i) => ap(t, 0.25 + (side === 'm' ? i : i + 0.5) * 0.12, 0.5);
  // threads
  for (let m = 0; m < 4; m++) {
    const w1 = MOPT[m], w2 = WOPT[m];
    if (!switched) pairThread(ctx, 'm', m, w1, { p: eio(ramp(t, 1.1 + m * 0.12, 1.9 + m * 0.12)), wob: 3, t });
    else {
      pairSnap(ctx, 'm', m, w1, ramp(t, tSwitch, tSwitch + 0.8));
      const p = eio(ramp(t, tSwitch + 0.35 + m * 0.1, tSwitch + 1.1 + m * 0.1));
      const [x1, y1] = hand('f', w2), [x2, y2] = hand('m', m);
      thread(ctx, x1, y1, x2, y2, { p, wob: 3, t });
    }
  }
  const after = ramp(t, tSwitch + 0.9, tSwitch + 1.2);
  const mood = (side, i) => {
    if (t < 1.8) return 'neutral';
    if (!switched) return side === 'm' ? 'happy' : 'neutral';
    if (after < 0.5) return 'shock';
    return side === 'f' ? 'happy' : 'sad';
  };
  const nb = ap(t, K('H4') - 0.1, 0.4);
  drawPeople(ctx, t, { appear, mood, dim: () => 0.7 * nb });
  // "同样的心意": everyone's ranking flashes over their heads
  const hA = fade(t, CH('H1') + 1.0, S('H2') + 0.2, 0.3, 0.3);
  withAlpha(ctx, hA, () => {
    for (const side of ['m', 'f']) for (let i = 0; i < 4; i++) {
      const { x, y } = pos(side, i);
      F.prefChips(ctx, x, y + 98, prefs(side)[i], people(other(side)), { s: 0.9 });
    }
  });
  // result label under the board
  withAlpha(ctx, fade(t, S('H3'), K('H4'), 0.3, 0.3), () => {
    text(ctx, '同样的人 · 同样的心意 · 不同的结局', W / 2, 1345, '36px Kai', rgba(P.inkSoft));
  });
  // Nobel stamp
  withAlpha(ctx, nb, () => {
    ctx.fillStyle = rgba(P.paperHi, 0.55); ctx.fillRect(0, 700, W, 520);
    stamp(ctx, '诺贝尔奖', W / 2, 930, 120, t - K('H4'), -0.1, P.red, '2012 · 经济学');
  });
}
function hookCues() {
  for (let i = 0; i < 8; i++) cue(0.25 + i * 0.12 * 0.5 + 0.1, 'pop', 0.25);
  for (let m = 0; m < 4; m++) cue(1.1 + m * 0.12, 'string', 0.35);
  const ts = K('H2') + 0.1;
  cue(ts - 0.2, 'whoosh', 0.7); cue(ts, 'snap', 1.0); cue(ts + 0.08, 'snap', 0.7);
  for (let m = 0; m < 4; m++) cue(ts + 0.35 + m * 0.1, 'string', 0.4);
  cue(K('H4') - 0.05, 'stamp', 1.1); SHAKES.push({ t: K('H4'), amp: 14 });
}

// ================================================================== TITLE
function title(ctx, t, sc) {
  const t0 = sc.t0;
  const k = ap(t, t0 + 0.1, 0.8);
  withAlpha(ctx, k, () => {
    withXform(ctx, W / 2, 880, lerp(1.08, 1, k), 0, () => {
      spaced(ctx, '红线算法', 0, 0, '168px SerifH', rgba(P.ink), 18);
    });
  });
  // the thread underline, drawn left to right, tied in a knot
  const p = eio(ramp(t, t0 + 0.5, t0 + 1.6));
  thread(ctx, 150, 945, 930, 945, { p, sag: 26, lw: 7, wob: 2, t });
  const kk = ap(t, t0 + 1.6, 0.4);
  withAlpha(ctx, kk, () => {
    dot(ctx, 930, 945, 13, P.red);
    line(ctx, 930, 945, 905, 1000, P.red, 1, 6); line(ctx, 930, 945, 960, 995, P.red, 1, 6);
  });
  withAlpha(ctx, ap(t, t0 + 1.0, 0.6), () => {
    text(ctx, '谁先开口，谁更如愿？', W / 2, 1060, '56px Kai', rgba(P.ink, 0.9));
    text(ctx, 'Gale – Shapley  ·  1962', W / 2, 1130, '32px SerifB', rgba(P.inkSoft));
  });
  stamp(ctx, '月老', W / 2, 680, 56, t - (t0 + 1.8), 0.08, P.red);
}
function titleCues() { const sc = sceneT('title'); cue(sc + 0.05, 'boom', 0.7); cue(sc + 0.5, 'string', 0.8); cue(sc + 1.6, 'knot', 0.8); cue(sc + 1.8, 'stamp', 0.5); }

// ================================================================== LEGEND (月老)
const COUPLES = [[150, 270], [480, 600], [810, 930]];
const CROWD = (() => {
  const out = [];
  for (let i = 0; i < 8; i++) out.push({ x: 140 + (i % 4) * 267 + (i >= 4 ? 0 : 0), y: i < 4 ? 1060 : 1290, p: i % 2 === 0 ? MEN[i >> 1] : WOMEN[i >> 1] });
  return out;
})();
function legend(ctx, t, sc) {
  const crowdK = ap(t, S('A2') - 0.1, 0.8);
  // 月老 floats at top; shrinks when the crowd arrives
  const ys = lerp(760, 560, crowdK), ss = lerp(1.55, 1.05, crowdK);
  F.yuelao(ctx, 540, ys, ss, t, ap(t, sc.t0, 0.6));
  const spool = [540 - 56 * ss, ys + 20 * ss];
  // three couples tied by threads (A1)
  withAlpha(ctx, 1 - crowdK, () => {
    COUPLES.forEach(([x1, x2], i) => {
      const tk = charT('A1', '系住') + i * 0.25;
      const p = eio(ramp(t, CH('A1', 0) + 0.6 + i * 0.3, tk + 0.4));
      const kx = (x1 + x2) / 2, ky = 1325;
      F.person(ctx, x1, 1250, MEN[i], { s: 0.62, t, mood: t > tk + 0.4 ? 'happy' : 'neutral', a: ap(t, sc.t0 + 0.3 + i * 0.15, 0.4) });
      F.person(ctx, x2, 1250, WOMEN[i], { s: 0.62, t, mood: t > tk + 0.4 ? 'shy' : 'neutral', a: ap(t, sc.t0 + 0.4 + i * 0.15, 0.4) });
      thread(ctx, spool[0], spool[1], kx, ky, { p, sag: 120, lw: 4, a: 0.9 });
      const tie = ap(t, tk + 0.4, 0.3);
      withAlpha(ctx, tie, () => {
        thread(ctx, x1 + 10, 1290, kx, ky, { sag: 8, lw: 4 }); thread(ctx, kx, ky, x2 - 10, 1290, { sag: 8, lw: 4 });
        dot(ctx, kx, ky, 8 * eback(tie), P.red);
      });
    });
  });
  // A2: a crowd, everyone with a ranking — and a tangle
  withAlpha(ctx, crowdK, () => {
    CROWD.forEach((c, i) => {
      const k = ap(t, S('A2') + i * 0.08, 0.5);
      F.person(ctx, c.x, c.y, c.p, { s: 0.72 * eback(k), t, mood: t > CH('A2', 1) ? 'think' : 'neutral', a: clamp(k * 2) });
      // ranking bubble
      const bk = ap(t, charT('A2', '排名') + i * 0.05, 0.4);
      const list = c.p.sex === 'm' ? MPREF[MEN.indexOf(c.p)] : WPREF[WOMEN.indexOf(c.p)];
      bubble(ctx, c.x, c.y - 140, 170, 56, bk, 0, (g) => {
        list.forEach((j, n) => { const q = (c.p.sex === 'm' ? WOMEN : MEN)[j]; dot(g, -57 + n * 38, 0, 15, q.col); text(g, q.ch, -57 + n * 38, 1, '18px SerifH', rgba(P.white), 'center', 'middle'); });
      });
    });
    // tangle of red thread + question mark
    const tk = ap(t, CH('A2', 1), 0.8);
    if (tk > 0) {
      ctx.save(); ctx.strokeStyle = rgba(P.red, 0.85); ctx.lineWidth = 3.5; ctx.lineCap = 'round';
      ctx.beginPath();
      const n = Math.floor(160 * tk);
      for (let i = 0; i <= n; i++) {
        const u = i / 160;
        const x = 540 + Math.sin(u * 37) * 120 * Math.sin(u * 5 + 1) + Math.cos(u * 11) * 30;
        const y = 860 + Math.cos(u * 29) * 70 * Math.sin(u * 7 + 2) + Math.sin(u * 13) * 20;
        if (i === 0) ctx.moveTo(spool[0], spool[1]); ctx.lineTo(x, y);
      }
      ctx.stroke(); ctx.restore();
      withAlpha(ctx, ap(t, charT('A2', '该怎么牵'), 0.4), () => text(ctx, '？', 700, 840, '120px SerifH', rgba(P.ink)));
    }
  });
}
function legendCues() {
  cue(S('A1') - 0.2, 'chime', 0.6);
  for (let i = 0; i < 3; i++) { cue(CH('A1', 0) + 0.6 + i * 0.3, 'string', 0.5); cue(charT('A1', '系住') + i * 0.25 + 0.4, 'knot', 0.6); }
  for (let i = 0; i < 8; i++) cue(S('A2') + i * 0.08, 'pop', 0.25);
  cue(CH('A2', 1), 'tangle', 0.6); cue(charT('A2', '该怎么牵'), 'pop', 0.6);
}

// ================================================================== PAPER (1962)
function paper(ctx, t, sc) {
  const k = ap(t, sc.t0 + 0.1, 0.7);
  // two authors
  const ak = ap(t, K('A3', 0) - 0.2, 0.5), bk = ap(t, K('A3', 1) - 0.2, 0.5);
  const author = (x, zh, en, yrs, kk) => withAlpha(ctx, kk, () => {
    withXform(ctx, x, 470 + (1 - kk) * 20, 1, 0, () => {
      paperRect(ctx, -180, -90, 360, 170, 12, P.paperHi);
      text(ctx, zh, 0, -16, '50px SerifH', rgba(P.ink));
      text(ctx, en, 0, 28, '28px SerifB', rgba(P.inkSoft));
      text(ctx, yrs, 0, 64, '24px SansM', rgba(P.inkFaint));
    });
  });
  author(290, '大卫·盖尔', 'David Gale', '1921 – 2008', ak);
  author(790, '劳埃德·沙普利', 'Lloyd Shapley', '1923 – 2016', bk);
  // the paper itself
  withAlpha(ctx, k, () => withXform(ctx, W / 2, 940 + (1 - k) * 60, 1, (1 - k) * 0.05 - 0.015, () => {
    const w = 640, h = 640;
    paperRect(ctx, -w / 2, -h / 2, w, h, 6, [250, 246, 236]);
    text(ctx, 'THE AMERICAN MATHEMATICAL MONTHLY', 0, -h / 2 + 50, '22px SerifB', rgba(P.inkSoft));
    text(ctx, 'Vol. 69, No. 1  ·  January 1962', 0, -h / 2 + 80, '20px SerifR', rgba(P.inkFaint));
    line(ctx, -w / 2 + 50, -h / 2 + 100, w / 2 - 50, -h / 2 + 100, P.ink, 0.25, 2);
    text(ctx, 'COLLEGE ADMISSIONS AND THE', 0, -h / 2 + 160, '34px SerifH', rgba(P.ink));
    text(ctx, 'STABILITY OF MARRIAGE', 0, -h / 2 + 204, '34px SerifH', rgba(P.ink));
    text(ctx, 'D. GALE AND L. S. SHAPLEY', 0, -h / 2 + 250, '22px SerifB', rgba(P.inkSoft));
    text(ctx, '《大学录取与婚姻的稳定性》', 0, -h / 2 + 300, '30px Kai', rgba(P.red));
    for (let i = 0; i < 6; i++) { const ww = i === 5 ? 300 : 520; ctx.fillStyle = rgba(P.ink, 0.12); ctx.fillRect(-260, -h / 2 + 340 + i * 26, ww, 9); }
    // a tiny matching diagram
    const dk = ap(t, CH('A3', 3), 0.8);
    for (let i = 0; i < 4; i++) {
      const y1 = 200 + (i - 1.5) * 30;
      dot(ctx, -120, y1 - 10, 7, MEN[i].col); dot(ctx, 120, y1 - 10, 7, WOMEN[i].col);
    }
    MOPT.forEach((w, m) => { const y1 = 190 + (m - 1.5) * 30, y2 = 190 + (w - 1.5) * 30; thread(ctx, -110, y1, 110, y2, { p: eio(clamp(dk * 1.4 - m * 0.12)), sag: 6, lw: 3 }); });
  }));
  // page-count tag
  withAlpha(ctx, ap(t, charT('A3', '七页'), 0.3), () => seal(ctx, '7页', 880, 690, 86, P.red, 0.12));
  stamp(ctx, '1962', 210, 1240, 64, t - (S('A3') + 0.15), -0.18, P.red);
}
function paperCues() {
  cue(S('A3') - 0.1, 'paper', 0.9); cue(S('A3') + 0.15, 'stamp', 0.8);
  cue(K('A3', 0) - 0.2, 'pop', 0.5); cue(K('A3', 1) - 0.2, 'pop', 0.5); cue(charT('A3', '七页'), 'pop', 0.6);
  cue(CH('A3', 3), 'string', 0.4);
}

// ================================================================== UNSTABLE (稳定的定义)
const UP = { c: { x: 300, y: 760 }, t: { x: 780, y: 760 }, s: { x: 300, y: 1110 }, l: { x: 780, y: 1110 } };
function unstable(ctx, t, sc) {
  const tB = S('B3');
  const tElope = K('B5');
  const elope = eio(ramp(t, tElope, tElope + 0.9));
  const hideAll = ap(t, S('B6') - 0.2, 0.5);
  // B1: the word 稳定 as a heading
  withAlpha(ctx, fade(t, sc.t0 + 0.1, tB + 0.2, 0.4, 0.4), () => {
    text(ctx, '什么样的配对，才算好？', W / 2, 760, '62px SerifH', rgba(P.ink));
    const kk = ap(t, K('B1') - 0.1, 0.5);
    withXform(ctx, W / 2, 960, eback(kk), 0, () => { ctx.globalAlpha *= clamp(kk * 2); spaced(ctx, '稳定', 0, 40, '160px SerifH', rgba(P.red), 20); });
  });
  withAlpha(ctx, ap(t, tB - 0.2, 0.5) * (1 - hideAll), () => {
    // couples
    const c = MEN[1], tw = WOMEN[0], s = MEN[0], l = WOMEN[2];
    const ca = ap(t, charT('B3', '阿川'), 0.4), sa = ap(t, charT('B3', '阿山'), 0.4);
    // elopers slide to the centre
    const cx = lerp(UP.c.x, 470, elope), cy = lerp(UP.c.y, 935, elope);
    const lx = lerp(UP.l.x, 610, elope), ly = lerp(UP.l.y, 935, elope);
    // old threads
    const sn = ramp(t, tElope, tElope + 0.9);
    if (t < tElope) {
      thread(ctx, UP.c.x + 56, UP.c.y + 20, UP.t.x - 56, UP.t.y + 20, { p: eio(ramp(t, charT('B3', '阿川') + 0.2, charT('B3', '阿川') + 0.9)), wob: 3, t });
      thread(ctx, UP.s.x + 56, UP.s.y + 20, UP.l.x - 56, UP.l.y + 20, { p: eio(ramp(t, charT('B3', '阿山') + 0.2, charT('B3', '阿山') + 0.9)), wob: 3, t });
    } else {
      threadSnap(ctx, UP.c.x + 56, UP.c.y + 20, UP.t.x - 56, UP.t.y + 20, sn);
      threadSnap(ctx, UP.s.x + 56, UP.s.y + 20, UP.l.x - 56, UP.l.y + 20, sn);
    }
    // the temptation line between 川 and 梨
    const tempt = fade(t, S('B4'), tElope + 0.2, 0.5, 0.3);
    withAlpha(ctx, tempt, () => {
      line(ctx, UP.c.x + 50, UP.c.y + 30, UP.l.x - 50, UP.l.y - 30, P.redSoft, 0.9, 4, [8, 12]);
      for (let i = 0; i < 3; i++) {
        const u = ((t * 0.5 + i / 3) % 1);
        heart(ctx, lerp(UP.c.x + 50, UP.l.x - 50, u), lerp(UP.c.y + 30, UP.l.y - 30, u), 14, P.red, Math.sin(u * Math.PI));
      }
    });
    const tempted = t > S('B4') + 0.3;
    const moodC = t > tElope ? 'happy' : tempted ? 'love' : 'neutral';
    const moodL = t > tElope ? 'happy' : t > CH('B4', 1) ? 'love' : 'neutral';
    const moodT = t > tElope + 0.3 ? 'shock' : 'neutral', moodS = t > tElope + 0.3 ? 'shock' : 'neutral';
    F.person(ctx, UP.t.x, UP.t.y, tw, { t, mood: moodT, a: ca, look: -0.6 });
    F.person(ctx, UP.s.x, UP.s.y, s, { t, mood: moodS, a: sa, look: 0.6 });
    F.person(ctx, cx, cy, c, { t, mood: moodC, a: ca, look: 0.6 });
    F.person(ctx, lx, ly, l, { t, mood: moodL, a: sa, look: -0.6 });
    seal(ctx, c.ch, cx - 100, cy - 52, 44, c.col, -0.06, ca); seal(ctx, tw.ch, UP.t.x + 100, UP.t.y - 52, 44, tw.col, 0.06, ca);
    seal(ctx, s.ch, UP.s.x - 100, UP.s.y - 52, 44, s.col, -0.06, sa); seal(ctx, l.ch, lx + 100, ly - 52, 44, l.col, 0.06, sa);
    // preference chips explain why
    const pk1 = fade(t, S('B4'), tElope + 0.5, 0.4, 0.4), pk2 = fade(t, CH('B4', 1), tElope + 0.5, 0.4, 0.4);
    F.prefChips(ctx, UP.c.x, UP.c.y + 98, MPREF[1], WOMEN, { a: pk1, hi: 0 });
    F.prefChips(ctx, UP.l.x, UP.l.y + 98, WPREF[2], MEN, { a: pk2, hi: 1 });
    withAlpha(ctx, pk2, () => text(ctx, '川 比 山 更好', UP.l.x, UP.l.y + 160, '30px Kai', rgba(P.red)));
    withAlpha(ctx, pk1, () => text(ctx, '最喜欢 梨', UP.c.x, UP.c.y + 160, '30px Kai', rgba(P.red)));
    // elope hearts + stamp
    if (t > tElope + 0.6) for (let i = 0; i < 5; i++) { const u = ((t - tElope) * 0.7 + i / 5) % 1; heart(ctx, 540 + Math.sin(i * 2.1 + u * 4) * 50, 860 - u * 160, 12 + 6 * hash(i), P.red, Math.sin(u * Math.PI) * 0.9); }
    stamp(ctx, '不稳定', W / 2, 600, 92, t - (CH('B5', 1) + 0.3), -0.12, P.red);
  });
  // B6: definition card
  const dk = fade(t, S('B6') - 0.1, S('B7') + 0.1, 0.5, 0.4);
  withAlpha(ctx, dk, () => withXform(ctx, W / 2, 920, lerp(0.94, 1, eo(dk)), 0, () => {
    paperRect(ctx, -420, -220, 840, 440, 14, P.paperHi);
    ctx.strokeStyle = rgba(P.red, 0.7); ctx.lineWidth = 3; roundRect(ctx, -400, -200, 800, 400, 10); ctx.stroke();
    spaced(ctx, '稳定', 0, -60, '110px SerifH', rgba(P.red), 14);
    text(ctx, '＝ 找不出任何两个人', 0, 50, '52px Kai', rgba(P.ink));
    text(ctx, '想丢下伴侣、一起私奔', 0, 125, '52px Kai', rgba(P.ink));
  }));
  // B7: two questions
  const qk = ap(t, S('B7') - 0.05, 0.5);
  withAlpha(ctx, qk, () => {
    const a1 = pop(t, CH('B7', 0) + 0.6, 0.5), a2 = pop(t, charT('B7', '怎么找'), 0.5);
    withXform(ctx, W / 2, 820, a1, -0.03, () => { text(ctx, '一定存在吗？', 0, 0, '92px SerifH', rgba(P.ink)); });
    withXform(ctx, W / 2, 1020, a2, 0.03, () => { text(ctx, '怎么找？', 0, 0, '92px SerifH', rgba(P.red)); });
  });
}
function unstableCues() {
  cue(K('B1') - 0.1, 'ding', 0.7);
  cue(charT('B3', '阿川'), 'pop', 0.5); cue(charT('B3', '阿川') + 0.2, 'string', 0.5);
  cue(charT('B3', '阿山'), 'pop', 0.5); cue(charT('B3', '阿山') + 0.2, 'string', 0.5);
  cue(S('B4') + 0.2, 'heart', 0.4);
  cue(K('B5'), 'snap', 1.0); cue(K('B5') + 0.06, 'snap', 0.8); cue(K('B5') + 0.2, 'whoosh', 0.6);
  cue(CH('B5', 1) + 0.3, 'stamp', 1.0); SHAKES.push({ t: CH('B5', 1) + 0.3, amp: 12 });
  cue(S('B6') - 0.1, 'paper', 0.7);
  cue(CH('B7', 0) + 0.6, 'pop', 0.6); cue(charT('B7', '怎么找'), 'pop', 0.7);
}

// ================================================================== RULES
const RULES = [
  { n: '一', title: '表白', sub: '单身的人，向排名最高、', sub2: '还没拒绝过他的人表白', seg: 'C2' },
  { n: '二', title: '只留一个', sub: '被表白的人，只留下最喜欢的，', sub2: '其余的，全部拒绝', seg: 'C3' },
  { n: '三', title: '找下一个', sub: '被拒绝的人，去找下一个；', sub2: '直到，没人再被拒绝', seg: 'C5' },
];
function rules(ctx, t, sc) {
  withAlpha(ctx, ap(t, sc.t0, 0.5), () => text(ctx, '三条规则', W / 2, 400, '64px SerifH', rgba(P.ink)));
  const active = t < S('C3') - 0.1 ? 0 : t < S('C5') - 0.1 ? 1 : 2;
  RULES.forEach((r, i) => {
    const k = ap(t, i === 0 ? S('C1') + 0.3 + i * 0.15 : S('C1') + 0.3 + i * 0.15, 0.5);
    const lit = t < S('C2') - 0.1 ? 1 : (i === active ? 1 : 0.42);
    const y = 540 + i * 300;
    withAlpha(ctx, k * lit, () => withXform(ctx, W / 2, y + 120 + (1 - k) * 30, i === active && t > S('C2') - 0.1 ? 1.02 : 1, 0, () => {
      paperRect(ctx, -450, -125, 900, 250, 14, P.paperHi);
      seal(ctx, r.n, -360, -20, 100, P.red, -0.06);
      text(ctx, r.title, -270, -40, '54px SerifH', rgba(P.ink), 'left');
      text(ctx, r.sub, -270, 22, '34px Kai', rgba(P.inkSoft), 'left');
      text(ctx, r.sub2, -270, 70, '34px Kai', rgba(P.inkSoft), 'left');
    }));
  });
  // card 1 mini animation: heart flying
  const c1 = fade(t, S('C2') + 0.5, S('C3'), 0.3, 0.3);
  withAlpha(ctx, c1, () => {
    const u = ((t - S('C2')) * 0.7) % 1;
    F.person(ctx, 750, 665, MEN[0], { s: 0.48, t, mood: 'love', noShadow: true });
    F.person(ctx, 900, 665, WOMEN[3], { s: 0.48, t, mood: 'shy', noShadow: true });
    heart(ctx, lerp(785, 870, u), 620 - Math.sin(u * Math.PI) * 40, 14, P.red, Math.sin(u * Math.PI));
  });
  // card 2: one kept, two rejected, then 暂
  const c2 = fade(t, S('C3') + 0.3, S('C5'), 0.3, 0.3);
  withAlpha(ctx, c2, () => {
    F.person(ctx, 900, 965, WOMEN[0], { s: 0.48, t, mood: 'think', noShadow: true });
    [0, 1, 2].forEach((i) => {
      const x = 640 + i * 70, y = 965;
      const rej = i !== 1 && t > charT('C3', '其余');
      F.person(ctx, x, y + (rej ? 6 : 0), MEN[i + 1], { s: 0.34, t, mood: rej ? 'sad' : i === 1 && t > charT('C3', '只留') ? 'happy' : 'love', a: rej ? 0.5 : 1, noShadow: true });
      if (rej) { line(ctx, x - 16, y - 50, x + 16, y - 18, P.red, 0.9, 5); line(ctx, x + 16, y - 50, x - 16, y - 18, P.red, 0.9, 5); }
    });
  });
  const zk = t - K('C4');
  if (zk > 0 && t < S('C5') + 0.2) withAlpha(ctx, 1 - ramp(t, S('C5') - 0.1, S('C5') + 0.2), () => {
    stamp(ctx, '暂', 820, 900, 86, zk, 0.12, P.red);
    withAlpha(ctx, ap(t, K('C4') + 0.3, 0.4), () => text(ctx, '来了更好的，随时可换', 760, 1060, '32px Kai', rgba(P.red)));
  });
  // card 3: arrow to next chip
  const c3 = fade(t, S('C5') + 0.3, E('C5') + 1.5, 0.3, 0.4);
  withAlpha(ctx, c3, () => {
    const u = ramp(t, S('C5') + 0.6, S('C5') + 1.4);
    F.prefChips(ctx, 820, 1265, MPREF[0], WOMEN, { s: 0.9, crossed: new Set(u > 0.2 ? [0] : []), ptr: u > 0.6 ? 1 : 0 });
    const end = ap(t, charT('C5', '直到'), 0.4);
    withAlpha(ctx, end, () => { E_.text(ctx, '✓ 无人被拒 → 结束', 820, 1335, '30px SerifB', rgba(P.green)); });
  });
}
function rulesCues() {
  cue(S('C1') + 0.2, 'paper', 0.6); for (let i = 0; i < 3; i++) cue(S('C1') + 0.3 + i * 0.15, 'pop', 0.35);
  cue(S('C2') - 0.1, 'tick', 0.6); cue(S('C2') + 0.8, 'heart', 0.3);
  cue(S('C3') - 0.1, 'tick', 0.6); cue(charT('C3', '其余'), 'snap', 0.6);
  cue(K('C4'), 'stamp', 0.9);
  cue(S('C5') - 0.1, 'tick', 0.6); cue(S('C5') + 0.7, 'snap', 0.5); cue(S('C5') + 1.2, 'pop', 0.5); cue(charT('C5', '直到'), 'ding', 0.5);
}

// ================================================================== THE BOARD (cast → menfirst → result1 → womenfirst)
const RUN_M = buildRun(MENFIRST, 'm', [
  { prop: S('E1') + 0.9, dur: 0.9, decide: charT('E3', '阿风被拒') },
  { prop: charT('E4', '阿风去找'), dur: 1.2, decide: charT('E5', '阿山被挤走') },
  { prop: charT('E7', '阿山去找'), dur: 0.9, decide: charT('E7', '阿云被挤走') },
  { prop: charT('E8', '阿云去找'), dur: 0.9, decide: charT('E8', '小杏答应') },
], S('E9') + 0.4);
const RUN_W = buildRun(WOMENFIRST, 'f', [
  { prop: ['小桃找', '小杏找', '小梨找', '小荷找'].map((s) => charT('G2', s)), dur: 0.8, decide: S('G3') },
], charT('G3', '一轮就结束'));

// domino strip (连锁反应): items appear as the chain unfolds
const CHAIN = [
  { side: 'm', i: 2, x: true, t: () => RUN_M.times[0].decide },
  { side: 'f', i: 3, t: () => RUN_M.times[1].prop + 1.2 },
  { side: 'm', i: 0, x: true, t: () => RUN_M.times[1].decide },
  { side: 'f', i: 0, t: () => RUN_M.times[2].prop + 0.9 },
  { side: 'm', i: 3, x: true, t: () => RUN_M.times[2].decide },
  { side: 'f', i: 1, ok: true, t: () => RUN_M.times[3].prop + 0.9 },
];
function chainStrip(ctx, t, a) {
  if (a <= 0.003) return;
  const y = 455, gap = 96, x0 = W / 2 - gap * 2.5;
  const pulse = fade(t, K('E6') - 0.1, E('E6') + 0.4, 0.2, 0.4);
  withAlpha(ctx, a, () => {
    CHAIN.forEach((c, n) => {
      const k = ap(t, c.t(), 0.35);
      if (k <= 0) return;
      const x = x0 + n * gap;
      if (n > 0) withAlpha(ctx, k, () => arrow(ctx, x - gap + 30, y, x - 30, y, P.red, 0.8 + 0.2 * pulse, 3, 10));
      const p = people(c.side)[c.i];
      seal(ctx, p.ch, x, y, 44 * eback(k) * (1 + 0.12 * pulse * Math.sin(t * 12 - n)), c.x ? mix(p.col, P.paperLo, 0.45) : p.col, 0, clamp(k * 2));
      if (c.x) withAlpha(ctx, k, () => { line(ctx, x - 14, y + 14, x + 14, y - 14, P.ink, 0.9, 4); });
      if (c.ok) withAlpha(ctx, k, () => heart(ctx, x + 22, y - 22, 9, P.red));
    });
    if (pulse > 0) glow(ctx, W / 2, y, 300, P.red, 0.12 * pulse);
  });
}

function board(ctx, t, sc) {
  const tCast = S('D2');
  // who appears when (D2 names)
  const nameT = (side, i) => charT('D2', people(side)[i].name);
  const appear = (side, i) => ap(t, nameT(side, i) - 0.1, 0.45);
  const chipReveal = (side, i) => (t - (CH('D3', 0) + 0.1 + i * 0.12 + (side === 'f' ? 0.25 : 0))) * 2.2;
  const tG = S('G1') + 0.2;                       // women-first begins
  const inW = t >= tG;
  const run = inW ? RUN_W : RUN_M;
  const st = t >= S('E1') - 0.2 ? runState(run, t) : null;
  const fadeM = 1 - ramp(t, tG, tG + 0.6);        // men-first threads fade out
  // ---- banner
  const bA = ap(t, K('D4') - 0.1, 0.4);
  let label = '第一次 · 男生先开口', dir = 1, round = 0;
  if (t >= S('E1') - 0.3) round = RUN_M.times.filter((x) => t >= x.prop - 0.4).length;
  if (inW) { label = '第二次 · 女生先开口'; dir = -1; round = t >= S('G2') - 0.3 ? 1 : 0; }
  const flip = inW ? eio(ramp(t, tG, tG + 0.5)) : 1;
  if (t < tG + 0.25 && inW) { label = '第一次 · 男生先开口'; dir = 1; }
  withAlpha(ctx, bA, () => {
    ctx.save(); ctx.translate(0, 330); ctx.scale(1, inW ? Math.abs(Math.cos(flip * Math.PI)) * 0.9 + 0.1 : 1); ctx.translate(0, -330);
    L.banner(ctx, { label, dir, round, total: inW ? 1 : 4 });
    ctx.restore();
  });
  // D3: arrow explaining chip order
  withAlpha(ctx, fade(t, CH('D3', 0) + 0.3, S('D4') + 0.3, 0.4, 0.4), () => {
    text(ctx, '最喜欢', MX - 69, ROWS[0] + 160, '26px Kai', rgba(P.red));
    arrow(ctx, MX - 30, ROWS[0] + 152, MX + 40, ROWS[0] + 152, P.red, 0.9, 3, 9);
    text(ctx, '最不喜欢', MX + 105, ROWS[0] + 160, '26px Kai', rgba(P.inkSoft));
    text(ctx, '最喜欢', WX - 69, ROWS[0] + 160, '26px Kai', rgba(P.red));
    arrow(ctx, WX - 30, ROWS[0] + 152, WX + 40, ROWS[0] + 152, P.red, 0.9, 3, 9);
    text(ctx, '最不喜欢', WX + 105, ROWS[0] + 160, '26px Kai', rgba(P.inkSoft));
  });
  // ---- threads
  if (!inW || fadeM > 0) drawRunThreads(ctx, t, RUN_M, inW ? fadeM : 1);
  if (inW) drawRunThreads(ctx, t, RUN_W, 1);
  // E2: collision highlight on 梨
  const coll = fade(t, S('E2'), RUN_M.times[0].decide + 0.3, 0.3, 0.3);
  if (coll > 0) { const { x, y } = pos('f', 2); glow(ctx, x, y - 20, 130, P.gold, 0.35 * coll); bubble(ctx, x - 20, y - 150, 90, 64, coll, 10, (g) => text(g, '？', 0, 4, '44px SerifH', rgba(P.ink), 'center', 'middle')); }
  // E5: 荷 compares 山 vs 风
  const cmp = fade(t, S('E5'), RUN_M.times[1].decide + 0.2, 0.3, 0.3);
  if (cmp > 0) { const { x, y } = pos('f', 3); glow(ctx, x, y - 20, 130, P.gold, 0.35 * cmp); }
  // ---- people
  const mood = (side, i) => {
    if (!st) return t > appear(side, i) ? 'neutral' : 'neutral';
    if (coll > 0.5 && side === 'f' && i === 2) return 'think';
    if (cmp > 0.5 && side === 'f' && i === 3) return 'think';
    let m = st.mood[side + i];
    if (inW && t < S('G2') - 0.2) m = 'neutral';
    return m;
  };
  const chips = (side, i) => {
    if (t < CH('D3', 0)) return null;
    const o = { reveal: chipReveal(side, i) };
    if (st && side === run.side) { o.crossed = st.crossed[i]; o.ptr = st.ptr[i]; }
    // result1: highlight where everyone ended up
    if (rankK > 0 && side === 'm' && !inW) o.hi = MPREF[i].indexOf(MOPT[i]);
    if (inW && t > K('G4') - 0.2 && side === 'f') o.hi = 0;
    return o;
  };
  const rankK = ap(t, S('F2') - 0.1, 0.4) * (1 - ap(t, tG - 0.3, 0.3));
  drawPeople(ctx, t, { appear, mood, chips });
  // ---- rank badges
  if (rankK > 0) for (let m = 0; m < 4; m++) rankBadge(ctx, 'm', m, rankOf(MPREF, m, MOPT[m]), clamp(rankK * 1.5 - (m === 1 ? 0 : 0.3 + m * 0.08)));
  const wRank = ap(t, K('G4') - 0.1, 0.4) * (1 - ap(t, E('G5') + 0.2, 0.3));
  if (wRank > 0) for (let w = 0; w < 4; w++) rankBadge(ctx, 'f', w, 1, clamp(wRank * 1.5 - w * 0.12));
  // ---- domino strip
  chainStrip(ctx, t, (t >= S('E3') ? 1 : 0) * (1 - ap(t, S('F1'), 0.4)));
  // ---- E9: done
  withAlpha(ctx, 1 - ap(t, S('F1'), 0.3), () => stamp(ctx, '结束', W / 2, 1335, 54, t - charT('E9', '结束'), -0.08, P.red));
  // ---- F1: stability check — every non-matched pair, one by one
  const chk0 = S('F1') + 0.4, chk1 = CH('F1', 1) + 0.2;
  if (t > chk0 && t < E('F1') + 0.5 && !inW) {
    const pairs = [];
    for (let m = 0; m < 4; m++) for (let w = 0; w < 4; w++) if (MOPT[m] !== w) pairs.push([m, w]);
    const n = Math.min(pairs.length, Math.floor((t - chk0) / ((chk1 - chk0) / pairs.length)) + 1);
    const fadeAll = 1 - ramp(t, chk1, chk1 + 0.4);
    pairs.slice(0, n).forEach(([m, w], idx) => {
      const recent = idx === n - 1 && fadeAll >= 1;
      const [x1, y1] = hand('m', m), [x2, y2] = hand('f', w);
      line(ctx, x1, y1 - 30, x2, y2 - 30, P.inkFaint, (recent ? 0.7 : 0.18) * fadeAll, recent ? 3 : 2, [6, 8]);
    });
    withAlpha(ctx, 1 - fadeAll * 0, () => {
      const cnt = Math.min(n, pairs.length);
      text(ctx, `逐对检查  ${cnt}/12   想私奔的：0`, W / 2, 1345, '32px SerifB', rgba(P.inkSoft, 0.9 * (1 - ramp(t, K('F1') + 0.6, K('F1') + 1)))); });
  }
  // the green stamp fades before F2 so the rank badges read
  withAlpha(ctx, 1 - ap(t, S('F2') - 0.2, 0.4), () => stamp(ctx, '稳定', W / 2, 925, 120, t - K('F1'), -0.1, P.green));
  // ---- G3/G5
  withAlpha(ctx, fade(t, charT('G3', '一轮就结束'), K('G4'), 0.3, 0.3), () => text(ctx, '一轮结束 · 没有任何拒绝', W / 2, 1345, '34px SerifB', rgba(P.green)));
  stamp(ctx, '稳定', W / 2, 925, 120, t - S('G5') - 0.1, 0.08, P.green);
  withAlpha(ctx, ap(t, charT('G5', '四对人'), 0.4), () => text(ctx, '四对，全换了', W / 2, 1345, '40px SerifH', rgba(P.red)));
}
const boardScene = board;
function boardCues() {
  for (const side of ['m', 'f']) for (let i = 0; i < 4; i++) cue(charT('D2', people(side)[i].name) - 0.1, 'pop', 0.4);
  cue(CH('D3', 0) + 0.1, 'shuffle', 0.6);
  cue(K('D4') - 0.1, 'whoosh', 0.6); cue(K('D4'), 'ding', 0.5);
  runCues(RUN_M);
  cue(S('E2'), 'think', 0.5); cue(S('E5') + 0.1, 'think', 0.4);
  CHAIN.forEach((c) => cue(c.t(), 'tick', 0.5));
  cue(K('E6') - 0.05, 'domino', 0.9);
  cue(RUN_M.final, 'chime', 0.6); cue(charT('E9', '结束'), 'stamp', 0.6);
  const chk0 = S('F1') + 0.4, chk1 = CH('F1', 1) + 0.2;
  for (let i = 0; i < 12; i++) cue(chk0 + i * (chk1 - chk0) / 12, 'tick', 0.3);
  cue(K('F1'), 'stamp', 1.0);
  for (let m = 0; m < 4; m++) cue(S('F2') + (m === 1 ? 0 : 0.2 + m * 0.05), 'pop', 0.4);
  cue(S('G1') + 0.2, 'whoosh', 0.7); cue(S('G1') + 0.4, 'snap', 0.3);
  runCues(RUN_W);
  cue(charT('G3', '一轮就结束'), 'chime', 0.7);
  cue(K('G4') - 0.1, 'ding', 0.6);
  cue(S('G5') + 0.1, 'stamp', 0.9);
}

// ================================================================== COMPARE
function mini(ctx, t, cy, pairsM, title, propSide, k, hiProp, hiRecv) {
  if (k <= 0.003) return;
  const xs = { m: 280, f: 800 }, gap = 88, s = 0.48;
  const yOf = (i) => cy - 112 + i * gap;
  withAlpha(ctx, k, () => {
    paperRect(ctx, 70, cy - 232, 940, 464, 16, P.paperHi);
    text(ctx, title, W / 2, cy - 172, '38px SerifH', rgba(P.ink));
    pairsM.forEach((w, m) => {
      const [x1, y1] = [xs.m + 34, yOf(m) + 8], [x2, y2] = [xs.f - 34, yOf(w) + 8];
      thread(ctx, x1, y1, x2, y2, { sag: 20, lw: 4 });
    });
    for (const side of ['m', 'f']) for (let i = 0; i < 4; i++) {
      const p = people(side)[i];
      const isProp = side === propSide;
      const j = side === 'm' ? pairsM[i] : pairsM.indexOf(i);
      const rank = side === 'm' ? rankOf(MPREF, i, j) : rankOf(WPREF, i, j);
      const happy = rank === 1 ? 'happy' : rank === 2 ? 'neutral' : 'sad';
      F.person(ctx, xs[side], yOf(i), p, { s, t, mood: happy, noShadow: true, tear: false });
      const bx = side === 'm' ? xs.m - 120 : xs.f + 120;
      const hl = isProp ? hiProp : hiRecv;
      const col = rank === 1 ? P.gold : rank === 2 ? [150, 128, 100] : P.inkFaint;
      if (hl > 0) glow(ctx, bx, yOf(i) - 4, 60, isProp ? P.gold : [120, 120, 140], 0.4 * hl);
      ctx.fillStyle = rgba(col); roundRect(ctx, bx - 40, yOf(i) - 24, 80, 40, 20); ctx.fill();
      text(ctx, `第${rank}`, bx, yOf(i) - 3, '26px SerifH', rgba(P.white), 'center', 'middle');
    }
  });
}
function compare(ctx, t, sc) {
  const k1 = ap(t, sc.t0 + 0.05, 0.5), k2 = ap(t, sc.t0 + 0.35, 0.5);
  const h1 = fade(t, S('K2'), CH('K2', 1), 0.3, 0.3) + ap(t, K('K4'), 0.4) * (1 - ap(t, S('K5'), 0.3));
  const h2 = fade(t, CH('K2', 1), S('K3'), 0.3, 0.3) + ap(t, K('K4'), 0.4) * (1 - ap(t, S('K5'), 0.3));
  const r = ap(t, S('K5'), 0.4);
  mini(ctx, t, 690, MOPT, '男生先开口 →', 'm', k1, clamp(h1), r);
  mini(ctx, t, 1180, WOPT, '← 女生先开口', 'f', k2, clamp(h2), r);
  // 如愿 tags
  withAlpha(ctx, ap(t, charT('K2', '男生如愿'), 0.3), () => stamp(ctx, '男生如愿', 900, 488, 44, t - charT('K2', '男生如愿'), 0.1, P.red));
  withAlpha(ctx, ap(t, charT('K2', '女生如愿'), 0.3), () => stamp(ctx, '女生如愿', 180, 978, 44, t - charT('K2', '女生如愿'), -0.1, P.red));
  // the theorem
  const th = ap(t, S('K3') + 0.2, 0.4);
  withAlpha(ctx, th, () => {
    ctx.fillStyle = rgba(P.paperHi, 0.94); roundRect(ctx, 90, 300, 900, 116, 20); ctx.fill();
    ctx.strokeStyle = rgba(P.red, 0.6); ctx.lineWidth = 3; ctx.stroke();
    const line1 = t < K('K4') - 0.1 ? '数学可以证明' : t < S('K5') ? '先开口的一方 → 最好的稳定结果' : '等着被挑的一方 → 最差的稳定结果';
    text(ctx, line1, W / 2, 374, '44px SerifH', rgba(t >= S('K5') ? P.inkSoft : P.red));
  });
}
function compareCues() {
  cue(sceneT('compare') + 0.05, 'whoosh', 0.5); cue(sceneT('compare') + 0.35, 'paper', 0.4);
  cue(charT('K2', '男生如愿'), 'stamp', 0.6); cue(charT('K2', '女生如愿'), 'stamp', 0.6);
  cue(S('K3') + 0.2, 'pop', 0.5); cue(K('K4') - 0.1, 'ding', 0.8); cue(S('K5'), 'dud', 0.6);
}

// ================================================================== REAL WORLD
function hospital(ctx, x, y, s, a = 1) {
  withAlpha(ctx, a, () => withXform(ctx, x, y, s, 0, () => {
    ctx.fillStyle = rgba(P.white); ctx.fillRect(-70, -90, 140, 150);
    ctx.strokeStyle = rgba(P.ink, 0.85); ctx.lineWidth = 3; ctx.strokeRect(-70, -90, 140, 150);
    ctx.fillStyle = rgba(P.red); ctx.fillRect(-12, -76, 24, 60); ctx.fillRect(-30, -58, 60, 24);
    ctx.fillStyle = rgba(P.sky, 0.55); for (let i = 0; i < 3; i++) ctx.fillRect(-52 + i * 40, 0, 24, 24);
    ctx.fillStyle = rgba(P.inkSoft); ctx.fillRect(-14, 28, 28, 32);
  }));
}
function school(ctx, x, y, s, a = 1) {
  withAlpha(ctx, a, () => withXform(ctx, x, y, s, 0, () => {
    ctx.fillStyle = rgba(P.paperHi); ctx.beginPath(); ctx.moveTo(-90, -40); ctx.lineTo(0, -100); ctx.lineTo(90, -40); ctx.closePath(); ctx.fill();
    ctx.strokeStyle = rgba(P.ink, 0.85); ctx.lineWidth = 3; ctx.stroke();
    ctx.fillStyle = rgba(P.white); ctx.fillRect(-80, -40, 160, 100); ctx.strokeRect(-80, -40, 160, 100);
    for (let i = 0; i < 4; i++) { ctx.fillStyle = rgba(P.inkSoft); ctx.fillRect(-66 + i * 38, -26, 10, 76); }
    dot(ctx, 0, -66, 12, P.gold);
  }));
}
function real(ctx, t, sc) {
  const partB = ap(t, S('R4') - 0.1, 0.5);
  // R2/R3: residency match
  withAlpha(ctx, 1 - partB, () => {
    withAlpha(ctx, ap(t, sc.t0, 0.4), () => {
      text(ctx, '美国 · 住院医师匹配', W / 2, 420, '56px SerifH', rgba(P.ink));
      text(ctx, 'National Resident Matching Program', W / 2, 470, '28px SerifB', rgba(P.inkSoft));
    });
    const studs = [MEN[0], WOMEN[1], MEN[1], WOMEN[3]];
    studs.forEach((p, i) => {
      const k = ap(t, sc.t0 + 0.3 + i * 0.1, 0.4);
      const y = 640 + i * 180;
      F.person(ctx, 220, y, p, { s: 0.75, t, mood: t > K('R3') ? 'happy' : 'neutral', a: k });
      // mortarboard
      withAlpha(ctx, k, () => { ctx.fillStyle = rgba(P.ink); ctx.beginPath(); ctx.moveTo(180, y - 100); ctx.lineTo(220, y - 116); ctx.lineTo(260, y - 100); ctx.lineTo(220, y - 86); ctx.closePath(); ctx.fill(); line(ctx, 250, y - 100, 256, y - 76, P.gold, 1, 3); });
    });
    [0, 1, 2].forEach((i) => hospital(ctx, 840, 720 + i * 230, 0.95, ap(t, sc.t0 + 0.5 + i * 0.12, 0.4)));
    // threads: direction flips at R3
    const flipK = eio(ramp(t, K('R3') - 0.2, K('R3') + 0.4));
    const assign = [0, 2, 1, 2];
    assign.forEach((h, i) => {
      const sx = 290, sy = 660 + i * 180, hx = 760, hy = 740 + h * 230;
      const p = eio(ramp(t, CH('R2', 1) + i * 0.15, CH('R2', 1) + 0.8 + i * 0.15));
      if (flipK < 0.5) thread(ctx, hx, hy, sx, sy, { p, a: 1 - flipK * 2, lw: 4, dash: [12, 8] });
      else thread(ctx, sx, sy, hx, hy, { p: eio((flipK - 0.5) * 2), lw: 5 });
    });
    // counter
    withAlpha(ctx, ap(t, CH('R2', 2), 0.4), () => {
      ctx.fillStyle = rgba(P.paperHi, 0.94); roundRect(ctx, 340, 1290, 400, 80, 40); ctx.fill();
      text(ctx, '每年 · 几万人', W / 2, 1345, '42px SerifH', rgba(P.red));
    });
    // R3: who proposes
    const lb = ap(t, S('R3') - 0.1, 0.4);
    withAlpha(ctx, lb, () => {
      const l = flipK < 0.5 ? '医院先开口 →' : '← 学生先开口';
      ctx.fillStyle = rgba(P.paperHi, 0.94); roundRect(ctx, 300, 525, 480, 70, 35); ctx.fill();
      ctx.strokeStyle = rgba(P.red, 0.7); ctx.lineWidth = 3; ctx.stroke();
      text(ctx, l, W / 2, 573, '38px SerifB', rgba(flipK < 0.5 ? P.inkSoft : P.red));
    });
    stamp(ctx, '1998', 880, 560, 54, t - (K('R3') + 0.3), 0.14, P.red, '新算法启用');
  });
  // R4: schools
  withAlpha(ctx, partB, () => {
    text(ctx, '公立学校招生', W / 2, 460, '56px SerifH', rgba(P.ink));
    [['纽约', 300], ['波士顿', 780]].forEach(([nm, x], i) => {
      const k = ap(t, charT('R4', nm) - 0.1, 0.45);
      school(ctx, x, 800, 1.3, k);
      withAlpha(ctx, k, () => text(ctx, nm, x, 960, '54px SerifH', rgba(P.ink)));
      for (let j = 0; j < 3; j++) F.person(ctx, x - 110 + j * 110, 1180, j % 2 ? WOMEN[(i * 2 + j) % 4] : MEN[(i + j) % 4], { s: 0.6, t, mood: 'happy', a: ap(t, charT('R4', nm) + 0.3 + j * 0.1, 0.4) });
    });
  });
}
function realCues() {
  const t0 = sceneT('real');
  cue(t0, 'whoosh', 0.6); for (let i = 0; i < 4; i++) cue(t0 + 0.3 + i * 0.1, 'pop', 0.25);
  for (let i = 0; i < 4; i++) cue(CH('R2', 1) + i * 0.15, 'string', 0.3);
  cue(CH('R2', 2), 'ding', 0.5);
  cue(K('R3') - 0.2, 'whoosh', 0.5); cue(K('R3') + 0.3, 'stamp', 0.8);
  cue(charT('R4', '纽约') - 0.1, 'pop', 0.6); cue(charT('R4', '波士顿') - 0.1, 'pop', 0.6);
}

// ================================================================== NOBEL
function medal(ctx, x, y, r, t, a = 1) {
  withAlpha(ctx, a, () => {
    // ribbon
    ctx.fillStyle = rgba(P.red); ctx.beginPath(); ctx.moveTo(x - 50, y - r - 140); ctx.lineTo(x - 10, y - r - 140); ctx.lineTo(x + 10, y - r + 10); ctx.lineTo(x - 30, y - r + 10); ctx.closePath(); ctx.fill();
    ctx.fillStyle = rgba(P.redDeep); ctx.beginPath(); ctx.moveTo(x + 50, y - r - 140); ctx.lineTo(x + 10, y - r - 140); ctx.lineTo(x - 10, y - r + 10); ctx.lineTo(x + 30, y - r + 10); ctx.closePath(); ctx.fill();
    glow(ctx, x, y, r * 2, P.goldHi, 0.35);
    const g = ctx.createRadialGradient(x - r * 0.3, y - r * 0.3, r * 0.1, x, y, r);
    g.addColorStop(0, 'rgb(255,232,160)'); g.addColorStop(0.6, 'rgb(214,166,72)'); g.addColorStop(1, 'rgb(160,112,40)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
    ring(ctx, x, y, r * 0.84, [140, 96, 30], 0.6, 3);
    text(ctx, '2012', x, y - 8, `${Math.round(r * 0.42)}px SerifH`, 'rgba(110,70,20,0.9)', 'center', 'middle');
    text(ctx, '经济学奖', x, y + r * 0.38, `${Math.round(r * 0.2)}px SerifH`, 'rgba(110,70,20,0.85)', 'center', 'middle');
    // sweep shine
    const u = (t * 0.35) % 1;
    ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.clip();
    ctx.fillStyle = 'rgba(255,255,240,0.35)'; ctx.translate(x - r * 2 + u * r * 4, y); ctx.rotate(0.5); ctx.fillRect(-12, -r * 2, 24, r * 4);
    ctx.restore();
  });
}
function nameCard(ctx, x, y, zh, en, sub, k, grey = 0) {
  withAlpha(ctx, k, () => withXform(ctx, x, y + (1 - k) * 30, 1, 0, () => {
    paperRect(ctx, -190, -100, 380, 200, 12, mix(P.paperHi, [220, 218, 214], grey));
    text(ctx, zh, 0, -20, '46px SerifH', rgba(mix(P.ink, P.inkSoft, grey)));
    text(ctx, en, 0, 26, '28px SerifB', rgba(P.inkSoft));
    text(ctx, sub, 0, 70, '26px Kai', rgba(grey ? P.inkFaint : P.red));
  }));
}
function nobel(ctx, t, sc) {
  const gK = ap(t, S('N2') - 0.1, 0.6);
  medal(ctx, W / 2, lerp(700, 640, gK), 150, t, ap(t, sc.t0 + 0.1, 0.6));
  nameCard(ctx, 290, 1050 - gK * 40, '劳埃德·沙普利', 'Lloyd Shapley', '1962 论文作者', ap(t, charT('N1', '沙普利') - 0.1, 0.45));
  nameCard(ctx, 790, 1050 - gK * 40, '阿尔文·罗斯', 'Alvin Roth', '把它用进现实', ap(t, K('N1') - 0.1, 0.45));
  // Gale, in grey, joined by a faint thread
  withAlpha(ctx, gK, () => {
    thread(ctx, 290, 1110, 540, 1250, { sag: 30, lw: 3, a: 0.5, dash: [8, 10] });
    nameCard(ctx, 540, 1250, '大卫·盖尔', 'David Gale', '1921 – 2008', 1, 1);
  });
}
function nobelCues() { const t0 = sceneT('nobel'); cue(t0 + 0.1, 'chime', 0.9); cue(charT('N1', '沙普利') - 0.1, 'pop', 0.5); cue(K('N1') - 0.1, 'pop', 0.5); cue(S('N2') - 0.1, 'bell', 0.5); }

// ================================================================== ENDING
function ending(ctx, t, sc) {
  const t0 = sc.t0;
  const endK = ap(t, S('J4') - 0.1, 0.5);
  // J1–J2: the advice
  withAlpha(ctx, 1 - endK, () => {
    withAlpha(ctx, ap(t, t0 + 0.1, 0.5), () => text(ctx, '算法的建议', W / 2, 460, '48px SerifB', rgba(P.inkSoft)));
    const big = pop(t, K('J2') - 0.1, 0.5);
    withXform(ctx, W / 2, 640, big, -0.03, () => { ctx.globalAlpha *= clamp(big * 2); spaced(ctx, '先开口', 0, 0, '170px SerifH', rgba(P.red), 14); });
    // a boy walks over and says it
    const walk = eio(ramp(t, K('J2'), K('J2') + 1.2));
    const bx = lerp(260, 430, walk);
    F.person(ctx, bx, 960, MEN[0], { t, mood: t > K('J2') ? 'love' : 'neutral', a: ap(t, S('J1') + 0.3, 0.4) });
    F.person(ctx, 820, 960, WOMEN[0], { t, mood: t > K('J2') + 1.3 ? 'shy' : 'neutral', a: ap(t, S('J1') + 0.45, 0.4), look: -0.6 });
    bubble(ctx, bx + 30, 800, 110, 70, ap(t, K('J2') + 0.2, 0.4), -10, (g) => heart(g, 0, 4, 18, P.red));
    thread(ctx, bx + 56, 980, 764, 980, { p: eio(ramp(t, K('J2') + 0.9, K('J2') + 1.6)), lw: 5, wob: 3, t });
    // J3: worst case — crossed, then the next one
    const j3 = ap(t, S('J3') - 0.1, 0.4);
    withAlpha(ctx, j3, () => {
      ctx.fillStyle = rgba(P.paperHi, 0.94); roundRect(ctx, 200, 1130, 680, 200, 24); ctx.fill();
      const cr = t > charT('J3', '被拒绝');
      F.prefChips(ctx, W / 2, 1195, MPREF[0], WOMEN, { s: 1.4, crossed: new Set(cr ? [0] : []), ptr: t > charT('J3', '再去找') ? 1 : 0 });
      text(ctx, t > charT('J3', '再去找') ? '被拒一次 → 下一个' : '最坏的情况：被拒绝一次', W / 2, 1295, '34px Kai', rgba(P.inkSoft));
    });
    withAlpha(ctx, ap(t, S('J3'), 0.4), () => text(ctx, '（数学模型，仅供参考，不构成恋爱建议）', W / 2, 1390, '26px SansR', rgba(P.inkFaint)));
  });
  // J4: like button + end card
  withAlpha(ctx, endK, () => {
    const press = charT('J4', '点个赞');
    const pk = pop(t, press, 0.5);
    const beat = 1 + 0.06 * Math.pow(Math.max(0, Math.sin(t * 5)), 8);
    withXform(ctx, W / 2, 720, (0.8 + 0.2 * pk) * beat, 0, () => {
      glow(ctx, 0, 0, 260, P.red, 0.25 * pk);
      dot(ctx, 0, 0, 150, t > press ? P.red : P.paperHi);
      ring(ctx, 0, 0, 150, P.red, 1, 6);
      heart(ctx, 0, 14, 70, t > press ? P.white : P.red, 1);
    });
    if (t > press) for (let i = 0; i < 14; i++) { const a = i / 14 * TAU, d = 170 + 160 * eo(ramp(t, press, press + 1)); heart(ctx, W / 2 + Math.cos(a) * d, 720 + Math.sin(a) * d, 12, P.red, 1 - ramp(t, press + 0.4, press + 1.3)); }
    withAlpha(ctx, ap(t, charT('J4', '也算你'), 0.5), () => text(ctx, '也算你，先开了口', W / 2, 990, '60px Kai', rgba(P.ink)));
    const ek = ap(t, E('J4') + 0.3, 0.6);
    withAlpha(ctx, ek, () => {
      spaced(ctx, '红线算法', W / 2, 1180, '96px SerifH', rgba(P.ink), 10);
      thread(ctx, 300, 1215, 780, 1215, { sag: 14, lw: 5 });
      text(ctx, '谁先开口，谁更如愿', W / 2, 1290, '40px Kai', rgba(P.inkSoft));
      stamp(ctx, '完', 860, 1110, 50, t - (E('J4') + 0.7), 0.12, P.red);
    });
  });
}
function endingCues() {
  cue(K('J2') - 0.1, 'boom', 0.6); cue(K('J2') + 0.2, 'heart', 0.5); cue(K('J2') + 0.9, 'string', 0.6); cue(K('J2') + 1.6, 'knot', 0.6);
  cue(S('J3') - 0.1, 'paper', 0.4); cue(charT('J3', '被拒绝'), 'snap', 0.6); cue(charT('J3', '再去找'), 'pop', 0.6);
  cue(charT('J4', '点个赞'), 'heart', 1.0); FLASHES.push({ t: charT('J4', '点个赞'), c: P.red, a: 0.12 });
  cue(E('J4') + 0.7, 'stamp', 0.5);
}

// ------------------------------------------------------------------ helpers
function sceneT(key) { return E_.TL.scenes.find((s) => s.key === key).t0; }

const SCENES = {
  hook, title, legend, paper, unstable, rules,
  cast: boardScene, menfirst: boardScene, result1: boardScene, womenfirst: boardScene,
  compare, real, nobel, ending,
};
// scenes that share one continuous drawing (no cross-fade between them)
const GROUP = { cast: 'board', menfirst: 'board', result1: 'board', womenfirst: 'board' };
[hookCues, titleCues, legendCues, paperCues, unstableCues, rulesCues, boardCues, compareCues, realCues, nobelCues, endingCues].forEach((f) => f());
CUES.sort((a, b) => a.t - b.t);

module.exports = { SCENES, GROUP, CUES, SHAKES, FLASHES };
