"""01 速度 (19.0–38.0s): transistor counts 1971→2024 on a LINEAR axis — flat for four decades,
then a near-vertical spike the camera has to chase. Then a dive into a silicon crystal lattice."""
import math
import numpy as np, cv2, skia
import gfx, gl3d, cards
from gfx import Layer, smoothstep, clamp, ease_in_out, ease_out, ease_in, lerp
from config import W, H

# (year, transistors, label) — public figures from the manufacturers
CHIPS = [
    (1971.9, 2.3e3, 'Intel 4004'), (1974.3, 4.5e3, 'Intel 8080'), (1978.4, 2.9e4, 'Intel 8086'),
    (1982.1, 1.34e5, 'Intel 80286'), (1985.8, 2.75e5, 'Intel 80386'), (1989.3, 1.18e6, 'Intel 80486'),
    (1993.2, 3.1e6, 'Pentium'), (1999.2, 9.5e6, 'Pentium III'), (2000.9, 4.2e7, 'Pentium 4'),
    (2006.6, 2.91e8, 'Core 2 Duo'), (2010.2, 1.17e9, 'Core i7'), (2012.9, 7.08e9, 'NVIDIA GK110'),
    (2016.3, 1.53e10, 'NVIDIA GP100'), (2017.4, 2.11e10, 'NVIDIA GV100'), (2020.4, 5.42e10, 'NVIDIA GA100'),
    (2022.3, 8.0e10, 'NVIDIA GH100'), (2024.2, 2.08e11, 'NVIDIA B200'),
]
LABELLED = {'Intel 4004', 'Intel 8086', 'Pentium', 'Pentium 4', 'Core 2 Duo', 'NVIDIA GK110', 'NVIDIA GA100',
            'NVIDIA GH100', 'NVIDIA B200'}

X_PER_YEAR = 30.0
Y_PER_UNIT = 1.0 / 1e8           # px per transistor
WARM = (1.0, 0.70, 0.36)
T0, T_SPIKE, T_TOP, T_END = 19.0, 23.6, 27.6, 34.2


def wx(year):
    return (year - 1971) * X_PER_YEAR


def wy(n):
    return -n * Y_PER_UNIT


def head_year(t):
    """Year reached by the drawn line at time t (slow along the flat part, then fast)."""
    if t < 19.6:
        return 1971.9
    if t < T_SPIKE:
        return lerp(1971.9, 2011.5, ease_in_out((t - 19.6) / (T_SPIKE - 19.6)) ** 1.1)
    if t < T_TOP:
        return lerp(2011.5, 2024.2, ease_in(clamp((t - T_SPIKE) / (T_TOP - T_SPIKE)), 1.6))
    return 2024.2


def count_at(year):
    ys = [c[0] for c in CHIPS]
    ns = [math.log(c[1]) for c in CHIPS]
    return math.exp(np.interp(year, ys, ns))


def curve_points(year_to):
    pts = []
    for (y, n, _) in CHIPS:
        if y <= year_to:
            pts.append((wx(y), wy(n)))
    if pts and year_to > CHIPS[0][0]:
        pts.append((wx(year_to), wy(count_at(year_to))))
    return pts


def camera(t):
    """-> (scale, world point that sits at screen centre)."""
    hy = head_year(t)
    hx, hyy = wx(hy), wy(count_at(hy))
    if t < T_SPIKE:
        # follow the head along the baseline, zoomed in
        s = lerp(3.0, 2.3, smoothstep(19.6, T_SPIKE, t))
        cx = lerp(wx(1971.9) + 260, hx + 80, smoothstep(19.6, 21.2, t))
        return s, (cx, -70)
    if t < T_TOP + 0.3:
        u = clamp((t - T_SPIKE) / (T_TOP + 0.3 - T_SPIKE))
        s = lerp(2.3, 1.2, ease_in_out(u))
        return s, (lerp(hx - 120, wx(2016), u), min(-70, hyy + 160))
    # pull back to show the whole hockey stick, parked on the right half of the frame
    u = ease_in_out(clamp((t - (T_TOP + 0.3)) / 2.4))
    s = lerp(1.2, 0.42, u)
    top = wy(2.08e11)
    return s, (lerp(wx(2016), -14.0, u), lerp(top + 160, -1057.0, u))


def to_screen(p, s, c):
    return W / 2 + (p[0] - c[0]) * s, H / 2 + (p[1] - c[1]) * s


