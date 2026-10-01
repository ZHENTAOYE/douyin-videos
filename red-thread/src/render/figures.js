// Q 版古风小人：同一个模板，只换发型、衣色和表情；外加月老。
'use strict';
const E_ = require('./engine');
const { TAU, P, rgba, mix, clamp, lerp, ramp, eo, hash, roundRect, dot, line, glow, seal, heart } = E_;

// mood: neutral | happy | sad | love | shock | shy | think
// o: { s, mood, a, t, seed, look (-1..1), bob, noShadow, tear }
function person(ctx, x, y, p, o = {}) {
  const s = o.s || 1, a = o.a == null ? 1 : o.a;
  if (a <= 0.003 || s <= 0.01) return;
  const t = o.t || 0, seed = o.seed || p.ch.charCodeAt(0);
  const mood = o.mood || 'neutral';
  const bob = (o.bob == null ? 1 : o.bob) * Math.sin(t * 2.2 + seed) * 2.2 + (mood === 'happy' || mood === 'love' ? -Math.abs(Math.sin(t * 6 + seed)) * 3 : 0);
  ctx.save(); ctx.translate(x, y); ctx.scale(s, s); ctx.globalAlpha *= a;
  const ink = rgba(P.ink, 0.9);
  // shadow
  if (!o.noShadow) { ctx.fillStyle = 'rgba(80,55,30,0.16)'; ctx.beginPath(); ctx.ellipse(0, 66, 52, 10, 0, 0, TAU); ctx.fill(); }
  ctx.translate(0, bob);
  const col = p.col, dark = mix(col, P.ink, 0.35), light = mix(col, P.white, 0.55);
  // ---- robe
  ctx.fillStyle = rgba(col);
  ctx.beginPath();
  ctx.moveTo(-26, -2); ctx.quadraticCurveTo(-34, 0, -38, 18);
  ctx.lineTo(-50, 62); ctx.quadraticCurveTo(0, 70, 50, 62);
  ctx.lineTo(38, 18); ctx.quadraticCurveTo(34, 0, 26, -2); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = ink; ctx.lineWidth = 2.6; ctx.stroke();
  // hem band
  ctx.save(); ctx.clip();
  ctx.fillStyle = rgba(dark); ctx.fillRect(-60, 52, 120, 20);
  // sleeves (two soft arcs)
  ctx.strokeStyle = rgba(dark, 0.55); ctx.lineWidth = 2.4;
  ctx.beginPath(); ctx.moveTo(-36, 22); ctx.quadraticCurveTo(-20, 40, -10, 40); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(36, 22); ctx.quadraticCurveTo(20, 40, 10, 40); ctx.stroke();
  ctx.restore();
  // crossed collar (交领, right over left)
  ctx.fillStyle = rgba(P.white);
  ctx.beginPath(); ctx.moveTo(-20, -2); ctx.lineTo(-12, -2); ctx.lineTo(10, 30); ctx.lineTo(2, 34); ctx.closePath(); ctx.fill();
  ctx.beginPath(); ctx.moveTo(20, -2); ctx.lineTo(12, -2); ctx.lineTo(-2, 20); ctx.lineTo(4, 22); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = rgba(light); ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(-12, -1); ctx.lineTo(9, 30); ctx.stroke();
  // sash
  ctx.fillStyle = rgba(light); ctx.fillRect(-36, 34, 72, 7);
  // ---- head
  const hy = -40, R = 40;
  const tilt = (o.look || 0) * 0.08 + (mood === 'shy' ? 0.08 : 0) + (mood === 'sad' ? -0.03 : 0);
  ctx.save(); ctx.translate(0, hy); ctx.rotate(tilt);
  // back hair for girls
  if (p.sex === 'f') {
    ctx.fillStyle = rgba(P.ink);
    ctx.beginPath(); ctx.ellipse(0, 6, R + 4, R + 6, 0, 0, TAU); ctx.fill();
    // twin buns
    for (const sx of [-1, 1]) {
      dot(ctx, sx * 30, -32, 15, P.ink);
      ctx.fillStyle = rgba(col); ctx.beginPath(); ctx.ellipse(sx * 22, -22, 7, 4, sx * 0.7, 0, TAU); ctx.fill();
    }
  }
  // face
  dot(ctx, 0, 0, R, P.skin);
  ctx.strokeStyle = ink; ctx.lineWidth = 2.6; ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.stroke();
  // hair cap
  ctx.fillStyle = rgba(P.ink);
  ctx.beginPath();
  if (p.sex === 'm') {
    ctx.arc(0, 0, R + 1, Math.PI * 1.02, Math.PI * 1.98);
    ctx.quadraticCurveTo(26, -14, 10, -16); ctx.quadraticCurveTo(0, -8, -6, -18); ctx.quadraticCurveTo(-24, -10, -R - 1, -2);
    ctx.fill();
    // topknot + band
    dot(ctx, 0, -R - 8, 13, P.ink);
    ctx.fillStyle = rgba(col); ctx.fillRect(-11, -R - 1, 22, 6);
  } else {
    ctx.arc(0, 0, R + 2, Math.PI * 1.0, Math.PI * 2.0);
    ctx.quadraticCurveTo(30, -6, 18, -12); ctx.quadraticCurveTo(8, -6, 0, -14); ctx.quadraticCurveTo(-10, -4, -20, -12); ctx.quadraticCurveTo(-32, -4, -R - 2, 0);
    ctx.fill();
    // side locks
    ctx.beginPath(); ctx.moveTo(-R + 2, -2); ctx.quadraticCurveTo(-R - 4, 18, -R + 6, 30); ctx.lineTo(-R + 10, 6); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(R - 2, -2); ctx.quadraticCurveTo(R + 4, 18, R - 6, 30); ctx.lineTo(R - 10, 6); ctx.closePath(); ctx.fill();
  }
  // ---- face features
  const lx = (o.look || 0) * 4;
  const blinkPh = (t * 0.37 + hash(seed) * 7) % 1;
  const blink = mood !== 'happy' && mood !== 'love' && blinkPh > 0.965;
  ctx.fillStyle = rgba(P.ink); ctx.strokeStyle = rgba(P.ink); ctx.lineCap = 'round';
  const ey = 8;
  for (const sx of [-1, 1]) {
    const ex = sx * 14 + lx;
    if (mood === 'love') { heart(ctx, ex, ey + 2, 7, P.red); continue; }
    if (mood === 'happy' || mood === 'shy') { ctx.lineWidth = 3; ctx.beginPath(); ctx.arc(ex, ey + 3, 5.5, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke(); continue; }
    if (blink) { ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(ex - 5, ey); ctx.lineTo(ex + 5, ey); ctx.stroke(); continue; }
    if (mood === 'shock') { ctx.lineWidth = 2.5; ctx.beginPath(); ctx.arc(ex, ey, 6, 0, TAU); ctx.stroke(); dot(ctx, ex, ey, 2.2, P.ink); continue; }
    ctx.beginPath(); ctx.ellipse(ex, ey, 4, 5.5, 0, 0, TAU); ctx.fill();
    dot(ctx, ex + 1.3, ey - 2, 1.4, P.white);
  }
  // brows
  if (mood === 'sad' || mood === 'think') {
    ctx.lineWidth = 2.6;
    for (const sx of [-1, 1]) { ctx.beginPath(); ctx.moveTo(sx * 9 + lx, ey - 10 - (mood === 'sad' ? 2 : 0)); ctx.lineTo(sx * 19 + lx, ey - 10 + (mood === 'sad' ? 3 : -2) * (sx > 0 ? 1 : 1)); ctx.stroke(); }
  }
  // blush
  const bl = mood === 'shy' || mood === 'love' ? 0.75 : 0.42;
  ctx.fillStyle = rgba(P.blush, bl);
  ctx.beginPath(); ctx.ellipse(-24 + lx * 0.5, 20, 7, 4.5, 0, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.ellipse(24 + lx * 0.5, 20, 7, 4.5, 0, 0, TAU); ctx.fill();
  // mouth
  ctx.lineWidth = 2.6; ctx.strokeStyle = rgba(P.ink);
  const my = 22;
  if (mood === 'happy' || mood === 'love') {
    ctx.fillStyle = rgba(P.redDeep); ctx.beginPath(); ctx.moveTo(-7 + lx, my - 1); ctx.quadraticCurveTo(lx, my + 10, 7 + lx, my - 1); ctx.closePath(); ctx.fill();
  } else if (mood === 'sad') {
    ctx.beginPath(); ctx.arc(lx, my + 6, 5.5, Math.PI * 1.2, Math.PI * 1.8); ctx.stroke();
  } else if (mood === 'shock') {
    ctx.beginPath(); ctx.ellipse(lx, my + 1, 3.5, 4.5, 0, 0, TAU); ctx.stroke();
  } else if (mood === 'think') {
    ctx.beginPath(); ctx.moveTo(-4 + lx, my + 1); ctx.lineTo(5 + lx, my - 1); ctx.stroke();
  } else {
    ctx.beginPath(); ctx.arc(lx, my - 3, 5, Math.PI * 0.2, Math.PI * 0.8); ctx.stroke();
  }
  // tear
  if (mood === 'sad' && o.tear !== false) {
    const k = (t * 0.8 + hash(seed)) % 1;
    ctx.fillStyle = rgba(P.tear, 0.85 * (1 - k));
    const tx = 17 + lx, ty = ey + 6 + k * 18;
    ctx.beginPath(); ctx.moveTo(tx, ty - 5); ctx.quadraticCurveTo(tx + 4, ty + 2, tx, ty + 3); ctx.quadraticCurveTo(tx - 4, ty + 2, tx, ty - 5); ctx.fill();
  }
  ctx.restore();
  ctx.restore();
}

// 月老：白胡子、红袍、手持线团
function yuelao(ctx, x, y, s, t, a = 1) {
  if (a <= 0.003) return;
  ctx.save(); ctx.translate(x, y + Math.sin(t * 1.4) * 4); ctx.scale(s, s); ctx.globalAlpha *= a;
  const ink = rgba(P.ink, 0.9);
  // cloud he stands on
  ctx.fillStyle = rgba(P.white, 0.95);
  for (const [cx, cy, r] of [[-60, 72, 30], [-20, 80, 36], [30, 78, 34], [70, 72, 26], [0, 66, 30]]) { ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.fill(); }
  ctx.strokeStyle = rgba(P.ink, 0.25); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(-20, 80, 36, Math.PI * 0.1, Math.PI * 0.9); ctx.stroke();
  // robe
  ctx.fillStyle = rgba(P.red);
  ctx.beginPath(); ctx.moveTo(-30, -6); ctx.quadraticCurveTo(-46, 4, -52, 30); ctx.lineTo(-62, 70); ctx.quadraticCurveTo(0, 80, 62, 70); ctx.lineTo(52, 30); ctx.quadraticCurveTo(46, 4, 30, -6); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = ink; ctx.lineWidth = 2.6; ctx.stroke();
  ctx.fillStyle = rgba(P.gold); ctx.fillRect(-48, 34, 96, 8);
  // staff
  line(ctx, 64, -70, 70, 74, [120, 84, 50], 1, 7);
  dot(ctx, 64, -76, 10, P.gold);
  // head
  ctx.save(); ctx.translate(0, -44);
  dot(ctx, 0, 0, 40, P.skin);
  ctx.strokeStyle = ink; ctx.lineWidth = 2.6; ctx.beginPath(); ctx.arc(0, 0, 40, 0, TAU); ctx.stroke();
  // bald top with white side hair + long white brows
  ctx.fillStyle = rgba(P.white);
  ctx.beginPath(); ctx.ellipse(-38, 2, 10, 16, 0.2, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.ellipse(38, 2, 10, 16, -0.2, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(P.white); ctx.lineWidth = 5; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-22, -6); ctx.quadraticCurveTo(-12, -12, -6, -6); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(22, -6); ctx.quadraticCurveTo(12, -12, 6, -6); ctx.stroke();
  ctx.strokeStyle = ink; ctx.lineWidth = 3;
  for (const sx of [-1, 1]) { ctx.beginPath(); ctx.arc(sx * 14, 4, 5, Math.PI * 1.15, Math.PI * 1.85); ctx.stroke(); }
  ctx.fillStyle = rgba(P.blush, 0.6);
  ctx.beginPath(); ctx.ellipse(-24, 14, 7, 4, 0, 0, TAU); ctx.fill(); ctx.beginPath(); ctx.ellipse(24, 14, 7, 4, 0, 0, TAU); ctx.fill();
  // beard
  ctx.fillStyle = rgba(P.white);
  ctx.beginPath(); ctx.moveTo(-26, 14); ctx.quadraticCurveTo(-30, 50, 0, 74 + Math.sin(t * 2) * 2); ctx.quadraticCurveTo(30, 50, 26, 14); ctx.quadraticCurveTo(0, 30, -26, 14); ctx.fill();
  ctx.strokeStyle = rgba(P.ink, 0.25); ctx.lineWidth = 2; ctx.stroke();
  ctx.strokeStyle = ink; ctx.lineWidth = 2.6; ctx.beginPath(); ctx.arc(0, 22, 6, Math.PI * 0.15, Math.PI * 0.85); ctx.stroke();
  // little hat
  ctx.fillStyle = rgba(P.redDeep); ctx.beginPath(); ctx.ellipse(0, -38, 18, 9, 0, 0, TAU); ctx.fill();
  ctx.restore();
  // spool in hand
  ctx.save(); ctx.translate(-56, 20);
  ctx.fillStyle = rgba([150, 100, 60]); ctx.fillRect(-16, -18, 32, 6); ctx.fillRect(-16, 12, 32, 6);
  ctx.fillStyle = rgba(P.red); ctx.fillRect(-12, -12, 24, 24);
  ctx.strokeStyle = rgba(P.redDeep); ctx.lineWidth = 1.5; for (let i = -10; i <= 10; i += 4) { ctx.beginPath(); ctx.moveTo(-12, i); ctx.lineTo(12, i + 2); ctx.stroke(); }
  ctx.restore();
  ctx.restore();
}

// preference chips: row of small circles (one per preferred person, best → worst)
// o: { crossed: Set(index in list), ptr (index) , ptrK, a, s, hi: index highlight }
function prefChips(ctx, x, y, list, people, o = {}) {
  const s = o.s || 1, a = o.a == null ? 1 : o.a;
  if (a <= 0.003) return;
  const gap = 46 * s, r = 19 * s;
  const x0 = x - gap * (list.length - 1) / 2;
  ctx.save(); ctx.globalAlpha *= a;
  // tray
  ctx.fillStyle = rgba(P.paperHi, 0.75); roundRect(ctx, x0 - r - 8 * s, y - r - 7 * s, gap * (list.length - 1) + 2 * r + 16 * s, 2 * r + 14 * s, r + 7 * s); ctx.fill();
  ctx.strokeStyle = rgba(P.ink, 0.15); ctx.lineWidth = 1.5; ctx.stroke();
  list.forEach((j, k) => {
    const cx = x0 + k * gap;
    const kIn = o.reveal == null ? 1 : clamp((o.reveal - k * 0.12) / 0.3);
    if (kIn <= 0) return;
    const crossed = o.crossed && o.crossed.has(k);
    const pp = people[j];
    ctx.save(); ctx.globalAlpha *= kIn;
    const sc = E_.eback(kIn);
    ctx.translate(cx, y); ctx.scale(sc, sc);
    dot(ctx, 0, 0, r, crossed ? mix(pp.col, P.paperLo, 0.75) : pp.col);
    E_.text(ctx, pp.ch, 0, r * 0.06, `${Math.round(r * 1.08)}px SerifH`, rgba(P.white, crossed ? 0.6 : 1), 'center', 'middle');
    if (crossed) line(ctx, -r * 0.9, r * 0.9, r * 0.9, -r * 0.9, P.ink, 0.85, 3.5 * s);
    ctx.restore();
    if (o.hi === k) { glow(ctx, cx, y, r * 2.4, P.gold, 0.45 * a); ring(ctx, cx, y, r + 5 * s, P.gold, 0.95, 3 * s); }
    if (o.ptr === k) { const pk = o.ptrK == null ? 1 : o.ptrK; E_.ring(ctx, cx, y, r + 5 * s + (1 - pk) * 10, P.red, pk, 3.5 * s); }
  });
  ctx.restore();
}
const ring = E_.ring;

module.exports = { person, yuelao, prefChips };
