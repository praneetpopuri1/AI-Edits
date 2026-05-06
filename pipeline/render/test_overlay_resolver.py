from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pipeline.render.overlay_resolver import resolve_overlay_assets


class OverlayResolverTests(unittest.TestCase):
    def test_keeps_existing_local_overlay_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp) / "public"
            overlays_dir = public_dir / "overlays"
            overlays_dir.mkdir(parents=True, exist_ok=True)
            asset_path = overlays_dir / "existing.png"
            asset_path.write_bytes(b"png")

            plan = {
                "overlays": [
                    {
                        "start_s": 1.0,
                        "end_s": 2.0,
                        "position": "picture_in_picture",
                        "image_url": "overlays/existing.png",
                        "search_query": "plane",
                    }
                ]
            }
            out, warnings = resolve_overlay_assets(plan, public_dir)
            self.assertEqual(warnings, [])
            self.assertEqual(out["overlays"][0]["image_url"], "overlays/existing.png")

    @patch("pipeline.render.overlay_resolver.requests.get")
    def test_resolves_via_pixabay(self, mock_get: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp) / "public"
            public_dir.mkdir(parents=True, exist_ok=True)
            plan = {
                "overlays": [
                    {
                        "start_s": 1.0,
                        "end_s": 2.0,
                        "position": "picture_in_picture",
                        "search_query": "plane in sky",
                    }
                ]
            }

            pixabay_response = Mock()
            pixabay_response.json.return_value = {
                "hits": [{"largeImageURL": "https://example.com/plane.jpg"}]
            }
            pixabay_response.raise_for_status.return_value = None

            image_response = Mock()
            image_response.content = b"img"
            image_response.headers = {"content-type": "image/jpeg"}
            image_response.raise_for_status.return_value = None

            mock_get.side_effect = [pixabay_response, image_response]
            with patch.dict("os.environ", {"PIXABAY_API_KEY": "pix-key"}, clear=False):
                out, warnings = resolve_overlay_assets(plan, public_dir)

            self.assertEqual(warnings, [])
            self.assertEqual(len(out["overlays"]), 1)
            self.assertTrue(out["overlays"][0]["image_url"].startswith("overlays/overlay_"))
            self.assertTrue((public_dir / out["overlays"][0]["image_url"]).exists())

    @patch("pipeline.render.overlay_resolver.requests.post")
    @patch("pipeline.render.overlay_resolver.requests.get")
    def test_falls_back_to_openai(self, mock_get: Mock, mock_post: Mock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            public_dir = Path(tmp) / "public"
            public_dir.mkdir(parents=True, exist_ok=True)
            plan = {
                "overlays": [
                    {
                        "start_s": 1.0,
                        "end_s": 2.0,
                        "position": "fullscreen",
                        "visual_description": "a plane flying over turquoise ocean",
                        "asset_type": "generated_illustration",
                    }
                ]
            }

            pixabay_empty = Mock()
            pixabay_empty.json.return_value = {"hits": []}
            pixabay_empty.raise_for_status.return_value = None
            mock_get.return_value = pixabay_empty

            payload = base64.b64encode(b"png-data").decode("utf-8")
            openai_response = Mock()
            openai_response.json.return_value = {"data": [{"b64_json": payload}]}
            openai_response.raise_for_status.return_value = None
            mock_post.return_value = openai_response

            with patch.dict(
                "os.environ",
                {"PIXABAY_API_KEY": "pix-key", "OPENAI_API_KEY": "openai-key"},
                clear=False,
            ):
                out, warnings = resolve_overlay_assets(plan, public_dir)

            self.assertEqual(warnings, [])
            self.assertEqual(len(out["overlays"]), 1)
            self.assertTrue(out["overlays"][0]["image_url"].endswith(".png"))
            self.assertTrue((public_dir / out["overlays"][0]["image_url"]).exists())


if __name__ == "__main__":
    unittest.main()
