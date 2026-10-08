"""Typography for the text-only cut: statements, big stats, chapter markers, sources, title."""
import functools, re
import numpy as np, skia
import gfx
from gfx import Layer, smoothstep, clamp, ease_out, ease_in_out
from config import W, H, ASSETS

SANS = '/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc'
SERIF = '/usr/share/fonts/opentype/noto/NotoSerifCJK-{}.ttc'
BARLOW = f'{ASSETS}/fonts/BarlowCondensed-{{}}.ttf'

WHITE = (0.96, 0.95, 0.93)
ACCENT = (1.0, 0.72, 0.36)


@functools.lru_cache(None)
def tf(kind, weight):
    if kind == 'sans':
        return skia.Typeface.MakeFromFile(SANS.format(weight), 2)
    if kind == 'serif':
        return skia.Typeface.MakeFromFile(SERIF.format(weight), 2)
    if kind == 'num':
        return skia.Typeface.MakeFromFile(BARLOW.format(weight))
    raise KeyError(kind)


def fnt(kind, weight, size):
    f = skia.Font(tf(kind, weight), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    f.setHinting(skia.FontHinting.kNone)
    return f


_ascii = re.compile(r'[\x20-\x7e−×%·.,+≤]+')


def runs(text):
    """Split into (is_latin, chunk) runs so digits/latin use the condensed numeric face."""
    out, i = [], 0
    for m in _ascii.finditer(text):
        if m.start() > i:
            out.append((False, text[i:m.start()]))
        out.append((True, m.group()))
        i = m.end()
    if i < len(text):
        out.append((False, text[i:]))
    return out


class Mixed:
    """A single line of mixed CJK / Latin text measured and drawn on a shared baseline."""

    def __init__(self, text, cjk_font, lat_font, spacing=0.0, lat_spacing=0.0):
        self.items = []
        x = 0.0
        for latin, chunk in runs(text):
            f = lat_font if latin else cjk_font
            sp = lat_spacing if latin else spacing
            glyphs = f.textToGlyphs(chunk)
            ws = f.getWidths(glyphs)
            pos = []
            for w in ws:
                pos.append(x)
                x += w + sp
            self.items.append((f, chunk, glyphs, pos))
        self.width = x

    def draw(self, canvas, x0, y, paint):
        for f, chunk, glyphs, pos in self.items:
            if not len(glyphs):
                continue
            b = skia.TextBlobBuilder()
            b.allocRunPos(f, glyphs, [skia.Point(x0 + p, y) for p in pos])
            canvas.drawTextBlob(b.make(), 0, 0, paint)


def paint(color, alpha, blur=0.0):
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(color[0], color[1], color[2], clamp(alpha)))
    if blur > 0.05:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def draw_mixed(c, text, x, y, cjk, lat, color, alpha, align='left', spacing=0.0, blur=0.0, shadow=0.0):
    m = Mixed(text, cjk, lat, spacing, spacing * 0.5)
    x0 = x - m.width / 2 if align == 'center' else (x - m.width if align == 'right' else x)
    if shadow > 0:
        m.draw(c, x0, y + 3, paint((0, 0, 0), alpha * shadow, 14))
    m.draw(c, x0, y, paint(color, alpha, blur))
    return m.width


def env(t, t0, t1, fin=0.45, fout=0.5):
    """Enter/exit progress pair (a_in 0..1, a_out 1..0)."""
    return smoothstep(t0, t0 + fin, t), 1.0 - smoothstep(t1 - fout, t1, t)


# ------------------------------------------------------------------ styles
def draw_q(c, card, t):
    a_in, a_out = env(t, card['t0'], card['t1'])
    a = a_in * a_out
    if a <= 0:
        return
    k = ease_out(a_in)
    cjk, lat = fnt('sans', 'Medium', 62), fnt('num', 'Medium', 70)
    draw_mixed(c, card['text'], W / 2, H / 2 + 22 + (1 - k) * 14, cjk, lat, WHITE, a,
               align='center', spacing=6, blur=(1 - k) * 8, shadow=0.75)


