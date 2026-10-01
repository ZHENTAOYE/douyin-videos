"""05 极限 (123.0–155.0s): the LHC (ring · cryomagnet tunnel · collision), the EAST tokamak plasma,
an optical-lattice clock and merging black holes for gravitational waves."""
import math
import numpy as np, cv2, skia
import gl3d, gfx, cards
from gfx import smoothstep, clamp, ease_in_out, ease_out, ease_in, lerp, Layer, radial_glow
from config import W, H

_X = {}

# ------------------------------------------------------------------ LHC ring from above (GL)
GROUND_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform mat4 inv_vp; uniform vec3 eye; uniform float ring_r; uniform float time;
float h21(vec2 p){ p = fract(p*vec2(233.34, 851.73)); p += dot(p, p+23.45); return fract(p.x*p.y); }
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(h21(i),h21(i+vec2(1,0)),f.x), mix(h21(i+vec2(0,1)),h21(i+vec2(1,1)),f.x), f.y); }
void main(){
  vec4 pp = inv_vp * vec4(uv*2.0-1.0, 1.0, 1.0);
  vec3 d = normalize(pp.xyz/pp.w - eye);
  vec3 col = vec3(0.0);
  if(d.y < 0.0){
    float t = -eye.y/d.y;
    vec2 p = (eye + d*t).xz;
    float n = vn(p*0.0012)*0.6 + vn(p*0.006)*0.3 + vn(p*0.03)*0.1;
    col = vec3(0.018, 0.022, 0.032) * (0.5 + 1.0*n);
    // villages: clusters of warm lights
    vec2 g = floor(p/180.0);
    float h = h21(g);
    if(h > 0.62){
      vec2 c = (g + 0.5 + 0.3*(vec2(h21(g+1.7), h21(g+3.1))-0.5))*180.0;
      float dd = length(p - c);
      for(int k=0;k<6;k++){
        vec2 q = c + (vec2(h21(g+float(k)*2.1), h21(g+float(k)*5.3))-0.5)*240.0;
        float e = length(p - q);
        col += vec3(1.0,0.72,0.38) * exp(-e*e/(60.0)) * 1.3;
      }
      col += vec3(0.6,0.4,0.2) * exp(-dd/220.0) * 0.03;
    }
    col *= exp(-t*0.00006);
  } else {
    col = mix(vec3(0.02,0.025,0.05), vec3(0.003,0.004,0.012), smoothstep(0.0, 0.3, d.y));
  }
  o = vec4(col, 1.0);
}
"""


def render_ring(t, t0=123.0):
    if 'gfs' not in _X:
        _X['gfs'] = gl3d.FullScreen('lhc_ground', GROUND_FS)
        _X['lines'] = gl3d.Lines(20000)
    lt = t - t0
    R = 4300.0
    u = ease_in_out(clamp(lt / 5.2))
    eye = np.array([lerp(-900, -300, u), lerp(6200, 2300, u), lerp(8200, 6900, u)])
    tgt = np.array([lerp(0, 500, u), 0.0, lerp(400, 2900, u)])
    view = gl3d.look_at(eye, tgt)
    proj = gl3d.perspective(42, W / H, 10, 60000)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    inv = np.linalg.inv(proj @ view).astype(np.float32)
    _X['gfs'].render(inv_vp=inv, eye=tuple(eye), ring_r=R, time=t)
    th = np.linspace(0, 2 * math.pi, 721)
    pts = np.c_[R * np.cos(th), np.full_like(th, 2.0), R * np.sin(th)]
    seg = np.stack([pts[:-1], pts[1:]], 1)
    col = np.tile([[0.55, 0.75, 1.0, 0.30]], (len(seg), 2, 1))
    _X['lines'].render(seg, col, width=9.0, depth_test=False, view=view, proj=proj)
    col = np.tile([[0.75, 0.88, 1.0, 0.9]], (len(seg), 2, 1))
    _X['lines'].render(seg, col, width=2.4, depth_test=False, view=view, proj=proj)
    # two counter-rotating proton beams: bright travelling arcs
    for direction, c in ((1, (1.0, 0.75, 0.45)), (-1, (0.55, 0.85, 1.0))):
        head = (direction * lt * 1.6) % (2 * math.pi)
        a = np.linspace(head - direction * 1.4, head, 120)
        p = np.c_[R * np.cos(a), np.full_like(a, 3.0), R * np.sin(a)]
        sg = np.stack([p[:-1], p[1:]], 1)
        fade = np.linspace(0, 1, len(sg)) ** 2
        cc = np.zeros((len(sg), 2, 4), np.float32)
        cc[..., :3] = c
        cc[:, 0, 3] = fade * 2.4
        cc[:, 1, 3] = fade * 2.4
        _X['lines'].render(sg, cc, width=7.0, depth_test=False, view=view, proj=proj)
    img = tg.read()[..., :3].copy()
    # labels on the ring: two big detectors as small markers
    L = Layer()
    c = L.canvas
    a = smoothstep(t0 + 1.2, t0 + 2.2, t)
    for ang, name in ((math.radians(90), 'ATLAS'), (math.radians(-90), 'CMS')):
        p = np.array([[R * math.cos(ang), 0, R * math.sin(ang)]])
        s, _, ok = gl3d.project(p, view, proj)
        if ok[0]:
            pa = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Color=skia.Color4f(1, 1, 1, 0.8 * a))
            c.drawCircle(s[0, 0], s[0, 1], 9, pa)
            cards.draw_mixed(c, name, s[0, 0] + 16, s[0, 1] - 12, cards.fnt('sans', 'Regular', 24), cards.fnt('num', 'Medium', 28),
                             (0.95, 0.95, 0.95), a * 0.85, shadow=0.6)
    gfx.over(img, L.rgba())
    return img


# ------------------------------------------------------------------ LHC tunnel (raymarched)
TUNNEL_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform vec3 eye; uniform vec3 fwd; uniform float frost; uniform float beam; uniform float time; uniform float speed;
const float RB = 400.0;
const float PER = 15.6;
vec3 loc(vec3 p){ float r = length(p.xz); float th = atan(p.z, p.x); return vec3(r - RB, p.y, th*RB); }
float sdTunnel(vec3 q){ return 1.95 - length(q.xy); }
float sdFloor(vec3 q){ return q.y + 1.25; }
float sdMag(vec3 q){
  float s = mod(q.z, PER) - PER*0.5;
  float d = length(q.xy - vec2(0.62, -0.62)) - 0.45;
  return max(d, abs(s) - 7.45);
}
float sdTray(vec3 q){ vec2 b = abs(q.xy - vec2(-1.35, 0.55)) - vec2(0.12, 0.30); return length(max(b,0.0)) + min(max(b.x,b.y),0.0); }
float map(vec3 p, out int id){
  vec3 q = loc(p);
  float d = sdTunnel(q); id = 0;
  float f = sdFloor(q); if(f < d){ d = f; id = 1; }
  float m = sdMag(q); if(m < d){ d = m; id = 2; }
  float tr = sdTray(q); if(tr < d){ d = tr; id = 3; }
  return d;
}
vec3 nrm(vec3 p){ int i; vec2 e = vec2(0.002, 0.0);
  return normalize(vec3(map(p+e.xyy,i)-map(p-e.xyy,i), map(p+e.yxy,i)-map(p-e.yxy,i), map(p+e.yyx,i)-map(p-e.yyx,i))); }
float h21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
void main(){
  vec2 qv = (uv - 0.5) * vec2(res.x/res.y, 1.0);
  vec3 f = normalize(fwd), r = normalize(cross(f, vec3(0,1,0))), u = cross(r, f);
  vec3 d = normalize(f + qv.x*r*1.05 + qv.y*u*1.05);
  float t = 0.05; int id = -1; vec3 p;
  for(int i=0;i<110;i++){
    p = eye + d*t;
    float h = map(p, id);
    if(h < 0.002) break;
    t += h*0.9;
    if(t > 140.0){ id = -1; break; }
  }
  vec3 col = vec3(0.0);
  if(id >= 0){
    vec3 n = nrm(p);
    vec3 q = loc(p);
    vec3 alb = vec3(0.30, 0.30, 0.30);
    if(id == 1) alb = vec3(0.42, 0.42, 0.40) * (0.85 + 0.15*h21(floor(q.zx*2.0)));
    if(id == 2){
      alb = vec3(0.10, 0.32, 0.85);
      float seam = smoothstep(7.2, 7.45, abs(mod(q.z, PER) - PER*0.5));
      alb = mix(alb, vec3(0.75), seam);
      // frost: speckled white crystals on the cold magnets
      float fr = h21(floor(q.zy*vec2(160.0, 220.0)) + floor(q.x*120.0));
      alb = mix(alb, vec3(0.80, 0.90, 1.0), frost * (0.18 + 0.45*step(0.72, fr)));
    }
    if(id == 3) alb = vec3(0.35, 0.33, 0.30);
    // ceiling lamps every 8 m along the tunnel
    vec3 lit = vec3(0.0);
    float zc = floor(q.z/8.0)*8.0;
    for(int k=-1;k<=2;k++){
      float zl = zc + float(k)*8.0 + 4.0;
      float th = zl/RB;
      vec3 lp = vec3(cos(th)*(RB-0.15), 1.70, sin(th)*(RB-0.15));
      vec3 L = lp - p; float dl = length(L); L /= dl;
      float ndl = max(dot(n, L), 0.0);
      vec3 h = normalize(L - d);
      float spec = pow(max(dot(n,h),0.0), id==2 ? 60.0 : 12.0) * (id==2 ? 0.9 : 0.1);
      lit += vec3(0.95, 0.97, 1.0) * (alb*ndl + spec) * 3.2 / (1.0 + dl*dl*0.45);
    }
    col = lit + alb*0.015;
    // lamp fixtures themselves
    float zz = mod(q.z, 8.0) - 4.0;
    float lamp = exp(-pow(zz/0.6, 2.0)) * exp(-pow((q.x+0.15)/0.10, 2.0)) * step(1.6, q.y);
    col += vec3(1.0, 0.95, 0.85) * lamp * 6.0;
  }
  // haze
  col = mix(col, vec3(0.05, 0.06, 0.08), 1.0 - exp(-t*0.012));
  // the beam: a glowing line along the magnet's beam pipe
  if(beam > 0.0){
    // closest approach of the ray to the beam line (approximated locally as straight along the tunnel)
    vec3 qe = loc(eye);
    float best = 1e9;
    for(int i=0;i<48;i++){
      float tt = 0.3 + float(i)*float(i)*0.06;
      vec3 qq = loc(eye + d*tt);
      float dd = length(qq.xy - vec2(0.62, -0.62));
      best = min(best, dd / max(tt*0.004 + 0.002, 0.002));
    }
    col += vec3(0.75, 0.88, 1.0) * beam * exp(-best*0.9) * 2.2;
  }
  o = vec4(col, 1.0);
}
"""


