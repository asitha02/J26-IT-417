"""Measure speech-to-text accuracy (WER) and speed (real-time factor) for different Whisper setups.

Whisper is not trained from scratch here. Instead the transcription component is *tuned by
experiment*: a short audio sample is transcribed by hand-corrected reference, then every
model / decoding setting is scored on it, and the fastest setting that is still accurate is chosen.

Usage (run from the backend folder, venv active):

  # 1. cut a sample out of a video and create a DRAFT reference transcript
  python -m tools.asr_benchmark prepare --url https://www.youtube.com/watch?v=... --name lecture1 --minutes 3

  # 2. open data/asr_eval/lecture1/reference.txt and CORRECT it by hand while listening to audio.wav
  #    (this manual correction is the human-labelled ground truth - do not skip it)

  # 3. benchmark every setting against your corrected reference
  python -m tools.asr_benchmark run --name lecture1 --prompt "terms, names, jargon from the video"

Outputs data/asr_eval/<name>/results.md and results.json.
Metrics: WER = (substitutions + deletions + insertions) / reference words (lower is better).
         RTF = processing time / audio length (lower is faster; speed = 1 / RTF x real time).
"""

import argparse
import json
import os
import re
import sys
import time
import wave
from pathlib import Path

SAMPLE_RATE = 16000
DEFAULT_MODELS = "tiny.en,base.en,distil-small.en,small.en"
EVAL_ROOT = Path("data/asr_eval")


# ----------------------------------------------------------------------------- metrics
def normalize(text: str) -> list[str]:
    """Lower-case words only: punctuation and capitalisation are not scored."""
    text = text.lower().replace("-", " ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate via word-level Levenshtein distance."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        raise ValueError("Reference transcript is empty.")
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def recommend(rows: list[dict], tolerance: float = 0.01) -> dict:
    """Fastest setting whose WER is within `tolerance` (absolute) of the best WER."""
    best = min(r["wer"] for r in rows)
    ok = [r for r in rows if r["wer"] <= best + tolerance]
    return min(ok, key=lambda r: r["rtf"])


# ----------------------------------------------------------------------------- audio io
def _write_wav(path: Path, audio) -> None:
    import numpy as np

    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm.tobytes())


