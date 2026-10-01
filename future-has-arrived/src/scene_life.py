"""06 生命与智能 (155.0–180.0s): a DNA double helix with a sequencer readout · a real protein structure
(PDB 2XHE, Unc18–syntaxin complex) folding into shape · a machine answering in human language."""
import math
import numpy as np, cv2, skia
import gl3d, gfx, cards
from gfx import smoothstep, clamp, ease_in_out, ease_out, lerp, Layer, radial_glow
from config import W, H, ASSETS

_L = {}

BASE_COL = {'A': (0.35, 0.85, 0.55), 'T': (0.95, 0.40, 0.38), 'G': (1.0, 0.78, 0.30), 'C': (0.38, 0.62, 1.0)}
PAIR = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}


def tube(path, radius, colors, segs=10):
    """Sweep a circle along a polyline -> (P, N, C) triangles. colors: (len(path),4)."""
    n = len(path)
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    ref = np.array([0.0, 1.0, 0.0])
    Nn = np.cross(T, ref)
    bad = np.linalg.norm(Nn, axis=1) < 1e-3
    Nn[bad] = np.cross(T[bad], np.array([1.0, 0, 0]))
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    B = np.cross(T, Nn)
    ang = np.linspace(0, 2 * math.pi, segs, endpoint=False)
    ring = np.cos(ang)[None, :, None] * Nn[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :]
    rad = np.broadcast_to(np.asarray(radius, float).reshape(-1, 1, 1) if np.ndim(radius) else radius, (n, 1, 1))
    P = path[:, None, :] + ring * rad
    Nr = ring
    C = np.repeat(colors[:, None, :], segs, axis=1)
    i = np.arange(n - 1)[:, None]
    j = np.arange(segs)[None, :]
    a = i * segs + j
    b = i * segs + (j + 1) % segs
    c = (i + 1) * segs + j
    d = (i + 1) * segs + (j + 1) % segs
    F = np.concatenate([np.stack([a, c, b], -1).reshape(-1, 3), np.stack([b, c, d], -1).reshape(-1, 3)])
    P, Nr, C = P.reshape(-1, 3), Nr.reshape(-1, 3), C.reshape(-1, 4)
    return P[F].reshape(-1, 3), Nr[F].reshape(-1, 3), C[F].reshape(-1, 4)


# ------------------------------------------------------------------ DNA
def dna_mesh():
    if 'dna' in _L:
        return _L['dna'], _L['seq']
    rng = np.random.default_rng(42)
    nbp = 90
    rise, twist, R = 0.34, 2 * math.pi / 10.5, 1.0
    seq = ''.join(rng.choice(list('ATGC'), nbp))
    z = np.arange(nbp) * rise
    th = np.arange(nbp) * twist
    k = 8
    zz = np.linspace(0, z[-1], nbp * k)
    tt = zz / rise * twist
    s1 = np.c_[R * np.cos(tt), R * np.sin(tt), zz]
    s2 = np.c_[R * np.cos(tt + 2.2), R * np.sin(tt + 2.2), zz]
    col1 = np.tile([0.80, 0.84, 0.92, 1], (len(s1), 1))
    parts = [tube(s1, 0.13, col1, 12), tube(s2, 0.13, col1, 12)]
    from meshes import cylinder, merge
    for i in range(nbp):
        a = np.array([R * math.cos(th[i]), R * math.sin(th[i]), z[i]])
        b = np.array([R * math.cos(th[i] + 2.2), R * math.sin(th[i] + 2.2), z[i]])
        m = (a + b) / 2
        parts.append(cylinder(a, m, 0.075, 10, (*BASE_COL[seq[i]], 1)))
        parts.append(cylinder(m, b, 0.075, 10, (*BASE_COL[PAIR[seq[i]]], 1)))
    P, N, C = merge(*parts)
    _L['dna'] = gl3d.Mesh(P, N, C)
    _L['seq'] = seq
    return _L['dna'], seq


