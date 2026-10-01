// 逐帧渲染：node main.js --still 12.5,40  → build/stills/*.png
//            node main.js --from 0 --to 120 --out build/part0.mp4
'use strict';
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const E_ = require('./engine');
E_.registerFonts();
const L = require('./layers');
const { SCENES, GROUP, CUES, SHAKES, FLASHES } = require('./scenes');
const { W, H, TL, BUILD, clamp, ramp, rgba, eo } = E_;

const FPS = TL.fps;
const canvas = E_.createCanvas(W, H);
const ctx = canvas.getContext('2d');

function shakeAt(t) {
  let x = 0, y = 0;
  for (const s of SHAKES) {
    const d = t - s.t; if (d < 0 || d > 0.6) continue;
    const a = s.amp * Math.exp(-d * 9);
    x += a * Math.sin(d * 83 + s.t); y += a * Math.cos(d * 67 + s.t * 2);
  }
  return [x, y];
}
function drawFlash(t) {
  for (const f of FLASHES) {
    const d = t - f.t; if (d < 0 || d > 0.5) continue;
    ctx.fillStyle = rgba(f.c, f.a * Math.exp(-d * 8)); ctx.fillRect(0, 0, W, H);
  }
}
function drawScene(i, t, alpha) {
  if (alpha <= 0.003) return;
  const sc = TL.scenes[i];
  ctx.save(); ctx.globalAlpha = alpha;
  SCENES[sc.key](ctx, t, sc);
  ctx.restore();
}
const TRANS = 0.45;
function frame(t) {
  ctx.save();
  const [sx, sy] = shakeAt(t);
  ctx.translate(sx, sy);
  L.drawBackground(ctx, t);
  const i = L.sceneAt(t);
  const sc = TL.scenes[i];
  const same = i > 0 && GROUP[sc.key] && GROUP[sc.key] === GROUP[TL.scenes[i - 1].key];
  const k = i > 0 && !same ? eo(ramp(t, sc.t0, sc.t0 + TRANS)) : 1;
  if (k < 1) drawScene(i - 1, t, 1 - k);
  drawScene(i, t, k);
  ctx.restore();
  drawFlash(t);
  L.drawVignette(ctx);
  L.drawSubtitle(ctx, t);
}

async function main() {
  const a = process.argv.slice(2);
  const opt = (k, d) => { const i = a.indexOf('--' + k); return i >= 0 ? a[i + 1] : d; };
  fs.writeFileSync(path.join(BUILD, 'cues.json'), JSON.stringify({ cues: CUES }));
  if (a.includes('--cues-only')) return;
  if (a.includes('--check')) {          // dry run: evaluate every scene at 6 fps, report exceptions
    let bad = 0;
    for (let t = 0; t < TL.duration; t += 1 / 6) { try { frame(t); } catch (e) { bad++; console.error(t.toFixed(2), e.message); } }
    console.log('check done, errors:', bad); return;
  }
  if (opt('still')) {
    const dir = path.join(BUILD, 'stills'); fs.mkdirSync(dir, { recursive: true });
    for (const s of opt('still').split(',')) {
      const t = parseFloat(s); frame(t);
      const f = path.join(dir, `t${t.toFixed(2).padStart(7, '0')}.png`);
      fs.writeFileSync(f, canvas.toBuffer('image/png')); console.log(f);
    }
    return;
  }
  const from = parseFloat(opt('from', '0')), to = Math.min(TL.duration, parseFloat(opt('to', String(TL.duration))));
  const out = opt('out', path.join(BUILD, 'video.mp4'));
  const f0 = Math.round(from * FPS), f1 = Math.round(to * FPS);
  const crf = opt('crf', '18');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', `${W}x${H}`, '-r', String(FPS), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', crf, '-tune', 'animation', '-pix_fmt', 'yuv420p', '-g', String(FPS * 2), '-movflags', '+faststart', out],
  { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    frame(f / FPS);
    const buf = canvas.data();
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if ((f - f0) % 300 === 0) process.stderr.write(`[${from}-${to}] frame ${f - f0}/${f1 - f0}  ${((Date.now() - t0) / Math.max(1, f - f0)).toFixed(0)} ms/f\n`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('wrote', out, ((Date.now() - t0) / 1000).toFixed(1) + 's');
}
main();
