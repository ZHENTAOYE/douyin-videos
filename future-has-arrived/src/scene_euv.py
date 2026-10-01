"""02 制造 (38.0–62.0s): EUV light source.
Side view of a collector mirror, a stream of tin droplets, laser pulses and the plasma burst,
then a low glide over a perfectly smooth mirror surface (GL)."""
import math
import numpy as np, cv2, skia
import gfx, gl3d, cards
from gfx import Layer, smoothstep, clamp, ease_in_out, ease_out, ease_in, lerp, radial_glow
from config import W, H

VIOLET = np.array([0.62, 0.42, 1.0], np.float32)
EUV_CORE = np.array([1.0, 0.92, 1.0], np.float32)
LASER = np.array([1.0, 0.28, 0.12], np.float32)
F1 = np.array([1080.0, 540.0])      # plasma focus (screen, at zoom 1)
F2 = np.array([3400.0, 540.0])      # intermediate focus, far off-screen right

_rng = np.random.default_rng(21)
DUST = _rng.uniform([0, 0, 0.2], [W, H, 1.0], (160, 3))


def cam(t):
    """2D camera: zoom about F1 + offset."""
    if t < 44.0:
        z = lerp(0.82, 1.0, ease_in_out((t - 38.0) / 6.0))
        return z, np.array([60.0, 0.0])
    if t < 54.2:
        z = lerp(1.0, 3.2, ease_in_out(clamp((t - 44.0) / 1.6)))
        z += 0.25 * ease_out(clamp((t - 49.2) / 4.0))
        return z, np.array([0.0, 0.0])
    return 1.0, np.array([0.0, 0.0])


def S(p, z, off):
    """world (zoom-1 screen space) -> screen."""
    return (np.asarray(p, float) - F1) * z + F1 + off * z


def mirror_points(n=64):
    # collector: an arc of a circle centred near F1 (concave, facing the plasma)
    R = 640.0
    angs = np.linspace(math.radians(122), math.radians(238), n)
    return np.c_[F1[0] + R * np.cos(angs), F1[1] + R * np.sin(angs)]


def draw_mirror(c, z, off, glow):
    pts = mirror_points(80)
    inner = [S(p, z, off) for p in pts]
    outer = [S(F1 + (p - F1) * 1.06, z, off) for p in pts]
    path = skia.Path()
    path.moveTo(*inner[0])
    for p in inner[1:]:
        path.lineTo(*p)
    for p in outer[::-1]:
        path.lineTo(*p)
    path.close()
    pa = skia.Paint(AntiAlias=True)
    mid = S(F1 + np.array([-640, 0]), z, off)
    pa.setShader(skia.GradientShader.MakeRadial(skia.Point(*mid), 560 * z, [
        skia.Color4f(0.55 + 0.4 * glow, 0.42 + 0.3 * glow, 0.85, 1), skia.Color4f(0.12, 0.10, 0.18, 1)]))
    c.drawPath(path, pa)
    rim = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.0 * z,
                     Color=skia.Color4f(0.85, 0.78, 1.0, 0.55 + 0.4 * glow))
    p2 = skia.Path()
    p2.moveTo(*inner[0])
    for p in inner[1:]:
        p2.lineTo(*p)
    c.drawPath(p2, rim)


def draw_rays(c, z, off, a):
    if a <= 0.01:
        return
    pts = mirror_points(22)[1:-1]
    for i, p in enumerate(pts):
        f1 = S(F1, z, off)
        pp = S(p, z, off)
        f2 = S(F2, z, off)
        pa = skia.Paint(AntiAlias=True, StrokeWidth=1.4, Color=skia.Color4f(0.7, 0.55, 1.0, 0.22 * a))
        c.drawLine(f1[0], f1[1], pp[0], pp[1], pa)
        pb = skia.Paint(AntiAlias=True, StrokeWidth=1.4, Color=skia.Color4f(0.75, 0.6, 1.0, 0.30 * a))
        c.drawLine(pp[0], pp[1], f2[0], f2[1], pb)


def droplet_stream(c, t, z, off, a=1.0, skip_near_focus=False):
    """Fast stream of tin droplets (motion streaks)."""
    spacing = 46.0
    speed = 900.0
    phase = (t * speed) % spacing
    for k in range(-2, int(H / spacing) + 3):
        y = k * spacing + phase - 40
        if skip_near_focus and abs(y - F1[1]) < 30:
            continue
        p = S((F1[0], y), z, off)
        pa = skia.Paint(AntiAlias=True, Color=skia.Color4f(0.95, 0.92, 0.85, 0.85 * a))
        pa.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 0.8))
        r = 2.6 * z
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(p[0] - r, p[1] - r * 3.2, 2 * r, r * 6.4), r, r), pa)


