"""Synthesize every narration line, trim silence, QA it with ASR, and find
the pauses inside each line so subtitle chunks can be timed to the audio.

Output: build/voice/<id>.wav (24 kHz mono) and build/voice.json
"""
import json, os, re, sys, difflib
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from script import SEGMENTS, plain, say_text
from kokoro_tts import write_wav

VOICE = 62        # Kokoro v1.1-zh 男声，实测吐字最清楚、语调起伏最大
SPEED = 1.12
RETRY_SPEEDS = [1.08, 1.04, 1.16]
BUILD = os.path.join(os.path.dirname(__file__), "..", "build")


def trim(sr, x, thr=0.008, pad=0.03):
    env = np.abs(x)
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * sr))
    b = min(len(x), idx[-1] + int(pad * sr))
    return x[a:b]


def pauses(sr, x, min_gap=0.07):
    """Return [(start, end)] of silent gaps inside the clip (seconds)."""
    hop = int(sr * 0.01)
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    quiet = rms < 0.012
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_gap and i > 0 and j < len(quiet):
                gaps.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return gaps


def chunk(text, maxlen=15):
    """Split a line into subtitle chunks at punctuation; keeps 【】 marks."""
    parts = re.split(r"(?<=[，。：；？！、])", text)
    parts = [p for p in parts if p.strip()]
    out, cur = [], ""
    for p in parts:
        if cur and len(plain(cur + p)) > maxlen:
            out.append(cur); cur = p
        else:
            cur += p
    if cur:
        out.append(cur)
    # hard-wrap anything still too long
    final = []
    for c in out:
        while len(plain(c)) > maxlen + 4:
            k = maxlen
            # don't cut inside 【】
            s = c[:k]
            if s.count("【") > s.count("】"):
                k = c.index("】", k) + 1
            final.append(c[:k]); c = c[k:]
        final.append(c)
    return final


def line_item(sid, scene, text, pause, sr, x):
    """Metadata for one narration line: duration + subtitle-chunk timings.
    Chunks are timed by character count, then snapped to the real pauses in the audio."""
    dur = len(x) / sr
    chunks = chunk(text)
    gaps = pauses(sr, x)
    weights = [len(re.sub(r"[，。：；？！、“”《》·【】\s]", "", c)) + 0.6 for c in chunks]
    cum = np.cumsum(weights) / sum(weights) * dur
    bounds = [0.0]
    for b in cum[:-1]:
        best = min(gaps, key=lambda g: abs((g[0] + g[1]) / 2 - b), default=None)
        if best and abs((best[0] + best[1]) / 2 - b) < 0.9:
            b = (best[0] + best[1]) / 2
        bounds.append(float(b))
    bounds.append(dur)
    bounds = sorted(bounds)
    return dict(id=sid, scene=scene, text=text, pause=pause, dur=round(dur, 3),
                chunks=[dict(text=c, t0=round(bounds[i], 3), t1=round(bounds[i + 1], 3))
                        for i, c in enumerate(chunks)])


def main():
    from kokoro_tts import synth
    os.makedirs(f"{BUILD}/voice", exist_ok=True)
    qa = "--qa" in sys.argv
    if qa:
        from asr_check import transcribe
    meta = []
    for sid, scene, text, pause in SEGMENTS:
        path = f"{BUILD}/voice/{sid}.wav"
        ref = re.sub(r"[^\w]", "", plain(text))
        best = None
        # 先用默认语速；ASR 听写不达标时换几档语速重试，取听得最清楚的一版
        for speed in ([SPEED] + RETRY_SPEEDS if qa else [SPEED]):
            sr, x = synth(say_text(text), VOICE, speed)
            x = trim(sr, x)
            x = x / (np.max(np.abs(x)) + 1e-9) * 0.89   # gentle per-line peak normalisation
            write_wav(path, sr, x)
            score, heard = 1.0, ""
            if qa:
                heard = transcribe(path).text
                score = difflib.SequenceMatcher(None, ref, re.sub(r"[^\w]", "", heard)).ratio()
            if best is None or score > best[0] + 0.02:
                best = (score, heard, speed, sr, x)
            if score >= 0.93:
                break
        score, heard, speed, sr, x = best
        write_wav(path, sr, x)
        item = line_item(sid, scene, text, pause, sr, x)
        dur = item["dur"]
        item["speed"] = speed
        if qa:
            item["asr"] = heard
            item["asr_ratio"] = round(score, 3)
        meta.append(item)
        print(f"{sid:3s} {dur:5.2f}s x{speed} {item.get('asr_ratio', '')} {plain(text)}"
              + (f"\n      heard: {item['asr']}" if qa and item['asr_ratio'] < 0.9 else ""))
    json.dump(dict(sr=sr, segments=meta), open(f"{BUILD}/voice.json", "w"), ensure_ascii=False, indent=1)
    tot = sum(m["dur"] + m["pause"] for m in meta)
    print(f"speech+pauses: {tot:.1f}s")


if __name__ == "__main__":
    main()
