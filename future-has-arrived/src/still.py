"""Render individual frames for review: python3 still.py <t1> <t2> ... (seconds) -> build/stills/"""
import sys, os, json
import numpy as np, cv2
from config import BUILD
import timeline, compose
tl = timeline.build()
os.makedirs(f'{BUILD}/stills', exist_ok=True)
for a in sys.argv[1:]:
    t = float(a)
    fr = compose.render_frame(tl, t, int(t * 30))
    fn = f'{BUILD}/stills/t{t:07.2f}.png'
    cv2.imwrite(fn, cv2.cvtColor(fr, cv2.COLOR_RGB2BGR))
    print(fn)
