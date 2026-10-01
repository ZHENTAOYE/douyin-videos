"""Voice-over generation with automatic best-of-N take selection.

Each narration line is synthesised several times (different speeds / punctuation
variants) with Kokoro v1.1-zh (voice zm_029). Every take is transcribed by
SenseVoice and compared to the script at the pinyin-syllable level (so harmless
homophones such as 他/它 don't count, but wrong tones and stray trailing
syllables like 啊/呀 do). Among the takes with the fewest syllable errors, the
one with the best UTMOS naturalness score wins.

Output: build/vo/<id>.wav (48 kHz mono, trimmed, loudness-matched) and
build/vo/vo.json with durations and take metadata.
"""
import os, sys, json, re
import numpy as np, soundfile as sf, librosa
import pyloudnorm as pyln
from pypinyin import lazy_pinyin, Style

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import MODELS, BUILD
from script_data import ALL_LINES

import sherpa_onnx

SID = 68          # kokoro v1.1-zh speaker index 68 == zm_029
SR_OUT = 48000
SPEEDS = [0.96, 1.0, 1.04]


def kokoro():
    d = f'{MODELS}/kokoro-multi-lang-v1_1'
    cfg = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                model=f'{d}/model.onnx', voices=f'{d}/voices.bin', tokens=f'{d}/tokens.txt',
                data_dir=f'{d}/espeak-ng-data', dict_dir=f'{d}/dict',
                lexicon=f'{d}/lexicon-us-en.txt,{d}/lexicon-zh.txt'),
            num_threads=4),
        rule_fsts=f'{d}/date-zh.fst,{d}/phone-zh.fst,{d}/number-zh.fst',
        max_num_sentences=1)
    return sherpa_onnx.OfflineTts(cfg)


def asr_model():
    import glob
    sv = glob.glob(f'{MODELS}/sherpa-onnx-sense-voice-*')[0]
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=f'{sv}/model.int8.onnx', tokens=f'{sv}/tokens.txt', num_threads=4, use_itn=False, language='zh')


def transcribe(rec, y, sr):
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)
    s = rec.create_stream()
    s.accept_waveform(16000, y16)
    rec.decode_stream(s)
    return s.result.text


def syllables(text):
    text = re.sub(r'[^一-鿿]', '', text)
    return lazy_pinyin(text, style=Style.TONE3, neutral_tone_with_five=True)


def edit_distance(a, b):
    d = np.arange(len(b) + 1)
    for i in range(1, len(a) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(b) + 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
            prev, d[j] = d[j], cur
    return int(d[len(b)])


def syllable_errors(ref, hyp):
    r, h = syllables(ref), syllables(hyp)
    # tone-insensitive pass catches real mispronunciations; tone errors weigh half
    full = edit_distance(r, h)
    base = edit_distance([x.rstrip('012345') for x in r], [x.rstrip('012345') for x in h])
    return base + 0.5 * (full - base)


def utmos_model():
    sys.path.insert(0, f'{MODELS}/../speechmos')
    import torch
    from speechmos.utmos22.strong.model import UTMOS22Strong
    torch.set_num_threads(4)
    m = UTMOS22Strong()
    m.load_state_dict(torch.load(f'{MODELS}/../speechmos/utmos22_strong.pt', map_location='cpu'))
    m.eval()

    def score(y, sr):
        y16 = librosa.resample(y, orig_sr=sr, target_sr=16000).astype(np.float32)
        with torch.no_grad():
            return float(m(torch.from_numpy(y16)[None], 16000)[0])
    return score


def trim(y, sr):
    """Trim leading/trailing silence, keep a short natural tail."""
    idx = librosa.effects.split(y, top_db=42, frame_length=1024, hop_length=128)
    if len(idx) == 0:
        return y
    a, b = idx[0][0], idx[-1][1]
    a = max(0, a - int(0.02 * sr))
    b = min(len(y), b + int(0.06 * sr))
    y = y[a:b].copy()
    fi, fo = int(0.008 * sr), int(0.05 * sr)
    y[:fi] *= np.linspace(0, 1, fi)
    y[-fo:] *= np.linspace(1, 0, fo) ** 2
    return y


def text_variants(say):
    out = [say]
    # an em-dash at the end sometimes produces a dragged vowel; offer a plain variant
    if say.endswith('——'):
        out.append(say[:-2] + '，')
        out.append(say[:-2] + '。')
    return out


def main():
    os.makedirs(f'{BUILD}/vo/takes', exist_ok=True)
    tts, rec, mos = kokoro(), asr_model(), utmos_model()
    meter = pyln.Meter(SR_OUT)
    only = set(sys.argv[1:])
    meta_path = f'{BUILD}/vo/vo.json'
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for ln in ALL_LINES:
        if only and ln['id'] not in only:
            continue
        takes = []
        for tv in text_variants(ln['say']):
            for sp in SPEEDS:
                a = tts.generate(tv, sid=SID, speed=sp)
                y = trim(np.array(a.samples, dtype=np.float32), a.sample_rate)
                hyp = transcribe(rec, y, a.sample_rate)
                err = syllable_errors(ln['say'], hyp)
                takes.append(dict(text=tv, speed=sp, hyp=hyp, err=err, y=y, sr=a.sample_rate))
        best_err = min(t['err'] for t in takes)
        pool = [t for t in takes if t['err'] <= best_err + 0.01]
        for t in pool:
            t['mos'] = mos(t['y'], t['sr'])
        best = max(pool, key=lambda t: t['mos'])
        y = librosa.resample(best['y'], orig_sr=best['sr'], target_sr=SR_OUT)
        loud = meter.integrated_loudness(np.concatenate([y, np.zeros(SR_OUT // 2)])) if len(y) > SR_OUT // 2 else -20
        y = y * 10 ** ((-19.0 - loud) / 20)
        sf.write(f'{BUILD}/vo/{ln["id"]}.wav', y, SR_OUT, subtype='PCM_24')
        meta[ln['id']] = dict(dur=len(y) / SR_OUT, speed=best['speed'], text=best['text'], hyp=best['hyp'],
                              err=best['err'], mos=round(best['mos'], 3),
                              n_takes=len(takes), errs=[round(t['err'], 1) for t in takes])
        print(ln['id'], json.dumps(meta[ln['id']], ensure_ascii=False), flush=True)
        json.dump(meta, open(meta_path, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
