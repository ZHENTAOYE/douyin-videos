"""Earth renderer (full-screen ray-traced sphere): night lights, day map, clouds, ocean glint,
atmosphere rim, star field. Unit sphere, y = north, lon 0 faces +z.
Textures: Solar System Scope (CC BY 4.0, based on NASA imagery) via three.js examples."""
import math
import numpy as np, cv2
import gl3d
from config import ASSETS

EARTH_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform vec2 res; uniform mat4 inv_vp; uniform vec3 eye; uniform vec3 sun; uniform float rot;
uniform sampler2D tday; uniform sampler2D tnight; uniform sampler2D tmisc;
uniform float lights_gain; uniform float day_gain; uniform float star_gain; uniform float lights_reveal;
uniform float atmo_gain; uniform float exposure;
float hash(vec3 p){ p = fract(p*0.3183099+.1); p*=17.0; return fract(p.x*p.y*p.z*(p.x+p.y+p.z)); }
vec3 stars(vec3 d){
  vec3 c = vec3(0.0);
  for(int i=0;i<2;i++){
    float sc = (i==0) ? 220.0 : 520.0;
    vec3 g = floor(d*sc);
    float h = hash(g + float(i)*13.1);
    if(h > (i==0 ? 0.9965 : 0.9985)){
      vec3 cen = (g + 0.5 + 0.35*(vec3(hash(g+1.3),hash(g+2.7),hash(g+5.1))-0.5))/sc;
      float dd = length(d*1.0 - normalize(cen)) * sc;
      float b = exp(-dd*dd*6.0) * pow(hash(g+9.1), 3.0) * (i==0 ? 2.2 : 1.0);
      vec3 tint = mix(vec3(0.7,0.8,1.0), vec3(1.0,0.85,0.7), hash(g+4.4));
      c += tint * b;
    }
  }
  return c;
}
vec3 rotY(vec3 v, float a){ float c=cos(a), s=sin(a); return vec3(c*v.x + s*v.z, v.y, -s*v.x + c*v.z); }
vec2 sph_uv(vec3 n){
  vec3 q = rotY(n, -rot);
  float lon = atan(q.x, q.z);
  float lat = asin(clamp(q.y,-1.0,1.0));
  return vec2(lon/6.2831853 + 0.5, 0.5 + lat/3.1415926);
}
void main(){
  vec4 pp = inv_vp * vec4(uv*2.0-1.0, 1.0, 1.0);
  vec3 d = normalize(pp.xyz/pp.w - eye);
  vec3 col = stars(d) * star_gain;
  float b = dot(eye, d);
  float c = dot(eye, eye) - 1.0;
  float h = b*b - c;
  vec3 S = normalize(sun);
  // closest approach for the atmosphere halo
  float tc = max(-b, 0.0);
  vec3 pc = eye + d*tc;
  float rmin = length(pc);
  if(h > 0.0 && -b - sqrt(h) > 0.0){
    float t = -b - sqrt(h);
    vec3 p = eye + d*t;
    vec3 n = normalize(p);
    vec2 st = sph_uv(n);
    vec3 day = texture(tday, st).rgb;
    vec3 night = texture(tnight, st).rgb;
    vec3 misc = texture(tmisc, st).rgb;
    float cloud = smoothstep(0.25, 1.0, misc.b);
    float rough = misc.g;
    float ndl = dot(n, S);
    float dayk = smoothstep(-0.12, 0.25, ndl);
    float nightk = 1.0 - smoothstep(-0.18, 0.06, ndl);
    vec3 dayc = day * day * 1.6 * max(ndl, 0.0) * day_gain;
    dayc = mix(dayc, vec3(1.0)*max(ndl,0.0)*1.1*day_gain, cloud*0.85);
    // ocean glint
    vec3 r = reflect(-S, n);
    float spec = pow(max(dot(r, -d), 0.0), 60.0) * (1.0 - rough) * (1.0 - cloud) * dayk;
    dayc += vec3(1.0, 0.85, 0.65) * spec * 1.2 * day_gain;
    // city lights (slightly warmed, dimmed under clouds); reveal mask lets them fade up
    vec3 lights = pow(max(night, vec3(0.0)), vec3(1.15)) * vec3(1.15, 0.95, 0.70) * lights_gain * lights_reveal;
    lights *= (1.0 - 0.55*cloud);
    vec3 moonlit = day * 0.025 + vec3(0.02,0.03,0.06)*cloud*0.6;
    vec3 surf = dayc*dayk + (lights + moonlit) * nightk;
    // terminator warmth
    float term = exp(-(ndl/0.08)*(ndl/0.08));
    surf += vec3(0.35, 0.12, 0.03) * term * 0.25 * day_gain;
    // atmosphere on the disc (rim)
    float mu = max(dot(n, -d), 0.0);
    float rim = pow(max(1.0 - mu, 0.0), 3.0);
    vec3 atm = mix(vec3(0.95,0.45,0.18), vec3(0.30,0.55,1.0), smoothstep(-0.05, 0.35, ndl));
    surf += atm * rim * smoothstep(-0.3, 0.2, ndl) * 0.9 * atmo_gain;
    col = surf;
  } else if (rmin < 1.06 && dot(d, -eye) > -1.0) {
    // halo just outside the limb
    float hgt = rmin - 1.0;
    float g = exp(-max(hgt,0.0)/0.012) * 0.9 + exp(-max(hgt,0.0)/0.035) * 0.25;
    float sl = dot(normalize(pc), S);
    vec3 atm = mix(vec3(1.0,0.45,0.15), vec3(0.35,0.6,1.0), smoothstep(-0.05, 0.4, sl));
    col += atm * g * smoothstep(-0.35, 0.15, sl) * atmo_gain;
  }
  o = vec4(col*exposure, 1.0);
}
"""

_E = {}


def textures():
    if _E:
        return _E

    def load(name):
        im = cv2.imread(f'{ASSETS}/{name}', cv2.IMREAD_COLOR)
        return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    _E['day'] = gl3d.texture_from_array(load('three_earth_day_4096.jpg'))
    _E['night'] = gl3d.texture_from_array(load('three_earth_night_4096.jpg'))
    _E['misc'] = gl3d.texture_from_array(load('three_clouds.jpg'))
    _E['fs'] = gl3d.FullScreen('earth', EARTH_FS)
    return _E


def latlon_to_xyz(lat, lon, r=1.0, rot=0.0):
    lat, lon = np.radians(lat), np.radians(lon)
    x = np.cos(lat) * np.sin(lon)
    y = np.sin(lat)
    z = np.cos(lat) * np.cos(lon)
    c, s = math.cos(rot), math.sin(rot)
    xr = c * x + s * z
    zr = -s * x + c * z
    return np.stack([xr, y, zr], -1) * r


def render_earth(view, proj, eye, sun, rot, lights_gain=1.0, day_gain=1.0, star_gain=1.0, lights_reveal=1.0,
                 atmo_gain=1.0, exposure=1.0):
    E = textures()
    inv = np.linalg.inv(proj @ view).astype(np.float32)
    gl3d.ctx().depth_mask = False
    E['fs'].render(textures={'tday': E['day'], 'tnight': E['night'], 'tmisc': E['misc']},
                   inv_vp=inv, eye=tuple(eye), sun=tuple(sun), rot=rot, lights_gain=lights_gain, day_gain=day_gain,
                   star_gain=star_gain, lights_reveal=lights_reveal, atmo_gain=atmo_gain, exposure=exposure)
    gl3d.ctx().depth_mask = True


def occluded(points, eye):
    """True where the segment eye->point passes through the unit sphere (point hidden by Earth)."""
    d = points - eye
    L = np.linalg.norm(d, axis=1)
    dn = d / L[:, None]
    b = dn @ eye
    c = eye @ eye - 1.0
    h = b * b - c
    t = -b - np.sqrt(np.maximum(h, 0))
    return (h > 0) & (t > 0) & (t < L - 1e-4)