def render_chart(t):
    img = np.zeros((H, W, 3), np.float32)
    gfx.radial_glow(img, W * 0.55, H * 0.6, 700, (0.10, 0.12, 0.22), 0.6, falloff=1.4)
    s, c = camera(t)
    L = Layer()
    cv = L.canvas
    a_scene = smoothstep(T0, T0 + 0.8, t)
    # grid: horizontal lines every 100亿 (1e10), vertical every 10 years
    gp = skia.Paint(AntiAlias=True, StrokeWidth=1.0, Color=skia.Color4f(1, 1, 1, 0.08 * a_scene))
    lab = cards.fnt('num', 'Regular', 26)
    lab_cjk = cards.fnt('sans', 'Regular', 22)
    for k in range(0, 23):
        y = wy(k * 1e10)
        sx0, sy = to_screen((wx(1970), y), s, c)
        sx1, _ = to_screen((wx(2026), y), s, c)
        if -40 < sy < H + 40:
            cv.drawLine(sx0, sy, sx1, sy, gp)
            if k % 2 == 0 and k > 0:
                cards.draw_mixed(cv, f'{k * 100} 亿', sx0 - 14, sy + 8, lab_cjk, lab, (0.8, 0.8, 0.8), 0.55 * a_scene, align='right')
    for yr in range(1970, 2030, 10):
        x0, y0 = to_screen((wx(yr), 0), s, c)
        _, y1 = to_screen((wx(yr), wy(2.2e11)), s, c)
        cv.drawLine(x0, y0, x0, y1, gp)
        cards.draw_mixed(cv, str(yr), x0, y0 + 44, lab_cjk, lab, (0.85, 0.85, 0.85), 0.6 * a_scene, align='center')
    # baseline
    bp = skia.Paint(AntiAlias=True, StrokeWidth=1.6, Color=skia.Color4f(1, 1, 1, 0.35 * a_scene))
    x0, y0 = to_screen((wx(1970), 0), s, c)
    x1, _ = to_screen((wx(2026), 0), s, c)
    cv.drawLine(x0, y0, x1, y0, bp)
    # the curve
    hy = head_year(t)
    pts = curve_points(hy)
    if len(pts) >= 2:
        path = skia.Path()
        sp = [to_screen(p, s, c) for p in pts]
        path.moveTo(*sp[0])
        for p in sp[1:]:
            path.lineTo(*p)
        glow = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=10,
                          Color=skia.Color4f(*WARM, 0.35), StrokeJoin=skia.Paint.kRound_Join)
        glow.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        cv.drawPath(path, glow)
        line = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.2,
                          Color=skia.Color4f(1.0, 0.86, 0.62, 1.0), StrokeJoin=skia.Paint.kRound_Join)
        cv.drawPath(path, line)
    # chip points + labels
    for (y, n, name) in CHIPS:
        if y > hy + 1e-6:
            continue
        px, py = to_screen((wx(y), wy(n)), s, c)
        age = clamp((hy - y) / 2.0)
        dot = skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 0.95, 0.85, 1))
        cv.drawCircle(px, py, 5.5, dot)
        if name in LABELLED:
            a = smoothstep(0, 0.15, age) * a_scene
            if name not in ('Intel 4004', 'NVIDIA GH100', 'NVIDIA B200'):
                a *= 1 - smoothstep(T_TOP + 0.2, T_TOP + 1.2, t)
            num = f'{n:,.0f}' if n < 1e8 else (f'{n / 1e8:,.1f} 亿' if n < 1e10 else f'{n / 1e8:,.0f} 亿')
            ly = py - 26 if n > 3e9 else py - 26 - (CHIPS.index((y, n, name)) % 2) * 58
            cards.draw_mixed(cv, name, px, ly - 26, cards.fnt('sans', 'Regular', 22), cards.fnt('num', 'Medium', 27),
                             (0.95, 0.94, 0.9), a * 0.9, align='center', shadow=0.6)
            cards.draw_mixed(cv, num, px, ly + 4, cards.fnt('sans', 'Medium', 24), cards.fnt('num', 'SemiBold', 30),
                             WARM, a, align='center', shadow=0.6)
    # live counter, top right
    if t < T_TOP + 0.2:
        cnt = count_at(hy)
        txt = f'{cnt:,.0f}'
        a = smoothstep(19.6, 20.2, t) * (1 - smoothstep(T_TOP - 0.1, T_TOP + 0.2, t))
        cards.draw_mixed(cv, txt, W - 110, 170, cards.fnt('sans', 'Bold', 60), cards.fnt('num', 'SemiBold', 92),
                         (1, 1, 1), a, align='right', shadow=0.7)
        cards.draw_mixed(cv, '个晶体管 / 芯片', W - 112, 222, cards.fnt('sans', 'Regular', 26), cards.fnt('num', 'Regular', 28),
                         (0.85, 0.85, 0.85), a * 0.8, align='right')
    layer = L.rgba()
    gfx.over(img, layer)
    # flare at the head of the curve
    if len(pts) >= 2:
        hx, hyy = to_screen(pts[-1], s, c)
        k = 0.6 + 1.6 * smoothstep(T_SPIKE, T_TOP, t) * (1 - smoothstep(T_TOP + 0.5, T_TOP + 2.0, t))
        gfx.radial_glow(img, hx, hyy, 10, (1.0, 0.8, 0.5), 1.6 * k)
        gfx.radial_glow(img, hx, hyy, 60, (1.0, 0.6, 0.3), 0.35 * k, falloff=1.8)
    return img * a_scene


