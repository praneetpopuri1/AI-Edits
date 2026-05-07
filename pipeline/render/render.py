"""
Copy assets into the Remotion `public/` folder, validate the plan, and run `npx remotion render`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from pipeline.render.overlay_resolver import resolve_overlay_assets
    from pipeline.render.validate_plan import validate_plan
except ImportError:  # pragma: no cover - keeps direct script usage working
    from overlay_resolver import resolve_overlay_assets
    from validate_plan import validate_plan
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _renderer_dir() -> Path:
    return _repo_root() / "renderer"


def _public_dir() -> Path:
    p = _renderer_dir() / "public"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _normalized_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _copy_if_needed(src: Path, dest: Path) -> None:
    # On Windows, `source.MOV` and `source.mov` can resolve to the same file.
    # Skip the copy so `copy2()` does not fail trying to copy onto itself.
    if _normalized_path(src) == _normalized_path(dest):
        return
    shutil.copy2(src, dest)


def _remotion_command(props_path: Path, out_path: Path) -> list[str]:
    remotion_args = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "EditPlanVideo",
        str(out_path),
        f"--props={props_path}",
    ]
    if os.name == "nt":
        return ["cmd.exe", "/c", *remotion_args]
    return remotion_args


def _normalized_output_path(out_path: Path) -> Path:
    # Remotion validates output extensions case-sensitively. Normalize common
    # container suffixes so `rendered.MOV` works the same as `rendered.mov`.
    suffix = out_path.suffix
    if suffix.lower() in {".mp4", ".mov", ".mkv"}:
        return out_path.with_suffix(suffix.lower())
    return out_path


def _write_debug_artifact(debug_dir: Path | None, filename: str, payload: str) -> None:
    if debug_dir is None:
        return
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / filename).write_text(payload, encoding="utf-8")


def render(
    plan_path: Path,
    source_video: Path,
    out_path: Path,
    *,
    music_track: Path | None = None,
    source_video_public_name: str | None = None,
    music_public_name: str = "music.mp3",
    debug_dir: Path | None = None,
) -> tuple[Path, list[str]]:
    out_path = _normalized_output_path(out_path).resolve()
    source_video = source_video.resolve()
    plan_path = plan_path.resolve()

    with plan_path.open(encoding="utf-8") as f:
        plan = json.load(f)

    public = _public_dir()
    plan, overlay_warnings = resolve_overlay_assets(plan, public)
    for warning in overlay_warnings:
        print(f"[overlay-resolver] {warning}", file=sys.stderr)
        print(f"[overlay-resolver] {warning}", flush=True)

    validate_plan(plan)
    _write_debug_artifact(
        debug_dir,
        "validated_plan_for_render.json",
        f"{json.dumps(plan, indent=2)}\n",
    )

    if source_video_public_name is None:
        # Preserve original extension so Remotion gets the right media type
        # (e.g. .mov remains .mov rather than being renamed to .mp4).
        suffix = source_video.suffix.lower() or ".mp4"
        source_video_public_name = f"source{suffix}"
    dest_video = public / source_video_public_name
    _copy_if_needed(source_video, dest_video)

    props: dict = {
        "editPlan": plan,
        "sourceVideoSrc": source_video_public_name,
    }
    if music_track is not None:
        _copy_if_needed(music_track, public / music_public_name)
        props["musicSrc"] = music_public_name

    renderer = _renderer_dir()
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as tmp:
        json.dump(props, tmp, indent=2)
        props_path = Path(tmp.name)

    try:
        cmd = _remotion_command(props_path, out_path)
        _write_debug_artifact(
            debug_dir,
            "render_inputs.json",
            (
                json.dumps(
                    {
                        "plan_path": str(plan_path),
                        "source_video": str(source_video),
                        "output_path": str(out_path),
                        "renderer_cwd": str(renderer),
                        "source_video_public_name": source_video_public_name,
                        "music_public_name": music_public_name if music_track is not None else None,
                        "music_track": str(music_track.resolve()) if music_track else None,
                        "command": cmd,
                    },
                    indent=2,
                )
                + "\n"
            ),
        )
        _write_debug_artifact(
            debug_dir,
            "remotion_props.json",
            f"{json.dumps(props, indent=2)}\n",
        )
        subprocess.run(cmd, cwd=renderer, check=True)
    finally:
        props_path.unlink(missing_ok=True)

    return out_path, overlay_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Render edit plan to MP4 via Remotion.")
    parser.add_argument("--plan", required=True, type=Path, help="Path to edit_plan.json")
    parser.add_argument("--source-video", required=True, type=Path, help="Source video file")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("out/rendered.mp4"),
        help="Output MP4 path (default: out/rendered.mp4)",
    )
    parser.add_argument("--music", type=Path, default=None, help="Optional music file to copy to public/")
    args = parser.parse_args()

    normalized_out = _normalized_output_path(args.out).resolve()
    normalized_out.parent.mkdir(parents=True, exist_ok=True)
    try:
        out, _warnings = render(args.plan, args.source_video, normalized_out, music_track=args.music)
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
