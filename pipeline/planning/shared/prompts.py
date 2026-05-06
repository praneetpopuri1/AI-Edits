from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TRANSCRIPT_WORD_LIMIT = 1000
PROMPT_TEMPLATE_PATH = Path(__file__).with_name("prompt_templates.json")


EDIT_PLAN_CONTRACT = """
Return one JSON object with edit decisions only.
Do not try to output a fully-complete final schema: backend compiles defaults and validates.

Decision object shape (all fields optional):
{
  "segments": [
    {
      "start_s": number,
      "end_s": number,
      "action": "keep" | "cut",
      "cut_reason": "silence" | "filler" | "repetition" | "off_topic" | "pacing" | "other",
      "speed": number,
      "transition_in": {"type": "none" | "crossfade" | "fade_from_black" | "wipe_left" | "wipe_right" | "wipe_up", "duration_s": number}
    }
  ],
  "captions": {
    "enabled": boolean,
    "position": "bottom_center" | "top_center" | "center" | "bottom_left" | "bottom_right",
    "grouping": "word_by_word" | "phrase" | "sentence",
    "emphasis_by_index": {"12": "bold", "24": "highlight"},
    "omit_indices": [13, 14],
    "words": [{"word": "token", "emphasis": "none" | "highlight" | "bold" | "color_pop", "omit": true}]
  },
  "zooms": [{"start_s": number, "end_s": number, "scale": number, "anchor": "top_left" | "top_center" | "top_right" | "center_left" | "center" | "center_right" | "bottom_left" | "bottom_center" | "bottom_right" | "custom", "anchor_xy": {"x": number, "y": number}, "easing": "ease_in_out" | "ease_in" | "ease_out" | "linear" | "spring"}],
  "overlays": [{"start_s": number, "end_s": number, "asset_type": "stock_photo" | "icon" | "generated_illustration" | "diagram", "visual_description": string, "search_query": string, "style": string, "position": "fullscreen" | "picture_in_picture" | "left_third" | "right_third" | "top_half" | "bottom_half" | "corner_tr" | "corner_tl" | "corner_br" | "corner_bl", "animation": "none" | "fade_in" | "slide_in_right" | "slide_in_left" | "slide_in_up" | "pop" | "scale_up"}],
  "text_overlays": [{"start_s": number, "end_s": number, "text": string, "position": "top_center" | "bottom_center" | "center" | "top_left" | "top_right" | "bottom_left" | "bottom_right", "style": "title_card" | "lower_third" | "callout" | "stat" | "label", "animation": "none" | "fade_in" | "typewriter" | "slide_in_up" | "pop"}],
  "music": {"enabled": boolean, "mood": "upbeat" | "chill" | "dramatic" | "corporate" | "playful" | "inspirational" | "dark" | "none", "start_s": number, "end_s": number, "volume": number, "duck_under_speech": boolean},
  "reframe": {"enabled": boolean, "target_aspect_ratio": "16:9" | "9:16" | "1:1" | "4:5", "focus": "center" | "custom"}
}

Caption rules:
- Whisper provides the canonical word list and timestamps.
- Do NOT rewrite full captions.words from scratch.
- Do NOT invent caption start_s/end_s values.
- Prefer sparse emphasis_by_index / omit_indices decisions.
- Keep output concise.

Zoom rules:
- zooms[].anchor is a coarse 3x3 region (fallback when anchor_xy is omitted).
- For a held object or precise subject, add anchor_xy: normalized (x,y) with (0,0)=top-left and (1,1)=bottom-right, placed on the subject's visual center. When anchor_xy is present, it overrides anchor for the zoom focal point so the punch-in stays on the subject.
- Reframe focus is only "center" | "custom" (no tracking).

Overlay rules:
- The model decides overlay intent only; do NOT output image_url.
- Always provide at least one of search_query or visual_description.
- Use stock_photo for real-world references; use generated_illustration/diagram for synthetic visuals.
""".strip()

DEFAULT_TIMELINE_PROMPT_TEMPLATE = """
You are analyzing a video for an editing pipeline.

Source metadata:
[[SOURCE_META_JSON]]

Return JSON only with this exact shape:
{
  "summary": "short summary",
  "events": [
    {
      "start": "mm:ss.ff",
      "end": "mm:ss.ff",
      "description": "short visual description",
      "visible_objects": ["object"],
      "confidence": "low|medium|high"
    }
  ]
}

Rules:
- Output at most 8 events.
- Timestamps must be in mm:ss.ff format.
- Each event must be at least 1 second long.
- Each description must be under 100 characters.
- Focus on visual changes and editing beats.
- Do NOT include markdown fences.
""".strip()

DEFAULT_PLAN_PROMPT_TEMPLATE = """
You are generating an edit plan for a deterministic renderer.

User editing request:
[[USER_PROMPT]]

Source metadata:
[[SOURCE_META_JSON]]

Timeline events from pass 1:
[[TIMELINE_EVENTS_JSON]]

Whisper word timestamps:
[[TRANSCRIPT_WORDS_JSON]]

Requirements:
- Keep segments gapless across the full video duration.
- Use cuts to remove silence/filler/repetition.
- Use overlays and text only when they clearly support spoken content.
- Keep edits tasteful and avoid over-editing.
- Whisper timing is authoritative; focus caption creativity on grouping and per-word emphasis.
- Keep caption words aligned with Whisper transcript ordering.
- Do not regenerate the full caption words array; add sparse creative decisions only.
- Return one concise JSON object of decisions; backend compiles and validates the final plan.

Contract:
[[EDIT_PLAN_CONTRACT]]
""".strip()


def _load_prompt_templates() -> dict[str, str]:
    templates = {
        "timeline": DEFAULT_TIMELINE_PROMPT_TEMPLATE,
        "plan": DEFAULT_PLAN_PROMPT_TEMPLATE,
    }
    try:
        data = json.loads(PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return templates
    except json.JSONDecodeError:
        return templates

    configured_templates = data.get("templates", {})
    if not isinstance(configured_templates, dict):
        return templates

    for key in templates:
        value = configured_templates.get(key)
        if isinstance(value, str) and value.strip():
            templates[key] = value.strip()
    return templates


def _render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"[[{key}]]", value)
    return rendered.strip()


def build_timeline_prompt(source_meta: dict[str, Any]) -> str:
    templates = _load_prompt_templates()
    return _render_template(
        templates["timeline"],
        {
            "SOURCE_META_JSON": json.dumps(source_meta, indent=2),
        },
    )


def build_plan_prompt(
    *,
    source_meta: dict[str, Any],
    events: list[dict[str, Any]],
    transcript_words: list[dict[str, Any]],
    user_prompt: str,
) -> str:
    # Keep transcript compact to avoid context blowups.
    transcript_slice = transcript_words[:TRANSCRIPT_WORD_LIMIT]
    templates = _load_prompt_templates()
    return _render_template(
        templates["plan"],
        {
            "USER_PROMPT": user_prompt,
            "SOURCE_META_JSON": json.dumps(source_meta, indent=2),
            "TIMELINE_EVENTS_JSON": json.dumps(events, indent=2),
            "TRANSCRIPT_WORDS_JSON": json.dumps(transcript_slice, indent=2),
            "EDIT_PLAN_CONTRACT": EDIT_PLAN_CONTRACT,
        },
    )