def render_dna(t):
    t0 = 155.0
    lt = t - t0
    mesh, seq = dna_mesh()
    zlen = 90 * 0.34
    zc = 4.0 + 1.9 * lt
    ang = math.radians(30 + 8 * lt)
    eye = np.array([6.4 * math.cos(ang), 2.0, zc - 5.0 + 6.4 * math.sin(ang) * 0.3])
    tgt = np.array([0.0, 0.0, zc + 2.5])
    view = gl3d.look_at(eye, tgt, (0, 1, 0))
    proj = gl3d.perspective(45, W / H, 0.05, 200)
    tg = gl3d.target()
    tg.begin((0, 0, 0, 1))
    mesh.render(view=view, proj=proj, eye=tuple(eye), key_dir=(-0.4, -0.6, 0.5), key_col=(1.1, 1.05, 1.0),
                amb_col=(0.10, 0.11, 0.15), shininess=50.0, spec_k=0.55, rim_col=(0.25, 0.4, 0.7), emit=0.05,
                fog_col=(0.0, 0.0, 0.0), fog_density=0.09)
    img = tg.read()[..., :3].copy()
    # depth-ish softness: blur the outer frame
    blur = cv2.GaussianBlur(img, (0, 0), 5)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    w = np.clip((np.sqrt(((xx - W * 0.5) / (W * 0.55)) ** 2 + ((yy - H * 0.5) / (H * 0.6)) ** 2) - 0.45) * 1.8, 0, 1)[..., None]
    img = img * (1 - w) + blur * w
    # sequencer readout scrolling on the right
    L = Layer()
    c = L.canvas
    a = smoothstep(t0 + 0.4, t0 + 1.2, t) * (1 - smoothstep(163.4, 164.0, t))
    f = cards.fnt('num', 'Medium', 30)
    rng = np.random.default_rng(int(lt * 20))
    off = (lt * 260) % 44
    for row in range(26):
        y = 60 + row * 44 - off
        line = ''.join(np.random.default_rng(row + int(lt * 260 // 44) * 7).choice(list('ATGC'), 18))
        x = W - 120 - 18 * 22
        for k_, ch in enumerate(line):
            col = BASE_COL[ch]
            al = a * (0.25 + 0.55 * (row / 26.0)) * (1.0 if k_ % 5 else 0.75)
            cards.draw_mixed(c, ch, x + k_ * 22, y, f, f, col, al)
    gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.6, t) * (1 - smoothstep(163.6, 164.0, t))


# ------------------------------------------------------------------ protein (PDB 2XHE)
def load_ca(path=f'{ASSETS}/pdb/2XHE.pdb'):
    chains = {}
    for line in open(path):
        if line.startswith('ATOM') and line[12:16].strip() == 'CA':
            ch = line[21]
            x, y, z = float(line[30:38]), float(line[38:46]), float(line[46:54])
            b = float(line[60:66])
            chains.setdefault(ch, []).append((x, y, z, b))
    return {k: np.array(v) for k, v in chains.items()}


def catmull(P, k=5):
    P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for s in np.linspace(0, 1, k, endpoint=False):
            s2, s3 = s * s, s * s * s
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s2 + (-p0 + 3 * p1 - 3 * p2 + p3) * s3))
    out.append(P[-2])
    return np.array(out)


AF_PALETTE = np.array([[0.05, 0.33, 0.83], [0.40, 0.80, 0.95], [1.0, 0.86, 0.30], [1.0, 0.49, 0.27]])


def protein_frame(fold):
    if 'ca' not in _L:
        ch = load_ca()
        allp = np.vstack([v[:, :3] for v in ch.values()])
        cen = allp.mean(0)
        sc = 1.0 / 3.8
        rng = np.random.default_rng(3)
        data = []
        for k, v in ch.items():
            P = (v[:, :3] - cen) * sc
            b = v[:, 3]
            q = np.clip((b - np.percentile(b, 10)) / (np.percentile(b, 95) - np.percentile(b, 10) + 1e-6), 0, 1)
            idx = np.clip(q * 3, 0, 2.999)
            lo = idx.astype(int)
            fr = (idx - lo)[:, None]
            col = AF_PALETTE[lo] * (1 - fr) + AF_PALETTE[lo + 1] * fr
            # an "unfolded" starting chain: a loose random walk stretched out
            steps = rng.normal(0, 1, (len(P), 3))
            steps[:, 0] += 0.9 if k == 'A' else -0.9
            U = np.cumsum(steps, 0) * 0.55
            U -= U.mean(0)
            U *= 0.55
            U += (np.array([0, 2.0, 0]) if k == 'A' else np.array([0, -2.0, 0]))
            data.append((P, U, col))
        _L['ca'] = data
    parts = []
    for P, U, col in _L['ca']:
        Q = U * (1 - fold) + P * fold
        S = catmull(Q, 4)
        C = np.repeat(col, 4, axis=0)[:len(S)]
        if len(C) < len(S):
            C = np.vstack([C, np.repeat(C[-1:], len(S) - len(C), 0)])
        C4 = np.c_[C, np.ones(len(C))]
        parts.append(tube(S, 0.22, C4, 9))
    P = np.concatenate([p[0] for p in parts])
    N = np.concatenate([p[1] for p in parts])
    C = np.concatenate([p[2] for p in parts])
    return P, N, C


