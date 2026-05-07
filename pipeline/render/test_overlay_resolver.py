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

    @patch("pipeline.render.overlay_resolver.requests.post")
    def test_resolves_stock_overlay_via_openai(self, mock_post: Mock) -> None:
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

            payload = base64.b64encode(b"png-bytes").decode("utf-8")
            openai_response = Mock()
            openai_response.json.return_value = {"data": [{"b64_json": payload}]}
            openai_response.raise_for_status.return_value = None
            mock_post.return_value = openai_response

            with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}, clear=False):
                out, warnings = resolve_overlay_assets(plan, public_dir)

            self.assertEqual(warnings, [])
            self.assertEqual(len(out["overlays"]), 1)
            self.assertTrue(out["overlays"][0]["image_url"].startswith("overlays/overlay_"))
            self.assertTrue(out["overlays"][0]["image_url"].endswith(".png"))
            self.assertTrue((public_dir / out["overlays"][0]["image_url"]).exists())

    @patch("pipeline.render.overlay_resolver.requests.post")
    def test_resolves_generated_illustration_via_openai(self, mock_post: Mock) -> None:
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

            payload = base64.b64encode(b"png-data").decode("utf-8")
            openai_response = Mock()
            openai_response.json.return_value = {"data": [{"b64_json": payload}]}
            openai_response.raise_for_status.return_value = None
            mock_post.return_value = openai_response

            with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}, clear=False):
                out, warnings = resolve_overlay_assets(plan, public_dir)

            self.assertEqual(warnings, [])
            self.assertEqual(len(out["overlays"]), 1)
            self.assertTrue(out["overlays"][0]["image_url"].endswith(".png"))
            self.assertTrue((public_dir / out["overlays"][0]["image_url"]).exists())


if __name__ == "__main__":
    unittest.main()
