"""A small procedural oil-lamp flame, rendered additively into a float frame."""
import math
import numpy as np, cv2, skia
from gfx import fbm1, noise1, radial_glow, Layer, over
from config import W, H

FLAME_WARM = np.array([1.0, 0.62, 0.26], np.float32)


def flame_params(t, seed=0):
    sway = 0.05 * math.sin(1.7 * t + seed) + 0.05 * (fbm1(t * 1.3, seed + 3) - 0.5)
    flick = 1.0 + 0.10 * (fbm1(t * 6.0, seed + 5) - 0.5) + 0.04 * (noise1(t * 17.0, seed + 9) - 0.5)
    return sway, flick


def draw_flame(img, cx, cy, scale, t, intensity=1.0, seed=0, glow=True):
    """cx, cy: base of the flame (screen px). scale 1 => flame ~150 px tall."""
    if intensity <= 0.001:
        return img
    sway, flick = flame_params(t, seed)
    fh = 150.0 * scale * flick
    fw = 34.0 * scale
    if fh < 6:
        # far away: a warm point of light
        return radial_glow(img, cx, cy - fh * 0.4, max(1.2, fh * 0.35), FLAME_WARM, 1.6 * intensity)
    pad = 10 * scale + 4
    x0, x1 = int(cx - fw - pad), int(cx + fw + pad)
    y0, y1 = int(cy - fh * 1.08 - pad), int(cy + fh * 0.12 + pad)
    X0, X1, Y0, Y1 = max(0, x0), min(W, x1), max(0, y0), min(H, y1)
    if X1 > X0 and Y1 > Y0:
        yy, xx = np.mgrid[Y0:Y1, X0:X1].astype(np.float32)
        v = (cy - yy) / fh                       # 0 at base, 1 at tip
        # horizontal displacement grows toward the tip
        tip = np.clip(v, 0, 1.2)
        wob = np.array([fbm1(t * 3.1 + k * 0.9, seed + 11) - 0.5 for k in range(8)], np.float32)
        vi = np.clip((tip * 7).astype(np.int32), 0, 7)
        dx = (sway * 1.4 * tip ** 1.6 + 0.10 * wob[vi] * tip ** 2) * fw * 2.2
        u = (xx - cx - dx) / fw
        # tear-drop width profile
        vc = np.clip(v, 0.0, 1.0)
        prof = 1.15 * np.power(vc + 0.02, 0.42) * np.power(1.0 - vc + 1e-4, 1.25)
        prof = np.where(v < 0, np.maximum(0.0, 1.0 + v * 6.0) * 0.55, prof)
        r = np.abs(u) / np.maximum(prof, 1e-3)
        dens = np.clip(1.0 - r, 0, 1) ** 0.9
        dens *= np.clip((v + 0.06) / 0.10, 0, 1) * np.clip((1.05 - v) / 0.15, 0, 1)
        core = np.clip(1.0 - r / 0.55, 0, 1) * np.clip(1 - np.abs(v - 0.32) / 0.38, 0, 1)
        blue = np.clip(1.0 - np.abs(v - 0.02) / 0.10, 0, 1) * np.clip(1 - r, 0, 1) * 0.6
        col = (dens[..., None] * np.array([1.0, 0.48, 0.13], np.float32) * 1.25
               + (dens * core)[..., None] * np.array([0.9, 0.85, 0.62], np.float32) * 1.9
               + blue[..., None] * np.array([0.15, 0.25, 0.9], np.float32))
        col *= intensity * flick
        col = cv2.GaussianBlur(col, (0, 0), max(0.6, 0.9 * scale))
        img[Y0:Y1, X0:X1] += col
    if glow:
        gcy = cy - fh * 0.45
        radial_glow(img, cx, gcy, 26 * scale, FLAME_WARM, 0.55 * intensity * flick)
        radial_glow(img, cx, gcy, 140 * scale, FLAME_WARM, 0.11 * intensity * flick, falloff=1.6)
    return img


def draw_lamp(img, cx, cy, scale, t, light=1.0):
    """A shallow clay oil-lamp dish whose rim catches the flame light. cx,cy = flame base."""
    L = Layer()
    c = L.canvas
    w = 170 * scale
    top = cy + 10 * scale
    p = skia.Path()
    p.moveTo(cx - w, top)
    p.cubicTo(cx - w * 0.92, top + 70 * scale, cx + w * 0.92, top + 70 * scale, cx + w, top)
    p.close()
    body = skia.Paint(AntiAlias=True)
    body.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(cx, top), skia.Point(cx, top + 60 * scale)],
        [skia.Color4f(0.30 * light, 0.17 * light, 0.08 * light, 1), skia.Color4f(0.02, 0.012, 0.008, 1)]))
    c.drawPath(p, body)
    # oil surface (dark ellipse) and lit rim
    oval = skia.Rect.MakeXYWH(cx - w, top - 9 * scale, 2 * w, 18 * scale)
    oil = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.05 * light, 0.03 * light, 0.015 * light, 1))
    c.drawOval(oval, oil)
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.2 * scale)
    rim.setShader(skia.GradientShader.MakeRadial(skia.Point(cx, top - 6 * scale), w * 1.05,
                                                 [skia.Color4f(1.0, 0.72, 0.4, 0.95 * light), skia.Color4f(0.5, 0.3, 0.15, 0.05 * light)]))
    c.drawOval(oval, rim)
    # wick
    wick = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.05, 0.03, 0.02, 1), StrokeWidth=3.0 * scale,
                      Style=skia.Paint.kStroke_Style, StrokeCap=skia.Paint.kRound_Cap)
    c.drawLine(cx - 3 * scale, top - 2 * scale, cx, cy - 2 * scale, wick)
    over(img, L.rgba())
    return img


def draw_table_light(img, cx, cy, scale, light=1.0):
    """Warm pool of light on the surface the lamp sits on + faint air haze."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    top = cy + 40 * scale
    plane = (yy > top).astype(np.float32)
    dx = (xx - cx) / (900 * scale)
    dy = (yy - top - 10 * scale) / (190 * scale)
    pool = 1.0 / (1.0 + (dx * dx + dy * dy) * 2.6)
    pool *= plane * np.clip((yy - top) / (14 * scale), 0, 1)
    wood = 0.85 + 0.15 * np.sin(yy * 0.9 / scale + np.sin(xx * 0.004) * 6)
    img += (pool * wood)[..., None] * (np.array([0.42, 0.22, 0.09], np.float32) * light)
    return img