def plasma(img, center, z, k, t, seed=0):
    """Additive plasma burst: k in 0..1 (intensity envelope)."""
    if k <= 0.003:
        return img
    cx, cy = center
    flick = 1 + 0.12 * math.sin(t * 70 + seed) + 0.08 * math.sin(t * 131)
    radial_glow(img, cx, cy, 6 * z, EUV_CORE, 7.0 * k * flick)
    radial_glow(img, cx, cy, 26 * z, VIOLET * 1.2, 1.4 * k * flick, falloff=2.2)
    radial_glow(img, cx, cy, 110 * z, VIOLET, 0.35 * k, falloff=1.7)
    return img


def sparks(c, center, z, age, n=220, seed=3):
    """Debris/sparks flying out of the burst. age in seconds since detonation (slow-mo time)."""
    if age <= 0 or age > 3.5:
        return
    rng = np.random.default_rng(seed)
    ang = rng.uniform(0, 2 * math.pi, n)
    spd = rng.gamma(2.0, 70, n)
    life = rng.uniform(1.0, 3.2, n)
    for i in range(n):
        if age > life[i]:
            continue
        d = spd[i] * (1 - math.exp(-age * 1.4)) * 1.6
        d0 = max(0.0, d - spd[i] * 0.12)
        x0, y0 = center[0] + math.cos(ang[i]) * d0 * z, center[1] + math.sin(ang[i]) * d0 * z
        x1, y1 = center[0] + math.cos(ang[i]) * d * z, center[1] + math.sin(ang[i]) * d * z
        f = (1 - age / life[i]) ** 1.5
        col = (1.0, 0.75 + 0.2 * f, 0.55 + 0.4 * f)
        pa = skia.Paint(AntiAlias=True, StrokeWidth=1.6 * z * f + 0.5, Color=skia.Color4f(*col, 0.9 * f),
                        StrokeCap=skia.Paint.kRound_Cap)
        c.drawLine(x0, y0, x1, y1, pa)


def laser_beam(img, start, end, width, color, k):
    if k <= 0.003:
        return img
    L = np.zeros((H, W), np.float32)
    cv2.line(L, tuple(int(v) for v in start), tuple(int(v) for v in end), 1.0, max(1, int(width)), cv2.LINE_AA)
    L = cv2.GaussianBlur(L, (0, 0), max(1.0, width * 0.8))
    img += L[..., None] * np.asarray(color, np.float32) * k
    return img


def render_source(t):
    z, off = cam(t)
    img = np.zeros((H, W, 3), np.float32)
    # chamber atmosphere
    radial_glow(img, *S(F1, z, off), 520 * z, (0.10, 0.07, 0.18), 0.6, falloff=1.4)
    slow = t >= 44.0
    # regular 50 kHz pulses, shown as rhythmic flashes in the wide shot
    pulse = 0.0
    if not slow:
        ph = ((t - 38.0) / 0.42) % 1.0
        pulse = math.exp(-ph * 9.0)
    # slow-motion single droplet timeline
    t_pre, t_main = 45.6, 48.3
    burst = 0.0
    if slow:
        if t >= t_main:
            age = t - t_main
            burst = clamp(age / 0.25) * (0.75 + 0.25 * math.exp(-age * 0.4)) * (1 - 0.35 * smoothstep(55.0, 60.0, t))
            if t >= 49.2:
                burst *= 1.0 + 0.6 * math.exp(-(t - 49.2) * 2.0)
    glow = max(pulse, burst * 0.9)
    L = Layer()
    c = L.canvas
    draw_mirror(c, z, off, glow)
    draw_rays(c, z, off, glow)
    if not slow:
        droplet_stream(c, t, z, off)
    else:
        # one big droplet (we are now deep in slow motion)
        if t < t_main:
            y = lerp(F1[1] - 160, F1[1], ease_out(clamp((t - 44.0) / (t_pre - 44.0)), 2))
            flat = smoothstep(t_pre, t_main, t)
            r = 12.0
            rx, ry = r * (1 + 3.2 * flat), r * (1 - 0.72 * flat)
            p = S((F1[0], y), z, off)
            pa = skia.Paint(AntiAlias=True)
            pa.setShader(skia.GradientShader.MakeRadial(skia.Point(p[0] - rx * z * 0.3, p[1] - ry * z * 0.4), max(rx, ry) * z * 1.3,
                                                        [skia.Color4f(1, 1, 0.97, 1), skia.Color4f(0.55, 0.53, 0.5, 1), skia.Color4f(0.18, 0.17, 0.17, 1)]))
            c.drawOval(skia.Rect.MakeXYWH(p[0] - rx * z, p[1] - ry * z, 2 * rx * z, 2 * ry * z), pa)
        sparks(c, S(F1, z, off), z * 0.5, (t - t_main) * 0.9)
    gfx.over(img, L.rgba())
    # lasers
    f1s = S(F1, z, off)
    if not slow:
        laser_beam(img, (W + 50, f1s[1]), f1s, 3, LASER, 0.5 * pulse)
    else:
        kp = math.exp(-max(0, t - t_pre) * 6) * (t >= t_pre)
        laser_beam(img, (W + 50, f1s[1] - 10), f1s, 4 * z * 0.5, LASER * 1.2, 1.4 * kp)
        km = math.exp(-max(0, t - t_main) * 3) * (t >= t_main)
        laser_beam(img, (W + 50, f1s[1]), f1s, 26 * z * 0.4, LASER * 1.4, 1.6 * km)
    plasma(img, f1s, z, max(pulse, burst), t)
    if slow and t >= t_main:
        # shockwave ring
        age = (t - t_main)
        r = 30 + 420 * (1 - math.exp(-age * 1.2))
        ring = np.zeros((H, W), np.float32)
        cv2.circle(ring, (int(f1s[0]), int(f1s[1])), int(r * z * 0.5), 1.0, 2, cv2.LINE_AA)
        ring = cv2.GaussianBlur(ring, (0, 0), 3)
        img += ring[..., None] * VIOLET * 0.8 * math.exp(-age * 0.9)
    # floating dust catching the light
    for (x, y, d) in DUST:
        px, py = (x - W / 2) * (0.9 + 0.3 * d) + W / 2, (y + t * 6 * d) % H
        dd = math.hypot(px - f1s[0], py - f1s[1])
        b = (0.25 + 1.5 * glow) * d / (1 + (dd / 260) ** 2)
        if b > 0.02:
            radial_glow(img, px, py, 1.2 + d, (0.8, 0.7, 1.0), b)
    # heat flash at the stat
    if t >= 49.2:
        img += np.float32(0.6) * math.exp(-(t - 49.2) * 5.0)
    a = smoothstep(38.0, 38.7, t)
    return img * a