def draw_body(c, card, t):
    a_in, a_out = env(t, card['t0'], card['t1'], 0.55, 0.5)
    if a_in * a_out <= 0:
        return
    lines = card['text'].split('\n')
    x = 132
    sizes = [52, 52] if len(lines) == 2 else [52]
    y_base = H - 132 - (len(lines) - 1) * 70
    # accent bar
    bar_h = ease_out(a_in) * (len(lines) * 70 - 12)
    p = paint(ACCENT, a_out * 0.95)
    c.drawRect(skia.Rect.MakeXYWH(x - 30, y_base - 48, 4, bar_h), p)
    for i, line in enumerate(lines):
        li_in = smoothstep(card['t0'] + i * 0.22, card['t0'] + i * 0.22 + 0.6, t)
        a = li_in * a_out
        if a <= 0:
            continue
        k = ease_out(li_in)
        weight = 'Medium' if i == 0 else 'Regular'
        col = WHITE if i == 0 else (0.86, 0.85, 0.83)
        cjk, lat = fnt('sans', weight, sizes[min(i, len(sizes) - 1)] - (0 if i == 0 else 6)), fnt('num', 'Medium', 58 - (0 if i == 0 else 6))
        c.save()
        c.clipRect(skia.Rect.MakeXYWH(x - 10, y_base + i * 70 - 70, W, 100))
        draw_mixed(c, line, x, y_base + i * 70 + (1 - k) * 26, cjk, lat, col, a, spacing=3, shadow=0.8)
        c.restore()


def draw_stat(c, card, t):
    a_in, a_out = env(t, card['t0'], card['t1'], 0.5, 0.5)
    if a_in * a_out <= 0:
        return
    cx, cy = card.get('x', W / 2), H / 2 + 30
    # pre-line
    if card.get('pre'):
        a = smoothstep(card['t0'], card['t0'] + 0.45, t) * a_out
        draw_mixed(c, card['pre'], cx, cy - 128, fnt('sans', 'Regular', 38), fnt('num', 'Regular', 42),
                   (0.88, 0.87, 0.85), a, align='center', spacing=4, shadow=0.8)
    # number: rises out of a mask with a slight scale settle
    k = ease_out(smoothstep(card['t0'] + 0.15, card['t0'] + 0.9, t), 4)
    a = smoothstep(card['t0'] + 0.15, card['t0'] + 0.6, t) * a_out
    num = card['num']
    cjk, lat = fnt('sans', 'Bold', 120), fnt('num', 'SemiBold', 196)
    m = Mixed(num, cjk, lat, 4, 2)
    s = 1.0 + 0.06 * (1 - k)
    c.save()
    c.translate(cx, cy + 40)
    c.scale(s, s)
    c.clipRect(skia.Rect.MakeXYWH(-W, -260, 2 * W, 300))
    yoff = (1 - k) * 120
    m.draw(c, -m.width / 2, yoff + 3, paint((0, 0, 0), a * 0.6, 22))
    m.draw(c, -m.width / 2, yoff, paint(WHITE, a))
    c.restore()
    if card.get('cap'):
        a = smoothstep(card['t0'] + 0.55, card['t0'] + 1.0, t) * a_out
        draw_mixed(c, card['cap'], cx, cy + 118, fnt('sans', 'Regular', 38), fnt('num', 'Regular', 42),
                   ACCENT, a, align='center', spacing=4, shadow=0.8)


def draw_chapter(c, card, t):
    a_in, a_out = env(t, card['t0'], card['t1'], 0.6, 0.8)
    a = a_in * a_out
    if a <= 0:
        return
    x, y = 96, 104
    draw_mixed(c, card['text'], x, y, fnt('sans', 'Medium', 30), fnt('num', 'SemiBold', 46), ACCENT, a, shadow=0.6)
    lw = ease_out(a_in) * 54
    c.drawRect(skia.Rect.MakeXYWH(x + 58, y - 17, lw, 2), paint(WHITE, a * 0.7))
    draw_mixed(c, card['label'], x + 128, y - 2, fnt('sans', 'Medium', 28), fnt('num', 'Medium', 30), WHITE, a * 0.92,
               spacing=8, shadow=0.6)


def draw_source(c, card, t):
    if not card.get('src'):
        return
    a_in, a_out = env(t, card['t0'] + 0.6, card['t1'], 0.5, 0.4)
    a = a_in * a_out * 0.62
    if a <= 0:
        return
    draw_mixed(c, card['src'], W - 72, H - 52, fnt('sans', 'Regular', 21), fnt('num', 'Regular', 23), WHITE, a,
               align='right', spacing=2, shadow=0.6)