def render_protein(t):
    t0 = 164.0
    lt = t - t0
    fold = ease_in_out(clamp((lt - 0.3) / 3.6))
    P, N, C = protein_frame(fold)
    mesh = gl3d.Mesh(P, N, C)
    ang = math.radians(20 + 14 * lt)
    dist = lerp(36, 25, ease_out(clamp(lt / 6)))
    eye = np.array([dist * math.cos(ang), 6.0, dist * math.sin(ang)])
    view = gl3d.look_at(eye, np.array([0.0, 0.0, 0.0]))
    proj = gl3d.perspective(40, W / H, 0.1, 300)
    tg = gl3d.target()
    tg.begin((0, 0, 0, 1))
    mesh.render(view=view, proj=proj, eye=tuple(eye), key_dir=(-0.5, -0.7, -0.4), key_col=(1.0, 0.98, 0.95),
                amb_col=(0.16, 0.17, 0.22), shininess=40.0, spec_k=0.5, rim_col=(0.25, 0.35, 0.55), emit=0.08,
                fog_col=(0.0, 0.0, 0.0), fog_density=0.012)
    img = tg.read()[..., :3].copy()
    mesh.vbo.release()
    mesh.vao.release()
    radial_glow(img, W * 0.5, H * 0.5, 600, (0.06, 0.10, 0.2), 0.5, falloff=1.4)
    a = smoothstep(t0 + 1.0, t0 + 2.0, t) * (1 - smoothstep(170.4, 170.9, t))
    if a > 0:
        L = Layer()
        c = L.canvas
        cards.draw_mixed(c, '蛋白质结构 · PDB 2XHE', W - 90, 120, cards.fnt('sans', 'Regular', 24), cards.fnt('num', 'Medium', 28),
                         (0.9, 0.9, 0.9), a * 0.7, align='right', shadow=0.6)
        gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.5, t) * (1 - smoothstep(170.6, 171.0, t))


# ------------------------------------------------------------------ AI: language
WORDS = ['语言', 'language', '思考', 'idea', '未来', '星辰', 'light', '问题', 'answer', '诗', 'code', '对话', 'λόγος',
         '言葉', '언어', 'Sprache', 'langue', 'lengua', '知识', '光', 'why', '答案', '宇宙', 'think', '理解', '世界', 'story',
         '文字', 'meaning', '记忆', 'dream', '学习', 'learn', '时间', 'time', '你好', 'hello', '谢谢', 'curious', '人类']


def render_ai(t):
    t0 = 171.0
    lt = t - t0
    img = np.zeros((H, W, 3), np.float32)
    radial_glow(img, W / 2, H / 2, 520, (0.08, 0.10, 0.18), 0.6, falloff=1.4)
    L = Layer()
    c = L.canvas
    # drifting field of words converging on the centre
    rng = np.random.default_rng(9)
    n = 160
    a_field = smoothstep(t0, t0 + 0.8, t) * (1 - 0.65 * smoothstep(174.2, 175.0, t))
    for k in range(n):
        w = WORDS[k % len(WORDS)]
        r0 = rng.uniform(300, 1300)
        ang = rng.uniform(0, 2 * math.pi)
        spd = rng.uniform(0.04, 0.10)
        depth = rng.uniform(0.3, 1.0)
        prog = (rng.uniform(0, 1) + lt * spd) % 1.0
        r = r0 * (1 - prog) ** 1.3
        x, y = W / 2 + math.cos(ang + prog * 0.6) * r * 1.2, H / 2 + math.sin(ang + prog * 0.6) * r * 0.62
        al = a_field * depth * 0.55 * smoothstep(0.0, 0.15, prog) * (1 - smoothstep(0.82, 1.0, prog))
        if al < 0.02:
            continue
        sz = 18 + 26 * depth
        cards.draw_mixed(c, w, x, y, cards.fnt('sans', 'Light', sz), cards.fnt('num', 'Light', sz * 1.05),
                         (0.75, 0.82, 1.0), al, align='center', blur=(1 - depth) * 3.0)
    # the exchange
    q = '未来什么时候到来？'
    ans = '它已经到了。'
    tq0, tq_char = 175.0, 0.09
    ta0, ta_char = tq0 + len(q) * tq_char + 0.9, 0.16
    fq = cards.fnt('sans', 'Regular', 52)
    fa = cards.fnt('sans', 'Medium', 76)
    nq = int(clamp((t - tq0) / tq_char, 0, len(q)))
    na = int(clamp((t - ta0) / ta_char, 0, len(ans)))
    a_box = smoothstep(174.6, 175.0, t)
    if a_box > 0:
        x0 = W / 2 - 360
        # question bubble (right aligned, like a sent message)
        if nq > 0:
            txt = q[:nq]
            wq = cards.Mixed(txt, fq, fq).width
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(W / 2 + 380 - wq - 64, H / 2 - 168, wq + 64, 96), 34, 34)
            c.drawRRect(r, cards.paint((0.20, 0.22, 0.28), 0.92 * a_box))
            cards.draw_mixed(c, txt, W / 2 + 380 - 32, H / 2 - 102, fq, fq, (0.95, 0.95, 0.95), a_box, align='right')
        # answer, token by token, with a blinking cursor
        if t > ta0 - 0.6:
            txt = ans[:na]
            cards.draw_mixed(c, txt, x0 - 20, H / 2 + 70, fa, fa, cards.ACCENT, 1.0, shadow=0.6)
            wa = cards.Mixed(txt, fa, fa).width - 20
            blink = (math.sin(t * 2 * math.pi * 1.6) > -0.2) or (0 < na < len(ans))
            if blink:
                c.drawRect(skia.Rect.MakeXYWH(x0 + wa + 10, H / 2 + 6, 5, 76), cards.paint(cards.ACCENT, 0.9))
    gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.5, t) * (1 - smoothstep(179.6, 180.0, t))
