"""Scene 1 — the 'prophecy': vertical handwriting on aged paper, lit by an unseen lamp,
followed by the reveal ('这不是预言。这是你，今天早上。') and the first title card."""
import math
import numpy as np, cv2, skia
import gfx
from gfx import Layer, font, draw_text, fade, smoothstep, ease_out, ease_in_out, fbm1, noise1, clamp
from paper import make_paper, PW, PH
from config import W, H

INK = (0.045, 0.03, 0.022)
INK_FONT = 'serif-SemiBold'
CH = 64            # glyph size
ADV = 76           # vertical advance
COLW = 118         # column pitch
LINE_GAP = 40      # extra gap between script lines
TOP = 214

BREAKS = {   # column breaks for each line (vertical text, read right → left)
    'L01': ['很久以后，', '每个人的口袋里，', '都会有一块发光的玻璃。'],
    'L02': ['隔着半个地球，', '你能看见另一个人的脸。'],
    'L04': ['迷了路，它会为你指路。'],
    'L05': ['你对它说话——'],
    'L06': ['它会回答你。'],
}
PUNCT = '，。、——'

_layout = None


def layout():
    """-> list of glyph dicts {ch, x, y, line, k} in paper coordinates, plus column centres."""
    global _layout
    if _layout:
        return _layout
    ncols = sum(len(v) for v in BREAKS.values())
    total_w = ncols * COLW + (len(BREAKS) - 1) * LINE_GAP
    x = PW / 2 + total_w / 2 - COLW / 2
    glyphs, colx = [], {}
    for lid, cols in BREAKS.items():
        k = 0
        colx[lid] = []
        for col in cols:
            y = TOP
            colx[lid].append(x)
            i = 0
            while i < len(col):
                ch = col[i]
                if col[i:i + 2] == '——':
                    glyphs.append(dict(ch='——', x=x, y=y, line=lid, k=k, punct=True))
                    y += ADV * 2
                    i += 2
                    continue
                glyphs.append(dict(ch=ch, x=x, y=y, line=lid, k=k, punct=ch in PUNCT))
                if ch not in PUNCT:
                    k += 1
                y += ADV
                i += 1
            x -= COLW
        x -= LINE_GAP
    _layout = (glyphs, colx)
    return _layout


def glyph_times(tl):
    glyphs, _ = layout()
    n_per_line = {}
    for g in glyphs:
        if not g['punct']:
            n_per_line[g['line']] = n_per_line.get(g['line'], 0) + 1
    out = []
    for g in glyphs:
        ln = tl['lines'][g['line']]
        n = n_per_line[g['line']]
        span = ln['dur'] * 0.92
        k = g['k'] if not g['punct'] else max(0, g['k'] - 1)
        out.append(ln['start'] + span * (k + (0.6 if g['punct'] else 0)) / n)
    return out


def ink_layer(tl, t):
    glyphs, _ = layout()
    times = glyph_times(tl)
    L = Layer(PW, PH)
    c = L.canvas
    f = font(INK_FONT, CH)
    for g, t0 in zip(glyphs, times):
        a = smoothstep(t0, t0 + 0.32, t)
        if a <= 0:
            continue
        blur = (1 - a) * 3.0
        if g['ch'] == '——':
            p = skia.Paint(AntiAlias=True, Color=skia.Color4f(*INK, a), StrokeWidth=3.0)
            if blur > 0.05:
                p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
            c.drawLine(g['x'], g['y'] + 8, g['x'], g['y'] + ADV * 2 - 18, p)
            continue
        if g['ch'] in '，。、':
            # vertical typesetting: punctuation sits in the upper-right of its cell
            draw_text(c, g['ch'], g['x'] + CH * 0.52, g['y'] + CH * 0.35, f, INK, a, blur=blur)
        else:
            draw_text(c, g['ch'], g['x'], g['y'] + CH * 0.88, f, INK, a, blur=blur)
    return L.rgba()


_ink_tex = None


def ink_texture():
    global _ink_tex
    if _ink_tex is None:
        from gfx import fbm_2d
        n = fbm_2d(PH, PW, 5, seed=31, octaves=3)
        m = fbm_2d(PH, PW, 120, seed=32, octaves=3)
        _ink_tex = (0.72 + 0.28 * n) * (0.88 + 0.24 * m)
    return _ink_tex


_light_cache = {}


def light_map(lx, ly, r):
    key = (int(lx), int(ly), int(r))
    if key not in _light_cache:
        yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
        d2 = ((xx - lx) ** 2 + (yy - ly) ** 2) / (r * r)
        _light_cache[key] = (1.0 / (1.0 + d2)).astype(np.float32)
    return _light_cache[key]


def lamp_level(tl, t):
    """Brightness of the off-screen lamp: strikes on, breathes, then is blown out."""
    s0 = tl['scenes'][0]['start']
    on = smoothstep(s0 + 0.45, s0 + 1.6, t)
    out_t = tl['lines']['L06']['end'] + 2.0
    off = 1.0 - smoothstep(out_t, out_t + 0.55, t)
    # the flame gutters just before going out
    gutter = 1.0 - 0.35 * smoothstep(out_t - 0.5, out_t, t) * (0.5 + 0.5 * math.sin(t * 40))
    flick = 1.0 + 0.07 * (fbm1(t * 5.0, 21) - 0.5) + 0.03 * (noise1(t * 19.0, 4) - 0.5)
    return on * off * gutter * flick


