from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

PIXABAY_ENDPOINT = "https://pixabay.com/api/"
OPENAI_IMAGE_ENDPOINT = "https://api.openai.com/v1/images/generations"
OVERLAY_DIR_NAME = "overlays"
REQUEST_TIMEOUT_S = 25

POSITION_TO_SIZE = {
    "fullscreen": "1536x1024",
    "top_half": "1536x1024",
    "bottom_half": "1536x1024",
}


def _public_relative_path(path: Path, public_dir: Path) -> str:
    return path.resolve().relative_to(public_dir.resolve()).as_posix()


def _is_local_public_safe(image_url: str, public_dir: Path) -> bool:
    if not image_url:
        return False
    parsed = urlparse(image_url)
    if parsed.scheme or parsed.netloc:
        return False
    if image_url.startswith("/") or ".." in Path(image_url).parts:
        return False
    candidate = (public_dir / image_url).resolve()
    return str(candidate).startswith(str(public_dir.resolve())) and candidate.exists()


def _overlay_cache_key(overlay: dict[str, Any]) -> str:
    payload = {
        "asset_type": overlay.get("asset_type", "stock_photo"),
        "visual_description": overlay.get("visual_description", ""),
        "search_query": overlay.get("search_query", ""),
        "image_query": overlay.get("image_query", ""),
        "style": overlay.get("style", ""),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _query_for_search(overlay: dict[str, Any]) -> str:
    for key in ("search_query", "image_query", "visual_description"):
        value = str(overlay.get(key, "")).strip()
        if value:
            return value
    return ""


def _generation_prompt(overlay: dict[str, Any]) -> str:
    description = str(overlay.get("visual_description", "")).strip()
    query = _query_for_search(overlay)
    style = str(overlay.get("style", "")).strip()
    asset_type = str(overlay.get("asset_type", "stock_photo")).strip()
    parts = [
        "Create a clean overlay image for a talking-head video.",
        f"Asset type: {asset_type}.",
        f"Core subject: {description or query}.",
        "No text, watermark, logos, or borders.",
        "Single clear subject with uncluttered composition.",
    ]
    if style:
        parts.append(f"Style direction: {style}.")
    return " ".join(parts)


def _size_for_overlay(overlay: dict[str, Any]) -> str:
    position = str(overlay.get("position", "")).strip().lower()
    return POSITION_TO_SIZE.get(position, "1024x1024")


def _guess_extension(content_type: str | None, fallback_url: str | None = None) -> str:
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ".jpg" if ext == ".jpe" else ext
    if fallback_url:
        parsed = urlparse(fallback_url)
        suffix = Path(parsed.path).suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return suffix
    return ".jpg"


def _resolve_from_pixabay(
    overlay: dict[str, Any],
    cache_key: str,
    overlays_dir: Path,
    pixabay_key: str,
) -> Path | None:
    query = _query_for_search(overlay)
    if not query:
        return None
    params = {
        "key": pixabay_key,
        "q": query,
        "image_type": "photo",
        "safesearch": "true",
        "per_page": 6,
    }
    response = requests.get(PIXABAY_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT_S)
    response.raise_for_status()
    hits = response.json().get("hits", [])
    if not hits:
        return None
    candidate = hits[0]
    source_url = candidate.get("largeImageURL") or candidate.get("webformatURL")
    if not source_url:
        return None
    media = requests.get(source_url, timeout=REQUEST_TIMEOUT_S)
    media.raise_for_status()
    ext = _guess_extension(media.headers.get("content-type"), source_url)
    out_path = overlays_dir / f"overlay_{cache_key}{ext}"
    out_path.write_bytes(media.content)
    return out_path


def _resolve_from_openai(
    overlay: dict[str, Any],
    cache_key: str,
    overlays_dir: Path,
    openai_key: str,
) -> Path | None:
    prompt = _generation_prompt(overlay)
    headers = {
        "Authorization": f"Bearer {openai_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.getenv("OPENAI_OVERLAY_MODEL", "gpt-image-1"),
        "prompt": prompt,
        "size": _size_for_overlay(overlay),
        "quality": os.getenv("OPENAI_OVERLAY_QUALITY", "medium"),
        "response_format": "b64_json",
    }
    response = requests.post(
        OPENAI_IMAGE_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data or "b64_json" not in data[0]:
        return None
    image_bytes = base64.b64decode(data[0]["b64_json"])
    out_path = overlays_dir / f"overlay_{cache_key}.png"
    out_path.write_bytes(image_bytes)
    return out_path


def resolve_overlay_assets(
    plan: dict[str, Any],
    public_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    """
    Resolve overlay intent into local public image assets.

    Returns a mutated plan clone and a list of warnings.
    """
    out_plan = dict(plan)
    overlays_raw = out_plan.get("overlays") or []
    if not isinstance(overlays_raw, list):
        out_plan["overlays"] = []
        return out_plan, ["overlays is not an array; dropped."]

    overlays_dir = public_dir / OVERLAY_DIR_NAME
    overlays_dir.mkdir(parents=True, exist_ok=True)
    pixabay_key = os.getenv("PIXABAY_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    warnings: list[str] = []
    resolved: list[dict[str, Any]] = []

    for idx, raw in enumerate(overlays_raw):
        if not isinstance(raw, dict):
            warnings.append(f"overlays[{idx}] is not an object; dropped.")
            continue
        overlay = dict(raw)

        existing_url = str(overlay.get("image_url", "")).strip()
        if existing_url and _is_local_public_safe(existing_url, public_dir):
            resolved.append(overlay)
            continue
        overlay.pop("image_url", None)

        cache_key = _overlay_cache_key(overlay)
        cached = list(overlays_dir.glob(f"overlay_{cache_key}.*"))
        if cached:
            overlay["image_url"] = _public_relative_path(cached[0], public_dir)
            resolved.append(overlay)
            continue

        output_path: Path | None = None
        query = _query_for_search(overlay)
        asset_type = str(overlay.get("asset_type", "stock_photo")).strip()
        # Stock searches should hit Pixabay first; illustration intent should try OpenAI first
        # when a key is present, then fall back to stock search.
        prefer_openai_first = asset_type == "generated_illustration" and bool(openai_key)

        if prefer_openai_first:
            try:
                output_path = _resolve_from_openai(overlay, cache_key, overlays_dir, openai_key)
            except requests.RequestException as exc:
                warnings.append(f"overlays[{idx}] openai generation failed: {exc}")

        if output_path is None and query and pixabay_key:
            try:
                output_path = _resolve_from_pixabay(overlay, cache_key, overlays_dir, pixabay_key)
            except requests.RequestException as exc:
                warnings.append(f"overlays[{idx}] pixabay lookup failed: {exc}")

        if output_path is None and openai_key and not prefer_openai_first:
            try:
                output_path = _resolve_from_openai(overlay, cache_key, overlays_dir, openai_key)
            except requests.RequestException as exc:
                warnings.append(f"overlays[{idx}] openai generation failed: {exc}")

        if output_path is None:
            warnings.append(f"overlays[{idx}] unresolved and dropped (no usable Pixabay/OpenAI result).")
            continue

        overlay["image_url"] = _public_relative_path(output_path, public_dir)
        resolved.append(overlay)

    out_plan["overlays"] = resolved
    return out_plan, warnings
