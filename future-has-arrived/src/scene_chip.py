"""Hook (0–14.6s) + title backdrop (14.6–19.0s).
A dusk flight over what looks like a city — copper interconnect inside a chip — then a fast
rise, a zoom-blur into the die photo, and the die floating as an object."""
import math
import numpy as np, cv2
import gl3d, chip_geo, sky, gfx, die
from gfx import smoothstep, clamp, ease_in_out, ease_out, ease_in, lerp
from config import W, H

_R = {}

KEY = np.array((-0.55, -0.20, 0.30))
KEY /= np.linalg.norm(KEY)
HOR = (0.85, 0.40, 0.21)
ZEN = (0.012, 0.022, 0.065)
FOG = (0.16, 0.085, 0.10)


def _init():
    if _R:
        return
    C, S, K, E, wires, top = chip_geo.build()
    _R['boxes'] = gl3d.Boxes(C, S, K, E)
    _R['sig'] = chip_geo.make_signals(wires)
    sc, ss, sk, se = chip_geo.signal_boxes(_R['sig'], 0.0)
    _R['sboxes'] = gl3d.Boxes(sc, ss, sk, se)
    sm = gl3d.ShadowMap(4096)
    center = np.array([270, 0, 0])
    lview = gl3d.look_at(center - KEY * 800, center, (0, 1, 0))
    lproj = gl3d.ortho(-600, 600, -600, 600, 1, 1800)
    _R['lvp'] = lproj @ lview
    sm.render([_R['boxes']], _R['lvp'])
    _R['sm'] = sm
    d = die.make_die()
    _R['die'] = cv2.resize(d, (2048, 2048), interpolation=cv2.INTER_AREA)
    _R['die_full'] = d


def city_camera(t):
    """Returns eye, target, fov for the city flight (t in seconds from 0)."""
    # glide
    g = min(t, 6.2)
    eye = np.array([10 + 21 * g, 96 - 4.2 * g, 150 - 5.5 * g])
    fwd = np.array([1.0, -0.42, -0.86])
    if t <= 6.2:
        return eye, eye + fwd * 100, 50.0
    # rise and tilt to look straight down
    u = clamp((t - 6.2) / 2.6)
    e = ease_in(u, 2.2)
    top = np.array([300.0, 520.0, -20.0])
    eye2 = eye + (top - eye) * e
    look_down = np.array([0.02, -1.0, -0.12])
    d = fwd * (1 - ease_in_out(u)) + look_down * ease_in_out(u)
    d /= np.linalg.norm(d)
    return eye2, eye2 + d * 100, 50.0 + 6 * e


def render_city(t):
    _init()
    eye, tgt_pt, fov = city_camera(t)
    view = gl3d.look_at(eye, tgt_pt, (0, 1, 0) if abs((tgt_pt - eye)[1]) < 99 else (0, 0, -1))
    proj = gl3d.perspective(fov, W / H, 0.5, 5000)
    tg = gl3d.target()
    tg.begin((0, 0, 0, 1))
    sky.render(view, proj, eye, ZEN, HOR, tuple(KEY), (2.4, 1.45, 0.85))
    U = dict(view=view, proj=proj, eye=tuple(eye), key_dir=tuple(KEY), key_col=(3.1, 1.85, 1.05),
             fill_dir=(0.5, -0.45, -0.6), fill_col=(0.10, 0.15, 0.32),
             sky_col=ZEN, hor_col=HOR, gnd_col=(0.02, 0.02, 0.03),
             fog_col=FOG, fog_density=0.0040, fog_height=70.0, metal=1.0, rough=0.28,
             exposure=1.0, light_vp=_R['lvp'], use_shadow=1.0, shadow_bias=0.0012, time=t)
    _R['sm'].tex.use(location=0)
    _R['boxes'].prog['shadow_map'].value = 0
    _R['boxes'].render(**U)
    sc, ss, sk, se = chip_geo.signal_boxes(_R['sig'], t)
    _R['sboxes'].update(sc, ss, sk, se)
    U['use_shadow'] = 0.0
    _R['sboxes'].render(**U)
    img = tg.read()[..., :3].copy()
    return img


def zoom_blur(img, strength, cx=W / 2, cy=H / 2, n=8):
    if strength <= 0.002:
        return img
    acc = img.copy()
    for i in range(1, n):
        s = 1 + strength * i / n
        M = np.array([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]], np.float32)
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def render_die_zoom(t, t0, t1):
    """Die photo seen top-down, zooming out from a cell region to the whole die."""
    _init()
    u = clamp((t - t0) / (t1 - t0))
    z = math.exp(lerp(math.log(7.0), math.log(1.0), ease_out(u, 2)))    # magnification
    d = _R['die_full']
    N = d.shape[0]
    fit = 860.0 / N                         # whole die = 860 px tall at z=1
    s = fit * z
    cx, cy = N * 0.47, N * 0.52             # zoom centre in texture
    M = np.array([[s, 0, W / 2 - cx * s], [0, s, H / 2 - cy * s]], np.float32)
    img = cv2.warpAffine(d, M, (W, H), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT)
    # simple sheen
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    img *= (0.85 + 0.3 * yy)[..., None]
    return img