def render_prophecy(tl, t):
    paper = make_paper()
    lvl = lamp_level(tl, t)
    img = np.zeros((H, W, 3), np.float32)
    if lvl <= 0.002:
        return img
    ink = ink_layer(tl, t)
    a = ink[..., 3]
    if a.max() > 0:
        bleed = cv2.GaussianBlur(a, (0, 0), 1.6)
        a = np.maximum(a, bleed * 0.55)
        a = np.clip(a * ink_texture(), 0, 1)
    a = a[..., None]
    surf = paper * (1 - a * 0.93) + np.array(INK, np.float32) * (a * 0.93)
    # lamp is off-screen, low and to the right; warm key + very low ambient
    lm = light_map(PW * 0.86, PH * 1.05, 1050)
    lm2 = light_map(PW * 0.5, PH * 0.5, 1500)
    light = (lm * 1.05 + lm2 * 0.20)[..., None] * np.array([1.0, 0.80, 0.56], np.float32) * lvl
    lit = surf * light
    # camera: slow push-in, gentle drift following the text (right → left)
    s0 = tl['scenes'][0]['start']
    s1 = tl['lines']['L06']['end'] + 2.6
    p = clamp((t - s0) / (s1 - s0))
    scale = (W / PW) * (1.0 + 0.085 * ease_in_out(p)) * 1.02
    pan_x = 120 - 240 * ease_in_out(p)
    pan_y = -10 + 20 * p
    ang = math.radians(-0.6 + 1.0 * p)
    M = cv2.getRotationMatrix2D((PW / 2, PH / 2), math.degrees(ang), scale)
    M[0, 2] += W / 2 - PW / 2 + pan_x
    M[1, 2] += H / 2 - PH / 2 + pan_y
    img = cv2.warpAffine(lit, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return img


# ------------------------------------------------------------------ reveal + title
def render_reveal(tl, t):
    img = np.zeros((H, W, 3), np.float32)
    L = Layer()
    c = L.canvas
    f = font('serif-Light', 66)
    l7, l8 = tl['lines']['L07'], tl['lines']['L08']
    title_start = [s for s in tl['scenes'] if s['id'] == 'title1'][0]['start']
    a7 = fade(t, l7['start'] - 0.05, l7['end'] + 0.5, 0.45, 0.5)
    if a7 > 0:
        k = ease_out(clamp((t - l7['start'] + 0.05) / 0.9))
        draw_text(c, '这不是预言。', W / 2, H / 2 + 22 + (1 - k) * 10, f, (0.95, 0.94, 0.91), a7, spacing=10, blur=(1 - k) * 6)
    a8 = fade(t, l8['start'] - 0.05, title_start - 0.2, 0.45, 0.7)
    if a8 > 0:
        k = ease_out(clamp((t - l8['start'] + 0.05) / 0.9))
        draw_text(c, '这是你，今天早上。', W / 2, H / 2 + 22 + (1 - k) * 10, f, (0.97, 0.96, 0.93), a8, spacing=10, blur=(1 - k) * 6)
    gfx.over(img, L.rgba())
    return img


def draw_title(img, t0, t, dur, big=118, english=True):
    """Title card: a hairline of light draws out, the characters condense out of blur."""
    L = Layer()
    c = L.canvas
    lt = t - t0
    out = 1 - smoothstep(dur - 1.1, dur - 0.1, lt)
    # hairline
    lw = ease_out(clamp(lt / 1.3)) * 760
    la = (smoothstep(0.0, 0.3, lt) * (1 - 0.75 * smoothstep(1.4, 2.6, lt))) * out
    if la > 0:
        p = skia.Paint(AntiAlias=True, StrokeWidth=1.3)
        p.setShader(skia.GradientShader.MakeLinear(
            [skia.Point(W / 2 - lw / 2, 0), skia.Point(W / 2 + lw / 2, 0)],
            [skia.Color4f(1, 0.95, 0.85, 0), skia.Color4f(1, 0.95, 0.85, la), skia.Color4f(1, 0.95, 0.85, 0)]))
        c.drawLine(W / 2 - lw / 2, H / 2 + 46, W / 2 + lw / 2, H / 2 + 46, p)
    f = font('serif-Light', big)
    text = '未来已到达'
    sp = big * 0.36
    total = gfx.text_width(text, f, sp)
    x = W / 2 - total / 2
    for i, ch in enumerate(text):
        a = smoothstep(0.55 + i * 0.13, 1.6 + i * 0.13, lt) * out
        cw = gfx.text_width(ch, f)
        draw_text(c, ch, x + cw / 2, H / 2 + 8, f, (0.97, 0.96, 0.93), a, blur=(1 - a) * 9 if a < 1 else 0)
        x += cw + sp
    if english:
        a = smoothstep(1.9, 2.9, lt) * out
        draw_text(c, 'THE FUTURE HAS ARRIVED', W / 2, H / 2 + 112, font('serif-Light', 22), (0.85, 0.83, 0.8), a * 0.7, spacing=11)
    gfx.over(img, L.rgba())
    return img


def render_title1(tl, t):
    sc = [s for s in tl['scenes'] if s['id'] == 'title1'][0]
    img = np.zeros((H, W, 3), np.float32)
    return draw_title(img, sc['start'], t, sc['end'] - sc['start'])
