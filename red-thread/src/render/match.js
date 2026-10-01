// 演示用的八个人和他们的偏好，以及 Gale–Shapley 延迟接受算法本身。
// 画面上每一轮谁向谁表白、谁被拒绝、谁被挤走，都是这里真的算出来的。
'use strict';

const MEN = [
  { ch: '山', name: '阿山', col: [78, 124, 88] },
  { ch: '川', name: '阿川', col: [58, 108, 158] },
  { ch: '风', name: '阿风', col: [122, 102, 172] },
  { ch: '云', name: '阿云', col: [70, 142, 150] },
];
const WOMEN = [
  { ch: '桃', name: '小桃', col: [226, 108, 128] },
  { ch: '杏', name: '小杏', col: [224, 142, 54] },
  { ch: '梨', name: '小梨', col: [168, 156, 40] },
  { ch: '荷', name: '小荷', col: [178, 80, 146] },
];
MEN.forEach((p) => { p.sex = 'm'; });
WOMEN.forEach((p) => { p.sex = 'f'; });

// 偏好：从最喜欢到最不喜欢（下标）
//   阿山: 荷 桃 杏 梨    小桃: 风 山 云 川
//   阿川: 梨 桃 杏 荷    小杏: 山 云 风 川
//   阿风: 梨 荷 杏 桃    小梨: 云 川 山 风
//   阿云: 桃 杏 梨 荷    小荷: 川 云 风 山
// 这组偏好恰好只有两个稳定配对：男生最优和女生最优，而且两者没有一对相同。
const MPREF = [[3, 0, 1, 2], [2, 0, 1, 3], [2, 3, 1, 0], [0, 1, 2, 3]];
const WPREF = [[2, 0, 3, 1], [0, 3, 2, 1], [3, 1, 0, 2], [1, 3, 2, 0]];

// 按轮并行的延迟接受：每一轮所有单身的提议者同时向下一个目标表白
function galeShapley(P, Q) {
  const n = P.length, next = Array(n).fill(0), hold = Array(n).fill(null);
  let free = [...Array(n).keys()];
  const rounds = [];
  while (free.length) {
    const proposals = free.map((m) => ({ from: m, to: P[m][next[m]++] }));
    const rejected = [], bumped = [];
    const byTarget = {};
    for (const pr of proposals) (byTarget[pr.to] = byTarget[pr.to] || []).push(pr.from);
    for (const [wS, ms] of Object.entries(byTarget)) {
      const w = +wS;
      const cand = ms.concat(hold[w] == null ? [] : [hold[w]]);
      const best = cand.reduce((a, b) => (Q[w].indexOf(a) < Q[w].indexOf(b) ? a : b));
      for (const m of ms) if (m !== best) rejected.push({ from: m, to: w, by: best });
      if (hold[w] != null && hold[w] !== best) bumped.push({ from: hold[w], to: w, by: best });
      hold[w] = best;
    }
    free = rejected.concat(bumped).map((r) => r.from).sort();
    rounds.push({ proposals, rejected, bumped, hold: hold.slice() });
  }
  const match = Array(n).fill(null);
  hold.forEach((m, w) => { match[m] = w; });
  return { rounds, match, hold };       // match[proposer] = receiver
}

function isStable(matchM, P = MPREF, Q = WPREF) {
  const n = matchM.length, matchW = Array(n);
  matchM.forEach((w, m) => { matchW[w] = m; });
  const blocking = [];
  for (let m = 0; m < n; m++) for (let w = 0; w < n; w++) {
    if (matchM[m] === w) continue;
    if (P[m].indexOf(w) < P[m].indexOf(matchM[m]) && Q[w].indexOf(m) < Q[w].indexOf(matchW[w])) blocking.push([m, w]);
  }
  return blocking;
}

const MENFIRST = galeShapley(MPREF, WPREF);
const WOMENFIRST = galeShapley(WPREF, MPREF);
// in men-index form: WM[m] = woman
const WM = Array(4); WOMENFIRST.match.forEach((m, w) => { WM[m] = w; });

const rankOf = (prefs, i, j) => prefs[i].indexOf(j) + 1;

// sanity checks — if the preference table is ever edited, the narration must change too
(function verify() {
  const mf = MENFIRST.match, wf = WM;
  const want = [0, 2, 3, 1];   // 山桃 川梨 风荷 云杏
  if (mf.join() !== want.join()) throw new Error('men-first result changed: ' + mf);
  if (wf.join() !== [1, 3, 0, 2].join()) throw new Error('women-first result changed: ' + wf);
  if (MENFIRST.rounds.length !== 4 || WOMENFIRST.rounds.length !== 1) throw new Error('round counts changed');
  if (isStable(mf).length || isStable(wf).length) throw new Error('unstable result?!');
  // the B-scene example: 川–桃, 山–梨 with 川 & 梨 the blocking pair
  const ex = isStable([2, 0, 1, 3]);
  if (!ex.some(([m, w]) => m === 1 && w === 2)) throw new Error('B-scene example is not blocked by 川–梨');
})();

module.exports = { MEN, WOMEN, MPREF, WPREF, galeShapley, isStable, MENFIRST, WOMENFIRST, WM, rankOf };

if (require.main === module) {
  const nm = (side, i) => (side === 'm' ? MEN : WOMEN)[i].ch;
  for (const [label, res, ps, rs] of [['男生先开口', MENFIRST, 'm', 'f'], ['女生先开口', WOMENFIRST, 'f', 'm']]) {
    console.log(label);
    res.rounds.forEach((r, i) => console.log(`  第${i + 1}轮`, r.proposals.map((p) => nm(ps, p.from) + '→' + nm(rs, p.to)).join(' '),
      '| 拒绝', r.rejected.map((p) => nm(ps, p.from)).join(' ') || '-', '| 挤走', r.bumped.map((p) => nm(ps, p.from)).join(' ') || '-'));
  }
}
