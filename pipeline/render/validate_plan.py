"""
Validate an edit plan JSON against edit_plan_schema.json plus semantic rules from edit_plan_schema_design.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_schema() -> dict[str, Any]:
    schema_path = _repo_root() / "edit_plan_schema.json"
    with schema_path.open(encoding="utf-8") as f:
        return json.load(f)


def _validate_json_schema(instance: dict[str, Any]) -> None:
    schema = _load_schema()
    Draft7Validator(schema).validate(instance)


def _semantic_validate(plan: dict[str, Any]) -> None:
    sv = plan["source_video"]
    duration = float(sv["duration_s"])
    segments = plan["segments"]

    # 1) Full coverage: partition [0, duration) contiguous, no gaps/overlaps
    t = 0.0
    for i, seg in enumerate(segments):
        start_s = float(seg["start_s"])
        end_s = float(seg["end_s"])
        if abs(start_s - t) > 1e-4:
            raise ValueError(
                f"segments[{i}] does not continue from previous end: expected start {t}, got {start_s}"
            )
        if end_s <= start_s:
            raise ValueError(f"segments[{i}] must have end_s > start_s")
        t = end_s
    if abs(t - duration) > 1e-3:
        raise ValueError(
            f"segments must cover source_video.duration_s ({duration}); covered up to {t}"
        )

    # 2) Temporal ordering for optional arrays
    def check_sorted(name: str, items: list[dict[str, Any]]) -> None:
        last = -1.0
        for i, it in enumerate(items):
            s = float(it["start_s"])
            if s < last:
                raise ValueError(f"{name}[{i}] is not ordered by start_s")
            last = s

    if plan.get("zooms"):
        check_sorted("zooms", plan["zooms"])
        for i, z in enumerate(plan["zooms"]):
            if float(z["end_s"]) <= float(z["start_s"]):
                raise ValueError(f"zooms[{i}] must have end_s > start_s")
        for i in range(len(plan["zooms"]) - 1):
            a, b = plan["zooms"][i], plan["zooms"][i + 1]
            if float(a["end_s"]) > float(b["start_s"]) + 1e-6:
                raise ValueError("zooms must not overlap in time")

    if plan.get("overlays"):
        check_sorted("overlays", plan["overlays"])
        for i, o in enumerate(plan["overlays"]):
            start_s = float(o["start_s"])
            end_s = float(o["end_s"])
            if end_s <= start_s:
                raise ValueError(f"overlays[{i}] must have end_s > start_s")
            if start_s < 0 or end_s > duration + 1e-3:
                raise ValueError(f"overlays[{i}] out of [0, duration_s]")
            image_url = str(o.get("image_url", "")).strip()
            if not image_url:
                raise ValueError(f"overlays[{i}] missing resolved image_url")
            if image_url.startswith(("http://", "https://")):
                raise ValueError(f"overlays[{i}] image_url must be local public path")
            if image_url.startswith("/") or ".." in Path(image_url).parts:
                raise ValueError(f"overlays[{i}] image_url is not a safe local path")
            if not image_url.startswith("overlays/"):
                raise ValueError(f"overlays[{i}] image_url must be under overlays/")
    if plan.get("text_overlays"):
        check_sorted("text_overlays", plan["text_overlays"])

    # 3) Cut segments require cut_reason
    for i, seg in enumerate(segments):
        if seg["action"] == "cut" and not seg.get("cut_reason"):
            raise ValueError(f"segments[{i}] action=cut requires cut_reason")

    # 4) transition_in only on keep after cut
    for i, seg in enumerate(segments):
        if seg["action"] != "keep":
            continue
        ti = seg.get("transition_in")
        if ti and ti.get("type") not in (None, "none"):
            prev = segments[i - 1] if i > 0 else None
            if prev is None or prev["action"] != "cut":
                raise ValueError(
                    f"segments[{i}]: transition_in is only valid when previous segment is a cut"
                )

    # 5) Bounds
    for i, seg in enumerate(segments):
        if float(seg["start_s"]) < 0 or float(seg["end_s"]) > duration + 1e-3:
            raise ValueError(f"segments[{i}] out of [0, duration_s]")

    if plan.get("zooms"):
        for i, z in enumerate(plan["zooms"]):
            if float(z["start_s"]) < 0 or float(z["end_s"]) > duration + 1e-3:
                raise ValueError(f"zooms[{i}] out of [0, duration_s]")


def validate_plan(plan: dict[str, Any]) -> None:
    _validate_json_schema(plan)
    _semantic_validate(plan)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_plan.py <edit_plan.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    with path.open(encoding="utf-8") as f:
        plan = json.load(f)
    try:
        validate_plan(plan)
    except (ValidationError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
