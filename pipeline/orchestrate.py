from __future__ import annotations

import argparse
import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pipeline.planning.local.client import request_plan
from pipeline.planning.local.preprocess import (
    encode_frames_base64,
    preprocess_video,
    sample_frames,
)
from pipeline.planning.local.run_local_to_colab import build_request_payload
from pipeline.render.render import render
from pipeline.render.validate_plan import validate_plan


def _ts() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _set_status(
    status_path: Path,
    *,
    status: str,
    step: str,
    message: str,
    started_at: str,
    error: str | None = None,
) -> None:
    payload = {
        "status": status,
        "step": step,
        "message": message,
        "error": error,
        "startedAt": started_at,
        "updatedAt": _ts(),
    }
    _write_json(status_path, payload)


def _load_job(job_dir: Path) -> tuple[str, Path]:
    job_path = job_dir / "job.json"
    if not job_path.exists():
        raise FileNotFoundError(f"Missing job.json at {job_path}")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    video_name = str(job.get("videoName", "")).strip()
    if not video_name:
        raise ValueError("job.json is missing videoName")
    user_prompt = str(job.get("prompt", ""))
    video_path = job_dir / video_name
    if not video_path.exists():
        raise FileNotFoundError(f"Uploaded video is missing at {video_path}")
    return user_prompt, video_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full AI-Edits pipeline for one frontend upload job.")
    parser.add_argument("--job-dir", required=True, type=Path, help="Path to frontend/uploads/<jobId> directory.")
    parser.add_argument("--colab-url", required=True, help="Base URL for Colab FastAPI planner.")
    parser.add_argument("--mode", default="style", help="Planner mode hint.")
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--use-frame-array", action="store_true", help="Send sampled JPEG frames to Colab.")
    parser.add_argument(
        "--colab-video-path",
        default=None,
        help="Path visible from Colab runtime for video_path mode.",
    )
    parser.add_argument("--run-whisper", action="store_true", help="Run Whisper locally before planning.")
    parser.add_argument("--whisper-model", default="base")
    parser.add_argument("--whisper-language", default=None)
    parser.add_argument("--output-plan-name", default="final_edit_plan.json")
    parser.add_argument("--output-video-name", default="rendered.mp4")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    job_dir = args.job_dir.resolve()
    status_path = job_dir / "status.json"
    started_at = _ts()
    _set_status(
        status_path,
        status="running",
        step="preprocessing",
        message="Loading upload and collecting source metadata.",
        started_at=started_at,
    )

    try:
        user_prompt, video_path = _load_job(job_dir)

        source_meta, transcript_words = preprocess_video(
            video_path,
            run_whisper=args.run_whisper,
            whisper_model=args.whisper_model,
            whisper_language=args.whisper_language,
        )

        frame_payload: list[dict] | None = None
        if args.use_frame_array:
            frame_dir = job_dir / "frames"
            frames = sample_frames(
                video_path,
                frame_dir,
                sample_fps=args.sample_fps,
                max_frames=args.max_frames,
            )
            frame_payload = encode_frames_base64(frames, sample_fps=args.sample_fps)
        elif not args.colab_video_path:
            raise ValueError("colab-video-path is required unless use-frame-array is enabled")

        _set_status(
            status_path,
            status="running",
            step="planning",
            message="Submitting job to Colab planner and waiting for response.",
            started_at=started_at,
        )

        payload = build_request_payload(
            run_id=uuid4().hex[:10],
            source_meta=source_meta,
            transcript_words=transcript_words,
            user_prompt=user_prompt,
            mode=args.mode,
            use_frame_array=args.use_frame_array,
            video_path=video_path,
            colab_video_path=args.colab_video_path,
            frame_payload=frame_payload,
            sample_fps=args.sample_fps,
            max_frames=args.max_frames,
        )
        response = request_plan(args.colab_url, payload)
        final_plan = response["final_edit_plan"]

        plan_path = job_dir / args.output_plan_name
        _write_json(plan_path, final_plan)
        _write_json(job_dir / "plan_response.json", response)
        validate_plan(final_plan)

        _set_status(
            status_path,
            status="running",
            step="rendering",
            message="Rendering final video with Remotion.",
            started_at=started_at,
        )

        out_path = render(plan_path, video_path, job_dir / args.output_video_name)
        output_video_name = out_path.name
        output_video_url = f"/api/video-files/{job_dir.name}/{output_video_name}"
        _write_json(
            job_dir / "output-video.json",
            {
                "outputVideoName": output_video_name,
                "outputVideoUrl": output_video_url,
                "updatedAt": _ts(),
            },
        )

        _set_status(
            status_path,
            status="completed",
            step="completed",
            message="Pipeline finished successfully.",
            started_at=started_at,
        )
        return 0
    except Exception as exc:
        _set_status(
            status_path,
            status="failed",
            step="failed",
            message="Pipeline execution failed.",
            error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
            started_at=started_at,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
