"""Render review stills: python3 still2.py t1 t2 ... -> build/stills2/tXXXX.png (+ a contact sheet)."""
import sys, os, time
import numpy as np, cv2
from config import BUILD
import compose2
os.makedirs(f'{BUILD}/stills2', exist_ok=True)
paths = []
for a in sys.argv[1:]:
    t = float(a)
    t0 = time.time()
    fr = compose2.render_frame(t, int(t * 30))
    fn = f'{BUILD}/stills2/t{t:07.2f}.png'
    cv2.imwrite(fn, cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    paths.append(fn)
    print(fn, round(time.time() - t0, 2), 's', flush=True)
if len(paths) > 1:
    ims = [cv2.resize(cv2.imread(p), (640, 360)) for p in paths]
    while len(ims) % 3:
        ims.append(np.zeros_like(ims[0]))
    rows = [np.hstack(ims[i:i + 3]) for i in range(0, len(ims), 3)]
    cv2.imwrite(f'{BUILD}/stills2/sheet.png', np.vstack(rows))
