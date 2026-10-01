"""03 连接 (62.0–96.0s): Earth at night with light routes across the oceans (illustrative), the
satellite swarm, and the navigation-satellite relativity beat."""
import math
import numpy as np, cv2, skia
import gl3d, earthgl, gfx, cards
from gfx import smoothstep, clamp, ease_in_out, ease_out, lerp, Layer
from config import W, H

HUBS = {
    'NY': (40.7, -74.0), 'LDN': (50.8, -4.5), 'LIS': (38.7, -9.1), 'MRS': (43.3, 5.4), 'ALX': (31.2, 29.9),
    'DJI': (11.6, 43.1), 'BOM': (19.1, 72.9), 'MAA': (13.1, 80.3), 'SIN': (1.35, 103.8), 'HKG': (22.3, 114.2),
    'SHA': (31.2, 121.5), 'TYO': (35.7, 139.7), 'PUS': (35.1, 129.0), 'LAX': (34.0, -118.2), 'SEA': (47.6, -122.3),
    'SYD': (-33.9, 151.2), 'AKL': (-36.8, 174.8), 'FOR': (-3.7, -38.5), 'LOS': (6.5, 3.4), 'CPT': (-33.9, 18.4),
    'MIA': (25.8, -80.2), 'MBA': (-4.0, 39.7), 'JKT': (-6.2, 106.8), 'GUM': (13.4, 144.8), 'HNL': (21.3, -157.8),
    'VAP': (-33.0, -71.6), 'PTY': (9.0, -79.5), 'PER': (-31.9, 115.9), 'NOR': (58.1, 7.9), 'RIO': (-22.9, -43.2),
}
ROUTES = [('NY', 'LDN'), ('NY', 'LIS'), ('NY', 'NOR'), ('MIA', 'FOR'), ('FOR', 'LIS'), ('LOS', 'LIS'), ('CPT', 'LOS'),
          ('CPT', 'MBA'), ('MRS', 'ALX'), ('ALX', 'DJI'), ('DJI', 'BOM'), ('MRS', 'BOM'), ('BOM', 'SIN'), ('MAA', 'SIN'),
          ('SIN', 'HKG'), ('HKG', 'SHA'), ('SHA', 'TYO'), ('TYO', 'SEA'), ('TYO', 'LAX'), ('SHA', 'LAX'), ('HKG', 'GUM'),
          ('GUM', 'HNL'), ('HNL', 'LAX'), ('SIN', 'SYD'), ('SYD', 'AKL'), ('SYD', 'HNL'), ('LAX', 'PTY'), ('PTY', 'VAP'),
          ('PUS', 'SEA'), ('JKT', 'SIN'), ('PER', 'SIN'), ('MBA', 'DJI'), ('RIO', 'FOR'), ('RIO', 'CPT'), ('LDN', 'LIS'),
          ('MIA', 'PTY'), ('TYO', 'GUM'), ('SHA', 'PUS'), ('JKT', 'PER'), ('VAP', 'RIO')]

_S = {}


def slerp_arc(a, b, n=90, lift=0.012):
    pa, pb = earthgl.latlon_to_xyz(*a), earthgl.latlon_to_xyz(*b)
    om = math.acos(np.clip(pa @ pb, -1, 1))
    ts = np.linspace(0, 1, n)
    pts = (np.sin((1 - ts) * om)[:, None] * pa + np.sin(ts * om)[:, None] * pb) / math.sin(om)
    h = 1.004 + lift * np.sin(ts * math.pi) * min(1.0, om / 0.6)
    return pts * h[:, None]


def routes_world():
    if 'routes' not in _S:
        _S['routes'] = [slerp_arc(HUBS[a], HUBS[b]) for a, b in ROUTES]
    return _S['routes']


def rot_y(p, a):
    c, s = math.cos(a), math.sin(a)
    return np.stack([c * p[..., 0] + s * p[..., 2], p[..., 1], -s * p[..., 0] + c * p[..., 2]], -1)


