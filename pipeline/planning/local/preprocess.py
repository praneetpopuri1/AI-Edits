from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any

from pipeline.planning.shared.metadata import get_video_metadata


def transcribe_with_whisper(
    video_path: Path,
    *,
    model_name: str = "base",
    language: str | None = None,
) -> list[dict[str, Any]]:
    """
    Run Whisper locally and return renderer-ready word timestamps.

    Requires `openai-whisper` package and ffmpeg on PATH.
    """
    try:
        import whisper
    except ImportError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "Whisper dependency missing. Install with `pip install openai-whisper`."
        ) from exc

    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(video_path),
        word_timestamps=True,
        language=language,
        verbose=False,
    )

    words: list[dict[str, Any]] = []
    for segment in result.get("segments", []):
        for word in segment.get("words", []):
            token = str(word.get("word", "")).strip()
            if not token:
                continue
            words.append(
                {
                    "word": token,
                    "start_s": round(float(word["start"]), 2),
                    "end_s": round(float(word["end"]), 2),
                }
            )
    return words


def sample_frames(
    video_path: Path,
    output_dir: Path,
    *,
    sample_fps: float = 2.0,
    max_frames: int = 160,
) -> list[Path]:
    """
    Sample frames locally with ffmpeg for optional frame-array payloads.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_pattern = output_dir / "frame_%06d.jpg"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps}",
        "-qscale:v",
        "2",
        str(frame_pattern),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frames = sorted(output_dir.glob("frame_*.jpg"))
    if len(frames) <= max_frames:
        return frames

    # Keep evenly spaced samples when ffmpeg produced too many frames.
    step = len(frames) / float(max_frames)
    selected = [frames[int(i * step)] for i in range(max_frames)]
    selected_set = set(selected)
    for frame in frames:
        if frame not in selected_set:
            frame.unlink(missing_ok=True)
    return selected


def encode_frames_base64(frames: list[Path], sample_fps: float) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for idx, frame in enumerate(frames):
        b64 = base64.b64encode(frame.read_bytes()).decode("ascii")
        payload.append(
            {
                "jpeg_b64": b64,
                "time_s": round(idx / sample_fps, 3),
            }
        )
    return payload


def write_run_artifacts(run_dir: Path, artifacts: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    for key, value in artifacts.items():
        out = run_dir / f"{key}.json"
        with out.open("w", encoding="utf-8") as f:
            json.dump(value, f, indent=2)


def preprocess_video(
    video_path: Path,
    *,
    run_whisper: bool,
    whisper_model: str,
    whisper_language: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_meta = get_video_metadata(str(video_path))
    words: list[dict[str, Any]] = []
    if run_whisper:
        words = transcribe_with_whisper(
            video_path,
            model_name=whisper_model,
            language=whisper_language,
        )
    return source_meta, words


def probe_video_raw(video_path: Path) -> dict[str, Any]:
    """
    Return full ffprobe stream/format data for debugging orientation and centering issues.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(video_path),
    ]
    out = subprocess.check_output(cmd).decode("utf-8")
    return json.loads(out)

