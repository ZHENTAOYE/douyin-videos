"""Minimal moderngl toolkit (headless EGL / Mesa llvmpipe): camera math, render targets,
instanced lit boxes, additive point sprites, thick lines, triangle meshes, full-screen shaders."""
import math
import numpy as np
import moderngl
from config import W, H

_CTX = None


def ctx():
    global _CTX
    if _CTX is None:
        _CTX = moderngl.create_standalone_context(backend='egl')
        _CTX.enable(moderngl.DEPTH_TEST)
    return _CTX


# ------------------------------------------------------------------ math
def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fovy_deg) / 2)
    m = np.zeros((4, 4), np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = (np.asarray(v, np.float64) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[0, 3], m[1, 3], m[2, 3] = -s @ eye, -u @ eye, f @ eye
    return m


def gl_mat(m):
    """numpy row-major 4x4 -> bytes in column-major order for GLSL mat4."""
    return np.ascontiguousarray(m.T, dtype=np.float32).tobytes()


def project(points, view, proj, w=W, h=H):
    """World points (N,3) -> screen xy (N,2), depth (N,) (view-space -z), visible mask."""
    p = np.c_[points, np.ones(len(points))] @ (proj @ view).T
    z = p[:, 3]
    ok = z > 1e-6
    ndc = p[:, :3] / np.where(ok, z, 1)[:, None]
    sx = (ndc[:, 0] * 0.5 + 0.5) * w
    sy = (1 - (ndc[:, 1] * 0.5 + 0.5)) * h
    return np.c_[sx, sy], z, ok


# ------------------------------------------------------------------ render target
class Target:
    def __init__(self, w=W, h=H, samples=4):
        c = ctx()
        self.w, self.h = w, h
        self.ms_color = c.renderbuffer((w, h), 4, dtype='f2', samples=samples)
        self.ms_depth = c.depth_renderbuffer((w, h), samples=samples)
        self.ms = c.framebuffer([self.ms_color], self.ms_depth)
        self.color = c.texture((w, h), 4, dtype='f2')
        self.depth = c.depth_texture((w, h))
        self.res = c.framebuffer([self.color], self.depth)

    def begin(self, clear=(0, 0, 0, 0)):
        self.ms.use()
        self.ms.clear(*clear, depth=1.0)
        c = ctx()
        c.enable(moderngl.DEPTH_TEST)
        c.disable(moderngl.BLEND)
        c.viewport = (0, 0, self.w, self.h)

    def read(self):
        ctx().copy_framebuffer(self.res, self.ms)
        raw = self.res.read(components=4, dtype='f2')
        a = np.frombuffer(raw, np.float16).reshape(self.h, self.w, 4).astype(np.float32)
        a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
        return a[::-1]      # GL origin is bottom-left


_targets = {}


def target(w=W, h=H, samples=4):
    k = (w, h, samples)
    if k not in _targets:
        _targets[k] = Target(w, h, samples)
    return _targets[k]


# ------------------------------------------------------------------ shaders
LIT_BOX_VS = """
#version 330
in vec3 in_pos; in vec3 in_nrm;
in vec3 i_c; in vec3 i_s; in vec4 i_col; in float i_emit;
uniform mat4 view; uniform mat4 proj;
out vec3 v_wpos; out vec3 v_nrm; out vec4 v_col; out float v_emit; out vec3 v_local; out vec3 v_size;
void main(){
  vec3 wp = i_c + in_pos * i_s;
  v_wpos = wp; v_nrm = in_nrm; v_col = i_col; v_emit = i_emit; v_local = in_pos; v_size = i_s;
  gl_Position = proj * view * vec4(wp, 1.0);
}
"""

LIT_BOX_FS = """
#version 330
in vec3 v_wpos; in vec3 v_nrm; in vec4 v_col; in float v_emit; in vec3 v_local; in vec3 v_size;
uniform vec3 eye; uniform vec3 key_dir; uniform vec3 key_col; uniform vec3 sky_col; uniform vec3 gnd_col;
uniform vec3 hor_col; uniform vec3 fill_dir; uniform vec3 fill_col;
uniform vec3 fog_col; uniform float fog_density; uniform float fog_height; uniform float time;
uniform float metal; uniform float rough; uniform float exposure;
uniform sampler2D shadow_map; uniform mat4 light_vp; uniform float use_shadow; uniform float shadow_bias;
out vec4 o;
float ggx(float NdH, float a){ float a2=a*a; float d=NdH*NdH*(a2-1.0)+1.0; return a2/(3.14159*d*d); }
vec3 env(vec3 d){
  float y = d.y;
  vec3 c = mix(hor_col, sky_col, smoothstep(0.0, 0.6, y));
  c = mix(c, gnd_col, smoothstep(0.0, -0.25, y));
  float s = max(dot(d, -normalize(key_dir)), 0.0);
  c += key_col * (pow(s, 48.0)*0.6 + pow(s, 6.0)*0.08);
  return c;
}
float shadow(vec3 wp, vec3 n){
  if(use_shadow < 0.5) return 1.0;
  vec4 lp = light_vp * vec4(wp + n*0.04, 1.0);
  vec3 q = lp.xyz/lp.w*0.5+0.5;
  if(q.x<0.0||q.x>1.0||q.y<0.0||q.y>1.0) return 1.0;
  float sh = 0.0; vec2 ts = 1.0/vec2(textureSize(shadow_map,0));
  for(int i=-1;i<=1;i++) for(int j=-1;j<=1;j++){
    float d = texture(shadow_map, q.xy + vec2(i,j)*ts*1.2).r;
    sh += (q.z - shadow_bias > d) ? 0.0 : 1.0;
  }
  return sh/9.0;
}
void main(){
  vec3 n = normalize(v_nrm);
  vec3 v = normalize(eye - v_wpos);
  vec3 l = normalize(-key_dir);
  vec3 h = normalize(l + v);
  vec3 base = v_col.rgb;
  float mt = metal * v_col.a;
  float NdL = max(dot(n,l),0.0), NdV = max(dot(n,v),1e-3), NdH = max(dot(n,h),0.0);
  vec3 F0 = mix(vec3(0.04), base, mt);
  float VdH = max(dot(h,v),0.0);
  vec3 F = F0 + (1.0-F0)*pow(1.0-VdH,5.0);
  float a = max(rough*rough, 0.02);
  float D = ggx(NdH, a);
  float k = (rough+1.0)*(rough+1.0)/8.0;
  float G = (NdL/(NdL*(1.0-k)+k))*(NdV/(NdV*(1.0-k)+k));
  vec3 spec = D*F*G/max(4.0*NdL*NdV,1e-3);
  vec3 diff = (1.0-F)*(1.0-mt)*base/3.14159;
  float sh = shadow(v_wpos, n);
  vec3 Fv = F0 + (1.0-F0)*pow(1.0-NdV,5.0);
  vec3 r = reflect(-v, n);
  float ao = clamp(0.30 + 0.70*(v_local.y+0.5), 0.0, 1.0);
  ao *= clamp(0.55 + v_wpos.y*0.03, 0.0, 1.0);
  vec3 amb = env(n)*(base*(1.0-mt))*0.9 + env(r)*Fv*(1.0-0.6*rough);
  vec3 col = (diff + spec) * key_col * NdL * sh + amb * ao;
  vec3 lf = normalize(-fill_dir); float NdF = max(dot(n,lf),0.0);
  vec3 hf = normalize(lf+v); float Df = ggx(max(dot(n,hf),0.0), a);
  col += (diff + Df*F0*0.25) * fill_col * NdF * ao;
  vec3 e = abs(v_local)*2.0;
  float edge = 1.0 - 0.3*smoothstep(0.93,1.0,max(max(min(e.x,e.y),min(e.y,e.z)),min(e.x,e.z)));
  col *= edge;
  col += base * v_emit;
  float d = length(eye - v_wpos);
  float fh = exp(-max(v_wpos.y,0.0)/max(fog_height,1e-3));
  float fog = 1.0 - exp(-d*fog_density*(0.5+0.5*fh));
  col = mix(col, fog_col, clamp(fog,0.0,1.0));
  o = vec4(col*exposure, 1.0);
}
"""

POINT_VS = """
#version 330
in vec3 i_p; in vec4 i_col; in float i_size;
uniform mat4 view; uniform mat4 proj; uniform float px_scale;
out vec4 v_col;
void main(){
  vec4 vp = view * vec4(i_p,1.0);
  gl_Position = proj * vp;
  gl_PointSize = clamp(i_size * px_scale / max(-vp.z,1e-3), 1.0, 256.0);
  v_col = i_col;
}
"""
POINT_FS = """
#version 330
in vec4 v_col; out vec4 o;
void main(){
  vec2 d = gl_PointCoord*2.0-1.0; float r2 = dot(d,d);
  if(r2>1.0) discard;
  float a = exp(-r2*4.0) + 0.25*exp(-r2*1.2);
  o = vec4(v_col.rgb * v_col.a * a, 0.0);
}
"""

LINE_VS = """
#version 330
in vec3 in_p; in vec4 in_col;
uniform mat4 view; uniform mat4 proj;
out vec4 g_col;
void main(){ gl_Position = proj*view*vec4(in_p,1.0); g_col = in_col; }
"""
LINE_GS = """
#version 330
layout(lines) in; layout(triangle_strip, max_vertices=4) out;
in vec4 g_col[]; out vec4 f_col; out float f_d;
uniform vec2 vp; uniform float width;
void main(){
  vec4 a = gl_in[0].gl_Position, b = gl_in[1].gl_Position;
  if(a.w<=0.0 || b.w<=0.0) return;
  vec2 sa = a.xy/a.w*vp*0.5, sb = b.xy/b.w*vp*0.5;
  vec2 dir = normalize(sb-sa + vec2(1e-6));
  vec2 nrm = vec2(-dir.y, dir.x) * width * 0.5;
  vec2 na = nrm/(vp*0.5)*a.w, nb = nrm/(vp*0.5)*b.w;
  f_col=g_col[0]; f_d=-1.0; gl_Position = a + vec4(na,0,0); EmitVertex();
  f_col=g_col[0]; f_d= 1.0; gl_Position = a - vec4(na,0,0); EmitVertex();
  f_col=g_col[1]; f_d=-1.0; gl_Position = b + vec4(nb,0,0); EmitVertex();
  f_col=g_col[1]; f_d= 1.0; gl_Position = b - vec4(nb,0,0); EmitVertex();
  EndPrimitive();
}
"""
LINE_FS = """
#version 330
in vec4 f_col; in float f_d; out vec4 o;
void main(){ float a = 1.0 - smoothstep(0.35, 1.0, abs(f_d)); o = vec4(f_col.rgb*f_col.a*a, 0.0); }
"""

MESH_VS = """
#version 330
in vec3 in_pos; in vec3 in_nrm; in vec4 in_col;
uniform mat4 view; uniform mat4 proj; uniform mat4 model;
out vec3 v_wpos; out vec3 v_nrm; out vec4 v_col;
void main(){ vec4 wp = model*vec4(in_pos,1.0); v_wpos = wp.xyz; v_nrm = mat3(model)*in_nrm; v_col = in_col; gl_Position = proj*view*wp; }
"""
MESH_FS = """
#version 330
in vec3 v_wpos; in vec3 v_nrm; in vec4 v_col;
uniform vec3 eye; uniform vec3 key_dir; uniform vec3 key_col; uniform vec3 amb_col; uniform float shininess; uniform float spec_k;
uniform vec3 rim_col; uniform float emit; uniform vec3 fog_col; uniform float fog_density;
out vec4 o;
void main(){
  vec3 n = normalize(v_nrm); vec3 v = normalize(eye - v_wpos); vec3 l = normalize(-key_dir);
  if(dot(n,v)<0.0) n = -n;
  float d = max(dot(n,l),0.0);
  float s = pow(max(dot(n, normalize(l+v)),0.0), shininess) * spec_k;
  float rim = pow(1.0 - max(dot(n,v),0.0), 3.0);
  vec3 c = v_col.rgb*(amb_col + key_col*d) + key_col*s + rim_col*rim + v_col.rgb*emit;
  float fd = length(eye - v_wpos);
  c = mix(c, fog_col, 1.0 - exp(-fd*fog_density));
  o = vec4(c, 1.0);
}
"""

FS_QUAD_VS = """
#version 330
in vec2 p; out vec2 uv;
void main(){ uv = p*0.5+0.5; gl_Position = vec4(p,0.0,1.0); }
"""

DEPTH_VS = """
#version 330
in vec3 in_pos; in vec3 i_c; in vec3 i_s;
uniform mat4 light_vp;
void main(){ gl_Position = light_vp * vec4(i_c + in_pos*i_s, 1.0); }
"""
DEPTH_FS = """
#version 330
void main(){}
"""

_progs = {}


def program(name, vs, fs, gs=None):
    if name not in _progs:
        _progs[name] = ctx().program(vertex_shader=vs, fragment_shader=fs, geometry_shader=gs)
    return _progs[name]


def set_uniforms(prog, **u):
    for k, v in u.items():
        if k not in prog:
            continue
        if isinstance(v, np.ndarray) and v.shape == (4, 4):
            prog[k].write(gl_mat(v))
        elif isinstance(v, (tuple, list, np.ndarray)):
            prog[k].value = tuple(float(x) for x in v)
        else:
            prog[k].value = v


# ------------------------------------------------------------------ geometry builders
def cube_vertices():
    faces = [((1, 0, 0), [(.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5), (.5, -.5, .5)]),
             ((-1, 0, 0), [(-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5), (-.5, -.5, -.5)]),
             ((0, 1, 0), [(-.5, .5, -.5), (-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5)]),
             ((0, -1, 0), [(-.5, -.5, .5), (-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5)]),
             ((0, 0, 1), [(-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]),
             ((0, 0, -1), [(.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5)])]
    out = []
    for n, q in faces:
        for i in (0, 1, 2, 0, 2, 3):
            out.extend(q[i] + n)
    return np.array(out, np.float32)


class Boxes:
    """Instanced boxes. instances: centers (N,3), sizes (N,3), colors (N,4), emit (N,)"""

    def __init__(self, centers, sizes, colors, emit=None):
        c = ctx()
        self.prog = program('litbox', LIT_BOX_VS, LIT_BOX_FS)
        self.vbo = c.buffer(cube_vertices().tobytes())
        n = len(centers)
        if emit is None:
            emit = np.zeros(n, np.float32)
        inst = np.c_[centers, sizes, colors, emit].astype(np.float32)
        self.ibo = c.buffer(inst.tobytes())
        self.n = n
        self.vao = c.vertex_array(self.prog, [
            (self.vbo, '3f 3f', 'in_pos', 'in_nrm'),
            (self.ibo, '3f 3f 4f 1f/i', 'i_c', 'i_s', 'i_col', 'i_emit')])

    def render_depth(self, light_vp):
        if not hasattr(self, 'dvao'):
            dp = program('depthbox', DEPTH_VS, DEPTH_FS)
            self.dprog = dp
            self.dvao = ctx().vertex_array(dp, [
                (self.vbo, '3f 12x', 'in_pos'),
                (self.ibo, '3f 3f 20x/i', 'i_c', 'i_s')])
        self.dprog['light_vp'].write(gl_mat(light_vp))
        self.dvao.render(moderngl.TRIANGLES, instances=self.n)

    def update(self, centers, sizes, colors, emit):
        inst = np.c_[centers, sizes, colors, emit].astype(np.float32)
        if len(inst) != self.n:
            raise ValueError('instance count changed')
        self.ibo.write(inst.tobytes())

    def render(self, **u):
        set_uniforms(self.prog, **u)
        self.vao.render(moderngl.TRIANGLES, instances=self.n)


class Points:
    def __init__(self, max_n=200000):
        c = ctx()
        self.prog = program('points', POINT_VS, POINT_FS)
        self.buf = c.buffer(reserve=max_n * 8 * 4)
        self.vao = c.vertex_array(self.prog, [(self.buf, '3f 4f 1f', 'i_p', 'i_col', 'i_size')])

    def render(self, pos, col, size, depth_test=True, **u):
        data = np.c_[pos, col, size].astype(np.float32)
        if len(data) == 0:
            return
        self.buf.orphan()
        self.buf.write(data.tobytes())
        c = ctx()
        c.enable(moderngl.BLEND)
        c.enable(moderngl.PROGRAM_POINT_SIZE)
        c.blend_func = moderngl.ONE, moderngl.ONE
        c.depth_mask = False
        if not depth_test:
            c.disable(moderngl.DEPTH_TEST)
        set_uniforms(self.prog, **u)
        self.vao.render(moderngl.POINTS, vertices=len(data))
        c.depth_mask = True
        c.enable(moderngl.DEPTH_TEST)
        c.disable(moderngl.BLEND)


class Lines:
    def __init__(self, max_segments=400000):
        c = ctx()
        self.prog = program('lines', LINE_VS, LINE_FS, LINE_GS)
        self.buf = c.buffer(reserve=max_segments * 2 * 7 * 4)
        self.vao = c.vertex_array(self.prog, [(self.buf, '3f 4f', 'in_p', 'in_col')])

    def render(self, seg_pos, seg_col, width=2.0, depth_test=True, **u):
        """seg_pos (N,2,3), seg_col (N,2,4) -> additive anti-aliased thick lines."""
        if len(seg_pos) == 0:
            return
        data = np.concatenate([seg_pos.reshape(-1, 3), seg_col.reshape(-1, 4)], axis=1).astype(np.float32)
        self.buf.orphan()
        self.buf.write(data.tobytes())
        c = ctx()
        c.enable(moderngl.BLEND)
        c.blend_func = moderngl.ONE, moderngl.ONE
        c.depth_mask = False
        if not depth_test:
            c.disable(moderngl.DEPTH_TEST)
        set_uniforms(self.prog, vp=(W, H), width=width, **u)
        self.vao.render(moderngl.LINES, vertices=len(data))
        c.depth_mask = True
        c.enable(moderngl.DEPTH_TEST)
        c.disable(moderngl.BLEND)


class Mesh:
    def __init__(self, pos, nrm, col, idx=None):
        c = ctx()
        self.prog = program('mesh', MESH_VS, MESH_FS)
        data = np.c_[pos, nrm, col].astype(np.float32)
        self.vbo = c.buffer(data.tobytes())
        if idx is not None:
            self.ibo = c.buffer(np.asarray(idx, np.int32).tobytes())
            self.vao = c.vertex_array(self.prog, [(self.vbo, '3f 3f 4f', 'in_pos', 'in_nrm', 'in_col')], self.ibo)
        else:
            self.vao = c.vertex_array(self.prog, [(self.vbo, '3f 3f 4f', 'in_pos', 'in_nrm', 'in_col')])

    def render(self, model=None, **u):
        set_uniforms(self.prog, model=np.eye(4, dtype=np.float32) if model is None else model, **u)
        self.vao.render(moderngl.TRIANGLES)


class FullScreen:
    """Full-screen fragment shader pass. Uniform `res` (vec2) is set automatically."""

    def __init__(self, name, frag):
        c = ctx()
        self.prog = program('fs_' + name, FS_QUAD_VS, frag)
        self.vbo = c.buffer(np.array([-1, -1, 1, -1, -1, 1, 1, 1], np.float32).tobytes())
        self.vao = c.vertex_array(self.prog, [(self.vbo, '2f', 'p')])

    def render(self, textures=None, blend=False, **u):
        c = ctx()
        c.disable(moderngl.DEPTH_TEST)
        if blend:
            c.enable(moderngl.BLEND)
            c.blend_func = moderngl.ONE, moderngl.ONE
        for i, (name, tex) in enumerate((textures or {}).items()):
            tex.use(location=i)
            if name in self.prog:
                self.prog[name].value = i
        set_uniforms(self.prog, res=(W, H), **u)
        self.vao.render(moderngl.TRIANGLE_STRIP)
        c.enable(moderngl.DEPTH_TEST)
        c.disable(moderngl.BLEND)


class ShadowMap:
    def __init__(self, size=4096):
        c = ctx()
        self.size = size
        self.tex = c.depth_texture((size, size))
        self.tex.compare_func = ''
        self.tex.filter = moderngl.NEAREST, moderngl.NEAREST
        self.fbo = c.framebuffer(depth_attachment=self.tex)

    def render(self, drawables, light_vp):
        c = ctx()
        self.fbo.use()
        self.fbo.clear(depth=1.0)
        c.viewport = (0, 0, self.size, self.size)
        c.enable(moderngl.DEPTH_TEST)
        for d in drawables:
            d.render_depth(light_vp)


def ortho(l, r, b, t, n, f):
    m = np.eye(4, dtype=np.float32)
    m[0, 0], m[1, 1], m[2, 2] = 2 / (r - l), 2 / (t - b), -2 / (f - n)
    m[0, 3], m[1, 3], m[2, 3] = -(r + l) / (r - l), -(t + b) / (t - b), -(f + n) / (f - n)
    return m


def texture_from_array(a, mipmaps=True, repeat_x=True):
    """float/uint8 HxWxC numpy -> GL texture (flipped so row 0 is the top)."""
    a = np.ascontiguousarray(a[::-1])
    h, w = a.shape[:2]
    comps = 1 if a.ndim == 2 else a.shape[2]
    if a.dtype == np.uint8:
        tex = ctx().texture((w, h), comps, a.tobytes())
    else:
        tex = ctx().texture((w, h), comps, a.astype(np.float32).tobytes(), dtype='f4')
    if mipmaps:
        tex.build_mipmaps()
        tex.filter = moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR
        tex.anisotropy = 8.0
    else:
        tex.filter = moderngl.LINEAR, moderngl.LINEAR
    tex.repeat_x = repeat_x
    tex.repeat_y = False
    return tex
