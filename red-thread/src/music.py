"""Original score + sound effects for 《红线算法》, synthesised from scratch and timed to the film.

Reads build/timeline.json (scenes) and build/cues.json (sound-effect cues written
by the renderer), writes build/music.wav and build/sfx.wav (48 kHz stereo).
Everything is generated here, so there is nothing to clear for copyright.
"""
import json, os
from functools import lru_cache
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve

SR = 48000
HERE = os.path.dirname(__file__)
BUILD = os.path.join(HERE, "..", "build")
RNG = np.random.default_rng(1962)

TL = json.load(open(f"{BUILD}/timeline.json"))
CUES = json.load(open(f"{BUILD}/cues.json"))
DUR = TL["duration"] + 0.5
N = int(DUR * SR)
SEG = {s["id"]: s for s in TL["segments"]}

BPM = 92
SECTION_GAIN = {"night": 1.1, "think": 0.9, "tender": 1.1, "domino": 1.0}
BEAT = 60 / BPM


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(n):
    return np.arange(n) / SR


def lp(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def env_adsr(n, a=0.005, d=0.1, s=0.7, r=0.2):
    t = tt(n); dur = n / SR
    e = np.ones(n) * s
    e = np.where(t < a, t / max(a, 1e-4), e)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    rel_start = max(a + d, dur - r)
    e = np.where(t >= rel_start, e * np.clip(1 - (t - rel_start) / max(r, 1e-4), 0, 1), e)
    return e


# ---------------------------------------------------------------- instruments (cached by pitch/duration)
@lru_cache(maxsize=None)
def piano(m, dur=2.5):
    f = mtof(m); n = int(dur * SR); t = tt(n)
    out = np.zeros(n)
    B = 0.00035
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 16000: break
        amp = 1 / k ** 1.25 * (1.0 if k > 1 else 1.2)
        dec = np.exp(-t * (0.9 + 0.55 * k) * (1 + (m - 60) / 60))
        out += amp * dec * (np.sin(2 * np.pi * fk * t) + 0.5 * np.sin(2 * np.pi * fk * 1.0012 * t + 0.3))
    hammer = lp(RNG.standard_normal(int(0.012 * SR)), 3000) * np.linspace(1, 0, int(0.012 * SR)) * 0.15
    out[:len(hammer)] += hammer
    out *= np.minimum(1, t / 0.004) * np.clip((dur - t) / 0.3, 0, 1)
    return out / 2.4


@lru_cache(maxsize=None)
def bell(m, dur=3.0, ratio=3.5, index=2.2):
    f = mtof(m); n = int(dur * SR); t = tt(n)
    ind = index * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + ind * np.sin(2 * np.pi * f * ratio * t))
    x += 0.3 * np.sin(2 * np.pi * f * 2.01 * t) * np.exp(-t * 2.5)
    return x * np.exp(-t * (1.6 if m > 70 else 0.9)) * np.minimum(1, t / 0.002) * np.clip((dur - t) / 0.2, 0, 1) * 0.5


@lru_cache(maxsize=None)
def pluck(m, dur=1.2, bright=0.5):
    f = mtof(m); n = int(dur * SR)
    p = max(2, int(round(SR / f)))
    buf = RNG.uniform(-1, 1, p)
    buf = lp(buf, 2000 + 6000 * bright, 1) if p > 12 else buf
    out = np.zeros(n)
    y = np.tile(buf, n // p + 2)[:n].copy()
    # Karplus–Strong (vectorised per period)
    out[:p] = buf
    for i in range(p, n, p):
        seg = out[i - p:i]
        nxt = 0.5 * (seg + np.roll(seg, -1)) * 0.996
        out[i:i + p] = nxt[:min(p, n - i)]
    return out * np.clip((dur - tt(n)) / 0.15, 0, 1) * 0.6


@lru_cache(maxsize=None)
def pad_note(m, dur, bright=1500.0, attack=1.2, release=1.4):
    f = mtof(m); n = int(dur * SR); t = tt(n)
    x = np.zeros(n)
    for det in (-0.09, 0.0, 0.08):
        ff = f * 2 ** (det / 12)
        ph = (ff * t + RNG.random()) % 1.0
        x += 2 * ph - 1
    x = lp(x, bright, 2)
    e = np.minimum(1, t / attack) * np.clip((dur - t) / release, 0, 1)
    return x * e * 0.22


@lru_cache(maxsize=None)
def bass_note(m, dur):
    f = mtof(m); n = int(dur * SR); t = tt(n)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return np.tanh(x * 1.2) * env_adsr(n, 0.008, 0.15, 0.6, min(0.25, dur * 0.4)) * 0.7


@lru_cache(maxsize=None)
def kick(strength=1.0):
    n = int(0.45 * SR); t = tt(n)
    f = 45 + 85 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 7) + 0.25 * lp(RNG.standard_normal(n), 3000) * np.exp(-t * 90)
    return np.tanh(x * 1.6 * strength) * 0.9


