#!/usr/bin/env bash
# Installs the transcription engine and Whisper model if missing.
# Hugging Face may be blocked, so the model comes from sherpa-onnx's GitHub releases.
set -euo pipefail
MODEL_DIR="${VIDEO_EDITOR_MODEL_DIR:-$HOME/.cache/video-editor}"
command -v ffmpeg >/dev/null || { echo "ffmpeg missing: apt-get install -y ffmpeg"; exit 1; }
command -v node >/dev/null || echo "note: node.js not found (only needed for npx-based tools)"
python3 -c "import sherpa_onnx" 2>/dev/null || pip install -q sherpa-onnx numpy
if [ ! -f "$MODEL_DIR/sherpa-onnx-whisper-small/small-encoder.int8.onnx" ]; then
  mkdir -p "$MODEL_DIR"
  curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2 \
    | tar xj -C "$MODEL_DIR"
fi
echo "ready: $MODEL_DIR/sherpa-onnx-whisper-small"
