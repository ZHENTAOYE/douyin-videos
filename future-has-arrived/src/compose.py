"""Frame compositor: picks the scene renderer for time t, applies post FX and subtitles."""
import numpy as np
import gfx
from gfx import Layer, font, draw_text, smoothstep, clamp
from config import W, H

import scene_prophecy as sp

RENDERERS = {}
POST = {
    # scene: (bloom threshold, bloom strength, vignette, grain)
    'prophecy': (0.85, 0.25, 0.45, 0.030),
    'reveal': (0.9, 0.2, 0.3, 0.022),
    'title1': (0.7, 0.5, 0.3, 0.022),
    'night': (0.55, 0.85, 0.45, 0.026),
    'dots': (0.45, 0.9, 0.35, 0.022),
    'accel': (0.6, 0.6, 0.35, 0.022),
    'earth': (0.5, 0.8, 0.3, 0.020),
    'quiet': (0.55, 0.7, 0.35, 0.022),
    'look': (0.55, 0.7, 0.35, 0.022),
    'coda': (0.55, 0.85, 0.45, 0.026),
    'title2': (0.7, 0.5, 0.3, 0.022),
}
NO_SUBS = {'prophecy', 'reveal', 'title1', 'title2'}


def register():
    RENDERERS['prophecy'] = sp.render_prophecy
    RENDERERS['reveal'] = sp.render_reveal
    RENDERERS['title1'] = sp.render_title1
    try:
        import scene_night
        RENDERERS['night'] = scene_night.render_night
        RENDERERS['dots'] = scene_night.render_night
    except ImportError:
        pass
    for mod, names in [('scene_accel', ['accel']), ('scene_earth', ['earth']), ('scene_quiet', ['quiet']),
                       ('scene_look', ['look', 'coda', 'title2'])]:
        try:
            m = __import__(mod)
            for n in names:
                RENDERERS[n] = getattr(m, f'render_{n}')
        except (ImportError, AttributeError):
            pass


register()


def scene_at(tl, t):
    for s in tl['scenes']:
        if s['start'] <= t < s['end']:
            return s
    return tl['scenes'][-1]


def subtitle_layer(tl, t, img):
    """Bottom subtitles, serif, soft shadow. Only one line at a time."""
    cur = None
    for lid, ln in tl['lines'].items():
        if ln['scene'] in NO_SUBS:
            continue
        if ln['start'] - 0.12 <= t <= ln['end'] + 0.55:
            cur = ln
    if cur is None:
        return img
    a = smoothstep(cur['start'] - 0.12, cur['start'] + 0.18, t) * (1 - smoothstep(cur['end'] + 0.25, cur['end'] + 0.55, t))
    if a <= 0:
        return img
    L = Layer()
    f = font('serif-Regular', 42)
    draw_text(L.canvas, cur['sub'], W / 2, H - 92, f, (0.94, 0.93, 0.9), a * 0.94, spacing=3, shadow=(7, 0.85))
    gfx.over(img, L.rgba())
    return img


def render_frame(tl, t, frame_idx):
    sc = scene_at(tl, t)
    fn = RENDERERS.get(sc['id'])
    img = fn(tl, t) if fn else np.zeros((H, W, 3), np.float32)
    thr, bs, vig, gr = POST[sc['id']]
    img = gfx.bloom(img, thr, bs)
    img = gfx.tonemap(img)
    img = gfx.vignette(img, vig)
    img = subtitle_layer(tl, t, img)
    img = gfx.grain(img, gr, frame_idx)
    return gfx.to_u8(img)
