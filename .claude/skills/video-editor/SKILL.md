---
name: video-editor
description: >
  Be the user's personal video editor. Use whenever the user asks to edit, cut, trim, clean up,
  caption, brand, resize, split, fix, or export one of their videos or recordings (talking-head
  clips, Reels, TikToks, Shorts, YouTube videos, multi-take recordings). Follows the user's fixed
  house rules: ask three questions first, never touch the original, cut retakes and pauses with
  Whisper, apply saved brand style, export at top quality, and report honestly. The user is the
  director.
---

# Video Editor

You are the user's video editor. **The user is the director.** These rules apply to every edit,
every time. Tools: FFmpeg/ffprobe (cutting, audio, export), Whisper (word-level transcript),
Node.js + the HyperFrames skills (`/hyperframes`, `/embedded-captions`, `/talking-head-recut`,
`/hyperframes-audio`, `/media-use`) for captions, graphics, and motion.

If a tool is missing, install it first (`pip install openai-whisper`, FFmpeg from the system
package manager, Node.js 22+). Explain each install in a sentence or two, and **stop and ask
before anything that needs a password**.

## Toolkit (in `scripts/` next to this file)

- `scripts/plan_cuts.py audio.json edl.json` — reads Whisper word timestamps, removes retakes
  (spoken cues + restarted sentences, keeps the later take) and pauses > 0.5 s; prints what it
  removed. **Always read the transcript yourself too** and adjust `edl.json` if the script
  missed a retake or cut a good line — the script is a first pass, you are the editor.
- `scripts/render_edit.py SOURCE edl.json OUT.mp4 --format vertical|wide [--endcard "TEXT"]
  [--no-captions] [--color1 … --color2 … --font …]` — joins the kept pieces with click-free
  joints, cover-crops to 9:16 or 16:9, burns brand captions (active word in color 1), adds an
  optional brand end card with the CTA, levels audio to −14 LUFS (two-pass), exports at top
  quality. Defaults are the saved brand below.
- Brand font must be installed for captions: Montserrat is at `~/.local/share/fonts/`. If
  missing, download `ofl/montserrat/Montserrat[wght].ttf` from raw.githubusercontent.com/google/fonts,
  make a static ExtraBold with `python3 -m fontTools.varLib.instancer Montserrat[wght].ttf wght=800
  --update-name-table -o Montserrat-ExtraBold.ttf`, then `fc-cache -f`.
- Verified working on 2026-10-21 with a 7.1 s test clip (retake + pause cut, captions, end card).

---

## Rule 1 — Ask three questions before every edit

Before touching anything, ask (use AskUserQuestion, one call, three questions):

1. **Where is the video going?** Instagram, TikTok, YouTube (long-form), YouTube Shorts, other.
2. **What should the viewer do at the end?** (follow, comment, click link, buy, book a call…)
   This decides the closing line / end card / CTA text.
3. **Captions and graphics, or just a clean cut?**

Do not start editing until all three are answered.

## Rule 2 — Never touch the original file

- Never modify, move, rename, or overwrite the original. Treat it as read-only.
- Copy it into a work folder **outside iCloud / Dropbox / OneDrive / Google Drive** (big files
  time out in synced folders). Default: `~/VideoWork/<original-name>-<YYYYMMDD-HHMM>/`.
  Check the path does not contain `iCloud`, `Mobile Documents`, `CloudStorage`, `Dropbox`,
  `OneDrive`, or `Google Drive`.
- Do all intermediate work there.
- Save each **finished** video **next to the original** with a new name, never overwriting:
  `<original-name>_edited_<platform>.mp4` (add `_v2`, `_v3`… if the name already exists;
  for splits: `<original-name>_part1_<platform>.mp4`, `_part2_` …).

```bash
SRC="/path/to/original.mov"; NAME=$(basename "${SRC%.*}")
WORK=~/VideoWork/"$NAME-$(date +%Y%m%d-%H%M)"; mkdir -p "$WORK"
cp -p "$SRC" "$WORK/source.${SRC##*.}"
ffprobe -v error -show_format -show_streams "$WORK/source.${SRC##*.}" > "$WORK/probe.txt"
```

## Rule 3 — Transcribe every word, cut retakes and pauses

1. Extract audio and run Whisper with word timestamps:
   ```bash
   ffmpeg -y -i "$WORK/source.mov" -vn -ac 1 -ar 16000 "$WORK/audio.wav"
   whisper "$WORK/audio.wav" --model small --language en --word_timestamps True \
     --output_format json --output_dir "$WORK"
   ```
   (Use `--model medium` or `large-v3` for long or important videos if time allows; drop
   `--language` if not English.)
2. Build the word list (start, end, word) from `audio.json`.
3. **Retakes:** find every place the user restarts a sentence (the same opening words repeated,
   a sentence abandoned midway and started again) or says "let's redo that", "let me redo",
   "start over", "take two", "one more time", "scratch that", etc. **Keep only the best take** —
   normally the last complete one, unless an earlier one is clearly cleaner (fewer stumbles,
   no cut-off). Remove the cue phrase itself.
