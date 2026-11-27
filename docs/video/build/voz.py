"""Narration with Piper (local, free): one WAV per scene + the timing of every sentence (for the subtitles).

Needs out/escenas.json (render_guion.py). The voices are downloaded once into docs/video/out/voces/ (git-ignored) from
the official Piper voice list (rhasspy/piper-voices on Hugging Face, licence in each voice's MODEL_CARD).

    uv run --with piper-tts==1.8.0 --with num2words python3 docs/video/build/voz.py                 # every scene
    uv run --with piper-tts==1.8.0 --with num2words python3 docs/video/build/voz.py \\
        --voz es_MX-ald-medium --escenas 3.5,4.5 --salida docs/privado/video/muestras_voz/x.wav    # one test file

Each sentence is synthesised on its own: the subtitle shows the sentence with its figures (as numeros.json prints
them) and the voice reads habla.spoken(sentence), which habla.check() guarantees has no digit, symbol or URL.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig

sys.path.insert(0, str(Path(__file__).parent))
from habla import check, spoken  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/video/out"
VOICES = {  # name -> path inside rhasspy/piper-voices
    "es_MX-claude-high": "es/es_MX/claude/high",
    "es_MX-ald-medium": "es/es_MX/ald/medium",
}
LENGTH_SCALE = 1.12      # > 1 = slower; 1.12 is a calm pace (about 140 words per minute)
SENTENCE_PAUSE = 0.45    # seconds of silence after each sentence
SCENE_TAIL = 0.8         # seconds of silence at the end of a scene


def voice_files(name: str) -> Path:
    """Download the voice model once; return the .onnx path."""
    d = OUT / "voces"
    d.mkdir(parents=True, exist_ok=True)
    onnx = d / f"{name}.onnx"
    for ext in (".onnx", ".onnx.json"):
        f = d / f"{name}{ext}"
        if not f.exists() or f.stat().st_size < 1000:
            url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{VOICES[name]}/{name}{ext}"
            print(f"Descargando {url}")
            urllib.request.urlretrieve(url, f)
    return onnx


def sentences(text: str) -> list[str]:
    """Split a scene into sentences ('20.2 minutos' is not split: there is no space after that dot)."""
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-ZÁÉÍÓÚÑ¿«])", text) if s.strip()]


def synth_scene(voice: PiperVoice, scene: dict) -> tuple[bytes, int, list[dict]]:
    """Return (pcm16 audio, sample rate, [{start, end, text}]) for one scene."""
    cfg = SynthesisConfig(length_scale=LENGTH_SCALE)
    pcm, rate, cues, t = b"", voice.config.sample_rate, [], 0.0
    for sub in sentences(scene["said"]):
        say = spoken(sub)
        check(say, f"escena {scene['id']}")
        audio = b"".join(chunk.audio_int16_bytes for chunk in voice.synthesize(say, syn_config=cfg))
        dur = len(audio) / 2 / rate
        cues.append({"start": round(t, 3), "end": round(t + dur, 3), "text": sub, "voz": say})
        pause = int(SENTENCE_PAUSE * rate) * 2
        pcm += audio + b"\0" * pause
        t += dur + SENTENCE_PAUSE
    pcm += b"\0" * (int(SCENE_TAIL * rate) * 2)
    return pcm, rate, cues


def write_wav(path: Path, pcm: bytes, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voz", default="es_MX-claude-high", choices=sorted(VOICES))
    ap.add_argument("--escenas", help="ids separados por comas (por omisión, todas)")
    ap.add_argument("--salida", help="con --escenas: un solo WAV con esas escenas seguidas")
    a = ap.parse_args()

    scenes = json.loads((OUT / "escenas.json").read_text(encoding="utf-8"))
    if a.escenas:
        wanted = a.escenas.split(",")
        scenes = [s for s in scenes if s["id"] in wanted]
    voice = PiperVoice.load(str(voice_files(a.voz)))

    if a.salida:
        pcm, rate = b"", voice.config.sample_rate
        for s in scenes:
            p, rate, _ = synth_scene(voice, s)
            pcm += p
        write_wav(Path(a.salida), pcm, rate)
        print(f"{a.salida}: {len(pcm) / 2 / rate:.1f} s")
        return

    timing = {}
    for s in scenes:
        pcm, rate, cues = synth_scene(voice, s)
        write_wav(OUT / "audio" / f"{s['id']}.wav", pcm, rate)
        timing[s["id"]] = {"seconds": round(len(pcm) / 2 / rate, 3), "cues": cues}
        print(f"escena {s['id']}: {timing[s['id']]['seconds']:.1f} s")
    (OUT / "audio" / "tiempos.json").write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Total: {sum(v['seconds'] for v in timing.values()) / 60:.1f} min")


if __name__ == "__main__":
    main()
