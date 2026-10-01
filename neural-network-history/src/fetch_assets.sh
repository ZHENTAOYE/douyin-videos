#!/usr/bin/env bash
# Downloads the fonts and offline speech models this project needs into ../assets
# (not committed: ~1 GB). Everything comes from GitHub releases.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p assets/fonts assets/models
cd assets/fonts
[ -f OTF/SimplifiedChinese/SourceHanSerifSC-Heavy.otf ] || { curl -sSL -o serif.zip https://github.com/adobe-fonts/source-han-serif/releases/download/2.003R/09_SourceHanSerifSC.zip && unzip -oq serif.zip && rm serif.zip; }
[ -f OTF/SimplifiedChinese/SourceHanSansSC-Bold.otf ] || { curl -sSL -o sans.zip https://github.com/adobe-fonts/source-han-sans/releases/download/2.005R/09_SourceHanSansSC.zip && unzip -oq sans.zip && rm sans.zip; }
[ -f LXGWWenKai-Regular.ttf ] || curl -sSL -o LXGWWenKai-Regular.ttf https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Regular.ttf
cd ../models
[ -d kokoro-multi-lang-v1_1 ] || { curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2 | tar xj; }
[ -d sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17 ] || { curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2 | tar xj; }
echo "assets ready"
