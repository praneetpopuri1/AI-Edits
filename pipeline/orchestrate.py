from __future__ import annotations

import argparse
import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pipeline.planning.local.client import request_plan
from pipeline.planning.local.preprocess import (
    encode_frames_base64,
    preprocess_video,
    probe_video_raw,
    sample_frames,
)
from pipeline.planning.local.run_local_to_colab import build_request_payload
from pipeline.render.render import render


def _ts() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _append_log(job_dir: Path, line: str) -> None:
    log_path = job_dir / "pipeline.log"
    stamp = _ts()
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{stamp}] {line}\n")


def _dump_artifact(job_dir: Path, filename: str, payload: dict | list) -> None:
    _write_json(job_dir / filename, payload)


def _payload_for_logging(payload: dict) -> dict:
    cloned = json.loads(json.dumps(payload))
    vision_input = cloned.get("vision_input")
    if isinstance(vision_input, dict) and vision_input.get("type") == "frame_array":
        frames = vision_input.get("frames")
        if isinstance(frames, list):
            vision_input["frames_preview"] = frames[:3]
            vision_input["frame_count"] = len(frames)
            vision_input["frames"] = ["<omitted_base64_frames>"]
    return cloned


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


def _fail_status(
    job_dir: Path,
    status_path: Path,
    *,
    active_step: str,
    started_at: str,
    exc: BaseException,
) -> None:
    tb = traceback.format_exc()
    err_text = f"{type(exc).__name__}: {exc}\n{tb}"
    _append_log(job_dir, f"FAILED during {active_step}: {type(exc).__name__}: {exc}")
    short_msg = str(exc).strip() or type(exc).__name__
    _set_status(
        status_path,
        status="failed",
        step=active_step,
        message=f"Failed during {active_step}: {short_msg}",
        error=err_text,
        started_at=started_at,
    )
    _append_log(job_dir, "Full traceback written to status.json (error field) and tail above.")


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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _output_videos_dir() -> Path:
    out = _repo_root() / "videos" / "output_videos"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _edit_plans_dir() -> Path:
    out = _repo_root() / "edit_plans"
    out.mkdir(parents=True, exist_ok=True)
    return out


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
    (job_dir / "pipeline.log").write_text(f"[{started_at}] Pipeline run started\n", encoding="utf-8")
    _set_status(
        status_path,
        status="running",
        step="preprocessing",
        message="Loading upload and collecting source metadata.",
        started_at=started_at,
    )

    phase = "preprocessing"
    try:
        user_prompt, video_path = _load_job(job_dir)

        source_meta, transcript_words = preprocess_video(
            video_path,
            run_whisper=args.run_whisper,
            whisper_model=args.whisper_model,
            whisper_language=args.whisper_language,
        )
        _dump_artifact(job_dir, "source_meta.json", source_meta)
        _dump_artifact(job_dir, "source_video_ffprobe.json", probe_video_raw(video_path))
        _dump_artifact(job_dir, "whisper_words.json", transcript_words)
        _append_log(
            job_dir,
            f"Preprocess done: duration_s={source_meta.get('duration_s')} words={len(transcript_words)}",
        )
        if transcript_words:
            preview = " ".join(word.get("word", "") for word in transcript_words[:12]).strip()
            _append_log(job_dir, f"Whisper preview: {preview}")

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

        phase = "planning"
        _set_status(
            status_path,
            status="running",
            step="planning",
            message="Submitting job to Colab planner and waiting for response.",
            started_at=started_at,
        )
        _append_log(job_dir, "Calling Colab /jobs/plan ...")

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
        _dump_artifact(job_dir, "planner_request_payload.json", _payload_for_logging(payload))
        response = request_plan(args.colab_url, payload)
        final_plan = response["final_edit_plan"]
        _append_log(job_dir, "Colab planner returned final_edit_plan.")

        plan_path = job_dir / args.output_plan_name
        _write_json(plan_path, final_plan)
        _write_json(job_dir / "plan_response.json", response)
        pass1_raw = str(response.get("pass1_raw_response", ""))
        pass2_raw = str(response.get("pass2_raw_response", ""))
        (job_dir / "pass1_raw_response.txt").write_text(pass1_raw, encoding="utf-8")
        (job_dir / "pass2_raw_response.txt").write_text(pass2_raw, encoding="utf-8")
        edit_plan_path = _edit_plans_dir() / f"{job_dir.name}_{args.output_plan_name}"
        _write_json(edit_plan_path, final_plan)
        _append_log(
            job_dir,
            f"Saved model plan to {plan_path} and {edit_plan_path}. "
            "Overlay URLs are resolved and validated inside render().",
        )

        phase = "rendering"
        _set_status(
            status_path,
            status="running",
            step="rendering",
            message="Rendering final video with Remotion.",
            started_at=started_at,
        )
        _append_log(job_dir, "Starting Remotion render ...")

        output_filename = f"{job_dir.name}_{args.output_video_name}"
        render_debug_dir = job_dir / "render_debug"
        out_path, overlay_warnings = render(
            plan_path,
            video_path,
            _output_videos_dir() / output_filename,
            debug_dir=render_debug_dir,
        )
        for ow in overlay_warnings:
            _append_log(job_dir, ow)
        output_video_name = out_path.name
        output_video_url = f"/api/output-videos/{output_video_name}"
        _write_json(
            job_dir / "output-video.json",
            {
                "outputVideoName": output_video_name,
                "outputVideoUrl": output_video_url,
                "updatedAt": _ts(),
            },
        )
        _append_log(job_dir, f"Render complete: {output_video_name}")

        _set_status(
            status_path,
            status="completed",
            step="completed",
            message="Pipeline finished successfully.",
            started_at=started_at,
        )
        return 0
    except Exception as exc:
        _fail_status(job_dir, status_path, active_step=phase, started_at=started_at, exc=exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
