"""Transcribe wav files with SenseVoice (sherpa-onnx) to QA the TTS output.
Also reports a rough median F0 so voices can be compared without listening."""
import sys, os, wave, numpy as np, sherpa_onnx
D = os.environ["SENSEVOICE_DIR"]
rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=f"{D}/model.int8.onnx", tokens=f"{D}/tokens.txt", language="zh", use_itn=True, num_threads=4)

def load(p):
    with wave.open(p) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)/32768
    return sr, x

def f0_median(sr, x):
    hop, win = int(sr*0.01), int(sr*0.04); f0s=[]
    for i in range(0, len(x)-win, hop):
        fr = x[i:i+win]*np.hanning(win)
        if np.sqrt(np.mean(fr**2)) < 0.02: continue
        ac = np.correlate(fr, fr, 'full')[win-1:]
        lo, hi = int(sr/400), int(sr/60)
        k = lo+np.argmax(ac[lo:hi])
        if ac[k] > 0.4*ac[0]: f0s.append(sr/k)
    return float(np.median(f0s)) if f0s else 0

def transcribe(p):
    sr, x = load(p); s = rec.create_stream(); s.accept_waveform(sr, x); rec.decode_stream(s)
    return s.result

if __name__ == "__main__":
    for p in sys.argv[1:]:
        sr, x = load(p); r = transcribe(p)
        print(os.path.basename(p), f"F0~{f0_median(sr,x):.0f}Hz", r.text)
