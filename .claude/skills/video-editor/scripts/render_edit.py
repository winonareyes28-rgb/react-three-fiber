#!/usr/bin/env python3
"""Render a cut from edl.json: join kept segments, reframe, burn brand captions, level audio.

Usage:
  render_edit.py SOURCE EDL.json OUT.mp4 [--format vertical|wide] [--no-captions] [--endcard TEXT]
                 [--color1 #FF5A5F] [--color2 #111111] [--font Montserrat] [--fontdir DIR]

Captions: white brand-font text, color2 outline, the word being spoken in color1,
up to 3 words per line. Audio: two-pass loudnorm to -14 LUFS / -1 dBTP.
Export: H.264 High, CRF 16, preset slow, AAC 320k, source frame rate.
"""
import argparse
import json
import os
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument("source")
p.add_argument("edl")
p.add_argument("out")
p.add_argument("--format", default="vertical", choices=["vertical", "wide"])
p.add_argument("--no-captions", action="store_true")
p.add_argument("--color1", default="#FF5A5F")
p.add_argument("--color2", default="#111111")
p.add_argument("--font", default="Montserrat ExtraBold")
p.add_argument("--fontdir", default=os.path.expanduser("~/.local/share/fonts"))
p.add_argument("--endcard", default="", help="call-to-action text for a brand end card, e.g. 'FOLLOW FOR MORE'")
p.add_argument("--endcard-dur", type=float, default=1.6)
a = p.parse_args()

edl = json.load(open(a.edl))
segs = edl["segments"]
work = os.path.dirname(os.path.abspath(a.edl))


def probe(key):
    return subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    f"stream={key}", "-of", "csv=p=0", a.source], text=True).strip()


w, h = map(int, probe("width,height").split(","))
fps = probe("r_frame_rate")


def ass_color(hex_):
    r, g, b = hex_.lstrip("#")[0:2], hex_.lstrip("#")[2:4], hex_.lstrip("#")[4:6]
    return f"&H00{b}{g}{r}".upper()


def remap(t):
    """Source time -> output time on the cut timeline."""
    out = 0.0
    for s, e in segs:
        if t < s:
            return out
        if t <= e:
            return out + t - s
        out += e - s
    return out


# Target canvas: keep source resolution when possible, never stretch.
if a.format == "vertical":
    W, H = (2160, 3840) if min(w, h) >= 2160 else (1080, 1920)
else:
    W, H = (3840, 2160) if min(w, h) >= 2160 else (1920, 1080)

# --- captions (ASS) ---
ass_path = os.path.join(work, "captions.ass")
if not a.no_captions:
    scale = H / 1920
    lines = []
    chunk = []
    for wd in edl["words"]:
        chunk.append(wd)
        if len(chunk) == 3 or re.search(r"[.,?!]$", wd["word"].strip()):
            lines.append(chunk)
            chunk = []
    if chunk:
        lines.append(chunk)
    events = []
    for line in lines:
        for i, wd in enumerate(line):
            start = remap(wd["start"])
            end = remap(line[i + 1]["start"]) if i + 1 < len(line) else remap(line[-1]["end"]) + 0.12
            parts = []
            for j, x in enumerate(line):
                txt = x["word"].strip().rstrip(".,")
                parts.append(f"{{\\c{ass_color(a.color1)}}}{txt}{{\\c&H00FFFFFF}}" if j == i else txt)
            ts = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
            events.append(f"Dialogue: 0,{ts(start)},{ts(max(end, start + 0.05))},Cap,,0,0,0,,{' '.join(parts)}")
    if a.endcard:
        t0 = sum(e - s for s, e in segs)
        t1 = t0 + a.endcard_dur
        ts = lambda t: f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
        events.append(f"Dialogue: 1,{ts(t0)},{ts(t1)},Cap,,0,0,0,,{{\\an7\\pos(0,0)\\bord0\\shad0\\fad(150,0)"
                      f"\\c{ass_color(a.color1)}\\p1}}m 0 0 l {W} 0 {W} {H} 0 {H}")
        events.append(f"Dialogue: 2,{ts(t0)},{ts(t1)},Cap,,0,0,0,,{{\\an5\\pos({W // 2},{H // 2})\\bord0\\shad0"
                      f"\\fad(250,0)\\fs{int(120 * scale)}\\c{ass_color(a.color2)}}}{a.endcard}")
    with open(ass_path, "w") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{a.font},{int(96 * scale)},&H00FFFFFF,&H00FFFFFF,{ass_color(a.color2)},&H80000000,0,0,0,0,100,100,0,0,1,{int(7 * scale)},{int(3 * scale)},2,{int(80 * scale)},{int(80 * scale)},{int((640 if a.format == 'vertical' else 120) * scale)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(events) + "\n")

# --- filter graph: trim + 15 ms audio fades at every joint, concat, reframe, captions ---
fc = []
for i, (s, e) in enumerate(segs):
    d = e - s
    fc.append(f"[0:v]trim={s:.3f}:{e:.3f},setpts=PTS-STARTPTS[v{i}]")
    fc.append(f"[0:a]atrim={s:.3f}:{e:.3f},asetpts=PTS-STARTPTS,"
              f"afade=t=in:d=0.015,afade=t=out:st={max(0, d - 0.015):.3f}:d=0.015[a{i}]")
fc.append("".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[vc0][ac0]")
if a.endcard:  # hold the last frame under the end card, silent audio
    fc.append(f"[vc0]tpad=stop_mode=clone:stop_duration={a.endcard_dur}[vc]")
    fc.append(f"[ac0]apad=pad_dur={a.endcard_dur}[ac]")
else:
    fc.append("[vc0]null[vc]")
    fc.append("[ac0]anull[ac]")
# Cover-crop to the target aspect (centered), then scale.
fc.append(f"[vc]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1"
          + (f",ass={ass_path}:fontsdir={a.fontdir}" if not a.no_captions else "") + "[vo]")


def run(extra_audio_filter, out_args):
    graph = ";".join(fc) + f";[ac]{extra_audio_filter}[ao]"
    return subprocess.run(["ffmpeg", "-v", "info", "-hide_banner", "-nostats", "-y", "-i", a.source, "-filter_complex", graph,
                           "-map", "[vo]", "-map", "[ao]"] + out_args, capture_output=True, text=True)


# Pass 1: measure loudness of the cut audio.
r = run("highpass=f=80,loudnorm=I=-14:TP=-1:LRA=11:print_format=json", ["-f", "null", "-"])
m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
ln = (f"highpass=f=80,loudnorm=I=-14:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
      f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:"
      f"linear=true,aresample=48000")
# Pass 2: final high-quality encode.
r = run(ln, ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-r", fps, "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", a.out])
if r.returncode:
    raise SystemExit(r.stderr)
print(f"wrote {a.out}  {W}x{H}  input loudness {m['input_i']} LUFS -> -14 LUFS")
