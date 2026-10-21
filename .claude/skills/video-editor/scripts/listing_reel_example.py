import subprocess, sys, os
W = sys.argv[1]; OUT = sys.argv[2]
FONTDIR = os.path.expanduser("~/.local/share/fonts")
CORAL, BLACK = "&H005F5AFF", "&H00111111"
# (source, seconds, kind) — order tells the story: arrive, outside, inside, price, contact
shots = [
    ("dji_fly_20250513_112624_162_1747625553337_photo_optimized.jpg", 3.6, "photo"),
    ("IMG_3509.MOV", 3.0, "clip"),
    ("IMG_3502.MOV", 2.6, "clip"),
    ("IMG_3536.MOV", 3.3, "clip"),
    ("IMG_3533.MOV", 3.0, "clip"),
    ("IMG_3532.MOV", 2.5, "clip"),
    ("IMG_3512.MOV", 2.7, "clip"),
    ("IMG_3514.MOV", 2.1, "clip"),
    ("dji_fly_20250513_112624_162_1747625553337_photo_optimized.jpg", 3.8, "photo"),
    ("END", 4.2, "end"),
]
inputs, fc, labels = [], [], []
for i, (src, d, kind) in enumerate(shots):
    if kind == "end":
        inputs += ["-f", "lavfi", "-t", str(d), "-i", "color=c=0xFF5A5F:s=1080x1920:r=30"]
        fc.append(f"[{i}:v]setsar=1,format=yuv420p[s{i}]")
    elif kind == "photo":
        inputs += ["-loop", "1", "-framerate", "30", "-t", str(d), "-i", os.path.join(W, src)]
        n = int(d * 30)
        # blurred fill behind, sharp photo slowly pushing in on top (no stretching, house stays whole)
        fc.append(f"[{i}:v]split[a{i}][b{i}];"
                  f"[a{i}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:3,eq=brightness=-0.08[bg{i}];"
                  f"[b{i}]scale=2160:-2,zoompan=z='1+0.08*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=1080x810:fps=30[fg{i}];"
                  f"[bg{i}][fg{i}]overlay=0:(H-h)/2-180,trim=duration={d},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[s{i}]")
    else:
        inputs += ["-t", str(d), "-i", os.path.join(W, src)]
        fc.append(f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920,"
                  f"fps=30,trim=duration={d},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[s{i}]")
# short crossfades between shots
XF = 0.35
cur, t = "s0", shots[0][1]
for i in range(1, len(shots)):
    off = t - XF
    fc.append(f"[{cur}][s{i}]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{i}]")
    cur, t = f"x{i}", off + shots[i][1]
total = t
starts, acc = [], 0.0
for i, (_, d, _) in enumerate(shots):
    starts.append(acc); acc += d - XF

def ts(x):
    return f"0:{int(x // 60):02d}:{x % 60:05.2f}"

ev = []
def line(i, text, style, y, fade=(200, 150), lag=0.0, end_trim=0.0):
    a = starts[i] + lag + (0.15 if i else 0)
    b = starts[i] + shots[i][1] - end_trim
    ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},{style},,0,0,0,,{{\\an7\\pos(80,{y})\\fad({fade[0]},{fade[1]})}}{text}")

line(0, "LINNEA", "Big", 1180)
line(0, "SINGLE ATTACHED", "Mid", 1330, lag=0.25)
line(0, "Le Moubréza South Phase 1", "Pill", 1520, lag=0.5)
line(0, "Sto. Tomas, Batangas", "Small", 1530, lag=0.6)
line(1, "Lot Area  100 sqm", "Pill", 1300)
line(1, "Floor Area  77.25 sqm", "Pill", 1400, lag=0.3)
line(2, "Actual Linnea model house", "Small", 1400)
line(3, "Living & Dining Area", "Pill", 1350)
line(4, "Kitchen", "Pill", 1350)
line(6, "Provision for 3 Bedrooms", "Pill", 1350)
line(7, "2 Toilet & Bath", "Pill", 1350)
line(8, "Total Contract Price", "Small", 1235)
line(8, "from ₱3,428,000", "Mid", 1290, lag=0.15)
line(8, "₱13,000 reservation", "Pill", 1420, lag=0.35)
line(8, "₱13,500/mo down payment · 24 mos", "Pill", 1520, lag=0.5)
line(8, "Pag-IBIG financing available", "Pill", 1620, lag=0.65)
e = 9; a, b = starts[e] + 0.3, total
ev.append(f"Dialogue: 0,{ts(a)},{ts(b)},EndBig,,0,0,0,,{{\\an5\\pos(540,700)\\fad(250,0)}}INQUIRE NOW")
ev.append(f"Dialogue: 0,{ts(a+0.2)},{ts(b)},EndMid,,0,0,0,,{{\\an5\\pos(540,880)\\fad(250,0)}}Linnea Single Attached\\NLe Moubréza South Phase 1")
ev.append(f"Dialogue: 0,{ts(a+0.35)},{ts(b)},EndBox,,0,0,0,,{{\\an5\\pos(540,1090)\\fad(250,0)}}0917 187 5095")
ev.append(f"Dialogue: 0,{ts(a+0.45)},{ts(b)},EndMid,,0,0,0,,{{\\an5\\pos(540,1220)\\fad(250,0)}}joanramores04@gmail.com")
ev.append(f"Dialogue: 0,{ts(a+0.5)},{ts(b)},Fine,,0,0,0,,{{\\an5\\pos(540,1420)\\fad(250,0)}}DHSUD LS No. 0003164, 0003165\\NPrices as of Oct 21, 2026 and subject to change.\\NModel house shown; actual unit finishes may vary.")

ass = os.path.join(W, "overlays.ass")
open(ass, "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Big,Montserrat ExtraBold,150,&H00FFFFFF,&H00FFFFFF,{BLACK},&H80000000,0,0,0,0,100,100,4,0,1,6,4,7,0,0,0,1
Style: Mid,Montserrat ExtraBold,76,&H00FFFFFF,&H00FFFFFF,{BLACK},&H80000000,0,0,0,0,100,100,2,0,1,5,3,7,0,0,0,1
Style: Small,Montserrat ExtraBold,46,&H00FFFFFF,&H00FFFFFF,{BLACK},&H80000000,0,0,0,0,100,100,1,0,1,4,2,7,0,0,0,1
Style: Pill,Montserrat ExtraBold,52,&H00FFFFFF,&H00FFFFFF,{CORAL},&H00000000,0,0,0,0,100,100,1,0,3,14,0,7,0,0,0,1
Style: EndBig,Montserrat ExtraBold,120,{BLACK},{BLACK},{BLACK},&H00000000,0,0,0,0,100,100,4,0,1,0,0,5,0,0,0,1
Style: EndMid,Montserrat ExtraBold,52,{BLACK},{BLACK},{BLACK},&H00000000,0,0,0,0,100,100,1,0,1,0,0,5,0,0,0,1
Style: EndBox,Montserrat ExtraBold,96,&H00FFFFFF,&H00FFFFFF,{BLACK},&H00000000,0,0,0,0,100,100,2,0,3,24,0,5,0,0,0,1
Style: Fine,Montserrat ExtraBold,30,{BLACK},{BLACK},{BLACK},&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")
fc.append(f"[{cur}]ass={ass}:fontsdir={FONTDIR}[vo]")
# silent audio track so every app accepts the file; add licensed music in the IG/FB editor
inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
cmd = ["ffmpeg", "-v", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vo]", "-map", f"{len(shots)}:a",
       "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.3f}", OUT]
subprocess.run(cmd, check=True)
print("wrote", OUT, f"{total:.2f}s")
