#!/usr/bin/env python3
"""Transcribe a media file into timed speech segments.

Usage: transcribe.py INPUT OUT.json [--min-pause 0.3]
Splits speech at silences (ffmpeg silencedetect), then runs Whisper on each
chunk. Output: {"duration": s, "segments": [{"start","end","text"}], "pauses": [{"start","end"}]}
Pauses are the silent gaps; use them to cut dead air (> 0.5 s) and to spot retakes.
"""
import json, os, re, subprocess, sys, tempfile, wave
import numpy as np, sherpa_onnx

inp, out = sys.argv[1], sys.argv[2]
min_pause = float(sys.argv[sys.argv.index("--min-pause") + 1]) if "--min-pause" in sys.argv else 0.3
mdir = os.path.join(os.environ.get("VIDEO_EDITOR_MODEL_DIR", os.path.expanduser("~/.cache/video-editor")), "sherpa-onnx-whisper-small")

with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, "a.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", inp, "-ac", "1", "-ar", "16000", wav], check=True)
    log = subprocess.run(["ffmpeg", "-hide_banner", "-i", wav, "-af", f"silencedetect=noise=-35dB:d={min_pause}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    w = wave.open(wav); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
dur = len(a) / sr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
pauses = [{"start": s, "end": (ends[i] if i < len(ends) else dur)} for i, s in enumerate(starts)]

# speech = complement of pauses; long chunks are split to fit Whisper's 30 s window
speech, t = [], 0.0
for p in pauses:
    if p["start"] > t: speech.append([t, p["start"]])
    t = p["end"]
if t < dur: speech.append([t, dur])
chunks = []
for s, e in speech:
    while e - s > 25: chunks.append([s, s + 25]); s += 25
    if e - s > 0.15: chunks.append([s, e])

r = sherpa_onnx.OfflineRecognizer.from_whisper(
    encoder=f"{mdir}/small-encoder.int8.onnx", decoder=f"{mdir}/small-decoder.int8.onnx",
    tokens=f"{mdir}/small-tokens.txt", task="transcribe", num_threads=os.cpu_count() or 4)
segs = []
for s, e in chunks:
    st = r.create_stream(); st.accept_waveform(sr, a[int(s * sr):int(e * sr)]); r.decode_stream(st)
    txt = st.result.text.strip()
    if txt: segs.append({"start": round(s, 3), "end": round(e, 3), "text": txt})
    print(f"[{s:7.2f}-{e:7.2f}] {txt}", file=sys.stderr)
json.dump({"duration": dur, "segments": segs, "pauses": pauses}, open(out, "w"), indent=1)
