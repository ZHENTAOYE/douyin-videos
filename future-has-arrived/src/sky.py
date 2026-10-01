"""Full-screen sky / haze backdrop for 3D scenes (depends on the camera's view direction)."""
import numpy as np
import gl3d

SKY_FS = """
#version 330
in vec2 uv; out vec4 o;
uniform mat4 inv_vp; uniform vec3 eye; uniform vec3 zen_col; uniform vec3 hor_col; uniform vec3 sun_dir; uniform vec3 sun_col;
uniform float exposure;
void main(){
  vec4 p = inv_vp * vec4(uv*2.0-1.0, 1.0, 1.0);
  vec3 d = normalize(p.xyz/p.w - eye);
  float y = d.y;
  vec3 c = mix(hor_col, zen_col, pow(smoothstep(-0.02, 0.55, y), 0.7));
  c *= smoothstep(-0.25, 0.0, y)*0.85+0.15;
  float s = max(dot(d, -normalize(sun_dir)), 0.0);
  c += sun_col*(pow(s, 900.0)*6.0 + pow(s, 40.0)*0.25 + pow(s, 5.0)*0.10);
  o = vec4(c*exposure, 1.0);
}
"""
_fs = None


def render(view, proj, eye, zen_col, hor_col, sun_dir, sun_col, exposure=1.0):
    global _fs
    if _fs is None:
        _fs = gl3d.FullScreen('sky', SKY_FS)
    inv = np.linalg.inv(proj @ view).astype(np.float32)
    gl3d.ctx().depth_mask = False
    _fs.render(inv_vp=inv, eye=eye, zen_col=zen_col, hor_col=hor_col, sun_dir=sun_dir, sun_col=sun_col, exposure=exposure)
    gl3d.ctx().depth_mask = True
