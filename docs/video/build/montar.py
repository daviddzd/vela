"""Montage with ffmpeg: recordings (or slides) + narration -> one MP4 with burnt-in subtitles, plus .srt and chapters.

Runs inside the vela-video image (full ffmpeg), from the repository root:
    python3 docs/video/build/montar.py --video 2

Inputs
  docs/video/out/escenas.json                 scenes of the script (render_guion.py)
  docs/video/out/audio/<id>.wav, tiempos.json  narration and the timing of each sentence (voz.py)
  docs/privado/video/clips/video<N>/<id>*.webm recordings (grabar.cjs); <id>.json says where the scene starts
  docs/privado/video/diapositivas/<id>.png      slides (video 1)
Outputs (docs/privado/video/, git-ignored)
  <name>.mp4 (subtitles burnt in), <name>.srt, <name>_descripcion.txt (chapters with their minute)

How a scene is fitted to its narration: T = max(narration, recording / MAX_SPEED). A longer recording is sped up
(at most MAX_SPEED); a shorter one holds its last frame. The audio is padded with silence to T.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/video/out"
PRIV = ROOT / "docs/privado/video"
FONTS = ROOT / "docs/presentacion/fuentes"
BOLD = FONTS / "AtkinsonHyperlegible-Bold.ttf"
MAX_SPEED = 1.6
FPS = 30
NAMES = {1: "enlaza_explicado", 2: "enlaza_demo_coloquio"}
LABELS = {"_izq": "Celular de la familia", "_der": "Tablero de coordinación"}
NAVY, DEEP = "0x3A5B76", "0x1B3349"


def run(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duration(f: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def start_of(clip: Path) -> float:
    marks = clip.with_suffix(".json")
    return json.loads(marks.read_text()).get("start", 0.0) if marks.exists() else 0.0


def scene_video(sid: str, video: int, tmp: Path) -> Path:
    """The scene's picture without sound: one clip, several clips one after another, two side by side, or a slide."""
    out = tmp / f"{sid}_raw.mp4"
    slide = PRIV / "diapositivas" / f"{sid}.png"
    # exactly <id>.webm or <id>_<part>.webm: "2.1*" would also take 2.10, 2.11, ...
    clips = sorted(c for c in (PRIV / "clips" / f"video{video}").glob(f"{sid}*.webm")
                   if c.stem == sid or c.stem.startswith(sid + "_"))
    norm = f"fps={FPS},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p"
    if not clips and slide.exists():
        run("-loop", "1", "-t", "4", "-i", str(slide), "-vf", norm, "-c:v", "libx264", "-crf", "18", str(out))
        return out
    if not clips:
        raise SystemExit(f"ERROR: la escena {sid} no tiene grabación ni diapositiva")
    halves = {c.stem[len(sid):]: c for c in clips if c.stem[len(sid):] in LABELS}
    if len(halves) == 2:
        # two windows recorded at the same time, each 960x1080: shrink a little and put a label band on top
        ins, parts = [], []
        for i, key in enumerate(("_izq", "_der")):
            ins += ["-ss", f"{start_of(halves[key]):.2f}", "-i", str(halves[key])]
            parts.append(f"[{i}:v]fps={FPS},scale=900:-2,pad=960:1080:30:68:color={DEEP},"
                         f"drawtext=fontfile={BOLD}:text='{LABELS[key]}':fontsize=34:fontcolor=white:x=(w-tw)/2:y=16[v{i}]")
        run(*ins, "-filter_complex", ";".join(parts) + ";[v0][v1]hstack=inputs=2,format=yuv420p[v]", "-map", "[v]",
            "-shortest", "-c:v", "libx264", "-crf", "20", str(out))
        return out
    # one or more clips in order (_a, _b, …): cut each from its start mark and join them
    ins, chain = [], ""
    for i, c in enumerate(clips):
        ins += ["-ss", f"{start_of(c):.2f}", "-i", str(c)]
        chain += f"[{i}:v]{norm},setsar=1[c{i}];"
    chain += "".join(f"[c{i}]" for i in range(len(clips))) + f"concat=n={len(clips)}:v=1:a=0[v]"
    run(*ins, "-filter_complex", chain, "-map", "[v]", "-c:v", "libx264", "-crf", "20", str(out))
    return out