# ------------------------------------------------------------------ the collector mirror (ray traced)
MIRROR_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform vec3 eye; uniform vec3 tgt; uniform float time; uniform float glow;
// concave spherical cap: sphere centre C, radius R, cap facing +z (towards the focus), aperture radius A
const float R = 1.6; const float A = 0.95; const float HOLE = 0.12;
const vec3 C = vec3(0.0, 0.0, 1.6);
vec3 F = vec3(0.0, 0.0, 0.8);            // focus (plasma) at R/2 in front of the vertex
float h21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
vec3 env(vec3 d){
  // clean room: a ceiling grid of light panels, soft walls, dark floor, two softboxes
  vec3 c = mix(vec3(0.010, 0.010, 0.016), vec3(0.05, 0.055, 0.075), smoothstep(-0.3, 0.3, d.y));
  if(d.y > 0.05){
    vec2 g = d.xz / d.y * 1.4 + vec2(0.0, 0.3);
    vec2 f = abs(fract(g) - 0.5);
    float panel = smoothstep(0.30, 0.27, max(f.x, f.y*0.8));
    c += vec3(0.95, 0.97, 1.0) * panel * 0.9 * smoothstep(0.05, 0.35, d.y);
  }
  c += vec3(1.0, 0.96, 0.92) * smoothstep(0.975, 0.99, dot(d, normalize(vec3(-0.7, 0.35, 0.6)))) * 2.0;
  c += vec3(0.85, 0.9, 1.0) * smoothstep(0.980, 0.993, dot(d, normalize(vec3(0.8, 0.25, 0.55)))) * 1.6;
  return c;
}
vec3 film(float x){ return 0.55 + 0.45*cos(6.2831*(vec3(0.0, 0.33, 0.67) + x)); }
float plasma_hit(vec3 ro, vec3 rd){
  vec3 oc = F - ro; float t = max(dot(oc, rd), 0.0); float d = length(oc - rd*t);
  return exp(-d*d/0.0008)*3.0 + exp(-d*d/0.02)*0.25;
}
void main(){
  vec2 q = (uv - 0.5) * vec2(res.x/res.y, 1.0);
  vec3 f = normalize(tgt - eye), r = normalize(cross(f, vec3(0,1,0))), u = cross(r, f);
  vec3 rd = normalize(f + q.x*r*0.80 + q.y*u*0.80);
  vec3 ro = eye;
  vec3 col = env(rd) + vec3(0.65, 0.45, 1.0) * plasma_hit(ro, rd) * glow;
  // ray-sphere (inside surface of the cap)
  vec3 oc = ro - C; float b = dot(oc, rd); float c = dot(oc, oc) - R*R; float h = b*b - c;
  if(h > 0.0){
    float sh = sqrt(h);
    for(int k=0;k<2;k++){
      float t = (k==0) ? (-b - sh) : (-b + sh);
      if(t <= 0.0) continue;
      vec3 p = ro + rd*t;
      float rad = length(p.xy);
      if(p.z > C.z || rad > A) continue;
      vec3 n = normalize(C - p);                 // concave side faces the focus
      if(rad < HOLE){ break; }
      vec3 rr = reflect(rd, n);
      float mu = abs(dot(rd, n));
      // multilayer coating: angle-dependent interference colour, slight radial variation
      vec3 tint = film(mu*0.9 + rad*0.35 + 0.1);
      vec3 refl = env(rr) + vec3(0.65, 0.45, 1.0) * plasma_hit(p, rr) * glow * 1.4;
      // the reflected plasma converges toward the second focus: a bright violet sheen across the dish
      float sheen = pow(max(dot(rr, normalize(F - p)), 0.0), 40.0);
      col = refl * mix(vec3(1.0), tint, 0.65) * 0.95 + tint * 0.035 + vec3(0.6, 0.4, 1.0) * sheen * 0.25 * glow;
      // fine polishing structure is invisible: keep it perfectly smooth; add subtle edge darkening
      col *= smoothstep(A, A - 0.03, rad) * 0.9 + 0.1;
      // rim: machined metal ring
      if(rad > A - 0.025) col = vec3(0.35, 0.34, 0.33) * (0.4 + 0.6*max(dot(n, normalize(vec3(-0.6,0.7,0.4))), 0.0));
      break;
    }
  }
  o = vec4(col, 1.0);
}
"""
_fs = {}


def render_mirror(t, t0):
    if 'm' not in _fs:
        _fs['m'] = gl3d.FullScreen('collector', MIRROR_FS)
    lt = t - t0
    ang = math.radians(-26 + 4.0 * lt)
    dist = 2.75 - 0.25 * ease_out(clamp(lt / 7.0))
    eye = (dist * math.sin(ang), 0.42 - 0.02 * lt, 0.15 + dist * math.cos(ang))
    tgt = (0.12, 0.02, 0.15)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    g = 0.8 + 0.2 * math.sin(lt * 9.0) ** 2
    _fs['m'].render(eye=eye, tgt=tgt, time=t, glow=g)
    img = tg.read()[..., :3].copy()
    # a flat surface-profile trace with a scale bar, drawn like a lab instrument readout
    L = Layer()
    c = L.canvas
    a = smoothstep(t0 + 0.8, t0 + 1.6, t) * (1 - smoothstep(61.0, 61.8, t))
    y0 = H * 0.22
    x0, x1 = W * 0.56, W * 0.93
    path = skia.Path()
    rng = np.random.default_rng(4)
    ys = np.convolve(rng.normal(0, 1, 260), np.ones(9) / 9, 'same') * 0.9
    for i, yy in enumerate(ys):
        x = lerp(x0, x1, i / (len(ys) - 1))
        (path.moveTo if i == 0 else path.lineTo)(x, y0 + yy)
    c.drawPath(path, skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=2.0,
                                Color=skia.Color4f(1.0, 0.9, 1.0, 0.85 * a)))
    tick = skia.Paint(AntiAlias=True, StrokeWidth=1.2, Color=skia.Color4f(1, 1, 1, 0.5 * a))
    c.drawLine(x0, y0 - 40, x0, y0 + 40, tick)
    c.drawLine(x1, y0 - 40, x1, y0 + 40, tick)
    cards.draw_mixed(c, '表面起伏（按“德国大小”等比放大）', x0, y0 - 58, cards.fnt('sans', 'Regular', 28), cards.fnt('num', 'Regular', 30),
                     (0.9, 0.9, 0.95), a * 0.85, shadow=0.6)
    cards.draw_mixed(c, '≤ 0.1 mm', x1, y0 + 78, cards.fnt('sans', 'Medium', 30), cards.fnt('num', 'SemiBold', 42),
                     (1.0, 0.8, 1.0), a, align='right', shadow=0.6)
    gfx.over(img, L.rgba())
    return img * smoothstep(t0, t0 + 0.6, t)


def render(t):
    if t < 54.2:
        img = render_source(t)
        k = smoothstep(53.6, 54.2, t)
        return img * (1 - k) + k * np.float32(1.0) * VIOLET * 0.8
    img = render_mirror(t, 54.2)
    flash = 1 - smoothstep(54.2, 54.7, t)
    img = img * (1 - flash) + flash * VIOLET * 0.8
    return img * (1 - smoothstep(61.5, 62.0, t))
