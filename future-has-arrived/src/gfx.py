"""Shared drawing helpers: fonts, text, easing, noise, compositing and post FX."""
import math, functools
import numpy as np, cv2, skia
from config import W, H, ASSETS

# ---------------------------------------------------------------- fonts
NOTO = '/usr/share/fonts/opentype/noto/NotoSerifCJK-{}.ttc'
WENKAI = '/usr/share/fonts/truetype/lxgw-wenkai/LXGWWenKai-{}.ttf'


@functools.lru_cache(None)
def typeface(name):
    if name.startswith('serif-'):
        return skia.Typeface.MakeFromFile(NOTO.format(name[6:]), 2)   # face 2 == SC
    if name.startswith('kai-'):
        return skia.Typeface.MakeFromFile(WENKAI.format(name[4:]))
    if name.startswith('garamond-'):
        tf = skia.Typeface.MakeFromFile(f'{ASSETS}/fonts/CormorantGaramond[wght].ttf')
        wght = int(name.split('-')[1])
        coord = skia.FontArguments.VariationPosition.Coordinate((ord('w') << 24) | (ord('g') << 16) | (ord('h') << 8) | ord('t'), wght)
        args = skia.FontArguments()
        args.setVariationDesignPosition(skia.FontArguments.VariationPosition(skia.FontArguments.VariationPosition.Coordinates([coord])))
        return tf.makeClone(args)
    raise KeyError(name)


def font(name, size):
    f = skia.Font(typeface(name), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    f.setHinting(skia.FontHinting.kNone)
    return f


def text_width(text, f, spacing=0.0):
    if not text:
        return 0.0
    ws = f.getWidths(f.textToGlyphs(text))
    return float(sum(ws) + spacing * (len(text) - 1))


def draw_text(canvas, text, x, y, f, color=(1, 1, 1), alpha=1.0, spacing=0.0, align='center', blur=0.0, shadow=None):
    """Draw a single line with letter spacing. x is the anchor per `align`, y the baseline."""
    if alpha <= 0.003 or not text:
        return
    glyphs = f.textToGlyphs(text)
    ws = f.getWidths(glyphs)
    total = sum(ws) + spacing * (len(ws) - 1)
    x0 = x - total / 2 if align == 'center' else (x - total if align == 'right' else x)
    pos, cx = [], x0
    for w in ws:
        pos.append(skia.Point(cx, y))
        cx += w + spacing
    blob = skia.TextBlob.MakeFromPosText(text, pos, f) if hasattr(skia.TextBlob, 'MakeFromPosText') else None
    if blob is None:
        builder = skia.TextBlobBuilder()
        builder.allocRunPos(f, glyphs, pos)
        blob = builder.make()
    if shadow:
        sp = skia.Paint(AntiAlias=True, Color=skia.Color4f(0, 0, 0, min(1, alpha * shadow[1])))
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, shadow[0]))
        canvas.drawTextBlob(blob, 0, 2, sp)
    p = skia.Paint(AntiAlias=True, Color=skia.Color4f(color[0], color[1], color[2], min(1.0, alpha)))
    if blur > 0.05:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    canvas.drawTextBlob(blob, 0, 0, p)
    return total


# ---------------------------------------------------------------- surfaces
def new_surface(w=W, h=H):
    info = skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


def surface_rgba(surface):
    """-> float32 HxWx4 premultiplied, 0..1"""
    a = surface.makeImageSnapshot().toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                                            alphaType=skia.AlphaType.kPremul_AlphaType)
    return a.astype(np.float32) * (1.0 / 255.0)


def over(dst, src_premul):
    """Composite premultiplied RGBA layer over an RGB float image (in place)."""
    a = src_premul[..., 3:4]
    dst *= (1.0 - a)
    dst += src_premul[..., :3]
    return dst


def add(dst, src_premul, k=1.0):
    dst += src_premul[..., :3] * k
    return dst


class Layer:
    """Convenience: a skia canvas that gets composited onto a float frame."""

    def __init__(self, w=W, h=H):
        self.surface = new_surface(w, h)
        self.canvas = self.surface.getCanvas()
        self.canvas.clear(skia.Color4f(0, 0, 0, 0))

    def rgba(self):
        return surface_rgba(self.surface)


# ---------------------------------------------------------------- math helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else float(x >= e1)
    return t * t * (3 - 2 * t)


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def ease_out(t, p=3):
    t = clamp(t)
    return 1 - (1 - t) ** p


def ease_in(t, p=3):
    t = clamp(t)
    return t ** p