@lru_cache(maxsize=None)
def snare():
    n = int(0.25 * SR); t = tt(n)
    x = bp(RNG.standard_normal(n), 1200, 7000) * np.exp(-t * 22) + 0.4 * np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30)
    return x * 0.55


@lru_cache(maxsize=None)
def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); t = tt(n)
    return hp(RNG.standard_normal(n), 7500) * np.exp(-t * (14 if open_ else 70)) * 0.25


@lru_cache(maxsize=None)
def staccato(m, dur=0.22):
    f = mtof(m); n = int(dur * SR); t = tt(n)
    ph = (f * t) % 1.0
    x = lp(2 * ph - 1, 900, 2)
    return x * env_adsr(n, 0.01, 0.08, 0.5, 0.08) * 0.5


# ---------------------------------------------------------------- buses
def put(bus, t0, x, gain=1.0, pan=0.0):
    i = int(round(t0 * SR))
    if i >= bus.shape[1] or i + len(x) <= 0:
        return
    a, b = max(0, i), min(bus.shape[1], i + len(x))
    seg = x[a - i:b - i] * gain
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    bus[0, a:b] += seg * l * 1.414
    bus[1, a:b] += seg * r * 1.414



# D 宫五声音阶 (D E F# A B) — the "Chinese" colour comes from the scale and the plucked timbre
CH = {  # chord tables (bass, voicing)
    "D": (38, [54, 57, 62]), "Bm": (35, [54, 59, 62]), "G": (43, [55, 59, 62]), "A": (45, [57, 61, 64]),
    "Em": (40, [55, 59, 64]), "F#m": (42, [57, 61, 66]), "Dadd9": (38, [57, 62, 64, 66]),
}
PENT = [62, 64, 66, 69, 71, 74, 76, 78, 81, 83, 86]
MOTIF = [69, 71, 74, 78, 76]      # the "red thread" motif: A B D F# E


def zheng(m, dur=1.6, bright=0.75):
    """guzheng-ish pluck (Karplus–Strong, bright attack)."""
    return pluck(m, dur, bright)


def arp_notes(chord, pattern):
    b, v = CH[chord]
    pool = [b + 12, v[0], v[1], v[2], v[0] + 12, v[1] + 12, v[2] + 12]
    return [pool[i % len(pool)] for i in pattern]


