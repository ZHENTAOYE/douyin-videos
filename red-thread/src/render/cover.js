// 封面：1080×1920，标题落在中间 3:4 安全区（主页九宫格会裁成 3:4）
'use strict';
const fs = require('fs');
const path = require('path');
const E_ = require('./engine');
E_.registerFonts();
const L = require('./layers');
const F = require('./figures');
const { MEN, WOMEN, MENFIRST, WM } = require('./match');
const { W, H, P, rgba, BUILD, text, spaced, thread, stamp } = E_;

const canvas = E_.createCanvas(W, H);
const ctx = canvas.getContext('2d');
L.drawBackground(ctx, 100);
// two columns of people, the women-first threads crossing behind the title
const ys = [500, 700, 1240, 1440];
const hand = (side, i) => [side === 'm' ? 266 : 814, ys[i] + 20];
WM.forEach((w, m) => { const [x1, y1] = hand('m', m), [x2, y2] = hand('f', w); thread(ctx, x1, y1, x2, y2, { lw: 6, a: 0.85 }); });
const moodsM = ['sad', 'sad', 'sad', 'sad'];
MEN.forEach((p, i) => F.person(ctx, 210, ys[i], p, { t: 0.4, mood: moodsM[i], look: 0.6, tear: false }));
WOMEN.forEach((p, i) => F.person(ctx, 870, ys[i], p, { t: 0.4, mood: 'happy', look: -0.6 }));
// title plate
const g = ctx.createLinearGradient(0, 820, 0, 1120);
g.addColorStop(0, 'rgba(248,242,228,0)'); g.addColorStop(0.2, 'rgba(248,242,228,0.95)'); g.addColorStop(0.8, 'rgba(248,242,228,0.95)'); g.addColorStop(1, 'rgba(248,242,228,0)');
ctx.fillStyle = g; ctx.fillRect(0, 820, W, 300);
spaced(ctx, '红线算法', W / 2, 990, '176px SerifH', rgba(P.ink), 16);
thread(ctx, 160, 1030, 920, 1030, { sag: 22, lw: 8 });
text(ctx, '谁先开口，谁更如愿？', W / 2, 1100, '58px Kai', rgba(P.red));
stamp(ctx, '诺贝尔奖', 560, 640, 60, 1, -0.06, P.red, '2012 · 经济学');
L.drawVignette(ctx);
const out = path.join(BUILD, 'cover.png');
fs.writeFileSync(out, canvas.toBuffer('image/png'));
console.log(out);
