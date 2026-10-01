// 封面：1080×1920，标题落在中间 3:4 安全区（主页九宫格会裁成 3:4）
'use strict';
const fs = require('fs');
const path = require('path');
const E_ = require('./engine');
E_.registerFonts();
const L = require('./layers');
const { W, H, P, rgba, BUILD, text, glow, neuron, line, stamp, layerNodes } = Object.assign({}, E_, { layerNodes: null });

const canvas = E_.createCanvas(W, H);
const ctx = canvas.getContext('2d');

L.drawBackground(ctx, 300, { act: 1, warm: 1, energy: 0.9, alpha: 0.5 });
// a big glowing network behind the title
const xs = [170, 360, 540, 720, 910], counts = [5, 7, 8, 7, 5];
const layers = xs.map((x, l) => Array.from({ length: counts[l] }, (_, i) => ({ x, y: 640 + (i - (counts[l] - 1) / 2) * 92 })));
for (let l = 0; l + 1 < layers.length; l++) for (const a of layers[l]) for (const b of layers[l + 1]) line(ctx, a.x, a.y, b.x, b.y, P.amber, 0.13, 2);
layers.forEach((ly, l) => ly.forEach((n, i) => neuron(ctx, n.x, n.y, 15, ((i * 7 + l * 3) % 5) / 5 + 0.2, P.amber)));
// dark plate for the title
const g = ctx.createLinearGradient(0, 760, 0, 1240);
g.addColorStop(0, 'rgba(11,12,16,0)'); g.addColorStop(0.25, 'rgba(11,12,16,0.88)'); g.addColorStop(0.8, 'rgba(11,12,16,0.88)'); g.addColorStop(1, 'rgba(11,12,16,0)');
ctx.fillStyle = g; ctx.fillRect(0, 760, W, 480);
glow(ctx, 540, 960, 420, P.amber, 0.12);
text(ctx, '神经网络', 540, 960, '200px SerifH', rgba(P.paper), 'center');
text(ctx, '往事', 540, 1150, '160px SerifH', rgba(P.amber), 'center');
text(ctx, '一个被判过两次死刑的想法', 540, 1270, '50px SansB', rgba(P.paper, 0.9), 'center');
line(ctx, 250, 1330, 380, 1330, P.amber, 0.7, 3); line(ctx, 700, 1330, 830, 1330, P.amber, 0.7, 3);
text(ctx, '1943 — 2024', 540, 1343, '40px SerifB', rgba(P.amber), 'center');
stamp(ctx, '死刑', 250, 560, 92, 1, -0.2, P.red, '1969');
stamp(ctx, '死刑', 840, 720, 92, 1, 0.14, P.red, '1990s');
L.drawVignette(ctx);
const out = path.join(BUILD, 'cover.png');
fs.writeFileSync(out, canvas.toBuffer('image/png'));
console.log(out);
