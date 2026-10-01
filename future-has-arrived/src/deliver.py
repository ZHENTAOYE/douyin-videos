"""Encode deliverables from build/picture.mp4 (silent for now):
  output/未来已到达_1080p.mp4        master for upload, ~3.4 Mbps two-pass (kept < 95 MB so it fits in git)
  output/preview_part1.mp4 / part2   chat previews, each < 29 MB
"""
import os, subprocess, json
from config import BUILD, OUTPUT

SRC = f'{BUILD}/picture.mp4'


def dur(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)['format']['duration'])


def two_pass(src, dst, kbps, ss=None, to=None, vf=None):
    base = ['ffmpeg', '-y', '-loglevel', 'error']
    rng = []
    if ss is not None:
        rng += ['-ss', str(ss)]
    if to is not None:
        rng += ['-to', str(to)]
    filt = ['-vf', vf] if vf else []
    common = ['-c:v', 'libx264', '-preset', 'slow', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.6)}k',
              '-bufsize', f'{kbps * 3}k', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-g', '60']
    log = f'{BUILD}/x264_2pass'
    subprocess.run(base + rng + ['-i', src] + filt + common + ['-pass', '1', '-passlogfile', log, '-an', '-f', 'mp4', '/dev/null'], check=True)
    # a silent stereo track keeps every player / uploader happy
    subprocess.run(base + rng + ['-i', src, '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo'] + filt + common +
                   ['-pass', '2', '-passlogfile', log, '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart', dst], check=True)
    print(dst, round(os.path.getsize(dst) / 1e6, 1), 'MB')


if __name__ == '__main__':
    os.makedirs(OUTPUT, exist_ok=True)
    total = dur(SRC)
    budget_mb = 93.0
    kbps = int(budget_mb * 8000 / total) - 70
    two_pass(SRC, f'{OUTPUT}/未来已到达_1080p.mp4', kbps)
    split = 106.0
    for name, a, b in (('preview_part1.mp4', 0.0, split), ('preview_part2.mp4', split, total)):
        k = int(28.0 * 8000 / (b - a)) - 70
        two_pass(SRC, f'{OUTPUT}/{name}', k, ss=a, to=b, vf='hqdn3d=1.2:1.2:3:3')
