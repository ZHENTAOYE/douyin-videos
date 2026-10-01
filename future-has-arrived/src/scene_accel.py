"""07 加速 (180.0–204.0s) and the finale (204.0–219.0s).
Wright Flyer at dawn · Earth rising over the Moon · an accelerating year counter 1903→2026 cutting
through recap shots of the whole film · the lit Earth under the closing lines and title."""
import math, os
import numpy as np, cv2, skia
import gl3d, gfx, cards, story, earthgl
from gfx import smoothstep, clamp, ease_in_out, ease_out, lerp, Layer, radial_glow
from config import W, H, BUILD

_A = {}


# ------------------------------------------------------------------ 1903: dawn flight
def wright_path(c, x, y, s, a):
    """Side silhouette of the 1903 Wright Flyer (biplane, front elevator, twin rudders)."""
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.02, 0.015, 0.02, a), Style=skia.Paint.kStroke_Style,
                   StrokeWidth=2.2 * s, StrokeCap=skia.Paint.kRound_Cap)
    pf = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.02, 0.015, 0.02, a))
    # wings (seen almost edge-on, slightly from below): two thin cambered plates
    for dy in (-14, 14):
        path = skia.Path()
        path.moveTo(x - 70 * s, y + dy * s)
        path.quadTo(x, y + (dy - 5) * s, x + 70 * s, y + dy * s)
        path.lineTo(x + 70 * s, y + (dy + 2.5) * s)
        path.quadTo(x, y + (dy - 2.5) * s, x - 70 * s, y + (dy + 2.5) * s)
        path.close()
        c.drawPath(path, pf)
    for k in range(-3, 4):
        c.drawLine(x + k * 20 * s, y - 13 * s, x + k * 20 * s, y + 14 * s, p)
    # front elevator on outriggers
    c.drawLine(x + 70 * s, y - 2 * s, x + 118 * s, y - 4 * s, p)
    c.drawLine(x + 70 * s, y + 10 * s, x + 118 * s, y + 4 * s, p)
    c.drawLine(x + 112 * s, y - 6 * s, x + 132 * s, y - 7 * s, p)
    c.drawLine(x + 112 * s, y + 4 * s, x + 132 * s, y + 3 * s, p)
    # rear rudders
    c.drawLine(x - 70 * s, y, x - 112 * s, y, p)
    c.drawLine(x - 112 * s, y - 13 * s, x - 112 * s, y + 13 * s, p)
    c.drawLine(x - 118 * s, y - 13 * s, x - 118 * s, y + 13 * s, p)
    # pilot lying on the lower wing
    c.drawOval(skia.Rect.MakeXYWH(x - 6 * s, y + 4 * s, 22 * s, 8 * s), pf)


def render_flight(t, t0=180.0):
    lt = t - t0
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    top = np.array([0.03, 0.05, 0.12], np.float32)
    mid = np.array([0.32, 0.24, 0.32], np.float32)
    hor = np.array([1.0, 0.62, 0.32], np.float32)
    sky = np.where(yy < 0.62, top + (mid - top) * (yy / 0.62) ** 1.5, mid + (hor - mid) * ((yy - 0.62) / 0.12).clip(0, 1))
    img = np.broadcast_to(sky, (H, W, 3)).copy()
    radial_glow(img, W * 0.70, H * 0.74, 60, (1.0, 0.75, 0.45), 0.9, falloff=1.6)
    radial_glow(img, W * 0.70, H * 0.74, 380, (1.0, 0.55, 0.3), 0.25, falloff=1.4)
    L = Layer()
    c = L.canvas
    # dunes, three silhouette layers
    rng = np.random.default_rng(2)
    for k, (base, amp, col) in enumerate(((0.76, 22, (0.13, 0.08, 0.09)), (0.82, 30, (0.07, 0.045, 0.05)), (0.9, 40, (0.025, 0.018, 0.02)))):
        path = skia.Path()
        path.moveTo(0, H)
        ph = rng.uniform(0, 6)
        for x in range(0, W + 41, 40):
            y = H * base - amp * (math.sin(x * 0.004 + ph) + 0.5 * math.sin(x * 0.011 + ph * 2)) - (k * 0.0) - lt * (k + 1) * 0.0
            path.lineTo(x, y)
        path.lineTo(W, H)
        path.close()
        c.drawPath(path, skia.Paint(AntiAlias=True, Color=skia.Color4f(*col, 1)))
    # the flyer: low over the sand, left to right; tiny wobble
    x = lerp(W * 0.12, W * 0.78, clamp(lt / 4.6))
    y = H * 0.70 - 30 * math.sin(clamp(lt / 4.6) * math.pi) + 3 * math.sin(lt * 5)
    c.save()
    c.rotate(-1.5 + 1.2 * math.sin(lt * 2.1), x, y)
    wright_path(c, x, y, 1.75, 1.0)
    c.restore()
    gfx.over(img, L.rgba())
    return img


