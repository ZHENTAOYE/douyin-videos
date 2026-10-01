"""Thin wrapper around sherpa-onnx Kokoro v1.1-zh for offline Chinese narration."""
import os, wave, numpy as np, sherpa_onnx

_tts = None
def engine():
    global _tts
    if _tts is None:
        M = os.environ["KOKORO_DIR"]
        cfg = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=f"{M}/model.onnx", voices=f"{M}/voices.bin", tokens=f"{M}/tokens.txt",
                    data_dir=f"{M}/espeak-ng-data", dict_dir=f"{M}/dict",
                    lexicon=f"{M}/lexicon-us-en.txt,{M}/lexicon-zh.txt"),
                num_threads=4),
            rule_fsts=f"{M}/phone-zh.fst,{M}/date-zh.fst,{M}/number-zh.fst",
            max_num_sentences=1)
        _tts = sherpa_onnx.OfflineTts(cfg)
    return _tts

def synth(text, sid, speed=1.0):
    a = engine().generate(text, sid=sid, speed=speed)
    return a.sample_rate, np.array(a.samples, dtype=np.float32)

def write_wav(path, sr, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