def ease_io_cubic(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def fade(t, t0, t1, fin=0.4, fout=0.4):
    """1 inside [t0,t1] with linear-smooth ramps."""
    if t < t0 - 1e-9 or t > t1 + fout:
        return 0.0
    a = smoothstep(t0, t0 + fin, t) if fin > 0 else 1.0
    b = 1.0 - smoothstep(t1, t1 + fout, t) if fout > 0 else 1.0
    return min(a, b)


# 1D value noise, deterministic
_rng = np.random.default_rng(7)
_perm = _rng.random(4096)


def noise1(x, seed=0):
    x = x + seed * 57.31
    i = math.floor(x)
    f = x - i
    a = _perm[i % 4096]
    b = _perm[(i + 1) % 4096]
    u = f * f * (3 - 2 * f)
    return a + (b - a) * u   # 0..1


def fbm1(x, seed=0, oct=3):
    v, amp, tot = 0.0, 1.0, 0.0
    for o in range(oct):
        v += amp * noise1(x * (2 ** o), seed + o * 13)
        tot += amp
        amp *= 0.5
    return v / tot


def value_noise_2d(h, w, scale, seed=0):
    """Smooth 2D noise image in 0..1 (bicubic-upsampled random grid)."""
    rng = np.random.default_rng(seed)
    gh, gw = max(2, int(h / scale) + 3), max(2, int(w / scale) + 3)
    g = rng.random((gh, gw)).astype(np.float32)
    big = cv2.resize(g, (int(gw * scale), int(gh * scale)), interpolation=cv2.INTER_CUBIC)
    return np.clip(big[:h, :w], 0, 1)


def fbm_2d(h, w, scale, seed=0, octaves=5, gain=0.5):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise_2d(h, w, max(1.5, scale / (2 ** o)), seed + o * 101)
        tot += amp
        amp *= gain
    return out / tot


# ---------------------------------------------------------------- post FX
_grain_bank = None


def grain(img, strength, frame_idx):
    global _grain_bank
    if strength <= 0:
        return img
    if _grain_bank is None:
        rng = np.random.default_rng(11)
        bank = rng.normal(0, 1, (6, H + 64, W + 64)).astype(np.float32)
        # soften grain a touch so it reads as film rather than digital noise
        for i in range(len(bank)):
            bank[i] = cv2.GaussianBlur(bank[i], (0, 0), 0.65) * 1.7
        _grain_bank = bank
    rs = np.random.default_rng(frame_idx * 7919 + 3)
    k = rs.integers(0, len(_grain_bank))
    ox, oy = rs.integers(0, 64), rs.integers(0, 64)
    g = _grain_bank[k, oy:oy + H, ox:ox + W]
    lum = img.mean(axis=2, keepdims=True)
    # grain more visible in mid-tones, less in deep black and in highlights
    wgt = 0.35 + 0.65 * np.clip(lum * 3.0, 0, 1) * np.clip(1.6 - lum, 0, 1)
    img += g[..., None] * strength * wgt
    return img


def bloom(img, threshold=0.75, strength=0.6, radius=1.0):
    if strength <= 0:
        return img
    bright = np.maximum(img - threshold, 0)
    small = cv2.resize(bright, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b1 = cv2.GaussianBlur(small, (0, 0), 3 * radius)
    b2 = cv2.GaussianBlur(small, (0, 0), 12 * radius)
    b3 = cv2.GaussianBlur(small, (0, 0), 36 * radius)
    b = b1 * 0.5 + b2 * 0.35 + b3 * 0.25
    img += cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR) * strength
    return img


_vig = None


def vignette(img, amount=0.35):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.85 + ((yy - H / 2) / (H / 2)) ** 2 * 0.6)
        _vig = np.clip(r, 0, 1.5)
    img *= (1 - amount * _vig ** 2.2)[..., None]
    return img


def tonemap(img):
    """Gentle highlight shoulder: linear below 0.8, compresses above."""
    x = np.maximum(img, 0)
    knee = 0.8
    over_ = np.maximum(x - knee, 0)
    y = np.minimum(x, knee) + (1 - knee) * (1 - np.exp(-over_ / (1 - knee)))
    return y


def to_u8(img):
    return np.clip(img * 255.0 + 0.5, 0, 255).astype(np.uint8)


def radial_glow(img, cx, cy, radius, color, intensity, falloff=2.0):
    """Additive radial light (1/(1+(d/r)^falloff)) in a bounding box for speed."""
    R = int(radius * 6)
    x0, x1 = int(max(0, cx - R)), int(min(W, cx + R))
    y0, y1 = int(max(0, cy - R)), int(min(H, cy + R))
    if x1 <= x0 or y1 <= y0:
        return img
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / radius
    g = 1.0 / (1.0 + d ** falloff)
    g *= np.clip(1.2 - d / 6.0, 0, 1)
    img[y0:y1, x0:x1] += g[..., None] * (np.array(color, np.float32) * intensity)
    return img


def vsmooth(e0, e1, x):
    """Vectorised smoothstep for numpy arrays."""
    t = np.clip((np.asarray(x, np.float32) - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)
