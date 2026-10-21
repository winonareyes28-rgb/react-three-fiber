#!/usr/bin/env python3
"""Plan cuts from a Whisper word-timestamp JSON.

Removes retakes (spoken cues like "let's redo that", and sentences restarted with the
same opening words, keeping the later take) and shrinks pauses longer than MAX_PAUSE.

Usage: plan_cuts.py audio.json edl.json [--max-pause 0.5]
Writes {"segments": [[start, end], ...], "words": [...kept words...], "removed": [...]}.
"""
import json
import re
import sys

MAX_PAUSE = 0.5
PAD_IN, PAD_OUT = 0.05, 0.10  # breathing room around kept speech (~0.15 s at each joint)
SENTENCE_GAP = 0.7  # a silence this long also ends a sentence

CUES = [
    r"let'?s redo that", r"let me redo( that)?", r"redo that", r"let'?s do that again",
    r"let me (try|do) that again", r"start (that )?over", r"scratch that", r"take two",
    r"one more time", r"let me start again", r"from the top",
]


def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def sentences(words):
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and w["start"] - cur[-1]["end"] > SENTENCE_GAP:
            out.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!]$", w["word"].strip()):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def text(sent):
    return " ".join(norm(w["word"]) for w in sent)


def opening(sent, n=2):
    return [norm(w["word"]) for w in sent if norm(w["word"]) not in ("um", "uh")][:n]


def main():
    args = sys.argv[1:]
    max_pause = MAX_PAUSE
    if "--max-pause" in args:
        i = args.index("--max-pause")
        max_pause = float(args[i + 1])
        del args[i:i + 2]
    src, dst = args
    data = json.load(open(src))
    words = [w for s in data["segments"] for w in s.get("words", [])]
    sents = sentences(words)
    drop = set()
    removed = []

    # Spoken retake cues: drop the cue sentence and the botched take before it.
    for k, s in enumerate(sents):
        t = text(s)
        for cue in CUES:
            m = re.search(cue, t)
            if not m:
                continue
            drop.add(k)
            before = t[:m.start()].strip()
            # cue said mid-sentence ("always cut the, um, let's redo that") -> whole sentence goes;
            # cue as its own sentence -> the previous sentence was the bad take.
            if not before and k > 0:
                drop.add(k - 1)
            break

    # Silent restarts: a sentence starting with the same words as the next kept one.
    kept = [k for k in range(len(sents)) if k not in drop]
    for a, b in zip(kept, kept[1:]):
        oa, ob = opening(sents[a]), opening(sents[b])
        if len(oa) == 2 and oa == ob:
            drop.add(a)

    for k in sorted(drop):
        removed.append(" ".join(w["word"].strip() for w in sents[k]))
    keep_words = [w for k, s in enumerate(sents) if k not in drop for w in s]

    # Group kept words into segments; split where words were dropped or the gap exceeds max_pause.
    segs = []
    prev = None
    for w in keep_words:
        contiguous = prev is not None and words.index(w) == words.index(prev) + 1
        if segs and contiguous and w["start"] - prev["end"] <= max_pause:
            segs[-1][1] = w["end"]
        else:
            segs.append([w["start"], w["end"]])
        prev = w
    segs = [[max(0.0, a - PAD_IN), b + PAD_OUT] for a, b in segs]
    # Merge any overlaps created by padding.
    merged = []
    for a, b in segs:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])

    json.dump({"segments": merged, "words": keep_words, "removed": removed}, open(dst, "w"), indent=1)
    before = words[-1]["end"] - words[0]["start"] if words else 0
    after = sum(b - a for a, b in merged)
    print(f"removed takes: {removed}")
    print(f"segments: {len(merged)}  speech span {before:.2f}s -> {after:.2f}s")


if __name__ == "__main__":
    main()