def render_tunnel(t, t0=127.6):
    if 'tfs' not in _X:
        _X['tfs'] = gl3d.FullScreen('lhc_tunnel', TUNNEL_FS)
    lt = t - t0
    RB = 400.0
    # distance travelled along the tunnel (accelerating for the speed beat)
    s = 6.0 * lt + 60.0 * max(0.0, lt - 4.4) ** 2
    th = s / RB
    eye = np.array([math.cos(th) * (RB - 0.75), 0.45, math.sin(th) * (RB - 0.75)])
    th2 = (s + 5.0) / RB
    ahead = np.array([math.cos(th2) * (RB - 0.2), 0.05, math.sin(th2) * (RB - 0.2)])
    fwd = ahead - eye
    frost = smoothstep(t0 + 0.8, t0 + 2.6, t) * (1 - smoothstep(t0 + 4.4, t0 + 5.0, t))
    beam = smoothstep(t0 + 4.3, t0 + 5.0, t)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    _X['tfs'].render(eye=tuple(eye), fwd=tuple(fwd), frost=frost, beam=beam, time=t, speed=1.0)
    img = tg.read()[..., :3].copy()
    if lt > 4.4:
        from scene_chip import zoom_blur
        img = zoom_blur(img, min(0.35, (lt - 4.4) * 0.25), W / 2, H / 2 + 40)
    # cold mist drifting
    if frost > 0:
        mist = _X.get('mist')
        if mist is None:
            mist = gfx.fbm_2d(H // 4, W // 4, 40, seed=91, octaves=4)
            _X['mist'] = mist
        m = np.roll(mist, int(lt * 18), axis=1)
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
        img += (np.clip(m - 0.45, 0, 1) * 0.35 * frost * yy)[..., None] * np.array([0.7, 0.85, 1.0], np.float32)
    return img


# ------------------------------------------------------------------ collision event display (2D)
def render_event(t, t0):
    lt = t - t0
    img = np.zeros((H, W, 3), np.float32)
    cx, cy = W / 2, H / 2 - 10
    L = Layer()
    c = L.canvas
    # detector layers
    a = smoothstep(0, 0.3, lt)
    for r, col, wdt in ((60, (0.5, 0.6, 0.8), 1.0), (120, (0.5, 0.6, 0.8), 1.0), (180, (0.5, 0.6, 0.8), 1.0),
                        (250, (0.9, 0.6, 0.3), 26.0), (330, (0.4, 0.55, 0.9), 34.0), (450, (0.8, 0.3, 0.3), 3.0),
                        (500, (0.8, 0.3, 0.3), 3.0)):
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=wdt,
                       Color=skia.Color4f(*col, (0.10 if wdt > 5 else 0.35) * a))
        c.drawCircle(cx, cy, r, p)
    rng = np.random.default_rng(14)
    grow = ease_out(clamp(lt / 0.9), 2)
    jets = [rng.uniform(0, 2 * math.pi) for _ in range(2)]
    for k in range(70):
        if k < 40:
            phi = jets[k % 2] + rng.normal(0, 0.18)
        else:
            phi = rng.uniform(0, 2 * math.pi)
        q = rng.choice([-1, 1])
        pt = rng.lognormal(0.0, 0.8)
        Rc = 120 * pt + 40          # radius of curvature in px (∝ momentum)
        rmax = min(250.0, 2 * Rc * 0.98)
        n = 40
        rs = np.linspace(0, rmax * grow, n)
        # circle through the origin: polar r = 2 Rc sin(alpha) ; walk along arc length
        alpha = np.arcsin(np.clip(rs / (2 * Rc), -1, 1))
        ang = phi + q * alpha
        xs, ys = cx + rs * np.cos(ang), cy + rs * np.sin(ang)
        path = skia.Path()
        path.moveTo(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(x, y)
        hue = (1.0, 0.9, 0.3) if pt > 1.6 else ((0.4, 1.0, 0.6) if q > 0 else (0.4, 0.85, 1.0))
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=1.6, Color=skia.Color4f(*hue, 0.9 * a))
        c.drawPath(path, p)
    # calorimeter energy towers along the jets
    for j in jets:
        for k in range(14):
            phi = j + rng.normal(0, 0.12)
            e = rng.gamma(2.0, 30) * smoothstep(0.4, 1.0, lt)
            x0, y0 = cx + 252 * math.cos(phi), cy + 252 * math.sin(phi)
            x1, y1 = cx + (252 + e) * math.cos(phi), cy + (252 + e) * math.sin(phi)
            p = skia.Paint(AntiAlias=True, StrokeWidth=7, Color=skia.Color4f(1.0, 0.75, 0.2, 0.85 * a))
            c.drawLine(x0, y0, x1, y1, p)
    gfx.over(img, L.rgba())
    radial_glow(img, cx, cy, 6, (1.0, 0.95, 0.85), 3.0 * math.exp(-lt * 2.5) + 0.4)
    return img


