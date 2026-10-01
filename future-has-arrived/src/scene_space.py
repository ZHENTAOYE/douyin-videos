"""04 宇宙 (96.0–123.0s): Voyager 1 far from home · a deep field down to a galaxy from ~290 Myr after
the Big Bang · the Moon turning to show the Chang'e-6 landing site on the far side."""
import math, os
import numpy as np, cv2, skia
import gl3d, gfx, cards, meshes
from gfx import smoothstep, clamp, ease_in_out, ease_out, lerp, Layer, radial_glow
from config import W, H, BUILD, ASSETS

_V = {}


# ------------------------------------------------------------------ Voyager 1
def voyager_mesh():
    if 'mesh' in _V:
        return _V['mesh']
    WHITE = (0.62, 0.62, 0.6, 1)
    GOLD = (0.78, 0.58, 0.28, 1)
    GREY = (0.45, 0.45, 0.47, 1)
    DARK = (0.18, 0.18, 0.2, 1)
    parts = []
    # high-gain antenna: shallow paraboloid, opening toward +y
    prof = [(r, 0.15 * r * r) for r in np.linspace(0.0, 1.83, 18)]
    parts.append(meshes.revolve(prof, 72, WHITE))
    parts.append(meshes.cylinder((0, 0, 0), (0, 0.55, 0), 0.06, 12, GREY))          # feed
    # decagonal bus below the dish, wrapped in gold foil
    parts.append(meshes.prism((0, -0.35, 0), 0.9, 0.47, 10, GOLD))
    parts.append(meshes.prism((0, -0.75, 0), 0.35, 0.35, 10, DARK))
    # magnetometer boom (13 m) and science boom with instrument platform
    parts.append(meshes.cylinder((0.8, -0.35, 0), (13.5, -0.6, 0.3), 0.025, 6, GREY, caps=False))
    parts.append(meshes.cylinder((-0.8, -0.35, 0.2), (-3.1, -0.5, 0.6), 0.05, 8, GREY))
    parts.append(meshes.box((-3.3, -0.5, 0.6), (0.6, 0.45, 0.5), DARK))
    parts.append(meshes.cylinder((-3.3, -0.25, 0.6), (-3.3, 0.15, 0.9), 0.12, 12, GREY))
    # RTG boom with three generators
    parts.append(meshes.cylinder((0.3, -0.4, -0.8), (0.9, -0.6, -3.4), 0.04, 8, GREY))
    for k in range(3):
        a = np.array([0.3, -0.4, -0.8]) + (np.array([0.6, -0.2, -2.6]) * (0.45 + 0.2 * k))
        parts.append(meshes.cylinder(a - [0, 0, 0.22], a + [0, 0, 0.22], 0.22, 16, DARK))
        for f in range(6):
            ang = f * math.pi / 3
            d = np.array([math.cos(ang), math.sin(ang), 0]) * 0.3
            parts.append(meshes.box(a + d, (0.04 + 0.14 * abs(math.cos(ang)), 0.04 + 0.14 * abs(math.sin(ang)), 0.42), DARK))
    P, N, C = meshes.merge(*parts)
    _V['mesh'] = gl3d.Mesh(P, N, C)
    return _V['mesh']


