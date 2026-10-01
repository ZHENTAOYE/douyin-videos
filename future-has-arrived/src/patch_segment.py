"""Re-render the first part of a scene segment and splice it onto the existing segment.
python3 patch_segment.py chip 1.6   -> re-renders [scene start, scene start + 1.6s) of segments/chip.mp4"""
import sys, os, subprocess, math
import numpy as np
from config import BUILD, W, H, FPS
import story, compose2

sid, dur = sys.argv[1], float(sys.argv[2])
a, b = [(x[1], x[2]) for x in story.SCENES if x[0] == sid][0]
seg = f'{BUILD}/segments/{sid}.mp4'
head = f'{BUILD}/segments/{sid}_head.mp4'
tail = f'{BUILD}/segments/{sid}_tail.mp4'
f0 = int(math.ceil(a * FPS - 1e-6))
n = int(round(dur * FPS))
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                      '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10', '-pix_fmt', 'yuv420p', head], stdin=subprocess.PIPE)
for i in range(f0, f0 + n):
    p.stdin.write(np.ascontiguousarray(compose2.render_frame(i / FPS, i)).tobytes())
p.stdin.close(); p.wait()
# drop the first n frames of the old segment (re-encode at the same quality so the cut is frame-exact)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', seg, '-vf', f'select=gte(n\\,{n}),setpts=PTS-STARTPTS', '-r', str(FPS),
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10', '-pix_fmt', 'yuv420p', tail], check=True)
lst = f'{BUILD}/segments/{sid}_patch.txt'
open(lst, 'w').write(f"file '{head}'\nfile '{tail}'\n")
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', seg + '.new.mp4'], check=True)
os.replace(seg + '.new.mp4', seg)
print('patched', seg)
