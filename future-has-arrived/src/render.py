"""Render the picture in parallel, one job per scene, to high-quality intermediate segments,
then concatenate. Usage:
  python3 render.py [--workers 3] [--only chip,earth] [--concat]
Segments: build/segments/<scene>.mp4 (x264 crf 10, yuv420p, 30 fps)."""
import os, sys, time, math, argparse, subprocess, multiprocessing as mp
from config import BUILD, W, H, FPS

SEG = f'{BUILD}/segments'


def frame_range(a, b):
    return int(math.ceil(a * FPS - 1e-6)), int(math.ceil(b * FPS - 1e-6))


def render_scene(job):
    sid, a, b = job
    os.environ.setdefault('LP_NUM_THREADS', '2')
    import numpy as np
    import compose2
    f0, f1 = frame_range(a, b)
    out = f'{SEG}/{sid}.mp4'
    tmp = out + '.part.mp4'
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
           '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10', '-pix_fmt', 'yuv420p', '-threads', '2', tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t_start = time.time()
    for i in range(f0, f1):
        fr = compose2.render_frame(i / FPS, i)
        p.stdin.write(np.ascontiguousarray(fr).tobytes())
        if (i - f0) % 60 == 0:
            el = time.time() - t_start
            done = i - f0 + 1
            print(f'[{sid}] {done}/{f1 - f0} frames, {el / done:.2f}s/frame', flush=True)
    p.stdin.close()
    p.wait()
    os.replace(tmp, out)
    print(f'[{sid}] DONE {f1 - f0} frames in {time.time() - t_start:.0f}s', flush=True)
    return sid


def concat(scenes):
    lst = f'{SEG}/list.txt'
    with open(lst, 'w') as f:
        for sid, a, b in scenes:
            f.write(f"file '{SEG}/{sid}.mp4'\n")
    out = f'{BUILD}/picture.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', out], check=True)
    print('concat ->', out)


if __name__ == '__main__':
    import story
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--only', default='')
    ap.add_argument('--concat', action='store_true')
    args = ap.parse_args()
    os.makedirs(SEG, exist_ok=True)
    scenes = story.SCENES
    if args.concat:
        concat(scenes)
        sys.exit(0)
    jobs = [s for s in scenes if not args.only or s[0] in args.only.split(',')]
    # longest / heaviest first
    weight = {'chip': 3.0, 'earth': 1.4, 'lhc': 1.5, 'fusion': 1.6, 'moore': 0.8}
    jobs.sort(key=lambda s: -(s[2] - s[1]) * weight.get(s[0], 1.0))
    # recap shots must exist before the montage renders
    import scene_accel
    scene_accel.precompute_recaps()
    ctx = mp.get_context('spawn')
    with ctx.Pool(args.workers, maxtasksperchild=1) as pool:
        for sid in pool.imap_unordered(render_scene, jobs):
            print('finished', sid, flush=True)
    if not args.only:
        concat(scenes)