def render_voyager(t):
    t0 = 96.0
    lt = t - t0
    mesh = voyager_mesh()
    sun_world = np.array([-260.0, 40.0, -120.0])
    key = -sun_world / np.linalg.norm(sun_world)
    tg = gl3d.target()
    tg.begin((0, 0, 0, 1))
    # model: dish faces the Sun/Earth; rotate so +y points toward the sun
    sd = sun_world / np.linalg.norm(sun_world)
    y = np.array([0, 1.0, 0])
    axis = np.cross(y, sd)
    s = np.linalg.norm(axis)
    ca = y @ sd
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]]) / max(s, 1e-9)
    R = np.eye(3) + K * s + K @ K * (1 - ca)
    model = np.eye(4, dtype=np.float32)
    model[:3, :3] = R
    # camera: three-quarter view from the sunward side so the dish catches the light
    centre = R @ np.array([2.5, -0.3, 0.0])
    side = np.cross(sd, np.array([0, 1.0, 0]))
    side /= np.linalg.norm(side)
    ang = math.radians(-20 + 3.0 * lt)
    dirv = sd * math.cos(ang) * 0.55 + side * math.sin(ang + 1.2) * 0.9 + np.array([0, 0.28, 0])
    dirv /= np.linalg.norm(dirv)
    eye = centre + dirv * (21.0 - 0.25 * lt)
    tgt = centre + np.array([-2.0, -2.2, 0.0])
    view = gl3d.look_at(eye, tgt)
    proj = gl3d.perspective(34, W / H, 0.1, 800)
    mesh.render(model=model, view=view, proj=proj, eye=tuple(eye), key_dir=tuple(key), key_col=(1.25, 1.15, 1.0),
                amb_col=(0.03, 0.035, 0.05), shininess=40.0, spec_k=0.7, rim_col=(0.16, 0.2, 0.32), emit=0.0)
    img = tg.read()[..., :3].copy()
    # stars + the Sun
    if 'stars' not in _V:
        rng = np.random.default_rng(31)
        n = 1400
        _V['stars'] = (rng.uniform(0, W, n), rng.uniform(0, H, n), rng.pareto(2.2, n) * 0.08 + 0.02,
                       rng.choice([0, 1, 2], n, p=[0.6, 0.25, 0.15]))
    sx, sy, sb, sc = _V['stars']
    buf = np.zeros((H, W, 3), np.float32)
    cols = np.array([[0.75, 0.82, 1.0], [1.0, 0.92, 0.8], [1.0, 0.8, 0.6]], np.float32)
    off = lt * 4.0
    xi = ((sx - off) % W).astype(int)
    yi = sy.astype(int)
    np.add.at(buf, (yi, xi), cols[sc] * np.minimum(sb, 3)[:, None])
    buf = cv2.GaussianBlur(buf, (0, 0), 0.7) * 3
    img = np.where(img.sum(-1, keepdims=True) > 0.002, img, img + buf)
    sscr, _, ok = gl3d.project(sun_world[None], view, proj)
    if ok[0]:
        sx0, sy0 = sscr[0]
        radial_glow(img, sx0, sy0, 3.0, (1.0, 0.97, 0.9), 6.0)
        radial_glow(img, sx0, sy0, 26, (1.0, 0.85, 0.6), 0.45, falloff=1.8)
        L = Layer()
        c = L.canvas
        a = smoothstep(t0 + 1.0, t0 + 2.0, t)
        cards.draw_mixed(c, '太阳 · 地球', sx0, sy0 + 46, cards.fnt('sans', 'Regular', 24), cards.fnt('num', 'Regular', 26),
                         (0.9, 0.9, 0.9), a * 0.75, align='center', shadow=0.6)
        # signal pulse from the dish toward home
        dish, _, okd = gl3d.project(np.array([[0.0, 0.0, 0.0]]), view, proj)
        if okd[0]:
            d0 = dish[0]
            p = skia.Paint(AntiAlias=True, StrokeWidth=1.2, Color=skia.Color4f(0.7, 0.85, 1.0, 0.25 * a))
            p.setPathEffect(skia.DashPathEffect.Make([6, 10], 0))
            c.drawLine(d0[0], d0[1], sx0, sy0, p)
            sig = smoothstep(t0 + 5.3, t0 + 9.6, t)
            if 0 < sig < 1:
                x = lerp(d0[0], sx0, sig)
                yv = lerp(d0[1], sy0, sig)
                gp = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.75, 0.9, 1.0, 0.95))
                gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
                c.drawCircle(x, yv, 5, gp)
                hrs = 23.6 * sig
                cards.draw_mixed(c, f'{int(hrs):02d} 小时 {int((hrs % 1) * 60):02d} 分', x, yv - 22, cards.fnt('sans', 'Medium', 24),
                                 cards.fnt('num', 'SemiBold', 30), (0.8, 0.92, 1.0), 0.9, align='center', shadow=0.7)
        gfx.over(img, L.rgba())
    # signal-time bar: Voyager 1 -> Earth, ~23.6 h one way
    a = smoothstep(101.3, 101.9, t) * (1 - smoothstep(105.2, 105.7, t))
    if a > 0:
        L = Layer()
        c = L.canvas
        x0, x1, yb = W * 0.56, W * 0.92, H * 0.86
        p = skia.Paint(AntiAlias=True, StrokeWidth=1.4, Color=skia.Color4f(1, 1, 1, 0.35 * a))
        c.drawLine(x0, yb, x1, yb, p)
        prog = smoothstep(101.6, 105.2, t)
        p2 = skia.Paint(AntiAlias=True, StrokeWidth=2.4, Color=skia.Color4f(0.75, 0.9, 1.0, 0.9 * a))
        c.drawLine(x0, yb, lerp(x0, x1, prog), yb, p2)
        gp = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.85, 0.95, 1.0, a))
        gp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 3))
        c.drawCircle(lerp(x0, x1, prog), yb, 5, gp)
        f, fl = cards.fnt('sans', 'Regular', 24), cards.fnt('num', 'Regular', 28)
        cards.draw_mixed(c, '旅行者 1 号', x0, yb + 40, f, fl, (0.9, 0.9, 0.9), a * 0.8, shadow=0.6)
        cards.draw_mixed(c, '地球', x1, yb + 40, f, fl, (0.9, 0.9, 0.9), a * 0.8, align='right', shadow=0.6)
        hrs = 23.6 * prog
        cards.draw_mixed(c, f'信号已飞行 {int(hrs):02d} 小时 {int((hrs % 1) * 60):02d} 分', x0, yb - 22,
                         cards.fnt('sans', 'Medium', 28), cards.fnt('num', 'SemiBold', 36), (0.8, 0.92, 1.0), a, shadow=0.7)
        gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.5, t) * (1 - smoothstep(105.6, 106.0, t))


