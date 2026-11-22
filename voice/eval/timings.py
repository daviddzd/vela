"""Measure transcription time (faster-whisper small, int8, CPU) for 10 / 30 / 60 s notes and LLM report time
for a short and a long note. The notes are SYNTHETIC Spanish speech (espeak-ng): good to measure TIME, not
accuracy (accuracy is measured with real voices in bias_wer.py).
Run:  docker compose run --rm voice python -m voice.eval.timings
"""
import json
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import pandas as pd

from app.services import llm_report

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "voice" / "eval" / "results"


def synth(text: str, path: str) -> float:
    subprocess.run(["espeak-ng", "-v", "es-419", "-s", "150", "-w", path, text], check=True, capture_output=True)
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    from faster_whisper import WhisperModel
    OUT.mkdir(parents=True, exist_ok=True)
    phrases = pd.read_csv(ROOT / "data" / "voice" / "external_phrases.csv").text.tolist()
    t0 = time.perf_counter()
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
    rows = [{"what": "load whisper small int8", "seconds": round(time.perf_counter() - t0, 1)}]
    for target in (10, 30, 60):
        text, i = "", 0
        with tempfile.TemporaryDirectory() as d:
            wav = f"{d}/n.wav"
            while True:                          # grow the text until the audio is ~target seconds
                text += " " + phrases[i % len(phrases)]
                i += 1
                dur = synth(text, wav)
                if dur >= target - 2:
                    break
            for run in (1, 2):
                t = time.perf_counter()
                segs, info = model.transcribe(wav, language="es", beam_size=5, vad_filter=True)
                list(segs)
                rows.append({"what": f"transcribe ~{target} s note (run {run})", "audio_s": round(dur, 1),
                             "seconds": round(time.perf_counter() - t, 1)})
    long_note = " ".join(phrases[46:50] + phrases[87:90])
    for label, note in (("short", phrases[100]), ("long", long_note)):
        _, status, problem, ms = llm_report.generate(note, "urgent")
        rows.append({"what": f"LLM report, {label} note ({len(note.split())} words)", "seconds": round(ms / 1000, 1),
                     "status": status, "problem": problem})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "timings.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