def _read_wav(path: Path):
    import numpy as np

    with wave.open(str(path), "rb") as f:
        raw = f.readframes(f.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0


# ----------------------------------------------------------------------------- commands
def prepare(args) -> None:
    from faster_whisper import WhisperModel, decode_audio

    from app.transcription.downloader import download_audio

    out = EVAL_ROOT / args.name
    out.mkdir(parents=True, exist_ok=True)
    print("Downloading audio...")
    res = download_audio(args.url, out / "_dl", max_duration=4 * 3600)
    audio = decode_audio(str(res.path), sampling_rate=SAMPLE_RATE)
    start, length = int(args.start * 60 * SAMPLE_RATE), int(args.minutes * 60 * SAMPLE_RATE)
    clip = audio[start : start + length]
    _write_wav(out / "audio.wav", clip)
    res.path.unlink(missing_ok=True)
    (out / "_dl").rmdir()

    print(f"Making a draft transcript with {args.draft_model} (you must correct it by hand)...")
    model = WhisperModel(args.draft_model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(clip, beam_size=5, language="en", vad_filter=True)
    (out / "reference.txt").write_text("\n".join(s.text.strip() for s in segments) + "\n", encoding="utf-8")
    print(
        f"\nDone: {out / 'audio.wav'} ({len(clip) / SAMPLE_RATE:.0f} s)\n"
        f"NEXT: listen to audio.wav and correct every error in {out / 'reference.txt'}.\n"
        "The draft came from a Whisper model, so until you correct it the scores favour that model."
    )


def _transcribe(pipe, audio, beam: int, batched: bool, prompt: str | None):
    kwargs = dict(beam_size=beam, language="en", vad_filter=True, initial_prompt=prompt or None)
    if batched:
        kwargs["batch_size"] = 8
    segments, _ = pipe.transcribe(audio, **kwargs)
    return " ".join(s.text.strip() for s in segments)  # consuming the generator = the real decoding work


def run(args) -> None:
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    folder = EVAL_ROOT / args.name
    audio = _read_wav(folder / "audio.wav")
    reference = (folder / "reference.txt").read_text(encoding="utf-8")
    seconds = len(audio) / SAMPLE_RATE
    threads = args.threads or os.cpu_count() or 4
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    beams = [int(b) for b in args.beams.split(",")]

    rows: list[dict] = []
    for name in [m.strip() for m in args.models.split(",") if m.strip()]:
        t0 = time.perf_counter()
        model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads)
        load = time.perf_counter() - t0
        batched_pipe = BatchedInferencePipeline(model=model)
        for mode in modes:
            for beam in beams:
                t1 = time.perf_counter()
                hyp = _transcribe(batched_pipe if mode == "batched" else model, audio, beam, mode == "batched", None)
                proc = time.perf_counter() - t1
                row = {"model": name, "beam": beam, "mode": mode, "wer": round(wer(reference, hyp), 4),
                       "rtf": round(proc / seconds, 3), "seconds": round(proc, 1), "load_s": round(load, 1)}
                rows.append(row)
                print(f"{name:16} beam={beam} {mode:8} WER {row['wer'] * 100:5.1f}%  RTF {row['rtf']:.3f}", flush=True)

    best = recommend(rows, args.tolerance)
    prompt_row = None
    if args.prompt:
        model = WhisperModel(best["model"], device="cpu", compute_type="int8", cpu_threads=threads)
        pipe = BatchedInferencePipeline(model=model) if best["mode"] == "batched" else model
        t1 = time.perf_counter()
        hyp = _transcribe(pipe, audio, best["beam"], best["mode"] == "batched", args.prompt)
        proc = time.perf_counter() - t1
        prompt_row = {"wer": round(wer(reference, hyp), 4), "rtf": round(proc / seconds, 3)}

    _report(folder, rows, best, prompt_row, seconds, len(normalize(reference)), args)


def _report(folder: Path, rows, best, prompt_row, seconds, ref_words, args) -> None:
    lines = [
        f"# ASR benchmark - {args.name}",
        "",
        f"Sample: {seconds:.0f} s of audio, {ref_words} reference words (hand-corrected). CPU, int8, "
        f"{args.threads or os.cpu_count()} threads, VAD on.",
        "",
        "| Model | Beam | Mode | WER % | RTF | Speed (x real time) |",
        "|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (r["wer"], r["rtf"])):
        mark = " **<- chosen**" if r is best else ""
        lines.append(
            f"| {r['model']}{mark} | {r['beam']} | {r['mode']} | {r['wer'] * 100:.1f} | {r['rtf']:.3f} | {1 / r['rtf']:.1f} |"
        )
    lines += [
        "",
        f"**Choice rule:** the fastest setting whose WER is within {args.tolerance * 100:.1f} percentage point(s) "
        "of the best WER.",
        f"**Chosen:** `{best['model']}`, beam {best['beam']}, {best['mode']} - WER {best['wer'] * 100:.1f}%, "
        f"{1 / best['rtf']:.1f}x real time.",
    ]
    if prompt_row:
        delta = (prompt_row["wer"] - best["wer"]) * 100
        lines.append(
            f"**Domain prompt** (\"{args.prompt}\") on the chosen setting: WER {prompt_row['wer'] * 100:.1f}% "
            f"({delta:+.1f} points), RTF {prompt_row['rtf']:.3f}."
        )
    (folder / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / "results.json").write_text(
        json.dumps({"rows": rows, "chosen": best, "prompt": prompt_row, "audio_seconds": seconds}, indent=2),
        encoding="utf-8",
    )
    print("\n" + "\n".join(lines))
    print(f"\nSaved {folder / 'results.md'}")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("prepare", help="cut an audio sample and write a draft reference transcript")
    a.add_argument("--url", required=True)
    a.add_argument("--name", required=True)
    a.add_argument("--start", type=float, default=0.0, help="start minute within the video")
    a.add_argument("--minutes", type=float, default=3.0)
    a.add_argument("--draft-model", default="small.en")
    a.set_defaults(func=prepare)

    b = sub.add_parser("run", help="benchmark settings against the corrected reference")
    b.add_argument("--name", required=True)
    b.add_argument("--models", default=DEFAULT_MODELS)
    b.add_argument("--beams", default="1,5")
    b.add_argument("--modes", default="batched", help="comma list of: batched, plain")
    b.add_argument("--threads", type=int, default=0)
    b.add_argument("--tolerance", type=float, default=0.01, help="WER slack (absolute) when choosing the fastest")
    b.add_argument("--prompt", default=None, help="domain words to bias decoding (initial_prompt)")
    b.set_defaults(func=run)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