# ------------------------------------------------------------------ deep field
DF_W, DF_H = 5760, 3240
TARGET = (3410.0, 1890.0)      # the distant galaxy we zoom to (deep-field pixel coords)


def deep_field():
    path = f'{BUILD}/cache/deepfield.npy'
    if os.path.exists(path):
        return np.load(path, mmap_mode='r')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = np.random.default_rng(77)
    img = np.zeros((DF_H, DF_W, 3), np.float32)

    def blob_layer(n, rmin, rmax, colfn, sig_scale, bright):
        L = np.zeros_like(img)
        for _ in range(n):
            x, y = rng.uniform(0, DF_W), rng.uniform(0, DF_H)
            r = rng.uniform(rmin, rmax)
            e = rng.uniform(0.3, 1.0)
            ang = rng.uniform(0, 180)
            col = colfn() * bright * rng.lognormal(0, 0.5)
            cv2.ellipse(L, (int(x), int(y)), (max(1, int(r)), max(1, int(r * e))), ang, 0, 360, tuple(float(v) for v in col), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(L, (0, 0), sig_scale)

    def red():
        return np.array([1.0, rng.uniform(0.35, 0.6), rng.uniform(0.15, 0.3)], np.float32)

    def warm():
        return np.array([1.0, rng.uniform(0.75, 0.9), rng.uniform(0.5, 0.7)], np.float32)

    def blue():
        return np.array([rng.uniform(0.55, 0.8), rng.uniform(0.75, 0.9), 1.0], np.float32)

    def mixc():
        k = rng.random()
        return red() if k < 0.45 else (warm() if k < 0.75 else blue())
    img += blob_layer(9000, 1, 3, mixc, 1.2, 0.35)
    img += blob_layer(2500, 3, 8, mixc, 2.5, 0.30)
    img += blob_layer(500, 8, 20, warm, 5.0, 0.30)
    img += blob_layer(160, 18, 46, warm, 9.0, 0.30)
    # spirals
    for _ in range(70):
        x, y = rng.uniform(200, DF_W - 200), rng.uniform(200, DF_H - 200)
        R = rng.uniform(18, 70)
        inc = rng.uniform(0.25, 1.0)
        rot = rng.uniform(0, math.pi)
        S = int(R * 2.4)
        yy, xx = np.mgrid[-S:S, -S:S].astype(np.float32)
        xr = xx * math.cos(rot) + yy * math.sin(rot)
        yr = (-xx * math.sin(rot) + yy * math.cos(rot)) / inc
        r = np.sqrt(xr ** 2 + yr ** 2) / R
        th = np.arctan2(yr, xr)
        arms = 0.5 + 0.5 * np.cos(2 * (th - 2.6 * np.log(r + 0.05)))
        disk = np.exp(-r * 2.6) * (0.35 + 0.9 * arms ** 3)
        bulge = np.exp(-(r / 0.16) ** 2)
        c = disk[..., None] * blue() * 0.9 + bulge[..., None] * np.array([1.0, 0.85, 0.6]) * 1.6
        c = cv2.GaussianBlur(c.astype(np.float32), (0, 0), 1.0) * rng.uniform(0.4, 1.0)
        x0, y0 = int(x) - S, int(y) - S
        img[max(0, y0):y0 + 2 * S, max(0, x0):x0 + 2 * S] += c[max(0, -y0):, max(0, -x0):][:min(2 * S, DF_H - y0), :min(2 * S, DF_W - x0)]
    # gravitational-lensing arcs around a cluster
    cx, cy = DF_W * 0.38, DF_H * 0.42
    arcs = np.zeros_like(img)
    for _ in range(14):
        r = rng.uniform(160, 420)
        a0 = rng.uniform(0, 360)
        cv2.ellipse(arcs, (int(cx), int(cy)), (int(r), int(r * 0.92)), 0, a0, a0 + rng.uniform(10, 26), tuple(float(v) for v in blue() * 0.5), 3, cv2.LINE_AA)
    img += cv2.GaussianBlur(arcs, (0, 0), 2.0)
    img += blob_layer(40, 20, 34, warm, 8.0, 0.45) * 0     # placeholder keeps rng order stable
    # stars with JWST-style diffraction spikes (6 long + 2 short)
    for _ in range(36):
        x, y = rng.uniform(0, DF_W), rng.uniform(0, DF_H)
        b = rng.lognormal(0.0, 0.8)
        col = warm() if rng.random() < 0.6 else blue()
        L = np.zeros((DF_H, DF_W), np.float32)
        Ls = int(60 + 180 * min(b, 3))
        for ang in (90, 30, 150):
            dx, dy = math.cos(math.radians(ang)) * Ls, math.sin(math.radians(ang)) * Ls
            cv2.line(L, (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)), 1.0, 1, cv2.LINE_AA)
        cv2.line(L, (int(x - Ls * 0.45), int(y)), (int(x + Ls * 0.45), int(y)), 0.5, 1, cv2.LINE_AA)
        x0, x1 = max(0, int(x) - Ls - 4), min(DF_W, int(x) + Ls + 4)
        y0, y1 = max(0, int(y) - Ls - 4), min(DF_H, int(y) + Ls + 4)
        sub = L[y0:y1, x0:x1]
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
        sub = cv2.GaussianBlur(sub, (0, 0), 0.9) * np.exp(-d / (Ls * 0.35)) * 1.8
        core = np.exp(-(d / 2.5) ** 2) * 6 + 0.6 / (1 + (d / 6) ** 2)
        img[y0:y1, x0:x1] += (sub + core)[..., None] * col * b * 0.6
    # the target: a faint, very red, compact galaxy
    tx, ty = TARGET
    yy, xx = np.mgrid[int(ty) - 40:int(ty) + 40, int(tx) - 40:int(tx) + 40].astype(np.float32)
    d = np.sqrt(((xx - tx) / 1.0) ** 2 + ((yy - ty) / 0.75) ** 2)
    img[int(ty) - 40:int(ty) + 40, int(tx) - 40:int(tx) + 40] += np.exp(-(d / 4.5) ** 2)[..., None] * np.array([1.0, 0.32, 0.12]) * 0.9
    img += rng.normal(0, 0.006, img.shape).astype(np.float32)
    img = np.clip(img, 0, 50).astype(np.float32)
    np.save(path, img)
    return np.load(path, mmap_mode='r')