def render_die_object(t, t0):
    """The die as a floating, slowly turning object with a moving specular sweep."""
    _init()
    lt = t - t0
    tex = _R['die']
    n = tex.shape[0]
    tilt = math.radians(52 - 6 * ease_out(clamp(lt / 3)))
    spin = math.radians(-18 + 7.5 * lt)
    size = 1.0
    corners = np.array([[-size, 0, -size], [size, 0, -size], [size, 0, size], [-size, 0, size]], np.float64)
    thick = 0.035

    def R(p):
        c, s = math.cos(spin), math.sin(spin)
        p = p @ np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]]).T
        c, s = math.cos(tilt), math.sin(tilt)
        return p @ np.array([[1, 0, 0], [0, c, -s], [0, s, c]]).T

    cam_d = 4.2
    f = 1750

    def P(p):
        z = cam_d - p[:, 2]
        return np.c_[W / 2 + f * p[:, 0] / z, H / 2 + 10 - f * p[:, 1] / z]

    top = P(R(corners))
    bot = P(R(corners - np.array([0, thick, 0])))
    img = np.zeros((H, W, 3), np.float32)
    # backdrop: dark warm haze + soft shadow under the die
    gfx.radial_glow(img, W / 2, H / 2 + 40, 520, (0.55, 0.30, 0.16), 0.20, falloff=2.2)
    shadow = np.zeros((H, W), np.float32)
    cv2.fillConvexPoly(shadow, (bot + np.array([0, 90])).astype(np.int32), 1.0)
    shadow = cv2.GaussianBlur(shadow, (0, 0), 45)
    img *= (1 - 0.7 * shadow)[..., None]
    # side faces
    for i in range(4):
        j = (i + 1) % 4
        quad = np.array([top[i], top[j], bot[j], bot[i]], np.float32)
        nrm_y = (top[i][1] + top[j][1]) / 2
        shade = 0.10 + 0.25 * clamp((nrm_y - H / 2 + 200) / 500)
        cv2.fillConvexPoly(img, quad.astype(np.int32), (0.22 * shade * 3, 0.20 * shade * 3, 0.19 * shade * 3), cv2.LINE_AA)
    # top face: perspective-warp the die photo
    src = np.array([[0, 0], [n, 0], [n, n], [0, n]], np.float32)
    Mp = cv2.getPerspectiveTransform(src, top.astype(np.float32))
    face = cv2.warpPerspective(tex, Mp, (W, H), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.ones((n, n), np.float32), Mp, (W, H), flags=cv2.INTER_LINEAR)
    # specular sweep in texture space
    uu, vv = np.meshgrid(np.linspace(0, 1, 256, dtype=np.float32), np.linspace(0, 1, 256, dtype=np.float32))
    ph = -0.6 + 0.32 * lt
    band = np.exp(-(((uu * 0.8 + vv * 0.6) - ph) / 0.16) ** 2)
    band = cv2.warpPerspective(band, cv2.getPerspectiveTransform(np.array([[0, 0], [256, 0], [256, 256], [0, 256]], np.float32),
                                                                   top.astype(np.float32)), (W, H))
    face = face * (0.95 + 0.9 * band[..., None]) + band[..., None] * np.array([0.55, 0.45, 0.32], np.float32) * 0.6
    img = img * (1 - mask[..., None]) + face * mask[..., None]
    # rim highlight on the top edges
    for i in range(4):
        j = (i + 1) % 4
        cv2.line(img, tuple(top[i].astype(int)), tuple(top[j].astype(int)), (0.9, 0.7, 0.45), 2, cv2.LINE_AA)
    return img


def render(t):
    if t < 8.55:
        img = render_city(t)
        fade_in = smoothstep(0.0, 0.35, t)
        img *= fade_in
        zb = smoothstep(7.2, 8.55, t) * 0.55
        img = zoom_blur(img, zb)
        img = img * (1 - 0.0) + smoothstep(8.1, 8.55, t) * 1.6 * np.ones_like(img) * 0.0
        flash = smoothstep(8.25, 8.55, t)
        img = img * (1 - flash) + flash * 1.4
        return img
    if t < 9.9:
        img = render_die_zoom(t, 8.55, 9.9)
        zb = (1 - smoothstep(8.55, 9.5, t)) * 0.6
        img = zoom_blur(img, zb)
        flash = 1 - smoothstep(8.55, 8.95, t)
        img = img * (1 - flash) + flash * 1.4
        # dissolve into the floating object
        k = smoothstep(9.45, 9.9, t)
        if k > 0:
            img = img * (1 - k) + render_die_object(t, 9.45) * k
        return img
    img = render_die_object(t, 9.45)
    if t > 14.6:      # title backdrop: dim and soften
        k = smoothstep(14.6, 15.4, t)
        img = img * (1 - 0.55 * k)
        img = cv2.GaussianBlur(img, (0, 0), 0.1 + 6 * k) if k > 0.01 else img
        img = img * (1 - smoothstep(18.3, 19.0, t))
    return img
