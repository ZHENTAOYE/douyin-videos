#!/usr/bin/env bash
# One-shot rebuild of 《神经网络往事》 from script.py to the final MP4.
#   pip install sherpa-onnx numpy scipy ; npm install   (in neural-network-history/)
#   src/fetch_assets.sh
#   src/build.sh
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
export KOKORO_DIR=${KOKORO_DIR:-$ROOT/assets/models/kokoro-multi-lang-v1_1}
export SENSEVOICE_DIR=${SENSEVOICE_DIR:-$ROOT/assets/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17}
export FONT_DIR=${FONT_DIR:-$ROOT/assets/fonts}
mkdir -p "$ROOT/build" "$ROOT/output"

python3 tts.py --qa            # narration, ASR-checked line by line
python3 timeline.py            # master timeline + voice track
(cd render && node main.js --cues-only)
python3 music.py               # original score + sound effects
python3 mix.py                 # ducking + loudness (-14 LUFS)

# frames: 4 parallel workers, then concatenate
D=$(python3 -c "import json;print(json.load(open('$ROOT/build/timeline.json'))['duration'])")
WORKERS=${WORKERS:-4}
pids=()
for i in $(seq 0 $((WORKERS-1))); do
  read a b < <(python3 -c "d=$D;n=$WORKERS;F=round(d*30);print(round(F*$i/n)/30, round(F*($i+1)/n)/30)")
  (cd render && node main.js --from "$a" --to "$b" --out "$ROOT/build/part$i.mp4") &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
: > "$ROOT/build/parts.txt"
for i in $(seq 0 $((WORKERS-1))); do echo "file 'part$i.mp4'" >> "$ROOT/build/parts.txt"; done
ffmpeg -y -loglevel error -f concat -safe 0 -i "$ROOT/build/parts.txt" -c copy "$ROOT/build/video.mp4"

ffmpeg -y -loglevel error -i "$ROOT/build/video.mp4" -i "$ROOT/build/mix.wav" \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart \
  -metadata title="神经网络往事" "$ROOT/output/神经网络往事.mp4"

(cd render && node cover.js)
cp "$ROOT/build/cover.png" "$ROOT/output/封面_9x16.png"
ffmpeg -y -loglevel error -i "$ROOT/build/cover.png" -vf "crop=1080:1440:0:240" -q:v 2 "$ROOT/output/封面_3x4.jpg"
echo "done → $ROOT/output/"