def render_deepfield(t):
    t0 = 106.0
    df = deep_field()
    # zoom from the full field (fits screen) toward the target galaxy
    fit = W / DF_W
    u = ease_in_out(clamp((t - 107.4) / 5.4))
    z = fit * math.exp(lerp(math.log(1.0), math.log(10.0), u)) * (1.0 + 0.03 * (t - t0))
    cx = lerp(DF_W / 2, TARGET[0], u ** 0.7)
    cy = lerp(DF_H / 2, TARGET[1], u ** 0.7)
    M = np.array([[z, 0, W / 2 - cx * z], [0, z, H / 2 - cy * z]], np.float32)
    # crop first so the warp touches only what is visible
    hw, hh = W / 2 / z + 4, H / 2 / z + 4
    x0, x1 = int(max(0, cx - hw)), int(min(DF_W, cx + hw))
    y0, y1 = int(max(0, cy - hh)), int(min(DF_H, cy + hh))
    crop = np.asarray(df[y0:y1, x0:x1], np.float32)
    M2 = M.copy()
    M2[0, 2] += x0 * z
    M2[1, 2] += y0 * z
    interp = cv2.INTER_AREA if z < 1 else cv2.INTER_CUBIC
    img = cv2.warpAffine(crop, M2, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT)
    img = np.maximum(img, 0) * 1.1
    # label the target
    a = smoothstep(110.2, 111.0, t) * (1 - smoothstep(115.6, 116.4, t))
    if a > 0:
        L = Layer()
        c = L.canvas
        px, py = W / 2 + (TARGET[0] - cx) * z, H / 2 + (TARGET[1] - cy) * z
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Color=skia.Color4f(1, 1, 1, 0.8 * a))
        r = 70
        for k in range(4):
            a0 = 90 * k + 15
            c.drawArc(skia.Rect.MakeXYWH(px - r, py - r, 2 * r, 2 * r), a0, 60, False, p)
        cards.draw_mixed(c, 'JADES-GS-z14-0', px + r + 22, py - 8, cards.fnt('sans', 'Regular', 26), cards.fnt('num', 'SemiBold', 34),
                         (1, 1, 1), a, shadow=0.7)
        cards.draw_mixed(c, '宇宙诞生后约 2.9 亿年', px + r + 22, py + 30, cards.fnt('sans', 'Regular', 26), cards.fnt('num', 'Medium', 30),
                         cards.ACCENT, a, shadow=0.7)
        gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.6, t) * (1 - smoothstep(116.0, 116.5, t))


