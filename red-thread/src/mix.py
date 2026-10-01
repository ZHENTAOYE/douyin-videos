"""Final audio mix: narration on top, score ducked under the voice, sound effects,
then EBU R128 loudness normalisation to -14 LUFS (short-video platform norm)."""
import os, subprocess, wave, json
import numpy as np
from scipy.signal import butter, sosfilt

BUILD = os.path.join(os.path.dirname(__file__), "..", "build")
SR = 48000


def load(p):
    with wave.open(p) as w:
        c = w.getnchannels(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    x = x.reshape(-1, c).T
    return np.vstack([x, x]) if c == 1 else x


def db(x):
    return 10 ** (x / 20)


def rms(x):
    return np.sqrt(np.mean(x ** 2) + 1e-12)


def main():
    v, m, f = load(f"{BUILD}/voice_track.wav"), load(f"{BUILD}/music.wav"), load(f"{BUILD}/sfx.wav")
    n = max(v.shape[1], m.shape[1], f.shape[1])
    pad = lambda x: np.pad(x, ((0, 0), (0, n - x.shape[1])))
    v, m, f = pad(v), pad(m), pad(f)
    # voice: gentle high-pass + a touch of presence
    sos = butter(2, 75, "high", fs=SR, output="sos")
    v = sosfilt(sos, v, axis=1)
    v += 0.18 * sosfilt(butter(2, [2500, 6000], "band", fs=SR, output="sos"), v, axis=1)
    speech = np.abs(v[0]) > 0.01
    vr = rms(v[0][speech])
    # duck envelope from the voice (attack 40 ms, release 450 ms)
    hop = 480
    e = np.array([rms(v[0, i:i + hop]) for i in range(0, n, hop)])
    act = np.clip((20 * np.log10(e + 1e-9) + 45) / 15, 0, 1)
    sm = np.zeros_like(act); a_up, a_dn = np.exp(-hop / SR / 0.04), np.exp(-hop / SR / 0.45)
    for i in range(1, len(act)):
        k = a_up if act[i] > sm[i - 1] else a_dn
        sm[i] = k * sm[i - 1] + (1 - k) * act[i]
    duck = np.interp(np.arange(n), np.arange(len(sm)) * hop, sm)
    music_lvl = db(-13) * vr / rms(m[0][np.abs(m[0]) > 1e-4])
    m = m * music_lvl * (1 - (1 - db(-6)) * duck)
    f = f * (db(-4) * np.max(np.abs(v)) / (np.max(np.abs(f)) + 1e-9))
    mix = v + m + f
    mix = np.tanh(mix * 0.95) / 0.95          # soft safety limiter
    with wave.open(f"{BUILD}/mix_raw.wav", "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype(np.int16).tobytes())
    # two-pass loudnorm to -14 LUFS / -1.5 dBTP
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", f"{BUILD}/mix_raw.wav", "-af",
                        "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    js = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    flt = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:"
           f"measured_LRA={js['input_lra']}:measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", f"{BUILD}/mix_raw.wav", "-af", flt,
                    "-ar", "48000", f"{BUILD}/mix.wav"], check=True)
    print("input loudness", js["input_i"], "LUFS → -14")


if __name__ == "__main__":
    main()