def render_lhc(t):
    if t < 127.6:
        img = render_ring(t)
        img *= smoothstep(123.0, 123.6, t)
        k = smoothstep(127.1, 127.6, t)
        return img * (1 - k) + k * 1.1
    if t < 133.4:
        img = render_tunnel(t)
        flash = 1 - smoothstep(127.6, 128.1, t)
        img = img * (1 - flash) + flash * 1.1
        k = smoothstep(133.0, 133.4, t)
        return img * (1 - k) + k * 1.6
    img = render_event(t, 133.4)
    flash = 1 - smoothstep(133.4, 133.9, t)
    img = img * (1 - flash) + flash * 1.6
    return img * (1 - smoothstep(135.6, 136.0, t))


# ------------------------------------------------------------------ tokamak plasma (raymarched)
TOKAMAK_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform vec3 eye; uniform vec3 fwd; uniform float time; uniform float glow;
const float R0 = 1.85;
float h21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
vec2 pol(vec3 p){ return vec2(length(p.xz) - R0, p.y); }
float vessel(vec3 p){ vec2 q = pol(p); return 0.82 - length(q*vec2(1.0, 0.72)); }
void main(){
  vec2 qv = (uv - 0.5) * vec2(res.x/res.y, 1.0);
  vec3 f = normalize(fwd), r = normalize(cross(f, vec3(0,1,0))), u = cross(r, f);
  vec3 d = normalize(f + qv.x*r*1.15 + qv.y*u*1.15);
  float t = 0.0; vec3 emis = vec3(0.0); vec3 p = eye; bool hit = false;
  for(int i=0;i<140;i++){
    p = eye + d*t;
    float h = vessel(p);
    vec2 q = pol(p);
    // plasma: D-shaped, bright edge layer + softer core, striated along helical field lines
    float rr = length(q*vec2(1.0, 0.62)) / 0.46;
    float edge = exp(-pow((rr - 0.95)/0.07, 2.0));
    float core = exp(-rr*rr*2.2) * 0.10;
    float phi = atan(p.z, p.x), th = atan(q.y, q.x);
    float str = 0.75 + 0.25*sin(phi*18.0 - th*6.0 + time*1.7) * sin(phi*7.0 + th*2.0 - time);
    float dens = (edge*1.0 + core) * str;
    float st = clamp(h*0.5, 0.012, 0.06);
    emis += vec3(1.0, 0.36, 0.78) * dens * st * 0.85 + vec3(0.40, 0.45, 1.0) * core * st * 0.6;
    if(h < 0.002){ hit = true; break; }
    t += st;
    if(t > 9.0) break;
  }
  vec3 col = emis * glow;
  if(hit){
    vec2 q = pol(p);
    float phi = atan(p.z, p.x), th = atan(q.y, q.x);
    vec2 tile = vec2(phi*60.0, th*18.0);
    vec2 ti = floor(tile), tf = fract(tile);
    float gap = smoothstep(0.0, 0.06, tf.x)*smoothstep(1.0, 0.94, tf.x)*smoothstep(0.0, 0.08, tf.y)*smoothstep(1.0, 0.92, tf.y);
    vec3 alb = vec3(0.13, 0.13, 0.14) * (0.7 + 0.5*h21(ti)) * (0.35 + 0.65*gap);
    // lit by the plasma (roughly: brighter on the outboard wall facing the plasma)
    float facing = clamp(-q.x/0.82*0.5 + 0.6, 0.0, 1.0);
    col += alb * vec3(1.0, 0.45, 0.85) * (0.6 + 1.4*facing) * glow;
  }
  o = vec4(col, 1.0);
}
"""


def render_fusion(t):
    t0 = 136.0
    if 'kfs' not in _X:
        _X['kfs'] = gl3d.FullScreen('tokamak', TOKAMAK_FS)
    lt = t - t0
    R0 = 1.85
    ph = math.radians(-20 + 4.5 * lt)
    eye = np.array([math.cos(ph) * (R0 + 0.55), 0.05 - 0.01 * lt, math.sin(ph) * (R0 + 0.55)])
    look = math.radians(-20 + 4.5 * lt + 38)
    tgt = np.array([math.cos(look) * (R0 - 0.1), -0.02, math.sin(look) * (R0 - 0.1)])
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    g = smoothstep(t0 + 0.2, t0 + 1.6, t) * (1.0 + 0.25 * smoothstep(141.0, 141.6, t))
    _X['kfs'].render(eye=tuple(eye), fwd=tuple(tgt - eye), time=t, glow=g)
    img = tg.read()[..., :3].copy()
    return img * (1 - smoothstep(144.6, 145.0, t))


# ------------------------------------------------------------------ optical lattice clock (2.5D)
def render_clock(t, t0=145.0):
    lt = t - t0
    img = np.zeros((H, W, 3), np.float32)
    rng = np.random.default_rng(5)
    # lattice laser: horizontal standing wave, perspective-tilted
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    zc = H * 0.5 + (xx - W / 2) * 0.10
    beam = np.exp(-((yy - zc) / 70.0) ** 2)
    phase = (xx - W / 2) * (1.0 + 0.0002 * (xx - W / 2))
    bands = 0.5 + 0.5 * np.cos(phase / 9.0 + lt * 0.3)
    img += (beam * (0.25 + 0.75 * bands ** 6))[..., None] * np.array([0.9, 0.12, 0.08], np.float32) * 0.8
    # atoms: pancakes of atoms sitting in the bright fringes
    if 'atoms' not in _X:
        ks = np.arange(-120, 121)
        pts = []
        for k in ks:
            for _ in range(10):
                pts.append((k, rng.normal(0, 0.18), rng.normal(0, 22)))
        _X['atoms'] = np.array(pts, np.float32)
    A = _X['atoms']
    xs = W / 2 + (A[:, 0] * 2 * math.pi * 9.0 - lt * 0.3 * 9.0) * 1.0 + A[:, 1] * 9.0
    ys = H * 0.5 + (xs - W / 2) * 0.10 + A[:, 2] + 2.0 * np.sin(lt * 6 + A[:, 0])
    m = (xs > 0) & (xs < W) & (ys > 0) & (ys < H)
    buf = np.zeros((H, W), np.float32)
    np.add.at(buf, (ys[m].astype(int), xs[m].astype(int)), 1.0)
    buf = cv2.GaussianBlur(buf, (0, 0), 1.6) * 9
    tick = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(lt * 2 * math.pi * 1.0))
    img += buf[..., None] * np.array([0.55, 0.75, 1.0], np.float32) * tick
    # probe laser
    img += (np.exp(-((yy - zc) / 3.0) ** 2) * 0.25)[..., None] * np.array([0.6, 0.85, 1.0], np.float32)
    # depth-of-field look: blur the far left/right
    blur = cv2.GaussianBlur(img, (0, 0), 6)
    wgt = np.clip(np.abs(xx - W / 2) / (W / 2), 0, 1)[..., None] ** 1.5
    img = img * (1 - wgt) + blur * wgt
    return img


# ------------------------------------------------------------------ gravitational waves (GL grid)
def render_gw(t, t0=150.0):
    if 'gwl' not in _X:
        _X['gwl'] = gl3d.Lines(200000)
    lt = t - t0
    T_MERGE = 3.0
    # inspiral: separation shrinks, orbital phase accelerates (chirp)
    tau = max(T_MERGE - lt, 0.02)
    sep = 1.2 * (tau / T_MERGE) ** 0.25
    phase = -2.0 * (tau ** 0.625) * 6.0
    merged = lt > T_MERGE
    n = 140
    xs = np.linspace(-9, 9, n)
    X, Z = np.meshgrid(xs, xs)
    Y = np.zeros_like(X)
    pos = [(sep * math.cos(phase), sep * math.sin(phase)), (-sep * math.cos(phase), -sep * math.sin(phase))]
    for (bx, bz) in (pos if not merged else [(0, 0)]):
        r = np.sqrt((X - bx) ** 2 + (Z - bz) ** 2)
        Y -= (0.9 if not merged else 1.5) / np.sqrt(r * r + 0.35)
    r = np.sqrt(X ** 2 + Z ** 2) + 1e-3
    ang = np.arctan2(Z, X)
    # quadrupole ripples travelling outward
    omega = 4.0 * (tau ** -0.375) if not merged else 9.0
    k = 1.6
    amp = 0.45 * (1.0 + 0.9 * math.exp(-max(0, lt - T_MERGE) * 1.2) * merged)
    wave = amp * np.cos(2 * ang - k * r + (lt * omega if not merged else lt * omega)) * np.clip(r / 2.0, 0, 1) / (1 + r * 0.25)
    if merged:
        front = (lt - T_MERGE) * 6.0
        wave *= 1.0 + 0.8 * np.exp(-((r - front) / 1.2) ** 2)
    Y += wave * 0.6
    P = np.stack([X, Y, Z], -1)
    segs = np.concatenate([np.stack([P[:, :-1], P[:, 1:]], 2).reshape(-1, 2, 3),
                           np.stack([P[:-1, :], P[1:, :]], 2).reshape(-1, 2, 3)], 0)
    mid = segs.mean(1)
    rr = np.sqrt(mid[:, 0] ** 2 + mid[:, 2] ** 2)
    alpha = np.clip(1.2 - rr / 9.0, 0, 1) ** 1.2 * 0.9
    col = np.zeros((len(segs), 2, 4), np.float32)
    col[..., 0], col[..., 1], col[..., 2] = 0.45, 0.75, 1.0
    col[..., 3] = alpha[:, None]
    ang_c = math.radians(25 + 6 * lt)
    eye = np.array([10.5 * math.cos(ang_c), 6.5 - 0.3 * lt, 10.5 * math.sin(ang_c)])
    view = gl3d.look_at(eye, np.array([0.0, -0.8, 0.0]))
    proj = gl3d.perspective(40, W / H, 0.1, 100)
    tg = gl3d.target(samples=0)
    tg.begin((0, 0, 0, 1))
    _X['gwl'].render(segs.astype(np.float32), col, width=1.7, depth_test=False, view=view, proj=proj)
    img = tg.read()[..., :3].copy()
    # the two black holes: dark cores with a bright photon-ring rim
    for (bx, bz) in (pos if not merged else [(0, 0)]):
        s, _, ok = gl3d.project(np.array([[bx, -1.4 if not merged else -2.0, bz]]), view, proj)
        if ok[0]:
            rpx = 18 if not merged else 26
            radial_glow(img, s[0, 0], s[0, 1], rpx * 1.6, (1.0, 0.8, 0.55), 0.5, falloff=3.0)
            cv2.circle(img, (int(s[0, 0]), int(s[0, 1])), rpx, (0, 0, 0), -1, cv2.LINE_AA)
            cv2.circle(img, (int(s[0, 0]), int(s[0, 1])), rpx, (1.0, 0.85, 0.6), 2, cv2.LINE_AA)
    if merged:
        img += np.float32(1.4) * math.exp(-(lt - T_MERGE) * 4.0)
    return img


def render_precision(t):
    if t < 150.2:
        img = render_clock(t)
        return img * smoothstep(145.0, 145.5, t) * (1 - smoothstep(149.8, 150.2, t))
    img = render_gw(t)
    return img * smoothstep(150.2, 150.7, t) * (1 - smoothstep(154.6, 155.0, t))
