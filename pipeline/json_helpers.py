import json
from typing import Any


def extract_video_json(raw_output: str) -> dict[str, Any]:
    """
    Extracts the first valid JSON object that matches the expected VLM output shape.
    It ignores text before/after the JSON, including <think>...</think>.
    """
    decoder = json.JSONDecoder()

    for i, ch in enumerate(raw_output):
        if ch != "{":
            continue

        try:
            obj, _ = decoder.raw_decode(raw_output[i:])
        except json.JSONDecodeError:
            continue

        if (
            isinstance(obj, dict)
            and "detailed_video_explanation" in obj
            and "segments" in obj
        ):
            return obj

    raise ValueError("No valid video-explanation JSON object found in output.")


def validate_video_json(
    data: dict[str, Any],
    video_duration_s: float | None = None,
) -> list[str]:
    """
    Validates structure + timestamp consistency.
    Returns a list of errors.
    If the list is empty, the JSON is valid.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Top-level JSON must be an object."]

    summary = data.get("detailed_video_explanation")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("'detailed_video_explanation' must be a non-empty string.")

    segments = data.get("segments")
    if not isinstance(segments, list) or len(segments) == 0:
        errors.append("'segments' must be a non-empty list.")
        return errors

    prev_end = None

    for i, seg in enumerate(segments):
        prefix = f"segments[{i}]"

        if not isinstance(seg, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        label = seg.get("label")
        start = seg.get("start_sec")
        end = seg.get("end_sec")

        if not isinstance(label, str) or not label.strip():
            errors.append(f"{prefix}.label must be a non-empty string.")

        if not isinstance(start, (int, float)):
            errors.append(f"{prefix}.start_sec must be a number.")
            continue

        if not isinstance(end, (int, float)):
            errors.append(f"{prefix}.end_sec must be a number.")
            continue

        if start < 0:
            errors.append(f"{prefix}.start_sec must be >= 0.")

        if end <= start:
            errors.append(f"{prefix}.end_sec must be greater than start_sec.")

        if video_duration_s is not None and end > video_duration_s:
            errors.append(
                f"{prefix}.end_sec={end} exceeds video duration {video_duration_s}."
            )

        if prev_end is not None:
            if start < prev_end:
                errors.append(
                    f"{prefix}.start_sec={start} overlaps previous segment ending at {prev_end}."
                )

        prev_end = end

    return errors

def extract_thinking_trace(raw_output: str) -> str | None:
    start_tag = "<think>"
    end_tag = "</think>"

    start = raw_output.find(start_tag)
    end = raw_output.find(end_tag)

    if start == -1 or end == -1 or end <= start:
        return None

    start += len(start_tag)
    return raw_output[start:end].strip()


# -------------------------
# Example usage
# -------------------------

# raw_vlm_output = """
# <think>
# Some reasoning text...
# </think>

# {
#   "detailed_video_explanation": "A Twitch streamer hosts a game show event where participants in purple uniforms engage in a challenge involving shooting targets of other streamers to determine who wins a million dollars. The video includes the streamer's introduction, game setup explanation, interactive gameplay, and the reveal of the most targeted streamers.",
#   "segments": [
#     {
#       "label": "streamer_introduction",
#       "start_sec": 0.0,
#       "end_sec": 22.0
#     },
#     {
#       "label": "game_show_introduction",
#       "start_sec": 22.0,
#       "end_sec": 75.0
#     },
#     {
#       "label": "challenge_rules_explanation",
#       "start_sec": 75.0,
#       "end_sec": 150.0
#     },
#     {
#       "label": "first_shooting_round",
#       "start_sec": 150.0,
#       "end_sec": 300.0
#     },
#     {
#       "label": "interactive_shooting_games",
#       "start_sec": 300.0,
#       "end_sec": 500.0
#     },
#     {
#       "label": "revealing_targeted_streamers",
#       "start_sec": 500.0,
#       "end_sec": 800.0
#     },
#     {
#       "label": "conclusion_and_wrapup",
#       "start_sec": 800.0,
#       "end_sec": 962.0
#     }
#   ]
# }
# """

# data = extract_video_json(raw_vlm_output)

# errors = validate_video_json(data, video_duration_s=962.0)

# if errors:
#     print("Invalid JSON output:")
#     for err in errors:
#         print("-", err)
# else:
#     print("Valid JSON output.")
#     print(json.dumps(data, indent=2))