def draw_title(c, card, t):
    lt = t - card['t0']
    dur = card['t1'] - card['t0']
    out = 1 - smoothstep(dur - 0.9, dur - 0.05, lt)
    if out <= 0 or lt < 0:
        return
    text = card['text']
    f = fnt('serif', 'Black', 132)
    sp = 46
    ws = [f.getWidths(f.textToGlyphs(ch))[0] for ch in text]
    total = sum(ws) + sp * (len(text) - 1)
    x = W / 2 - total / 2
    for i, ch in enumerate(text):
        a = smoothstep(0.05 + i * 0.07, 0.55 + i * 0.07, lt) * out
        blur = (1 - smoothstep(0.05 + i * 0.07, 0.75 + i * 0.07, lt)) * 14
        scale = 1.0 + 0.25 * (1 - ease_out(smoothstep(0.05 + i * 0.07, 0.9 + i * 0.07, lt), 3))
        c.save()
        c.translate(x + ws[i] / 2, H / 2 + 10)
        c.scale(scale, scale)
        g = f.textToGlyphs(ch)
        b = skia.TextBlobBuilder()
        b.allocRunPos(f, g, [skia.Point(-ws[i] / 2, 0)])
        blob = b.make()
        c.drawTextBlob(blob, 0, 4, paint((0, 0, 0), a * 0.6, 20))
        c.drawTextBlob(blob, 0, 0, paint(WHITE, a, blur))
        c.restore()
        x += ws[i] + sp
    # hairline + subtitle
    la = smoothstep(0.6, 1.2, lt) * out
    lw = ease_out(smoothstep(0.6, 1.6, lt)) * 520
    p = skia.Paint(AntiAlias=True, StrokeWidth=1.4)
    p.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(W / 2 - lw / 2, 0), skia.Point(W / 2 + lw / 2, 0)],
        [skia.Color4f(1, 0.85, 0.6, 0), skia.Color4f(1, 0.85, 0.6, la), skia.Color4f(1, 0.85, 0.6, 0)]))
    c.drawLine(W / 2 - lw / 2, H / 2 + 60, W / 2 + lw / 2, H / 2 + 60, p)
    if card.get('sub'):
        a = smoothstep(1.1, 1.8, lt) * out
        draw_mixed(c, card['sub'], W / 2, H / 2 + 118, fnt('sans', 'Regular', 34), fnt('num', 'Regular', 38),
                   (0.9, 0.89, 0.87), a, align='center', spacing=6, shadow=0.7)


STYLES = dict(q=draw_q, body=draw_body, stat=draw_stat, chapter=draw_chapter, title=draw_title)


def card_layer(cards, t):
    """-> premultiplied RGBA float layer with every card visible at time t, or None."""
    live = [cd for cd in cards if cd['t0'] - 0.05 <= t <= cd['t1'] + 0.05]
    if not live:
        return None
    L = Layer()
    c = L.canvas
    for cd in live:
        STYLES[cd['style']](c, cd, t)
        draw_source(c, cd, t)
    return L.rgba()


def legibility_shade(img, cards, t):
    """Darken the image slightly behind lower-left body text and big centred stats."""
    k_body, mids = 0.0, {}
    for cd in cards:
        a_in, a_out = env(t, cd['t0'], cd['t1'])
        a = a_in * a_out
        if cd['style'] == 'body':
            k_body = max(k_body, a)
        elif cd['style'] in ('stat', 'q', 'title') and a > 0:
            cx = int(cd.get('x', W / 2))
            mids[cx] = max(mids.get(cx, 0.0), a)
    if k_body > 0:
        img *= 1 - 0.55 * k_body * _shade('body')[..., None]
    for cx, k in mids.items():
        img *= 1 - 0.45 * k * _shade(('mid', cx))[..., None]
    return img


@functools.lru_cache(None)
def _shade(kind):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    if kind == 'body':
        d = np.sqrt(((xx - 420) / 900) ** 2 + ((yy - (H - 150)) / 300) ** 2)
    else:
        cx = kind[1] if isinstance(kind, tuple) else W / 2
        wx = 900 if abs(cx - W / 2) < 10 else 620
        d = np.sqrt(((xx - cx) / wx) ** 2 + ((yy - H / 2) / 330) ** 2)
    return np.clip(1 - d, 0, 1) ** 1.5
