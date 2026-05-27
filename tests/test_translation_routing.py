from __future__ import annotations

import unittest
from unittest import mock


class TranslationRoutingConfigTests(unittest.TestCase):
    def test_explicit_google_is_honored_for_kannada(self) -> None:
        from translation.run_translate import _effective_preferred_engine

        with mock.patch.dict(
            "os.environ",
            {"VIDIOLINGUA_TRANSLATION_ENGINE": "google"},
            clear=False,
        ):
            self.assertEqual(_effective_preferred_engine("en", "kn"), "deep_translator")

    def test_auto_uses_indictrans2_for_kannada(self) -> None:
        from translation.base import TranslationRequest
        from translation.router import select_translation_engine

        request = TranslationRequest(
            source_text="This is a test.",
            source_language="en",
            target_language="kn",
            preferred_engine="auto",
        )
        self.assertEqual(select_translation_engine(request), "indictrans2")


if __name__ == "__main__":
    unittest.main()
