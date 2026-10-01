"""Lay the narration lines end-to-end and write the master timeline.

Everything downstream (frames, music, sound effects) reads build/timeline.json,
so changing a line or a pause in script.py re-times the whole film.
"""
import json, os, re, wave
import numpy as np
from scipy.signal import resample_poly

from script import SCENES, plain

HERE = os.path.dirname(__file__)
BUILD = os.path.join(HERE, "..", "build")
SR = 48000
LEAD_IN = 0.35          # 第一帧先给画面，0.35 秒后开口
TAIL = 1.2              # 最后一句之后留给片尾


def read_wav(p):
    with wave.open(p) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return sr, x


def keyword_times(text, t0, t1, chunks):
    """Estimate when each 【keyword】 starts, using chunk timings + char position."""
    out = []
    for c in chunks:
        raw = c["text"]
        body = re.sub(r"[【】]", "", raw)
        n = max(1, len(body))
        pos = 0
        for m in re.finditer(r"【(.+?)】", raw):
            before = re.sub(r"[【】]", "", raw[:m.start()])
            frac = len(before) / n
            out.append(dict(word=m.group(1), t=round(t0 + c["t0"] + frac * (c["t1"] - c["t0"]), 3),
                            t_end=round(t0 + c["t0"] + (len(before) + len(m.group(1))) / n * (c["t1"] - c["t0"]), 3)))
    return out


def main():
    meta = json.load(open(f"{BUILD}/voice.json"))
    segs = meta["segments"]
    t = LEAD_IN
    track = []
    timeline_segs = []
    for s in segs:
        sr, x = read_wav(f"{BUILD}/voice/{s['id']}.wav")
        x = resample_poly(x, SR, sr).astype(np.float32)
        start = t
        end = start + len(x) / SR
        track.append((start, x))
        chunks = [dict(text=c["text"], t0=round(start + c["t0"], 3), t1=round(start + c["t1"], 3)) for c in s["chunks"]]
        timeline_segs.append(dict(id=s["id"], scene=s["scene"], text=plain(s["text"]), raw=s["text"],
                                  t0=round(start, 3), t1=round(end, 3), chunks=chunks,
                                  keywords=keyword_times(s["text"], start, end, s["chunks"])))
        t = end + s["pause"]
    total = t + TAIL

    # scenes: from first line start (or 0) to next scene start
    order = [k for k, _, _ in SCENES]
    info = {k: dict(year=y, mood=m) for k, y, m in SCENES}
    scenes = []
    for k in order:
        ss = [x for x in timeline_segs if x["scene"] == k]
        if not ss:
            continue
        scenes.append(dict(key=k, t0=ss[0]["t0"], year=info[k]["year"], mood=info[k]["mood"]))
    scenes[0]["t0"] = 0.0
    for i, sc in enumerate(scenes):
        sc["t1"] = scenes[i + 1]["t0"] if i + 1 < len(scenes) else total
        # let each scene start slightly before its first word so the cut lands on the breath
        if i > 0:
            sc["t0"] = round(max(scenes[i - 1]["t0"] + 0.5, sc["t0"] - 0.25), 3)
            scenes[i - 1]["t1"] = sc["t0"]

    n = int(total * SR) + SR
    voice = np.zeros(n, np.float32)
    for start, x in track:
        i = int(start * SR)
        voice[i:i + len(x)] += x
    voice = voice[:int(total * SR)]
    with wave.open(f"{BUILD}/voice_track.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(voice, -1, 1) * 32767).astype(np.int16).tobytes())

    json.dump(dict(duration=round(total, 3), fps=30, segments=timeline_segs, scenes=scenes),
              open(f"{BUILD}/timeline.json", "w"), ensure_ascii=False, indent=1)
    for sc in scenes:
        print(f"{sc['key']:12s} {sc['t0']:7.2f} → {sc['t1']:7.2f}  ({sc['t1'] - sc['t0']:5.1f}s) {sc['mood']}")
    print(f"total {total:.2f}s")


if __name__ == "__main__":
    main()