def section(kind, t0, t1, ctx):
    """Render one musical section into a fresh stereo buffer covering [t0, t1 + tail]."""
    tail = 3.0
    n = int((t1 - t0 + tail) * SR)
    bus = np.zeros((2, n))
    L = t1 - t0
    beats = int(L / BEAT) + 1
    P = lambda tb, x, g=1.0, pan=0.0: put(bus, tb, x, g, pan)

    def chords_for(prog, per):
        return [(i * per, prog[i % len(prog)]) for i in range(int(beats / per) + 1)]

    if kind == "pulse":          # hook: light pizzicato groove that stops dead on the switch
        prog = ["D", "Bm", "G", "A"]
        sw = ctx["switch"] - t0
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            P(tb, pad_note(b + 12, 4 * BEAT + 0.6, 900, 0.3, 0.6), 0.35)
            for k in range(8):
                ts = tb + k * BEAT / 2
                if abs(ts - sw) < 0.35: continue
                nt = arp_notes(ch, [0, 2, 4, 2, 5, 2, 4, 3])[k]
                P(ts, zheng(nt + 12, 0.7, 0.8), 0.18, -0.5 + (k % 4) * 0.33)
                if k % 2 == 1: P(ts, hat(), 0.22, 0.35)
            for k in range(4):
                if abs(tb + k * BEAT - sw) > 0.35: P(tb + k * BEAT, kick(0.6), 0.32 if k % 2 == 0 else 0.18)
    elif kind == "title":
        P(0, pad_note(50, 4.5, 1300, 0.05, 2.5), 0.9); P(0, pad_note(57, 4.5, 1300, 0.05, 2.5), 0.7); P(0, pad_note(66, 4.5, 1600, 0.05, 2.5), 0.5)
        for i, m in enumerate(MOTIF):
            P(0.3 + i * 0.28, zheng(m + 12, 2.5, 0.85), 0.42, -0.3 + 0.15 * i)
        P(0.3, bell(86, 3.0), 0.2)
    elif kind in ("night", "tender"):   # moonlit: drone + sparse plucks, a slow gliss now and then
        P(0, pad_note(38, L + 2, 500, 2.0, 2.0), 0.6); P(0, pad_note(45, L + 2, 700, 2.0, 2.0), 0.4)
        P(0, pad_note(62, L + 2, 900, 2.5, 2.0), 0.14 if kind == "night" else 0.2)
        tb = 0.4
        i = 0
        while tb < L:
            m = MOTIF[i % len(MOTIF)] if i % 6 < 5 else int(RNG.choice(PENT))
            P(tb, zheng(m + (0 if kind == "night" else -12 + 12), 2.4, 0.7), 0.24, RNG.uniform(-0.5, 0.5))
            if i % 5 == 4:
                for k, mm in enumerate([74, 76, 78, 81, 83]):
                    P(tb + 0.4 + k * 0.06, zheng(mm + 12, 0.9, 0.9), 0.07, 0.4)
            tb += BEAT * (1.5 if i % 3 else 2.0)
            i += 1
    elif kind == "play":         # light walking plucks
        prog = ["D", "G", "Bm", "A"]
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            P(tb, bass_note(b, BEAT * 0.9), 0.3); P(tb + 2 * BEAT, bass_note(b + 7, BEAT * 0.9), 0.24)
            for m in v:
                P(tb, pad_note(m, 4 * BEAT + 0.8, 1300, 0.4, 0.8), 0.13)
            for k in range(8):
                if k in (3, 7) and RNG.random() < 0.5: continue
                nt = arp_notes(ch, [1, 3, 2, 4, 3, 5, 4, 2])[k]
                P(tb + k * BEAT / 2, zheng(nt + 12, 0.8, 0.75), 0.15, -0.4 + 0.8 * (k % 2))
            for k in range(4):
                P(tb + k * BEAT + BEAT / 2, hat(), 0.15, 0.4)
    elif kind == "think":        # rules: a clock-like ostinato, warm pad
        prog = ["Bm", "G", "D", "A"]
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            for m in v:
                P(tb, pad_note(m, 4 * BEAT + 1.0, 1100, 0.8, 1.0), 0.18)
            P(tb, pad_note(b + 12, 4 * BEAT + 1.0, 700, 0.8, 1.0), 0.3)
            for k in range(8):
                P(tb + k * BEAT / 2, zheng(arp_notes(ch, [4, 2, 3, 2, 4, 2, 5, 2])[k] + 12, 0.5, 0.6), 0.1, 0.3 - 0.6 * (k % 2))
            for k in range(4):
                P(tb + k * BEAT, hat(), 0.25, 0.5)
    elif kind == "domino":       # the algorithm run: builds round by round
        prog = ["D", "Bm", "G", "A"]
        rounds = ctx["rounds"]
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            inten = sum(1 for r in rounds if r - t0 <= tb) / max(1, len(rounds))
            P(tb, bass_note(b, 4 * BEAT * 0.9), 0.3 + 0.1 * inten)
            for m in v:
                P(tb, pad_note(m + 12, 4 * BEAT + 1, 1200 + 1600 * inten, 0.4, 1.0), 0.15 + 0.06 * inten)
            for k in range(16):
                if k % 2 == 1 and inten < 0.5: continue
                nt = arp_notes(ch, [0, 2, 4, 6, 4, 2, 5, 3])[k % 8]
                P(tb + k * BEAT / 4, zheng(nt + 12, 0.5, 0.6 + 0.3 * inten), 0.08 + 0.05 * inten, -0.5 + (k % 4) * 0.33)
            for k in range(4):
                P(tb + k * BEAT, kick(0.6 + 0.3 * inten), 0.22 + 0.2 * inten if k % 2 == 0 else 0.12 * inten)
                if k % 2 == 1 and inten > 0.4: P(tb + k * BEAT, snare(), 0.18 * inten, 0.1)
    elif kind in ("reveal", "reveal2"):   # resolution: open chord + motif
        P(0, bass_note(38, min(L, 6.0)), 0.4)
        for m in CH["Dadd9"][1]:
            P(0, pad_note(m, L + 2, 1800, 0.3, 2.0), 0.24)
        for i, m in enumerate(MOTIF):
            P(0.2 + i * 0.3, zheng(m + 12, 2.0, 0.85), 0.25, -0.3 + 0.15 * i)
        prog = ["G", "D", "A", "D"] if kind == "reveal" else ["Bm", "G", "D", "A"]
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT + 2.0
            if tb > L: break
            b, v = CH[ch]
            P(tb, bass_note(b, 4 * BEAT * 0.9), 0.28)
            for k in range(8):
                P(tb + k * BEAT / 2, zheng(arp_notes(ch, [0, 2, 4, 5, 6, 5, 4, 2])[k] + 12, 0.8, 0.8), 0.13, -0.4 + 0.8 * (k % 2))
            for k in range(4):
                P(tb + k * BEAT, kick(0.7), 0.25 if k % 2 == 0 else 0.0)
                if k % 2 == 1: P(tb + k * BEAT, snare(), 0.14, 0.1)
    elif kind == "warm":
        prog = ["G", "D", "Em", "A"]
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            P(tb, bass_note(b, 4 * BEAT * 0.95), 0.3)
            for m in v + [v[2] + 12]:
                P(tb, pad_note(m + 12, 4 * BEAT + 1.5, 1800, 0.8, 1.5), 0.15)
            for k in range(8):
                P(tb + k * BEAT / 2, piano(arp_notes(ch, [0, 2, 4, 5, 6, 5, 4, 2])[k] + 12, 1.8), 0.12, -0.3 + 0.6 * (k % 2))
                if k % 2 == 1: P(tb + k * BEAT / 2, hat(), 0.14, 0.4)
    elif kind == "coda":
        prog = ["G", "A", "F#m", "Bm", "G", "A", "D", "D"]
        heart = ctx["like"] - t0
        for cb, ch in chords_for(prog, 4):
            tb = cb * BEAT
            if tb > L: break
            b, v = CH[ch]
            P(tb, bass_note(b, 4 * BEAT * 0.95), 0.32)
            for m in v:
                P(tb, pad_note(m + 12, 4 * BEAT + 1.5, 1600, 0.8, 1.5), 0.18)
            for k in range(8):
                P(tb + k * BEAT / 2, zheng(arp_notes(ch, [0, 2, 4, 5, 6, 5, 4, 2])[k] + 12, 1.0, 0.8), 0.15, -0.4 + 0.8 * (k % 2))
        if 0 < heart < L:
            for i, m in enumerate(MOTIF + [86]):
                P(heart + i * 0.14, zheng(m + 12, 2.5, 0.9), 0.3, -0.4 + 0.15 * i)
            for m in CH["Dadd9"][1]:
                P(heart, pad_note(m + 12, max(1.0, L - heart + 3), 2000, 0.3, 3.0), 0.22)
            P(heart, bass_note(38, 4.0), 0.45)
    return bus


