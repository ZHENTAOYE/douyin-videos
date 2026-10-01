import subprocess, numpy as np, soundfile as sf, timeline, compose
from config import BUILD, W, H, FPS, SR
tl = timeline.build(); T = 34.84
out = '/home/user/douyin-videos/future-has-arrived/output/preview_opening.mp4'
a = np.zeros(int(T*SR)+SR)
for lid, ln in tl['lines'].items():
    if ln['start'] < T:
        y, _ = sf.read(f'{BUILD}/vo/{lid}.wav'); i = int(ln['start']*SR); a[i:i+len(y)] += y[:len(a)-i]
sf.write(f'{BUILD}/preview.wav', a[:int(T*SR)]*0.9, SR)
p = subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
    '-i',f'{BUILD}/preview.wav','-c:v','libx264','-crf','19','-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-shortest',out], stdin=subprocess.PIPE)
for i in range(int(T*FPS)):
    p.stdin.write(compose.render_frame(tl, i/FPS, i).tobytes())
p.stdin.close(); p.wait(); print(out)