def fit(sid: str, raw: Path, wav: Path, tmp: Path) -> tuple[Path, float]:
    """Join picture and narration in a segment of length T (see the module docstring)."""
    v, a = duration(raw), duration(wav)
    t = max(a, v / MAX_SPEED)
    vf = f"setpts=PTS/{v / t:.4f}" if v > t else f"tpad=stop_mode=clone:stop_duration={t - v + 0.1:.2f}"
    out = tmp / f"{sid}.mp4"
    run("-i", str(raw), "-i", str(wav), "-filter_complex",
        f"[0:v]{vf},trim=duration={t:.3f},setpts=PTS-STARTPTS[v];[1:a]apad,atrim=duration={t:.3f},aresample=48000[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k",
        "-ac", "2", str(out))
    return out, t


def srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def cues_for(sentence: str, start: float, end: float) -> list[tuple[float, float, str]]:
    """A long sentence becomes several cues of at most two lines of 42 characters, timed by their length."""
    lines = textwrap.wrap(sentence, 42)
    chunks = ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]
    total = sum(len(c) for c in chunks)
    out, t = [], start
    for c in chunks:
        d = (end - start) * len(c) / total
        out.append((t, t + d, c))
        t += d
    return out


def mmss(s: float) -> str:
    return f"{int(s) // 60:02d}:{int(s) % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=int, choices=(1, 2), required=True)
    ap.add_argument("--escenas", help="solo estas escenas (para probar); el resultado se llama <nombre>_prueba")
    a = ap.parse_args()

    scenes = [s for s in json.loads((OUT / "escenas.json").read_text(encoding="utf-8")) if s["video"] == a.video]
    if a.escenas:
        scenes = [s for s in scenes if s["id"] in a.escenas.split(",")]
    timing = json.loads((OUT / "audio/tiempos.json").read_text(encoding="utf-8"))
    tmp = OUT / f"montaje{a.video}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)

    segments, cues, chapters, t0, last_part = [], [], [], 0.0, None
    for s in scenes:
        sid = s["id"]
        seg, t = fit(sid, scene_video(sid, a.video, tmp), OUT / "audio" / f"{sid}.wav", tmp)
        segments.append(seg)
        for c in timing[sid]["cues"]:
            cues += cues_for(c["text"], t0 + c["start"], t0 + c["end"])
        title = re.sub(r"\s*\(≈.*\)$", "", s["part"]) if a.video == 1 else s["title"]
        if title != last_part:
            chapters.append(f"{mmss(t0)} {title}")
            last_part = title
        print(f"escena {sid}: {t:5.1f} s")
        t0 += t

    name = NAMES[a.video] + ("_prueba" if a.escenas else "")
    PRIV.mkdir(parents=True, exist_ok=True)
    srt = PRIV / f"{name}.srt"
    srt.write_text("\n".join(f"{i}\n{srt_time(b)} --> {srt_time(e)}\n{txt}\n" for i, (b, e, txt) in enumerate(cues, 1)),
                   encoding="utf-8")
    (tmp / "lista.txt").write_text("".join(f"file '{p}'\n" for p in segments))
    joined = tmp / "unido.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"), "-c", "copy", str(joined))
    # libass measures an .srt on a 288-pixel-high canvas: 12 ≈ 45 px on 1080p; BorderStyle=3 = a solid box behind
    style = (f"FontName=Atkinson Hyperlegible,FontSize=12,Bold=1,PrimaryColour=&H00FFFFFF,BorderStyle=3,"
             f"OutlineColour=&H22{DEEP[6:8]}{DEEP[4:6]}{DEEP[2:4]},BackColour=&H22{DEEP[6:8]}{DEEP[4:6]}{DEEP[2:4]},"
             f"Outline=2,Shadow=0,MarginV=10")
    final = PRIV / f"{name}.mp4"
    run("-i", str(joined), "-vf", f"subtitles={srt}:fontsdir={FONTS}:force_style='{style}'",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final))
    desc = PRIV / f"{name}_descripcion.txt"
    desc.write_text("Capítulos\n" + "\n".join(chapters) + "\n\nPrototipo académico · datos sintéticos. "
                    "Narración con voz sintética (Piper, es_MX-claude-high).\n", encoding="utf-8")
    print(f"{final}: {mmss(t0)} ({t0 / 60:.1f} min)\n{srt}\n{desc}")


if __name__ == "__main__":
    main()
