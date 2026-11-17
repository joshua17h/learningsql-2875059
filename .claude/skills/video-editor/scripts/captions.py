#!/usr/bin/env python3
"""Build an .ass caption file from transcribe.py output, styled from brand.json.

Usage: captions.py SEGMENTS.json OUT.ass --width W --height H [--brand brand.json] [--offset SECONDS]
Words are split into short punchy groups (2-4 words) timed in proportion to their
length inside each segment. Burn in with: ffmpeg -i in.mp4 -vf "ass=OUT.ass" ...
"""
import json, os, sys
args = sys.argv
seg_path, out = args[1], args[2]
W = int(args[args.index("--width") + 1]); H = int(args[args.index("--height") + 1])
off = float(args[args.index("--offset") + 1]) if "--offset" in args else 0.0
here = os.path.dirname(os.path.abspath(__file__))
bp = args[args.index("--brand") + 1] if "--brand" in args else os.path.join(here, "..", "brand.json")
brand = json.load(open(bp))

def ass_color(hexstr, alpha="00"):
    h = hexstr.lstrip("#"); return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}".upper()

fs = int(H * (0.055 if H > W else 0.065))
style = (f"Style: Cap,{brand['font']},{fs},{ass_color(brand['text_color'])},{ass_color(brand['accent_color'])},"
         f"{ass_color('#000000')},{ass_color('#000000','80')},-1,0,0,0,100,100,0,0,1,{max(2,fs//14)},{max(1,fs//30)},2,"
         f"{W//12},{W//12},{int(H*0.22) if H > W else int(H*0.08)},1")
def ts(t):
    t = max(0, t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
lines = []
for s in json.load(open(seg_path))["segments"]:
    words = s["text"].split()
    if not words: continue
    groups, g = [], []
    for wd in words:
        g.append(wd)
        if len(g) >= 3 or wd[-1] in ".,!?":
            groups.append(g); g = []
    if g: groups.append(g)
    total = sum(len(" ".join(x)) for x in groups); t = s["start"] - off
    span = s["end"] - s["start"]
    for grp in groups:
        d = span * len(" ".join(grp)) / total
        # highlight the last word of each group in the accent colour
        txt = " ".join(grp[:-1] + [r"{\c" + ass_color(brand["accent_color"]) + "&}" + grp[-1]]) if len(grp) > 1 else grp[0]
        lines.append(f"Dialogue: 0,{ts(t)},{ts(t+d)},Cap,,0,0,0,,{txt.upper() if brand.get('uppercase') else txt}")
        t += d
open(out, "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
{style}

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
""" + "\n".join(lines) + "\n")