# ------------------------------------------------------------------ 1969: Earth over the Moon
def render_earthrise(t, t0=184.4):
    lt = t - t0
    img = np.zeros((H, W, 3), np.float32)
    # Earth: a half-lit blue marble high in a black sky
    eye = np.array([0.0, 0.0, 15.0])
    view = gl3d.look_at(eye, np.array([2.6, -1.0, 0.0]))
    proj = gl3d.perspective(30, W / H, 0.1, 100)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    earthgl.render_earth(view, proj, eye, (1.0, 0.25, 0.25), math.radians(-60 + 2 * lt), lights_gain=0.4, day_gain=1.3,
                         star_gain=0.6, lights_reveal=1.0, atmo_gain=1.1)
    img = tg.read()[..., :3].copy()
    # lunar horizon in the foreground, slowly sinking as the Earth "rises"
    if 'lunar' not in _A:
        n = gfx.fbm_2d(H, W, 60, seed=17, octaves=5)
        fine = gfx.fbm_2d(H, W, 6, seed=18, octaves=3)
        _A['lunar'] = (0.22 + 0.25 * n + 0.08 * fine).astype(np.float32)
    lun = _A['lunar']
    drop = 30 * ease_out(clamp(lt / 3.6))
    xs = np.arange(W, dtype=np.float32)
    horizon = H * 0.66 + drop + 0.00012 * (xs - W * 0.4) ** 2 + 8 * np.sin(xs * 0.01) + 4 * np.sin(xs * 0.037)
    yy = np.arange(H, dtype=np.float32)[:, None]
    mask = (yy > horizon[None, :]).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.0)
    shade = np.clip((yy - horizon[None, :]) / 260.0, 0, 1)
    ground = lun * (0.95 - 0.55 * shade) * 0.55
    ground = np.repeat(ground[..., None], 3, axis=2) * np.array([1.0, 0.98, 0.95], np.float32)
    img = img * (1 - mask[..., None]) + ground * mask[..., None]
    return img


# ------------------------------------------------------------------ recap shots for the montage
RECAP = [  # one shot per milestone, in story.MILESTONES order
    ('accel_flight', 182.0), ('earth', 77.0), ('earth', 63.0), ('earthrise', 186.6), ('earth', 78.5),
    ('chip', 12.0), ('chip', 3.0), ('earth', 66.5), ('earth', 70.0), ('earth', 71.5), ('dna', 157.5),
    ('dna', 160.5), ('earth', 63.6), ('chip', 5.0), ('earth', 72.4), ('ai', 172.5), ('precision', 152.0),
    ('ai', 173.5), ('precision', 153.6), ('moon', 119.0), ('earth', 84.0), ('voyager', 99.0), ('fusion', 141.0),
    ('ai', 177.6), ('dna', 158.6), ('moon', 122.0), ('fusion', 138.0), ('chip', 1.0), ('earth', 64.5),
]


def recap_image(idx):
    key = f'm{idx:02d}'
    path = f'{BUILD}/cache/recap/{key}.npy'
    if key in _A:
        return _A[key]
    if os.path.exists(path):
        _A[key] = np.load(path).astype(np.float32)
        return _A[key]
    import compose2
    sid, tt = RECAP[idx]
    if sid == 'accel_flight':
        img = render_flight(tt)
    elif sid == 'earthrise':
        img = render_earthrise(tt)
    else:
        fn = compose2.scene_fn(sid)
        img = fn(tt)
    img = np.nan_to_num(np.asarray(img[..., :3], np.float32))
    img = gfx.bloom(img, 0.6, 0.8)
    img = gfx.tonemap(img)
    small = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA).astype(np.float16)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.save(path, small)
    _A[key] = small.astype(np.float32)
    return _A[key]


def precompute_recaps():
    assert len(RECAP) == len(story.MILESTONES)
    for i in range(len(story.MILESTONES)):
        recap_image(i)


# ------------------------------------------------------------------ the year montage
M_T0, M_T1 = 188.0, 202.6


def schedule():
    if 'sched' in _A:
        return _A['sched']
    ms = story.MILESTONES
    n = len(ms) - 1                         # the last one (2026) holds
    r = 0.92
    total = (M_T1 - 1.6) - M_T0
    d0 = total * (1 - r) / (1 - r ** n)
    times, t = [], M_T0
    for k in range(n):
        times.append(t)
        t += d0 * r ** k
    times.append(t)                         # 2026 arrives here and holds to M_T1
    _A['sched'] = times
    return times