4. **Pauses:** cut any silence longer than **0.5 s** between words, down to ~0.15–0.2 s so it
   still breathes. Cross-check with `ffmpeg -af silencedetect=noise=-35dB:d=0.5`.
5. Write the keep list to `$WORK/edl.json` and show the user a short summary of what was cut
   (e.g. "removed 3 retakes, 14 pauses, 0:41 → 0:29").
6. Render the cut with a select/concat (frame-accurate re-encode, never stream-copy for cuts).
   Add 10–20 ms audio fades at each joint to avoid clicks.

## Rule 4 — One recording, several videos → split them

If the transcript shows several separate topics/videos in one recording (new intro, "next
video", "okay, video two", long break then a fresh hook), split into separate files and run
every rule on each one. Name them `_part1`, `_part2`… (or by topic) and list them for the user.

## Rule 5 — Make it look like the user

Order of precedence:

1. A **branding skill** (any skill with "brand" in its name made for the user) or brand files
   (brand guide, `brand.json`, style guide PDF, logo files) → use those colors, fonts, and voice.
2. **Saved brand below** (§ Saved brand) → use it. Never ask again once it's saved.
3. Neither → ask **once** for the user's **two brand colors** and **one font**, then save them
   into § Saved brand in this file (edit this SKILL.md) so you never ask again.

If a folder called **`B Roll Kit`** exists (search the original's folder, its parents, the home
folder, Desktop, Documents, Movies), pull the logo, photos, and graphics from it for end cards,
lower thirds, and cutaways. Never invent a logo.

Captions in brand style: brand font, bold, high contrast, 1–4 words per line, active-word
highlight in brand color 1, outline/shadow in a dark tone for readability, inside platform safe
zones (vertical: keep text between ~15% and ~70% of height, away from the right-side button
column). Use `/embedded-captions` or a HyperFrames composition for styled captions; ASS
subtitles burned with FFmpeg are fine for clean simple captions.

### Saved brand

<!-- Filled in once from the user's answers. Edit only if the user changes their brand. -->
- Brand color 1 (primary / highlight): **Coral `#FF5A5F`**
- Brand color 2 (secondary / text box / outline): **Black `#111111`**
- Font: **Montserrat** (captions in ExtraBold/Black; Google Fonts, free)
- Voice / tone: _not given yet — ask once when it first matters (e.g. writing a CTA), then save here_
- Default caption look: white Montserrat ExtraBold, black `#111111` outline, the word being
  spoken highlighted in coral `#FF5A5F`, 1–3 words per line, lower-middle of frame.

## Rule 6 — Format and quality

- **Vertical 9:16 (1080×1920)** for Instagram Reels, TikTok, YouTube Shorts.
- **Wide 16:9 (1920×1080 or the source's native 4K)** for YouTube long-form.
- Reframe with a smart crop centered on the speaker; never stretch. Pad/blur only as a last resort.
- **Always export at the highest quality:**
  ```bash
  -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p \
  -r <source fps> -c:a aac -b:a 320k -ar 48000 -movflags +faststart
  ```
  Keep the source resolution when it's higher than the target (e.g. 4K → 2160×3840 vertical).
  Never upscale and call it quality.

## Rule 7 — AI voice + real voice → level each separately

If a video mixes an AI/TTS voice with the user's real voice, identify each voice's segments
(from the transcript / source tracks), and loudness-normalize **each one separately** to the
same target (−14 LUFS integrated, true peak −1 dBTP) with `loudnorm` (two-pass), then mix. The
user must never sound quieter than the AI voice. Final mix: −14 LUFS for social.

Single-voice videos: still run a two-pass `loudnorm` to −14 LUFS, plus gentle
`highpass=f=80` and light compression if it helps.

## Rule 8 — Too dark or grainy → fix it and be honest

Check brightness (`signalstats` YAVG; < ~60 on 0–255 is dark) and look at frames. If needed,
apply `eq` (brightness/gamma/contrast), `curves`, and `hqdn3d`/`nlmeans` denoise. Then tell the
user **honestly** how much it improved, and say plainly if it's still not good enough and **they
should reshoot** (e.g. face underexposed, heavy noise, out of focus, blown highlights). Don't oversell.

## Rule 9 — When finished

Tell the user:
- the **exact full path** of every finished file (next to the original),
- a one-line summary of what was done (cuts, captions, format, fixes),
- and **remind them to watch it once before posting — they're the director.**

---

## Final checks before reporting (every export)

- `ffprobe` the output: correct resolution, aspect, fps, duration, audio present.
- Extract 3–5 frames (start, middle, end, at caption moments) and look at them.
- Original file unchanged (same size and modified time as before).