# ------------------------------------------------------------------ satellites
def satellites():
    if 'sats' in _S:
        return _S['sats']
    rng = np.random.default_rng(8)
    R_E = 6371.0
    shells = [  # (altitude km, inclination deg, count)
        (550, 53.0, 3600), (540, 53.2, 1500), (570, 70.0, 700), (560, 97.6, 600), (530, 43.0, 1600),
        (1200, 87.9, 630), (700, 98.0, 900), (800, 86.4, 400), (500, 45.0, 300)]
    a, inc, raan, ph = [], [], [], []
    for alt, i, n in shells:
        planes = max(6, int(math.sqrt(n) * 1.3))
        for k in range(n):
            a.append((R_E + alt + rng.normal(0, 6)) / R_E)
            inc.append(math.radians(i + rng.normal(0, 0.3)))
            raan.append(2 * math.pi * (k % planes) / planes + rng.normal(0, 0.01))
            ph.append(rng.uniform(0, 2 * math.pi))
    # navigation (MEO) and geostationary belts
    nav = []
    for k in range(30):
        nav.append(((R_E + 20200) / R_E, math.radians(55), 2 * math.pi * (k % 6) / 6, 2 * math.pi * (k // 6) / 5 + (k % 6) * 0.3))
    for k in range(24):
        nav.append(((R_E + 21500) / R_E, math.radians(55), 2 * math.pi * (k % 3) / 3 + 0.5, 2 * math.pi * (k // 3) / 8))
    geo = [((R_E + 35786) / R_E, 0.0, 0.0, 2 * math.pi * k / 120 + rng.normal(0, 0.02)) for k in range(120)]
    _S['sats'] = dict(a=np.array(a), inc=np.array(inc), raan=np.array(raan), ph=np.array(ph),
                      nav=np.array(nav), geo=np.array(geo))
    return _S['sats']


def orbit_pos(a, inc, raan, ph, t, speed=1.0):
    # mean motion ~ a^-1.5 (relative), sped up for visibility
    n = speed * a ** -1.5
    u = ph + n * t
    x = np.cos(u)
    y = np.sin(u)
    # orbital plane: rotate by inclination about x, then by RAAN about y (north)
    xo = x
    yo = y * np.sin(inc)
    zo = y * np.cos(inc)
    c, s = np.cos(raan), np.sin(raan)
    return np.stack([c * xo + s * zo, yo, -s * xo + c * zo], -1) * a[..., None] if np.ndim(a) else \
        np.stack([c * xo + s * zo, yo, -s * xo + c * zo], -1) * a


# ------------------------------------------------------------------ camera
def camera(t):
    """-> eye, target, fov, earth rotation, sun direction."""
    # Earth turns slowly westward in view so Asia comes round for the stat
    rot = math.radians(lerp(10, -95, ease_in_out(clamp((t - 62.0) / 16.0))))
    if t < 74.6:
        u = clamp((t - 62.0) / 12.6)
        dist = lerp(2.25, 2.05, ease_in_out(u))
        el = math.radians(lerp(18, 24, u))
        az = math.radians(lerp(-8, 4, u))
        eye = np.array([dist * math.cos(el) * math.sin(az), dist * math.sin(el), dist * math.cos(el) * math.cos(az)])
        tgt = np.array([0.0, 0.18, 0.0])
        return eye, tgt, 40.0, rot
    # pull back for the satellite swarm and the navigation belts, then a slow push back in
    u = ease_in_out(clamp((t - 74.6) / 6.5))
    dist = lerp(2.05, 12.5, u ** 1.15) - 3.6 * ease_in_out(clamp((t - 81.5) / 14.0))
    el = math.radians(lerp(24, 20, u))
    az = math.radians(lerp(4, -30, u) + (t - 74.6) * 1.2)
    eye = np.array([dist * math.cos(el) * math.sin(az), dist * math.sin(el), dist * math.cos(el) * math.cos(az)])
    tgt = np.array([0.0, lerp(0.18, 0.0, u), 0.0])
    return eye, tgt, lerp(40.0, 38.0, u), rot


def sun_dir(t):
    # sun behind the Earth, a little to the right: a thin sunrise crescent
    a = math.radians(lerp(165, 150, clamp((t - 62.0) / 34.0)))
    s = np.array([math.sin(a), 0.22, math.cos(a)])
    return s / np.linalg.norm(s)


def render(t):
    eye, tgt, fov, rot = camera(t)
    view = gl3d.look_at(eye, tgt)
    proj = gl3d.perspective(fov, W / H, 0.01, 200)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    reveal = smoothstep(62.2, 64.0, t)
    earthgl.render_earth(view, proj, eye, sun_dir(t), rot, lights_gain=1.35, day_gain=0.9, star_gain=0.9,
                         lights_reveal=reveal, atmo_gain=1.0)
    img = tg.read()[..., :3].copy()
    # ---- light routes (projected, culled by the globe)
    a_routes = smoothstep(64.4, 65.6, t) * (1 - smoothstep(77.5, 79.5, t))
    if a_routes > 0:
        L = Layer()
        c = L.canvas
        grow = ease_out(clamp((t - 64.4) / 2.5))
        for k, arc in enumerate(routes_world()):
            pts = rot_y(arc, rot)
            n = max(2, int(len(pts) * clamp(grow * 1.25 - (k % 7) * 0.04)))
            pts = pts[:n]
            scr, z, ok = gl3d.project(pts, view, proj)
            vis = (~earthgl.occluded(pts, eye)) & ok
            for i in range(len(pts) - 1):
                if vis[i] and vis[i + 1]:
                    p = skia.Paint(AntiAlias=True, StrokeWidth=1.6, Color=skia.Color4f(1.0, 0.78, 0.45, 0.55 * a_routes))
                    c.drawLine(scr[i, 0], scr[i, 1], scr[i + 1, 0], scr[i + 1, 1], p)
            # travelling pulses
            for j in range(2):
                f = ((t * 0.32 + k * 0.137 + j * 0.5) % 1.0)
                idx = int(f * (len(pts) - 1))
                if idx < len(pts) and vis[idx]:
                    gp = skia.Paint(AntiAlias=True, Color=skia.Color4f(1.0, 0.95, 0.8, 0.95 * a_routes))
                    gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 2.2))
                    c.drawCircle(scr[idx, 0], scr[idx, 1], 2.6, gp)
        lay = L.rgba()
        img += lay[..., :3] * 1.6
    # ---- satellites
    a_sats = smoothstep(74.8, 76.5, t)
    if a_sats > 0:
        S = satellites()
        ts = (t - 74.0) * 0.55
        p = orbit_pos(S['a'], S['inc'], S['raan'], S['ph'], ts, speed=0.9)
        hid = earthgl.occluded(p, eye)
        p = p[~hid]
        scr, z, ok = gl3d.project(p, view, proj)
        m = ok & (scr[:, 0] > -5) & (scr[:, 0] < W + 5) & (scr[:, 1] > -5) & (scr[:, 1] < H + 5)
        scr = scr[m]
        buf = np.zeros((H, W), np.float32)
        xi = np.clip(scr[:, 0].astype(int), 0, W - 1)
        yi = np.clip(scr[:, 1].astype(int), 0, H - 1)
        np.add.at(buf, (yi, xi), 1.0)
        buf = cv2.GaussianBlur(buf, (0, 0), 0.9) * 5.0
        img += buf[..., None] * np.array([0.75, 0.88, 1.0], np.float32) * a_sats
    # ---- navigation constellation (orbits + satellites) and the relativity beat
    a_nav = smoothstep(79.6, 81.2, t)
    if a_nav > 0:
        S = satellites()
        nav = S['nav']
        L = Layer()
        c = L.canvas
        for k, (a, inc, raan, ph) in enumerate(nav[:30:5]):
            ring = orbit_pos(np.full(120, a), inc, raan, np.linspace(0, 2 * math.pi, 120), 0.0)
            scr, z, ok = gl3d.project(ring, view, proj)
            hid = earthgl.occluded(ring, eye)
            for i in range(119):
                if ok[i] and ok[i + 1] and not hid[i]:
                    pa = skia.Paint(AntiAlias=True, StrokeWidth=1.1, Color=skia.Color4f(0.55, 0.8, 1.0, 0.28 * a_nav))
                    c.drawLine(scr[i, 0], scr[i, 1], scr[i + 1, 0], scr[i + 1, 1], pa)
        pn = orbit_pos(nav[:, 0], nav[:, 1], nav[:, 2], nav[:, 3], (t - 74.0) * 0.12, speed=1.0)
        scr, z, ok = gl3d.project(pn, view, proj)
        hid = earthgl.occluded(pn, eye)
        for i in range(len(pn)):
            if ok[i] and not hid[i]:
                gp = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.85, 0.95, 1.0, 0.95 * a_nav))
                gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 1.5))
                c.drawCircle(scr[i, 0], scr[i, 1], 3.2, gp)
        # one highlighted satellite sending timing signals to a point on the ground
        hi = 7
        sp = scr[hi]
        ground = rot_y(earthgl.latlon_to_xyz(39.9, 116.4)[None], rot)[0]
        gs, _, _ = gl3d.project(ground[None], view, proj)
        gs = gs[0]
        if ok[hi] and not hid[hi]:
            ring_t = (t * 0.9) % 1.0
            for j in range(3):
                f = (ring_t + j / 3) % 1.0
                x = lerp(sp[0], gs[0], f)
                y = lerp(sp[1], gs[1], f)
                pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6,
                                Color=skia.Color4f(1.0, 0.85, 0.55, 0.7 * a_nav * (1 - f)))
                c.drawCircle(x, y, 6 + 20 * f, pa)
            hp = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.0,
                            Color=skia.Color4f(1.0, 0.8, 0.45, a_nav))
            c.drawCircle(sp[0], sp[1], 12, hp)
            cards.draw_mixed(c, '+38 μs / 天', sp[0] + 22, sp[1] - 16, cards.fnt('sans', 'Medium', 26),
                             cards.fnt('num', 'SemiBold', 34), (1.0, 0.85, 0.55), a_nav * smoothstep(80.6, 81.4, t), shadow=0.7)
        # position error circle growing on the ground (when uncorrected)
        err = smoothstep(86.0, 90.5, t) * (1 - smoothstep(91.0, 92.0, t))
        if err > 0:
            ep = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.8,
                            Color=skia.Color4f(1.0, 0.45, 0.35, 0.9 * min(1.0, err * 3)))
            c.drawCircle(gs[0], gs[1], 4 + 70 * err, ep)
        gp = skia.Paint(AntiAlias=True, Color=skia.Color4f(1, 1, 1, a_nav))
        c.drawCircle(gs[0], gs[1], 3.5, gp)
        lay = L.rgba()
        img = img * (1 - lay[..., 3:4]) + lay[..., :3] * 1.3
    return img * smoothstep(62.0, 62.6, t) * (1 - smoothstep(95.4, 96.0, t))