# ------------------------------------------------------------------ Moon (far side, Chang'e-6)
MOON_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform mat4 inv_vp; uniform vec3 eye; uniform vec3 sun; uniform float rot; uniform sampler2D tmoon;
uniform vec2 site; uniform float site_a;
vec3 rotY(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(c*v.x + s*v.z, v.y, -s*v.x + c*v.z); }
void main(){
  vec4 pp = inv_vp * vec4(uv*2.0-1.0, 1.0, 1.0);
  vec3 d = normalize(pp.xyz/pp.w - eye);
  float b = dot(eye, d), c = dot(eye, eye) - 1.0, h = b*b - c;
  vec3 col = vec3(0.0);
  if(h > 0.0){
    float t = -b - sqrt(h);
    vec3 n = normalize(eye + d*t);
    vec3 q = rotY(n, -rot);
    float lon = atan(q.x, q.z), lat = asin(clamp(q.y,-1.0,1.0));
    vec2 st = vec2(lon/6.2831853 + 0.5, 0.5 + lat/3.1415926);
    vec3 alb = texture(tmoon, st).rgb;
    float ndl = max(dot(n, normalize(sun)), 0.0);
    float lit = pow(ndl, 0.85);
    col = alb*alb*1.5 * lit * vec3(1.0, 0.98, 0.95) + alb*0.012;
    // landing-site marker (great-circle distance on the sphere)
    float dlon = lon - site.x; float clat = cos(lat)*cos(site.y);
    float cosd = sin(lat)*sin(site.y) + clat*cos(dlon);
    float dist = acos(clamp(cosd, -1.0, 1.0));
    float ring = exp(-pow((dist - 0.075)/0.006, 2.0)) + exp(-pow(dist/0.012, 2.0))*1.5;
    col += vec3(1.0, 0.72, 0.35) * ring * site_a * 1.6;
  }
  o = vec4(col, 1.0);
}
"""


def render_moon(t):
    t0 = 116.5
    if 'moonfs' not in _V:
        im = cv2.cvtColor(cv2.imread(f'{ASSETS}/moon_1024.jpg'), cv2.COLOR_BGR2RGB)
        _V['moontex'] = gl3d.texture_from_array(im)
        _V['moonfs'] = gl3d.FullScreen('moon', MOON_FS)
    lt = t - t0
    # rotate so the far-side site (154°W) comes round to face the camera
    rot = math.radians(lerp(-80, 154 - 2, ease_out(clamp(lt / 5.5), 2)))
    eye = np.array([0.35, -1.25, 2.95])
    view = gl3d.look_at(eye, np.array([0.25, -0.12, 0.0]))
    proj = gl3d.perspective(40, W / H, 0.01, 50)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    inv = np.linalg.inv(proj @ view).astype(np.float32)
    sun = (0.75, 0.25, 0.55)
    _V['moonfs'].render(textures={'tmoon': _V['moontex']}, inv_vp=inv, eye=tuple(eye), sun=sun, rot=rot,
                        site=(math.radians(-153.98), math.radians(-41.63)), site_a=smoothstep(t0 + 2.5, t0 + 3.5, t))
    img = tg.read()[..., :3].copy()
    a = smoothstep(t0 + 3.0, t0 + 4.0, t) * (1 - smoothstep(122.4, 122.9, t))
    if a > 0:
        # project the site to place its label
        lat, lon = math.radians(-41.63), math.radians(-153.98)
        q = np.array([math.cos(lat) * math.sin(lon), math.sin(lat), math.cos(lat) * math.cos(lon)])
        c_, s_ = math.cos(rot), math.sin(rot)
        p = np.array([c_ * q[0] + s_ * q[2], q[1], -s_ * q[0] + c_ * q[2]])
        scr, _, ok = gl3d.project(p[None], view, proj)
        if ok[0] and p @ (eye - p) > 0:
            L = Layer()
            c = L.canvas
            x, y = scr[0]
            pa = skia.Paint(AntiAlias=True, StrokeWidth=1.4, Color=skia.Color4f(1, 0.85, 0.6, 0.8 * a))
            c.drawLine(x + 30, y - 20, x + 140, y - 90, pa)
            c.drawLine(x + 140, y - 90, x + 330, y - 90, pa)
            cards.draw_mixed(c, '嫦娥六号着陆区', x + 150, y - 104, cards.fnt('sans', 'Medium', 28), cards.fnt('num', 'Medium', 30),
                             (1, 1, 1), a, shadow=0.7)
            cards.draw_mixed(c, '月球背面 · 南极-艾特肯盆地', x + 150, y - 62, cards.fnt('sans', 'Regular', 22), cards.fnt('num', 'Regular', 24),
                             cards.ACCENT, a * 0.9, shadow=0.7)
            gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.5, t) * (1 - smoothstep(122.6, 123.0, t))