# ------------------------------------------------------------------ silicon lattice
_L = {}


def lattice():
    if 'pos' in _L:
        return _L
    a = 1.0
    base = np.array([[0, 0, 0], [0, .5, .5], [.5, 0, .5], [.5, .5, 0]])
    basis = np.vstack([base, base + 0.25])
    n = 9
    cells = np.array([[i, j, k] for i in range(-n, n) for j in range(-n // 2, n // 2) for k in range(-n, n)], float)
    pos = (cells[:, None, :] + basis[None, :, :]).reshape(-1, 3) * a
    # bonds: each atom on the shifted sub-lattice bonds to 4 neighbours at distance sqrt(3)/4
    from scipy.spatial import cKDTree
    tree = cKDTree(pos)
    pairs = tree.query_pairs(math.sqrt(3) / 4 + 1e-3)
    pairs = np.array(sorted(pairs))
    _L.update(pos=pos.astype(np.float32), pairs=pairs)
    _L['pts'] = gl3d.Points(len(pos) + 10)
    _L['lines'] = gl3d.Lines(len(pairs) + 10)
    return _L


def render_lattice(t, t0):
    L = lattice()
    lt = t - t0
    ang = 0.35 + 0.10 * lt
    r = 7.5 - 1.6 * ease_out(clamp(lt / 3.4))
    eye = np.array([r * math.cos(ang), 1.2 + 0.25 * lt, r * math.sin(ang)])
    tgt = np.array([0.0, 0.0, 0.0])
    view = gl3d.look_at(eye, tgt)
    proj = gl3d.perspective(48, W / H, 0.05, 100)
    tg = gl3d.target()
    tg.begin((0, 0, 0, 1))
    pos = L['pos']
    d = np.linalg.norm(pos - eye, axis=1)
    focus = np.linalg.norm(eye - tgt)
    fog = np.exp(-np.maximum(d - focus, 0) * 0.22)
    near = gfx.vsmooth(0.4, 1.4, d)
    cols = np.c_[np.tile([[0.55, 0.75, 1.0]], (len(pos), 1)), (1.6 * fog * near)[:, None]]
    sizes = np.full(len(pos), 0.055, np.float32)
    pr = L['pairs']
    seg = np.stack([pos[pr[:, 0]], pos[pr[:, 1]]], axis=1)
    sd = np.linalg.norm(seg.mean(axis=1) - eye, axis=1)
    sf = (np.exp(-np.maximum(sd - focus, 0) * 0.22) * gfx.vsmooth(0.4, 1.4, sd))[:, None]
    scol = np.concatenate([np.tile([[[1.0, 0.72, 0.4, 0.22]]], (len(seg), 2, 1))], axis=0)
    scol[..., 3] *= sf
    L['lines'].render(seg, scol, width=2.2, depth_test=False, view=view, proj=proj)
    L['pts'].render(pos, cols, sizes, depth_test=False, view=view, proj=proj, px_scale=H * 1.2)
    img = tg.read()[..., :3].copy()
    return img * smoothstep(t0, t0 + 0.5, t)


def render(t):
    if t < 34.2:
        img = render_chart(t)
        if t > 33.4:
            k = smoothstep(33.4, 34.2, t)
            img = img * (1 - k) + k * 1.2
        return img
    img = render_lattice(t, 34.2)
    flash = 1 - smoothstep(34.2, 34.7, t)
    return img * (1 - flash) + flash * 1.2