# ---------------------------------------------------------------- sound effects
def noise(n):
    return RNG.standard_normal(n)


def zheng_sfx(m):
    return pluck(m, 1.2, 0.9)


def sfx(kind):
    if kind == "string":         # a thread being pulled taut: soft gliss up
        n = int(0.8 * SR); t = tt(n); u = t / 0.8
        f = mtof(74) * 2 ** (u * 7 / 12)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) ** 1.5 * 0.12
        return x + bp(noise(n), 3000, 9000) * np.sin(np.pi * u) * 0.025
    if kind == "snap":           # thread snapping: bright twang + crack
        n = int(0.6 * SR); t = tt(n)
        tw = np.sin(2 * np.pi * (1200 * np.exp(-t * 18) + 220) * t) * np.exp(-t * 9) * 0.35
        crack = bp(noise(n), 1500, 8000) * np.exp(-t * 70) * 0.7
        return tw + crack
    if kind == "knot":
        return zheng_sfx(81) * 0.7 + zheng_sfx(88) * 0.4
    if kind == "tangle":
        n = int(1.4 * SR); out = np.zeros(n)
        for k in range(12):
            b = pluck(int(RNG.choice([74, 76, 78, 81, 83])), 0.3, 0.9); i = int(RNG.uniform(0, 1.1) * SR); out[i:i + len(b)] += b[:n - i] * 0.25
        return out
    if kind == "think":
        n = int(0.9 * SR); out = np.zeros(n)
        for k, m in enumerate([79, 76]):
            b = bell(m, 0.6, 2.0, 0.6); i = int(k * 0.25 * SR); out[i:i + len(b)] += b[:n - i] * 0.35
        return out
    if kind == "domino":
        n = int(1.4 * SR); out = np.zeros(n)
        for k in range(6):
            m = int(0.06 * SR); i = int(k * 0.11 * SR); tm = tt(m)
            out[i:i + m] += (bp(noise(m), 800, 3000) * np.exp(-tm * 80) + np.sin(2 * np.pi * (300 + 60 * k) * tm) * np.exp(-tm * 50)) * (0.5 + 0.1 * k)
        b = bell(86, 1.2, 2.0, 1.0); out[int(0.7 * SR):int(0.7 * SR) + len(b)] += b[:n - int(0.7 * SR)] * 0.4
        return out * 0.6
    if kind == "shuffle":
        n = int(1.0 * SR); out = np.zeros(n)
        for k in range(8):
            m = int(0.05 * SR); i = int(k * 0.1 * SR)
            out[i:i + m] += bp(noise(m), 2000, 7000) * np.exp(-tt(m) * 60) * 0.3
        return out
    if kind == "whoosh":
        n = int(0.7 * SR); t = tt(n); x = noise(n)
        c = 400 + 3000 * np.sin(np.pi * t / 0.7) ** 2
        out = np.zeros(n)
        for i in range(0, n, 2400):
            out[i:i + 2400] = bp(x[i:i + 2400], max(100, c[i] * 0.6), min(20000, c[i] * 1.6), 1)
        return out * np.sin(np.pi * t / 0.7) ** 2 * 0.35
    if kind == "stamp":
        n = int(0.6 * SR); t = tt(n)
        thud = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * np.exp(-t * 14)
        clack = bp(noise(n), 600, 3500) * np.exp(-t * 45)
        return np.tanh((thud * 1.4 + clack * 0.7) * 1.3) * 0.9
    if kind == "paper":
        n = int(0.32 * SR); t = tt(n)
        x = bp(noise(n), 1800, 8000) * (0.4 + 0.6 * np.abs(np.sin(t * 90))) * np.sin(np.pi * t / 0.32)
        return x * 0.25
    if kind == "pop":
        n = int(0.09 * SR); t = tt(n)
        return np.sin(2 * np.pi * (500 + 500 * t / 0.09) * t) * np.exp(-t * 40) * 0.35
    if kind == "click":
        n = int(0.03 * SR); t = tt(n)
        return bp(noise(n), 1500, 5000) * np.exp(-t * 200) * 0.6
    if kind == "tick":
        n = int(0.05 * SR); t = tt(n)
        return np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 120) * 0.3
    if kind == "error":
        n = int(0.26 * SR); t = tt(n)
        sq = np.sign(np.sin(2 * np.pi * 196 * t)) * (t < 0.11) + np.sign(np.sin(2 * np.pi * 185 * t)) * (t >= 0.13)
        return lp(sq, 1800) * 0.12
    if kind == "ding":
        return (bell(88, 2.0, 2.0, 1.0) + 0.7 * bell(95, 2.0, 2.0, 0.8)) * 0.55
    if kind == "fire":
        n = int(1.2 * SR); t = tt(n)
        zap = np.sin(2 * np.pi * (880 + 900 * np.exp(-t * 25)) * t) * np.exp(-t * 9) * 0.25
        return zap + bell(81, 1.2, 3.5, 1.4) * 0.6
    if kind == "dud":
        n = int(0.3 * SR); t = tt(n)
        return np.sin(2 * np.pi * 140 * t) * np.exp(-t * 20) * 0.4
    if kind == "freeze":
        n = int(0.9 * SR); t = tt(n)
        f = 900 * np.exp(-t * 3.5) + 60
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3) * 0.25 + lp(noise(n), 800) * np.exp(-t * 6) * 0.1
    if kind == "type":
        n = int(2.8 * SR); out = np.zeros(n); tcur = 0.0
        while tcur < 2.6:
            i = int(tcur * SR); m = int(0.025 * SR)
            out[i:i + m] += bp(noise(m), 2000, 6000) * np.exp(-tt(m) * 250) * RNG.uniform(0.4, 0.8)
            tcur += RNG.uniform(0.06, 0.13)
        return out * 0.5
    if kind == "marker":
        n = int(0.5 * SR); t = tt(n)
        return bp(noise(n), 3000, 7000) * np.sin(np.pi * t / 0.5) * 0.12
    if kind == "riser":
        n = int(2.2 * SR); t = tt(n); u = t / 2.2
        return (bp(noise(n), 500, 7000) * u ** 2 * 0.2 + np.sin(2 * np.pi * np.cumsum(200 + 900 * u ** 2) / SR) * u ** 2 * 0.12)
    if kind == "fall":
        n = int(1.8 * SR); t = tt(n)
        f = 700 * np.exp(-t * 1.6) + 70
        return np.sin(2 * np.pi * np.cumsum(f) / SR + 3 * np.sin(2 * np.pi * 5 * t)) * np.exp(-t * 1.2) * 0.22
    if kind == "bell":
        return bell(57, 5.0, 2.76, 1.5) * 0.7
    if kind == "roll":
        n = int(2.5 * SR); t = tt(n)
        return lp(noise(n), 300) * (0.6 + 0.4 * np.sin(t * 30)) * np.exp(-t * 1.0) * 0.5
    if kind in ("sweepUp", "sweepDown"):
        n = int(0.9 * SR); t = tt(n); u = t / 0.9
        f = (300 + 900 * u) if kind == "sweepUp" else (1200 - 900 * u)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * u) * 0.12
    if kind == "scan":
        n = int(3.5 * SR); out = np.zeros(n)
        for k in range(0, 28):
            i = int(k * 0.12 * SR); m = int(0.02 * SR)
            out[i:i + m] += np.sin(2 * np.pi * 3200 * tt(m)) * np.exp(-tt(m) * 300)
        return out * 0.15
    if kind == "flock":
        n = int(1.6 * SR); out = np.zeros(n)
        for k in range(14):
            i = int(RNG.uniform(0, 1.4) * SR); m = int(0.06 * SR)
            out[i:i + m] += np.sin(2 * np.pi * RNG.uniform(500, 900) * tt(m)) * np.exp(-tt(m) * 60)
        return out * 0.12
    if kind == "swell":
        n = int(2.0 * SR); t = tt(n); u = t / 2.0
        x = sum(pad_note(m, 2.0, 2500, 1.9, 0.05) for m in (57, 64, 69, 76))
        return x * u ** 1.5 * 1.4
    if kind == "shimmer":
        n = int(2.0 * SR); out = np.zeros(n)
        for k, m in enumerate([81, 84, 88, 91, 93, 96]):
            b = bell(m, 1.6, 3.0, 0.8); i = int(k * 0.11 * SR); out[i:i + len(b)] += b[:n - i]
        return out * 0.28
    if kind == "build":
        n = int(2.0 * SR); out = np.zeros(n)
        for k, m in enumerate([45, 48, 52, 55, 57, 60, 64, 67]):
            b = pluck(m + 12, 0.5, 0.6); i = int(k * 0.18 * SR); out[i:i + len(b)] += b[:n - i]
        return out * 0.35
    if kind == "fans":
        n = int(4.5 * SR); t = tt(n)
        return lp(noise(n), 700) * (0.7 + 0.3 * np.sin(2 * np.pi * 37 * t)) * np.minimum(1, t / 0.8) * np.clip((4.5 - t) / 1.0, 0, 1) * 0.12
    if kind == "rise":
        n = int(0.8 * SR); t = tt(n); u = t / 0.8
        return np.sin(2 * np.pi * np.cumsum(300 + 500 * u) / SR) * np.sin(np.pi * u) * 0.1
    if kind == "drop":
        n = int(1.0 * SR); t = tt(n)
        return np.sin(2 * np.pi * np.cumsum(500 * np.exp(-t * 4) + 50) / SR) * np.exp(-t * 3) * 0.35
    if kind in ("impact", "boom"):
        big = kind == "impact"
        n = int((2.5 if big else 1.8) * SR); t = tt(n)
        sub = np.sin(2 * np.pi * np.cumsum(30 + 70 * np.exp(-t * 12)) / SR) * np.exp(-t * (1.6 if big else 2.4))
        crash = hp(noise(n), 3000) * np.exp(-t * (2.5 if big else 6)) * (0.35 if big else 0.12)
        body = lp(noise(n), 400) * np.exp(-t * 8) * 0.5
        return np.tanh((sub * 1.3 + body) * 1.2) * 0.85 + crash
    if kind == "bid":
        n = int(0.08 * SR); t = tt(n)
        return bp(noise(n), 500, 1600) * np.exp(-t * 70) * 0.5
    if kind == "gavel":
        n = int(0.9 * SR); out = np.zeros(n)
        for k, g in ((0, 1.0), (0.22, 0.7)):
            i = int(k * SR); m = int(0.2 * SR); tm = tt(m)
            out[i:i + m] += (bp(noise(m), 300, 1400) * np.exp(-tm * 40) + np.sin(2 * np.pi * 160 * tm) * np.exp(-tm * 30)) * g
        return out * 0.7
    if kind == "stone":
        n = int(0.12 * SR); t = tt(n)
        return (bp(noise(n), 2500, 6000) * np.exp(-t * 160) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 90) * 0.4) * 0.5
    if kind == "chime":
        n = int(4.0 * SR); out = np.zeros(n)
        for k, m in enumerate([84, 88, 91, 96]):
            b = bell(m, 3.5, 2.0, 1.2); i = int(k * 0.16 * SR); out[i:i + len(b)] += b[:n - i]
        return out * 0.45
    if kind == "phone":
        n = int(1.6 * SR); t = tt(n)
        tone = (np.sin(2 * np.pi * 440 * t) + np.sin(2 * np.pi * 480 * t)) * (np.sin(2 * np.pi * 20 * t) > 0)
        gate = ((t % 0.8) < 0.5).astype(float)
        return lp(tone * gate, 3000) * 0.08
    if kind == "low":
        n = int(2.0 * SR); t = tt(n)
        return np.sin(2 * np.pi * 55 * t) * np.exp(-t * 1.5) * 0.5 + pad_note(45, 2.0, 400, 0.05, 1.5) * 0.6
    if kind == "heart":
        n = int(3.0 * SR); t = tt(n)
        thump = np.sin(2 * np.pi * (60 + 40 * np.exp(-t * 20)) * t) * np.exp(-t * 8) * 0.8
        pop = np.sin(2 * np.pi * (600 + 700 * np.minimum(1, t / 0.08)) * t) * np.exp(-t * 25) * 0.3
        out = thump + pop
        for k, m in enumerate([84, 88, 91]):
            b = bell(m, 2.5, 2.0, 1.0); i = int((0.05 + k * 0.08) * SR); out[i:i + len(b)] += b[:n - i] * 0.4
        return out
    raise ValueError(kind)


