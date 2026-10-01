"""Use narration exported from an external dubbing tool (e.g. 冬瓜配音) instead of the
built-in TTS.

    python3 import_voice.py 旁白.mp3                 # one file with the whole script
    python3 import_voice.py 第1段.mp3 第2段.mp3 ...   # or several files, in script order

The audio is split into speech regions at silences, every region is transcribed
with SenseVoice, and a dynamic-programming alignment assigns consecutive regions
to the script lines. Each line is written to build/voice/<id>.wav with the same
metadata tts.py produces, so timeline.py / music.py / the renderer re-time the
whole film to the new voice automatically.
"""
import argparse, difflib, json, os, re, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from script import SEGMENTS, plain
from tts import line_item, trim
from kokoro_tts import write_wav

SR = 24000
BUILD = os.path.join(os.path.dirname(__file__), "..", "build")


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def norm(s):
    s = plain(s).lower()
    return re.sub(r"[^\w]", "", s)


def regions(x, min_sil=0.12, min_len=0.12):
    """Speech regions [(start, end)] in seconds, split at silences >= min_sil."""
    hop = int(SR * 0.01)
    rms = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    ref = np.percentile(rms, 99)
    speech = 20 * np.log10(rms / ref) > -36
    out, i, n = [], 0, len(speech)
    while i < n:
        if speech[i]:
            j = i
            while j < n:
                if not speech[j]:
                    k = j
                    while k < n and not speech[k]:
                        k += 1
                    if (k - j) * 0.01 >= min_sil or k == n:
                        break
                    j = k
                else:
                    j += 1
            out.append([i * 0.01, j * 0.01]); i = j
        else:
            i += 1
    return [r for r in out if r[1] - r[0] >= min_len]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out", default=BUILD)
    a = ap.parse_args()
    from asr_check import rec

    parts = []
    for f in a.files:
        parts += [decode(f), np.zeros(int(0.6 * SR), np.float32)]
    x = np.concatenate(parts)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.89
    regs = regions(x)
    print(f"audio {len(x) / SR:.1f}s, {len(regs)} speech regions")

    texts = []
    for r0, r1 in regs:
        a0, a1 = max(0, int((r0 - 0.05) * SR)), min(len(x), int((r1 + 0.05) * SR))
        st = rec.create_stream(); st.accept_waveform(SR, x[a0:a1]); rec.decode_stream(st)
        texts.append(norm(st.result.text))

    lines = [norm(t) for _, _, t, _ in SEGMENTS]
    L, R, MAXK = len(lines), len(regs), 14
    NEG = -1e9
    dp = np.full((L + 1, R + 1), NEG); dp[0, 0] = 0
    back = {}
    # a line may span several regions; stray regions (breaths, an intro) can be skipped at a cost
    for i in range(1, R + 1):
        # skip region i-1 without assigning it
        for j in range(0, L + 1):
            pen = 0.5 + len(texts[i - 1])
            if dp[j, i - 1] > NEG and dp[j, i - 1] - pen > dp[j, i]:
                dp[j, i] = dp[j, i - 1] - pen; back[(j, i)] = (j, i - 1, None)
        for j in range(1, L + 1):
            tgt = lines[j - 1]
            cat = ""
            for k in range(i - 1, max(-1, i - 1 - MAXK), -1):
                cat = texts[k] + cat
                if len(cat) > len(tgt) * 1.8 + 6:
                    break
                prev = dp[j - 1, k]
                if prev <= NEG:
                    continue
                sim = difflib.SequenceMatcher(None, tgt, cat).ratio()
                sc = prev + sim * (len(tgt) + len(cat)) / 2 - abs(len(cat) - len(tgt)) * 0.3
                if sc > dp[j, i]:
                    dp[j, i] = sc; back[(j, i)] = (j - 1, k, sim)
    # best end: all lines used, any number of trailing regions skipped
    i = int(np.argmax(dp[L])); j = L
    if dp[L, i] <= NEG:
        sys.exit("alignment failed: the audio does not seem to contain the whole script")
    spans = {}
    while j > 0:
        pj, pk, sim = back[(j, i)]
        if sim is not None:
            spans[j - 1] = (pk, i, sim)
        j, i = pj, pk

    os.makedirs(f"{a.out}/voice", exist_ok=True)
    meta, weak = [], []
    for li, (sid, scene, text, pause) in enumerate(SEGMENTS):
        k0, k1, sim = spans[li]
        s0 = max(0, int((regs[k0][0] - 0.04) * SR)); s1 = min(len(x), int((regs[k1 - 1][1] + 0.06) * SR))
        clip = trim(SR, x[s0:s1])
        write_wav(f"{a.out}/voice/{sid}.wav", SR, clip)
        item = line_item(sid, scene, text, pause, SR, clip)
        item["asr"] = "".join(texts[k0:k1]); item["asr_ratio"] = round(sim, 3)
        item["source_span"] = [round(regs[k0][0], 2), round(regs[k1 - 1][1], 2)]
        meta.append(item)
        flag = "  <-- check" if sim < 0.8 else ""
        if sim < 0.8:
            weak.append(sid)
        print(f"{sid:3s} {item['dur']:5.2f}s sim {sim:.2f}  {plain(text)[:28]}{flag}")
    json.dump(dict(sr=SR, source=[os.path.basename(f) for f in a.files], segments=meta),
              open(f"{a.out}/voice.json", "w"), ensure_ascii=False, indent=1)
    print(f"lines: {len(meta)}, weak matches: {weak or 'none'}")


if __name__ == "__main__":
    main()
