"""Speech-recognition bias check (docs/spec/05): word error rate (WER) per group and whether any EMERGENCY is
lost because of a transcription error. Two sources, both local (audio is never committed to Git):

1. Team recordings:  voice/eval/audio/<person>/<EXT-xxx>.(webm|m4a|ogg|wav|mp3)  +  voice/eval/audio/team.csv
   (columns: person, age_band, gender, accent, consent=yes). Reference text = data/voice/external_phrases.csv.
   For each clip: WER, and the triage of the TRANSCRIPT vs the triage of the REFERENCE text (same rules +
   classifier): an emergency on the reference that is not an emergency on the transcript = lost by Whisper.
2. Mozilla Common Voice (CC0), Spanish, downloaded by hand from Mozilla Data Collective:
   --cv-dir <folder with validated.tsv and clips/>. WER per age, gender and accent (sample of --cv-n clips).

Run:  docker compose run --rm voice python -m voice.eval.bias_wer [--cv-dir /repo/voice/eval/audio/cv-es] [--cv-n 300]
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import jiwer
import pandas as pd

from app.services.triage_rules import normalize, rule_hits
from voice.triage import classifier

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "voice" / "eval" / "audio"
OUT = ROOT / "voice" / "eval" / "results"
EXTS = (".webm", ".m4a", ".ogg", ".wav", ".mp3", ".opus")


def clean(t: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", normalize(t)).split())   # no punctuation, lowercase, no accents


def level(text: str, model) -> str:
    return "emergency" if rule_hits(text) else classifier.predict(model, [text])[0]["label"]


def team(model, whisper) -> pd.DataFrame | None:
    meta_path = AUDIO / "team.csv"
    if not meta_path.exists():
        print("Sin grabaciones del equipo (falta voice/eval/audio/team.csv). Ver voice/eval/README.md.")
        return None
    meta = pd.read_csv(meta_path)
    meta = meta[meta.consent.str.lower().isin(["yes", "si", "sí"])]
    ref = pd.read_csv(ROOT / "data/voice/external_phrases.csv").set_index("phrase_id")
    rows = []
    for _, m in meta.iterrows():
        for f in sorted((AUDIO / m.person).glob("EXT-*")):
            if f.suffix.lower() not in EXTS or f.stem not in ref.index:
                continue
            segs, _ = whisper.transcribe(str(f), language="es", beam_size=5, vad_filter=True)
            hyp = " ".join(s.text.strip() for s in segs)
            r = ref.loc[f.stem]
            rows.append({"person": m.person, "age_band": m.age_band, "gender": m.gender, "accent": m.accent,
                         "phrase_id": f.stem, "label": r.label, "reference": r.text, "transcript": hyp,
                         "wer": jiwer.wer(clean(r.text), clean(hyp) or "-"),
                         "level_reference": level(r.text, model), "level_transcript": level(hyp, model)})
    df = pd.DataFrame(rows)
    if df.empty:
        print("team.csv existe pero no hay audios EXT-xxx con consentimiento.")
        return None
    df["lost_by_transcription"] = (df.level_reference == "emergency") & (df.level_transcript != "emergency")
    df.to_csv(OUT / "bias_team_clips.csv", index=False)
    print("\n== Equipo: WER por persona / grupo")
    print(df.groupby(["person", "age_band", "gender", "accent"]).agg(clips=("wer", "size"), wer=("wer", "mean"),
          emergencias_perdidas=("lost_by_transcription", "sum")).round(3).to_string())
    lost = df[df.lost_by_transcription]
    print("\nEmergencias perdidas por un error de transcripción:", len(lost))
    for _, x in lost.iterrows():
        print(f"  {x.person} {x.phrase_id}: «{x.reference}» → «{x.transcript}»")
    return df


def common_voice(cv_dir: Path, n: int, whisper) -> pd.DataFrame | None:
    tsv = cv_dir / "validated.tsv"
    if not tsv.exists():
        print(f"Sin Common Voice en {cv_dir} (falta validated.tsv). Ver voice/eval/README.md.")
        return None
    meta = pd.read_csv(tsv, sep="\t", quoting=3, usecols=lambda c: c in {"path", "sentence", "age", "gender", "accents"})
    meta = meta.dropna(subset=["age"]).sample(min(n, len(meta)), random_state=2026)
    rows = []
    for _, m in meta.iterrows():
        segs, _ = whisper.transcribe(str(cv_dir / "clips" / m.path), language="es", beam_size=5, vad_filter=True)
        hyp = " ".join(s.text.strip() for s in segs)
        rows.append({**m.to_dict(), "transcript": hyp, "wer": jiwer.wer(clean(m.sentence), clean(hyp) or "-")})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "bias_common_voice.csv", index=False)
    for col in ("age", "gender", "accents"):
        print(f"\n== Common Voice: WER por {col}")
        print(df.groupby(col).wer.agg(["size", "mean"]).round(3).to_string())
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv-dir", type=Path, default=AUDIO / "cv-es")
    ap.add_argument("--cv-n", type=int, default=300)
    args = ap.parse_args()
    from faster_whisper import WhisperModel
    OUT.mkdir(parents=True, exist_ok=True)
    whisper = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
    model = classifier.load()
    team(model, whisper)
    common_voice(args.cv_dir, args.cv_n, whisper)


if __name__ == "__main__":
    main()