def render_montage(t):
    ms = story.MILESTONES
    times = schedule()
    k = max(0, min(len(ms) - 1, int(np.searchsorted(times, t, side='right') - 1)))
    year, label = ms[k]
    prev_year = ms[k - 1][0] if k > 0 else 1900
    t_k = times[k]
    t_next = times[k + 1] if k + 1 < len(times) else M_T1
    span = max(t_next - t_k, 1e-3)
    # odometer: roll quickly from the previous milestone year, then land
    roll = ease_out(clamp((t - t_k) / min(0.35, span * 0.6)), 3)
    shown_year = int(round(lerp(prev_year, year, roll)))
    bg = recap_image(k)
    big = cv2.resize(bg, (W, H), interpolation=cv2.INTER_LINEAR)
    zoom = 1.0 + 0.06 * clamp((t - t_k) / max(span, 0.5))
    M = np.array([[zoom, 0, W / 2 * (1 - zoom)], [0, zoom, H / 2 * (1 - zoom)]], np.float32)
    big = cv2.warpAffine(big, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    img = big * 0.42
    # quick white flash on each cut
    flash = math.exp(-max(0.0, t - t_k) * 22.0) * (0.55 if k < len(ms) - 1 else 1.2)
    img = img + flash
    L = Layer()
    c = L.canvas
    # timeline ruler along the bottom
    x0, x1, yb = 140, W - 140, H - 120
    def yx(y):
        return lerp(x0, x1, (y - 1900) / 126.0)
    c.drawLine(x0, yb, x1, yb, cards.paint((1, 1, 1), 0.3))
    for j in range(k + 1):
        yj = ms[j][0]
        c.drawLine(yx(yj), yb - 14, yx(yj), yb + 14, cards.paint(cards.ACCENT, 0.9))
    head = yx(lerp(prev_year, year, roll))
    c.drawLine(x0, yb, head, yb, skia.Paint(AntiAlias=True, StrokeWidth=3, Color=skia.Color4f(*cards.ACCENT, 1)))
    for yy_, lab in ((1900, '1900'), (1950, '1950'), (2000, '2000')):
        cards.draw_mixed(c, lab, yx(yy_), yb + 48, cards.fnt('sans', 'Regular', 22), cards.fnt('num', 'Regular', 26),
                         (0.85, 0.85, 0.85), 0.6, align='center')
    # the year, huge
    fy = cards.fnt('num', 'SemiBold', 300)
    cards.draw_mixed(c, str(shown_year), W / 2, H / 2 + 70, fy, fy, (1, 1, 1), 1.0, align='center', shadow=0.6)
    a_lab = smoothstep(t_k, t_k + min(0.12, span * 0.3), t)
    cards.draw_mixed(c, label, W / 2, H / 2 + 170, cards.fnt('sans', 'Medium', 54), cards.fnt('num', 'Medium', 60),
                     cards.ACCENT if year == 2026 else (1, 1, 1), a_lab, align='center', spacing=4, shadow=0.8)
    gfx.over(img, L.rgba())
    return img


def render(t):
    if t < 184.4:
        img = render_flight(t)
        img *= smoothstep(180.0, 180.6, t)
        return img * (1 - smoothstep(184.0, 184.4, t))
    if t < M_T0:
        img = render_earthrise(t)
        img *= smoothstep(184.4, 184.9, t)
        return img * (1 - smoothstep(187.7, 188.0, t)) + smoothstep(187.75, 188.0, t) * 0.0
    if t < 203.4:
        img = render_montage(min(t, M_T1 - 0.001))
        if t > M_T1:
            img = img * (1 - smoothstep(M_T1, 203.4, t))
        return img
    return np.zeros((H, W, 3), np.float32)


# ------------------------------------------------------------------ finale
def render_finale(t):
    t0 = 204.0
    lt = t - t0
    ang = math.radians(25 + 1.8 * lt)
    dist = 3.4 - 0.5 * ease_out(clamp(lt / 14.0))
    eye = np.array([dist * math.sin(ang) * 0.35, 0.9 + 0.02 * lt, dist])
    view = gl3d.look_at(eye, np.array([0.0, -0.05, 0.0]))
    proj = gl3d.perspective(38, W / H, 0.01, 100)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    reveal = smoothstep(t0 + 0.4, t0 + 3.0, t)
    earthgl.render_earth(view, proj, eye, (-0.75, 0.25, -0.62), math.radians(-102 + 1.2 * lt), lights_gain=1.45,
                         day_gain=0.9, star_gain=0.9, lights_reveal=reveal, atmo_gain=1.0)
    img = tg.read()[..., :3].copy()
    img *= smoothstep(t0 + 0.2, t0 + 2.0, t) * (1 - smoothstep(218.2, 219.0, t))
    # during the title, dim a little so the type sits well
    img *= 1 - 0.35 * smoothstep(212.6, 213.6, t)
    return img
