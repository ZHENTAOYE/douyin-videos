"""v2 compositor: scene visuals + text cards + post FX, for any time t."""
import importlib
import numpy as np
import gfx, cards, story
from config import W, H

# scene id -> (module, function). Modules are imported lazily so one scene can be rendered alone.
SCENE_FN = {
    'chip': ('scene_chip', 'render'),
    'title': ('scene_chip', 'render'),
    'moore': ('scene_moore', 'render'),
    'euv': ('scene_euv', 'render'),
    'earth': ('scene_earth', 'render'),
    'voyager': ('scene_space', 'render_voyager'),
    'deepfield': ('scene_space', 'render_deepfield'),
    'moon': ('scene_space', 'render_moon'),
    'lhc': ('scene_extreme', 'render_lhc'),
    'fusion': ('scene_extreme', 'render_fusion'),
    'precision': ('scene_extreme', 'render_precision'),
    'dna': ('scene_life', 'render_dna'),
    'protein': ('scene_life', 'render_protein'),
    'ai': ('scene_life', 'render_ai'),
    'accel': ('scene_accel', 'render'),
    'finale': ('scene_accel', 'render_finale'),
}

# post: bloom threshold, bloom strength, vignette, grain
POST = {
    'chip': (0.75, 0.75, 0.32, 0.016), 'title': (0.75, 0.75, 0.32, 0.016),
    'moore': (0.7, 0.8, 0.3, 0.014), 'euv': (0.6, 1.0, 0.35, 0.016), 'earth': (0.6, 0.85, 0.28, 0.014),
    'voyager': (0.6, 0.9, 0.3, 0.014), 'deepfield': (0.55, 0.9, 0.25, 0.012), 'moon': (0.7, 0.6, 0.3, 0.014),
    'lhc': (0.55, 1.0, 0.32, 0.014), 'fusion': (0.55, 1.0, 0.32, 0.014), 'precision': (0.6, 0.9, 0.3, 0.014),
    'dna': (0.6, 0.9, 0.3, 0.014), 'protein': (0.65, 0.8, 0.3, 0.014), 'ai': (0.7, 0.6, 0.3, 0.012),
    'accel': (0.6, 0.9, 0.3, 0.014), 'finale': (0.6, 0.9, 0.35, 0.014),
}

_fns = {}


def scene_fn(sid):
    if sid not in _fns:
        mod, fn = SCENE_FN[sid]
        try:
            _fns[sid] = getattr(importlib.import_module(mod), fn)
        except (ImportError, AttributeError):
            _fns[sid] = None
    return _fns[sid]


def render_frame(t, frame_idx=0):
    sid, a, b = story.scene_at(t)
    fn = scene_fn(sid)
    img = fn(t) if fn else np.zeros((H, W, 3), np.float32)
    img = np.nan_to_num(np.ascontiguousarray(img[..., :3], dtype=np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    thr, bs, vig, gr = POST[sid]
    img = gfx.bloom(img, thr, bs)
    img = gfx.tonemap(img)
    img = gfx.vignette(img, vig)
    img = cards.legibility_shade(img, story.CARDS, t)
    layer = cards.card_layer(story.CARDS, t)
    if layer is not None:
        gfx.over(img, layer)
    img = gfx.grain(img, gr, frame_idx)
    return gfx.to_u8(img)
