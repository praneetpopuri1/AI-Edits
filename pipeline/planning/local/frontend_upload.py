from __future__ import annotations

import json
from pathlib import Path

_VIDEO_SUFFIXES = (".mp4", ".mov", ".webm", ".mkv", ".m4v")


def repo_root() -> Path:
    """Repository root (directory containing `pipeline/`)."""
    return Path(__file__).resolve().parents[3]


def resolve_frontend_upload_dir(job_id: str, *, uploads_root: Path) -> Path:
    """
    Resolve `frontend/uploads/<job_id>/` (or custom root) and validate it exists.
    """
    if not job_id or not job_id.strip():
        raise SystemExit("--frontend-upload-job-id must be a non-empty job id.")

    root = repo_root()
    base = uploads_root if uploads_root.is_absolute() else (root / uploads_root)
    upload_dir = (base / job_id.strip()).resolve()

    if not upload_dir.is_dir():
        raise SystemExit(f"Upload directory not found: {upload_dir}")

    return upload_dir


def _legacy_video_path(upload_dir: Path) -> Path:
    candidates: list[Path] = []
    for ext in _VIDEO_SUFFIXES:
        candidates.extend(p for p in upload_dir.glob(f"*{ext}") if p.is_file())

    candidates = [p for p in candidates if not p.name.lower().startswith("output")]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit(f"No video file found under {upload_dir}")
    raise SystemExit(
        f"Multiple video files under {upload_dir}; upload again from the web UI "
        "so job.json is written, or remove extra videos."
    )


def load_frontend_upload_job(upload_dir: Path) -> tuple[Path, str]:
    """
    Return (absolute video path, user prompt string) for a Next.js upload folder.

    Prefers job.json (current); falls back to prompt.txt + a single video file.
    """
    job_path = upload_dir / "job.json"
    if job_path.is_file():
        data = json.loads(job_path.read_text(encoding="utf-8"))
        video_name = data.get("videoName")
        if not isinstance(video_name, str) or not video_name.strip():
            raise SystemExit(f"Invalid or missing videoName in {job_path}")
        prompt_val = data.get("prompt", "")
        if not isinstance(prompt_val, str):
            prompt_val = ""
        video_path = (upload_dir / video_name).resolve()
        if not video_path.is_file():
            raise SystemExit(f"Uploaded video missing: {video_path}")
        return video_path, prompt_val

    prompt_path = upload_dir / "prompt.txt"
    prompt_text = prompt_path.read_text(encoding="utf-8").strip() if prompt_path.is_file() else ""
    return _legacy_video_path(upload_dir).resolve(), prompt_text
