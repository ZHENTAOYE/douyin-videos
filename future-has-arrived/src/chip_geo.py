"""Procedural chip interconnect stack: transistor gates/fins, 10 copper metal layers, vias,
plus 'signal' pulses that travel along some wires. 1 world unit ~ 10 nm."""
import numpy as np

COPPER = (0.96, 0.60, 0.42)
COPPER_DARK = (0.80, 0.48, 0.34)
TUNGSTEN = (0.62, 0.62, 0.66)
GATE = (0.55, 0.58, 0.66)
SI = (0.05, 0.07, 0.12)

# (pitch, thickness, gap_above) per metal layer, bottom → top
LAYERS = [(1.0, 0.8, 0.8), (1.0, 0.8, 0.8), (1.6, 1.2, 1.1), (1.6, 1.2, 1.1), (2.6, 1.9, 1.6),
          (2.6, 1.9, 1.6), (4.4, 3.2, 2.6), (4.4, 3.2, 2.6), (12.0, 7.5, 4.0), (12.0, 7.5, 4.0)]
X0, X1 = -160.0, 700.0          # flight runs along +x
Z_HALF = [70, 70, 110, 110, 170, 170, 260, 260, 340, 340]
KEEP = [0.78, 0.78, 0.78, 0.78, 0.78, 0.78, 0.75, 0.75, 0.35, 0.35]


def build(seed=3):
    rng = np.random.default_rng(seed)
    C, S, K, E = [], [], [], []       # centres, sizes, colours(rgba: a=metalness), emission

    def box(c, s, col, metal=1.0, emit=0.0):
        C.append(c)
        S.append(s)
        K.append((*col, metal))
        E.append(emit)

    # silicon substrate
    box((250, -1.0, 0), (1400, 2.0, 700), SI, 0.0)
    # FEOL: fins (along x) and gates (along z)
    y = 0.0
    fz = 60
    for z in np.arange(-fz, fz, 1.3):
        x = X0
        while x < X1:
            L = rng.exponential(16) + 3
            if rng.random() < 0.8:
                box((x + L / 2, y + 0.25, z), (L, 0.5, 0.22), (0.25, 0.28, 0.36), 0.2)
            x += L + rng.exponential(3) + 0.6
    for x in np.arange(X0, X1, 0.9):
        if rng.random() < 0.15:
            continue
        z = -fz
        while z < fz:
            L = rng.exponential(10) + 2
            box((x, y + 0.6, z + L / 2), (0.16, 1.2, L), GATE, 0.6)
            z += L + rng.exponential(2) + 0.5
    y = 1.6
    wires = []   # (layer, axis, x0, x1, fixed coordinate, y_centre, width, thickness)
    for li, (p, t, gap) in enumerate(LAYERS):
        axis = 'x' if li % 2 == 0 else 'z'
        zh = Z_HALF[li]
        w = p * 0.5
        yc = y + t / 2
        if axis == 'x':
            tracks = np.arange(-zh, zh, p)
            span0, span1 = X0, X1
        else:
            tracks = np.arange(X0, X1, p)
            span0, span1 = -zh, zh
        mean_len = 14 * p if li < 8 else 5 * p
        for tr in tracks:
            if rng.random() > KEEP[li]:
                continue
            a = span0 + rng.uniform(0, 4 * p)
            while a < span1:
                L = rng.exponential(mean_len) + 2 * p
                b = min(span1, a + L)
                col = COPPER if rng.random() < 0.85 else COPPER_DARK
                if axis == 'x':
                    box(((a + b) / 2, yc, tr), (b - a, t, w), col, 1.0)
                else:
                    box((tr, yc, (a + b) / 2), (w, t, b - a), col, 1.0)
                wires.append((li, axis, a, b, tr, yc, w, t))
                # vias down to the layer below at both ends (and sometimes the middle)
                if li > 0:
                    vh = LAYERS[li - 1][2]
                    for u in ([a + w, b - w] + ([(a + b) / 2] if rng.random() < 0.3 else [])):
                        if axis == 'x':
                            box((u, y - vh / 2, tr), (w * 0.9, vh, w * 0.9), TUNGSTEN if li < 4 else COPPER_DARK, 1.0)
                        else:
                            box((tr, y - vh / 2, u), (w * 0.9, vh, w * 0.9), TUNGSTEN if li < 4 else COPPER_DARK, 1.0)
                a = b + rng.exponential(3 * p) + p
        y += t + gap
    top = y
    return (np.array(C, np.float32), np.array(S, np.float32), np.array(K, np.float32),
            np.array(E, np.float32), wires, top)


def make_signals(wires, n=5000, seed=5):
    """Pick wires that will carry travelling light pulses."""
    rng = np.random.default_rng(seed)
    cand = [w for w in wires if w[0] in (1, 2, 3, 4, 5, 6, 7) and (w[3] - w[2]) > 12]
    idx = rng.choice(len(cand), size=min(n, len(cand)), replace=False)
    sig = []
    for i in idx:
        li, axis, a, b, tr, yc, w, t = cand[i]
        sig.append(dict(axis=axis, a=a, b=b, tr=tr, y=yc + t / 2 + 0.05, w=w,
                        speed=rng.uniform(25, 70) * rng.choice([-1, 1]), phase=rng.uniform(0, 1),
                        L=rng.uniform(2.5, 8), hue=rng.random(), bright=rng.uniform(4, 14)))
    return sig


def signal_boxes(sig, t):
    C, S, K, E = [], [], [], []
    for s in sig:
        span = s['b'] - s['a']
        u = (s['phase'] * span + s['speed'] * t) % span
        L = min(s['L'], span * 0.5)
        pos = s['a'] + u
        col = (1.0, 0.86, 0.62) if s['hue'] < 0.75 else (0.65, 0.85, 1.0)
        if s['axis'] == 'x':
            C.append((pos, s['y'], s['tr']))
            S.append((L, 0.12, s['w'] * 0.75))
        else:
            C.append((s['tr'], s['y'], pos))
            S.append((s['w'] * 0.75, 0.12, L))
        K.append((*col, 0.0))
        E.append(s['bright'])
    return (np.array(C, np.float32), np.array(S, np.float32), np.array(K, np.float32), np.array(E, np.float32))