def reverb_ir(seconds=2.6, seed=0, damp=3500):
    r = np.random.default_rng(seed)
    n = int(seconds * SR); t = tt(n)
    ir = r.standard_normal(n) * np.exp(-t * 6.9 / seconds)
    ir = lp(ir, damp, 1)
    ir[:int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    return ir / np.sqrt(np.sum(ir ** 2))


def add_reverb(bus, wet=0.25, seconds=2.6):
    out = bus.copy()
    for c in range(2):
        out[c] += wet * fftconvolve(bus[c], reverb_ir(seconds, c + 1), mode="full")[:bus.shape[1]]
    return out


def main():
    scenes = TL["scenes"]
    secs = []
    for sc in scenes:
        if secs and secs[-1]["mood"] == sc["mood"]:
            secs[-1]["t1"] = sc["t1"]
        else:
            secs.append(dict(mood=sc["mood"], t0=sc["t0"], t1=sc["t1"]))
    cue_t = lambda typ: [c["t"] for c in CUES["cues"] if c["type"] == typ]
    kw = lambda sid, i=0: SEG[sid]["keywords"][i]["t"]
    rounds = [SEG[s]["t0"] for s in ("E1", "E4", "E7", "E8")]
    ctx = dict(switch=kw("H2") + 0.1, rounds=rounds, like=[c for c in cue_t("heart")][-1])
    music = np.zeros((2, N))
    for i, s in enumerate(secs):
        kind = s["mood"]
        t0, t1 = s["t0"], s["t1"]
        buf = section(kind, t0, t1, ctx)
        n = buf.shape[1]
        t = t0 + tt(n)
        fin = np.clip((t - (t0 - 0.05)) / 0.5, 0, 1) if i > 0 else np.ones(n)
        fout = np.clip(1 - (t - t1) / 1.4, 0, 1)
        buf *= fin * fout * SECTION_GAIN.get(kind, 1.0)
        put(music, t0, buf[0] / 1.414, 1.0, -1.0)
        put(music, t0, buf[1] / 1.414, 1.0, 1.0)
        print(f"{kind:8s} {t0:7.2f}–{t1:7.2f}")
    music = add_reverb(music, 0.3)

    fx = np.zeros((2, N))
    for c in CUES["cues"]:
        x = sfx(c["type"])
        pan = {"paper": -0.2, "pop": 0.15, "tick": 0.2, "string": RNG.uniform(-0.3, 0.3)}.get(c["type"], 0.0)
        put(fx, c["t"], x * 0.5, c["gain"], pan)
    fx = add_reverb(fx, 0.18, 1.6)

    def save(name, x):
        x = np.clip(x, -1, 1)
        import wave
        with wave.open(f"{BUILD}/{name}", "wb") as wv:
            wv.setnchannels(2); wv.setsampwidth(2); wv.setframerate(SR)
            wv.writeframes((x.T * 32767).astype(np.int16).tobytes())
    pk = max(np.max(np.abs(music)), 1e-9)
    save("music.wav", music / pk * 0.8)
    pk2 = max(np.max(np.abs(fx)), 1e-9)
    save("sfx.wav", fx / pk2 * 0.8)
    print("music peak", pk, "sfx peak", pk2, "cues", len(CUES["cues"]))


if __name__ == "__main__":
    main()
