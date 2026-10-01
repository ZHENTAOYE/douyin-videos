"""Builds the master timeline (seconds) from the script structure + VO durations."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import BUILD
from script_data import SCENES


def build():
    p = f'{BUILD}/vo/vo.json'
    vo = json.load(open(p)) if os.path.exists(p) else {}
    t = 0.0
    scenes, lines = [], {}
    for sc in SCENES:
        s0 = t
        t += sc['lead']
        for ln in sc['lines']:
            d = vo[ln['id']]['dur'] if ln['id'] in vo else len(ln['say']) * 0.27   # estimate until VO exists
            lines[ln['id']] = dict(start=round(t, 3), end=round(t + d, 3), dur=d, sub=ln['sub'], scene=sc['id'])
            t += d + ln['pause']
        t += sc['tail']
        scenes.append(dict(id=sc['id'], start=round(s0, 3), end=round(t, 3)))
    tl = dict(total=round(t, 3), scenes=scenes, lines=lines)
    return tl


if __name__ == '__main__':
    tl = build()
    json.dump(tl, open(f'{BUILD}/timeline.json', 'w'), ensure_ascii=False, indent=1)
    for s in tl['scenes']:
        print(f"{s['id']:10s} {s['start']:7.2f} → {s['end']:7.2f}  ({s['end']-s['start']:.1f}s)")
    print('TOTAL', tl['total'])
